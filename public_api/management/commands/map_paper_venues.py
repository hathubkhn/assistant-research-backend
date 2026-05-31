"""
Export papers → test venue mapping via CSV → apply approved mappings to DB.

Examples:
  python manage.py map_paper_venues export --limit 100 -o data/venue_mapping_input.csv
  python manage.py map_paper_venues test -i data/venue_mapping_input.csv -o data/venue_mapping_results.csv
  python manage.py map_paper_venues apply -i data/venue_mapping_results.csv --dry-run
  python manage.py map_paper_venues apply -i data/venue_mapping_results.csv --status ok_auto
"""
import csv
import os
import time
import uuid as uuid_mod

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from public_api.models import Conference, Journal, Paper, PaperVenueMapping
from public_api.services.venue_mapping import map_paper_record

MAPPING_UPDATE_FIELDS = [
    "lookup_key",
    "status",
    "input_doi",
    "resolved_doi",
    "classification",
    "venue_from_api",
    "match_score",
    "api_source",
    "year",
    "db_venue_kind",
    "db_venue_id",
    "db_venue_name",
    "db_venue_fuzzy_score",
    "no_match_db_payload",
    "notes",
    "candidates_count",
    "processed_at",
]


def _parse_uuid(value) -> uuid_mod.UUID | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return uuid_mod.UUID(text)
    except ValueError:
        return None


def _row_to_mapping(paper_id: str, row: dict) -> PaperVenueMapping:
    return PaperVenueMapping(
        paper_id=paper_id,
        lookup_key=str(row.get("lookup_key") or "")[:128],
        status=str(row.get("status") or PaperVenueMapping.Status.NO_VENUE),
        input_doi=str(row.get("input_doi") or "")[:200],
        resolved_doi=str(row.get("resolved_doi") or "")[:200],
        classification=str(row.get("classification") or "")[:80],
        venue_from_api=str(row.get("venue_from_api") or "")[:500],
        match_score=row.get("match_score") if row.get("match_score") != "" else None,
        api_source=str(row.get("api_source") or "")[:80],
        year=str(row.get("year") or "")[:16],
        db_venue_kind=str(row.get("db_venue_kind") or "")[:20],
        db_venue_id=_parse_uuid(row.get("db_venue_id")),
        db_venue_name=str(row.get("db_venue_name") or "")[:255],
        db_venue_fuzzy_score=row.get("db_venue_fuzzy_score")
        if row.get("db_venue_fuzzy_score") != ""
        else None,
        no_match_db_payload=str(row.get("no_match_db_payload") or ""),
        notes=str(row.get("notes") or "")[:255],
        candidates_count=int(row.get("candidates_count") or 0),
        processed_at=timezone.now(),
    )


class Command(BaseCommand):
    help = "Export / test / apply paper → journal|conference venue mapping"

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="action", required=True)

        export = sub.add_parser("export", help="Export papers from DB to CSV for batch testing")
        export.add_argument("--limit", type=int, default=100)
        export.add_argument("-o", "--output", required=True, help="Output CSV path")
        export.add_argument(
            "--only-missing-venue",
            action="store_true",
            help="Only papers without journal and conference FK",
        )
        export.add_argument(
            "--arxiv-only",
            action="store_true",
            help="Only papers whose DOI looks like arXiv (10.48550/arxiv...)",
        )

        test = sub.add_parser("test", help="Run external API mapping on CSV rows")
        test.add_argument("-i", "--input", required=True)
        test.add_argument("-o", "--output", required=True)
        test.add_argument("--delay", type=float, default=0.5, help="Seconds between papers")
        test.add_argument("--min-title-match", type=int, default=85)
        test.add_argument("--min-db-match", type=int, default=82)
        test.add_argument(
            "--no-match-db-output",
            default="",
            help="Optional CSV path for rows with status=no_match_db. "
            "Default: <output>_no_match_db.csv",
        )

        apply_cmd = sub.add_parser("apply", help="Apply mapping results CSV to DB")
        apply_cmd.add_argument("-i", "--input", required=True)
        apply_cmd.add_argument(
            "--status",
            default="ok_auto",
            help="Comma-separated status values to apply (default: ok_auto)",
        )
        apply_cmd.add_argument(
            "--dry-run",
            action="store_true",
            help="Print changes without saving",
        )
        apply_cmd.add_argument(
            "--update-doi",
            action="store_true",
            help="Overwrite paper.doi when resolved_doi differs",
        )

        run = sub.add_parser(
            "run",
            help="Scale mapping: DB → cache + paper_venue_mapping (dedupe API via cache)",
        )
        run.add_argument("--limit", type=int, default=0, help="0 = no limit")
        run.add_argument(
            "--only-missing-venue",
            action="store_true",
            help="Only papers without journal and conference FK",
        )
        run.add_argument(
            "--resume",
            action="store_true",
            help="Skip papers that already have a PaperVenueMapping row",
        )
        run.add_argument(
            "--write-batch",
            type=int,
            default=1000,
            help="Bulk upsert PaperVenueMapping every N papers",
        )
        run.add_argument(
            "--fast",
            action="store_true",
            help="Skip Semantic Scholar (faster; Crossref + OpenAlex only)",
        )
        run.add_argument("--min-title-match", type=int, default=85)
        run.add_argument("--min-db-match", type=int, default=82)
        run.add_argument(
            "--log-every",
            type=int,
            default=500,
            help="Progress log interval",
        )

        apply_db = sub.add_parser(
            "apply-db",
            help="Apply PaperVenueMapping rows to Paper (bulk, no CSV)",
        )
        apply_db.add_argument(
            "--status",
            default="ok_auto",
            help="Comma-separated statuses (default: ok_auto)",
        )
        apply_db.add_argument("--dry-run", action="store_true")
        apply_db.add_argument("--update-doi", action="store_true")
        apply_db.add_argument(
            "--bulk-size",
            type=int,
            default=500,
            help="Papers per bulk_update batch",
        )
        apply_db.add_argument(
            "--assign-others",
            action="store_true",
            help='Before apply: set all status=review mappings to Conference "Others"',
        )

        export_results = sub.add_parser(
            "export-results",
            help="Export paper_venue_mapping table to CSV for Excel review",
        )
        export_results.add_argument("-o", "--output", required=True)
        export_results.add_argument(
            "--status",
            default="",
            help="Comma-separated statuses to include (default: all)",
        )
        export_results.add_argument("--limit", type=int, default=0, help="0 = no limit")

    def handle(self, *args, **options):
        action = options["action"]
        if action == "export":
            self._export(options)
        elif action == "test":
            self._test(options)
        elif action == "apply":
            self._apply(options)
        elif action == "run":
            self._run(options)
        elif action == "apply-db":
            self._apply_db(options)
        elif action == "export-results":
            self._export_results(options)

    def _paper_queryset(self, options):
        qs = Paper.objects.all().order_by("id")
        if options.get("only_missing_venue"):
            qs = qs.filter(journal__isnull=True, conference__isnull=True)
        if options.get("arxiv_only"):
            qs = qs.filter(doi__icontains="10.48550/arxiv")
        return qs

    def _export(self, options):
        qs = self._paper_queryset(options)
        limit = options["limit"]
        if limit <= 0:
            self.stderr.write(self.style.ERROR("export requires --limit > 0 (use run for full corpus)"))
            return
        papers = list(qs[:limit])

        out_path = options["output"]
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "paper_id",
                    "title",
                    "doi",
                    "current_journal_id",
                    "current_conference_id",
                ],
            )
            writer.writeheader()
            for p in papers:
                writer.writerow({
                    "paper_id": str(p.id),
                    "title": p.title,
                    "doi": p.doi or "",
                    "current_journal_id": str(p.journal_id) if p.journal_id else "",
                    "current_conference_id": str(p.conference_id) if p.conference_id else "",
                })

        self.stdout.write(self.style.SUCCESS(f"Exported {len(papers)} papers → {out_path}"))

    def _load_venue_catalogs(self):
        journals = [(str(j.id), j.name) for j in Journal.objects.only("id", "name")]
        conferences = [(str(c.id), c.name) for c in Conference.objects.only("id", "name")]
        return journals, conferences

    def _test(self, options):
        df = pd.read_csv(options["input"])
        journals, conferences = self._load_venue_catalogs()
        rows_out = []
        total = len(df)

        for idx, row in df.iterrows():
            paper_id = str(row.get("paper_id", "")).strip()
            title = str(row.get("title", "")).strip()
            doi = str(row.get("doi", "")).strip() if pd.notna(row.get("doi")) else ""

            self.stdout.write(f"[{idx + 1}/{total}] {title[:60]}...")

            result = map_paper_record(
                paper_id=paper_id,
                title=title,
                doi=doi or None,
                journals=journals,
                conferences=conferences,
                min_title_match=options["min_title_match"],
                min_db_match=options["min_db_match"],
            )
            rows_out.append(result)
            time.sleep(options["delay"])

        out_df = pd.DataFrame(rows_out)
        out_path = options["output"]
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        out_df.to_csv(out_path, index=False)

        no_match_df = out_df[out_df["status"] == "no_match_db"]
        if not no_match_df.empty:
            no_match_path = options["no_match_db_output"].strip()
            if not no_match_path:
                root, ext = os.path.splitext(out_path)
                ext = ext or ".csv"
                no_match_path = f"{root}_no_match_db{ext}"
            os.makedirs(os.path.dirname(os.path.abspath(no_match_path)) or ".", exist_ok=True)
            no_match_df.to_csv(no_match_path, index=False)
            self.stdout.write(
                self.style.WARNING(
                    f"Wrote {len(no_match_df)} no_match_db rows → {no_match_path}"
                )
            )

        counts = out_df["status"].value_counts().to_dict()
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(rows_out)} rows → {out_path}"))
        self.stdout.write(f"Status breakdown: {counts}")

    def _apply(self, options):
        df = pd.read_csv(options["input"])
        allowed = {s.strip() for s in options["status"].split(",") if s.strip()}
        dry_run = options["dry_run"]
        update_doi = options["update_doi"]

        updated = 0
        skipped = 0
        errors = 0

        for _, row in df.iterrows():
            status = str(row.get("status", "")).strip()
            if status not in allowed:
                skipped += 1
                continue

            paper_id = str(row.get("paper_id", "")).strip()
            if not paper_id:
                skipped += 1
                continue

            try:
                paper = Paper.objects.get(pk=paper_id)
            except Paper.DoesNotExist:
                self.stderr.write(self.style.WARNING(f"Paper not found: {paper_id}"))
                errors += 1
                continue

            venue_kind = str(row.get("db_venue_kind", "")).strip()
            venue_id = str(row.get("db_venue_id", "")).strip()
            resolved_doi = str(row.get("resolved_doi", "")).strip()

            if not venue_kind or not venue_id:
                skipped += 1
                continue

            msg = (
                f"{'[dry-run] ' if dry_run else ''}{paper.title[:50]}… "
                f"→ {venue_kind} {row.get('db_venue_name', venue_id)}"
            )
            if update_doi and resolved_doi and resolved_doi != (paper.doi or ""):
                msg += f" | DOI: {paper.doi} → {resolved_doi}"

            self.stdout.write(msg)

            if dry_run:
                updated += 1
                continue

            with transaction.atomic():
                if venue_kind == "journal":
                    paper.journal_id = venue_id
                    paper.conference_id = None
                elif venue_kind == "conference":
                    paper.conference_id = venue_id
                    paper.journal_id = None
                else:
                    skipped += 1
                    continue

                if update_doi and resolved_doi:
                    paper.doi = resolved_doi

                paper.save(update_fields=["journal", "conference", "doi", "updated_at"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. applied={updated} skipped={skipped} errors={errors} dry_run={dry_run}"
            )
        )

    def _flush_mapping_batch(self, batch: list[PaperVenueMapping]) -> None:
        if not batch:
            return
        PaperVenueMapping.objects.bulk_create(
            batch,
            update_conflicts=["paper_id"],
            unique_fields=["paper_id"],
            update_fields=MAPPING_UPDATE_FIELDS,
        )
        batch.clear()

    def _run(self, options):
        qs = self._paper_queryset(options)
        if options["limit"] > 0:
            qs = qs[: options["limit"]]

        journals, conferences = self._load_venue_catalogs()
        skip_ss = options["fast"]
        batch: list[PaperVenueMapping] = []
        processed = 0
        cache_hits = 0
        api_calls = 0

        from public_api.models import VenueLookupCache
        from public_api.services.venue_mapping import build_lookup_key

        for paper in qs.iterator(chunk_size=2000):
            if options["resume"] and PaperVenueMapping.objects.filter(paper_id=paper.id).exists():
                continue

            key_info = build_lookup_key(paper.doi, paper.title)
            if key_info and VenueLookupCache.objects.filter(lookup_key=key_info[0]).exists():
                cache_hits += 1
            elif key_info:
                api_calls += 1

            row = map_paper_record(
                paper_id=str(paper.id),
                title=paper.title,
                doi=paper.doi or None,
                journals=journals,
                conferences=conferences,
                min_title_match=options["min_title_match"],
                min_db_match=options["min_db_match"],
                skip_semantic_scholar=skip_ss,
            )
            batch.append(_row_to_mapping(str(paper.id), row))
            processed += 1

            if len(batch) >= options["write_batch"]:
                self._flush_mapping_batch(batch)

            if processed % options["log_every"] == 0:
                self.stdout.write(
                    f"… {processed} papers | cache_hits≈{cache_hits} api_lookups≈{api_calls}"
                )

        self._flush_mapping_batch(batch)

        counts = dict(
            PaperVenueMapping.objects.values_list("status")
            .annotate(c=Count("id"))
            .values_list("status", "c")
        )
        self.stdout.write(self.style.SUCCESS(f"Processed {processed} papers into paper_venue_mapping"))
        self.stdout.write(f"Status in DB: {counts}")
        self.stdout.write(
            f"Unique API lookups (approx): {api_calls} | cache hits (approx): {cache_hits}"
        )

    def _apply_db(self, options):
        allowed = {s.strip() for s in options["status"].split(",") if s.strip()}
        dry_run = options["dry_run"]
        update_doi = options["update_doi"]
        bulk_size = options["bulk_size"]

        if options["assign_others"]:
            try:
                others = Conference.objects.get(name="Others")
            except Conference.DoesNotExist:
                self.stderr.write(self.style.ERROR('Conference "Others" not found. Run ensure_others_conference.'))
                return
            if not dry_run:
                updated = PaperVenueMapping.objects.filter(
                    status=PaperVenueMapping.Status.REVIEW
                ).update(
                    db_venue_kind="conference",
                    db_venue_id=others.id,
                    db_venue_name=others.name,
                    notes="assigned_to_others_bucket",
                )
                self.stdout.write(self.style.WARNING(f"Assigned {updated} review rows → Others"))

        qs = (
            PaperVenueMapping.objects.filter(status__in=allowed)
            .exclude(db_venue_id__isnull=True)
            .exclude(db_venue_kind="")
            .select_related("paper")
            .order_by("paper_id")
        )

        total = qs.count()
        updated = 0
        skipped = 0
        buffer: list[Paper] = []

        for mapping in qs.iterator(chunk_size=bulk_size):
            paper = mapping.paper
            if mapping.db_venue_kind == "journal":
                paper.journal_id = mapping.db_venue_id
                paper.conference_id = None
            elif mapping.db_venue_kind == "conference":
                paper.conference_id = mapping.db_venue_id
                paper.journal_id = None
            else:
                skipped += 1
                continue

            if update_doi and mapping.resolved_doi:
                paper.doi = mapping.resolved_doi

            if dry_run:
                updated += 1
                continue

            buffer.append(paper)
            if len(buffer) >= bulk_size:
                Paper.objects.bulk_update(
                    buffer,
                    ["journal_id", "conference_id", "doi", "updated_at"],
                )
                updated += len(buffer)
                buffer.clear()

        if not dry_run and buffer:
            Paper.objects.bulk_update(
                buffer,
                ["journal_id", "conference_id", "doi", "updated_at"],
            )
            updated += len(buffer)

        self.stdout.write(
            self.style.SUCCESS(
                f"apply-db: {updated}/{total} papers "
                f"(skipped={skipped}, dry_run={dry_run})"
            )
        )

    def _export_results(self, options):
        qs = (
            PaperVenueMapping.objects.select_related("paper")
            .order_by("paper_id")
        )
        status_filter = [s.strip() for s in options["status"].split(",") if s.strip()]
        if status_filter:
            qs = qs.filter(status__in=status_filter)

        limit = options["limit"]
        if limit > 0:
            qs = qs[:limit]

        out_path = options["output"]
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)

        fieldnames = [
            "paper_id",
            "title",
            "lookup_key",
            "status",
            "input_doi",
            "resolved_doi",
            "classification",
            "venue_from_api",
            "match_score",
            "api_source",
            "year",
            "db_venue_kind",
            "db_venue_id",
            "db_venue_name",
            "db_venue_fuzzy_score",
            "no_match_db_payload",
            "notes",
            "candidates_count",
        ]

        count = 0
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for m in qs.iterator(chunk_size=2000):
                writer.writerow({
                    "paper_id": str(m.paper_id),
                    "title": m.paper.title if m.paper_id else "",
                    "lookup_key": m.lookup_key,
                    "status": m.status,
                    "input_doi": m.input_doi,
                    "resolved_doi": m.resolved_doi,
                    "classification": m.classification,
                    "venue_from_api": m.venue_from_api,
                    "match_score": m.match_score if m.match_score is not None else "",
                    "api_source": m.api_source,
                    "year": m.year,
                    "db_venue_kind": m.db_venue_kind,
                    "db_venue_id": str(m.db_venue_id) if m.db_venue_id else "",
                    "db_venue_name": m.db_venue_name,
                    "db_venue_fuzzy_score": m.db_venue_fuzzy_score
                    if m.db_venue_fuzzy_score is not None
                    else "",
                    "no_match_db_payload": m.no_match_db_payload,
                    "notes": m.notes,
                    "candidates_count": m.candidates_count,
                })
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Exported {count} rows → {out_path}"))
        if status_filter:
            self.stdout.write(f"Filter status: {status_filter}")

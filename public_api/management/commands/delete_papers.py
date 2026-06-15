"""
Delete papers and all related DB rows (M2M, user bookmarks, venue mapping, Qdrant).

Usage:
    python manage.py delete_papers                          # IDs from data/papers_to_delete.txt
    python manage.py delete_papers --ids <uuid>,<uuid>      # explicit IDs
    python manage.py delete_papers --file path/to/ids.txt
    python manage.py delete_papers --dry-run                # preview only
    python manage.py delete_papers --skip-embedding         # DB only, keep Qdrant vectors
"""
from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from public_api.models import (
    DownloadedPaper,
    InterestingPaper,
    Paper,
    PaperVenueMapping,
)
from public_api.services.embed_client import delete_embedding

DEFAULT_IDS_FILE = Path(settings.BASE_DIR) / "data" / "papers_to_delete.txt"


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value.strip())
    except ValueError as exc:
        raise CommandError(f"Invalid UUID: {value!r}") from exc


def _load_ids_from_file(path: Path) -> list[uuid.UUID]:
    if not path.is_file():
        raise CommandError(f"IDs file not found: {path}")
    ids: list[uuid.UUID] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        ids.append(_parse_uuid(line))
    if not ids:
        raise CommandError(f"No paper IDs found in {path}")
    return ids


def _relation_counts(paper: Paper) -> dict[str, int]:
    return {
        "references_out": paper.references.count(),
        "references_in": paper.referenced_papers.count(),
        "authors": paper.authors.count(),
        "datasets": paper.datasets.count(),
        "tasks": paper.tasks.count(),
        "interesting": InterestingPaper.objects.filter(paper=paper).count(),
        "downloaded": DownloadedPaper.objects.filter(paper=paper).count(),
        "venue_mapping": PaperVenueMapping.objects.filter(paper=paper).count(),
    }


def _clear_m2m(paper: Paper) -> None:
    ref_through = Paper.references.through
    ref_through.objects.filter(from_paper_id=paper.id).delete()
    ref_through.objects.filter(to_paper_id=paper.id).delete()

    paper.authors.clear()
    paper.datasets.clear()
    paper.tasks.clear()


def _delete_paper_row(
    paper: Paper,
    *,
    delete_files: bool,
    delete_embedding_flag: bool,
) -> None:
    _clear_m2m(paper)

    InterestingPaper.objects.filter(paper=paper).delete()
    DownloadedPaper.objects.filter(paper=paper).delete()
    PaperVenueMapping.objects.filter(paper=paper).delete()

    paper_id = str(paper.id)

    if delete_files and paper.pdf_file:
        paper.pdf_file.delete(save=False)

    paper.delete()

    if delete_embedding_flag:
        delete_embedding(paper_id)


class Command(BaseCommand):
    help = "Delete papers by UUID together with all related rows and optional Qdrant embeddings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ids",
            type=str,
            default="",
            help="Comma-separated paper UUIDs",
        )
        parser.add_argument(
            "--file",
            type=str,
            default="",
            help=f"Text file with one UUID per line (default: {DEFAULT_IDS_FILE})",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without changing the database",
        )
        parser.add_argument(
            "--skip-embedding",
            action="store_true",
            help="Do not call research_assistant DELETE /papers/{id}",
        )
        parser.add_argument(
            "--keep-files",
            action="store_true",
            help="Do not remove PDF files from storage",
        )

    def handle(self, *args, **options):
        if options["ids"]:
            paper_ids = [_parse_uuid(part) for part in options["ids"].split(",") if part.strip()]
        else:
            path = Path(options["file"]) if options["file"] else DEFAULT_IDS_FILE
            paper_ids = _load_ids_from_file(path)

        dry_run = options["dry_run"]
        delete_embedding_flag = not options["skip_embedding"]
        delete_files = not options["keep_files"]

        self.stdout.write(f"Paper IDs to process: {len(paper_ids)}")

        found = list(Paper.objects.filter(id__in=paper_ids).order_by("created_at"))
        found_ids = {p.id for p in found}
        missing = [pid for pid in paper_ids if pid not in found_ids]

        if missing:
            self.stdout.write(self.style.WARNING(f"Not found in DB ({len(missing)}):"))
            for pid in missing:
                self.stdout.write(f"  - {pid}")

        if not found:
            raise CommandError("No matching papers in the database.")

        deleted = 0
        for paper in found:
            counts = _relation_counts(paper)
            title = (paper.title or "")[:80]
            self.stdout.write(f"\n{paper.id} | {title}")
            for key, value in counts.items():
                if value:
                    self.stdout.write(f"  {key}: {value}")

            if dry_run:
                self.stdout.write(self.style.NOTICE("  [dry-run] would delete"))
                continue

            try:
                with transaction.atomic():
                    _delete_paper_row(
                        paper,
                        delete_files=delete_files,
                        delete_embedding_flag=delete_embedding_flag,
                    )
                deleted += 1
                self.stdout.write(self.style.SUCCESS("  deleted"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  FAILED: {exc}"))

        if dry_run:
            self.stdout.write(self.style.NOTICE(f"\nDry run complete. {len(found)} papers would be deleted."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nDone. deleted={deleted} missing={len(missing)}"))

"""
Apply venue mapping to a Paper at ingest time (upload, crawler callback).

Status handling:
  ok_auto      -> link matched journal/conference
  review       -> link Conference "Others"
  no_match_db  -> create Journal/Conference (sparse fields) then link
  no_venue     -> leave FKs empty
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from django.db import close_old_connections, transaction
from django.db.utils import InterfaceError, OperationalError

from public_api.models import Conference, Journal, Paper, PaperVenueMapping
from public_api.services.venue_mapping import (
    MIN_DB_VENUE_MATCH,
    MIN_TITLE_MATCH,
    is_arxiv_doi,
    map_paper_record,
    normalize_doi,
    venue_kind_from_classification,
)

logger = logging.getLogger(__name__)

VENUE_OK_AUTO_FUZZY = int(os.environ.get("VENUE_OK_AUTO_FUZZY", "92"))
OTHERS_NAME = "Others"
OTHERS_RANK = ""  # unranked bucket; list API displays as "Not ranked"


def get_venue_id_lists() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    journals = [(str(pk), name) for pk, name in Journal.objects.values_list("id", "name")]
    conferences = [
        (str(pk), name) for pk, name in Conference.objects.values_list("id", "name")
    ]
    return journals, conferences


def get_or_create_others_conference() -> Conference:
    conference, _ = Conference.objects.update_or_create(
        name=OTHERS_NAME,
        defaults={
            "abbreviation": "",
            "rank": OTHERS_RANK,
            "location": "",
            "url": "",
        },
    )
    return conference


def _parse_uuid(value: Any) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _row_to_mapping_defaults(paper_id: str, row: dict[str, Any]) -> dict[str, Any]:
    fuzzy = row.get("db_venue_fuzzy_score")
    if fuzzy == "":
        fuzzy = None
    match_score = row.get("match_score")
    if match_score == "":
        match_score = None
    return {
        "lookup_key": str(row.get("lookup_key") or "")[:128],
        "status": str(row.get("status") or PaperVenueMapping.Status.NO_VENUE),
        "input_doi": str(row.get("input_doi") or "")[:200],
        "resolved_doi": str(row.get("resolved_doi") or "")[:200],
        "classification": str(row.get("classification") or "")[:80],
        "venue_from_api": str(row.get("venue_from_api") or "")[:500],
        "match_score": match_score,
        "api_source": str(row.get("api_source") or "")[:80],
        "year": str(row.get("year") or "")[:16],
        "db_venue_kind": str(row.get("db_venue_kind") or "")[:20],
        "db_venue_id": _parse_uuid(row.get("db_venue_id")),
        "db_venue_name": str(row.get("db_venue_name") or "")[:255],
        "db_venue_fuzzy_score": fuzzy,
        "no_match_db_payload": str(row.get("no_match_db_payload") or ""),
        "notes": str(row.get("notes") or "")[:255],
        "candidates_count": int(row.get("candidates_count") or 0),
    }


def _truncate(value: str | None, max_len: int) -> str:
    if not value:
        return ""
    return str(value).strip()[:max_len]


def create_venue_from_mapping_row(row: dict[str, Any]) -> tuple[str, uuid.UUID, bool]:
    """
    Create Journal or Conference when API venue is not in DB.
    Returns (kind, id, created).
    """
    venue_name = _truncate(row.get("venue_from_api"), 255)
    if not venue_name:
        raise ValueError("venue_from_api is required to create a venue")

    kind = (row.get("db_venue_kind") or "").strip() or venue_kind_from_classification(
        str(row.get("classification") or "")
    )
    if kind not in ("journal", "conference"):
        kind = "conference"

    publisher = _truncate(row.get("publisher"), 255)
    venue_url = _truncate(row.get("venue_url"), 200)

    if kind == "journal":
        journal, created = Journal.objects.get_or_create(
            name=venue_name,
            defaults={
                "abbreviation": "",
                "quartile": "",
                "publisher": publisher,
                "url": venue_url,
            },
        )
        return "journal", journal.id, created

    conference, created = Conference.objects.get_or_create(
        name=venue_name,
        defaults={
            "abbreviation": "",
            "rank": "",
            "location": "",
            "url": venue_url,
        },
    )
    return "conference", conference.id, created


def _assign_review_to_others(row: dict[str, Any]) -> None:
    others = get_or_create_others_conference()
    row["db_venue_kind"] = "conference"
    row["db_venue_id"] = str(others.id)
    row["db_venue_name"] = others.name
    note = (row.get("notes") or "").strip()
    row["notes"] = f"{note};auto_assigned_others".strip(";")


def _mapping_row_for_venue_create(mapping: PaperVenueMapping) -> dict[str, Any]:
    from public_api.services.venue_mapping import (
        parse_no_match_db_payload,
        venue_kind_from_classification,
    )

    payload = parse_no_match_db_payload(mapping.no_match_db_payload or "")
    kind = (
        (mapping.db_venue_kind or "").strip()
        or payload.get("suggested_kind")
        or venue_kind_from_classification(mapping.classification or "")
        or "conference"
    )
    if kind not in ("journal", "conference"):
        kind = "conference"

    return {
        "venue_from_api": mapping.venue_from_api,
        "classification": mapping.classification,
        "db_venue_kind": kind,
        "resolved_doi": mapping.resolved_doi,
        "publisher": payload.get("publisher", ""),
        "venue_url": "",
    }


def _is_db_connection_error(exc: BaseException) -> bool:
    if isinstance(exc, (OperationalError, InterfaceError)):
        return True
    msg = str(exc).lower()
    return "connection" in msg and ("closed" in msg or "terminated" in msg or "reset" in msg)


def _process_materialize_batch(
    mappings: list[PaperVenueMapping],
    *,
    venue_cache: dict[tuple[str, str], uuid.UUID],
    dry_run: bool,
    update_doi: bool,
    skip_if_paper_has_venue: bool,
    stats: dict[str, int],
) -> tuple[list[PaperVenueMapping], list[Paper]]:
    mapping_buffer: list[PaperVenueMapping] = []
    paper_buffer: list[Paper] = []

    for mapping in mappings:
        stats["mappings_seen"] += 1
        paper = mapping.paper
        if skip_if_paper_has_venue and (paper.journal_id or paper.conference_id):
            stats["skipped_has_venue"] += 1
            continue

        venue_name = _truncate(mapping.venue_from_api, 255)
        if not venue_name:
            stats["skipped_no_venue_name"] += 1
            continue

        row = _mapping_row_for_venue_create(mapping)
        kind = str(row["db_venue_kind"])
        cache_key = (kind, venue_name.casefold())

        if cache_key in venue_cache:
            venue_id = venue_cache[cache_key]
        elif dry_run:
            venue_id = uuid.uuid4()
            venue_cache[cache_key] = venue_id
            stats["venues_created"] += 1
        else:
            try:
                kind, venue_id, created = create_venue_from_mapping_row(row)
                venue_cache[cache_key] = venue_id
                if created:
                    stats["venues_created"] += 1
                else:
                    stats["venues_reused"] += 1
            except Exception as exc:
                logger.warning(
                    "materialize venue failed paper_id=%s venue=%r: %s",
                    mapping.paper_id,
                    venue_name,
                    exc,
                )
                stats["errors"] += 1
                continue

        mapping.status = PaperVenueMapping.Status.OK_AUTO
        mapping.db_venue_kind = kind
        mapping.db_venue_id = venue_id
        mapping.db_venue_name = venue_name
        note = (mapping.notes or "").strip()
        mapping.notes = f"{note};materialized_no_match_db".strip(";")

        _apply_fks_to_paper(paper, kind, venue_id)
        if update_doi:
            _upgrade_paper_doi_if_publisher_found(
                paper,
                {"resolved_doi": mapping.resolved_doi},
            )

        stats["papers_linked"] += 1
        mapping_buffer.append(mapping)
        paper_buffer.append(paper)

    return mapping_buffer, paper_buffer


def _flush_materialize_buffers(
    mapping_buffer: list[PaperVenueMapping],
    paper_buffer: list[Paper],
) -> None:
    if not mapping_buffer and not paper_buffer:
        return
    with transaction.atomic():
        if mapping_buffer:
            PaperVenueMapping.objects.bulk_update(
                mapping_buffer,
                [
                    "status",
                    "db_venue_kind",
                    "db_venue_id",
                    "db_venue_name",
                    "notes",
                    "processed_at",
                ],
            )
        if paper_buffer:
            Paper.objects.bulk_update(
                paper_buffer,
                ["journal_id", "conference_id", "doi", "updated_at"],
            )


def materialize_no_match_db_mappings(
    *,
    dry_run: bool = False,
    update_doi: bool = False,
    bulk_size: int = 500,
    skip_if_paper_has_venue: bool = False,
    limit: int = 0,
    log_every: int = 1000,
) -> dict[str, int]:
    """
    For PaperVenueMapping rows with status=no_match_db:
      1) get_or_create Journal/Conference (unranked / empty quartile)
      2) update mapping db_venue_* + status=ok_auto
      3) link Paper journal/conference FK

    Uses paper_id cursor pagination (not queryset.iterator) so a dropped
    PostgreSQL connection can be recovered by reconnecting on the next batch.
    """
    base_qs = (
        PaperVenueMapping.objects.filter(status=PaperVenueMapping.Status.NO_MATCH_DB)
        .exclude(venue_from_api="")
        .order_by("paper_id")
    )
    if limit > 0:
        paper_ids = list(base_qs.values_list("paper_id", flat=True)[:limit])
    else:
        paper_ids = list(base_qs.values_list("paper_id", flat=True))

    venue_cache: dict[tuple[str, str], uuid.UUID] = {}
    stats = {
        "mappings_seen": 0,
        "venues_created": 0,
        "venues_reused": 0,
        "papers_linked": 0,
        "skipped_no_venue_name": 0,
        "skipped_has_venue": 0,
        "errors": 0,
        "batches": 0,
    }

    for offset in range(0, len(paper_ids), bulk_size):
        batch_ids = paper_ids[offset : offset + bulk_size]
        if not batch_ids:
            break

        close_old_connections()
        stats["batches"] += 1

        try:
            mappings = list(
                PaperVenueMapping.objects.filter(paper_id__in=batch_ids)
                .select_related("paper")
                .order_by("paper_id")
            )
            mapping_buffer, paper_buffer = _process_materialize_batch(
                mappings,
                venue_cache=venue_cache,
                dry_run=dry_run,
                update_doi=update_doi,
                skip_if_paper_has_venue=skip_if_paper_has_venue,
                stats=stats,
            )
            if not dry_run:
                _flush_materialize_buffers(mapping_buffer, paper_buffer)
        except Exception as exc:
            if _is_db_connection_error(exc):
                close_old_connections()
                logger.warning(
                    "materialize batch failed (connection); retrying once: %s",
                    exc,
                )
                try:
                    mappings = list(
                        PaperVenueMapping.objects.filter(paper_id__in=batch_ids)
                        .select_related("paper")
                        .order_by("paper_id")
                    )
                    mapping_buffer, paper_buffer = _process_materialize_batch(
                        mappings,
                        venue_cache=venue_cache,
                        dry_run=dry_run,
                        update_doi=update_doi,
                        skip_if_paper_has_venue=skip_if_paper_has_venue,
                        stats=stats,
                    )
                    if not dry_run:
                        _flush_materialize_buffers(mapping_buffer, paper_buffer)
                except Exception as retry_exc:
                    logger.error(
                        "materialize batch retry failed offset=%s: %s",
                        offset,
                        retry_exc,
                    )
                    stats["errors"] += len(batch_ids)
                    continue
            else:
                logger.error("materialize batch failed offset=%s: %s", offset, exc)
                stats["errors"] += len(batch_ids)
                continue

        if log_every > 0 and stats["mappings_seen"] % log_every < bulk_size:
            logger.info(
                "materialize progress: seen=%s linked=%s venues_created=%s errors=%s",
                stats["mappings_seen"],
                stats["papers_linked"],
                stats["venues_created"],
                stats["errors"],
            )

    return stats


def _resolve_no_match_db(row: dict[str, Any]) -> None:
    preferred = venue_kind_from_classification(str(row.get("classification") or ""))
    if preferred:
        row["db_venue_kind"] = preferred
    kind, venue_id, _created = create_venue_from_mapping_row(row)
    row["db_venue_kind"] = kind
    row["db_venue_id"] = str(venue_id)
    row["db_venue_name"] = _truncate(row.get("venue_from_api"), 255)
    note = (row.get("notes") or "").strip()
    row["notes"] = f"{note};auto_created_venue".strip(";")


def _upgrade_paper_doi_if_publisher_found(paper: Paper, row: dict[str, Any]) -> bool:
    """
    Replace arXiv DOI (or empty) with publisher DOI from mapping APIs when available.
    """
    resolved = normalize_doi(str(row.get("resolved_doi") or ""))
    if not resolved or is_arxiv_doi(resolved):
        return False
    current = normalize_doi(paper.doi or "")
    if resolved == current:
        return False
    paper.doi = resolved[:200]
    return True


def _apply_fks_to_paper(paper: Paper, kind: str, venue_id: uuid.UUID) -> None:
    if kind == "journal":
        paper.journal_id = venue_id
        paper.conference_id = None
    elif kind == "conference":
        paper.conference_id = venue_id
        paper.journal_id = None


@transaction.atomic
def apply_venue_mapping_for_paper(
    paper: Paper,
    *,
    update_doi: bool = True,
    skip_if_has_venue: bool = False,
) -> dict[str, Any]:
    """
    Run external venue lookup, persist PaperVenueMapping, and update paper FKs.

    Returns a small summary dict for API responses / logs.
    """
    if skip_if_has_venue and (paper.journal_id or paper.conference_id):
        return {
            "paper_id": str(paper.id),
            "status": "skipped",
            "reason": "paper_already_has_venue",
        }

    journals, conferences = get_venue_id_lists()
    row = map_paper_record(
        paper_id=str(paper.id),
        title=paper.title or "",
        doi=paper.doi,
        journals=journals,
        conferences=conferences,
        min_title_match=MIN_TITLE_MATCH,
        min_db_match=MIN_DB_VENUE_MATCH,
        min_ok_auto_fuzzy=VENUE_OK_AUTO_FUZZY,
    )

    status = row.get("status") or PaperVenueMapping.Status.NO_VENUE
    applied = False
    apply_error = ""

    try:
        if status == PaperVenueMapping.Status.REVIEW:
            _assign_review_to_others(row)
            applied = True
        elif status == PaperVenueMapping.Status.NO_MATCH_DB:
            _resolve_no_match_db(row)
            applied = True
        elif status == PaperVenueMapping.Status.OK_AUTO:
            applied = True
        # no_venue: do not set FKs
    except Exception as exc:
        apply_error = str(exc)
        logger.warning(
            "venue apply failed for paper_id=%s status=%s: %s",
            paper.id,
            status,
            exc,
        )

    update_fields: list[str] = []

    if applied:
        kind = str(row.get("db_venue_kind") or "")
        venue_id = _parse_uuid(row.get("db_venue_id"))
        if kind and venue_id:
            _apply_fks_to_paper(paper, kind, venue_id)
            update_fields.extend(["journal_id", "conference_id"])

    if update_doi and _upgrade_paper_doi_if_publisher_found(paper, row):
        update_fields.append("doi")

    if update_fields:
        update_fields.append("updated_at")
        paper.save(update_fields=update_fields)

    PaperVenueMapping.objects.update_or_create(
        paper=paper,
        defaults=_row_to_mapping_defaults(str(paper.id), row),
    )

    return {
        "paper_id": str(paper.id),
        "status": status,
        "applied": applied and not apply_error,
        "doi": paper.doi or "",
        "resolved_doi": row.get("resolved_doi") or "",
        "venue_from_api": row.get("venue_from_api") or "",
        "db_venue_kind": row.get("db_venue_kind") or "",
        "db_venue_name": row.get("db_venue_name") or "",
        "error": apply_error,
    }

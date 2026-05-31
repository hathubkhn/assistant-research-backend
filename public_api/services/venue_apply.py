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

from django.db import transaction

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
OTHERS_RANK = "not rank"


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


def create_venue_from_mapping_row(row: dict[str, Any]) -> tuple[str, uuid.UUID]:
    """
    Create Journal or Conference when API venue is not in DB.
    Only fills fields we can infer; optional metadata stays empty.
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
        journal, _ = Journal.objects.get_or_create(
            name=venue_name,
            defaults={
                "abbreviation": "",
                "quartile": "",
                "publisher": publisher,
                "url": venue_url,
            },
        )
        return "journal", journal.id

    conference, _ = Conference.objects.get_or_create(
        name=venue_name,
        defaults={
            "abbreviation": "",
            "rank": "",
            "location": "",
            "url": venue_url,
        },
    )
    return "conference", conference.id


def _assign_review_to_others(row: dict[str, Any]) -> None:
    others = get_or_create_others_conference()
    row["db_venue_kind"] = "conference"
    row["db_venue_id"] = str(others.id)
    row["db_venue_name"] = others.name
    note = (row.get("notes") or "").strip()
    row["notes"] = f"{note};auto_assigned_others".strip(";")


def _resolve_no_match_db(row: dict[str, Any]) -> None:
    preferred = venue_kind_from_classification(str(row.get("classification") or ""))
    if preferred:
        row["db_venue_kind"] = preferred
    kind, venue_id = create_venue_from_mapping_row(row)
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

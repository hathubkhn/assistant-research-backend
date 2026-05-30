"""Fire-and-forget client to mirror Paper rows into the research_assistant Qdrant index.

Failures are logged but never raise — the upload/crawl flow must not block on
embedding. Papers left with embedded_at IS NULL get picked up by the
`backfill_embeddings` management command.
"""
import logging
import os
from typing import Optional

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

# All papers are embedded under a single global tenant. Recommendation queries
# do not filter by user_id; ranking comes purely from semantic similarity.
GLOBAL_USER_ID = "global"

DEFAULT_TIMEOUT = 15  # seconds — covers OpenAI cold-start; upload still feels snappy


def _assistant_url() -> str:
    return os.environ.get("RESEARCH_ASSISTANT_URL", "http://research-assistant:8001").rstrip("/")


def _paper_payload(paper) -> dict:
    keywords = paper.keywords or []
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]

    # Indexed in Qdrant for fast filter: publication_year, doi, conference_name,
    # journal_name, file_format, citations_count. Other fields just stored for display.
    metadata = {
        "doi": getattr(paper, "doi", None),
        "url": getattr(paper, "url", None),
        "pdf_url": getattr(paper, "pdf_url", None),
        "github_url": getattr(paper, "github_url", None),
        "file_format": getattr(paper, "file_format", None),
        "citations_count": getattr(paper, "citations_count", None),
        "download_count": getattr(paper, "download_count", None),
        "views_count": getattr(paper, "views_count", None),
    }

    pub_date = getattr(paper, "publication_date", None)
    if pub_date:
        metadata["publication_date"] = pub_date.isoformat()
        metadata["publication_year"] = pub_date.year

    # FK fields exist only on the backend Paper model, not the crawler's unmanaged stub.
    conference = getattr(paper, "conference", None)
    if conference is not None:
        metadata["conference_name"] = conference.name
        metadata["conference_id"] = str(conference.id)
    journal = getattr(paper, "journal", None)
    if journal is not None:
        metadata["journal_name"] = journal.name
        metadata["journal_id"] = str(journal.id)

    return {
        "paper_id": str(paper.id),
        "title": paper.title or "",
        "abstract": paper.abstract or "",
        "keywords": keywords,
        "user_id": GLOBAL_USER_ID,
        "metadata": metadata,
    }


def embed_paper(paper, *, timeout: int = DEFAULT_TIMEOUT) -> bool:
    """POST the paper to research_assistant /papers. Returns True on success.

    On success, sets paper.embedded_at = now() and persists that single field.
    Never raises.
    """
    try:
        resp = requests.post(
            f"{_assistant_url()}/papers",
            json=_paper_payload(paper),
            timeout=timeout,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("embed_paper failed for paper_id=%s: %s", paper.id, exc)
        return False

    try:
        paper.embedded_at = timezone.now()
        paper.save(update_fields=["embedded_at", "updated_at"])
    except Exception as exc:
        logger.warning("embed_paper succeeded but couldn't persist embedded_at for %s: %s", paper.id, exc)
    return True


def delete_embedding(paper_id: str, *, timeout: int = DEFAULT_TIMEOUT) -> bool:
    """Best-effort DELETE for a paper's embedding."""
    try:
        resp = requests.delete(f"{_assistant_url()}/papers/{paper_id}", timeout=timeout)
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("delete_embedding failed for paper_id=%s: %s", paper_id, exc)
        return False

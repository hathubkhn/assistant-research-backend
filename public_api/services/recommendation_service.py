"""Recommended papers: Qdrant semantic search with keyword-match fallback."""
import json
import logging
import os
import uuid
from datetime import timedelta
from typing import List, Set

import requests
from django.utils import timezone

from ..models import InterestingPaper, Paper, Profile

logger = logging.getLogger(__name__)

RECOMMENDATION_LIMIT = 8
RECOMMENDATION_DAYS = 30
SEMANTIC_SEARCH_LIMIT = 40
SEARCH_TIMEOUT = 20


def _assistant_url() -> str:
    return os.environ.get(
        "RESEARCH_ASSISTANT_URL", "http://research-assistant:8001"
    ).rstrip("/")


def profile_keyword_set(profile: Profile) -> Set[str]:
    keywords: Set[str] = set()
    if profile.research_interests:
        keywords.update(
            k.strip().lower()
            for k in profile.research_interests.split(",")
            if k and k.strip()
        )
    if profile.additional_keywords:
        keywords.update(
            k.strip().lower()
            for k in profile.additional_keywords.split(",")
            if k and k.strip()
        )
    return keywords


def build_semantic_query(profile: Profile) -> str:
    """Natural-language query from profile fields for embedding search."""
    parts = []
    if profile.research_interests and profile.research_interests.strip():
        parts.append(profile.research_interests.strip())
    if profile.additional_keywords and profile.additional_keywords.strip():
        parts.append(profile.additional_keywords.strip())
    return ". ".join(parts)


def _parse_paper_keywords(raw) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [pk for pk in raw if isinstance(pk, str)]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [pk for pk in parsed if isinstance(pk, str)]
        except json.JSONDecodeError:
            pass
        return [k.strip() for k in raw.split(",") if k and k.strip()]
    return []


def keyword_recommendation_ids(
    user,
    user_keywords_lower: Set[str],
    *,
    limit: int = RECOMMENDATION_LIMIT,
) -> List[uuid.UUID]:
    """Legacy recommendation: intersection of profile and paper keywords."""
    if not user_keywords_lower:
        return []

    thirty_days_ago = timezone.now() - timedelta(days=RECOMMENDATION_DAYS)
    excluded_paper_ids = InterestingPaper.objects.filter(user=user).values_list(
        "paper_id", flat=True
    )

    matched_ids: List[uuid.UUID] = []
    candidates = (
        Paper.objects.filter(created_at__gte=thirty_days_ago)
        .exclude(id__in=excluded_paper_ids)
        .only("id", "keywords")
        .iterator(chunk_size=200)
    )

    for paper in candidates:
        paper_keywords_lower = {
            pk.lower() for pk in _parse_paper_keywords(paper.keywords)
        }
        if user_keywords_lower & paper_keywords_lower:
            matched_ids.append(paper.id)
            if len(matched_ids) >= limit:
                break

    return matched_ids


def semantic_search_paper_ids(query: str, *, limit: int = SEMANTIC_SEARCH_LIMIT) -> List[uuid.UUID]:
    """Call research_assistant /search; return paper UUIDs in similarity order."""
    if not query.strip():
        return []

    try:
        response = requests.post(
            f"{_assistant_url()}/search",
            json={"query": query, "limit": limit},
            timeout=SEARCH_TIMEOUT,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning("semantic_search failed: %s", exc)
        return []

    ordered_ids: List[uuid.UUID] = []
    seen: Set[uuid.UUID] = set()

    for item in response.json().get("papers") or []:
        raw_id = item.get("paper_id")
        if raw_id is None:
            continue
        try:
            paper_uuid = uuid.UUID(str(raw_id))
        except (ValueError, TypeError):
            logger.debug("skip invalid paper_id from search: %r", raw_id)
            continue
        if paper_uuid in seen:
            continue
        seen.add(paper_uuid)
        ordered_ids.append(paper_uuid)

    return ordered_ids


def _filter_recommendation_candidates(
    user,
    candidate_ids: List[uuid.UUID],
    *,
    limit: int = RECOMMENDATION_LIMIT,
) -> List[uuid.UUID]:
    """Keep ids that exist, are recent, and are not already starred."""
    if not candidate_ids:
        return []

    thirty_days_ago = timezone.now() - timedelta(days=RECOMMENDATION_DAYS)
    excluded = set(
        InterestingPaper.objects.filter(user=user).values_list("paper_id", flat=True)
    )

    allowed = set(
        Paper.objects.filter(
            id__in=candidate_ids,
            created_at__gte=thirty_days_ago,
        ).values_list("id", flat=True)
    )

    filtered: List[uuid.UUID] = []
    for pid in candidate_ids:
        if pid not in allowed or pid in excluded:
            continue
        filtered.append(pid)
        if len(filtered) >= limit:
            break
    return filtered


def recommend_paper_ids(user, profile: Profile) -> List[uuid.UUID]:
    """
    Prefer semantic (Qdrant) matches from profile text; fall back or top up with
    keyword intersection when semantic is empty or unavailable.
    """
    keywords_lower = profile_keyword_set(profile)
    semantic_query = build_semantic_query(profile)

    if not semantic_query and not keywords_lower:
        return []

    matched_ids: List[uuid.UUID] = []

    if semantic_query:
        semantic_candidates = semantic_search_paper_ids(semantic_query)
        matched_ids = _filter_recommendation_candidates(
            user, semantic_candidates, limit=RECOMMENDATION_LIMIT
        )
        if matched_ids:
            logger.info(
                "recommendations semantic ok user=%s count=%s",
                user.id,
                len(matched_ids),
            )

    semantic_count = len(matched_ids)

    if len(matched_ids) < RECOMMENDATION_LIMIT and keywords_lower:
        keyword_ids = keyword_recommendation_ids(user, keywords_lower)
        seen = set(matched_ids)
        for kid in keyword_ids:
            if kid in seen:
                continue
            matched_ids.append(kid)
            seen.add(kid)
            if len(matched_ids) >= RECOMMENDATION_LIMIT:
                break

    if matched_ids:
        mode = "semantic"
        if semantic_count == 0:
            mode = "keyword"
        elif len(matched_ids) > semantic_count:
            mode = "semantic+keyword"
        logger.info(
            "recommendations %s user=%s count=%s",
            mode,
            user.id,
            len(matched_ids),
        )

    return matched_ids[:RECOMMENDATION_LIMIT]


def load_recommended_papers(matched_ids: List[uuid.UUID]) -> List[Paper]:
    if not matched_ids:
        return []

    papers_by_id = {
        p.id: p
        for p in Paper.objects.filter(id__in=matched_ids)
        .select_related("journal", "conference")
        .prefetch_related("tasks")
    }
    return [papers_by_id[pid] for pid in matched_ids if pid in papers_by_id]

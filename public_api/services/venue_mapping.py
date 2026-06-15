"""
Resolve paper DOI/title to published venue via Crossref, OpenAlex, Semantic Scholar,
then fuzzy-match venue name to Journal / Conference rows in the DB.
"""
from __future__ import annotations

import copy
import hashlib
import os
import re
import time
from typing import Any

import requests
from rapidfuzz import fuzz

HEADERS = {
    "User-Agent": "assistant-research-venue-mapper/0.1 (mailto:your_email@example.com)"
}

ARXIV_DOI_PREFIX = "10.48550/arxiv"
MIN_TITLE_MATCH = 85
MIN_DB_VENUE_MATCH = 82
MIN_OK_AUTO_FUZZY = int(os.environ.get("VENUE_OK_AUTO_FUZZY", "92"))


def normalize_title(title: str) -> str:
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r"[^a-z0-9\s]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def normalize_doi(doi: str | None) -> str:
    if not doi:
        return ""
    doi = doi.strip()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return doi.lower()


def is_arxiv_doi(doi: str) -> bool:
    return normalize_doi(doi).startswith(ARXIV_DOI_PREFIX)


def extract_crossref_year(msg: dict) -> int | None:
    for key in ("published-print", "published-online", "published", "issued"):
        parts = msg.get(key, {}).get("date-parts")
        if parts and parts[0]:
            return parts[0][0]
    return None


def get_crossref_by_doi(doi: str) -> dict | None:
    doi = normalize_doi(doi)
    url = f"https://api.crossref.org/works/{doi}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None
        msg = r.json().get("message", {})
        return {
            "source": "Crossref DOI",
            "doi": msg.get("DOI"),
            "title": (msg.get("title") or [""])[0],
            "type": msg.get("type"),
            "venue": (msg.get("container-title") or [""])[0],
            "publisher": msg.get("publisher"),
            "year": extract_crossref_year(msg),
            "issn": "; ".join(msg.get("ISSN", [])),
            "isbn": "; ".join(msg.get("ISBN", [])),
            "url": msg.get("URL"),
            "raw": msg,
        }
    except Exception:
        return None


def search_crossref_by_title(title: str, rows: int = 5) -> list[dict]:
    url = "https://api.crossref.org/works"
    params = {
        "query.title": title,
        "rows": rows,
        "select": "DOI,title,type,container-title,publisher,issued,ISBN,ISSN,URL",
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return []
        items = r.json().get("message", {}).get("items", [])
        results = []
        for item in items:
            candidate_title = (item.get("title") or [""])[0]
            score = fuzz.token_sort_ratio(
                normalize_title(title), normalize_title(candidate_title)
            )
            results.append({
                "source": "Crossref title search",
                "doi": item.get("DOI"),
                "title": candidate_title,
                "type": item.get("type"),
                "venue": (item.get("container-title") or [""])[0],
                "publisher": item.get("publisher"),
                "year": extract_crossref_year(item),
                "issn": "; ".join(item.get("ISSN", [])),
                "isbn": "; ".join(item.get("ISBN", [])),
                "url": item.get("URL"),
                "match_score": score,
                "raw": item,
            })
        return sorted(results, key=lambda x: x["match_score"], reverse=True)
    except Exception:
        return []


def get_openalex_by_doi(doi: str) -> dict | None:
    doi = normalize_doi(doi)
    url = f"https://api.openalex.org/works/doi:{doi}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None
        w = r.json()
        source = (w.get("primary_location", {}).get("source", {})) or {}
        return {
            "source": "OpenAlex DOI",
            "doi": w.get("doi", "").replace("https://doi.org/", "") if w.get("doi") else None,
            "title": w.get("title"),
            "type": w.get("type"),
            "venue": source.get("display_name"),
            "venue_type": source.get("type"),
            "publisher": source.get("host_organization_name"),
            "year": w.get("publication_year"),
            "issn": "; ".join(source.get("issn") or []),
            "url": w.get("id"),
            "raw": w,
        }
    except Exception:
        return None


def search_openalex_by_title(title: str, rows: int = 5) -> list[dict]:
    url = "https://api.openalex.org/works"
    params = {"search": title, "per-page": rows}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return []
        results = []
        for w in r.json().get("results", []):
            candidate_title = w.get("title") or ""
            score = fuzz.token_sort_ratio(
                normalize_title(title), normalize_title(candidate_title)
            )
            source = (w.get("primary_location", {}).get("source", {})) or {}
            results.append({
                "source": "OpenAlex title search",
                "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
                "title": candidate_title,
                "type": w.get("type"),
                "venue": source.get("display_name"),
                "venue_type": source.get("type"),
                "publisher": source.get("host_organization_name"),
                "year": w.get("publication_year"),
                "issn": "; ".join(source.get("issn") or []),
                "url": w.get("id"),
                "match_score": score,
                "raw": w,
            })
        return sorted(results, key=lambda x: x["match_score"], reverse=True)
    except Exception:
        return []


def search_semantic_scholar_by_title(title: str, rows: int = 5) -> list[dict]:
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": title,
        "limit": rows,
        "fields": "title,year,venue,publicationVenue,externalIds,url,authors",
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return []
        results = []
        for p in r.json().get("data", []):
            candidate_title = p.get("title") or ""
            score = fuzz.token_sort_ratio(
                normalize_title(title), normalize_title(candidate_title)
            )
            pub_venue = p.get("publicationVenue") or {}
            external_ids = p.get("externalIds") or {}
            results.append({
                "source": "Semantic Scholar title search",
                "doi": external_ids.get("DOI"),
                "title": candidate_title,
                "type": pub_venue.get("type"),
                "venue": p.get("venue") or pub_venue.get("name"),
                "publisher": None,
                "year": p.get("year"),
                "issn": None,
                "url": p.get("url"),
                "match_score": score,
                "raw": p,
            })
        return sorted(results, key=lambda x: x["match_score"], reverse=True)
    except Exception:
        return []


def classify_publication(record: dict) -> str:
    typ = (record.get("type") or "").lower()
    venue_type = (record.get("venue_type") or "").lower()
    venue = (record.get("venue") or "").lower()
    doi = normalize_doi(record.get("doi"))

    if doi.startswith(ARXIV_DOI_PREFIX):
        return "arXiv preprint"

    if "journal" in typ or "journal" in venue_type:
        return "Journal article"

    if "proceedings" in typ or "conference" in typ:
        return "Conference paper"

    if "conference" in venue_type:
        return "Conference paper"

    if "proceedings" in venue:
        return "Conference/proceedings item"

    if typ in ("book-chapter", "book"):
        return "Book chapter / proceedings-like item"

    if typ:
        return typ

    return "Unknown"


def _rank_candidate(c: dict, query_title: str | None) -> float:
    cls = c.get("classification", "")
    score = c.get("match_score") or 0

    published_bonus = 0
    if cls in ("Conference paper", "Journal article", "Conference/proceedings item"):
        published_bonus = 30
    elif cls == "arXiv preprint":
        published_bonus = -20

    has_venue_bonus = 10 if c.get("venue") else 0
    has_doi_bonus = 5 if c.get("doi") and not is_arxiv_doi(c.get("doi")) else 0

    return score + published_bonus + has_venue_bonus + has_doi_bonus


def _stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_lookup_key(doi: str | None, title: str | None) -> tuple[str, str, str] | None:
    """Return (lookup_key, lookup_type, lookup_value) for cache grouping."""
    normalized_doi = normalize_doi(doi)
    if normalized_doi:
        # DB column lookup_key is max 128 chars; hash very long DOIs.
        key_body = (
            normalized_doi
            if len(normalized_doi) <= 120
            else _stable_hash(normalized_doi)
        )
        return f"doi:{key_body}", "doi", normalized_doi[:500]
    normalized = normalize_title(title or "")
    if normalized:
        return f"title:{_stable_hash(normalized)}", "title", (title or "")[:500]
    return None


def _strip_raw_for_cache(candidates: list[dict]) -> list[dict]:
    cleaned = []
    for c in candidates:
        item = {k: v for k, v in c.items() if k != "raw"}
        cleaned.append(item)
    return cleaned


def rescore_candidates_for_title(candidates: list[dict], title: str | None) -> list[dict]:
    """Recompute match_score per paper title from shared cached candidates."""
    if not title:
        return copy.deepcopy(candidates)
    out = []
    for c in candidates:
        item = copy.deepcopy(c)
        if item.get("title"):
            item["match_score"] = fuzz.token_sort_ratio(
                normalize_title(title), normalize_title(item["title"])
            )
        item["classification"] = classify_publication(item)
        out.append(item)
    return sorted(out, key=lambda x: _rank_candidate(x, title), reverse=True)


def collect_candidates(
    doi: str | None = None,
    title: str | None = None,
    *,
    search_rows: int = 5,
    throttle_sec: float = 0.2,
    skip_semantic_scholar: bool = False,
) -> list[dict]:
    """Query external APIs and return deduplicated, ranked candidates."""
    candidates: list[dict] = []
    doi = normalize_doi(doi) or None
    title = (title or "").strip() or None

    if doi:
        cr = get_crossref_by_doi(doi)
        if cr:
            candidates.append(cr)
        oa = get_openalex_by_doi(doi)
        if oa:
            candidates.append(oa)

        if is_arxiv_doi(doi) and not title:
            for c in candidates:
                if c.get("title"):
                    title = c["title"]
                    break

    if title:
        candidates.extend(search_crossref_by_title(title, rows=search_rows))
        time.sleep(throttle_sec)
        candidates.extend(search_openalex_by_title(title, rows=search_rows))
        time.sleep(throttle_sec)
        if not skip_semantic_scholar:
            candidates.extend(search_semantic_scholar_by_title(title, rows=search_rows))

    seen: set[tuple[str, str, str]] = set()
    cleaned: list[dict] = []

    for c in candidates:
        key = (
            normalize_title(c.get("title", "")),
            normalize_doi(c.get("doi")),
            (c.get("venue") or "").lower(),
        )
        if key in seen:
            continue
        seen.add(key)

        c["classification"] = classify_publication(c)
        if "match_score" not in c:
            if title and c.get("title"):
                c["match_score"] = fuzz.token_sort_ratio(
                    normalize_title(title), normalize_title(c["title"])
                )
            else:
                c["match_score"] = 100
        cleaned.append(c)

    return sorted(cleaned, key=lambda c: _rank_candidate(c, title), reverse=True)


def get_or_fetch_cached_candidates(
    doi: str | None,
    title: str | None,
    *,
    search_rows: int = 5,
    throttle_sec: float = 0.2,
    skip_semantic_scholar: bool = False,
) -> tuple[list[dict], str | None]:
    """
    Return (candidates, lookup_key). Uses VenueLookupCache when Django ORM is available.
    """
    key_info = build_lookup_key(doi, title)
    if not key_info:
        return [], None

    lookup_key, lookup_type, lookup_value = key_info

    try:
        from public_api.models import VenueLookupCache
    except Exception:
        return collect_candidates(
            doi=doi,
            title=title,
            search_rows=search_rows,
            throttle_sec=throttle_sec,
            skip_semantic_scholar=skip_semantic_scholar,
        ), lookup_key

    cached = VenueLookupCache.objects.filter(lookup_key=lookup_key).first()
    if cached and cached.candidates:
        return cached.candidates, lookup_key

    candidates = collect_candidates(
        doi=doi,
        title=title,
        search_rows=search_rows,
        throttle_sec=throttle_sec,
        skip_semantic_scholar=skip_semantic_scholar,
    )
    VenueLookupCache.objects.update_or_create(
        lookup_key=lookup_key,
        defaults={
            "lookup_type": lookup_type,
            "lookup_value": lookup_value,
            "candidates": _strip_raw_for_cache(candidates),
        },
    )
    return candidates, lookup_key


def pick_resolved_publisher_doi(
    candidates: list[dict],
    *,
    input_doi: str = "",
    title: str | None = None,
    min_title_match: int = MIN_TITLE_MATCH,
) -> str:
    """
    When input is an arXiv DOI, prefer a publisher DOI from title/DOI search results.
    Falls back to input_doi if no published match passes the title score gate.
    """
    input_norm = normalize_doi(input_doi)
    ranked = sorted(
        candidates,
        key=lambda c: _rank_candidate(c, title),
        reverse=True,
    )
    for c in ranked:
        if c.get("match_score", 0) < min_title_match:
            continue
        candidate_doi = normalize_doi(c.get("doi"))
        if candidate_doi and not is_arxiv_doi(candidate_doi):
            return candidate_doi
    return input_norm


def pick_best_candidate(
    candidates: list[dict],
    *,
    min_title_match: int = MIN_TITLE_MATCH,
    require_venue: bool = True,
) -> dict | None:
    """Return top candidate if it passes quality gates."""
    for c in candidates:
        if c.get("match_score", 0) < min_title_match:
            continue
        if require_venue and not (c.get("venue") or "").strip():
            continue
        if c.get("classification") == "arXiv preprint" and is_arxiv_doi(c.get("doi")):
            continue
        return c
    return None


def venue_kind_from_classification(classification: str) -> str | None:
    if classification == "Journal article":
        return "journal"
    if classification in ("Conference paper", "Conference/proceedings item"):
        return "conference"
    return None


def build_no_match_db_payload(candidate: dict, preferred_kind: str | None) -> str:
    """
    Build compact text payload to help manual/automated venue creation
    when API venue is found but not matched in DB.
    """
    return " | ".join(
        [
            f"suggested_kind={preferred_kind or ''}",
            f"venue={candidate.get('venue') or ''}",
            f"classification={candidate.get('classification') or ''}",
            f"publisher={candidate.get('publisher') or ''}",
            f"issn={candidate.get('issn') or ''}",
            f"source={candidate.get('source') or ''}",
            f"year={candidate.get('year') or ''}",
            f"resolved_doi={normalize_doi(candidate.get('doi')) or ''}",
        ]
    )


def parse_no_match_db_payload(payload: str) -> dict[str, str]:
    """Parse payload produced by build_no_match_db_payload."""
    result: dict[str, str] = {}
    if not payload:
        return result
    for part in payload.split(" | "):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def fuzzy_match_venue_name(
    venue_name: str,
    journals: list[tuple[str, str]],
    conferences: list[tuple[str, str]],
    preferred_kind: str | None = None,
    min_score: int = MIN_DB_VENUE_MATCH,
) -> dict[str, Any] | None:
    """
    Match API venue string to DB Journal/Conference by name.
    journals/conferences: list of (uuid_str, name).
    """
    if not venue_name or not venue_name.strip():
        return None

    norm_query = normalize_title(venue_name)
    best: dict[str, Any] | None = None

    def scan(kind: str, items: list[tuple[str, str]]) -> None:
        nonlocal best
        for pk, name in items:
            score = fuzz.token_sort_ratio(norm_query, normalize_title(name))
            if score < min_score:
                continue
            if best is None or score > best["fuzzy_score"]:
                best = {
                    "venue_kind": kind,
                    "venue_id": pk,
                    "venue_name": name,
                    "fuzzy_score": score,
                }

    if preferred_kind in (None, "journal"):
        scan("journal", journals)
    if preferred_kind in (None, "conference"):
        scan("conference", conferences)

    return best


def map_paper_record(
    *,
    paper_id: str,
    title: str,
    doi: str | None,
    journals: list[tuple[str, str]],
    conferences: list[tuple[str, str]],
    min_title_match: int = MIN_TITLE_MATCH,
    min_db_match: int = MIN_DB_VENUE_MATCH,
    min_ok_auto_fuzzy: int = MIN_OK_AUTO_FUZZY,
    candidates: list[dict] | None = None,
    lookup_key: str | None = None,
    skip_semantic_scholar: bool = False,
) -> dict[str, Any]:
    """
    Full pipeline for one paper: external APIs → best candidate → DB venue match.
    Returns a flat dict suitable for CSV export / review.
    """
    input_doi = doi or ""
    if candidates is None:
        candidates, lookup_key = get_or_fetch_cached_candidates(
            doi=doi,
            title=title,
            skip_semantic_scholar=skip_semantic_scholar,
        )
    else:
        candidates = rescore_candidates_for_title(candidates, title)
        if lookup_key is None:
            key_info = build_lookup_key(doi, title)
            lookup_key = key_info[0] if key_info else None

    best = pick_best_candidate(candidates, min_title_match=min_title_match)
    top_candidate = best or (candidates[0] if candidates else None)

    row: dict[str, Any] = {
        "paper_id": paper_id,
        "lookup_key": lookup_key or "",
        "title": title,
        "input_doi": input_doi,
        "resolved_doi": "",
        "classification": "",
        "venue_from_api": "",
        "match_score": "",
        "api_source": "",
        "year": "",
        "db_venue_kind": "",
        "db_venue_id": "",
        "db_venue_name": "",
        "db_venue_fuzzy_score": "",
        "no_match_db_payload": "",
        "publisher": "",
        "venue_url": "",
        "status": "no_venue",
        "notes": "",
        "candidates_count": len(candidates),
    }

    if top_candidate:
        resolved_doi = pick_resolved_publisher_doi(
            candidates,
            input_doi=input_doi,
            title=title,
            min_title_match=min_title_match,
        )
        classification = top_candidate.get("classification", "")
        venue_name = (top_candidate.get("venue") or "").strip()
        row.update({
            "resolved_doi": resolved_doi,
            "classification": classification,
            "venue_from_api": venue_name,
            "match_score": top_candidate.get("match_score"),
            "api_source": top_candidate.get("source"),
            "year": top_candidate.get("year") or "",
            "publisher": (top_candidate.get("publisher") or "")[:255],
            "venue_url": (top_candidate.get("url") or "")[:200],
        })
    else:
        return row

    if not best:
        row["notes"] = "candidates_found_but_none_passed_filters"
        row["status"] = "review"
        return row

    if best.get("match_score", 0) < min_title_match:
        row["status"] = "review"
        row["notes"] = "low_title_match_score"
        return row

    if not venue_name:
        row["status"] = "no_venue"
        return row

    preferred = venue_kind_from_classification(classification)
    db_match = fuzzy_match_venue_name(
        venue_name,
        journals,
        conferences,
        preferred_kind=preferred,
        min_score=min_db_match,
    )

    if not db_match and preferred:
        db_match = fuzzy_match_venue_name(
            venue_name, journals, conferences, preferred_kind=None, min_score=min_db_match
        )

    if not db_match:
        row["status"] = "no_match_db"
        row["notes"] = f"venue_not_in_db:{venue_name}"
        row["no_match_db_payload"] = build_no_match_db_payload(best, preferred)
        return row

    row.update({
        "db_venue_kind": db_match["venue_kind"],
        "db_venue_id": db_match["venue_id"],
        "db_venue_name": db_match["venue_name"],
        "db_venue_fuzzy_score": db_match["fuzzy_score"],
    })

    if (
        db_match["fuzzy_score"] >= min_ok_auto_fuzzy
        and best.get("match_score", 0) >= min_title_match
    ):
        row["status"] = "ok_auto"
    else:
        row["status"] = "review"
        row["notes"] = "fuzzy_or_title_needs_human_check"

    return row

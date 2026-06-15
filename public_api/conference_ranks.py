"""Shared conference rank constants and helpers.

Ranked tiers (CORE): A*, A, B, C.
Everything else is treated as unranked for list filters and display.
"""
from django.db.models import Q

RANKED_VALUES = frozenset({"A*", "A", "B", "C"})

# Legacy / import values normalized to unranked (empty string in DB).
UNRANKED_ALIASES = frozenset(
    {
        "",
        "not rank",
        "not ranked",
        "not_rank",
        "unranked",
        "n/a",
        "na",
        "null",
        "none",
        "-",
    }
)

DISPLAY_UNRANKED = "Not ranked"


def normalize_conference_rank(rank: str | None) -> str:
    """Return canonical DB value: A*|A|B|C or empty string for unranked."""
    if rank is None:
        return ""
    cleaned = str(rank).strip()
    if cleaned in RANKED_VALUES:
        return cleaned
    if cleaned.casefold() in UNRANKED_ALIASES or cleaned.casefold() == DISPLAY_UNRANKED.casefold():
        return ""
    # Unknown non-tier label → treat as unranked rather than a fake tier.
    return ""


def is_unranked_rank(rank: str | None) -> bool:
    return normalize_conference_rank(rank) == ""


def display_conference_rank(rank: str | None) -> str:
    normalized = normalize_conference_rank(rank)
    return normalized if normalized else DISPLAY_UNRANKED


def unranked_rank_q() -> Q:
    """Django Q matching every unranked conference rank in the DB."""
    q = Q(rank__isnull=True) | Q(rank="")
    for alias in UNRANKED_ALIASES:
        if alias:
            q |= Q(rank__iexact=alias)
    q |= Q(rank__iexact=DISPLAY_UNRANKED)
    return q

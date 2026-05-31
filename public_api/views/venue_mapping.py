"""Internal endpoint for crawler / workers to trigger venue mapping."""
import os

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from public_api.models import Paper
from public_api.services.venue_apply import apply_venue_mapping_for_paper


def _internal_key_ok(request) -> bool:
    expected = getattr(settings, "INTERNAL_VENUE_MAP_KEY", None) or os.environ.get(
        "INTERNAL_VENUE_MAP_KEY", ""
    )
    if not expected:
        return bool(settings.DEBUG)
    return request.headers.get("X-Internal-Key", "") == expected


class MapPaperVenueView(APIView):
    """POST /api/papers/<paper_id>/map-venue/ — run auto venue pipeline."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, paper_id):
        if not _internal_key_ok(request):
            return Response(
                {"error": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        paper = get_object_or_404(Paper, id=paper_id)
        result = apply_venue_mapping_for_paper(
            paper,
            update_doi=True,
            skip_if_has_venue=False,
        )
        paper.refresh_from_db()
        return Response(
            {
                **result,
                "journal_id": str(paper.journal_id) if paper.journal_id else None,
                "conference_id": str(paper.conference_id) if paper.conference_id else None,
                "journal_name": paper.journal.name if paper.journal else None,
                "conference_name": paper.conference.name if paper.conference else None,
            },
            status=status.HTTP_200_OK,
        )

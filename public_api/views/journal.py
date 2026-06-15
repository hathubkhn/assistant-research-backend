from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Journal
from ..venue_papers import paginate_venue_papers


class JournalsList(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 20))

        search = request.query_params.get("search")
        quartile = request.query_params.get("quartile")
        tier = request.query_params.get("tier")
        impact_min = request.query_params.get("impactMin")
        impact_max = request.query_params.get("impactMax")

        journals = Journal.objects.annotate(
            quartile_order=Case(
                When(quartile="Q1", then=Value(0)),
                When(quartile="Q2", then=Value(1)),
                When(quartile="Q3", then=Value(2)),
                When(quartile="Q4", then=Value(3)),
                default=Value(99),
                output_field=IntegerField(),
            )
        ).order_by("quartile_order", "name")

        if search:
            journals = journals.filter(
                Q(name__icontains=search) | Q(abbreviation__icontains=search)
            )

        if quartile:
            journals = journals.filter(quartile=quartile)

        if tier == "top":
            journals = journals.filter(quartile="Q1")
        elif tier == "other":
            journals = journals.exclude(quartile="Q1")

        if impact_min is not None:
            journals = journals.filter(impact_factor__gte=float(impact_min))

        if impact_max is not None:
            journals = journals.filter(impact_factor__lte=float(impact_max))

        paginator = Paginator(journals, page_size)
        paginated_journals = paginator.page(page)

        result = []
        for journal in paginated_journals:
            papers_count = journal.papers.count()

            journal_data = {
                "id": journal.id,
                "name": journal.name,
                "abbreviation": journal.abbreviation,
                "impactFactor": journal.impact_factor,
                "quartile": journal.quartile,
                "publisher": journal.publisher,
                "url": journal.url,
                "papersCount": papers_count,
            }
            result.append(journal_data)

        response_data = {
            "results": result,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalItems": paginator.count,
                "totalPages": paginator.num_pages,
            },
        }
        return Response(response_data, status=status.HTTP_200_OK)


class JournalDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, journal_id):
        journal = get_object_or_404(Journal, id=journal_id)
        papers_count = journal.papers.count()

        journal_data = {
            "id": journal.id,
            "name": journal.name,
            "abbreviation": journal.abbreviation,
            "impactFactor": journal.impact_factor,
            "quartile": journal.quartile,
            "publisher": journal.publisher,
            "url": journal.url,
            "papersCount": papers_count,
            "created_at": journal.created_at,
        }
        return Response(journal_data, status=status.HTTP_200_OK)


class JournalPapersView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, journal_id):
        journal = get_object_or_404(Journal, id=journal_id)
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 20))
        data = paginate_venue_papers(journal.papers.all(), page, page_size)
        return Response(data, status=status.HTTP_200_OK)
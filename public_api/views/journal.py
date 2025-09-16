from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Journal


class JournalsList(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 20))

        search = request.query_params.get("search")
        quartile = request.query_params.get("quartile")
        impact_min = request.query_params.get("impactMin")
        impact_max = request.query_params.get("impactMax")

        journals = Journal.objects.all()

        if search:
            journals = journals.filter(
                Q(name__icontains=search) | Q(abbreviation__icontains=search)
            )

        if quartile:
            journals = journals.filter(quartile=quartile)

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
        papers = journal.papers.all()

        paper_items = papers.values_list("id", "title", "publication_date", "authors")
        paper_items = [{
            "id": paper[0],
            "title": paper[1],
            "publication_date": paper[2],
            "authors": paper[3],
        } for paper in paper_items]

        journal_data = {
            "id": journal.id,
            "name": journal.name,
            "abbreviation": journal.abbreviation,
            "impactFactor": journal.impact_factor,
            "quartile": journal.quartile,
            "publisher": journal.publisher,
            "url": journal.url,
            "papersCount": papers_count,
            "papers": paper_items,
            "created_at": journal.created_at,
        }
        return Response(journal_data, status=status.HTTP_200_OK)
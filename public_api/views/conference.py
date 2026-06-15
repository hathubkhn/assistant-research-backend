from rest_framework.views import APIView

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Case, IntegerField, Q, Value, When
from django.core.paginator import Paginator

from ..conference_ranks import unranked_rank_q
from ..models import Conference
from ..serializers import ConferenceListSerializer, ConferenceDetailSerializer
from ..venue_papers import paginate_venue_papers


class ConferencesList(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 20))

        search = request.query_params.get("search")
        rank = request.query_params.get("rank")
        tier = request.query_params.get("tier")
        conferences = Conference.objects.annotate(
            rank_order=Case(
                When(rank="A*", then=Value(0)),
                When(rank="A", then=Value(1)),
                When(rank="B", then=Value(2)),
                When(rank="C", then=Value(3)),
                default=Value(99),
                output_field=IntegerField(),
            )
        ).order_by("rank_order", "name")

        if search:
            conferences = conferences.filter(
                Q(name__icontains=search) | Q(abbreviation__icontains=search)
            )

        if rank:
            if rank.lower() in ("null", "not ranked", "unranked"):
                conferences = conferences.filter(unranked_rank_q())
            else:
                conferences = conferences.filter(rank=rank)

        if tier == "top":
            conferences = conferences.filter(rank__in=["A*", "A"])
        elif tier == "other":
            conferences = conferences.exclude(rank__in=["A*", "A"])

        paginator = Paginator(conferences, page_size)
        paginated_conferences = paginator.page(page)

        serializer = ConferenceListSerializer(paginated_conferences, many=True)
        result = serializer.data

        response_data = {
            "results": result,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalItems": paginator.count,
                "totalPages": paginator.num_pages,
            },
        }

        return Response(response_data)

class ConferenceDetail(APIView):
    permission_classes = [AllowAny]

    def get(self, request, conference_id):
        conference = get_object_or_404(Conference, id=conference_id)
        
        serializer = ConferenceDetailSerializer(conference)
        result = serializer.data
        return Response(result, status=status.HTTP_200_OK)


class ConferencePapersView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, conference_id):
        conference = get_object_or_404(Conference, id=conference_id)
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 20))
        data = paginate_venue_papers(conference.papers.all(), page, page_size)
        return Response(data, status=status.HTTP_200_OK)

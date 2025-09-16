from rest_framework.views import APIView

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator

from ..models import Conference
from ..serializers import ConferenceListSerializer, ConferenceDetailSerializer


class ConferencesList(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 20))

        search = request.query_params.get("search")
        rank = request.query_params.get("rank")
        conferences = Conference.objects.all()

        if search:
            conferences = conferences.filter(
                Q(name__icontains=search) | Q(abbreviation__icontains=search)
            )

        if rank:
            if rank.lower() == "null":
                conferences = conferences.filter(Q(rank__isnull=True) | Q(rank=""))
            else:
                conferences = conferences.filter(rank=rank)

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

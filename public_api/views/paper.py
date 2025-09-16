from datetime import datetime

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework import filters
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Paper, InterestingPaper, DownloadedPaper
from ..serializers import PaperDetailSerializer, PaperListSerializer, PaperSerializer


class PaperDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, paper_id):
        paper = get_object_or_404(Paper, id=paper_id)
        serializer = PaperDetailSerializer(paper)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaperBySlugView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        title_words = slug.split("-")
        queryset = Paper.objects.all()
        title_words = [word for word in title_words if len(word) > 2]
        for word in title_words:
            queryset = queryset.filter(title__icontains=word)
        paper = queryset.first()

        serializer = PaperDetailSerializer(paper)
        response_data = serializer.data
        return Response(response_data)


class PapersList(APIView):
    queryset = Paper.objects.all()
    serializer_class = PaperListSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ["-publication_date"]
    search_fields = ["title"]

    def filter_queryset(self):
        for backend in self.filter_backends:
            self.queryset = backend().filter_queryset(self.request, self.queryset, self)
        return self.queryset

    def get(self, request):
        queryset = self.filter_queryset()

        year = request.query_params.get("year")
        venue = request.query_params.get("venue")
        start_date = request.query_params.get("startDate")
        end_date = request.query_params.get("endDate")

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 20))
        task_ids = request.query_params.get("taskIds", [])

        filter_criteria = {}
        if year:
            filter_criteria["publication_date__year"] = int(year)
        if venue:
            filter_criteria["journal_or_conference"] = venue
        if task_ids:
            filter_criteria["task_id__in"] = task_ids

        if start_date:
            start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            filter_criteria["crawled_at__gte"] = start_date
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            filter_criteria["crawled_at__lte"] = end_date

        papers = queryset.filter(**filter_criteria).order_by(self.ordering_fields[0])

        paginator = Paginator(papers, page_size)
        paginated_papers = paginator.page(page)

        serializer = PaperListSerializer(paginated_papers, many=True)
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


class StarPaperView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, paper_id):
        user = request.user
        paper = get_object_or_404(Paper, id=paper_id)
        interesting, created = InterestingPaper.objects.get_or_create(
            user=user, paper=paper
        )
        return Response(
            {"message": "Paper marked as interesting", "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class UnstarPaperView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, paper_id):
        user = request.user
        interesting = InterestingPaper.objects.get(user=user, paper__id=paper_id)
        interesting.delete()
        return Response(
            {"message": "Paper removed from interesting"}, status=status.HTTP_200_OK
        )


class ListDownloadedPapers(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        downloaded_papers = DownloadedPaper.objects.filter(user=user).values_list(
            "paper", flat=True
        )
        serializer = PaperSerializer(downloaded_papers, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)


class MarkPaperDownloaded(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, paper_id):
        user = request.user
        paper = get_object_or_404(Paper, id=paper_id)
        downloaded, created = DownloadedPaper.objects.get_or_create(
            user=user, paper=paper
        )
        return Response(
            data={"message": "Paper marked as downloaded", "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class UnmarkPaperDownloaded(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, paper_id):
        user = request.user
        paper = get_object_or_404(Paper, id=paper_id)
        try:
            downloaded = DownloadedPaper.objects.get(user=user, paper=paper)
            downloaded.delete()
            return Response(
                data={"message": "Paper removed from downloaded"},
                status=status.HTTP_200_OK,
            )
        except DownloadedPaper.DoesNotExist:
            return Response(
                data={"message": "Paper was not marked as downloaded"},
                status=status.HTTP_404_NOT_FOUND,
            )

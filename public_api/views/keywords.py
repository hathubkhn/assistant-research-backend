from django.core.paginator import Paginator
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Paper, Task
from ..serializers import TaskListParamsSerializer, TaskSerializer


class ListKeywordsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        search = request.query_params.get("search", "")
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 50))

        papers = Paper.objects.all()
        keywords = papers.values_list("keywords", flat=True)
        all_keywords = list()

        for keyword in keywords:
            all_keywords.extend(keyword)

        all_keywords = list(set(all_keywords))
        sorted_keywords = sorted(all_keywords)
        paginator = Paginator(sorted_keywords, page_size)
        paginated_keywords = paginator.page(page)

        output = {
            "keywords": paginated_keywords,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalItems": paginator.count,
                "totalPages": paginator.num_pages,
            },
        }
        return Response(output, status=status.HTTP_200_OK)


class TasksList(APIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [AllowAny]
    ordering_fields = ["-created_at"]

    def get(self, request):
        try:
            params_serializer = TaskListParamsSerializer(data=request.query_params)
            params_serializer.is_valid(raise_exception=True)
            start_date = params_serializer.validated_data.get("startDate")
            end_date = params_serializer.validated_data.get("endDate")
            page = params_serializer.validated_data.get("page")
            page_size = params_serializer.validated_data.get("pageSize")
            task_ids = params_serializer.validated_data.get("taskIds", [])

            query = Q()
            if start_date:
                query &= Q(created_at__gte=start_date)
            if end_date:
                query &= Q(created_at__lte=end_date)
            if task_ids:
                query &= Q(id__in=task_ids)

            queryset = (
                self.queryset.filter(query)
                .annotate(papers_count=Count("papers"))
                .order_by("-papers_count")
            )
            paginator = Paginator(queryset, page_size)
            paginated_queryset = paginator.page(page)
            serializer = TaskSerializer(paginated_queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

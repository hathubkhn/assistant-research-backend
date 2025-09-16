from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from rest_framework import status

from ..models import Dataset, DatasetSimilarDataset, InterestingDataset
from ..serializers import DatasetListSerializer


class DatasetsList(APIView):
    queryset = Dataset.objects.all()
    permission_classes = [AllowAny]
    ordering_fields = ["-created_at"]

    def get(self, request):
        category = request.query_params.get("category")
        language = request.query_params.get("language")
        search = request.query_params.get("search")
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 20))

        datasets = Dataset.objects.all()

        filter_q = Q()
        if category:
            filter_q &= Q(data_type__icontains=category)
        if language:
            filter_q &= Q(language=language)
        if search:
            filter_q &= Q(name__icontains=search) | Q(description__icontains=search)

        datasets = datasets.filter(filter_q)

        total_count = datasets.count()
        paginator = Paginator(datasets, page_size)
        paginated_datasets = paginator.page(page)

        serializer = DatasetListSerializer(paginated_datasets, many=True)
        result = serializer.data

        response_data = {
            "results": result,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalItems": total_count,
                "totalPages": paginator.num_pages,
            },
        }

        return Response(response_data)


class DatasetDetail(APIView):
    permission_classes = [AllowAny]

    def get(self, request, dataset_id):
        dataset = get_object_or_404(Dataset, id=dataset_id)
        serializer = DatasetListSerializer(dataset, context={"request": request})
        dataset_data = serializer.data

        related_papers = []

        papers = dataset.papers.all().order_by("-created_at")
        for paper in papers:
            authors = paper.authors.values_list("name", flat=True)
            keywords = paper.keywords
            venue_type = paper.venue_type if hasattr(paper, "venue_type") else "conference"
            venue_name = (
                paper.venue_name if hasattr(paper, "venue_name") else paper.conference
            )
            paper_data = {
                "id": str(paper.id),
                "title": paper.title,
                "authors": authors,
                "abstract": paper.abstract,
                "conference": venue_name,
                "year": paper.publication_date.year if paper.publication_date else None,
                "field": None,
                "venue_type": venue_type,
                "keywords": keywords,
                "downloadUrl": paper.pdf_url if paper.pdf_url else None,
                "doi": paper.doi if paper.doi else None,
            }
            related_papers.append(paper_data)

        similar_datasets = []
        similar_relations = DatasetSimilarDataset.objects.filter(from_dataset=dataset)
        for relation in similar_relations:
            similar = relation.to_dataset
            similar_paper_count = similar.papers.count()
            similar_data = {
                "id": str(similar.id),
                "name": similar.name,
                "abbreviation": similar.abbreviation,
                "description": similar.description,
                "downloadUrl": similar.source_url,
                "language": similar.language if similar.language else "English",
                "category": similar.data_type or "Unknown",
                "tasks": similar.tasks.values_list("name", flat=True),
                "paperCount": similar_paper_count,
                "benchmarks": similar.benchmarks if similar.benchmarks else [],
            }
            similar_datasets.append(similar_data)

        result = {
            "dataset": dataset_data,
            "relatedPapers": related_papers,
            "similarDatasets": similar_datasets,
        }

        return Response(result, status=status.HTTP_200_OK)
    

class InterestingDatasets(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get datasets marked as interesting by the authenticated user with pagination
        """
        user = request.user
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 20))
        interesting = InterestingDataset.objects.filter(user=user)
        dataset_ids = [item.dataset.id for item in interesting]
        datasets = Dataset.objects.filter(id__in=dataset_ids)
        search = request.query_params.get("search")
        if search:
            datasets = datasets.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        paginator = Paginator(datasets, page_size)
        paginated_datasets = paginator.page(page)
        serializer = DatasetListSerializer(paginated_datasets, many=True)
        pagination = {
            "page": page,
            "pageSize": page_size,
            "totalItems": paginator.count,
            "totalPages": paginator.num_pages,
        }

        return Response({"results": serializer.data, "pagination": pagination}, status=status.HTTP_200_OK   )


class MarkDatasetInteresting(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, dataset_id):
        user = request.user

        dataset = get_object_or_404(Dataset, id=dataset_id)

        interesting, created = InterestingDataset.objects.get_or_create(
            user=user, dataset=dataset
        )

        return Response(
            {"message": "Dataset marked as interesting", "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class UnmarkDatasetInteresting(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, dataset_id):
        user = request.user
        dataset = get_object_or_404(Dataset, id=dataset_id)

        try:
            interesting = InterestingDataset.objects.get(user=user, dataset=dataset)
            interesting.delete()
            return Response(
                {"message": "Dataset removed from interesting"},
                status=status.HTTP_200_OK,
            )
        except InterestingDataset.DoesNotExist:
            return Response(
                {"message": "Dataset was not marked as interesting"},
                status=status.HTTP_404_NOT_FOUND,
            )

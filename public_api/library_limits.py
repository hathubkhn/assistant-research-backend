from rest_framework import status

from .error_responses import standard_error_response
from .models import InterestingDataset, InterestingPaper

MAX_INTERESTING_PAPERS = 50
MAX_INTERESTING_DATASETS = 10

PAPER_LIMIT_MESSAGE = (
    f"Bạn chỉ được thích tối đa {MAX_INTERESTING_PAPERS} bài báo. "
    "Hãy vào My Library để xóa bớt các bài không cần thiết."
)

DATASET_LIMIT_MESSAGE = (
    f"Bạn chỉ được thích tối đa {MAX_INTERESTING_DATASETS} dataset. "
    "Hãy vào My Library để xóa bớt các dataset không cần thiết."
)


def paper_interesting_limit_response(request):
    return standard_error_response(
        request,
        status.HTTP_403_FORBIDDEN,
        "LIBRARY_LIMIT_REACHED",
        PAPER_LIMIT_MESSAGE,
    )


def dataset_interesting_limit_response(request):
    return standard_error_response(
        request,
        status.HTTP_403_FORBIDDEN,
        "LIBRARY_LIMIT_REACHED",
        DATASET_LIMIT_MESSAGE,
    )


def can_add_interesting_paper(user, paper=None) -> bool:
    if paper is not None and InterestingPaper.objects.filter(
        user=user, paper=paper
    ).exists():
        return True
    return InterestingPaper.objects.filter(user=user).count() < MAX_INTERESTING_PAPERS


def can_add_interesting_dataset(user, dataset=None) -> bool:
    if dataset is not None and InterestingDataset.objects.filter(
        user=user, dataset=dataset
    ).exists():
        return True
    return (
        InterestingDataset.objects.filter(user=user).count()
        < MAX_INTERESTING_DATASETS
    )

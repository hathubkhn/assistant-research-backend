from django.core.paginator import Paginator


def _serialize_paper(paper):
    author_names = list(paper.authors.values_list("name", flat=True))
    return {
        "id": paper.id,
        "title": paper.title,
        "publication_date": paper.publication_date,
        "year": paper.publication_date.year if paper.publication_date else None,
        "authors": author_names if author_names else ["Unknown"],
    }


def paginate_venue_papers(papers_queryset, page=1, page_size=20):
    ordered = papers_queryset.order_by("-publication_date")
    paginator = Paginator(ordered, page_size)
    page_obj = paginator.get_page(page)
    papers = page_obj.object_list.prefetch_related("authors")
    items = [_serialize_paper(paper) for paper in papers]
    return {
        "results": items,
        "pagination": {
            "page": page_obj.number,
            "pageSize": page_size,
            "totalItems": paginator.count,
            "totalPages": paginator.num_pages,
        },
    }

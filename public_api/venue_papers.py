def serialize_venue_papers(papers_queryset):
    papers = papers_queryset.prefetch_related("authors").order_by("-publication_date")
    items = []
    for paper in papers:
        author_names = list(paper.authors.values_list("name", flat=True))
        items.append(
            {
                "id": paper.id,
                "title": paper.title,
                "publication_date": paper.publication_date,
                "year": paper.publication_date.year if paper.publication_date else None,
                "authors": author_names if author_names else ["Unknown"],
            }
        )
    return items

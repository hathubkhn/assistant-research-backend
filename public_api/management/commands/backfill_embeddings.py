"""Backfill Qdrant embeddings for papers that were never indexed.

Usage:
    python manage.py backfill_embeddings              # all papers with embedded_at IS NULL
    python manage.py backfill_embeddings --limit 100  # cap for a smoke test
    python manage.py backfill_embeddings --redo-all   # re-embed everything (Qdrant upserts)
"""
from django.core.management.base import BaseCommand

from public_api.models import Paper
from public_api.services.embed_client import embed_paper


class Command(BaseCommand):
    help = "POST every paper with embedded_at IS NULL to the research_assistant /papers endpoint."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Stop after N papers")
        parser.add_argument(
            "--redo-all",
            action="store_true",
            help="Re-embed every paper, including ones already marked embedded.",
        )

    def handle(self, *args, **opts):
        qs = Paper.objects.all() if opts["redo_all"] else Paper.objects.filter(embedded_at__isnull=True)
        qs = qs.order_by("created_at")
        if opts["limit"]:
            qs = qs[: opts["limit"]]

        total = qs.count() if not opts["limit"] else min(opts["limit"], Paper.objects.count())
        self.stdout.write(f"Embedding {total} papers...")

        ok, fail = 0, 0
        for i, paper in enumerate(qs.iterator(), 1):
            if embed_paper(paper):
                ok += 1
            else:
                fail += 1
            if i % 25 == 0:
                self.stdout.write(f"  [{i}/{total}] ok={ok} fail={fail}")

        self.stdout.write(self.style.SUCCESS(f"Done. ok={ok} fail={fail}"))

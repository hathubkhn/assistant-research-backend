"""Assign placeholder thumbnail URLs to datasets from frontend static images.

Usage:
    python manage.py assign_dataset_thumbnails
    python manage.py assign_dataset_thumbnails --dry-run
    python manage.py assign_dataset_thumbnails --only-empty
    python manage.py assign_dataset_thumbnails --base-url https://staging-ai-research.hust.edu.vn
"""
import random

from django.conf import settings
from django.core.management.base import BaseCommand

from public_api.models import Dataset

DATASET_THUMBNAIL_FILES = [
    "celeba.jpg",
    "cifar100.jpeg",
    "cityscapes.png",
    "kitti.jpg",
    "mnist.png",
    "nerf.jpeg",
    "svhn.png",
]


class Command(BaseCommand):
    help = "Assign random placeholder thumbnail_url values for all datasets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            type=str,
            default=None,
            help="Frontend origin for image URLs (default: settings.FRONTEND_URL)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Records per bulk_update batch",
        )
        parser.add_argument(
            "--only-empty",
            action="store_true",
            help="Only update datasets with blank thumbnail_url",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview counts and sample URLs without writing to DB",
        )

    def handle(self, *args, **options):
        base_url = (options["base_url"] or settings.FRONTEND_URL).rstrip("/")
        batch_size = max(1, options["batch_size"])
        urls = [f"{base_url}/images/datasets/{name}" for name in DATASET_THUMBNAIL_FILES]

        qs = Dataset.objects.all().order_by("id")
        if options["only_empty"]:
            qs = qs.filter(thumbnail_url="")

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No datasets to update."))
            return

        self.stdout.write(
            f"{'[dry-run] ' if options['dry_run'] else ''}"
            f"Updating {total} datasets with thumbnails from {base_url}/images/datasets/"
        )
        self.stdout.write(f"Pool: {', '.join(DATASET_THUMBNAIL_FILES)}")

        if options["dry_run"]:
            sample = qs[:5]
            for ds in sample:
                self.stdout.write(f"  {ds.name}: {random.choice(urls)}")
            self.stdout.write(self.style.SUCCESS(f"Dry run complete. Would update {total} datasets."))
            return

        updated = 0
        buffer: list[Dataset] = []

        for dataset in qs.only("id", "thumbnail_url").iterator(chunk_size=2000):
            dataset.thumbnail_url = random.choice(urls)
            buffer.append(dataset)

            if len(buffer) >= batch_size:
                Dataset.objects.bulk_update(buffer, ["thumbnail_url"], batch_size=batch_size)
                updated += len(buffer)
                self.stdout.write(f"  updated {updated}/{total}")
                buffer.clear()

        if buffer:
            Dataset.objects.bulk_update(buffer, ["thumbnail_url"], batch_size=batch_size)
            updated += len(buffer)

        self.stdout.write(self.style.SUCCESS(f"Done. Updated {updated} datasets."))

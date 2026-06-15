"""
Normalize conference.rank to A*|A|B|C or empty (unranked).

Usage:
  python manage.py normalize_conference_ranks --dry-run
  python manage.py normalize_conference_ranks
"""
from django.core.management.base import BaseCommand

from public_api.conference_ranks import DISPLAY_UNRANKED, normalize_conference_rank
from public_api.models import Conference


class Command(BaseCommand):
    help = "Set conference.rank to A*|A|B|C or empty string for all unranked aliases."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print changes without saving",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        changed = 0
        samples: list[str] = []

        qs = Conference.objects.all().only("id", "name", "rank")
        for conf in qs.iterator():
            current = conf.rank or ""
            normalized = normalize_conference_rank(current)
            if current == normalized:
                continue
            changed += 1
            if len(samples) < 15:
                shown = normalized or DISPLAY_UNRANKED
                samples.append(
                    f"  {conf.name[:60]!r}: {current!r} -> {shown!r}"
                )
            if not dry_run:
                conf.rank = normalized
                conf.save(update_fields=["rank", "updated_at"])

        for line in samples:
            self.stdout.write(line)
        if changed > len(samples):
            self.stdout.write(f"  ... and {changed - len(samples)} more")

        verb = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f"{verb} {changed} conference(s). Unranked stored as empty string; API displays '{DISPLAY_UNRANKED}'.")
        )

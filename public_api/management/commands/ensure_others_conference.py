"""
Create or update the placeholder Conference used for papers pending venue review.

Usage:
  python manage.py ensure_others_conference
  python manage.py ensure_others_conference --dry-run
"""
from django.core.management.base import BaseCommand

from public_api.models import Conference

OTHERS_NAME = "Others"
OTHERS_RANK = "not rank"


class Command(BaseCommand):
    help = 'Ensure Conference(name="Others") exists for temporary review mapping'

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be done without saving",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        defaults = {
            "abbreviation": "",
            "rank": OTHERS_RANK,
            "location": "",
            "url": "",
        }

        if dry_run:
            existing = Conference.objects.filter(name=OTHERS_NAME).first()
            if existing:
                self.stdout.write(
                    f'[dry-run] Would update: id={existing.id} name="{OTHERS_NAME}" '
                    f'rank="{OTHERS_RANK}" (other fields empty)'
                )
            else:
                self.stdout.write(
                    f'[dry-run] Would create: name="{OTHERS_NAME}" rank="{OTHERS_RANK}" '
                    "(abbreviation, location, url empty)"
                )
            return

        conference, created = Conference.objects.update_or_create(
            name=OTHERS_NAME,
            defaults=defaults,
        )

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f'{action} Conference "{OTHERS_NAME}" (id={conference.id}, rank="{OTHERS_RANK}")'
            )
        )
        self.stdout.write(
            "Use this id when applying review papers to the Others bucket."
        )

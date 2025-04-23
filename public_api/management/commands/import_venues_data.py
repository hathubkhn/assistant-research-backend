import csv
import pandas as pd
import os
from django.core.management.base import BaseCommand
from public_api.models import Journal, Conference
from django.db import transaction


class Command(BaseCommand):
    help = 'Imports journal and conference data from files in backend/data directory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-existing',
            action='store_true',
            help='Delete existing journal and conference data before importing',
        )

    def handle(self, *args, **options):
        # Use absolute paths relative to the project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        data_dir = os.path.join(base_dir, 'data')
        journal_file = os.path.join(data_dir, 'scimagojr 2024.csv')
        conference_file = os.path.join(data_dir, 'era2010_conference_list.xlsx')

        self.stdout.write(f'Looking for data files in: {data_dir}')

        if options['delete_existing']:
            self.stdout.write('Deleting existing journal and conference data...')
            Journal.objects.all().delete()
            Conference.objects.all().delete()

        self.import_journals(journal_file)
        self.import_conferences(conference_file)

    def import_journals(self, journal_file):
        self.stdout.write(f'Importing journals from {journal_file}...')
        
        if not os.path.exists(journal_file):
            self.stderr.write(self.style.ERROR(f'Journal file not found: {journal_file}'))
            return
            
        journals_created = 0
        journals_skipped = 0
        
        try:
            with open(journal_file, 'r', encoding='utf-8') as file:
                reader = csv.reader(file, delimiter=';')
                headers = next(reader)  # Skip header row
                
                # Find indexes for relevant columns
                title_idx = headers.index('Title')
                issn_idx = headers.index('Issn')
                quartile_idx = headers.index('SJR Best Quartile')
                publisher_idx = headers.index('Publisher')
                
                # SJR is the impact factor
                impact_factor_idx = headers.index('SJR')
                
                with transaction.atomic():
                    for row in reader:
                        if len(row) >= len(headers):
                            name = row[title_idx].strip('"')
                            impact_factor = None
                            try:
                                # Convert impact factor from string to float, handling comma as decimal separator
                                impact_value = row[impact_factor_idx].replace(',', '.')
                                impact_factor = float(impact_value)
                            except (ValueError, IndexError):
                                pass
                            
                            quartile = row[quartile_idx] if quartile_idx < len(row) else ''
                            publisher = row[publisher_idx].strip('"') if publisher_idx < len(row) else ''
                            issn = row[issn_idx].strip('"') if issn_idx < len(row) else ''
                            
                            # Skip if name is empty
                            if not name:
                                journals_skipped += 1
                                continue
                            
                            try:
                                journal, created = Journal.objects.get_or_create(
                                    name=name,
                                    defaults={
                                        'impact_factor': impact_factor,
                                        'quartile': quartile,
                                        'publisher': publisher,
                                        'abbreviation': issn  # Using ISSN as abbreviation
                                    }
                                )
                                
                                if created:
                                    journals_created += 1
                                else:
                                    # Update existing journal with the new data
                                    journal.impact_factor = impact_factor
                                    journal.quartile = quartile
                                    journal.publisher = publisher
                                    journal.abbreviation = issn
                                    journal.save()
                            except Exception as e:
                                self.stderr.write(f'Error creating journal {name}: {str(e)}')
                                journals_skipped += 1
                
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {journals_created} journals ({journals_skipped} skipped)'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error importing journals: {str(e)}'))

    def import_conferences(self, conference_file):
        self.stdout.write(f'Importing conferences from {conference_file}...')
        
        if not os.path.exists(conference_file):
            self.stderr.write(self.style.ERROR(f'Conference file not found: {conference_file}'))
            return
            
        conferences_created = 0
        conferences_skipped = 0
        
        try:
            df = pd.read_excel(conference_file)
            
            with transaction.atomic():
                for _, row in df.iterrows():
                    try:
                        name = row['Title']
                        acronym = row['Acronym'] if not pd.isna(row['Acronym']) else ''
                        rank = row['Rank'] if not pd.isna(row['Rank']) else ''
                        
                        # Skip if name is empty
                        if pd.isna(name) or not name:
                            conferences_skipped += 1
                            continue
                        
                        conference, created = Conference.objects.get_or_create(
                            name=name,
                            defaults={
                                'abbreviation': acronym,
                                'rank': rank,
                            }
                        )
                        
                        if created:
                            conferences_created += 1
                        else:
                            # Update existing conference with the new data
                            conference.abbreviation = acronym
                            conference.rank = rank
                            conference.save()
                    except Exception as e:
                        self.stderr.write(f'Error creating conference {name if "name" in locals() else "unknown"}: {str(e)}')
                        conferences_skipped += 1
            
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {conferences_created} conferences ({conferences_skipped} skipped)'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error importing conferences: {str(e)}')) 
from django.core.management.base import BaseCommand
from public_api.models import Journal, Conference, Paper
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Populates the Journal and Conference models with data and links them to papers'

    def handle(self, *args, **options):
        # Pre-defined journals with their impact factors and quartiles
        journals_data = {
            'IEEE Transactions on Pattern Analysis and Machine Intelligence': {'impactFactor': 24.314, 'quartile': 'Q1'},
            'Journal of Machine Learning Research': {'impactFactor': 8.09, 'quartile': 'Q1'},
            'IEEE Transactions on Neural Networks and Learning Systems': {'impactFactor': 14.255, 'quartile': 'Q1'},
            'Computational Linguistics': {'impactFactor': 6.244, 'quartile': 'Q1'},
            'ACM Computing Surveys': {'impactFactor': 14.324, 'quartile': 'Q1'},
            'Journal of Artificial Intelligence Research': {'impactFactor': 5.151, 'quartile': 'Q1'},
            'International Journal of Computer Vision': {'impactFactor': 13.369, 'quartile': 'Q1'},
            'IEEE Transactions on Image Processing': {'impactFactor': 10.856, 'quartile': 'Q1'},
            'IEEE Transactions on Knowledge and Data Engineering': {'impactFactor': 8.935, 'quartile': 'Q1'},
            'Data Mining and Knowledge Discovery': {'impactFactor': 5.389, 'quartile': 'Q2'},
            'ACM Transactions on Database Systems': {'impactFactor': 3.785, 'quartile': 'Q2'},
            'The VLDB Journal': {'impactFactor': 4.595, 'quartile': 'Q2'}
        }
        
        # Major conferences in CS/AI/ML
        conferences_data = {
            'Neural Information Processing Systems': {'abbreviation': 'NeurIPS', 'rank': 'A*'},
            'International Conference on Machine Learning': {'abbreviation': 'ICML', 'rank': 'A*'},
            'IEEE Conference on Computer Vision and Pattern Recognition': {'abbreviation': 'CVPR', 'rank': 'A*'},
            'International Conference on Learning Representations': {'abbreviation': 'ICLR', 'rank': 'A*'},
            'ACM SIGKDD Conference on Knowledge Discovery and Data Mining': {'abbreviation': 'KDD', 'rank': 'A*'},
            'AAAI Conference on Artificial Intelligence': {'abbreviation': 'AAAI', 'rank': 'A*'},
            'International Joint Conference on Artificial Intelligence': {'abbreviation': 'IJCAI', 'rank': 'A*'},
            'ACL Annual Meeting': {'abbreviation': 'ACL', 'rank': 'A*'},
            'European Conference on Computer Vision': {'abbreviation': 'ECCV', 'rank': 'A*'},
            'International Conference on Computer Vision': {'abbreviation': 'ICCV', 'rank': 'A*'},
            'SIAM International Conference on Data Mining': {'abbreviation': 'SDM', 'rank': 'A'},
            'Conference on Empirical Methods in Natural Language Processing': {'abbreviation': 'EMNLP', 'rank': 'A'},
            'International Conference on Computational Linguistics': {'abbreviation': 'COLING', 'rank': 'A'},
            'International Conference on Information and Knowledge Management': {'abbreviation': 'CIKM', 'rank': 'A'},
            'International Conference on Web Search and Data Mining': {'abbreviation': 'WSDM', 'rank': 'A'},
            'International Conference on Artificial Intelligence and Statistics': {'abbreviation': 'AISTATS', 'rank': 'A'},
            'International Conference on Automated Planning and Scheduling': {'abbreviation': 'ICAPS', 'rank': 'A'},
            'International Conference on Database Theory': {'abbreviation': 'ICDT', 'rank': 'A'},
            'International World Wide Web Conference': {'abbreviation': 'WWW', 'rank': 'A'}
        }
        
        # Create journals
        journals_created = 0
        for name, data in journals_data.items():
            journal, created = Journal.objects.get_or_create(
                name=name,
                defaults={
                    'impact_factor': data['impactFactor'],
                    'quartile': data['quartile'],
                    'abbreviation': name[:10] if len(name) > 10 else name
                }
            )
            if created:
                journals_created += 1
        
        # Create conferences
        conferences_created = 0
        for name, data in conferences_data.items():
            conference, created = Conference.objects.get_or_create(
                name=name,
                defaults={
                    'abbreviation': data['abbreviation'],
                    'rank': data['rank']
                }
            )
            if created:
                conferences_created += 1
                
        self.stdout.write(self.style.SUCCESS(f'Created {journals_created} journals and {conferences_created} conferences'))
        
        # Link existing papers to journals/conferences
        journal_names = list(journals_data.keys())
        conference_names = list(conferences_data.keys())
        
        papers_updated = 0
        papers_not_found = 0
        
        # Update all papers
        for paper in Paper.objects.all():
            # Skip if already linked
            if paper.journal is not None or paper.conference_venue is not None:
                continue
                
            venue_name = paper.conference
            if venue_name in journal_names:
                try:
                    journal = Journal.objects.get(name=venue_name)
                    paper.journal = journal
                    paper.save()
                    papers_updated += 1
                except Journal.DoesNotExist:
                    papers_not_found += 1
                    logger.warning(f"Journal not found: {venue_name}")
            elif venue_name in conference_names:
                try:
                    conference = Conference.objects.get(name=venue_name)
                    paper.conference_venue = conference
                    paper.save()
                    papers_updated += 1
                except Conference.DoesNotExist:
                    papers_not_found += 1
                    logger.warning(f"Conference not found: {venue_name}")
            else:
                # For venues not in our known list, create as conference (default)
                if venue_name:
                    conference, _ = Conference.objects.get_or_create(
                        name=venue_name,
                        defaults={
                            'abbreviation': venue_name[:5] if len(venue_name) > 5 else venue_name
                        }
                    )
                    paper.conference_venue = conference
                    paper.save()
                    papers_updated += 1
        
        self.stdout.write(self.style.SUCCESS(f'Updated {papers_updated} papers with venue references'))
        if papers_not_found > 0:
            self.stdout.write(self.style.WARNING(f'Could not find venue for {papers_not_found} papers')) 
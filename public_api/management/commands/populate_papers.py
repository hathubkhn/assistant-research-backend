from django.core.management.base import BaseCommand
from public_api.models import Journal, Conference, Paper
import uuid
import random
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Populates the Paper model with sample data linked to journals and conferences'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of papers to generate for each venue type (journals and conferences)'
        )

    def handle(self, *args, **options):
        count = options['count']
        self.stdout.write(f"Generating {count} papers for each venue type (journals and conferences)...")

        # Get all journals and conferences
        journals = list(Journal.objects.all())
        conferences = list(Conference.objects.all())

        if not journals:
            self.stdout.write(self.style.WARNING('No journals found. Please run populate_venues command first.'))
            return
            
        if not conferences:
            self.stdout.write(self.style.WARNING('No conferences found. Please run populate_venues command first.'))
            return

        # Sample paper data
        paper_titles = [
            "Deep Learning for Natural Language Processing: A Comprehensive Review",
            "Transformer-based Architectures for Vision Tasks",
            "A Survey of Reinforcement Learning Techniques in Robotics",
            "Attention Mechanisms in Computer Vision: Progress and Challenges",
            "Large Language Models: Capabilities, Limitations and Ethics",
            "Transfer Learning Approaches for Low-Resource Languages",
            "Explainable AI: Methods, Applications and Future Directions",
            "Neural Architecture Search: Automated Machine Learning",
            "Graph Neural Networks for Knowledge Representation",
            "Self-Supervised Learning in Computer Vision",
            "Federated Learning for Privacy-Preserving AI",
            "Multimodal Deep Learning: Integrating Vision and Language",
            "Generative Adversarial Networks: Recent Advances",
            "Diffusion Models for Image Generation and Editing",
            "Quantum Machine Learning: Algorithms and Applications",
            "Deep Reinforcement Learning for Game Playing",
            "Neural Machine Translation: Beyond Transformers",
            "Contrastive Learning Methods for Visual Representations",
            "Few-Shot Learning: Methods and Applications",
            "Robustness in Deep Learning: Addressing Adversarial Attacks",
            "Causal Inference in Machine Learning",
            "Natural Language Generation: Techniques and Evaluation",
            "Deep Learning for Time Series Analysis",
            "Multiagent Reinforcement Learning: Cooperation and Competition",
            "Ethical Considerations in AI Development",
            "AI for Climate Change: Methods and Applications",
            "Neural Networks for Recommendation Systems",
            "Knowledge Distillation in Deep Neural Networks",
            "Vision Transformers: Architecture and Performance",
            "Deep Learning for Medical Image Analysis"
        ]
        
        abstracts = [
            "This paper provides a comprehensive review of recent advances in deep learning for natural language processing. We explore transformer models, pre-training techniques, and downstream applications.",
            "We present a novel architecture that combines the strengths of transformers and convolutional networks for vision tasks. Our approach achieves state-of-the-art results on several benchmarks.",
            "This study examines reinforcement learning applications in robotics, with a focus on sample efficiency and real-world deployment challenges. We demonstrate significant improvements over previous methods.",
            "Our work investigates attention mechanisms for computer vision tasks. We propose several new techniques that enhance model performance while reducing computational requirements.",
            "This research explores the capabilities and limitations of large language models. We evaluate their reasoning abilities, factual accuracy, and ethical implications across diverse tasks.",
            "We propose a new approach for transfer learning in low-resource languages that leverages multilingual representations. Our method shows significant improvements over existing techniques.",
            "This paper presents novel methods for making AI systems more explainable. We demonstrate applications across healthcare, finance, and legal domains with human evaluation studies.",
            "Our work introduces an efficient neural architecture search framework that reduces computational costs while maintaining performance. We provide extensive benchmarks across multiple domains.",
            "This research applies graph neural networks to knowledge representation tasks. Our approach shows superior performance on knowledge graph completion and question answering.",
            "We present a self-supervised learning framework for computer vision that requires no labeled data. Our method achieves competitive results compared to supervised approaches.",
        ]
        
        fields = [
            "Artificial Intelligence",
            "Computational Linguistics",
            "Computer Vision & Pattern Recognition",
            "Data Mining & Analysis",
            "Databases & Information Systems",
            "Robotics",
            "Computer Graphics",
            "Computer Networks & Wireless Communication",
            "Multimedia"
        ]
        
        all_keywords = [
            "Deep Learning", "Neural Networks", "Transformers", "Machine Learning", "NLP", 
            "Computer Vision", "Reinforcement Learning", "Transfer Learning", "Few-Shot Learning",
            "Self-Supervised Learning", "Attention Mechanisms", "GANs", "Knowledge Graphs",
            "Graph Neural Networks", "Explainable AI", "Large Language Models", "Multimodal Learning",
            "Diffusion Models", "Vision Transformers", "Quantum Computing", "Federated Learning",
            "Ethical AI", "Adversarial Robustness", "Causal Inference", "Image Generation",
            "Contrastive Learning", "Multiagent Systems", "Time Series Analysis", "Medical AI"
        ]
        
        authors_list = [
            ["John Smith", "Emily Chen", "David Wong"],
            ["Zhang Wei", "Sarah Johnson", "Michael Brown"],
            ["Aisha Patel", "Carlos Rodriguez", "Emma Wilson"],
            ["Raj Kumar", "Sophia Lee", "Thomas Miller"],
            ["Olivia Davis", "Yuki Tanaka", "Alexander Petrov"],
            ["Maria Garcia", "James Kim", "Fatima Ahmed"],
            ["Li Wei", "Samantha Taylor", "Robert Jackson"],
            ["Hiroshi Yamamoto", "Elizabeth Martin", "Ahmed Hassan"],
            ["Isabella Romano", "Noah Chen", "Priya Singh"],
            ["Daniel Park", "Grace Wang", "William Johnson"],
            ["Sofia Gonzalez", "Mohammed Al-Farsi", "Jennifer Wu"],
            ["Mateo Rossi", "Chitra Patel", "Kevin Zhang"],
            ["Lucas Silva", "Anya Ivanova", "Gabriel Chen"]
        ]
        
        current_year = datetime.now().year
        years = list(range(current_year - 4, current_year + 1))
        
        # Generate papers for journals
        journal_papers_created = 0
        for i in range(count):
            # Randomize properties
            title = random.choice(paper_titles)
            abstract = random.choice(abstracts)
            authors = random.choice(authors_list)
            journal = random.choice(journals)
            year = random.choice(years)
            field = random.choice(fields)
            
            # Create 2-5 random keywords
            num_keywords = random.randint(2, 5)
            keywords = random.sample(all_keywords, num_keywords)
            
            # Create the paper
            paper = Paper.objects.create(
                title=title,
                abstract=abstract,
                authors=authors,
                journal=journal,
                year=year,
                field=field,
                keywords=keywords,
                downloadUrl=f"https://example.com/papers/{uuid.uuid4()}",
                doi=f"10.{random.randint(1000, 9999)}/{uuid.uuid4().hex[:8]}",
                method="Our method utilizes a novel approach combining techniques from...",
                results="Experiments demonstrate significant improvements over baselines...",
                conclusions="We have shown that our approach outperforms existing methods...",
                bibtex=f"@article{{{authors[0].split()[-1].lower()}{year},\n  title={{{title}}},\n  author={{{' and '.join(authors)}}},\n  journal={{{journal.name}}},\n  year={{{year}}}\n}}",
                sourceCode=f"https://github.com/example/paper-{uuid.uuid4().hex[:8]}"
            )
            
            journal_papers_created += 1
        
        # Generate papers for conferences
        conference_papers_created = 0
        for i in range(count):
            # Randomize properties
            title = random.choice(paper_titles) 
            abstract = random.choice(abstracts)
            authors = random.choice(authors_list)
            conference_venue = random.choice(conferences)
            year = random.choice(years)
            field = random.choice(fields)
            
            # Create 2-5 random keywords
            num_keywords = random.randint(2, 5)
            keywords = random.sample(all_keywords, num_keywords)
            
            # Create the paper
            paper = Paper.objects.create(
                title=title,
                abstract=abstract,
                authors=authors,
                conference_venue=conference_venue,
                conference=conference_venue.name,  # Also set the legacy field
                year=year,
                field=field,
                keywords=keywords,
                downloadUrl=f"https://example.com/papers/{uuid.uuid4()}",
                doi=f"10.{random.randint(1000, 9999)}/{uuid.uuid4().hex[:8]}",
                method="We propose a novel architecture that...",
                results="Our approach achieves state-of-the-art performance on multiple benchmarks...",
                conclusions="This work demonstrates the effectiveness of our proposed method...",
                bibtex=f"@inproceedings{{{authors[0].split()[-1].lower()}{year},\n  title={{{title}}},\n  author={{{' and '.join(authors)}}},\n  booktitle={{{conference_venue.name}}},\n  year={{{year}}}\n}}",
                sourceCode=f"https://github.com/example/paper-{uuid.uuid4().hex[:8]}"
            )
            
            conference_papers_created += 1
            
        self.stdout.write(self.style.SUCCESS(f'Created {journal_papers_created} journal papers and {conference_papers_created} conference papers')) 
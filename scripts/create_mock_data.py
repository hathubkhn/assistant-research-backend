#!/usr/bin/env python
import os
import sys
import json
import random
import uuid
from django.utils import timezone
from datetime import datetime, timedelta

# Add project path for Django app import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')

import django
django.setup()

# After Django setup, import models
from django.contrib.auth.models import User
from public_api.models import Profile, Paper, Dataset, Publication, InterestingPaper

# Sample data
paper_titles = [
    "A Comprehensive Survey of Neural Network Architectures",
    "Deep Learning for Computer Vision: A Review",
    "Natural Language Processing with Transformers",
    "Reinforcement Learning: Algorithms and Applications",
    "Graph Neural Networks for Knowledge Representation",
    "Attention Mechanisms in Deep Learning",
    "Generative Adversarial Networks: State of the Art",
    "Self-Supervised Learning Methods for Visual Recognition",
    "Federated Learning: Privacy-Preserving Machine Learning",
    "Transfer Learning in Natural Language Processing",
    "Meta-Learning Approaches for Few-Shot Learning",
    "Explainable AI: Methods and Applications",
    "Contrastive Learning for Visual Representation",
    "Quantum Machine Learning: Challenges and Opportunities",
    "Time Series Analysis with Neural Networks",
    "Multimodal Learning for Healthcare Applications",
    "Robotic Learning: From Simulation to Real-World",
    "Deep Reinforcement Learning for Game AI",
    "Neural Architecture Search: A Survey",
    "Adversarial Attacks and Defenses in Deep Learning"
]

conference_names = [
    "NeurIPS", "ICML", "ICLR", "CVPR", "ECCV", "ACL", 
    "EMNLP", "NAACL", "AAAI", "IJCAI", "KDD", "WWW", 
    "SIGIR", "CIKM", "WSDM", "ICDE", "VLDB", "SIGMOD"
]

fields = [
    "Computer Vision", "Natural Language Processing", "Reinforcement Learning",
    "Graph Neural Networks", "Generative Models", "Self-Supervised Learning",
    "Federated Learning", "Transfer Learning", "Meta-Learning", "Explainable AI",
    "Contrastive Learning", "Quantum Computing", "Time Series Analysis", 
    "Multimodal Learning", "Robotics", "Game AI", "Neural Architecture Search", 
    "Adversarial Learning"
]

keywords_list = [
    "deep learning", "neural networks", "machine learning", "artificial intelligence",
    "computer vision", "NLP", "reinforcement learning", "GNN", "GANs", "transformers",
    "self-supervised", "federated learning", "transfer learning", "meta-learning",
    "XAI", "contrastive learning", "quantum ML", "time series", "multimodal",
    "robotics", "game AI", "NAS", "adversarial", "attention mechanisms",
    "representation learning", "few-shot learning", "zero-shot learning", 
    "multi-task learning", "generative models", "knowledge graphs"
]

dataset_names = [
    "ImageNet", "COCO", "CIFAR-10", "CIFAR-100", "MNIST", "Fashion-MNIST",
    "WikiText", "SQuAD", "GLUE", "SuperGLUE", "Penn Treebank", "UCI ML Repository",
    "KITTI", "NYU Depth", "CelebA", "MS MARCO", "ChestX-ray14", "MIMIC-III",
    "Cityscapes", "Pascal VOC", "ADE20K", "LFW", "VQA", "Flickr30k", "Open Images",
    "YouTube-8M", "Kinetics", "AudioSet", "LibriSpeech", "VoxCeleb"
]

dataset_categories = [
    "Computer Vision", "Natural Language Processing", "Speech Recognition",
    "Healthcare", "Autonomous Driving", "Recommendation Systems", "Graph Analysis",
    "Time Series", "Multimodal", "Facial Recognition", "Object Detection",
    "Sentiment Analysis", "Machine Translation", "Question Answering"
]

languages = ["English", "Multilingual", "Chinese", "Spanish", "French", "German", "Japanese", "Korean"]

tasks = [
    "Image Classification", "Object Detection", "Semantic Segmentation", "Instance Segmentation",
    "Text Classification", "Named Entity Recognition", "Machine Translation", "Question Answering",
    "Summarization", "Sentiment Analysis", "Speech Recognition", "Speech Synthesis",
    "Recommendation", "Link Prediction", "Node Classification", "Time Series Forecasting",
    "Anomaly Detection", "Clustering", "Dimensionality Reduction", "Reinforcement Learning"
]

# Hàm helpers
def generate_random_authors(min_authors=2, max_authors=6):
    first_names = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa", 
                  "Daniel", "Amy", "William", "Susan", "Richard", "Mary", "Joseph", "Linda", 
                  "Thomas", "Patricia", "Charles", "Jennifer"]
    last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", 
                 "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", 
                 "Thompson", "Garcia", "Martinez", "Robinson"]
    
    num_authors = random.randint(min_authors, max_authors)
    authors = []
    
    for _ in range(num_authors):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        authors.append(f"{first_name} {last_name}")
    
    return json.dumps(authors)

def generate_random_keywords(min_kw=3, max_kw=8):
    num_keywords = random.randint(min_kw, max_kw)
    selected_keywords = random.sample(keywords_list, num_keywords)
    return json.dumps(selected_keywords)

def generate_random_date(start_year=2015, end_year=2023):
    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return timezone.make_aware(datetime(year, month, day))

def generate_random_abstract():
    sentences = [
        "This paper presents a novel approach to address the challenges in the field.",
        "We propose a new architecture that outperforms existing methods.",
        "Our method achieves state-of-the-art results on multiple benchmarks.",
        "Experimental results demonstrate the effectiveness of the proposed approach.",
        "We conduct extensive experiments to evaluate the performance of our method.",
        "The results show significant improvements over baseline methods.",
        "Our approach effectively addresses the limitations of previous work.",
        "We introduce a new dataset for evaluating the proposed method.",
        "The proposed method is scalable and can be applied to various domains.",
        "We provide theoretical analysis to support our empirical findings."
    ]
    
    num_sentences = random.randint(5, 10)
    selected_sentences = random.sample(sentences, num_sentences)
    return " ".join(selected_sentences)

def generate_random_tasks(min_tasks=1, max_tasks=4):
    num_tasks = random.randint(min_tasks, max_tasks)
    selected_tasks = random.sample(tasks, num_tasks)
    return json.dumps(selected_tasks)

def get_or_create_users(num_users=10):
    """Get existing users or create new ones if needed"""
    # Get existing users
    existing_users = list(User.objects.all())
    print(f"Found {len(existing_users)} existing users")
    
    # If we have enough, return the existing list
    if len(existing_users) >= num_users:
        return existing_users[:num_users]
    
    # If not enough, create more users
    users = existing_users.copy()
    for i in range(len(existing_users) + 1, num_users + 1):
        username = f"user{i}"
        email = f"user{i}@example.com"
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password="password123",
                first_name=f"First{i}",
                last_name=f"Last{i}",
                is_active=True
            )
            
            # Create user profile
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': f"First{i} Last{i}",
                    'faculty_institute': f"Institute {i}",
                    'school': f"University {i}",
                    'research_interests': f"keyword{i}, research{i}, topic{i}",
                    'position': random.choice(["Professor", "Associate Professor", "Assistant Professor", "PhD Student", "Researcher"]),
                    'bio': f"This is a bio for user {i}. Research interests include AI, ML, and NLP.",
                    'is_profile_completed': True
                }
            )
            
            users.append(user)
            print(f"Created user: {username}")
        except Exception as e:
            print(f"Failed to create user {username}: {e}")
    
    # Cập nhật profiles cho các users hiện có
    for user in existing_users:
        if not hasattr(user, 'profile') or user.profile is None:
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': f"{user.first_name} {user.last_name}",
                    'faculty_institute': f"Institute {random.randint(1, 5)}",
                    'school': f"University {random.randint(1, 10)}",
                    'keywords': f"keyword{random.randint(1, 20)}, research, topic",
                    'position': random.choice(["Professor", "Associate Professor", "Assistant Professor", "PhD Student", "Researcher"]),
                    'bio': f"This is a bio for {user.username}. Research interests include AI, ML, and NLP.",
                    'is_profile_completed': True
                }
            )
            
        if not hasattr(user, 'public_profile') or user.public_profile is None:
            public_profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'name': f"{user.first_name} {user.last_name}",
                    'institution': f"University {random.randint(1, 10)}",
                    'role': user.profile.position if hasattr(user, 'profile') else "Researcher",
                    'bio': user.profile.bio if hasattr(user, 'profile') else f"Bio for {user.username}",
                    'research_interests': user.profile.keywords if hasattr(user, 'profile') else "AI, ML, NLP"
                }
            )
    
    return users

def create_papers(num_papers=20):
    """Create sample papers in the database"""
    print(f"Creating {num_papers} papers...")
    papers = []
    
    for i in range(num_papers):
        title = random.choice(paper_titles) if i < len(paper_titles) else f"Research Paper {i+1}"
        authors = generate_random_authors()
        year = random.randint(2015, 2023)
        conference = random.choice(conference_names)
        field = random.choice(fields)
        keywords = generate_random_keywords()
        abstract = generate_random_abstract()
        download_url = f"https://example.com/papers/{uuid.uuid4()}"
        doi = f"10.1234/paper.{random.randint(1000, 9999)}.{random.randint(100, 999)}"
        
        # Create paper object
        paper = Paper.objects.create(
            id=uuid.uuid4(),
            title=title,
            authors=json.loads(authors),
            year=year,
            conference=conference,
            field=field,
            keywords=json.loads(keywords),
            abstract=abstract,
            downloadUrl=download_url,
            doi=doi,
            created_at=generate_random_date(),
            updated_at=timezone.now()
        )
        papers.append(paper)
        
    print(f"Created {len(papers)} papers")
    return papers

def create_datasets(num_datasets=10):
    """Create sample datasets in the database"""
    print(f"Creating {num_datasets} datasets...")
    datasets = []
    
    for i in range(num_datasets):
        name = random.choice(dataset_names) if i < len(dataset_names) else f"Dataset {i+1}"
        description = f"A comprehensive dataset for {random.choice(fields)} research."
        data_type = random.choice(dataset_categories)
        size = f"{random.randint(1, 100)}GB, {random.randint(10000, 1000000)} samples"
        format = random.choice(["JSON", "CSV", "Images", "Audio", "Text", "Videos", "Graphs"])
        source_url = f"https://example.com/datasets/{uuid.uuid4()}"
        license = random.choice(["MIT", "Apache 2.0", "CC BY-NC", "CC BY", "CC BY-SA"])
        citation = f"Dataset Citation {i}"
        
        # Create dataset
        dataset = Dataset.objects.create(
            id=uuid.uuid4(),
            name=name,
            description=description,
            data_type=data_type,
            size=size,
            format=format,
            source_url=source_url,
            license=license,
            citation=citation,
            created_at=generate_random_date(),
            updated_at=timezone.now()
        )
        datasets.append(dataset)
    
    print(f"Created {len(datasets)} datasets")
    return datasets

def link_papers_to_datasets(papers, datasets, num_links=30):
    """Link papers to datasets"""
    print(f"Creating {num_links} paper-dataset associations...")
    
    for _ in range(min(num_links, len(papers) * len(datasets))):
        paper = random.choice(papers)
        dataset = random.choice(datasets)
        
        # Add dataset to paper's datasets
        paper.datasets.add(dataset)
    
    print(f"Created paper-dataset associations")

def create_interesting_papers(users, papers, num_interests=15):
    """Mark some papers as interesting for users"""
    print(f"Creating {num_interests} interesting paper records...")
    
    for _ in range(min(num_interests, len(users) * len(papers))):
        user = random.choice(users)
        paper = random.choice(papers)
        
        # Create interesting paper record if it doesn't exist
        if not InterestingPaper.objects.filter(user=user, paper=paper).exists():
            InterestingPaper.objects.create(
                user=user,
                paper=paper,
                created_at=timezone.now()
            )
    
    print(f"Created interesting paper records")

def main():
    """Hàm chính để tạo tất cả dữ liệu mẫu"""
    print("==== Creating Mock Data ====")
    
    print("\n--- Getting/Creating Users ---")
    users = get_or_create_users(num_users=10)
    
    print("\n--- Creating Papers ---")
    papers = create_papers(num_papers=20)
    
    print("\n--- Creating Datasets ---")
    datasets = create_datasets(num_datasets=10)
    
    print("\n--- Linking Papers to Datasets ---")
    link_papers_to_datasets(papers, datasets, num_links=30)
    
    print("\n--- Adding Interesting Papers ---")
    create_interesting_papers(users, papers, num_interests=15)
    
    print("\n==== Mock Data Creation Complete ====")

if __name__ == "__main__":
    main() 
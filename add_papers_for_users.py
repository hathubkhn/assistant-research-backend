#!/usr/bin/env python
import os
import django
import random
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')
django.setup()

from django.contrib.auth.models import User
from public_api.models import Paper, InterestingPaper, Profile

# Sample papers data with various keywords
PAPERS_DATA = [
    # AI and Machine Learning papers
    {
        "title": "Deep Learning for Natural Language Processing",
        "authors": ["John Smith", "Maria Johnson"],
        "abstract": "This paper explores deep learning techniques for natural language processing tasks.",
        "year": 2022,
        "conference": "International Conference on Machine Learning",
        "field": "Artificial Intelligence",
        "keywords": ["deep learning", "nlp", "transformers", "language models", "machine learning"],
        "downloadUrl": "https://example.com/papers/dl-nlp.pdf",
    },
    {
        "title": "Transformer Models for Language Understanding",
        "authors": ["Alex Brown", "Sarah Davis"],
        "abstract": "An overview of transformer architecture and its applications in language understanding.",
        "year": 2021,
        "conference": "Conference on Neural Information Processing Systems",
        "field": "Artificial Intelligence",
        "keywords": ["transformers", "attention mechanism", "nlp", "machine learning"],
        "downloadUrl": "https://example.com/papers/transformers.pdf",
    },
    {
        "title": "Reinforcement Learning in Robotics",
        "authors": ["David Wilson", "Emma Miller"],
        "abstract": "This paper presents advances in reinforcement learning for robotic control systems.",
        "year": 2023,
        "conference": "IEEE Conference on Robotics and Automation",
        "field": "Robotics",
        "keywords": ["reinforcement learning", "robotics", "machine learning", "control systems"],
        "downloadUrl": "https://example.com/papers/rl-robotics.pdf",
    },
    
    # Computer Vision papers
    {
        "title": "Convolutional Neural Networks for Image Classification",
        "authors": ["Michael Chen", "Jennifer Wang"],
        "abstract": "A comprehensive study of CNN architectures for image classification tasks.",
        "year": 2022,
        "conference": "Computer Vision and Pattern Recognition",
        "field": "Computer Vision",
        "keywords": ["cnn", "computer vision", "image classification", "deep learning"],
        "downloadUrl": "https://example.com/papers/cnn-classification.pdf",
    },
    {
        "title": "Object Detection with YOLO Architecture",
        "authors": ["Robert Taylor", "Lisa Anderson"],
        "abstract": "This paper examines the YOLO architecture for real-time object detection.",
        "year": 2021,
        "conference": "European Conference on Computer Vision",
        "field": "Computer Vision",
        "keywords": ["object detection", "yolo", "computer vision", "real-time detection"],
        "downloadUrl": "https://example.com/papers/yolo-detection.pdf",
    },
    
    # Data Science papers
    {
        "title": "Data Mining Techniques for Big Data Analysis",
        "authors": ["James Wilson", "Patricia Moore"],
        "abstract": "This paper explores efficient data mining algorithms for big data analytics.",
        "year": 2023,
        "conference": "International Conference on Data Mining",
        "field": "Data Science",
        "keywords": ["data mining", "big data", "algorithms", "data science"],
        "downloadUrl": "https://example.com/papers/data-mining.pdf",
    },
    {
        "title": "Statistical Methods in Data Analysis",
        "authors": ["Thomas Garcia", "Nancy Martin"],
        "abstract": "A review of statistical methods used in modern data analysis.",
        "year": 2022,
        "conference": "Statistical Computing Conference",
        "field": "Data Science",
        "keywords": ["statistics", "data analysis", "regression", "data science"],
        "downloadUrl": "https://example.com/papers/statistical-methods.pdf",
    },
    
    # Cybersecurity papers
    {
        "title": "Network Security in Cloud Computing",
        "authors": ["Daniel White", "Karen Lewis"],
        "abstract": "This paper discusses security challenges and solutions in cloud computing environments.",
        "year": 2023,
        "conference": "IEEE Symposium on Security and Privacy",
        "field": "Cybersecurity",
        "keywords": ["network security", "cloud computing", "cybersecurity", "threat detection"],
        "downloadUrl": "https://example.com/papers/cloud-security.pdf",
    },
    {
        "title": "Blockchain Technology for Secure Transactions",
        "authors": ["Christopher Adams", "Michelle Harris"],
        "abstract": "An analysis of blockchain technology for secure and transparent transactions.",
        "year": 2022,
        "conference": "International Conference on Blockchain",
        "field": "Cybersecurity",
        "keywords": ["blockchain", "cryptography", "secure transactions", "cybersecurity"],
        "downloadUrl": "https://example.com/papers/blockchain.pdf",
    },
    
    # Software Engineering papers
    {
        "title": "Agile Development Methodologies",
        "authors": ["Stephen Turner", "Rachel Scott"],
        "abstract": "This paper evaluates agile development methodologies in modern software projects.",
        "year": 2023,
        "conference": "International Conference on Software Engineering",
        "field": "Software Engineering",
        "keywords": ["agile", "software development", "project management", "scrum"],
        "downloadUrl": "https://example.com/papers/agile-methods.pdf",
    },
    {
        "title": "Microservices Architecture Patterns",
        "authors": ["Kevin Young", "Laura Baker"],
        "abstract": "A study of design patterns and best practices in microservices architecture.",
        "year": 2022,
        "conference": "IEEE Software Architecture Conference",
        "field": "Software Engineering",
        "keywords": ["microservices", "software architecture", "design patterns", "distributed systems"],
        "downloadUrl": "https://example.com/papers/microservices.pdf",
    }
]

def add_papers_to_user(user, papers_data, num_papers=5, common_keywords_count=3):
    """
    Add papers to a user's favorites with some papers sharing keywords
    
    Args:
        user: Django User object
        papers_data: List of paper data dictionaries
        num_papers: Number of papers to add (default: 5)
        common_keywords_count: Number of papers that should share keywords (default: 3)
    """
    if num_papers > len(papers_data):
        num_papers = len(papers_data)
    
    # Sample random papers from the list without replacement
    selected_papers_data = random.sample(papers_data, num_papers)
    
    # Get user's profile for reference
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        print(f"No profile found for user {user.username}. Creating one...")
        # Create a basic profile if it doesn't exist
        profile = Profile.objects.create(
            user=user,
            research_interests="machine learning, artificial intelligence",
            additional_keywords="computer science, deep learning"
        )
    
    # Extract keywords from user profile
    user_keywords = []
    if profile.research_interests:
        user_keywords += [k.strip() for k in profile.research_interests.split(',') if k.strip()]
    if profile.additional_keywords:
        user_keywords += [k.strip() for k in profile.additional_keywords.split(',') if k.strip()]
    
    created_papers = []
    for i, paper_data in enumerate(selected_papers_data):
        # For the first 'common_keywords_count' papers, ensure they share some keywords with the user
        if i < common_keywords_count and user_keywords:
            # Add some of the user's keywords to ensure recommendation will work
            shared_keywords = random.sample(user_keywords, min(2, len(user_keywords)))
            paper_data["keywords"] = list(set(paper_data["keywords"] + shared_keywords))
        
        # Check if this paper already exists (based on title and authors)
        existing_paper = Paper.objects.filter(title=paper_data["title"]).first()
        
        if existing_paper:
            paper = existing_paper
        else:
            # Create a new paper
            paper = Paper.objects.create(
                title=paper_data["title"],
                authors=paper_data["authors"],
                abstract=paper_data["abstract"],
                year=paper_data["year"],
                conference=paper_data["conference"],
                field=paper_data["field"],
                keywords=paper_data["keywords"],
                downloadUrl=paper_data["downloadUrl"],
                created_at=datetime.now()
            )
        
        created_papers.append(paper)
        
        # Mark the paper as interesting for this user
        InterestingPaper.objects.get_or_create(user=user, paper=paper)
    
    return created_papers

def main():
    # Get all users
    users = User.objects.all()
    
    if not users.exists():
        print("No users found in the database. Please create some users first.")
        return
    
    print(f"Adding papers to {users.count()} users...")
    
    for user in users:
        papers = add_papers_to_user(user, PAPERS_DATA)
        print(f"Added {len(papers)} papers to user {user.username}")
        
        # Print the first few keywords of added papers to confirm common keywords
        print("Papers keywords:")
        for paper in papers:
            print(f"  - {paper.title}: {', '.join(paper.keywords[:3])}{'...' if len(paper.keywords) > 3 else ''}")
    
    print("Done!")

if __name__ == "__main__":
    main() 
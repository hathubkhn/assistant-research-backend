import json
import traceback
from datetime import datetime, timedelta
from django.db.models import Q, Sum, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.base import ContentFile
import uuid
import random
import math

from .authentication import AllowAnyAuthentication
from .models import Paper, Dataset, InterestingPaper, Profile, Publication, DownloadedPaper, InterestingDataset, Journal, Conference
from .serializers import (ProfileSerializer, PublicationSerializer, PaperDetailSerializer, 
                          PaperSerializer, DatasetSerializer, PaperListSerializer)
from rest_framework.authtoken.models import Token
from django.core.paginator import Paginator
import requests
import os
from django.core.files.storage import default_storage

User = get_user_model()

@api_view(['GET'])
@permission_classes([AllowAny])
def papers_list(request):
    """
    Get a list of all papers with pagination
    """
    try:
        # Get query parameters
        year = request.query_params.get('year')
        venue = request.query_params.get('venue')
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')
        
        # Pagination parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 20))

        # Build filter criteria
        filter_criteria = {}
        if year:
            filter_criteria['publication_date__year'] = int(year)
        if venue:
            filter_criteria['journal_or_conference'] = venue

        # Add date filtering if provided
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                filter_criteria['crawled_at__gte'] = start_date
            except ValueError:
                pass
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                filter_criteria['crawled_at__lte'] = end_date
            except ValueError:
                pass

        # Query the database
        papers = Paper.objects.filter(**filter_criteria)
        
        # Apply pagination
        paginator = Paginator(papers, page_size)
        paginated_papers = paginator.page(page)
        
        serializer = PaperListSerializer(paginated_papers, many=True)
        result = serializer.data
        
        # Create response with pagination metadata
        response_data = {
            "results": result,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalItems": paginator.count,
                "totalPages": paginator.num_pages
            }
        }
            
        return Response(response_data)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def paper_detail(request, paper_id):
    """
    Get details for a specific paper by ID
    """
    try:
        paper = get_object_or_404(Paper, id=paper_id)
        
        # Process authors field - ensure it's a list 
        if not paper.authors or not isinstance(paper.authors, (list, tuple)):
            try:
                if isinstance(paper.authors, str):
                    if paper.authors.strip():
                        try:
                            # Try to parse as JSON
                            authors = json.loads(paper.authors)
                        except json.JSONDecodeError:
                            # If regular string, split by commas
                            if ',' in paper.authors:
                                authors = [name.strip() for name in paper.authors.split(',')]
                            else:
                                authors = [paper.authors]
                    else:
                        authors = ["Unknown"]
                else:
                    authors = ["Unknown"]
            except Exception:
                authors = ["Unknown"]
        else:
            authors = paper.authors
            
        # Ensure authors is not empty
        if not authors:
            authors = ["Unknown"]
            
        # Process keywords field - ensure it's a list
        if not paper.keywords or not isinstance(paper.keywords, (list, tuple)):
            try:
                if isinstance(paper.keywords, str):
                    if paper.keywords.strip():
                        try:
                            # Try to parse as JSON
                            keywords = json.loads(paper.keywords)
                        except json.JSONDecodeError:
                            # If regular string, split by commas
                            if ',' in paper.keywords:
                                keywords = [kw.strip() for kw in paper.keywords.split(',')]
                            else:
                                keywords = [paper.keywords]
                    else:
                        keywords = []
                else:
                    keywords = []
            except Exception:
                keywords = []
        else:
            keywords = paper.keywords
        
        # Get citation data
        citations_by_year = list(paper.citations.all().values('year', 'count'))
        
        # Get venue name and type from the model properties
        venue_type = paper.venue_type
        venue_name = paper.venue_name
        
        # Construct the response manually
        response_data = {
            "id": str(paper.id),
            "title": paper.title,
            "authors": authors,
            "venue": venue_name,
            "venueType": venue_type,
            "year": paper.year,
            "field": paper.field,
            "keywords": keywords,
            "abstract": paper.abstract,
            "downloadUrl": paper.downloadUrl,
            "citationsByYear": citations_by_year,
        }
        
        # Add optional fields if they exist
        if paper.doi:
            response_data["doi"] = paper.doi
        if paper.method:
            response_data["method"] = paper.method
        if paper.results:
            response_data["results"] = paper.results
        if paper.conclusions:
            response_data["conclusions"] = paper.conclusions
        if paper.bibtex:
            response_data["bibtex"] = paper.bibtex
        if paper.sourceCode:
            response_data["sourceCode"] = paper.sourceCode
            
        # Add journal specific information
        if venue_type == 'journal' and paper.journal:
            response_data["impactFactor"] = paper.journal.impact_factor
            response_data["quartile"] = paper.journal.quartile
        elif venue_type == 'journal':
            # Fallback for legacy data
            journal_info = {
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
            
            if paper.conference in journal_info:
                info = journal_info[paper.conference]
                response_data["impactFactor"] = info["impactFactor"]
                response_data["quartile"] = info["quartile"]
                
        # Add conference information if available
        if venue_type == 'conference' and paper.conference_venue:
            response_data["conferenceRank"] = paper.conference_venue.rank
            response_data["conferenceAbbreviation"] = paper.conference_venue.abbreviation
                
        # Add dataset information
        if hasattr(paper, 'datasets') and paper.datasets.exists():
            datasets = []
            for dataset in paper.datasets.all():
                datasets.append({
                    "id": str(dataset.id),
                    "name": dataset.name,
                    "abbreviation": dataset.name[:10].upper() if len(dataset.name) > 10 else dataset.name.upper(),
                    "description": dataset.description,
                    "data_type": dataset.data_type,
                    "category": dataset.data_type,
                    "size": dataset.size,
                    "format": dataset.format,
                    "source_url": dataset.source_url,
                    "license": dataset.license
                })
            response_data["datasets"] = datasets
            
        return Response(response_data)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def paper_by_slug(request, slug):
    """
    Get a paper by its title slug
    """
    try:
        try:
            paper_id = uuid.UUID(slug)
            paper = Paper.objects.filter(id=paper_id).first()
        except ValueError:
            title_words = slug.split('-')
            queryset = Paper.objects.all()
            title_words = [word for word in title_words if len(word) > 2]
            for word in title_words:
                queryset = queryset.filter(title__icontains=word)
            paper = queryset.first()
        
        if not paper:
            return Response({"error": "Paper not found"}, status=404)
        
        serializer = PaperDetailSerializer(paper)
        response_data = serializer.data     
        return Response(response_data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def datasets_list(request):
    """
    Get a list of all datasets with pagination
    """
    try:
        # Get query parameters
        category = request.query_params.get('category')
        language = request.query_params.get('language')
        search = request.query_params.get('search')
        
        # Pagination parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 20))
        
        # Use Dataset model from public_api.models
        datasets = Dataset.objects.all()
        
        # Apply filters if provided
        if category:
            datasets = datasets.filter(data_type__icontains=category)
        if language:
            datasets = datasets.filter(name__icontains=language)
            
        # Apply search filter if provided
        if search:
            datasets = datasets.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search)
            )
        
        # Count total items before pagination
        total_count = datasets.count()
        
        # Apply pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_datasets = datasets[start_index:end_index]
        
        result = []
        for dataset in paginated_datasets:
            # Process tasks properly
            tasks = []
            if dataset.tasks:
                if isinstance(dataset.tasks, list):
                    tasks = dataset.tasks
                elif isinstance(dataset.tasks, str):
                    try:
                        tasks = json.loads(dataset.tasks)
                    except:
                        tasks = [dataset.tasks]
            
            # Process benchmarks properly
            benchmarks = []
            if dataset.benchmarks:
                if isinstance(dataset.benchmarks, list):
                    benchmarks = dataset.benchmarks
                elif isinstance(dataset.benchmarks, int):
                    benchmarks = [{"placeholder": True} for _ in range(dataset.benchmarks)]
                elif isinstance(dataset.benchmarks, str):
                    try:
                        benchmarks = json.loads(dataset.benchmarks)
                    except:
                        # If it's a number in string format
                        try:
                            benchmark_count = int(dataset.benchmarks)
                            benchmarks = [{"placeholder": True} for _ in range(benchmark_count)]
                        except:
                            benchmarks = []
            
            # Generate proper abbreviation
            abbreviation = dataset.abbreviation
            if not abbreviation or abbreviation == dataset.name:
                if len(dataset.name.split()) > 1:
                    # Try to create abbreviation from first letters of words
                    words = dataset.name.split()
                    abbreviation = ''.join(word[0] for word in words if word[0].isalpha()).upper()
                else:
                    abbreviation = dataset.name[:5].upper()
            
            # Get the actual count of related papers from the ManyToMany relationship
            paper_count = dataset.papers.count()
            
            dataset_data = {
                "id": str(dataset.id),
                "name": dataset.name,
                "abbreviation": abbreviation,
                "description": dataset.description,
                "downloadUrl": dataset.source_url,
                "language": dataset.language if dataset.language else "English",
                "category": dataset.data_type or "Unknown",
                "tasks": tasks,
                "paperCount": paper_count,
                "benchmarks": benchmarks
            }
                
            result.append(dataset_data)
            
        # Create response with pagination metadata
        response_data = {
            "results": result,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalItems": total_count,
                "totalPages": (total_count + page_size - 1) // page_size
            }
        }
        
        return Response(response_data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
        
@api_view(['GET'])
@permission_classes([AllowAny])
def dataset_detail(request, dataset_id):
    """
    Get details for a specific dataset
    """
    try:
        # Use Dataset model from public_api.models
        dataset = get_object_or_404(Dataset, id=dataset_id)
        
        # Process tasks properly
        tasks = []
        if dataset.tasks:
            if isinstance(dataset.tasks, list):
                tasks = dataset.tasks
            elif isinstance(dataset.tasks, str):
                try:
                    tasks = json.loads(dataset.tasks)
                except:
                    tasks = [dataset.tasks]
        
        # Process benchmarks properly
        benchmarks = []
        if dataset.benchmarks:
            if isinstance(dataset.benchmarks, list):
                benchmarks = dataset.benchmarks
            elif isinstance(dataset.benchmarks, int):
                benchmarks = [{"placeholder": True} for _ in range(dataset.benchmarks)]
            elif isinstance(dataset.benchmarks, str):
                try:
                    benchmarks = json.loads(dataset.benchmarks)
                except:
                    # If it's a number in string format
                    try:
                        benchmark_count = int(dataset.benchmarks)
                        benchmarks = [{"placeholder": True} for _ in range(benchmark_count)]
                    except:
                        benchmarks = []
        
        # Generate proper abbreviation
        abbreviation = dataset.abbreviation
        if not abbreviation or abbreviation == dataset.name:
            if len(dataset.name.split()) > 1:
                # Try to create abbreviation from first letters of words
                words = dataset.name.split()
                abbreviation = ''.join(word[0] for word in words if word[0].isalpha()).upper()
            else:
                abbreviation = dataset.name[:5].upper()
            
        dataset_data = {
            "id": str(dataset.id),
            "name": dataset.name,
            "abbreviation": abbreviation,
            "description": dataset.description,
            "downloadUrl": dataset.source_url,
            "language": dataset.language if dataset.language else "English",
            "category": dataset.data_type or "Unknown",
            "tasks": tasks,
            "paperCount": dataset.papers.count(),
            "benchmarks": benchmarks,
            "link": dataset.link if dataset.link else None,
            "paper_link": dataset.paper_link if dataset.paper_link else None,
            "subtitle": dataset.subtitle if dataset.subtitle else None,
            "thumbnailUrl": dataset.thumbnailUrl if dataset.thumbnailUrl else None,
            "dataloaders": dataset.dataloaders if dataset.dataloaders else [],
            "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
            "updated_at": dataset.updated_at.isoformat() if dataset.updated_at else None,
            "isStarred": False  # Default value, will update below if user is authenticated
        }
            
        # Check if the dataset is starred by the current user
        if request.user.is_authenticated:
            try:
                is_starred = InterestingDataset.objects.filter(user=request.user, dataset=dataset).exists()
                dataset_data["isStarred"] = is_starred
            except Exception as e:
                print(f"Error checking if dataset is starred: {str(e)}")
            
        # Get related papers from the many-to-many relationship
        related_papers = []
        if hasattr(dataset, 'papers'):
            papers = dataset.papers.all().order_by('-year')
            for paper in papers:
                # Extract and parse author data safely
                try:
                    authors = paper.authors
                    if isinstance(authors, str):
                        try:
                            authors = json.loads(authors)
                        except:
                            authors = [authors]
                except Exception as e:
                    authors = ["Unknown"]
                    
                # Extract and parse keywords safely
                try:
                    keywords = paper.keywords
                    if isinstance(keywords, str):
                        try:
                            keywords = json.loads(keywords)
                        except:
                            keywords = []
                except Exception as e:
                    keywords = []
                
                # Get venue information
                venue_type = paper.venue_type if hasattr(paper, 'venue_type') else "conference"
                venue_name = paper.venue_name if hasattr(paper, 'venue_name') else paper.conference
                
                # Build paper data with more detailed information
                paper_data = {
                    "id": str(paper.id),
                    "title": paper.title,
                    "authors": authors,
                    "abstract": paper.abstract,
                    "conference": venue_name,
                    "year": paper.year,
                    "field": paper.field,
                    "venue_type": venue_type,
                    "keywords": keywords,
                    "downloadUrl": paper.downloadUrl if paper.downloadUrl else None,
                    "doi": paper.doi if paper.doi else None
                }
                
                related_papers.append(paper_data)
        
        # Get similar datasets from the DatasetSimilarDataset model
        similar_datasets = []
        
        # Get similar datasets from the DatasetSimilarDataset relation table
        from public_api.models import DatasetSimilarDataset
        similar_relations = DatasetSimilarDataset.objects.filter(from_dataset=dataset)
        
        for relation in similar_relations:
            similar = relation.to_dataset
            
            # Get the actual count of related papers from the ManyToMany relationship
            similar_paper_count = similar.papers.count()
            
            similar_data = {
                "id": str(similar.id),
                "name": similar.name,
                "abbreviation": similar.abbreviation if similar.abbreviation else similar.name[:10],
                "description": similar.description,
                "downloadUrl": similar.source_url,
                "language": similar.language if similar.language else "English",
                "category": similar.data_type or "Unknown",
                "tasks": similar.tasks if similar.tasks else [],
                "paperCount": similar_paper_count,
                "benchmarks": similar.benchmarks if similar.benchmarks else []
            }
            similar_datasets.append(similar_data)
                
        # Structure the complete response
        result = {
            "dataset": dataset_data,
            "relatedPapers": related_papers,
            "similarDatasets": similar_datasets
        }
            
        return Response(result)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def interesting_papers(request):
    """
    Get papers marked as interesting by the authenticated user
    """
    try:
        user = request.user
        interesting = InterestingPaper.objects.filter(user=user)
        
        # Extract paper IDs
        paper_ids = [item.paper.id for item in interesting]
        
        # Get actual paper objects
        papers = Paper.objects.filter(id__in=paper_ids)
        
        serializer = PaperSerializer(papers, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_paper_interesting(request, paper_id):
    """
    Mark a paper as interesting for the authenticated user
    """
    try:
        user = request.user
        
        # Check if paper exists
        paper = get_object_or_404(Paper, id=paper_id)
        
        # Create or update interesting paper entry
        interesting, created = InterestingPaper.objects.get_or_create(
            user=user,
            paper=paper
        )
        
        return Response({
            "message": "Paper marked as interesting",
            "created": created
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def unmark_paper_interesting(request, paper_id):
    """
    Remove a paper from user's interesting list
    """
    try:
        user = request.user
        
        # Try to find and delete the entry
        try:
            interesting = InterestingPaper.objects.get(user=user, paper__id=paper_id)
            interesting.delete()
            return Response({"message": "Paper removed from interesting"}, status=status.HTTP_200_OK)
        except InterestingPaper.DoesNotExist:
            return Response({"error": "Paper was not marked as interesting"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([AllowAnyAuthentication])
def search(request):
    """
    Search papers, datasets, etc. based on a query string with pagination
    """
    try:
        query = request.query_params.get('q', '')
        if not query or len(query.strip()) < 2:
            return Response({"error": "Search query must be at least 2 characters"}, status=400)
        
        # Pagination parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 10))
        
        # Search papers
        papers_query = Paper.objects.filter(
            Q(title__icontains=query) | 
            Q(authors__icontains=query) | 
            Q(abstract__icontains=query) |
            Q(keywords__icontains=query)
        )
        
        # Search datasets using Dataset model
        datasets_query = Dataset.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )
        
        # Count total items
        total_papers = papers_query.count()
        total_datasets = datasets_query.count()
        
        # Apply pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        papers = papers_query[start_index:end_index]
        datasets = datasets_query[start_index:end_index]
        
        # Format results
        results = {
            "papers": [],
            "datasets": []
        }
        
        # Add papers to results
        for paper in papers:
            try:
                authors = json.loads(paper.authors) if paper.authors else ["Unknown"]
                if isinstance(authors, list) and len(authors) > 3:
                    authors = authors[:3] + ["et al."]
            except:
                authors = ["Unknown"]
                
            results["papers"].append({
                "id": str(paper.id),
                "title": paper.title,
                "authors": authors,
                "year": paper.year,
                "abstract": paper.abstract[:200] + "..." if len(paper.abstract) > 200 else paper.abstract,
                "venue": paper.conference
            })
            
        # Add datasets to results
        for dataset in datasets:
            results["datasets"].append({
                "id": str(dataset.id),
                "name": dataset.name,
                "description": dataset.description[:200] + "..." if len(dataset.description) > 200 else dataset.description,
                "category": dataset.data_type or "Unknown",
                "papers_count": dataset.papers.count()
            })
            
        # Create response with pagination metadata
        response_data = {
            "results": results,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalPapers": total_papers,
                "totalDatasets": total_datasets,
                "totalItems": total_papers + total_datasets,
                "totalPages": max(
                    (total_papers + page_size - 1) // page_size,
                    (total_datasets + page_size - 1) // page_size
                )
            }
        }
            
        return Response(response_data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    """
    Get or update the profile of the authenticated user
    """
    try:
        # Get the user profile from the public_api Profile model
        profile, created = Profile.objects.get_or_create(user=request.user)
        
        if request.method == 'GET':
            serializer = ProfileSerializer(profile)
            # Get the serialized profile data
            data = serializer.data
            
            # Fetch and add the user's publications to the response
            user_publications = Publication.objects.filter(user=request.user)
            publications_serializer = PublicationSerializer(user_publications, many=True)
            data['publications'] = publications_serializer.data
            
            # Convert research_interests to keywords for backward compatibility
            if 'research_interests' in data and 'keywords' not in data:
                data['keywords'] = data['research_interests']
            
            return Response(data)
        
        elif request.method == 'PUT':
            # Use serializer to update the profile
            serializer = ProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                
                # Mark profile as completed if required fields are filled
                if not profile.is_profile_completed:
                    required_fields = ['full_name', 'faculty_institute', 'position', 'research_interests']
                    is_complete = all(getattr(profile, field, None) for field in required_fields)
                    if is_complete:
                        profile.is_profile_completed = True
                        profile.save()
                
                # Get updated data with publications
                updated_data = serializer.data
                user_publications = Publication.objects.filter(user=request.user)
                publications_serializer = PublicationSerializer(user_publications, many=True)
                updated_data['publications'] = publications_serializer.data
                
                # Convert research_interests to keywords for backward compatibility
                if 'research_interests' in updated_data and 'keywords' not in updated_data:
                    updated_data['keywords'] = updated_data['research_interests']
                
                return Response(updated_data)
            return Response(serializer.errors, status=400)
            
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Update the profile of the authenticated user
    """
    try:
        # Get public_api Profile
        profile, created = Profile.objects.get_or_create(user=request.user)
        
        # Use serializer to update the profile
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Mark profile as completed if required fields are filled
            if not profile.is_profile_completed:
                required_fields = ['full_name', 'faculty_institute', 'position', 'research_interests']
                is_complete = all(getattr(profile, field, None) for field in required_fields)
                if is_complete:
                    profile.is_profile_completed = True
                    profile.save()
            
            # Get updated data with publications
            updated_data = serializer.data
            user_publications = Publication.objects.filter(user=request.user)
            publications_serializer = PublicationSerializer(user_publications, many=True)
            updated_data['publications'] = publications_serializer.data
            
            # Convert research_interests to keywords for backward compatibility
            if 'research_interests' in updated_data and 'keywords' not in updated_data:
                updated_data['keywords'] = updated_data['research_interests']
            
            return Response(updated_data)
        return Response(serializer.errors, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def publications_list(request):
    """
    Get publications for the authenticated user
    """
    try:
        user = request.user
        publications = Publication.objects.filter(user=user)
        serializer = PublicationSerializer(publications, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_publication(request):
    """
    Create a new publication for the authenticated user
    """
    try:
        user = request.user
        data = request.data.copy()
        data['user'] = user.id
        
        serializer = PublicationSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def publication_detail(request, publication_id):
    """
    Retrieve, update or delete a publication
    """
    try:
        user = request.user
        
        # Debug info
        print(f"[DEBUG] Publication detail view called")
        print(f"[DEBUG] Request path: {request.path}")
        print(f"[DEBUG] Request method: {request.method}")
        print(f"[DEBUG] User: {user.username} (ID: {user.id})")
        print(f"[DEBUG] Publication model being used: {Publication.__module__}.{Publication.__name__}")
        print(f"[DEBUG] Publication ID type: {type(publication_id)}")
        print(f"[DEBUG] Searching for publication with ID: {publication_id}")
        
        try:
            # Convert UUID from string to UUID object if needed
            if isinstance(publication_id, str):
                try:
                    publication_id = uuid.UUID(publication_id)
                except ValueError:
                    pass
                    
            publication = Publication.objects.get(id=publication_id, user=user)
            print(f"[DEBUG] Found publication: {publication.id}, title: {publication.title}")
        except Publication.DoesNotExist:
            # Log the error for debugging
            print(f"[DEBUG] Publication not found: {publication_id}, user: {user.id}")
            print(f"[DEBUG] All publications for user: {[str(p.id) for p in Publication.objects.filter(user=user)]}")
            return Response({"error": "Publication not found"}, status=status.HTTP_404_NOT_FOUND)
            
        if request.method == 'GET':
            serializer = PublicationSerializer(publication)
            return Response(serializer.data)
            
        elif request.method == 'PUT':
            data = request.data.copy()
            data['user'] = user.id
            
            serializer = PublicationSerializer(publication, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == 'DELETE':
            print(f"[DEBUG] Deleting publication with ID: {publication.id}")
            publication.delete()
            return Response({"message": "Publication deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
            
    except Exception as e:
        print(f"[DEBUG] Error in publication_detail: {str(e)}")
        print(traceback.format_exc())
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def stats(request):
    """
    Get general statistics
    """
    try:
        # Count total papers
        total_papers = Paper.objects.count()
        
        # Count papers in the current month
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        papers_this_month = Paper.objects.filter(created_at__gte=current_month_start).count()
        
        # Calculate total and average citations
        citations_data = Paper.objects.aggregate(
            total_citations=Sum('citations'),
            avg_citations=Avg('citations')
        )
        total_citations = citations_data['total_citations'] or 0
        avg_citations = citations_data['avg_citations'] or 0
        
        # Return the statistics
        return Response({
            'totalPapers': total_papers,
            'papersThisMonth': papers_this_month,
            'totalCitations': total_citations,
            'averageCitations': round(float(avg_citations), 1)
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_stats(request):
    """
    Get dashboard statistics: monthly papers count, papers by category, 
    and most common keywords
    """
    try:
        # Get user for created_by filter if authenticated
        user = request.user if request.user.is_authenticated else None
        
        # Get date range parameters
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')
        
        # Build the where clause based on date range
        query_params = {}
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query_params['created_at__gte'] = start_date
            except ValueError:
                pass
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query_params['created_at__lte'] = end_date
            except ValueError:
                pass
        
        # Filter by created_by if authenticated user
        if user:
            query_params['created_by'] = user
            
        # Get all papers within date range (and created_by if authenticated)
        all_papers = Paper.objects.filter(**query_params)
        
        # For Papers Published by Month, only filter by created_by, not by date
        monthly_query = {}
        if user:
            monthly_query['created_by'] = user
            
        # For monthly papers, we need all papers by this user regardless of date filter
        monthly_papers_queryset = Paper.objects.filter(**monthly_query)
        
        # Count papers by month
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        monthly_papers_count = {month: 0 for month in month_names}
        
        for paper in monthly_papers_queryset:
            month_idx = paper.created_at.month - 1  # 0-based index
            month_name = month_names[month_idx]
            monthly_papers_count[month_name] += 1
        
        # Convert to array format for the frontend
        monthly_papers = [{'name': name, 'papers': count} for name, count in monthly_papers_count.items()]
        
        # Get papers by category (field) from the filtered papers (based on date and created_by)
        paper_fields = {}
        for paper in all_papers:
            fields = paper.field.split(',')
            for field in fields:
                field = field.strip()
                if field and field not in paper_fields:
                    paper_fields[field] = 0
                if field:
                    paper_fields[field] += 1
        
        # Convert to array format and sort by count
        category_data = [{'name': name, 'value': count} for name, count in paper_fields.items()]
        category_data.sort(key=lambda x: x['value'], reverse=True)
        category_data = category_data[:10]  # Top 10 categories
        
        # Get papers with their keywords from the filtered papers
        papers_with_keywords = all_papers.values('id', 'keywords')
        
        # Count occurrences of each keyword
        keyword_count = {}
        
        for index, paper in enumerate(papers_with_keywords):
            try:
                keywords_data = json.loads(paper['keywords'])
                if isinstance(keywords_data, list):
                    for keyword in keywords_data:
                        if keyword not in keyword_count:
                            keyword_count[keyword] = {'id': index * 100 + len(keyword_count), 'name': keyword, 'count': 0}
                        keyword_count[keyword]['count'] += 1
            except (json.JSONDecodeError, TypeError):
                # Try comma-separated format
                if paper['keywords'] and isinstance(paper['keywords'], str):
                    keywords = paper['keywords'].split(',')
                    for keyword in keywords:
                        keyword = keyword.strip()
                        if keyword:
                            if keyword not in keyword_count:
                                keyword_count[keyword] = {'id': index * 100 + len(keyword_count), 'name': keyword, 'count': 0}
                            keyword_count[keyword]['count'] += 1
        
        # Convert to array and sort by count
        keyword_sets = list(keyword_count.values())
        keyword_sets.sort(key=lambda x: x['count'], reverse=True)
        keyword_sets = keyword_sets[:10]  # Top 10 keywords
        
        return Response({
            'monthlyPapers': monthly_papers,
            'categoryData': category_data,
            'keywordSets': keyword_sets
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def papers_stats(request):
    """
    Get summary statistics for papers
    """
    try:
        # Get user for created_by filter if authenticated
        user = request.user if request.user.is_authenticated else None
        
        # Get date range parameters for citation calculation
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')
        
        # Build the query based on date range for citation calculation
        date_query_params = {}
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                date_query_params['created_at__gte'] = start_date
            except ValueError:
                pass
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                date_query_params['created_at__lte'] = end_date
            except ValueError:
                pass
            
        # Count total papers based on created_by if authenticated
        if user:
            # Filter by created_by for authenticated user
            total_papers = Paper.objects.filter(created_by=user).count()
        else:
            # Total count for all papers when not authenticated
            total_papers = Paper.objects.count()
        
        # Count papers in the current month based on created_by
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if user:
            papers_this_month = Paper.objects.filter(
                created_at__gte=current_month_start,
                created_by=user
            ).count()
        else:
            papers_this_month = Paper.objects.filter(created_at__gte=current_month_start).count()
        
        # Calculate total citations based on date filter
        citation_data = Paper.objects.filter(**date_query_params).aggregate(
            total_citations=Sum('citations'),
            avg_citations=Avg('citations')
        )
        total_citations = citation_data['total_citations'] or 0
        avg_citations = round(float(citation_data['avg_citations'] or 0), 1)
        
        return Response({
            'totalPapers': total_papers,
            'papersThisMonth': papers_this_month,
            'totalCitations': total_citations,
            'averageCitations': avg_citations
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def keywords_stats(request):
    """
    Get research interests statistics with optional date filtering
    
    This function is kept for backward compatibility, but it's recommended
    to use research_interests_stats instead.
    """
    # Convert the DRF Request back to HttpRequest before passing it
    return research_interests_stats(request._request)

@api_view(['GET'])
@permission_classes([AllowAny])
def research_interests_stats(request):
    """
    Get research interests statistics with optional date filtering
    """
    try:
        import traceback
        
        # Get user for created_by filter if authenticated
        user = request.user if request.user.is_authenticated else None
        
        # Get date range parameters
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')
        period = request.query_params.get('period', 'monthly')  # 'daily', 'monthly', 'yearly'
        
        # Build the query based on date range
        query_params = {}
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query_params['created_at__gte'] = start_date
            except ValueError:
                pass
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query_params['created_at__lte'] = end_date
            except ValueError:
                pass
            
        # Debugging log query
        print(f"research_interests_stats query_params: {query_params}")
            
        # Filter by created_by if authenticated user (and not anonymous)
        if user and not user.is_anonymous:
            query_params['created_by'] = user
        
        # Get papers with their keywords/research interests
        papers = Paper.objects.filter(**query_params).values('id', 'keywords', 'created_at')
        
        # Log count for debugging
        print(f"Found {papers.count()} papers for research interests stats")
        
        # Process research interests from all papers
        interests_counts = {}
        interests_by_period = {}
        
        for paper in papers:
            keywords_array = []
            try:
                if paper['keywords']:
                    if isinstance(paper['keywords'], list):
                        keywords_array = paper['keywords']
                    elif isinstance(paper['keywords'], str):
                        # Thử parse JSON nếu là string
                        try:
                            parsed_keywords = json.loads(paper['keywords'])
                            keywords_array = parsed_keywords if isinstance(parsed_keywords, list) else [paper['keywords']]
                        except json.JSONDecodeError:
                            # Nếu không phải JSON, xử lý như chuỗi thường
                            keywords_array = [k.strip() for k in paper['keywords'].split(',') if k.strip()]
                    else:
                        print(f"Unknown keywords type for paper {paper['id']}: {type(paper['keywords'])}")
                        continue
            except Exception as e:
                print(f"Error processing keywords for paper {paper['id']}: {str(e)}")
                traceback.print_exc()
                continue
            
            # Skip if no keywords
            if not keywords_array:
                continue
                
            # Log để debug
            if paper == papers[0]:
                print(f"First paper keywords: {keywords_array}")
                
            # Get period key based on paper's creation date
            date = paper['created_at']
            if period == 'daily':
                period_key = date.strftime('%Y-%m-%d')
            elif period == 'yearly':
                period_key = str(date.year)
            else:  # monthly (default)
                period_key = date.strftime('%Y-%m')
            
            # Initialize period data if not exists
            if period_key not in interests_by_period:
                interests_by_period[period_key] = {}
            
            # Count each keyword
            for keyword in keywords_array:
                # Skip empty keywords
                if not keyword or not isinstance(keyword, str):
                    continue
                    
                keyword = keyword.strip()
                if not keyword:
                    continue
                
                # Update overall count
                if keyword not in interests_counts:
                    interests_counts[keyword] = 0
                interests_counts[keyword] += 1
                
                # Update period count
                if keyword not in interests_by_period[period_key]:
                    interests_by_period[period_key][keyword] = 0
                interests_by_period[period_key][keyword] += 1
        
        # Format for response
        keywords_list = [{'name': k, 'count': v} for k, v in interests_counts.items()]
        keywords_list.sort(key=lambda x: x['count'], reverse=True)
        
        # If no keywords found but we have papers, try creating some mock data for testing
        if not interests_by_period and len(papers) > 0:
            print(f"No keywords found despite having {len(papers)} papers. Creating mock data.")
            # Using current period
            current_period = datetime.now().strftime('%Y-%m') if period == 'monthly' else datetime.now().strftime('%Y')
            interests_by_period[current_period] = {'AI': 10, 'Machine Learning': 8, 'Deep Learning': 6, 'NLP': 4, 'Computer Vision': 2}
        
        # Format period data - show only top-1 keyword for each period for trend analysis
        period_data = []
        for period_key, keywords in sorted(interests_by_period.items()):
            if keywords:
                # Get only top-1 keyword for this period
                top_keyword = max(keywords.items(), key=lambda x: x[1])
                period_item = {
                    'period': period_key,
                    'keywords': [{'name': top_keyword[0], 'count': top_keyword[1]}]
                }
                period_data.append(period_item)
        
        result = {
            'totalKeywords': len(interests_counts),
            'keywords': keywords_list[:20],  # Top 20 keywords
            'periodData': period_data
        }
        
        # Log the result size
        print(f"Returning {len(result['keywords'])} keywords and {len(result['periodData'])} periods")
        
        return Response(result)
    except Exception as e:
        traceback.print_exc()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def datasets_stats(request):
    """
    Get dataset statistics with optional date filtering
    """
    try:
        # Get user for created_by filter if authenticated
        user = request.user if request.user.is_authenticated else None
        
        # Get date range parameters
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')
        period = request.query_params.get('period', 'monthly')  # 'daily', 'monthly', 'yearly'
        
        # Build the query based on date range
        query_params = {}
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query_params['created_at__gte'] = start_date
            except ValueError:
                pass
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query_params['created_at__lte'] = end_date
            except ValueError:
                pass
                
        # Filter by created_by if authenticated user
        if user:
            query_params['created_by'] = user
        
        # Get all datasets using Dataset model
        datasets = Dataset.objects.all()
        
        # Get papers with dataset references
        papers = Paper.objects.filter(**query_params)
        
        # Count dataset usage
        dataset_counts = {}
        datasets_by_period = {}
        
        for dataset in datasets:
            dataset_name = dataset.name
            dataset_id = str(dataset.id)
            
            # Initialize counts
            dataset_counts[dataset_name] = 0
            
            # Filter papers that reference this dataset and match our query params
            related_papers = dataset.papers.filter(**query_params)
            paper_count = related_papers.count()
            
            if paper_count > 0:
                dataset_counts[dataset_name] = paper_count
                
                # For period tracking
                for paper in related_papers:
                    # Track by period
                    date = paper.created_at
                    if period == 'daily':
                        period_key = date.strftime('%Y-%m-%d')
                    elif period == 'yearly':
                        period_key = str(date.year)
                    else:  # monthly (default)
                        period_key = date.strftime('%Y-%m')
                    
                    if period_key not in datasets_by_period:
                        datasets_by_period[period_key] = {}
                    
                    if dataset_name not in datasets_by_period[period_key]:
                        datasets_by_period[period_key][dataset_name] = 0
                    
                    datasets_by_period[period_key][dataset_name] += 1
        
        # Format for response
        datasets_list = [{'name': k, 'count': v} for k, v in dataset_counts.items() if v > 0]
        datasets_list.sort(key=lambda x: x['count'], reverse=True)
        
        # Format period data
        period_data = []
        for period_key, period_datasets in sorted(datasets_by_period.items()):
            # Get top datasets for this period
            top_datasets = sorted(period_datasets.items(), key=lambda x: x[1], reverse=True)[:5]
            period_item = {
                'period': period_key,
                'datasets': [{'name': k, 'count': v} for k, v in top_datasets]
            }
            period_data.append(period_item)
        
        return Response({
            'totalDatasets': len([d for d in dataset_counts.values() if d > 0]),
            'datasets': datasets_list[:20],  # Top 20 datasets
            'periodData': period_data
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user
    """
    try:
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        
        # Check if required fields are provided
        if not username or not email or not password:
            return Response({"error": "Username, email, and password are required"}, status=400)
        
        # Check if user with the given username or email already exists
        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already exists"}, status=400)
        
        # Create the user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Create profile for the user (will be automatically created by signals)
        profile = Profile.objects.get_or_create(user=user)[0]
        
        # Generate token for the user
        token, _ = Token.objects.get_or_create(user=user)
        
        # Return success message and token
        return Response({
            "message": "User registered successfully",
            "token": token.key,
            "userId": user.id,
            "username": user.username,
            "email": user.email
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def token_login(request):
    """
    Login with username/email and password
    """
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        # Try to find user by username or email
        try:
            if '@' in username:
                user = User.objects.get(email=username)
            else:
                user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"non_field_errors": ["Invalid credentials"]}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check password
        if not user.check_password(password):
            return Response({"non_field_errors": ["Invalid credentials"]}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate token
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            "token": token.key,
            "user_id": user.id,
            "username": user.username,
            "email": user.email
        })
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def google_callback(request):
    """
    Handle Google OAuth callback
    
    When accessed from a private IP address, device_id and device_name parameters are required.
    """
    try:
        code = request.data.get('code')
        redirect_uri = request.data.get('redirect_uri')
        device_id = request.data.get('device_id')
        device_name = request.data.get('device_name')
        
        # Check if request is coming from a private IP
        client_ip = request.META.get('REMOTE_ADDR', '')
        is_private_ip = (
            client_ip.startswith('10.') or 
            client_ip.startswith('172.16.') or 
            client_ip.startswith('192.168.') or
            client_ip == '127.0.0.1'
        )
        
        # For private IP addresses, device_id and device_name are required
        if is_private_ip and (not device_id or not device_name):
            return Response(
                {"error": "invalid_request", "error_description": "device_id and device_name are required for private IP access"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not code:
            return Response({"detail": "Authorization code is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Exchange code for token (this is a simplified example)
        token_url = "https://oauth2.googleapis.com/token"
        client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
        client_secret = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET
        
        token_data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post(token_url, data=token_data)
        
        if token_response.status_code != 200:
            return Response({"detail": "Failed to exchange code for token"}, status=status.HTTP_400_BAD_REQUEST)
        
        token_json = token_response.json()
        access_token = token_json.get('access_token')
        
        # Get user info from Google
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        user_info_response = requests.get(user_info_url, headers={
            'Authorization': f'Bearer {access_token}'
        })
        
        if user_info_response.status_code != 200:
            return Response({"detail": "Failed to get user info"}, status=status.HTTP_400_BAD_REQUEST)
        
        user_info = user_info_response.json()
        email = user_info.get('email')
        
        if not email:
            return Response({"detail": "Email not provided by Google"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find or create user
        username = email.split('@')[0]
        user, created = User.objects.get_or_create(email=email, username=username)
        if created:
            Profile.objects.create(
                user=user,
                full_name=user_info.get('name', '')
            )
        # Generate token
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            "token": token.key,
            "user_id": user.id,
            "username": user.username,
            "email": user.email
        })
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def microsoft_callback(request):
    """
    Handle Microsoft OAuth code exchange and user creation/login.
    """
    try:
        code = request.data.get('code')
        redirect_uri = request.data.get('redirect_uri')
        device_id = request.data.get('device_id')
        device_name = request.data.get('device_name')
        
        # Check if request is coming from a private IP
        client_ip = request.META.get('REMOTE_ADDR', '')
        is_private_ip = (
            client_ip.startswith('10.') or 
            client_ip.startswith('172.16.') or 
            client_ip.startswith('192.168.') or
            client_ip == '127.0.0.1'
        )
        
        # For private IP addresses, device_id and device_name are required
        if is_private_ip and (not device_id or not device_name):
            return Response(
                {"error": "invalid_request", "error_description": "device_id and device_name are required for private IP access"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not code or not redirect_uri:
            return Response(
                {"error": "Missing code or redirect_uri parameter"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get OAuth credentials
        client_id = settings.SOCIAL_AUTH_MICROSOFT_OAUTH2_KEY
        client_secret = settings.SOCIAL_AUTH_MICROSOFT_OAUTH2_SECRET
        
        # Exchange code for token with Microsoft
        token_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }
        
        token_response = requests.post(token_url, data=token_data)
        if token_response.status_code != 200:
            return Response({"detail": "Failed to exchange code for token"}, status=status.HTTP_400_BAD_REQUEST)
        
        token_json = token_response.json()
        access_token = token_json.get('access_token')
        
        # Get user info from Microsoft Graph
        user_info_url = 'https://graph.microsoft.com/v1.0/me'
        user_info_response = requests.get(user_info_url, headers={
            'Authorization': f'Bearer {access_token}'
        })
        if user_info_response.status_code != 200:
            return Response({"detail": "Failed to get user info"}, status=status.HTTP_400_BAD_REQUEST)
        
        user_info = user_info_response.json()
        email = user_info.get('mail') or user_info.get('userPrincipalName')
        
        if not email:
            return Response({"error": "No email found in Microsoft user data"},status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user exists with this email
        username = email.split('@')[0]
        user, created = User.objects.get_or_create(email=email, username=username)
        if created:
            Profile.objects.create(
                user=user,
                full_name=user_info.get('name', '')
            )
        # Generate token
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user_id': user.id,
            'email': user.email,
            'username': user.username
        })
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Get login options
    """
    google_login_url = f"https://accounts.google.com/o/oauth2/auth"
    redirect_uri = f"{settings.API_URL}/sso-callback/google"
    
    client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
    
    google_login = f"{google_login_url}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=email%20profile&access_type=offline&prompt=consent"
    
    microsoft_login = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    
    return Response({
        "google_login": google_login,
        "microsoft_login": microsoft_login,
        "token_login": f"{settings.API_URL}/api/token-login/"
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_avatar(request):
    """
    Update user avatar
    """
    try:
        user = request.user
        
        # Get the uploaded file
        avatar_file = request.FILES.get('avatar')
        if not avatar_file:
            return Response({"error": "No file provided"}, status=400)
        
        # Check file size (limit to 5MB)
        if avatar_file.size > 5 * 1024 * 1024:
            return Response({"error": "File size exceeds 5MB limit"}, status=400)
        
        # Check file type
        if not avatar_file.content_type.startswith('image/'):
            return Response({"error": "File must be an image"}, status=400)
        
        # Generate a unique filename
        import uuid
        filename = f"avatar_{user.id}_{uuid.uuid4()}.jpg"
        
        # Save file to storage
        file_path = default_storage.save(f"avatars/{filename}", ContentFile(avatar_file.read()))
        
        # Generate public URL
        avatar_url = default_storage.url(file_path)
        
        # Update the avatar URL in Profile
        try:
            profile = Profile.objects.get(user=user)
            profile.avatar_url = avatar_url
            profile.save()
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=user, avatar_url=avatar_url)
        
        return Response({
            "avatar_url": avatar_url,
            "message": "Avatar updated successfully"
        })
        
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def seed_papers(request):
    """
    Seed the database with sample papers if none exist
    """
    try:
        # Check if papers already exist
        existing_papers = Paper.objects.count()
        if existing_papers > 0:
            return Response({"message": f"{existing_papers} papers already exist in the database"})
            
        # Create sample papers
        sample_papers = [
            {
                "title": "Attention Is All You Need",
                "authors": json.dumps(["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"]),
                "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
                "conference": "Neural Information Processing Systems",
                "year": 2017,
                "field": "Natural Language Processing",
                "keywords": json.dumps(["Transformer", "Attention", "NLP", "Deep Learning"]),
                "downloadUrl": "https://arxiv.org/pdf/1706.03762.pdf",
                "doi": "10.48550/arXiv.1706.03762",
                "bibtex": '@inproceedings{vaswani2017attention,\n  title={Attention is all you need},\n  author={Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and Uszkoreit, Jakob and Jones, Llion and Gomez, Aidan N and Kaiser, Lukasz and Polosukhin, Illia},\n  booktitle={Advances in neural information processing systems},\n  pages={5998--6008},\n  year={2017}\n}'
            },
            {
                "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
                "authors": json.dumps(["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"]),
                "abstract": "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers.",
                "conference": "North American Chapter of the Association for Computational Linguistics",
                "year": 2019,
                "field": "Natural Language Processing",
                "keywords": json.dumps(["BERT", "Transformers", "Pre-training", "NLP"]),
                "downloadUrl": "https://arxiv.org/pdf/1810.04805.pdf",
                "doi": "10.18653/v1/N19-1423",
                "bibtex": '@inproceedings{devlin2019bert,\n  title={BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding},\n  author={Devlin, Jacob and Chang, Ming-Wei and Lee, Kenton and Toutanova, Kristina},\n  booktitle={Proceedings of the 2019 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies, Volume 1 (Long and Short Papers)},\n  pages={4171--4186},\n  year={2019}\n}'
            },
            {
                "title": "Deep Residual Learning for Image Recognition",
                "authors": json.dumps(["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"]),
                "abstract": "Deeper neural networks are more difficult to train. We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously. We explicitly reformulate the layers as learning residual functions with reference to the layer inputs, instead of learning unreferenced functions.",
                "conference": "IEEE Conference on Computer Vision and Pattern Recognition",
                "year": 2016,
                "field": "Computer Vision",
                "keywords": json.dumps(["ResNet", "Deep Learning", "Computer Vision", "Image Recognition"]),
                "downloadUrl": "https://arxiv.org/pdf/1512.03385.pdf",
                "doi": "10.1109/CVPR.2016.90",
                "bibtex": '@inproceedings{he2016deep,\n  title={Deep residual learning for image recognition},\n  author={He, Kaiming and Zhang, Xiangyu and Ren, Shaoqing and Sun, Jian},\n  booktitle={Proceedings of the IEEE conference on computer vision and pattern recognition},\n  pages={770--778},\n  year={2016}\n}'
            },
            {
                "title": "GPT-3: Language Models are Few-Shot Learners",
                "authors": json.dumps(["Tom B. Brown", "Benjamin Mann", "Nick Ryder", "Melanie Subbiah"]),
                "abstract": "Recent work has demonstrated substantial gains on many NLP tasks and benchmarks by pre-training on a large corpus of text followed by fine-tuning on a specific task. While typically task-agnostic in architecture, this method still requires task-specific fine-tuning datasets of thousands or tens of thousands of examples.",
                "conference": "Neural Information Processing Systems",
                "year": 2020,
                "field": "Natural Language Processing",
                "keywords": json.dumps(["GPT-3", "Language Models", "Few-Shot Learning", "NLP"]),
                "downloadUrl": "https://arxiv.org/pdf/2005.14165.pdf",
                "doi": "10.48550/arXiv.2005.14165",
                "bibtex": '@article{brown2020language,\n  title={Language models are few-shot learners},\n  author={Brown, Tom B and Mann, Benjamin and Ryder, Nick and Subbiah, Melanie and Kaplan, Jared and Dhariwal, Prafulla and Neelakantan, Arvind and Shyam, Pranav and Sastry, Girish and Askell, Amanda and others},\n  journal={Advances in neural information processing systems},\n  volume={33},\n  pages={1877--1901},\n  year={2020}\n}'
            },
            {
                "title": "ImageNet Classification with Deep Convolutional Neural Networks",
                "authors": json.dumps(["Alex Krizhevsky", "Ilya Sutskever", "Geoffrey E. Hinton"]),
                "abstract": "We trained a large, deep convolutional neural network to classify the 1.2 million high-resolution images in the ImageNet LSVRC-2010 contest into the 1000 different classes. On the test data, we achieved top-1 and top-5 error rates of 37.5% and 17.0% which is considerably better than the previous state-of-the-art.",
                "conference": "Neural Information Processing Systems",
                "year": 2012,
                "field": "Computer Vision",
                "keywords": json.dumps(["AlexNet", "CNN", "Computer Vision", "Image Classification"]),
                "downloadUrl": "https://papers.nips.cc/paper_files/paper/2012/file/c399862d3b9d6b76c8436e924a68c45b-Paper.pdf",
                "doi": "10.1145/3065386",
                "bibtex": '@article{krizhevsky2017imagenet,\n  title={ImageNet classification with deep convolutional neural networks},\n  author={Krizhevsky, Alex and Sutskever, Ilya and Hinton, Geoffrey E},\n  journal={Communications of the ACM},\n  volume={60},\n  number={6},\n  pages={84--90},\n  year={2017},\n  publisher={ACM New York, NY, USA}\n}'
            }
        ]
        
        # Create papers in the database
        created_papers = []
        for paper_data in sample_papers:
            # Check if the venue is a known conference or journal
            conference_name = paper_data['conference']
            
            # Create the paper first without the venue references
            paper = Paper.objects.create(**paper_data)
            
            # Now add the venue reference
            try:
                # Try to find a conference first
                conference = Conference.objects.get(name=conference_name)
                paper.conference_venue = conference
                paper.save()
            except Conference.DoesNotExist:
                try:
                    # Try to find a journal
                    journal = Journal.objects.get(name=conference_name)
                    paper.journal = journal
                    paper.save()
                except Journal.DoesNotExist:
                    # If not found in either, create as conference (default venue type)
                    conference = Conference.objects.create(
                        name=conference_name,
                        abbreviation=conference_name[:5] if len(conference_name) > 5 else conference_name
                    )
                    paper.conference_venue = conference
                    paper.save()
            
            created_papers.append(paper)
            
        # Generate citations for these papers
        current_year = datetime.now().year
        
        for paper in created_papers:
            # Calculate starting year - we'll start from the publication year
            start_year = paper.year
            
            # Generate citation data for each year from publication until current year
            for year in range(start_year, current_year + 1):
                # Citations tend to increase for the first few years then plateau or decrease
                years_since_publication = year - start_year
                
                if years_since_publication == 0:
                    # Few citations in the publication year
                    count = random.randint(0, 3)
                elif years_since_publication < 3:
                    # Citations increase in first few years
                    count = random.randint(5, 20) * years_since_publication
                elif years_since_publication < 6:
                    # Citations peak
                    count = random.randint(15, 40)
                else:
                    # Citations start to decrease or plateau for older papers
                    count = random.randint(5, 30)
                    
                # Create citation record
                PaperCitation.objects.create(
                    paper=paper,
                    year=year,
                    count=count
                )
        
        return Response({"message": f"Created {len(created_papers)} sample papers with citation data"})
            
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def dataset_by_slug(request, slug):
    """
    Get details for a specific dataset by slug (simplified name)
    """
    try:
        # Convert slug to lowercase for case-insensitive search
        slug_lower = slug.lower()
        
        # Try to find dataset where name contains the slug (case insensitive)
        datasets = Dataset.objects.filter(name__icontains=slug_lower)
        
        if datasets.exists():
            dataset = datasets.first()
            
            # Get actual paper count from the ManyToMany relationship
            paper_count = dataset.papers.count()
            
            dataset_data = {
                "id": str(dataset.id),
                "name": dataset.name,
                "abbreviation": dataset.abbreviation if dataset.abbreviation else dataset.name[:10],
                "description": dataset.description,
                "downloadUrl": dataset.source_url,
                "language": dataset.language if dataset.language else "English",
                "category": dataset.data_type or "Unknown",
                "tasks": dataset.tasks if dataset.tasks else [],
                "paperCount": paper_count,
                "benchmarks": dataset.benchmarks if dataset.benchmarks else [],
                "link": dataset.link if dataset.link else None,
                "paper_link": dataset.paper_link if dataset.paper_link else None,
                "subtitle": dataset.subtitle if dataset.subtitle else None,
                "thumbnailUrl": dataset.thumbnailUrl if dataset.thumbnailUrl else None,
                "dataloaders": dataset.dataloaders if dataset.dataloaders else [],
                "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
                "updated_at": dataset.updated_at.isoformat() if dataset.updated_at else None,
                "isStarred": False  # Default value, will update below if user is authenticated
            }
            
            # Check if dataset is starred by current user
            if request.user.is_authenticated:
                try:
                    is_starred = InterestingDataset.objects.filter(user=request.user, dataset=dataset).exists()
                    dataset_data["isStarred"] = is_starred
                except Exception as e:
                    print(f"Error checking if dataset is starred: {str(e)}")
            
            # Get related papers data
            related_papers = []
            if hasattr(dataset, 'papers'):
                papers = dataset.papers.all().order_by('-year')
                for paper in papers:
                    # Build paper data
                    paper_data = {
                        "id": str(paper.id),
                        "title": paper.title,
                        "authors": paper.authors if hasattr(paper, 'authors') else [],
                        "abstract": paper.abstract,
                        "conference": paper.conference,
                        "year": paper.year,
                        "field": paper.field if hasattr(paper, 'field') else "",
                        "venue_type": paper.venue_type if hasattr(paper, 'venue_type') else "conference"
                    }
                    related_papers.append(paper_data)
            
            # Get similar datasets
            similar_datasets = []
            
            # Get similar datasets from the DatasetSimilarDataset relation table
            from public_api.models import DatasetSimilarDataset
            similar_relations = DatasetSimilarDataset.objects.filter(from_dataset=dataset)
            
            for relation in similar_relations:
                similar = relation.to_dataset
                
                # Get the actual count of related papers from the ManyToMany relationship
                similar_paper_count = similar.papers.count()
                
                similar_data = {
                    "id": str(similar.id),
                    "name": similar.name,
                    "abbreviation": similar.abbreviation if similar.abbreviation else similar.name[:10],
                    "description": similar.description,
                    "downloadUrl": similar.source_url,
                    "language": similar.language if similar.language else "English",
                    "category": similar.data_type or "Unknown",
                    "tasks": similar.tasks if similar.tasks else [],
                    "paperCount": similar_paper_count,
                    "benchmarks": similar.benchmarks if similar.benchmarks else []
                }
                similar_datasets.append(similar_data)
                
            # Structure the complete response
            result = {
                "dataset": dataset_data,
                "relatedPapers": related_papers,
                "similarDatasets": similar_datasets
            }
                
            return Response(result)
        else:
            return Response({"error": f"No dataset found with slug: {slug}"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_similar_dataset(request, dataset_id):
    """
    Add a similar dataset relationship to a dataset
    """
    try:
        # Get the source dataset
        source_dataset = get_object_or_404(Dataset, id=dataset_id)
        
        # Get the similar dataset ID from request
        similar_dataset_id = request.data.get('similar_dataset_id')
        if not similar_dataset_id:
            return Response({"error": "similar_dataset_id is required"}, status=400)
        
        # Get the similar dataset
        try:
            similar_dataset = Dataset.objects.get(id=similar_dataset_id)
        except Dataset.DoesNotExist:
            return Response({"error": f"Dataset with id {similar_dataset_id} not found"}, status=404)
        
        # Add the similar dataset
        source_dataset.similar_datasets.add(similar_dataset)
        
        return Response({
            "success": True,
            "message": f"Added {similar_dataset.name} as similar to {source_dataset.name}"
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def downloaded_papers(request):
    """
    Get papers marked as downloaded by the authenticated user
    """
    try:
        user = request.user
        downloaded = DownloadedPaper.objects.filter(user=user)
        
        # Extract paper IDs
        paper_ids = [item.paper.id for item in downloaded]
        
        # Get actual paper objects
        papers = Paper.objects.filter(id__in=paper_ids)
        
        serializer = PaperSerializer(papers, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_paper_downloaded(request, paper_id):
    """
    Mark a paper as downloaded for the authenticated user
    """
    try:
        user = request.user
        
        # Check if paper exists
        paper = get_object_or_404(Paper, id=paper_id)
        
        # Create or update downloaded paper entry
        downloaded, created = DownloadedPaper.objects.get_or_create(
            user=user,
            paper=paper
        )
        
        return Response({
            "message": "Paper marked as downloaded",
            "created": created
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def unmark_paper_downloaded(request, paper_id):
    """
    Remove a paper from the user's downloaded papers
    """
    try:
        user = request.user
        
        # Check if paper exists
        paper = get_object_or_404(Paper, id=paper_id)
        
        # Get the downloaded paper entry if it exists
        try:
            downloaded = DownloadedPaper.objects.get(user=user, paper=paper)
            downloaded.delete()
            return Response({"message": "Paper removed from downloaded"}, status=status.HTTP_200_OK)
        except DownloadedPaper.DoesNotExist:
            return Response({"message": "Paper was not marked as downloaded"}, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def interesting_datasets(request):
    """
    Get datasets marked as interesting by the authenticated user with pagination
    """
    try:
        user = request.user
        
        # Pagination parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 20))
        
        interesting = InterestingDataset.objects.filter(user=user)
        
        # Extract dataset IDs
        dataset_ids = [item.dataset.id for item in interesting]
        
        # Get actual dataset objects
        datasets = Dataset.objects.filter(id__in=dataset_ids)
        
        # Apply search filter if provided
        search = request.query_params.get('search')
        if search:
            datasets = datasets.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search)
            )
        
        # Count total items before pagination
        total_count = datasets.count()
        
        # Apply pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_datasets = datasets[start_index:end_index]
        
        result = []
        for dataset in paginated_datasets:
            # Get the actual count of related papers from the ManyToMany relationship
            paper_count = dataset.papers.count()
            
            dataset_data = {
                "id": str(dataset.id),
                "name": dataset.name,
                "abbreviation": dataset.abbreviation if dataset.abbreviation else dataset.name[:10],
                "description": dataset.description,
                "downloadUrl": dataset.source_url,
                "language": dataset.language if dataset.language else "English",
                "category": dataset.data_type or "Unknown",
                "tasks": dataset.tasks if dataset.tasks else [],
                "paperCount": paper_count,
                "benchmarks": dataset.benchmarks if dataset.benchmarks else [],
                "link": dataset.link if dataset.link else None,
                "paper_link": dataset.paper_link if dataset.paper_link else None,
                "subtitle": dataset.subtitle if dataset.subtitle else None,
                "thumbnailUrl": dataset.thumbnailUrl if dataset.thumbnailUrl else None,
                "dataloaders": dataset.dataloaders if dataset.dataloaders else [],
                "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
                "updated_at": dataset.updated_at.isoformat() if dataset.updated_at else None,
                "isStarred": False  # Default value, will update below if user is authenticated
            }
            
            result.append(dataset_data)
        
        # Pagination information
        pagination = {
            "page": page,
            "pageSize": page_size,
            "totalItems": total_count,
            "totalPages": math.ceil(total_count / page_size) if page_size > 0 else 0
        }
        
        return Response({
            "results": result,
            "pagination": pagination
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_dataset_interesting(request, dataset_id):
    """
    Mark a dataset as interesting for the authenticated user
    """
    try:
        user = request.user
        
        # Check if dataset exists
        dataset = get_object_or_404(Dataset, id=dataset_id)
        
        # Create or update interesting dataset entry
        interesting, created = InterestingDataset.objects.get_or_create(
            user=user,
            dataset=dataset
        )
        
        return Response({
            "message": "Dataset marked as interesting",
            "created": created
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def unmark_dataset_interesting(request, dataset_id):
    """
    Remove a dataset from the user's interesting datasets
    """
    try:
        user = request.user
        
        # Check if dataset exists
        dataset = get_object_or_404(Dataset, id=dataset_id)
        
        # Get the interesting dataset entry if it exists
        try:
            interesting = InterestingDataset.objects.get(user=user, dataset=dataset)
            interesting.delete()
            return Response({"message": "Dataset removed from interesting"}, status=status.HTTP_200_OK)
        except InterestingDataset.DoesNotExist:
            return Response({"message": "Dataset was not marked as interesting"}, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def journals_list(request):
    """
    Get a list of all journals with pagination
    """
    try:
        # Pagination parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 20))
        
        # Get filter parameters
        search = request.query_params.get('search')
        quartile = request.query_params.get('quartile')
        impact_min = request.query_params.get('impactMin')
        impact_max = request.query_params.get('impactMax')
        
        # Query the database
        journals = Journal.objects.all()
        
        # Apply filters
        if search:
            journals = journals.filter(
                Q(name__icontains=search) | 
                Q(abbreviation__icontains=search)
            )
            
        if quartile:
            journals = journals.filter(quartile=quartile)
        
        # Apply impact factor filters if provided
        if impact_min is not None:
            journals = journals.filter(impact_factor__gte=float(impact_min))
        
        if impact_max is not None:
            journals = journals.filter(impact_factor__lte=float(impact_max))
            
        # Count total items before pagination
        total_count = journals.count()
        
        # Apply pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_journals = journals[start_index:end_index]
        
        # Prepare results
        result = []
        for journal in paginated_journals:
            papers_count = journal.papers.count()
            
            journal_data = {
                "id": str(journal.id),
                "name": journal.name,
                "abbreviation": journal.abbreviation,
                "impactFactor": journal.impact_factor,
                "quartile": journal.quartile,
                "publisher": journal.publisher,
                "url": journal.url,
                "papersCount": papers_count
            }
            result.append(journal_data)
            
        # Create response with pagination metadata
        response_data = {
            "results": result,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalItems": total_count,
                "totalPages": (total_count + page_size - 1) // page_size
            }
        }
        
        return Response(response_data)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def journal_detail(request, journal_id):
    """
    Get details for a specific journal
    """
    try:
        journal = get_object_or_404(Journal, id=journal_id)
        
        # Count papers published in this journal
        papers_count = journal.papers.count()
        
        # Get papers published in this journal
        papers = journal.papers.all()[:10]  # Just get the first 10 for overview
        
        paper_items = []
        for paper in papers:
            paper_items.append({
                "id": str(paper.id),
                "title": paper.title,
                "year": paper.year,
                "authors": paper.authors
            })
        
        # Prepare journal data
        journal_data = {
            "id": str(journal.id),
            "name": journal.name,
            "abbreviation": journal.abbreviation,
            "impactFactor": journal.impact_factor,
            "quartile": journal.quartile,
            "publisher": journal.publisher,
            "url": journal.url,
            "papersCount": papers_count,
            "papers": paper_items,
            "created_at": journal.created_at
        }
        
        return Response(journal_data)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def conferences_list(request):
    """
    Get a list of all conferences with pagination
    """
    try:
        # Pagination parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 20))
        
        # Get filter parameters
        search = request.query_params.get('search')
        rank = request.query_params.get('rank')
        print(rank)
        # Query the database
        conferences = Conference.objects.all()
        
        # Apply filters
        if search:
            conferences = conferences.filter(
                Q(name__icontains=search) | 
                Q(abbreviation__icontains=search)
            )
            
        if rank:
            # Handle special case for rank "null"
            if rank.lower() == 'null':
                conferences = conferences.filter(Q(rank__isnull=True) | Q(rank=''))
            else:
                # Proper URL decoding for special characters like '*'
                import urllib.parse
                decoded_rank = urllib.parse.unquote(rank)
                conferences = conferences.filter(rank=decoded_rank)
            
        # Count total items before pagination
        total_count = conferences.count()
        
        # Apply pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_conferences = conferences[start_index:end_index]
        
        # Prepare results
        result = []
        for conference in paginated_conferences:
            papers_count = conference.papers.count()
            
            conference_data = {
                "id": str(conference.id),
                "name": conference.name,
                "abbreviation": conference.abbreviation,
                "rank": conference.rank,
                "location": conference.location,
                "url": conference.url,
                "papersCount": papers_count
            }
            result.append(conference_data)
            
        # Create response with pagination metadata
        response_data = {
            "results": result,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalItems": total_count,
                "totalPages": (total_count + page_size - 1) // page_size
            }
        }
        
        return Response(response_data)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def conference_detail(request, conference_id):
    """
    Get details for a specific conference
    """
    try:
        conference = get_object_or_404(Conference, id=conference_id)
        
        # Count papers published in this conference
        papers_count = conference.papers.count()
        
        # Get papers published in this conference
        papers = conference.papers.all()[:10]  # Just get the first 10 for overview
        
        paper_items = []
        for paper in papers:
            paper_items.append({
                "id": str(paper.id),
                "title": paper.title,
                "year": paper.year,
                "authors": paper.authors
            })
        
        # Prepare conference data
        conference_data = {
            "id": str(conference.id),
            "name": conference.name,
            "abbreviation": conference.abbreviation,
            "rank": conference.rank,
            "location": conference.location,
            "url": conference.url,
            "papersCount": papers_count,
            "papers": paper_items,
            "created_at": conference.created_at
        }
        
        return Response(conference_data)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_journal(request):
    """
    Create a new journal (admin only)
    """
    try:
        # Check if user is admin
        if not request.user.is_staff and not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=403)
        
        data = request.data
        
        # Create journal
        journal = Journal.objects.create(
            name=data.get('name'),
            abbreviation=data.get('abbreviation', ''),
            impact_factor=data.get('impactFactor'),
            quartile=data.get('quartile', ''),
            publisher=data.get('publisher', ''),
            url=data.get('url', '')
        )
        
        return Response({
            "id": str(journal.id),
            "name": journal.name,
            "message": "Journal created successfully"
        }, status=201)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_conference(request):
    """
    Create a new conference (admin only)
    """
    try:
        # Check if user is admin
        if not request.user.is_staff and not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=403)
        
        data = request.data
        
        # Create conference
        conference = Conference.objects.create(
            name=data.get('name'),
            abbreviation=data.get('abbreviation', ''),
            rank=data.get('rank', ''),
            location=data.get('location', ''),
            url=data.get('url', '')
        )
        
        return Response({
            "id": str(conference.id),
            "name": conference.name,
            "message": "Conference created successfully"
        }, status=201)
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_journal(request, journal_id):
    """
    Update a journal (admin only)
    """
    try:
        # Check if user is admin
        if not request.user.is_staff and not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=403)
        
        journal = get_object_or_404(Journal, id=journal_id)
        data = request.data
        
        # Update fields
        if 'name' in data:
            journal.name = data['name']
        if 'abbreviation' in data:
            journal.abbreviation = data['abbreviation']
        if 'impactFactor' in data:
            journal.impact_factor = data['impactFactor']
        if 'quartile' in data:
            journal.quartile = data['quartile']
        if 'publisher' in data:
            journal.publisher = data['publisher']
        if 'url' in data:
            journal.url = data['url']
            
        journal.save()
        
        return Response({
            "id": str(journal.id),
            "message": "Journal updated successfully"
        })
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_conference(request, conference_id):
    """
    Update a conference (admin only)
    """
    try:
        # Check if user is admin
        if not request.user.is_staff and not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=403)
        
        conference = get_object_or_404(Conference, id=conference_id)
        data = request.data
        
        # Update fields
        if 'name' in data:
            conference.name = data['name']
        if 'abbreviation' in data:
            conference.abbreviation = data['abbreviation']
        if 'rank' in data:
            conference.rank = data['rank']
        if 'location' in data:
            conference.location = data['location']
        if 'url' in data:
            conference.url = data['url']
            
        conference.save()
        
        return Response({
            "id": str(conference.id),
            "message": "Conference updated successfully"
        })
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def papers_by_venue_type(request, venue_type):
    """
    Get papers filtered by venue type (journal or conference)
    """
    try:
        # Pagination parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 20))
        
        # Get venue ID if specified
        venue_id = request.query_params.get('venue_id', None)
        
        # Get base query
        papers = Paper.objects.all()
        
        # Filter by venue type 
        if venue_type.lower() == 'journal':
            # Journal papers
            papers = papers.filter(Q(journal__isnull=False) | Q(conference__in=Journal.objects.values_list('name', flat=True)))
            
            # Filter by specific journal if ID provided
            if venue_id:
                papers = papers.filter(journal__id=venue_id)
                
        elif venue_type.lower() == 'conference':
            # Conference papers
            papers = papers.filter(Q(conference_venue__isnull=False) | (~Q(conference__in=Journal.objects.values_list('name', flat=True)) & Q(journal__isnull=True)))
            
            # Filter by specific conference if ID provided
            if venue_id:
                papers = papers.filter(conference_venue__id=venue_id)
        else:
            return Response({"error": "Invalid venue type. Must be 'journal' or 'conference'"}, status=400)
        
        # Count total items before pagination
        total_count = papers.count()
        
        # Apply pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_papers = papers[start_index:end_index]
        
        result = []
        
        for paper in paginated_papers:
            # Process authors and keywords (similar to papers_list)
            authors = paper.authors
            if not isinstance(authors, list):
                try:
                    authors = json.loads(authors) if authors else ["Unknown"]
                except:
                    authors = ["Unknown"]
                    
            keywords = paper.keywords
            if not isinstance(keywords, list):
                try:
                    keywords = json.loads(keywords) if keywords else []
                except:
                    keywords = []
            
            venue_name = paper.venue_name
            venue_type = paper.venue_type
            
            paper_data = {
                "id": str(paper.id),
                "title": paper.title,
                "authors": authors,
                "venue": venue_name,
                "venueType": venue_type,
                "year": paper.year,
                "field": paper.field,
                "keywords": keywords,
                "abstract": paper.abstract,
                "downloadUrl": paper.downloadUrl
            }
            
            # Add journal specific information
            if venue_type == 'journal' and paper.journal:
                paper_data["impactFactor"] = paper.journal.impact_factor
                paper_data["quartile"] = paper.journal.quartile
            # Add conference specific information
            elif venue_type == 'conference' and paper.conference_venue:
                paper_data["conferenceRank"] = paper.conference_venue.rank
                paper_data["conferenceAbbreviation"] = paper.conference_venue.abbreviation
            
            result.append(paper_data)
        
        # Create response with pagination metadata
        response_data = {
            "results": result,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalItems": total_count,
                "totalPages": (total_count + page_size - 1) // page_size
            }
        }
            
        return Response(response_data)
        
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def filter_journals_list(request):
    """
    Get a list of all journals for filter dropdown, with search capability
    """
    try:
        # Get search parameter
        search = request.query_params.get('search', '')
        
        # Query the database
        journals = Journal.objects.all().order_by('-impact_factor', 'name')
        
        # Apply search filter if provided
        if search:
            journals = journals.filter(
                Q(name__icontains=search) | 
                Q(abbreviation__icontains=search)
            )
            
        # No limit on results to ensure all journals are available
        # Prepare results
        result = []
        for journal in journals:
            journal_data = {
                "id": str(journal.id),
                "name": journal.name,
                "abbreviation": journal.abbreviation,
                "impactFactor": journal.impact_factor,
                "quartile": journal.quartile
            }
            result.append(journal_data)
        
        return Response(result)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def filter_conferences_list(request):
    """
    Get a list of all conferences for filter dropdown, with search capability
    """
    try:
        # Get search parameter
        search = request.query_params.get('search', '')
        rank = request.query_params.get('rank')
        
        # Query the database
        conferences = Conference.objects.all().order_by('name')
        
        # Apply search filter if provided
        if search:
            conferences = conferences.filter(
                Q(name__icontains=search) | 
                Q(abbreviation__icontains=search)
            )
            
        # Apply rank filter if provided
        if rank:
            # Handle special case for rank "null"
            if rank.lower() == 'null':
                conferences = conferences.filter(Q(rank__isnull=True) | Q(rank=''))
            else:
                # Proper URL decoding for special characters like '*'
                import urllib.parse
                decoded_rank = urllib.parse.unquote(rank)
                conferences = conferences.filter(rank=decoded_rank)
            
        # Prepare results
        result = []
        for conference in conferences:
            conference_data = {
                "id": str(conference.id),
                "name": conference.name,
                "abbreviation": conference.abbreviation,
                "rank": conference.rank
            }
            result.append(conference_data)
        
        return Response(result)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def venues_counts(request):
    """
    Get the total counts of conferences and journals in the database
    """
    try:
        # Count total conferences
        conferences_count = Conference.objects.count()
        
        # Count total journals
        journals_count = Journal.objects.count()
        
        # Return the counts
        return Response({
            "conferencesCount": conferences_count,
            "journalsCount": journals_count
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def conference_counts_debug(request):
    """
    Debug endpoint to compare database and API conference counts
    """
    try:
        # Get total from database
        total_in_db = Conference.objects.count()
        
        # Replicate filter_conferences_list logic for count
        conferences = Conference.objects.all().order_by('name')
        search = request.query_params.get('search', '')
        
        if search:
            conferences = conferences.filter(
                Q(name__icontains=search) | 
                Q(abbreviation__icontains=search)
            )
        
        # Check what would be returned by filter API without rank filter
        filter_api_count = conferences.count()
        
        # Check rank filtering for A*
        conferences_a_star_db = Conference.objects.filter(rank="A*").count()
        
        # Check if any filtering by URL decoding issue
        import urllib.parse
        decoded_rank = urllib.parse.unquote("A*")
        conferences_a_star_decoded = Conference.objects.filter(rank=decoded_rank).count()
        
        # Simulate conferences_list rank filter
        conferences_list_filtered = Conference.objects.all()
        if decoded_rank:
            conferences_list_filtered = conferences_list_filtered.filter(rank=decoded_rank)
        conferences_list_count = conferences_list_filtered.count()
        
        # Simulate filter_conferences_list rank filter
        filter_conferences_filtered = Conference.objects.all().order_by('name')
        if decoded_rank:
            filter_conferences_filtered = filter_conferences_filtered.filter(rank=decoded_rank)
        filter_conferences_count = filter_conferences_filtered.count()
        
        return Response({
            "databaseCount": total_in_db,
            "filterApiCount": filter_api_count,
            "isEqual": total_in_db == filter_api_count,
            "difference": abs(total_in_db - filter_api_count),
            "aStarInDatabase": conferences_a_star_db,
            "aStarDecodedCount": conferences_a_star_decoded,
            "conferencesList_aStarCount": conferences_list_count,
            "filterConferences_aStarCount": filter_conferences_count,
            "aStarRank": "A*",
            "aStarDecodedRank": decoded_rank
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Add these at the end of the file

@api_view(['GET'])
@permission_classes([AllowAny])
def papers_by_keywords(request):
    """
    Get papers filtered by keywords or research interests
    This endpoint supports both keywords and research_interests parameter names
    """
    try:
        # Get keywords parameter - check both keywords and research_interests
        keywords_param = request.query_params.get('keywords', '')
        research_interests_param = request.query_params.get('research_interests', '')
        
        # Use either parameter, prioritizing research_interests
        keywords_list = []
        if research_interests_param:
            keywords_list = [k.strip() for k in research_interests_param.split(',') if k.strip()]
        elif keywords_param:
            keywords_list = [k.strip() for k in keywords_param.split(',') if k.strip()]
            
        if not keywords_list:
            return Response({"error": "No research interests specified"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 10))
        
        # Build query for papers with any of the specified keywords
        papers = Paper.objects.all()
        filtered_papers = []
        
        for paper in papers:
            paper_keywords = []
            # Extract keywords from paper
            if paper.keywords:
                if isinstance(paper.keywords, list):
                    paper_keywords = paper.keywords
                elif isinstance(paper.keywords, str):
                    try:
                        paper_keywords = json.loads(paper.keywords)
                    except json.JSONDecodeError:
                        paper_keywords = [k.strip() for k in paper.keywords.split(',') if k.strip()]
            
            # Check if any of the keywords match
            if any(k.lower() in [pk.lower() for pk in paper_keywords] for k in keywords_list):
                filtered_papers.append(paper)
        
        # Paginate results
        start = (page - 1) * page_size
        end = start + page_size
        paginated_papers = filtered_papers[start:end]
        
        serializer = PaperSerializer(paginated_papers, many=True)
        
        return Response({
            "count": len(filtered_papers),
            "next": f"/api/papers/by-research-interests/?page={page+1}&pageSize={page_size}" if end < len(filtered_papers) else None,
            "previous": f"/api/papers/by-research-interests/?page={page-1}&pageSize={page_size}" if page > 1 else None,
            "results": serializer.data
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def all_keywords(request):
    """
    Get all unique keywords/research interests
    """
    try:
        # Get all papers
        papers = Paper.objects.all()
        
        # Extract all unique keywords
        all_keywords = set()
        
        for paper in papers:
            if paper.keywords:
                keywords_array = []
                if isinstance(paper.keywords, list):
                    keywords_array = paper.keywords
                elif isinstance(paper.keywords, str):
                    try:
                        keywords_array = json.loads(paper.keywords)
                    except json.JSONDecodeError:
                        keywords_array = [k.strip() for k in paper.keywords.split(',') if k.strip()]
                
                for keyword in keywords_array:
                    if keyword and isinstance(keyword, str):
                        all_keywords.add(keyword.strip())
        
        # Sort alphabetically
        sorted_keywords = sorted(all_keywords)
        
        return Response({"keywords": sorted_keywords})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def keywords(request):
    """
    Manage keywords/research interests
    GET: List all keywords with pagination
    POST: Create a new keyword
    PUT: Update a keyword
    DELETE: Delete a keyword
    """
    try:
        if request.method == 'GET':
            # Get search parameter
            search = request.query_params.get('search', '')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('pageSize', 50))
            
            # Get all papers to extract keywords
            papers = Paper.objects.all()
            
            # Count keywords
            keyword_counts = {}
            
            for paper in papers:
                if paper.keywords:
                    keywords_array = []
                    if isinstance(paper.keywords, list):
                        keywords_array = paper.keywords
                    elif isinstance(paper.keywords, str):
                        try:
                            keywords_array = json.loads(paper.keywords)
                        except json.JSONDecodeError:
                            keywords_array = [k.strip() for k in paper.keywords.split(',') if k.strip()]
                    
                    for keyword in keywords_array:
                        if keyword and isinstance(keyword, str):
                            keyword = keyword.strip()
                            if not keyword:
                                continue
                                
                            if search and search.lower() not in keyword.lower():
                                continue
                                
                            if keyword not in keyword_counts:
                                keyword_counts[keyword] = 0
                            keyword_counts[keyword] += 1
            
            # Format and sort
            keywords_list = [{'id': i, 'name': k, 'count': v} for i, (k, v) in enumerate(keyword_counts.items(), 1)]
            keywords_list.sort(key=lambda x: x['name'])
            
            # Paginate
            total_count = len(keywords_list)
            start = (page - 1) * page_size
            end = start + page_size
            paginated_keywords = keywords_list[start:end]
            
            return Response({
                "count": total_count,
                "next": f"/api/research-interests/?page={page+1}&pageSize={page_size}" if end < total_count else None,
                "previous": f"/api/research-interests/?page={page-1}&pageSize={page_size}" if page > 1 else None,
                "results": paginated_keywords
            })
            
        elif request.method == 'POST':
            # Create a new keyword
            name = request.data.get('name')
            if not name:
                return Response({"error": "Name is required"}, status=status.HTTP_400_BAD_REQUEST)
                
            # Since we don't have a Keyword model, this is a placeholder
            # In a real implementation, you'd create a new keyword in the database
            return Response({"id": 1, "name": name, "count": 0}, status=status.HTTP_201_CREATED)
            
        elif request.method == 'PUT':
            # Update a keyword
            keyword_id = request.data.get('id')
            count = request.data.get('count')
            
            if not keyword_id or count is None:
                return Response({"error": "ID and count are required"}, status=status.HTTP_400_BAD_REQUEST)
                
            # Placeholder for keyword update
            return Response({"id": keyword_id, "name": "Updated Keyword", "count": count})
            
        elif request.method == 'DELETE':
            # Delete a keyword
            keyword_id = request.query_params.get('id')
            
            if not keyword_id:
                return Response({"error": "ID is required"}, status=status.HTTP_400_BAD_REQUEST)
                
            # Placeholder for keyword deletion
            return Response({"success": True})
            
        return Response({"error": "Invalid method"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def sync_keywords(request):
    """
    Synchronize keywords/research interests from papers
    """
    try:
        # Get all papers
        papers = Paper.objects.all()
        
        # Extract all keywords
        keyword_counts = {}
        processed_papers = 0
        
        for paper in papers:
            if paper.keywords:
                keywords_array = []
                if isinstance(paper.keywords, list):
                    keywords_array = paper.keywords
                elif isinstance(paper.keywords, str):
                    try:
                        keywords_array = json.loads(paper.keywords)
                    except json.JSONDecodeError:
                        keywords_array = [k.strip() for k in paper.keywords.split(',') if k.strip()]
                
                for keyword in keywords_array:
                    if keyword and isinstance(keyword, str):
                        keyword = keyword.strip()
                        if not keyword:
                            continue
                            
                        if keyword not in keyword_counts:
                            keyword_counts[keyword] = 0
                        keyword_counts[keyword] += 1
                
                processed_papers += 1
        
        # Return stats
        return Response({
            "success": True,
            "processed_papers": processed_papers,
            "total_keywords": len(keyword_counts),
            "message": f"Synchronized {len(keyword_counts)} research interests from {processed_papers} papers"
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def debug_publications(request):
    """
    Debug endpoint to check publication data
    """
    try:
        publication_id = request.query_params.get('id')
        
        # Get publication model info
        publication_model_info = {
            'module': Publication.__module__,
            'name': Publication.__name__,
            'model_meta': str(Publication._meta)
        }
        
        # List all publications if no ID provided
        if not publication_id:
            publications = Publication.objects.all()
            data = {
                'message': 'Publication data debug info',
                'model_info': publication_model_info,
                'count': publications.count(),
                'publications': [
                    {
                        'id': str(p.id),
                        'title': p.title,
                        'user_id': str(p.user.id),
                        'username': p.user.username
                    }
                    for p in publications
                ]
            }
        else:
            # Try to find specific publication
            try:
                publication = Publication.objects.get(id=publication_id)
                data = {
                    'message': 'Publication data debug info',
                    'model_info': publication_model_info,
                    'publication': {
                        'id': str(publication.id),
                        'title': publication.title,
                        'user_id': str(publication.user.id),
                        'username': publication.user.username
                    }
                }
            except Publication.DoesNotExist:
                data = {
                    'message': 'Publication not found',
                    'model_info': publication_model_info,
                    'publication_id': publication_id
                }
        
        return Response(data)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def home_stats(request):
    """
    Get statistics for the home page:
    - Total papers count
    - Total users/researchers count
    - Total datasets count
    - Total conferences and journals count
    """
    try:
        # Count total papers
        total_papers = Paper.objects.count()
        
        # Count total users (researchers)
        total_users = User.objects.count()
        
        # Count total datasets
        total_datasets = Dataset.objects.count()
        
        # Count total conferences and journals
        total_conferences = Conference.objects.count()
        total_journals = Journal.objects.count()
        total_venues = total_conferences + total_journals
        
        return Response({
            'totalPapers': total_papers,
            'totalUsers': total_users,
            'totalDatasets': total_datasets,
            'totalVenues': total_venues
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_library(request):
    """
    Get user's library items based on the section parameter
    """
    try:
        section = request.query_params.get('section', 'interesting')
        user = request.user
        
        if section == 'interesting':
            # Get interesting papers
            interesting = InterestingPaper.objects.filter(user=user)
            paper_ids = [item.paper.id for item in interesting]
            papers = Paper.objects.filter(id__in=paper_ids)
            serializer = PaperSerializer(papers, many=True)
            return Response(serializer.data)
            
        elif section == 'downloaded':
            # Get downloaded papers
            downloaded = DownloadedPaper.objects.filter(user=user)
            paper_ids = [item.paper.id for item in downloaded]
            papers = Paper.objects.filter(id__in=paper_ids)
            serializer = PaperSerializer(papers, many=True)
            return Response(serializer.data)
            
        elif section == 'datasets':
            # Get interesting datasets
            interesting = InterestingDataset.objects.filter(user=user)
            dataset_ids = [item.dataset.id for item in interesting]
            datasets = Dataset.objects.filter(id__in=dataset_ids)
            serializer = DatasetSerializer(datasets, many=True)
            return Response(serializer.data)
            
        elif section == 'recommended':
            # Extract keywords from user profile
            try:
                profile = Profile.objects.get(user=request.user)
            except Profile.DoesNotExist:
                # Create profile if it doesn't exist
                profile = Profile.objects.create(user=request.user)
            
            user_keywords = []
            
            # From research interests - handle None values
            if profile.research_interests:
                user_keywords = user_keywords + [k.strip() for k in profile.research_interests.split(',') if k and k.strip()]
                
            # From additional keywords - handle None values
            if profile.additional_keywords:
                user_keywords = user_keywords + [k.strip() for k in profile.additional_keywords.split(',') if k and k.strip()]
                
            # Remove duplicates
            user_keywords = list(set(user_keywords))
            
            if not user_keywords:
                return Response([])
                
            # Get papers matching keywords
            papers = Paper.objects.all()
            filtered_papers = []
            
            # Get user's existing papers to exclude
            interesting_papers = InterestingPaper.objects.filter(user=user)
            existing_paper_ids = [item.paper.id for item in interesting_papers]
            
            # Filter by date - last 30 days
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            for paper in papers:
                if paper.id in existing_paper_ids:
                    continue
                
                # Skip papers without created_at date or older than 30 days
                if not hasattr(paper, 'created_at') or paper.created_at is None or paper.created_at < thirty_days_ago:
                    continue
                    
                paper_keywords = []
                # Safely process keywords
                if paper.keywords:
                    if isinstance(paper.keywords, list):
                        paper_keywords = paper.keywords
                    elif isinstance(paper.keywords, str):
                        try:
                            paper_keywords = json.loads(paper.keywords)
                        except json.JSONDecodeError:
                            paper_keywords = [k.strip() for k in paper.keywords.split(',') if k and k.strip()]
                    else:
                        # Handle unexpected keyword format
                        continue
                
                # Check if any keywords match
                if any(k.lower() in [pk.lower() for pk in paper_keywords] for k in user_keywords):
                    filtered_papers.append(paper)
            
            # Limit to 20 papers
            filtered_papers = filtered_papers[:20]
            
            # Use PaperSerializer for proper venue_name inclusion
            serializer = PaperSerializer(filtered_papers, many=True)
            return Response(serializer.data)
            
        else:
            return Response({"error": "Invalid section parameter"}, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_paper(request):
    """
    Upload a PDF academic paper and extract metadata.
    
    Required:
    - file: PDF file upload (multipart/form-data)
    
    Process:
    1. Validates the uploaded file is a PDF
    2. Extracts text from the PDF
    3. Analyzes the content using Azure OpenAI to extract metadata
    4. Creates a paper record with the extracted metadata
    
    Returns:
    - Complete paper object with extracted metadata
    """
    # Debug information
    print("---- Paper Upload Debug ----")
    print(f"User: {request.user}")
    print(f"Auth: {request.auth}")
    print(f"FILES: {request.FILES}")
    print(f"Content-Type: {request.headers.get('Content-Type')}")
    
    # Check if 'file' is in the request
    if 'file' not in request.FILES:
        return Response(
            {"error": "No file was provided."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    file = request.FILES['file']
    
    # Check if the file is a PDF
    if not file.name.lower().endswith('.pdf'):
        return Response(
            {"error": "Only PDF files are supported."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Extract text from PDF
    try:
        from users.utils import extract_text_from_pdf, extract_metadata_with_openai
        pdf_text = extract_text_from_pdf(file)
        
        # Extract metadata using OpenAI
        metadata = extract_metadata_with_openai(pdf_text, file.name)
        
        # Create a paper object based on public_api's Paper model
        from public_api.models import Paper
        import os
        import uuid
        
        # Save the file first
        file_name = file.name
        file_path = f"papers/{uuid.uuid4()}_{file_name}"
        media_root = os.path.join(settings.MEDIA_ROOT, file_path)
        os.makedirs(os.path.dirname(media_root), exist_ok=True)
        
        with open(media_root, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        file_url = f"{settings.MEDIA_URL}{file_path}"
        
        # Create paper with the model fields from public_api
        paper = Paper.objects.create(
            title=metadata['title'],
            authors=metadata['authors'],
            abstract=metadata['abstract'],
            conference=metadata['conference'],
            year=metadata['year'],
            field=metadata['field'],
            keywords=metadata['keywords'],
            downloadUrl=file_url,
            doi=metadata['doi'],
            bibtex=metadata['bibtex'],
            sourceCode=metadata['sourceCode'],
        )
        
        # Also create a record in the user's interesting papers
        from public_api.models import InterestingPaper
        InterestingPaper.objects.create(
            user=request.user,
            paper=paper
        )
        
        # Also create a record in the user's downloaded papers
        from public_api.models import DownloadedPaper
        DownloadedPaper.objects.create(
            user=request.user,
            paper=paper
        )
        
        # Return a response compatible with the frontend
        response_data = {
            "id": str(paper.id),
            "title": paper.title,
            "authors": paper.authors,
            "conference": paper.conference,
            "year": paper.year,
            "field": paper.field,
            "keywords": paper.keywords,
            "abstract": paper.abstract,
            "downloadUrl": paper.downloadUrl,
            "doi": paper.doi,
            "bibtex": paper.bibtex,
            "sourceCode": paper.sourceCode,
            "is_interesting": True,
            "is_downloaded": True,
            "is_uploaded": True,
            "added_date": paper.created_at.isoformat(),
            "file_name": file_name,
            "file_size": file.size
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        import traceback
        print(f"Error processing the PDF: {str(e)}")
        print(traceback.format_exc())
        return Response(
            {"error": f"Error processing the PDF: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def research_assistant(request):
    """
    Endpoint for research assistant functionality
    """
    try:
        import requests
        
        data = request.data
        query = data.get('query', '')
        user_id = str(request.user.id) if request.user.is_authenticated else None
        system_prompt = data.get('system_prompt', None)
        
        if not query:
            return Response({"error": "Query is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Forward the request to the research assistant service
        assistant_url = os.environ.get('RESEARCH_ASSISTANT_URL', 'http://localhost:8090')
        
        payload = {
            "query": query,
            "user_id": user_id,
            "system_prompt": system_prompt
        }
        
        try:
            response = requests.post(f"{assistant_url}/query", json=payload, timeout=30)
            response.raise_for_status()
            return Response(response.json())
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to research assistant service: {str(e)}")
            return Response(
                {"error": f"Error connecting to research assistant service: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )
            
    except Exception as e:
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from datetime import datetime, timedelta
import json
import os
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Avg, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
import requests
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.utils import extract_metadata_with_openai, extract_text_from_pdf

from ..authentication import AllowAnyAuthentication
from ..models import (
    Conference,
    Dataset,
    DownloadedPaper,
    InterestingDataset,
    InterestingPaper,
    Journal,
    Paper,
    Profile,
    Publication,
)
from ..serializers import (
    DatasetSerializer,
    PaperSerializer,
    ProfileSerializer,
    PublicationSerializer,
)

User = get_user_model()


class SearchView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AllowAnyAuthentication]

    def get(self, request):
        query = request.query_params.get("q", "")
        if not query or len(query.strip()) < 2:
            return Response(
                {"error": "Search query must be at least 2 characters"}, status=400
            )

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 10))

        papers_query = Paper.objects.filter(
            Q(title__icontains=query)
            | Q(authors__icontains=query)
            | Q(abstract__icontains=query)
            | Q(keywords__icontains=query)
        )

        # Search datasets using Dataset model
        datasets_query = Dataset.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
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
        results = {"papers": [], "datasets": []}

        # Add papers to results
        for paper in papers:
            try:
                authors = json.loads(paper.authors) if paper.authors else ["Unknown"]
                if isinstance(authors, list) and len(authors) > 3:
                    authors = authors[:3] + ["et al."]
            except:
                authors = ["Unknown"]

            results["papers"].append(
                {
                    "id": str(paper.id),
                    "title": paper.title,
                    "authors": authors,
                    "year": paper.year,
                    "abstract": (
                        paper.abstract[:200] + "..."
                        if len(paper.abstract) > 200
                        else paper.abstract
                    ),
                    "venue": paper.conference,
                }
            )

        # Add datasets to results
        for dataset in datasets:
            results["datasets"].append(
                {
                    "id": str(dataset.id),
                    "name": dataset.name,
                    "description": (
                        dataset.description[:200] + "..."
                        if len(dataset.description) > 200
                        else dataset.description
                    ),
                    "category": dataset.data_type or "Unknown",
                    "papers_count": dataset.papers.count(),
                }
            )

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
                    (total_datasets + page_size - 1) // page_size,
                ),
            },
        }

        return Response(response_data)


class GetProfile(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [AllowAnyAuthentication]

    def get(self, request):
        profile = Profile.objects.get(user=request.user)
        serializer = ProfileSerializer(profile)
        data = serializer.data

        user_publications = Publication.objects.filter(user=request.user)
        publications_serializer = PublicationSerializer(user_publications, many=True)
        data["publications"] = publications_serializer.data

        if "research_interests" in data and "keywords" not in data:
            data["keywords"] = data["research_interests"]

        return Response(data, status=status.HTTP_200_OK)


class UpdateProfile(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [AllowAnyAuthentication]

    def patch(self, request):
        user = request.user
        profile = Profile.objects.get(user=user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        profile = serializer.save()

        updated_data = serializer.data
        publications = user.public_publications
        publications_serializer = PublicationSerializer(publications, many=True)
        updated_data["publications"] = publications_serializer.data

        research_interests = updated_data.get("research_interests", "")
        if "keywords" not in updated_data:
            updated_data["keywords"] = research_interests

        return Response(updated_data, status=status.HTTP_200_OK)


class PublicationsList(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [AllowAnyAuthentication]

    def get(self, request):
        user = request.user
        publications = user.public_publications
        serializer = PublicationSerializer(publications, many=True)
        return Response(serializer.data)

    def post(self, request):
        user = request.user
        serializer = PublicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PublicationDetail(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [AllowAnyAuthentication]

    def get(self, request, publication_id):
        user = request.user
        publication = Publication.objects.get(id=publication_id, user=user)
        serializer = PublicationSerializer(publication)
        return Response(serializer.data)

    def put(self, request, publication_id):
        user = request.user
        publication = get_object_or_404(Publication, id=publication_id, user=user)
        serializer = PublicationSerializer(publication, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Convert UUID from string to UUID object if needed
            if isinstance(publication_id, str):
                try:
                    publication_id = uuid.UUID(publication_id)
                except ValueError:
                    pass

            publication = Publication.objects.get(id=publication_id, user=user)
            print(
                f"[DEBUG] Found publication: {publication.id}, title: {publication.title}"
            )
        except Publication.DoesNotExist:
            # Log the error for debugging
            print(f"[DEBUG] Publication not found: {publication_id}, user: {user.id}")
            print(
                f"[DEBUG] All publications for user: {[str(p.id) for p in Publication.objects.filter(user=user)]}"
            )
            return Response(
                {"error": "Publication not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if request.method == "GET":
            serializer = PublicationSerializer(publication)
            return Response(serializer.data)

        elif request.method == "PUT":
            data = request.data.copy()
            data["user"] = user.id

            serializer = PublicationSerializer(publication, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == "DELETE":
            print(f"[DEBUG] Deleting publication with ID: {publication.id}")
            publication.delete()
            return Response(
                {"message": "Publication deleted successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )


class Stats(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AllowAnyAuthentication]

    def get(self, request):
        total_papers = Paper.objects.count()

        # Count papers in the current month
        current_month_start = datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        papers_this_month = Paper.objects.filter(
            created_at__gte=current_month_start
        ).count()

        # Calculate total and average citations
        citations_data = Paper.objects.aggregate(
            total_citations=Sum("citations"), avg_citations=Avg("citations")
        )
        total_citations = citations_data["total_citations"] or 0
        avg_citations = citations_data["avg_citations"] or 0

        # Return the statistics
        return Response(
            {
                "totalPapers": total_papers,
                "papersThisMonth": papers_this_month,
                "totalCitations": total_citations,
                "averageCitations": round(float(avg_citations), 1),
            }
        )


class DashboardStats(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AllowAnyAuthentication]

    def get(self, request):
        user = request.user if request.user.is_authenticated else None

        start_date = request.query_params.get("startDate")
        end_date = request.query_params.get("endDate")

        query_params = {}
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                query_params["created_at__gte"] = start_date
            except ValueError:
                pass
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                query_params["created_at__lte"] = end_date
            except ValueError:
                pass

        if user:
            query_params["created_by"] = user

        all_papers = Paper.objects.filter(**query_params)

        monthly_query = {}
        if user:
            monthly_query["created_by"] = user

        monthly_papers_queryset = Paper.objects.filter(**monthly_query)

        month_names = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        monthly_papers_count = {month: 0 for month in month_names}

        for paper in monthly_papers_queryset:
            month_idx = paper.created_at.month - 1
            month_name = month_names[month_idx]
            monthly_papers_count[month_name] += 1

        monthly_papers = [
            {"name": name, "papers": count}
            for name, count in monthly_papers_count.items()
        ]

        paper_fields = {}
        for paper in all_papers:
            fields = paper.field.split(",")
            for field in fields:
                field = field.strip()
                if field and field not in paper_fields:
                    paper_fields[field] = 0
                if field:
                    paper_fields[field] += 1

        category_data = [
            {"name": name, "value": count} for name, count in paper_fields.items()
        ]
        category_data.sort(key=lambda x: x["value"], reverse=True)
        category_data = category_data[:10]

        papers_with_keywords = all_papers.values("id", "keywords")

        keyword_count = {}

        for index, paper in enumerate(papers_with_keywords):
            try:
                keywords_data = json.loads(paper["keywords"])
                if isinstance(keywords_data, list):
                    for keyword in keywords_data:
                        if keyword not in keyword_count:
                            keyword_count[keyword] = {
                                "id": index * 100 + len(keyword_count),
                                "name": keyword,
                                "count": 0,
                            }
                        keyword_count[keyword]["count"] += 1
            except (json.JSONDecodeError, TypeError):
                if paper["keywords"] and isinstance(paper["keywords"], str):
                    keywords = paper["keywords"].split(",")
                    for keyword in keywords:
                        keyword = keyword.strip()
                        if keyword:
                            if keyword not in keyword_count:
                                keyword_count[keyword] = {
                                    "id": index * 100 + len(keyword_count),
                                    "name": keyword,
                                    "count": 0,
                                }
                            keyword_count[keyword]["count"] += 1

        keyword_sets = list(keyword_count.values())
        keyword_sets.sort(key=lambda x: x["count"], reverse=True)
        keyword_sets = keyword_sets[:10]

        return Response(
            {
                "monthlyPapers": monthly_papers,
                "categoryData": category_data,
                "keywordSets": keyword_sets,
            }
        )


class PapersStats(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AllowAnyAuthentication]

    def get(self, request):
        # Get user for created_by filter if authenticated
        user = request.user if request.user.is_authenticated else None

        # Get date range parameters for citation calculation
        start_date = request.query_params.get("startDate")
        end_date = request.query_params.get("endDate")

        # Build the query based on date range for citation calculation
        date_query_params = {}
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                date_query_params["created_at__gte"] = start_date
            except ValueError:
                pass
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                date_query_params["created_at__lte"] = end_date
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
        current_month_start = datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        if user:
            papers_this_month = Paper.objects.filter(
                created_at__gte=current_month_start, created_by=user
            ).count()
        else:
            papers_this_month = Paper.objects.filter(
                created_at__gte=current_month_start
            ).count()

        # Calculate total citations based on date filter
        citation_data = Paper.objects.filter(**date_query_params).aggregate(
            total_citations=Sum("citations"), avg_citations=Avg("citations")
        )
        total_citations = citation_data["total_citations"] or 0
        avg_citations = round(float(citation_data["avg_citations"] or 0), 1)

        return Response(
            {
                "totalPapers": total_papers,
                "papersThisMonth": papers_this_month,
                "totalCitations": total_citations,
                "averageCitations": avg_citations,
            }
        )


class KeywordsStats(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AllowAnyAuthentication]

    def get(self, request):
        user = request.user if request.user.is_authenticated else None

        start_date = request.query_params.get("startDate")
        end_date = request.query_params.get("endDate")
        period = request.query_params.get("period", "monthly")

        query_params = {}
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                query_params["created_at__gte"] = start_date
            except ValueError:
                pass
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                query_params["created_at__lte"] = end_date
            except ValueError:
                pass

        if user and not user.is_anonymous:
            query_params["created_by"] = user

        papers = Paper.objects.filter(**query_params).values(
            "id", "keywords", "created_at"
        )

        interests_counts = {}
        interests_by_period = {}

        for paper in papers:
            keywords_array = []
            try:
                if paper["keywords"]:
                    if isinstance(paper["keywords"], list):
                        keywords_array = paper["keywords"]
                    elif isinstance(paper["keywords"], str):
                        try:
                            parsed_keywords = json.loads(paper["keywords"])
                            keywords_array = (
                                parsed_keywords
                                if isinstance(parsed_keywords, list)
                                else [paper["keywords"]]
                            )
                        except json.JSONDecodeError:
                            keywords_array = [
                                k.strip()
                                for k in paper["keywords"].split(",")
                                if k.strip()
                            ]
                    else:
                        print(
                            f"Unknown keywords type for paper {paper['id']}: {type(paper['keywords'])}"
                        )
                        continue
            except Exception as e:
                print(f"Error processing keywords for paper {paper['id']}: {str(e)}")
                continue

            if not keywords_array:
                continue

            date = paper["created_at"]
            if period == "daily":
                period_key = date.strftime("%Y-%m-%d")
            elif period == "yearly":
                period_key = str(date.year)
            else:
                period_key = date.strftime("%Y-%m")

            if period_key not in interests_by_period:
                interests_by_period[period_key] = {}

            for keyword in keywords_array:
                if not keyword or not isinstance(keyword, str):
                    continue

                keyword = keyword.strip()
                if not keyword:
                    continue

                if keyword not in interests_counts:
                    interests_counts[keyword] = 0
                interests_counts[keyword] += 1

                if keyword not in interests_by_period[period_key]:
                    interests_by_period[period_key][keyword] = 0
                interests_by_period[period_key][keyword] += 1

        keywords_list = [{"name": k, "count": v} for k, v in interests_counts.items()]
        keywords_list.sort(key=lambda x: x["count"], reverse=True)

        if not interests_by_period and len(papers) > 0:
            current_period = (
                datetime.now().strftime("%Y-%m")
                if period == "monthly"
                else datetime.now().strftime("%Y")
            )
            interests_by_period[current_period] = {
                "AI": 10,
                "Machine Learning": 8,
                "Deep Learning": 6,
                "NLP": 4,
                "Computer Vision": 2,
            }

        period_data = []
        for period_key, keywords in sorted(interests_by_period.items()):
            if keywords:
                top_keyword = max(keywords.items(), key=lambda x: x[1])
                period_item = {
                    "period": period_key,
                    "keywords": [{"name": top_keyword[0], "count": top_keyword[1]}],
                }
                period_data.append(period_item)

        result = {
            "totalKeywords": len(interests_counts),
            "keywords": keywords_list[:20],
            "periodData": period_data,
        }

        return Response(result)


class DatasetsStats(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AllowAnyAuthentication]

    def get(self, request):
        user = request.user if request.user.is_authenticated else None

        start_date = request.query_params.get("startDate")
        end_date = request.query_params.get("endDate")
        period = request.query_params.get("period", "monthly")

        query_params = {}
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                query_params["created_at__gte"] = start_date
            except ValueError:
                pass
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                query_params["created_at__lte"] = end_date
            except ValueError:
                pass

        if user:
            query_params["created_by"] = user

        datasets = Dataset.objects.all()

        papers = Paper.objects.filter(**query_params)

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
                    if period == "daily":
                        period_key = date.strftime("%Y-%m-%d")
                    elif period == "yearly":
                        period_key = str(date.year)
                    else:  # monthly (default)
                        period_key = date.strftime("%Y-%m")

                    if period_key not in datasets_by_period:
                        datasets_by_period[period_key] = {}

                    if dataset_name not in datasets_by_period[period_key]:
                        datasets_by_period[period_key][dataset_name] = 0

                    datasets_by_period[period_key][dataset_name] += 1

        # Format for response
        datasets_list = [
            {"name": k, "count": v} for k, v in dataset_counts.items() if v > 0
        ]
        datasets_list.sort(key=lambda x: x["count"], reverse=True)

        # Format period data
        period_data = []
        for period_key, period_datasets in sorted(datasets_by_period.items()):
            # Get top datasets for this period
            top_datasets = sorted(
                period_datasets.items(), key=lambda x: x[1], reverse=True
            )[:5]
            period_item = {
                "period": period_key,
                "datasets": [{"name": k, "count": v} for k, v in top_datasets],
            }
            period_data.append(period_item)

        return Response(
            {
                "totalDatasets": len([d for d in dataset_counts.values() if d > 0]),
                "datasets": datasets_list[:20],  # Top 20 datasets
                "periodData": period_data,
            }
        )


class Register(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AllowAnyAuthentication]

    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if not username or not email or not password:
            return Response(
                {"error": "Username, email, and password are required"}, status=400
            )

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already exists"}, status=400)

        user = User.objects.create_user(
            username=username, email=email, password=password
        )

        Profile.objects.get_or_create(user=user)[0]
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "message": "User registered successfully",
                "token": token.key,
                "userId": user.id,
                "username": user.username,
                "email": user.email,
            }
        )


class TokenLogin(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AllowAnyAuthentication]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        try:
            if "@" in username:
                user = User.objects.get(email=username)
            else:
                user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {"non_field_errors": ["Invalid credentials"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.check_password(password):
            return Response(
                {"non_field_errors": ["Invalid credentials"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
            }
        )


class GoogleCallback(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AllowAnyAuthentication]

    def post(self, request):
        code = request.data.get("code")
        redirect_uri = request.data.get("redirect_uri")
        device_id = request.data.get("device_id")
        device_name = request.data.get("device_name")

        client_ip = request.META.get("REMOTE_ADDR", "")
        is_private_ip = (
            client_ip.startswith("10.")
            or client_ip.startswith("172.16.")
            or client_ip.startswith("192.168.")
            or client_ip == "127.0.0.1"
        )

        if is_private_ip and (not device_id or not device_name):
            return Response(
                {
                    "error": "invalid_request",
                    "error_description": "device_id and device_name are required for private IP access",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not code:
            return Response(
                {"detail": "Authorization code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_url = "https://oauth2.googleapis.com/token"
        client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
        client_secret = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET

        token_data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        token_response = requests.post(token_url, data=token_data)

        if token_response.status_code != 200:
            return Response(
                {"detail": "Failed to exchange code for token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_json = token_response.json()
        access_token = token_json.get("access_token")

        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        user_info_response = requests.get(
            user_info_url, headers={"Authorization": f"Bearer {access_token}"}
        )

        if user_info_response.status_code != 200:
            return Response(
                {"detail": "Failed to get user info"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_info = user_info_response.json()
        email = user_info.get("email")

        if not email:
            return Response(
                {"detail": "Email not provided by Google"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = email.split("@")[0]
        user, created = User.objects.get_or_create(email=email, username=username)
        if created:
            Profile.objects.create(user=user, full_name=user_info.get("name", ""))
        # Generate token
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
            }
        )


class MicrosoftCallback(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AllowAnyAuthentication]

    def post(self, request):
        code = request.data.get("code")
        redirect_uri = request.data.get("redirect_uri")
        device_id = request.data.get("device_id")
        device_name = request.data.get("device_name")

        client_ip = request.META.get("REMOTE_ADDR", "")
        is_private_ip = (
            client_ip.startswith("10.")
            or client_ip.startswith("172.16.")
            or client_ip.startswith("192.168.")
            or client_ip == "127.0.0.1"
        )

        if is_private_ip and (not device_id or not device_name):
            return Response(
                {
                    "error": "invalid_request",
                    "error_description": "device_id and device_name are required for private IP access",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not code or not redirect_uri:
            return Response(
                {"error": "Missing code or redirect_uri parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client_id = settings.SOCIAL_AUTH_MICROSOFT_OAUTH2_KEY
        client_secret = settings.SOCIAL_AUTH_MICROSOFT_OAUTH2_SECRET

        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        token_response = requests.post(token_url, data=token_data)
        if token_response.status_code != 200:
            return Response(
                {"detail": "Failed to exchange code for token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_json = token_response.json()
        access_token = token_json.get("access_token")

        user_info_url = "https://graph.microsoft.com/v1.0/me"
        user_info_response = requests.get(
            user_info_url, headers={"Authorization": f"Bearer {access_token}"}
        )
        if user_info_response.status_code != 200:
            return Response(
                {"detail": "Failed to get user info"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_info = user_info_response.json()
        email = user_info.get("mail") or user_info.get("userPrincipalName")

        if not email:
            return Response(
                {"error": "No email found in Microsoft user data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = email.split("@")[0]
        user, created = User.objects.get_or_create(email=email, username=username)
        if created:
            Profile.objects.create(user=user, full_name=user_info.get("name", ""))
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user_id": user.id,
                "email": user.email,
                "username": user.username,
            }
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AllowAnyAuthentication]

    def get(self, request):
        google_login_url = f"https://accounts.google.com/o/oauth2/auth"
        redirect_uri = f"{settings.API_URL}/sso-callback/google"

        client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY

        google_login = f"{google_login_url}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=email%20profile&access_type=offline&prompt=consent"

        microsoft_login = (
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        )

        return Response(
            {
                "google_login": google_login,
                "microsoft_login": microsoft_login,
                "token_login": f"{settings.API_URL}/api/token-login/",
            }
        )


class UpdateAvatar(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [AllowAnyAuthentication]

    def post(self, request):
        user = request.user

        avatar_file = request.FILES.get("avatar")
        if not avatar_file:
            return Response({"error": "No file provided"}, status=400)

        if avatar_file.size > 5 * 1024 * 1024:
            return Response({"error": "File size exceeds 5MB limit"}, status=400)

        if not avatar_file.content_type.startswith("image/"):
            return Response({"error": "File must be an image"}, status=400)

        filename = f"avatar_{user.id}_{uuid.uuid4()}.jpg"

        file_path = default_storage.save(
            f"avatars/{filename}", ContentFile(avatar_file.read())
        )

        avatar_url = default_storage.url(file_path)

        try:
            profile = Profile.objects.get(user=user)
            profile.avatar_url = avatar_url
            profile.save()
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=user, avatar_url=avatar_url)

        return Response(
            {"avatar_url": avatar_url, "message": "Avatar updated successfully"}
        )


class VenuesCounts(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        conferences_count = Conference.objects.count()
        journals_count = Journal.objects.count()
        output = {
            "conferencesCount": conferences_count,
            "journalsCount": journals_count,
        }
        return Response(output, status=status.HTTP_200_OK)


class HomeStats(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        total_papers = Paper.objects.count()
        total_users = User.objects.count()
        total_datasets = Dataset.objects.count()

        total_conferences = Conference.objects.count()
        total_journals = Journal.objects.count()
        total_venues = total_conferences + total_journals

        return Response(
            {
                "totalPapers": total_papers,
                "totalUsers": total_users,
                "totalDatasets": total_datasets,
                "totalVenues": total_venues,
            }
        )


class MyLibrary(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        section = request.query_params.get("section", "interesting")
        user = request.user

        if section == "interesting":
            interesting = InterestingPaper.objects.filter(user=user)
            paper_ids = [item.paper.id for item in interesting]
            papers = Paper.objects.filter(id__in=paper_ids)
            serializer = PaperSerializer(papers, many=True)
            return Response(serializer.data)

        elif section == "downloaded":
            downloaded = DownloadedPaper.objects.filter(user=user)
            paper_ids = [item.paper.id for item in downloaded]
            papers = Paper.objects.filter(id__in=paper_ids)
            serializer = PaperSerializer(papers, many=True)
            return Response(serializer.data)

        elif section == "datasets":
            interesting = InterestingDataset.objects.filter(user=user)
            dataset_ids = [item.dataset.id for item in interesting]
            datasets = Dataset.objects.filter(id__in=dataset_ids)
            serializer = DatasetSerializer(datasets, many=True)
            return Response(serializer.data)

        elif section == "recommended":
            try:
                profile = Profile.objects.get(user=request.user)
            except Profile.DoesNotExist:
                profile = Profile.objects.create(user=request.user)

            user_keywords = []

            if profile.research_interests:
                user_keywords = user_keywords + [
                    k.strip()
                    for k in profile.research_interests.split(",")
                    if k and k.strip()
                ]

            if profile.additional_keywords:
                user_keywords = user_keywords + [
                    k.strip()
                    for k in profile.additional_keywords.split(",")
                    if k and k.strip()
                ]

            user_keywords = list(set(user_keywords))

            if not user_keywords:
                return Response([])

            papers = Paper.objects.all()
            filtered_papers = []

            interesting_papers = InterestingPaper.objects.filter(user=user)
            existing_paper_ids = [item.paper.id for item in interesting_papers]

            thirty_days_ago = timezone.now() - timedelta(days=30)

            for paper in papers:
                if paper.id in existing_paper_ids:
                    continue

                if (
                    not hasattr(paper, "created_at")
                    or paper.created_at is None
                    or paper.created_at < thirty_days_ago
                ):
                    continue

                paper_keywords = []
                if paper.keywords:
                    if isinstance(paper.keywords, list):
                        paper_keywords = paper.keywords
                    elif isinstance(paper.keywords, str):
                        try:
                            paper_keywords = json.loads(paper.keywords)
                        except json.JSONDecodeError:
                            paper_keywords = [
                                k.strip()
                                for k in paper.keywords.split(",")
                                if k and k.strip()
                            ]
                    else:
                        continue

                if any(
                    k.lower() in [pk.lower() for pk in paper_keywords]
                    for k in user_keywords
                ):
                    filtered_papers.append(paper)

            filtered_papers = filtered_papers[:20]

            serializer = PaperSerializer(filtered_papers, many=True)
            return Response(serializer.data)

        else:
            return Response(
                {"error": "Invalid section parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UploadPaper(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [AllowAnyAuthentication]

    def post(self, request):
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

        if "file" not in request.FILES:
            return Response(
                {"error": "No file was provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES["file"]

        if not file.name.lower().endswith(".pdf"):
            return Response(
                {"error": "Only PDF files are supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pdf_text = extract_text_from_pdf(file)

        metadata = extract_metadata_with_openai(pdf_text, file.name)

        paper = Paper.objects.create(
            title=metadata["title"],
            authors=metadata["authors"],
            abstract=metadata["abstract"],
            conference=metadata["conference"],
            year=metadata["year"],
            field=metadata["field"],
            keywords=metadata["keywords"],
            downloadUrl=file.url,
            doi=metadata["doi"],
            bibtex=metadata["bibtex"],
            sourceCode=metadata["sourceCode"],
            pdf_file=file,
            file_name=file.name,
            file_size=file.size,
        )

        InterestingPaper.objects.create(user=request.user, paper=paper)
        DownloadedPaper.objects.create(user=request.user, paper=paper)

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
            "file_name": file.name,
            "file_size": file.size,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class ResearchAssistant(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AllowAnyAuthentication]

    def post(self, request):
        data = request.data
        query = data.get("query", "")
        user_id = str(request.user.id) if request.user.is_authenticated else None
        system_prompt = data.get("system_prompt", None)

        if not query:
            return Response(
                {"error": "Query is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        assistant_url = os.environ.get(
            "RESEARCH_ASSISTANT_URL", "http://localhost:8090"
        )
        payload = {"query": query, "user_id": user_id, "system_prompt": system_prompt}

        response = requests.post(f"{assistant_url}/query", json=payload, timeout=30)
        response.raise_for_status()
        return Response(response.json())

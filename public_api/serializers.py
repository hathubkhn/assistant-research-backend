import json

from rest_framework import serializers

from .models import (
    Conference,
    Dataset,
    DownloadedPaper,
    InterestingDataset,
    Journal,
    Paper,
    Profile,
    Publication,
    Task,
)


def resolve_paper_download_url(paper, request=None):
    """Prefer stored pdf_url; fall back to uploaded pdf_file with absolute URI."""
    placeholder = "https://example.com"
    if paper.pdf_url and paper.pdf_url != placeholder:
        return paper.pdf_url
    if paper.pdf_file:
        url = paper.pdf_file.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url
    return paper.pdf_url or ""


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "username",
            "email",
            "full_name",
            "faculty_institute",
            "school",
            "position",
            "google_scholar_link",
            "bio",
            "research_interests",
            "additional_keywords",
            "avatar_url",
            "is_profile_completed",
            "created_at",
            "updated_at",
        ]


class JournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Journal
        fields = "__all__"


class ConferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conference
        fields = "__all__"


class PaperSerializer(serializers.ModelSerializer):
    journal_details = JournalSerializer(source="journal", read_only=True)
    conference_details = ConferenceSerializer(source="conference_venue", read_only=True)
    tasks = serializers.SerializerMethodField()
    venue_type = serializers.ReadOnlyField()
    venue_name = serializers.ReadOnlyField()

    class Meta:
        model = Paper
        fields = "__all__"

    def get_tasks(self, obj):
        return list(obj.tasks.all().values_list("name", flat=True))


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = "__all__"


class PublicationSerializer(serializers.ModelSerializer):
    # FE often sends authors as list/object; normalize to text for DB storage.
    authors = serializers.JSONField()
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Publication
        fields = "__all__"
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    @staticmethod
    def _normalize_authors_value(value):
        if isinstance(value, (list, dict)):
            return json.dumps(value)
        return value

    def create(self, validated_data):
        if "authors" in validated_data:
            validated_data["authors"] = self._normalize_authors_value(
                validated_data["authors"]
            )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "authors" in validated_data:
            validated_data["authors"] = self._normalize_authors_value(
                validated_data["authors"]
            )
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        raw_authors = data.get("authors")
        if isinstance(raw_authors, str):
            try:
                data["authors"] = json.loads(raw_authors)
            except (TypeError, ValueError):
                pass
        return data


class PaperListSerializer(serializers.ModelSerializer):
    year = serializers.SerializerMethodField()
    downloadUrl = serializers.SerializerMethodField()
    authors = serializers.SerializerMethodField()
    venueType = serializers.SerializerMethodField()
    venue = serializers.SerializerMethodField()
    impactFactor = serializers.SerializerMethodField()
    quartile = serializers.SerializerMethodField()
    keywords = serializers.SerializerMethodField()

    class Meta:
        model = Paper
        fields = [
            "id",
            "title",
            "authors",
            "venue",
            "venueType",
            "year",
            "keywords",
            "abstract",
            "downloadUrl",
            "impactFactor",
            "quartile",
        ]

    def get_authors(self, obj):
        authors_list = obj.authors.values_list("name", flat=True)
        authors_list = list(authors_list)
        if len(authors_list) > 0:
            return authors_list
        else:
            return ["Unknown"]

    def get_downloadUrl(self, obj):
        request = self.context.get("request")
        return resolve_paper_download_url(obj, request)

    def get_year(self, obj):
        return obj.publication_date.year if obj.publication_date else None

    def get_venueType(self, obj):
        return obj.venue_type

    def get_venue(self, obj):
        if obj.journal is not None:
            return {
                "id": obj.journal.id,
                "name": obj.journal.name,
                "abbreviation": obj.journal.abbreviation,
                "impactFactor": obj.journal.impact_factor,
                "rank": obj.journal.quartile,
            }
        elif obj.conference is not None:
            return {
                "id": obj.conference.id,
                "name": obj.conference.name,
                "abbreviation": obj.conference.abbreviation,
                "rank": obj.conference.rank,
            }
        else:
            return None

    def get_impactFactor(self, obj):
        if obj.venue_type == "journal" and obj.journal:
            return obj.journal.impact_factor
        else:
            return None

    def get_quartile(self, obj):
        if obj.venue_type == "journal" and obj.journal:
            return obj.journal.quartile
        else:
            return None

    def get_keywords(self, obj):
        if obj.keywords:
            return obj.keywords
        else:
            return []


class LibraryItemSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="paper.id", read_only=True)
    title = serializers.CharField(source="paper.title", read_only=True)
    authors = serializers.SerializerMethodField()
    conference = serializers.SerializerMethodField()
    year = serializers.SerializerMethodField()
    keywords = serializers.SerializerMethodField()
    abstract = serializers.CharField(source="paper.abstract", read_only=True)
    downloadUrl = serializers.SerializerMethodField()
    is_interesting = serializers.SerializerMethodField()
    is_downloaded = serializers.SerializerMethodField()
    added_date = serializers.DateTimeField(source="created_at", read_only=True)
    doi = serializers.CharField(source="paper.doi", read_only=True)
    bibtex = serializers.CharField(source="paper.bibtex", read_only=True)

    class Meta:
        fields = [
            "id",
            "title",
            "authors",
            "conference",
            "year",
            "keywords",
            "abstract",
            "downloadUrl",
            "is_interesting",
            "is_downloaded",
            "added_date",
            "doi",
            "bibtex",
        ]

    def get_authors(self, obj):
        authors_list = [author.name for author in obj.paper.authors.all()]
        return authors_list if authors_list else ["Unknown"]

    def get_conference(self, obj):
        if obj.paper.conference is not None:
            return obj.paper.conference.name
        return ""

    def get_year(self, obj):
        return obj.paper.publication_date.year if obj.paper.publication_date else None

    def get_keywords(self, obj):
        return obj.paper.keywords or []

    def get_downloadUrl(self, obj):
        request = self.context.get("request")
        return resolve_paper_download_url(obj.paper, request)

    def get_is_interesting(self, obj):
        return obj.paper.interested_users.filter(user=obj.user).exists()

    def get_is_downloaded(self, obj):
        return hasattr(obj, "paper") and obj.paper.downloaded_users.filter(user=obj.user).exists()


class DatasetListSerializer(serializers.ModelSerializer):
    downloadUrl = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    thumbnailUrl = serializers.SerializerMethodField()
    tasks = serializers.SerializerMethodField()
    paperCount = serializers.SerializerMethodField()
    benchmarks = serializers.SerializerMethodField()
    isStarred = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = [
            "id",
            "name",
            "abbreviation",
            "description",
            "downloadUrl",
            "language",
            "category",
            "tasks",
            "paperCount",
            "benchmarks",
            "link",
            "paper_link",
            "subtitle",
            "thumbnailUrl",
            "dataloaders",
            "created_at",
            "updated_at",
            "isStarred",
        ]

    def get_downloadUrl(self, obj):
        return obj.source_url

    def get_category(self, obj):
        return obj.data_type

    def get_tasks(self, obj):
        return list(obj.tasks.all().values_list("name", flat=True))

    def get_thumbnailUrl(self, obj):
        return obj.thumbnail_url

    def get_paperCount(self, obj):
        return obj.papers.count()

    def get_benchmarks(self, obj):
        benchmarks = []
        if obj.benchmarks:
            if isinstance(obj.benchmarks, list):
                benchmarks = obj.benchmarks
            elif isinstance(obj.benchmarks, int):
                benchmarks = [{"placeholder": True} for _ in range(obj.benchmarks)]
            elif isinstance(obj.benchmarks, str):
                try:
                    benchmarks = json.loads(obj.benchmarks)
                except:
                    try:
                        benchmark_count = int(obj.benchmarks)
                        benchmarks = [
                            {"placeholder": True} for _ in range(benchmark_count)
                        ]
                    except:
                        benchmarks = []
        return benchmarks

    def get_isStarred(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return InterestingDataset.objects.filter(
                user=request.user, dataset=obj
            ).exists()
        return False


class PaperDetailSerializer(PaperListSerializer):
    datasets = serializers.SerializerMethodField()
    sourceCode = serializers.SerializerMethodField()
    citationsByYear = serializers.SerializerMethodField()
    conferenceRank = serializers.SerializerMethodField()
    conferenceAbbreviation = serializers.SerializerMethodField()
    is_interesting = serializers.SerializerMethodField()
    is_downloaded = serializers.SerializerMethodField()

    class Meta:
        model = Paper
        fields = [
            "id",
            "title",
            "authors",
            "venue",
            "venueType",
            "year",
            "keywords",
            "abstract",
            "downloadUrl",
            "impactFactor",
            "quartile",
            "citationsByYear",
            "doi",
            "method",
            "results",
            "conclusions",
            "bibtex",
            "sourceCode",
            "conferenceRank",
            "conferenceAbbreviation",
            "datasets",
            "is_interesting",
            "is_downloaded",
        ]

    def get_citationsByYear(self, obj):
        return obj.citations_count

    def get_datasets(self, obj):
        datasets = obj.datasets.all()
        datasets_list = []
        for dataset in datasets:
            datasets_list.append(
                {
                    "id": dataset.id,
                    "name": dataset.name,
                    "abbreviation": dataset.abbreviation,
                    "description": dataset.description,
                    "data_type": dataset.data_type,
                    "category": dataset.tasks.all().values_list("name", flat=True),
                    "size": dataset.size,
                    "format": dataset.format,
                    "source_url": dataset.source_url,
                    "license": dataset.license,
                }
            )
        return datasets_list

    def get_conferenceRank(self, obj):
        if obj.venue_type == "conference" and obj.conference:
            return obj.conference.rank
        else:
            return None

    def get_conferenceAbbreviation(self, obj):
        if obj.venue_type == "conference" and obj.conference:
            return obj.conference.abbreviation
        else:
            return None

    def get_sourceCode(self, obj):
        if obj.github_url:
            return obj.github_url
        else:
            return None

    def _get_request_user(self):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return request.user
        return None

    def get_is_interesting(self, obj):
        user = self._get_request_user()
        if not user:
            return False
        return obj.interested_users.filter(user=user).exists()

    def get_is_downloaded(self, obj):
        user = self._get_request_user()
        if not user:
            return False
        return obj.downloaded_users.filter(user=user).exists()


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"


class TaskListParamsSerializer(serializers.ModelSerializer):
    startDate = serializers.DateField(required=False)
    endDate = serializers.DateField(required=False)
    period = serializers.ChoiceField(
        choices=["day", "week", "month", "year"], required=False
    )
    page = serializers.IntegerField(default=1, required=False)
    pageSize = serializers.IntegerField(default=20, required=False)

    class Meta:
        model = Task
        fields = ["startDate", "endDate", "period", "page", "pageSize"]


class InterestingDatasetsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterestingDataset
        fields = "__all__"


class ConferenceListSerializer(serializers.ModelSerializer):
    papersCount = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()

    class Meta:
        model = Conference
        fields = [
            "id",
            "name",
            "abbreviation",
            "rank",
            "location",
            "url",
            "papersCount"
        ]

    def get_rank(self, obj):
        from .conference_ranks import display_conference_rank

        return display_conference_rank(obj.rank)

    def get_papersCount(self, obj):
        return obj.papers.count()
    

class ConferenceDetailSerializer(serializers.ModelSerializer):
    papersCount = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()

    class Meta:
        model = Conference
        fields = [
            "id",
            "name",
            "abbreviation",
            "rank",
            "location",
            "url",
            "papersCount",
            "created_at"
        ]

    def get_rank(self, obj):
        from .conference_ranks import display_conference_rank

        return display_conference_rank(obj.rank)

    def get_papersCount(self, obj):
        return obj.papers.count()
        
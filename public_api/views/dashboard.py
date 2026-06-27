import logging
from datetime import date, datetime, timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear
from ..error_responses import standard_error_response
from ..models import Paper, Dataset, Task
from ..serializers import PaperSerializer, TaskSerializer

logger = logging.getLogger(__name__)


def _inclusive_end_date(end_exclusive: date) -> date:
    return end_exclusive - timedelta(days=1)


def _bucket_key(value, period: str):
    """Normalize Trunc* values and bucket dates to a comparable lookup key."""
    if value is None:
        return None
    if isinstance(value, datetime):
        d = value.date()
    else:
        d = value
    if period == "daily":
        return d
    if period == "weekly":
        return d - timedelta(days=d.weekday())
    if period == "monthly":
        return (d.year, d.month)
    if period == "yearly":
        return d.year
    return d


def _build_time_range(start: date, end_exclusive: date, period: str) -> list:
    inclusive_end = _inclusive_end_date(end_exclusive)
    if period == "daily":
        return [start + timedelta(days=x) for x in range((end_exclusive - start).days + 1)]
    if period == "weekly":
        cursor = start - timedelta(days=start.weekday())
        buckets = []
        while cursor <= inclusive_end:
            buckets.append(cursor)
            cursor += timedelta(weeks=1)
        return buckets
    if period == "monthly":
        y, m = start.year, start.month
        buckets = []
        while (y, m) <= (inclusive_end.year, inclusive_end.month):
            buckets.append(date(y, m, 1))
            m += 1
            if m > 12:
                m = 1
                y += 1
        return buckets
    if period == "yearly":
        return [date(y, 1, 1) for y in range(start.year, inclusive_end.year + 1)]
    return []


def _period_bounds(bucket, period: str, inclusive_end: date) -> tuple[str, str]:
    if period == "daily":
        return str(bucket), str(bucket)
    if period == "weekly":
        week_end = min(bucket + timedelta(days=6), inclusive_end)
        return str(bucket), str(week_end)
    if period == "monthly":
        if bucket.month == 12:
            next_month = date(bucket.year + 1, 1, 1)
        else:
            next_month = date(bucket.year, bucket.month + 1, 1)
        month_end = min(next_month - timedelta(days=1), inclusive_end)
        return str(bucket), str(month_end)
    if period == "yearly":
        year_end = min(date(bucket.year, 12, 31), inclusive_end)
        return str(bucket), str(year_end)
    return str(bucket), str(bucket)


class Dashboard(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        start_date = request.query_params.get('startDate')
        end_date = datetime.strptime(request.query_params.get('endDate'), '%Y-%m-%d') + timedelta(days=1)
        period = request.query_params.get('period')
        
        try:
            paper_count = Paper.objects.filter(created_at__gte=start_date, created_at__lte=end_date).count()
            dataset_count = Dataset.objects.filter(created_at__gte=start_date, created_at__lte=end_date).count()
            
            response_data = {
                "paper_count": paper_count,
                "dataset_count": dataset_count,
            }
            
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = end_date.date()
            inclusive_end = _inclusive_end_date(end)

            period_config = {
                'daily': TruncDate('created_at'),
                'weekly': TruncWeek('created_at'),
                'monthly': TruncMonth('created_at'),
                'yearly': TruncYear('created_at'),
            }
            if period not in period_config:
                return Response({"error": "Invalid period"}, status=status.HTTP_400_BAD_REQUEST)

            annotation_func = period_config[period]
            time_range = _build_time_range(start, end, period)

            papers_per_period = Paper.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            ).annotate(
                date=annotation_func
            ).values('date').annotate(
                count=Count('id')
            ).order_by('date')

            counts_by_bucket = {
                _bucket_key(row["date"], period): row["count"]
                for row in papers_per_period
            }

            paper_count_details = []
            for bucket in time_range:
                count = counts_by_bucket.get(_bucket_key(bucket, period), 0)
                period_start, period_end = _period_bounds(bucket, period, inclusive_end)
                paper_count_details.append({
                    "period": {
                        "start": period_start,
                        "end": period_end,
                    },
                    "count": count,
                })
            
            response_data.update({
                "paper_count_detail": paper_count_details
            })

            papers_per_dataset = Dataset.objects.annotate(
                filtered_paper_count=Count(
                    'papers', 
                    filter=Q(
                        papers__created_at__gte=start_date, 
                        papers__created_at__lte=end_date
                    )
                )
            ).filter(
                filtered_paper_count__gt=0
            ).values(
                'id', 'name', 'filtered_paper_count'
            ).order_by('-filtered_paper_count')
            
            response_data.update({
                "papers_per_dataset": list(papers_per_dataset)
            })
            
            papers_per_task = Task.objects.annotate(
                filtered_paper_count=Count(
                    'papers', 
                    filter=Q(
                        papers__created_at__gte=start_date, 
                        papers__created_at__lte=end_date
                    )
                )
            ).filter(
                filtered_paper_count__gt=0
            )
            papers_task_detail = papers_per_task.values('id', 'name', 'filtered_paper_count').order_by('-filtered_paper_count')
            response_data.update({
                "papers_per_task": list(papers_task_detail)
            })
            trending_tasks = papers_per_task.values('id', 'name').order_by('-filtered_paper_count')[:5]
            response_data.update({
                "trending_tasks": list(trending_tasks)
            })
            return Response(response_data)
        except Exception:
            logger.exception("Dashboard stats failed")
            return standard_error_response(
                request,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "INTERNAL_SERVER_ERROR",
                "An unexpected error occurred while processing the request.",
            )

class TaskPaperAnalytics(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')
        
        if not start_date or not end_date:
            return Response(
                {"error": "Both startDate and endDate are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            papers_per_task = Task.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            ).annotate(
                filtered_paper_count=Count(
                    'papers',
                    filter=Q(
                        papers__created_at__gte=start_date,
                        papers__created_at__lte=end_date
                    )
                )
            ).filter(
                filtered_paper_count__gt=0
            ).order_by('-filtered_paper_count')
            
            top_20_tasks = papers_per_task[:20]
            
            top_20_task_ids = [task.id for task in top_20_tasks]
            
            top_papers = Paper.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                tasks__id__in=top_20_task_ids
            ).distinct().order_by('-views_count', '-citations_count', '-created_at')[:100]
            
            # Create task lookup and distribution
            task_distribution = []
            task_lookup = {}
            for task in top_20_tasks:
                task_data = {
                    'id': task.id,
                    'name': task.name,
                    'description': task.description,
                    'paper_count': task.filtered_paper_count,
                    'created_at': task.created_at
                }
                task_distribution.append(task_data)
                task_lookup[task.id] = task_data
            
            # Add task information to each paper
            papers_with_tasks = []
            papers_by_task = {}
            
            for paper in top_papers:
                paper_data = PaperSerializer(paper).data
                # Get all tasks associated with this paper from the top 20
                paper_tasks = paper.tasks.filter(id__in=top_20_task_ids)
                paper_task_info = []
                
                for task in paper_tasks:
                    task_info = {
                        'id': task.id,
                        'name': task.name,
                        'description': task.description
                    }
                    paper_task_info.append(task_info)
                    
                    # Group papers by task
                    if task.id not in papers_by_task:
                        papers_by_task[task.id] = {
                            'task_info': task_lookup[task.id],
                            'papers': []
                        }
                    papers_by_task[task.id]['papers'].append(paper_data)
                
                paper_data['tasks'] = paper_task_info
                paper_data['task_ids'] = [task.id for task in paper_tasks]
                papers_with_tasks.append(paper_data)
            
            # Convert papers_by_task to a list format for easier frontend handling
            papers_grouped_by_task = []
            for task_id, data in papers_by_task.items():
                papers_grouped_by_task.append({
                    'task_id': task_id,
                    'task_name': data['task_info']['name'],
                    'task_description': data['task_info']['description'],
                    'paper_count': len(data['papers']),
                    'papers': data['papers']
                })
            
            # Sort by number of papers descending
            papers_grouped_by_task.sort(key=lambda x: x['paper_count'], reverse=True)
            
            response_data = {
                "summary": {
                    "total_tasks_in_range": papers_per_task.count(),
                    "total_papers_in_range": Paper.objects.filter(
                        created_at__gte=start_date,
                        created_at__lte=end_date
                    ).count(),
                    "tasks_with_papers": papers_per_task.count(),
                    "top_20_tasks_count": len(top_20_task_ids),
                    "top_papers_count": len(top_papers)
                },
                "task_distribution": task_distribution,
                "papers_with_tasks": papers_with_tasks,
                "papers_grouped_by_task": papers_grouped_by_task,
                "task_lookup": task_lookup,
                "date_range": {
                    "start_date": start_date,
                    "end_date": end_date
                }
            }
            
            return Response(response_data)

        except Exception:
            logger.exception("Task paper analytics failed")
            return standard_error_response(
                request,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "INTERNAL_SERVER_ERROR",
                "An unexpected error occurred while processing the request.",
            )
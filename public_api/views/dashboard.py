from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear
from ..models import Paper, Dataset, Task
from ..serializers import PaperSerializer, TaskSerializer

class Dashboard(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')
        period = request.query_params.get('period')
        
        try:
            paper_count = Paper.objects.filter(created_at__gte=start_date, created_at__lte=end_date).count()
            dataset_count = Dataset.objects.filter(created_at__gte=start_date, created_at__lte=end_date).count()
            
            response_data = {
                "paper_count": paper_count,
                "dataset_count": dataset_count,
            }

            if period == 'daily':
                papers_per_day = Paper.objects.filter(
                    created_at__gte=start_date, 
                    created_at__lte=end_date
                ).annotate(
                    date=TruncDate('created_at')
                ).values('date').annotate(
                    count=Count('id')
                ).order_by('date')
                
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                date_range = [(start + timedelta(days=x)) for x in range((end - start).days + 1)]
                
                paper_count_details = []
                for date in date_range:
                    count = next((p["count"] for p in papers_per_day if p["date"] == date), 0)
                    paper_count_details.append({
                        "period": {
                            "start": str(date),
                            "end": str(date)
                        },
                        "count": count
                    })
                
                response_data.update({
                    "paper_count_detail": paper_count_details
                })
                
            elif period == 'weekly':
                papers_per_week = Paper.objects.filter(
                    created_at__gte=start_date, 
                    created_at__lte=end_date
                ).annotate(
                    week=TruncWeek('created_at')
                ).values('week').annotate(
                    count=Count('id')
                ).order_by('week')
                
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                week_range = []
                current = start - timedelta(days=start.weekday())
                while current <= end:
                    week_range.append(current)
                    current += timedelta(weeks=1)
                
                paper_count_details = []
                for week_start in week_range:
                    week_end = week_start + timedelta(days=6)
                    count = next((p["count"] for p in papers_per_week if p["week"].date() == week_start), 0)
                    paper_count_details.append({
                        "period": {
                            "start": str(week_start),
                            "end": str(week_end)
                        },
                        "count": count
                    })
                
                response_data.update({
                    "paper_count_detail": paper_count_details
                })
            elif period == 'monthly':
                papers_per_month = Paper.objects.filter(
                    created_at__gte=start_date, 
                    created_at__lte=end_date
                ).annotate(
                    month=TruncMonth('created_at')
                ).values('month').annotate(
                    count=Count('id')
                ).order_by('month')
                
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                month_range = []
                current = datetime(start.year, start.month, 1).date()
                while current <= end:
                    month_range.append(current)
                    if current.month == 12:
                        current = datetime(current.year + 1, 1, 1).date()
                    else:
                        current = datetime(current.year, current.month + 1, 1).date()
                
                paper_count_details = []
                for month_start in month_range:
                    if month_start.month == 12:
                        month_end = datetime(month_start.year + 1, 1, 1).date() - timedelta(days=1)
                    else:
                        month_end = datetime(month_start.year, month_start.month + 1, 1).date() - timedelta(days=1)
                    
                    count = next((p["count"] for p in papers_per_month if p["month"].date().replace(day=1) == month_start), 0)
                    paper_count_details.append({
                        "period": {
                            "start": str(month_start),
                            "end": str(month_end)
                        },
                        "count": count
                    })
                
                response_data.update({
                    "paper_count_detail": paper_count_details
                })
            elif period == 'yearly':
                papers_per_year = Paper.objects.filter(
                    created_at__gte=start_date, 
                    created_at__lte=end_date
                ).annotate(
                    year=TruncYear('created_at')
                ).values('year').annotate(
                    count=Count('id')
                ).order_by('year')
                
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                year_range = range(start.year, end.year + 1)
                
                paper_count_details = []
                for year in year_range:
                    year_start = datetime(year, 1, 1).date()
                    year_end = datetime(year, 12, 31).date()
                    
                    count = next((p["count"] for p in papers_per_year if p["year"].date().replace(day=1, month=1) == year_start), 0)
                    paper_count_details.append({
                        "period": {
                            "start": str(year_start),
                            "end": str(year_end)
                        },
                        "count": count
                    })
                
                response_data.update({
                    "paper_count_detail": paper_count_details
                })
            else:
                return Response({"error": "Invalid period"}, status=status.HTTP_400_BAD_REQUEST)
            
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
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
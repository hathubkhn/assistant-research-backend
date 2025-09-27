import time
import logging
from django.db import connection
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestProfilingMiddleware(MiddlewareMixin):
    """
    Middleware to profile all requests with timing and query information
    
    Add to MIDDLEWARE in settings.py:
    'public_api.middleware.RequestProfilingMiddleware',
    """
    
    def process_request(self, request):
        # Store timing info on the request object
        request._profiling_start_time = time.time()
        request._profiling_initial_queries = len(connection.queries)
        
        # Log request start
        logger.info(f"🚀 {request.method} {request.path} - Request started")
        
        return None
    
    def process_response(self, request, response):
        # Calculate total time
        if hasattr(request, '_profiling_start_time'):
            total_time = (time.time() - request._profiling_start_time) * 1000
            
            # Calculate query info
            if hasattr(request, '_profiling_initial_queries'):
                total_queries = len(connection.queries) - request._profiling_initial_queries
                
                # Calculate total query time
                query_time = 0
                if settings.DEBUG:  # Query timing only available in DEBUG mode
                    new_queries = connection.queries[request._profiling_initial_queries:]
                    query_time = sum(float(q['time']) for q in new_queries) * 1000
                
                # Log performance summary
                logger.info(
                    f"✅ {request.method} {request.path} - "
                    f"Status: {response.status_code}, "
                    f"Total: {total_time:.2f}ms, "
                    f"Queries: {total_queries} ({query_time:.2f}ms), "
                    f"Python: {total_time - query_time:.2f}ms"
                )
                
                # Log slow requests
                if total_time > 1000:  # > 1 second
                    logger.warning(f"🐌 SLOW REQUEST: {request.path} took {total_time:.2f}ms")
                
                # Log requests with many queries
                if total_queries > 10:
                    logger.warning(f"🗄️ HIGH QUERY COUNT: {request.path} executed {total_queries} queries")
                
                # Add timing headers to response (useful for frontend monitoring)
                response['X-Response-Time'] = f"{total_time:.2f}ms"
                response['X-Query-Count'] = str(total_queries)
                response['X-Query-Time'] = f"{query_time:.2f}ms"
        
        return response


class DetailedProfilingMiddleware(MiddlewareMixin):
    """
    More detailed profiling middleware that logs individual slow queries
    
    Only enable this in development/staging environments
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_query_threshold = 50  # ms
        self.many_queries_threshold = 5
    
    def __call__(self, request):
        # Store initial state
        request._profiling_start_time = time.time()
        request._profiling_initial_queries = len(connection.queries)
        
        # Process request
        response = self.get_response(request)
        
        # Analyze performance
        self._analyze_performance(request, response)
        
        return response
    
    def _analyze_performance(self, request, response):
        if not hasattr(request, '_profiling_start_time'):
            return
        
        total_time = (time.time() - request._profiling_start_time) * 1000
        initial_count = getattr(request, '_profiling_initial_queries', 0)
        new_queries = connection.queries[initial_count:]
        
        # Basic performance logging
        logger.info(
            f"📊 {request.method} {request.path} - "
            f"{total_time:.2f}ms, {len(new_queries)} queries"
        )
        
        # Analyze individual queries
        slow_queries = []
        total_query_time = 0
        
        for i, query in enumerate(new_queries):
            query_time = float(query['time']) * 1000
            total_query_time += query_time
            
            if query_time > self.slow_query_threshold:
                slow_queries.append({
                    'index': i + 1,
                    'time': query_time,
                    'sql': query['sql'][:200] + '...' if len(query['sql']) > 200 else query['sql']
                })
        
        # Log slow queries
        if slow_queries:
            logger.warning(f"🐌 Found {len(slow_queries)} slow queries for {request.path}:")
            for sq in slow_queries:
                logger.warning(f"   Query {sq['index']}: {sq['time']:.2f}ms - {sq['sql']}")
        
        # Log if too many queries
        if len(new_queries) > self.many_queries_threshold:
            logger.warning(
                f"🗄️ High query count for {request.path}: {len(new_queries)} queries, "
                f"{total_query_time:.2f}ms total query time"
            )
        
        # Performance breakdown
        python_time = total_time - total_query_time
        if total_time > 0:
            query_percentage = (total_query_time / total_time) * 100
            logger.info(
                f"⚡ Performance breakdown for {request.path}: "
                f"DB: {total_query_time:.2f}ms ({query_percentage:.1f}%), "
                f"Python: {python_time:.2f}ms ({100-query_percentage:.1f}%)"
            )


class APIEndpointProfilingMiddleware(MiddlewareMixin):
    """
    Specialized middleware for API endpoints that tracks common performance patterns
    """
    
    def process_request(self, request):
        # Only profile API endpoints
        if not request.path.startswith('/api/'):
            return None
        
        request._api_profiling_start = time.time()
        request._api_profiling_queries = len(connection.queries)
        
        # Log API request with parameters
        query_params = dict(request.GET.items()) if request.GET else {}
        logger.info(f"🔌 API {request.method} {request.path} - Params: {query_params}")
        
        return None
    
    def process_response(self, request, response):
        if not hasattr(request, '_api_profiling_start'):
            return response
        
        total_time = (time.time() - request._api_profiling_start) * 1000
        query_count = len(connection.queries) - request._api_profiling_queries
        
        # Determine performance category
        if total_time < 100:
            status_emoji = "🟢"  # Fast
        elif total_time < 500:
            status_emoji = "🟡"  # Medium
        else:
            status_emoji = "🔴"  # Slow
        
        # Log API response
        logger.info(
            f"{status_emoji} API {request.method} {request.path} - "
            f"Status: {response.status_code}, "
            f"Time: {total_time:.2f}ms, "
            f"Queries: {query_count}"
        )
        
        # Add performance headers for API monitoring
        response['X-API-Time'] = f"{total_time:.2f}"
        response['X-API-Queries'] = str(query_count)
        
        return response

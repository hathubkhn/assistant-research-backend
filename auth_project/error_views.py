"""
Django-level error handlers for URL resolution and server errors (JSON, unified shape).
"""

from django.http import JsonResponse

from public_api.error_responses import build_error_payload


def handler404(request, exception):
    _ = exception
    payload = build_error_payload(
        request,
        404,
        "Not Found",
        "RESOURCE_NOT_FOUND",
        "The requested resource was not found.",
    )
    return JsonResponse(payload, status=404, json_dumps_params={"ensure_ascii": False})


def handler403(request, exception=None):
    _ = exception
    payload = build_error_payload(
        request,
        403,
        "Forbidden",
        "PERMISSION_DENIED",
        "You do not have permission to perform this action.",
    )
    return JsonResponse(payload, status=403, json_dumps_params={"ensure_ascii": False})


def handler500(request):
    payload = build_error_payload(
        request,
        500,
        "Internal Server Error",
        "INTERNAL_SERVER_ERROR",
        "An unexpected error occurred. Please try again later.",
    )
    return JsonResponse(payload, status=500, json_dumps_params={"ensure_ascii": False})

"""
Normalize non-JSON or legacy JSON error responses under /api/ to the unified error format.
"""

from __future__ import annotations

import json

from django.http import JsonResponse

from .error_responses import build_error_payload

_STATUS_DEFAULTS = {
    401: (
        "Unauthorized",
        "AUTHENTICATION_REQUIRED",
        "Authentication credentials were not provided or are invalid.",
    ),
    403: (
        "Forbidden",
        "PERMISSION_DENIED",
        "You do not have permission to perform this action.",
    ),
    404: (
        "Not Found",
        "RESOURCE_NOT_FOUND",
        "The requested resource was not found.",
    ),
    405: (
        "Method Not Allowed",
        "INVALID_HTTP_METHOD",
        "This HTTP method is not allowed for this resource.",
    ),
    500: (
        "Internal Server Error",
        "INTERNAL_SERVER_ERROR",
        "An unexpected error occurred. Please try again later.",
    ),
}


def _is_standardized(body: dict) -> bool:
    required = {"status", "error", "code", "message", "path", "timestamp"}
    return isinstance(body, dict) and required.issubset(body.keys())


class StandardApiErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        path = getattr(request, "path", "") or ""
        if not path.startswith("/api/"):
            return response
        code = response.status_code
        if code not in _STATUS_DEFAULTS:
            return response
        content_type = response.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                raw = response.content.decode("utf-8") or "{}"
                body = json.loads(raw)
                if _is_standardized(body):
                    return response
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                pass
        error_name, internal_code, message = _STATUS_DEFAULTS[code]
        payload = build_error_payload(request, code, error_name, internal_code, message)
        return JsonResponse(
            payload,
            status=code,
            json_dumps_params={"ensure_ascii": False},
        )

"""
Unified API error payload helpers for JSON responses.
"""

from __future__ import annotations

from django.utils import timezone
from rest_framework.response import Response

_DEFAULT_ERROR_NAMES = {
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
}


def build_error_payload(
    request,
    status_code: int,
    error_name: str,
    internal_code: str,
    message: str,
) -> dict:
    path = getattr(request, "path", "") or ""
    return {
        "status": status_code,
        "error": error_name,
        "code": internal_code,
        "message": message,
        "path": path,
        "timestamp": timezone.now().isoformat(),
    }


def standard_error_response(
    request,
    status_code: int,
    internal_code: str,
    message: str,
    *,
    error_name: str | None = None,
) -> Response:
    name = error_name or _DEFAULT_ERROR_NAMES.get(status_code, "Error")
    payload = build_error_payload(request, status_code, name, internal_code, message)
    return Response(payload, status=status_code)

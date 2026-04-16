"""
DRF EXCEPTION_HANDLER: unified JSON for 401, 403, 404, 405, and safe 500 handling.
"""

from __future__ import annotations

import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .error_responses import build_error_payload

logger = logging.getLogger(__name__)


def _detail_to_message(detail) -> str:
    if detail is None:
        return "An error occurred."
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                for k, v in item.items():
                    parts.append(f"{k}: {v}" if v is not None else str(k))
            else:
                parts.append(str(item))
        return "; ".join(parts) if parts else "An error occurred."
    if isinstance(detail, dict):
        parts = [f"{k}: {v}" for k, v in detail.items()]
        return "; ".join(parts) if parts else "An error occurred."
    return str(detail)


def _message_from_exc_and_response(exc, response: Response | None) -> str:
    if hasattr(exc, "detail"):
        return _detail_to_message(exc.detail)
    if response is not None and response.data is not None:
        return _detail_to_message(response.data)
    return "An error occurred."


def custom_exception_handler(exc, context):
    request = context.get("request")

    # Map Django / ORM errors before DRF handler (DRF returns None for these)
    if isinstance(exc, Http404):
        msg = (str(exc) or "").strip()
        if not msg or msg == "Not Found":
            msg = "The requested resource was not found."
        payload = build_error_payload(
            request,
            status.HTTP_404_NOT_FOUND,
            "Not Found",
            "RESOURCE_NOT_FOUND",
            msg,
        )
        return Response(payload, status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, DjangoPermissionDenied):
        msg = str(exc) if str(exc) else "You do not have permission to perform this action."
        payload = build_error_payload(
            request,
            status.HTTP_403_FORBIDDEN,
            "Forbidden",
            "PERMISSION_DENIED",
            msg,
        )
        return Response(payload, status=status.HTTP_403_FORBIDDEN)

    if isinstance(exc, ObjectDoesNotExist):
        payload = build_error_payload(
            request,
            status.HTTP_404_NOT_FOUND,
            "Not Found",
            "RESOURCE_NOT_FOUND",
            "The requested resource was not found.",
        )
        return Response(payload, status=status.HTTP_404_NOT_FOUND)

    response = drf_exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception in API view")
        msg = "An unexpected error occurred. Please try again later."
        payload = build_error_payload(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal Server Error",
            "INTERNAL_SERVER_ERROR",
            msg,
        )
        return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    status_code = response.status_code
    if status_code not in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_405_METHOD_NOT_ALLOWED,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        return response

    if isinstance(exc, NotAuthenticated):
        internal_code, default_msg = "AUTHENTICATION_REQUIRED", "Authentication credentials were not provided or are invalid."
    elif isinstance(exc, AuthenticationFailed):
        internal_code, default_msg = "AUTHENTICATION_FAILED", "Invalid authentication credentials."
    elif isinstance(exc, PermissionDenied):
        internal_code, default_msg = "PERMISSION_DENIED", "You do not have permission to perform this action."
    elif isinstance(exc, (NotFound, Http404)):
        internal_code, default_msg = "RESOURCE_NOT_FOUND", "The requested resource was not found."
    elif isinstance(exc, MethodNotAllowed):
        internal_code, default_msg = "INVALID_HTTP_METHOD", "This HTTP method is not allowed for this resource."
    elif isinstance(exc, APIException) and status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        internal_code, default_msg = "INTERNAL_SERVER_ERROR", "An unexpected error occurred."
    else:
        mapping = {
            status.HTTP_401_UNAUTHORIZED: ("AUTHENTICATION_REQUIRED", "Authentication credentials were not provided or are invalid."),
            status.HTTP_403_FORBIDDEN: ("PERMISSION_DENIED", "You do not have permission to perform this action."),
            status.HTTP_404_NOT_FOUND: ("RESOURCE_NOT_FOUND", "The requested resource was not found."),
            status.HTTP_405_METHOD_NOT_ALLOWED: ("INVALID_HTTP_METHOD", "This HTTP method is not allowed for this resource."),
            status.HTTP_500_INTERNAL_SERVER_ERROR: ("INTERNAL_SERVER_ERROR", "An unexpected error occurred."),
        }
        internal_code, default_msg = mapping.get(
            status_code,
            ("INTERNAL_SERVER_ERROR", "An unexpected error occurred."),
        )

    message = _message_from_exc_and_response(exc, response)
    if not message or message == "Not Found":
        message = default_msg

    error_names = {
        status.HTTP_401_UNAUTHORIZED: "Unauthorized",
        status.HTTP_403_FORBIDDEN: "Forbidden",
        status.HTTP_404_NOT_FOUND: "Not Found",
        status.HTTP_405_METHOD_NOT_ALLOWED: "Method Not Allowed",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "Internal Server Error",
    }
    error_name = error_names.get(status_code, "Error")

    payload = build_error_payload(request, status_code, error_name, internal_code, message)

    extra_headers = {}
    if status_code == status.HTTP_401_UNAUTHORIZED:
        www = response.get("WWW-Authenticate")
        if www:
            extra_headers["WWW-Authenticate"] = www

    return Response(payload, status=status_code, headers=extra_headers)

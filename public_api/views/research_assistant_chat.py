import os
from typing import Any, Dict, List, Optional

import requests
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from public_api.models import ChatMessage, ChatSession

SESSION_TITLE_MAX_LEN = 80
DEFAULT_MESSAGE_LIMIT = 6
MAX_MESSAGE_LIMIT = 50


def _truncate_title(text: str) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= SESSION_TITLE_MAX_LEN:
        return cleaned or "New chat"
    return cleaned[: SESSION_TITLE_MAX_LEN - 3].rstrip() + "..."


def _normalize_session_title(text: str) -> str:
    cleaned = " ".join((text or "").split())
    max_len = ChatSession._meta.get_field("title").max_length
    if len(cleaned) <= max_len:
        return cleaned or "New chat"
    return cleaned[: max_len - 3].rstrip() + "..."


def _serialize_message(msg: ChatMessage) -> Dict[str, Any]:
    return {
        "id": str(msg.id),
        "role": msg.role,
        "content": msg.content,
        "papers": msg.papers or [],
        "citations": msg.citations or [],
        "using_fallback": msg.using_fallback,
        "created_at": msg.created_at.isoformat(),
    }


def _serialize_session(session: ChatSession, message_count: int = 0) -> Dict[str, Any]:
    return {
        "id": str(session.id),
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "message_count": message_count,
    }


def _get_user_session(session_id, user) -> ChatSession:
    return get_object_or_404(ChatSession, id=session_id, user=user)


def _fetch_messages_page(
    session: ChatSession, limit: int, before_id: Optional[str] = None
) -> tuple[List[ChatMessage], bool]:
    qs = ChatMessage.objects.filter(session=session)
    if before_id:
        ref = get_object_or_404(ChatMessage, id=before_id, session=session)
        qs = qs.filter(created_at__lt=ref.created_at)

    batch = list(qs.order_by("-created_at")[: limit + 1])
    has_more = len(batch) > limit
    if has_more:
        batch = batch[:limit]
    batch.reverse()
    return batch, has_more


def _call_research_assistant(query: str) -> Dict[str, Any]:
    """Call RAG service without user_id filter — papers are indexed as tenant \"global\"."""
    assistant_url = os.environ.get(
        "RESEARCH_ASSISTANT_URL", "http://research-assistant:8001"
    ).rstrip("/")
    payload = {"query": query}
    response = requests.post(
        f"{assistant_url}/query", json=payload, timeout=120
    )
    response.raise_for_status()
    return response.json()


class ChatSessionListView(APIView):
    """List chat sessions for the authenticated user."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        sessions = (
            ChatSession.objects.filter(user=request.user)
            .annotate(message_count=Count("messages"))
            .order_by("-updated_at")[:100]
        )
        data = [
            _serialize_session(s, message_count=s.message_count) for s in sessions
        ]
        return Response({"sessions": data})


class ChatSessionDetailView(APIView):
    """Rename or delete a chat session (messages cascade on delete)."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def patch(self, request, session_id):
        session = _get_user_session(session_id, request.user)
        raw_title = (request.data.get("title") or "").strip()
        if not raw_title:
            return Response(
                {"error": "Title is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        session.title = _normalize_session_title(raw_title)
        session.save(update_fields=["title", "updated_at"])
        message_count = session.messages.count()
        return Response(_serialize_session(session, message_count=message_count))

    def delete(self, request, session_id):
        session = _get_user_session(session_id, request.user)
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatSessionMessagesView(APIView):
    """Paginated messages for a session (newest batch first; use ?before= for older)."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request, session_id):
        session = _get_user_session(session_id, request.user)
        try:
            limit = int(request.query_params.get("limit", DEFAULT_MESSAGE_LIMIT))
        except (TypeError, ValueError):
            limit = DEFAULT_MESSAGE_LIMIT
        limit = max(1, min(limit, MAX_MESSAGE_LIMIT))
        before_id = request.query_params.get("before") or None

        messages, has_more = _fetch_messages_page(session, limit, before_id)
        return Response(
            {
                "session_id": str(session.id),
                "messages": [_serialize_message(m) for m in messages],
                "has_more": has_more,
            }
        )


class ResearchAssistantChatQueryView(APIView):
    """
    Run RAG query, persist user + assistant messages on the session.
    Creates a session when session_id is omitted (title = first question).
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        data = request.data
        query = (data.get("query") or "").strip()
        session_id = data.get("session_id")

        if not query:
            return Response(
                {"error": "Query is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if session_id:
            session = _get_user_session(session_id, request.user)
        else:
            session = ChatSession.objects.create(
                user=request.user,
                title=_truncate_title(query),
            )

        user_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_USER,
            content=query,
        )

        try:
            result = _call_research_assistant(query)
        except requests.RequestException as exc:
            return Response(
                {"error": f"Research assistant unavailable: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        assistant_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_ASSISTANT,
            content=result.get("answer", ""),
            papers=result.get("papers") or [],
            citations=result.get("citations") or [],
            using_fallback=result.get("using_fallback", False),
        )

        ChatSession.objects.filter(pk=session.pk).update(updated_at=timezone.now())

        return Response(
            {
                "session_id": str(session.id),
                "session_title": session.title,
                "query": query,
                "answer": assistant_msg.content,
                "papers": assistant_msg.papers,
                "citations": assistant_msg.citations,
                "using_fallback": assistant_msg.using_fallback,
                "user_message": _serialize_message(user_msg),
                "assistant_message": _serialize_message(assistant_msg),
            }
        )


class ResearchAssistantHealthView(APIView):
    """Proxy health check so the browser hits Django (public DNS), not Docker-internal RA host."""

    permission_classes = [AllowAny]

    def get(self, request):
        assistant_url = os.environ.get(
            "RESEARCH_ASSISTANT_URL", "http://research-assistant:8001"
        ).rstrip("/")
        try:
            response = requests.get(f"{assistant_url}/health", timeout=5)
            try:
                body = response.json()
            except ValueError:
                body = {"status": "unknown", "raw": response.text[:200]}
            return Response(body, status=response.status_code)
        except requests.RequestException as exc:
            return Response(
                {"status": "unavailable", "vector_db": "unavailable", "detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

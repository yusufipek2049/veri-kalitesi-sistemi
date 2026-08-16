"""Notification alanı HTTP route kayıtları."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException, Query as FastApiQuery, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from veri_kalitesi.identity import ActorContext
from veri_kalitesi.notifications.models import (
    NotificationChannel,
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationSubscription,
)
from veri_kalitesi.notifications.stream_hub import get_stream_hub

logger = logging.getLogger(__name__)

# Allowlisted payload keys safe for frontend consumption
_PAYLOAD_ALLOWLIST = frozenset(
    {
        "rule_code",
        "rule_name",
        "rule_id",
        "quality_rule_id",
        "decision",
        "threshold_value",
        "current_value",
        "dimension",
        "score",
        "issue_id",
        "issue_title",
        "execution_id",
        "dataset_id",
        "source_id",
        "source_name",
        "assignee_id",
        "assignee_name",
    }
)


class _BulkReadRequest(BaseModel):
    delivery_ids: list[str]


class _Resolver(Protocol):
    def resolve(self, request: Request) -> ActorContext | None: ...


class NotificationInboxPage(Protocol):
    """Bildirim kutusu sayfasının route tarafından tüketilen yüzeyi."""

    @property
    def deliveries(self) -> tuple[NotificationDelivery, ...]: ...

    @property
    def total_unread(self) -> int: ...

    @property
    def cursor(self) -> str | None: ...

    @property
    def has_more(self) -> bool: ...

    @property
    def failed_count(self) -> int: ...

    @property
    def today_count(self) -> int: ...


class NotificationQuery(Protocol):
    """Bildirim HTTP route'larının salt-okunur servis sözleşmesi."""

    def get_inbox(
        self,
        *,
        recipient_user_id: str,
        actor_user_id: str,
        status: NotificationDeliveryStatus | None = None,
        event_type: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> NotificationInboxPage: ...

    def count_unread(self, *, recipient_user_id: str, actor_user_id: str) -> int: ...

    def get_delivery(self, delivery_id: str, *, actor_user_id: str) -> NotificationDelivery: ...

    def get_event(self, event_id: str, *, actor_user_id: str) -> NotificationEvent: ...

    def get_events_by_ids(self, event_ids: list[str]) -> dict[str, NotificationEvent]: ...

    def list_subscriptions(
        self,
        *,
        user_id: str,
        actor_user_id: str,
        event_type: str | None = None,
    ) -> tuple[NotificationSubscription, ...]: ...

    def list_channels(
        self,
        *,
        status: str | None = None,
        channel_type: str | None = None,
    ) -> tuple[NotificationChannel, ...]: ...

    def mark_all_read(self, *, recipient_user_id: str, actor_user_id: str) -> int: ...


class NotificationDeliveryCommand(Protocol):
    """Bildirim HTTP route'larının okundu işaretleme sözleşmesi."""

    def mark_read(self, delivery_id: str, *, actor_user_id: str) -> NotificationDelivery: ...


def _resolve_actor(request: Request, resolver: _Resolver) -> ActorContext:
    actor_context = getattr(request.state, "actor_context", None) or resolver.resolve(request)
    if actor_context is None:
        raise HTTPException(status_code=401, detail="Authentication is required.")
    return actor_context


def _require_notification_query(service: NotificationQuery | None) -> NotificationQuery:
    if service is None:
        raise HTTPException(status_code=503, detail="Notification service unavailable.")
    return service


def _parse_delivery_status(status: str | None) -> NotificationDeliveryStatus | None:
    if status is None:
        return None

    try:
        return NotificationDeliveryStatus(status)
    except ValueError:
        return None


def _get_severity_for_event_type(event_type_value: str | None) -> str | None:
    """Derive severity from event type using the EVENT_SEVERITY mapping."""
    if not event_type_value:
        return None
    from veri_kalitesi.notifications.models import (
        EVENT_SEVERITY,
        NotificationEventType,
    )

    try:
        et = NotificationEventType(event_type_value)
        severity = EVENT_SEVERITY.get(et)
        return severity.value if severity else None
    except ValueError:
        return None


def _extract_safe_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Extract only allowlisted keys from event payload."""
    if not payload or not isinstance(payload, dict):
        return {}
    return {k: v for k, v in payload.items() if k in _PAYLOAD_ALLOWLIST}


def _delivery_to_dict(delivery: NotificationDelivery) -> dict:
    return {
        "delivery_id": delivery.delivery_id,
        "event_id": delivery.event_id,
        "recipient_user_id": delivery.recipient_user_id,
        "channel_id": delivery.channel_id,
        "status": delivery.status.value,
        "attempt_count": delivery.attempt_count,
        "created_at": delivery.created_at.isoformat(),
        "updated_at": delivery.updated_at.isoformat(),
        "delivered_at": (delivery.delivered_at.isoformat() if delivery.delivered_at else None),
        "read_at": (delivery.read_at.isoformat() if delivery.read_at else None),
    }


def _delivery_to_dict_with_event(
    delivery: NotificationDelivery,
    event: NotificationEvent | None,
) -> dict:
    result = _delivery_to_dict(delivery)
    event_type_value = event.event_type.value if event else None
    result["event_type"] = event_type_value
    result["scope_type"] = event.scope_type.value if event else None
    result["scope_id"] = event.scope_id if event else None
    result["source_ref"] = event.source_ref if event else None
    result["severity"] = _get_severity_for_event_type(event_type_value)
    result["payload"] = _extract_safe_payload(event.payload if event else None)
    return result


def register_notifications_routes(
    app: FastAPI,
    *,
    notification_query_service: NotificationQuery | None,
    notification_delivery_service: NotificationDeliveryCommand | None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """Notification alanının route'larını FastAPI uygulamasına kaydeder."""

    @app.get(
        "/api/v1/notifications/inbox",
        tags=["notifications"],
        response_model=dict,
    )
    def get_notification_inbox(
        request: Request,
        status: str | None = None,
        event_type: str | None = None,
        limit: int = FastApiQuery(ge=1, le=200, default=50),
        cursor: str | None = None,
    ) -> dict:
        query_service = _require_notification_query(notification_query_service)
        actor_context = _resolve_actor(request, resolver)
        page = query_service.get_inbox(
            recipient_user_id=actor_context.actor_id,
            actor_user_id=actor_context.actor_id,
            status=_parse_delivery_status(status),
            event_type=event_type,
            limit=limit,
            cursor=cursor,
        )
        # Batch-lookup events for scope/event_type enrichment
        event_ids = [d.event_id for d in page.deliveries]
        events_map: dict[str, NotificationEvent] = {}
        try:
            events_map = query_service.get_events_by_ids(event_ids)
        except Exception:
            pass
        return {
            "api_version": "v1",
            "data_origin": data_origin,
            "correlation_id": request.state.correlation_id,
            "total_unread": page.total_unread,
            "cursor": page.cursor,
            "has_more": page.has_more,
            "failed_count": page.failed_count,
            "today_count": page.today_count,
            "items": [
                _delivery_to_dict_with_event(d, events_map.get(d.event_id)) for d in page.deliveries
            ],
        }

    @app.get(
        "/api/v1/notifications/inbox/unread-count",
        tags=["notifications"],
        response_model=dict,
    )
    def get_unread_count(request: Request) -> dict:
        query_service = _require_notification_query(notification_query_service)
        actor_context = _resolve_actor(request, resolver)
        count = query_service.count_unread(
            recipient_user_id=actor_context.actor_id,
            actor_user_id=actor_context.actor_id,
        )
        return {
            "api_version": "v1",
            "data_origin": data_origin,
            "correlation_id": request.state.correlation_id,
            "unread_count": count,
        }

    @app.get(
        "/api/v1/notifications/deliveries/{delivery_id}",
        tags=["notifications"],
        response_model=dict,
    )
    def get_delivery_detail(delivery_id: str, request: Request) -> dict:
        query_service = _require_notification_query(notification_query_service)
        actor_context = _resolve_actor(request, resolver)
        delivery = query_service.get_delivery(delivery_id, actor_user_id=actor_context.actor_id)
        return {
            "api_version": "v1",
            "data_origin": data_origin,
            "correlation_id": request.state.correlation_id,
            "delivery": _delivery_to_dict(delivery),
        }

    @app.post(
        "/api/v1/notifications/deliveries/{delivery_id}/read",
        tags=["notifications"],
        response_model=dict,
    )
    def mark_delivery_read(delivery_id: str, request: Request) -> dict:
        actor_context = _resolve_actor(request, resolver)
        if notification_delivery_service is None:
            raise HTTPException(status_code=503, detail="Notification service unavailable.")
        delivery = notification_delivery_service.mark_read(
            delivery_id, actor_user_id=actor_context.actor_id
        )
        return {
            "api_version": "v1",
            "data_origin": data_origin,
            "correlation_id": request.state.correlation_id,
            "delivery": _delivery_to_dict(delivery),
        }

    @app.post(
        "/api/v1/notifications/inbox/mark-all-read",
        tags=["notifications"],
        response_model=dict,
    )
    def mark_all_read(request: Request) -> dict:
        query_service = _require_notification_query(notification_query_service)
        actor_context = _resolve_actor(request, resolver)
        marked = query_service.mark_all_read(
            recipient_user_id=actor_context.actor_id,
            actor_user_id=actor_context.actor_id,
        )
        return {
            "api_version": "v1",
            "data_origin": data_origin,
            "correlation_id": request.state.correlation_id,
            "marked_count": marked,
        }

    @app.post(
        "/api/v1/notifications/deliveries/bulk-read",
        tags=["notifications"],
        response_model=dict,
    )
    def bulk_mark_read(body: _BulkReadRequest, request: Request) -> dict:
        actor_context = _resolve_actor(request, resolver)
        if notification_delivery_service is None:
            raise HTTPException(status_code=503, detail="Notification service unavailable.")
        if not body.delivery_ids:
            return {
                "api_version": "v1",
                "data_origin": data_origin,
                "correlation_id": request.state.correlation_id,
                "marked_count": 0,
            }
        if len(body.delivery_ids) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 delivery IDs per request.")
        marked = 0
        for delivery_id in body.delivery_ids:
            try:
                notification_delivery_service.mark_read(
                    delivery_id, actor_user_id=actor_context.actor_id
                )
                marked += 1
            except Exception:
                pass  # Skip items that can't be marked (already read, not found, etc.)
        return {
            "api_version": "v1",
            "data_origin": data_origin,
            "correlation_id": request.state.correlation_id,
            "marked_count": marked,
        }

    @app.get(
        "/api/v1/notifications/events/{event_id}",
        tags=["notifications"],
        response_model=dict,
    )
    def get_event_detail(event_id: str, request: Request) -> dict:
        query_service = _require_notification_query(notification_query_service)
        actor_context = _resolve_actor(request, resolver)
        event = query_service.get_event(event_id, actor_user_id=actor_context.actor_id)
        return {
            "api_version": "v1",
            "data_origin": data_origin,
            "correlation_id": request.state.correlation_id,
            "event": {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "scope_type": event.scope_type.value,
                "scope_id": event.scope_id,
                "source_ref": event.source_ref,
                "correlation_id": event.correlation_id,
                "occurred_at": event.occurred_at.isoformat(),
                "published_at": (event.published_at.isoformat() if event.published_at else None),
                "severity": _get_severity_for_event_type(event.event_type.value),
                "payload": _extract_safe_payload(event.payload),
            },
        }

    @app.get(
        "/api/v1/notifications/subscriptions",
        tags=["notifications"],
        response_model=dict,
    )
    def list_subscriptions(
        request: Request,
        event_type: str | None = None,
    ) -> dict:
        query_service = _require_notification_query(notification_query_service)
        actor_context = _resolve_actor(request, resolver)
        subs = query_service.list_subscriptions(
            user_id=actor_context.actor_id,
            actor_user_id=actor_context.actor_id,
            event_type=event_type,
        )
        return {
            "api_version": "v1",
            "data_origin": data_origin,
            "correlation_id": request.state.correlation_id,
            "items": [
                {
                    "subscription_id": s.subscription_id,
                    "event_type": s.event_type.value,
                    "channel_id": s.channel_id,
                    "status": s.status.value,
                    "scope_type": (s.scope_type.value if s.scope_type else None),
                    "scope_id": s.scope_id,
                }
                for s in subs
            ],
        }

    @app.get(
        "/api/v1/notifications/channels",
        tags=["notifications"],
        response_model=dict,
    )
    def list_channels(request: Request) -> dict:
        query_service = _require_notification_query(notification_query_service)
        channels = query_service.list_channels()
        return {
            "api_version": "v1",
            "data_origin": data_origin,
            "correlation_id": request.state.correlation_id,
            "items": [
                {
                    "channel_id": ch.channel_id,
                    "name": ch.name,
                    "channel_type": ch.channel_type,
                    "status": ch.status.value,
                }
                for ch in channels
            ],
        }

    # ── SSE stream ─────────────────────────────────────────────────────

    @app.get(
        "/api/v1/notifications/stream",
        tags=["notifications"],
    )
    async def notification_stream(
        request: Request,
        user_id: str | None = FastApiQuery(default=None),
    ) -> StreamingResponse:
        """Server-Sent Events stream for real-time notifications.

        The client receives:
        - ``new_delivery`` events when a new notification is staged
        - ``keepalive`` comments every 30 seconds to prevent proxy timeouts

        Not: EventSource özel header gönderemez; kullanıcı kimliği ``user_id``
        query parametresi ile de iletilebilir.
        """
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            # EventSource query parametresinden gelen user_id'yi header'a çevir
            if user_id and not request.headers.get("X-Development-User-Id"):
                request.scope["headers"] = list(request.scope.get("headers", [])) + [
                    (b"x-development-user-id", user_id.encode("latin-1")),
                ]
            actor_context = resolver.resolve(request)
        if actor_context is None:
            raise HTTPException(status_code=401, detail="Authentication required.")

        hub = get_stream_hub()
        try:
            loop = asyncio.get_running_loop()
            hub.bind_loop(loop)
        except RuntimeError:
            pass

        stream = hub.register(actor_context.actor_id)

        async def event_generator():
            try:
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        message = await asyncio.wait_for(stream.queue.get(), timeout=30.0)
                        yield message
                    except asyncio.TimeoutError:
                        yield hub.keepalive()
            finally:
                hub.unregister(actor_context.actor_id, stream)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

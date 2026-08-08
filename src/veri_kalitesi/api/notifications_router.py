"""Notification alanı HTTP route kayıtları."""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import FastAPI, HTTPException, Query as FastApiQuery, Request

from veri_kalitesi.identity import ActorContext


class _Resolver(Protocol):
    def resolve(self, request: Request) -> ActorContext | None: ...


def _parse_delivery_status(status: str | None) -> object | None:
    if status is None:
        return None
    from veri_kalitesi.notifications.models import NotificationDeliveryStatus

    try:
        return NotificationDeliveryStatus(status)
    except ValueError:
        return None


def _delivery_to_dict(delivery: Any) -> dict:
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


def register_notifications_routes(
    app: FastAPI,
    *,
    notification_query_service: Any | None,
    notification_delivery_service: Any | None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """Notification alanının route'larını FastAPI uygulamasına kaydeder."""

    if notification_query_service is None:
        return

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
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            raise HTTPException(status_code=401, detail="Trusted session required.")
        page = notification_query_service.get_inbox(
            recipient_user_id=actor_context.actor_id,
            actor_user_id=actor_context.actor_id,
            status=_parse_delivery_status(status),
            event_type=event_type,
            limit=limit,
            cursor=cursor,
        )
        return {
            "api_version": "v1",
            "data_origin": data_origin,
            "correlation_id": request.state.correlation_id,
            "total_unread": page.total_unread,
            "cursor": page.cursor,
            "has_more": page.has_more,
            "items": [_delivery_to_dict(d) for d in page.deliveries],
        }

    @app.get(
        "/api/v1/notifications/inbox/unread-count",
        tags=["notifications"],
        response_model=dict,
    )
    def get_unread_count(request: Request) -> dict:
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            raise HTTPException(status_code=401, detail="Trusted session required.")
        count = notification_query_service.count_unread(
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
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            raise HTTPException(status_code=401, detail="Trusted session required.")
        delivery = notification_query_service.get_delivery(
            delivery_id, actor_user_id=actor_context.actor_id
        )
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
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            raise HTTPException(status_code=401, detail="Trusted session required.")
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

    @app.get(
        "/api/v1/notifications/events/{event_id}",
        tags=["notifications"],
        response_model=dict,
    )
    def get_event_detail(event_id: str, request: Request) -> dict:
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            raise HTTPException(status_code=401, detail="Trusted session required.")
        event = notification_query_service.get_event(event_id, actor_user_id=actor_context.actor_id)
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
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            raise HTTPException(status_code=401, detail="Trusted session required.")
        subs = notification_query_service.list_subscriptions(
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
        channels = notification_query_service.list_channels()
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

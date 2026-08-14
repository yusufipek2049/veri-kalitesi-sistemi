"""Notification SSE stream hub — per-actor event distribution.

Each connected SSE client registers an asyncio.Queue keyed by actor_id.
When a new delivery is staged, the hub fans out the event to all queues
registered for that recipient.  A background keepalive task prevents
proxy/load-balancer timeouts.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_KEEPALIVE_SECONDS = 30
_MAX_QUEUE_SIZE = 256


@dataclass
class _ActorStream:
    """A single SSE connection for an actor."""

    queue: asyncio.Queue[str] = field(
        default_factory=lambda: asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
    )


class NotificationStreamHub:
    """Fan-out hub for server-sent notification events.

    Thread-safety: all mutations happen on the event loop via
    ``call_soon_threadsafe`` so synchronous repository code can
    safely call ``publish``.
    """

    def __init__(self) -> None:
        self._streams: dict[str, list[_ActorStream]] = defaultdict(list)
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind the hub to the running event loop (called once at startup)."""
        self._loop = loop

    def register(self, actor_id: str) -> _ActorStream:
        """Create a new stream for *actor_id* and return it."""
        stream = _ActorStream()
        self._streams[actor_id].append(stream)
        logger.debug("SSE stream registered for actor %s", actor_id)
        return stream

    def unregister(self, actor_id: str, stream: _ActorStream) -> None:
        """Remove a previously registered stream."""
        streams = self._streams.get(actor_id, [])
        try:
            streams.remove(stream)
        except ValueError:
            pass
        if not streams:
            self._streams.pop(actor_id, None)
        logger.debug("SSE stream unregistered for actor %s", actor_id)

    def publish(self, actor_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Push an event to all streams for *actor_id*.

        Safe to call from a synchronous context — uses
        ``call_soon_threadsafe`` when a loop is bound.
        """
        payload = json.dumps({"type": event_type, "data": data}, default=str)
        message = f"event: {event_type}\ndata: {payload}\n\n"

        def _push() -> None:
            for stream in self._streams.get(actor_id, []):
                try:
                    stream.queue.put_nowait(message)
                except asyncio.QueueFull:
                    logger.warning("SSE queue full for actor %s — dropping event", actor_id)

        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(_push)
        else:
            _push()

    def keepalive(self) -> str:
        """Return an SSE comment line for keepalive."""
        return ": keepalive\n\n"

    @property
    def active_count(self) -> int:
        """Total number of active streams across all actors."""
        return sum(len(streams) for streams in self._streams.values())


# Module-level singleton — created once, shared via app.state
_global_hub: NotificationStreamHub | None = None


def get_stream_hub() -> NotificationStreamHub:
    """Return the global stream hub, creating it if needed."""
    global _global_hub
    if _global_hub is None:
        _global_hub = NotificationStreamHub()
    return _global_hub

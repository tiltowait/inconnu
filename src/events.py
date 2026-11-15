"""In-process pub/sub for character changes, streamed to the web app."""

import asyncio
from collections import defaultdict
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from enum import StrEnum


class CharEventType(StrEnum):
    """What happened to a character. Streams send the value as the message."""

    CHANGED = "changed"
    DELETED = "deleted"
    CLOSED = "closed"
    """Ends a stream without being sent; the client reconnects on its own."""


class CharEvents:
    """Notifies subscribers when a character changes. Each subscriber has a
    one-slot queue, so a burst of saves collapses into one event, and a slow
    subscriber can't grow memory without limit."""

    def __init__(self):
        self._subs: defaultdict[str, set[asyncio.Queue[CharEventType]]] = defaultdict(set)
        self._closed = False

    def subscribers(self, oid: str) -> int:
        """The number of subscribers to a character."""
        return len(self._subs.get(oid, ()))

    def publish(self, oid: str, event=CharEventType.CHANGED):
        """Notify a character's subscribers. A subscriber with an event still
        waiting keeps it, unless this is a deletion, which replaces it."""
        for queue in self._subs.get(oid, ()):
            if event == CharEventType.DELETED:
                _replace(queue, event)
            else:
                with suppress(asyncio.QueueFull):
                    queue.put_nowait(event)

    def open(self):
        """Let new streams run again, after a close()."""
        self._closed = False

    def close(self):
        """End every stream, now and later (until open()), so the server can
        shut down without waiting on them."""
        self._closed = True
        for queues in self._subs.values():
            for queue in queues:
                waiting = _take(queue)
                # A waiting deletion ends the stream too, and the client must
                # hear of it
                if waiting == CharEventType.DELETED:
                    queue.put_nowait(waiting)
                else:
                    queue.put_nowait(CharEventType.CLOSED)

    @asynccontextmanager
    async def subscribe(self, oid: str) -> AsyncGenerator[asyncio.Queue[CharEventType]]:
        """Subscribe to a character's events for the life of the context."""
        queue: asyncio.Queue[CharEventType] = asyncio.Queue(maxsize=1)
        if self._closed:
            queue.put_nowait(CharEventType.CLOSED)
        self._subs[oid].add(queue)
        try:
            yield queue
        finally:
            self._subs[oid].discard(queue)
            if not self._subs[oid]:
                del self._subs[oid]


def _take(queue: asyncio.Queue[CharEventType]) -> CharEventType | None:
    """Take the event waiting in the queue, if any."""
    try:
        return queue.get_nowait()
    except asyncio.QueueEmpty:
        return None


def _replace(queue: asyncio.Queue[CharEventType], event: CharEventType):
    """Put an event in the queue, replacing any event still waiting."""
    _take(queue)
    queue.put_nowait(event)


char_events = CharEvents()

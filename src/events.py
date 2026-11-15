"""In-process pub/sub for character changes, streamed to the web app."""

import asyncio
from collections import defaultdict
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress


class CharEvents:
    """Notifies subscribers when a character changes. Each subscriber has a
    one-slot queue, so a burst of saves collapses into one event, and a slow
    subscriber can't grow memory without limit."""

    def __init__(self):
        self._subs: defaultdict[str, set[asyncio.Queue[str]]] = defaultdict(set)

    def subscribers(self, oid: str) -> int:
        """The number of subscribers to a character."""
        return len(self._subs.get(oid, ()))

    def publish(self, oid: str, event="changed"):
        """Notify a character's subscribers. A subscriber with an event still
        waiting keeps it, unless this is a deletion, which replaces it."""
        for queue in self._subs.get(oid, ()):
            if event == "deleted":
                with suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            with suppress(asyncio.QueueFull):
                queue.put_nowait(event)

    @asynccontextmanager
    async def subscribe(self, oid: str) -> AsyncGenerator[asyncio.Queue[str]]:
        """Subscribe to a character's events for the life of the context."""
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1)
        self._subs[oid].add(queue)
        try:
            yield queue
        finally:
            self._subs[oid].discard(queue)
            if not self._subs[oid]:
                del self._subs[oid]


char_events = CharEvents()

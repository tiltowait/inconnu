"""Tests for events.py."""

import pytest

from events import CharEvents

OID = "abc123"


@pytest.fixture
def events() -> CharEvents:
    """A fresh pub/sub with no subscribers."""
    return CharEvents()


async def test_subscriber_receives_event(events: CharEvents):
    """A subscriber gets the character's events."""
    async with events.subscribe(OID) as queue:
        events.publish(OID)
        assert queue.get_nowait() == "changed"


async def test_other_characters_are_ignored(events: CharEvents):
    """A subscriber doesn't hear about other characters."""
    async with events.subscribe(OID) as queue:
        events.publish("other")
        assert queue.empty()


async def test_events_coalesce(events: CharEvents):
    """A burst of saves collapses into one waiting event."""
    async with events.subscribe(OID) as queue:
        for _ in range(5):
            events.publish(OID)
        assert queue.qsize() == 1


async def test_deletion_replaces_waiting_event(events: CharEvents):
    """A deletion isn't lost behind a waiting change."""
    async with events.subscribe(OID) as queue:
        events.publish(OID)
        events.publish(OID, "deleted")
        assert queue.get_nowait() == "deleted"
        assert queue.empty()


async def test_every_subscriber_receives_event(events: CharEvents):
    """Each viewer of a character gets their own event."""
    async with events.subscribe(OID) as first, events.subscribe(OID) as second:
        events.publish(OID)
        assert first.get_nowait() == "changed"
        assert second.get_nowait() == "changed"


async def test_unsubscribe_cleans_up(events: CharEvents):
    """Leaving the context removes the subscriber, and the character with its
    last one."""
    async with events.subscribe(OID):
        async with events.subscribe(OID):
            assert events.subscribers(OID) == 2
        assert events.subscribers(OID) == 1
    assert events.subscribers(OID) == 0
    assert OID not in events._subs


def test_publish_without_subscribers(events: CharEvents):
    """Publishing to a character nobody watches does nothing."""
    events.publish(OID)
    assert OID not in events._subs

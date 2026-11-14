"""VChar sub-document tests."""

from datetime import UTC, datetime

import pytest
from beanie.odm.utils.encoder import Encoder

from models.vchardocs import CAREER_STATS_LIVE, VCharLog


@pytest.mark.parametrize(
    "name,key",
    [
        ("hunger_slaked", "slake"),
        ("remorse_checks", "remorse"),
        ("remorse_failures", "degen"),
        ("rouse_checks", "rouse"),
        ("stains_gained", "stains"),
        ("times_awakened", "awaken"),
        ("times_blushed", "blush"),
        ("times_frenzied", "frenzy"),
    ],
)
def test_log_legacy_keys(name: str, key: str):
    """Test that renamed counters keep their old database keys but show their
    clear names to the API."""
    log = VCharLog.model_validate({key: 7})
    assert getattr(log, name) == 7

    # FastAPI dumps by alias
    for dumped in (log.model_dump(), log.model_dump(by_alias=True)):
        assert dumped[name] == 7
        assert key not in dumped

    stored = Encoder().encode(log)
    assert stored[key] == 7
    assert name not in stored


def test_log_remorse_successes_serialized_not_stored():
    """Test that Remorse successes go to the API but not to the database."""
    log = VCharLog.model_validate({"remorse": 5, "degen": 2})

    assert log.model_dump()["remorse_successes"] == 3
    assert "remorse_successes" not in Encoder().encode(log)


@pytest.mark.parametrize(
    "created,incomplete",
    [
        (datetime(2025, 1, 1, tzinfo=UTC), True),
        (datetime(2025, 1, 1), True),  # Naive, as loaded from the database
        (CAREER_STATS_LIVE, False),
        (datetime(2027, 1, 1), False),
    ],
)
def test_log_incomplete_since(created: datetime, incomplete: bool):
    """Test that characters older than a counter flag it as incomplete."""
    log = VCharLog(created=created)

    if incomplete:
        assert log.incomplete_since == VCharLog.TRACKING_STARTED
    else:
        assert log.incomplete_since == {}
    assert "incomplete_since" in log.model_dump()
    assert "incomplete_since" not in Encoder().encode(log)


def test_log_tracking_started_names_real_fields():
    """Test that every tracked counter is a field the API sends by that name."""
    dumped = VCharLog().model_dump(by_alias=True)

    for field in VCharLog.TRACKING_STARTED:
        assert field in VCharLog.model_fields
        assert field in dumped

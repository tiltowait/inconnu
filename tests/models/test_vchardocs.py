"""VChar sub-document tests."""

import pytest
from beanie.odm.utils.encoder import Encoder

from models.vchardocs import VCharLog


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

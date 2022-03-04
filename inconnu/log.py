"""log.py - Logging facilities."""
# pylint: disable=too-few-public-methods

import datetime

import inconnu


async def log_event(event_key, **context):
    """Log a bot event."""
    log = inconnu.db.log

    if event_key in ["update", "update_error", "roll_error", "macro_update_error"]:
        await log.insert_one({
            "date": datetime.datetime.utcnow(),
            "event": event_key,
            "context": context
        })
    else:
        raise KeyError("Invalid event key:", event_key)

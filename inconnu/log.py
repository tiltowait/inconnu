"""log.py - Logging facilities."""

import datetime
import os

import pymongo


class Log:
    """Logs various events."""
    _CLIENT = None
    _LOG = None


    @classmethod
    def log(cls, event_key, **context):
        """Log a bot event."""
        Log._prepare()

        if event_key in ["update", "update_error", "roll_error", "macro_update_error"]:
            Log._LOG.insert_one({
                "date": datetime.datetime.utcnow(),
                "event": event_key,
                "context": context
            })
        else:
            raise KeyError("Invalid event key:", event_key)


    @classmethod
    def _prepare(cls):
        """Prepare the database."""
        try:
            Log._CLIENT.admin.command('ismaster')
        except (AttributeError, pymongo.errors.ConnectionFailure):
            Log._CLIENT = None
        finally:
            if Log._CLIENT is None:
                mongo = pymongo.MongoClient(os.environ["MONGO_URL"])
                Log._CLIENT = mongo
                Log._LOG = mongo.inconnu.log

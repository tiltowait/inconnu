"""
Logger object
=============
The Kivy `Logger` class provides a singleton logger instance. This instance
exposes a standard Python
`logger <https://docs.python.org/3/library/logging.html>`_ object but adds
some convenient features.
All the standard logging levels are available : `trace`, `debug`, `info`,
`warning`, `error` and `critical`.
Example Usage
-------------
Use the `Logger` as you would a standard Python logger. ::
    from logger import Logger
    Logger.info('title: This is a info message.')
    Logger.debug('title: This is a debug message.')
    try:
        raise Exception('bleh')
    except Exception:
        Logger.exception('Something happened!')
The message passed to the logger is split into two parts separated by a colon
(:). The first part is used as a title and the second part is used as the
message. This way, you can "categorize" your messages easily. ::
    Logger.info('Application: This is a test')
    # will appear as
    [INFO   ] [Application ] This is a test
You can change the logging level at any time using the `setLevel` method. ::
    from logger import Logger, LOG_LEVELS
    Logger.setLevel(LOG_LEVELS["debug"])
Features
--------
Although you are free to use standard python loggers, the Kivy `Logger` offers
some solid benefits and useful features. These include:
* simplied usage (single instance, simple configuration, works by default)
* color-coded output
* output to `stdout` by default
* message categorization via colon separation
* access to log history even if logging is disabled
* built-in handling of various cross-platform considerations
Kivys' logger was designed to be used with kivy apps and makes logging from
Kivy apps more convenient.
Logger Configuration
--------------------
The Logger can be controlled via the config/logging.py configuration file
Logger History
--------------
Even if the logger is not enabled, you still have access to the last 100
messages::
    from logger import LoggerHistory
    print(LoggerHistory.history)
"""
# pylint: disable=invalid-name

import copy
import logging
import logging.handlers
import os
import pathlib
import sys
from datetime import datetime, timezone
from functools import partial

import boto3

import config.logging as config

__all__ = ("Logger", "LOG_LEVELS", "COLORS", "LoggerHistory", "file_log_handler")


BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = list(range(8))

# These are the sequences need to get colored output
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"

previous_stderr = sys.stderr


def formatter_message(message, use_color=True):
    if use_color:
        message = message.replace("$RESET", RESET_SEQ)
        message = message.replace("$BOLD", BOLD_SEQ)
    else:
        message = message.replace("$RESET", "").replace("$BOLD", "")
    return message


COLORS = {
    "TRACE": MAGENTA,
    "WARNING": YELLOW,
    "INFO": GREEN,
    "DEBUG": CYAN,
    "CRITICAL": RED,
    "ERROR": RED,
}

logging.TRACE = 9
LOG_LEVELS = {
    "trace": logging.TRACE,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


class FileHandler(logging.Handler):
    history = []
    filename = "log.txt"
    fd = None
    log_dir = "logs"
    encoding = "utf-8"
    last_update = datetime.utcnow()

    def purge_logs(self):
        """Purge logs which exceed the maximum amount of log files,
        starting with the oldest creation timestamp (or edit-timestamp on Linux)
        """

        if not self.log_dir:
            return

        maxfiles = config.log_maxfiles

        # Get path to log directory
        log_dir = pathlib.Path(self.log_dir)

        if maxfiles < 0:  # No log file limit set
            return

        Logger.info("Logger: Purge log fired. Processing...")

        # Get all files from log directory and corresponding creation timestamps
        files = [(item, item.stat().st_ctime) for item in log_dir.iterdir() if item.is_file()]
        # Sort files by ascending timestamp
        files.sort(key=lambda x: x[1])

        for file, _ in files[: (-maxfiles or len(files))]:
            # More log files than allowed maximum,
            # delete files, starting with oldest creation timestamp
            # (or edit-timestamp on Linux)
            try:
                file.unlink()
            except (PermissionError, FileNotFoundError) as e:
                Logger.info(f"Logger: Skipped file {file}, {repr(e)}")

        Logger.info("Logger: Purge finished!")

    def _configure(self, *largs, **kwargs):
        from time import strftime

        log_dir = config.log_dir
        log_name = config.log_name

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.log_dir = log_dir

        pattern = log_name.replace("%_", "@@NUMBER@@")
        pattern = os.path.join(log_dir, strftime(pattern))
        n = 0
        while True:
            filename = pattern.replace("@@NUMBER@@", str(n))
            if not os.path.exists(filename):
                break
            n += 1
            if n > 10000:  # prevent maybe flooding ?
                raise Exception("Too many logfile, remove them")

        if FileHandler.filename == filename and FileHandler.fd is not None:
            return

        FileHandler.filename = filename
        if FileHandler.fd not in (None, False):
            FileHandler.fd.close()
        FileHandler.fd = open(filename, "w", encoding=FileHandler.encoding)
        Logger.info("Logger: Record log in %s" % filename)

    def _write_message(self, record):
        if FileHandler.fd in (None, False):
            return

        now = datetime.utcnow()
        if now.day != self.last_update.day:
            # The day rolled over, so start a new log
            self.last_update = now
            self._configure()

        msg = self.format(record)
        stream = FileHandler.fd
        fs = "%s\n"
        stream.write("[%-7s] " % record.levelname)
        stream.write(fs % msg)
        stream.flush()

    def emit(self, message):
        # during the startup, store the message in the history
        if Logger.logfile_activated is None:
            FileHandler.history += [message]
            return

        # startup done, if the logfile is not activated, avoid history.
        if Logger.logfile_activated is False:
            FileHandler.history = []
            return

        if FileHandler.fd is None:
            try:
                self._configure()
            except Exception:
                # deactivate filehandler...
                if FileHandler.fd not in (None, False):
                    FileHandler.fd.close()
                FileHandler.fd = False
                Logger.exception("Error while activating FileHandler logger")
                return
            while FileHandler.history:
                _message = FileHandler.history.pop()
                self._write_message(_message)

        self._write_message(message)


class LoggerHistory(logging.Handler):

    history = []

    def emit(self, message):
        LoggerHistory.history = [message] + LoggerHistory.history[:100]

    @classmethod
    def clear_history(cls):
        del cls.history[:]

    def flush(self):
        super(LoggerHistory, self).flush()
        self.clear_history()


class ColoredFormatter(logging.Formatter):
    def __init__(self, msg, use_color=True):
        logging.Formatter.__init__(self, msg)
        self.use_color = use_color

    def format(self, record):
        """Apply terminal color code to the record"""
        # deepcopy so we do not mess up the record for other formatters
        record = copy.deepcopy(record)
        try:
            msg = record.msg.split(":", 1)
            if len(msg) == 2:
                record.msg = "[%-12s]%s" % (msg[0], msg[1])
        except:
            pass
        levelname = record.levelname
        if record.levelno == logging.TRACE:
            levelname = "TRACE"
            record.levelname = levelname
        if self.use_color and levelname in COLORS:
            levelname_color = COLOR_SEQ % (30 + COLORS[levelname]) + levelname + RESET_SEQ
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)


class ConsoleHandler(logging.StreamHandler):
    def filter(self, record):
        try:
            msg = record.msg
            k = msg.split(":", 1)
            if k[0] == "stderr" and len(k) == 2:
                previous_stderr.write(k[1] + "\n")
                return False
        except:
            pass
        return True


class CloudWatchHandler(logging.handlers.BufferingHandler):
    """A handler that flushes to AWS CloudWatch Logs."""

    LOG_GROUP_NAME = "Inconnu"

    def __init__(self, capacity=50):
        logging.handlers.BufferingHandler.__init__(self, capacity)
        self.last_event = None
        self.last_flush = None

        # AWS stuff
        self.cloudwatch = boto3.client("logs")
        self.log_stream_name = None
        self.next_sequence_token = None

        self.create_log_stream()

    def create_log_stream(self):
        """Create a log stream based on the current time."""
        fmt = "%Y-%m-%d_%H-%M-%S"
        log_start = datetime.now(timezone.utc)
        self.log_stream_name = log_start.strftime(fmt)
        self.cloudwatch.create_log_stream(
            logGroupName=self.LOG_GROUP_NAME, logStreamName=self.log_stream_name
        )

    def process_time(self):
        """Set the last event time and create a new log stream if new date."""
        now = datetime.now(timezone.utc)
        if self.last_event is not None:
            if now.day != self.last_event.day:
                self.create_log_stream()
        self.last_event = now

    def emit(self, record):
        """Add the record to the buffer, with a timestamp."""
        msg = self.format(record)

        if ":" in msg:
            msg = msg.split(":", 1)
            msg = f"[{msg[0]}]{msg[1]}"

        msg = "[" + record.levelname + "." * (7 - len(record.levelname)) + "]" + msg
        timestamp = datetime.now(timezone.utc).timestamp() * 1000

        self.buffer.append({"timestamp": int(timestamp), "message": msg})

        self.process_time()
        if self.shouldFlush(record):
            self.flush()

    def shouldFlush(self, record) -> bool:
        """We should flush if the buffer is full and it's been > 5 seconds."""
        if self.last_flush is not None:
            # AWS limits us to one update every 5 seconds
            delta = self.last_event - self.last_flush
            if delta.seconds < 5:
                return False

        return super().shouldFlush(record)

    def flush(self):
        """Upload the events to CloudWatch Logs and flush."""
        if self.next_sequence_token:
            response = self.cloudwatch.put_log_events(
                logGroupName=self.LOG_GROUP_NAME,
                logStreamName=self.log_stream_name,
                logEvents=self.buffer,
                sequenceToken=self.next_sequence_token,
            )
        else:
            response = self.cloudwatch.put_log_events(
                logGroupName=self.LOG_GROUP_NAME,
                logStreamName=self.log_stream_name,
                logEvents=self.buffer,
            )

        self.next_sequence_token = response["nextSequenceToken"]
        del self.buffer[:]
        self.last_flush = datetime.now(timezone.utc)


class LogFile(object):
    def __init__(self, channel, func):
        self.buffer = ""
        self.func = func
        self.channel = channel
        self.errors = ""

    def write(self, s):
        s = self.buffer + s
        self.flush()
        f = self.func
        channel = self.channel
        lines = s.split("\n")
        for l in lines[:-1]:
            f("%s: %s" % (channel, l))
        self.buffer = lines[-1]

    def flush(self):
        return

    def isatty(self):
        return False


def logger_config_update(value):
    if LOG_LEVELS.get(value) is None:
        raise AttributeError("Loglevel {0!r} doesn't exists".format(value))
    Logger.setLevel(level=LOG_LEVELS.get(value))


#: Inconnu default logger instance
Logger = logging.getLogger("inconnu")
Logger.logfile_activated = True
Logger.trace = partial(Logger.log, logging.TRACE)
logger_config_update(config.log_level)

# Set the Inconnu logger as the default
logging.root = Logger

Logger.addHandler(LoggerHistory())
Logger.addHandler(CloudWatchHandler())

file_log_handler = None
if config.log_to_file:
    file_log_handler = FileHandler()
    Logger.addHandler(file_log_handler)

# Use the custom handler instead of streaming one.
if "INCONNU_NO_CONSOLELOG" not in os.environ:
    if hasattr(sys, "_in_logging_handler"):
        Logger.addHandler(getattr(sys, "_in_logging_handler"))
    else:
        use_color = (
            os.environ.get("WT_SESSION")
            or os.environ.get("COLORTERM") == "truecolor"
            or os.environ.get("PYCHARM_HOSTED") == "1"
            or os.environ.get("TERM")
            in (
                "rxvt",
                "rxvt-256color",
                "rxvt-unicode",
                "rxvt-unicode-256color",
                "xterm",
                "xterm-256color",
            )
        )
        if not use_color:
            # No additional control characters will be inserted inside the
            # levelname field, 7 chars will fit "WARNING"
            color_fmt = formatter_message("[%(levelname)-7s] %(message)s", use_color)
        else:
            # levelname field width need to take into account the length of the
            # color control codes (7+4 chars for bold+color, and reset)
            color_fmt = formatter_message("[%(levelname)-18s] %(message)s", use_color)
        formatter = ColoredFormatter(color_fmt, use_color=use_color)
        console = ConsoleHandler()
        console.setFormatter(formatter)
        Logger.addHandler(console)

# install stderr handlers
sys.stderr = LogFile("stderr", Logger.warning)

if not config.log_to_file:
    Logger.warning("LOGGER: Log saving disabled")

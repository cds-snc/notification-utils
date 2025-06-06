import logging
import logging.handlers
import re
import sys
from itertools import product
from pathlib import Path
from time import monotonic
from typing import Any

from flask import g, request
from flask.ctx import has_request_context
from pythonjsonlogger.jsonlogger import JsonFormatter as BaseJSONFormatter

LOG_FORMAT = "%(asctime)s %(app_name)s %(name)s %(levelname)s " '%(request_id)s "%(message)s" [in %(pathname)s:%(lineno)d]'
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

regex_pattern_for_replace_api_signed_secret = "[a-zA-Z0-9]{51}\.[a-zA-Z0-9-_]{27}"  # noqa: W605

logger = logging.getLogger(__name__)


def build_log_line(extra_fields):
    fields = []
    if "service_id" in extra_fields:
        fields.append(str(extra_fields.get("service_id")))
    standard_fields = [extra_fields.get("method"), extra_fields.get("url"), extra_fields.get("status")]
    fields += [str(field) for field in standard_fields if field is not None]
    if "time_taken" in extra_fields:
        fields.append(extra_fields.get("time_taken"))
    return " ".join(fields)


def build_statsd_line(extra_fields):
    fields = []
    if "service_id" in extra_fields:
        if extra_fields.get("service_id") == "notify-admin":
            fields = [str(extra_fields.get("service_id"))]
        else:
            fields = ["service-id", str(extra_fields.get("service_id"))]
    standard_fields = [extra_fields.get("method"), extra_fields.get("endpoint"), extra_fields.get("status")]
    fields += [str(field) for field in standard_fields if field is not None]
    return ".".join(fields)


def init_app(app, statsd_client=None):
    app.config.setdefault("NOTIFY_LOG_LEVEL", "INFO")
    app.config.setdefault("NOTIFY_APP_NAME", "none")
    app.config.setdefault("NOTIFY_LOG_PATH", "./log/application.log")

    @app.after_request
    def after_request(response):
        extra_fields = {"method": request.method, "url": request.url, "status": response.status_code}

        if "service_id" in g:
            extra_fields.update({"service_id": g.service_id})

        if "start" in g:
            extra_fields.update({"time_taken": (monotonic() - g.start) * 1000})

        if "endpoint" in g:
            extra_fields.update({"endpoint": g.endpoint})

        record_stats(statsd_client, extra_fields)

        return response

    logging.getLogger().addHandler(logging.NullHandler())

    del app.logger.handlers[:]

    ensure_log_path_exists(app.config["NOTIFY_LOG_PATH"])
    handlers = get_handlers(app)
    loglevel = logging.getLevelName(app.config["NOTIFY_LOG_LEVEL"])
    loggers = [app.logger, logging.getLogger("utils")]
    for current_logger, handler in product(loggers, handlers):
        current_logger.addHandler(handler)
        current_logger.setLevel(loglevel)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("s3transfer").setLevel(logging.WARNING)
    app.logger.info("Logging configured")


def record_stats(statsd_client, extra_fields):
    if not statsd_client:
        return
    stats = [build_statsd_line(extra_fields)]
    if "service_id" in g:
        line_without_service_id = build_statsd_line({k: v for k, v in extra_fields.items() if k != "service_id"})
        stats.append(line_without_service_id)

    for stat in stats:
        statsd_client.incr(stat)

        if "time_taken" in extra_fields:
            statsd_client.timing(stat, extra_fields["time_taken"])


def ensure_log_path_exists(path):
    """
    This function assumes you're passing a path to a file and attempts to create
    the path leading to that file.
    """
    try:
        Path(path).parent.mkdir(mode=755, parents=True)
    except FileExistsError:
        pass


def get_handlers(app):
    handlers = []
    standard_formatter = CustomLogFormatter(LOG_FORMAT, TIME_FORMAT)
    json_formatter = JSONFormatter(LOG_FORMAT, TIME_FORMAT)

    stream_handler = logging.StreamHandler(sys.stdout)
    if not app.debug:
        # machine readable json to both file and stdout
        # file_handler = logging.handlers.WatchedFileHandler(
        #     filename='{}.json'.format(app.config['NOTIFY_LOG_PATH'])
        # )

        handlers.append(configure_handler(stream_handler, app, json_formatter))
        # Do not write to files, stdout logging is only needed
        # handlers.append(configure_handler(file_handler, app, json_formatter))
    else:
        # turn off 200 OK static logs in development
        def is_200_static_log(log):
            msg = log.getMessage()
            return not ("GET /static/" in msg and " 200 " in msg)

        logging.getLogger("werkzeug").addFilter(is_200_static_log)

        # human readable stdout logs
        handlers.append(configure_handler(stream_handler, app, standard_formatter))

    return handlers


def configure_handler(handler, app, formatter):
    handler.setLevel(logging.getLevelName(app.config["NOTIFY_LOG_LEVEL"]))
    handler.setFormatter(formatter)
    handler.addFilter(AppNameFilter(app.config["NOTIFY_APP_NAME"]))
    handler.addFilter(RequestIdFilter())

    return handler


def get_class_attrs(cls, sensitive_attrs: list[str]) -> dict[str, Any]:
    """
    Returns a dict of Class attribute key/values.  Any attribute names in the
    sensitive_attrs list will be masked.
    """
    attrs = {}
    for attr in dir(cls):
        if not attr.startswith("__") and not callable(getattr(cls, attr)):
            value = getattr(cls, attr)
            if attr not in sensitive_attrs:
                attrs[attr] = value
            elif len(str(value)) >= 20:
                attrs[attr] = "***" + str(value)[-2:]
            else:
                attrs[attr] = "***"
    return attrs


class AppNameFilter(logging.Filter):
    def __init__(self, app_name):
        self.app_name = app_name

    def filter(self, record):
        record.app_name = self.app_name

        return record


class RequestIdFilter(logging.Filter):
    @property
    def request_id(self):
        if has_request_context() and hasattr(request, "request_id"):
            return request.request_id  # type: ignore
        else:
            return "no-request-id"

    def filter(self, record):
        record.request_id = self.request_id

        return record


class CustomLogFormatter(logging.Formatter):
    """Accepts a format string for the message and formats it with the extra fields"""

    FORMAT_STRING_FIELDS_PATTERN = re.compile(r"\((.+?)\)", re.IGNORECASE)

    def add_fields(self, record):
        if self._fmt is None:
            raise TypeError("self._fmt is None")
        for field in self.FORMAT_STRING_FIELDS_PATTERN.findall(self._fmt):
            record.__dict__[field] = record.__dict__.get(field)
        return record

    def format(self, record):
        record = self.add_fields(record)
        try:
            # Replace the API signed secret with asterisks
            record.msg = re.sub(regex_pattern_for_replace_api_signed_secret, "***", record.msg)
            # sometimes record.msg is an exception so this is checking for that
            if isinstance(record.msg, str):
                record.msg += _getAdditionalLoggingDetails()
            record.msg = str(record.msg).format(**record.__dict__)
        except (KeyError, IndexError) as e:
            logger.exception("failed to format log message: {} not found".format(e))

        return super(CustomLogFormatter, self).format(record)


class JSONFormatter(BaseJSONFormatter):
    def process_log_record(self, log_record):
        rename_map = {
            "asctime": "time",
            "request_id": "requestId",
            "app_name": "application",
        }
        for key, newkey in rename_map.items():
            log_record[newkey] = log_record.pop(key)
        log_record["logType"] = "application"
        try:
            # Replace the API signed secret with asterisks
            log_record["message"] = re.sub(regex_pattern_for_replace_api_signed_secret, "***", log_record["message"])
            log_record["message"] = str(log_record["message"])
        except (KeyError, IndexError) as e:
            logger.exception("failed to format log message: {} not found".format(e))

        # add additional details to log message when we can
        log_record["message"] += _getAdditionalLoggingDetails()

        return log_record


# log request details when logging occurs as part of a request
def _getAdditionalLoggingDetails():
    if has_request_context():
        # request fields to log
        requestFields = ("full_path", "endpoint")
        # body fields to log
        bodyFields = ("template_id", "service_id", "notification_id")
        additionalDetails = " [Request details: "

        # Add timing information if available
        if hasattr(g, "start"):
            time_taken = (monotonic() - g.start) * 1000  # Convert to milliseconds
            additionalDetails += f"time_taken: {time_taken:.2f}ms "

        try:
            # log request fields if they are present
            for field in requestFields:
                additionalDetails += f"{field}: '{getattr(request, field)}' " if hasattr(request, field) else ""

            # log body fields if they are present
            json = request.get_json(silent=True)
            if json:
                for field in bodyFields:
                    additionalDetails += f"{field}: '{json[field]}' " if field in json else ""

            additionalDetails += "]"

        except Exception as e:
            logger.exception("unable to get json data or header data from the request: {} ".format(e))

        return additionalDetails

    return ""

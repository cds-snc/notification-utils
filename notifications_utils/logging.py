import logging
import re
from pathlib import Path
from time import monotonic
from typing import Any

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.logging.formatter import LambdaPowertoolsFormatter
from flask import g, request
from flask.ctx import has_request_context

# Initialize tracer and logger with custom configuration
tracer = Tracer()
logger = Logger(service="notification-utils", use_rfc3339=True)

# For Flask, we need to patch to ensure all HTTP calls are traced
tracer.patch(["requests", "boto3"])

# Setup custom formatters that integrate with Powertools
LOG_FORMAT = "%(asctime)s %(app_name)s %(name)s %(levelname)s %(request_id)s " "%(message)s [in %(pathname)s:%(lineno)d]"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


class AppLogFormatter(LambdaPowertoolsFormatter):
    """Extends Powertools formatter with app-specific needs"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "default_attributes"):
            self.default_attributes = {}
        self.default_attributes.update({"app_name": "notification-utils", "request_id": "no-request-id"})

    def format(self, record):
        if has_request_context():
            self.default_attributes["request_id"] = getattr(request, "request_id", "no-request-id")
            # Add request context to structured logs
            for key, value in self.default_attributes.items():
                setattr(record, key, value)

        # Mask sensitive data in logs
        if isinstance(record.msg, str):
            record.msg = re.sub(regex_pattern_for_replace_api_signed_secret, "***", record.msg)
            record.msg += _getAdditionalLoggingDetails()

        return super().format(record)


regex_pattern_for_replace_api_signed_secret = "[a-zA-Z0-9]{51}\.[a-zA-Z0-9-_]{27}"  # noqa: W605


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
    app.config.setdefault("NOTIFY_LOG_PATH", None)

    # Configure the Powertools logger with custom formatter
    formatter = AppLogFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if app.config["NOTIFY_LOG_PATH"]:
        # Add file logging if configured
        ensure_log_path_exists(app.config["NOTIFY_LOG_PATH"])
        file_handler = logging.FileHandler(filename=app.config["NOTIFY_LOG_PATH"])
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    @app.after_request
    def after_request(response):
        extra_fields = {
            "method": request.method,
            "url": request.url,
            "status": response.status_code,
            "app_name": app.config["NOTIFY_APP_NAME"],
        }

        if "service_id" in g:
            extra_fields.update({"service_id": g.service_id})

        if "start" in g:
            extra_fields.update({"time_taken": (monotonic() - g.start) * 1000})

        if "endpoint" in g:
            extra_fields.update({"endpoint": g.endpoint})

        record_stats(statsd_client, extra_fields)
        logger.debug("Request completed", extra=extra_fields)
        return response

    # Configure default log levels
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("s3transfer").setLevel(logging.WARNING)
    logger.info("Logging configured")


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


# Powertools Logger handles all log configuration


def get_handlers(app):
    """Get handlers for backwards compatibility with tests"""
    handler = logging.StreamHandler()
    handler.setFormatter(AppLogFormatter())
    return [handler]


class CustomLogFormatter(logging.Formatter):
    """Kept for backwards compatibility with tests"""

    pass


class JSONFormatter(logging.Formatter):
    """Kept for backwards compatibility with tests"""

    pass


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


# Powertools logger handles formatting and filtering automatically


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

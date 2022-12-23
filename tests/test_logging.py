import json
import logging as builtin_logging
import uuid
from time import monotonic
from unittest.mock import call

import pytest
from flask import request, g

from notifications_utils import logging


def test_should_build_complete_log_line():
    service_id = uuid.uuid4()
    extra_fields = {"method": "method", "url": "url", "status": 200, "time_taken": "time_taken", "service_id": service_id}
    assert "{service_id} method url 200 time_taken".format(service_id=str(service_id)) == logging.build_log_line(extra_fields)


def test_should_build_complete_log_line_ignoring_missing_fields():
    service_id = uuid.uuid4()
    extra_fields = {"method": "method", "status": 200, "time_taken": "time_taken", "service_id": service_id}
    assert "{service_id} method 200 time_taken".format(service_id=str(service_id)) == logging.build_log_line(extra_fields)


def test_should_build_log_line_without_service_id():
    extra_fields = {"method": "method", "url": "url", "status": 200, "time_taken": "time_taken"}
    assert "method url 200 time_taken" == logging.build_log_line(extra_fields)


def test_should_build_log_line_without_service_id_or_time_taken():
    extra_fields = {"method": "method", "url": "url", "status": 200}
    assert "method url 200" == logging.build_log_line(extra_fields)


def test_should_build_complete_statsd_line():
    service_id = uuid.uuid4()
    extra_fields = {"method": "method", "endpoint": "endpoint", "status": 200, "service_id": service_id}
    assert "service-id.{service_id}.method.endpoint.200".format(service_id=str(service_id)) == logging.build_statsd_line(
        extra_fields
    )


def test_should_build_complete_statsd_line_without_service_id_prefix_for_admin_api_calls():
    extra_fields = {"method": "method", "endpoint": "endpoint", "status": 200, "service_id": "notify-admin"}
    assert "notify-admin.method.endpoint.200" == logging.build_statsd_line(extra_fields)


def test_should_build_complete_statsd_line_ignoring_missing_fields():
    service_id = uuid.uuid4()
    extra_fields = {"method": "method", "endpoint": "endpoint", "service_id": service_id}
    assert "service-id.{service_id}.method.endpoint".format(service_id=str(service_id)) == logging.build_statsd_line(extra_fields)


def test_should_build_statsd_line_without_service_id_or_time_taken():
    extra_fields = {"method": "method", "endpoint": "endpoint", "status": 200}
    assert "method.endpoint.200" == logging.build_statsd_line(extra_fields)


def test_get_handlers_sets_up_logging_appropriately_with_debug(tmpdir):
    class App:
        config = {"NOTIFY_LOG_PATH": str(tmpdir / "foo"), "NOTIFY_APP_NAME": "bar", "NOTIFY_LOG_LEVEL": "ERROR"}
        debug = True

    app = App()

    handlers = logging.get_handlers(app)

    assert len(handlers) == 1
    assert type(handlers[0]) == builtin_logging.StreamHandler
    assert type(handlers[0].formatter) == logging.CustomLogFormatter
    assert not (tmpdir / "foo").exists()


def test_get_handlers_sets_up_logging_appropriately_without_debug(tmpdir):
    class App:
        config = {
            # make a tempfile called foo
            "NOTIFY_LOG_PATH": str(tmpdir / "foo"),
            "NOTIFY_APP_NAME": "bar",
            "NOTIFY_LOG_LEVEL": "ERROR",
        }
        debug = False

    app = App()

    handlers = logging.get_handlers(app)

    assert len(handlers) == 1
    assert type(handlers[0]) == builtin_logging.StreamHandler
    assert type(handlers[0].formatter) == logging.JSONFormatter

    # assert type(handlers[1]) == builtin_logging_handlers.WatchedFileHandler
    # assert type(handlers[1].formatter) == logging.JSONFormatter

    # dir_contents = tmpdir.listdir()
    # assert len(dir_contents) == 1
    # assert dir_contents[0].basename == 'foo.json'


@pytest.mark.parametrize("service_id", ["fake-service_id", None])
def test_logging_records_statsd_stats(app_with_statsd, service_id):
    app = app_with_statsd
    statsd = app_with_statsd.statsd_client
    logging.init_app(app_with_statsd, statsd)

    @app.before_request
    def record_request_details():
        g.start = monotonic()
        g.endpoint = request.endpoint
        if service_id:
            g.service_id = "fake-service_id"

    @app.route("/")
    def homepage():
        return "ok"

    with app.app_context():
        response = app.test_client().get("/")
        assert response.status_code == 200
        if service_id:
            assert statsd.incr.call_args_list == [
                call("service-id.fake-service_id.GET.homepage.200"),
                call("GET.homepage.200"),
            ]
            assert statsd.timing.call_count == 2
        else:
            assert statsd.incr.call_args_list == [call("GET.homepage.200")]
            assert statsd.timing.call_count == 1
            args, _ = statsd.timing.call_args_list[0]
            time_ms = args[1]
            assert time_ms >= 0.1


@pytest.mark.parametrize("service_id", ["fake-service_id", None])
def test_logging_records_statsd_stats_without_time(app_with_statsd, service_id):
    app = app_with_statsd
    statsd = app_with_statsd.statsd_client
    logging.init_app(app_with_statsd, statsd)

    @app.before_request
    def record_request_details():
        g.endpoint = request.endpoint
        if service_id:
            g.service_id = "fake-service_id"

    @app.route("/")
    def homepage():
        return "ok"

    with app.app_context():
        response = app.test_client().get("/")
        assert response.status_code == 200
        if service_id:
            assert statsd.incr.call_args_list == [
                call("service-id.fake-service_id.GET.homepage.200"),
                call("GET.homepage.200"),
            ]
            statsd.timing.assert_not_called()
        else:
            assert statsd.incr.call_args_list == [call("GET.homepage.200")]
            statsd.timing.assert_not_called()


def test_get_class_attrs():
    class Config:
        some_dict = {
            "FOO": "bar",
            "BAM": "baz",
        }
        env = "prod"

        def some_function(self):
            return True

    assert logging.get_class_attrs(Config, []) == {
        "some_dict": {
            "FOO": "bar",
            "BAM": "baz",
        },
        "env": "prod",
    }

    an_instance = Config()
    an_instance.some_dict = {"BAR": "bloop"}

    assert logging.get_class_attrs(an_instance, ["env"]) == {
        "some_dict": {
            "BAR": "bloop",
        },
        "env": "***",
    }


@pytest.mark.parametrize("debugconfig", [True, False])
@pytest.mark.parametrize("testcases", [("info", "warning", "error", "exception", "critical")])
def test_logger_adds_extra_context_details(app, mocker, debugconfig, testcases):
    app.debug = debugconfig

    @app.route("/info", methods=["POST"])
    def info():
        app.logger.info("info")
        return "ok"

    @app.route("/warning", methods=["POST"])
    def warning():
        app.logger.warning("warning")
        return "ok"

    @app.route("/error", methods=["POST"])
    def error():
        app.logger.error("error")
        return "ok"

    @app.route("/exception", methods=["POST"])
    def exception():
        app.logger.exception("exception")
        return "ok"

    @app.route("/critical", methods=["POST"])
    def critical():
        app.logger.critical("critical")
        return "ok"

    logging.init_app(app)

    if debugconfig:
        log_spy = mocker.spy(logging.CustomLogFormatter, "format")
    else:
        log_spy = mocker.spy(logging.JSONFormatter, "process_log_record")

    with app.app_context():
        for route in testcases:
            response = app.test_client().post(
                f"/{route}", data=json.dumps({"template_id": "1234"}), headers={"Content-Type": "application/json"}
            )

            if debugconfig:
                errorMessage = log_spy.spy_return  # message is returned as a string when using the CustomLogFormatter
            else:
                errorMessage = log_spy.spy_return["message"]  # message is embedded in JSON when using the JSONFormatter

            # ensure extra request details are being added
            assert "Request details" in errorMessage
            # ensure body data (template_id) is shown
            assert "template_id" in errorMessage
            # ensure request data (endpoint) is shown
            assert "endpoint" in errorMessage

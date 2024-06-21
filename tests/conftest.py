from unittest.mock import Mock

import pytest
import requests_mock
from flask import Flask


class FakeService:
    id = "1234"


@pytest.fixture
def app():
    flask_app = Flask(__name__)
    ctx = flask_app.app_context()
    ctx.push()
    yield flask_app

    ctx.pop()


@pytest.fixture(scope="session")
def sample_service():
    return FakeService()


@pytest.yield_fixture
def rmock():
    with requests_mock.mock() as rmock:
        yield rmock


@pytest.fixture
def app_with_statsd(app):
    app.config["NOTIFY_ENVIRONMENT"] = "test"
    app.config["NOTIFY_APP_NAME"] = "utils"
    app.config["STATSD_HOST"] = "localhost"
    app.config["STATSD_PORT"] = "8000"
    app.config["STATSD_PREFIX"] = "prefix"
    app.statsd_client = Mock()
    return app

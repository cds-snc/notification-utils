import pytest
from flask import Flask

import requests_mock


class FakeService():
    id = "1234"


@pytest.fixture
def app():
    flask_app = Flask(__name__)
    ctx = flask_app.app_context()
    ctx.push()

    yield flask_app

    ctx.pop()


@pytest.fixture(scope='session')
def sample_service():
    return FakeService()


@pytest.yield_fixture
def rmock():
    with requests_mock.mock() as rmock:
        yield rmock

# https://superorbital.io/journal/focusing-on-pytest/
def pytest_configure(config):
    """
    Register the `focus` marker, so we don't get warnings.
    """

    config.addinivalue_line("markers", "focus: Only run this test.")


def pytest_collection_modifyitems(items, config):
    """
    Focus on tests marked focus, if any.  Run all otherwise.
    """

    selected_items = []
    deselected_items = []

    focused = False
    for item in items:
        if item.get_closest_marker("focus"):
            focused = True
            selected_items.append(item)
        else:
            deselected_items.append(item)

    if focused:
        print("\nOnly running @pytest.mark.focus tests")
        config.hook.pytest_deselected(items=deselected_items)
        items[:] = selected_items
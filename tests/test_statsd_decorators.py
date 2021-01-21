import pytest
from unittest.mock import ANY, Mock
from notifications_utils.statsd_decorators import statsd


class AnyStringWith(str):
    def __eq__(self, other):
        return self in other


@pytest.fixture
def test_app(app):
    app.config['NOTIFY_ENVIRONMENT'] = "test"
    app.config['NOTIFY_APP_NAME'] = "api"
    app.config['STATSD_HOST'] = "localhost"
    app.config['STATSD_PORT'] = "8000"
    app.config['STATSD_PREFIX'] = "prefix"
    app.statsd_client = Mock()

    return app


def test_should_call_statsd(test_app, mocker):

    mock_logger = mocker.patch.object(test_app.logger, 'debug')

    @statsd(namespace="test")
    def test_function():
        return True

    assert test_function()
    mock_logger.assert_called_once_with(AnyStringWith("test call test_function took "))
    test_app.statsd_client.incr.assert_any_call("test.test_function")
    test_app.statsd_client.incr.assert_any_call("test.test_function.success")
    test_app.statsd_client.timing.assert_called_once_with("test.test_function.success.elapsed_time", ANY)


def test_should_call_statsd_on_exception(test_app):

    @statsd(namespace="test")
    def test_function():
        raise Exception()

    with pytest.raises(Exception):
        test_function()

    test_app.statsd_client.incr.assert_any_call("test.test_function")
    test_app.statsd_client.incr.assert_any_call("test.test_function.exception")

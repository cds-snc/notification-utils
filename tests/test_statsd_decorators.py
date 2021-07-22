import pytest
from unittest.mock import ANY
from notifications_utils.statsd_decorators import statsd, statsd_catch


class AnyStringWith(str):
    def __eq__(self, other):
        return self in other


def test_should_call_statsd(app_with_statsd, mocker):
    mock_logger = mocker.patch.object(app_with_statsd.logger, "debug")

    @statsd(namespace="test")
    def test_function():
        return True

    assert test_function()
    mock_logger.assert_called_once_with(AnyStringWith("test call test_function took "))
    app_with_statsd.statsd_client.incr.assert_called_once_with("test.test_function")
    app_with_statsd.statsd_client.timing.assert_called_once_with("test.test_function", ANY)


def test_should_call_statsd_catch(app_with_statsd, mocker):
    class CustomException(Exception):
        pass

    class FooBar:
        @statsd_catch(namespace="test", counter_name="rate.test", exception=CustomException)
        def test_function(self):
            return True

    fb = FooBar()
    mocker.spy(fb, "test_function")

    assert fb.test_function()
    fb.test_function.assert_called_once()
    app_with_statsd.statsd_client.incr.assert_not_called()


def test_should_incr_statsd_on_catch(app_with_statsd, mocker):
    class CustomException(Exception):
        pass

    class FooBar:
        @statsd_catch(namespace="test", counter_name="rate.test", exception=CustomException)
        def test_function(self):
            raise CustomException("huh huh")

    fb = FooBar()
    mocker.spy(fb, "test_function")

    with pytest.raises(CustomException):
        fb.test_function()
    fb.test_function.assert_called_once()
    app_with_statsd.statsd_client.incr.assert_called_once_with("test.rate.test")


def test_should_not_incr_statsd_on_catch_and_non_matching_exception(app_with_statsd, mocker):
    class CustomException(BaseException):
        pass

    class FooBar:
        @statsd_catch(namespace="test", counter_name="rate.test", exception=AssertionError)
        def test_function(self):
            raise CustomException("huh huh")

    fb = FooBar()
    mocker.spy(fb, "test_function")

    with pytest.raises(CustomException):
        fb.test_function()
    fb.test_function.assert_called_once()
    app_with_statsd.statsd_client.incr.assert_not_called()

import pytest
from flask import current_app
from notifications_utils.decorators import requires_feature
from unittest import mock

@requires_feature('FEATURE_FLAG')
def decorated_function():
    return "Feature enabled"

def test_requires_feature_enabled(mocker, app):
    app.config['FEATURE_FLAG'] = True
    result = decorated_function()
    assert result == "Feature enabled"

def test_requires_feature_disabled(mocker, app):
    app.config['FEATURE_FLAG'] = False
    result = decorated_function()
    assert result is None
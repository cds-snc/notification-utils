from notifications_utils.decorators import parallel_process_iterable, requires_feature


@requires_feature("FEATURE_FLAG")
def decorated_function():
    return "Feature enabled"


def test_requires_feature_enabled(mocker, app):
    app.config["FEATURE_FLAG"] = True
    result = decorated_function()
    assert result == "Feature enabled"


def test_requires_feature_disabled(mocker, app):
    app.config["FEATURE_FLAG"] = False
    result = decorated_function()
    assert result is None


# Sample function to be decorated
@parallel_process_iterable(chunk_size=2, max_workers=2)
def process_chunk(chunk):
    return [x * 2 for x in chunk]


def test_parallel_process_iterable():
    data = [1, 2, 3, 4, 5, 6]
    expected_result = [[2, 4], [6, 8], [10, 12]]
    result = process_chunk(data)
    assert result == expected_result


def test_parallel_process_iterable_with_break_condition():
    data = [1, 2, 3, 4, 5, 6]

    def break_condition(result):
        return 6 in result

    @parallel_process_iterable(chunk_size=2, max_workers=2, break_condition=break_condition)
    def process_chunk_with_break(chunk):
        return [x * 2 for x in chunk]

    expected_result = [[2, 4], [6, 8]]
    result = process_chunk_with_break(data)
    assert result == expected_result

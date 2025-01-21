import pytest
from notifications_utils.decorators import control_chunk_and_worker_size, parallel_process_iterable, requires_feature


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
@parallel_process_iterable()
def process_chunk(chunk):
    return [x * 2 for x in chunk]


def test_parallel_process_iterable(app):
    data = [1, 2, 3, 4, 5, 6]
    expected_result = [2, 4, 6, 8, 10, 12]
    with app.app_context():
        result = process_chunk(data)
    assert result[0] == expected_result


def test_parallel_process_iterable_with_break_condition(app):
    data = [num for num in range(1500, 1, -1)]

    def break_condition(result):
        return 1500 in result

    @parallel_process_iterable(break_condition=break_condition)
    def process_chunk_with_break(chunk):
        return [x * 2 for x in chunk]

    with app.app_context():
        results = process_chunk_with_break(data)
    assert len(results) == 1  # Only 1 thread should have processed data
    assert any(result == 1500 for result in results[0])


@pytest.mark.parametrize(
    "data_size, expected_worker_count, expected_chunk_size",
    [
        (1000, 1, 1000),  # data_size <= the minimum chunk size
        (900, 1, 900),  # data_size <= the minimum chunk size
        (
            8000,
            8,
            1000,
        ),  # Small overall data and chunk size, less risk of context switching and CPU overhead, should scale to utilize more workers
        (
            9000,
            9,
            1000,
        ),  # Small overall data and chunk size, less risk of context switching and CPU overhead, should scale to utilize more workers
        (
            20000,
            20,
            1000,
        ),  # Hitting the max worker count, ensure the worker count stays capped at 28 and chunk_size scales accordingly
        (80000, 28, 2858),  # Ensure chunk size is scaling, not max workers
    ],
)
def test_parallel_process_iterable_adjusts_workers_and_chunk_size(
    app, data_size, expected_worker_count, expected_chunk_size, mocker
):
    data = [num + 1 for num in range(0, data_size, 1)]
    mocker.patch("multiprocessing.cpu_count", return_value=28)  # m5.large has 28 cores

    @parallel_process_iterable()
    def process_chunk(chunk):
        return [x * 2 for x in chunk]

    with app.app_context():
        results = process_chunk(data)
        assert len(results) == expected_worker_count
        assert any(len(result) == expected_chunk_size for result in results)


def test_parallel_process_iterable_handles_break_condition_exceptions(app):
    data = [num + 1 for num in range(0, 1002, 1)]

    def break_condition(result):
        raise ValueError("Something went wrong")

    @parallel_process_iterable(chunk_size=2, max_workers=2, break_condition=break_condition)
    def process_chunk_with_break(chunk):
        return [x * 2 for x in chunk]

    with pytest.raises(ValueError), app.app_context():
        process_chunk_with_break(data)


def test_control_chunk_and_worker_size_scales_workers_down_when_chunk_size_exceeds_threshold(mocker):
    mocker.patch("multiprocessing.cpu_count", return_value=28)  # m5.large has 28 cores
    assert control_chunk_and_worker_size(300000) == (10000, 14)  # (chunk_size, worker_count)

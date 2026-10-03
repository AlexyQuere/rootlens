from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

import pytest

from rootlens.evaluation.cross_modal_artifacts import (
    CommonTimeWindow,
    common_time_window,
)


class FakeSlice:
    def __init__(
        self,
        start,
        end,
    ):
        self.start = start
        self.end = end


def dt(
    hour: int,
    minute: int,
):
    return datetime(
        2026,
        10,
        3,
        hour,
        minute,
        tzinfo=timezone.utc,
    )


def test_common_window():
    first = FakeSlice(
        dt(10, 0),
        dt(10, 10),
    )

    second = FakeSlice(
        dt(10, 5),
        dt(10, 15),
    )

    result = (
        common_time_window(
            first,
            second,
        )
    )

    assert result == (
        CommonTimeWindow(
            start=dt(
                10,
                5,
            ),

            end=dt(
                10,
                10,
            ),
        )
    )


def test_disjoint_windows_do_not_merge():
    metrics = FakeSlice(
        dt(10, 0),
        dt(10, 5),
    )

    traces = FakeSlice(
        dt(12, 0),
        dt(12, 5),
    )

    result = (
        common_time_window(
            metrics,
            traces,
        )
    )

    assert result is None


def test_touching_windows_are_not_overlap():
    first = FakeSlice(
        dt(10, 0),
        dt(10, 5),
    )

    second = FakeSlice(
        dt(10, 5),
        dt(10, 10),
    )

    assert (
        common_time_window(
            first,
            second,
        )
        is None
    )


def test_empty_input_rejected():
    with pytest.raises(
        ValueError
    ):
        common_time_window()
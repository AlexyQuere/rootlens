from datetime import (
    datetime,
    timedelta,
    timezone,
)

import math

import pytest

from rootlens.observability.evidence import (
    MetricComparisonEvidence,
    MetricEvidence,
    TimeWindow,
)


def make_window(
    start_offset_minutes: int = 0,
) -> TimeWindow:

    start = datetime(
        2026,
        10,
        2,
        8,
        0,
        tzinfo=timezone.utc,
    ) + timedelta(
        minutes=start_offset_minutes
    )

    end = (
        start
        + timedelta(
            minutes=5
        )
    )

    return TimeWindow(
        start=start,
        end=end,
    )


def make_metric(
    *,
    value: float,
    window: TimeWindow,
    statistic: str = "p95",
    service: str = "checkout",
) -> MetricEvidence:

    return MetricEvidence(
        name=(
            "http_server_request_"
            "duration_seconds"
        ),
        statistic=statistic,
        value=value,
        unit="seconds",
        service=service,
        window=window,
        promql=(
            "histogram_quantile(...)"
        ),
    )


def test_time_window_duration():

    window = make_window()

    assert (
        window.duration_seconds
        == pytest.approx(
            300.0
        )
    )


def test_time_window_rejects_naive_start():

    with pytest.raises(
        ValueError,
        match="start must be timezone-aware",
    ):

        TimeWindow(
            start=datetime(
                2026,
                10,
                2,
                8,
                0,
            ),
            end=datetime(
                2026,
                10,
                2,
                8,
                5,
                tzinfo=timezone.utc,
            ),
        )


def test_time_window_rejects_naive_end():

    with pytest.raises(
        ValueError,
        match="end must be timezone-aware",
    ):

        TimeWindow(
            start=datetime(
                2026,
                10,
                2,
                8,
                0,
                tzinfo=timezone.utc,
            ),
            end=datetime(
                2026,
                10,
                2,
                8,
                5,
            ),
        )


def test_time_window_rejects_invalid_order():

    start = datetime(
        2026,
        10,
        2,
        8,
        0,
        tzinfo=timezone.utc,
    )

    with pytest.raises(
        ValueError,
        match="end must be after start",
    ):

        TimeWindow(
            start=start,
            end=start,
        )


def test_metric_evidence_preserves_provenance():

    metric = make_metric(
        value=0.471,
        window=make_window(),
    )

    assert (
        metric.value
        == pytest.approx(
            0.471
        )
    )

    assert (
        metric.service
        == "checkout"
    )

    assert (
        metric.source
        == "prometheus"
    )

    assert (
        metric.promql
        == "histogram_quantile(...)"
    )


def test_metric_evidence_rejects_empty_promql():

    with pytest.raises(
        ValueError,
        match="promql must not be empty",
    ):

        MetricEvidence(
            name="requests",
            statistic="rate",
            value=1.0,
            unit="requests_per_second",
            service="checkout",
            window=make_window(),
            promql="",
        )


def test_metric_evidence_rejects_non_finite_value():

    with pytest.raises(
        ValueError,
        match="metric value must be finite",
    ):

        make_metric(
            value=math.nan,
            window=make_window(),
        )


def test_metric_comparison_accepts_matching_metrics():

    baseline = make_metric(
        value=0.350,
        window=make_window(
            0
        ),
    )

    incident = make_metric(
        value=0.471,
        window=make_window(
            10
        ),
    )

    comparison = (
        MetricComparisonEvidence(
            baseline=baseline,
            incident=incident,
        )
    )

    assert (
        comparison.name
        == baseline.name
    )

    assert (
        comparison.statistic
        == "p95"
    )

    assert (
        comparison.service
        == "checkout"
    )


def test_metric_comparison_computes_absolute_delta():

    baseline = make_metric(
        value=0.350,
        window=make_window(
            0
        ),
    )

    incident = make_metric(
        value=0.471,
        window=make_window(
            10
        ),
    )

    comparison = (
        MetricComparisonEvidence(
            baseline=baseline,
            incident=incident,
        )
    )

    assert (
        comparison.absolute_delta
        == pytest.approx(
            0.121
        )
    )


def test_metric_comparison_computes_relative_delta():

    baseline = make_metric(
        value=0.350,
        window=make_window(
            0
        ),
    )

    incident = make_metric(
        value=0.471,
        window=make_window(
            10
        ),
    )

    comparison = (
        MetricComparisonEvidence(
            baseline=baseline,
            incident=incident,
        )
    )

    assert (
        comparison.relative_delta
        == pytest.approx(
            0.121
            / 0.350
        )
    )


def test_metric_comparison_zero_baseline_has_no_relative_delta():

    baseline = make_metric(
        value=0.0,
        window=make_window(
            0
        ),
    )

    incident = make_metric(
        value=0.637,
        window=make_window(
            10
        ),
    )

    comparison = (
        MetricComparisonEvidence(
            baseline=baseline,
            incident=incident,
        )
    )

    assert (
        comparison.absolute_delta
        == pytest.approx(
            0.637
        )
    )

    assert (
        comparison.relative_delta
        is None
    )


def test_metric_comparison_rejects_different_statistics():

    baseline = make_metric(
        value=0.350,
        window=make_window(),
        statistic="p95",
    )

    incident = make_metric(
        value=0.600,
        window=make_window(
            10
        ),
        statistic="p99",
    )

    with pytest.raises(
        ValueError,
        match="same statistic",
    ):

        MetricComparisonEvidence(
            baseline=baseline,
            incident=incident,
        )


def test_metric_comparison_rejects_different_services():

    baseline = make_metric(
        value=0.350,
        window=make_window(),
        service="checkout",
    )

    incident = make_metric(
        value=0.600,
        window=make_window(
            10
        ),
        service="payment",
    )

    with pytest.raises(
        ValueError,
        match="same service",
    ):

        MetricComparisonEvidence(
            baseline=baseline,
            incident=incident,
        )


def test_negative_zero_tolerance_is_rejected():

    baseline = make_metric(
        value=0.350,
        window=make_window(),
    )

    incident = make_metric(
        value=0.471,
        window=make_window(
            10
        ),
    )

    with pytest.raises(
        ValueError,
        match="zero_tolerance",
    ):

        MetricComparisonEvidence(
            baseline=baseline,
            incident=incident,
            zero_tolerance=-1.0,
        )
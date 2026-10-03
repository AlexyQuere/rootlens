from datetime import (
    datetime,
    timedelta,
    timezone,
)

import math

import pytest

from rootlens.observability.evidence import (
    TimeWindow,
)

from rootlens.observability.metrics import (
    MetricCardinalityError,
    MetricUnavailableError,
    MetricsTool,
    UnsupportedMetricOperationError,
)

from rootlens.observability.prometheus import (
    InstantSample,
)


class FakePrometheusClient:

    def __init__(
        self,
        responses,
    ):

        self.responses = list(
            responses
        )

        self.calls = []

    def query(
        self,
        promql,
        *,
        time=None,
    ):

        self.calls.append(
            {
                "promql":
                    promql,

                "time":
                    time,
            }
        )

        if not self.responses:
            raise AssertionError(
                "No fake response left."
            )

        return self.responses.pop(
            0
        )


def sample(
    value,
):

    return (
        InstantSample(
            metric={},
            timestamp=1.0,
            value=value,
        ),
    )


def window():

    end = datetime(
        2026,
        10,
        2,
        8,
        30,
        tzinfo=timezone.utc,
    )

    start = (
        end
        - timedelta(
            minutes=5
        )
    )

    return TimeWindow(
        start=start,
        end=end,
    )


def test_rpc_server_request_rate():

    client = (
        FakePrometheusClient(
            [
                sample(
                    0.21
                )
            ]
        )
    )

    tool = MetricsTool(
        client
    )

    evidence = (
        tool.request_rate(
            family="rpc_server",
            service="checkout",
            operation=(
                "oteldemo."
                "CheckoutService/"
                "PlaceOrder"
            ),
            window=window(),
        )
    )

    assert (
        evidence.value
        == pytest.approx(
            0.21
        )
    )

    assert (
        evidence.unit
        == "requests_per_second"
    )

    query = (
        client.calls[0][
            "promql"
        ]
    )

    assert (
        "rpc_server_call_"
        "duration_seconds_count"
        in query
    )

    assert (
        'service_name="checkout"'
        in query
    )

    assert (
        'rpc_system_name="grpc"'
        in query
    )

    assert (
        'rpc_method="oteldemo.'
        'CheckoutService/PlaceOrder"'
        in query
    )

    assert (
        "[300s]"
        in query
    )


def test_rpc_client_error_rate():

    client = (
        FakePrometheusClient(
            [
                sample(
                    0.637
                )
            ]
        )
    )

    tool = MetricsTool(
        client
    )

    evidence = (
        tool.error_rate(
            family="rpc_client",
            service="checkout",
            operation=(
                "oteldemo."
                "PaymentService/"
                "Charge"
            ),
            window=window(),
        )
    )

    assert (
        evidence.value
        == pytest.approx(
            0.637
        )
    )

    assert (
        evidence.unit
        == "ratio"
    )

    query = (
        client.calls[0][
            "promql"
        ]
    )

    assert (
        "rpc_client_call_"
        "duration_seconds_count"
        in query
    )

    assert (
        'rpc_response_status_code!="OK"'
        in query
    )

    assert (
        "or vector(0)"
        in query
    )

    assert (
        "PaymentService/Charge"
        in query
    )


def test_http_error_rate_uses_5xx():

    client = (
        FakePrometheusClient(
            [
                sample(
                    0.10
                )
            ]
        )
    )

    tool = MetricsTool(
        client
    )

    tool.error_rate(
        family="http_server",
        service="frontend",
        window=window(),
    )

    query = (
        client.calls[0][
            "promql"
        ]
    )

    assert (
        'http_response_status_code=~"5.."'
        in query
    )


def test_rpc_server_p95():

    client = (
        FakePrometheusClient(
            [
                sample(
                    0.471
                )
            ]
        )
    )

    tool = MetricsTool(
        client
    )

    evidence = (
        tool.latency_quantile(
            family="rpc_server",
            service="checkout",
            operation=(
                "oteldemo."
                "CheckoutService/"
                "PlaceOrder"
            ),
            quantile=0.95,
            window=window(),
        )
    )

    assert (
        evidence.value
        == pytest.approx(
            0.471
        )
    )

    assert (
        evidence.statistic
        == "p95"
    )

    assert (
        evidence.unit
        == "seconds"
    )

    query = (
        client.calls[0][
            "promql"
        ]
    )

    assert (
        "histogram_quantile(0.95"
        in query
    )

    assert (
        "sum by (le)"
        in query
    )

    assert (
        "rpc_server_call_"
        "duration_seconds_bucket"
        in query
    )


def test_default_latency_quantiles():

    client = (
        FakePrometheusClient(
            [
                sample(
                    0.100
                ),
                sample(
                    0.400
                ),
                sample(
                    0.700
                ),
            ]
        )
    )

    tool = MetricsTool(
        client
    )

    result = (
        tool.latency_quantiles(
            family="rpc_server",
            service="checkout",
            window=window(),
        )
    )

    assert [
        item.statistic
        for item in result
    ] == [
        "p50",
        "p95",
        "p99",
    ]


def test_rpc_client_latency_not_yet_enabled():

    client = (
        FakePrometheusClient(
            []
        )
    )

    tool = MetricsTool(
        client
    )

    with pytest.raises(
        UnsupportedMetricOperationError,
        match="not yet been validated",
    ):

        tool.latency_quantile(
            family="rpc_client",
            service="checkout",
            operation=(
                "oteldemo."
                "PaymentService/"
                "Charge"
            ),
            quantile=0.95,
            window=window(),
        )


def test_empty_prometheus_result():

    client = (
        FakePrometheusClient(
            [
                ()
            ]
        )
    )

    tool = MetricsTool(
        client
    )

    with pytest.raises(
        MetricUnavailableError,
        match="no series",
    ):

        tool.request_rate(
            family="rpc_server",
            service="checkout",
            window=window(),
        )


def test_multiple_scalar_results_are_rejected():

    client = (
        FakePrometheusClient(
            [
                (
                    InstantSample(
                        metric={},
                        timestamp=1,
                        value=1,
                    ),
                    InstantSample(
                        metric={},
                        timestamp=1,
                        value=2,
                    ),
                )
            ]
        )
    )

    tool = MetricsTool(
        client
    )

    with pytest.raises(
        MetricCardinalityError,
        match="Expected one",
    ):

        tool.request_rate(
            family="rpc_server",
            service="checkout",
            window=window(),
        )


def test_nan_is_rejected():

    client = (
        FakePrometheusClient(
            [
                sample(
                    math.nan
                )
            ]
        )
    )

    tool = MetricsTool(
        client
    )

    with pytest.raises(
        MetricUnavailableError,
        match="non-finite",
    ):

        tool.request_rate(
            family="rpc_server",
            service="checkout",
            window=window(),
        )


def test_invalid_quantile_is_rejected():

    client = (
        FakePrometheusClient(
            []
        )
    )

    tool = MetricsTool(
        client
    )

    with pytest.raises(
        ValueError,
        match="strictly between",
    ):

        tool.latency_quantile(
            family="rpc_server",
            service="checkout",
            quantile=1.0,
            window=window(),
        )


def test_label_values_are_escaped():

    client = (
        FakePrometheusClient(
            [
                sample(
                    1.0
                )
            ]
        )
    )

    tool = MetricsTool(
        client
    )

    tool.request_rate(
        family="rpc_server",
        service='check"out',
        window=window(),
    )

    query = (
        client.calls[0][
            "promql"
        ]
    )

    assert (
        'service_name="check\\"out"'
        in query
    )

def test_rpc_client_request_count():

    client = FakePrometheusClient(
        [
            sample(
                42.0
            )
        ]
    )

    tool = MetricsTool(
        client
    )

    evidence = tool.request_count(
        family="rpc_client",
        service="checkout",
        operation=(
            "oteldemo."
            "PaymentService/"
            "Charge"
        ),
        window=window(),
    )

    assert (
        evidence.value
        == pytest.approx(
            42.0
        )
    )

    assert (
        evidence.unit
        == "requests"
    )

    query = client.calls[0][
        "promql"
    ]

    assert (
        "increase("
        in query
    )

    assert (
        "[300s]"
        in query
    )
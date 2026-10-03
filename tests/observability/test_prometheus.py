import json

from datetime import (
    datetime,
    timezone,
)
from urllib.error import URLError
from urllib.parse import (
    parse_qs,
    urlparse,
)

import pytest

import rootlens.observability.prometheus as prometheus_module

from rootlens.observability.prometheus import (
    InstantSample,
    PrometheusAPIError,
    PrometheusClient,
    PrometheusResponseError,
    PrometheusTransportError,
    RangeSeries,
)


class FakeHTTPResponse:

    def __init__(
        self,
        payload,
    ):

        self.payload = payload

    def read(
        self,
    ):

        return json.dumps(
            self.payload
        ).encode(
            "utf-8"
        )

    def __enter__(
        self,
    ):

        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):

        return False


def install_fake_response(
    monkeypatch,
    payload,
):

    captured = {}

    def fake_urlopen(
        request,
        timeout,
    ):

        captured[
            "url"
        ] = request.full_url

        captured[
            "timeout"
        ] = timeout

        return FakeHTTPResponse(
            payload
        )

    monkeypatch.setattr(
        prometheus_module,
        "urlopen",
        fake_urlopen,
    )

    return captured


def test_instant_query_parses_vector(
    monkeypatch,
):

    payload = {
        "status":
            "success",

        "data": {
            "resultType":
                "vector",

            "result": [
                {
                    "metric": {
                        "service_name":
                            "checkout",
                    },

                    "value": [
                        1720000000.0,
                        "0.637",
                    ],
                }
            ],
        },
    }

    captured = (
        install_fake_response(
            monkeypatch,
            payload,
        )
    )

    client = PrometheusClient(
        "http://localhost:9090"
    )

    result = client.query(
        "up"
    )

    assert len(
        result
    ) == 1

    sample = result[0]

    assert isinstance(
        sample,
        InstantSample,
    )

    assert (
        sample.metric[
            "service_name"
        ]
        == "checkout"
    )

    assert (
        sample.timestamp
        == pytest.approx(
            1720000000.0
        )
    )

    assert (
        sample.value
        == pytest.approx(
            0.637
        )
    )

    parsed_url = urlparse(
        captured[
            "url"
        ]
    )

    assert (
        parsed_url.path
        == "/api/v1/query"
    )

    params = parse_qs(
        parsed_url.query
    )

    assert (
        params[
            "query"
        ]
        == ["up"]
    )


def test_instant_query_can_return_empty_vector(
    monkeypatch,
):

    payload = {
        "status":
            "success",

        "data": {
            "resultType":
                "vector",

            "result":
                [],
        },
    }

    install_fake_response(
        monkeypatch,
        payload,
    )

    client = PrometheusClient(
        "http://localhost:9090"
    )

    result = client.query(
        "missing_metric"
    )

    assert result == ()


def test_instant_query_preserves_labels(
    monkeypatch,
):

    payload = {
        "status":
            "success",

        "data": {
            "resultType":
                "vector",

            "result": [
                {
                    "metric": {
                        "service_name":
                            "checkout",

                        "status_code":
                            "500",
                    },

                    "value": [
                        10,
                        "4.2",
                    ],
                }
            ],
        },
    }

    install_fake_response(
        monkeypatch,
        payload,
    )

    client = PrometheusClient(
        "http://localhost:9090"
    )

    result = client.query(
        "some_metric"
    )

    assert result[0].metric == {
        "service_name":
            "checkout",

        "status_code":
            "500",
    }


def test_range_query_parses_matrix(
    monkeypatch,
):

    payload = {
        "status":
            "success",

        "data": {
            "resultType":
                "matrix",

            "result": [
                {
                    "metric": {
                        "service_name":
                            "checkout",
                    },

                    "values": [
                        [
                            100,
                            "0.1",
                        ],
                        [
                            115,
                            "0.2",
                        ],
                        [
                            130,
                            "0.3",
                        ],
                    ],
                }
            ],
        },
    }

    captured = (
        install_fake_response(
            monkeypatch,
            payload,
        )
    )

    client = PrometheusClient(
        "http://localhost:9090"
    )

    result = (
        client.query_range(
            "rate(requests_total[5m])",
            start=100,
            end=130,
            step=15,
        )
    )

    assert len(
        result
    ) == 1

    series = result[0]

    assert isinstance(
        series,
        RangeSeries,
    )

    assert (
        series.metric[
            "service_name"
        ]
        == "checkout"
    )

    assert len(
        series.samples
    ) == 3

    assert (
        series.samples[1].value
        == pytest.approx(
            0.2
        )
    )

    parsed_url = urlparse(
        captured[
            "url"
        ]
    )

    assert (
        parsed_url.path
        == "/api/v1/query_range"
    )

    params = parse_qs(
        parsed_url.query
    )

    assert (
        params[
            "start"
        ]
        == ["100"]
    )

    assert (
        params[
            "end"
        ]
        == ["130"]
    )

    assert (
        params[
            "step"
        ]
        == ["15"]
    )


def test_timezone_aware_datetime_is_supported(
    monkeypatch,
):

    payload = {
        "status":
            "success",

        "data": {
            "resultType":
                "vector",

            "result":
                [],
        },
    }

    captured = (
        install_fake_response(
            monkeypatch,
            payload,
        )
    )

    client = PrometheusClient(
        "http://localhost:9090"
    )

    timestamp = datetime(
        2026,
        10,
        2,
        8,
        30,
        tzinfo=timezone.utc,
    )

    client.query(
        "up",
        time=timestamp,
    )

    parsed_url = urlparse(
        captured[
            "url"
        ]
    )

    params = parse_qs(
        parsed_url.query
    )

    assert (
        float(
            params[
                "time"
            ][0]
        )
        == pytest.approx(
            timestamp.timestamp()
        )
    )


def test_naive_datetime_is_rejected():

    client = PrometheusClient(
        "http://localhost:9090"
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):

        client.query(
            "up",
            time=datetime(
                2026,
                10,
                2,
                8,
                30,
            ),
        )


def test_prometheus_api_error_is_raised(
    monkeypatch,
):

    payload = {
        "status":
            "error",

        "errorType":
            "bad_data",

        "error":
            "invalid parameter",
    }

    install_fake_response(
        monkeypatch,
        payload,
    )

    client = PrometheusClient(
        "http://localhost:9090"
    )

    with pytest.raises(
        PrometheusAPIError,
        match="bad_data",
    ):

        client.query(
            "invalid promql"
        )


def test_wrong_result_type_is_rejected(
    monkeypatch,
):

    payload = {
        "status":
            "success",

        "data": {
            "resultType":
                "matrix",

            "result":
                [],
        },
    }

    install_fake_response(
        monkeypatch,
        payload,
    )

    client = PrometheusClient(
        "http://localhost:9090"
    )

    with pytest.raises(
        PrometheusResponseError,
        match="Expected instant query",
    ):

        client.query(
            "up"
        )


def test_network_error_is_wrapped(
    monkeypatch,
):

    def fake_urlopen(
        request,
        timeout,
    ):

        raise URLError(
            "connection refused"
        )

    monkeypatch.setattr(
        prometheus_module,
        "urlopen",
        fake_urlopen,
    )

    client = PrometheusClient(
        "http://localhost:9090"
    )

    with pytest.raises(
        PrometheusTransportError,
        match="Could not reach Prometheus",
    ):

        client.query(
            "up"
        )


def test_empty_promql_is_rejected():

    client = PrometheusClient(
        "http://localhost:9090"
    )

    with pytest.raises(
        ValueError,
        match="non-empty",
    ):

        client.query(
            ""
        )


def test_non_positive_step_is_rejected():

    client = PrometheusClient(
        "http://localhost:9090"
    )

    with pytest.raises(
        ValueError,
        match="step must be positive",
    ):

        client.query_range(
            "up",
            start=0,
            end=100,
            step=0,
        )
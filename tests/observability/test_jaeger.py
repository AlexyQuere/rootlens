from __future__ import annotations

import io
import json

from datetime import (
    datetime,
    timezone,
)
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.parse import (
    parse_qs,
    urlparse,
)

import pytest

from rootlens.observability import (
    jaeger as jaeger_module,
)

from rootlens.observability.jaeger import (
    JaegerAPIError,
    JaegerClient,
    JaegerResponseError,
    JaegerTransportError,
)


class FakeResponse:

    def __init__(
        self,
        payload,
    ) -> None:

        self._raw = json.dumps(
            payload
        ).encode(
            "utf-8"
        )

    def read(
        self,
    ) -> bytes:

        return self._raw

    def __enter__(
        self,
    ):

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:

        return None


def aware(
    hour: int,
) -> datetime:

    return datetime(
        2026,
        10,
        3,
        hour,
        0,
        0,
        tzinfo=timezone.utc,
    )


def test_list_services_is_deterministic(
    monkeypatch,
):

    def fake_urlopen(
        request,
        timeout,
    ):

        assert timeout == 10.0

        return FakeResponse(
            {
                "services": [
                    "payment",
                    "checkout",
                ]
            }
        )

    monkeypatch.setattr(
        jaeger_module,
        "urlopen",
        fake_urlopen,
    )

    client = JaegerClient(
        "http://localhost:16686"
    )

    assert client.list_services() == (
        "checkout",
        "payment",
    )


def test_find_traces_builds_v3_query(
    monkeypatch,
):

    captured = {}

    def fake_urlopen(
        request,
        timeout,
    ):

        captured[
            "url"
        ] = request.full_url

        return FakeResponse(
            {
                "result": {
                    "resourceSpans": []
                }
            }
        )

    monkeypatch.setattr(
        jaeger_module,
        "urlopen",
        fake_urlopen,
    )

    client = JaegerClient(
        "http://localhost:16686"
    )

    result = client.find_traces(
        service_name="checkout",
        start=aware(10),
        end=aware(11),
        num_traces=5,
    )

    assert (
        result.resource_spans
        == ()
    )

    parsed = urlparse(
        captured["url"]
    )

    assert parsed.path == (
        "/jaeger/ui/api/v3/traces"
    )

    query = parse_qs(
        parsed.query
    )

    assert query[
        "query.service_name"
    ] == [
        "checkout"
    ]

    assert query[
        "query.num_traces"
    ] == [
        "5"
    ]

    assert query[
        "query.start_time_min"
    ] == [
        "2026-10-03T10:00:00.000000Z"
    ]

    assert query[
        "query.start_time_max"
    ] == [
        "2026-10-03T11:00:00.000000Z"
    ]


def test_find_traces_can_filter_operation(
    monkeypatch,
):

    captured = {}

    def fake_urlopen(
        request,
        timeout,
    ):

        captured[
            "url"
        ] = request.full_url

        return FakeResponse(
            {
                "result": {
                    "resourceSpans": []
                }
            }
        )

    monkeypatch.setattr(
        jaeger_module,
        "urlopen",
        fake_urlopen,
    )

    client = JaegerClient(
        "http://localhost:16686"
    )

    client.find_traces(
        service_name="checkout",
        operation_name=(
            "oteldemo."
            "CheckoutService/"
            "PlaceOrder"
        ),
        start=aware(10),
        end=aware(11),
    )

    query = parse_qs(
        urlparse(
            captured["url"]
        ).query
    )

    assert query[
        "query.operation_name"
    ] == [
        (
            "oteldemo."
            "CheckoutService/"
            "PlaceOrder"
        )
    ]


def test_find_traces_preserves_raw_resource_spans(
    monkeypatch,
):

    raw_resource_span = {
        "resource": {
            "attributes": []
        },
        "scopeSpans": [],
    }

    monkeypatch.setattr(
        jaeger_module,
        "urlopen",
        lambda request, timeout:
            FakeResponse(
                {
                    "result": {
                        "resourceSpans": [
                            raw_resource_span
                        ]
                    }
                }
            ),
    )

    client = JaegerClient(
        "http://localhost:16686"
    )

    result = client.find_traces(
        service_name="checkout",
        start=aware(10),
        end=aware(11),
    )

    assert len(
        result.resource_spans
    ) == 1

    assert (
        result.resource_spans[0]
        == raw_resource_span
    )


def test_get_trace(
    monkeypatch,
):

    captured = {}

    def fake_urlopen(
        request,
        timeout,
    ):

        captured[
            "url"
        ] = request.full_url

        return FakeResponse(
            {
                "result": {
                    "resourceSpans": []
                }
            }
        )

    monkeypatch.setattr(
        jaeger_module,
        "urlopen",
        fake_urlopen,
    )

    client = JaegerClient(
        "http://localhost:16686"
    )

    trace_id = (
        "0123456789abcdef"
        "0123456789abcdef"
    )

    client.get_trace(
        trace_id
    )

    assert captured[
        "url"
    ].endswith(
        f"/traces/{trace_id}"
    )


def test_get_trace_rejects_invalid_id():

    client = JaegerClient(
        "http://localhost:16686"
    )

    with pytest.raises(
        ValueError
    ):

        client.get_trace(
            "not-a-trace-id"
        )


def test_find_traces_rejects_naive_time():

    client = JaegerClient(
        "http://localhost:16686"
    )

    with pytest.raises(
        ValueError
    ):

        client.find_traces(
            service_name="checkout",
            start=datetime(
                2026,
                10,
                3,
                10,
            ),
            end=aware(11),
        )


def test_find_traces_rejects_invalid_window():

    client = JaegerClient(
        "http://localhost:16686"
    )

    with pytest.raises(
        ValueError
    ):

        client.find_traces(
            service_name="checkout",
            start=aware(11),
            end=aware(10),
        )


def test_find_traces_rejects_zero_limit():

    client = JaegerClient(
        "http://localhost:16686"
    )

    with pytest.raises(
        ValueError
    ):

        client.find_traces(
            service_name="checkout",
            start=aware(10),
            end=aware(11),
            num_traces=0,
        )


def test_api_error(
    monkeypatch,
):

    def fake_urlopen(
        request,
        timeout,
    ):

        raise HTTPError(
            request.full_url,
            500,
            "boom",
            hdrs=None,
            fp=io.BytesIO(
                b'{"error":"boom"}'
            ),
        )

    monkeypatch.setattr(
        jaeger_module,
        "urlopen",
        fake_urlopen,
    )

    client = JaegerClient(
        "http://localhost:16686"
    )

    with pytest.raises(
        JaegerAPIError
    ):

        client.list_services()


def test_transport_error(
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
        jaeger_module,
        "urlopen",
        fake_urlopen,
    )

    client = JaegerClient(
        "http://localhost:16686"
    )

    with pytest.raises(
        JaegerTransportError
    ):

        client.list_services()


def test_invalid_trace_schema(
    monkeypatch,
):

    monkeypatch.setattr(
        jaeger_module,
        "urlopen",
        lambda request, timeout:
            FakeResponse(
                {
                    "result": {
                        "resourceSpans":
                            "not-a-list"
                    }
                }
            ),
    )

    client = JaegerClient(
        "http://localhost:16686"
    )

    with pytest.raises(
        JaegerResponseError
    ):

        client.find_traces(
            service_name="checkout",
            start=aware(10),
            end=aware(11),
        )

def test_find_traces_returns_empty_on_no_traces(
    monkeypatch,
):

    def fake_urlopen(
        request,
        timeout,
    ):

        raise HTTPError(
            request.full_url,
            404,
            "Not Found",
            hdrs=None,
            fp=io.BytesIO(
                (
                    b'{"error":{'
                    b'"httpCode":404,'
                    b'"message":"No traces found"'
                    b'}}'
                )
            ),
        )

    monkeypatch.setattr(
        jaeger_module,
        "urlopen",
        fake_urlopen,
    )

    client = JaegerClient(
        "http://localhost:8080"
    )

    result = client.find_traces(
        service_name="checkout",
        start=aware(10),
        end=aware(11),
    )

    assert result.resource_spans == ()
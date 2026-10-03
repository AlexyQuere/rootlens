from __future__ import annotations

import io
import json

from datetime import (
    datetime,
    timezone,
)
from urllib.error import HTTPError

import pytest

import rootlens.observability.opensearch as opensearch_module

from rootlens.observability.opensearch import (
    OpenSearchAPIError,
    OpenSearchClient,
)


class FakeResponse:
    def __init__(
        self,
        payload: dict,
    ) -> None:
        self.payload = payload

    def read(
        self,
    ) -> bytes:
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
        tb,
    ):
        return False


def test_search_logs_parses_hit(
    monkeypatch,
):
    captured = {}

    payload = {
        "took": 4,
        "timed_out": False,

        "hits": {
            "total": {
                "value": 1,
                "relation": "eq",
            },

            "hits": [
                {
                    "_index":
                        "otel-logs-2026-10-03",

                    "_id":
                        "abc",

                    "_source": {
                        "@timestamp":
                            (
                                "2026-10-03"
                                "T13:29:24"
                                ".940475510Z"
                            ),

                        "observedTimestamp":
                            (
                                "2026-10-03"
                                "T13:29:25"
                                ".166777760Z"
                            ),

                        "body":
                            "[PlaceOrder]",

                        "severity": {
                            "text":
                                "INFO",

                            "number":
                                9,
                        },

                        "traceId":
                            (
                                "0123456789abcdef"
                                "0123456789abcdef"
                            ),

                        "spanId":
                            (
                                "0123456789abcdef"
                            ),

                        "attributes": {
                            "test": True,
                        },

                        "resource": {
                            "service.name":
                                "checkout",
                        },

                        "instrumentationScope":
                            {},
                    },
                }
            ],
        },
    }

    def fake_urlopen(
        request,
        timeout,
    ):
        captured[
            "url"
        ] = request.full_url

        captured[
            "body"
        ] = json.loads(
            request.data.decode(
                "utf-8"
            )
        )

        return FakeResponse(
            payload
        )

    monkeypatch.setattr(
        opensearch_module,
        "urlopen",
        fake_urlopen,
    )

    client = OpenSearchClient(
        "http://localhost:9200"
    )

    start = datetime(
        2026,
        10,
        3,
        13,
        0,
        tzinfo=timezone.utc,
    )

    end = datetime(
        2026,
        10,
        3,
        14,
        0,
        tzinfo=timezone.utc,
    )

    result = client.search_logs(
        start=start,
        end=end,

        service_name="checkout",

        trace_id=(
            "0123456789abcdef"
            "0123456789abcdef"
        ),

        limit=20,
    )

    assert result.total_hits == 1
    assert result.took_ms == 4
    assert not result.timed_out

    assert len(
        result.logs
    ) == 1

    log = result.logs[0]

    assert (
        log.service_name
        == "checkout"
    )

    assert (
        log.severity_text
        == "INFO"
    )

    assert (
        log.body
        == "[PlaceOrder]"
    )

    assert (
        log.event_timestamp_raw
        ==
        "2026-10-03T13:29:24.940475510Z"
    )

    assert (
        log.observed_timestamp_raw
        ==
        "2026-10-03T13:29:25.166777760Z"
    )

    assert (
        log.observed_minus_event_ms
        is not None
    )

    assert (
        "ignore_unavailable=true"
        in captured["url"]
    )

    request_body = (
        captured["body"]
    )

    assert (
        request_body["size"]
        == 20
    )

    assert (
        result.query.service_name
        == "checkout"
    )

    assert (
        result.query.time_field
        == "observedTimestamp"
    )

    filters = (
        request_body[
            "query"
        ][
            "bool"
        ][
            "filter"
        ]
    )

    assert (
        "observedTimestamp"
        in filters[0]["range"]
    )


def test_missing_optional_fields(
    monkeypatch,
):
    payload = {
        "hits": {
            "total": {
                "value": 1,
            },

            "hits": [
                {
                    "_index": "logs",
                    "_id": "1",

                    "_source": {
                        "observedTimestamp":
                            (
                                "2026-10-03"
                                "T13:00:00Z"
                            ),

                        "body":
                            "message",

                        "severity": {},

                        "resource": {
                            "service.name":
                                "frontend-proxy",
                        },
                    },
                }
            ],
        }
    }

    monkeypatch.setattr(
        opensearch_module,
        "urlopen",
        lambda request, timeout:
            FakeResponse(
                payload
            ),
    )

    client = OpenSearchClient(
        "http://localhost:9200"
    )

    start = datetime(
        2026,
        10,
        3,
        12,
        0,
        tzinfo=timezone.utc,
    )

    end = datetime(
        2026,
        10,
        3,
        14,
        0,
        tzinfo=timezone.utc,
    )

    result = client.search_logs(
        start=start,
        end=end,
    )

    log = result.logs[0]

    assert log.trace_id is None
    assert log.span_id is None

    assert (
        log.severity_text
        is None
    )

    assert (
        log.event_timestamp
        is None
    )

    assert (
        log.event_timestamp_raw
        is None
    )

    assert (
        log.observed_timestamp_raw
        ==
        "2026-10-03T13:00:00Z"
    )


def test_empty_result(
    monkeypatch,
):
    payload = {
        "hits": {
            "total": {
                "value": 0,
            },

            "hits": [],
        }
    }

    monkeypatch.setattr(
        opensearch_module,
        "urlopen",
        lambda request, timeout:
            FakeResponse(
                payload
            ),
    )

    client = OpenSearchClient(
        "http://localhost:9200"
    )

    start = datetime(
        2026,
        10,
        3,
        12,
        0,
        tzinfo=timezone.utc,
    )

    end = datetime(
        2026,
        10,
        3,
        13,
        0,
        tzinfo=timezone.utc,
    )

    result = client.search_logs(
        start=start,
        end=end,
    )

    assert result.logs == ()
    assert result.total_hits == 0


def test_can_query_by_event_timestamp(
    monkeypatch,
):
    captured = {}

    payload = {
        "hits": {
            "total": {
                "value": 0,
            },
            "hits": [],
        }
    }

    def fake_urlopen(
        request,
        timeout,
    ):
        captured[
            "body"
        ] = json.loads(
            request.data.decode(
                "utf-8"
            )
        )

        return FakeResponse(
            payload
        )

    monkeypatch.setattr(
        opensearch_module,
        "urlopen",
        fake_urlopen,
    )

    client = OpenSearchClient(
        "http://localhost:9200"
    )

    start = datetime(
        2026,
        10,
        3,
        12,
        0,
        tzinfo=timezone.utc,
    )

    end = datetime(
        2026,
        10,
        3,
        13,
        0,
        tzinfo=timezone.utc,
    )

    result = client.search_logs(
        start=start,
        end=end,
        time_field="@timestamp",
    )

    filters = (
        captured[
            "body"
        ][
            "query"
        ][
            "bool"
        ][
            "filter"
        ]
    )

    assert (
        "@timestamp"
        in filters[0]["range"]
    )

    assert (
        result.query.time_field
        == "@timestamp"
    )


def test_http_error(
    monkeypatch,
):
    def fake_urlopen(
        request,
        timeout,
    ):
        raise HTTPError(
            request.full_url,
            500,
            "Internal Server Error",
            hdrs=None,
            fp=io.BytesIO(
                b'{"error":"boom"}'
            ),
        )

    monkeypatch.setattr(
        opensearch_module,
        "urlopen",
        fake_urlopen,
    )

    client = OpenSearchClient(
        "http://localhost:9200"
    )

    start = datetime(
        2026,
        10,
        3,
        12,
        0,
        tzinfo=timezone.utc,
    )

    end = datetime(
        2026,
        10,
        3,
        13,
        0,
        tzinfo=timezone.utc,
    )

    with pytest.raises(
        OpenSearchAPIError
    ):
        client.search_logs(
            start=start,
            end=end,
        )
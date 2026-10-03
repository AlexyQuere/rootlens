from __future__ import annotations

import pytest

from rootlens.observability.jaeger import (
    JaegerTracePayload,
)

from rootlens.observability.otlp_trace import (
    OTLPTraceParseError,
    parse_otlp_traces,
)

from rootlens.observability.trace_evidence import (
    SpanKind,
    SpanStatusCode,
)


TRACE_ID = (
    "0123456789abcdef"
    "0123456789abcdef"
)

SPAN_ID = (
    "0123456789abcdef"
)


def payload_with_span(
    span: dict,
) -> JaegerTracePayload:

    return JaegerTracePayload(
        resource_spans=(
            {
                "resource": {
                    "attributes": [
                        {
                            "key": "service.name",
                            "value": {
                                "stringValue":
                                    "checkout"
                            },
                        }
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {
                            "name":
                                "otelgrpc",
                            "version":
                                "1.0",
                        },
                        "spans": [
                            span
                        ],
                    }
                ],
            },
        )
    )


def base_span() -> dict:

    return {
        "traceId":
            TRACE_ID,

        "spanId":
            SPAN_ID,

        "name":
            (
                "oteldemo."
                "CheckoutService/"
                "PlaceOrder"
            ),

        "kind":
            2,

        "startTimeUnixNano":
            "1000000000",

        "endTimeUnixNano":
            "1250000000",

        "status": {
            "code": 2,
            "message": "boom",
        },

        "attributes": [
            {
                "key":
                    "rpc.system",

                "value": {
                    "stringValue":
                        "grpc"
                },
            },
            {
                "key":
                    "retry.count",

                "value": {
                    "intValue":
                        "2"
                },
            },
        ],
    }


def test_parse_span():

    traces = parse_otlp_traces(
        payload_with_span(
            base_span()
        )
    )

    assert len(
        traces
    ) == 1

    trace = traces[0]

    assert trace.trace_id == (
        TRACE_ID
    )

    assert len(
        trace.spans
    ) == 1

    span = trace.spans[0]

    assert (
        span.service_name
        == "checkout"
    )

    assert (
        span.kind
        == SpanKind.SERVER
    )

    assert (
        span.status_code
        == SpanStatusCode.ERROR
    )

    assert (
        span.duration_ms
        == pytest.approx(
            250.0
        )
    )

    assert (
        span.attributes[
            "retry.count"
        ]
        == 2
    )


def test_empty_parent_is_root():

    span = base_span()

    span[
        "parentSpanId"
    ] = ""

    trace = parse_otlp_traces(
        payload_with_span(
            span
        )
    )[0]

    assert len(
        trace.root_spans
    ) == 1


def test_event_parsing():

    span = base_span()

    span["events"] = [
        {
            "name": "charged",
            "timeUnixNano":
                "1100000000",
            "attributes": [],
        }
    ]

    parsed = parse_otlp_traces(
        payload_with_span(
            span
        )
    )[0].spans[0]

    assert (
        parsed.events[0].name
        == "charged"
    )


def test_accepts_named_enums():

    span = base_span()

    span[
        "kind"
    ] = "SPAN_KIND_CLIENT"

    span[
        "status"
    ] = {
        "code":
            "STATUS_CODE_ERROR"
    }

    parsed = parse_otlp_traces(
        payload_with_span(
            span
        )
    )[0].spans[0]

    assert (
        parsed.kind
        == SpanKind.CLIENT
    )

    assert (
        parsed.status_code
        == SpanStatusCode.ERROR
    )


def test_rejects_invalid_trace_id():

    span = base_span()

    span[
        "traceId"
    ] = "bad"

    with pytest.raises(
        OTLPTraceParseError
    ):
        parse_otlp_traces(
            payload_with_span(
                span
            )
        )


def test_rejects_negative_duration():

    span = base_span()

    span[
        "endTimeUnixNano"
    ] = "1"

    with pytest.raises(
        OTLPTraceParseError
    ):
        parse_otlp_traces(
            payload_with_span(
                span
            )
        )
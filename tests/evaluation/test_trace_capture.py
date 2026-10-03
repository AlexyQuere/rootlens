from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from rootlens.evaluation.trace_capture import (
    capture_relation_window,
    trace_has_span_in_window,
)

from rootlens.evaluation.trace_incident import (
    ClientServerRelationSpec,
)

from rootlens.observability.jaeger import (
    JaegerTracePayload,
)

from rootlens.observability.trace_evidence import (
    SpanEvidence,
    SpanKind,
    SpanStatusCode,
    TraceEvidence,
)

from rootlens.observability.trace_investigation import (
    TraceInvestigationTool,
)


TRACE_ID = (
    "0123456789abcdef"
    "0123456789abcdef"
)


def make_trace() -> TraceEvidence:

    start = datetime(
        2026,
        10,
        3,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    start_ns = int(
        start.timestamp()
        * 1_000_000_000
    )

    span = SpanEvidence(
        trace_id=TRACE_ID,
        span_id=(
            "0000000000000001"
        ),
        parent_span_id=None,
        service_name="checkout",
        operation_name=(
            "oteldemo."
            "CheckoutService/"
            "PlaceOrder"
        ),
        kind=SpanKind.SERVER,
        start_time_unix_nano=(
            start_ns
        ),
        end_time_unix_nano=(
            start_ns
            + 10_000_000
        ),
        status_code=(
            SpanStatusCode.UNSET
        ),
        status_message=None,
        attributes={},
        resource_attributes={},
    )

    return TraceEvidence(
        trace_id=TRACE_ID,
        spans=(span,),
    )


def test_trace_has_span_in_window():

    trace = make_trace()

    start = datetime(
        2026,
        10,
        3,
        9,
        59,
        tzinfo=timezone.utc,
    )

    end = (
        start
        + timedelta(
            minutes=2
        )
    )

    assert trace_has_span_in_window(
        trace,
        start=start,
        end=end,
        service_name="checkout",
        operation_name=(
            "oteldemo."
            "CheckoutService/"
            "PlaceOrder"
        ),
        kind=SpanKind.SERVER,
    )


def test_trace_outside_window():

    trace = make_trace()

    start = datetime(
        2026,
        10,
        3,
        11,
        0,
        tzinfo=timezone.utc,
    )

    end = (
        start
        + timedelta(
            minutes=1
        )
    )

    assert not trace_has_span_in_window(
        trace,
        start=start,
        end=end,
        service_name="checkout",
        operation_name=(
            "oteldemo."
            "CheckoutService/"
            "PlaceOrder"
        ),
        kind=SpanKind.SERVER,
    )


class EmptyJaegerClient:

    def find_traces(
        self,
        **kwargs,
    ):

        return JaegerTracePayload(
            resource_spans=()
        )

    def get_trace(
        self,
        trace_id,
    ):

        raise AssertionError(
            "get_trace should not "
            "be called."
        )


def test_empty_window_capture():

    start = datetime(
        2026,
        10,
        3,
        10,
        0,
        tzinfo=timezone.utc,
    )

    end = (
        start
        + timedelta(
            minutes=5
        )
    )

    spec = ClientServerRelationSpec(
        client_service="checkout",
        client_operation=(
            "oteldemo."
            "PaymentService/"
            "Charge"
        ),
        server_service="payment",
        server_operation=(
            "oteldemo."
            "PaymentService/"
            "Charge"
        ),
    )

    result = capture_relation_window(
        client=EmptyJaegerClient(),
        tool=TraceInvestigationTool(),
        relation_spec=spec,
        start=start,
        end=end,
        search_service="checkout",
        search_operation=(
            "oteldemo."
            "CheckoutService/"
            "PlaceOrder"
        ),
    )

    assert (
        result["search"][
            "discovered_trace_count"
        ]
        == 0
    )

    assert (
        result[
            "fetched_trace_count"
        ]
        == 0
    )

    assert (
        result["raw_traces"]
        == []
    )

    assert (
        result["summary"][
            "trace_count"
        ]
        == 0
    )
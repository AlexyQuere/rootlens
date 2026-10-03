from __future__ import annotations

from rootlens.observability.trace_evidence import (
    SpanEvidence,
    SpanKind,
    SpanStatusCode,
    TraceEvidence,
)

from rootlens.observability.trace_investigation import (
    TraceInvestigationTool,
)


BASELINE_TRACE_ID = (
    "0123456789abcdef"
    "0123456789abcdef"
)

INCIDENT_TRACE_ID = (
    "fedcba9876543210"
    "fedcba9876543210"
)


def make_span(
    *,
    trace_id: str,
    span_id: str,
    parent_span_id: str | None,
    service: str,
    operation: str,
    kind: SpanKind,
    start: int,
    end: int,
    status:
        SpanStatusCode
        = SpanStatusCode.UNSET,
) -> SpanEvidence:

    return SpanEvidence(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=(
            parent_span_id
        ),
        service_name=service,
        operation_name=operation,
        kind=kind,
        start_time_unix_nano=start,
        end_time_unix_nano=end,
        status_code=status,
        status_message=None,
        attributes={},
        resource_attributes={},
    )


def build_trace(
    *,
    trace_id: str,
    include_payment_server:
        bool = True,
) -> TraceEvidence:

    root = make_span(
        trace_id=trace_id,
        span_id="0000000000000001",
        parent_span_id=None,
        service="load-generator",
        operation="user_checkout_single",
        kind=SpanKind.INTERNAL,
        start=0,
        end=100_000_000,
    )

    frontend_client = make_span(
        trace_id=trace_id,
        span_id="0000000000000002",
        parent_span_id=(
            "0000000000000001"
        ),
        service="frontend",
        operation=(
            "CheckoutService/"
            "PlaceOrder"
        ),
        kind=SpanKind.CLIENT,
        start=10_000_000,
        end=90_000_000,
    )

    checkout_server = make_span(
        trace_id=trace_id,
        span_id="0000000000000003",
        parent_span_id=(
            "0000000000000002"
        ),
        service="checkout",
        operation=(
            "CheckoutService/"
            "PlaceOrder"
        ),
        kind=SpanKind.SERVER,
        start=12_000_000,
        end=85_000_000,
        status=(
            SpanStatusCode.ERROR
        ),
    )

    payment_client = make_span(
        trace_id=trace_id,
        span_id="0000000000000004",
        parent_span_id=(
            "0000000000000003"
        ),
        service="checkout",
        operation=(
            "PaymentService/"
            "Charge"
        ),
        kind=SpanKind.CLIENT,
        start=20_000_000,
        end=60_000_000,
        status=(
            SpanStatusCode.ERROR
        ),
    )

    db_client = make_span(
        trace_id=trace_id,
        span_id="0000000000000006",
        parent_span_id=(
            "0000000000000003"
        ),
        service="checkout",
        operation="database",
        kind=SpanKind.CLIENT,
        start=30_000_000,
        end=40_000_000,
    )

    spans = [
        root,
        frontend_client,
        checkout_server,
        payment_client,
        db_client,
    ]

    if include_payment_server:

        spans.append(
            make_span(
                trace_id=trace_id,
                span_id=(
                    "0000000000000005"
                ),
                parent_span_id=(
                    "0000000000000004"
                ),
                service="payment",
                operation=(
                    "PaymentService/"
                    "Charge"
                ),
                kind=SpanKind.SERVER,
                start=22_000_000,
                end=50_000_000,
                status=(
                    SpanStatusCode.ERROR
                ),
            )
        )

    return TraceEvidence(
        trace_id=trace_id,
        spans=tuple(
            spans
        ),
    )


def test_summary():

    trace = build_trace(
        trace_id=BASELINE_TRACE_ID
    )

    tool = (
        TraceInvestigationTool()
    )

    summary = tool.summarize(
        trace
    )

    assert summary.span_count == 6
    assert summary.root_count == 1
    assert summary.orphan_count == 0

    assert (
        summary.error_span_count
        == 3
    )

    assert (
        summary.single_root_service
        == "load-generator"
    )

    assert (
        summary.single_root_duration_ms
        == 100.0
    )


def test_find_error_spans():

    trace = build_trace(
        trace_id=BASELINE_TRACE_ID
    )

    tool = (
        TraceInvestigationTool()
    )

    errors = (
        tool.find_error_spans(
            trace
        )
    )

    assert {
        span.span_id
        for span in errors
    } == {
        "0000000000000003",
        "0000000000000004",
        "0000000000000005",
    }


def test_find_slow_spans():

    trace = build_trace(
        trace_id=BASELINE_TRACE_ID
    )

    tool = (
        TraceInvestigationTool()
    )

    slow = (
        tool.find_slow_spans(
            trace,
            limit=2,
        )
    )

    assert [
        span.span_id
        for span in slow
    ] == [
        "0000000000000001",
        "0000000000000002",
    ]


def test_client_server_pairs():

    trace = build_trace(
        trace_id=BASELINE_TRACE_ID
    )

    tool = (
        TraceInvestigationTool()
    )

    pairs = (
        tool.find_client_server_pairs(
            trace
        )
    )

    assert {
        (
            pair.client.span_id,
            pair.server.span_id,
        )
        for pair in pairs
    } == {
        (
            "0000000000000002",
            "0000000000000003",
        ),
        (
            "0000000000000004",
            "0000000000000005",
        ),
    }


def test_unmatched_client_spans():

    trace = build_trace(
        trace_id=BASELINE_TRACE_ID
    )

    tool = (
        TraceInvestigationTool()
    )

    unmatched = (
        tool.find_unmatched_client_spans(
            trace
        )
    )

    assert {
        span.span_id
        for span in unmatched
    } == {
        "0000000000000006"
    }


def test_payment_client_becomes_unmatched():

    trace = build_trace(
        trace_id=BASELINE_TRACE_ID,
        include_payment_server=False,
    )

    tool = (
        TraceInvestigationTool()
    )

    unmatched = (
        tool.find_unmatched_client_spans(
            trace
        )
    )

    assert {
        span.span_id
        for span in unmatched
    } == {
        "0000000000000004",
        "0000000000000006",
    }


def test_compare_trace_paths_detects_missing_server():

    baseline = build_trace(
        trace_id=BASELINE_TRACE_ID,
        include_payment_server=True,
    )

    incident = build_trace(
        trace_id=INCIDENT_TRACE_ID,
        include_payment_server=False,
    )

    tool = (
        TraceInvestigationTool()
    )

    comparison = (
        tool.compare_trace_paths(
            baseline,
            incident,
        )
    )

    assert not comparison.identical

    assert len(
        comparison.differences
    ) == 1

    difference = (
        comparison.differences[0]
    )

    assert (
        difference.edge
        .parent_service
        == "checkout"
    )

    assert (
        difference.edge
        .child_service
        == "payment"
    )

    assert (
        difference.baseline_count
        == 1
    )

    assert (
        difference.incident_count
        == 0
    )

    assert difference.delta == -1
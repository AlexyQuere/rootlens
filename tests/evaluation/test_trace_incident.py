from __future__ import annotations

from rootlens.evaluation.trace_incident import (
    ClientServerRelationSpec,
    observe_relation,
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


SPEC = ClientServerRelationSpec(
    client_service="checkout",
    client_operation=(
        "oteldemo.PaymentService/Charge"
    ),
    server_service="payment",
    server_operation=(
        "oteldemo.PaymentService/Charge"
    ),
)


def make_span(
    *,
    span_id: str,
    parent_span_id: str | None,
    service: str,
    operation: str,
    kind: SpanKind,
    status: SpanStatusCode,
) -> SpanEvidence:

    return SpanEvidence(
        trace_id=TRACE_ID,
        span_id=span_id,
        parent_span_id=parent_span_id,
        service_name=service,
        operation_name=operation,
        kind=kind,
        start_time_unix_nano=0,
        end_time_unix_nano=1_000_000,
        status_code=status,
        status_message=None,
        attributes={},
        resource_attributes={},
    )


def build_trace(
    *,
    client_status:
        SpanStatusCode,
    include_server: bool,
    server_status:
        SpanStatusCode
        = SpanStatusCode.UNSET,
) -> TraceEvidence:

    root = make_span(
        span_id="0000000000000001",
        parent_span_id=None,
        service="checkout",
        operation=(
            "oteldemo."
            "CheckoutService/"
            "PlaceOrder"
        ),
        kind=SpanKind.SERVER,
        status=client_status,
    )

    client = make_span(
        span_id="0000000000000002",
        parent_span_id=(
            "0000000000000001"
        ),
        service="checkout",
        operation=(
            "oteldemo."
            "PaymentService/"
            "Charge"
        ),
        kind=SpanKind.CLIENT,
        status=client_status,
    )

    spans = [
        root,
        client,
    ]

    if include_server:

        spans.append(
            make_span(
                span_id=(
                    "0000000000000003"
                ),
                parent_span_id=(
                    "0000000000000002"
                ),
                service="payment",
                operation=(
                    "oteldemo."
                    "PaymentService/"
                    "Charge"
                ),
                kind=SpanKind.SERVER,
                status=server_status,
            )
        )

    return TraceEvidence(
        trace_id=TRACE_ID,
        spans=tuple(
            spans
        ),
    )


def test_non_error_pair():

    trace = build_trace(
        client_status=(
            SpanStatusCode.UNSET
        ),
        include_server=True,
    )

    observation = observe_relation(
        trace,
        spec=SPEC,
        tool=TraceInvestigationTool(),
    )

    assert (
        observation.classification
        ==
        "client_non_error_server_non_error"
    )


def test_error_pair():

    trace = build_trace(
        client_status=(
            SpanStatusCode.ERROR
        ),
        include_server=True,
        server_status=(
            SpanStatusCode.ERROR
        ),
    )

    observation = observe_relation(
        trace,
        spec=SPEC,
        tool=TraceInvestigationTool(),
    )

    assert (
        observation.classification
        ==
        "client_error_server_error"
    )


def test_error_without_server():

    trace = build_trace(
        client_status=(
            SpanStatusCode.ERROR
        ),
        include_server=False,
    )

    observation = observe_relation(
        trace,
        spec=SPEC,
        tool=TraceInvestigationTool(),
    )

    assert (
        observation.classification
        ==
        "client_error_no_server"
    )


def test_non_error_without_server():

    trace = build_trace(
        client_status=(
            SpanStatusCode.UNSET
        ),
        include_server=False,
    )

    observation = observe_relation(
        trace,
        spec=SPEC,
        tool=TraceInvestigationTool(),
    )

    assert (
        observation.classification
        ==
        "client_non_error_no_server"
    )
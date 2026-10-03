from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)

from rootlens.observability.incident_view import (
    build_incident_evidence_view,
)
from rootlens.observability.log_evidence import (
    LogEvidence,
)
from rootlens.observability.metric_identity import (
    MetricFamily,
    MetricServiceBinding,
    MetricServiceRole,
)
from rootlens.observability.unified_evidence import (
    AcquisitionState,
    EvidenceModality,
    IncidentEvidenceBundle,
    ModalityAcquisition,
)


@dataclass(frozen=True)
class FakeSpan:
    span_id: str
    service_name: str | None


@dataclass(frozen=True)
class FakeTrace:
    trace_id: str

    spans: tuple[
        FakeSpan,
        ...
    ]


def timestamp():
    return datetime(
        2026,
        10,
        3,
        13,
        0,
        tzinfo=timezone.utc,
    )


def make_log(
    *,
    document_id: str,

    service_name: str | None,

    trace_id: str | None,

    span_id: str | None,

    body: str = "message",
) -> LogEvidence:
    time = timestamp()

    return LogEvidence(
        event_timestamp=time,

        event_timestamp_raw=(
            "2026-10-03T13:00:00Z"
        ),

        observed_timestamp=time,

        observed_timestamp_raw=(
            "2026-10-03T13:00:00Z"
        ),

        service_name=(
            service_name
        ),

        severity_text="INFO",

        severity_number=None,

        body=body,

        trace_id=trace_id,

        span_id=span_id,

        attributes={},

        resource_attributes={},

        instrumentation_scope={},

        index="otel-logs",

        document_id=(
            document_id
        ),

        raw_source={},
    )


def make_window():
    start = timestamp()

    end = datetime(
        2026,
        10,
        3,
        13,
        5,
        tzinfo=timezone.utc,
    )

    return start, end


def test_service_view_combines_three_modalities():
    metric = object()

    trace = FakeTrace(
        trace_id="trace-1",

        spans=(
            FakeSpan(
                span_id="payment-span",

                service_name="payment",
            ),
        ),
    )

    log = make_log(
        document_id="log-1",

        service_name="payment",

        trace_id="trace-1",

        span_id="payment-span",

        body=(
            "Payment request failed"
        ),
    )

    start, end = make_window()

    bundle = (
        IncidentEvidenceBundle(
            incident_id="incident",

            start=start,
            end=end,

            metrics=(
                metric,
            ),

            traces=(
                trace,
            ),

            logs=(
                log,
            ),
        )
    )

    binding = (
        MetricServiceBinding(
            metric_index=0,

            metric_key=(
                "payment_error_rate"
            ),

            family=(
                MetricFamily.RPC_SERVER
            ),

            service_name="payment",
        )
    )

    view = (
        build_incident_evidence_view(
            bundle,

            metric_bindings=(
                binding,
            ),
        )
    )

    payment = view.service(
        "payment"
    )

    assert payment is not None

    assert payment.metric_count == 1
    assert payment.span_count == 1
    assert payment.log_count == 1

    assert (
        payment.metrics[0].evidence
        is metric
    )

    assert (
        payment.metrics[0].role
        == MetricServiceRole.PRIMARY
    )

    assert (
        payment.modalities_with_evidence
        == (
            EvidenceModality.METRIC,
            EvidenceModality.TRACE,
            EvidenceModality.LOG,
        )
    )


def test_global_log_acquisition_is_preserved():
    trace = FakeTrace(
        trace_id="trace-1",

        spans=(
            FakeSpan(
                span_id="payment-span",

                service_name="payment",
            ),
        ),
    )

    frontend_log = make_log(
        document_id="log-1",

        service_name="frontend",

        trace_id="trace-1",

        span_id=None,
    )

    start, end = make_window()

    bundle = (
        IncidentEvidenceBundle(
            incident_id="incident",

            start=start,
            end=end,

            traces=(
                trace,
            ),

            logs=(
                frontend_log,
            ),

            acquisitions=(
                ModalityAcquisition(
                    modality=(
                        EvidenceModality
                        .TRACE
                    ),

                    state=(
                        AcquisitionState
                        .OBSERVED
                    ),

                    source_system=(
                        "jaeger"
                    ),

                    evidence_count=1,
                ),

                ModalityAcquisition(
                    modality=(
                        EvidenceModality
                        .LOG
                    ),

                    state=(
                        AcquisitionState
                        .OBSERVED
                    ),

                    source_system=(
                        "opensearch"
                    ),

                    evidence_count=1,
                ),
            ),
        )
    )

    view = (
        build_incident_evidence_view(
            bundle
        )
    )

    payment = view.service(
        "payment"
    )

    assert payment is not None

    assert payment.log_count == 0

    assert (
        payment.log_acquisition
        is not None
    )

    assert (
        payment.log_acquisition.state
        == AcquisitionState.OBSERVED
    )


def test_unavailable_is_not_converted_to_empty():
    trace = FakeTrace(
        trace_id="trace-1",

        spans=(
            FakeSpan(
                span_id="payment-span",

                service_name="payment",
            ),
        ),
    )

    start, end = make_window()

    bundle = (
        IncidentEvidenceBundle(
            incident_id="incident",

            start=start,
            end=end,

            traces=(
                trace,
            ),

            acquisitions=(
                ModalityAcquisition(
                    modality=(
                        EvidenceModality
                        .TRACE
                    ),

                    state=(
                        AcquisitionState
                        .OBSERVED
                    ),

                    source_system="jaeger",

                    evidence_count=1,
                ),

                ModalityAcquisition(
                    modality=(
                        EvidenceModality
                        .LOG
                    ),

                    state=(
                        AcquisitionState
                        .UNAVAILABLE
                    ),

                    source_system=(
                        "opensearch"
                    ),

                    evidence_count=0,

                    detail=(
                        "OpenSearch unavailable"
                    ),
                ),
            ),
        )
    )

    view = (
        build_incident_evidence_view(
            bundle
        )
    )

    payment = view.service(
        "payment"
    )

    assert payment is not None

    assert payment.log_count == 0

    assert (
        payment.log_acquisition
        is not None
    )

    assert (
        payment.log_acquisition.state
        == AcquisitionState.UNAVAILABLE
    )


def test_service_integrity_is_explicit():
    trace = FakeTrace(
        trace_id="trace-1",

        spans=(
            FakeSpan(
                span_id="span-1",

                service_name="checkout",
            ),
        ),
    )

    matching = make_log(
        document_id="1",

        service_name="checkout",

        trace_id="trace-1",

        span_id="span-1",
    )

    unknown_span = make_log(
        document_id="2",

        service_name="checkout",

        trace_id="trace-1",

        span_id="unknown",
    )

    unknown_trace = make_log(
        document_id="3",

        service_name="checkout",

        trace_id="trace-2",

        span_id="span-2",
    )

    missing_context = make_log(
        document_id="4",

        service_name="checkout",

        trace_id=None,

        span_id=None,
    )

    start, end = make_window()

    bundle = (
        IncidentEvidenceBundle(
            incident_id="incident",

            start=start,
            end=end,

            traces=(
                trace,
            ),

            logs=(
                matching,
                unknown_span,
                unknown_trace,
                missing_context,
            ),
        )
    )

    view = (
        build_incident_evidence_view(
            bundle
        )
    )

    checkout = view.service(
        "checkout"
    )

    assert checkout is not None

    integrity = (
        checkout.integrity
    )

    assert integrity.log_count == 4

    assert (
        integrity
        .logs_without_trace_id
        == 1
    )

    assert (
        integrity
        .logs_without_span_id
        == 1
    )

    assert (
        integrity
        .logs_with_unmatched_trace
        == 1
    )

    assert (
        integrity
        .logs_with_unmatched_span
        == 2
    )


def test_services_are_deterministically_sorted():
    start, end = make_window()

    logs = (
        make_log(
            document_id="1",

            service_name="shipping",

            trace_id=None,

            span_id=None,
        ),

        make_log(
            document_id="2",

            service_name="checkout",

            trace_id=None,

            span_id=None,
        ),

        make_log(
            document_id="3",

            service_name="payment",

            trace_id=None,

            span_id=None,
        ),
    )

    bundle = (
        IncidentEvidenceBundle(
            incident_id="incident",

            start=start,
            end=end,

            logs=logs,
        )
    )

    view = (
        build_incident_evidence_view(
            bundle
        )
    )

    assert tuple(
        service.service_name
        for service
        in view.services
    ) == (
        "checkout",
        "payment",
        "shipping",
    )

from dataclasses import dataclass
from datetime import datetime, timezone

from rootlens.observability.incident_view import (
    build_incident_evidence_view,
)
from rootlens.observability.log_evidence import (
    LogEvidence,
)
from rootlens.observability.unified_evidence import (
    IncidentEvidenceBundle,
)


@dataclass(frozen=True)
class IntegrityFakeSpan:
    trace_id: str
    span_id: str
    service_name: str


@dataclass(frozen=True)
class IntegrityFakeTrace:
    trace_id: str
    spans: tuple[
        IntegrityFakeSpan,
        ...
    ]


def _integrity_log(
    *,
    trace_id: str | None,
    span_id: str | None,
) -> LogEvidence:
    timestamp = datetime(
        2026,
        10,
        3,
        16,
        0,
        tzinfo=timezone.utc,
    )

    return LogEvidence(
        event_timestamp=timestamp,
        event_timestamp_raw=(
            timestamp.isoformat()
        ),
        observed_timestamp=timestamp,
        observed_timestamp_raw=(
            timestamp.isoformat()
        ),
        service_name="payment",
        severity_text="INFO",
        severity_number=9,
        body="synthetic integrity test",
        trace_id=trace_id,
        span_id=span_id,
        attributes={},
        resource_attributes={
            "service.name":
                "payment",
        },
        instrumentation_scope={},
        index="otel-logs-test",
        document_id=(
            "synthetic-document"
        ),
        raw_source={},
    )


def _integrity_bundle(
    log: LogEvidence,
) -> IncidentEvidenceBundle:
    start = datetime(
        2026,
        10,
        3,
        16,
        0,
        tzinfo=timezone.utc,
    )

    end = datetime(
        2026,
        10,
        3,
        16,
        5,
        tzinfo=timezone.utc,
    )

    trace_id = (
        "11111111111111111111111111111111"
    )

    span = IntegrityFakeSpan(
        trace_id=trace_id,
        span_id="2222222222222222",
        service_name="payment",
    )

    trace = IntegrityFakeTrace(
        trace_id=trace_id,
        spans=(
            span,
        ),
    )

    return IncidentEvidenceBundle(
        incident_id=(
            "integrity-test"
        ),
        start=start,
        end=end,
        traces=(
            trace,
        ),
        logs=(
            log,
        ),
    )


def _payment_service(
    bundle: IncidentEvidenceBundle,
):
    view = (
        build_incident_evidence_view(
            bundle
        )
    )

    services = {
        service.service_name:
            service
        for service
        in view.services
    }

    return (
        view,
        services[
            "payment"
        ],
    )


def test_log_without_trace_or_span_context():
    log = _integrity_log(
        trace_id=None,
        span_id=None,
    )

    view, payment = (
        _payment_service(
            _integrity_bundle(
                log
            )
        )
    )

    assert (
        payment.integrity.log_count
        == 1
    )

    assert (
        payment.integrity
        .logs_without_trace_id
        == 1
    )

    assert (
        payment.integrity
        .logs_without_span_id
        == 1
    )

    assert (
        payment.integrity
        .logs_with_unmatched_trace
        == 0
    )

    assert (
        payment.integrity
        .logs_with_unmatched_span
        == 0
    )

    assert (
        view.coverage
        .logs_without_trace_id
        == 1
    )

    assert (
        view.coverage
        .logs_without_span_id
        == 1
    )


def test_log_with_trace_but_without_span_context():
    trace_id = (
        "11111111111111111111111111111111"
    )

    log = _integrity_log(
        trace_id=trace_id,
        span_id=None,
    )

    view, payment = (
        _payment_service(
            _integrity_bundle(
                log
            )
        )
    )

    assert (
        payment.integrity
        .logs_without_trace_id
        == 0
    )

    assert (
        payment.integrity
        .logs_without_span_id
        == 1
    )

    assert (
        payment.integrity
        .logs_with_unmatched_trace
        == 0
    )

    assert (
        payment.integrity
        .logs_with_unmatched_span
        == 0
    )

    assert (
        view.coverage
        .logs_with_matching_trace
        == 1
    )

    assert (
        view.coverage
        .logs_without_span_id
        == 1
    )


def test_log_with_present_but_unmatched_span_context():
    trace_id = (
        "11111111111111111111111111111111"
    )

    log = _integrity_log(
        trace_id=trace_id,
        span_id="ffffffffffffffff",
    )

    view, payment = (
        _payment_service(
            _integrity_bundle(
                log
            )
        )
    )

    assert (
        payment.integrity
        .logs_without_trace_id
        == 0
    )

    assert (
        payment.integrity
        .logs_without_span_id
        == 0
    )

    assert (
        payment.integrity
        .logs_with_unmatched_trace
        == 0
    )

    assert (
        payment.integrity
        .logs_with_unmatched_span
        == 1
    )

    assert (
        view.coverage
        .logs_with_span_id
        == 1
    )

    assert (
        view.coverage
        .logs_with_matching_span
        == 0
    )

    assert (
        view.coverage
        .logs_without_matching_span
        == 1
    )
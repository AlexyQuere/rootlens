from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)

from rootlens.observability.cross_modal import (
    CrossModalIndex,
)
from rootlens.observability.log_evidence import (
    LogEvidence,
)
from rootlens.observability.unified_evidence import (
    IncidentEvidenceBundle,
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


def make_log(
    *,
    document_id: str,
    trace_id: str | None,
    span_id: str | None,
    service_name: str | None,
    body: str,
) -> LogEvidence:
    timestamp = datetime(
        2026,
        10,
        3,
        13,
        0,
        tzinfo=timezone.utc,
    )

    return LogEvidence(
        event_timestamp=(
            timestamp
        ),

        event_timestamp_raw=(
            "2026-10-03T13:00:00Z"
        ),

        observed_timestamp=(
            timestamp
        ),

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

        index="index",

        document_id=(
            document_id
        ),

        raw_source={},
    )


def make_bundle(
    *,
    traces=(),
    logs=(),
):
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
        13,
        5,
        tzinfo=timezone.utc,
    )

    return IncidentEvidenceBundle(
        incident_id="incident",

        start=start,
        end=end,

        traces=tuple(
            traces
        ),

        logs=tuple(
            logs
        ),
    )


def test_trace_correlation():
    trace = FakeTrace(
        trace_id="trace-1",

        spans=(
            FakeSpan(
                span_id="span-1",
                service_name="checkout",
            ),
        ),
    )

    log = make_log(
        document_id="1",

        trace_id="trace-1",
        span_id="span-1",

        service_name="checkout",

        body="[PlaceOrder]",
    )

    bundle = make_bundle(
        traces=(
            trace,
        ),
        logs=(
            log,
        ),
    )

    index = CrossModalIndex(
        bundle
    )

    correlation = (
        index.trace_correlation(
            "trace-1"
        )
    )

    assert correlation is not None

    assert (
        correlation.trace
        is trace
    )

    assert (
        correlation.logs
        == (log,)
    )

    assert (
        correlation
        .logs_with_matching_span
        == (log,)
    )

    assert (
        correlation
        .logs_without_matching_span
        == ()
    )

    assert (
        correlation.service_names
        == ("checkout",)
    )


def test_span_identity_uses_trace_and_span():
    trace_1 = FakeTrace(
        trace_id="trace-1",

        spans=(
            FakeSpan(
                span_id="same-span",
                service_name="checkout",
            ),
        ),
    )

    trace_2 = FakeTrace(
        trace_id="trace-2",

        spans=(
            FakeSpan(
                span_id="same-span",
                service_name="payment",
            ),
        ),
    )

    log_1 = make_log(
        document_id="1",

        trace_id="trace-1",
        span_id="same-span",

        service_name="checkout",

        body="checkout log",
    )

    log_2 = make_log(
        document_id="2",

        trace_id="trace-2",
        span_id="same-span",

        service_name="payment",

        body="payment log",
    )

    index = CrossModalIndex(
        make_bundle(
            traces=(
                trace_1,
                trace_2,
            ),

            logs=(
                log_1,
                log_2,
            ),
        )
    )

    first = (
        index.span_correlation(
            "trace-1",
            "same-span",
        )
    )

    second = (
        index.span_correlation(
            "trace-2",
            "same-span",
        )
    )

    assert first is not None
    assert second is not None

    assert first.logs == (
        log_1,
    )

    assert second.logs == (
        log_2,
    )


def test_log_without_matching_span_is_preserved():
    trace = FakeTrace(
        trace_id="trace-1",

        spans=(
            FakeSpan(
                span_id="known",
                service_name="checkout",
            ),
        ),
    )

    log = make_log(
        document_id="1",

        trace_id="trace-1",
        span_id="unknown",

        service_name="checkout",

        body="message",
    )

    index = CrossModalIndex(
        make_bundle(
            traces=(
                trace,
            ),

            logs=(
                log,
            ),
        )
    )

    correlation = (
        index.trace_correlation(
            "trace-1"
        )
    )

    assert correlation is not None

    assert (
        correlation
        .logs_without_matching_span
        == (log,)
    )

    assert (
        index
        .logs_without_matching_span()
        == (log,)
    )


def test_log_without_matching_trace_is_preserved():
    log = make_log(
        document_id="1",

        trace_id="missing-trace",
        span_id="span-1",

        service_name="frontend",

        body="message",
    )

    index = CrossModalIndex(
        make_bundle(
            logs=(
                log,
            )
        )
    )

    assert (
        index
        .logs_without_matching_trace()
        == (log,)
    )

    correlation = (
        index.trace_correlation(
            "missing-trace"
        )
    )

    assert correlation is not None

    assert (
        correlation.trace
        is None
    )

    assert (
        correlation.logs
        == (log,)
    )


def test_service_correlation_combines_trace_and_logs():
    trace = FakeTrace(
        trace_id="trace-1",

        spans=(
            FakeSpan(
                span_id="span-1",
                service_name="payment",
            ),

            FakeSpan(
                span_id="span-2",
                service_name="checkout",
            ),
        ),
    )

    payment_log = make_log(
        document_id="1",

        trace_id="trace-1",
        span_id="span-1",

        service_name="payment",

        body="Transaction complete",
    )

    index = CrossModalIndex(
        make_bundle(
            traces=(
                trace,
            ),

            logs=(
                payment_log,
            ),
        )
    )

    correlation = (
        index.service_correlation(
            "payment"
        )
    )

    assert correlation is not None

    assert (
        correlation.trace_ids
        == ("trace-1",)
    )

    assert (
        correlation.span_count
        == 1
    )

    assert (
        correlation.log_count
        == 1
    )


def test_coverage_distinguishes_missing_context():
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

        trace_id="trace-1",
        span_id="span-1",

        service_name="checkout",

        body="matching",
    )

    unknown_span = make_log(
        document_id="2",

        trace_id="trace-1",
        span_id="unknown",

        service_name="checkout",

        body="unknown span",
    )

    unknown_trace = make_log(
        document_id="3",

        trace_id="trace-2",
        span_id="span-2",

        service_name="frontend",

        body="unknown trace",
    )

    no_context = make_log(
        document_id="4",

        trace_id=None,
        span_id=None,

        service_name="checkout",

        body="no context",
    )

    index = CrossModalIndex(
        make_bundle(
            traces=(
                trace,
            ),

            logs=(
                matching,
                unknown_span,
                unknown_trace,
                no_context,
            ),
        )
    )

    coverage = (
        index.coverage()
    )

    assert (
        coverage.trace_count
        == 1
    )

    assert (
        coverage.span_count
        == 1
    )

    assert (
        coverage.log_count
        == 4
    )

    assert (
        coverage.logs_with_trace_id
        == 3
    )

    assert (
        coverage.logs_without_trace_id
        == 1
    )

    assert (
        coverage.logs_with_matching_trace
        == 2
    )

    assert (
        coverage.logs_without_matching_trace
        == 1
    )

    assert (
        coverage.logs_with_matching_span
        == 1
    )

    assert (
        coverage.logs_without_matching_span
        == 2
    )
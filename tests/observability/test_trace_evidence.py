from __future__ import annotations

import pytest

from rootlens.observability.trace_evidence import (
    SpanEvidence,
    SpanKind,
    SpanStatusCode,
    TraceEvidence,
)


TRACE_ID = (
    "0123456789abcdef"
    "0123456789abcdef"
)


def span(
    *,
    span_id: str,
    parent_span_id: str | None,
    service: str,
    start: int,
    end: int,
) -> SpanEvidence:

    return SpanEvidence(
        trace_id=TRACE_ID,
        span_id=span_id,
        parent_span_id=parent_span_id,
        service_name=service,
        operation_name="operation",
        kind=SpanKind.INTERNAL,
        start_time_unix_nano=start,
        end_time_unix_nano=end,
        status_code=(
            SpanStatusCode.UNSET
        ),
        status_message=None,
        attributes={},
        resource_attributes={},
    )


def test_envelope_duration():

    root = span(
        span_id="0000000000000001",
        parent_span_id=None,
        service="frontend",
        start=1_000_000_000,
        end=2_000_000_000,
    )

    child = span(
        span_id="0000000000000002",
        parent_span_id=(
            "0000000000000001"
        ),
        service="checkout",
        start=1_200_000_000,
        end=1_800_000_000,
    )

    trace = TraceEvidence(
        trace_id=TRACE_ID,
        spans=(root, child),
    )

    assert (
        trace.envelope_duration_ms
        == pytest.approx(
            1000.0
        )
    )


def test_no_temporal_violation():

    root = span(
        span_id="0000000000000001",
        parent_span_id=None,
        service="frontend",
        start=1_000,
        end=10_000,
    )

    child = span(
        span_id="0000000000000002",
        parent_span_id=(
            "0000000000000001"
        ),
        service="checkout",
        start=2_000,
        end=9_000,
    )

    trace = TraceEvidence(
        trace_id=TRACE_ID,
        spans=(root, child),
    )

    assert (
        trace.temporal_violations
        == ()
    )

    assert (
        trace.integrity
        .max_temporal_skew_ms
        == 0.0
    )


def test_child_starts_before_parent():

    root = span(
        span_id="0000000000000001",
        parent_span_id=None,
        service="shipping",
        start=10_000_000,
        end=20_000_000,
    )

    child = span(
        span_id="0000000000000002",
        parent_span_id=(
            "0000000000000001"
        ),
        service="quote",
        start=5_000_000,
        end=15_000_000,
    )

    trace = TraceEvidence(
        trace_id=TRACE_ID,
        spans=(root, child),
    )

    violation = (
        trace.temporal_violations[0]
    )

    assert (
        violation.starts_before_parent_ms
        == pytest.approx(
            5.0
        )
    )

    assert (
        violation.ends_after_parent_ms
        == 0.0
    )


def test_child_ends_after_parent():

    root = span(
        span_id="0000000000000001",
        parent_span_id=None,
        service="frontend",
        start=1_000_000,
        end=5_000_000,
    )

    child = span(
        span_id="0000000000000002",
        parent_span_id=(
            "0000000000000001"
        ),
        service="checkout",
        start=2_000_000,
        end=7_000_000,
    )

    trace = TraceEvidence(
        trace_id=TRACE_ID,
        spans=(root, child),
    )

    violation = (
        trace.temporal_violations[0]
    )

    assert (
        violation.starts_before_parent_ms
        == 0.0
    )

    assert (
        violation.ends_after_parent_ms
        == pytest.approx(
            2.0
        )
    )


def test_orphan_is_not_root():

    orphan = span(
        span_id="0000000000000002",
        parent_span_id=(
            "ffffffffffffffff"
        ),
        service="checkout",
        start=1_000,
        end=2_000,
    )

    trace = TraceEvidence(
        trace_id=TRACE_ID,
        spans=(orphan,),
    )

    assert trace.root_spans == ()

    assert (
        trace.orphan_spans
        == (orphan,)
    )

    assert (
        trace.integrity.root_count
        == 0
    )

    assert (
        trace.integrity.orphan_count
        == 1
    )


def test_integrity_reports_largest_skew():

    root = span(
        span_id="0000000000000001",
        parent_span_id=None,
        service="shipping",
        start=100_000_000,
        end=200_000_000,
    )

    small = span(
        span_id="0000000000000002",
        parent_span_id=(
            "0000000000000001"
        ),
        service="frontend",
        start=99_000_000,
        end=150_000_000,
    )

    huge = span(
        span_id="0000000000000003",
        parent_span_id=(
            "0000000000000001"
        ),
        service="quote",
        start=1_000_000,
        end=2_000_000,
    )

    trace = TraceEvidence(
        trace_id=TRACE_ID,
        spans=(
            root,
            small,
            huge,
        ),
    )

    integrity = trace.integrity

    assert (
        integrity.temporal_violation_count
        == 2
    )

    assert (
        integrity.max_temporal_skew_ms
        == pytest.approx(
            99.0
        )
    )

    assert (
        integrity.temporal_violations[
            0
        ].child_service
        == "quote"
    )
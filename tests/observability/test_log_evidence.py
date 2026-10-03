from datetime import (
    datetime,
    timezone,
)

from rootlens.observability.log_evidence import (
    LogEvidence,
)


def test_log_evidence_properties():
    event_timestamp = datetime(
        2026,
        10,
        3,
        13,
        29,
        tzinfo=timezone.utc,
    )

    log = LogEvidence(
        event_timestamp=event_timestamp,

        event_timestamp_raw=(
            "2026-10-03T13:29:00Z"
        ),

        observed_timestamp=(
            event_timestamp
        ),

        observed_timestamp_raw=(
            "2026-10-03T13:29:00Z"
        ),

        service_name="frontend",

        severity_text="ERROR",

        severity_number=17,

        body=(
            "Checkout failed"
        ),

        trace_id=(
            "0123456789abcdef"
            "0123456789abcdef"
        ),

        span_id=(
            "0123456789abcdef"
        ),

        attributes={
            "key": "value",
        },

        resource_attributes={
            "service.name":
                "frontend",
        },

        instrumentation_scope={},

        index=(
            "otel-logs-2026-10-03"
        ),

        document_id="abc",

        raw_source={},
    )

    assert log.trace_id_valid
    assert log.span_id_valid

    assert (
        log.severity_casefold
        == "error"
    )

    assert (
        log.body_text
        == "Checkout failed"
    )

    assert (
        log.observed_minus_event_ms
        == 0.0
    )


def test_missing_trace_context_is_valid():
    event_timestamp = datetime(
        2026,
        10,
        3,
        tzinfo=timezone.utc,
    )

    log = LogEvidence(
        event_timestamp=(
            event_timestamp
        ),

        event_timestamp_raw=(
            "2026-10-03T00:00:00Z"
        ),

        observed_timestamp=None,

        observed_timestamp_raw=None,

        service_name="checkout",

        severity_text=None,

        severity_number=None,

        body="message",

        trace_id=None,
        span_id=None,

        attributes={},
        resource_attributes={},
        instrumentation_scope={},

        index="index",
        document_id="id",

        raw_source={},
    )

    assert not log.trace_id_valid
    assert not log.span_id_valid

    assert (
        log.observed_minus_event_ms
        is None
    )


def test_frozen_nested_attributes():
    event_timestamp = datetime(
        2026,
        10,
        3,
        tzinfo=timezone.utc,
    )

    original = {
        "nested": {
            "values": [
                1,
                2,
            ]
        }
    }

    log = LogEvidence(
        event_timestamp=(
            event_timestamp
        ),

        event_timestamp_raw=(
            "2026-10-03T00:00:00Z"
        ),

        observed_timestamp=None,

        observed_timestamp_raw=None,

        service_name=None,

        severity_text=None,
        severity_number=None,

        body=None,

        trace_id=None,
        span_id=None,

        attributes=original,

        resource_attributes={},
        instrumentation_scope={},

        index="index",
        document_id="id",

        raw_source={},
    )

    assert (
        log.attributes[
            "nested"
        ][
            "values"
        ]
        == (1, 2)
    )


def test_preserves_epoch_event_timestamp():
    event_time = datetime(
        1970,
        1,
        1,
        tzinfo=timezone.utc,
    )

    observed_time = datetime(
        2026,
        10,
        3,
        13,
        29,
        25,
        tzinfo=timezone.utc,
    )

    log = LogEvidence(
        event_timestamp=(
            event_time
        ),

        event_timestamp_raw=(
            "1970-01-01T00:00:00Z"
        ),

        observed_timestamp=(
            observed_time
        ),

        observed_timestamp_raw=(
            "2026-10-03T13:29:25Z"
        ),

        service_name="shipping",

        severity_text="INFO",
        severity_number=None,

        body="Requesting quote",

        trace_id=None,
        span_id=None,

        attributes={},
        resource_attributes={},
        instrumentation_scope={},

        index="index",
        document_id="id",

        raw_source={},
    )

    assert (
        log.event_timestamp
        == event_time
    )

    assert (
        log.observed_timestamp
        == observed_time
    )

    assert (
        log.observed_minus_event_ms
        is not None
    )

    assert (
        log.observed_minus_event_ms
        > 1_000_000_000
    )


def test_log_can_have_only_observed_timestamp():
    observed_time = datetime(
        2026,
        10,
        3,
        13,
        29,
        25,
        tzinfo=timezone.utc,
    )

    log = LogEvidence(
        event_timestamp=None,
        event_timestamp_raw=None,

        observed_timestamp=(
            observed_time
        ),

        observed_timestamp_raw=(
            "2026-10-03T13:29:25Z"
        ),

        service_name="frontend-proxy",

        severity_text=None,
        severity_number=None,

        body="access log",

        trace_id=None,
        span_id=None,

        attributes={},
        resource_attributes={},
        instrumentation_scope={},

        index="index",
        document_id="id",

        raw_source={},
    )

    assert log.event_timestamp is None

    assert (
        log.observed_timestamp
        == observed_time
    )

    assert (
        log.observed_minus_event_ms
        is None
    )
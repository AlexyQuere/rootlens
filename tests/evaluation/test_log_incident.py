from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

from rootlens.evaluation.log_incident import (
    compare_log_windows,
    observe_trace_logs,
)

from rootlens.observability.log_evidence import (
    LogEvidence,
)


def make_log(
    *,
    trace_id: str,
    document_id: str,
    service_name: str,
    body: str,
    severity_text:
        str | None = "INFO",
) -> LogEvidence:
    event_time = datetime(
        2026,
        10,
        3,
        13,
        0,
        tzinfo=timezone.utc,
    )

    observed_time = datetime(
        2026,
        10,
        3,
        13,
        0,
        1,
        tzinfo=timezone.utc,
    )

    return LogEvidence(
        event_timestamp=(
            event_time
        ),

        event_timestamp_raw=(
            event_time.isoformat()
        ),

        observed_timestamp=(
            observed_time
        ),

        observed_timestamp_raw=(
            observed_time
            .isoformat()
        ),

        service_name=(
            service_name
        ),

        severity_text=(
            severity_text
        ),

        severity_number=None,

        body=body,

        trace_id=trace_id,

        span_id=(
            "0123456789abcdef"
        ),

        attributes={},

        resource_attributes={
            "service.name":
                service_name,
        },

        instrumentation_scope={},

        index="index",

        document_id=(
            document_id
        ),

        raw_source={},
    )


def test_observe_trace_logs():
    trace_id = (
        "0123456789abcdef"
        "0123456789abcdef"
    )

    logs = (
        make_log(
            trace_id=trace_id,
            document_id="1",
            service_name="checkout",
            body="[PlaceOrder]",
        ),

        make_log(
            trace_id=trace_id,
            document_id="2",
            service_name="frontend",
            body="Checkout failed",
            severity_text="error",
        ),
    )

    observation = (
        observe_trace_logs(
            trace_id,
            logs,
        )
    )

    assert (
        observation.log_count
        == 2
    )

    assert (
        observation
        .unique_signature_count
        == 2
    )


def test_duplicate_logs_count_once_for_prevalence():
    signature_trace = (
        "aaaaaaaaaaaaaaaa"
        "aaaaaaaaaaaaaaaa"
    )

    baseline_trace_2 = (
        "bbbbbbbbbbbbbbbb"
        "bbbbbbbbbbbbbbbb"
    )

    incident_trace = (
        "cccccccccccccccc"
        "cccccccccccccccc"
    )

    baseline = (
        observe_trace_logs(
            signature_trace,
            (
                make_log(
                    trace_id=signature_trace,
                    document_id="1",
                    service_name="checkout",
                    body="same",
                ),
            ),
        ),

        observe_trace_logs(
            baseline_trace_2,
            (
                make_log(
                    trace_id=baseline_trace_2,
                    document_id="2",
                    service_name="checkout",
                    body="same",
                ),
            ),
        ),
    )

    incident = (
        observe_trace_logs(
            incident_trace,
            (
                make_log(
                    trace_id=incident_trace,
                    document_id="3",
                    service_name="checkout",
                    body="same",
                ),

                make_log(
                    trace_id=incident_trace,
                    document_id="4",
                    service_name="checkout",
                    body="same",
                ),

                make_log(
                    trace_id=incident_trace,
                    document_id="5",
                    service_name="checkout",
                    body="same",
                ),
            ),
        ),
    )

    comparison = (
        compare_log_windows(
            baseline,
            incident,
        )
    )

    assert (
        comparison.differences
        == ()
    )


def test_incident_only_signature_has_delta_one():
    baseline_trace = (
        "aaaaaaaaaaaaaaaa"
        "aaaaaaaaaaaaaaaa"
    )

    incident_trace = (
        "bbbbbbbbbbbbbbbb"
        "bbbbbbbbbbbbbbbb"
    )

    baseline = (
        observe_trace_logs(
            baseline_trace,
            (
                make_log(
                    trace_id=(
                        baseline_trace
                    ),
                    document_id="1",
                    service_name="checkout",
                    body="healthy",
                ),
            ),
        ),
    )

    incident = (
        observe_trace_logs(
            incident_trace,
            (
                make_log(
                    trace_id=(
                        incident_trace
                    ),
                    document_id="2",
                    service_name="frontend",
                    body="Checkout failed",
                    severity_text="error",
                ),
            ),
        ),
    )

    comparison = (
        compare_log_windows(
            baseline,
            incident,
        )
    )

    incident_only = [
        difference
        for difference
        in comparison.differences
        if (
            difference.signature
            .body_key
            == repr(
                "Checkout failed"
            )
        )
    ]

    assert len(
        incident_only
    ) == 1

    assert (
        incident_only[0]
        .baseline_prevalence
        == 0.0
    )

    assert (
        incident_only[0]
        .incident_prevalence
        == 1.0
    )

    assert (
        incident_only[0]
        .delta
        == 1.0
    )
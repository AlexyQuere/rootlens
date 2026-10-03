from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from rootlens.observability.log_evidence import (
    LogEvidence,
)

from rootlens.observability.log_investigation import (
    LogInvestigationTool,
)


TRACE_ID = (
    "0123456789abcdef"
    "0123456789abcdef"
)


def make_log(
    *,
    document_id: str,
    service_name: str,
    body: str,
    severity_text: str | None = "INFO",
    trace_id: str | None = TRACE_ID,
    span_id: str | None = (
        "0123456789abcdef"
    ),
    event_offset_seconds:
        float = 0.0,
    observed_offset_seconds:
        float = 1.0,
) -> LogEvidence:

    base = datetime(
        2026,
        10,
        3,
        13,
        0,
        tzinfo=timezone.utc,
    )

    event_timestamp = (
        base
        + timedelta(
            seconds=(
                event_offset_seconds
            )
        )
    )

    observed_timestamp = (
        base
        + timedelta(
            seconds=(
                observed_offset_seconds
            )
        )
    )

    return LogEvidence(
        event_timestamp=(
            event_timestamp
        ),

        event_timestamp_raw=(
            event_timestamp
            .isoformat()
        ),

        observed_timestamp=(
            observed_timestamp
        ),

        observed_timestamp_raw=(
            observed_timestamp
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
        span_id=span_id,

        attributes={},

        resource_attributes={
            "service.name":
                service_name,
        },

        instrumentation_scope={},

        index=(
            "otel-logs-2026-10-03"
        ),

        document_id=(
            document_id
        ),

        raw_source={},
    )


def test_summary():

    tool = (
        LogInvestigationTool()
    )

    logs = (
        make_log(
            document_id="1",
            service_name="checkout",
            body="one",
        ),
        make_log(
            document_id="2",
            service_name="checkout",
            body="two",
        ),
        make_log(
            document_id="3",
            service_name="frontend",
            body="three",
            severity_text="error",
            trace_id=None,
            span_id=None,
        ),
    )

    summary = tool.summarize(
        logs
    )

    assert summary.log_count == 3

    assert summary.service_counts == (
        ("checkout", 2),
        ("frontend", 1),
    )

    assert summary.logs_with_trace_id == 2
    assert summary.logs_without_trace_id == 1


def test_find_logs_uses_exact_filters():

    tool = (
        LogInvestigationTool()
    )

    logs = (
        make_log(
            document_id="1",
            service_name="frontend",
            body="error",
            severity_text="error",
        ),
        make_log(
            document_id="2",
            service_name="frontend",
            body="info",
            severity_text="INFO",
        ),
    )

    found = tool.find_logs(
        logs,
        severity_text="error",
    )

    assert len(found) == 1

    assert (
        found[0].document_id
        == "1"
    )


def test_possible_duplicates_are_reported_not_removed():

    tool = (
        LogInvestigationTool()
    )

    first = make_log(
        document_id="1",
        service_name=(
            "load-generator"
        ),
        body="same message",
        event_offset_seconds=0,
        observed_offset_seconds=1,
    )

    second = make_log(
        document_id="2",
        service_name=(
            "load-generator"
        ),
        body="same message",
        event_offset_seconds=0,
        observed_offset_seconds=2,
    )

    unique = make_log(
        document_id="3",
        service_name="checkout",
        body="unique",
    )

    groups = (
        tool
        .find_possible_duplicates(
            (
                first,
                second,
                unique,
            )
        )
    )

    assert len(groups) == 1
    assert groups[0].count == 2

    assert {
        log.document_id
        for log
        in groups[0].logs
    } == {
        "1",
        "2",
    }


def test_largest_timestamp_differences():

    tool = (
        LogInvestigationTool()
    )

    normal = make_log(
        document_id="normal",
        service_name="checkout",
        body="normal",
        event_offset_seconds=0,
        observed_offset_seconds=1,
    )

    epoch = LogEvidence(
        event_timestamp=(
            datetime(
                1970,
                1,
                1,
                tzinfo=timezone.utc,
            )
        ),

        event_timestamp_raw=(
            "1970-01-01T00:00:00Z"
        ),

        observed_timestamp=(
            datetime(
                2026,
                10,
                3,
                13,
                0,
                tzinfo=timezone.utc,
            )
        ),

        observed_timestamp_raw=(
            "2026-10-03T13:00:00Z"
        ),

        service_name="shipping",

        severity_text="INFO",

        severity_number=None,

        body="Requesting quote",

        trace_id=TRACE_ID,

        span_id=(
            "fedcba9876543210"
        ),

        attributes={},

        resource_attributes={},

        instrumentation_scope={},

        index="index",

        document_id="epoch",

        raw_source={},
    )

    results = (
        tool
        .largest_timestamp_differences(
            (
                normal,
                epoch,
            ),
            limit=1,
        )
    )

    assert len(results) == 1

    assert (
        results[0]
        .document_id
        == "epoch"
    )

    assert (
        results[0]
        .service_name
        == "shipping"
    )


def test_order_logs_can_use_observed_time():

    tool = (
        LogInvestigationTool()
    )

    first_observed = make_log(
        document_id="first",
        service_name="checkout",
        body="first",
        event_offset_seconds=10,
        observed_offset_seconds=1,
    )

    second_observed = make_log(
        document_id="second",
        service_name="checkout",
        body="second",
        event_offset_seconds=0,
        observed_offset_seconds=2,
    )

    ordered = tool.order_logs(
        (
            second_observed,
            first_observed,
        ),
        by="observed",
    )

    assert (
        ordered[0].document_id
        == "first"
    )

    assert (
        ordered[1].document_id
        == "second"
    )


def test_compare_exact_events():

    tool = (
        LogInvestigationTool()
    )

    baseline = (
        make_log(
            document_id="1",
            service_name="checkout",
            body="payment went through",
        ),
    )

    incident = (
        make_log(
            document_id="2",
            service_name="frontend",
            body=(
                "Checkout failed "
                "to place order"
            ),
            severity_text="error",
        ),
    )

    comparison = (
        tool.compare_exact_events(
            baseline,
            incident,
        )
    )

    assert not comparison.identical

    assert len(
        comparison.differences
    ) == 2

    deltas = {
        (
            difference
            .signature
            .service_name,
            difference.delta,
        )
        for difference
        in comparison.differences
    }

    assert (
        "checkout",
        -1,
    ) in deltas

    assert (
        "frontend",
        1,
    ) in deltas
from __future__ import annotations

import argparse

from collections import (
    Counter,
)

from rootlens.evaluation.cross_modal_content import (
    exact_log_body_prevalence,
    metric_changes,
    trace_payment_observations,
)
from rootlens.evaluation.runtime_feature_flag import (
    extract_feature_flag_observations,
    runtime_state_matches,
)
from rootlens.evaluation.synced_cross_modal import (
    load_synced_incident_evidence,
)
from rootlens.observability.trace_investigation import (
    TraceInvestigationTool,
)


FLAG_KEY = (
    "paymentUnreachable"
)

PAYMENT_OPERATION = (
    "oteldemo.PaymentService/Charge"
)

EXPECTED_RESOLVER_TEXT = (
    "name resolver error: "
    "produced zero addresses"
)


def span_status_message(
    span,
) -> str | None:
    for attribute_name in (
        "status_message",
        "status_description",
        "status_text",
        "message",
    ):
        value = getattr(
            span,
            attribute_name,
            None,
        )

        if value is not None:
            return str(
                value
            )

    return None


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "artifact",
    )

    args = parser.parse_args()

    loaded = (
        load_synced_incident_evidence(
            args.artifact
        )
    )

    if (
        loaded.scenario
        != "paymentUnreachable"
    ):
        raise ValueError(
            "This evaluation is "
            "specific to "
            "paymentUnreachable."
        )

    bundle = loaded.bundle

    trace_ids = tuple(
        trace.trace_id
        for trace
        in bundle.traces
    )

    print(
        "=" * 90
    )
    print(
        "ROOTLENS 015D — "
        "PAYMENT UNREACHABLE "
        "CONTENT VALIDATION"
    )
    print(
        "=" * 90
    )

    print(
        f"incident traces: "
        f"{len(trace_ids)}"
    )

    print()

    #
    # 1. Metric evidence
    #

    print(
        "METRIC EVIDENCE"
    )

    changes = metric_changes(
        bundle=bundle,
        metric_bindings=(
            loaded.metric_bindings
        ),
        metric_keys=(
            "checkout_error_rate",
            (
                "checkout_payment_"
                "error_rate"
            ),
            "frontend_http_error_rate",
        ),
    )

    changes_by_key = {
        change.metric_key:
            change
        for change
        in changes
    }

    for change in changes:
        print(
            "  "
            f"{change.metric_key:<34} "
            f"{change.baseline:.6f}"
            " -> "
            f"{change.incident:.6f}"
            "  delta="
            f"{change.absolute_delta:+.6f}"
        )

    #
    # 2. Runtime manipulation evidence
    #

    flag_observations = (
        extract_feature_flag_observations(
            bundle.traces,
            flag_key=(
                FLAG_KEY
            ),
        )
    )

    flag_counter = Counter(
        (
            observation.value,
            observation.variant,
            observation.reason,
            observation.provider,
        )
        for observation
        in flag_observations
    )

    traces_with_flag = {
        observation.trace_id
        for observation
        in flag_observations
    }

    matching_flag_traces = {
        observation.trace_id
        for observation
        in flag_observations
        if runtime_state_matches(
            observation,
            expected_value=True,
            expected_variant="on",
        )
    }

    print()
    print(
        "RUNTIME FEATURE-FLAG EVIDENCE"
    )

    print(
        "  traces with "
        "paymentUnreachable event: "
        f"{len(traces_with_flag)}/"
        f"{len(trace_ids)}"
    )

    print(
        "  traces evaluating True/on:   "
        f"{len(matching_flag_traces)}/"
        f"{len(trace_ids)}"
    )

    for (
        value,
        variant,
        reason,
        provider,
    ), count in (
        flag_counter.most_common()
    ):
        print(
            "  "
            f"{count:>2} events | "
            f"value={value!r} | "
            f"variant={variant!r} | "
            f"reason={reason!r} | "
            f"provider={provider!r}"
        )

    #
    # 3. Request-level trace structure
    #

    observations = (
        trace_payment_observations(
            bundle
        )
    )

    client_observed = sum(
        observation
        .checkout_payment_client_observed
        for observation
        in observations
    )

    client_error = sum(
        observation
        .checkout_payment_client_error
        for observation
        in observations
    )

    server_observed = sum(
        observation
        .payment_server_observed
        for observation
        in observations
    )

    server_error = sum(
        observation
        .payment_server_error
        for observation
        in observations
    )

    print()
    print(
        "TRACE STRUCTURE"
    )

    print(
        "  Checkout -> Payment "
        "CLIENT observed: "
        f"{client_observed}/"
        f"{len(observations)}"
    )

    print(
        "  Checkout -> Payment "
        "CLIENT error:    "
        f"{client_error}/"
        f"{len(observations)}"
    )

    print(
        "  Payment SERVER observed: "
        f"{server_observed}/"
        f"{len(observations)}"
    )

    print(
        "  Payment SERVER error:    "
        f"{server_error}/"
        f"{len(observations)}"
    )

    #
    # 4. Exact client error messages
    #

    tool = (
        TraceInvestigationTool()
    )

    client_error_messages = []

    for trace in bundle.traces:
        for span in (
            tool.find_error_spans(
                trace
            )
        ):
            if (
                span.service_name
                != "checkout"
            ):
                continue

            if (
                span.operation_name
                != PAYMENT_OPERATION
            ):
                continue

            client_error_messages.append(
                span_status_message(
                    span
                )
            )

    message_counter = Counter(
        client_error_messages
    )

    resolver_message_count = sum(
        count
        for message, count
        in message_counter.items()
        if (
            message is not None
            and
            EXPECTED_RESOLVER_TEXT
            in message
        )
    )

    print()
    print(
        "CHECKOUT -> PAYMENT "
        "CLIENT ERROR MESSAGES"
    )

    for message, count in (
        message_counter.most_common()
    ):
        print(
            f"  {count:>2} | "
            f"{message!r}"
        )

    #
    # 5. Payment log evidence
    #

    payment_logs = tuple(
        log
        for log in bundle.logs
        if (
            log.service_name
            == "payment"
        )
    )

    print()
    print(
        "PAYMENT LOG EVIDENCE"
    )

    print(
        "  Payment logs observed: "
        f"{len(payment_logs)}"
    )

    if payment_logs:
        prevalence = (
            exact_log_body_prevalence(
                bundle.logs,
                service_name=(
                    "payment"
                ),
                trace_ids=(
                    trace_ids
                ),
            )
        )

        for row in (
            prevalence[:10]
        ):
            print(
                "  "
                f"{row.trace_count:>2}/"
                f"{row.total_trace_count:<2} "
                "traces | "
                f"{row.log_count:>3} logs | "
                f"{row.body}"
            )

    else:
        print(
            "  no Payment log observed "
            "for the captured incident "
            "traces"
        )

    #
    # 6. Frontend symptom evidence
    #

    frontend_prevalence = (
        exact_log_body_prevalence(
            bundle.logs,
            service_name=(
                "frontend"
            ),
            trace_ids=(
                trace_ids
            ),
        )
    )

    print()
    print(
        "FRONTEND LOG EVIDENCE"
    )

    for row in (
        frontend_prevalence[:10]
    ):
        print(
            "  "
            f"{row.trace_count:>2}/"
            f"{row.total_trace_count:<2} "
            "traces | "
            f"{row.log_count:>3} logs | "
            f"{row.body}"
        )

    #
    # 7. Controlled acceptance checks
    #

    checkout_change = (
        changes_by_key[
            "checkout_error_rate"
        ]
    )

    edge_change = (
        changes_by_key[
            "checkout_payment_error_rate"
        ]
    )

    checks = {
        (
            "checkout_error_rate "
            "changed 0 -> 1"
        ):
            (
                checkout_change.baseline
                == 0.0
                and
                checkout_change.incident
                == 1.0
            ),

        (
            "checkout_payment_error_rate "
            "changed 0 -> 1"
        ):
            (
                edge_change.baseline
                == 0.0
                and
                edge_change.incident
                == 1.0
            ),

        (
            "every measured trace "
            "contains the runtime "
            "feature-flag event"
        ):
            (
                len(
                    traces_with_flag
                )
                == len(
                    trace_ids
                )
                and
                len(
                    trace_ids
                ) > 0
            ),

        (
            "every measured trace "
            "evaluates "
            "paymentUnreachable=True/on"
        ):
            (
                len(
                    matching_flag_traces
                )
                == len(
                    trace_ids
                )
                and
                len(
                    trace_ids
                ) > 0
            ),

        (
            "every measured trace "
            "contains Checkout -> "
            "Payment CLIENT error"
        ):
            (
                client_error
                == len(
                    observations
                )
                and
                len(
                    observations
                ) > 0
            ),

        (
            "no Payment SERVER span "
            "is observed"
        ):
            (
                server_observed
                == 0
            ),

        (
            "no Payment log "
            "is observed"
        ):
            (
                len(
                    payment_logs
                )
                == 0
            ),

        (
            "every Checkout -> Payment "
            "client error exposes the "
            "resolver message"
        ):
            (
                resolver_message_count
                == client_error
                and
                client_error > 0
            ),
    }

    print()
    print(
        "CONTROLLED CASE CHECKS"
    )

    for description, passed in (
        checks.items()
    ):
        print(
            "  "
            f"{'PASS' if passed else 'FAIL'} "
            f"{description}"
        )

    if not all(
        checks.values()
    ):
        raise SystemExit(
            "PAYMENT UNREACHABLE "
            "CONTENT VALIDATION FAILED"
        )

    print()
    print(
        "PAYMENT UNREACHABLE "
        "CONTENT VALIDATION PASSED"
    )


if __name__ == "__main__":
    main()
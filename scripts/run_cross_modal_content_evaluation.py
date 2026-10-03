from __future__ import annotations

import argparse

from rootlens.evaluation.cross_modal_content import (
    exact_log_body_prevalence,
    metric_changes,
    request_evidence_rows,
    trace_payment_observations,
)
from rootlens.evaluation.synced_cross_modal import (
    load_synced_incident_evidence,
)


INVALID_TOKEN_TEXT = (
    "Payment request failed. "
    "Invalid token. "
    "demo.user_context.loyalty_level=gold"
)


def yes_no(
    value: bool,
) -> str:
    return (
        "YES"
        if value
        else "NO"
    )


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

    bundle = loaded.bundle

    print(
        "=" * 90
    )
    print(
        "ROOTLENS 015D — "
        "CROSS-MODAL CONTENT "
        "VALIDATION"
    )
    print(
        "=" * 90
    )

    print(
        f"scenario: "
        f"{loaded.scenario}"
    )

    print()

    #
    # 1. Metrics
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
    # 2. Traces
    #

    observations = (
        trace_payment_observations(
            bundle
        )
    )

    total_traces = len(
        observations
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
        "TRACE EVIDENCE"
    )

    print(
        "  traces: "
        f"{total_traces}"
    )

    print(
        "  Checkout -> Payment "
        "CLIENT observed: "
        f"{client_observed}/"
        f"{total_traces}"
    )

    print(
        "  Checkout -> Payment "
        "CLIENT error:    "
        f"{client_error}/"
        f"{total_traces}"
    )

    print(
        "  Payment SERVER observed: "
        f"{server_observed}/"
        f"{total_traces}"
    )

    print(
        "  Payment SERVER error:    "
        f"{server_error}/"
        f"{total_traces}"
    )

    #
    # 3. Logs
    #

    trace_ids = tuple(
        observation.trace_id
        for observation
        in observations
    )

    log_prevalence = (
        exact_log_body_prevalence(
            bundle.logs,
            service_name="payment",
            trace_ids=trace_ids,
        )
    )

    print()
    print(
        "PAYMENT LOG EVIDENCE"
    )

    for row in (
        log_prevalence[:10]
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
    # 4. Request-level cross-modal join
    #

    rows = request_evidence_rows(
        bundle
    )

    print()
    print(
        "REQUEST-LEVEL "
        "CROSS-MODAL JOIN"
    )

    print(
        "  trace_id"
        "                           "
        "client_error "
        "server_error "
        "invalid_token_log"
    )

    joined_count = 0

    for row in rows:
        invalid_token = (
            INVALID_TOKEN_TEXT
            in row.payment_log_bodies
        )

        all_three = (
            row
            .checkout_payment_client_error
            and
            row
            .payment_server_error
            and
            invalid_token
        )

        if all_three:
            joined_count += 1

        print(
            "  "
            f"{row.trace_id} "
            f"{yes_no(row.checkout_payment_client_error):>12} "
            f"{yes_no(row.payment_server_error):>12} "
            f"{yes_no(invalid_token):>17}"
        )

    print()

    print(
        "  traces with all three "
        "evidence elements: "
        f"{joined_count}/"
        f"{len(rows)}"
    )

    #
    # Controlled positive-control acceptance
    #

    print()
    print(
        "POSITIVE CONTROL CHECKS"
    )

    checks = {
        (
            "checkout_error_rate "
            "changed 0 -> 1"
        ):
            any(
                change.metric_key
                == "checkout_error_rate"
                and change.baseline == 0.0
                and change.incident == 1.0
                for change
                in changes
            ),

        (
            "checkout_payment_error_rate "
            "changed 0 -> 1"
        ):
            any(
                change.metric_key
                == (
                    "checkout_payment_"
                    "error_rate"
                )
                and change.baseline == 0.0
                and change.incident == 1.0
                for change
                in changes
            ),

        (
            "all incident traces contain "
            "Checkout -> Payment "
            "CLIENT error"
        ):
            (
                total_traces > 0
                and client_error
                == total_traces
            ),

        (
            "all incident traces contain "
            "Payment SERVER error"
        ):
            (
                total_traces > 0
                and server_error
                == total_traces
            ),

        (
            "all incident traces contain "
            "the expected Payment "
            "invalid-token log"
        ):
            (
                len(rows) > 0
                and joined_count
                == len(rows)
            ),
    }

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
            "CONTENT VALIDATION FAILED"
        )

    print()
    print(
        "CONTENT VALIDATION PASSED"
    )


if __name__ == "__main__":
    main()
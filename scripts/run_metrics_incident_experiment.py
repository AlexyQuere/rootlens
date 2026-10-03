from __future__ import annotations

import argparse
import json
import time

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path
from urllib.request import urlopen

from rootlens.observability.evidence import (
    MetricComparisonEvidence,
    MetricEvidence,
    TimeWindow,
)

from rootlens.observability.metrics import (
    MetricsTool,
)

from rootlens.observability.prometheus import (
    PrometheusClient,
)


PROMETHEUS_URL = (
    "http://localhost:9090"
)

FEATURE_API_URL = (
    "http://localhost:8080/"
    "feature/api/read"
)


CHECKOUT_OPERATION = (
    "oteldemo."
    "CheckoutService/"
    "PlaceOrder"
)


PAYMENT_OPERATION = (
    "oteldemo."
    "PaymentService/"
    "Charge"
)


TARGET_FLAGS = (
    "paymentFailure",
    "paymentUnreachable",
)


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Run a controlled RootLens "
            "metrics incident experiment."
        )
    )

    parser.add_argument(
        "--scenario",
        required=True,
        choices=(
            "paymentFailure",
            "paymentUnreachable",
        ),
    )

    parser.add_argument(
        "--failure-percent",
        type=int,
        default=100,
    )

    parser.add_argument(
        "--window-seconds",
        type=int,
        default=300,
    )

    parser.add_argument(
        "--artifact-version",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
    )

    args = parser.parse_args()

    if args.window_seconds <= 0:
        parser.error(
            "--window-seconds must "
            "be positive."
        )

    if args.artifact_version <= 0:
        parser.error(
            "--artifact-version must "
            "be positive."
        )

    return args


def utc_now() -> datetime:

    return datetime.now(
        timezone.utc
    )


def make_window(
    end: datetime,
    seconds: int,
) -> TimeWindow:

    return TimeWindow(
        start=(
            end
            - timedelta(
                seconds=seconds
            )
        ),
        end=end,
    )


def read_feature_configuration() -> dict:

    with urlopen(
        FEATURE_API_URL,
        timeout=10,
    ) as response:

        payload = json.loads(
            response.read()
        )

    flags = payload.get(
        "flags"
    )

    if not isinstance(
        flags,
        dict,
    ):
        raise RuntimeError(
            "Feature API returned no "
            "valid flags object."
        )

    return flags


def default_variants(
    flags: dict,
) -> dict[str, str]:

    result = {}

    for name, configuration in (
        flags.items()
    ):

        variant = configuration.get(
            "defaultVariant"
        )

        if isinstance(
            variant,
            str,
        ):
            result[
                name
            ] = variant

    return result


def target_variants(
    flags: dict,
) -> dict[str, str]:

    variants = (
        default_variants(
            flags
        )
    )

    return {
        name:
            variants.get(
                name,
                "<missing>",
            )
        for name
        in TARGET_FLAGS
    }


def print_target_flags(
    title: str,
    flags: dict,
) -> None:

    print()
    print(title)

    for name, value in (
        target_variants(
            flags
        ).items()
    ):

        print(
            f"  {name:<20} "
            f"{value}"
        )


def require_target_state(
    flags: dict,
    *,
    payment_failure: str,
    payment_unreachable: str,
) -> None:

    actual = target_variants(
        flags
    )

    expected = {
        "paymentFailure":
            payment_failure,

        "paymentUnreachable":
            payment_unreachable,
    }

    if actual != expected:

        raise RuntimeError(
            "Unexpected target feature-flag "
            "state.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}"
        )


def changed_flags(
    before: dict,
    after: dict,
) -> dict[
    str,
    tuple[
        str | None,
        str | None,
    ],
]:

    before_values = (
        default_variants(
            before
        )
    )

    after_values = (
        default_variants(
            after
        )
    )

    names = (
        set(
            before_values
        )
        | set(
            after_values
        )
    )

    changes = {}

    for name in sorted(
        names
    ):

        left = before_values.get(
            name
        )

        right = after_values.get(
            name
        )

        if left != right:
            changes[
                name
            ] = (
                left,
                right,
            )

    return changes


def expected_incident_variant(
    scenario: str,
    failure_percent: int,
) -> str:

    if scenario == "paymentFailure":
        return (
            f"{failure_percent}%"
        )

    return "on"


def require_expected_changes(
    baseline_flags: dict,
    incident_flags: dict,
    *,
    scenario: str,
    failure_percent: int,
) -> None:

    changes = changed_flags(
        baseline_flags,
        incident_flags,
    )

    expected_variant = (
        expected_incident_variant(
            scenario,
            failure_percent,
        )
    )

    expected_changes = {
        scenario: (
            "off",
            expected_variant,
        )
    }

    if changes != expected_changes:

        raise RuntimeError(
            "Unexpected feature-flag changes "
            "between baseline and incident.\n"
            f"Expected: {expected_changes}\n"
            f"Actual:   {changes}\n"
            "\n"
            "Another fault may have changed. "
            "Abort the experiment."
        )


def require_confirmation(
    message: str,
) -> None:

    print()
    print(message)
    print()

    answer = input(
        "Type YES to confirm: "
    )

    if (
        answer.strip().upper()
        != "YES"
    ):
        raise SystemExit(
            "Experiment cancelled."
        )


def wait_for_window(
    seconds: int,
    *,
    label: str,
) -> None:

    remaining = seconds

    print()
    print(
        f"{label}: waiting for a "
        f"complete {seconds}-second window."
    )

    while remaining > 0:

        interval = min(
            60,
            remaining,
        )

        time.sleep(
            interval
        )

        remaining -= interval

        print(
            f"  {remaining:>4} s remaining"
        )


def collect_metrics(
    metrics: MetricsTool,
    window: TimeWindow,
) -> dict[
    str,
    MetricEvidence,
]:

    result = {}

    result[
        "checkout_request_count"
    ] = metrics.request_count(
        family="rpc_server",
        service="checkout",
        operation=(
            CHECKOUT_OPERATION
        ),
        window=window,
    )

    result[
        "checkout_request_rate"
    ] = metrics.request_rate(
        family="rpc_server",
        service="checkout",
        operation=(
            CHECKOUT_OPERATION
        ),
        window=window,
    )

    result[
        "checkout_error_rate"
    ] = metrics.error_rate(
        family="rpc_server",
        service="checkout",
        operation=(
            CHECKOUT_OPERATION
        ),
        window=window,
    )

    for evidence in (
        metrics.latency_quantiles(
            family="rpc_server",
            service="checkout",
            operation=(
                CHECKOUT_OPERATION
            ),
            window=window,
        )
    ):

        result[
            f"checkout_"
            f"{evidence.statistic}"
        ] = evidence

    result[
        "checkout_payment_request_count"
    ] = metrics.request_count(
        family="rpc_client",
        service="checkout",
        operation=(
            PAYMENT_OPERATION
        ),
        window=window,
    )

    result[
        "checkout_payment_request_rate"
    ] = metrics.request_rate(
        family="rpc_client",
        service="checkout",
        operation=(
            PAYMENT_OPERATION
        ),
        window=window,
    )

    result[
        "checkout_payment_error_rate"
    ] = metrics.error_rate(
        family="rpc_client",
        service="checkout",
        operation=(
            PAYMENT_OPERATION
        ),
        window=window,
    )

    result[
        "frontend_http_error_rate"
    ] = metrics.error_rate(
        family="http_server",
        service="frontend",
        window=window,
    )

    return result


def validate_healthy_baseline(
    observations:
        dict[
            str,
            MetricEvidence,
        ],
) -> None:

    checkout_errors = (
        observations[
            "checkout_error_rate"
        ].value
    )

    payment_errors = (
        observations[
            "checkout_payment_error_rate"
        ].value
    )

    checkout_count = (
        observations[
            "checkout_request_count"
        ].value
    )

    if checkout_count <= 0:
        raise RuntimeError(
            "Healthy baseline contains "
            "no checkout observations."
        )

    tolerance = 1e-9

    if (
        checkout_errors > tolerance
        or payment_errors > tolerance
    ):
        raise RuntimeError(
            "Baseline is not clean.\n"
            f"Checkout error rate: "
            f"{checkout_errors}\n"
            f"Checkout -> Payment error rate: "
            f"{payment_errors}\n"
            "\n"
            "Disable all faults and wait "
            "for another clean window."
        )


def serialize_evidence(
    evidence: MetricEvidence,
) -> dict:

    return {
        "name":
            evidence.name,

        "statistic":
            evidence.statistic,

        "value":
            evidence.value,

        "unit":
            evidence.unit,

        "service":
            evidence.service,

        "window": {
            "start":
                evidence.window
                .start
                .isoformat(),

            "end":
                evidence.window
                .end
                .isoformat(),
        },

        "promql":
            evidence.promql,

        "source":
            evidence.source,

        "labels":
            (
                dict(
                    evidence.labels
                )
                if evidence.labels
                is not None
                else None
            ),
    }


def print_observations(
    title: str,
    observations:
        dict[
            str,
            MetricEvidence,
        ],
) -> None:

    print()
    print("=" * 82)
    print(title)
    print("=" * 82)

    for key, evidence in (
        observations.items()
    ):

        print(
            f"{key:<40}"
            f"{evidence.value:>12.6f} "
            f"{evidence.unit}"
        )


def compare_observations(
    baseline:
        dict[
            str,
            MetricEvidence,
        ],
    incident:
        dict[
            str,
            MetricEvidence,
        ],
):

    comparisons = {}

    print()
    print("=" * 82)
    print(
        "HEALTHY VS INCIDENT"
    )
    print("=" * 82)

    for key in baseline:

        comparison = (
            MetricComparisonEvidence(
                baseline=baseline[
                    key
                ],
                incident=incident[
                    key
                ],
            )
        )

        comparisons[
            key
        ] = comparison

        relative = (
            "n/a"
            if comparison.relative_delta
            is None
            else (
                f"{comparison.relative_delta:+.2%}"
            )
        )

        print()
        print(key)

        print(
            f"  baseline: "
            f"{comparison.baseline.value:.6f}"
        )

        print(
            f"  incident: "
            f"{comparison.incident.value:.6f}"
        )

        print(
            f"  absolute delta: "
            f"{comparison.absolute_delta:+.6f}"
        )

        print(
            f"  relative delta: "
            f"{relative}"
        )

    return comparisons


def serialize_comparison(
    comparison:
        MetricComparisonEvidence,
) -> dict:

    return {
        "baseline_value":
            comparison.baseline.value,

        "incident_value":
            comparison.incident.value,

        "absolute_delta":
            comparison.absolute_delta,

        "relative_delta":
            comparison.relative_delta,

        "unit":
            comparison.unit,
    }


def output_path(
    *,
    scenario: str,
    failure_percent: int,
    version: int,
) -> Path:

    if scenario == "paymentFailure":
        name = (
            "payment_failure_"
            f"{failure_percent}"
        )

    else:
        name = (
            "payment_unreachable"
        )

    return Path(
        "data/evaluation/"
        f"metrics_{name}_v{version}.json"
    )


def main() -> None:

    args = parse_args()

    path = output_path(
        scenario=args.scenario,
        failure_percent=(
            args.failure_percent
        ),
        version=(
            args.artifact_version
        ),
    )

    if (
        path.exists()
        and not args.overwrite
    ):
        raise SystemExit(
            "Refusing to overwrite "
            f"{path}"
        )

    client = PrometheusClient(
        PROMETHEUS_URL
    )

    metrics = MetricsTool(
        client
    )

    print(
        "Experiment 015A — "
        "Deterministic Metrics Investigation"
    )

    print(
        f"Scenario: {args.scenario}"
    )

    print(
        "RootLens analysis input: "
        "Prometheus only."
    )

    print(
        "Feature-flag state is "
        "benchmark metadata only."
    )

    initial_flags = (
        read_feature_configuration()
    )

    print_target_flags(
        "INITIAL TARGET FLAGS",
        initial_flags,
    )

    require_target_state(
        initial_flags,
        payment_failure="off",
        payment_unreachable="off",
    )

    require_confirmation(
        "PRE-BASELINE CHECK\n"
        "\n"
        "1. The Flagd Scheduler is STOPPED.\n"
        "2. Both payment faults are OFF.\n"
        "3. The load generator is running.\n"
        "4. A manual checkout succeeds."
    )

    wait_for_window(
        args.window_seconds,
        label="BASELINE WASHOUT",
    )

    baseline_flags = (
        read_feature_configuration()
    )

    require_target_state(
        baseline_flags,
        payment_failure="off",
        payment_unreachable="off",
    )

    baseline_end = (
        utc_now()
    )

    baseline_window = (
        make_window(
            baseline_end,
            args.window_seconds,
        )
    )

    baseline = (
        collect_metrics(
            metrics,
            baseline_window,
        )
    )

    print_observations(
        "HEALTHY BASELINE",
        baseline,
    )

    validate_healthy_baseline(
        baseline
    )

    print()
    print(
        "Healthy baseline validated."
    )

    if (
        args.scenario
        == "paymentFailure"
    ):
        instruction = (
            "Enable ONLY paymentFailure "
            f"at {args.failure_percent}%."
        )

    else:
        instruction = (
            "Enable ONLY "
            "paymentUnreachable."
        )

    require_confirmation(
        "INCIDENT MANIPULATION CHECK\n"
        "\n"
        f"{instruction}\n"
        "Perform several manual checkouts.\n"
        "Confirm that the expected failure "
        "is actually observable."
    )

    incident_start_flags = (
        read_feature_configuration()
    )

    if (
        args.scenario
        == "paymentFailure"
    ):
        require_target_state(
            incident_start_flags,
            payment_failure=(
                f"{args.failure_percent}%"
            ),
            payment_unreachable="off",
        )

    else:
        require_target_state(
            incident_start_flags,
            payment_failure="off",
            payment_unreachable="on",
        )

    require_expected_changes(
        baseline_flags,
        incident_start_flags,
        scenario=args.scenario,
        failure_percent=(
            args.failure_percent
        ),
    )

    incident_confirmed_at = (
        utc_now()
    )

    wait_for_window(
        args.window_seconds,
        label="INCIDENT",
    )

    incident_end_flags = (
        read_feature_configuration()
    )

    if (
        changed_flags(
            incident_start_flags,
            incident_end_flags,
        )
    ):
        raise RuntimeError(
            "Feature-flag configuration "
            "changed during the incident "
            "window. Run is confounded."
        )

    incident_end = utc_now()

    incident_window = (
        make_window(
            incident_end,
            args.window_seconds,
        )
    )

    incident = collect_metrics(
        metrics,
        incident_window,
    )

    print_observations(
        "INCIDENT",
        incident,
    )

    comparisons = (
        compare_observations(
            baseline,
            incident,
        )
    )

    artifact = {
        "experiment":
            "015A",

        "scenario":
            args.scenario,

        "window_seconds":
            args.window_seconds,

        "analysis_inputs": [
            "prometheus",
        ],

        "control_plane_used_for_analysis":
            False,

        "manipulation_check": {
            "scheduler_confirmed_stopped":
                True,

            "manual_healthy_checkout_confirmed":
                True,

            "manual_incident_effect_confirmed":
                True,

            "baseline_target_flags_verified":
                True,

            "incident_target_flags_verified":
                True,

            "incident_flags_stable":
                True,
        },

        "control_plane": {
            "baseline":
                default_variants(
                    baseline_flags
                ),

            "incident_start":
                default_variants(
                    incident_start_flags
                ),

            "incident_end":
                default_variants(
                    incident_end_flags
                ),
        },

        "baseline_capture_time":
            baseline_end.isoformat(),

        "incident_confirmed_time":
            incident_confirmed_at
            .isoformat(),

        "incident_capture_time":
            incident_end.isoformat(),

        "baseline": {
            key:
                serialize_evidence(
                    value
                )
            for key, value
            in baseline.items()
        },

        "incident": {
            key:
                serialize_evidence(
                    value
                )
            for key, value
            in incident.items()
        },

        "comparisons": {
            key:
                serialize_comparison(
                    value
                )
            for key, value
            in comparisons.items()
        },
    }

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            artifact,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "VALID EXPERIMENT ARTIFACT"
    )

    print(
        path
    )

    print()
    print(
        "The injected fault can "
        "now be disabled."
    )


if __name__ == "__main__":
    main()
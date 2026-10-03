from __future__ import annotations

import argparse
import json
import os
import time

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.request import (
    Request,
    urlopen,
)

from rootlens.evaluation.trace_capture import (
    capture_relation_window,
)

from rootlens.evaluation.trace_incident import (
    ClientServerRelationSpec,
)

from rootlens.observability.jaeger import (
    JaegerClient,
)

from rootlens.observability.trace_investigation import (
    TraceInvestigationTool,
)


CHECKOUT_OPERATION = (
    "oteldemo.CheckoutService/"
    "PlaceOrder"
)

PAYMENT_OPERATION = (
    "oteldemo.PaymentService/"
    "Charge"
)


TARGET_FLAGS = (
    "paymentFailure",
    "paymentUnreachable",
)


HEALTHY_STATE = {
    "paymentFailure":
        "off",

    "paymentUnreachable":
        "off",
}


INCIDENT_STATE = {
    "paymentFailure": {
        "paymentFailure":
            "100%",

        "paymentUnreachable":
            "off",
    },

    "paymentUnreachable": {
        "paymentFailure":
            "off",

        "paymentUnreachable":
            "on",
    },
}


def now_utc() -> datetime:

    return datetime.now(
        timezone.utc
    )


def read_feature_flags(
    feature_url: str,
) -> dict:

    request = Request(
        feature_url,
        headers={
            "Accept":
                "application/json"
        },
        method="GET",
    )

    try:

        with urlopen(
            request,
            timeout=10,
        ) as response:

            raw = response.read()

    except HTTPError as exc:

        body = (
            exc.read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        raise RuntimeError(
            "Feature API returned "
            f"HTTP {exc.code}: "
            f"{body}"
        ) from exc

    except URLError as exc:

        raise RuntimeError(
            "Could not reach "
            "feature API: "
            f"{exc.reason}"
        ) from exc

    payload = json.loads(
        raw.decode(
            "utf-8"
        )
    )

    flags = payload.get(
        "flags"
    )

    if not isinstance(
        flags,
        dict,
    ):
        raise RuntimeError(
            "Feature API response "
            "does not contain "
            "a flags object."
        )

    return flags


def default_variants(
    flags: dict,
) -> dict[str, str]:

    result = {}

    for name, config in (
        flags.items()
    ):

        if not isinstance(
            config,
            dict,
        ):
            continue

        variant = config.get(
            "defaultVariant"
        )

        if isinstance(
            variant,
            str,
        ):
            result[name] = variant

    return result


def assert_target_state(
    variants: dict[str, str],
    expected: dict[str, str],
    *,
    label: str,
) -> None:

    failures = []

    for flag, value in (
        expected.items()
    ):

        actual = variants.get(
            flag
        )

        if actual != value:

            failures.append(
                f"{flag}: "
                f"expected={value!r}, "
                f"actual={actual!r}"
            )

    if failures:

        raise RuntimeError(
            f"{label} target-state "
            "validation failed:\n"
            + "\n".join(
                failures
            )
        )


def changed_flags(
    before: dict[str, str],
    after: dict[str, str],
) -> set[str]:

    names = (
        set(before)
        | set(after)
    )

    return {
        name
        for name in names
        if (
            before.get(name)
            != after.get(name)
        )
    }


def assert_unchanged(
    before: dict[str, str],
    after: dict[str, str],
    *,
    label: str,
) -> None:

    changed = changed_flags(
        before,
        after,
    )

    if changed:

        changes = [
            (
                f"{name}: "
                f"{before.get(name)!r}"
                " -> "
                f"{after.get(name)!r}"
            )
            for name
            in sorted(changed)
        ]

        raise RuntimeError(
            f"{label}: feature "
            "configuration changed "
            "during the window:\n"
            + "\n".join(
                changes
            )
        )


def wait_seconds(
    seconds: int,
    *,
    label: str,
) -> None:

    if seconds <= 0:
        return

    print()
    print(label)

    remaining = seconds

    while remaining > 0:

        chunk = min(
            60,
            remaining,
        )

        time.sleep(
            chunk
        )

        remaining -= chunk

        print(
            f"  {remaining:4d} s "
            "remaining"
        )


def write_artifact(
    path: Path,
    artifact: dict,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            artifact,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def capture_window(
    *,
    name: str,
    client: JaegerClient,
    tool: TraceInvestigationTool,
    relation_spec:
        ClientServerRelationSpec,
    feature_url: str,
    expected_state:
        dict[str, str],
    window_seconds: int,
    ingestion_grace_seconds: int,
    max_traces: int,
) -> tuple[
    dict,
    dict[str, str],
    dict[str, str],
]:

    flags_start = (
        read_feature_flags(
            feature_url
        )
    )

    variants_start = (
        default_variants(
            flags_start
        )
    )

    assert_target_state(
        variants_start,
        expected_state,
        label=f"{name} start",
    )

    start = now_utc()

    wait_seconds(
        window_seconds,
        label=(
            f"Collecting complete "
            f"{window_seconds}-second "
            f"{name} window."
        ),
    )

    end = now_utc()

    flags_end = (
        read_feature_flags(
            feature_url
        )
    )

    variants_end = (
        default_variants(
            flags_end
        )
    )

    assert_target_state(
        variants_end,
        expected_state,
        label=f"{name} end",
    )

    assert_unchanged(
        variants_start,
        variants_end,
        label=name,
    )

    wait_seconds(
        ingestion_grace_seconds,
        label=(
            "Waiting for trace "
            "ingestion grace period."
        ),
    )

    captured = (
        capture_relation_window(
            client=client,
            tool=tool,
            relation_spec=(
                relation_spec
            ),
            start=start,
            end=end,
            search_service=(
                "checkout"
            ),
            search_operation=(
                CHECKOUT_OPERATION
            ),
            max_traces=(
                max_traces
            ),
        )
    )

    flags_after_capture = (
        read_feature_flags(
            feature_url
        )
    )

    variants_after_capture = (
        default_variants(
            flags_after_capture
        )
    )

    assert_target_state(
        variants_after_capture,
        expected_state,
        label=(
            f"{name} "
            "post-capture"
        ),
    )

    assert_unchanged(
        variants_end,
        variants_after_capture,
        label=(
            f"{name} capture"
        ),
    )

    captured[
        "control_plane"
    ] = {
        "start_default_variants":
            variants_start,

        "end_default_variants":
            variants_end,

        "post_capture_default_variants":
            variants_after_capture,

        "used_for_analysis":
            False,
    }

    return (
        captured,
        variants_start,
        variants_after_capture,
    )


def print_capture_summary(
    name: str,
    capture: dict,
) -> None:

    print()
    print("=" * 90)
    print(
        name.upper()
    )
    print("=" * 90)

    print(
        "window: "
        f"{capture['start']} "
        "-> "
        f"{capture['end']}"
    )

    print(
        "discovered traces: "
        f"{capture['search']['discovered_trace_count']}"
    )

    print(
        "frozen checkout traces: "
        f"{capture['fetched_trace_count']}"
    )

    print(
        "fetch errors: "
        f"{len(capture['fetch_errors'])}"
    )

    print(
        "excluded traces: "
        f"{len(capture['excluded_no_target_span'])}"
    )

    summary = capture[
        "summary"
    ]

    print()
    print(
        "Checkout -> Payment "
        "relation classes:"
    )

    for (
        classification,
        count,
    ) in summary[
        "class_counts"
    ]:

        print(
            f"  "
            f"{classification:<40}"
            f"{count}"
        )

    print()
    print(
        "client observed: "
        f"{summary['client_observed_count']}"
    )

    print(
        "client ERROR: "
        f"{summary['client_error_count']}"
    )

    print(
        "server observed: "
        f"{summary['server_observed_count']}"
    )

    print(
        "server ERROR: "
        f"{summary['server_error_count']}"
    )

    print(
        "client ERROR without server: "
        f"{summary['client_error_no_server_count']}"
    )

    print(
        "client non-error without server: "
        f"{summary['client_non_error_no_server_count']}"
    )


def main() -> None:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scenario",
        choices=(
            "paymentFailure",
            "paymentUnreachable",
        ),
        required=True,
    )

    parser.add_argument(
        "--window-seconds",
        type=int,
        default=300,
    )

    parser.add_argument(
        "--washout-seconds",
        type=int,
        default=30,
    )

    parser.add_argument(
        "--ingestion-grace-seconds",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--max-traces",
        type=int,
        default=200,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    if args.window_seconds <= 0:
        raise ValueError(
            "window-seconds must "
            "be positive."
        )

    if args.washout_seconds < 0:
        raise ValueError(
            "washout-seconds must "
            "be non-negative."
        )

    if (
        args.ingestion_grace_seconds
        < 0
    ):
        raise ValueError(
            "ingestion-grace-seconds "
            "must be non-negative."
        )

    feature_url = os.getenv(
        "ROOTLENS_FEATURE_URL",
        (
            "http://localhost:8080/"
            "feature/api/read"
        ),
    )

    jaeger_url = os.getenv(
        "ROOTLENS_JAEGER_URL",
        "http://localhost:8080",
    )

    client = JaegerClient(
        jaeger_url
    )

    tool = (
        TraceInvestigationTool()
    )

    relation_spec = (
        ClientServerRelationSpec(
            client_service=(
                "checkout"
            ),
            client_operation=(
                PAYMENT_OPERATION
            ),
            server_service=(
                "payment"
            ),
            server_operation=(
                PAYMENT_OPERATION
            ),
        )
    )

    scenario = args.scenario

    incident_state = (
        INCIDENT_STATE[
            scenario
        ]
    )

    output = Path(
        args.output
    )

    print(
        "=" * 90
    )

    print(
        "ROOTLENS EXPERIMENT 015B.4"
    )

    print(
        "=" * 90
    )

    print(
        f"Scenario: {scenario}"
    )

    print(
        f"Window: "
        f"{args.window_seconds}s"
    )

    print(
        f"Jaeger: {jaeger_url}"
    )

    print(
        f"Feature API: "
        f"{feature_url}"
    )

    print()
    print(
        "This experiment does not "
        "modify feature flags."
    )

    print(
        "Control-plane state is "
        "recorded for experimental "
        "validation only."
    )

    print()

    input(
        "Confirm the Feature Flag "
        "Scheduler is STOPPED, both "
        "paymentFailure and "
        "paymentUnreachable are OFF, "
        "the load generator is running, "
        "and a manual healthy checkout "
        "works. Press Enter..."
    )

    initial_flags = (
        read_feature_flags(
            feature_url
        )
    )

    initial_variants = (
        default_variants(
            initial_flags
        )
    )

    assert_target_state(
        initial_variants,
        HEALTHY_STATE,
        label="initial",
    )

    wait_seconds(
        args.washout_seconds,
        label=(
            "Baseline washout before "
            "the measured trace window."
        ),
    )

    baseline, _, (
        baseline_final_variants
    ) = capture_window(
        name="baseline",
        client=client,
        tool=tool,
        relation_spec=(
            relation_spec
        ),
        feature_url=(
            feature_url
        ),
        expected_state=(
            HEALTHY_STATE
        ),
        window_seconds=(
            args.window_seconds
        ),
        ingestion_grace_seconds=(
            args
            .ingestion_grace_seconds
        ),
        max_traces=(
            args.max_traces
        ),
    )

    artifact = {
        "experiment":
            "015B.4",

        "status":
            "baseline_captured",

        "scenario":
            scenario,

        "created_at":
            now_utc().isoformat(),

        "window_seconds":
            args.window_seconds,

        "washout_seconds":
            args.washout_seconds,

        "ingestion_grace_seconds":
            (
                args
                .ingestion_grace_seconds
            ),

        "jaeger_url":
            jaeger_url,

        "feature_url":
            feature_url,

        "analysis_inputs": [
            "jaeger",
        ],

        "control_plane_used_for_analysis":
            False,

        "relation": {
            "client_service":
                "checkout",

            "client_operation":
                PAYMENT_OPERATION,

            "server_service":
                "payment",

            "server_operation":
                PAYMENT_OPERATION,
        },

        "baseline":
            baseline,

        "incident":
            None,
    }

    write_artifact(
        output,
        artifact,
    )

    print_capture_summary(
        "baseline",
        baseline,
    )

    print()
    print(
        "Baseline traces have now "
        "been frozen to disk."
    )

    print()
    print(
        f"Now enable ONLY "
        f"{scenario}."
    )

    if (
        scenario
        == "paymentFailure"
    ):

        print(
            "Set paymentFailure "
            "to the 100% variant."
        )

    else:

        print(
            "Set paymentUnreachable "
            "to ON."
        )

    input(
        "After enabling it, trigger "
        "one manual checkout and "
        "confirm the expected failure. "
        "Then press Enter..."
    )

    incident_pre_flags = (
        read_feature_flags(
            feature_url
        )
    )

    incident_pre_variants = (
        default_variants(
            incident_pre_flags
        )
    )

    assert_target_state(
        incident_pre_variants,
        incident_state,
        label=(
            "incident pre-window"
        ),
    )

    changed = changed_flags(
        baseline_final_variants,
        incident_pre_variants,
    )

    if changed != {
        scenario
    }:

        raise RuntimeError(
            "Expected exactly one "
            "feature flag to change "
            "between baseline and "
            "incident: "
            f"{scenario}. "
            "Observed changes: "
            f"{sorted(changed)}"
        )

    incident, _, _ = (
        capture_window(
            name="incident",
            client=client,
            tool=tool,
            relation_spec=(
                relation_spec
            ),
            feature_url=(
                feature_url
            ),
            expected_state=(
                incident_state
            ),
            window_seconds=(
                args.window_seconds
            ),
            ingestion_grace_seconds=(
                args
                .ingestion_grace_seconds
            ),
            max_traces=(
                args.max_traces
            ),
        )
    )

    artifact[
        "status"
    ] = "complete"

    artifact[
        "completed_at"
    ] = (
        now_utc().isoformat()
    )

    artifact[
        "incident"
    ] = incident

    write_artifact(
        output,
        artifact,
    )

    print_capture_summary(
        "incident",
        incident,
    )

    print()
    print("=" * 90)

    print(
        "EXPERIMENT COMPLETE"
    )

    print("=" * 90)

    print(
        f"Frozen artifact: "
        f"{output}"
    )

    print()
    print(
        f"You can now disable "
        f"{scenario}."
    )


if __name__ == "__main__":
    main()
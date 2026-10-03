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

from dotenv import load_dotenv

from rootlens.evaluation.runtime_feature_flag import (
    extract_feature_flag_observations,
    runtime_state_matches,
)
from rootlens.observability.jaeger import (
    JaegerClient,
)
from rootlens.observability.otlp_trace import (
    parse_otlp_traces,
)


CHECKOUT_OPERATION = (
    "oteldemo.CheckoutService/PlaceOrder"
)


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def atomic_write_json(
    path: Path,
    payload,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    temporary.replace(
        path
    )


def parse_bool(
    value: str,
) -> bool:
    normalized = (
        value.casefold()
    )

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise argparse.ArgumentTypeError(
        "Expected true or false."
    )


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--flag",
        default=(
            "paymentUnreachable"
        ),
    )

    parser.add_argument(
        "--expected-value",
        type=parse_bool,
        default=True,
    )

    parser.add_argument(
        "--expected-variant",
        default="on",
    )

    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=90,
    )

    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=5.0,
    )

    parser.add_argument(
        "--trace-limit",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--minimum-matching-events",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--jaeger-url",
        default=None,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    jaeger_url = (
        args.jaeger_url
        or os.environ.get(
            "ROOTLENS_JAEGER_URL",
            "http://localhost:8080",
        )
    )

    jaeger = JaegerClient(
        jaeger_url
    )

    probe_started_at = (
        utc_now()
    )

    deadline = (
        time.monotonic()
        + args.timeout_seconds
    )

    print(
        "=" * 90
    )
    print(
        "ROOTLENS 015D — "
        "RUNTIME FEATURE-FLAG "
        "MANIPULATION CHECK"
    )
    print(
        "=" * 90
    )

    print(
        f"flag: "
        f"{args.flag}"
    )
    print(
        "expected runtime value: "
        f"{args.expected_value}"
    )
    print(
        "expected variant: "
        f"{args.expected_variant}"
    )
    print(
        f"probe start: "
        f"{probe_started_at.isoformat()}"
    )
    print()

    final_observations = ()
    result = "timeout"

    while (
        time.monotonic()
        < deadline
    ):
        now = utc_now()

        payload = (
            jaeger.find_traces(
                service_name="checkout",
                start=(
                    probe_started_at
                ),
                end=now,
                num_traces=(
                    args.trace_limit
                ),
                operation_name=(
                    CHECKOUT_OPERATION
                ),
            )
        )

        traces = (
            parse_otlp_traces(
                payload
            )
        )

        observations = (
            extract_feature_flag_observations(
                traces,
                flag_key=(
                    args.flag
                ),
            )
        )

        final_observations = (
            observations
        )

        print(
            "matching runtime "
            "flag events: "
            f"{len(observations)}",
            end="\r",
            flush=True,
        )

        if observations:
            mismatches = [
                observation
                for observation
                in observations
                if not runtime_state_matches(
                    observation,
                    expected_value=(
                        args.expected_value
                    ),
                    expected_variant=(
                        args.expected_variant
                    ),
                )
            ]

            if mismatches:
                result = "fail"
                break

            if (
                len(
                    observations
                )
                >= args
                .minimum_matching_events
            ):
                result = "pass"
                break

        time.sleep(
            args.poll_seconds
        )

    probe_finished_at = (
        utc_now()
    )

    print()
    print()

    print(
        "OBSERVATIONS"
    )

    for observation in (
        final_observations
    ):
        print()
        print(
            f"trace: "
            f"{observation.trace_id}"
        )
        print(
            f"  value:   "
            f"{observation.value!r}"
        )
        print(
            f"  variant: "
            f"{observation.variant!r}"
        )
        print(
            f"  reason:  "
            f"{observation.reason!r}"
        )
        print(
            f"  provider:"
            f" {observation.provider!r}"
        )

    artifact = {
        "experiment":
            "015D",

        "kind":
            "runtime_manipulation_check",

        "used_for_analysis":
            False,

        "flag_key":
            args.flag,

        "expected": {
            "value":
                args.expected_value,

            "variant":
                args.expected_variant,
        },

        "service":
            "checkout",

        "operation":
            CHECKOUT_OPERATION,

        "probe_started_at":
            probe_started_at
            .isoformat(),

        "probe_finished_at":
            probe_finished_at
            .isoformat(),

        "jaeger_url":
            jaeger_url,

        "result":
            result,

        "observations": [
            {
                "trace_id":
                    observation.trace_id,

                "span_id":
                    observation.span_id,

                "value":
                    observation.value,

                "variant":
                    observation.variant,

                "reason":
                    observation.reason,

                "provider":
                    observation.provider,

                "event_time":
                    observation.event_time,
            }
            for observation
            in final_observations
        ],
    }

    output = Path(
        args.output
    )

    atomic_write_json(
        output,
        artifact,
    )

    print()
    print(
        "=" * 90
    )

    if result == "pass":
        print(
            "MANIPULATION CHECK PASSED"
        )
        print(
            "Checkout runtime is "
            "observably evaluating "
            f"{args.flag}=True/on."
        )

    elif result == "fail":
        print(
            "MANIPULATION CHECK FAILED"
        )
        print(
            "Do NOT start the "
            "incident window."
        )
        print(
            "The Checkout runtime "
            "is not yet evaluating "
            "the requested state."
        )

    else:
        print(
            "MANIPULATION CHECK TIMED OUT"
        )
        print(
            "No sufficient matching "
            "runtime evidence was "
            "observed."
        )

    print(
        "=" * 90
    )

    print()
    print(
        "Artifact:"
    )
    print(
        output
    )

    if result != "pass":
        raise SystemExit(
            2
        )


if __name__ == "__main__":
    main()
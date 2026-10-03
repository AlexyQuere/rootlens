from __future__ import annotations

import argparse
import json
import os
import time

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path

from dotenv import load_dotenv

from rootlens.evaluation.cross_modal_capture import (
    collect_metric_snapshot,
    collect_phase,
)
from rootlens.observability.jaeger import (
    JaegerClient,
)
from rootlens.observability.opensearch import (
    OpenSearchClient,
)
from rootlens.observability.prometheus import (
    PrometheusClient,
)


SCENARIO_INSTRUCTIONS = {
    "paymentFailure": {
        "baseline": (
            "Ensure paymentFailure is "
            "DISABLED."
        ),
        "incident": (
            "Enable paymentFailure at "
            "100%."
        ),
    },
    "paymentUnreachable": {
        "baseline": (
            "Ensure paymentUnreachable "
            "is DISABLED."
        ),
        "incident": (
            "Enable paymentUnreachable. "
            "For the controlled real-ON "
            "run, ensure Checkout has "
            "picked up the ON state "
            "before the measured window."
        ),
    },
}


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def wait_seconds(
    seconds: int,
    *,
    label: str,
) -> None:
    if seconds <= 0:
        return

    print()
    print(
        f"{label}: "
        f"{seconds}s"
    )

    deadline = (
        time.monotonic()
        + seconds
    )

    while True:
        remaining = (
            deadline
            - time.monotonic()
        )

        if remaining <= 0:
            print()
            return

        print(
            f"  {remaining:6.1f} s "
            "remaining",
            end="\r",
            flush=True,
        )

        time.sleep(
            min(
                remaining,
                5.0,
            )
        )


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scenario",
        choices=tuple(
            SCENARIO_INSTRUCTIONS
        ),
        default="paymentFailure",
    )

    parser.add_argument(
        "--window-seconds",
        type=int,
        default=300,
    )

    parser.add_argument(
        "--washout-seconds",
        type=int,
        default=60,
    )

    parser.add_argument(
        "--ingestion-wait-seconds",
        type=int,
        default=15,
    )

    parser.add_argument(
        "--trace-limit",
        type=int,
        default=200,
    )

    parser.add_argument(
        "--log-query-margin-seconds",
        type=int,
        default=60,
    )

    parser.add_argument(
        "--log-limit-per-trace",
        type=int,
        default=1000,
    )

    parser.add_argument(
        "--prometheus-url",
        default=None,
    )

    parser.add_argument(
        "--jaeger-url",
        default=None,
    )

    parser.add_argument(
        "--opensearch-url",
        default=None,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Reuse valid baseline/incident "
            "checkpoints when available."
        ),
    )

    return parser.parse_args()


def require_positive(
    value,
    name,
) -> None:
    if value <= 0:
        raise ValueError(
            f"{name} must be > 0."
        )


def checkpoint_path(
    output: Path,
    phase: str,
) -> Path:
    return output.with_name(
        output.stem
        + f".{phase}.checkpoint.json"
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


def write_phase_checkpoint(
    *,
    output: Path,
    scenario: str,
    phase: str,
    confirmed_at: datetime | None,
    capture_config,
    endpoints,
    data,
) -> None:
    path = checkpoint_path(
        output,
        phase,
    )

    payload = {
        "experiment":
            "015D",
        "version":
            1,
        "scenario":
            scenario,
        "phase":
            phase,
        "capture_config":
            capture_config,
        "endpoints":
            endpoints,
        "confirmed_at": (
            confirmed_at.isoformat()
            if confirmed_at is not None
            else None
        ),
        "historical_recovery":
            False,
        "data":
            data,
    }

    atomic_write_json(
        path,
        payload,
    )

    print()
    print(
        f"{phase.capitalize()} "
        "checkpoint written:"
    )
    print(
        f"  {path}"
    )


def load_phase_checkpoint(
    *,
    output: Path,
    scenario: str,
    phase: str,
    capture_config,
):
    path = checkpoint_path(
        output,
        phase,
    )

    if not path.exists():
        return None

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if (
        payload.get(
            "experiment"
        )
        != "015D"
    ):
        raise ValueError(
            "Invalid checkpoint "
            "experiment."
        )

    if (
        payload.get(
            "scenario"
        )
        != scenario
    ):
        raise ValueError(
            "Checkpoint scenario "
            "does not match."
        )

    if (
        payload.get(
            "phase"
        )
        != phase
    ):
        raise ValueError(
            "Checkpoint phase "
            "does not match."
        )

    stored_config = payload.get(
        "capture_config"
    )

    if stored_config != capture_config:
        raise ValueError(
            "Checkpoint capture "
            "configuration differs "
            "from current run."
        )

    if "data" not in payload:
        raise ValueError(
            "Checkpoint has no "
            "phase data."
        )

    return payload


def parse_optional_datetime(
    value,
) -> datetime | None:
    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise ValueError(
            "Checkpoint confirmed_at "
            "must be a string or null."
        )

    result = datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
        )
    )

    if (
        result.tzinfo is None
        or result.utcoffset() is None
    ):
        raise ValueError(
            "Checkpoint confirmed_at "
            "must be timezone-aware."
        )

    return result


def datetime_to_json(
    value: datetime | None,
):
    if value is None:
        return None

    return value.isoformat()


def collect_or_resume_phase(
    *,
    args,
    output: Path,
    scenario: str,
    phase: str,
    instruction: str,
    capture_config,
    endpoints,
    prometheus: PrometheusClient,
    jaeger: JaegerClient,
    opensearch: OpenSearchClient,
):
    checkpoint = None

    if args.resume:
        checkpoint = (
            load_phase_checkpoint(
                output=output,
                scenario=scenario,
                phase=phase,
                capture_config=(
                    capture_config
                ),
            )
        )

    if checkpoint is not None:
        print()
        print(
            f"Reusing {phase} "
            "checkpoint."
        )

        if checkpoint.get(
            "historical_recovery"
        ):
            print(
                "  checkpoint origin: "
                "historical recovery"
            )

        return (
            checkpoint["data"],
            parse_optional_datetime(
                checkpoint.get(
                    "confirmed_at"
                )
            ),
        )

    input(
        instruction
        + (
            "\nPress Enter when ready..."
            if phase == "baseline"
            else (
                "\nPress Enter only when "
                "the requested state is "
                "configured..."
            )
        )
    )

    confirmed_at = utc_now()

    wait_seconds(
        args.washout_seconds,
        label=(
            f"{phase.capitalize()} "
            "washout"
        ),
    )

    data = collect_phase(
        phase_name=phase,
        window_seconds=(
            args.window_seconds
        ),
        ingestion_wait_seconds=(
            args.ingestion_wait_seconds
        ),
        trace_limit=(
            args.trace_limit
        ),
        log_query_margin_seconds=(
            args.log_query_margin_seconds
        ),
        log_limit_per_trace=(
            args.log_limit_per_trace
        ),
        prometheus_client=(
            prometheus
        ),
        jaeger_client=(
            jaeger
        ),
        opensearch_client=(
            opensearch
        ),
    )

    write_phase_checkpoint(
        output=output,
        scenario=scenario,
        phase=phase,
        confirmed_at=confirmed_at,
        capture_config=(
            capture_config
        ),
        endpoints=endpoints,
        data=data,
    )

    return (
        data,
        confirmed_at,
    )


def main() -> None:
    load_dotenv()

    args = parse_args()

    require_positive(
        args.window_seconds,
        "window_seconds",
    )

    require_positive(
        args.trace_limit,
        "trace_limit",
    )

    require_positive(
        args.log_limit_per_trace,
        "log_limit_per_trace",
    )

    prometheus_url = (
        args.prometheus_url
        or os.environ.get(
            "ROOTLENS_PROMETHEUS_URL",
            "http://localhost:9090",
        )
    )

    jaeger_url = (
        args.jaeger_url
        or os.environ.get(
            "ROOTLENS_JAEGER_URL",
            "http://localhost:8080",
        )
    )

    opensearch_url = (
        args.opensearch_url
        or os.environ.get(
            "ROOTLENS_OPENSEARCH_URL"
        )
    )

    if not opensearch_url:
        raise RuntimeError(
            "OpenSearch URL is required. "
            "Set ROOTLENS_OPENSEARCH_URL "
            "or pass --opensearch-url."
        )

    output = Path(
        args.output
    )

    capture_config = {
        "window_seconds":
            args.window_seconds,
        "washout_seconds":
            args.washout_seconds,
        "ingestion_wait_seconds":
            args.ingestion_wait_seconds,
        "trace_limit":
            args.trace_limit,
        "log_query_margin_seconds":
            args.log_query_margin_seconds,
        "log_limit_per_trace":
            args.log_limit_per_trace,
    }

    endpoints = {
        "prometheus":
            prometheus_url,
        "jaeger":
            jaeger_url,
        "opensearch":
            opensearch_url,
    }

    prometheus = PrometheusClient(
        prometheus_url
    )

    jaeger = JaegerClient(
        jaeger_url
    )

    opensearch = OpenSearchClient(
        opensearch_url
    )

    scenario = args.scenario

    instructions = (
        SCENARIO_INSTRUCTIONS[
            scenario
        ]
    )

    print(
        "=" * 90
    )
    print(
        "EXPERIMENT 015D — "
        "SYNCHRONIZED "
        "CROSS-MODAL CAPTURE"
    )
    print(
        "=" * 90
    )
    print(
        f"scenario: {scenario}"
    )
    print(
        f"window: "
        f"{args.window_seconds}s"
    )
    print(
        f"washout: "
        f"{args.washout_seconds}s"
    )
    print(
        f"ingestion wait: "
        f"{args.ingestion_wait_seconds}s"
    )
    print()

    print(
        "Prometheus:"
    )
    print(
        f"  {prometheus_url}"
    )
    print(
        "Jaeger:"
    )
    print(
        f"  {jaeger_url}"
    )
    print(
        "OpenSearch:"
    )
    print(
        f"  {opensearch_url}"
    )
    print()

    print(
        "The scenario label and manual "
        "fault manipulation are NOT "
        "used as analysis evidence."
    )
    print()

    print(
        "Running telemetry preflight..."
    )

    preflight_end = utc_now()

    preflight_start = (
        preflight_end
        - timedelta(
            seconds=args.window_seconds
        )
    )

    preflight_metrics = (
        collect_metric_snapshot(
            prometheus_client=(
                prometheus
            ),
            start=preflight_start,
            end=preflight_end,
        )
    )

    print(
        "  Prometheus validated metrics: "
        f"{len(preflight_metrics)}"
    )

    services = (
        jaeger.list_services()
    )

    if "checkout" not in services:
        raise RuntimeError(
            "Jaeger preflight failed: "
            "checkout service not found."
        )

    print(
        "  Jaeger checkout service: OK"
    )
    print(
        "  Telemetry preflight: OK"
    )

    baseline, baseline_confirmed_at = (
        collect_or_resume_phase(
            args=args,
            output=output,
            scenario=scenario,
            phase="baseline",
            instruction=(
                instructions[
                    "baseline"
                ]
            ),
            capture_config=(
                capture_config
            ),
            endpoints=endpoints,
            prometheus=prometheus,
            jaeger=jaeger,
            opensearch=opensearch,
        )
    )

    print()
    print(
        "=" * 90
    )
    print(
        "BASELINE COMPLETE"
    )
    print(
        "=" * 90
    )

    incident, incident_confirmed_at = (
        collect_or_resume_phase(
            args=args,
            output=output,
            scenario=scenario,
            phase="incident",
            instruction=(
                instructions[
                    "incident"
                ]
            ),
            capture_config=(
                capture_config
            ),
            endpoints=endpoints,
            prometheus=prometheus,
            jaeger=jaeger,
            opensearch=opensearch,
        )
    )

    artifact = {
        "experiment":
            "015D",
        "version":
            1,
        "scenario":
            scenario,
        "captured_at":
            utc_now().isoformat(),
        "analysis_inputs": [
            "metrics",
            "traces",
            "logs",
        ],
        "control_plane_used_for_analysis":
            False,
        "capture_config":
            capture_config,
        "endpoints":
            endpoints,
        "manual_manipulation": {
            "baseline_instruction":
                instructions[
                    "baseline"
                ],
            "baseline_confirmed_at":
                datetime_to_json(
                    baseline_confirmed_at
                ),
            "incident_instruction":
                instructions[
                    "incident"
                ],
            "incident_confirmed_at":
                datetime_to_json(
                    incident_confirmed_at
                ),
        },
        "baseline":
            baseline,
        "incident":
            incident,
    }

    atomic_write_json(
        output,
        artifact,
    )

    print()
    print(
        "=" * 90
    )
    print(
        "CAPTURE COMPLETE"
    )
    print(
        "=" * 90
    )

    for phase_name in (
        "baseline",
        "incident",
    ):
        phase = artifact[
            phase_name
        ]

        metrics = phase[
            "metrics"
        ]

        traces = phase[
            "traces"
        ]

        logs = phase[
            "logs"
        ]

        print()
        print(
            phase_name.upper()
        )
        print(
            "  window:"
        )
        print(
            "    "
            f"{phase['window']['start']}"
        )
        print(
            "    "
            f"{phase['window']['end']}"
        )

        for key in (
            "checkout_error_rate",
            "checkout_payment_error_rate",
            "frontend_http_error_rate",
        ):
            metric = metrics.get(
                key
            )

            if metric is None:
                continue

            print(
                f"  {key:<32} "
                f"{metric['value']:.6f}"
            )

        print(
            "  checkout traces: "
            f"{traces['trace_count']}"
        )
        print(
            "  correlated logs: "
            f"{logs['total_logs']}"
        )

    print()
    print(
        "Frozen artifact:"
    )
    print(
        output
    )
    print()
    print(
        "Disable the incident fault "
        "when appropriate."
    )


if __name__ == "__main__":
    main()

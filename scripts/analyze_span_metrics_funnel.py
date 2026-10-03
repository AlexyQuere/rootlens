from __future__ import annotations

import argparse
import json

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rootlens.observability.prometheus import (
    PrometheusClient,
)


PROMETHEUS_URL = "http://localhost:9090"

SPAN_METRIC = (
    "traces_span_metrics_"
    "duration_milliseconds_count"
)


@dataclass(frozen=True)
class FunnelStage:
    name: str
    selectors: dict[str, str]


@dataclass(frozen=True)
class FunnelObservation:
    name: str
    total: float
    statuses: dict[str, float]
    promql: str


STAGES = (
    FunnelStage(
        name="load_generator_single",
        selectors={
            "service_name": "load-generator",
            "span_name": "user_checkout_single",
        },
    ),
    FunnelStage(
        name="load_generator_multi",
        selectors={
            "service_name": "load-generator",
            "span_name": "user_checkout_multi",
        },
    ),
    FunnelStage(
        name="frontend_checkout_server",
        selectors={
            "service_name": "frontend",
            "span_name": "POST /api/checkout",
            "span_kind": "SPAN_KIND_SERVER",
        },
    ),
    FunnelStage(
        name="frontend_to_checkout",
        selectors={
            "service_name": "frontend",
            "span_name": (
                "oteldemo.CheckoutService/"
                "PlaceOrder"
            ),
            "span_kind": "SPAN_KIND_CLIENT",
        },
    ),
    FunnelStage(
        name="checkout_server",
        selectors={
            "service_name": "checkout",
            "span_name": (
                "oteldemo.CheckoutService/"
                "PlaceOrder"
            ),
            "span_kind": "SPAN_KIND_SERVER",
        },
    ),
    FunnelStage(
        name="checkout_to_payment",
        selectors={
            "service_name": "checkout",
            "span_name": (
                "oteldemo.PaymentService/"
                "Charge"
            ),
            "span_kind": "SPAN_KIND_CLIENT",
        },
    ),
    FunnelStage(
        name="payment_server",
        selectors={
            "service_name": "payment",
            "span_name": (
                "oteldemo.PaymentService/"
                "Charge"
            ),
            "span_kind": "SPAN_KIND_SERVER",
        },
    ),
)


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Analyze the trace-derived "
            "checkout funnel for a frozen "
            "RootLens experiment artifact."
        )
    )

    parser.add_argument(
        "--artifact",
        required=True,
        type=Path,
        help=(
            "Path to a frozen metrics "
            "experiment JSON artifact."
        ),
    )

    return parser.parse_args()


def parse_timestamp(
    value: str,
) -> datetime:

    timestamp = datetime.fromisoformat(
        value
    )

    if timestamp.tzinfo is None:
        raise ValueError(
            "Experiment timestamps must "
            "be timezone-aware."
        )

    return timestamp


def promql_string(
    value: str,
) -> str:

    escaped = (
        value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
    )

    return f'"{escaped}"'


def selector_string(
    selectors: dict[str, str],
) -> str:

    parts = [
        (
            f"{key}="
            f"{promql_string(value)}"
        )
        for key, value
        in sorted(
            selectors.items()
        )
    ]

    return (
        "{"
        + ",".join(parts)
        + "}"
    )


def build_query(
    stage: FunnelStage,
    *,
    window_seconds: int,
) -> str:

    selector = selector_string(
        stage.selectors
    )

    return (
        "sum by (status_code) ("
        "increase("
        f"{SPAN_METRIC}"
        f"{selector}"
        f"[{window_seconds}s]"
        ")"
        ")"
    )


def observe_stage(
    client: PrometheusClient,
    stage: FunnelStage,
    *,
    evaluation_time: datetime,
    window_seconds: int,
) -> FunnelObservation:

    promql = build_query(
        stage,
        window_seconds=window_seconds,
    )

    samples = client.query(
        promql,
        time=evaluation_time,
    )

    statuses: dict[str, float] = {}

    for sample in samples:

        status = sample.metric.get(
            "status_code",
            "<missing>",
        )

        statuses[
            status
        ] = (
            statuses.get(
                status,
                0.0,
            )
            + sample.value
        )

    total = sum(
        statuses.values()
    )

    return FunnelObservation(
        name=stage.name,
        total=total,
        statuses=statuses,
        promql=promql,
    )


def collect_funnel(
    client: PrometheusClient,
    *,
    evaluation_time: datetime,
    window_seconds: int,
) -> dict[
    str,
    FunnelObservation,
]:

    return {
        stage.name:
            observe_stage(
                client,
                stage,
                evaluation_time=(
                    evaluation_time
                ),
                window_seconds=(
                    window_seconds
                ),
            )
        for stage in STAGES
    }


def print_funnel(
    title: str,
    observations: dict[
        str,
        FunnelObservation,
    ],
) -> None:

    print()
    print("=" * 90)
    print(title)
    print("=" * 90)

    for stage in STAGES:

        observation = observations[
            stage.name
        ]

        print()
        print(
            observation.name
        )

        print(
            f"  total: "
            f"{observation.total:.3f}"
        )

        print(
            f"  statuses: "
            f"{observation.statuses}"
        )

        print(
            f"  PromQL: "
            f"{observation.promql}"
        )


def print_comparison(
    baseline: dict[
        str,
        FunnelObservation,
    ],
    incident: dict[
        str,
        FunnelObservation,
    ],
) -> None:

    print()
    print("=" * 90)
    print("FUNNEL COMPARISON")
    print("=" * 90)

    for stage in STAGES:

        healthy = baseline[
            stage.name
        ].total

        degraded = incident[
            stage.name
        ].total

        delta = (
            degraded
            - healthy
        )

        print(
            f"{stage.name:<30}"
            f" healthy="
            f"{healthy:>8.3f}"
            f"  incident="
            f"{degraded:>8.3f}"
            f"  delta="
            f"{delta:>+8.3f}"
        )


def status_value(
    observation: FunnelObservation,
    status: str,
) -> float:

    return observation.statuses.get(
        status,
        0.0,
    )


def print_incident_diagnostics(
    incident: dict[
        str,
        FunnelObservation,
    ],
) -> None:

    client = incident[
        "checkout_to_payment"
    ]

    server = incident[
        "payment_server"
    ]

    client_total = client.total
    server_total = server.total

    missing_server = (
        client_total
        - server_total
    )

    client_error = status_value(
        client,
        "STATUS_CODE_ERROR",
    )

    server_error = status_value(
        server,
        "STATUS_CODE_ERROR",
    )

    print()
    print("=" * 90)
    print("INCIDENT FLOW DIAGNOSTICS")
    print("=" * 90)

    print()
    print(
        "Checkout -> Payment "
        f"client attempts: {client_total:.3f}"
    )

    print(
        "Payment server "
        f"observations:      {server_total:.3f}"
    )

    print(
        "Client - server "
        f"difference:        {missing_server:+.3f}"
    )

    print()
    print(
        "Checkout -> Payment "
        f"client errors:     {client_error:.3f}"
    )

    print(
        "Payment server "
        f"errors:            {server_error:.3f}"
    )

    print()
    print(
        "Interpretation is intentionally "
        "not automated here."
    )

    print(
        "These values are observations, "
        "not a root-cause conclusion."
    )


def load_artifact(
    path: Path,
) -> dict:

    if not path.exists():
        raise FileNotFoundError(
            path
        )

    artifact = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    required = (
        "scenario",
        "window_seconds",
        "baseline_capture_time",
        "incident_capture_time",
    )

    missing = [
        key
        for key in required
        if key not in artifact
    ]

    if missing:
        raise ValueError(
            "Artifact is missing "
            f"required fields: {missing}"
        )

    return artifact


def main() -> None:

    args = parse_args()

    artifact = load_artifact(
        args.artifact
    )

    scenario = artifact[
        "scenario"
    ]

    window_seconds = int(
        artifact[
            "window_seconds"
        ]
    )

    baseline_time = (
        parse_timestamp(
            artifact[
                "baseline_capture_time"
            ]
        )
    )

    incident_time = (
        parse_timestamp(
            artifact[
                "incident_capture_time"
            ]
        )
    )

    print(
        "Trace-derived Funnel Diagnostic"
    )

    print(
        f"Artifact: {args.artifact}"
    )

    print(
        f"Scenario: {scenario}"
    )

    print(
        f"Window: {window_seconds}s"
    )

    print(
        f"Baseline evaluation time: "
        f"{baseline_time.isoformat()}"
    )

    print(
        f"Incident evaluation time: "
        f"{incident_time.isoformat()}"
    )

    print()
    print(
        "NOTE: traces_span_metrics_* "
        "is derived from trace data."
    )

    print(
        "This diagnostic is not treated "
        "as an independent native-metrics "
        "source."
    )

    client = PrometheusClient(
        PROMETHEUS_URL
    )

    baseline = collect_funnel(
        client,
        evaluation_time=(
            baseline_time
        ),
        window_seconds=(
            window_seconds
        ),
    )

    incident = collect_funnel(
        client,
        evaluation_time=(
            incident_time
        ),
        window_seconds=(
            window_seconds
        ),
    )

    print_funnel(
        "HEALTHY FUNNEL",
        baseline,
    )

    print_funnel(
        "INCIDENT FUNNEL",
        incident,
    )

    print_comparison(
        baseline,
        incident,
    )

    print_incident_diagnostics(
        incident
    )


if __name__ == "__main__":
    main()
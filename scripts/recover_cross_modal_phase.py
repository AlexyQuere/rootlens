from __future__ import annotations

import argparse
import json
import os

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

from dotenv import load_dotenv

from rootlens.evaluation.cross_modal_capture import (
    collect_logs_for_traces,
    collect_metric_snapshot,
    collect_trace_payload,
    serialize_metric,
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


def parse_datetime(
    value: str,
) -> datetime:
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
            "Timestamp must be timezone-aware."
        )

    return result


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


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scenario",
        required=True,
    )

    parser.add_argument(
        "--phase",
        choices=(
            "baseline",
            "incident",
        ),
        required=True,
    )

    parser.add_argument(
        "--start",
        required=True,
    )

    parser.add_argument(
        "--end",
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
        "--output",
        required=True,
    )

    args = parser.parse_args()

    start = parse_datetime(
        args.start
    )

    end = parse_datetime(
        args.end
    )

    actual_seconds = (
        end - start
    ).total_seconds()

    if abs(
        actual_seconds
        - args.window_seconds
    ) > 0.001:
        raise ValueError(
            "Provided timestamps do not "
            "match --window-seconds: "
            f"{actual_seconds}s"
        )

    prometheus_url = os.environ.get(
        "ROOTLENS_PROMETHEUS_URL",
        "http://localhost:9090",
    )

    jaeger_url = os.environ.get(
        "ROOTLENS_JAEGER_URL",
        "http://localhost:8080",
    )

    opensearch_url = os.environ.get(
        "ROOTLENS_OPENSEARCH_URL"
    )

    if not opensearch_url:
        raise RuntimeError(
            "ROOTLENS_OPENSEARCH_URL "
            "is required."
        )

    prometheus = PrometheusClient(
        prometheus_url
    )

    jaeger = JaegerClient(
        jaeger_url
    )

    opensearch = OpenSearchClient(
        opensearch_url
    )

    print(
        "=" * 90
    )
    print(
        "ROOTLENS 015D — "
        "HISTORICAL PHASE RECOVERY"
    )
    print(
        "=" * 90
    )

    print(
        f"scenario: {args.scenario}"
    )
    print(
        f"phase:    {args.phase}"
    )
    print(
        f"start:    {start.isoformat()}"
    )
    print(
        f"end:      {end.isoformat()}"
    )

    print()
    print(
        "Recovering pinned metrics..."
    )

    metrics = collect_metric_snapshot(
        prometheus_client=prometheus,
        start=start,
        end=end,
    )

    print(
        f"  metrics: {len(metrics)}"
    )

    print()
    print(
        "Recovering traces..."
    )

    traces = collect_trace_payload(
        jaeger_client=jaeger,
        start=start,
        end=end,
        trace_limit=args.trace_limit,
    )

    trace_ids = tuple(
        traces["trace_ids"]
    )

    print(
        f"  traces: {len(trace_ids)}"
    )

    print()
    print(
        "Recovering logs..."
    )

    logs = collect_logs_for_traces(
        opensearch_client=opensearch,
        trace_ids=trace_ids,
        analytical_start=start,
        analytical_end=end,
        query_margin_seconds=(
            args.log_query_margin_seconds
        ),
        limit_per_trace=(
            args.log_limit_per_trace
        ),
    )

    recovered_at = datetime.now(
        timezone.utc
    )

    phase_data = {
        "phase":
            args.phase,

        "window": {
            "start":
                start.isoformat(),

            "end":
                end.isoformat(),

            "seconds":
                args.window_seconds,

            "window_finished_at":
                end.isoformat(),
        },

        "acquisition": {
            "ingestion_wait_seconds":
                args.ingestion_wait_seconds,

            "recovered":
                True,

            "recovered_at":
                recovered_at.isoformat(),

            "note": (
                "Evidence was reacquired "
                "historically after the "
                "original synchronized "
                "capture failed during "
                "serialization."
            ),
        },

        "metrics": {
            key: serialize_metric(
                evidence
            )
            for key, evidence
            in metrics.items()
        },

        "traces":
            traces,

        "logs":
            logs,
    }

    checkpoint = {
        "experiment":
            "015D",

        "version":
            1,

        "scenario":
            args.scenario,

        "phase":
            args.phase,

        "capture_config": {
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
        },

        "endpoints": {
            "prometheus":
                prometheus_url,

            "jaeger":
                jaeger_url,

            "opensearch":
                opensearch_url,
        },

        "confirmed_at":
            None,

        "historical_recovery":
            True,

        "data":
            phase_data,
    }

    output = Path(
        args.output
    )

    atomic_write_json(
        output,
        checkpoint,
    )

    print()
    print(
        "=" * 90
    )
    print(
        "RECOVERY COMPLETE"
    )
    print(
        "=" * 90
    )

    print(
        f"metrics: "
        f"{len(metrics)}"
    )

    print(
        f"traces:  "
        f"{traces['trace_count']}"
    )

    print(
        f"logs:    "
        f"{logs['total_logs']}"
    )

    print()
    print(
        "checkpoint:"
    )
    print(
        output
    )


if __name__ == "__main__":
    main()
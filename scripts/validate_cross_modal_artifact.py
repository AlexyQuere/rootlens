from __future__ import annotations

import argparse
import json

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


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
            "Timestamp must be "
            "timezone-aware."
        )

    return result


def require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise ValueError(
            f"{name} must be "
            "a mapping."
        )

    return value


def require_list(
    value: Any,
    name: str,
) -> list:
    if not isinstance(
        value,
        list,
    ):
        raise ValueError(
            f"{name} must be "
            "a list."
        )

    return value


def validate_phase(
    *,
    phase_name: str,
    phase: Mapping[str, Any],
) -> dict[str, Any]:
    errors = []

    if (
        phase.get("phase")
        != phase_name
    ):
        errors.append(
            "phase field does not "
            "match artifact section"
        )

    window = require_mapping(
        phase.get("window"),
        f"{phase_name}.window",
    )

    start = parse_datetime(
        window["start"]
    )

    end = parse_datetime(
        window["end"]
    )

    expected_seconds = (
        window["seconds"]
    )

    actual_seconds = (
        end - start
    ).total_seconds()

    if abs(
        actual_seconds
        - expected_seconds
    ) > 0.001:
        errors.append(
            "window duration mismatch: "
            f"declared={expected_seconds}, "
            f"actual={actual_seconds}"
        )

    metrics = require_mapping(
        phase.get("metrics"),
        f"{phase_name}.metrics",
    )

    if not metrics:
        errors.append(
            "no metric evidence"
        )

    for key, metric_value in (
        metrics.items()
    ):
        metric = require_mapping(
            metric_value,
            (
                f"{phase_name}."
                f"metrics.{key}"
            ),
        )

        metric_window = (
            require_mapping(
                metric.get(
                    "window"
                ),
                (
                    f"{phase_name}."
                    f"metrics.{key}."
                    "window"
                ),
            )
        )

        metric_start = (
            parse_datetime(
                metric_window[
                    "start"
                ]
            )
        )

        metric_end = (
            parse_datetime(
                metric_window[
                    "end"
                ]
            )
        )

        if (
            metric_start != start
            or metric_end != end
        ):
            errors.append(
                "metric window mismatch: "
                f"{key}"
            )

    traces = require_mapping(
        phase.get("traces"),
        f"{phase_name}.traces",
    )

    trace_ids = require_list(
        traces.get("trace_ids"),
        (
            f"{phase_name}."
            "traces.trace_ids"
        ),
    )

    trace_count = traces.get(
        "trace_count"
    )

    if (
        trace_count
        != len(trace_ids)
    ):
        errors.append(
            "trace_count does not "
            "match trace_ids length"
        )

    if (
        len(set(trace_ids))
        != len(trace_ids)
    ):
        errors.append(
            "duplicate trace IDs"
        )

    trace_start = (
        parse_datetime(
            traces["start"]
        )
    )

    trace_end = (
        parse_datetime(
            traces["end"]
        )
    )

    if (
        trace_start != start
        or trace_end != end
    ):
        errors.append(
            "trace search window "
            "does not match "
            "analytical window"
        )

    logs = require_mapping(
        phase.get("logs"),
        f"{phase_name}.logs",
    )

    log_start = (
        parse_datetime(
            logs[
                "analytical_start"
            ]
        )
    )

    log_end = (
        parse_datetime(
            logs[
                "analytical_end"
            ]
        )
    )

    if (
        log_start != start
        or log_end != end
    ):
        errors.append(
            "log analytical window "
            "does not match "
            "phase window"
        )

    log_trace_count = (
        logs.get(
            "trace_count"
        )
    )

    if (
        log_trace_count
        != len(trace_ids)
    ):
        errors.append(
            "log trace_count does not "
            "match Jaeger trace_count"
        )

    trace_results = (
        require_list(
            logs.get("traces"),
            (
                f"{phase_name}."
                "logs.traces"
            ),
        )
    )

    if (
        len(trace_results)
        != len(trace_ids)
    ):
        errors.append(
            "number of per-trace log "
            "results differs from "
            "Jaeger trace count"
        )

    expected_trace_ids = set(
        trace_ids
    )

    seen_log_trace_ids = set()

    total_logs = 0
    unmatched_log_trace_ids = 0

    for index, trace_result_value in (
        enumerate(
            trace_results
        )
    ):
        trace_result = (
            require_mapping(
                trace_result_value,
                (
                    f"{phase_name}."
                    f"logs.traces[{index}]"
                ),
            )
        )

        trace_id = trace_result.get(
            "trace_id"
        )

        if trace_id not in (
            expected_trace_ids
        ):
            errors.append(
                "log query references "
                "unknown trace_id: "
                f"{trace_id}"
            )

        if trace_id in (
            seen_log_trace_ids
        ):
            errors.append(
                "duplicate per-trace "
                "log result: "
                f"{trace_id}"
            )

        seen_log_trace_ids.add(
            trace_id
        )

        returned_logs = (
            trace_result.get(
                "returned_logs"
            )
        )

        total_hits = (
            trace_result.get(
                "total_hits"
            )
        )

        raw_logs = require_list(
            trace_result.get(
                "logs"
            ),
            (
                f"{phase_name}."
                f"logs.traces[{index}]"
                ".logs"
            ),
        )

        if (
            returned_logs
            != len(raw_logs)
        ):
            errors.append(
                "returned_logs mismatch "
                f"for trace {trace_id}"
            )

        if (
            total_hits
            != returned_logs
        ):
            errors.append(
                "possible log truncation "
                f"for trace {trace_id}: "
                f"hits={total_hits}, "
                f"returned={returned_logs}"
            )

        total_logs += len(
            raw_logs
        )

        for raw_log in raw_logs:
            log = require_mapping(
                raw_log,
                "log",
            )

            if (
                log.get("trace_id")
                != trace_id
            ):
                unmatched_log_trace_ids += 1

    if (
        logs.get("total_logs")
        != total_logs
    ):
        errors.append(
            "total_logs does not match "
            "sum of per-trace logs"
        )

    if unmatched_log_trace_ids:
        errors.append(
            "logs whose trace_id differs "
            "from the trace query: "
            f"{unmatched_log_trace_ids}"
        )

    acquisition = require_mapping(
        phase.get("acquisition"),
        (
            f"{phase_name}."
            "acquisition"
        ),
    )

    return {
        "phase":
            phase_name,

        "start":
            start.isoformat(),

        "end":
            end.isoformat(),

        "metric_count":
            len(metrics),

        "trace_count":
            len(trace_ids),

        "log_count":
            total_logs,

        "historical_recovery":
            bool(
                acquisition.get(
                    "recovered",
                    False,
                )
            ),

        "errors":
            errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "artifact",
    )

    args = parser.parse_args()

    path = Path(
        args.artifact
    )

    artifact = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if (
        artifact.get(
            "experiment"
        )
        != "015D"
    ):
        raise ValueError(
            "Not an Experiment "
            "015D artifact."
        )

    baseline = validate_phase(
        phase_name="baseline",
        phase=require_mapping(
            artifact.get(
                "baseline"
            ),
            "baseline",
        ),
    )

    incident = validate_phase(
        phase_name="incident",
        phase=require_mapping(
            artifact.get(
                "incident"
            ),
            "incident",
        ),
    )

    print(
        "=" * 90
    )
    print(
        "ROOTLENS 015D — "
        "CROSS-MODAL ARTIFACT "
        "VALIDATION"
    )
    print(
        "=" * 90
    )

    print(
        f"scenario: "
        f"{artifact.get('scenario')}"
    )

    for result in (
        baseline,
        incident,
    ):
        print()
        print(
            result[
                "phase"
            ].upper()
        )

        print(
            "  window:"
        )
        print(
            "    "
            f"{result['start']}"
        )
        print(
            "    "
            f"{result['end']}"
        )

        print(
            "  metrics: "
            f"{result['metric_count']}"
        )

        print(
            "  traces:  "
            f"{result['trace_count']}"
        )

        print(
            "  logs:    "
            f"{result['log_count']}"
        )

        print(
            "  historical recovery: "
            f"{result['historical_recovery']}"
        )

        if result[
            "errors"
        ]:
            print(
                "  status: INVALID"
            )

            for error in (
                result[
                    "errors"
                ]
            ):
                print(
                    f"    - {error}"
                )

        else:
            print(
                "  status: VALID"
            )

    print()
    print(
        "METRIC SIGNALS"
    )

    for key in (
        "checkout_error_rate",
        "checkout_payment_error_rate",
        "frontend_http_error_rate",
    ):
        baseline_metric = (
            artifact[
                "baseline"
            ][
                "metrics"
            ].get(
                key
            )
        )

        incident_metric = (
            artifact[
                "incident"
            ][
                "metrics"
            ].get(
                key
            )
        )

        if (
            baseline_metric is None
            or incident_metric is None
        ):
            continue

        baseline_value = (
            baseline_metric[
                "value"
            ]
        )

        incident_value = (
            incident_metric[
                "value"
            ]
        )

        print(
            f"  {key:<32} "
            f"{baseline_value:.6f}"
            " -> "
            f"{incident_value:.6f}"
        )

    errors = (
        baseline["errors"]
        + incident["errors"]
    )

    print()

    if errors:
        raise SystemExit(
            "VALIDATION FAILED"
        )

    print(
        "VALIDATION PASSED"
    )


if __name__ == "__main__":
    main()
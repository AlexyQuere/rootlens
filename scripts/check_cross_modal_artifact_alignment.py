from __future__ import annotations

import argparse

from rootlens.evaluation.cross_modal_artifacts import (
    common_time_window,
    load_log_artifact,
    load_metric_artifact,
    load_trace_artifact,
)


def print_window(
    name,
    evidence,
):
    print(
        f"{name:<10}"
        f"{evidence.start.isoformat()}"
        " -> "
        f"{evidence.end.isoformat()}"
    )


def main():
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--metrics",
        required=True,
    )

    parser.add_argument(
        "--traces",
        required=True,
    )

    parser.add_argument(
        "--logs",
        required=True,
    )

    parser.add_argument(
        "--phase",
        choices=(
            "baseline",
            "incident",
        ),
        default="incident",
    )

    args = parser.parse_args()

    metrics = (
        load_metric_artifact(
            args.metrics
        )
    )

    traces = (
        load_trace_artifact(
            args.traces,

            phase=args.phase,
        )
    )

    logs = (
        load_log_artifact(
            args.logs,

            phase=args.phase,
        )
    )

    print(
        "=" * 90
    )

    print(
        "ROOTLENS 015D "
        "CROSS-MODAL ALIGNMENT"
    )

    print(
        "=" * 90
    )

    print(
        f"metrics scenario: "
        f"{metrics.scenario}"
    )

    print(
        f"traces scenario:  "
        f"{traces.scenario}"
    )

    print(
        f"logs scenario:    "
        f"{logs.scenario}"
    )

    print()

    print_window(
        "metrics",
        metrics,
    )

    print_window(
        "traces",
        traces,
    )

    print_window(
        "logs",
        logs,
    )

    print()

    common = common_time_window(
        metrics,
        traces,
        logs,
    )

    if common is None:
        print(
            "RESULT: NOT TEMPORALLY "
            "COMPATIBLE"
        )

        print()

        print(
            "These artifacts came "
            "from different runs."
        )

        print(
            "They must not be merged "
            "into one incident bundle."
        )

        return

    print(
        "RESULT: TEMPORALLY "
        "COMPATIBLE"
    )

    print(
        "common window:"
    )

    print(
        f"  {common.start.isoformat()}"
    )

    print(
        f"  {common.end.isoformat()}"
    )


if __name__ == "__main__":
    main()
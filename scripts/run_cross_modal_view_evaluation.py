from __future__ import annotations

import argparse

from rootlens.evaluation.synced_cross_modal import (
    load_synced_incident_evidence,
)


def enum_text(
    value,
) -> str:
    raw = getattr(
        value,
        "value",
        value,
    )

    return str(
        raw
    )


def metric_key(
    item,
) -> str:
    binding = getattr(
        item,
        "binding",
        None,
    )

    if binding is None:
        return "unknown"

    return str(
        getattr(
            binding,
            "metric_key",
            "unknown",
        )
    )


def metric_role(
    item,
) -> str:
    role = getattr(
        item,
        "role",
        None,
    )

    if role is None:
        return "unknown"

    return enum_text(
        role
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
    view = loaded.view

    print(
        "=" * 90
    )
    print(
        "ROOTLENS 015D — "
        "TYPED CROSS-MODAL VIEW"
    )
    print(
        "=" * 90
    )

    print(
        f"scenario: "
        f"{loaded.scenario}"
    )

    print(
        f"incident_id: "
        f"{bundle.incident_id}"
    )

    print(
        f"window: "
        f"{bundle.start.isoformat()}"
    )

    print(
        f"        "
        f"{bundle.end.isoformat()}"
    )

    print()

    print(
        "BUNDLE"
    )

    print(
        f"  metric comparisons: "
        f"{len(bundle.metrics)}"
    )

    print(
        f"  traces:             "
        f"{len(bundle.traces)}"
    )

    print(
        f"  logs:               "
        f"{len(bundle.logs)}"
    )

    print(
        f"  metric bindings:    "
        f"{len(loaded.metric_bindings)}"
    )

    print()

    print(
        "SERVICES"
    )

    for service in (
        view.services
    ):
        print()
        print(
            service.service_name
        )

        print(
            "  metrics: "
            f"{len(service.metrics)}"
        )

        for metric in (
            service.metrics
        ):
            print(
                "    "
                f"{metric_key(metric):<38} "
                f"role="
                f"{metric_role(metric)}"
            )

        print(
            "  traces:  "
            f"{len(service.trace_ids)}"
        )

        print(
            "  spans:   "
            f"{len(service.spans)}"
        )

        print(
            "  logs:    "
            f"{len(service.logs)}"
        )

        print(
            "  acquisition:"
        )

        print(
            "    metric="
            f"{service.metric_acquisition}"
        )

        print(
            "    trace="
            f"{service.trace_acquisition}"
        )

        print(
            "    log="
            f"{service.log_acquisition}"
        )

        print(
            "  integrity:"
        )

        print(
            "    "
            f"{service.integrity}"
        )

    print()
    print(
        "UNBOUND METRICS"
    )

    print(
        f"  {len(view.unbound_metrics)}"
    )

    print()
    print(
        "COVERAGE"
    )

    print(
        f"  {view.coverage}"
    )


if __name__ == "__main__":
    main()
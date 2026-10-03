from __future__ import annotations

import argparse
import json

from pathlib import Path

from rootlens.observability.jaeger import (
    JaegerTracePayload,
)

from rootlens.observability.otlp_trace import (
    parse_otlp_traces,
)


FEATURE_FLAG_EVENT = (
    "feature_flag.evaluation"
)


def load_trace(
    raw_trace: dict,
):

    payload = JaegerTracePayload(
        resource_spans=tuple(
            raw_trace[
                "resource_spans"
            ]
        )
    )

    traces = parse_otlp_traces(
        payload
    )

    trace_id = raw_trace[
        "trace_id"
    ]

    matching = [
        trace
        for trace in traces
        if trace.trace_id
        == trace_id
    ]

    if len(matching) != 1:
        raise ValueError(
            "Expected exactly one "
            f"trace for {trace_id}; "
            f"got {len(matching)}."
        )

    return matching[0]


def feature_flag_events(
    trace,
    *,
    flag_key: str,
):

    results = []

    for span in trace.spans:

        for event in span.events:

            if (
                event.name
                != FEATURE_FLAG_EVENT
            ):
                continue

            attributes = dict(
                event.attributes
            )

            observed_key = (
                attributes.get(
                    "feature_flag.key"
                )
            )

            if observed_key != flag_key:
                continue

            results.append(
                {
                    "trace_id":
                        trace.trace_id,

                    "span_id":
                        span.span_id,

                    "service_name":
                        span.service_name,

                    "operation_name":
                        span.operation_name,

                    "span_kind":
                        span.kind.name,

                    "span_status":
                        span.status_code.name,

                    "event_time":
                        event.time.isoformat(),

                    "attributes":
                        attributes,
                }
            )

    return results


def analyze_window(
    window: dict,
    *,
    flag_key: str,
) -> dict:

    events = []

    traces_without_event = []

    for raw_trace in window[
        "raw_traces"
    ]:

        trace = load_trace(
            raw_trace
        )

        trace_events = (
            feature_flag_events(
                trace,
                flag_key=flag_key,
            )
        )

        if not trace_events:

            traces_without_event.append(
                trace.trace_id
            )

        events.extend(
            trace_events
        )

    return {
        "trace_count":
            len(
                window[
                    "raw_traces"
                ]
            ),

        "event_count":
            len(events),

        "traces_without_event":
            traces_without_event,

        "events":
            events,
    }


def print_window(
    name: str,
    result: dict,
) -> None:

    print()
    print("=" * 90)
    print(name.upper())
    print("=" * 90)

    print(
        f"traces: "
        f"{result['trace_count']}"
    )

    print(
        f"matching flag events: "
        f"{result['event_count']}"
    )

    print(
        "traces without matching "
        "flag event: "
        f"{len(result['traces_without_event'])}"
    )

    print()

    for event in result[
        "events"
    ]:

        print(
            f"trace: "
            f"{event['trace_id']}"
        )

        print(
            f"  service: "
            f"{event['service_name']}"
        )

        print(
            f"  operation: "
            f"{event['operation_name']}"
        )

        print(
            f"  span status: "
            f"{event['span_status']}"
        )

        print(
            f"  event time: "
            f"{event['event_time']}"
        )

        print(
            "  attributes:"
        )

        for key, value in sorted(
            event[
                "attributes"
            ].items()
        ):

            print(
                f"    {key}: "
                f"{value!r}"
            )

        print()


def main() -> None:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--artifact",
        required=True,
    )

    parser.add_argument(
        "--flag",
        default=(
            "paymentUnreachable"
        ),
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

    baseline = analyze_window(
        artifact[
            "baseline"
        ],
        flag_key=args.flag,
    )

    incident = analyze_window(
        artifact[
            "incident"
        ],
        flag_key=args.flag,
    )

    print(
        f"Artifact: {path}"
    )

    print(
        f"Scenario: "
        f"{artifact['scenario']}"
    )

    print(
        f"Flag: {args.flag}"
    )

    print_window(
        "baseline",
        baseline,
    )

    print_window(
        "incident",
        incident,
    )


if __name__ == "__main__":
    main()
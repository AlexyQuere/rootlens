from __future__ import annotations

import argparse
import json
import os

from dataclasses import asdict
from datetime import (
    datetime,
    timedelta,
)
from pathlib import Path

from rootlens.evaluation.trace_incident import (
    ClientServerRelationSpec,
    observe_relation,
    summarize_observations,
)

from rootlens.observability.jaeger import (
    JaegerClient,
    JaegerError,
)

from rootlens.observability.otlp_trace import (
    parse_otlp_traces,
)

from rootlens.observability.trace_evidence import (
    SpanKind,
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


def parse_time(
    value: str,
) -> datetime:

    parsed = datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
        )
    )

    if (
        parsed.tzinfo is None
        or parsed.utcoffset()
        is None
    ):
        raise ValueError(
            "Timestamp must be "
            "timezone-aware."
        )

    return parsed


def trace_has_checkout_in_window(
    trace,
    *,
    start: datetime,
    end: datetime,
    tool: TraceInvestigationTool,
) -> bool:

    checkouts = tool.find_spans(
        trace,
        service_name="checkout",
        operation_name=(
            CHECKOUT_OPERATION
        ),
        kind=SpanKind.SERVER,
    )

    for span in checkouts:

        timestamp = span.start_time

        if (
            start
            <= timestamp
            <= end
        ):
            return True

    return False


def evaluate_window(
    *,
    client: JaegerClient,
    tool: TraceInvestigationTool,
    start: datetime,
    end: datetime,
    max_traces: int,
):

    search_payload = (
        client.find_traces(
            service_name="checkout",
            start=start,
            end=end,
            num_traces=max_traces,
        )
    )

    search_traces = (
        parse_otlp_traces(
            search_payload
        )
    )

    trace_ids = tuple(
        sorted(
            {
                trace.trace_id
                for trace
                in search_traces
            }
        )
    )

    relation_spec = (
        ClientServerRelationSpec(
            client_service="checkout",
            client_operation=(
                PAYMENT_OPERATION
            ),
            server_service="payment",
            server_operation=(
                PAYMENT_OPERATION
            ),
        )
    )

    observations = []

    fetch_errors = []

    excluded_no_checkout = []

    for trace_id in trace_ids:

        try:

            payload = (
                client.get_trace(
                    trace_id
                )
            )

            traces = (
                parse_otlp_traces(
                    payload
                )
            )

        except JaegerError as exc:

            fetch_errors.append(
                {
                    "trace_id":
                        trace_id,

                    "error":
                        str(exc),
                }
            )

            continue

        matching = [
            trace
            for trace in traces
            if (
                trace.trace_id
                == trace_id
            )
        ]

        if len(matching) != 1:

            fetch_errors.append(
                {
                    "trace_id":
                        trace_id,

                    "error":
                        (
                            "Expected exactly "
                            "one fetched trace; "
                            f"got {len(matching)}."
                        ),
                }
            )

            continue

        trace = matching[0]

        if not trace_has_checkout_in_window(
            trace,
            start=start,
            end=end,
            tool=tool,
        ):

            excluded_no_checkout.append(
                trace_id
            )

            continue

        observation = observe_relation(
            trace,
            spec=relation_spec,
            tool=tool,
        )

        observations.append(
            observation
        )

    observations_tuple = tuple(
        observations
    )

    summary = (
        summarize_observations(
            observations_tuple
        )
    )

    return {
        "start":
            start.isoformat(),

        "end":
            end.isoformat(),

        "searched_trace_ids":
            len(trace_ids),

        "fetched_checkout_traces":
            len(
                observations_tuple
            ),

        "fetch_errors":
            fetch_errors,

        "excluded_no_checkout":
            excluded_no_checkout,

        "summary":
            asdict(
                summary
            ),

        "observations": [
            asdict(
                observation
            )
            for observation
            in observations_tuple
        ],
    }


def print_window(
    name: str,
    data: dict,
) -> None:

    print()
    print("=" * 90)
    print(name.upper())
    print("=" * 90)

    print(
        "window: "
        f"{data['start']} -> "
        f"{data['end']}"
    )

    print(
        "searched trace IDs: "
        f"{data['searched_trace_ids']}"
    )

    print(
        "checkout traces: "
        f"{data['fetched_checkout_traces']}"
    )

    print(
        "fetch errors: "
        f"{len(data['fetch_errors'])}"
    )

    summary = data[
        "summary"
    ]

    print(
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
            f"{classification:<38}"
            f"{count}"
        )

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

    print()
    print(
        "PER TRACE"
    )

    for observation in data[
        "observations"
    ]:

        print(
            f"  "
            f"{observation['trace_id']}  "
            f"{observation['classification']}"
        )

        if any(
            observation[
                "client_status_messages"
            ]
        ):

            print(
                "    client messages: "
                f"{observation['client_status_messages']}"
            )

        if any(
            observation[
                "server_status_messages"
            ]
        ):

            print(
                "    server messages: "
                f"{observation['server_status_messages']}"
            )


def main() -> None:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scenario",
        required=True,
    )

    parser.add_argument(
        "--baseline-end",
        required=True,
    )

    parser.add_argument(
        "--incident-end",
        required=True,
    )

    parser.add_argument(
        "--window-seconds",
        type=int,
        default=300,
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

    baseline_end = parse_time(
        args.baseline_end
    )

    incident_end = parse_time(
        args.incident_end
    )

    baseline_start = (
        baseline_end
        - timedelta(
            seconds=(
                args.window_seconds
            )
        )
    )

    incident_start = (
        incident_end
        - timedelta(
            seconds=(
                args.window_seconds
            )
        )
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

    baseline = evaluate_window(
        client=client,
        tool=tool,
        start=baseline_start,
        end=baseline_end,
        max_traces=args.max_traces,
    )

    incident = evaluate_window(
        client=client,
        tool=tool,
        start=incident_start,
        end=incident_end,
        max_traces=args.max_traces,
    )

    artifact = {
        "experiment":
            "015B.4",

        "scenario":
            args.scenario,

        "window_seconds":
            args.window_seconds,

        "jaeger_url":
            jaeger_url,

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
            incident,
    }

    output = Path(
        args.output
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            artifact,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"Scenario: "
        f"{args.scenario}"
    )

    print_window(
        "baseline",
        baseline,
    )

    print_window(
        "incident",
        incident,
    )

    print()
    print(
        f"Frozen artifact: "
        f"{output}"
    )


if __name__ == "__main__":
    main()
from __future__ import annotations

import os

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from rootlens.observability.jaeger import (
    JaegerClient,
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


FLAG_EVENT = "feature_flag.evaluation"

CHECKOUT_OPERATION = (
    "oteldemo.CheckoutService/"
    "PlaceOrder"
)

PAYMENT_OPERATION = (
    "oteldemo.PaymentService/"
    "Charge"
)


def main() -> None:

    client = JaegerClient(
        os.getenv(
            "ROOTLENS_JAEGER_URL",
            "http://localhost:8080",
        )
    )

    tool = TraceInvestigationTool()

    end = datetime.now(
        timezone.utc
    )

    start = (
        end
        - timedelta(
            minutes=5
        )
    )

    payload = client.find_traces(
        service_name="checkout",
        operation_name=(
            CHECKOUT_OPERATION
        ),
        start=start,
        end=end,
        num_traces=20,
    )

    traces = parse_otlp_traces(
        payload
    )

    if not traces:
        raise RuntimeError(
            "No Checkout traces found."
        )

    candidates = []

    for trace in traces:

        checkout_spans = (
            tool.find_spans(
                trace,
                service_name=(
                    "checkout"
                ),
                operation_name=(
                    CHECKOUT_OPERATION
                ),
                kind=SpanKind.SERVER,
            )
        )

        if not checkout_spans:
            continue

        latest_checkout = max(
            checkout_spans,
            key=lambda span:
                span.start_time_unix_nano,
        )

        candidates.append(
            (
                latest_checkout
                .start_time_unix_nano,
                trace.trace_id,
            )
        )

    if not candidates:
        raise RuntimeError(
            "No Checkout PlaceOrder "
            "span found."
        )

    _, trace_id = max(
        candidates
    )

    full_payload = (
        client.get_trace(
            trace_id
        )
    )

    parsed = parse_otlp_traces(
        full_payload
    )

    matching = [
        trace
        for trace in parsed
        if trace.trace_id
        == trace_id
    ]

    if len(matching) != 1:
        raise RuntimeError(
            "Expected one trace."
        )

    trace = matching[0]

    checkout_spans = (
        tool.find_spans(
            trace,
            service_name="checkout",
            operation_name=(
                CHECKOUT_OPERATION
            ),
            kind=SpanKind.SERVER,
        )
    )

    payment_clients = (
        tool.find_spans(
            trace,
            service_name="checkout",
            operation_name=(
                PAYMENT_OPERATION
            ),
            kind=SpanKind.CLIENT,
        )
    )

    payment_servers = (
        tool.find_spans(
            trace,
            service_name="payment",
            operation_name=(
                PAYMENT_OPERATION
            ),
            kind=SpanKind.SERVER,
        )
    )

    print(
        f"trace_id: {trace.trace_id}"
    )

    print()

    print(
        "FEATURE FLAG EVENTS"
    )

    for span in checkout_spans:

        for event in span.events:

            if (
                event.name
                != FLAG_EVENT
            ):
                continue

            attrs = dict(
                event.attributes
            )

            if (
                attrs.get(
                    "feature_flag.key"
                )
                != "paymentUnreachable"
            ):
                continue

            print(
                "  value: "
                f"{attrs.get('feature_flag.result.value')!r}"
            )

            print(
                "  variant: "
                f"{attrs.get('feature_flag.result.variant')!r}"
            )

            print(
                "  reason: "
                f"{attrs.get('feature_flag.result.reason')!r}"
            )

            print(
                "  provider: "
                f"{attrs.get('feature_flag.provider.name')!r}"
            )

    print()
    print(
        "CHECKOUT -> PAYMENT CLIENT"
    )

    if not payment_clients:

        print(
            "  not observed"
        )

    for span in payment_clients:

        print(
            f"  status: "
            f"{span.status_code.name}"
        )

        print(
            f"  message: "
            f"{span.status_message!r}"
        )

    print()
    print(
        "PAYMENT SERVER"
    )

    if not payment_servers:

        print(
            "  not observed"
        )

    for span in payment_servers:

        print(
            f"  status: "
            f"{span.status_code.name}"
        )

        print(
            f"  message: "
            f"{span.status_message!r}"
        )


if __name__ == "__main__":
    main()
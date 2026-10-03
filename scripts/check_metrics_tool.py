from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from rootlens.observability.evidence import (
    TimeWindow,
)

from rootlens.observability.metrics import (
    MetricUnavailableError,
    MetricsTool,
)

from rootlens.observability.prometheus import (
    PrometheusClient,
)


def show(
    title,
    function,
):

    print()
    print(
        f"=== {title} ==="
    )

    try:
        evidence = function()

    except MetricUnavailableError as exc:
        print(
            f"Unavailable: {exc}"
        )
        return

    if isinstance(
        evidence,
        tuple,
    ):
        for item in evidence:
            print(
                f"{item.statistic}: "
                f"{item.value:.6f} "
                f"{item.unit}"
            )
            print(
                f"PromQL: "
                f"{item.promql}"
            )

    else:
        print(
            f"{evidence.statistic}: "
            f"{evidence.value:.6f} "
            f"{evidence.unit}"
        )
        print(
            f"PromQL: "
            f"{evidence.promql}"
        )


def main() -> None:

    client = PrometheusClient(
        "http://localhost:9090"
    )

    metrics = MetricsTool(
        client
    )

    end = datetime.now(
        timezone.utc
    )

    window = TimeWindow(
        start=(
            end
            - timedelta(
                minutes=5
            )
        ),
        end=end,
    )

    show(
        "Checkout PlaceOrder request rate",
        lambda:
            metrics.request_rate(
                family="rpc_server",
                service="checkout",
                operation=(
                    "oteldemo."
                    "CheckoutService/"
                    "PlaceOrder"
                ),
                window=window,
            ),
    )

    show(
        "Checkout PlaceOrder error rate",
        lambda:
            metrics.error_rate(
                family="rpc_server",
                service="checkout",
                operation=(
                    "oteldemo."
                    "CheckoutService/"
                    "PlaceOrder"
                ),
                window=window,
            ),
    )

    show(
        "Checkout PlaceOrder latency",
        lambda:
            metrics.latency_quantiles(
                family="rpc_server",
                service="checkout",
                operation=(
                    "oteldemo."
                    "CheckoutService/"
                    "PlaceOrder"
                ),
                window=window,
            ),
    )

    show(
        "Checkout -> Payment request rate",
        lambda:
            metrics.request_rate(
                family="rpc_client",
                service="checkout",
                operation=(
                    "oteldemo."
                    "PaymentService/"
                    "Charge"
                ),
                window=window,
            ),
    )

    show(
        "Checkout -> Payment error rate",
        lambda:
            metrics.error_rate(
                family="rpc_client",
                service="checkout",
                operation=(
                    "oteldemo."
                    "PaymentService/"
                    "Charge"
                ),
                window=window,
            ),
    )

    show(
        "Frontend HTTP error rate",
        lambda:
            metrics.error_rate(
                family="http_server",
                service="frontend",
                window=window,
            ),
    )


if __name__ == "__main__":
    main()
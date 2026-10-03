from rootlens.observability.prometheus import (
    PrometheusClient,
)


def main() -> None:

    client = PrometheusClient(
        "http://localhost:9090"
    )

    result = client.query(
        "up"
    )

    print(
        f"Series returned: "
        f"{len(result)}"
    )

    for sample in result:

        print(
            sample
        )


if __name__ == "__main__":
    main()
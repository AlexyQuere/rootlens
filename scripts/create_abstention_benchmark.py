from __future__ import annotations

import json

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_DIR = (
    ROOT
    / "data"
    / "benchmark_v2"
)

EVALUATION_DIR = (
    ROOT
    / "data"
    / "evaluation"
)

QUERIES_FILE = (
    BENCHMARK_DIR
    / "abstention_queries_v1.json"
)

GOLD_FILE = (
    EVALUATION_DIR
    / "abstention_gold_v1.json"
)


CASES = [
    #
    # ------------------------------------------------
    # Pair 1 — Payment responsibility / DB version
    # ------------------------------------------------
    #
    {
        "query_id": "abs-001",
        "pair_id": "payment_database",
        "variant": "answerable",
        "query": (
            "Which service is responsible for "
            "charging the customer during checkout?"
        ),
        "expected_status": "answered",
        "supported_component": (
            "PaymentService is responsible for "
            "charging the customer during checkout."
        ),
        "missing_component": None,
        "expected_sources": [
            "payment-service.md",
        ],
    },
    {
        "query_id": "abs-002",
        "pair_id": "payment_database",
        "variant": "partial",
        "query": (
            "Which service is responsible for "
            "charging the customer during checkout, "
            "and which PostgreSQL version does it "
            "use in production?"
        ),
        "expected_status": "partial",
        "supported_component": (
            "PaymentService is responsible for "
            "charging the customer."
        ),
        "missing_component": (
            "The PostgreSQL version used in "
            "production is not described."
        ),
        "expected_sources": [
            "payment-service.md",
        ],
    },
    {
        "query_id": "abs-003",
        "pair_id": "payment_database",
        "variant": "unanswerable",
        "query": (
            "Which PostgreSQL version does "
            "PaymentService use in production?"
        ),
        "expected_status": "abstained",
        "supported_component": None,
        "missing_component": (
            "The corpus does not specify a "
            "PostgreSQL version."
        ),
        "expected_sources": [],
    },

    #
    # ------------------------------------------------
    # Pair 2 — Metrics / production region
    # ------------------------------------------------
    #
    {
        "query_id": "abs-004",
        "pair_id": "metrics_region",
        "variant": "answerable",
        "query": (
            "Which observability signal should be "
            "used to detect and quantify an increase "
            "in checkout error rate?"
        ),
        "expected_status": "answered",
        "supported_component": (
            "Metrics are used for detection and "
            "quantification of checkout degradation."
        ),
        "missing_component": None,
        "expected_sources": [
            "metrics-guide.md",
            "observability-guide.md",
        ],
    },
    {
        "query_id": "abs-005",
        "pair_id": "metrics_region",
        "variant": "partial",
        "query": (
            "Which observability signal should be "
            "used to detect and quantify an increase "
            "in checkout error rate, and which "
            "production cloud region hosts the system?"
        ),
        "expected_status": "partial",
        "supported_component": (
            "Metrics are appropriate for detecting "
            "and quantifying the degradation."
        ),
        "missing_component": (
            "The production cloud region is not "
            "specified."
        ),
        "expected_sources": [
            "metrics-guide.md",
            "observability-guide.md",
        ],
    },
    {
        "query_id": "abs-006",
        "pair_id": "metrics_region",
        "variant": "unanswerable",
        "query": (
            "Which production cloud region "
            "hosts the checkout system?"
        ),
        "expected_status": "abstained",
        "supported_component": None,
        "missing_component": (
            "The corpus does not specify a "
            "production cloud region."
        ),
        "expected_sources": [],
    },

    #
    # ------------------------------------------------
    # Pair 3 — Trace evidence / on-call
    # ------------------------------------------------
    #
    {
        "query_id": "abs-007",
        "pair_id": "trace_oncall",
        "variant": "answerable",
        "query": (
            "A failing client span has no matching "
            "downstream server span. What should "
            "I investigate?"
        ),
        "expected_status": "answered",
        "supported_component": (
            "Investigate failures occurring before "
            "the downstream application handled "
            "the request, including resolution, "
            "discovery, endpoint, or connectivity "
            "problems."
        ),
        "missing_component": None,
        "expected_sources": [
            "grpc-troubleshooting.md",
            "service-discovery.md",
            "payment-runbook.md",
        ],
    },
    {
        "query_id": "abs-008",
        "pair_id": "trace_oncall",
        "variant": "partial",
        "query": (
            "A failing client span has no matching "
            "downstream server span. What should "
            "I investigate, and who is the current "
            "on-call engineer?"
        ),
        "expected_status": "partial",
        "supported_component": (
            "The missing server span supports "
            "investigating pre-service failures."
        ),
        "missing_component": (
            "The current on-call engineer is not "
            "specified."
        ),
        "expected_sources": [
            "grpc-troubleshooting.md",
            "service-discovery.md",
            "payment-runbook.md",
        ],
    },
    {
        "query_id": "abs-009",
        "pair_id": "trace_oncall",
        "variant": "unanswerable",
        "query": (
            "Who is the current on-call engineer "
            "for checkout incidents?"
        ),
        "expected_status": "abstained",
        "supported_component": None,
        "missing_component": (
            "The corpus does not identify a "
            "current on-call engineer."
        ),
        "expected_sources": [],
    },

    #
    # ------------------------------------------------
    # Pair 4 — Shipping / replicas
    # ------------------------------------------------
    #
    {
        "query_id": "abs-010",
        "pair_id": "shipping_replicas",
        "variant": "answerable",
        "query": (
            "What role does the Shipping service "
            "play in checkout before payment "
            "is completed?"
        ),
        "expected_status": "answered",
        "supported_component": (
            "Shipping calculates delivery quotes "
            "and participates before payment "
            "is completed."
        ),
        "missing_component": None,
        "expected_sources": [
            "shipping-service.md",
        ],
    },
    {
        "query_id": "abs-011",
        "pair_id": "shipping_replicas",
        "variant": "partial",
        "query": (
            "What role does the Shipping service "
            "play in checkout before payment is "
            "completed, and how many Kubernetes "
            "replicas does it run in production?"
        ),
        "expected_status": "partial",
        "supported_component": (
            "Shipping calculates delivery quotes "
            "before payment completes."
        ),
        "missing_component": (
            "The production Kubernetes replica "
            "count is not specified."
        ),
        "expected_sources": [
            "shipping-service.md",
        ],
    },
    {
        "query_id": "abs-012",
        "pair_id": "shipping_replicas",
        "variant": "unanswerable",
        "query": (
            "How many Kubernetes replicas does "
            "the Shipping service run in production?"
        ),
        "expected_status": "abstained",
        "supported_component": None,
        "missing_component": (
            "The corpus does not specify "
            "Kubernetes replica counts."
        ),
        "expected_sources": [],
    },

    #
    # ------------------------------------------------
    # Pair 5 — Deadline / TLS expiry
    # ------------------------------------------------
    #
    {
        "query_id": "abs-013",
        "pair_id": "deadline_tls",
        "variant": "answerable",
        "query": (
            "What does DEADLINE_EXCEEDED tell me, "
            "and what does it not establish about "
            "the underlying root cause?"
        ),
        "expected_status": "answered",
        "supported_component": (
            "DEADLINE_EXCEEDED indicates a deadline "
            "was exceeded but does not by itself "
            "identify the underlying cause."
        ),
        "missing_component": None,
        "expected_sources": [
            "timeout-and-retry-guidance.md",
            "grpc-troubleshooting.md",
            "latency-troubleshooting.md",
        ],
    },
    {
        "query_id": "abs-014",
        "pair_id": "deadline_tls",
        "variant": "partial",
        "query": (
            "What does DEADLINE_EXCEEDED tell me "
            "about the request, and when does the "
            "production TLS certificate expire?"
        ),
        "expected_status": "partial",
        "supported_component": (
            "The meaning and limitations of "
            "DEADLINE_EXCEEDED are documented."
        ),
        "missing_component": (
            "The TLS certificate expiration date "
            "is not specified."
        ),
        "expected_sources": [
            "timeout-and-retry-guidance.md",
            "grpc-troubleshooting.md",
        ],
    },
    {
        "query_id": "abs-015",
        "pair_id": "deadline_tls",
        "variant": "unanswerable",
        "query": (
            "When does the production TLS "
            "certificate expire?"
        ),
        "expected_status": "abstained",
        "supported_component": None,
        "missing_component": (
            "The corpus contains no production "
            "TLS certificate expiry information."
        ),
        "expected_sources": [],
    },

    #
    # ------------------------------------------------
    # Pair 6 — Currency / CPU limit
    # ------------------------------------------------
    #
    {
        "query_id": "abs-016",
        "pair_id": "currency_cpu",
        "variant": "answerable",
        "query": (
            "What is the Currency service "
            "responsible for during checkout?"
        ),
        "expected_status": "answered",
        "supported_component": (
            "CurrencyService converts monetary "
            "values between currencies."
        ),
        "missing_component": None,
        "expected_sources": [
            "currency-service.md",
        ],
    },
    {
        "query_id": "abs-017",
        "pair_id": "currency_cpu",
        "variant": "partial",
        "query": (
            "What is the Currency service "
            "responsible for during checkout, "
            "and what CPU limit is configured "
            "for it in production?"
        ),
        "expected_status": "partial",
        "supported_component": (
            "CurrencyService converts monetary "
            "values."
        ),
        "missing_component": (
            "The production CPU limit is not "
            "specified."
        ),
        "expected_sources": [
            "currency-service.md",
        ],
    },
    {
        "query_id": "abs-018",
        "pair_id": "currency_cpu",
        "variant": "unanswerable",
        "query": (
            "What CPU limit is configured for "
            "CurrencyService in production?"
        ),
        "expected_status": "abstained",
        "supported_component": None,
        "missing_component": (
            "The corpus does not specify "
            "CPU limits."
        ),
        "expected_sources": [],
    },
]


def main() -> None:

    EVALUATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    query_items = []

    gold_items = []

    seen_ids = set()

    for case in CASES:

        query_id = (
            case[
                "query_id"
            ]
        )

        if query_id in seen_ids:
            raise RuntimeError(
                "Duplicate query_id: "
                f"{query_id}"
            )

        seen_ids.add(
            query_id
        )

        query_items.append(
            {
                "query_id":
                    query_id,

                "pair_id":
                    case[
                        "pair_id"
                    ],

                "variant":
                    case[
                        "variant"
                    ],

                "query":
                    case[
                        "query"
                    ],
            }
        )

        gold_items.append(
            {
                "query_id":
                    query_id,

                "expected_status":
                    case[
                        "expected_status"
                    ],

                "supported_component":
                    case[
                        "supported_component"
                    ],

                "missing_component":
                    case[
                        "missing_component"
                    ],

                "expected_sources":
                    case[
                        "expected_sources"
                    ],
            }
        )

    queries = {
        "metadata": {
            "version":
                "v1",

            "experiment":
                "014D",

            "design":
                "6 matched status triplets",

            "gold_labels_included":
                False,
        },

        "queries":
            query_items,
    }

    gold = {
        "metadata": {
            "version":
                "v1",

            "experiment":
                "014D",

            "classes": [
                "answered",
                "partial",
                "abstained",
            ],

            "class_balance": {
                "answered": 6,
                "partial": 6,
                "abstained": 6,
            },

            "absence_audit":
                (
                    "Unknown components were selected "
                    "from corpus-wide abstention "
                    "candidate audit results."
                ),
        },

        "gold":
            gold_items,
    }

    QUERIES_FILE.write_text(
        json.dumps(
            queries,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    GOLD_FILE.write_text(
        json.dumps(
            gold,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        "Experiment 014D benchmark created"
    )

    print(
        f"Queries: {len(query_items)}"
    )

    print(
        "  answered: 6"
    )

    print(
        "  partial: 6"
    )

    print(
        "  abstained: 6"
    )

    print()

    print(
        "Generation file:"
    )

    print(
        QUERIES_FILE
    )

    print()

    print(
        "Hidden gold file:"
    )

    print(
        GOLD_FILE
    )


if __name__ == "__main__":
    main()
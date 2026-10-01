from __future__ import annotations

import re

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

KNOWLEDGE_DIR = (
    ROOT
    / "data"
    / "benchmark_v2"
    / "knowledge"
)


CANDIDATES = {
    "postgresql_version": [
        r"\bpostgres",
        r"\bpostgresql",
        r"\bdatabase version",
    ],

    "production_cloud_region": [
        r"\baws\b",
        r"\bgcp\b",
        r"\bazure\b",
        r"\bcloud region",
        r"\bproduction region",
        r"\beu-west",
        r"\bus-east",
    ],

    "on_call_engineer": [
        r"\bon[- ]call",
        r"\bphone number",
        r"\bcontact person",
        r"\bengineer name",
    ],

    "kubernetes_replica_count": [
        r"\bkubernetes",
        r"\breplica",
        r"\breplicas",
        r"\bdeployment count",
    ],

    "tls_certificate_expiry": [
        r"\btls\b",
        r"\bcertificate",
        r"\bcert expiry",
        r"\bexpiration date",
    ],

    "database_retention": [
        r"\bretention",
        r"\bdata retention",
        r"\bdatabase retention",
    ],

    "payment_hostname": [
        r"\bhostname",
        r"\bhost name",
        r"\bpayment.*\.internal",
        r"\bpayment.*\.local",
    ],

    "cpu_limit": [
        r"\bcpu limit",
        r"\bcpu request",
        r"\bmillicpu",
        r"\bmCPU\b",
    ],

    "memory_limit": [
        r"\bmemory limit",
        r"\bmemory request",
        r"\bMiB\b",
        r"\bGiB\b",
    ],

    "deployment_timestamp": [
        r"\bdeployment time",
        r"\bdeployed at",
        r"\bdeployment timestamp",
        r"\blast deployment",
    ],
}


def load_documents() -> dict[str, str]:

    documents = {}

    for path in sorted(
        KNOWLEDGE_DIR.glob(
            "*.md"
        )
    ):

        documents[
            path.name
        ] = (
            path.read_text(
                encoding="utf-8"
            )
        )

    if not documents:
        raise RuntimeError(
            "No knowledge documents found."
        )

    return documents


def main() -> None:

    documents = load_documents()

    print(
        "Experiment 014D — "
        "Abstention Candidate Audit"
    )

    print(
        f"Documents: {len(documents)}"
    )

    print()

    clean_candidates = []

    for candidate, patterns in (
        CANDIDATES.items()
    ):

        matches = []

        for source_id, text in (
            documents.items()
        ):

            for pattern in patterns:

                match = re.search(
                    pattern,
                    text,
                    flags=re.IGNORECASE,
                )

                if match is not None:

                    start = max(
                        0,
                        match.start() - 80,
                    )

                    end = min(
                        len(text),
                        match.end() + 120,
                    )

                    snippet = (
                        text[
                            start:end
                        ]
                        .replace(
                            "\n",
                            " ",
                        )
                    )

                    matches.append(
                        {
                            "source":
                                source_id,

                            "pattern":
                                pattern,

                            "snippet":
                                snippet,
                        }
                    )

        print(
            "=" * 80
        )

        print(
            candidate
        )

        if not matches:

            print(
                "  NO lexical matches"
            )

            clean_candidates.append(
                candidate
            )

            continue

        print(
            f"  Matches: "
            f"{len(matches)}"
        )

        for result in matches:

            print(
                f"  - "
                f"{result['source']}"
            )

            print(
                f"    pattern: "
                f"{result['pattern']}"
            )

            print(
                f"    {result['snippet']}"
            )

    print()
    print(
        "=" * 80
    )

    print(
        "Candidates with no "
        "lexical corpus match:"
    )

    for candidate in clean_candidates:

        print(
            f"  - {candidate}"
        )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "No lexical match is evidence "
        "for absence, not a formal proof "
        "of semantic absence."
    )

    print(
        "Candidate facts must still be "
        "chosen so that they cannot be "
        "reasonably inferred from other "
        "corpus content."
    )


if __name__ == "__main__":
    main()
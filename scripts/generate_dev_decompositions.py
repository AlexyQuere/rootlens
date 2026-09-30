import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from rootlens.llm.provider import (
    OpenAICompatibleLLM,
)
from rootlens.retrieval.query_decomposer import (
    LLMQueryDecomposer,
)


ROOT = Path(__file__).resolve().parents[1]

load_dotenv(
    ROOT / ".env"
)


DEV_FILE = (
    ROOT
    / "data"
    / "benchmark_v2"
    / "dev_queries.json"
)

OUTPUT_FILE = (
    ROOT
    / "data"
    / "benchmark_v2"
    / "dev_decompositions_v3.json"
)


MAX_DECOMPOSITIONS = 3


def require_env(
    name: str,
) -> str:

    value = os.getenv(
        name
    )

    if not value:
        raise RuntimeError(
            f"Missing environment "
            f"variable: {name}"
        )

    return value


def build_metadata(
    model: str,
    base_url: str,
) -> dict:

    return {
        "prompt_version":
            LLMQueryDecomposer
            .PROMPT_VERSION,

        "model":
            model,

        "base_url":
            base_url,

        "max_decompositions":
            MAX_DECOMPOSITIONS,
    }


def save_checkpoint(
    items: list[dict],
    model: str,
    base_url: str,
) -> None:

    output = {
        "metadata":
            build_metadata(
                model=model,
                base_url=base_url,
            ),

        "items":
            items,
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def validate_existing_file(
    existing: dict,
    model: str,
    base_url: str,
) -> None:

    metadata = existing.get(
        "metadata",
        {}
    )

    expected = build_metadata(
        model=model,
        base_url=base_url,
    )

    for key in (
        "prompt_version",
        "model",
        "base_url",
        "max_decompositions",
    ):

        actual_value = (
            metadata.get(
                key
            )
        )

        expected_value = (
            expected[
                key
            ]
        )

        if (
            actual_value
            != expected_value
        ):
            raise RuntimeError(
                "Existing decomposition "
                "file is incompatible with "
                "the current generation "
                "configuration.\n"
                f"Field: {key}\n"
                f"Existing: {actual_value!r}\n"
                f"Expected: {expected_value!r}\n\n"
                "Use a new output file or "
                "remove the incompatible "
                "file before regenerating."
            )


def main() -> None:

    queries = json.loads(
        DEV_FILE.read_text(
            encoding="utf-8"
        )
    )

    base_url = require_env(
        "ROOTLENS_LLM_BASE_URL"
    )

    api_key = require_env(
        "ROOTLENS_LLM_API_KEY"
    )

    model = require_env(
        "ROOTLENS_LLM_MODEL"
    )

    provider = (
        OpenAICompatibleLLM(
            base_url=base_url,
            api_key=api_key,
            model=model,
        )
    )

    decomposer = (
        LLMQueryDecomposer(
            provider
        )
    )

    #
    # Resume only if the frozen file
    # was generated with the exact same
    # configuration.
    #
    if OUTPUT_FILE.exists():

        existing = json.loads(
            OUTPUT_FILE.read_text(
                encoding="utf-8"
            )
        )

        validate_existing_file(
            existing=existing,
            model=model,
            base_url=base_url,
        )

        items = existing.get(
            "items",
            []
        )

        completed_ids = {
            item["query_id"]
            for item in items
        }

        print(
            f"Resuming with "
            f"{len(completed_ids)} "
            f"queries already completed."
        )

    else:

        items = []
        completed_ids = set()

    #
    # Generate decompositions.
    #
    for index, example in enumerate(
        queries,
        start=1,
    ):

        query_id = (
            example[
                "query_id"
            ]
        )

        query = (
            example[
                "query"
            ]
        )

        if (
            query_id
            in completed_ids
        ):

            print(
                f"[{index}/{len(queries)}] "
                f"{query_id} "
                "(already completed)"
            )

            continue

        print(
            f"[{index}/{len(queries)}] "
            f"{query_id}",
            flush=True,
        )

        start = (
            time.perf_counter()
        )

        decompositions = (
            decomposer.decompose(
                query,
                n=MAX_DECOMPOSITIONS,
            )
        )

        latency_ms = (
            time.perf_counter()
            - start
        ) * 1000.0

        for decomposition in (
            decompositions
        ):

            print(
                f"  - {decomposition}",
                flush=True,
            )

        print(
            "  "
            f"num_decompositions="
            f"{len(decompositions)}",
            flush=True,
        )

        print(
            "  "
            f"latency="
            f"{latency_ms:.1f} ms",
            flush=True,
        )

        items.append(
            {
                "query_id":
                    query_id,

                "query":
                    query,

                "decompositions":
                    decompositions,

                "num_decompositions":
                    len(
                        decompositions
                    ),

                "prompt_version":
                    LLMQueryDecomposer
                    .PROMPT_VERSION,

                "latency_ms":
                    latency_ms,
            }
        )

        #
        # Persist immediately so the
        # generation can safely resume.
        #
        save_checkpoint(
            items=items,
            model=model,
            base_url=base_url,
        )

        completed_ids.add(
            query_id
        )

    #
    # Final write.
    #
    save_checkpoint(
        items=items,
        model=model,
        base_url=base_url,
    )

    print()
    print(
        "Saved frozen decompositions "
        "to:"
    )

    print(
        OUTPUT_FILE
    )

    print()

    counts = [
        item[
            "num_decompositions"
        ]
        for item in items
    ]

    if counts:

        print(
            "Decomposition statistics:"
        )

        print(
            "  queries="
            f"{len(counts)}"
        )

        print(
            "  total_subqueries="
            f"{sum(counts)}"
        )

        print(
            "  mean_subqueries="
            f"{sum(counts) / len(counts):.2f}"
        )

        for n in range(
            1,
            MAX_DECOMPOSITIONS + 1,
        ):

            count = sum(
                value == n
                for value in counts
            )

            print(
                f"  queries_with_{n}_"
                f"subqueries="
                f"{count}"
            )


if __name__ == "__main__":
    main()
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

from rootlens.llm.provider import (
    OpenAICompatibleLLM,
)
from rootlens.retrieval.query_rewriter import (
    LLMQueryRewriter,
)

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]

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
    / "dev_rewrites_v1.json"
)

NUM_REWRITES = 3


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

def save_checkpoint(
    items: list[dict],
    model: str,
    base_url: str,
) -> None:

    output = {
        "metadata": {
            "prompt_version":
                LLMQueryRewriter
                .PROMPT_VERSION,
            "model":
                model,
            "base_url":
                base_url,
            "num_rewrites":
                NUM_REWRITES,
        },
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

    rewriter = (
        LLMQueryRewriter(
            provider
        )
    )

    if OUTPUT_FILE.exists():

        existing = json.loads(
            OUTPUT_FILE.read_text(
                encoding="utf-8"
            )
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

    for index, example in enumerate(
        queries,
        start=1,
    ):
        if (
            example["query_id"]
            in completed_ids
        ):
            print(
                f"[{index}/{len(queries)}] "
                f"{example['query_id']} "
                f"(already completed)"
            )

            continue

        print(
            f"[{index}/{len(queries)}] "
            f"{example['query_id']}",
            flush=True,
        )

        start = (
            time.perf_counter()
        )

        rewrites = (
            rewriter.rewrite(
                example["query"],
                n=NUM_REWRITES,
            )
        )

        latency_ms = (
            time.perf_counter()
            - start
        ) * 1000.0

        for rewrite in rewrites:
            print(
                f"  - {rewrite}",
                flush=True,
            )

        print(
            f"  latency="
            f"{latency_ms:.1f} ms",
            flush=True,
        )

        items.append(
            {
                "query_id":
                    example[
                        "query_id"
                    ],
                "query":
                    example[
                        "query"
                    ],
                "rewrites":
                    rewrites,
                "latency_ms":
                    latency_ms,
            }
        )

        save_checkpoint(
            items=items,
            model=model,
            base_url=base_url,
        )

    output = {
        "metadata": {
            "prompt_version":
                LLMQueryRewriter
                .PROMPT_VERSION,
            "model":
                model,
            "base_url":
                base_url,
            "num_rewrites":
                NUM_REWRITES,
        },
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

    print()
    print(
        f"Saved frozen rewrites to "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
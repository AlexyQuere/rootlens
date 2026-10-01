from __future__ import annotations

import hashlib
import json
import os
import time

from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from rootlens.evaluation.grounding_judge import (
    GroundingJudge,
)
from rootlens.llm.provider import (
    OpenAICompatibleLLM,
)


ROOT = Path(__file__).resolve().parents[1]

load_dotenv(
    ROOT / ".env"
)


EVALUATION_DIR = (
    ROOT
    / "data"
    / "evaluation"
)

BENCHMARK_DIR = (
    ROOT
    / "data"
    / "benchmark_v2"
)

ANNOTATION_FILE = (
    EVALUATION_DIR
    / "rag_grounding_dev_v1.json"
)

RAG_OUTPUTS_FILE = (
    BENCHMARK_DIR
    / "dev_rag_outputs_v1.json"
)

OUTPUT_FILE = (
    EVALUATION_DIR
    / "rag_grounding_judge_dev_v1.json"
)


def require_env(
    name: str,
) -> str:

    value = os.getenv(
        name
    )

    if not value:
        raise RuntimeError(
            "Missing environment "
            f"variable: {name}"
        )

    return value


def optional_env(
    judge_name: str,
    fallback_name: str,
) -> str:

    value = os.getenv(
        judge_name
    )

    if value:
        return value

    return require_env(
        fallback_name
    )


def load_json(
    path: Path,
):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def file_sha256(
    path: Path,
) -> str:

    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def build_metadata(
    judge_model: str,
    judge_base_url: str,
    generator_model: str | None,
) -> dict:

    return {
        "version":
            "v1",

        "judge_prompt_version":
            GroundingJudge
            .PROMPT_VERSION,

        "input_file":
            ANNOTATION_FILE.name,

        "input_sha256":
            file_sha256(
                ANNOTATION_FILE
            ),

        "judge_model":
            judge_model,

        "judge_base_url":
            judge_base_url,

        "generator_model":
            generator_model,

        "same_model_as_generator":
            (
                generator_model
                == judge_model
                if generator_model
                is not None
                else None
            ),

        "qrels_visible_to_judge":
            False,

        "evaluation_level":
            "claim",

        "labels": [
            "full",
            "partial",
            "none",
        ],
    }


def validate_existing_output(
    existing: dict,
    expected_metadata: dict,
) -> None:

    metadata = existing.get(
        "metadata",
        {}
    )

    fields = (
        "version",
        "judge_prompt_version",
        "input_file",
        "input_sha256",
        "judge_model",
        "judge_base_url",
        "generator_model",
        "same_model_as_generator",
        "qrels_visible_to_judge",
        "evaluation_level",
    )

    for field in fields:

        if (
            metadata.get(
                field
            )
            != expected_metadata.get(
                field
            )
        ):
            raise RuntimeError(
                "Existing grounding judge "
                "artifact is incompatible "
                "with the current run.\n"
                f"Field: {field}\n"
                f"Existing: "
                f"{metadata.get(field)!r}\n"
                f"Expected: "
                f"{expected_metadata.get(field)!r}"
            )


def save_checkpoint(
    metadata: dict,
    items: list[dict],
) -> None:

    output = {
        "metadata":
            metadata,

        "items":
            items,
    }

    temporary_file = (
        OUTPUT_FILE.with_suffix(
            ".json.tmp"
        )
    )

    temporary_file.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    temporary_file.replace(
        OUTPUT_FILE
    )


def annotation_id(
    annotation: dict,
) -> str:

    return (
        f"{annotation['query_id']}"
        f":claim-"
        f"{annotation['claim_index']:02d}"
    )


def get_generator_model() -> str | None:

    if not RAG_OUTPUTS_FILE.exists():
        return None

    frozen = load_json(
        RAG_OUTPUTS_FILE
    )

    metadata = frozen.get(
        "metadata",
        {}
    )

    model = metadata.get(
        "llm_model"
    )

    if (
        isinstance(
            model,
            str,
        )
        and model
    ):
        return model

    return None


def main() -> None:

    if not ANNOTATION_FILE.exists():
        raise FileNotFoundError(
            "Grounding annotation file "
            "does not exist: "
            f"{ANNOTATION_FILE}"
        )

    annotation_data = load_json(
        ANNOTATION_FILE
    )

    annotations = annotation_data.get(
        "annotations",
        []
    )

    if not annotations:
        raise RuntimeError(
            "No claims found in "
            "grounding annotation file."
        )

    judge_base_url = optional_env(
        "ROOTLENS_JUDGE_BASE_URL",
        "ROOTLENS_LLM_BASE_URL",
    )

    judge_api_key = optional_env(
        "ROOTLENS_JUDGE_API_KEY",
        "ROOTLENS_LLM_API_KEY",
    )

    judge_model = optional_env(
        "ROOTLENS_JUDGE_MODEL",
        "ROOTLENS_LLM_MODEL",
    )

    generator_model = (
        get_generator_model()
    )

    metadata = build_metadata(
        judge_model=judge_model,
        judge_base_url=(
            judge_base_url
        ),
        generator_model=(
            generator_model
        ),
    )

    provider = (
        OpenAICompatibleLLM(
            base_url=(
                judge_base_url
            ),
            api_key=(
                judge_api_key
            ),
            model=(
                judge_model
            ),
        )
    )

    judge = GroundingJudge(
        provider=provider,
        max_schema_retries=1,
    )

    if OUTPUT_FILE.exists():

        existing = load_json(
            OUTPUT_FILE
        )

        validate_existing_output(
            existing=existing,
            expected_metadata=(
                metadata
            ),
        )

        items = existing.get(
            "items",
            []
        )

        completed_ids = {
            item[
                "annotation_id"
            ]
            for item
            in items
        }

        print(
            "Resuming with "
            f"{len(completed_ids)} "
            "claims already judged."
        )

    else:

        items = []
        completed_ids = set()

    print()
    print(
        "Experiment 014C — "
        "Claim-Level Grounding Judge"
    )

    print(
        "Claims: "
        f"{len(annotations)}"
    )

    print(
        "Judge model: "
        f"{judge_model}"
    )

    print(
        "Generator model: "
        f"{generator_model}"
    )

    print(
        "Same model as generator: "
        f"{metadata['same_model_as_generator']}"
    )

    print(
        "Qrels visible to judge: False"
    )

    print()

    for index, annotation in enumerate(
        annotations,
        start=1,
    ):

        item_id = annotation_id(
            annotation
        )

        if item_id in completed_ids:

            print(
                f"[{index}/"
                f"{len(annotations)}] "
                f"{item_id} "
                "(already completed)"
            )

            continue

        cited_evidence = [
            (
                citation[
                    "source_id"
                ],
                citation[
                    "source_text"
                ],
            )
            for citation
            in annotation[
                "citations"
            ]
        ]

        print(
            f"[{index}/"
            f"{len(annotations)}] "
            f"{item_id}"
        )

        print(
            "  claim: "
            f"{annotation['claim']}"
        )

        print(
            "  sources: "
            + ", ".join(
                source_id
                for source_id, _
                in cited_evidence
            )
        )

        start = (
            time.perf_counter()
        )

        judgment = judge.judge(
            question=(
                annotation[
                    "query"
                ]
            ),
            claim=(
                annotation[
                    "claim"
                ]
            ),
            cited_evidence=(
                cited_evidence
            ),
        )

        latency_ms = (
            time.perf_counter()
            - start
        ) * 1000.0

        print(
            "  label: "
            f"{judgment.label}"
        )

        print(
            "  supporting_sources: "
            + (
                ", ".join(
                    judgment
                    .supporting_sources
                )
                if judgment
                .supporting_sources
                else "[]"
            )
        )

        if (
            judgment.unsupported_part
            is not None
        ):

            print(
                "  unsupported_part: "
                f"{judgment.unsupported_part}"
            )

        print(
            "  rationale: "
            f"{judgment.rationale}"
        )

        print(
            "  generation_attempts: "
            f"{judgment.generation_attempts}"
        )

        print(
            "  latency_ms: "
            f"{latency_ms:.1f}"
        )

        item = {
            "annotation_id":
                item_id,

            "query_id":
                annotation[
                    "query_id"
                ],

            "claim_index":
                annotation[
                    "claim_index"
                ],

            "category":
                annotation[
                    "category"
                ],

            "query":
                annotation[
                    "query"
                ],

            "claim":
                annotation[
                    "claim"
                ],

            "cited_sources": [
                source_id
                for source_id, _
                in cited_evidence
            ],

            "judgment": {
                "label":
                    judgment.label,

                "supporting_sources":
                    list(
                        judgment
                        .supporting_sources
                    ),

                "unsupported_part":
                    judgment
                    .unsupported_part,

                "rationale":
                    judgment
                    .rationale,
            },

            "generation_attempts":
                judgment
                .generation_attempts,

            "latency_ms":
                latency_ms,

            "raw_model_output":
                judgment
                .raw_model_output,
        }

        items.append(
            item
        )

        completed_ids.add(
            item_id
        )

        save_checkpoint(
            metadata=metadata,
            items=items,
        )

        print()

    save_checkpoint(
        metadata=metadata,
        items=items,
    )

    label_counts = Counter(
        item[
            "judgment"
        ][
            "label"
        ]
        for item in items
    )

    retry_count = sum(
        item[
            "generation_attempts"
        ]
        > 1
        for item in items
    )

    mean_attempts = (
        sum(
            item[
                "generation_attempts"
            ]
            for item in items
        )
        / len(items)
    )

    mean_latency = (
        sum(
            item[
                "latency_ms"
            ]
            for item in items
        )
        / len(items)
    )

    print()
    print(
        "=== Grounding Judge Summary ==="
    )

    print(
        f"Claims judged: "
        f"{len(items)}"
    )

    print(
        f"Full: "
        f"{label_counts['full']}"
    )

    print(
        f"Partial: "
        f"{label_counts['partial']}"
    )

    print(
        f"None: "
        f"{label_counts['none']}"
    )

    print(
        "Full support rate: "
        f"{label_counts['full'] / len(items):.4f}"
    )

    print(
        "Partial support rate: "
        f"{label_counts['partial'] / len(items):.4f}"
    )

    print(
        "Unsupported claim rate: "
        f"{label_counts['none'] / len(items):.4f}"
    )

    print(
        "Schema retries: "
        f"{retry_count}/"
        f"{len(items)}"
    )

    print(
        "Mean judge attempts: "
        f"{mean_attempts:.3f}"
    )

    print(
        "Mean judge latency_ms: "
        f"{mean_latency:.1f}"
    )

    print()

    print(
        "Saved frozen judge outputs to:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
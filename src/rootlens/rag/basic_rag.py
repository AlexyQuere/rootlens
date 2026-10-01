from __future__ import annotations

import json
import re

from dataclasses import dataclass
from typing import Literal
from typing import Mapping
from typing import Protocol

from rootlens.llm.provider import (
    LLMProvider,
)


AnswerStatus = Literal[
    "answered",
    "partial",
    "abstained",
]


class RAGOutputError(ValueError):
    """Base class for invalid LLM RAG outputs."""


class RAGSchemaError(RAGOutputError):
    """The LLM output violates the structured answer contract."""


class RAGCitationError(RAGOutputError):
    """The LLM cites evidence that was not retrieved."""


class Retriever(Protocol):

    def search(
        self,
        query: str,
        k: int,
    ) -> list[
        tuple[str, float]
    ]:
        ...


@dataclass(frozen=True)
class RetrievedEvidence:

    source_id: str
    content: str
    rank: int
    retrieval_score: float


@dataclass(frozen=True)
class GroundedClaim:

    text: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class GroundedAnswer:

    status: AnswerStatus

    claims: tuple[
        GroundedClaim,
        ...
    ]

    limitation: str | None


@dataclass(frozen=True)
class RAGResult:

    question: str

    evidence: tuple[
        RetrievedEvidence,
        ...
    ]

    answer: GroundedAnswer

    raw_model_output: str

    generation_attempts: int


class BasicGroundedRAG:

    PROMPT_VERSION = "v1"

    SCHEMA_RETRY_VERSION = "v1"

    VALID_STATUSES = {
        "answered",
        "partial",
        "abstained",
    }

    def __init__(
        self,
        documents: Mapping[
            str,
            str,
        ],
        retriever: Retriever,
        provider: LLMProvider,
        top_k: int = 5,
        max_schema_retries: int = 1,
    ) -> None:

        if top_k <= 0:
            raise ValueError(
                "top_k must be positive."
            )

        if max_schema_retries < 0:
            raise ValueError(
                "max_schema_retries "
                "cannot be negative."
            )

        if not documents:
            raise ValueError(
                "documents cannot be empty."
            )

        self.documents = dict(
            documents
        )

        self.retriever = retriever
        self.provider = provider
        self.top_k = top_k

        self.max_schema_retries = (
            max_schema_retries
        )

    def answer(
        self,
        question: str,
    ) -> RAGResult:

        question = (
            question.strip()
        )

        if not question:
            raise ValueError(
                "question cannot be empty."
            )

        #
        # Retrieval is performed once.
        #
        # If structured generation fails,
        # the retry receives exactly the
        # same evidence.
        #
        evidence = (
            self._retrieve(
                question
            )
        )

        context = (
            self._format_context(
                evidence
            )
        )

        allowed_sources = {
            item.source_id
            for item in evidence
        }

        previous_output = None
        previous_error = None

        total_attempts = (
            1
            + self.max_schema_retries
        )

        for attempt_index in range(
            total_attempts
        ):

            if attempt_index == 0:

                system_prompt = (
                    self._system_prompt()
                )

                user_prompt = (
                    self._user_prompt(
                        question=question,
                        context=context,
                    )
                )

            else:

                if (
                    previous_output is None
                    or previous_error is None
                ):
                    raise RuntimeError(
                        "Schema retry requested "
                        "without previous failure."
                    )

                system_prompt = (
                    self._schema_retry_system_prompt()
                )

                user_prompt = (
                    self._schema_retry_user_prompt(
                        question=question,
                        context=context,
                        previous_output=(
                            previous_output
                        ),
                        validation_error=(
                            str(
                                previous_error
                            )
                        ),
                    )
                )

            raw_output = (
                self.provider.generate(
                    system_prompt,
                    user_prompt,
                    max_tokens=768,
                    temperature=0.0,
                )
            )

            try:

                answer = (
                    self._parse_answer(
                        raw_output=raw_output,
                        allowed_sources=(
                            allowed_sources
                        ),
                    )
                )

            except RAGCitationError:

                #
                # Do not repair or regenerate an
                # invented citation.
                #
                # This is not a harmless schema
                # problem.
                #
                raise

            except RAGSchemaError as exc:

                previous_output = (
                    raw_output
                )

                previous_error = exc

                if (
                    attempt_index
                    >= self.max_schema_retries
                ):
                    raise

                continue

            return RAGResult(
                question=question,
                evidence=tuple(
                    evidence
                ),
                answer=answer,
                raw_model_output=(
                    raw_output
                ),
                generation_attempts=(
                    attempt_index + 1
                ),
            )

        raise RuntimeError(
            "Generation loop terminated "
            "unexpectedly."
        )

    def _retrieve(
        self,
        question: str,
    ) -> list[
        RetrievedEvidence
    ]:

        ranking = (
            self.retriever.search(
                question,
                k=self.top_k,
            )
        )

        if not ranking:
            raise RuntimeError(
                "Retriever returned "
                "no evidence."
            )

        evidence = []
        seen = set()

        for rank, (
            source_id,
            score,
        ) in enumerate(
            ranking,
            start=1,
        ):

            if source_id in seen:
                raise RuntimeError(
                    "Retriever returned "
                    "duplicate source: "
                    f"{source_id}"
                )

            seen.add(
                source_id
            )

            if source_id not in (
                self.documents
            ):
                raise RuntimeError(
                    "Retriever returned "
                    "unknown source: "
                    f"{source_id}"
                )

            content = (
                self.documents[
                    source_id
                ]
                .strip()
            )

            if not content:
                raise RuntimeError(
                    "Retrieved source "
                    "is empty: "
                    f"{source_id}"
                )

            evidence.append(
                RetrievedEvidence(
                    source_id=source_id,
                    content=content,
                    rank=rank,
                    retrieval_score=float(
                        score
                    ),
                )
            )

        return evidence

    @staticmethod
    def _format_context(
        evidence: list[
            RetrievedEvidence
        ],
    ) -> str:

        blocks = []

        for item in evidence:

            block = (
                f"[SOURCE: "
                f"{item.source_id}]\n"
                f"{item.content}\n"
                f"[/SOURCE]"
            )

            blocks.append(
                block
            )

        return "\n\n".join(
            blocks
        )

    @staticmethod
    def _system_prompt() -> str:

        return (
            "You are an evidence-grounded "
            "technical assistant.\n\n"

            "You must answer using ONLY the "
            "evidence explicitly provided in "
            "the context.\n\n"

            "Do not use external knowledge, "
            "prior assumptions, or facts that "
            "are not supported by the supplied "
            "evidence.\n\n"

            "Every factual claim must cite at "
            "least one source identifier from "
            "the provided evidence.\n\n"

            "A cited source must directly "
            "support the entire claim. "
            "Do not attach a source merely "
            "because it is related.\n\n"

            "Never invent a source identifier.\n\n"

            "If the supplied evidence only "
            "supports part of the requested "
            "answer, return status 'partial', "
            "include only supported claims, "
            "and explain what information is "
            "missing in 'limitation'.\n\n"

            "If the central question cannot "
            "be answered from the evidence, "
            "return status 'abstained', an "
            "empty claims list, and explain "
            "what evidence is missing.\n\n"

            "If the evidence fully supports "
            "the answer, return status "
            "'answered'.\n\n"

            "Return ONLY valid JSON using "
            "exactly this schema:\n\n"

            "{\n"
            '  "status": '
            '"answered | partial | abstained",\n'
            '  "claims": [\n'
            "    {\n"
            '      "text": "supported claim",\n'
            '      "sources": '
            '["source-id"]\n'
            "    }\n"
            "  ],\n"
            '  "limitation": '
            '"string or null"\n'
            "}\n"
        )

    @staticmethod
    def _user_prompt(
        question: str,
        context: str,
    ) -> str:

        return (
            "QUESTION\n"
            "--------\n"
            f"{question}\n\n"

            "EVIDENCE\n"
            "--------\n"
            f"{context}\n\n"

            "Produce the grounded "
            "structured answer."
        )

    @staticmethod
    def _schema_retry_system_prompt() -> str:

        return (
            "You are repairing a structured "
            "evidence-grounded answer that "
            "failed validation.\n\n"

            "Use ONLY the evidence supplied "
            "in this retry request.\n\n"

            "Do not use external knowledge.\n\n"

            "Do not invent source identifiers.\n\n"

            "Every claim MUST be a JSON object "
            "with exactly two fields:\n"
            '- "text": a non-empty string\n'
            '- "sources": a non-empty array '
            "of source identifiers that appear "
            "in the supplied evidence.\n\n"

            "If evidence does not support a "
            "claim, omit that claim.\n\n"

            "Return ONLY valid JSON using "
            "exactly this schema:\n\n"

            "{\n"
            '  "status": '
            '"answered | partial | abstained",\n'
            '  "claims": [\n'
            "    {\n"
            '      "text": "supported claim",\n'
            '      "sources": '
            '["source-id"]\n'
            "    }\n"
            "  ],\n"
            '  "limitation": '
            '"string or null"\n'
            "}\n"
        )

    @staticmethod
    def _schema_retry_user_prompt(
        question: str,
        context: str,
        previous_output: str,
        validation_error: str,
    ) -> str:

        return (
            "The previous answer violated "
            "the required output contract.\n\n"

            "VALIDATION ERROR\n"
            "----------------\n"
            f"{validation_error}\n\n"

            "QUESTION\n"
            "--------\n"
            f"{question}\n\n"

            "EVIDENCE\n"
            "--------\n"
            f"{context}\n\n"

            "PREVIOUS INVALID OUTPUT\n"
            "-----------------------\n"
            f"{previous_output}\n\n"

            "Regenerate the answer using the "
            "same evidence while respecting "
            "the required JSON schema."
        )

    @staticmethod
    def _normalize_source_id(
        source: str,
        allowed_sources: set[str],
    ) -> str:

        candidate = (
            source.strip()
        )

        #
        # Preferred canonical form.
        #
        if candidate in allowed_sources:
            return candidate

        #
        # Accept harmless formatting that
        # mirrors the context markers.
        #
        # Examples:
        #
        # SOURCE: payment-service.md
        # [SOURCE: payment-service.md]
        #
        match = re.fullmatch(
            (
                r"\[?\s*SOURCE\s*:\s*"
                r"([^\]]+?)\s*\]?"
            ),
            candidate,
            flags=re.IGNORECASE,
        )

        if match is not None:

            normalized = (
                match.group(1)
                .strip()
            )

            if normalized in (
                allowed_sources
            ):
                return normalized

        raise RAGCitationError(
            "Model cited source that "
            "was not retrieved: "
            f"{source!r}"
        )

    @classmethod
    def _parse_answer(
        cls,
        raw_output: str,
        allowed_sources: set[str],
    ) -> GroundedAnswer:

        data = (
            cls._parse_json(
                raw_output
            )
        )

        if not isinstance(
            data,
            dict,
        ):
            raise RAGSchemaError(
                "Model output must be "
                "a JSON object."
            )

        expected_keys = {
            "status",
            "claims",
            "limitation",
        }

        if set(data) != expected_keys:
            raise RAGSchemaError(
                "Model output must contain "
                "exactly the keys: "
                "status, claims, limitation."
            )

        status = data[
            "status"
        ]

        if status not in (
            cls.VALID_STATUSES
        ):
            raise RAGSchemaError(
                "Invalid answer status: "
                f"{status!r}"
            )

        raw_claims = data[
            "claims"
        ]

        if not isinstance(
            raw_claims,
            list,
        ):
            raise RAGSchemaError(
                "claims must be a list."
            )

        claims = []

        for raw_claim in raw_claims:

            if not isinstance(
                raw_claim,
                dict,
            ):
                raise RAGSchemaError(
                    "Each claim must be "
                    "a JSON object. "
                    "Received "
                    f"{type(raw_claim).__name__}: "
                    f"{raw_claim!r}"
                )

            if set(
                raw_claim
            ) != {
                "text",
                "sources",
            }:
                raise RAGSchemaError(
                    "Each claim must contain "
                    "exactly text and sources."
                )

            text = raw_claim[
                "text"
            ]

            sources = raw_claim[
                "sources"
            ]

            if (
                not isinstance(
                    text,
                    str,
                )
                or not text.strip()
            ):
                raise RAGSchemaError(
                    "Claim text must be "
                    "a non-empty string."
                )

            if (
                not isinstance(
                    sources,
                    list,
                )
                or not sources
            ):
                raise RAGSchemaError(
                    "Every claim must cite "
                    "at least one source."
                )

            if not all(
                isinstance(
                    source,
                    str,
                )
                and source.strip()
                for source
                in sources
            ):
                raise RAGSchemaError(
                    "Claim sources must be "
                    "non-empty strings."
                )

            normalized_sources = []

            for source in sources:

                normalized_source = (
                    cls._normalize_source_id(
                        source=source,
                        allowed_sources=(
                            allowed_sources
                        ),
                    )
                )

                normalized_sources.append(
                    normalized_source
                )

            unique_sources = tuple(
                dict.fromkeys(
                    normalized_sources
                )
            )

            claims.append(
                GroundedClaim(
                    text=text.strip(),
                    sources=(
                        unique_sources
                    ),
                )
            )

        limitation = data[
            "limitation"
        ]

        if (
            limitation is not None
            and not isinstance(
                limitation,
                str,
            )
        ):
            raise RAGSchemaError(
                "limitation must be "
                "a string or null."
            )

        if isinstance(
            limitation,
            str,
        ):

            limitation = (
                limitation.strip()
            )

            if not limitation:
                limitation = None

        cls._validate_status_contract(
            status=status,
            claims=claims,
            limitation=limitation,
        )

        return GroundedAnswer(
            status=status,
            claims=tuple(
                claims
            ),
            limitation=limitation,
        )

    @staticmethod
    def _validate_status_contract(
        status: AnswerStatus,
        claims: list[
            GroundedClaim
        ],
        limitation: str | None,
    ) -> None:

        if status == "answered":

            if not claims:
                raise RAGSchemaError(
                    "An answered response "
                    "must contain at least "
                    "one claim."
                )

            if limitation is not None:
                raise RAGSchemaError(
                    "An answered response "
                    "must not contain a "
                    "limitation."
                )

            return

        if status == "partial":

            if not claims:
                raise RAGSchemaError(
                    "A partial response must "
                    "contain at least one "
                    "supported claim."
                )

            if limitation is None:
                raise RAGSchemaError(
                    "A partial response must "
                    "explain the missing "
                    "evidence."
                )

            return

        if status == "abstained":

            if claims:
                raise RAGSchemaError(
                    "An abstained response "
                    "must not contain claims."
                )

            if limitation is None:
                raise RAGSchemaError(
                    "An abstained response "
                    "must explain why the "
                    "evidence is insufficient."
                )

            return

        raise RAGSchemaError(
            "Unsupported status: "
            f"{status}"
        )

    @staticmethod
    def _parse_json(
        raw_output: str,
    ):

        cleaned = (
            raw_output.strip()
        )

        if not cleaned:
            raise RAGSchemaError(
                "Model returned "
                "an empty response."
            )

        if cleaned.startswith(
            "```"
        ):

            cleaned = re.sub(
                r"^```(?:json)?\s*",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )

            cleaned = re.sub(
                r"\s*```$",
                "",
                cleaned,
            )

        start = cleaned.find(
            "{"
        )

        if start == -1:
            raise RAGSchemaError(
                "Model response does "
                "not contain JSON."
            )

        decoder = (
            json.JSONDecoder()
        )

        try:

            data, _ = (
                decoder.raw_decode(
                    cleaned[
                        start:
                    ]
                )
            )

        except json.JSONDecodeError as exc:

            raise RAGSchemaError(
                "Invalid JSON returned "
                "by model."
            ) from exc

        return data
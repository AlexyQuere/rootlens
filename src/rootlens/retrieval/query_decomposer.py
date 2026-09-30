from __future__ import annotations

import json
import re
from typing import Protocol

from rootlens.llm.provider import (
    LLMProvider,
)
from rootlens.retrieval.query_rewriter import (
    extract_identifiers,
)


class QueryDecomposer(Protocol):

    def decompose(
        self,
        query: str,
        n: int = 3,
    ) -> list[str]:
        ...


class LLMQueryDecomposer:

    PROMPT_VERSION = "v3"

    def __init__(
        self,
        provider: LLMProvider,
        max_attempts: int = 3,
    ) -> None:

        if max_attempts <= 0:
            raise ValueError(
                "max_attempts must be positive."
            )

        self.provider = provider
        self.max_attempts = max_attempts

    def decompose(
        self,
        query: str,
        n: int = 3,
    ) -> list[str]:

        if n <= 0:
            raise ValueError(
                "n must be positive."
            )

        last_reason = None

        for attempt in range(
            1,
            self.max_attempts + 1,
        ):

            raw = self._generate(
                query=query,
                n=n,
                attempt=attempt,
                feedback=last_reason,
            )

            try:
                candidates = (
                    self._parse_response(
                        raw
                    )
                )

            except ValueError as exc:
                last_reason = (
                    "invalid JSON output: "
                    f"{exc}"
                )
                continue

            candidates = (
                self._deduplicate(
                    candidates
                )
            )

            if not (
                1
                <= len(candidates)
                <= n
            ):
                last_reason = (
                    "expected between "
                    f"1 and {n} unique "
                    "subqueries, received "
                    f"{len(candidates)}"
                )
                continue

            if not self._preserves_identifiers(
                query,
                candidates,
            ):
                identifiers = (
                    extract_identifiers(
                        query
                    )
                )

                last_reason = (
                    "the required technical "
                    "identifiers were not "
                    "preserved: "
                    f"{identifiers}"
                )
                continue

            return candidates

        raise ValueError(
            "Could not generate a valid "
            "query decomposition after "
            f"{self.max_attempts} attempts. "
            "Last rejection reason: "
            f"{last_reason}"
        )


    def _generate(
        self,
        query: str,
        n: int,
        attempt: int,
        feedback: str | None = None,
    ) -> str:

        identifiers = (
            extract_identifiers(
                query
            )
        )

        if identifiers:
            identifier_instruction = (
                "\n\nThe following technical identifiers "
                "MUST appear verbatim at least once across "
                "the returned subqueries:\n"
                + "\n".join(
                    f"- {identifier}"
                    for identifier
                    in identifiers
                )
            )
        else:
            identifier_instruction = ""

        feedback_instruction = ""

        if feedback:
            feedback_instruction = (
                "\n\nThe previous attempt was rejected "
                f"because:\n{feedback}\n"
                "Correct that problem in this attempt."
            )

        system_prompt = (
            "You decompose technical search queries into "
            "complementary retrieval subqueries.\n\n"

            "A decomposition is NOT a list of paraphrases.\n"
            "Each subquery must represent a genuinely "
            "different information need that is already "
            "contained in the original query.\n\n"

            "Rules:\n"

            "1. Return between 1 and the requested maximum "
            "number of subqueries.\n"

            "2. If the original query is atomic, return "
            "ONE subquery only. Never invent artificial "
            "facets to reach the maximum.\n"

            "3. Split only information needs that are "
            "actually present in the original query.\n"

            "4. Do NOT introduce specific technologies, "
            "components, protocols, causes, metrics, logs, "
            "tools, infrastructure elements, payloads, "
            "error codes, or diagnostic procedures unless "
            "they are present or clearly required by the "
            "original query.\n"

            "5. Preserve contrast, negation and scope. "
            "Words and constructions such as 'rather than', "
            "'instead of', 'versus', 'without', 'before', "
            "'after', 'not', and 'no' are hard constraints. "
            "Never turn an explicitly excluded alternative "
            "into a retrieval goal.\n"

            "6. Prefer the terminology of the original "
            "query. Decomposition should narrow the query, "
            "not enrich it with domain assumptions.\n"

            "7. Do not answer the query.\n"

            "8. Together, the subqueries must preserve the "
            "complete original information need.\n"

            "9. Preserve required technical identifiers "
            "exactly.\n"

            "10. Return only a JSON array of strings.\n\n"

            "Examples:\n\n"

            "Atomic query:\n"
            "'Which service owns FooService/Bar?'\n"
            "Good decomposition:\n"
            '["Which service owns FooService/Bar?"]\n\n'

            "Comparative query:\n"
            "'How do ServiceA and ServiceB differ?'\n"
            "Good decomposition:\n"
            '["What are the responsibilities of ServiceA?", '
            '"What are the responsibilities of ServiceB?"]\n\n'

            "Contrastive query:\n"
            "'Which guide covers capacity monitoring rather "
            "than debugging one request?'\n"
            "Good decomposition:\n"
            '["Which guide covers capacity monitoring rather '
            'than single-request debugging?"]\n'
            "Do NOT create a subquery asking how to debug "
            "one request.\n\n"

            "Multi-stage query:\n"
            "'How should I investigate a latency increase "
            "from detection to request-level evidence?'\n"
            "Good decomposition:\n"
            '["Which evidence detects and quantifies the '
            'latency increase?", '
            '"Which evidence localizes where latency is '
            'introduced?", '
            '"Which request-level evidence explains the '
            'observed latency?"]'
        )

        user_prompt = (
            f"Original query:\n{query}\n\n"
            f"Generate between 1 and {n} complementary "
            "retrieval subqueries."
            f"{identifier_instruction}"
            f"{feedback_instruction}\n\n"
            "Use fewer subqueries whenever decomposition "
            "would otherwise create paraphrases or invent "
            "new information needs."
        )

        return self.provider.generate(
            system_prompt,
            user_prompt,
            max_tokens=384,
            temperature=0.0,
        )

    @staticmethod
    def _deduplicate(
        queries: list[str],
    ) -> list[str]:

        seen = set()
        result = []

        for query in queries:

            normalized = " ".join(
                query.lower().split()
            )

            if normalized in seen:
                continue

            seen.add(normalized)
            result.append(query)

        return result

    @staticmethod
    def _preserves_identifiers(
        original: str,
        subqueries: list[str],
    ) -> bool:

        identifiers = (
            extract_identifiers(
                original
            )
        )

        combined = "\n".join(
            subqueries
        )

        return all(
            identifier in combined
            for identifier
            in identifiers
        )

    @staticmethod
    def _parse_response(
        raw: str,
    ) -> list[str]:

        cleaned = raw.strip()

        if cleaned.startswith("```"):
            cleaned = re.sub(
                r"^```(?:json)?\s*",
                "",
                cleaned,
            )

            cleaned = re.sub(
                r"\s*```$",
                "",
                cleaned,
            )

        start = cleaned.find("[")

        if start == -1:
            raise ValueError(
                "LLM did not return "
                "a JSON array."
            )

        decoder = json.JSONDecoder()

        parsed, _ = decoder.raw_decode(
            cleaned[start:]
        )

        if not isinstance(
            parsed,
            list,
        ):
            raise ValueError(
                "Expected JSON list."
            )

        if not all(
            isinstance(item, str)
            for item in parsed
        ):
            raise ValueError(
                "Every subquery must "
                "be a string."
            )

        return [
            item.strip()
            for item in parsed
            if item.strip()
        ]

    


class StaticQueryDecomposer:

    def __init__(
        self,
        decompositions:
            dict[str, list[str]],
    ) -> None:

        self.decompositions = (
            decompositions
        )

    def decompose(
        self,
        query: str,
        n: int = 3,
    ) -> list[str]:

        if n <= 0:
            raise ValueError(
                "n must be positive."
            )

        if query not in (
            self.decompositions
        ):
            raise KeyError(
                f"No decomposition "
                f"for query: {query}"
            )

        subqueries = (
            self.decompositions[
                query
            ]
        )

        if not subqueries:
            raise ValueError(
                "Frozen decomposition "
                "cannot be empty."
            )

        return subqueries[:n]
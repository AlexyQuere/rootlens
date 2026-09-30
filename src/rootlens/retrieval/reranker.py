from __future__ import annotations

import math
import torch

from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
)
from typing import Protocol, Sequence

from sentence_transformers import CrossEncoder


class Reranker(Protocol):
    """Interface for query-document reranking models."""

    def score(
        self,
        query: str,
        documents: Sequence[str],
    ) -> list[float]:
        """Return one finite relevance score per document."""


class CrossEncoderReranker:
    """Cross-encoder reranker backed by Sentence Transformers.

    The model jointly encodes each (query, document) pair.

    Scores are ranking scores, not calibrated probabilities.
    """

    DEFAULT_MODEL_NAME = (
        "cross-encoder/ms-marco-MiniLM-L6-v2"
    )

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        device: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.device = device

        self.model = CrossEncoder(
            model_name,
            device=device,
        )

    def score(
        self,
        query: str,
        documents: Sequence[str],
    ) -> list[float]:
        if not documents:
            return []

        pairs = [
            (query, document)
            for document in documents
        ]

        raw_scores = self.model.predict(
            pairs,
            show_progress_bar=False,
        )

        scores = [
            float(score)
            for score in raw_scores
        ]

        invalid = [
            score
            for score in scores
            if not math.isfinite(score)
        ]

        if invalid:
            raise RuntimeError(
                "Cross-encoder produced non-finite "
                "scores. This makes reranking invalid. "
                f"model={self.model_name!r}, "
                f"device={self.device!r}. "
                "On Apple Silicon, "
                "cross-encoder/ms-marco-MiniLM-L6-v2 "
                "is known to produce NaN scores when "
                "forced to CPU in some environments. "
                "Try device='mps' or another reranker."
            )

        return scores


class BGEReranker:
    """BAAI BGE cross-encoder-style reranker.

    The model jointly scores a query-document pair using a
    sequence-classification model.

    Returned values are raw ranking logits, not calibrated
    probabilities or confidence scores.
    """

    DEFAULT_MODEL_NAME = (
        "BAAI/bge-reranker-base"
    )

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        device: str = "cpu",
        batch_size: int = 4,
        max_length: int = 512,
    ) -> None:
        if batch_size <= 0:
            raise ValueError(
                "batch_size must be strictly positive."
            )

        if max_length <= 0:
            raise ValueError(
                "max_length must be strictly positive."
            )

        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.max_length = max_length

        self.tokenizer = (
            AutoTokenizer.from_pretrained(
                model_name
            )
        )

        self.model = (
            AutoModelForSequenceClassification
            .from_pretrained(
                model_name
            )
        )

        self.model.to(
            self.device
        )

        self.model.eval()

    def score(
        self,
        query: str,
        documents,
    ) -> list[float]:
        if not documents:
            return []

        scores: list[float] = []

        for start in range(
            0,
            len(documents),
            self.batch_size,
        ):
            batch_documents = documents[
                start:
                start + self.batch_size
            ]

            pairs = [
                (
                    query,
                    document,
                )
                for document
                in batch_documents
            ]

            inputs = self.tokenizer(
                pairs,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            )

            inputs = {
                name: tensor.to(
                    self.device
                )
                for name, tensor
                in inputs.items()
            }

            with torch.inference_mode():
                outputs = self.model(
                    **inputs,
                    return_dict=True,
                )

            batch_scores = (
                outputs
                .logits
                .view(-1)
                .float()
                .detach()
                .cpu()
                .tolist()
            )

            scores.extend(
                float(score)
                for score
                in batch_scores
            )

        if len(scores) != len(documents):
            raise RuntimeError(
                "BGE reranker returned a different "
                "number of scores than documents."
            )

        invalid_scores = [
            score
            for score in scores
            if not math.isfinite(score)
        ]

        if invalid_scores:
            raise RuntimeError(
                "BGE reranker produced "
                "non-finite scores."
            )

        return scores
    

class RerankedRetriever:
    """Retrieve candidates, then rerank them with a slower model."""

    def __init__(
        self,
        candidate_retriever,
        documents: dict[str, str],
        reranker: Reranker,
        candidate_k: int = 10,
    ) -> None:
        if candidate_k <= 0:
            raise ValueError(
                "candidate_k must be strictly positive."
            )

        self.candidate_retriever = (
            candidate_retriever
        )
        self.documents = documents
        self.reranker = reranker
        self.candidate_k = candidate_k

    def search(
        self,
        query: str,
        k: int = 5,
    ) -> list[tuple[str, float]]:
        if k <= 0:
            raise ValueError(
                "k must be strictly positive."
            )

        candidates = (
            self.candidate_retriever.search(
                query,
                k=self.candidate_k,
            )
        )

        if not candidates:
            return []

        candidate_ids = [
            document_id
            for document_id, _
            in candidates
        ]

        candidate_texts = [
            self.documents[
                document_id
            ]
            for document_id
            in candidate_ids
        ]

        rerank_scores = (
            self.reranker.score(
                query,
                candidate_texts,
            )
        )

        if (
            len(rerank_scores)
            != len(candidate_ids)
        ):
            raise ValueError(
                "Reranker returned a different "
                "number of scores than candidates."
            )

        for score in rerank_scores:
            if not math.isfinite(score):
                raise RuntimeError(
                    "Reranker returned a non-finite score."
                )

        reranked = list(
            zip(
                candidate_ids,
                rerank_scores,
            )
        )

        reranked.sort(
            key=lambda item: (
                -item[1],
                item[0],
            )
        )

        return reranked[:k]

import pytest

from rootlens.evaluation.rag_metrics import (
    citation_qrel_precision,
    citation_qrel_recall,
    compute_query_rag_metrics,
    relevant_evidence_retention,
    retrieval_qrel_recall,
    validate_frozen_rag_item,
)


def test_retrieval_qrel_recall():

    relevant = {
        "a.md",
        "b.md",
    }

    retrieved = {
        "a.md",
        "c.md",
    }

    assert (
        retrieval_qrel_recall(
            retrieved,
            relevant,
        )
        == pytest.approx(
            0.5
        )
    )


def test_citation_qrel_precision():

    relevant = {
        "a.md",
        "b.md",
    }

    cited = {
        "a.md",
        "c.md",
    }

    assert (
        citation_qrel_precision(
            cited,
            relevant,
        )
        == pytest.approx(
            0.5
        )
    )


def test_citation_precision_is_none_without_citations():

    assert (
        citation_qrel_precision(
            set(),
            {
                "a.md",
            },
        )
        is None
    )


def test_citation_qrel_recall():

    relevant = {
        "a.md",
        "b.md",
    }

    cited = {
        "a.md",
    }

    assert (
        citation_qrel_recall(
            cited,
            relevant,
        )
        == pytest.approx(
            0.5
        )
    )


def test_relevant_evidence_retention():

    relevant = {
        "a.md",
        "b.md",
        "c.md",
    }

    retrieved = {
        "a.md",
        "b.md",
        "x.md",
    }

    cited = {
        "a.md",
    }

    assert (
        relevant_evidence_retention(
            retrieved,
            cited,
            relevant,
        )
        == pytest.approx(
            0.5
        )
    )


def test_compute_query_metrics():

    metrics = (
        compute_query_rag_metrics(
            relevance={
                "a.md": 2,
                "b.md": 1,
                "c.md": 0,
            },
            retrieved_source_ids=[
                "a.md",
                "c.md",
            ],
            claims=[
                {
                    "text":
                        "Claim one.",
                    "sources": [
                        "a.md",
                    ],
                },
                {
                    "text":
                        "Claim two.",
                    "sources": [
                        "c.md",
                    ],
                },
            ],
        )
    )

    assert (
        metrics.retrieval_qrel_recall
        == pytest.approx(
            0.5
        )
    )

    assert (
        metrics.citation_qrel_precision
        == pytest.approx(
            0.5
        )
    )

    assert (
        metrics.citation_qrel_recall
        == pytest.approx(
            0.5
        )
    )

    assert (
        metrics.source_utilization
        == pytest.approx(
            1.0
        )
    )

    assert (
        metrics.claim_count
        == 2
    )

    assert (
        metrics.mean_sources_per_claim
        == pytest.approx(
            1.0
        )
    )

    assert (
        metrics.missing_relevant_from_retrieval
        == (
            "b.md",
        )
    )

    assert (
        metrics.retrieved_relevant_not_cited
        == ()
    )

    assert (
        metrics.cited_qrel_irrelevant
        == (
            "c.md",
        )
    )


def test_validate_frozen_item_accepts_valid_answer():

    item = {
        "evidence": [
            {
                "source_id":
                    "a.md",
            }
        ],
        "answer": {
            "status":
                "answered",
            "claims": [
                {
                    "text":
                        "Supported claim.",
                    "sources": [
                        "a.md",
                    ],
                }
            ],
            "limitation":
                None,
        },
    }

    validate_frozen_rag_item(
        item
    )


def test_validate_frozen_item_rejects_unretrieved_source():

    item = {
        "evidence": [
            {
                "source_id":
                    "a.md",
            }
        ],
        "answer": {
            "status":
                "answered",
            "claims": [
                {
                    "text":
                        "Claim.",
                    "sources": [
                        "b.md",
                    ],
                }
            ],
            "limitation":
                None,
        },
    }

    with pytest.raises(
        ValueError,
        match="not retrieved",
    ):

        validate_frozen_rag_item(
            item
        )


def test_validate_frozen_abstention():

    item = {
        "evidence": [
            {
                "source_id":
                    "a.md",
            }
        ],
        "answer": {
            "status":
                "abstained",
            "claims": [],
            "limitation":
                "Evidence is insufficient.",
        },
    }

    validate_frozen_rag_item(
        item
    )
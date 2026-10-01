import pytest

from rootlens.evaluation.failure_attribution import (
    build_qrel_enriched_context,
    citation_qrel_recall,
    recovered_evidence_uptake,
)


def test_build_qrel_enriched_context():

    baseline = [
        "a.md",
        "x.md",
        "c.md",
        "y.md",
        "z.md",
    ]

    relevance = {
        "a.md": 2,
        "b.md": 2,
        "c.md": 1,
        "d.md": 1,
        "x.md": 0,
        "y.md": 0,
        "z.md": 0,
    }

    result = (
        build_qrel_enriched_context(
            baseline_ids=baseline,
            relevance=relevance,
            k=5,
        )
    )

    assert set(
        result.enriched_ids
    ) == {
        "a.md",
        "b.md",
        "c.md",
        "d.md",
        "x.md",
    }

    assert set(
        result.recovered_qrel_ids
    ) == {
        "b.md",
        "d.md",
    }

    assert set(
        result.dropped_baseline_ids
    ) == {
        "y.md",
        "z.md",
    }

    assert (
        result.omitted_positive_qrel_ids
        == ()
    )


def test_primary_qrels_are_prioritized():

    result = (
        build_qrel_enriched_context(
            baseline_ids=[
                "x.md",
                "y.md",
                "z.md",
            ],
            relevance={
                "primary.md": 2,
                "support-a.md": 1,
                "support-b.md": 1,
            },
            k=2,
        )
    )

    assert (
        result.enriched_ids[
            0
        ]
        == "primary.md"
    )

    assert len(
        result.enriched_ids
    ) == 2

    assert len(
        result.omitted_positive_qrel_ids
    ) == 1


def test_citation_qrel_recall():

    recall = (
        citation_qrel_recall(
            cited_sources={
                "a.md",
                "x.md",
            },
            relevance={
                "a.md": 2,
                "b.md": 1,
                "x.md": 0,
            },
        )
    )

    assert recall == pytest.approx(
        0.5
    )


def test_recovered_evidence_uptake():

    intervention = (
        build_qrel_enriched_context(
            baseline_ids=[
                "a.md",
                "x.md",
                "y.md",
            ],
            relevance={
                "a.md": 2,
                "b.md": 1,
            },
            k=3,
        )
    )

    uptake = (
        recovered_evidence_uptake(
            cited_sources={
                "a.md",
                "b.md",
            },
            intervention=(
                intervention
            ),
        )
    )

    assert uptake == pytest.approx(
        1.0
    )


def test_recovered_evidence_uptake_is_none_without_recovery():

    intervention = (
        build_qrel_enriched_context(
            baseline_ids=[
                "a.md",
                "b.md",
                "x.md",
            ],
            relevance={
                "a.md": 2,
                "b.md": 1,
            },
            k=3,
        )
    )

    assert (
        recovered_evidence_uptake(
            cited_sources={
                "a.md",
            },
            intervention=(
                intervention
            ),
        )
        is None
    )
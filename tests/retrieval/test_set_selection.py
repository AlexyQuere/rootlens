import pytest

from rootlens.retrieval.set_selection import (
    greedy_query_coverage,
    maximal_marginal_relevance,
    normalize_score_maps,
)


def test_normalization_maps_scores_to_zero_one():

    normalized = normalize_score_maps(
        [
            "a.md",
            "b.md",
        ],
        [
            {
                "a.md": 0.2,
                "b.md": 0.8,
            }
        ],
    )

    assert (
        normalized[0]["a.md"]
        == pytest.approx(0.0)
    )

    assert (
        normalized[0]["b.md"]
        == pytest.approx(1.0)
    )


def test_constant_score_map_has_no_discrimination():

    normalized = normalize_score_maps(
        [
            "a.md",
            "b.md",
        ],
        [
            {
                "a.md": 0.5,
                "b.md": 0.5,
            }
        ],
    )

    assert normalized[0] == {
        "a.md": 0.0,
        "b.md": 0.0,
    }


def test_query_coverage_selects_complementary_documents():

    candidates = [
        "metrics.md",
        "tracing.md",
        "generic.md",
    ]

    score_maps = [
        {
            "metrics.md": 1.0,
            "tracing.md": 0.0,
            "generic.md": 0.4,
        },
        {
            "metrics.md": 0.0,
            "tracing.md": 1.0,
            "generic.md": 0.4,
        },
    ]

    ranking = (
        greedy_query_coverage(
            candidates,
            score_maps,
            k=2,
        )
    )

    selected = [
        document_id
        for document_id, _
        in ranking
    ]

    assert selected == [
        "metrics.md",
        "tracing.md",
    ]


def test_mmr_avoids_near_duplicate():

    candidates = [
        "a.md",
        "b.md",
        "c.md",
        "irrelevant.md",
    ]

    score_maps = [
        {
            "a.md": 0.90,
            "b.md": 0.88,
            "c.md": 0.80,
            "irrelevant.md": 0.50,
        }
    ]

    document_similarities = {
        "a.md": {
            "a.md": 1.0,
            "b.md": 0.95,
            "c.md": 0.10,
            "irrelevant.md": 0.05,
        },
        "b.md": {
            "a.md": 0.95,
            "b.md": 1.0,
            "c.md": 0.10,
            "irrelevant.md": 0.05,
        },
        "c.md": {
            "a.md": 0.10,
            "b.md": 0.10,
            "c.md": 1.0,
            "irrelevant.md": 0.05,
        },
        "irrelevant.md": {
            "a.md": 0.05,
            "b.md": 0.05,
            "c.md": 0.05,
            "irrelevant.md": 1.0,
        },
    }

    ranking = (
        maximal_marginal_relevance(
            candidates,
            score_maps,
            document_similarities,
            k=2,
            lambda_relevance=0.5,
        )
    )

    selected = [
        document_id
        for document_id, _
        in ranking
    ]

    assert selected[0] == "a.md"
    assert selected[1] == "c.md"

def test_mmr_does_not_select_irrelevant_document_for_diversity():

    candidates = [
        "relevant.md",
        "similar.md",
        "irrelevant.md",
    ]

    score_maps = [
        {
            "relevant.md": 0.90,
            "similar.md": 0.85,
            "irrelevant.md": 0.10,
        }
    ]

    document_similarities = {
        "relevant.md": {
            "relevant.md": 1.0,
            "similar.md": 0.80,
            "irrelevant.md": -0.20,
        },
        "similar.md": {
            "relevant.md": 0.80,
            "similar.md": 1.0,
            "irrelevant.md": -0.20,
        },
        "irrelevant.md": {
            "relevant.md": -0.20,
            "similar.md": -0.20,
            "irrelevant.md": 1.0,
        },
    }

    ranking = (
        maximal_marginal_relevance(
            candidates,
            score_maps,
            document_similarities,
            k=2,
            lambda_relevance=0.5,
        )
    )

    selected = [
        document_id
        for document_id, _
        in ranking
    ]

    assert selected[0] == "relevant.md"
    assert selected[1] == "similar.md"

    
def test_selection_is_deterministic_on_ties():

    ranking = (
        greedy_query_coverage(
            [
                "b.md",
                "a.md",
            ],
            [
                {
                    "a.md": 1.0,
                    "b.md": 1.0,
                }
            ],
            k=2,
        )
    )

    assert [
        document_id
        for document_id, _
        in ranking
    ] == [
        "a.md",
        "b.md",
    ]


def test_missing_score_is_rejected():

    with pytest.raises(
        ValueError,
        match="Missing similarity score",
    ):
        greedy_query_coverage(
            [
                "a.md",
                "b.md",
            ],
            [
                {
                    "a.md": 0.5,
                }
            ],
            k=2,
        )


def test_non_finite_score_is_rejected():

    with pytest.raises(
        ValueError,
        match="Non-finite",
    ):
        greedy_query_coverage(
            [
                "a.md",
            ],
            [
                {
                    "a.md":
                        float("nan"),
                }
            ],
            k=1,
        )
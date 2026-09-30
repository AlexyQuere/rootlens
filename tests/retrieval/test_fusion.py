import pytest

from rootlens.retrieval.fusion import (
    max_similarity_fusion,
    mean_similarity_fusion,
)


def test_maxsim_rewards_single_strong_match():

    candidates = [
        "generic.md",
        "specialized.md",
    ]

    score_maps = [
        {
            "generic.md": 0.72,
            "specialized.md": 0.61,
        },
        {
            "generic.md": 0.73,
            "specialized.md": 0.65,
        },
        {
            "generic.md": 0.71,
            "specialized.md": 0.91,
        },
        {
            "generic.md": 0.72,
            "specialized.md": 0.60,
        },
    ]

    ranking = (
        max_similarity_fusion(
            candidates,
            score_maps,
        )
    )

    assert (
        ranking[0][0]
        == "specialized.md"
    )


def test_meansim_rewards_consistent_match():

    candidates = [
        "generic.md",
        "specialized.md",
    ]

    score_maps = [
        {
            "generic.md": 0.72,
            "specialized.md": 0.61,
        },
        {
            "generic.md": 0.73,
            "specialized.md": 0.65,
        },
        {
            "generic.md": 0.71,
            "specialized.md": 0.91,
        },
        {
            "generic.md": 0.72,
            "specialized.md": 0.60,
        },
    ]

    ranking = (
        mean_similarity_fusion(
            candidates,
            score_maps,
        )
    )

    assert (
        ranking[0][0]
        == "generic.md"
    )


def test_maxsim_uses_actual_scores():

    ranking = (
        max_similarity_fusion(
            [
                "a.md",
                "b.md",
            ],
            [
                {
                    "a.md": 0.50,
                    "b.md": 0.40,
                },
                {
                    "a.md": 0.55,
                    "b.md": 0.95,
                },
            ],
        )
    )

    assert ranking == [
        (
            "b.md",
            0.95,
        ),
        (
            "a.md",
            0.55,
        ),
    ]


def test_meansim_uses_all_queries():

    ranking = (
        mean_similarity_fusion(
            [
                "a.md",
                "b.md",
            ],
            [
                {
                    "a.md": 0.8,
                    "b.md": 0.7,
                },
                {
                    "a.md": 0.4,
                    "b.md": 0.7,
                },
            ],
        )
    )

    assert ranking[0][0] == "b.md"


def test_ties_are_deterministic():

    score_maps = [
        {
            "b.md": 0.8,
            "a.md": 0.8,
        }
    ]

    ranking = (
        max_similarity_fusion(
            [
                "b.md",
                "a.md",
            ],
            score_maps,
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
        max_similarity_fusion(
            [
                "a.md",
                "b.md",
            ],
            [
                {
                    "a.md": 0.8,
                }
            ],
        )


def test_non_finite_score_is_rejected():

    with pytest.raises(
        ValueError,
        match="Non-finite",
    ):
        mean_similarity_fusion(
            [
                "a.md",
            ],
            [
                {
                    "a.md":
                        float("nan"),
                }
            ],
        )
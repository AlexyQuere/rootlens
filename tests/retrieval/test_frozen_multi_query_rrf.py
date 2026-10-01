import pytest

from rootlens.retrieval.frozen_multi_query_rrf import (
    FrozenMultiQueryRRFRetriever,
)


class FakeRetriever:

    def __init__(
        self,
        rankings,
    ):

        self.rankings = (
            rankings
        )

        self.calls = []

    def search(
        self,
        query,
        k,
    ):

        self.calls.append(
            query
        )

        return (
            self.rankings[
                query
            ][
                :k
            ]
        )


def test_rrf_rewards_documents_found_across_queries():

    base = FakeRetriever(
        {
            "original": [
                ("a.md", 0.9),
                ("b.md", 0.8),
                ("c.md", 0.7),
            ],

            "rewrite": [
                ("b.md", 0.9),
                ("d.md", 0.8),
                ("a.md", 0.7),
            ],
        }
    )

    retriever = (
        FrozenMultiQueryRRFRetriever(
            base_retriever=base,
            rewrites={
                "original": [
                    "rewrite",
                ]
            },
            candidates_per_query=3,
            rrf_k=60,
        )
    )

    ranking = (
        retriever.search(
            "original",
            k=4,
        )
    )

    ids = [
        document_id
        for document_id, _
        in ranking
    ]

    assert ids[
        0
    ] == "b.md"

    assert set(
        ids
    ) == {
        "a.md",
        "b.md",
        "c.md",
        "d.md",
    }


def test_duplicate_queries_are_removed():

    base = FakeRetriever(
        {
            "original": [
                ("a.md", 1.0),
            ],

            "rewrite": [
                ("b.md", 1.0),
            ],
        }
    )

    retriever = (
        FrozenMultiQueryRRFRetriever(
            base_retriever=base,
            rewrites={
                "original": [
                    "original",
                    "rewrite",
                    "rewrite",
                ]
            },
        )
    )

    retriever.search(
        "original",
        k=2,
    )

    assert base.calls == [
        "original",
        "rewrite",
    ]


def test_search_respects_final_k():

    base = FakeRetriever(
        {
            "q": [
                ("a.md", 1.0),
                ("b.md", 0.9),
                ("c.md", 0.8),
            ],

            "r": [
                ("c.md", 1.0),
                ("d.md", 0.9),
                ("e.md", 0.8),
            ],
        }
    )

    retriever = (
        FrozenMultiQueryRRFRetriever(
            base_retriever=base,
            rewrites={
                "q": [
                    "r",
                ]
            },
            candidates_per_query=3,
        )
    )

    ranking = (
        retriever.search(
            "q",
            k=2,
        )
    )

    assert len(
        ranking
    ) == 2


def test_unknown_query_is_rejected():

    base = FakeRetriever(
        {}
    )

    retriever = (
        FrozenMultiQueryRRFRetriever(
            base_retriever=base,
            rewrites={},
        )
    )

    with pytest.raises(
        KeyError,
        match="No frozen rewrites",
    ):

        retriever.search(
            "unknown",
            k=5,
        )


def test_invalid_parameters_are_rejected():

    base = FakeRetriever(
        {}
    )

    with pytest.raises(
        ValueError,
        match="candidates_per_query",
    ):

        FrozenMultiQueryRRFRetriever(
            base_retriever=base,
            rewrites={},
            candidates_per_query=0,
        )

    with pytest.raises(
        ValueError,
        match="rrf_k",
    ):

        FrozenMultiQueryRRFRetriever(
            base_retriever=base,
            rewrites={},
            rrf_k=0,
        )
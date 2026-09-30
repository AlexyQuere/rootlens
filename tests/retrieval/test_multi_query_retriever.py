import pytest

from rootlens.retrieval.multi_query_retriever import (
    MultiQueryRetriever,
    reciprocal_rank_fusion,
)


class FakeRetriever:

    def __init__(
        self,
        results_by_query,
    ):
        self.results_by_query = (
            results_by_query
        )

    def search(
        self,
        query: str,
        k: int = 10,
    ):
        return (
            self.results_by_query[
                query
            ][:k]
        )


class FakeRewriter:

    def __init__(
        self,
        rewrites,
    ):
        self.rewrites = rewrites

    def rewrite(
        self,
        query: str,
        n: int = 3,
    ):
        return (
            self.rewrites[:n]
        )


def test_rrf_promotes_documents_seen_repeatedly():

    rankings = [
        [
            ("a.md", 0.9),
            ("b.md", 0.8),
        ],
        [
            ("b.md", 0.95),
            ("c.md", 0.7),
        ],
        [
            ("b.md", 0.7),
            ("a.md", 0.6),
        ],
    ]

    fused = (
        reciprocal_rank_fusion(
            rankings,
            rrf_k=60,
        )
    )

    assert (
        fused[0][0]
        == "b.md"
    )


def test_multi_query_always_includes_original():

    retriever = FakeRetriever(
        {
            "original": [
                ("a.md", 1.0)
            ],
            "rewrite one": [
                ("b.md", 1.0)
            ],
            "rewrite two": [
                ("c.md", 1.0)
            ],
        }
    )

    rewriter = FakeRewriter(
        [
            "rewrite one",
            "rewrite two",
        ]
    )

    multi = MultiQueryRetriever(
        retriever=retriever,
        query_rewriter=rewriter,
        num_rewrites=2,
        candidates_per_query=1,
    )

    result = (
        multi.search_with_details(
            "original",
            k=3,
        )
    )

    assert (
        result.expanded_queries[0]
        == "original"
    )


def test_union_contains_candidates_from_all_queries():

    retriever = FakeRetriever(
        {
            "original": [
                ("a.md", 1.0),
                ("b.md", 0.9),
            ],
            "rewrite one": [
                ("c.md", 1.0),
                ("a.md", 0.8),
            ],
            "rewrite two": [
                ("d.md", 1.0),
                ("b.md", 0.8),
            ],
        }
    )

    multi = MultiQueryRetriever(
        retriever=retriever,
        query_rewriter=(
            FakeRewriter(
                [
                    "rewrite one",
                    "rewrite two",
                ]
            )
        ),
        num_rewrites=2,
        candidates_per_query=2,
    )

    result = (
        multi.search_with_details(
            "original",
            k=3,
        )
    )

    assert set(
        result.union_document_ids
    ) == {
        "a.md",
        "b.md",
        "c.md",
        "d.md",
    }


def test_search_returns_requested_k():

    retriever = FakeRetriever(
        {
            "original": [
                ("a.md", 1.0),
                ("b.md", 0.9),
            ],
            "rewrite": [
                ("c.md", 1.0),
                ("d.md", 0.9),
            ],
        }
    )

    multi = MultiQueryRetriever(
        retriever=retriever,
        query_rewriter=(
            FakeRewriter(
                ["rewrite"]
            )
        ),
        num_rewrites=1,
        candidates_per_query=2,
    )

    results = multi.search(
        "original",
        k=2,
    )

    assert len(results) == 2


def test_rrf_ties_are_deterministic():

    rankings = [
        [
            ("b.md", 1.0),
            ("a.md", 0.5),
        ],
        [
            ("a.md", 1.0),
            ("b.md", 0.5),
        ],
    ]

    fused = (
        reciprocal_rank_fusion(
            rankings
        )
    )

    assert [
        document_id
        for document_id, _
        in fused
    ] == [
        "a.md",
        "b.md",
    ]


def test_invalid_configuration_is_rejected():

    with pytest.raises(
        ValueError
    ):
        MultiQueryRetriever(
            retriever=None,
            query_rewriter=None,
            num_rewrites=0,
        )
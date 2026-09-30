import pytest

from rootlens.retrieval.chunking import (
    chunk_document,
)


def test_short_document_produces_one_chunk():
    chunks = chunk_document(
        document_id="doc.md",
        text="one two three four",
        chunk_size_words=10,
        overlap_words=2,
    )

    assert len(chunks) == 1

    assert chunks[0].text == (
        "one two three four"
    )


def test_chunking_with_overlap():
    text = " ".join(
        str(index)
        for index in range(10)
    )

    chunks = chunk_document(
        document_id="doc.md",
        text=text,
        chunk_size_words=4,
        overlap_words=1,
    )

    assert chunks[0].text == (
        "0 1 2 3"
    )

    assert chunks[1].text == (
        "3 4 5 6"
    )


def test_overlap_must_be_smaller_than_chunk():
    with pytest.raises(ValueError):
        chunk_document(
            document_id="doc.md",
            text="hello world",
            chunk_size_words=4,
            overlap_words=4,
        )
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    document_id: str
    text: str
    start_word: int
    end_word: int


def chunk_document(
    document_id: str,
    text: str,
    chunk_size_words: int,
    overlap_words: int = 0,
) -> list[TextChunk]:
    if chunk_size_words <= 0:
        raise ValueError(
            "chunk_size_words must be positive."
        )

    if overlap_words < 0:
        raise ValueError(
            "overlap_words cannot be negative."
        )

    if overlap_words >= chunk_size_words:
        raise ValueError(
            "overlap_words must be smaller "
            "than chunk_size_words."
        )

    words = text.split()

    if not words:
        return []

    step = (
        chunk_size_words
        - overlap_words
    )

    chunks: list[TextChunk] = []

    chunk_index = 0

    for start in range(
        0,
        len(words),
        step,
    ):
        end = min(
            start + chunk_size_words,
            len(words),
        )

        chunk_text = " ".join(
            words[start:end]
        )

        chunks.append(
            TextChunk(
                chunk_id=(
                    f"{document_id}"
                    f"::chunk-{chunk_index}"
                ),
                document_id=document_id,
                text=chunk_text,
                start_word=start,
                end_word=end,
            )
        )

        chunk_index += 1

        if end == len(words):
            break

    return chunks


def chunk_corpus(
    documents: dict[str, str],
    chunk_size_words: int,
    overlap_words: int = 0,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []

    for document_id, text in documents.items():
        chunks.extend(
            chunk_document(
                document_id=document_id,
                text=text,
                chunk_size_words=(
                    chunk_size_words
                ),
                overlap_words=overlap_words,
            )
        )

    return chunks
from sentence_transformers import SentenceTransformer


class BGEEncoder:
    """Local text encoder based on BGE Small English v1.5."""

    QUERY_INSTRUCTION = (
        "Represent this sentence for searching relevant passages: "
    )

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
    ) -> None:
        self.model = SentenceTransformer(
            model_name,
            device="cpu",
        )

    def encode_documents(
        self,
        documents: list[str],
    ):
        """Encode documents into normalized dense vectors."""

        return self.model.encode(
            documents,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

    def encode_query(
        self,
        query: str,
    ):
        """Encode a retrieval query using the BGE query instruction."""

        instructed_query = (
            self.QUERY_INSTRUCTION
            + query
        )

        return self.model.encode(
            instructed_query,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

class DenseRetriever:
    """In-memory dense semantic retriever."""

    def __init__(
        self,
        documents: dict[str, str],
        encoder: BGEEncoder,
    ) -> None:
        self.documents = documents
        self.encoder = encoder

        self.document_ids = list(
            documents.keys()
        )

        document_texts = [
            documents[document_id]
            for document_id
            in self.document_ids
        ]

        self.document_embeddings = (
            self.encoder.encode_documents(
                document_texts
            )
        )

    def search(
        self,
        query: str,
        k: int = 5,
    ) -> list[tuple[str, float]]:
        if k <= 0:
            raise ValueError(
                "k must be strictly positive."
            )

        query_embedding = (
            self.encoder.encode_query(query)
        )

        scores = (
            self.document_embeddings
            @ query_embedding
        )

        results = [
            (
                document_id,
                float(score),
            )
            for document_id, score
            in zip(
                self.document_ids,
                scores,
            )
        ]

        results.sort(
            key=lambda item: (
                -item[1],
                item[0],
            )
        )

        return results[:k]
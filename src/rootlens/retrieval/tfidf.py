import math
import re


_TOKEN_PATTERN = re.compile(r"[a-z0-9_]+(?:\.[a-z0-9_]+)*")


def tokenize(text: str) -> list[str]:
    """Convert raw text into normalized lexical tokens.

    The initial RootLens tokenizer:
    - lowercases text;
    - keeps alphanumeric characters and underscores;
    - preserves dotted technical identifiers;
    - splits on other punctuation and whitespace.

    Examples:
        "Payment service unavailable"
        -> ["payment", "service", "unavailable"]

        "rpc.response.status_code=UNAVAILABLE"
        -> ["rpc.response.status_code", "unavailable"]

    This is intentionally a simple baseline tokenizer.
    """

    return _TOKEN_PATTERN.findall(text.lower())


def term_frequency(tokens: list[str]) -> dict[str, int]:
    """Count the number of occurrences of each token.

    Example:
        ["payment", "payment", "service"]

        becomes:

        {
            "payment": 2,
            "service": 1,
        }
    """

    frequencies: dict[str, int] = {}

    for token in tokens:
        frequencies[token] = frequencies.get(token, 0) + 1

    return frequencies

def document_frequency(
    term: str,
    documents: list[list[str]],
) -> int:
    """Count how many documents contain a term at least once.

    Example:
        documents = [
            ["payment", "service"],
            ["payment", "payment", "unavailable"],
            ["shipping", "service"],
        ]

        document_frequency("payment", documents)
        -> 2

    Multiple occurrences inside the same document count only once.
    """

    count = 0

    for document in documents:
        if term in document:
            count += 1

    return count

def inverse_document_frequency(
    term: str,
    documents: list[list[str]],
) -> float:
    """Compute the unsmoothed inverse document frequency of a term.

    IDF(t) = log(N / df(t))

    where:
        N     = total number of documents
        df(t) = number of documents containing the term

    Terms absent from the entire corpus receive an IDF of 0.0 in this
    initial implementation because they cannot contribute to matching
    any indexed document.
    """

    number_of_documents = len(documents)

    if number_of_documents == 0:
        return 0.0

    df = document_frequency(term, documents)

    if df == 0:
        return 0.0

    return math.log(number_of_documents / df)

def build_vocabulary(
    documents: list[list[str]],
) -> dict[str, int]:
    """Build a deterministic token-to-index mapping from a corpus.

    Tokens are sorted alphabetically so the vocabulary is reproducible.

    Example:
        documents = [
            ["payment", "service"],
            ["shipping", "service"],
        ]

        result:
        {
            "payment": 0,
            "service": 1,
            "shipping": 2,
        }
    """

    unique_terms: set[str] = set()

    for document in documents:
        unique_terms.update(document)

    sorted_terms = sorted(unique_terms)

    return {
        term: index
        for index, term in enumerate(sorted_terms)
    }

def tfidf_vector(
    tokens: list[str],
    documents: list[list[str]],
    vocabulary: dict[str, int],
) -> list[float]:
    """Represent one document as a TF-IDF vector.

    The vector follows the dimensions defined by `vocabulary`.

    TF-IDF(t, d) = TF(t, d) * IDF(t)
    """

    vector = [0.0] * len(vocabulary)

    frequencies = term_frequency(tokens)

    for term, tf in frequencies.items():
        if term not in vocabulary:
            continue

        index = vocabulary[term]

        idf = inverse_document_frequency(
            term,
            documents,
        )

        vector[index] = tf * idf

    return vector
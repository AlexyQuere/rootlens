from rootlens.retrieval.tfidf import (
    document_frequency,
    inverse_document_frequency,
    term_frequency,
    tokenize,
)

def test_tokenize_basic_sentence():
    text = "Payment service unavailable"

    result = tokenize(text)

    assert result == ["payment", "service", "unavailable"]


def test_tokenize_lowercases_text():
    text = "Payment SERVICE Unavailable"

    result = tokenize(text)

    assert result == ["payment", "service", "unavailable"]


def test_tokenize_preserves_dotted_technical_identifier():
    text = "rpc.response.status_code=UNAVAILABLE"

    result = tokenize(text)

    assert result == [
        "rpc.response.status_code",
        "unavailable",
    ]


def test_tokenize_splits_hyphenated_terms():
    text = "payment-service"

    result = tokenize(text)

    assert result == ["payment", "service"]


def test_tokenize_handles_empty_string():
    assert tokenize("") == []


def test_term_frequency_counts_tokens():
    tokens = ["payment", "payment", "service"]

    result = term_frequency(tokens)

    assert result == {
        "payment": 2,
        "service": 1,
    }


def test_term_frequency_handles_empty_tokens():
    assert term_frequency([]) == {}


import math


DOCUMENTS = [
    ["payment", "service"],
    ["payment", "service", "unavailable"],
    ["shipping", "service"],
]


def test_document_frequency_counts_documents():
    assert document_frequency("payment", DOCUMENTS) == 2
    assert document_frequency("service", DOCUMENTS) == 3
    assert document_frequency("unavailable", DOCUMENTS) == 1
    assert document_frequency("shipping", DOCUMENTS) == 1


def test_document_frequency_counts_term_once_per_document():
    documents = [
        ["payment", "payment", "payment"],
        ["payment", "service"],
    ]

    assert document_frequency("payment", documents) == 2


def test_document_frequency_returns_zero_for_unknown_term():
    assert document_frequency("database", DOCUMENTS) == 0


def test_idf_is_zero_for_term_in_every_document():
    result = inverse_document_frequency("service", DOCUMENTS)

    assert result == 0.0


def test_idf_for_payment():
    result = inverse_document_frequency("payment", DOCUMENTS)

    expected = math.log(3 / 2)

    assert math.isclose(result, expected)


def test_idf_for_rare_term():
    result = inverse_document_frequency("unavailable", DOCUMENTS)

    expected = math.log(3)

    assert math.isclose(result, expected)


def test_idf_returns_zero_for_unknown_term():
    assert inverse_document_frequency("database", DOCUMENTS) == 0.0


def test_idf_handles_empty_corpus():
    assert inverse_document_frequency("payment", []) == 0.0
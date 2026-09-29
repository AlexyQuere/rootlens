from rootlens.retrieval.tfidf import term_frequency, tokenize


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
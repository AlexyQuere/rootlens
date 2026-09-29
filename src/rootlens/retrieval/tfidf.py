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
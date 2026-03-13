"""Token estimation utilities for Russian text."""
from __future__ import annotations

# Среднее количество символов на один токен для русского текста.
# BPE-токенайзеры разбивают кириллицу на большее число субтокенов,
# чем латиницу, поэтому коэффициент ниже, чем ~4 для английского.
CHARS_PER_TOKEN_RU = 2.5


def estimate_tokens(text: str, chars_per_token: float = CHARS_PER_TOKEN_RU) -> int:
    """Estimate the number of tokens in *text* without loading a tokenizer.

    Uses a simple ``len(text) / chars_per_token`` heuristic.  For Russian
    (Cyrillic) text the default ratio is ~2.5 characters per token.

    Args:
        text: Input text string.
        chars_per_token: Average characters per token.

    Returns:
        Estimated token count (rounded up).
    """
    if not text:
        return 0
    import math
    return math.ceil(len(text) / chars_per_token)

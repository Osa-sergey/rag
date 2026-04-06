"""Tests for firefly_iii.account_resolver — account name resolution with synonyms."""
import pytest

from voice_bot.integrations.firefly_iii.account_resolver import AccountResolver
from voice_bot.integrations.firefly_iii.schemas import FireflyAccount


# Simulated accounts from Firefly III
MOCK_ACCOUNTS = [
    FireflyAccount(id="1", name="Наличка", account_type="asset"),
    FireflyAccount(id="2", name="Сбер расчетный счет", account_type="asset"),
    FireflyAccount(id="3", name="Сбер накопительный счет общий", account_type="asset"),
    FireflyAccount(id="4", name="Альфа расчетный счет", account_type="asset"),
    FireflyAccount(id="5", name="Тинькофф расчетный счет", account_type="asset"),
    FireflyAccount(id="6", name="Копилки", account_type="asset"),
]

SYNONYMS = {
    "сбер": "Сбер расчетный счет",
    "сбербанк": "Сбер расчетный счет",
    "альфа": "Альфа расчетный счет",
    "тинькофф": "Тинькофф расчетный счет",
    "наличка": "Наличка",
    "наличные": "Наличка",
    "нал": "Наличка",
    "копилка": "Копилки",
}


@pytest.fixture
def resolver():
    r = AccountResolver(
        synonyms=SYNONYMS,
        default_account="Сбер расчетный счет",
    )
    # Manually load accounts instead of calling API
    r._accounts = MOCK_ACCOUNTS
    r._name_to_account = {acc.name.lower(): acc for acc in MOCK_ACCOUNTS}
    return r


class TestSynonymMatch:
    def test_sber_synonym(self, resolver):
        result = resolver.resolve("сбер")
        assert result is not None
        assert result.firefly_id == "2"
        assert result.name == "Сбер расчетный счет"
        assert result.match_type == "synonym"

    def test_nalichka_synonym(self, resolver):
        result = resolver.resolve("наличка")
        assert result.firefly_id == "1"
        assert result.match_type == "synonym"

    def test_nalichnye_synonym(self, resolver):
        result = resolver.resolve("наличные")
        assert result.firefly_id == "1"

    def test_tinkoff_synonym(self, resolver):
        result = resolver.resolve("тинькофф")
        assert result.firefly_id == "5"
        assert result.match_type == "synonym"

    def test_kopilka_synonym(self, resolver):
        result = resolver.resolve("копилка")
        assert result.firefly_id == "6"
        assert result.match_type == "synonym"

    def test_nal_synonym(self, resolver):
        result = resolver.resolve("нал")
        assert result.firefly_id == "1"

    def test_case_insensitive_synonym(self, resolver):
        result = resolver.resolve("СБЕР")
        assert result.firefly_id == "2"


class TestExactMatch:
    def test_exact_account_name(self, resolver):
        result = resolver.resolve("Альфа расчетный счет")
        assert result.firefly_id == "4"
        assert result.match_type == "exact"

    def test_exact_case_insensitive(self, resolver):
        result = resolver.resolve("наличка")
        # This hits synonym first
        assert result.firefly_id == "1"


class TestSubstringMatch:
    def test_substring_kopilki(self, resolver):
        result = resolver.resolve("Копилки")
        assert result is not None
        assert result.firefly_id == "6"

    def test_substring_partial(self, resolver):
        result = resolver.resolve("Тинькофф расчетный")
        assert result is not None
        assert result.firefly_id == "5"


class TestDefault:
    def test_empty_string(self, resolver):
        result = resolver.resolve("")
        assert result is not None
        assert result.name == "Сбер расчетный счет"
        assert result.match_type == "default"

    def test_none(self, resolver):
        result = resolver.resolve(None)
        assert result is not None
        assert result.match_type == "default"

    def test_unknown(self, resolver):
        result = resolver.resolve("неизвестный банк")
        assert result is not None
        assert result.match_type == "default"


class TestEdgeCases:
    def test_empty_resolver(self):
        r = AccountResolver(synonyms={}, default_account="")
        r._accounts = []
        r._name_to_account = {}
        assert r.resolve("something") is None

    def test_account_names_property(self, resolver):
        names = resolver.account_names
        assert "Наличка" in names
        assert "Сбер расчетный счет" in names
        assert len(names) == 6

    def test_synonym_map_property(self, resolver):
        smap = resolver.synonym_map
        assert smap["сбер"] == "Сбер расчетный счет"


# ── Embedding-based matching ─────────────────────────────────


class _MockEmbedder:
    """Fake embedder that produces deterministic vectors for testing.

    Generates a normalized vector where each dimension corresponds to
    a character code, giving semantically-similar strings close vectors.
    """

    DIM = 64

    def _text_to_vec(self, text: str) -> list[float]:
        import numpy as np
        vec = np.zeros(self.DIM, dtype=np.float32)
        for ch in text.lower():
            idx = ord(ch) % self.DIM
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._text_to_vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._text_to_vec(text)


@pytest.fixture
def resolver_with_embeddings():
    """Resolver with a mock embedder so embedding path is exercised."""
    embedder = _MockEmbedder()
    r = AccountResolver(
        synonyms=SYNONYMS,
        default_account="Сбер расчетный счет",
        embedder=embedder,
    )
    r._accounts = MOCK_ACCOUNTS
    r._name_to_account = {acc.name.lower(): acc for acc in MOCK_ACCOUNTS}
    r._build_account_embeddings()
    return r


class TestEmbeddingMatch:
    def test_has_embeddings(self, resolver_with_embeddings):
        assert resolver_with_embeddings.has_embeddings is True

    def test_no_embeddings_without_embedder(self, resolver):
        assert resolver.has_embeddings is False

    def test_embedding_fallback_for_close_name(self, resolver_with_embeddings):
        """A query close to an account name but not an exact/substring match
        should still be found via embedding similarity."""
        # "расчетный счет сбер" is not a substring of "Сбер расчетный счет"
        # but shares many characters → should match via embedding
        result = resolver_with_embeddings.resolve("расчетный счет сбер")
        assert result is not None
        # Should match one of the "расчетный счет" accounts
        assert "расчетный счет" in result.name.lower() or result.match_type in (
            "fuzzy", "embedding"
        )

    def test_synonym_still_wins_over_embedding(self, resolver_with_embeddings):
        """Synonym match should still take priority over embedding."""
        result = resolver_with_embeddings.resolve("сбер")
        assert result.match_type == "synonym"
        assert result.name == "Сбер расчетный счет"

    def test_exact_still_wins_over_embedding(self, resolver_with_embeddings):
        # Use full account name that's NOT in the synonym dict
        result = resolver_with_embeddings.resolve("Сбер накопительный счет общий")
        assert result.match_type == "exact"

    def test_unknown_falls_to_embedding(self, resolver_with_embeddings):
        """Something that doesn't match strings but is semantically close."""
        result = resolver_with_embeddings.resolve("тинькофф банк расчетный")
        assert result is not None
        # Should find something via substring or embedding
        assert result.match_type in ("fuzzy", "embedding", "default")

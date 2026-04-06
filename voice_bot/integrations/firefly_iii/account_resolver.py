"""Account name resolver with synonym + embedding support.

Maps spoken account references (e.g. "сбер", "кредитка", "наличка")
to canonical Firefly III account names and IDs.

Resolution order:
1. Exact synonym match (from config)
2. Case-insensitive exact match
3. Substring match
4. Reverse substring match
5. **Cosine similarity** via embeddings (BERTA or any sentence-transformer)
6. Default account
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

from voice_bot.integrations.firefly_iii.schemas import FireflyAccount

logger = logging.getLogger(__name__)

# Minimum cosine similarity to accept an embedding match
_EMBEDDING_THRESHOLD = 0.45


class EmbeddingProvider(Protocol):
    """Minimal embedding interface (compatible with raptor's BaseEmbeddingProvider)."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


@dataclass
class ResolvedAccount:
    """Result of account resolution."""

    firefly_id: str
    name: str
    match_type: str  # "synonym", "exact", "fuzzy", "embedding", "default"
    confidence: float = 1.0


class AccountResolver:
    """Resolve spoken account names to Firefly III account IDs.

    Resolution order:
    1. Exact synonym match (from config)
    2. Case-insensitive exact match against Firefly account names
    3. Substring match (query in account name)
    4. Reverse substring (account name in query)
    5. Cosine similarity via embeddings
    6. Default account from config

    Usage::

        resolver = AccountResolver(
            synonyms={"сбер": "Сбер расчетный счет", "наличка": "Наличка"},
            default_account="Сбер расчетный счет",
            embedder=embedding_provider,  # optional but recommended
        )
        await resolver.load_accounts(firefly_client)
        result = resolver.resolve("зарплатный счёт")
        # result.name == "Сбер расчетный счет", match_type == "embedding"
    """

    def __init__(
        self,
        synonyms: dict[str, str] | None = None,
        default_account: str = "",
        embedder: Any | None = None,
        embedding_threshold: float = _EMBEDDING_THRESHOLD,
    ) -> None:
        self._synonyms: dict[str, str] = {
            k.lower(): v for k, v in (synonyms or {}).items()
        }
        self._default_account = default_account
        self._accounts: list[FireflyAccount] = []
        self._name_to_account: dict[str, FireflyAccount] = {}

        # Embedding-based matching
        self._embedder = embedder
        self._embedding_threshold = embedding_threshold
        self._account_embeddings: np.ndarray | None = None  # shape: (N, dim)
        self._account_names_ordered: list[str] = []

    async def load_accounts(self, client) -> None:
        """Fetch all asset accounts from Firefly III and build lookup index."""
        self._accounts = await client.get_accounts(account_type="asset")
        self._name_to_account = {
            acc.name.lower(): acc for acc in self._accounts
        }
        logger.info(
            "AccountResolver loaded %d asset accounts from Firefly III",
            len(self._accounts),
        )

        # Pre-compute embeddings for account names
        if self._embedder and self._accounts:
            self._build_account_embeddings()

    def _build_account_embeddings(self) -> None:
        """Pre-compute normalized embeddings for all account names.

        Also embeds synonym keys so queries close to synonyms
        can still be matched semantically.
        """
        # Build combined texts: account names + their synonyms as context
        names: list[str] = []
        account_refs: list[FireflyAccount] = []

        for acc in self._accounts:
            # Embed the full account name
            names.append(acc.name)
            account_refs.append(acc)

        self._account_names_ordered = [acc.name for acc in account_refs]

        try:
            vecs = self._embedder.embed_texts(names)
            embeddings = np.array(vecs, dtype=np.float32)

            # Normalize each row
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self._account_embeddings = embeddings / norms

            logger.info(
                "Built embeddings for %d account names (dim=%d)",
                len(names), embeddings.shape[1],
            )
        except Exception as e:
            logger.warning("Failed to build account embeddings: %s", e)
            self._account_embeddings = None

    def resolve(self, spoken_name: str | None) -> ResolvedAccount | None:
        """Resolve a spoken account name to a Firefly III account.

        Returns ``None`` only if no accounts are loaded AND no default is set.
        """
        if not spoken_name or not spoken_name.strip():
            return self._resolve_default()

        query = spoken_name.lower().strip()

        # 1. Synonym match
        canonical = self._synonyms.get(query)
        if canonical:
            account = self._name_to_account.get(canonical.lower())
            if account:
                logger.debug("Synonym match: '%s' → '%s'", spoken_name, account.name)
                return ResolvedAccount(
                    firefly_id=account.id,
                    name=account.name,
                    match_type="synonym",
                )
            logger.warning(
                "Synonym '%s' maps to '%s' which is not in Firefly accounts",
                spoken_name, canonical,
            )

        # 2. Exact match (case-insensitive)
        account = self._name_to_account.get(query)
        if account:
            logger.debug("Exact match: '%s'", account.name)
            return ResolvedAccount(
                firefly_id=account.id,
                name=account.name,
                match_type="exact",
            )

        # 3. Substring match — find accounts whose name contains the query
        matches = [
            acc for acc in self._accounts
            if query in acc.name.lower()
        ]
        if len(matches) == 1:
            acc = matches[0]
            logger.debug("Substring match: '%s' → '%s'", spoken_name, acc.name)
            return ResolvedAccount(
                firefly_id=acc.id,
                name=acc.name,
                match_type="fuzzy",
                confidence=0.8,
            )
        if len(matches) > 1:
            acc = min(matches, key=lambda a: len(a.name))
            logger.debug(
                "Ambiguous match: '%s' → '%s' (out of %d candidates)",
                spoken_name, acc.name, len(matches),
            )
            return ResolvedAccount(
                firefly_id=acc.id,
                name=acc.name,
                match_type="fuzzy",
                confidence=0.6,
            )

        # 4. Reverse substring — account name is contained in the query
        matches = [
            acc for acc in self._accounts
            if acc.name.lower() in query
        ]
        if matches:
            acc = max(matches, key=lambda a: len(a.name))
            logger.debug("Reverse substring: '%s' → '%s'", spoken_name, acc.name)
            return ResolvedAccount(
                firefly_id=acc.id,
                name=acc.name,
                match_type="fuzzy",
                confidence=0.5,
            )

        # 5. Embedding cosine similarity
        emb_result = self._resolve_by_embedding(spoken_name)
        if emb_result:
            return emb_result

        # 6. Default fallback
        logger.info("No match for '%s', falling back to default", spoken_name)
        return self._resolve_default()

    # ── Embedding-based resolution ────────────────────────────

    def _resolve_by_embedding(self, spoken_name: str) -> ResolvedAccount | None:
        """Try to match via cosine similarity against account name embeddings.

        Returns the best match if similarity >= threshold, else None.
        """
        if self._embedder is None or self._account_embeddings is None:
            return None

        try:
            query_vec = np.array(
                self._embedder.embed_query(spoken_name), dtype=np.float32
            )
            # Normalize query
            norm = np.linalg.norm(query_vec)
            if norm == 0:
                return None
            query_vec = query_vec / norm

            # Cosine similarities (dot product since both are normalized)
            similarities = self._account_embeddings @ query_vec

            best_idx = int(np.argmax(similarities))
            best_score = float(similarities[best_idx])

            if best_score >= self._embedding_threshold:
                acc = self._accounts[best_idx]
                logger.info(
                    "Embedding match: '%s' → '%s' (similarity=%.3f)",
                    spoken_name, acc.name, best_score,
                )
                return ResolvedAccount(
                    firefly_id=acc.id,
                    name=acc.name,
                    match_type="embedding",
                    confidence=best_score,
                )

            # Below threshold — log top candidates for debugging
            top_indices = np.argsort(similarities)[-3:][::-1]
            candidates = [
                f"'{self._accounts[i].name}' ({similarities[i]:.3f})"
                for i in top_indices
            ]
            logger.debug(
                "Embedding no match for '%s' (best=%.3f < %.3f). Top: %s",
                spoken_name, best_score, self._embedding_threshold,
                ", ".join(candidates),
            )

        except Exception as e:
            logger.warning("Embedding resolution failed for '%s': %s", spoken_name, e)

        return None

    # ── Default fallback ──────────────────────────────────────

    def _resolve_default(self) -> ResolvedAccount | None:
        """Resolve to the default account."""
        if not self._default_account:
            return None

        account = self._name_to_account.get(self._default_account.lower())
        if account:
            return ResolvedAccount(
                firefly_id=account.id,
                name=account.name,
                match_type="default",
            )
        if self._accounts:
            acc = self._accounts[0]
            logger.warning(
                "Default account '%s' not found, using first account: '%s'",
                self._default_account, acc.name,
            )
            return ResolvedAccount(
                firefly_id=acc.id,
                name=acc.name,
                match_type="default",
                confidence=0.3,
            )
        return None

    @property
    def account_names(self) -> list[str]:
        """Return all loaded account names."""
        return [acc.name for acc in self._accounts]

    @property
    def synonym_map(self) -> dict[str, str]:
        """Return the current synonym mapping."""
        return dict(self._synonyms)

    @property
    def has_embeddings(self) -> bool:
        """Return True if embedding-based matching is available."""
        return self._account_embeddings is not None

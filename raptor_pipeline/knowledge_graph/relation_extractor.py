"""LLM-based relation extraction, aware of previously extracted keywords."""
from __future__ import annotations

import json
import logging

from omegaconf import DictConfig

from raptor_pipeline.knowledge_graph.base import (
    BaseRelationExtractor,
    Keyword,
    Relation,
)
from raptor_pipeline.summarizer.llm_summarizer import _build_llm

logger = logging.getLogger(__name__)


class LLMRelationExtractor(BaseRelationExtractor):
    """Extract relations (triples) using an LLM.

    The LLM receives both the text *and* the list of previously extracted
    keywords so that it can build relations between them.

    The prompt template is loaded from ``prompts.relations`` Hydra config.
    """

    def __init__(self, cfg: DictConfig, prompt_cfg: DictConfig) -> None:
        self._llm = _build_llm(cfg)
        self._max_relations: int = cfg.get("max_relations", 20)
        self._confidence_threshold: float = cfg.get("confidence_threshold", 0.5)
        self._template: str = prompt_cfg.get(
            "template",
            (
                "На основе текста и списка ключевых слов извлеки "
                "до {max_relations} связей (триплетов) вида "
                '(subject, predicate, object).\n'
                "subject и object должны быть из списка ключевых слов или "
                "являться значимыми сущностями из текста.\n"
                "Для каждой связи укажи уверенность (0–1).\n"
                "Верни JSON-массив объектов "
                '[{{"subject": "...", "predicate": "...", '
                '"object": "...", "confidence": 0.X}}].\n\n'
                "Ключевые слова: {keywords}\n\n"
                "Текст:\n{text}\n\n"
                "JSON:"
            ),
        )
        self._prompt_version: str = prompt_cfg.get("version", "1.0")
        logger.info(
            "LLMRelationExtractor ready (prompt v%s, max=%d)",
            self._prompt_version,
            self._max_relations,
        )

    def extract(
        self,
        text: str,
        keywords: list[Keyword],
        chunk_id: str = "",
    ) -> list[Relation]:
        kw_str = ", ".join(k.word for k in keywords) if keywords else "—"
        prompt = (
            self._template
            .replace("{text}", text)
            .replace("{keywords}", kw_str)
            .replace("{max_relations}", str(self._max_relations))
        )
        response = self._llm.invoke(prompt)
        raw = response.content if hasattr(response, "content") else str(response)

        relations: list[Relation] = []
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            items = json.loads(cleaned)
            for item in items:
                rel = Relation(
                    subject=item.get("subject", "").strip(),
                    predicate=item.get("predicate", "").strip(),
                    object=item.get("object", "").strip(),
                    confidence=float(item.get("confidence", 1.0)),
                    chunk_id=chunk_id,
                )
                if (
                    rel.subject
                    and rel.predicate
                    and rel.object
                    and rel.confidence >= self._confidence_threshold
                ):
                    relations.append(rel)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning(
                "Failed to parse relation JSON: %s | raw: %s", exc, raw[:200]
            )

        return relations[: self._max_relations]

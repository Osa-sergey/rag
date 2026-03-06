"""LLM-based relation extraction, aware of previously extracted keywords."""
from __future__ import annotations

import json
import logging

from omegaconf import DictConfig

from raptor_pipeline.knowledge_graph.base import (
    BaseRelationExtractor,
    Keyword,
    Relation,
    RelationListSO,
)
from raptor_pipeline.summarizer.llm_summarizer import _build_llm

logger = logging.getLogger(__name__)


class LLMRelationExtractor(BaseRelationExtractor):
    """Extract relations (triples) using an LLM with Structured Output.
    """

    def __init__(self, cfg: DictConfig, prompt_cfg: DictConfig) -> None:
        llm = _build_llm(cfg)
        self._structured_llm = llm.with_structured_output(RelationListSO)
        
        self._max_relations: int = cfg.get("max_relations", 20)
        self._confidence_threshold: float = cfg.get("confidence_threshold", 0.5)
        self._template: str = prompt_cfg.get(
            "template",
            "Ключевые слова: {keywords}\n\nТекст:\n{text}"
        )
        self._prompt_version: str = prompt_cfg.get("version", "1.0")
        logger.info(
            "LLMRelationExtractor ready (SO enabled, v%s)",
            self._prompt_version
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
        
        try:
            result: RelationListSO = self._structured_llm.invoke(prompt)
            if not result or not result.relations:
                return []

            relations: list[Relation] = []
            for item in result.relations:
                rel = Relation(
                    subject=item.subject.strip(),
                    predicate=item.predicate.strip(),
                    object=item.object.strip(),
                    confidence=item.confidence,
                    chunk_id=chunk_id,
                )
                if (
                    rel.subject
                    and rel.predicate
                    and rel.object
                    and rel.confidence >= self._confidence_threshold
                ):
                    relations.append(rel)
            return relations[: self._max_relations]
        except Exception as exc:
            logger.warning("SO Relation extraction failed: %s", exc)
            return []

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

    def __init__(self, cfg: DictConfig, prompt_cfg: DictConfig, *, tracker=None) -> None:
        self._llm = _build_llm(cfg)
        self._tracker = tracker
        self._structured_llm = self._llm.with_structured_output(RelationListSO)
        
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

    def _clean_json_text(self, text: str) -> str:
        """Strip markdown code blocks and reasoning tags."""
        import re
        text = text.strip()
        # Remove reasoning/thinking tags
        text = re.sub(r'<(thought|think)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove markdown code blocks
        if "```" in text:
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(1)
            else:
                text = text.replace("```json", "").replace("```", "")
        return text.strip()

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
            # 1. Try primary structured output
            result: RelationListSO = self._structured_llm.invoke(prompt)
            if self._tracker and hasattr(result, 'response_metadata'):
                self._tracker.track(result, "relation_extractor")
            if result and result.relations:
                return self._parse_so_result(result, chunk_id)
            
            # 2. Fallback: Manual parse
            return self._manual_fallback(prompt, chunk_id)
        except Exception as exc:
            logger.debug("SO Relation extraction failed: %s. Trying manual fallback...", exc)
            return self._manual_fallback(prompt, chunk_id)

    def _manual_fallback(self, prompt: str, chunk_id: str) -> list[Relation]:
        try:
            raw_response = self._llm.invoke(prompt)
            if self._tracker:
                self._tracker.track(raw_response, "relation_extractor")
            content = raw_response.content if hasattr(raw_response, "content") else str(raw_response)
            clean_content = self._clean_json_text(content)
            
            parsed = json.loads(clean_content)
            if isinstance(parsed, list):
                result = RelationListSO(relations=parsed)
            elif isinstance(parsed, dict):
                if "relations" in parsed:
                    result = RelationListSO(relations=parsed["relations"])
                else:
                    return []
            else:
                return []
            return self._parse_so_result(result, chunk_id)
        except Exception as exc:
            logger.warning("Manual fallback relation extraction failed: %s", exc)
            return []

    def _parse_so_result(self, result: RelationListSO, chunk_id: str) -> list[Relation]:
        relations: list[Relation] = []
        for item in result.relations:
            if isinstance(item, dict):
                subject = item.get('subject', '')
                predicate = item.get('predicate', '')
                obj = item.get('object', '')
                confidence = item.get('confidence', 1.0)
            else:
                subject = getattr(item, 'subject', '')
                predicate = getattr(item, 'predicate', '')
                obj = getattr(item, 'object', '')
                confidence = getattr(item, 'confidence', 1.0)

            rel = Relation(
                subject=str(subject).strip(),
                predicate=str(predicate).strip(),
                object=str(obj).strip(),
                confidence=float(confidence),
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

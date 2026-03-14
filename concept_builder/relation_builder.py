"""Relation builder — LLM-based cross-concept relationship extraction."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from omegaconf import DictConfig

from concept_builder.models import ConceptNode, CrossRelation
from raptor_pipeline.summarizer.llm_summarizer import _build_llm

logger = logging.getLogger(__name__)


class RelationBuilder:
    """Extract cross-article relations between Concept nodes using LLM."""

    def __init__(
        self,
        llm_cfg: DictConfig,
        prompt_cfg: DictConfig,
        *,
        tracker: Any = None,
        max_prompt_tokens: int = 3000,
        chars_per_token: float = 2.5,
    ) -> None:
        self._llm = _build_llm(llm_cfg)
        self._template: str = prompt_cfg.get("template", "Найди связи между {concepts}")
        self._tracker = tracker
        self._max_prompt_tokens = max_prompt_tokens
        self._chars_per_token = chars_per_token

    def extract(self, concepts: list[ConceptNode]) -> list[CrossRelation]:
        """Find relations between concepts using LLM.

        Args:
            concepts: List of ConceptNode objects with descriptions.

        Returns:
            List of CrossRelation objects.
        """
        if len(concepts) < 2:
            return []

        # Build concepts description for prompt
        max_chars = int(self._max_prompt_tokens * self._chars_per_token)
        concepts_text = self._format_concepts(concepts, max_chars)

        prompt = self._template.replace("{concepts}", concepts_text)

        try:
            response = self._llm.invoke(prompt)
            if self._tracker:
                self._tracker.track(response, "cross_relations")
            content = response.content if hasattr(response, "content") else str(response)
            return self._parse_response(content, concepts)
        except Exception as exc:
            logger.warning("Failed to extract cross-relations: %s", exc)
            return []

    def _format_concepts(self, concepts: list[ConceptNode], max_chars: int) -> str:
        """Format concepts list for prompt, respecting char budget."""
        parts = []
        budget = int(max_chars * 0.7)  # 70% for concepts, rest for template
        used = 0

        for c in concepts:
            entry = (
                f"- {c.canonical_name} (домен: {c.domain}): {c.description}"
            )
            if used + len(entry) > budget:
                entry = entry[:budget - used]
                parts.append(entry)
                break
            parts.append(entry)
            used += len(entry) + 1

        return "\n".join(parts)

    def _parse_response(
        self, content: str, concepts: list[ConceptNode],
    ) -> list[CrossRelation]:
        """Parse LLM response JSON into CrossRelation objects."""
        # Clean markdown code blocks
        content = content.strip()
        content = re.sub(r'<(thought|think)>.*?</\1>', '', content, flags=re.DOTALL | re.IGNORECASE)
        if "```" in content:
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
            if match:
                content = match.group(1)

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse cross-relations JSON")
            return []

        if isinstance(parsed, dict) and "relations" in parsed:
            parsed = parsed["relations"]
        if not isinstance(parsed, list):
            return []

        # Build concept lookup
        concept_by_name: dict[str, ConceptNode] = {}
        for c in concepts:
            concept_by_name[c.canonical_name.lower()] = c

        relations: list[CrossRelation] = []
        for item in parsed:
            source_name = str(item.get("source", "")).strip().lower()
            target_name = str(item.get("target", "")).strip().lower()

            source_concept = concept_by_name.get(source_name)
            target_concept = concept_by_name.get(target_name)

            if not source_concept or not target_concept:
                continue
            if source_concept.id == target_concept.id:
                continue

            # Merge source articles from both concepts
            all_articles = list(set(
                source_concept.source_articles + target_concept.source_articles
            ))
            all_versions = {**source_concept.source_versions, **target_concept.source_versions}

            rel = CrossRelation(
                source_concept_id=source_concept.id,
                target_concept_id=target_concept.id,
                predicate=str(item.get("predicate", "")).strip(),
                description=str(item.get("description", "")).strip(),
                source_articles=all_articles,
                source_versions=all_versions,
                confidence=float(item.get("confidence", 0.5)),
            )
            relations.append(rel)

        logger.info("Extracted %d cross-relations", len(relations))
        return relations

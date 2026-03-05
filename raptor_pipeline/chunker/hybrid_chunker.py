"""Hybrid chunker — respects paragraphs, semantic splits inside, strictly whole sentences."""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

import numpy as np
from omegaconf import DictConfig

from document_parser.text_extractor import flatten_blocks, render_block
from raptor_pipeline.chunker.base import BaseChunker, Chunk

if TYPE_CHECKING:
    from raptor_pipeline.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)

# Basic sentence splitter regex (handles . ! ? followed by space or newline)
SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[.!?])\s+')

class HybridChunker(BaseChunker):
    """Hybrid Chunker:
    1. Respects paragraph (block) boundaries — never merges blocks.
    2. Within each block, splits into sentences.
    3. Groups sentences semantically.
    4. Ensures no sentence is cut in half.
    5. If a chunk exceeds max_chars, rounds down to the previous sentence.
    """

    def __init__(
        self,
        cfg: DictConfig,
        embedding_provider: BaseEmbeddingProvider,
    ) -> None:
        self.max_chunk_chars: int = cfg.get("max_chunk_chars", 2000)
        self.similarity_threshold: float = cfg.get("similarity_threshold", 0.6)
        self._embedder = embedding_provider

    def chunk(self, document: list[dict], article_id: str) -> list[Chunk]:
        flat_blocks = flatten_blocks(document)
        all_chunks: list[Chunk] = []
        chunk_idx = 1
        current_header = ""

        for block in flat_blocks:
            is_header = block.get("type", "") == "header"
            raw_text = render_block(block).strip()
            if not raw_text:
                continue
                
            if is_header:
                current_header = raw_text

            # If it's not a header and we have a current header, prepend context 
            # (but only for the LLM's understanding, so we add it to the text)
            if not is_header and current_header:
                text = f"[Section: {current_header}]\n{raw_text}"
            else:
                text = raw_text

            # Process each block independently (paragraph boundary constraint)
            block_sentences = SENTENCE_SPLIT_REGEX.split(raw_text) # split on raw_text to not split our header injection if we want to keep it together
            block_sentences = [s.strip() for s in block_sentences if s.strip()]
            
            if not block_sentences:
                continue

            # If block is small, it's one chunk
            if len(text) <= self.max_chunk_chars:
                all_chunks.append(self._create_chunk(text, [block], article_id, chunk_idx, current_header))
                chunk_idx += 1
                continue

            # If block is large, apply semantic splitting within sentences
            sentence_embeddings = self._embedder.embed_texts(block_sentences)
            sentence_groups = self._group_sentences_semantically(block_sentences, sentence_embeddings)
            
            # Sub-divide groups to fit max_chunk_chars (rounded down to sentence)
            for group in sentence_groups:
                final_subgroups = self._ensure_length_limit(group)
                for subgroup_raw_text in final_subgroups:
                    # Inject header context into subgroup text as well
                    if not is_header and current_header:
                        subgroup_text = f"[Section: {current_header}]\n{subgroup_raw_text}"
                    else:
                        subgroup_text = subgroup_raw_text
                        
                    all_chunks.append(self._create_chunk(subgroup_text, [block], article_id, chunk_idx, current_header))
                    chunk_idx += 1

        return all_chunks

    def _group_sentences_semantically(self, sentences: list[str], embeddings: list[list[float]]) -> list[list[str]]:
        if not sentences:
            return []
        
        groups: list[list[str]] = [[sentences[0]]]
        for i in range(1, len(sentences)):
            sim = self._cosine_sim(embeddings[i-1], embeddings[i])
            if sim >= self.similarity_threshold:
                groups[-1].append(sentences[i])
            else:
                groups.append([sentences[i]])
        return groups

    def _ensure_length_limit(self, sentence_group: list[str]) -> list[str]:
        """Split a group of sentences further if it exceeds max_chunk_chars."""
        result = []
        current_sentences = []
        current_len = 0
        
        for sent in sentence_group:
            sent_len = len(sent)
            # +2 for space/newline if we join with them, but let's be conservative
            if current_len + sent_len + 2 > self.max_chunk_chars and current_sentences:
                result.append(" ".join(current_sentences))
                current_sentences = []
                current_len = 0
            
            # If a single sentence is longer than max_chars (rare but possible),
            # we unfortunately have to break it or just keep it as is.
            # User said "запретить прерывать чанк не по предложениям". 
            # So we keep it even if it slightly exceeds.
            current_sentences.append(sent)
            current_len += sent_len + 1
            
        if current_sentences:
            result.append(" ".join(current_sentences))
        return result

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        a_arr = np.array(a)
        b_arr = np.array(b)
        denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
        if denom == 0: return 0.0
        return float(np.dot(a_arr, b_arr) / denom)

    def _create_chunk(self, text: str, blocks: list[dict], article_id: str, idx: int, section: str = "") -> Chunk:
        block_ids = [str(b.get("id", "")) for b in blocks if "id" in b]
        return Chunk(
            chunk_id=f"{article_id}_hybrid_{idx}",
            article_id=article_id,
            text=text,
            block_ids=block_ids,
            level=0,
            metadata={
                "char_count": len(text),
                "type": "hybrid",
                "section": section
            }
        )

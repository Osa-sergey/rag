"""Section-based chunker — groups blocks by header sections, merges short ones."""
from __future__ import annotations

from omegaconf import DictConfig

from document_parser.text_extractor import flatten_blocks, render_block
from raptor_pipeline.chunker.base import BaseChunker, Chunk


class SectionChunker(BaseChunker):
    """Chunks a document by header sections.

    Blocks between two headers of the same or higher level form a section.
    Short sections (< min_chunk_chars) are merged with their neighbours
    until they reach target_chunk_chars.  Long sections (> max_chunk_chars)
    are split with overlap_chars overlap.
    """

    def __init__(self, cfg: DictConfig) -> None:
        self.min_chunk_chars: int = cfg.get("min_chunk_chars", 200)
        self.target_chunk_chars: int = cfg.get("target_chunk_chars", 800)
        self.max_chunk_chars: int = cfg.get("max_chunk_chars", 2000)
        self.overlap_chars: int = cfg.get("overlap_chars", 100)

    # ------------------------------------------------------------------
    def chunk(self, document: list[dict], article_id: str) -> list[Chunk]:
        flat = flatten_blocks(document)
        sections = self._split_into_sections(flat)
        sections = self._merge_short(sections)
        sections = self._split_long(sections)
        return self._to_chunks(sections, article_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _split_into_sections(self, flat: list[dict]) -> list[list[dict]]:
        """Group blocks into sections by headers."""
        sections: list[list[dict]] = []
        current: list[dict] = []

        for block in flat:
            if block.get("type") == "header" and current:
                sections.append(current)
                current = []
            current.append(block)

        if current:
            sections.append(current)
        return sections

    def _render_section(self, blocks: list[dict]) -> str:
        parts = []
        for b in blocks:
            text = render_block(b)
            if text.strip():
                parts.append(text)
        return "\n\n".join(parts).strip()

    def _merge_short(self, sections: list[list[dict]]) -> list[list[dict]]:
        """Merge short sections with the next one."""
        merged: list[list[dict]] = []
        buf: list[dict] = []

        for sec in sections:
            buf.extend(sec)
            text = self._render_section(buf)
            if len(text) >= self.min_chunk_chars:
                merged.append(buf)
                buf = []

        if buf:
            if merged:
                merged[-1].extend(buf)
            else:
                merged.append(buf)
        return merged

    def _split_long(self, sections: list[list[dict]]) -> list[list[dict]]:
        """Split sections that exceed max_chunk_chars."""
        result: list[list[dict]] = []
        for sec in sections:
            text = self._render_section(sec)
            if len(text) <= self.max_chunk_chars:
                result.append(sec)
                continue

            # split block-by-block with overlap
            current_blocks: list[dict] = []
            current_len = 0
            for b in sec:
                block_text = render_block(b)
                blen = len(block_text)
                if current_len + blen > self.max_chunk_chars and current_blocks:
                    result.append(current_blocks)
                    # keep last few blocks for context overlap
                    overlap_blocks: list[dict] = []
                    overlap_len = 0
                    for ob in reversed(current_blocks):
                        obt = render_block(ob)
                        if overlap_len + len(obt) > self.overlap_chars:
                            break
                        overlap_blocks.insert(0, ob)
                        overlap_len += len(obt)
                    current_blocks = list(overlap_blocks)
                    current_len = overlap_len
                current_blocks.append(b)
                current_len += blen
            if current_blocks:
                result.append(current_blocks)
        return result

    def _to_chunks(
        self,
        sections: list[list[dict]],
        article_id: str,
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        for i, sec in enumerate(sections, 1):
            text = self._render_section(sec)
            if not text:
                continue
            block_ids = [str(b.get("id", "")) for b in sec if "id" in b]
            chunk = Chunk(
                chunk_id=f"{article_id}_chunk_{i}",
                article_id=article_id,
                text=text,
                block_ids=block_ids,
                level=0,
                metadata={
                    "section_index": i,
                    "char_count": len(text),
                },
            )
            chunks.append(chunk)
        return chunks

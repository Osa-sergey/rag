"""Parse Obsidian wiki-links and markdown links from text.

Obsidian link formats:
    [[target]]                              → simple
    [[target|display]]                      → with alias
    [[target#section]]                      → with section
    [[target#section|display]]              → full form
    [[#section]]                            → same-file section link

Markdown link:
    [display](url)

Filename versioning:
    article_name_YYYYMMDD_HHMMSS.yaml       → version = YYYYMMDD_HHMMSS
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Obsidian link regex:  [[  (content)  ]]
_OBSIDIAN_RE = re.compile(r"\[\[([^\[\]]+?)\]\]")
# Markdown link regex:  [display](url)
_MARKDOWN_LINK_RE = re.compile(r"\[([^\[\]]+?)\]\(([^)]+)\)")
# Filename version suffix: _YYYYMMDD_HHMMSS.yaml
_VERSION_RE = re.compile(r"_(\d{8}_\d{6})\.yaml$")


@dataclass
class ExtractedLink:
    """A link found in chunk text."""

    raw: str                   # original text as found: [[target#sec|display]]
    display: str               # text shown to reader
    target: str                # file/article name (without section)
    section: str = ""          # #section if present
    link_type: str = "obsidian"  # "obsidian" | "markdown" | "url"

    @property
    def target_article_id(self) -> str:
        """Normalized target for matching against article IDs.

        Obsidian guarantees unique names within a vault,
        so we match by name only (case-insensitive).
        """
        return self.target.strip().lower()


def parse_obsidian_link(raw_content: str) -> ExtractedLink:
    """Parse the content inside [[ ]] brackets.

    Examples:
        "MOC RAG|RAG"                       → target=MOC RAG, display=RAG
        "file#Hybrid RAG|Hybrid RAG"        → target=file, section=Hybrid RAG, display=Hybrid RAG
        "semantic text segmentation"        → target=semantic text segmentation
        "#section"                          → target="", section=section (same-file)
    """
    raw = f"[[{raw_content}]]"

    # Split by | for alias
    if "|" in raw_content:
        path_part, display = raw_content.rsplit("|", 1)
    else:
        path_part = raw_content
        display = ""

    # Split by # for section
    if "#" in path_part:
        target, section = path_part.split("#", 1)
    else:
        target = path_part
        section = ""

    target = target.strip()
    section = section.strip()
    display = display.strip() or section or target

    return ExtractedLink(
        raw=raw,
        display=display,
        target=target,
        section=section,
        link_type="obsidian",
    )


def extract_links_from_text(text: str) -> list[ExtractedLink]:
    """Extract all Obsidian and markdown links from a text string."""
    links: list[ExtractedLink] = []
    seen_raw: set[str] = set()

    # 1. Obsidian links [[...]]
    for match in _OBSIDIAN_RE.finditer(text):
        content = match.group(1).strip()
        if content:
            link = parse_obsidian_link(content)
            if link.raw not in seen_raw:
                seen_raw.add(link.raw)
                links.append(link)

    # 2. Markdown links [text](url)
    for match in _MARKDOWN_LINK_RE.finditer(text):
        display = match.group(1).strip()
        url = match.group(2).strip()
        raw = f"[{display}]({url})"
        if raw not in seen_raw:
            seen_raw.add(raw)
            links.append(ExtractedLink(
                raw=raw,
                display=display,
                target=url,
                link_type="markdown",
            ))

    return links


def parse_article_version(filename: str) -> tuple[str, str]:
    """Extract article name and version from filename.

    Args:
        filename: e.g. "21 Chunking Strategies for RAG_20260218_145649.yaml"

    Returns:
        (article_name, version) where version is "YYYYMMDD_HHMMSS" or ""
        article_name is the base name used as vault-unique identifier.
    """
    # Remove .yaml extension for matching
    name = filename
    if name.endswith(".yaml"):
        name = name[:-5]

    match = _VERSION_RE.search(filename)
    if match:
        version = match.group(1)
        # Article name = everything before _YYYYMMDD_HHMMSS
        article_name = name[: -(len(version) + 1)]  # +1 for the underscore
    else:
        version = ""
        article_name = name

    return article_name, version

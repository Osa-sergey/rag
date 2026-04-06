import React from "react";

export interface HighlightSpan {
    /** Start character index */
    start: number;
    /** End character index */
    end: number;
    /** Highlight color */
    color?: string;
    /** Label for the highlight (shown on hover) */
    label?: string;
}

export interface MarkdownRendererProps {
    /** Raw markdown or plain text content */
    content: string;
    /** Keyword highlights to overlay */
    highlights?: HighlightSpan[];
    /** Max height with scroll (0 = no limit) */
    maxHeight?: number;
    /** Compact mode (smaller text) */
    compact?: boolean;
}

/**
 * A lightweight markdown-to-HTML renderer.
 * Supports: # headings, **bold**, *italic*, `code`, ```blocks```, - lists, > blockquotes, [links](url)
 * Does NOT use a full markdown parser — just regex for common patterns.
 */
function renderMarkdown(text: string): string {
    let html = text
        // Escape HTML
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Code blocks (``` ... ```)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_match, _lang, code) =>
        `<pre class="md-code-block"><code>${code.trim()}</code></pre>`
    );

    // Headings
    html = html.replace(/^### (.+)$/gm, '<h3 class="md-h3">$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2 class="md-h2">$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1 class="md-h1">$1</h1>');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>');

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="md-link" target="_blank" rel="noopener">$1</a>');

    // Blockquotes (&gt; already escaped)
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote class="md-blockquote">$1</blockquote>');

    // Unordered lists
    html = html.replace(/^- (.+)$/gm, '<li class="md-li">$1</li>');
    html = html.replace(/((?:<li class="md-li">.*<\/li>\n?)+)/g, '<ul class="md-ul">$1</ul>');

    // Paragraphs (double newline)
    html = html.replace(/\n\n/g, '</p><p class="md-p">');
    html = `<p class="md-p">${html}</p>`;

    // Clean up empty paragraphs
    html = html.replace(/<p class="md-p"><\/p>/g, '');
    html = html.replace(/<p class="md-p">(<(?:h[1-3]|pre|ul|blockquote))/g, '<$1'.replace('<$1', '$1'));

    return html;
}

function applyHighlights(content: string, highlights: HighlightSpan[]): React.ReactNode[] {
    if (!highlights.length) return [content];

    const sorted = [...highlights].sort((a, b) => a.start - b.start);
    const parts: React.ReactNode[] = [];
    let cursor = 0;

    for (const span of sorted) {
        if (span.start > cursor) {
            parts.push(content.slice(cursor, span.start));
        }
        parts.push(
            <mark
                key={`${span.start}-${span.end}`}
                className="rounded px-0.5 transition-colors cursor-help"
                style={{
                    background: `color-mix(in srgb, ${span.color ?? "var(--color-keyword)"} 20%, transparent)`,
                    color: span.color ?? "var(--color-keyword)",
                    borderBottom: `1.5px solid ${span.color ?? "var(--color-keyword)"}`,
                }}
                title={span.label}
            >
                {content.slice(span.start, span.end)}
            </mark>
        );
        cursor = span.end;
    }

    if (cursor < content.length) {
        parts.push(content.slice(cursor));
    }

    return parts;
}

export function MarkdownRenderer({
    content,
    highlights,
    maxHeight = 0,
    compact = false,
}: MarkdownRendererProps) {
    const hasHighlights = highlights && highlights.length > 0;

    return (
        <div
            className="markdown-renderer"
            style={{
                maxHeight: maxHeight > 0 ? maxHeight : undefined,
                overflowY: maxHeight > 0 ? "auto" : undefined,
                fontSize: compact ? 12 : 14,
                lineHeight: compact ? "1.5" : "1.7",
                color: "var(--text-secondary)",
            }}
        >
            <style>{`
                .markdown-renderer .md-h1 { font-size: 1.25em; font-weight: 700; color: var(--text-primary); margin: 1em 0 0.5em; }
                .markdown-renderer .md-h2 { font-size: 1.1em; font-weight: 600; color: var(--text-primary); margin: 0.8em 0 0.4em; }
                .markdown-renderer .md-h3 { font-size: 0.95em; font-weight: 600; color: var(--text-primary); margin: 0.6em 0 0.3em; }
                .markdown-renderer .md-p { margin: 0.4em 0; }
                .markdown-renderer .md-inline-code { font-family: "JetBrains Mono", monospace; font-size: 0.85em; padding: 1px 5px; border-radius: 4px; background: var(--bg-node-hover); color: var(--text-primary); }
                .markdown-renderer .md-code-block { font-family: "JetBrains Mono", monospace; font-size: 0.8em; padding: 12px 16px; border-radius: 8px; background: var(--bg-node); overflow-x: auto; margin: 0.5em 0; white-space: pre; line-height: 1.5; }
                .markdown-renderer .md-link { color: var(--color-info); text-decoration: none; }
                .markdown-renderer .md-link:hover { text-decoration: underline; }
                .markdown-renderer .md-blockquote { border-left: 3px solid var(--text-muted); padding-left: 12px; margin: 0.5em 0; color: var(--text-muted); font-style: italic; }
                .markdown-renderer .md-ul { padding-left: 1.2em; margin: 0.3em 0; }
                .markdown-renderer .md-li { margin: 0.15em 0; list-style-type: disc; }
                .markdown-renderer strong { color: var(--text-primary); }
            `}</style>

            {hasHighlights ? (
                <div>{applyHighlights(content, highlights!)}</div>
            ) : (
                <div dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }} />
            )}
        </div>
    );
}

import { Badge } from "../Badge";
import { DataTable, Column } from "../DataTable";
import { Accordion, AccordionItem } from "../Accordion";
import { FileText, Calendar, Hash, Tag, Type } from "lucide-react";

export interface ArticleKeyword {
    id: string;
    keyword: string;
    score: number;
    mentions: number;
}

export interface ArticleChunk {
    id: string;
    text: string;
    sequence: number;
}

export interface ArticleDetailPanelProps {
    title: string;
    domain?: string;
    dateIndexed?: string;
    wordCount?: number;
    keywords?: ArticleKeyword[];
    chunks?: ArticleChunk[];
    onClose?: () => void;
    onKeywordClick?: (kwId: string) => void;
}

export function ArticleDetailPanel({
    title,
    domain,
    dateIndexed,
    wordCount,
    keywords = [],
    chunks = [],
    onClose,
    onKeywordClick,
}: ArticleDetailPanelProps) {
    const keywordCols: Column<ArticleKeyword>[] = [
        {
            key: "keyword",
            header: "Keyword",
            render: ({ keyword }) => <span className="font-semibold text-xs text-[var(--text-primary)]">{keyword}</span>,
        },
        {
            key: "score",
            header: "TF-IDF",
            width: "60px",
            render: ({ score }) => <span className="font-mono text-[10px] text-[var(--color-info)]">{Number(score).toFixed(2)}</span>,
        },
        {
            key: "mentions",
            header: "Mentions",
            width: "70px",
            render: ({ mentions }) => <span className="font-mono text-[10px] text-[var(--text-muted)] text-center w-full block">{mentions}</span>,
        },
    ];

    const accordionItems: AccordionItem[] = chunks.map((c) => ({
        id: c.id,
        title: `Chunk #${c.sequence}`,
        badge: `${c.text.length} chars`,
        content: (
            <div className="text-[11px] leading-relaxed relative" style={{ color: "var(--text-primary)" }}>
                {c.text.length > 200 ? (
                    <>
                        {c.text.slice(0, 200)}...
                        <button className="text-[10px] ml-1 hover:underline" style={{ color: "var(--color-info)" }}>
                            Read more
                        </button>
                    </>
                ) : (
                    c.text
                )}
            </div>
        ),
    }));

    return (
        <div className="flex flex-col h-full overflow-hidden" style={{ background: "var(--bg-panel)", borderLeft: "1px solid var(--border-panel)" }}>
            {/* Header */}
            <div className="flex-shrink-0 flex items-start justify-between p-4" style={{ borderBottom: "1px solid var(--border-panel)" }}>
                <div className="flex flex-col gap-2 min-w-0 pr-4">
                    <div className="flex items-center gap-2">
                        <FileText size={16} style={{ color: "var(--color-article)", flexShrink: 0 }} />
                        <h2 className="text-base font-bold leading-tight" style={{ color: "var(--text-primary)" }}>
                            {title}
                        </h2>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-[10px]" style={{ color: "var(--text-muted)" }}>
                        {domain && <Badge variant="info">{domain}</Badge>}
                        {dateIndexed && (
                            <span className="flex items-center gap-1">
                                <Calendar size={10} /> {dateIndexed}
                            </span>
                        )}
                        {wordCount !== undefined && (
                            <span className="flex items-center gap-1">
                                <Type size={10} /> {wordCount} words
                            </span>
                        )}
                    </div>
                </div>
                {onClose && (
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-md hover:bg-white/5 transition-colors flex-shrink-0"
                        style={{ color: "var(--text-muted)" }}
                    >
                        ✕
                    </button>
                )}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6">

                {/* Keywords Table */}
                <div className="flex flex-col gap-3">
                    <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
                        <Tag size={12} /> Extracted Keywords ({keywords.length})
                    </div>
                    {keywords.length > 0 ? (
                        <div className="border rounded-xl overflow-hidden" style={{ borderColor: "var(--border-node)" }}>
                            <DataTable
                                columns={keywordCols}
                                data={keywords}
                                rowKey={(r) => r.id}
                                onRowClick={(r) => onKeywordClick?.(r.id)}
                            />
                        </div>
                    ) : (
                        <div className="p-4 rounded-xl text-center text-[10px]" style={{ background: "var(--bg-node-hover)", color: "var(--text-muted)" }}>
                            No keywords extracted yet.
                        </div>
                    )}
                </div>

                <div style={{ height: 1, borderBottom: "1px dashed var(--border-node)" }} />

                {/* Content Chunks */}
                <div className="flex flex-col gap-3">
                    <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
                        <Hash size={12} /> Formatted Chunks ({chunks.length})
                    </div>
                    {chunks.length > 0 ? (
                        <div className="border rounded-xl" style={{ borderColor: "var(--border-node)" }}>
                            <Accordion items={accordionItems} />
                        </div>
                    ) : (
                        <div className="p-4 rounded-xl text-center text-[10px]" style={{ background: "var(--bg-node-hover)", color: "var(--text-muted)" }}>
                            Article has not been chunked.
                        </div>
                    )}
                </div>

            </div>
        </div>
    );
}

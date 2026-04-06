import { useState } from "react";
import { Badge } from "../Badge";
import { DataTable, Column } from "../DataTable";
import { ConceptCard, ConceptCardProps } from "../ConceptCard";
import { SourceTextViewer } from "../SourceTextViewer";
import { Copy, Link as LinkIcon, ExternalLink } from "lucide-react";

export interface KeywordOccurrence {
    /** Unique ID of the occurrence */
    id: string;
    /** Source article title */
    articleTitle: string;
    /** Chunk text containing the keyword */
    text: string;
    /** Score (e.g. TF-IDF or frequency) */
    score?: number;
}

export interface KeywordDetailPanelProps {
    /** The keyword string */
    keyword: string;
    /** High-level domain or category if applicable */
    domain?: string;
    /** List of occurrences in source texts */
    occurrences?: KeywordOccurrence[];
    /** List of concepts that use this keyword */
    relatedConcepts?: (ConceptCardProps & { id: string })[];
    /** Total frequency across all documents */
    globalFrequency?: number;
    /** On close panel */
    onClose?: () => void;
}

export function KeywordDetailPanel({
    keyword,
    domain,
    occurrences = [],
    relatedConcepts = [],
    globalFrequency,
    onClose,
}: KeywordDetailPanelProps) {
    const [selectedOccId, setSelectedOccId] = useState<string | null>(occurrences[0]?.id || null);

    const activeOccurrence = occurrences.find((o) => o.id === selectedOccId);

    const chunkColumns: Column<KeywordOccurrence>[] = [
        {
            key: "articleTitle",
            header: "Source Article",
            render: (v) => (
                <div className="flex items-center gap-2">
                    <span className="text-xs truncate max-w-[120px]" style={{ color: "var(--text-primary)" }}>
                        {String(v)}
                    </span>
                </div>
            ),
        },
        {
            key: "score",
            header: "Score",
            width: "60px",
            render: (v) => (
                <span className="text-[10px] font-mono" style={{ color: "var(--color-info)" }}>
                    {v !== undefined ? Number(v).toFixed(2) : "-"}
                </span>
            ),
        },
    ];

    return (
        <div className="flex flex-col h-full overflow-hidden" style={{ background: "var(--bg-panel)", borderLeft: "1px solid var(--border-panel)" }}>
            {/* Header */}
            <div className="flex-shrink-0 flex items-center justify-between p-4" style={{ borderBottom: "1px solid var(--border-panel)" }}>
                <div className="flex flex-col gap-1.5">
                    <div className="flex items-center gap-2">
                        <h2 className="text-base font-bold truncate" style={{ color: "var(--text-primary)" }}>
                            {keyword}
                        </h2>
                        {domain && (
                            <Badge variant="info">
                                {domain}
                            </Badge>
                        )}
                    </div>
                    <div className="flex items-center gap-3 text-xs" style={{ color: "var(--text-muted)" }}>
                        {globalFrequency !== undefined && (
                            <span className="flex items-center gap-1">
                                <b>{globalFrequency}</b> mentions total
                            </span>
                        )}
                        <span className="flex items-center gap-1 hover:text-[var(--text-primary)] cursor-pointer transition-colors" title="Copy to clipboard">
                            <Copy size={12} />
                        </span>
                    </div>
                </div>
                {onClose && (
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-md hover:bg-white/5 transition-colors"
                        style={{ color: "var(--text-muted)" }}
                    >
                        ✕
                    </button>
                )}
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 flex flex-col gap-6">

                {/* Related Concepts */}
                {relatedConcepts.length > 0 && (
                    <div className="flex flex-col gap-3">
                        <div className="flex items-center justify-between">
                            <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
                                Mapped Concepts ({relatedConcepts.length})
                            </h3>
                            <button className="text-[10px] hover:underline" style={{ color: "var(--color-info)" }}>
                                Add mapping...
                            </button>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {relatedConcepts.map((concept) => (
                                <div key={concept.id} className="relative group/card scale-95 origin-top-left hover:scale-100 transition-transform">
                                    <ConceptCard {...concept} />
                                    <div className="absolute top-2 right-2 opacity-0 group-hover/card:opacity-100 transition-opacity flex gap-1">
                                        <button className="p-1 rounded bg-[rgba(0,0,0,0.5)] hover:bg-[var(--color-info)] text-white backdrop-blur-md transition-colors">
                                            <LinkIcon size={12} />
                                        </button>
                                        <button className="p-1 rounded bg-[rgba(0,0,0,0.5)] hover:bg-[var(--text-primary)] text-white backdrop-blur-md transition-colors">
                                            <ExternalLink size={12} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <div style={{ height: 1, borderBottom: "1px dashed var(--border-node)" }} />

                {/* Source Occurrences */}
                <div className="flex flex-col gap-4">
                    <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
                        Source Occurrences ({occurrences.length})
                    </h3>

                    {occurrences.length === 0 ? (
                        <div className="p-4 rounded-xl text-center text-xs" style={{ background: "var(--bg-node-hover)", color: "var(--text-muted)" }}>
                            No text chunks found linking to this keyword.
                        </div>
                    ) : (
                        <div className="flex flex-col gap-4">
                            {/* Occurrences Table */}
                            <div className="border rounded-xl overflow-hidden" style={{ borderColor: "var(--border-node)" }}>
                                <DataTable
                                    columns={chunkColumns}
                                    data={occurrences}
                                    onRowClick={(row) => setSelectedOccId(row.id)}
                                    rowKey={(row) => row.id}
                                />
                            </div>

                            {/* Active Chunk Viewer */}
                            {activeOccurrence && (
                                <div className="flex flex-col gap-2 rounded-xl" style={{}}>
                                    <div className="h-[250px] rounded-lg overflow-hidden border bg-[var(--bg-canvas)] shadow-xl" style={{ borderColor: "var(--border-node)" }}>
                                        <SourceTextViewer
                                            currentText={activeOccurrence.text}
                                            snapshotText={activeOccurrence.text}
                                            articleTitle={activeOccurrence.articleTitle}
                                            defaultTab="highlights"
                                            highlights={[{
                                                start: activeOccurrence.text.toLowerCase().indexOf(keyword.toLowerCase()) !== -1
                                                    ? activeOccurrence.text.toLowerCase().indexOf(keyword.toLowerCase())
                                                    : 0,
                                                end: activeOccurrence.text.toLowerCase().indexOf(keyword.toLowerCase()) !== -1
                                                    ? activeOccurrence.text.toLowerCase().indexOf(keyword.toLowerCase()) + keyword.length
                                                    : keyword.length,
                                                color: "var(--color-warning)",
                                                label: "Match"
                                            }]}
                                        />
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

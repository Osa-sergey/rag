import { useState } from "react";
import { Badge } from "../Badge";
import { DataTable, Column } from "../DataTable";
import { Check, X, Tag } from "lucide-react";

export interface ReviewKeyword {
    id: string;
    keyword: string;
    score: number;
    mentions: number;
    sourceArticles: number;
    status: "pending" | "approved" | "rejected";
}

export interface KeywordReviewListProps {
    keywords: ReviewKeyword[];
    onApprove?: (ids: string[]) => void;
    onReject?: (ids: string[]) => void;
    onKeywordClick?: (id: string) => void;
}

export function KeywordReviewList({
    keywords,
    onApprove,
    onReject,
    onKeywordClick,
}: KeywordReviewListProps) {
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

    const toggleSelection = (id: string) => {
        const next = new Set(selectedIds);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        setSelectedIds(next);
    };

    const toggleAll = () => {
        if (selectedIds.size === pendingKeywords.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(pendingKeywords.map((k) => k.id)));
        }
    };

    const pendingKeywords = keywords.filter((k) => k.status === "pending");

    const columns: Column<ReviewKeyword>[] = [
        {
            key: "select",
            header: "✓",
            width: "40px",
            render: (row) => (
                <div
                    className="w-4 h-4 rounded border flex items-center justify-center cursor-pointer transition-colors"
                    style={{
                        background: selectedIds.has(row.id) ? "var(--color-info)" : "transparent",
                        borderColor: selectedIds.has(row.id) ? "var(--color-info)" : "var(--border-node)",
                    }}
                    onClick={(e) => { e.stopPropagation(); toggleSelection(row.id); }}
                >
                    {selectedIds.has(row.id) && <Check size={10} color="white" strokeWidth={3} />}
                </div>
            )
        },
        {
            key: "keyword",
            header: "Extracted Keyword",
            render: ({ keyword }) => (
                <span className="font-semibold text-xs text-[var(--text-primary)]">{keyword}</span>
            ),
        },
        {
            key: "score",
            header: "Avg Score",
            width: "80px",
            render: ({ score }) => (
                <span className="font-mono text-[10px] text-[var(--color-info)]">{Number(score).toFixed(2)}</span>
            ),
        },
        {
            key: "mentions",
            header: "Mentions",
            width: "70px",
            render: ({ mentions }) => (
                <div className="flex justify-center w-full">
                    <Badge variant="warning">{mentions}</Badge>
                </div>
            ),
        },
        {
            key: "sourceArticles",
            header: "Sources",
            width: "70px",
            render: ({ sourceArticles }) => (
                <div className="flex justify-center w-full">
                    <span className="text-[10px] font-mono text-[var(--text-muted)]">{sourceArticles}</span>
                </div>
            ),
        },
        {
            key: "actions",
            header: "Action",
            width: "90px",
            render: (row) => (
                <div className="flex items-center gap-1 justify-end w-full">
                    <button
                        onClick={(e) => { e.stopPropagation(); onApprove?.([row.id]); }}
                        className="p-1 rounded-md transition-colors hover:bg-[var(--color-success)] hover:text-white"
                        style={{ color: "var(--color-success)" }}
                        title="Approve"
                    >
                        <Check size={14} />
                    </button>
                    <button
                        onClick={(e) => { e.stopPropagation(); onReject?.([row.id]); }}
                        className="p-1 rounded-md transition-colors hover:bg-[var(--color-error)] hover:text-white"
                        style={{ color: "var(--color-error)" }}
                        title="Reject"
                    >
                        <X size={14} />
                    </button>
                </div>
            ),
        }
    ];

    const allSelected = pendingKeywords.length > 0 && selectedIds.size === pendingKeywords.length;

    return (
        <div className="flex flex-col h-full rounded-xl overflow-hidden shadow-2xl pb-2" style={{ background: "var(--bg-panel)", border: "1px solid var(--border-panel)" }}>
            {/* Header */}
            <div className="flex-shrink-0 flex items-center justify-between p-4 px-5 border-b" style={{ borderColor: "var(--border-panel)" }}>
                <div className="flex items-center gap-2">
                    <Tag size={16} style={{ color: "var(--color-info)" }} />
                    <h2 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
                        Keyword Extraction Review
                    </h2>
                    {pendingKeywords.length > 0 && (
                        <Badge variant="warning">{pendingKeywords.length} pending</Badge>
                    )}
                </div>

                {selectedIds.size > 0 && (
                    <div className="flex items-center gap-2 animate-in fade-in zoom-in-95">
                        <span className="text-[10px] font-semibold" style={{ color: "var(--text-muted)" }}>
                            {selectedIds.size} selected
                        </span>
                        <button
                            onClick={() => { onApprove?.(Array.from(selectedIds)); setSelectedIds(new Set()); }}
                            className="flex items-center gap-1 px-3 py-1.5 rounded text-[10px] font-bold text-white transition-colors"
                            style={{ background: "var(--color-success)" }}
                        >
                            <Check size={12} strokeWidth={3} /> Approve
                        </button>
                        <button
                            onClick={() => { onReject?.(Array.from(selectedIds)); setSelectedIds(new Set()); }}
                            className="flex items-center gap-1 px-3 py-1.5 rounded text-[10px] font-bold text-white transition-colors"
                            style={{ background: "var(--color-error)" }}
                        >
                            <X size={12} strokeWidth={3} /> Reject
                        </button>
                    </div>
                )}
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
                {pendingKeywords.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-12 text-center rounded-xl" style={{ border: "1px dashed var(--border-node)" }}>
                        <div className="w-12 h-12 rounded-full mb-3 flex items-center justify-center" style={{ background: "rgba(34, 197, 94, 0.1)", color: "var(--color-success)" }}>
                            <Check size={20} strokeWidth={3} />
                        </div>
                        <h3 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>All caught up!</h3>
                        <p className="text-xs max-w-[200px]" style={{ color: "var(--text-muted)" }}>There are no pending keywords to review right now.</p>
                    </div>
                ) : (
                    <div className="flex flex-col gap-2">
                        {/* Select All Row */}
                        <div className="flex items-center px-4 py-2 border-b" style={{ borderColor: "var(--border-node)" }}>
                            <div
                                className="w-4 h-4 rounded border flex items-center justify-center cursor-pointer transition-colors"
                                style={{
                                    background: allSelected ? "var(--color-info)" : "transparent",
                                    borderColor: allSelected ? "var(--color-info)" : "var(--border-node)",
                                }}
                                onClick={toggleAll}
                            >
                                {allSelected && <Check size={10} color="white" strokeWidth={3} />}
                            </div>
                            <span className="text-[10px] font-bold tracking-wider uppercase ml-3" style={{ color: "var(--text-secondary)" }}>
                                Select All ({pendingKeywords.length})
                            </span>
                        </div>

                        {/* Table */}
                        <div className="rounded-xl overflow-hidden border" style={{ borderColor: "var(--border-node)" }}>
                            <DataTable
                                columns={columns}
                                data={pendingKeywords}
                                rowKey={(r) => r.id}
                                onRowClick={(r) => onKeywordClick?.(r.id)}
                            />
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

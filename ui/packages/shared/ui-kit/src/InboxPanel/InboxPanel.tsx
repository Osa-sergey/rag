import React from "react";
import { Inbox, Clock, ChevronRight, AlertTriangle, Eye } from "lucide-react";

export interface InboxItem {
    id: string;
    conceptName: string;
    domain?: string;
    staleDays: number;
    severity: "low" | "medium" | "high";
    sourceCount?: number;
}

export interface InboxPanelProps {
    /** Stale items */
    items: InboxItem[];
    /** On review click */
    onReview?: (item: InboxItem) => void;
}

const severityColors: Record<string, string> = {
    low: "var(--color-warning)",
    medium: "var(--color-warning)",
    high: "var(--color-error)",
};

export function InboxPanel({ items, onReview }: InboxPanelProps) {
    if (items.length === 0) {
        return (
            <div
                className="rounded-xl flex flex-col items-center justify-center py-12 gap-3"
                style={{ background: "var(--bg-panel)", border: "var(--border-node)", width: 340 }}
            >
                <Inbox size={32} style={{ color: "var(--color-success)", opacity: 0.5 }} />
                <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Inbox clear!</span>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>No stale concepts to review</span>
            </div>
        );
    }

    return (
        <div
            className="rounded-xl overflow-hidden flex flex-col"
            style={{ background: "var(--bg-panel)", border: "var(--border-node)", width: 340 }}
        >
            {/* Header */}
            <div className="px-4 py-2.5 flex items-center gap-2" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <Inbox size={13} style={{ color: "var(--text-muted)" }} />
                <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>Review Inbox</span>
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full ml-auto" style={{ background: "rgba(239,68,68,0.12)", color: "var(--color-error)" }}>
                    {items.length}
                </span>
            </div>

            {/* Items */}
            <div className="flex flex-col overflow-y-auto" style={{ maxHeight: 400 }}>
                {items.map((item) => (
                    <div
                        key={item.id}
                        className="flex items-center gap-3 px-4 py-2.5 hover:bg-white/3 transition-colors"
                        style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}
                    >
                        <AlertTriangle size={12} className="flex-shrink-0" style={{ color: severityColors[item.severity] }} />

                        <div className="flex-1 min-w-0">
                            <div className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>
                                {item.conceptName}
                            </div>
                            <div className="flex items-center gap-2 text-[9px] mt-0.5" style={{ color: "var(--text-muted)" }}>
                                {item.domain && <span>{item.domain}</span>}
                                <span className="flex items-center gap-0.5"><Clock size={8} /> {item.staleDays}d ago</span>
                                {item.sourceCount && <span>{item.sourceCount} sources</span>}
                            </div>
                        </div>

                        <button
                            onClick={() => onReview?.(item)}
                            className="flex items-center gap-1 px-2 py-1 rounded-lg text-[9px] font-semibold transition-colors hover:bg-white/5"
                            style={{ color: "var(--color-info)" }}
                        >
                            <Eye size={10} /> Review
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}

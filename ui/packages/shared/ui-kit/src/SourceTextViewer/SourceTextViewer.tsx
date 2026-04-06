import React, { useState } from "react";
import { DiffViewer } from "../DiffViewer/DiffViewer";
import { MarkdownRenderer, HighlightSpan } from "../MarkdownRenderer/MarkdownRenderer";
import { ArrowLeftRight, Eye, FileText, Highlighter } from "lucide-react";

export type SourceTextTab = "snapshot" | "current" | "diff" | "highlights";

export interface SourceTextViewerProps {
    /** Snapshot text (at concept creation time K2) */
    snapshotText: string;
    /** Current text (latest version) */
    currentText: string;
    /** Snapshot date */
    snapshotDate?: string;
    /** Current date */
    currentDate?: string;
    /** Source article title */
    articleTitle?: string;
    /** Keyword highlights for the highlights tab */
    highlights?: HighlightSpan[];
    /** Default active tab */
    defaultTab?: SourceTextTab;
}

const tabs: Array<{ key: SourceTextTab; label: string; icon: React.ReactNode }> = [
    { key: "snapshot", label: "Snapshot", icon: <FileText size={12} /> },
    { key: "current", label: "Current", icon: <Eye size={12} /> },
    { key: "diff", label: "Diff", icon: <ArrowLeftRight size={12} /> },
    { key: "highlights", label: "Highlights", icon: <Highlighter size={12} /> },
];

export function SourceTextViewer({
    snapshotText,
    currentText,
    snapshotDate,
    currentDate,
    articleTitle,
    highlights = [],
    defaultTab = "snapshot",
}: SourceTextViewerProps) {
    const [activeTab, setActiveTab] = useState<SourceTextTab>(defaultTab);

    return (
        <div
            className="rounded-xl overflow-hidden flex flex-col"
            style={{ background: "var(--bg-node)", border: "var(--border-node)" }}
        >
            {/* Header */}
            <div
                className="flex items-center justify-between px-4 py-2.5 gap-2"
                style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
            >
                <div className="flex items-center gap-2 min-w-0">
                    <FileText size={14} style={{ color: "var(--color-article)" }} />
                    {articleTitle && (
                        <span className="text-xs font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                            {articleTitle}
                        </span>
                    )}
                </div>

                {/* Tab bar */}
                <div className="flex gap-0.5 flex-shrink-0">
                    {tabs.map((tab) => (
                        <button
                            key={tab.key}
                            onClick={() => setActiveTab(tab.key)}
                            className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-colors"
                            style={{
                                background: activeTab === tab.key ? "rgba(99,102,241,0.12)" : "transparent",
                                color: activeTab === tab.key ? "var(--color-info)" : "var(--text-muted)",
                            }}
                        >
                            {tab.icon}
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Content */}
            <div className="overflow-y-auto" style={{ maxHeight: 400 }}>
                {activeTab === "snapshot" && (
                    <div className="p-4">
                        {snapshotDate && (
                            <div className="flex items-center gap-2 mb-3">
                                <span className="text-[10px] font-mono px-2 py-0.5 rounded" style={{ background: "var(--bg-node-hover)", color: "var(--text-muted)" }}>
                                    📸 Snapshot: {snapshotDate}
                                </span>
                            </div>
                        )}
                        <MarkdownRenderer content={snapshotText} compact />
                    </div>
                )}

                {activeTab === "current" && (
                    <div className="p-4">
                        {currentDate && (
                            <div className="flex items-center gap-2 mb-3">
                                <span className="text-[10px] font-mono px-2 py-0.5 rounded" style={{ background: "rgba(34,197,94,0.08)", color: "var(--color-success)" }}>
                                    🟢 Current: {currentDate}
                                </span>
                            </div>
                        )}
                        <MarkdownRenderer content={currentText} compact />
                    </div>
                )}

                {activeTab === "diff" && (
                    <DiffViewer
                        oldText={snapshotText}
                        newText={currentText}
                        oldLabel={`Snapshot${snapshotDate ? ` (${snapshotDate})` : ""}`}
                        newLabel={`Current${currentDate ? ` (${currentDate})` : ""}`}
                        allowModeToggle
                    />
                )}

                {activeTab === "highlights" && (
                    <div className="p-4">
                        <MarkdownRenderer content={currentText} highlights={highlights} compact />
                        {highlights.length > 0 && (
                            <div className="mt-3 pt-2 flex flex-wrap gap-1.5" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                                {highlights.map((h, i) => (
                                    <span
                                        key={i}
                                        className="text-[10px] px-1.5 py-0.5 rounded"
                                        style={{
                                            background: `color-mix(in srgb, ${h.color ?? "var(--color-keyword)"} 12%, transparent)`,
                                            color: h.color ?? "var(--color-keyword)",
                                        }}
                                    >
                                        {h.label ?? `[${h.start}:${h.end}]`}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

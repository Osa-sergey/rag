import React, { useState } from "react";
import { GitCompare, ChevronRight, Check, X, Plus, Minus } from "lucide-react";

export interface DiffLine {
    type: "added" | "removed" | "unchanged";
    content: string;
}

export interface ExpandPanelProps {
    /** From version */
    fromVersion: string;
    /** To version */
    toVersion: string;
    /** Concept name */
    conceptName: string;
    /** Diff lines */
    diffLines?: DiffLine[];
    /** Candidate keywords for review */
    candidateKeywords?: Array<{ keyword: string; checked?: boolean }>;
    /** On keyword toggle */
    onKeywordToggle?: (keyword: string, checked: boolean) => void;
    /** On accept expansion */
    onAccept?: () => void;
    /** On reject */
    onReject?: () => void;
}

export function ExpandPanel({
    fromVersion,
    toVersion,
    conceptName,
    diffLines = [],
    candidateKeywords = [],
    onKeywordToggle,
    onAccept,
    onReject,
}: ExpandPanelProps) {
    const [checkedKws, setCheckedKws] = useState<Set<string>>(
        new Set(candidateKeywords.filter((k) => k.checked).map((k) => k.keyword))
    );

    const toggleKw = (kw: string) => {
        setCheckedKws((prev) => {
            const next = new Set(prev);
            if (next.has(kw)) next.delete(kw); else next.add(kw);
            onKeywordToggle?.(kw, next.has(kw));
            return next;
        });
    };

    return (
        <div
            className="rounded-xl overflow-hidden flex flex-col"
            style={{ background: "var(--bg-panel)", border: "var(--border-node)", width: 400 }}
        >
            {/* Header */}
            <div className="px-4 py-3 flex items-center gap-2" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <GitCompare size={14} style={{ color: "var(--color-info)" }} />
                <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>{conceptName}</span>
                <span className="text-[9px] font-mono ml-auto px-2 py-0.5 rounded" style={{ background: "rgba(99,102,241,0.1)", color: "var(--color-info)" }}>
                    {fromVersion} → {toVersion}
                </span>
            </div>

            {/* Diff */}
            {diffLines.length > 0 && (
                <div className="px-2 py-2 font-mono text-[10px] overflow-x-auto" style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", maxHeight: 200 }}>
                    {diffLines.map((line, i) => (
                        <div
                            key={i}
                            className="flex items-center gap-1 px-2 py-0.5 rounded"
                            style={{
                                background: line.type === "added" ? "rgba(34,197,94,0.06)" : line.type === "removed" ? "rgba(239,68,68,0.06)" : "transparent",
                                color: line.type === "added" ? "var(--color-success)" : line.type === "removed" ? "var(--color-error)" : "var(--text-secondary)",
                            }}
                        >
                            {line.type === "added" && <Plus size={9} className="flex-shrink-0" />}
                            {line.type === "removed" && <Minus size={9} className="flex-shrink-0" />}
                            {line.type === "unchanged" && <span className="w-[9px] flex-shrink-0" />}
                            <span>{line.content}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Candidate keywords */}
            {candidateKeywords.length > 0 && (
                <div className="px-4 py-2" style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <div className="text-[9px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>
                        Candidate Keywords ({checkedKws.size}/{candidateKeywords.length})
                    </div>
                    <div className="flex flex-wrap gap-1">
                        {candidateKeywords.map((kw) => {
                            const isChecked = checkedKws.has(kw.keyword);
                            return (
                                <button
                                    key={kw.keyword}
                                    onClick={() => toggleKw(kw.keyword)}
                                    className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] transition-all"
                                    style={{
                                        background: isChecked ? "rgba(34,197,94,0.12)" : "var(--bg-node)",
                                        color: isChecked ? "var(--color-success)" : "var(--text-muted)",
                                        border: `1px solid ${isChecked ? "rgba(34,197,94,0.3)" : "rgba(255,255,255,0.06)"}`,
                                    }}
                                >
                                    {isChecked && <Check size={8} />}
                                    {kw.keyword}
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Actions */}
            <div className="px-4 py-2 flex items-center gap-2 justify-end">
                <button onClick={onReject} className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[10px] font-medium transition-colors hover:bg-red-500/10" style={{ color: "var(--color-error)" }}>
                    <X size={10} /> Reject
                </button>
                <button onClick={onAccept} className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[10px] font-semibold transition-colors hover:bg-green-500/20" style={{ background: "rgba(34,197,94,0.1)", color: "var(--color-success)" }}>
                    <Check size={10} /> Accept
                </button>
            </div>
        </div>
    );
}

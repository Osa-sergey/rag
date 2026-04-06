import React, { useState } from "react";
import { ArrowLeftRight, AlignLeft, Equal } from "lucide-react";

export type DiffViewMode = "inline" | "side-by-side";

export interface DiffLine {
    type: "added" | "removed" | "unchanged";
    content: string;
    lineNumber?: number;
}

export interface DiffViewerProps {
    /** Title (e.g. "v2 → v3") */
    title?: string;
    /** Left content (old) */
    oldText: string;
    /** Right content (new) */
    newText: string;
    /** Old version label */
    oldLabel?: string;
    /** New version label */
    newLabel?: string;
    /** View mode */
    mode?: DiffViewMode;
    /** Allow toggle between modes */
    allowModeToggle?: boolean;
    /** Language hint for syntax coloring */
    language?: string;
}

function computeDiff(oldText: string, newText: string): DiffLine[] {
    const oldLines = oldText.split("\n");
    const newLines = newText.split("\n");
    const result: DiffLine[] = [];
    const maxLen = Math.max(oldLines.length, newLines.length);

    for (let i = 0; i < maxLen; i++) {
        const oldLine = oldLines[i];
        const newLine = newLines[i];

        if (oldLine === undefined && newLine !== undefined) {
            result.push({ type: "added", content: newLine, lineNumber: i + 1 });
        } else if (newLine === undefined && oldLine !== undefined) {
            result.push({ type: "removed", content: oldLine, lineNumber: i + 1 });
        } else if (oldLine !== newLine) {
            result.push({ type: "removed", content: oldLine!, lineNumber: i + 1 });
            result.push({ type: "added", content: newLine!, lineNumber: i + 1 });
        } else {
            result.push({ type: "unchanged", content: oldLine!, lineNumber: i + 1 });
        }
    }

    return result;
}

const lineColors: Record<DiffLine["type"], { bg: string; text: string; prefix: string }> = {
    added: { bg: "rgba(34,197,94,0.08)", text: "var(--color-success)", prefix: "+" },
    removed: { bg: "rgba(239,68,68,0.08)", text: "var(--color-error)", prefix: "−" },
    unchanged: { bg: "transparent", text: "var(--text-muted)", prefix: " " },
};

export function DiffViewer({
    title,
    oldText,
    newText,
    oldLabel = "Old",
    newLabel = "New",
    mode: initialMode = "inline",
    allowModeToggle = true,
    language,
}: DiffViewerProps) {
    const [mode, setMode] = useState<DiffViewMode>(initialMode);
    const diff = computeDiff(oldText, newText);
    const hasChanges = diff.some((l) => l.type !== "unchanged");
    const addedCount = diff.filter((l) => l.type === "added").length;
    const removedCount = diff.filter((l) => l.type === "removed").length;

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
                    <ArrowLeftRight size={14} style={{ color: "var(--text-muted)" }} />
                    {title && <span className="text-xs font-semibold truncate" style={{ color: "var(--text-primary)" }}>{title}</span>}
                    {hasChanges && (
                        <div className="flex items-center gap-2 text-[10px] font-mono">
                            <span style={{ color: "var(--color-success)" }}>+{addedCount}</span>
                            <span style={{ color: "var(--color-error)" }}>−{removedCount}</span>
                        </div>
                    )}
                </div>

                {allowModeToggle && (
                    <div className="flex gap-0.5 flex-shrink-0">
                        <button
                            onClick={() => setMode("inline")}
                            className="p-1 rounded transition-colors"
                            style={{
                                background: mode === "inline" ? "rgba(99,102,241,0.12)" : "transparent",
                                color: mode === "inline" ? "var(--color-info)" : "var(--text-muted)",
                            }}
                            title="Inline"
                        >
                            <AlignLeft size={12} />
                        </button>
                        <button
                            onClick={() => setMode("side-by-side")}
                            className="p-1 rounded transition-colors"
                            style={{
                                background: mode === "side-by-side" ? "rgba(99,102,241,0.12)" : "transparent",
                                color: mode === "side-by-side" ? "var(--color-info)" : "var(--text-muted)",
                            }}
                            title="Side by side"
                        >
                            <Equal size={12} />
                        </button>
                    </div>
                )}
            </div>

            {/* No changes */}
            {!hasChanges && (
                <div className="flex items-center justify-center py-8 text-xs" style={{ color: "var(--text-muted)" }}>
                    ✓ No changes — contents are identical
                </div>
            )}

            {/* Inline mode */}
            {hasChanges && mode === "inline" && (
                <div className="overflow-x-auto">
                    <table className="w-full text-xs font-mono" style={{ borderCollapse: "collapse" }}>
                        <tbody>
                            {diff.map((line, i) => {
                                const c = lineColors[line.type];
                                return (
                                    <tr key={i} style={{ background: c.bg }}>
                                        <td className="w-8 text-right px-2 py-0.5 select-none" style={{ color: "var(--text-muted)", opacity: 0.4 }}>
                                            {line.lineNumber}
                                        </td>
                                        <td className="w-4 text-center py-0.5 select-none font-bold" style={{ color: c.text }}>
                                            {c.prefix}
                                        </td>
                                        <td className="pl-2 pr-4 py-0.5 whitespace-pre" style={{ color: line.type === "unchanged" ? "var(--text-secondary)" : c.text }}>
                                            {line.content}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Side-by-side mode */}
            {hasChanges && mode === "side-by-side" && (
                <div className="flex overflow-x-auto">
                    {/* Old */}
                    <div className="flex-1 min-w-0" style={{ borderRight: "1px solid rgba(255,255,255,0.06)" }}>
                        <div className="px-3 py-1 text-[10px] font-semibold" style={{ color: "var(--text-muted)", background: "rgba(239,68,68,0.04)" }}>{oldLabel}</div>
                        <div className="text-xs font-mono">
                            {diff.filter((l) => l.type !== "added").map((line, i) => {
                                const c = lineColors[line.type];
                                return (
                                    <div key={i} className="flex" style={{ background: c.bg }}>
                                        <span className="w-8 text-right px-2 py-0.5 select-none" style={{ color: "var(--text-muted)", opacity: 0.4 }}>{line.lineNumber}</span>
                                        <span className="pl-2 pr-4 py-0.5 whitespace-pre" style={{ color: line.type === "unchanged" ? "var(--text-secondary)" : c.text }}>{line.content}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                    {/* New */}
                    <div className="flex-1 min-w-0">
                        <div className="px-3 py-1 text-[10px] font-semibold" style={{ color: "var(--text-muted)", background: "rgba(34,197,94,0.04)" }}>{newLabel}</div>
                        <div className="text-xs font-mono">
                            {diff.filter((l) => l.type !== "removed").map((line, i) => {
                                const c = lineColors[line.type];
                                return (
                                    <div key={i} className="flex" style={{ background: c.bg }}>
                                        <span className="w-8 text-right px-2 py-0.5 select-none" style={{ color: "var(--text-muted)", opacity: 0.4 }}>{line.lineNumber}</span>
                                        <span className="pl-2 pr-4 py-0.5 whitespace-pre" style={{ color: line.type === "unchanged" ? "var(--text-secondary)" : c.text }}>{line.content}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

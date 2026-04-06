import React, { useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronRight, X, RefreshCw } from "lucide-react";

export interface ValidationError {
    id: string;
    severity: "error" | "warning";
    message: string;
    nodeId?: string;
    nodeName?: string;
    field?: string;
}

export interface ValidationOverlayProps {
    /** Errors list */
    errors: ValidationError[];
    /** On click error */
    onErrorClick?: (error: ValidationError) => void;
    /** On dismiss */
    onDismiss?: () => void;
    /** On re-validate */
    onRevalidate?: () => void;
}

export function ValidationOverlay({
    errors,
    onErrorClick,
    onDismiss,
    onRevalidate,
}: ValidationOverlayProps) {
    const [expanded, setExpanded] = useState(true);
    const errorCount = errors.filter((e) => e.severity === "error").length;
    const warnCount = errors.filter((e) => e.severity === "warning").length;
    const allClear = errors.length === 0;

    return (
        <div
            className="rounded-xl overflow-hidden"
            style={{
                background: "var(--bg-panel)",
                border: allClear ? "1px solid rgba(34,197,94,0.2)" : "1px solid rgba(239,68,68,0.2)",
                width: 300,
            }}
        >
            {/* Header */}
            <div
                className="flex items-center justify-between px-3 py-2"
                style={{ borderBottom: expanded ? "1px solid rgba(255,255,255,0.06)" : "none" }}
            >
                <button onClick={() => setExpanded(!expanded)} className="flex items-center gap-2">
                    <ChevronRight
                        size={12}
                        className="transition-transform"
                        style={{ transform: expanded ? "rotate(90deg)" : "none", color: "var(--text-muted)" }}
                    />
                    {allClear ? (
                        <div className="flex items-center gap-1.5">
                            <CheckCircle2 size={13} style={{ color: "var(--color-success)" }} />
                            <span className="text-xs font-semibold" style={{ color: "var(--color-success)" }}>All checks passed</span>
                        </div>
                    ) : (
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>Validation</span>
                            {errorCount > 0 && (
                                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full" style={{ background: "rgba(239,68,68,0.12)", color: "var(--color-error)" }}>
                                    {errorCount} error{errorCount > 1 ? "s" : ""}
                                </span>
                            )}
                            {warnCount > 0 && (
                                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full" style={{ background: "rgba(245,158,11,0.12)", color: "var(--color-warning)" }}>
                                    {warnCount} warn
                                </span>
                            )}
                        </div>
                    )}
                </button>
                <div className="flex items-center gap-1">
                    {onRevalidate && (
                        <button onClick={onRevalidate} className="p-1 rounded hover:bg-white/5 transition-colors" style={{ color: "var(--text-muted)" }} title="Re-validate">
                            <RefreshCw size={11} />
                        </button>
                    )}
                    {onDismiss && (
                        <button onClick={onDismiss} className="p-1 rounded hover:bg-white/5 transition-colors" style={{ color: "var(--text-muted)" }}>
                            <X size={11} />
                        </button>
                    )}
                </div>
            </div>

            {/* Error list */}
            {expanded && errors.length > 0 && (
                <div className="flex flex-col max-h-[200px] overflow-y-auto">
                    {errors.map((err) => (
                        <button
                            key={err.id}
                            onClick={() => onErrorClick?.(err)}
                            className="flex items-start gap-2 px-3 py-2 text-left hover:bg-white/3 transition-colors"
                            style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}
                        >
                            <AlertTriangle
                                size={11}
                                className="flex-shrink-0 mt-0.5"
                                style={{ color: err.severity === "error" ? "var(--color-error)" : "var(--color-warning)" }}
                            />
                            <div className="flex-1 min-w-0">
                                <div className="text-[10px] truncate" style={{ color: "var(--text-primary)" }}>
                                    {err.message}
                                </div>
                                {err.nodeName && (
                                    <div className="text-[9px] font-mono mt-0.5" style={{ color: "var(--text-muted)" }}>
                                        → {err.nodeName}{err.field ? `.${err.field}` : ""}
                                    </div>
                                )}
                            </div>
                            <ChevronRight size={10} className="flex-shrink-0 mt-1" style={{ color: "var(--text-muted)", opacity: 0.5 }} />
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

import React from "react";

export interface NodeTooltipProps {
    /** Node name */
    name: string;
    /** Node type label */
    type?: string;
    /** Type color */
    typeColor?: string;
    /** Module path (e.g. raptor.parse.ArticleParser) */
    module?: string;
    /** Status */
    status?: "idle" | "running" | "success" | "failed";
    /** Stats entries */
    stats?: Array<{ label: string; value: string | number }>;
    /** Loading state */
    loading?: boolean;
}

const statusConfig: Record<string, { label: string; color: string }> = {
    idle: { label: "Idle", color: "var(--text-muted)" },
    running: { label: "Running", color: "var(--color-info)" },
    success: { label: "Success", color: "var(--color-success)" },
    failed: { label: "Failed", color: "var(--color-error)" },
};

export function NodeTooltip({
    name,
    type,
    typeColor,
    module,
    status,
    stats = [],
    loading = false,
}: NodeTooltipProps) {
    if (loading) {
        return (
            <div className="px-3 py-2.5 rounded-xl" style={{ background: "var(--bg-panel)", border: "var(--border-node)", minWidth: 160 }}>
                <div className="flex flex-col gap-1.5">
                    <div className="h-3 w-24 rounded" style={{ background: "var(--bg-node-hover)" }} />
                    <div className="h-2 w-32 rounded" style={{ background: "var(--bg-node-hover)", opacity: 0.6 }} />
                    <div className="h-2 w-20 rounded" style={{ background: "var(--bg-node-hover)", opacity: 0.4 }} />
                </div>
            </div>
        );
    }

    const st = status ? statusConfig[status] : undefined;

    return (
        <div
            className="rounded-xl overflow-hidden"
            style={{
                background: "var(--bg-panel)",
                border: "var(--border-node)",
                boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
                minWidth: 160,
                maxWidth: 260,
            }}
        >
            <div className="px-3 py-2 flex flex-col gap-1">
                {/* Name + type */}
                <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                        {name}
                    </span>
                    {type && (
                        <span
                            className="text-[9px] font-bold px-1.5 py-0.5 rounded flex-shrink-0"
                            style={{
                                background: `color-mix(in srgb, ${typeColor ?? "var(--color-info)"} 15%, transparent)`,
                                color: typeColor ?? "var(--color-info)",
                            }}
                        >
                            {type}
                        </span>
                    )}
                </div>

                {/* Module */}
                {module && (
                    <span className="text-[10px] font-mono truncate" style={{ color: "var(--text-muted)" }}>
                        {module}
                    </span>
                )}

                {/* Status */}
                {st && (
                    <div className="flex items-center gap-1.5 mt-0.5">
                        <span
                            className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                            style={{
                                background: st.color,
                                animation: status === "running" ? "pulse 1.5s infinite" : "none",
                            }}
                        />
                        <span className="text-[10px]" style={{ color: st.color }}>{st.label}</span>
                    </div>
                )}
            </div>

            {/* Stats */}
            {stats.length > 0 && (
                <div
                    className="px-3 py-1.5 flex flex-col gap-0.5"
                    style={{ borderTop: "1px solid rgba(255,255,255,0.06)", background: "rgba(0,0,0,0.1)" }}
                >
                    {stats.map((s) => (
                        <div key={s.label} className="flex items-center justify-between text-[10px]">
                            <span style={{ color: "var(--text-muted)" }}>{s.label}</span>
                            <span className="font-mono" style={{ color: "var(--text-primary)" }}>{s.value}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

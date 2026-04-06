import { Component, Hash, FileText, Tag, Link2, AlertTriangle } from "lucide-react";

export type KBNodeType = "article" | "keyword" | "concept";

export interface KBNodeProps {
    /** Node type */
    type: KBNodeType;
    /** Label */
    label: string;
    /** Score (for keyword sizing) */
    score?: number;
    /** Count (keywords/sources/chunks) */
    count?: number;
    /** Version label */
    version?: string;
    /** Is selected */
    selected?: boolean;
    /** Is stale */
    stale?: boolean;
    /** On click */
    onClick?: () => void;
}

const typeStyles: Record<KBNodeType, { color: string; bg: string }> = {
    article: { color: "var(--color-article, #3b82f6)", bg: "rgba(59,130,246,0.08)" },
    keyword: { color: "var(--color-keyword, #22c55e)", bg: "rgba(34,197,94,0.08)" },
    concept: { color: "var(--color-concept, #a855f7)", bg: "rgba(168,85,247,0.08)" },
};

export function KBNode({
    type,
    label,
    score,
    count,
    version,
    selected = false,
    stale = false,
    onClick,
}: KBNodeProps) {
    const st = typeStyles[type];

    // Determine dynamic size for keywords based on score, but keep bounds reasonable
    const size = type === "keyword" && score !== undefined
        ? Math.max(76, Math.min(130, 60 + score * 70))
        : type === "concept" ? 110 : 90;

    const TypeIcon = type === "concept" ? Component : type === "keyword" ? Hash : FileText;

    // Label for the count statistic
    const countLabel = type === "concept" ? "kws" : type === "article" ? "chunks" : "refs";
    const CountIcon = type === "concept" ? Tag : Link2;

    return (
        <div
            className="rounded-xl cursor-pointer transition-all hover:scale-105 flex flex-col items-center text-center gap-1.5"
            style={{
                width: size,
                minHeight: size * 0.75,
                background: selected ? `color-mix(in srgb, ${st.color} 15%, transparent)` : st.bg,
                border: selected
                    ? `2px solid ${st.color}`
                    : stale
                        ? "2px dashed rgba(245,158,11,0.4)"
                        : `1px solid color-mix(in srgb, ${st.color} 20%, transparent)`,
                boxShadow: selected ? `0 0 16px color-mix(in srgb, ${st.color} 25%, transparent)` : "none",
                padding: "8px 8px",
                opacity: stale && !selected ? 0.6 : 1,
            }}
            onClick={onClick}
        >
            {/* Type Header */}
            <div className="flex items-center justify-center gap-1 w-full" style={{ color: st.color, opacity: 0.9 }}>
                <TypeIcon size={10} />
                <span className="text-[8px] uppercase tracking-wider font-bold">{type}</span>
            </div>

            {/* Main Label */}
            <span
                className="text-[11px] font-bold leading-tight truncate w-full"
                style={{ color: selected ? st.color : "var(--text-primary)" }}
                title={label}
            >
                {label}
            </span>

            {/* Badges / Stats Container */}
            <div className="flex flex-wrap items-center justify-center gap-1.5 mt-0.5 w-full">
                {count !== undefined && (
                    <span
                        className="flex items-center gap-0.5 text-[8.5px] font-medium px-1 rounded-sm"
                        style={{ color: "var(--text-secondary)", background: "rgba(255,255,255,0.05)" }}
                        title={`${count} ${countLabel}`}
                    >
                        <CountIcon size={8} /> {count} {countLabel}
                    </span>
                )}

                {version && (
                    <span className="text-[8px] font-mono font-bold px-1 rounded-sm" style={{ background: st.bg, color: st.color }}>
                        {version}
                    </span>
                )}

                {stale && (
                    <span className="flex items-center gap-0.5 text-[8.5px] font-bold px-1 rounded-sm" style={{ background: "rgba(245,158,11,0.1)", color: "var(--color-warning)" }}>
                        <AlertTriangle size={8} /> Stale
                    </span>
                )}
            </div>

            {/* Score Bar with explicit text (Keyword only) */}
            {type === "keyword" && score !== undefined && (
                <div className="flex flex-col gap-0.5 w-full mt-1 px-1">
                    <div className="flex items-center justify-between w-full">
                        <span className="text-[7.5px] uppercase tracking-wider font-semibold" style={{ color: "var(--text-muted)" }}>Match</span>
                        <span className="text-[8px] font-mono" style={{ color: st.color }}>{Math.round(score * 100)}%</span>
                    </div>
                    <div className="w-full h-1 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
                        <div className="h-full rounded-full" style={{ width: `${score * 100}%`, background: st.color }} />
                    </div>
                </div>
            )}
        </div>
    );
}

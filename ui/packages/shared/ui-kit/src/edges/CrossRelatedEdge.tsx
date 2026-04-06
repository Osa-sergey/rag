import React from "react";

export interface CrossRelatedEdgeProps {
    /** Predicate label (e.g. defines, extends) */
    predicate: string;
    /** Confidence score (0 to 1) */
    confidence?: number;
    /** Width */
    width?: number;
    /** Height */
    height?: number;
}

export function CrossRelatedEdge({
    predicate,
    confidence,
    width = 200,
    height = 60,
}: CrossRelatedEdgeProps) {
    const color = "var(--color-info)";

    return (
        <div className="relative select-none" style={{ width, height }}>
            <svg width={width} height={height} className="absolute inset-0 overflow-visible">
                <path
                    d={`M 10 ${height / 2} C ${width / 3} ${height / 2}, ${(2 * width) / 3} ${height / 2}, ${width - 10} ${height / 2}`}
                    fill="none"
                    stroke={color}
                    strokeWidth={2}
                    strokeOpacity={0.6}
                />
                <polygon points={`${width - 10},${height / 2 - 4} ${width - 10},${height / 2 + 4} ${width},${height / 2}`} fill={color} />
                <circle cx={10} cy={height / 2} r={2.5} fill={color} />
            </svg>
            <div
                title={`Cross-relation predicate: "${predicate}"${confidence !== undefined ? ` (Confidence: ${confidence.toFixed(2)})` : ""}`}
                className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 shadow-sm flex items-center overflow-hidden rounded-md border"
                style={{
                    background: "var(--bg-node)",
                    borderColor: "var(--border-node)",
                }}
            >
                <span className="px-2 py-1 text-[10px] uppercase font-bold tracking-widest leading-none text-[var(--text-secondary)]">
                    {predicate}
                </span>
                {confidence !== undefined && (
                    <span
                        className="px-1.5 py-1 text-[9px] font-mono font-bold leading-none border-l border-[var(--border-node)]"
                        style={{
                            background: "color-mix(in srgb, var(--color-info) 10%, transparent)",
                            color: "var(--color-info)"
                        }}
                    >
                        {confidence.toFixed(2)}
                    </span>
                )}
            </div>
        </div>
    );
}

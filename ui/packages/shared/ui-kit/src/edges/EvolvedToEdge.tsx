import React from "react";

export interface EvolvedToEdgeProps {
    /** From version */
    fromVersion: string;
    /** To version */
    toVersion: string;
    /** Is this part of a chain (v1->v2->v3) */
    isChain?: boolean;
    /** Width */
    width?: number;
    /** Height */
    height?: number;
}

export function EvolvedToEdge({
    fromVersion,
    toVersion,
    isChain = false,
    width = 200,
    height = 60,
}: EvolvedToEdgeProps) {
    const color = "var(--color-stale)";

    return (
        <div className="relative select-none" style={{ width, height }}>
            <svg width={width} height={height} className="absolute inset-0 overflow-visible">
                <path
                    d={`M 10 ${height / 2} C ${width / 3} ${height / 2}, ${(2 * width) / 3} ${height / 2}, ${width - 10} ${height / 2}`}
                    fill="none"
                    stroke={color}
                    strokeWidth={2}
                    strokeDasharray={isChain ? "6 4" : "none"}
                    strokeOpacity={0.8}
                />
                <polygon points={`${width - 10},${height / 2 - 4} ${width - 10},${height / 2 + 4} ${width},${height / 2}`} fill={color} />
                <circle cx={10} cy={height / 2} r={2.5} fill={color} />
            </svg>
            <div
                title={`Version evolution semantic link: ${fromVersion} evolved to ${toVersion}`}
                className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 px-2 py-0.5 rounded shadow-sm text-[9px] font-mono font-bold border"
                style={{
                    background: "var(--bg-node)",
                    borderColor: "var(--border-node)",
                    color: "var(--text-primary)",
                }}
            >
                <span style={{ color: "var(--text-muted)" }}>{fromVersion}</span>
                <span className="mx-1" style={{ color: "var(--color-stale)" }}>→</span>
                <span>{toVersion}</span>
            </div>
        </div>
    );
}

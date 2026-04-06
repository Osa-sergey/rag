import React from "react";

export interface InstanceOfEdgeProps {
    /** Semantic similarity score (0 to 1) */
    similarity?: number;
    /** Width */
    width?: number;
    /** Height */
    height?: number;
}

export function InstanceOfEdge({
    similarity = 0.85,
    width = 200,
    height = 60,
}: InstanceOfEdgeProps) {
    const isHigh = similarity >= 0.8;
    const isLow = similarity < 0.4;
    const strokeWidth = isHigh ? 3 : isLow ? 1 : 2;
    const opacity = isHigh ? 1 : isLow ? 0.4 : 0.7;
    const color = "var(--color-concept)";

    return (
        <div className="relative select-none" style={{ width, height }}>
            <svg width={width} height={height} className="absolute inset-0 overflow-visible">
                <path
                    d={`M 10 ${height / 2} C ${width / 3} ${height / 2}, ${(2 * width) / 3} ${height / 2}, ${width - 10} ${height / 2}`}
                    fill="none"
                    stroke={color}
                    strokeWidth={strokeWidth}
                    strokeOpacity={opacity}
                />
                <circle cx={width - 10} cy={height / 2} r={4} fill={color} fillOpacity={opacity} />
                <circle cx={10} cy={height / 2} r={2.5} fill={color} fillOpacity={opacity} />
            </svg>
            <div
                title={`Ontological "is-a" relation with similarity score of ${similarity.toFixed(2)}`}
                className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 px-2 py-0.5 rounded text-[10px] font-bold shadow-sm flex items-center gap-1"
                style={{
                    background: "var(--bg-node)",
                    color,
                    border: "1px solid var(--border-node)",
                    opacity: opacity < 1 ? Math.max(0.6, opacity) : 1,
                }}
            >
                <span className="uppercase tracking-widest text-[9px]">is-a</span>
                <span className="font-mono">{similarity.toFixed(2)}</span>
            </div>
        </div>
    );
}

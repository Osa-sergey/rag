import React from "react";

export interface ReferencesEdgeProps {
    /** Width */
    width?: number;
    /** Height */
    height?: number;
}

export function ReferencesEdge({ width = 200, height = 60 }: ReferencesEdgeProps) {
    const color = "var(--text-muted)";

    return (
        <div className="relative select-none" style={{ width, height }}>
            <svg width={width} height={height} className="absolute inset-0 overflow-visible">
                <path
                    d={`M 10 ${height / 2} C ${width / 3} ${height / 2}, ${(2 * width) / 3} ${height / 2}, ${width - 10} ${height / 2}`}
                    fill="none"
                    stroke={color}
                    strokeWidth={1}
                    strokeDasharray="4 2"
                    strokeOpacity={0.5}
                />
                <polyline points={`${width - 10},${height / 2 - 3} ${width - 2},${height / 2} ${width - 10},${height / 2 + 3}`} fill="none" stroke={color} strokeWidth={1} />
                <circle cx={10} cy={height / 2} r={2} fill={color} fillOpacity={0.5} />
            </svg>
        </div>
    );
}

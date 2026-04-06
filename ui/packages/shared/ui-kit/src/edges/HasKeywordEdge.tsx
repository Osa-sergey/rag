import React from "react";

export interface HasKeywordEdgeProps {
    /** Score or weight of the keyword link */
    weight?: number;
    /** Width */
    width?: number;
    /** Height */
    height?: number;
}

export function HasKeywordEdge({ weight = 1, width = 200, height = 60 }: HasKeywordEdgeProps) {
    const color = "var(--color-keyword)";

    return (
        <div className="relative select-none" style={{ width, height }}>
            <svg width={width} height={height} className="absolute inset-0 overflow-visible">
                <path
                    d={`M 10 ${height / 2} C ${width / 3} ${height / 2}, ${(2 * width) / 3} ${height / 2}, ${width - 10} ${height / 2}`}
                    fill="none"
                    stroke={color}
                    strokeWidth={1.5}
                    strokeOpacity={0.5}
                />
                {/* Diamond marker */}
                <polygon points={`${width - 10},${height / 2} ${width - 5},${height / 2 - 3} ${width},${height / 2} ${width - 5},${height / 2 + 3}`} fill={color} />
                <circle cx={10} cy={height / 2} r={2} fill={color} />
            </svg>
            {weight && weight < 1 && (
                <div
                    title={`Keyword extraction weight: ${weight.toFixed(2)}`}
                    className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 px-1 py-0.5 rounded text-[8px] font-mono shadow-sm"
                    style={{
                        background: "color-mix(in srgb, var(--color-keyword) 10%, var(--bg-node))",
                        color: "var(--color-keyword)",
                        border: "1px solid color-mix(in srgb, var(--color-keyword) 20%, transparent)",
                    }}
                >
                    w:{weight.toFixed(2)}
                </div>
            )}
        </div>
    );
}

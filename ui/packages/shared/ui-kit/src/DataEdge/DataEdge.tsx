import React from "react";

export interface DataEdgeProps {
    /** Data type being transferred */
    dataType: string;
    /** Edge variant */
    variant?: "normal" | "mismatch" | "animated";
    /** Score label (for similarity edges) */
    score?: number;
    /** Width */
    width?: number;
    /** Height */
    height?: number;
}

export function DataEdge({
    dataType,
    variant = "normal",
    score,
    width = 200,
    height = 60,
}: DataEdgeProps) {
    const isMismatch = variant === "mismatch";
    const isAnimated = variant === "animated";
    const color = isMismatch ? "var(--color-error)" : "rgba(99,102,241,0.5)";

    return (
        <div className="relative" style={{ width, height }}>
            <svg width={width} height={height} className="absolute inset-0">
                <defs>
                    {isAnimated && (
                        <linearGradient id="flow-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="transparent" />
                            <stop offset="50%" stopColor={color} />
                            <stop offset="100%" stopColor="transparent">
                                <animate attributeName="offset" from="0%" to="200%" dur="2s" repeatCount="indefinite" />
                            </stop>
                        </linearGradient>
                    )}
                </defs>
                {/* Main curve */}
                <path
                    d={`M 10 ${height / 2} C ${width / 3} ${height / 2}, ${(2 * width) / 3} ${height / 2}, ${width - 10} ${height / 2}`}
                    fill="none"
                    stroke={color}
                    strokeWidth={isMismatch ? 2.5 : 2}
                    strokeDasharray={isMismatch ? "4 3" : "none"}
                />
                {/* Particles for animated variant */}
                {isAnimated && (
                    <circle r={3} fill="var(--color-info)">
                        <animateMotion dur="2s" repeatCount="indefinite"
                            path={`M 10 ${height / 2} C ${width / 3} ${height / 2}, ${(2 * width) / 3} ${height / 2}, ${width - 10} ${height / 2}`}
                        />
                    </circle>
                )}
                {/* Arrow */}
                <circle cx={width - 10} cy={height / 2} r={3} fill={color} />
                {/* Start dot */}
                <circle cx={10} cy={height / 2} r={2.5} fill={color} />
            </svg>

            {/* Label */}
            <div
                className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 px-2 py-0.5 rounded text-[9px] font-mono font-bold shadow-sm"
                style={{
                    background: isMismatch
                        ? "color-mix(in srgb, var(--color-error) 15%, var(--bg-canvas, #0a0a0f))"
                        : "color-mix(in srgb, var(--color-info) 15%, var(--bg-canvas, #0a0a0f))",
                    color: isMismatch ? "var(--color-error)" : "var(--color-info)",
                    border: isMismatch
                        ? "1px solid color-mix(in srgb, var(--color-error) 40%, transparent)"
                        : "1px solid color-mix(in srgb, var(--color-info) 20%, transparent)",
                    zIndex: 10,
                }}
            >
                {isMismatch && "⚠ "}
                {dataType}
                {score !== undefined && ` · ${score.toFixed(2)}`}
            </div>
        </div>
    );
}

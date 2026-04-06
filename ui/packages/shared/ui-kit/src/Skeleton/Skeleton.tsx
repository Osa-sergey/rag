import React from "react";

export type SkeletonVariant = "text" | "circle" | "card" | "row";

export interface SkeletonProps {
    /** Shape variant */
    variant?: SkeletonVariant;
    /** Width (any CSS value) */
    width?: string | number;
    /** Height (any CSS value) */
    height?: string | number;
    /** Number of repetitions for text/row */
    count?: number;
}

/*
 * Shimmer uses a separate CSS custom property so it works in both themes:
 *   dark  → --shimmer-hi = rgba(255,255,255,0.10)
 *   light → --shimmer-hi = rgba(0,0,0,0.06)
 * Falls back to a safe middle if neither is defined.
 */
const shimmerStyle: React.CSSProperties = {
    background: `linear-gradient(
    90deg,
    var(--bg-node) 25%,
    var(--shimmer-hi, rgba(128,128,128,0.12)) 50%,
    var(--bg-node) 75%
  )`,
    backgroundSize: "200% 100%",
    animation: "shimmer 1.6s ease-in-out infinite",
};

export function Skeleton({
    variant = "text",
    width,
    height,
    count = 1,
}: SkeletonProps) {
    const items = Array.from({ length: count }, (_, i) => i);

    const getStyles = (): React.CSSProperties => {
        switch (variant) {
            case "circle":
                return {
                    width: width ?? 40,
                    height: height ?? 40,
                    borderRadius: "50%",
                    ...shimmerStyle,
                };
            case "card":
                return {
                    width: width ?? "100%",
                    height: height ?? 120,
                    borderRadius: "var(--radius-node)",
                    ...shimmerStyle,
                };
            case "row":
                return {
                    width: width ?? "100%",
                    height: height ?? 48,
                    borderRadius: 8,
                    ...shimmerStyle,
                };
            case "text":
            default:
                return {
                    width: width ?? "100%",
                    height: height ?? 14,
                    borderRadius: 4,
                    ...shimmerStyle,
                };
        }
    };

    return (
        <>
            <style>{`
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {items.map((i) => (
                    <div key={i} style={getStyles()} />
                ))}
            </div>
        </>
    );
}

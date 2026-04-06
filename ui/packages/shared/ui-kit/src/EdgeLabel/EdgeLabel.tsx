import React from "react";

export type EdgeLabelVariant = "type" | "score" | "dependency";

export interface EdgeLabelProps {
    /** Label text */
    label: string;
    /** Variant determines styling */
    variant?: EdgeLabelVariant;
    /** Custom color */
    color?: string;
    /** Show on hover only (reduced opacity by default) */
    hoverReveal?: boolean;
    /** Error state (type mismatch) */
    error?: boolean;
}

const variantStyles: Record<EdgeLabelVariant, { bg: string; color: string }> = {
    type: { bg: "rgba(99,102,241,0.12)", color: "var(--color-info)" },
    score: { bg: "rgba(34,197,94,0.12)", color: "var(--color-success)" },
    dependency: { bg: "rgba(245,158,11,0.12)", color: "var(--color-warning)" },
};

export function EdgeLabel({
    label,
    variant = "type",
    color,
    hoverReveal = false,
    error = false,
}: EdgeLabelProps) {
    const styles = error
        ? { bg: "rgba(239,68,68,0.12)", color: "var(--color-error)" }
        : { bg: color ? `color-mix(in srgb, ${color} 12%, transparent)` : variantStyles[variant].bg, color: color ?? variantStyles[variant].color };

    return (
        <div
            className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold whitespace-nowrap transition-opacity"
            style={{
                background: styles.bg,
                color: styles.color,
                opacity: hoverReveal ? 0.5 : 1,
                border: error ? `1px solid ${styles.color}` : "none",
            }}
        >
            {error && "⚠ "}
            {label}
        </div>
    );
}

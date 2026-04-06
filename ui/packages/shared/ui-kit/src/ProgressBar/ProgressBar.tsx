import React from "react";
import { motion } from "framer-motion";
import { transitions } from "../motion";

export interface ProgressBarProps {
    /** Progress value 0–100 (omit for indeterminate) */
    value?: number;
    /** Label shown above bar */
    label?: string;
    /** Show percentage text */
    showPercent?: boolean;
    /** Color variant */
    variant?: "info" | "success" | "warning" | "error";
    /** Height in px */
    height?: number;
}

const variantColors: Record<string, string> = {
    info: "var(--color-info)",
    success: "var(--color-success)",
    warning: "var(--color-warning)",
    error: "var(--color-error)",
};

export function ProgressBar({
    value,
    label,
    showPercent = false,
    variant = "info",
    height = 4,
}: ProgressBarProps) {
    const isDeterminate = value !== undefined;
    const clampedValue = isDeterminate ? Math.min(100, Math.max(0, value)) : 0;
    const color = variantColors[variant];

    return (
        <div className="flex flex-col gap-1.5 w-full">
            {/* Header row */}
            {(label || showPercent) && (
                <div className="flex items-center justify-between">
                    {label && (
                        <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                            {label}
                        </span>
                    )}
                    {showPercent && isDeterminate && (
                        <span className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
                            {Math.round(clampedValue)}%
                        </span>
                    )}
                </div>
            )}

            {/* Track */}
            <div
                className="relative w-full rounded-full overflow-hidden"
                style={{ height, background: "var(--bg-node-hover)" }}
                role="progressbar"
                aria-valuenow={isDeterminate ? clampedValue : undefined}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={label}
            >
                {isDeterminate ? (
                    /* Determinate fill */
                    <motion.div
                        className="absolute top-0 left-0 h-full rounded-full"
                        style={{ background: color }}
                        initial={{ width: "0%" }}
                        animate={{ width: `${clampedValue}%` }}
                        transition={transitions.spring}
                    />
                ) : (
                    /* Indeterminate sliding bar */
                    <motion.div
                        className="absolute top-0 h-full rounded-full"
                        style={{ background: color, width: "35%" }}
                        animate={{
                            x: ["-35%", "300%"],
                        }}
                        transition={{
                            repeat: Infinity,
                            duration: 1.5,
                            ease: "easeInOut",
                        }}
                    />
                )}

                {/* M3 stop indicator for determinate — subtle dot at the end of track */}
                {isDeterminate && clampedValue > 0 && clampedValue < 100 && (
                    <motion.div
                        className="absolute top-0 right-0 h-full rounded-full"
                        style={{
                            width: height,
                            background: "var(--text-muted)",
                            opacity: 0.3,
                        }}
                    />
                )}
            </div>
        </div>
    );
}

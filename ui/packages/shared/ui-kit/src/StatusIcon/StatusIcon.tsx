import React from "react";
import { motion } from "framer-motion";

export type Status = "success" | "error" | "warning" | "info" | "idle" | "running" | "stale";

export interface StatusIconProps {
    /** Current status */
    status: Status;
    /** Size in pixels */
    size?: number;
    /** Show pulse animation for active states */
    pulse?: boolean;
    /** Optional label text after icon */
    label?: string;
}

const statusConfig: Record<Status, { color: string; emoji: string }> = {
    success: { color: "var(--color-success)", emoji: "●" },
    error: { color: "var(--color-error)", emoji: "●" },
    warning: { color: "var(--color-warning)", emoji: "●" },
    info: { color: "var(--color-info)", emoji: "●" },
    idle: { color: "var(--color-dep)", emoji: "●" },
    running: { color: "var(--color-info)", emoji: "●" },
    stale: { color: "var(--color-stale)", emoji: "●" },
};

export function StatusIcon({ status, size = 10, pulse = false, label }: StatusIconProps) {
    const config = statusConfig[status];
    const shouldPulse = pulse || status === "running";

    return (
        <span className="inline-flex items-center gap-1.5 select-none">
            <span className="relative inline-flex" style={{ width: size, height: size }}>
                {shouldPulse && (
                    <motion.span
                        className="absolute inset-0 rounded-full"
                        style={{ backgroundColor: config.color, opacity: 0.4 }}
                        animate={{ scale: [1, 1.8, 1], opacity: [0.4, 0, 0.4] }}
                        transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                    />
                )}
                <span
                    className="relative inline-block rounded-full"
                    style={{
                        width: size,
                        height: size,
                        backgroundColor: config.color,
                    }}
                />
            </span>
            {label && (
                <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
                    {label}
                </span>
            )}
        </span>
    );
}

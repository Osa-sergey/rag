import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from "lucide-react";
import { transitions } from "../motion";

export type ToastVariant = "success" | "error" | "warning" | "info";

export interface ToastProps {
    /** Message text */
    message: string;
    /** Variant */
    variant?: ToastVariant;
    /** Optional action button */
    action?: { label: string; onClick: () => void };
    /** Auto-dismiss delay in ms (0 = no auto-dismiss) */
    duration?: number;
    /** Called when dismissed */
    onDismiss?: () => void;
    /** Show the toast */
    open?: boolean;
}

const variantConfig: Record<ToastVariant, {
    icon: React.ReactNode;
    border: string;
    glow: string;
}> = {
    success: {
        icon: <CheckCircle2 size={18} />,
        border: "var(--color-success)",
        glow: "var(--glow-success)",
    },
    error: {
        icon: <AlertCircle size={18} />,
        border: "var(--color-error)",
        glow: "var(--glow-error)",
    },
    warning: {
        icon: <AlertTriangle size={18} />,
        border: "var(--color-warning)",
        glow: "var(--glow-warning)",
    },
    info: {
        icon: <Info size={18} />,
        border: "var(--color-info)",
        glow: "var(--glow-info)",
    },
};

export function Toast({
    message,
    variant = "info",
    action,
    duration = 5000,
    onDismiss,
    open = true,
}: ToastProps) {
    const [visible, setVisible] = useState(open);
    const cfg = variantConfig[variant];

    useEffect(() => {
        setVisible(open);
    }, [open]);

    useEffect(() => {
        if (!visible || duration <= 0) return;
        const timer = setTimeout(() => {
            setVisible(false);
            onDismiss?.();
        }, duration);
        return () => clearTimeout(timer);
    }, [visible, duration, onDismiss]);

    const handleDismiss = () => {
        setVisible(false);
        onDismiss?.();
    };

    return (
        <AnimatePresence>
            {visible && (
                <motion.div
                    initial={{ y: 60, opacity: 0, scale: 0.95 }}
                    animate={{ y: 0, opacity: 1, scale: 1 }}
                    exit={{ y: 20, opacity: 0, scale: 0.95 }}
                    transition={transitions.spring}
                    className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm"
                    style={{
                        background: "var(--glass-bg, var(--bg-node))",
                        backdropFilter: "var(--glass-blur, blur(8px))",
                        border: `1px solid ${cfg.border}`,
                        borderLeft: `3px solid ${cfg.border}`,
                        boxShadow: `${cfg.glow}, -4px 6px 20px rgba(0,0,0,0.3)`,
                        color: "var(--text-primary)",
                        maxWidth: 440,
                    }}
                    role="status"
                    aria-live="polite"
                >
                    <span style={{ color: cfg.border, flexShrink: 0 }}>
                        {cfg.icon}
                    </span>

                    <span className="flex-1">{message}</span>

                    {action && (
                        <button
                            onClick={action.onClick}
                            className="text-xs font-semibold px-2 py-1 rounded-md transition-colors"
                            style={{ color: cfg.border, background: "rgba(255,255,255,0.05)" }}
                        >
                            {action.label}
                        </button>
                    )}

                    <button
                        onClick={handleDismiss}
                        className="flex-shrink-0 p-0.5 rounded transition-colors"
                        style={{ color: "var(--text-muted)" }}
                        aria-label="Dismiss"
                    >
                        <X size={14} />
                    </button>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

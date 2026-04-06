import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Info, AlertTriangle, AlertCircle, CheckCircle2 } from "lucide-react";
import { transitions } from "../motion";

export type AlertBannerVariant = "info" | "warning" | "error" | "success";

export interface AlertBannerProps {
    /** Message */
    message: string;
    /** Variant */
    variant?: AlertBannerVariant;
    /** Dismissible */
    dismissible?: boolean;
    /** Controlled visibility */
    visible?: boolean;
    /** Dismiss handler */
    onDismiss?: () => void;
    /** Action button */
    action?: { label: string; onClick: () => void };
}

const variantConfig: Record<AlertBannerVariant, { icon: React.ReactNode; color: string }> = {
    info: { icon: <Info size={16} />, color: "var(--color-info)" },
    warning: { icon: <AlertTriangle size={16} />, color: "var(--color-warning)" },
    error: { icon: <AlertCircle size={16} />, color: "var(--color-error)" },
    success: { icon: <CheckCircle2 size={16} />, color: "var(--color-success)" },
};

export function AlertBanner({
    message,
    variant = "info",
    dismissible = true,
    visible: controlledVisible,
    onDismiss,
    action,
}: AlertBannerProps) {
    const [internalVisible, setInternalVisible] = useState(true);
    const isVisible = controlledVisible ?? internalVisible;
    const cfg = variantConfig[variant];

    const handleDismiss = () => {
        setInternalVisible(false);
        onDismiss?.();
    };

    return (
        <AnimatePresence>
            {isVisible && (
                <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={transitions.smooth}
                    className="overflow-hidden"
                >
                    <div
                        className="flex items-center gap-3 px-4 py-2.5 text-sm"
                        style={{
                            background: `color-mix(in srgb, ${cfg.color} 8%, transparent)`,
                            borderBottom: `1px solid color-mix(in srgb, ${cfg.color} 20%, transparent)`,
                        }}
                        role="alert"
                    >
                        <span style={{ color: cfg.color, flexShrink: 0 }}>{cfg.icon}</span>
                        <span className="flex-1" style={{ color: "var(--text-primary)" }}>{message}</span>

                        {action && (
                            <button
                                onClick={action.onClick}
                                className="text-xs font-semibold px-2 py-0.5 rounded hover:underline flex-shrink-0"
                                style={{ color: cfg.color }}
                            >
                                {action.label}
                            </button>
                        )}

                        {dismissible && (
                            <button
                                onClick={handleDismiss}
                                className="flex-shrink-0 p-0.5 rounded hover:bg-white/5"
                                style={{ color: "var(--text-muted)" }}
                                aria-label="Dismiss"
                            >
                                <X size={14} />
                            </button>
                        )}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

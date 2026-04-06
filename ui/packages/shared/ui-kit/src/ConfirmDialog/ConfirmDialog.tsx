import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Info, Trash2, X } from "lucide-react";
import { transitions } from "../motion";

export type ConfirmDialogIntent = "info" | "destructive";

export interface ConfirmDialogProps {
    /** Is open */
    open: boolean;
    /** Close handler */
    onClose: () => void;
    /** Confirm handler */
    onConfirm: () => void;
    /** Title */
    title: string;
    /** Description */
    description?: string;
    /** Intent (affects button color & icon) */
    intent?: ConfirmDialogIntent;
    /** Confirm button text */
    confirmLabel?: string;
    /** Cancel button text */
    cancelLabel?: string;
}

export function ConfirmDialog({
    open,
    onClose,
    onConfirm,
    title,
    description,
    intent = "info",
    confirmLabel,
    cancelLabel = "Cancel",
}: ConfirmDialogProps) {
    const isDestructive = intent === "destructive";
    const accentColor = isDestructive ? "var(--color-error)" : "var(--color-info)";
    const Icon = isDestructive ? AlertTriangle : Info;
    const defaultConfirmLabel = isDestructive ? "Delete" : "Confirm";

    return (
        <AnimatePresence>
            {open && (
                <div className="fixed inset-0 z-50 flex items-center justify-center">
                    {/* Scrim */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="absolute inset-0"
                        style={{ background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)" }}
                        onClick={onClose}
                    />

                    {/* Dialog */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 24 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 12 }}
                        transition={transitions.spring}
                        role="alertdialog"
                        aria-modal="true"
                        aria-labelledby="confirm-title"
                        aria-describedby="confirm-desc"
                        className="relative z-10 rounded-2xl p-6 flex flex-col gap-4"
                        style={{
                            width: 380,
                            maxWidth: "90vw",
                            background: "var(--bg-panel)",
                            border: "var(--border-node)",
                            boxShadow: "0 16px 48px rgba(0,0,0,0.4)",
                        }}
                    >
                        {/* Close */}
                        <button
                            onClick={onClose}
                            className="absolute top-3 right-3 p-1 rounded-lg hover:bg-white/5"
                            style={{ color: "var(--text-muted)" }}
                            aria-label="Close"
                        >
                            <X size={14} />
                        </button>

                        {/* Icon + Title */}
                        <div className="flex items-start gap-3">
                            <div
                                className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center"
                                style={{ background: `color-mix(in srgb, ${accentColor} 15%, transparent)` }}
                            >
                                <Icon size={20} style={{ color: accentColor }} />
                            </div>
                            <div className="flex flex-col gap-1 pt-0.5">
                                <h3 id="confirm-title" className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                                    {title}
                                </h3>
                                {description && (
                                    <p id="confirm-desc" className="text-xs" style={{ color: "var(--text-muted)" }}>
                                        {description}
                                    </p>
                                )}
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center justify-end gap-2 pt-2">
                            <button
                                onClick={onClose}
                                className="px-4 py-2 rounded-lg text-xs font-medium transition-colors hover:bg-white/5"
                                style={{ color: "var(--text-muted)" }}
                            >
                                {cancelLabel}
                            </button>
                            <button
                                onClick={() => { onConfirm(); onClose(); }}
                                className="px-4 py-2 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
                                style={{ background: accentColor, color: isDestructive ? "#fff" : "var(--text-inverse)" }}
                            >
                                {isDestructive && <Trash2 size={12} />}
                                {confirmLabel ?? defaultConfirmLabel}
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}

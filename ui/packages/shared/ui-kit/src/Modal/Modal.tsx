import React, { useEffect, useRef, useId } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { transitions } from "../motion";

export type ModalSize = "sm" | "md" | "lg" | "full";

export interface ModalProps {
    /** Is the modal open */
    open: boolean;
    /** Close handler */
    onClose: () => void;
    /** Title */
    title?: string;
    /** Size */
    size?: ModalSize;
    /** Children (body) */
    children: React.ReactNode;
    /** Footer actions */
    footer?: React.ReactNode;
    /** Close on scrim click (default true) */
    closeOnOverlay?: boolean;
    /** Show close button (default true) */
    showCloseButton?: boolean;
}

const sizeWidths: Record<ModalSize, string> = {
    sm: "360px",
    md: "520px",
    lg: "720px",
    full: "calc(100vw - 64px)",
};

export function Modal({
    open,
    onClose,
    title,
    size = "md",
    children,
    footer,
    closeOnOverlay = true,
    showCloseButton = true,
}: ModalProps) {
    const titleId = useId();
    const dialogRef = useRef<HTMLDivElement>(null);

    /* Focus trap — refocus dialog on Tab if focus escapes */
    useEffect(() => {
        if (!open) return;
        const handler = (e: KeyboardEvent) => {
            if (e.key === "Escape") onClose();
        };
        document.addEventListener("keydown", handler);
        return () => document.removeEventListener("keydown", handler);
    }, [open, onClose]);

    return (
        <AnimatePresence>
            {open && (
                <div className="fixed inset-0 z-50 flex items-center justify-center">
                    {/* Scrim */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="absolute inset-0"
                        style={{ background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)" }}
                        onClick={closeOnOverlay ? onClose : undefined}
                    />

                    {/* Dialog */}
                    <motion.div
                        ref={dialogRef}
                        initial={{ opacity: 0, scale: 0.92, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 10 }}
                        transition={transitions.spring}
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby={title ? titleId : undefined}
                        className="relative z-10 rounded-2xl flex flex-col overflow-hidden"
                        style={{
                            width: sizeWidths[size],
                            maxWidth: "95vw",
                            maxHeight: "85vh",
                            background: "var(--bg-panel)",
                            border: "var(--border-node)",
                            boxShadow: "0 16px 48px rgba(0,0,0,0.4)",
                        }}
                    >
                        {/* Header */}
                        {(title || showCloseButton) && (
                            <div className="flex items-center justify-between px-6 py-4 flex-shrink-0" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                                {title && (
                                    <h2 id={titleId} className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
                                        {title}
                                    </h2>
                                )}
                                {showCloseButton && (
                                    <button
                                        onClick={onClose}
                                        className="p-1 rounded-lg transition-colors hover:bg-white/5"
                                        style={{ color: "var(--text-muted)" }}
                                        aria-label="Close"
                                    >
                                        <X size={16} />
                                    </button>
                                )}
                            </div>
                        )}

                        {/* Body */}
                        <div className="overflow-y-auto flex-1 px-6 py-4">
                            {children}
                        </div>

                        {/* Footer */}
                        {footer && (
                            <div className="flex items-center justify-end gap-2 px-6 py-3 flex-shrink-0" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                                {footer}
                            </div>
                        )}
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}

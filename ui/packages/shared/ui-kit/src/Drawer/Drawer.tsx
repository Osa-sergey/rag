import React, { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { transitions } from "../motion";

export type DrawerSide = "left" | "right";
export type DrawerSize = "sm" | "md" | "lg";

export interface DrawerProps {
    /** Is drawer open */
    open: boolean;
    /** Close handler */
    onClose: () => void;
    /** Which side the drawer slides from */
    side?: DrawerSide;
    /** Width preset */
    size?: DrawerSize;
    /** Title in header */
    title?: string;
    /** Children content */
    children: React.ReactNode;
    /** Show overlay behind drawer */
    overlay?: boolean;
    /** Header actions (e.g. tabs, buttons) */
    headerActions?: React.ReactNode;
}

const widths: Record<DrawerSize, number> = {
    sm: 280,
    md: 380,
    lg: 520,
};

export function Drawer({
    open,
    onClose,
    side = "right",
    size = "md",
    title,
    children,
    overlay = true,
    headerActions,
}: DrawerProps) {
    const w = widths[size];
    const isLeft = side === "left";

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
                <div className="fixed inset-0 z-40 flex" style={{ justifyContent: isLeft ? "flex-start" : "flex-end" }}>
                    {/* Overlay */}
                    {overlay && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="absolute inset-0"
                            style={{ background: "rgba(0,0,0,0.35)" }}
                            onClick={onClose}
                        />
                    )}

                    {/* Panel */}
                    <motion.aside
                        initial={{ x: isLeft ? -w : w }}
                        animate={{ x: 0 }}
                        exit={{ x: isLeft ? -w : w }}
                        transition={transitions.spring}
                        className="relative z-10 h-full flex flex-col"
                        style={{
                            width: w,
                            maxWidth: "90vw",
                            background: "var(--bg-panel)",
                            borderRight: isLeft ? "var(--border-node)" : "none",
                            borderLeft: isLeft ? "none" : "var(--border-node)",
                            boxShadow: `${isLeft ? "" : "-"}8px 0 32px rgba(0,0,0,0.2)`,
                        }}
                        role="complementary"
                        aria-label={title ?? "Drawer"}
                    >
                        {/* Header */}
                        {(title || headerActions) && (
                            <div
                                className="flex items-center justify-between gap-2 px-4 py-3 flex-shrink-0"
                                style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
                            >
                                <div className="flex items-center gap-2 min-w-0">
                                    {title && (
                                        <h3 className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                                            {title}
                                        </h3>
                                    )}
                                </div>
                                <div className="flex items-center gap-1 flex-shrink-0">
                                    {headerActions}
                                    <button
                                        onClick={onClose}
                                        className="p-1.5 rounded-lg transition-colors hover:bg-white/5"
                                        style={{ color: "var(--text-muted)" }}
                                        aria-label="Close drawer"
                                    >
                                        <X size={14} />
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Body */}
                        <div className="flex-1 overflow-y-auto">
                            {children}
                        </div>
                    </motion.aside>
                </div>
            )}
        </AnimatePresence>
    );
}

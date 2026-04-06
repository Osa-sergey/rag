import React, { useState, useRef, useEffect, useLayoutEffect } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { transitions } from "../motion";

export type PopoverTrigger = "click" | "hover";
export type PopoverPlacement = "top" | "bottom" | "left" | "right";

export interface PopoverProps {
    /** Trigger element */
    children: React.ReactElement;
    /** Content inside popover */
    content: React.ReactNode;
    /** Trigger mode */
    trigger?: PopoverTrigger;
    /** Placement relative to trigger */
    placement?: PopoverPlacement;
    /** Width constraint (auto | number) */
    width?: number | "auto";
    /** Max width constraint */
    maxWidth?: number;
    /** Controlled open state */
    open?: boolean;
    /** Change handler */
    onOpenChange?: (open: boolean) => void;
    /** Whether the popover can be dragged */
    draggable?: boolean;
}

const getPlacement = (rect: DOMRect, placement: PopoverPlacement): React.CSSProperties => {
    switch (placement) {
        case "top":
            return { top: rect.top - 8, left: rect.left + rect.width / 2, transform: "translate(-50%, -100%)" };
        case "bottom":
            return { top: rect.bottom + 8, left: rect.left + rect.width / 2, transform: "translate(-50%, 0)" };
        case "left":
            return { top: rect.top + rect.height / 2, left: rect.left - 8, transform: "translate(-100%, -50%)" };
        case "right":
            return { top: rect.top + rect.height / 2, left: rect.right + 8, transform: "translate(0, -50%)" };
    }
};

const originMap: Record<PopoverPlacement, string> = {
    top: "bottom center",
    bottom: "top center",
    left: "right center",
    right: "left center",
};

export function Popover({
    children,
    content,
    trigger = "click",
    placement = "bottom",
    width = "auto",
    maxWidth,
    open: controlledOpen,
    onOpenChange,
    draggable = false,
}: PopoverProps) {
    const [internalOpen, setInternalOpen] = useState(false);
    const [rect, setRect] = useState<DOMRect | null>(null);
    const isOpen = controlledOpen ?? internalOpen;
    const containerRef = useRef<HTMLDivElement>(null);
    const portalRef = useRef<HTMLDivElement>(null);
    const hoverTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

    const setOpen = (val: boolean) => {
        setInternalOpen(val);
        onOpenChange?.(val);
    };

    useLayoutEffect(() => {
        if (isOpen && containerRef.current) {
            setRect(containerRef.current.getBoundingClientRect());
        }
    }, [isOpen]);

    // Close on outside click — must check portal too
    useEffect(() => {
        if (trigger !== "click" || !isOpen) return;
        const handler = (e: MouseEvent) => {
            const inTrigger = containerRef.current?.contains(e.target as Node);
            const inPortal = portalRef.current?.contains(e.target as Node);
            if (!inTrigger && !inPortal) {
                setOpen(false);
            }
        };
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, [isOpen, trigger]);

    // Block native wheel on portal so canvas doesn't zoom/pan
    useEffect(() => {
        if (!isOpen) return;
        const el = portalRef.current;
        if (!el) return;
        const blockWheel = (e: WheelEvent) => { e.stopPropagation(); };
        el.addEventListener("wheel", blockWheel, { passive: false });
        return () => el.removeEventListener("wheel", blockWheel);
    }, [isOpen]);

    const clickProps = trigger === "click" ? { onClick: () => setOpen(!isOpen) } : {};
    const hoverProps = trigger === "hover" ? {
        onMouseEnter: () => {
            if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
            setOpen(true);
        },
        onMouseLeave: () => {
            hoverTimeout.current = setTimeout(() => setOpen(false), 150);
        },
    } : {};

    const placementStyle: React.CSSProperties = {
        position: "fixed",
        zIndex: 100,
        ...(rect ? getPlacement(rect, placement) : {}),
        pointerEvents: "none",
    };

    const panelStyle: React.CSSProperties = {
        width: width === "auto" ? "max-content" : width,
        maxWidth: maxWidth ?? 360,
        background: "var(--bg-panel)",
        border: "var(--border-node)",
        boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
        transformOrigin: originMap[placement],
        pointerEvents: "auto",
    };

    return (
        <div ref={containerRef} className="relative inline-block" {...hoverProps}>
            {/* Trigger */}
            <div {...clickProps} className={trigger === "click" ? "cursor-pointer" : ""}>
                {children}
            </div>

            {/* Content Portal */}
            {isOpen && rect && createPortal(
                <div style={placementStyle}>
                    <AnimatePresence>
                        <motion.div
                            ref={portalRef}
                            drag={draggable || false}
                            dragMomentum={false}
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            transition={transitions.snappy}
                            className={`rounded-xl ${draggable ? "cursor-grab active:cursor-grabbing" : "overflow-hidden"}`}
                            style={panelStyle}
                            {...(trigger === "hover" ? hoverProps : {})}
                        >
                            {/* Inner content div: stops events from reaching the canvas */}
                            <div
                                onClickCapture={(e) => e.stopPropagation()}
                                onWheelCapture={(e) => e.stopPropagation()}
                                onMouseDownCapture={(e) => {
                                    // Stop canvas pan, but only if not on the drag handle (outer border)
                                    e.stopPropagation();
                                }}
                                style={{ cursor: "auto" }}
                            >
                                {content}
                            </div>
                        </motion.div>
                    </AnimatePresence>
                </div>,
                document.body
            )}
        </div>
    );
}


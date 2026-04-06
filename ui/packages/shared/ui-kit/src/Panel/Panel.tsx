import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { slideInRight, slideInLeft, slideInBottom } from "../motion";

export type PanelSide = "left" | "right" | "bottom";

export interface PanelProps {
    /** Panel position */
    side: PanelSide;
    /** Whether visible */
    open: boolean;
    /** Toggle callback */
    onToggle?: () => void;
    /** Panel title */
    title?: string;
    /** Default width (left/right) or height (bottom) in px */
    defaultSize?: number;
    /** Minimum size in px */
    minSize?: number;
    /** Content */
    children: React.ReactNode;
}

const variants: Record<PanelSide, typeof slideInRight> = {
    left: slideInLeft,
    right: slideInRight,
    bottom: slideInBottom,
};

export function Panel({
    side,
    open,
    onToggle,
    title,
    defaultSize = side === "bottom" ? 200 : 320,
    minSize = side === "bottom" ? 100 : 200,
    children,
}: PanelProps) {
    const [size, setSize] = useState(defaultSize);
    const isHorizontal = side === "left" || side === "right";

    const sizeStyle: React.CSSProperties = isHorizontal
        ? { width: size, minWidth: minSize, height: "100%" }
        : { height: size, minHeight: minSize, width: "100%" };

    const positionStyle: React.CSSProperties = {
        position: "relative",
        ...(side === "left" ? { borderRight: "var(--border-node)" } : {}),
        ...(side === "right" ? { borderLeft: "var(--border-node)" } : {}),
        ...(side === "bottom" ? { borderTop: "var(--border-node)" } : {}),
    };

    const handleMouseDown = useCallback(
        (e: React.MouseEvent) => {
            e.preventDefault();
            const startPos = isHorizontal ? e.clientX : e.clientY;
            const startSize = size;

            const onMouseMove = (ev: MouseEvent) => {
                const currentPos = isHorizontal ? ev.clientX : ev.clientY;
                const delta = side === "left" || side === "bottom"
                    ? currentPos - startPos
                    : startPos - currentPos;
                setSize(Math.max(minSize, startSize + (side === "bottom" ? -delta : delta)));
            };

            const onMouseUp = () => {
                document.removeEventListener("mousemove", onMouseMove);
                document.removeEventListener("mouseup", onMouseUp);
            };

            document.addEventListener("mousemove", onMouseMove);
            document.addEventListener("mouseup", onMouseUp);
        },
        [isHorizontal, size, side, minSize]
    );

    const resizeHandleStyle: React.CSSProperties = isHorizontal
        ? {
            position: "absolute",
            top: 0,
            [side === "left" ? "right" : "left"]: -3,
            width: 6,
            height: "100%",
            cursor: "col-resize",
            zIndex: 10,
        }
        : {
            position: "absolute",
            left: 0,
            top: -3,
            width: "100%",
            height: 6,
            cursor: "row-resize",
            zIndex: 10,
        };

    return (
        <AnimatePresence>
            {open && (
                <motion.div
                    className="flex flex-col overflow-hidden"
                    style={{
                        ...sizeStyle,
                        ...positionStyle,
                        background: "var(--bg-panel)",
                    }}
                    variants={variants[side]}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                >
                    {/* Resize handle */}
                    <div
                        style={resizeHandleStyle}
                        onMouseDown={handleMouseDown}
                        className="hover:bg-blue-400/30 transition-colors"
                    />

                    {/* Header */}
                    {title && (
                        <div
                            className="flex items-center justify-between px-4 py-2 text-sm font-semibold select-none flex-shrink-0"
                            style={{
                                color: "var(--text-primary)",
                                borderBottom: "var(--border-node)",
                            }}
                            onDoubleClick={onToggle}
                        >
                            {title}
                            {onToggle && (
                                <button
                                    onClick={onToggle}
                                    className="text-xs opacity-50 hover:opacity-100 transition-opacity px-1"
                                >
                                    ✕
                                </button>
                            )}
                        </div>
                    )}

                    {/* Content */}
                    <div className="flex-1 overflow-auto p-4">{children}</div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

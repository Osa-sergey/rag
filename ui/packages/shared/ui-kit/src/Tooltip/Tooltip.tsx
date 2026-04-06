import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { scaleIn } from "../motion";

export type TooltipPosition = "top" | "bottom" | "left" | "right";

export interface TooltipProps {
    /** Content to show inside the tooltip */
    content: React.ReactNode;
    /** The element that triggers the tooltip on hover */
    children: React.ReactNode;
    /** Tooltip position relative to trigger */
    position?: TooltipPosition;
    /** Delay before showing (ms) */
    delay?: number;
}

const positionStyles: Record<TooltipPosition, React.CSSProperties> = {
    top: { bottom: "100%", left: "50%", transform: "translateX(-50%)", marginBottom: 8 },
    bottom: { top: "100%", left: "50%", transform: "translateX(-50%)", marginTop: 8 },
    left: { right: "100%", top: "50%", transform: "translateY(-50%)", marginRight: 8 },
    right: { left: "100%", top: "50%", transform: "translateY(-50%)", marginLeft: 8 },
};

export function Tooltip({ content, children, position = "top", delay = 200 }: TooltipProps) {
    const [visible, setVisible] = useState(false);
    const [timer, setTimer] = useState<ReturnType<typeof setTimeout> | null>(null);

    const show = () => {
        const t = setTimeout(() => setVisible(true), delay);
        setTimer(t);
    };

    const hide = () => {
        if (timer) clearTimeout(timer);
        setVisible(false);
    };

    return (
        <span
            className="relative inline-flex"
            onMouseEnter={show}
            onMouseLeave={hide}
            onFocus={show}
            onBlur={hide}
        >
            {children}
            <AnimatePresence>
                {visible && (
                    <motion.div
                        className="absolute z-50 pointer-events-none"
                        style={positionStyles[position]}
                        variants={scaleIn}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                    >
                        <div
                            className="px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap"
                            style={{
                                background: "var(--text-primary)",
                                color: "var(--text-inverse)",
                                boxShadow: "var(--shadow-hover)",
                            }}
                        >
                            {content}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </span>
    );
}

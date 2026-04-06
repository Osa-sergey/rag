import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { transitions, expandHeight } from "../motion";

export interface AccordionItem {
    /** Unique key */
    id: string;
    /** Header label */
    title: string;
    /** Optional subtitle/description */
    subtitle?: string;
    /** Optional badge on the right */
    badge?: React.ReactNode;
    /** Collapsible content */
    content: React.ReactNode;
}

export interface AccordionProps {
    /** Items to render */
    items: AccordionItem[];
    /** Allow multiple sections open simultaneously */
    multiple?: boolean;
    /** Default open item ids */
    defaultOpen?: string[];
}

export function Accordion({ items, multiple = false, defaultOpen = [] }: AccordionProps) {
    const [openIds, setOpenIds] = useState<Set<string>>(new Set(defaultOpen));

    const toggle = (id: string) => {
        setOpenIds((prev) => {
            const next = new Set(multiple ? prev : []);
            if (prev.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    };

    return (
        <div className="flex flex-col" style={{ borderRadius: "var(--radius-node)", overflow: "hidden" }}>
            {items.map((item, i) => {
                const isOpen = openIds.has(item.id);
                return (
                    <div
                        key={item.id}
                        style={{
                            borderBottom: i < items.length - 1 ? "var(--border-node)" : "none",
                        }}
                    >
                        {/* Header */}
                        <button
                            onClick={() => toggle(item.id)}
                            className="w-full flex items-center justify-between px-4 py-3 text-left transition-colors"
                            style={{
                                background: isOpen ? "var(--bg-node-hover)" : "var(--bg-node)",
                                color: "var(--text-primary)",
                            }}
                        >
                            <div className="flex flex-col gap-0.5">
                                <span className="text-sm font-medium">{item.title}</span>
                                {item.subtitle && (
                                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                                        {item.subtitle}
                                    </span>
                                )}
                            </div>
                            <div className="flex items-center gap-2">
                                {item.badge}
                                <motion.div
                                    animate={{ rotate: isOpen ? 180 : 0 }}
                                    transition={transitions.spring}
                                >
                                    <ChevronDown size={16} style={{ color: "var(--text-muted)" }} />
                                </motion.div>
                            </div>
                        </button>

                        {/* Collapsible content */}
                        <AnimatePresence>
                            {isOpen && (
                                <motion.div
                                    variants={expandHeight}
                                    initial="initial"
                                    animate="animate"
                                    exit="exit"
                                >
                                    <div
                                        className="px-4 py-3 text-sm"
                                        style={{
                                            background: "var(--bg-panel)",
                                            color: "var(--text-secondary)",
                                        }}
                                    >
                                        {item.content}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                );
            })}
        </div>
    );
}

import React from "react";
import { motion } from "framer-motion";
import { fadeIn, transitions } from "../motion";

export interface TimelineItem {
    /** Unique id */
    id: string;
    /** Title (e.g., "v2 — LLM enrichment") */
    title: string;
    /** Subtitle / description */
    description?: string;
    /** Date/time string */
    date?: string;
    /** Dot color */
    color?: string;
    /** Optional action */
    action?: { label: string; onClick: () => void };
    /** Active / current item */
    active?: boolean;
}

export interface TimelineProps {
    /** Timeline items (top = newest) */
    items: TimelineItem[];
    /** Show animated entrance */
    animated?: boolean;
}

export function Timeline({ items, animated = true }: TimelineProps) {
    return (
        <div className="flex flex-col" role="list" aria-label="Timeline">
            {items.map((item, i) => (
                <motion.div
                    key={item.id}
                    className="flex gap-3"
                    role="listitem"
                    variants={animated ? fadeIn : undefined}
                    initial={animated ? "initial" : undefined}
                    animate={animated ? "animate" : undefined}
                    transition={animated ? { ...transitions.smooth, delay: i * 0.06 } : undefined}
                >
                    {/* Left: dot + connector line */}
                    <div className="flex flex-col items-center flex-shrink-0" style={{ width: 20 }}>
                        {/* Dot */}
                        <div
                            className="rounded-full flex-shrink-0"
                            style={{
                                width: item.active ? 12 : 8,
                                height: item.active ? 12 : 8,
                                marginTop: 6,
                                background: item.color ?? "var(--color-info)",
                                boxShadow: item.active ? `0 0 8px ${item.color ?? "var(--color-info)"}` : "none",
                            }}
                        />
                        {/* Connector line */}
                        {i < items.length - 1 && (
                            <div
                                className="flex-1 w-px"
                                style={{
                                    background: "var(--text-muted)",
                                    opacity: 0.3,
                                    minHeight: 24,
                                }}
                            />
                        )}
                    </div>

                    {/* Right: content */}
                    <div className="flex flex-col gap-0.5 pb-4 flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                            <span
                                className="text-sm font-medium truncate"
                                style={{ color: item.active ? "var(--text-primary)" : "var(--text-secondary)" }}
                            >
                                {item.title}
                            </span>
                            {item.date && (
                                <span className="text-[10px] flex-shrink-0 font-mono" style={{ color: "var(--text-muted)" }}>
                                    {item.date}
                                </span>
                            )}
                        </div>

                        {item.description && (
                            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                                {item.description}
                            </p>
                        )}

                        {item.action && (
                            <button
                                onClick={item.action.onClick}
                                className="text-xs font-medium mt-1 hover:underline transition-colors self-start"
                                style={{ color: item.color ?? "var(--color-info)" }}
                            >
                                {item.action.label}
                            </button>
                        )}
                    </div>
                </motion.div>
            ))}
        </div>
    );
}

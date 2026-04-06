import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { transitions } from "../motion";

export interface Tab {
    /** Unique key */
    id: string;
    /** Display label */
    label: string;
    /** Optional badge count */
    badge?: number;
    /** Tab content (render lazily) */
    content: React.ReactNode;
}

export interface TabPanelProps {
    /** List of tabs */
    tabs: Tab[];
    /** Controlled active tab id */
    activeId?: string;
    /** Callback on tab change */
    onChange?: (id: string) => void;
}

export function TabPanel({ tabs, activeId, onChange }: TabPanelProps) {
    const [internalId, setInternalId] = useState(tabs[0]?.id ?? "");
    const current = activeId ?? internalId;

    const handleSelect = (id: string) => {
        setInternalId(id);
        onChange?.(id);
    };

    const activeTab = tabs.find((t) => t.id === current);

    return (
        <div className="flex flex-col w-full">
            {/* Tab bar */}
            <div
                className="relative flex gap-0.5 px-2 pt-1"
                style={{
                    borderBottom: "var(--border-node)",
                    background: "var(--bg-panel)",
                }}
            >
                {tabs.map((tab) => {
                    const isActive = tab.id === current;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => handleSelect(tab.id)}
                            className="relative px-3 py-2 text-sm font-medium rounded-t-lg transition-colors"
                            style={{
                                color: isActive ? "var(--text-primary)" : "var(--text-muted)",
                                background: isActive ? "var(--bg-node)" : "transparent",
                            }}
                        >
                            <span className="flex items-center gap-1.5">
                                {tab.label}
                                {tab.badge !== undefined && (
                                    <span
                                        className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-semibold rounded-full"
                                        style={{
                                            background: isActive
                                                ? "var(--color-info)"
                                                : "var(--text-muted)",
                                            color: "var(--text-inverse)",
                                        }}
                                    >
                                        {tab.badge}
                                    </span>
                                )}
                            </span>
                            {/* Active indicator line */}
                            {isActive && (
                                <motion.div
                                    className="absolute bottom-0 left-2 right-2 h-0.5 rounded-full"
                                    style={{ background: "var(--color-info)" }}
                                    layoutId="tab-indicator"
                                    transition={transitions.spring}
                                />
                            )}
                        </button>
                    );
                })}
            </div>

            {/* Tab content */}
            <div className="relative overflow-hidden" style={{ minHeight: 100 }}>
                <AnimatePresence mode="wait">
                    <motion.div
                        key={current}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -8 }}
                        transition={transitions.smooth}
                        className="p-4"
                    >
                        {activeTab?.content}
                    </motion.div>
                </AnimatePresence>
            </div>
        </div>
    );
}

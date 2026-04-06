import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Check } from "lucide-react";
import { transitions } from "../motion";

export interface Chip {
    /** Unique key */
    id: string;
    /** Display label */
    label: string;
    /** Icon (optional) */
    icon?: React.ReactNode;
    /** Chip color (optional accent) */
    color?: string;
}

export interface FilterChipsProps {
    /** Available chips */
    chips: Chip[];
    /** Allow multiple selection */
    multiple?: boolean;
    /** Controlled selected ids */
    selected?: string[];
    /** Change callback */
    onChange?: (selected: string[]) => void;
    /** Chip size */
    size?: "sm" | "md";
}

export function FilterChips({
    chips,
    multiple = true,
    selected: controlledSelected,
    onChange,
    size = "md",
}: FilterChipsProps) {
    const [internalSelected, setInternalSelected] = useState<string[]>([]);
    const selected = controlledSelected ?? internalSelected;

    const toggle = (id: string) => {
        let next: string[];
        if (selected.includes(id)) {
            next = selected.filter((s) => s !== id);
        } else {
            next = multiple ? [...selected, id] : [id];
        }
        setInternalSelected(next);
        onChange?.(next);
    };

    const isSelected = (id: string) => selected.includes(id);

    const px = size === "sm" ? "px-2 py-0.5" : "px-3 py-1";
    const textSize = size === "sm" ? "text-[11px]" : "text-xs";

    return (
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter options">
            {chips.map((chip) => {
                const active = isSelected(chip.id);
                return (
                    <motion.button
                        key={chip.id}
                        onClick={() => toggle(chip.id)}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.97 }}
                        transition={transitions.spring}
                        className={`inline-flex items-center gap-1 ${px} ${textSize} font-medium rounded-full select-none transition-colors`}
                        style={{
                            background: active
                                ? chip.color || "var(--color-info)"
                                : "var(--bg-node-hover)",
                            color: active
                                ? "var(--text-inverse)"
                                : "var(--text-secondary)",
                            border: active
                                ? `1px solid transparent`
                                : "var(--border-node)",
                        }}
                        aria-pressed={active}
                    >
                        {/* M3: checkmark on selection for Filter chips */}
                        <AnimatePresence mode="wait">
                            {active ? (
                                <motion.span
                                    key="check"
                                    initial={{ scale: 0, width: 0 }}
                                    animate={{ scale: 1, width: "auto" }}
                                    exit={{ scale: 0, width: 0 }}
                                    transition={transitions.snappy}
                                >
                                    <Check size={size === "sm" ? 10 : 12} strokeWidth={3} />
                                </motion.span>
                            ) : chip.icon ? (
                                <motion.span
                                    key="icon"
                                    initial={{ scale: 0, width: 0 }}
                                    animate={{ scale: 1, width: "auto" }}
                                    exit={{ scale: 0, width: 0 }}
                                    transition={transitions.snappy}
                                >
                                    {chip.icon}
                                </motion.span>
                            ) : null}
                        </AnimatePresence>

                        <span>{chip.label}</span>
                    </motion.button>
                );
            })}
        </div>
    );
}

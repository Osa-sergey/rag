import React, { useState } from "react";
import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { transitions } from "../motion";

export interface ViewOption {
    id: string;
    label: string;
    icon?: React.ReactNode;
}

export interface ViewSwitcherProps {
    /** Available views */
    options: ViewOption[];
    /** Selected view id */
    value?: string;
    /** Change handler */
    onChange?: (id: string) => void;
    /** Size */
    size?: "sm" | "md";
}

export function ViewSwitcher({
    options,
    value: controlledValue,
    onChange,
    size = "md",
}: ViewSwitcherProps) {
    const [internalValue, setInternalValue] = useState(options[0]?.id ?? "");
    const selected = controlledValue ?? internalValue;

    const handleSelect = (id: string) => {
        setInternalValue(id);
        onChange?.(id);
    };

    const px = size === "sm" ? "px-2.5 py-1" : "px-3.5 py-1.5";
    const textSize = size === "sm" ? "text-[11px]" : "text-xs";

    return (
        <div
            className="inline-flex rounded-full p-0.5"
            style={{ background: "var(--bg-node-hover)", border: "var(--border-node)" }}
            role="radiogroup"
        >
            {options.map((opt) => {
                const isSelected = opt.id === selected;
                return (
                    <button
                        key={opt.id}
                        onClick={() => handleSelect(opt.id)}
                        className={`relative flex items-center gap-1.5 ${px} ${textSize} font-medium rounded-full transition-colors select-none`}
                        style={{ color: isSelected ? "var(--text-primary)" : "var(--text-muted)" }}
                        role="radio"
                        aria-checked={isSelected}
                    >
                        {/* Animated background pill */}
                        {isSelected && (
                            <motion.div
                                layoutId="view-switcher-pill"
                                className="absolute inset-0 rounded-full"
                                style={{ background: "var(--bg-panel)", border: "var(--border-node)" }}
                                transition={transitions.spring}
                            />
                        )}

                        {/* Content */}
                        <span className="relative flex items-center gap-1.5">
                            {isSelected && (
                                <motion.span
                                    initial={{ scale: 0, width: 0 }}
                                    animate={{ scale: 1, width: "auto" }}
                                    transition={transitions.snappy}
                                >
                                    <Check size={size === "sm" ? 10 : 12} strokeWidth={3} />
                                </motion.span>
                            )}
                            {opt.icon && <span className="flex">{opt.icon}</span>}
                            {opt.label}
                        </span>
                    </button>
                );
            })}
        </div>
    );
}

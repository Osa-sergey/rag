import React, { useState, useId } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, Minus } from "lucide-react";
import { transitions } from "../motion";

export interface CheckboxProps {
    /** Label */
    label?: string;
    /** Description */
    description?: string;
    /** Controlled checked state */
    checked?: boolean;
    /** Indeterminate state (partial selection) */
    indeterminate?: boolean;
    /** Change handler */
    onChange?: (checked: boolean) => void;
    /** Disabled */
    disabled?: boolean;
    /** Size */
    size?: "sm" | "md";
    /** Accent color */
    color?: string;
}

export function Checkbox({
    label,
    description,
    checked: controlledChecked,
    indeterminate = false,
    onChange,
    disabled = false,
    size = "md",
    color = "var(--color-info)",
}: CheckboxProps) {
    const [internalChecked, setInternalChecked] = useState(false);
    const id = useId();
    const isChecked = controlledChecked ?? internalChecked;
    const isActive = isChecked || indeterminate;

    const handleToggle = () => {
        if (disabled) return;
        const next = !isChecked;
        setInternalChecked(next);
        onChange?.(next);
    };

    const boxSize = size === "sm" ? 16 : 20;
    const iconSize = size === "sm" ? 10 : 14;

    return (
        <div
            className="flex items-start gap-2.5 select-none"
            style={{ opacity: disabled ? 0.5 : 1, cursor: disabled ? "not-allowed" : "pointer" }}
            onClick={handleToggle}
        >
            {/* Checkbox box */}
            <div
                className="relative flex-shrink-0 rounded flex items-center justify-center transition-colors"
                style={{
                    width: boxSize,
                    height: boxSize,
                    marginTop: 2,
                    background: isActive ? color : "transparent",
                    border: isActive ? "none" : "2px solid var(--text-muted)",
                    borderRadius: size === "sm" ? 3 : 4,
                }}
                role="checkbox"
                aria-checked={indeterminate ? "mixed" : isChecked}
                aria-labelledby={label ? id : undefined}
                tabIndex={disabled ? -1 : 0}
                onKeyDown={(e) => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); handleToggle(); } }}
            >
                <AnimatePresence mode="wait">
                    {isActive && (
                        <motion.span
                            key={indeterminate ? "minus" : "check"}
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            exit={{ scale: 0 }}
                            transition={transitions.spring}
                        >
                            {indeterminate ? (
                                <Minus size={iconSize} style={{ color: "var(--text-inverse)" }} strokeWidth={3} />
                            ) : (
                                <Check size={iconSize} style={{ color: "var(--text-inverse)" }} strokeWidth={3} />
                            )}
                        </motion.span>
                    )}
                </AnimatePresence>
            </div>

            {/* Labels */}
            {(label || description) && (
                <div className="flex flex-col gap-0.5">
                    {label && (
                        <span id={id} className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                            {label}
                        </span>
                    )}
                    {description && (
                        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                            {description}
                        </span>
                    )}
                </div>
            )}
        </div>
    );
}

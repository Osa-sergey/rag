import React, { useState, useId } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { transitions } from "../motion";

export type InputVariant = "outlined" | "filled";
export type InputSize = "sm" | "md" | "lg";

export interface InputProps {
    /** Label (required per M3) */
    label: string;
    /** Value (controlled) */
    value?: string;
    /** Change handler */
    onChange?: (value: string) => void;
    /** Placeholder (shown when empty & focused) */
    placeholder?: string;
    /** Helper text (hidden when error shown) */
    helperText?: string;
    /** Error text (replaces helperText) */
    errorText?: string;
    /** Input type */
    type?: "text" | "number" | "password" | "email" | "url";
    /** M3 variant */
    variant?: InputVariant;
    /** Size */
    size?: InputSize;
    /** Disabled */
    disabled?: boolean;
    /** Leading icon */
    leadingIcon?: React.ReactNode;
    /** Trailing icon or action */
    trailingIcon?: React.ReactNode;
    /** Full width */
    fullWidth?: boolean;
}

const sizeStyles: Record<InputSize, { height: number; fontSize: number; labelSize: number }> = {
    sm: { height: 32, fontSize: 12, labelSize: 9 },
    md: { height: 48, fontSize: 14, labelSize: 11 },
    lg: { height: 56, fontSize: 16, labelSize: 12 },
};

export function Input({
    label,
    value: controlledValue,
    onChange,
    placeholder,
    helperText,
    errorText,
    type = "text",
    variant = "outlined",
    size = "md",
    disabled = false,
    leadingIcon,
    trailingIcon,
    fullWidth = false,
}: InputProps) {
    const [internalValue, setInternalValue] = useState("");
    const [focused, setFocused] = useState(false);
    const id = useId();

    const value = controlledValue ?? internalValue;
    const hasValue = value.length > 0;
    const floated = focused || hasValue;
    const hasError = !!errorText;
    const styles = sizeStyles[size];

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setInternalValue(e.target.value);
        onChange?.(e.target.value);
    };

    const borderColor = hasError
        ? "var(--color-error)"
        : focused
            ? "var(--color-info)"
            : "var(--text-muted)";

    const bgColor = variant === "filled" ? "var(--bg-node-hover)" : "transparent";

    return (
        <div
            className="flex flex-col gap-1.5"
            style={{ width: fullWidth ? "100%" : "auto", minWidth: 200, opacity: disabled ? 0.5 : 1 }}
        >
            {/* Input container */}
            <div
                className="relative flex items-center gap-2 rounded-lg px-3 transition-all"
                style={{
                    height: styles.height,
                    border: variant === "outlined"
                        ? `${focused || hasError ? 2 : 1}px solid ${borderColor}`
                        : "none",
                    borderBottom: variant === "filled"
                        ? `2px solid ${borderColor}`
                        : undefined,
                    background: bgColor,
                }}
            >
                {/* Leading icon */}
                {leadingIcon && (
                    <span
                        className="flex-shrink-0 flex items-center"
                        style={{ color: focused ? "var(--color-info)" : "var(--text-muted)" }}
                    >
                        {leadingIcon}
                    </span>
                )}

                {/* Label + Input stack */}
                <div className="relative flex-1 flex flex-col justify-center">
                    {/* Floating label */}
                    <motion.label
                        htmlFor={id}
                        className="absolute left-0 pointer-events-none font-medium origin-top-left"
                        animate={{
                            y: floated ? -styles.height / 2 + 8 : 0,
                            scale: floated ? 0.75 : 1,
                            color: hasError
                                ? "var(--color-error)"
                                : focused
                                    ? "var(--color-info)"
                                    : "var(--text-muted)",
                        }}
                        transition={transitions.snappy}
                        style={{ fontSize: styles.fontSize }}
                    >
                        {label}
                    </motion.label>

                    {/* Input */}
                    <input
                        id={id}
                        type={type}
                        value={value}
                        onChange={handleChange}
                        onFocus={() => setFocused(true)}
                        onBlur={() => setFocused(false)}
                        disabled={disabled}
                        placeholder={focused ? placeholder : ""}
                        className="bg-transparent outline-none w-full font-mono"
                        style={{
                            fontSize: styles.fontSize,
                            color: "var(--text-primary)",
                            paddingTop: floated ? 8 : 0,
                            caretColor: hasError ? "var(--color-error)" : "var(--color-info)",
                        }}
                        aria-invalid={hasError}
                        aria-describedby={helperText || errorText ? `${id}-helper` : undefined}
                    />
                </div>

                {/* Trailing icon */}
                {trailingIcon && (
                    <span
                        className="flex-shrink-0 flex items-center"
                        style={{ color: hasError ? "var(--color-error)" : "var(--text-muted)" }}
                    >
                        {trailingIcon}
                    </span>
                )}
            </div>

            {/* Helper / Error text (M3: error replaces helper) */}
            <AnimatePresence mode="wait">
                {(errorText || helperText) && (
                    <motion.p
                        key={hasError ? "error" : "helper"}
                        id={`${id}-helper`}
                        role={hasError ? "alert" : undefined}
                        initial={{ opacity: 0, y: -4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -4 }}
                        transition={transitions.snappy}
                        className="text-xs px-3"
                        style={{
                            color: hasError ? "var(--color-error)" : "var(--text-muted)",
                        }}
                    >
                        {hasError ? `⚠ ${errorText}` : helperText}
                    </motion.p>
                )}
            </AnimatePresence>
        </div>
    );
}

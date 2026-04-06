import React, { useState, useId, useCallback } from "react";
import { motion } from "framer-motion";
import { transitions } from "../motion";

export interface SliderProps {
    /** Label */
    label?: string;
    /** Min value */
    min?: number;
    /** Max value */
    max?: number;
    /** Step increment */
    step?: number;
    /** Controlled value */
    value?: number;
    /** Change handler */
    onChange?: (value: number) => void;
    /** Show current value label */
    showValue?: boolean;
    /** Format value display */
    formatValue?: (val: number) => string;
    /** Tick marks count (0 = none) */
    ticks?: number;
    /** Disabled */
    disabled?: boolean;
    /** Accent color */
    color?: string;
}

export function Slider({
    label,
    min = 0,
    max = 100,
    step = 1,
    value: controlledValue,
    onChange,
    showValue = true,
    formatValue,
    ticks = 0,
    disabled = false,
    color = "var(--color-info)",
}: SliderProps) {
    const [internalValue, setInternalValue] = useState(min);
    const id = useId();
    const value = controlledValue ?? internalValue;
    const percent = ((value - min) / (max - min)) * 100;

    const displayValue = formatValue ? formatValue(value) : String(value);

    const handleChange = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            const v = Number(e.target.value);
            setInternalValue(v);
            onChange?.(v);
        },
        [onChange],
    );

    const tickMarks = ticks > 0
        ? Array.from({ length: ticks + 1 }, (_, i) => (i / ticks) * 100)
        : [];

    return (
        <div
            className="flex flex-col gap-2 w-full"
            style={{ opacity: disabled ? 0.5 : 1 }}
        >
            {/* Header */}
            {(label || showValue) && (
                <div className="flex items-center justify-between">
                    {label && (
                        <label htmlFor={id} className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                            {label}
                        </label>
                    )}
                    {showValue && (
                        <motion.span
                            key={displayValue}
                            initial={{ y: -4, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            transition={transitions.snappy}
                            className="text-xs font-mono font-semibold"
                            style={{ color }}
                        >
                            {displayValue}
                        </motion.span>
                    )}
                </div>
            )}

            {/* Slider track */}
            <div className="relative h-5 flex items-center">
                {/* Background track */}
                <div
                    className="absolute w-full rounded-full"
                    style={{ height: 4, background: "var(--bg-node-hover)" }}
                />

                {/* Active fill */}
                <motion.div
                    className="absolute rounded-full"
                    style={{ height: 4, background: color, left: 0 }}
                    animate={{ width: `${percent}%` }}
                    transition={transitions.snappy}
                />

                {/* Tick marks */}
                {tickMarks.map((pos) => (
                    <div
                        key={pos}
                        className="absolute rounded-full"
                        style={{
                            width: 2,
                            height: 8,
                            left: `${pos}%`,
                            transform: "translateX(-50%)",
                            background: pos <= percent ? color : "var(--text-muted)",
                            opacity: 0.5,
                        }}
                    />
                ))}

                {/* Native input (invisible, for accessibility + interaction) */}
                <input
                    id={id}
                    type="range"
                    min={min}
                    max={max}
                    step={step}
                    value={value}
                    onChange={handleChange}
                    disabled={disabled}
                    className="absolute w-full opacity-0 cursor-pointer"
                    style={{
                        height: 20,
                        WebkitAppearance: "none",
                    }}
                />

                {/* Custom thumb */}
                <motion.div
                    className="absolute pointer-events-none rounded-full"
                    animate={{ left: `${percent}%` }}
                    transition={transitions.snappy}
                    style={{
                        width: 16,
                        height: 16,
                        transform: "translateX(-50%)",
                        background: color,
                        boxShadow: `0 0 0 3px var(--bg-panel), 0 2px 6px rgba(0,0,0,0.3)`,
                    }}
                />
            </div>

            {/* Min/Max labels */}
            {ticks > 0 && (
                <div className="flex justify-between">
                    <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                        {formatValue ? formatValue(min) : min}
                    </span>
                    <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                        {formatValue ? formatValue(max) : max}
                    </span>
                </div>
            )}
        </div>
    );
}

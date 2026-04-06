import React, { useState, useCallback, useRef, useEffect } from "react";

export interface RangeInputProps {
    /** Current min value */
    min?: number;
    /** Current max value */
    max?: number;
    /** Range lower bound */
    rangeLow?: number;
    /** Range upper bound */
    rangeHigh?: number;
    /** Step */
    step?: number;
    /** Allow single value (not range) */
    singleValue?: boolean;
    /** Current single value */
    value?: number;
    /** Label */
    label?: string;
    /** Format function for display */
    format?: (v: number) => string;
    /** On range change */
    onRangeChange?: (min: number, max: number) => void;
    /** On single value change */
    onValueChange?: (val: number) => void;
    /** Color accent */
    color?: string;
    /** Compact mode */
    compact?: boolean;
}

export function RangeInput({
    min: controlledMin,
    max: controlledMax,
    rangeLow = 0,
    rangeHigh = 100,
    step = 1,
    singleValue = false,
    value: controlledValue,
    label,
    format = (v) => String(v),
    onRangeChange,
    onValueChange,
    color = "var(--color-info)",
    compact = false,
}: RangeInputProps) {
    const [internalMin, setInternalMin] = useState(controlledMin ?? rangeLow);
    const [internalMax, setInternalMax] = useState(controlledMax ?? rangeHigh);
    const [internalVal, setInternalVal] = useState(controlledValue ?? rangeLow);
    const trackRef = useRef<HTMLDivElement>(null);

    const currentMin = controlledMin ?? internalMin;
    const currentMax = controlledMax ?? internalMax;
    const currentVal = controlledValue ?? internalVal;

    const total = rangeHigh - rangeLow;
    const minPct = ((currentMin - rangeLow) / total) * 100;
    const maxPct = ((currentMax - rangeLow) / total) * 100;
    const valPct = ((currentVal - rangeLow) / total) * 100;

    const handleMinChange = useCallback((v: number) => {
        const clamped = Math.min(v, currentMax - step);
        setInternalMin(clamped);
        onRangeChange?.(clamped, currentMax);
    }, [currentMax, step, onRangeChange]);

    const handleMaxChange = useCallback((v: number) => {
        const clamped = Math.max(v, currentMin + step);
        setInternalMax(clamped);
        onRangeChange?.(currentMin, clamped);
    }, [currentMin, step, onRangeChange]);

    const handleValueChange = useCallback((v: number) => {
        setInternalVal(v);
        onValueChange?.(v);
    }, [onValueChange]);

    return (
        <div className="flex flex-col gap-1.5" style={{ minWidth: compact ? 140 : 200 }}>
            {/* Label + values */}
            {label && (
                <div className="flex items-center justify-between">
                    <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                        {label}
                    </span>
                    <span className="text-[10px] font-mono font-bold" style={{ color }}>
                        {singleValue
                            ? format(currentVal)
                            : `${format(currentMin)} – ${format(currentMax)}`}
                    </span>
                </div>
            )}

            {/* Track */}
            <div className="relative" style={{ height: compact ? 20 : 28 }}>
                {/* Base track */}
                <div
                    ref={trackRef}
                    className="absolute left-0 right-0 rounded-full"
                    style={{
                        top: "50%",
                        transform: "translateY(-50%)",
                        height: compact ? 4 : 6,
                        background: "var(--bg-node-hover)",
                    }}
                />

                {/* Active range fill */}
                <div
                    className="absolute rounded-full"
                    style={{
                        top: "50%",
                        transform: "translateY(-50%)",
                        height: compact ? 4 : 6,
                        left: singleValue ? "0%" : `${minPct}%`,
                        width: singleValue ? `${valPct}%` : `${maxPct - minPct}%`,
                        background: color,
                        opacity: 0.6,
                    }}
                />

                {singleValue ? (
                    /* Single thumb */
                    <input
                        type="range"
                        min={rangeLow}
                        max={rangeHigh}
                        step={step}
                        value={currentVal}
                        onChange={(e) => handleValueChange(Number(e.target.value))}
                        className="absolute w-full appearance-none bg-transparent cursor-pointer"
                        style={{ top: 0, height: "100%", zIndex: 2 }}
                    />
                ) : (
                    /* Dual thumbs */
                    <>
                        <input
                            type="range"
                            min={rangeLow}
                            max={rangeHigh}
                            step={step}
                            value={currentMin}
                            onChange={(e) => handleMinChange(Number(e.target.value))}
                            className="absolute w-full appearance-none bg-transparent cursor-pointer"
                            style={{ top: 0, height: "100%", zIndex: 3 }}
                        />
                        <input
                            type="range"
                            min={rangeLow}
                            max={rangeHigh}
                            step={step}
                            value={currentMax}
                            onChange={(e) => handleMaxChange(Number(e.target.value))}
                            className="absolute w-full appearance-none bg-transparent cursor-pointer"
                            style={{ top: 0, height: "100%", zIndex: 4 }}
                        />
                    </>
                )}
            </div>

            {/* Min/Max numeric inputs */}
            {!compact && (
                <div className="flex items-center gap-2">
                    {singleValue ? (
                        <input
                            type="number"
                            min={rangeLow}
                            max={rangeHigh}
                            step={step}
                            value={currentVal}
                            onChange={(e) => handleValueChange(Number(e.target.value))}
                            className="flex-1 px-2 py-1 rounded text-[10px] font-mono text-center"
                            style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-primary)" }}
                        />
                    ) : (
                        <>
                            <input
                                type="number"
                                min={rangeLow}
                                max={currentMax}
                                step={step}
                                value={currentMin}
                                onChange={(e) => handleMinChange(Number(e.target.value))}
                                className="flex-1 px-2 py-1 rounded text-[10px] font-mono text-center"
                                style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-primary)" }}
                            />
                            <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>—</span>
                            <input
                                type="number"
                                min={currentMin}
                                max={rangeHigh}
                                step={step}
                                value={currentMax}
                                onChange={(e) => handleMaxChange(Number(e.target.value))}
                                className="flex-1 px-2 py-1 rounded text-[10px] font-mono text-center"
                                style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-primary)" }}
                            />
                        </>
                    )}
                </div>
            )}
        </div>
    );
}

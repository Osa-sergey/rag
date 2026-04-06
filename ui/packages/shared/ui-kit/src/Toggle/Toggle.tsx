import React, { useState, useId } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, X } from "lucide-react";
import { transitions } from "../motion";

export type ToggleVariant = "default" | "labeled";

export interface ToggleProps {
    /** Label text (outside the toggle) */
    label?: string;
    /** Description / helper */
    description?: string;
    /** Controlled state */
    checked?: boolean;
    /** Change callback — M3: effect must be instant */
    onChange?: (checked: boolean) => void;
    /** Disabled */
    disabled?: boolean;
    /** Show check/X icons inside thumb (M3 optional, default variant only) */
    showIcons?: boolean;
    /** Size variant */
    size?: "sm" | "md" | "lg";
    /**
     * Toggle variant:
     * - "default": standard M3 switch
     * - "labeled": wide toggle with text labels inside track
     */
    variant?: ToggleVariant;
    /** Label shown inside track when OFF (only for "labeled" variant) */
    offLabel?: string;
    /** Label shown inside track when ON (only for "labeled" variant) */
    onLabel?: string;
    /** Icon for OFF state inside thumb (only for "labeled" variant) */
    offIcon?: React.ReactNode;
    /** Icon for ON state inside thumb (only for "labeled" variant) */
    onIcon?: React.ReactNode;
    /** Accent color for ON state */
    activeColor?: string;
    /** Track color for OFF state */
    inactiveColor?: string;
}

/* ─── Dimensions ──────────────────────────────────── */

const defaultDims = {
    sm: { trackW: 36, trackH: 20, thumb: 16 },
    md: { trackW: 48, trackH: 26, thumb: 22 },
    lg: { trackW: 56, trackH: 30, thumb: 26 },
};

const labeledDims = {
    sm: { trackW: 100, trackH: 30, thumb: 30 },
    md: { trackW: 130, trackH: 36, thumb: 36 },
    lg: { trackW: 160, trackH: 42, thumb: 42 },
};

/* ─── Component ───────────────────────────────────── */

export function Toggle({
    label,
    description,
    checked: controlledChecked,
    onChange,
    disabled = false,
    showIcons = true,
    size = "md",
    variant = "default",
    offLabel,
    onLabel,
    offIcon,
    onIcon,
    activeColor = "var(--color-info)",
    inactiveColor,
}: ToggleProps) {
    const [internalChecked, setInternalChecked] = useState(false);
    const htmlId = useId();
    const isChecked = controlledChecked ?? internalChecked;

    const handleToggle = () => {
        if (disabled) return;
        const next = !isChecked;
        setInternalChecked(next);
        onChange?.(next);
    };

    const kbHandler = (e: React.KeyboardEvent) => {
        if (e.key === " " || e.key === "Enter") { e.preventDefault(); handleToggle(); }
    };

    /* ═══════════════════════════════════════════════════
       Labeled variant — wide, text inside, thumb = full height, flush edges
       ═══════════════════════════════════════════════════ */
    if (variant === "labeled") {
        const d = labeledDims[size];
        // thumb is full height, flush to the edge
        const thumbTravel = d.trackW - d.thumb;

        return (
            <div
                className="flex items-start gap-3"
                style={{ opacity: disabled ? 0.5 : 1, cursor: disabled ? "not-allowed" : "pointer" }}
                onClick={handleToggle}
            >
                <div
                    className="relative flex-shrink-0 rounded-full select-none overflow-hidden"
                    style={{
                        width: d.trackW,
                        height: d.trackH,
                        background: isChecked
                            ? (activeColor)
                            : (inactiveColor ?? "var(--bg-node-hover)"),
                        border: `1px solid ${isChecked ? "transparent" : "var(--text-muted)"}`,
                        transition: "background 0.2s, border 0.2s",
                    }}
                    role="switch"
                    aria-checked={isChecked}
                    aria-labelledby={label ? htmlId : undefined}
                    tabIndex={disabled ? -1 : 0}
                    onKeyDown={kbHandler}
                >
                    {/* ── Text: OFF label on the RIGHT side (visible when unchecked) ── */}
                    <span
                        className="absolute flex items-center justify-center font-bold uppercase tracking-wider transition-opacity"
                        style={{
                            /* position text in the space NOT occupied by thumb */
                            right: 0,
                            top: 0,
                            bottom: 0,
                            width: d.trackW - d.thumb,
                            fontSize: size === "sm" ? 9 : size === "md" ? 10 : 12,
                            color: "var(--text-secondary)",
                            opacity: isChecked ? 0 : 1,
                            pointerEvents: "none",
                        }}
                    >
                        {offLabel}
                    </span>

                    {/* ── Text: ON label on the LEFT side (visible when checked) ── */}
                    <span
                        className="absolute flex items-center justify-center font-bold uppercase tracking-wider transition-opacity"
                        style={{
                            left: 0,
                            top: 0,
                            bottom: 0,
                            width: d.trackW - d.thumb,
                            fontSize: size === "sm" ? 9 : size === "md" ? 10 : 12,
                            color: "var(--text-inverse)",
                            opacity: isChecked ? 1 : 0,
                            pointerEvents: "none",
                        }}
                    >
                        {onLabel}
                    </span>

                    {/* ── Thumb: full height, flush to edge ── */}
                    <motion.div
                        className="absolute top-0 left-0 rounded-full flex items-center justify-center"
                        animate={{ x: isChecked ? thumbTravel : 0 }}
                        style={{
                            width: d.thumb,
                            height: d.thumb,
                            background: isChecked ? "var(--text-inverse)" : "var(--text-primary)",
                            boxShadow: "0 2px 8px rgba(0,0,0,0.25)",
                        }}
                        transition={transitions.spring}
                    >
                        <AnimatePresence mode="wait">
                            {isChecked ? (
                                onIcon && (
                                    <motion.span key="on-icon" initial={{ scale: 0, rotate: -90 }} animate={{ scale: 1, rotate: 0 }} exit={{ scale: 0 }} transition={transitions.spring}>
                                        {onIcon}
                                    </motion.span>
                                )
                            ) : (
                                offIcon && (
                                    <motion.span key="off-icon" initial={{ scale: 0, rotate: 90 }} animate={{ scale: 1, rotate: 0 }} exit={{ scale: 0 }} transition={transitions.spring}>
                                        {offIcon}
                                    </motion.span>
                                )
                            )}
                        </AnimatePresence>
                    </motion.div>
                </div>

                {/* External labels */}
                {(label || description) && (
                    <div className="flex flex-col gap-0.5 select-none">
                        {label && <span id={htmlId} className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{label}</span>}
                        {description && <span className="text-xs" style={{ color: "var(--text-muted)" }}>{description}</span>}
                    </div>
                )}
            </div>
        );
    }

    /* ═══════════════════════════════════════════════════
       Default M3 switch
       ═══════════════════════════════════════════════════ */
    const d = defaultDims[size];
    const pad = (d.trackH - d.thumb) / 2;

    return (
        <div
            className="flex items-start gap-3"
            style={{ opacity: disabled ? 0.5 : 1, cursor: disabled ? "not-allowed" : "pointer" }}
            onClick={handleToggle}
        >
            <div
                className="relative flex-shrink-0 rounded-full"
                style={{
                    width: d.trackW,
                    height: d.trackH,
                    background: isChecked ? activeColor : (inactiveColor ?? "var(--text-muted)"),
                    boxShadow: isChecked ? "none" : "inset 0 0 0 1px var(--text-muted)",
                    transition: "background 0.2s, box-shadow 0.2s",
                }}
                role="switch"
                aria-checked={isChecked}
                aria-labelledby={label ? htmlId : undefined}
                tabIndex={disabled ? -1 : 0}
                onKeyDown={kbHandler}
            >
                <motion.div
                    className="absolute rounded-full flex items-center justify-center"
                    animate={{ x: isChecked ? d.trackW - d.thumb - pad : 0 }}
                    style={{
                        top: pad,
                        left: pad,
                        width: d.thumb,
                        height: d.thumb,
                        background: isChecked ? "var(--text-inverse)" : "var(--bg-node)",
                        boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
                    }}
                    transition={transitions.spring}
                >
                    {showIcons && (
                        <AnimatePresence mode="wait">
                            <motion.span
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                exit={{ scale: 0 }}
                                key={isChecked ? "chk" : "x"}
                            >
                                {isChecked ? (
                                    <Check size={d.thumb * 0.5} style={{ color: activeColor }} strokeWidth={3} />
                                ) : (
                                    <X size={d.thumb * 0.5} style={{ color: "var(--text-muted)" }} strokeWidth={3} />
                                )}
                            </motion.span>
                        </AnimatePresence>
                    )}
                </motion.div>
            </div>

            {(label || description) && (
                <div className="flex flex-col gap-0.5 select-none">
                    {label && <span id={htmlId} className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{label}</span>}
                    {description && <span className="text-xs" style={{ color: "var(--text-muted)" }}>{description}</span>}
                </div>
            )}
        </div>
    );
}

import React, { useState } from "react";
import { Pipette } from "lucide-react";

export interface ColorPickerProps {
    /** Current color value (hex) */
    value?: string;
    /** Change handler */
    onChange?: (color: string) => void;
    /** Preset palette */
    palette?: string[];
    /** Label */
    label?: string;
    /** Allow custom hex input */
    allowCustom?: boolean;
}

const defaultPalette = [
    "#ef4444", "#f97316", "#f59e0b", "#eab308",
    "#22c55e", "#10b981", "#14b8a6", "#06b6d4",
    "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7",
    "#d946ef", "#ec4899", "#f43f5e", "#64748b",
    "#1e293b", "#fafafa",
];

export function ColorPicker({
    value,
    onChange,
    palette = defaultPalette,
    label,
    allowCustom = true,
}: ColorPickerProps) {
    const [customHex, setCustomHex] = useState(value ?? "#6366f1");
    const current = value ?? customHex;

    const handleSelect = (color: string) => {
        setCustomHex(color);
        onChange?.(color);
    };

    const handleCustomInput = (hex: string) => {
        setCustomHex(hex);
        if (/^#[0-9a-fA-F]{6}$/.test(hex)) {
            onChange?.(hex);
        }
    };

    return (
        <div className="flex flex-col gap-2" style={{ maxWidth: 240 }}>
            {label && (
                <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                    {label}
                </label>
            )}

            {/* Preview */}
            <div className="flex items-center gap-3">
                <div
                    className="w-10 h-10 rounded-lg flex-shrink-0"
                    style={{
                        background: current,
                        boxShadow: `0 0 12px ${current}40`,
                        border: "2px solid rgba(255,255,255,0.1)",
                    }}
                />
                <div className="flex flex-col gap-0.5">
                    <span className="text-xs font-mono font-semibold" style={{ color: "var(--text-primary)" }}>
                        {current.toUpperCase()}
                    </span>
                    <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                        Selected color
                    </span>
                </div>
            </div>

            {/* Palette grid */}
            <div className="grid grid-cols-6 gap-1.5">
                {palette.map((color) => (
                    <button
                        key={color}
                        onClick={() => handleSelect(color)}
                        className="w-7 h-7 rounded-lg transition-all hover:scale-110"
                        style={{
                            background: color,
                            boxShadow: current === color ? `0 0 0 2px var(--bg-panel), 0 0 0 3.5px ${color}` : "none",
                        }}
                        title={color}
                    />
                ))}
            </div>

            {/* Custom hex input */}
            {allowCustom && (
                <div className="flex items-center gap-2">
                    <Pipette size={12} style={{ color: "var(--text-muted)" }} />
                    <input
                        type="text"
                        value={customHex}
                        onChange={(e) => handleCustomInput(e.target.value)}
                        className="flex-1 px-2 py-1 rounded text-xs font-mono"
                        style={{
                            background: "var(--bg-node)",
                            border: "var(--border-node)",
                            color: "var(--text-primary)",
                        }}
                        placeholder="#000000"
                        maxLength={7}
                    />
                </div>
            )}
        </div>
    );
}

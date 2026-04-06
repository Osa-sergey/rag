import React, { useState, useEffect } from "react";
import { ColorPicker } from "../ColorPicker";
import { IconPicker } from "../IconPicker";

export interface NodeAppearance {
    color: string;
    icon: string;
}

export interface NodeAppearanceEditorProps {
    /** Current appearance */
    value?: NodeAppearance;
    /** On change handler */
    onChange?: (val: NodeAppearance) => void;
}

export function NodeAppearanceEditor({
    value = { color: "var(--color-info)", icon: "database" },
    onChange,
}: NodeAppearanceEditorProps) {
    const [local, setLocal] = useState<NodeAppearance>(value);

    // Sync if external value changes
    useEffect(() => {
        setLocal(value);
    }, [value.color, value.icon]);

    const handleChange = (update: Partial<NodeAppearance>) => {
        const next = { ...local, ...update };
        setLocal(next);
        onChange?.(next);
    };

    return (
        <div className="flex flex-col gap-6 w-full max-w-sm select-none">
            <div className="flex flex-col gap-2">
                <span className="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-widest px-1">
                    Accent Color
                </span>
                <ColorPicker
                    value={local.color}
                    onChange={(color) => handleChange({ color })}
                />
            </div>

            <div className="w-full h-px bg-[var(--border-node)]" />

            <div className="flex flex-col gap-2">
                <span className="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-widest px-1">
                    Node Icon
                </span>
                <IconPicker
                    value={local.icon}
                    onChange={(icon) => handleChange({ icon })}
                    searchable
                />
            </div>
        </div>
    );
}

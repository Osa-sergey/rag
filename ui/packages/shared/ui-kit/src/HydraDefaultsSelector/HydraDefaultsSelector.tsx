import React from "react";
import { Select } from "../Select";
import { Badge } from "../Badge";
import { Layers } from "lucide-react";

export interface HydraDefaultGroup {
    /** Configuration group id (e.g., config/embed/...) */
    id: string;
    /** Display label (e.g., "Embedding Model") */
    label: string;
    /** Available YAML options in that folder */
    options: { label: string; value: string; description?: string }[];
    /** Currently active selection */
    selectedValue?: string;
}

export interface HydraDefaultsSelectorProps {
    /** List of Hydra default groups */
    groups: HydraDefaultGroup[];
    /** On selection change */
    onChange?: (groupId: string, value: string) => void;
}

export function HydraDefaultsSelector({ groups, onChange }: HydraDefaultsSelectorProps) {
    if (!groups || groups.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-6 rounded-xl" style={{ background: "var(--bg-node)", border: "1px dashed rgba(255,255,255,0.1)" }}>
                <Layers size={16} style={{ color: "var(--text-muted)", marginBottom: 8 }} />
                <span className="text-xs" style={{ color: "var(--text-secondary)" }}>No defaults defined</span>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-4 p-4 rounded-xl" style={{ background: "var(--bg-panel)", border: "1px solid var(--border-node)" }}>
            <div className="flex items-center gap-2 mb-2">
                <Layers size={14} style={{ color: "var(--color-info)" }} />
                <h3 className="text-xs font-bold" style={{ color: "var(--text-primary)" }}>Hydra Defaults</h3>
                <Badge variant="info">hydra/config</Badge>
            </div>

            <div className="flex flex-col gap-3">
                {groups.map((group) => (
                    <div key={group.id} className="flex flex-col gap-1.5">
                        <label className="text-[10px] font-semibold uppercase tracking-wider pl-1" style={{ color: "var(--text-secondary)" }}>
                            {group.label}
                        </label>
                        <Select
                            value={group.selectedValue}
                            options={group.options}
                            onChange={(v) => onChange?.(group.id, v as string)}
                            placeholder={`Select ${group.label}`}
                        />
                    </div>
                ))}
            </div>
        </div>
    );
}

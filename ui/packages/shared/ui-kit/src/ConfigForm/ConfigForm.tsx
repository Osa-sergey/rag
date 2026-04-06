
import { Badge } from "../Badge";
import { Input } from "../Input";
import { Toggle } from "../Toggle";
import { Select } from "../Select";
import { KeyValueList } from "../KeyValueList";
import { AlertCircle } from "lucide-react";

/** Source of config value */
export type ConfigSource = "DEF" | "GLB" | "STP" | "OVR";

export interface ConfigField {
    key: string;
    label: string;
    type: "string" | "number" | "boolean" | "select" | "dict";
    value: any;
    source: ConfigSource;
    options?: { label: string; value: string }[];
    error?: string;
    description?: string;
}

export interface ConfigGroup {
    id: string;
    title: string;
    fields: ConfigField[];
}

export interface ConfigFormProps {
    groups: ConfigGroup[];
    onChange?: (group: string, key: string, value: any) => void;
}

function getSourceVariant(source: ConfigSource): "default" | "success" | "warning" | "error" | "info" {
    switch (source) {
        case "DEF": return "default";
        case "GLB": return "info";
        case "STP": return "success";
        case "OVR": return "warning";
        default: return "default";
    }
}

export function ConfigForm({ groups, onChange }: ConfigFormProps) {
    if (!groups || groups.length === 0) {
        return <div className="p-4 text-xs" style={{ color: "var(--text-muted)" }}>No configuration schema available.</div>;
    }

    return (
        <div className="flex flex-col gap-6">
            {groups.map((group) => (
                <div key={group.id} className="flex flex-col gap-3">
                    <h4 className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                        {group.title}
                    </h4>
                    <div className="flex flex-col gap-4">
                        {group.fields.map((field) => (
                            <div key={field.key} className="flex flex-col gap-1.5">
                                {/* Label row */}
                                <div className="flex items-center justify-between">
                                    <label className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
                                        {field.label}
                                    </label>
                                    <Badge variant={getSourceVariant(field.source)}>
                                        {field.source}
                                    </Badge>
                                </div>
                                {/* Description */}
                                {field.description && (
                                    <div className="text-[10px]" style={{ color: "var(--text-secondary)" }}>
                                        {field.description}
                                    </div>
                                )}
                                {/* Input controls */}
                                <div className="mt-0.5 relative">
                                    {field.type === "string" && (
                                        <Input
                                            label=""
                                            size="sm"
                                            value={field.value}
                                            onChange={(v) => onChange?.(group.id, field.key, v)}
                                            placeholder={`Enter ${field.label}...`}
                                        />
                                    )}
                                    {field.type === "number" && (
                                        <Input
                                            label=""
                                            size="sm"
                                            type="number"
                                            value={String(field.value)}
                                            onChange={(v) => onChange?.(group.id, field.key, Number(v))}
                                        />
                                    )}
                                    {field.type === "boolean" && (
                                        <Toggle
                                            checked={field.value}
                                            onChange={(c) => onChange?.(group.id, field.key, c)}
                                            label={field.value ? "Enabled" : "Disabled"}
                                        />
                                    )}
                                    {field.type === "select" && field.options && (
                                        <div style={{ border: field.error ? "1px solid var(--color-error)" : "none", borderRadius: "8px" }}>
                                            <Select
                                                value={field.value}
                                                options={field.options}
                                                onChange={(v) => onChange?.(group.id, field.key, v)}
                                                placeholder={`Select ${field.label}`}
                                            />
                                        </div>
                                    )}
                                    {field.type === "dict" && (
                                        <div className="p-3 rounded-xl" style={{ background: "var(--bg-node)", border: field.error ? "1px solid var(--color-error)" : "1px dashed rgba(255,255,255,0.1)" }}>
                                            <KeyValueList
                                                entries={Object.entries(field.value || {}).map(([k, v]) => ({ key: k, value: String(v) }))}
                                            />
                                        </div>
                                    )}
                                    {/* Error message */}
                                    {field.error && (
                                        <div className="flex items-center gap-1 mt-1.5 text-[9px] font-medium" style={{ color: "var(--color-error)" }}>
                                            <AlertCircle size={10} />
                                            {field.error}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}

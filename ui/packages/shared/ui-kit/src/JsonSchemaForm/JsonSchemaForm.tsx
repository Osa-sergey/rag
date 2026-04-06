import { useState } from "react";
import { ChevronRight, Info } from "lucide-react";

export type FieldSource = "DEF" | "GLB" | "STP" | "OVR";

export interface SchemaField {
    /** Field key */
    key: string;
    /** Display label */
    label?: string;
    /** Field type */
    type: "string" | "number" | "boolean" | "select" | "group";
    /** Current value */
    value?: any;
    /** Default value from Pydantic schema */
    defaultValue?: any;
    /** Source badge (DEF/GLB/STP/OVR) */
    source?: FieldSource;
    /** Enum options (for select) */
    options?: string[];
    /** Description / help text */
    description?: string;
    /** Nested fields (for group type) */
    children?: SchemaField[];
    /** Is read-only */
    readOnly?: boolean;
}

export interface JsonSchemaFormProps {
    /** Title */
    title?: string;
    /** Fields */
    fields: SchemaField[];
    /** Change handler */
    onChange?: (key: string, value: any) => void;
    /** Show source badges */
    showSources?: boolean;
    /** Compact mode */
    compact?: boolean;
}

const sourceColors: Record<FieldSource, { bg: string; text: string }> = {
    DEF: { bg: "rgba(99,102,241,0.12)", text: "var(--color-info)" },
    GLB: { bg: "rgba(245,158,11,0.12)", text: "var(--color-warning)" },
    STP: { bg: "rgba(34,197,94,0.12)", text: "var(--color-success)" },
    OVR: { bg: "rgba(168,85,247,0.12)", text: "var(--color-concept)" },
};

function FieldRow({
    field,
    onChange,
    showSources,
    depth = 0,
}: {
    field: SchemaField;
    onChange?: (key: string, value: any) => void;
    showSources: boolean;
    depth?: number;
}) {
    const [expanded, setExpanded] = useState(true);

    if (field.type === "group") {
        return (
            <div className="flex flex-col">
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="flex items-center gap-2 py-2 text-left hover:bg-white/3 transition-colors"
                    style={{ paddingLeft: depth * 16 + 4 }}
                >
                    <ChevronRight
                        size={12}
                        className="transition-transform flex-shrink-0"
                        style={{
                            transform: expanded ? "rotate(90deg)" : "rotate(0deg)",
                            color: "var(--text-muted)",
                        }}
                    />
                    <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
                        {field.label ?? field.key}
                    </span>
                    {field.children && (
                        <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>
                            ({field.children.length})
                        </span>
                    )}
                </button>
                {expanded && field.children?.map((child) => (
                    <FieldRow key={child.key} field={child} onChange={onChange} showSources={showSources} depth={depth + 1} />
                ))}
            </div>
        );
    }

    return (
        <div
            className="flex items-center gap-2 py-1.5 group"
            style={{ paddingLeft: depth * 16 + 20 }}
        >
            {/* Label */}
            <div className="flex items-center gap-1 min-w-0" style={{ width: "40%" }}>
                <span className="text-xs font-mono truncate" style={{ color: "var(--text-secondary)" }}>
                    {field.label ?? field.key}
                </span>
                {field.description && (
                    <span className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity cursor-help" title={field.description}>
                        <Info size={10} style={{ color: "var(--text-muted)" }} />
                    </span>
                )}
            </div>

            {/* Input */}
            <div className="flex-1 flex items-center gap-1.5">
                {field.type === "boolean" ? (
                    <button
                        onClick={() => !field.readOnly && onChange?.(field.key, !field.value)}
                        className="relative w-9 h-5 rounded-full transition-colors flex-shrink-0"
                        style={{
                            background: field.value ? "var(--color-info)" : "var(--text-muted)",
                            opacity: field.readOnly ? 0.5 : 1,
                        }}
                    >
                        <div
                            className="absolute top-0.5 w-4 h-4 rounded-full transition-all"
                            style={{
                                left: field.value ? 18 : 2,
                                background: "var(--text-inverse)",
                            }}
                        />
                    </button>
                ) : field.type === "select" ? (
                    <select
                        value={field.value ?? ""}
                        onChange={(e) => onChange?.(field.key, e.target.value)}
                        disabled={field.readOnly}
                        className="px-2 py-1 rounded text-xs flex-1"
                        style={{
                            background: "var(--bg-node)",
                            border: "var(--border-node)",
                            color: "var(--text-primary)",
                            opacity: field.readOnly ? 0.5 : 1,
                        }}
                    >
                        {field.options?.map((opt) => (
                            <option key={opt} value={opt}>{opt}</option>
                        ))}
                    </select>
                ) : (
                    <input
                        type={field.type === "number" ? "number" : "text"}
                        value={field.value ?? ""}
                        onChange={(e) => onChange?.(field.key, field.type === "number" ? Number(e.target.value) : e.target.value)}
                        readOnly={field.readOnly}
                        className="px-2 py-1 rounded text-xs flex-1 min-w-0"
                        style={{
                            background: "var(--bg-node)",
                            border: "var(--border-node)",
                            color: "var(--text-primary)",
                            fontFamily: field.type === "number" ? "'JetBrains Mono', monospace" : "inherit",
                            opacity: field.readOnly ? 0.5 : 1,
                        }}
                        placeholder={field.defaultValue !== undefined ? `default: ${field.defaultValue}` : undefined}
                    />
                )}

                {/* Source badge */}
                {showSources && field.source && (
                    <span
                        className="text-[9px] font-bold px-1.5 py-0.5 rounded flex-shrink-0"
                        style={{ background: sourceColors[field.source].bg, color: sourceColors[field.source].text }}
                        title={
                            field.source === "DEF" ? "Pydantic default" :
                                field.source === "GLB" ? "Global config override" :
                                    field.source === "STP" ? "Step-level config" :
                                        "Runtime override"
                        }
                    >
                        {field.source}
                    </span>
                )}
            </div>
        </div>
    );
}

export function JsonSchemaForm({
    title,
    fields,
    onChange,
    showSources = false,
    compact = false,
}: JsonSchemaFormProps) {
    return (
        <div
            className="rounded-xl overflow-hidden flex flex-col"
            style={{ background: "var(--bg-node)", border: "var(--border-node)" }}
        >
            {/* Header */}
            {(title || showSources) && (
                <div
                    className="flex items-center justify-between px-4 py-2.5 flex-shrink-0"
                    style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
                >
                    {title && <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>{title}</span>}
                    {showSources && (
                        <div className="flex items-center gap-1.5">
                            {(["DEF", "GLB", "STP", "OVR"] as FieldSource[]).map((src) => (
                                <span key={src} className="text-[8px] font-bold px-1 py-0.5 rounded" style={{ background: sourceColors[src].bg, color: sourceColors[src].text }}>
                                    {src}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Fields */}
            <div className="px-2 py-2" style={{ fontSize: compact ? 11 : 12 }}>
                {fields.map((field) => (
                    <FieldRow key={field.key} field={field} onChange={onChange} showSources={showSources} />
                ))}
            </div>
        </div>
    );
}

import React from "react";
import { Badge } from "../Badge";
import { KeyValueList } from "../KeyValueList";
import { Database, Info } from "lucide-react";

export interface ContextField {
    /** Field name */
    name: string;
    /** Field type annotation */
    type: string;
    /** Optional field description */
    description?: string;
}

export interface ContextInspectorProps {
    /** Name of the context class */
    contextName?: string;
    /** Fields defined in the context dataclass */
    fields?: ContextField[];
}

export function ContextInspector({ contextName, fields = [] }: ContextInspectorProps) {
    if (!contextName || fields.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-6 rounded-xl text-center" style={{ background: "var(--bg-node)", border: "1px dashed rgba(255,255,255,0.1)" }}>
                <Info size={16} style={{ color: "var(--text-muted)", marginBottom: 8 }} />
                <span className="text-xs" style={{ color: "var(--text-secondary)" }}>No context requirements defined for this step.</span>
            </div>
        );
    }

    const items = fields.map(f => ({
        key: f.name,
        value: f.type,
    }));

    return (
        <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Database size={14} style={{ color: "var(--color-info)" }} />
                    <h3 className="text-xs font-bold" style={{ color: "var(--text-primary)" }}>Required Context</h3>
                    <Badge variant="info">{contextName}</Badge>
                </div>
            </div>

            <div className="p-3 rounded-xl" style={{ background: "var(--bg-panel)", border: "1px solid var(--border-node)" }}>
                <KeyValueList entries={items} />
            </div>

            {/* Field descriptions */}
            {fields.some(f => f.description) && (
                <div className="flex flex-col gap-2 mt-2">
                    <h4 className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Field Descriptions</h4>
                    <div className="flex flex-col gap-1.5">
                        {fields.map(f => f.description && (
                            <div key={f.name} className="flex gap-2 text-[10px]">
                                <span className="font-mono font-bold" style={{ color: "var(--color-info)", width: 80, flexShrink: 0 }}>{f.name}</span>
                                <span style={{ color: "var(--text-secondary)" }}>{f.description}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

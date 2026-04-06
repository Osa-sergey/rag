import { useState, useRef, useEffect } from "react";
import { Search, Bell, X, Check, ChevronDown, Settings, Plus } from "lucide-react";
import { Popover } from "../Popover";
import { KeyValueList, KeyValueEntry } from "../KeyValueList/KeyValueList";
import { JsonSchemaForm, SchemaField } from "../JsonSchemaForm/JsonSchemaForm";
import { Toggle } from "../Toggle/Toggle";

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════
export interface CallbackParamDef {
    key: string;
    label: string;
    default: string;
    type: "string" | "number" | "boolean";
}

export interface CallbackConfig {
    id: string;
    name: string;
    type?: string;
    enabled: boolean;
    description?: string;
    hasParams?: boolean;
    params?: CallbackParamDef[];
    paramValues?: Record<string, string>;
}

export interface CallbackRegistryEntry {
    id: string;
    name: string;
    type?: string;
    description?: string;
    hasParams?: boolean;
    params?: CallbackParamDef[];
}

export interface CallbackPickerProps {
    callbacks?: CallbackConfig[];
    registry?: CallbackRegistryEntry[];
    onAdd?: (id: string) => void;
    onRemove?: (id: string) => void;
    onToggle?: (id: string, enabled: boolean) => void;
    onSaveParams?: (id: string, values: Record<string, string>) => void;
}

// ═══════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════
function paramsToKeyValueEntries(params: CallbackParamDef[]): KeyValueEntry[] {
    return params.map(p => ({
        key: p.label,
        value: String(p.default),
    }));
}

function paramsToSchemaFields(params: CallbackParamDef[], values: Record<string, string>): SchemaField[] {
    return params.map(p => {
        const isBoolean = p.type === "boolean";
        // for booleans, default must be cast to boolean; for strings/numbers, let undefined trigger placeholder
        const value = isBoolean
            ? (values[p.key] !== undefined ? values[p.key] === "true" : String(p.default) === "true")
            : values[p.key];

        return {
            key: p.key,
            label: p.label,
            type: isBoolean ? "boolean" : p.type === "number" ? "number" : "string",
            value,
            defaultValue: p.default,
        };
    });
}

// ═══════════════════════════════════════════════════════════════
// Component
// ═══════════════════════════════════════════════════════════════
export function CallbackPicker({
    callbacks = [],
    registry = [],
    onAdd,
    onRemove,
    onToggle,
    onSaveParams,
}: CallbackPickerProps) {
    const [search, setSearch] = useState("");
    const [showDropdown, setShowDropdown] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editValues, setEditValues] = useState<Record<string, string>>({});
    const inputRef = useRef<HTMLInputElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // Close dropdown on outside click
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setShowDropdown(false);
            }
        };
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

    const activeIds = new Set(callbacks.map(c => c.id));

    // Filter & group registry
    const filtered = registry.filter(
        r => r.name.toLowerCase().includes(search.toLowerCase()) ||
            (r.description ?? "").toLowerCase().includes(search.toLowerCase()) ||
            (r.type ?? "").toLowerCase().includes(search.toLowerCase())
    );
    const groupedRegistry: Record<string, CallbackRegistryEntry[]> = {};
    filtered.forEach(r => { const g = r.type || "Other"; (groupedRegistry[g] ??= []).push(r); });

    // Group active callbacks by type
    const groupedActive: Record<string, CallbackConfig[]> = {};
    callbacks.forEach(cb => { const g = cb.type || "Other"; (groupedActive[g] ??= []).push(cb); });

    // Open param editor
    const startEditing = (cb: CallbackConfig) => {
        if (!cb.hasParams) return;
        setEditingId(cb.id);
        const regEntry = registry.find(r => r.id === cb.id);
        const paramDefs = regEntry?.params ?? (Array.isArray(cb.params) ? cb.params : []);
        const defaults: Record<string, string> = {};
        paramDefs.forEach(p => { defaults[p.key] = String(p.default); });
        setEditValues({ ...defaults, ...(cb.paramValues ?? {}) });
    };

    const saveParams = () => {
        if (editingId) {
            onSaveParams?.(editingId, { ...editValues });
            setEditingId(null);
            setEditValues({});
        }
    };

    return (
        <div ref={containerRef} className="rounded-xl overflow-visible flex flex-col"
            style={{ background: "var(--bg-panel)", border: "var(--border-node)" }}>

            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2.5"
                style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <div className="flex items-center gap-2">
                    <Bell size={13} style={{ color: "var(--color-warning)" }} />
                    <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>Callbacks</span>
                </div>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded"
                    style={{ background: "var(--bg-node)", color: "var(--text-muted)" }}>
                    {callbacks.filter(c => c.enabled).length}/{callbacks.length}
                </span>
            </div>

            {/* Active callbacks grouped by type */}
            {callbacks.length > 0 && (
                <div className="flex flex-col" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                    {Object.entries(groupedActive).map(([group, cbs]) => (
                        <div key={group}>
                            <div className="text-[8px] font-bold uppercase tracking-widest px-3 pt-2 pb-0.5"
                                style={{ color: "var(--text-muted)" }}>
                                {group}
                            </div>
                            {cbs.map(cb => {
                                const regEntry = registry.find(r => r.id === cb.id);
                                const paramDefs = regEntry?.params ?? (Array.isArray(cb.params) ? cb.params : []);
                                const paramCount = paramDefs.length;
                                const isEditing = editingId === cb.id;

                                // Build current param values for tooltip
                                const currentParamEntries = paramDefs.map(p => ({
                                    key: p.label,
                                    value: String(cb.paramValues?.[p.key] ?? p.default),
                                }));

                                return (
                                    <div key={cb.id} className="flex flex-col">
                                        <div className="flex items-center gap-3 px-3 py-2 group/cb transition-colors hover:bg-[var(--bg-node-hover)]"
                                            style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                                            {/* Toggle enable/disable */}
                                            <div className="flex-shrink-0 pt-0.5">
                                                <Toggle
                                                    size="sm"
                                                    checked={cb.enabled}
                                                    onChange={(checked) => {
                                                        if (!checked) {
                                                            onRemove?.(cb.id); // Remove if disabled as requested
                                                        } else {
                                                            onToggle?.(cb.id, checked);
                                                        }
                                                    }}
                                                />
                                            </div>

                                            {/* Name + click to edit */}
                                            <div className="flex-1 min-w-0 cursor-pointer" onClick={() => startEditing(cb)}>
                                                <div className="text-[11px] font-semibold truncate"
                                                    style={{
                                                        color: cb.enabled ? "var(--text-primary)" : "var(--text-muted)",
                                                        textDecoration: cb.enabled ? "none" : "line-through",
                                                    }}>
                                                    {cb.name}
                                                </div>
                                                {/* Show configured param values inline */}
                                                {cb.paramValues && Object.keys(cb.paramValues).length > 0 && (
                                                    <div className="text-[9px] truncate font-mono mt-0.5" style={{ color: "var(--text-muted)" }}>
                                                        {Object.entries(cb.paramValues).filter(([k, v]) => v).map(([k, v]) => `${k}=${v}`).join(", ")}
                                                    </div>
                                                )}
                                            </div>

                                            {/* Param count with hover preview of current parameters */}
                                            {paramCount > 0 && (
                                                <Popover trigger="hover" placement="left" width="auto" content={
                                                    <div className="p-1 min-w-[180px]">
                                                        <div className="text-[9px] font-bold uppercase tracking-wider px-2 pt-1 pb-1"
                                                            style={{ color: "var(--text-muted)" }}>
                                                            Current Parameters
                                                        </div>
                                                        <KeyValueList entries={currentParamEntries} />
                                                    </div>
                                                }>
                                                    <span className="text-[8px] font-mono px-1.5 py-0.5 rounded cursor-help flex-shrink-0"
                                                        style={{ background: "rgba(99,102,241,0.1)", color: "var(--color-info)" }}>
                                                        ⚙ {paramCount}p
                                                    </span>
                                                </Popover>
                                            )}

                                            {/* Edit params button */}
                                            {cb.hasParams && (
                                                <button
                                                    onClick={() => isEditing ? setEditingId(null) : startEditing(cb)}
                                                    className={`p-1 rounded transition-colors flex-shrink-0 ${isEditing ? 'opacity-100 bg-[var(--bg-node-hover)]' : 'opacity-0 group-hover/cb:opacity-100 hover:bg-[var(--bg-node-hover)]'}`}
                                                    style={{ color: "var(--color-info)" }}
                                                    title={isEditing ? "Close parameters" : "Edit parameters"}
                                                >
                                                    <Settings size={13} />
                                                </button>
                                            )}
                                        </div>

                                        {/* Inline Parameter Editor */}
                                        {isEditing && paramDefs.length > 0 && (
                                            <div className="px-4 pb-3 pt-2" style={{ background: "var(--bg-panel)", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                                                <JsonSchemaForm
                                                    fields={paramsToSchemaFields(paramDefs, editValues)}
                                                    compact
                                                    onChange={(key, value) => {
                                                        setEditValues(prev => ({ ...prev, [key]: String(value) }));
                                                    }}
                                                />
                                                <div className="mt-2 text-right">
                                                    <button onClick={saveParams}
                                                        className="px-3 py-1 rounded text-[10px] font-bold transition-all hover:opacity-90"
                                                        style={{ background: "var(--color-info)", color: "#fff" }}>
                                                        Save
                                                    </button>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    ))}
                </div>
            )}
            {/* Search to add new */}
            <div className="px-2 pt-2 pb-1.5 relative">
                <div
                    className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg cursor-text"
                    style={{
                        background: "var(--bg-node)",
                        border: showDropdown ? "1px solid var(--color-info)" : "1px solid rgba(255,255,255,0.08)",
                        transition: "border-color 0.2s",
                    }}
                    onClick={() => { inputRef.current?.focus(); setShowDropdown(true); }}
                >
                    <Search size={11} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
                    <input
                        ref={inputRef}
                        type="text"
                        value={search}
                        onChange={e => { setSearch(e.target.value); setShowDropdown(true); }}
                        onFocus={() => setShowDropdown(true)}
                        placeholder="Add callback…"
                        className="flex-1 bg-transparent text-[10px] font-medium outline-none"
                        style={{ color: "var(--text-primary)" }}
                    />
                    <ChevronDown size={10} style={{
                        color: "var(--text-muted)", flexShrink: 0,
                        transform: showDropdown ? "rotate(180deg)" : "none",
                        transition: "transform 0.2s",
                    }} />
                </div>

                {/* Dropdown grouped by type */}
                {showDropdown && (
                    <div className="absolute left-2 right-2 mt-1 rounded-lg overflow-hidden shadow-xl z-50"
                        style={{ background: "var(--bg-panel)", border: "1px solid rgba(255,255,255,0.12)", maxHeight: 260, overflowY: "auto" }}>
                        {filtered.length === 0 && (
                            <div className="text-[10px] text-center py-4" style={{ color: "var(--text-muted)" }}>
                                No callbacks found
                            </div>
                        )}
                        {Object.entries(groupedRegistry).map(([group, items]) => (
                            <div key={group}>
                                <div className="text-[8px] font-bold uppercase tracking-widest px-3 pt-2 pb-1"
                                    style={{ color: "var(--color-info)" }}>
                                    {group}
                                </div>
                                {items.map(r => {
                                    const added = activeIds.has(r.id);
                                    const paramCount = (r.params ?? []).length;
                                    return (
                                        <div key={r.id}
                                            className={`flex items-center gap-2.5 px-3 py-1.5 transition-colors ${added ? "cursor-default" : "cursor-pointer hover:bg-white/5"}`}
                                            style={{ borderBottom: "1px solid rgba(255,255,255,0.03)", opacity: added ? 0.35 : 1 }}
                                            onClick={() => {
                                                if (added) return;
                                                onAdd?.(r.id);
                                                setSearch("");
                                                setShowDropdown(false);
                                            }}
                                        >
                                            {added
                                                ? <Check size={11} style={{ color: "var(--color-success)", flexShrink: 0 }} />
                                                : <Plus size={11} style={{ color: "var(--color-info)", flexShrink: 0 }} />
                                            }
                                            <div className="flex-1 min-w-0">
                                                <div className="text-[10px] font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                                                    {r.name}
                                                </div>
                                                {r.description && (
                                                    <div className="text-[9px] truncate" style={{ color: "var(--text-muted)" }}>
                                                        {r.description}
                                                    </div>
                                                )}
                                            </div>
                                            {/* Param count badge with hover showing defaults via KeyValueList */}
                                            {paramCount > 0 && !added && (
                                                <Popover trigger="hover" placement="left" width="auto" content={
                                                    <div className="p-1 min-w-[180px]">
                                                        <div className="text-[9px] font-bold uppercase tracking-wider px-2 pt-1 pb-1"
                                                            style={{ color: "var(--text-muted)" }}>
                                                            Default Parameters
                                                        </div>
                                                        <KeyValueList entries={paramsToKeyValueEntries(r.params!)} />
                                                    </div>
                                                }>
                                                    <span className="text-[8px] font-mono px-1.5 py-0.5 rounded cursor-help flex-shrink-0"
                                                        style={{ background: "rgba(99,102,241,0.1)", color: "var(--color-info)" }}>
                                                        ⚙ {paramCount}p
                                                    </span>
                                                </Popover>
                                            )}
                                            {added && (
                                                <span className="text-[8px] font-bold px-1.5 py-0.5 rounded"
                                                    style={{ background: "rgba(255,255,255,0.05)", color: "var(--text-muted)" }}>Added</span>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Empty state */}
            {
                callbacks.length === 0 && !showDropdown && (
                    <div className="text-[10px] text-center py-3 px-3" style={{ color: "var(--text-muted)" }}>
                        No callbacks. Focus search to browse available callbacks.
                    </div>
                )
            }
        </div >
    );
}

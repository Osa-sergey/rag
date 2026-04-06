import React, { useState, useRef, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, X, ChevronDown, Filter } from "lucide-react";
import { transitions } from "../motion";

/** Filter shortcut definition */
export interface SearchFilter {
    /** Prefix key (e.g. "type:", "status:", "domain:", "score:") */
    prefix: string;
    /** Display label */
    label: string;
    /** Filter type */
    type?: "select" | "range" | "integer";
    /** Possible values — for "select" type, shows dropdown */
    options?: string[];
    /** Color for selected chips */
    color?: string;
    /** Range bounds — for "range" and "integer" type */
    rangeLow?: number;
    /** Range upper bound */
    rangeHigh?: number;
    /** Step — for "range" and "integer" type */
    step?: number;
    /** Format function for display */
    format?: (v: number) => string;
    /** Group name — filters with same group are under the same divider */
    group?: string;
}

/** Active filter value — string for select, or {min,max} or {value} for range/integer */
export type FilterValue = string | { min: number; max: number } | { value: number };

/** Autocomplete suggestion item */
export interface Suggestion {
    /** Unique id */
    id: string;
    /** Display text */
    text: string;
    /** Secondary text (subtitle) */
    subtitle?: string;
    /** Group label — suggestions with same group get a divider */
    group?: string;
    /** Icon (ReactNode) to show before text */
    icon?: React.ReactNode;
    /** Color accent */
    color?: string;
}

export interface SearchBarProps {
    /** Current search value */
    value?: string;
    /** Callback on value change */
    onChange?: (value: string) => void;
    /** Placeholder text */
    placeholder?: string;
    /** Whether search bar should expand on focus */
    expandOnFocus?: boolean;
    /** Width when collapsed (px) */
    collapsedWidth?: number;
    /** Width when expanded (px) */
    expandedWidth?: number;
    /** Available filter shortcuts */
    filters?: SearchFilter[];
    /** Active filter values */
    activeFilters?: Record<string, FilterValue>;
    /** On filter change — value=undefined means remove */
    onFilterChange?: (prefix: string, value: FilterValue | undefined) => void;
    /** Autocomplete suggestions (grouped) */
    suggestions?: Suggestion[];
    /** On suggestion select */
    onSuggestionSelect?: (suggestion: Suggestion) => void;
}

function InlineRange({
    filter,
    currentValue,
    onApply,
}: {
    filter: SearchFilter;
    currentValue?: FilterValue;
    onApply: (prefix: string, val: FilterValue) => void;
}) {
    const low = filter.rangeLow ?? 0;
    const high = filter.rangeHigh ?? 100;
    const step = filter.step ?? 1;
    const fmt = filter.format ?? ((v: number) => String(v));
    const isRange = filter.type === "range";

    const existing = currentValue as any;
    const [minV, setMinV] = useState(existing?.min ?? low);
    const [maxV, setMaxV] = useState(existing?.max ?? high);
    const [singleV, setSingleV] = useState(existing?.value ?? Math.round((low + high) / 2));

    const total = high - low;
    const minPct = ((minV - low) / total) * 100;
    const maxPct = ((maxV - low) / total) * 100;
    const valPct = ((singleV - low) / total) * 100;

    const handleApply = () => {
        if (isRange) onApply(filter.prefix, { min: minV, max: maxV });
        else onApply(filter.prefix, { value: singleV });
    };

    return (
        <div className="px-4 py-2 flex flex-col gap-2" onMouseDown={(e) => e.preventDefault()}>
            <div className="flex items-center justify-between">
                <span className="text-[9px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{filter.label}</span>
                <span className="text-[10px] font-mono font-bold" style={{ color: filter.color ?? "var(--color-info)" }}>
                    {isRange ? `${fmt(minV)} – ${fmt(maxV)}` : fmt(singleV)}
                </span>
            </div>
            <div className="relative h-5">
                <div className="absolute left-0 right-0 rounded-full" style={{ top: "50%", transform: "translateY(-50%)", height: 4, background: "var(--bg-node-hover)" }} />
                <div className="absolute rounded-full" style={{
                    top: "50%", transform: "translateY(-50%)", height: 4,
                    left: isRange ? `${minPct}%` : "0%",
                    width: isRange ? `${maxPct - minPct}%` : `${valPct}%`,
                    background: filter.color ?? "var(--color-info)", opacity: 0.6,
                }} />
                {isRange ? (
                    <>
                        <input type="range" min={low} max={high} step={step} value={minV}
                            onChange={(e) => { const v = Number(e.target.value); if (v < maxV) setMinV(v); }}
                            className="absolute w-full appearance-none bg-transparent cursor-pointer" style={{ top: 0, height: "100%", zIndex: 3 }} />
                        <input type="range" min={low} max={high} step={step} value={maxV}
                            onChange={(e) => { const v = Number(e.target.value); if (v > minV) setMaxV(v); }}
                            className="absolute w-full appearance-none bg-transparent cursor-pointer" style={{ top: 0, height: "100%", zIndex: 4 }} />
                    </>
                ) : (
                    <input type="range" min={low} max={high} step={step} value={singleV}
                        onChange={(e) => setSingleV(Number(e.target.value))}
                        className="absolute w-full appearance-none bg-transparent cursor-pointer" style={{ top: 0, height: "100%", zIndex: 3 }} />
                )}
            </div>
            <div className="flex items-center gap-1.5">
                {isRange ? (
                    <>
                        <input type="number" min={low} max={maxV} step={step} value={minV}
                            onChange={(e) => setMinV(Number(e.target.value))}
                            className="flex-1 px-1.5 py-0.5 rounded text-[9px] font-mono text-center"
                            style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-primary)" }} />
                        <span className="text-[8px]" style={{ color: "var(--text-muted)" }}>—</span>
                        <input type="number" min={minV} max={high} step={step} value={maxV}
                            onChange={(e) => setMaxV(Number(e.target.value))}
                            className="flex-1 px-1.5 py-0.5 rounded text-[9px] font-mono text-center"
                            style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-primary)" }} />
                    </>
                ) : (
                    <input type="number" min={low} max={high} step={step} value={singleV}
                        onChange={(e) => setSingleV(Number(e.target.value))}
                        className="flex-1 px-1.5 py-0.5 rounded text-[9px] font-mono text-center"
                        style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-primary)" }} />
                )}
                <button onClick={handleApply} className="px-2 py-0.5 rounded text-[9px] font-semibold transition-colors hover:opacity-80"
                    style={{ background: `color-mix(in srgb, ${filter.color ?? "var(--color-info)"} 15%, transparent)`, color: filter.color ?? "var(--color-info)" }}>
                    Apply
                </button>
            </div>
        </div>
    );
}

/** Group divider label */
function GroupDivider({ label }: { label: string }) {
    return (
        <div className="flex items-center gap-2 px-3 py-1" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
            <span className="text-[8px] font-bold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>{label}</span>
            <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.04)" }} />
        </div>
    );
}

/** Format a FilterValue for display as chip text */
function formatFilterValue(val: FilterValue, filter: SearchFilter): string {
    if (typeof val === "string") return val;
    const fmt = filter.format ?? ((v: number) => String(v));
    if ("min" in val && "max" in val) return `${fmt(val.min)}–${fmt(val.max)}`;
    if ("value" in val) return fmt(val.value);
    return String(val);
}

export function SearchBar({
    value: controlledValue,
    onChange,
    placeholder = "Search...",
    expandOnFocus = true,
    collapsedWidth = 200,
    expandedWidth = 360,
    filters = [],
    activeFilters = {},
    onFilterChange,
    suggestions = [],
    onSuggestionSelect,
}: SearchBarProps) {
    const [focused, setFocused] = useState(false);
    const [internalValue, setInternalValue] = useState("");
    const [openDropdown, setOpenDropdown] = useState<string | null>(null);
    const [showFilters, setShowFilters] = useState(false);
    const [highlightedIdx, setHighlightedIdx] = useState(-1);
    const inputRef = useRef<HTMLInputElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const value = controlledValue ?? internalValue;
    const setValue = (v: string) => {
        setInternalValue(v);
        onChange?.(v);
    };

    const width = expandOnFocus && focused ? expandedWidth : collapsedWidth;
    const hasFilters = filters.length > 0;
    const activeCount = Object.keys(activeFilters).length;
    const hasSuggestions = suggestions.length > 0 && value.length > 0;

    // Group filters by their group prop
    const groupedFilters = useMemo(() => {
        const groups: { group: string; items: SearchFilter[] }[] = [];
        const seenGroups = new Set<string>();
        for (const f of filters) {
            const g = f.group ?? "";
            if (!seenGroups.has(g)) {
                seenGroups.add(g);
                groups.push({ group: g, items: [] });
            }
            groups.find((gr) => gr.group === g)!.items.push(f);
        }
        return groups;
    }, [filters]);

    // Group suggestions by their group prop
    const groupedSuggestions = useMemo(() => {
        const groups: { group: string; items: Suggestion[] }[] = [];
        const seenGroups = new Set<string>();
        for (const s of suggestions) {
            const g = s.group ?? "";
            if (!seenGroups.has(g)) {
                seenGroups.add(g);
                groups.push({ group: g, items: [] });
            }
            groups.find((gr) => gr.group === g)!.items.push(s);
        }
        return groups;
    }, [suggestions]);

    // Flat suggestion list for keyboard navigation
    const flatSuggestions = useMemo(() => suggestions, [suggestions]);

    const handleClear = () => {
        setValue("");
        setHighlightedIdx(-1);
        inputRef.current?.focus();
    };

    const handleFilterSelect = (prefix: string, val: FilterValue) => {
        onFilterChange?.(prefix, val);
        setOpenDropdown(null);
    };

    const handleFilterRemove = (prefix: string) => {
        onFilterChange?.(prefix, undefined);
    };

    const handleSuggestionClick = (s: Suggestion) => {
        onSuggestionSelect?.(s);
        setHighlightedIdx(-1);
    };

    // Keyboard navigation
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (!hasSuggestions) return;
        if (e.key === "ArrowDown") {
            e.preventDefault();
            setHighlightedIdx((i) => Math.min(i + 1, flatSuggestions.length - 1));
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setHighlightedIdx((i) => Math.max(i - 1, -1));
        } else if (e.key === "Enter" && highlightedIdx >= 0) {
            e.preventDefault();
            handleSuggestionClick(flatSuggestions[highlightedIdx]);
        } else if (e.key === "Escape") {
            setHighlightedIdx(-1);
            inputRef.current?.blur();
        }
    };

    // Close on outside click
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setOpenDropdown(null);
                setShowFilters(false);
                setHighlightedIdx(-1);
            }
        };
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

    // Parse typed prefix shortcuts
    useEffect(() => {
        if (!value || !hasFilters) return;
        for (const f of filters) {
            if (value.toLowerCase().endsWith(f.prefix.toLowerCase()) && (f.options?.length || f.type === "range" || f.type === "integer")) {
                setOpenDropdown(f.prefix);
                setShowFilters(true);
                break;
            }
        }
    }, [value, filters, hasFilters]);

    // Reset highlighted when suggestions change
    useEffect(() => { setHighlightedIdx(-1); }, [suggestions]);

    // Determine what to show: suggestions (when typing) or filter panel
    const showSuggestionsPanel = focused && hasSuggestions;
    const showFilterPanel = focused && showFilters && hasFilters && !hasSuggestions;

    return (
        <div ref={containerRef} className="relative flex flex-col">
            <motion.div
                className="relative flex items-center"
                animate={{ width }}
                transition={transitions.spring}
            >
                <Search
                    size={16}
                    className="absolute left-3 pointer-events-none"
                    style={{ color: focused ? "var(--color-step)" : "var(--text-muted)" }}
                />
                <input
                    ref={inputRef}
                    type="text"
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    onFocus={() => { setFocused(true); if (hasFilters) setShowFilters(true); }}
                    onBlur={() => setFocused(false)}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder}
                    className="w-full pl-9 pr-16 py-2 text-sm rounded-lg outline-none transition-colors"
                    style={{
                        background: "var(--bg-node)",
                        color: "var(--text-primary)",
                        border: focused ? "1px solid var(--color-step)" : "var(--border-node)",
                        boxShadow: focused ? "0 0 0 3px rgba(59, 130, 246, 0.1)" : "none",
                    }}
                />

                {/* Right side: filter button + clear */}
                <div className="absolute right-2 flex items-center gap-0.5">
                    {hasFilters && (
                        <button
                            className="p-1 rounded hover:bg-white/5 transition-colors relative"
                            onClick={() => setShowFilters(!showFilters)}
                            onMouseDown={(e) => e.preventDefault()}
                        >
                            <Filter size={13} style={{ color: activeCount > 0 ? "var(--color-info)" : "var(--text-muted)" }} />
                            {activeCount > 0 && (
                                <span className="absolute -top-0.5 -right-0.5 w-3 h-3 rounded-full text-[7px] font-bold flex items-center justify-center"
                                    style={{ background: "var(--color-info)", color: "white" }}>{activeCount}</span>
                            )}
                        </button>
                    )}
                    <AnimatePresence>
                        {value && (
                            <motion.button className="p-1 rounded hover:bg-slate-200/50 dark:hover:bg-slate-700/50"
                                onClick={handleClear}
                                initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.8 }} transition={transitions.snappy}>
                                <X size={14} style={{ color: "var(--text-muted)" }} />
                            </motion.button>
                        )}
                    </AnimatePresence>
                </div>
            </motion.div>

            {/* Active filter chips */}
            {activeCount > 0 && (
                <div className="flex flex-wrap gap-1 mt-1.5">
                    {Object.entries(activeFilters).map(([prefix, val]) => {
                        const filterDef = filters.find((f) => f.prefix === prefix);
                        const display = filterDef ? formatFilterValue(val, filterDef) : String(val);
                        return (
                            <span key={prefix} className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium"
                                style={{ background: `color-mix(in srgb, ${filterDef?.color ?? "var(--color-info)"} 12%, transparent)`, color: filterDef?.color ?? "var(--color-info)" }}>
                                <span className="font-mono font-semibold">{prefix.replace(":", "")}</span>
                                <span>{display}</span>
                                <button onClick={() => handleFilterRemove(prefix)} className="ml-0.5 hover:opacity-70">×</button>
                            </span>
                        );
                    })}
                </div>
            )}

            {/* ===== AUTOCOMPLETE SUGGESTIONS PANEL ===== */}
            <AnimatePresence>
                {showSuggestionsPanel && (
                    <motion.div
                        className="absolute top-full left-0 mt-1 rounded-xl overflow-hidden z-50"
                        style={{ background: "var(--bg-panel)", border: "var(--border-node)", boxShadow: "0 8px 32px rgba(0,0,0,0.4)", width: expandedWidth, maxHeight: 300, overflowY: "auto" }}
                        initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={transitions.snappy}
                    >
                        {/* Autocomplete hint */}
                        <div className="px-3 py-1 text-[8px] flex items-center justify-between" style={{ color: "var(--text-muted)", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                            <span>{flatSuggestions.length} result{flatSuggestions.length !== 1 ? "s" : ""}</span>
                            <span>↑↓ navigate • Enter select</span>
                        </div>

                        {groupedSuggestions.map((group) => (
                            <div key={group.group}>
                                {group.group && <GroupDivider label={group.group} />}
                                {group.items.map((s) => {
                                    const idx = flatSuggestions.indexOf(s);
                                    const isHighlighted = idx === highlightedIdx;
                                    return (
                                        <button
                                            key={s.id}
                                            className="w-full flex items-center gap-2 px-3 py-1.5 text-left transition-colors"
                                            style={{ background: isHighlighted ? "rgba(99,102,241,0.08)" : "transparent" }}
                                            onMouseDown={(e) => e.preventDefault()}
                                            onClick={() => handleSuggestionClick(s)}
                                            onMouseEnter={() => setHighlightedIdx(idx)}
                                        >
                                            {s.icon && <span style={{ color: s.color ?? "var(--text-muted)", flexShrink: 0 }}>{s.icon}</span>}
                                            <div className="flex flex-col flex-1 min-w-0">
                                                <span className="text-[11px] font-medium truncate" style={{ color: isHighlighted ? "var(--color-info)" : "var(--text-primary)" }}>{s.text}</span>
                                                {s.subtitle && <span className="text-[9px] truncate" style={{ color: "var(--text-muted)" }}>{s.subtitle}</span>}
                                            </div>
                                            {s.group && (
                                                <span className="text-[8px] px-1.5 py-0.5 rounded flex-shrink-0"
                                                    style={{ background: "var(--bg-node-hover)", color: s.color ?? "var(--text-muted)" }}>{s.group}</span>
                                            )}
                                        </button>
                                    );
                                })}
                            </div>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ===== FILTER PANEL (with group dividers) ===== */}
            <AnimatePresence>
                {showFilterPanel && (
                    <motion.div
                        className="absolute top-full left-0 mt-1 rounded-xl overflow-hidden z-50"
                        style={{ background: "var(--bg-panel)", border: "var(--border-node)", boxShadow: "0 8px 32px rgba(0,0,0,0.4)", width: expandedWidth }}
                        initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={transitions.snappy}
                    >
                        {/* Hint */}
                        <div className="px-3 py-1.5 text-[9px]" style={{ color: "var(--text-muted)", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                            Type prefix or click to filter • Supports lists, ranges, and integers
                        </div>

                        {groupedFilters.map((group) => (
                            <div key={group.group}>
                                {group.group && <GroupDivider label={group.group} />}

                                {group.items.map((filter) => {
                                    const isOpen = openDropdown === filter.prefix;
                                    const currentVal = activeFilters[filter.prefix];
                                    const filterType = filter.type ?? "select";
                                    const hasOptions = filter.options && filter.options.length > 0;
                                    const isNumeric = filterType === "range" || filterType === "integer";

                                    return (
                                        <div key={filter.prefix}>
                                            <button
                                                className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/3 transition-colors"
                                                onMouseDown={(e) => e.preventDefault()}
                                                onClick={() => {
                                                    if (hasOptions || isNumeric) setOpenDropdown(isOpen ? null : filter.prefix);
                                                    else { setValue(value + filter.prefix); inputRef.current?.focus(); }
                                                }}
                                            >
                                                <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded"
                                                    style={{ background: `color-mix(in srgb, ${filter.color ?? "var(--color-info)"} 10%, transparent)`, color: filter.color ?? "var(--color-info)" }}>
                                                    {filter.prefix}
                                                </span>
                                                <span className="text-[10px] flex-1" style={{ color: "var(--text-secondary)" }}>{filter.label}</span>
                                                <span className="text-[8px] font-mono px-1 py-0.5 rounded"
                                                    style={{ background: "var(--bg-node-hover)", color: "var(--text-muted)" }}>{filterType}</span>
                                                {currentVal && (
                                                    <span className="text-[9px] font-medium" style={{ color: filter.color ?? "var(--color-info)" }}>
                                                        {formatFilterValue(currentVal, filter)}
                                                    </span>
                                                )}
                                                <ChevronDown size={10} className="transition-transform"
                                                    style={{ transform: isOpen ? "rotate(180deg)" : "none", color: "var(--text-muted)" }} />
                                            </button>

                                            {isOpen && hasOptions && filterType === "select" && (
                                                <div className="pl-6 pb-1" style={{ background: "rgba(0,0,0,0.05)" }}>
                                                    {filter.options!.map((opt) => (
                                                        <button key={opt}
                                                            className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-white/5 transition-colors rounded"
                                                            onMouseDown={(e) => e.preventDefault()}
                                                            onClick={() => handleFilterSelect(filter.prefix, opt)}>
                                                            <span className="w-1.5 h-1.5 rounded-full"
                                                                style={{ background: currentVal === opt ? (filter.color ?? "var(--color-info)") : "var(--text-muted)", opacity: currentVal === opt ? 1 : 0.3 }} />
                                                            <span className="text-[10px]" style={{ color: currentVal === opt ? (filter.color ?? "var(--color-info)") : "var(--text-secondary)" }}>{opt}</span>
                                                        </button>
                                                    ))}
                                                </div>
                                            )}

                                            {isOpen && isNumeric && (
                                                <InlineRange filter={filter} currentValue={currentVal} onApply={handleFilterSelect} />
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

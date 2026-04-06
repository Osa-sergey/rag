import React, { useState, useRef, useEffect, useId } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, X, Check, Search } from "lucide-react";
import { transitions } from "../motion";

export interface SelectOption {
    value: string;
    label: string;
    group?: string;
    icon?: React.ReactNode;
    disabled?: boolean;
}

export interface SelectProps {
    /** Label */
    label?: string;
    /** Options */
    options: SelectOption[];
    /** Controlled value(s) */
    value?: string | string[];
    /** Change handler */
    onChange?: (value: string | string[]) => void;
    /** Placeholder */
    placeholder?: string;
    /** Multiple selection */
    multiple?: boolean;
    /** Searchable */
    searchable?: boolean;
    /** Disabled */
    disabled?: boolean;
    /** Helper text */
    helperText?: string;
    /** Error text */
    errorText?: string;
    /** Full width */
    fullWidth?: boolean;
}

export function Select({
    label,
    options,
    value: controlledValue,
    onChange,
    placeholder = "Select...",
    multiple = false,
    searchable = false,
    disabled = false,
    helperText,
    errorText,
    fullWidth = false,
}: SelectProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [search, setSearch] = useState("");
    const [internalValue, setInternalValue] = useState<string[]>([]);
    const containerRef = useRef<HTMLDivElement>(null);
    const id = useId();

    const selected = controlledValue
        ? Array.isArray(controlledValue) ? controlledValue : [controlledValue]
        : internalValue;

    const hasError = !!errorText;

    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setIsOpen(false);
                setSearch("");
            }
        };
        document.addEventListener("mousedown", handleClick);
        return () => document.removeEventListener("mousedown", handleClick);
    }, []);

    const handleSelect = (val: string) => {
        let next: string[];
        if (multiple) {
            next = selected.includes(val) ? selected.filter((v) => v !== val) : [...selected, val];
        } else {
            next = [val];
            setIsOpen(false);
            setSearch("");
        }
        setInternalValue(next);
        onChange?.(multiple ? next : next[0]);
    };

    const handleRemove = (val: string, e: React.MouseEvent) => {
        e.stopPropagation();
        const next = selected.filter((v) => v !== val);
        setInternalValue(next);
        onChange?.(multiple ? next : next[0] ?? "");
    };

    const filtered = options.filter(
        (o) => o.label.toLowerCase().includes(search.toLowerCase()),
    );

    const groups = Array.from(new Set(filtered.map((o) => o.group).filter(Boolean)));
    const hasGroups = groups.length > 0;

    const selectedLabels = options.filter((o) => selected.includes(o.value));

    return (
        <div
            ref={containerRef}
            className="flex flex-col gap-1.5 relative"
            style={{ width: fullWidth ? "100%" : "auto", minWidth: 200, opacity: disabled ? 0.5 : 1 }}
        >
            {label && (
                <label htmlFor={id} className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                    {label}
                </label>
            )}

            {/* Trigger */}
            <button
                id={id}
                type="button"
                onClick={() => !disabled && setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-all"
                style={{
                    border: `${isOpen || hasError ? 2 : 1}px solid ${hasError ? "var(--color-error)" : isOpen ? "var(--color-info)" : "var(--border-node)"
                        }`,
                    background: "transparent",
                    color: selected.length > 0 ? "var(--text-primary)" : "var(--text-muted)",
                    minHeight: 42,
                }}
                aria-expanded={isOpen}
                aria-haspopup="listbox"
            >
                <div className="flex-1 flex flex-wrap gap-1 min-w-0">
                    {selectedLabels.length > 0 ? (
                        multiple ? (
                            selectedLabels.map((opt) => (
                                <span
                                    key={opt.value}
                                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium"
                                    style={{ background: "var(--bg-node-hover)", color: "var(--text-primary)" }}
                                >
                                    {opt.label}
                                    <X
                                        size={10}
                                        className="cursor-pointer"
                                        style={{ color: "var(--text-muted)" }}
                                        onClick={(e) => handleRemove(opt.value, e)}
                                    />
                                </span>
                            ))
                        ) : (
                            <span className="truncate flex items-center gap-1.5">
                                {selectedLabels[0].icon}
                                {selectedLabels[0].label}
                            </span>
                        )
                    ) : (
                        <span>{placeholder}</span>
                    )}
                </div>
                <ChevronDown
                    size={14}
                    className="flex-shrink-0 transition-transform"
                    style={{
                        transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
                        color: "var(--text-muted)",
                    }}
                />
            </button>

            {/* Dropdown */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: -8, scaleY: 0.95 }}
                        animate={{ opacity: 1, y: 0, scaleY: 1 }}
                        exit={{ opacity: 0, y: -8, scaleY: 0.95 }}
                        transition={transitions.snappy}
                        className="absolute top-full left-0 right-0 mt-1 rounded-lg overflow-hidden z-50"
                        style={{
                            background: "var(--bg-panel)",
                            border: "var(--border-node)",
                            boxShadow: "0 8px 24px rgba(0,0,0,0.3)",
                            maxHeight: 240,
                            transformOrigin: "top",
                        }}
                    >
                        {/* Search */}
                        {searchable && (
                            <div className="flex items-center gap-2 px-3 py-2 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                                <Search size={12} style={{ color: "var(--text-muted)" }} />
                                <input
                                    autoFocus
                                    value={search}
                                    onChange={(e) => setSearch(e.target.value)}
                                    className="bg-transparent outline-none text-xs flex-1"
                                    style={{ color: "var(--text-primary)" }}
                                    placeholder="Search..."
                                />
                            </div>
                        )}

                        {/* Options list */}
                        <div className="overflow-y-auto" style={{ maxHeight: searchable ? 196 : 240 }} role="listbox">
                            {hasGroups ? (
                                groups.map((group) => (
                                    <div key={group}>
                                        <div className="px-3 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                                            {group}
                                        </div>
                                        {filtered.filter((o) => o.group === group).map((opt) => (
                                            <OptionItem key={opt.value} opt={opt} selected={selected} onSelect={handleSelect} multiple={multiple} />
                                        ))}
                                    </div>
                                ))
                            ) : (
                                filtered.map((opt) => (
                                    <OptionItem key={opt.value} opt={opt} selected={selected} onSelect={handleSelect} multiple={multiple} />
                                ))
                            )}

                            {filtered.length === 0 && (
                                <div className="px-3 py-4 text-xs text-center" style={{ color: "var(--text-muted)" }}>
                                    No options found
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Helper / Error */}
            {(errorText || helperText) && (
                <p className="text-xs px-1" style={{ color: hasError ? "var(--color-error)" : "var(--text-muted)" }}>
                    {hasError ? `⚠ ${errorText}` : helperText}
                </p>
            )}
        </div>
    );
}

function OptionItem({
    opt,
    selected,
    onSelect,
    multiple,
}: {
    opt: SelectOption;
    selected: string[];
    onSelect: (val: string) => void;
    multiple: boolean;
}) {
    const isSelected = selected.includes(opt.value);
    return (
        <button
            onClick={() => !opt.disabled && onSelect(opt.value)}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-left transition-colors hover:bg-white/5"
            style={{
                color: opt.disabled ? "var(--text-muted)" : "var(--text-primary)",
                opacity: opt.disabled ? 0.5 : 1,
                cursor: opt.disabled ? "not-allowed" : "pointer",
            }}
            role="option"
            aria-selected={isSelected}
            disabled={opt.disabled}
        >
            {multiple && (
                <div
                    className="w-4 h-4 rounded flex items-center justify-center flex-shrink-0"
                    style={{
                        background: isSelected ? "var(--color-info)" : "transparent",
                        border: isSelected ? "none" : "1.5px solid var(--text-muted)",
                    }}
                >
                    {isSelected && <Check size={10} style={{ color: "var(--text-inverse)" }} strokeWidth={3} />}
                </div>
            )}
            {opt.icon && <span className="flex-shrink-0">{opt.icon}</span>}
            <span className="flex-1 truncate">{opt.label}</span>
            {!multiple && isSelected && (
                <Check size={12} style={{ color: "var(--color-info)" }} strokeWidth={3} />
            )}
        </button>
    );
}

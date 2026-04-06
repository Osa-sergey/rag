import React, { useState, useMemo } from "react";
import { Pipette, X, Search, Plus } from "lucide-react";
import {
    Database, Cloud, Cpu, GitBranch, Layers, Tag,
    FileText, Settings, Zap, Brain, Network, BarChart3,
    BookOpen, Folder, Globe, Lock, Key, Shield, Workflow,
    Code, Terminal, Package, Box, ArrowRight, Check,
    Bell, Clock, Filter, Hash, Link, List, Mail,
    Map, Monitor, Play, RefreshCw, Server, Star,
    Upload, Download, Eye, Heart, Home, Image,
} from "lucide-react";

export interface IconColorPickerProps {
    /** Selected icon name */
    selectedIcon?: string;
    /** Selected icon color (hex) */
    selectedColor?: string;
    /** On change */
    onChange?: (icon: string, color: string) => void;
    /** Color palette */
    palette?: string[];
    /** Saved/recent colors (user can remove these) */
    savedColors?: string[];
    /** On saved colors change (add/remove) */
    onSavedColorsChange?: (colors: string[]) => void;
    /** Label */
    label?: string;
    /** Show search */
    searchable?: boolean;
    /** Allow custom hex */
    allowCustomHex?: boolean;
}

const defaultPalette = [
    "#ef4444", "#f97316", "#f59e0b", "#eab308",
    "#22c55e", "#10b981", "#14b8a6", "#06b6d4",
    "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7",
    "#d946ef", "#ec4899", "#f43f5e", "#64748b",
    "#1e293b", "#fafafa",
];

const iconMap: Record<string, React.ReactNode> = {
    database: <Database size={16} />,
    cloud: <Cloud size={16} />,
    cpu: <Cpu size={16} />,
    "git-branch": <GitBranch size={16} />,
    layers: <Layers size={16} />,
    tag: <Tag size={16} />,
    "file-text": <FileText size={16} />,
    settings: <Settings size={16} />,
    zap: <Zap size={16} />,
    brain: <Brain size={16} />,
    network: <Network size={16} />,
    "bar-chart": <BarChart3 size={16} />,
    "book-open": <BookOpen size={16} />,
    folder: <Folder size={16} />,
    globe: <Globe size={16} />,
    lock: <Lock size={16} />,
    key: <Key size={16} />,
    shield: <Shield size={16} />,
    workflow: <Workflow size={16} />,
    code: <Code size={16} />,
    terminal: <Terminal size={16} />,
    package: <Package size={16} />,
    box: <Box size={16} />,
    "arrow-right": <ArrowRight size={16} />,
    check: <Check size={16} />,
    bell: <Bell size={16} />,
    clock: <Clock size={16} />,
    filter: <Filter size={16} />,
    hash: <Hash size={16} />,
    link: <Link size={16} />,
    list: <List size={16} />,
    mail: <Mail size={16} />,
    map: <Map size={16} />,
    monitor: <Monitor size={16} />,
    play: <Play size={16} />,
    "refresh-cw": <RefreshCw size={16} />,
    server: <Server size={16} />,
    star: <Star size={16} />,
    upload: <Upload size={16} />,
    download: <Download size={16} />,
    eye: <Eye size={16} />,
    heart: <Heart size={16} />,
    home: <Home size={16} />,
    image: <Image size={16} />,
    search: <Search size={16} />,
};

const categories: Record<string, string[]> = {
    "Data & Storage": ["database", "server", "cloud", "folder", "package", "box", "upload", "download"],
    "ML & Processing": ["brain", "cpu", "zap", "network", "bar-chart", "workflow", "code", "terminal"],
    "Pipeline": ["play", "git-branch", "layers", "arrow-right", "refresh-cw", "clock", "check"],
    "Content": ["file-text", "book-open", "tag", "hash", "link", "list", "image", "globe"],
    "Access & Security": ["lock", "key", "shield", "eye", "bell", "mail"],
    "UI": ["search", "filter", "settings", "star", "heart", "home", "map", "monitor"],
};

type ActiveTab = "icons" | "colors";

export function IconColorPicker({
    selectedIcon,
    selectedColor,
    onChange,
    palette = defaultPalette,
    savedColors: controlledSaved,
    onSavedColorsChange,
    label,
    searchable = true,
    allowCustomHex = true,
}: IconColorPickerProps) {
    const [icon, setIcon] = useState(selectedIcon ?? "brain");
    const [color, setColor] = useState(selectedColor ?? "#6366f1");
    const [saved, setSaved] = useState<string[]>(controlledSaved ?? []);
    const [query, setQuery] = useState("");
    const [customHex, setCustomHex] = useState("");
    const [tab, setTab] = useState<ActiveTab>("icons");

    const currentIcon = selectedIcon ?? icon;
    const currentColor = selectedColor ?? color;
    const currentSaved = controlledSaved ?? saved;

    const handleSelectIcon = (name: string) => {
        setIcon(name);
        onChange?.(name, currentColor);
    };

    const handleSelectColor = (c: string) => {
        setColor(c);
        onChange?.(currentIcon, c);
    };

    const handleCustomInput = (hex: string) => {
        setCustomHex(hex);
        if (/^#[0-9a-fA-F]{6}$/.test(hex)) {
            handleSelectColor(hex);
        }
    };

    const handleSaveColor = (c: string) => {
        if (!currentSaved.includes(c)) {
            const next = [c, ...currentSaved];
            setSaved(next);
            onSavedColorsChange?.(next);
        }
    };

    const handleRemoveSaved = (c: string) => {
        const next = currentSaved.filter((s) => s !== c);
        setSaved(next);
        onSavedColorsChange?.(next);
    };

    const filtered = useMemo(() => {
        if (!query.trim()) return categories;
        const q = query.toLowerCase();
        const result: Record<string, string[]> = {};
        for (const [cat, icons] of Object.entries(categories)) {
            const matched = icons.filter((name) => name.includes(q));
            if (matched.length > 0) result[cat] = matched;
        }
        return result;
    }, [query]);

    return (
        <div className="flex flex-col gap-2 rounded-xl overflow-hidden" style={{ background: "var(--bg-panel)", border: "var(--border-node)", maxWidth: 340 }}>
            {/* Label */}
            {label && (
                <div className="px-4 pt-3">
                    <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>{label}</span>
                </div>
            )}

            {/* Live Preview */}
            <div className="flex items-center gap-3 px-4 py-2">
                <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center transition-all"
                    style={{
                        background: `color-mix(in srgb, ${currentColor} 15%, transparent)`,
                        border: `2px solid ${currentColor}`,
                        boxShadow: `0 0 16px ${currentColor}30`,
                        color: currentColor,
                    }}
                >
                    {iconMap[currentIcon] ?? <span className="text-sm">?</span>}
                </div>
                <div className="flex flex-col gap-0.5">
                    <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>{currentIcon}</span>
                    <span className="text-[10px] font-mono" style={{ color: currentColor }}>{currentColor.toUpperCase()}</span>
                </div>
            </div>

            {/* Tabs: Icons | Colors */}
            <div className="flex" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                {(["icons", "colors"] as ActiveTab[]).map((t) => (
                    <button
                        key={t}
                        onClick={() => setTab(t)}
                        className="flex-1 py-2 text-[10px] font-semibold uppercase tracking-wider transition-colors"
                        style={{
                            color: tab === t ? "var(--color-info)" : "var(--text-muted)",
                            borderBottom: tab === t ? "2px solid var(--color-info)" : "2px solid transparent",
                        }}
                    >
                        {t === "icons" ? "🎨 Icons" : "🎯 Colors"}
                    </button>
                ))}
            </div>

            {/* Tab content */}
            <div className="px-3 pb-3">
                {tab === "icons" && (
                    <div className="flex flex-col gap-2">
                        {/* Search */}
                        {searchable && (
                            <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg" style={{ background: "var(--bg-node)", border: "var(--border-node)" }}>
                                <Search size={11} style={{ color: "var(--text-muted)" }} />
                                <input
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    className="bg-transparent outline-none text-xs flex-1"
                                    style={{ color: "var(--text-primary)" }}
                                    placeholder="Search icons..."
                                />
                            </div>
                        )}

                        {/* Grid */}
                        <div className="flex flex-col gap-2 overflow-y-auto" style={{ maxHeight: 220 }}>
                            {Object.entries(filtered).map(([cat, icons]) => (
                                <div key={cat}>
                                    <div className="text-[8px] font-semibold uppercase tracking-wider px-1 mb-1" style={{ color: "var(--text-muted)" }}>{cat}</div>
                                    <div className="grid grid-cols-8 gap-1">
                                        {icons.map((name) => (
                                            <button
                                                key={name}
                                                onClick={() => handleSelectIcon(name)}
                                                className="w-8 h-8 rounded-lg flex items-center justify-center transition-all hover:bg-white/5"
                                                style={{
                                                    color: currentIcon === name ? currentColor : "var(--text-secondary)",
                                                    background: currentIcon === name ? `color-mix(in srgb, ${currentColor} 12%, transparent)` : "transparent",
                                                    boxShadow: currentIcon === name ? `inset 0 0 0 1.5px ${currentColor}` : "none",
                                                }}
                                                title={name}
                                            >
                                                {iconMap[name]}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            ))}
                            {Object.keys(filtered).length === 0 && (
                                <div className="text-xs text-center py-4" style={{ color: "var(--text-muted)" }}>No icons match "{query}"</div>
                            )}
                        </div>
                    </div>
                )}

                {tab === "colors" && (
                    <div className="flex flex-col gap-3">
                        {/* Palette grid */}
                        <div>
                            <div className="text-[8px] font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>Palette</div>
                            <div className="grid grid-cols-9 gap-1">
                                {palette.map((c) => (
                                    <button
                                        key={c}
                                        onClick={() => handleSelectColor(c)}
                                        className="w-6 h-6 rounded-md transition-all hover:scale-110"
                                        style={{
                                            background: c,
                                            boxShadow: currentColor === c ? `0 0 0 2px var(--bg-panel), 0 0 0 3px ${c}` : "none",
                                        }}
                                        title={c}
                                    />
                                ))}
                            </div>
                        </div>

                        {/* Saved colors (removable) */}
                        <div>
                            <div className="flex items-center justify-between mb-1">
                                <span className="text-[8px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                                    Saved ({currentSaved.length})
                                </span>
                                <button
                                    onClick={() => handleSaveColor(currentColor)}
                                    className="flex items-center gap-0.5 text-[8px] px-1.5 py-0.5 rounded hover:bg-white/5 transition-colors"
                                    style={{ color: "var(--color-info)" }}
                                    title="Save current color"
                                >
                                    <Plus size={8} /> Save
                                </button>
                            </div>
                            {currentSaved.length > 0 ? (
                                <div className="flex flex-wrap gap-1">
                                    {currentSaved.map((c) => (
                                        <div key={c} className="relative group">
                                            <button
                                                onClick={() => handleSelectColor(c)}
                                                className="w-6 h-6 rounded-md transition-all hover:scale-110"
                                                style={{
                                                    background: c,
                                                    boxShadow: currentColor === c ? `0 0 0 2px var(--bg-panel), 0 0 0 3px ${c}` : "none",
                                                }}
                                                title={c}
                                            />
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleRemoveSaved(c); }}
                                                className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                                                style={{ background: "var(--color-error)", color: "white" }}
                                                title="Remove from saved"
                                            >
                                                <X size={7} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-[9px] py-2 text-center" style={{ color: "var(--text-muted)" }}>
                                    Click "Save" to add current color
                                </div>
                            )}
                        </div>

                        {/* Custom hex */}
                        {allowCustomHex && (
                            <div className="flex items-center gap-2">
                                <Pipette size={11} style={{ color: "var(--text-muted)" }} />
                                <input
                                    type="text"
                                    value={customHex || currentColor}
                                    onChange={(e) => handleCustomInput(e.target.value)}
                                    className="flex-1 px-2 py-1 rounded text-[10px] font-mono"
                                    style={{ background: "var(--bg-node)", border: "var(--border-node)", color: "var(--text-primary)" }}
                                    placeholder="#000000"
                                    maxLength={7}
                                />
                                <div className="w-5 h-5 rounded" style={{ background: currentColor, border: "1px solid rgba(255,255,255,0.1)" }} />
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

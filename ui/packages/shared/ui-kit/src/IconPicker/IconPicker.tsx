import React, { useState, useMemo } from "react";
import {
    Search, Database, Cloud, Cpu, GitBranch, Layers, Tag,
    FileText, Settings, Zap, Brain, Network, BarChart3,
    BookOpen, Folder, Globe, Lock, Key, Shield, Workflow,
    Code, Terminal, Package, Box, ArrowRight, Check,
    Bell, Clock, Filter, Hash, Link, List, Mail,
    Map, Monitor, Play, RefreshCw, Server, Star,
    Upload, Download, Eye, Heart, Home, Image,
} from "lucide-react";

export interface IconPickerProps {
    /** Current selected icon name */
    value?: string;
    /** Change handler (icon name) */
    onChange?: (iconName: string) => void;
    /** Label */
    label?: string;
    /** Show search */
    searchable?: boolean;
}

export const iconMap: Record<string, React.ReactNode> = {
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

export function IconPicker({
    value,
    onChange,
    label,
    searchable = true,
}: IconPickerProps) {
    const [query, setQuery] = useState("");

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
        <div className="flex flex-col gap-2" style={{ maxWidth: 320 }}>
            {label && (
                <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
                    {label}
                </label>
            )}

            {/* Selected preview */}
            {value && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg" style={{ background: "var(--bg-node-hover)" }}>
                    <span style={{ color: "var(--color-info)" }}>{iconMap[value]}</span>
                    <span className="text-xs font-mono" style={{ color: "var(--text-primary)" }}>{value}</span>
                </div>
            )}

            {/* Search */}
            {searchable && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg" style={{ background: "var(--bg-node)", border: "var(--border-node)" }}>
                    <Search size={12} style={{ color: "var(--text-muted)" }} />
                    <input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="bg-transparent outline-none text-xs flex-1"
                        style={{ color: "var(--text-primary)" }}
                        placeholder="Search icons..."
                    />
                </div>
            )}

            {/* Grid by category */}
            <div className="flex flex-col gap-2 overflow-y-auto" style={{ maxHeight: 280 }}>
                {Object.entries(filtered).map(([cat, icons]) => (
                    <div key={cat}>
                        <div className="text-[9px] font-semibold uppercase tracking-wider px-1 mb-1" style={{ color: "var(--text-muted)" }}>
                            {cat}
                        </div>
                        <div className="grid grid-cols-8 gap-1">
                            {icons.map((name) => (
                                <button
                                    key={name}
                                    onClick={() => onChange?.(name)}
                                    className="w-8 h-8 rounded-lg flex items-center justify-center transition-all hover:bg-white/5"
                                    style={{
                                        color: value === name ? "var(--color-info)" : "var(--text-secondary)",
                                        background: value === name ? "rgba(99,102,241,0.12)" : "transparent",
                                        boxShadow: value === name ? "inset 0 0 0 1.5px var(--color-info)" : "none",
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
                    <div className="text-xs text-center py-4" style={{ color: "var(--text-muted)" }}>
                        No icons match "{query}"
                    </div>
                )}
            </div>
        </div>
    );
}

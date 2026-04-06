import React, { useState } from "react";
import { Search, Filter, ChevronDown, FileText, Brain, Tag, Inbox } from "lucide-react";

export type NavigatorTab = "articles" | "concepts" | "keywords" | "inbox";

export interface NavigatorItem {
    id: string;
    label: string;
    type?: string;
    badge?: string | number;
    badgeColor?: string;
    stale?: boolean;
}

export interface NavigatorSidebarProps {
    /** Active tab */
    activeTab?: NavigatorTab;
    /** Items to display */
    items: NavigatorItem[];
    /** Search query */
    searchQuery?: string;
    /** On search */
    onSearch?: (q: string) => void;
    /** On tab change */
    onTabChange?: (tab: NavigatorTab) => void;
    /** On item click */
    onItemClick?: (item: NavigatorItem) => void;
    /** Inbox count */
    inboxCount?: number;
}

const tabIcons: Record<NavigatorTab, React.ReactNode> = {
    articles: <FileText size={13} />,
    concepts: <Brain size={13} />,
    keywords: <Tag size={13} />,
    inbox: <Inbox size={13} />,
};

export function NavigatorSidebar({
    activeTab = "articles",
    items,
    searchQuery = "",
    onSearch,
    onTabChange,
    onItemClick,
    inboxCount = 0,
}: NavigatorSidebarProps) {
    const [query, setQuery] = useState(searchQuery);

    const filtered = items.filter((item) =>
        item.label.toLowerCase().includes(query.toLowerCase())
    );

    return (
        <div
            className="flex flex-col rounded-xl overflow-hidden h-full"
            style={{ background: "var(--bg-panel)", border: "var(--border-node)", width: 260 }}
        >
            {/* Tabs */}
            <div className="flex" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                {(["articles", "concepts", "keywords", "inbox"] as NavigatorTab[]).map((tab) => (
                    <button
                        key={tab}
                        onClick={() => onTabChange?.(tab)}
                        className="flex-1 flex items-center justify-center gap-1 py-2.5 text-[10px] font-medium transition-colors relative"
                        style={{
                            color: activeTab === tab ? "var(--color-info)" : "var(--text-muted)",
                            background: activeTab === tab ? "rgba(99,102,241,0.06)" : "transparent",
                        }}
                    >
                        {tabIcons[tab]}
                        {tab === "inbox" && inboxCount > 0 && (
                            <span
                                className="absolute top-1 right-1 w-4 h-4 rounded-full text-[8px] font-bold flex items-center justify-center"
                                style={{ background: "var(--color-error)", color: "white" }}
                            >
                                {inboxCount}
                            </span>
                        )}
                    </button>
                ))}
            </div>

            {/* Search */}
            <div className="px-3 py-2">
                <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg" style={{ background: "var(--bg-node)", border: "var(--border-node)" }}>
                    <Search size={11} style={{ color: "var(--text-muted)" }} />
                    <input
                        value={query}
                        onChange={(e) => { setQuery(e.target.value); onSearch?.(e.target.value); }}
                        className="bg-transparent outline-none text-xs flex-1"
                        style={{ color: "var(--text-primary)" }}
                        placeholder={`Search ${activeTab}...`}
                    />
                </div>
            </div>

            {/* Items */}
            <div className="flex-1 overflow-y-auto px-1 pb-2" style={{ maxHeight: 400 }}>
                {filtered.map((item) => (
                    <button
                        key={item.id}
                        onClick={() => onItemClick?.(item)}
                        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left hover:bg-white/3 transition-colors"
                    >
                        <div className="flex-1 min-w-0">
                            <div className="text-xs truncate" style={{ color: item.stale ? "var(--color-warning)" : "var(--text-primary)" }}>
                                {item.stale && "⚠ "}{item.label}
                            </div>
                            {item.type && (
                                <div className="text-[9px]" style={{ color: "var(--text-muted)" }}>{item.type}</div>
                            )}
                        </div>
                        {item.badge !== undefined && (
                            <span
                                className="text-[9px] font-bold px-1.5 py-0.5 rounded flex-shrink-0"
                                style={{
                                    background: item.badgeColor ? `color-mix(in srgb, ${item.badgeColor} 12%, transparent)` : "var(--bg-node-hover)",
                                    color: item.badgeColor ?? "var(--text-muted)",
                                }}
                            >
                                {item.badge}
                            </span>
                        )}
                    </button>
                ))}

                {filtered.length === 0 && (
                    <div className="text-xs text-center py-8" style={{ color: "var(--text-muted)" }}>
                        No {activeTab} found
                    </div>
                )}
            </div>
        </div>
    );
}

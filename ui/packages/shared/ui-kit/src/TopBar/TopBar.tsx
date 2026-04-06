import React from "react";
import { Search, Settings, Bell, Moon, Sun } from "lucide-react";

export interface TopBarProps {
    /** App or page title */
    title?: string;
    /** Breadcrumb slot (render your own <Breadcrumb> here) */
    breadcrumb?: React.ReactNode;
    /** Search slot (render your own <SearchBar> here) */
    search?: React.ReactNode;
    /** Right-side actions */
    actions?: React.ReactNode;
    /** Show the default dark/light toggle */
    showThemeToggle?: boolean;
    /** Custom left element */
    leading?: React.ReactNode;
}

export function TopBar({
    title,
    breadcrumb,
    search,
    actions,
    showThemeToggle = false,
    leading,
}: TopBarProps) {
    return (
        <header
            className="flex items-center gap-3 px-4 h-12 flex-shrink-0"
            style={{
                background: "var(--bg-panel)",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
                backdropFilter: "blur(12px)",
            }}
            role="banner"
        >
            {/* Left */}
            <div className="flex items-center gap-3 min-w-0">
                {leading}
                {title && (
                    <h1 className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                        {title}
                    </h1>
                )}
                {breadcrumb}
            </div>

            {/* Spacer */}
            <div className="flex-1" />

            {/* Center / Search */}
            {search && <div className="max-w-xs w-full">{search}</div>}

            {/* Spacer */}
            {search && <div className="flex-1" />}

            {/* Right actions */}
            <div className="flex items-center gap-1 flex-shrink-0">
                {actions}
                {showThemeToggle && (
                    <button
                        className="p-2 rounded-lg transition-colors hover:bg-white/5"
                        style={{ color: "var(--text-muted)" }}
                        aria-label="Toggle theme"
                    >
                        <Moon size={14} />
                    </button>
                )}
            </div>
        </header>
    );
}

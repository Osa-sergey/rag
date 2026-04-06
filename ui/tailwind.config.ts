import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./packages/**/*.{ts,tsx}",
        "./apps/**/*.{ts,tsx}",
        "./.storybook/**/*.{ts,tsx}",
    ],
    darkMode: ["class", '[data-theme="dark"]'],
    theme: {
        extend: {
            colors: {
                canvas: "var(--bg-canvas)",
                node: "var(--bg-node)",
                "node-hover": "var(--bg-node-hover)",
                group: "var(--bg-group)",
                panel: "var(--bg-panel)",
                article: "var(--color-article)",
                keyword: "var(--color-keyword)",
                concept: "var(--color-concept)",
                step: "var(--color-step)",
                "data-edge": "var(--color-data)",
                dep: "var(--color-dep)",
                success: "var(--color-success)",
                error: "var(--color-error)",
                warning: "var(--color-warning)",
                info: "var(--color-info)",
                stale: "var(--color-stale)",
            },
            fontFamily: {
                sans: ["Inter", "system-ui", "sans-serif"],
                mono: ["JetBrains Mono", "Fira Code", "monospace"],
            },
            fontSize: {
                xs: "11px",
                sm: "13px",
                base: "14px",
                lg: "16px",
                xl: "20px",
            },
            borderRadius: {
                node: "12px",
                badge: "6px",
            },
            boxShadow: {
                node: "0 2px 8px rgba(0, 0, 0, 0.08)",
                "node-hover": "0 4px 16px rgba(0, 0, 0, 0.12)",
            },
        },
    },
    plugins: [],
};

export default config;

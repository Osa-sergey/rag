import { useState } from "react";
import { Copy, Check, AlertTriangle, Code } from "lucide-react";

export interface YamlPanelProps {
    /** YAML content */
    content: string;
    /** Error lines */
    errorLines?: number[];
    /** Read only */
    readOnly?: boolean;
    /** On change */
    onChange?: (content: string) => void;
    /** Container class */
    className?: string;
    /** Container style */
    style?: React.CSSProperties;
    /** Header Title */
    title?: React.ReactNode;
}

export function YamlPanel({
    content,
    errorLines = [],
    className = "",
    style,
    title = "Pipeline YAML",
}: YamlPanelProps) {
    const [copied, setCopied] = useState(false);
    const lines = content.split("\n");
    const errorSet = new Set(errorLines);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div
            className={`rounded-xl overflow-hidden flex flex-col ${className}`}
            style={{ background: "var(--bg-panel)", border: "var(--border-node)", ...style }}
        >
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <div className="flex items-center gap-2">
                    <Code size={13} style={{ color: "var(--text-muted)" }} />
                    <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>{title}</span>
                    {errorLines.length > 0 && (
                        <span className="flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ background: "rgba(239,68,68,0.1)", color: "var(--color-error)" }}>
                            <AlertTriangle size={9} /> {errorLines.length} error{errorLines.length > 1 ? "s" : ""}
                        </span>
                    )}
                </div>
                <button
                    onClick={handleCopy}
                    className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium transition-colors hover:bg-white/5"
                    style={{ color: copied ? "var(--color-success)" : "var(--text-muted)" }}
                >
                    {copied ? <Check size={10} /> : <Copy size={10} />}
                    {copied ? "Copied" : "Copy"}
                </button>
            </div>

            {/* Code area */}
            <div className="flex-1 overflow-auto font-mono text-[10px] leading-5" style={{ background: "var(--bg-canvas)" }}>
                <table className="w-full border-collapse">
                    <tbody>
                        {lines.map((line, i) => {
                            const lineNum = i + 1;
                            const isError = errorSet.has(lineNum);
                            return (
                                <tr key={i} style={{ background: isError ? "rgba(239,68,68,0.06)" : "transparent" }}>
                                    <td
                                        className="px-3 py-0 text-right select-none"
                                        style={{
                                            color: isError ? "var(--color-error)" : "rgba(255,255,255,0.2)",
                                            width: 40,
                                            minWidth: 40,
                                            userSelect: "none",
                                        }}
                                    >
                                        {lineNum}
                                    </td>
                                    <td className="px-2 py-0 whitespace-pre" style={{ color: isError ? "var(--color-error)" : "var(--text-secondary)" }}>
                                        {line}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

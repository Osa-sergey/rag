import React, { useState, useCallback } from "react";

export interface AppShellProps {
    /** Top bar content */
    topBar?: React.ReactNode;
    /** Left sidebar content */
    sidebar?: React.ReactNode;
    /** Main canvas content */
    canvas?: React.ReactNode;
    /** Right inspector panel */
    inspector?: React.ReactNode;
    /** Bottom panel (e.g. YamlPanel) */
    bottomPanel?: React.ReactNode;
    /** Show sidebar */
    showSidebar?: boolean;
    /** Show inspector */
    showInspector?: boolean;
    /** Show bottom panel */
    showBottom?: boolean;
    /** Sidebar width */
    sidebarWidth?: number;
    /** Inspector width */
    inspectorWidth?: number;
    /** Bottom panel height */
    bottomHeight?: number;
}

export function AppShell({
    topBar,
    sidebar,
    canvas,
    inspector,
    bottomPanel,
    showSidebar = true,
    showInspector = true,
    showBottom = true,
    sidebarWidth: initialSidebarWidth = 240,
    inspectorWidth: initialInspectorWidth = 340,
    bottomHeight: initialBottomHeight = 260,
}: AppShellProps) {
    const [sidebarWidth, setSidebarWidth] = useState(initialSidebarWidth);
    const [inspectorWidth, setInspectorWidth] = useState(initialInspectorWidth);
    const [bottomHeight, setBottomHeight] = useState(initialBottomHeight);

    const handleSidebarResize = useCallback((startX: number) => {
        const sw = sidebarWidth;
        const onMove = (e: MouseEvent) => {
            setSidebarWidth(Math.max(200, Math.min(320, sw + e.clientX - startX)));
        };
        const onUp = () => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    }, [sidebarWidth]);

    const handleInspectorResize = useCallback((startX: number) => {
        const iw = inspectorWidth;
        const onMove = (e: MouseEvent) => {
            setInspectorWidth(Math.max(260, Math.min(420, iw - (e.clientX - startX))));
        };
        const onUp = () => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    }, [inspectorWidth]);

    const handleBottomResize = useCallback((startY: number) => {
        const bh = bottomHeight;
        const onMove = (e: MouseEvent) => {
            setBottomHeight(Math.max(40, Math.min(400, bh - (e.clientY - startY))));
        };
        const onUp = () => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };
        document.body.style.cursor = 'row-resize';
        document.body.style.userSelect = 'none';
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    }, [bottomHeight]);

    return (
        <div
            className="flex flex-col h-full w-full overflow-hidden"
            style={{
                background: "var(--bg-canvas)",
                color: "var(--text-primary)",
            }}
        >
            {/* Top Bar Area */}
            {topBar && (
                <div
                    className="flex-shrink-0 z-30 shadow-sm relative flex items-center"
                    style={{
                        height: 48,
                        background: "var(--bg-panel)",
                        borderBottom: "1px solid var(--border-panel)",
                    }}
                >
                    {topBar}
                </div>
            )}

            {/* Main Stage */}
            <div className="flex flex-1 min-h-0 relative z-10 w-full overflow-hidden">

                {/* Left Sidebar */}
                {showSidebar && sidebar && (
                    <aside
                        className="flex-shrink-0 overflow-y-auto h-full z-20 relative"
                        style={{
                            width: sidebarWidth,
                            background: "var(--bg-panel)",
                            borderRight: "1px solid var(--border-panel)",
                            boxShadow: "2px 0 8px rgba(0,0,0,0.02)",
                        }}
                    >
                        {sidebar}
                    </aside>
                )}

                {/* Sidebar resize handle */}
                {showSidebar && sidebar && (
                    <div
                        className="flex-shrink-0 cursor-col-resize hover:bg-blue-500/20 active:bg-blue-500/40 transition-colors z-30"
                        style={{ width: 4 }}
                        onMouseDown={(e) => { e.preventDefault(); handleSidebarResize(e.clientX); }}
                    />
                )}

                {/* Center Axis */}
                <main className="flex-1 flex flex-col min-w-0 h-full relative z-0 overflow-hidden">
                    {/* Interactive Canvas */}
                    <div
                        className="flex-1 relative overflow-hidden"
                        style={{ background: "var(--bg-canvas)" }}
                    >
                        {canvas ?? (
                            <div className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-[var(--text-muted)] select-none">
                                Canvas Area
                            </div>
                        )}
                    </div>

                    {/* Bottom resize handle */}
                    {showBottom && bottomPanel && (
                        <div
                            className="flex-shrink-0 cursor-row-resize hover:bg-blue-500/20 active:bg-blue-500/40 transition-colors z-30"
                            style={{ height: 4 }}
                            onMouseDown={(e) => { e.preventDefault(); handleBottomResize(e.clientY); }}
                        />
                    )}

                    {/* Bottom Console Panel */}
                    {showBottom && bottomPanel && (
                        <div
                            className="flex-shrink-0 overflow-y-auto z-20 relative"
                            style={{
                                height: bottomHeight,
                                background: "var(--bg-panel)",
                                borderTop: "1px solid var(--border-panel)",
                                boxShadow: "0 -2px 8px rgba(0,0,0,0.02)",
                            }}
                        >
                            {bottomPanel}
                        </div>
                    )}
                </main>

                {/* Inspector resize handle */}
                {showInspector && inspector && (
                    <div
                        className="flex-shrink-0 cursor-col-resize hover:bg-blue-500/20 active:bg-blue-500/40 transition-colors z-30"
                        style={{ width: 4 }}
                        onMouseDown={(e) => { e.preventDefault(); handleInspectorResize(e.clientX); }}
                    />
                )}

                {/* Right Inspector Panel */}
                {showInspector && inspector && (
                    <aside
                        className="flex-shrink-0 overflow-y-auto h-full z-20 relative"
                        style={{
                            width: inspectorWidth,
                            background: "var(--bg-panel)",
                            borderLeft: "1px solid var(--border-panel)",
                            boxShadow: "-2px 0 8px rgba(0,0,0,0.02)",
                        }}
                    >
                        {inspector}
                    </aside>
                )}
            </div>
        </div>
    );
}

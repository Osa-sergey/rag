import React from "react";
import { motion } from "framer-motion";
import { FileQuestion, SearchX, AlertOctagon, Sparkles } from "lucide-react";
import { scaleIn, transitions } from "../motion";

export type EmptyStateType = "no-data" | "no-results" | "error" | "first-time";

export interface EmptyStateProps {
    /** Type determines icon and default message */
    type?: EmptyStateType;
    /** Title */
    title?: string;
    /** Description */
    description?: string;
    /** Optional action button */
    action?: { label: string; onClick: () => void };
    /** Custom icon override */
    icon?: React.ReactNode;
}

const defaults: Record<EmptyStateType, { icon: React.ReactNode; title: string; description: string }> = {
    "no-data": {
        icon: <FileQuestion size={40} />,
        title: "No data yet",
        description: "There's nothing to display here. Start by adding some content.",
    },
    "no-results": {
        icon: <SearchX size={40} />,
        title: "No results found",
        description: "Try adjusting your search or filter criteria.",
    },
    error: {
        icon: <AlertOctagon size={40} />,
        title: "Something went wrong",
        description: "An error occurred while loading data. Please try again.",
    },
    "first-time": {
        icon: <Sparkles size={40} />,
        title: "Welcome!",
        description: "Get started by creating your first item.",
    },
};

export function EmptyState({
    type = "no-data",
    title,
    description,
    action,
    icon,
}: EmptyStateProps) {
    const config = defaults[type];

    return (
        <motion.div
            variants={scaleIn}
            initial="initial"
            animate="animate"
            className="flex flex-col items-center justify-center gap-3 py-12 px-6 text-center"
        >
            <div
                className="flex items-center justify-center w-16 h-16 rounded-2xl"
                style={{
                    background: "var(--bg-node-hover)",
                    color: "var(--text-muted)",
                }}
            >
                {icon || config.icon}
            </div>

            <h3
                className="text-base font-semibold"
                style={{ color: "var(--text-primary)" }}
            >
                {title || config.title}
            </h3>

            <p
                className="text-sm max-w-xs"
                style={{ color: "var(--text-muted)" }}
            >
                {description || config.description}
            </p>

            {action && (
                <motion.button
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    transition={transitions.spring}
                    className="mt-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors"
                    style={{
                        background: "var(--color-info)",
                        color: "var(--text-inverse)",
                    }}
                    onClick={action.onClick}
                >
                    {action.label}
                </motion.button>
            )}
        </motion.div>
    );
}

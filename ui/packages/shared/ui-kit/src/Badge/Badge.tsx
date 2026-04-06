import React from "react";

export type BadgeVariant =
    | "success"
    | "error"
    | "warning"
    | "info"
    | "stale"
    | "default";

export type BadgeSize = "sm" | "md" | "lg";

export interface BadgeProps {
    /** Display text */
    children: React.ReactNode;
    /** Color variant */
    variant?: BadgeVariant;
    /** Size */
    size?: BadgeSize;
    /** Optional icon before text */
    icon?: React.ReactNode;
}

const variantClasses: Record<BadgeVariant, string> = {
    success:
        "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-300",
    error: "bg-red-100 text-red-800 dark:bg-red-500/20 dark:text-red-300",
    warning:
        "bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-300",
    info: "bg-indigo-100 text-indigo-800 dark:bg-indigo-500/20 dark:text-indigo-300",
    stale:
        "bg-orange-100 text-orange-800 dark:bg-orange-500/20 dark:text-orange-300",
    default:
        "bg-slate-100 text-slate-700 dark:bg-zinc-700/50 dark:text-zinc-200",
};

const sizeClasses: Record<BadgeSize, string> = {
    sm: "px-1.5 py-0.5 text-[10px] leading-tight",
    md: "px-2 py-0.5 text-xs leading-normal",
    lg: "px-2.5 py-1 text-sm leading-normal",
};

export function Badge({
    children,
    variant = "default",
    size = "md",
    icon,
}: BadgeProps) {
    return (
        <span
            className={`
        inline-flex items-center gap-1 font-medium
        rounded-badge whitespace-nowrap select-none
        ${variantClasses[variant]}
        ${sizeClasses[size]}
      `}
        >
            {icon && <span className="flex-shrink-0">{icon}</span>}
            {children}
        </span>
    );
}

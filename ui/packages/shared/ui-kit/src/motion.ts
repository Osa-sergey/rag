import type { Transition, Variants } from "framer-motion";

/* ═══════════════════════════════════════════
   Shared animation presets (UXUI_DESIGN §2.2)
   Rule: no animation longer than 300ms
   ═══════════════════════════════════════════ */

export const transitions = {
    spring: { type: "spring", stiffness: 300, damping: 24 } as Transition,
    smooth: { type: "tween", duration: 0.2, ease: "easeInOut" } as Transition,
    snappy: { type: "tween", duration: 0.15, ease: "easeOut" } as Transition,
};

export const fadeIn: Variants = {
    initial: { opacity: 0 },
    animate: { opacity: 1, transition: transitions.smooth },
    exit: { opacity: 0, transition: transitions.snappy },
};

export const scaleIn: Variants = {
    initial: { scale: 0.9, opacity: 0 },
    animate: { scale: 1, opacity: 1, transition: transitions.spring },
    exit: { scale: 0.9, opacity: 0, transition: transitions.snappy },
};

export const slideInRight: Variants = {
    initial: { x: 300, opacity: 0 },
    animate: { x: 0, opacity: 1, transition: transitions.spring },
    exit: { x: 300, opacity: 0, transition: transitions.smooth },
};

export const slideInLeft: Variants = {
    initial: { x: -300, opacity: 0 },
    animate: { x: 0, opacity: 1, transition: transitions.spring },
    exit: { x: -300, opacity: 0, transition: transitions.smooth },
};

export const slideInBottom: Variants = {
    initial: { y: 200, opacity: 0 },
    animate: { y: 0, opacity: 1, transition: transitions.spring },
    exit: { y: 200, opacity: 0, transition: transitions.smooth },
};

export const expandHeight: Variants = {
    initial: { height: 0, opacity: 0, overflow: "hidden" },
    animate: { height: "auto", opacity: 1, overflow: "hidden", transition: transitions.spring },
    exit: { height: 0, opacity: 0, overflow: "hidden", transition: transitions.smooth },
};

import type { Meta, StoryObj } from "@storybook/react";
import { Timeline } from "./Timeline";

const meta: Meta<typeof Timeline> = {
    title: "UI Kit/Timeline",
    component: Timeline,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof Timeline>;

const noop = () => { };

export const ThreeItems: Story = {
    name: "3 Items",
    args: {
        items: [
            { id: "3", title: "v3 — LLM enrichment", date: "2024-03-15", active: true, color: "var(--color-success)" },
            { id: "2", title: "v2 — Direct update", date: "2024-02-28", color: "var(--color-info)" },
            { id: "1", title: "v1 — Initial extraction", date: "2024-01-10", color: "var(--text-muted)" },
        ],
    },
};

export const WithDiffLinks: Story = {
    name: "🧩 Version Timeline with Diff Links (J4, J5)",
    args: {
        items: [
            {
                id: "v3", title: "v3 — LLM enriched", date: "Mar 15",
                description: "Added 12 keywords, expanded description via GPT-4",
                active: true, color: "var(--color-success)",
                action: { label: "Compare with v2 →", onClick: noop },
            },
            {
                id: "v2", title: "v2 — Direct update", date: "Feb 28",
                description: "2 new articles merged, 5 keywords updated",
                color: "var(--color-info)",
                action: { label: "Compare with v1 →", onClick: noop },
            },
            {
                id: "v1", title: "v1 — Initial extraction", date: "Jan 10",
                description: "Created from 3 source articles",
                color: "var(--text-muted)",
            },
        ],
    },
};

export const LongTimeline: Story = {
    name: "10-item Pipeline Run",
    args: {
        items: Array.from({ length: 10 }, (_, i) => ({
            id: `step-${i}`,
            title: `Step ${i + 1}: ${["parse", "extract", "embed", "cluster", "build_tree", "index", "validate", "export", "notify", "cleanup"][i]}`,
            date: `00:${String(i * 3).padStart(2, "0")}`,
            color: i < 7 ? "var(--color-success)" : i === 7 ? "var(--color-warning)" : "var(--text-muted)",
            active: i === 7,
            description: i === 7 ? "Running... 45% complete" : undefined,
        })),
    },
};

export const Loading: Story = {
    name: "Loading (Skeleton placeholder)",
    args: {
        items: Array.from({ length: 3 }, (_, i) => ({
            id: `skel-${i}`,
            title: "Loading...",
            color: "var(--text-muted)",
        })),
        animated: false,
    },
};

import type { Meta, StoryObj } from "@storybook/react";
import { Toggle } from "./Toggle";
import { Sun, Moon, Eye, EyeOff, Volume2, VolumeX } from "lucide-react";

const meta: Meta<typeof Toggle> = {
    title: "UI Kit/Toggle",
    component: Toggle,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        size: { control: "select", options: ["sm", "md", "lg"] },
        variant: { control: "select", options: ["default", "labeled"] },
        disabled: { control: "boolean" },
        showIcons: { control: "boolean" },
    },
};

export default meta;
type Story = StoryObj<typeof Toggle>;

/* ─── Default M3 switch ───────────────────────────── */

export const Default: Story = {
    name: "Default (Off)",
    args: {
        label: "Enable callbacks",
        description: "Run on_success / on_failure hooks after step completion",
    },
};

export const Checked: Story = {
    name: "Checked (On)",
    args: {
        label: "Retry on failure",
        description: "Automatically retry failed steps up to max_retries",
        checked: true,
    },
};

export const SmallSize: Story = {
    name: "Small Size",
    args: { label: "Compact toggle", size: "sm" },
};

export const LargeSize: Story = {
    name: "Large Size",
    args: { label: "Large toggle", size: "lg", checked: true },
};

export const Disabled: Story = {
    name: "Disabled",
    args: {
        label: "Auto-index vectors",
        description: "Locked by pipeline configuration",
        disabled: true,
        checked: true,
    },
};

export const WithoutIcons: Story = {
    name: "Without Icons (Minimal)",
    args: { label: "Send notifications", showIcons: false },
};

/* ─── Labeled (wide) variant ──────────────────────── */

export const DayNightMode: Story = {
    name: "🧩 Day / Night Mode",
    args: {
        variant: "labeled",
        offLabel: "DAY",
        onLabel: "NIGHT",
        offIcon: <Sun size={14} strokeWidth={2.5} />,
        onIcon: <Moon size={14} strokeWidth={2.5} />,
        checked: true,
        activeColor: "#18181b",
        inactiveColor: "#e4e4e7",
        size: "md",
    },
};

export const ShowHideLabeled: Story = {
    name: "🧩 Show / Hide (Labeled)",
    args: {
        variant: "labeled",
        offLabel: "HIDE",
        onLabel: "SHOW",
        offIcon: <EyeOff size={12} />,
        onIcon: <Eye size={12} />,
        label: "Keywords layer",
        description: "Toggle keyword nodes visibility on graph",
        size: "sm",
    },
};

export const SoundToggle: Story = {
    name: "🧩 Sound Toggle (Labeled LG)",
    args: {
        variant: "labeled",
        offLabel: "MUTE",
        onLabel: "SOUND",
        offIcon: <VolumeX size={16} />,
        onIcon: <Volume2 size={16} />,
        size: "lg",
        checked: true,
    },
};

/* ─── Composite ───────────────────────────────────── */

export const SettingsGroup: Story = {
    name: "🧩 Pipeline Settings Group",
    render: () => (
        <div
            className="flex flex-col gap-4 p-4 rounded-lg"
            style={{ background: "var(--bg-node)", border: "var(--border-node)", maxWidth: 380 }}
        >
            <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                Pipeline Settings
            </h3>
            <Toggle label="Enable retries" description="Max 3 attempts per step" checked={true} />
            <Toggle label="Run callbacks" description="on_success, on_failure, on_start hooks" checked={true} />
            <Toggle label="Auto-validate" description="Validation runs before execution" />
            <Toggle label="Dry run mode" description="No side effects, just validate config" disabled />
        </div>
    ),
};

export const GraphControls: Story = {
    name: "🧩 Graph Layer Controls",
    render: () => (
        <div
            className="flex flex-col gap-3 p-4 rounded-lg"
            style={{ background: "var(--bg-node)", border: "var(--border-node)", maxWidth: 340 }}
        >
            <h4 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Layers
            </h4>
            <Toggle
                variant="labeled" size="sm"
                offLabel="HIDE" onLabel="SHOW"
                offIcon={<EyeOff size={10} />} onIcon={<Eye size={10} />}
                label="Articles" checked={true}
            />
            <Toggle
                variant="labeled" size="sm"
                offLabel="HIDE" onLabel="SHOW"
                offIcon={<EyeOff size={10} />} onIcon={<Eye size={10} />}
                label="Keywords" checked={true}
            />
            <Toggle
                variant="labeled" size="sm"
                offLabel="HIDE" onLabel="SHOW"
                offIcon={<EyeOff size={10} />} onIcon={<Eye size={10} />}
                label="Concepts"
            />
        </div>
    ),
};

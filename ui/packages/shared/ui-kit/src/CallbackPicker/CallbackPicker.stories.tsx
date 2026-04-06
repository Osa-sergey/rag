import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { CallbackPicker, CallbackConfig, CallbackRegistryEntry } from "./CallbackPicker";

const meta: Meta<typeof CallbackPicker> = {
    title: "DAG Builder/CallbackPicker",
    component: CallbackPicker,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof CallbackPicker>;

const mockRegistry: CallbackRegistryEntry[] = [
    {
        id: "cb_retry", name: "Retry on Failure", type: "Recovery", description: "Automatically retries step execution on exception.", hasParams: true,
        params: [
            { key: "max_retries", label: "Max Retries", default: "3", type: "number" },
            { key: "delay", label: "Delay (s)", default: "5", type: "number" },
            { key: "backoff", label: "Exponential Backoff", default: "true", type: "boolean" },
        ]
    },
    {
        id: "cb_fallback", name: "Run Fallback Node", type: "Recovery", description: "Executes an alternate graph upon failure.", hasParams: true,
        params: [
            { key: "fallback_step", label: "Fallback Step", default: "cleanup", type: "string" },
        ]
    },
    {
        id: "cb_alert", name: "Slack Alert", type: "Notifications", description: "Sends a notification to a Slack channel on state change.", hasParams: true,
        params: [
            { key: "channel", label: "Channel", default: "#pipeline-alerts", type: "string" },
            { key: "mention", label: "Mention @oncall", default: "false", type: "boolean" },
        ]
    },
    {
        id: "cb_email", name: "Email Digest", type: "Notifications", description: "Sends an email digest at the end.", hasParams: true,
        params: [
            { key: "to", label: "Recipients", default: "team@example.com", type: "string" },
        ]
    },
    { id: "cb_log", name: "Verbose Auditing", type: "Observability", description: "Records detailed I/O traces to the audit log.", hasParams: false },
    {
        id: "cb_ddog", name: "Datadog Metrics", type: "Observability", description: "Pushes custom metrics to Datadog.", hasParams: true,
        params: [
            { key: "metric_prefix", label: "Metric Prefix", default: "pipeline.", type: "string" },
            { key: "sample_rate", label: "Sample Rate", default: "1.0", type: "number" },
        ]
    },
    { id: "cb_cleanup", name: "Filesystem Cleanup", type: "System", description: "Removes temporary artifacts created by the step.", hasParams: false },
];

const mockInitial: CallbackConfig[] = [
    {
        id: "cb_retry", name: "Retry on Failure", type: "Recovery", description: "Automatically retries step...", enabled: true, hasParams: true,
        params: mockRegistry[0].params, paramValues: { max_retries: "3", delay: "5", backoff: "true" }
    },
    {
        id: "cb_alert", name: "Slack Alert", type: "Notifications", description: "Sends a notification...", enabled: false, hasParams: true,
        params: mockRegistry[2].params
    },
    { id: "cb_log", name: "Verbose Auditing", type: "Observability", description: "Records detailed I/O...", enabled: true, hasParams: false },
];

const StatefulPicker = ({ initial = [] }: { initial?: CallbackConfig[] }) => {
    const [callbacks, setCallbacks] = useState<CallbackConfig[]>(initial);

    return (
        <div className="w-[380px]">
            <CallbackPicker
                callbacks={callbacks}
                registry={mockRegistry}
                onAdd={(id) => {
                    const reg = mockRegistry.find(r => r.id === id);
                    if (reg) setCallbacks(prev => [...prev, { ...reg, enabled: true }]);
                }}
                onRemove={(id) => setCallbacks(prev => prev.filter(c => c.id !== id))}
                onToggle={(id, enabled) => setCallbacks(prev => prev.map(c => c.id === id ? { ...c, enabled } : c))}
                onSaveParams={(id, values) => setCallbacks(prev => prev.map(c => c.id === id ? { ...c, paramValues: values } : c))}
            />
        </div>
    );
};

export const Default: Story = {
    name: "Default — With Callbacks",
    render: () => <StatefulPicker initial={mockInitial} />,
};

export const WithCallbacks: Story = {
    name: "With Callbacks — Toggle & Edit Params",
    render: () => <StatefulPicker initial={mockInitial} />,
};

export const AddNew: Story = {
    name: "Single Callback — Add More",
    render: () => <StatefulPicker initial={mockInitial.slice(0, 1)} />,
};

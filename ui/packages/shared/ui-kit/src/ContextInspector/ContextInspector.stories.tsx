import React from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { ContextInspector, ContextField } from "./ContextInspector";

const meta: Meta<typeof ContextInspector> = {
    title: "DAG Builder/ContextInspector",
    component: ContextInspector,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof ContextInspector>;

const parseFields: ContextField[] = [
    { name: "session_dir", type: "Path", description: "Directory where downloaded source HTML is temporarily stored." },
    { name: "timeout_sec", type: "int", description: "Parsing timeout per page." },
    { name: "parser_flags", type: "dict[str, bool]" },
];

export const Empty: Story = {
    name: "Empty — No context provided",
    args: {},
    render: () => <div className="w-[300px]"><ContextInspector /></div>
};

export const WithFields: Story = {
    name: "With Fields — ParseContext dataclass",
    args: { contextName: "ParseContext", fields: parseFields },
    render: (args) => <div className="w-[380px]"><ContextInspector {...args} /></div>
};

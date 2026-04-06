import React from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { Input } from "./Input";
import { Search, Mail, AlertCircle, Hash } from "lucide-react";

const meta: Meta<typeof Input> = {
    title: "UI Kit/Input",
    component: Input,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
    argTypes: {
        variant: { control: "select", options: ["outlined", "filled"] },
        size: { control: "select", options: ["sm", "md", "lg"] },
        type: { control: "select", options: ["text", "number", "password", "email", "url"] },
        disabled: { control: "boolean" },
        fullWidth: { control: "boolean" },
    },
};

export default meta;
type Story = StoryObj<typeof Input>;

/* --- Basic --- */

export const Outlined: Story = {
    name: "Outlined (Default M3)",
    args: {
        label: "Step Name",
        placeholder: "e.g. parse_articles",
        helperText: "Unique identifier for this pipeline step",
        variant: "outlined",
    },
};

export const Filled: Story = {
    name: "Filled",
    args: {
        label: "Module Path",
        placeholder: "e.g. raptor_pipeline.parse",
        helperText: "Python module path resolved by Dagster",
        variant: "filled",
    },
};

/* --- With Icons --- */

export const WithLeadingIcon: Story = {
    name: "With Leading Icon (Search)",
    args: {
        label: "Search steps",
        placeholder: "Filter by name...",
        leadingIcon: <Search size={16} />,
        fullWidth: true,
    },
};

export const WithTrailingIcon: Story = {
    name: "With Trailing Icon (Email)",
    args: {
        label: "Notification Email",
        type: "email",
        leadingIcon: <Mail size={16} />,
        trailingIcon: <AlertCircle size={16} />,
        helperText: "Used for pipeline failure alerts",
    },
};

/* --- Validation States --- */

export const WithError: Story = {
    name: "Validation Error",
    args: {
        label: "Temperature",
        value: "2.5",
        type: "number",
        errorText: "Must be between 0.0 and 2.0",
        leadingIcon: <Hash size={16} />,
    },
};

export const WithHelperToError: Story = {
    name: "Helper → Error transition",
    render: () => {
        const [val, setVal] = React.useState("");
        const error = val.length > 0 && val.length < 3 ? "Minimum 3 characters" : undefined;
        return (
            <Input
                label="Pipeline Name"
                value={val}
                onChange={setVal}
                helperText="Name must be at least 3 characters"
                errorText={error}
                fullWidth
            />
        );
    },
};

/* --- Sizes --- */

export const Sizes: Story = {
    name: "Size Comparison",
    render: () => (
        <div className="flex flex-col gap-4">
            <Input label="Small Input" size="sm" placeholder="sm" />
            <Input label="Medium Input" size="md" placeholder="md (default)" />
            <Input label="Large Input" size="lg" placeholder="lg" />
        </div>
    ),
};

/* --- Disabled --- */

export const Disabled: Story = {
    name: "Disabled State",
    args: {
        label: "Chunk Overlap",
        value: "64",
        disabled: true,
        helperText: "Locked by global config",
    },
};

/* --- Complex: DAG Config Form --- */

export const ConfigForm: Story = {
    name: "🧩 DAG Config Form",
    render: () => (
        <div className="flex flex-col gap-3" style={{ maxWidth: 400 }}>
            <Input label="Step Name" value="parse_articles" variant="outlined" fullWidth />
            <Input label="Module" value="raptor_pipeline.parse" variant="outlined" fullWidth leadingIcon={<Hash size={14} />} />
            <div className="flex gap-3">
                <Input label="Chunk Size" value="512" type="number" variant="outlined" />
                <Input label="Overlap" value="64" type="number" variant="outlined" />
            </div>
            <Input
                label="Neo4j URI"
                value="bolt://localhost:7687"
                variant="outlined"
                fullWidth
                helperText="From pipeline globals"
            />
        </div>
    ),
};

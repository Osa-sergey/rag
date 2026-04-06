import type { Meta, StoryObj } from "@storybook/react";
import { IconPicker } from "./IconPicker";

const meta: Meta<typeof IconPicker> = {
    title: "UI Kit/IconPicker",
    component: IconPicker,
    tags: ["autodocs"],
    parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof IconPicker>;

export const Default: Story = {
    name: "🧩 Full Grid with Categories",
    args: {
        label: "Step Icon",
        value: "brain",
    },
};

export const Searchable: Story = {
    name: "Searchable — type 'data'",
    args: {
        label: "Select Icon",
        searchable: true,
    },
};

export const NodeAppearance: Story = {
    name: "🧩 Node Appearance (B11)",
    args: {
        label: "Node Icon",
        value: "database",
    },
};

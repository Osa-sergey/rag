import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { RangeInput } from "./RangeInput";

const meta: Meta<typeof RangeInput> = {
    title: "UI Kit/RangeInput",
    component: RangeInput,
    tags: ["autodocs"],
    parameters: { layout: "centered" },
};

export default meta;
type Story = StoryObj<typeof RangeInput>;

const SingleDemo = () => {
    const [val, setVal] = useState(42);
    return <RangeInput label="Score" singleValue value={val} rangeLow={0} rangeHigh={100} step={1} onValueChange={setVal} />;
};

export const SingleValue: Story = {
    name: "🧩 Single Value — Integer Picker",
    render: () => <SingleDemo />,
};

const RangeDemo = () => {
    const [min, setMin] = useState(20);
    const [max, setMax] = useState(80);
    return <RangeInput label="Range" min={min} max={max} rangeLow={0} rangeHigh={100} step={5} onRangeChange={(a, b) => { setMin(a); setMax(b); }} />;
};

export const DualRange: Story = {
    name: "🧩 Dual Range — Min/Max",
    render: () => <RangeDemo />,
};

const SimilarityDemo = () => {
    const [min, setMin] = useState(0.5);
    const [max, setMax] = useState(0.95);
    return (
        <RangeInput
            label="Similarity"
            min={min}
            max={max}
            rangeLow={0}
            rangeHigh={1}
            step={0.05}
            format={(v) => v.toFixed(2)}
            color="var(--color-success)"
            onRangeChange={(a, b) => { setMin(a); setMax(b); }}
        />
    );
};

export const SimilarityRange: Story = {
    name: "🧩 Similarity Range — 0.50–0.95",
    render: () => <SimilarityDemo />,
};

const CompactDemo = () => {
    const [val, setVal] = useState(7);
    return <RangeInput label="Level" singleValue compact value={val} rangeLow={1} rangeHigh={10} step={1} onValueChange={setVal} color="var(--color-warning)" />;
};

export const Compact: Story = {
    name: "Compact — No Inputs",
    render: () => <CompactDemo />,
};

export const AllVariants: Story = {
    name: "All Variants",
    render: () => (
        <div className="flex flex-col gap-6" style={{ width: 260 }}>
            <SingleDemo />
            <RangeDemo />
            <SimilarityDemo />
            <CompactDemo />
        </div>
    ),
};

import React, { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react";
import { PipelineConfigPanel, PipelineConfig } from "../PipelineConfigPanel/PipelineConfigPanel";
import { CallbackParamForm, CallbackType } from "../CallbackParamForm/CallbackParamForm";

const meta: Meta = {
    title: "Knowledge Base/DAG Configs",
    parameters: { layout: "centered" },
    decorators: [
        (Story) => (
            <div className="p-8 rounded-xl flex gap-8 h-full bg-[var(--bg-canvas)] min-w-[800px] justify-center items-start">
                <Story />
            </div>
        ),
    ],
};

export default meta;
type Story = StoryObj;

export const ConfigPanels: Story = {
    name: "⚙️ Pipeline & Callback Configs",
    render: () => {
        const [pipeCfg, setPipeCfg] = useState<Partial<PipelineConfig>>({
            retries: 3,
            concurrency: 16,
            timeout: 3600,
            executor: "kubernetes",
            catchup: false,
        });

        const [successParams, setSuccessParams] = useState<string>("{\n  \"url\": \"https://hooks.slack.com/services/T000...\",\n  \"method\": \"POST\"\n}");
        const [retryParams, setRetryParams] = useState<string>("{\n  \"max_delay\": 300,\n  \"multiplier\": 1.5,\n  \"jitter\": true\n}");

        return (
            <div className="flex gap-16 w-full max-w-5xl justify-center items-start">

                {/* Pipeline Config panel */}
                <div className="flex flex-col gap-3 flex-1 max-w-md">
                    <span className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-widest pl-1">Global DAG Config</span>
                    <PipelineConfigPanel
                        value={pipeCfg}
                        onChange={setPipeCfg}
                        onSave={() => alert("Saved Pipeline Config: " + JSON.stringify(pipeCfg))}
                    />
                </div>

                {/* Callback forms */}
                <div className="flex flex-col gap-6 flex-1 max-w-[320px]">
                    <div className="flex flex-col gap-3">
                        <span className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-widest pl-1">Success Hook</span>
                        <CallbackParamForm
                            type="on_success"
                            initialParams={successParams}
                            onSave={(p) => setSuccessParams(p)}
                        />
                    </div>
                    <div className="flex flex-col gap-3">
                        <span className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-widest pl-1">Retry Logic</span>
                        <CallbackParamForm
                            type="on_retry"
                            initialParams={retryParams}
                            onSave={(p) => setRetryParams(p)}
                        />
                    </div>
                </div>

            </div>
        );
    },
};

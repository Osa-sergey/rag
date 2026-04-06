import type { Preview } from "@storybook/react";
import { withThemeByDataAttribute } from "@storybook/addon-themes";
import "../packages/shared/ui-kit/src/styles/tokens.css";
import "../packages/shared/ui-kit/src/styles/globals.css";

const preview: Preview = {
    parameters: {
        controls: {
            matchers: {
                color: /(background|color)$/i,
                date: /Date$/i,
            },
        },
        layout: "centered",
        backgrounds: { disable: true },
    },
    decorators: [
        withThemeByDataAttribute({
            themes: {
                Light: "light",
                Dark: "dark",
            },
            defaultTheme: "Light",
            attributeName: "data-theme",
        }),
    ],
};

export default preview;

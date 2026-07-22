import type { Preview } from "@storybook/react-vite";
import { ThemeModeProvider } from "../src/theme/ThemeModeProvider";
import { MemoryRouter } from "react-router-dom";

export const globalTypes = {
  theme: {
    description: "Görsel tema",
    defaultValue: "light",
    toolbar: {
      icon: "mirror",
      items: [
        { value: "light", title: "Açık" },
        { value: "dark", title: "Koyu" },
      ],
    },
  },
};

const preview: Preview = {
  decorators: [
    (Story, context) => (
      <ThemeModeProvider forcedMode={context.globals.theme === "dark" ? "dark" : "light"}>
        <MemoryRouter>
          <Story />
        </MemoryRouter>
      </ThemeModeProvider>
    ),
  ],
  parameters: {
    a11y: { test: "error" },
    backgrounds: { disable: true },
    layout: "fullscreen",
  },
};

export default preview;

import type { Meta, StoryObj } from "@storybook/react-vite";
import { DataSourcesPage } from "./DataSourcesPage";

const meta = {
  title: "Alan Ekranları/Veri Kaynakları",
  component: DataSourcesPage,
  parameters: { layout: "fullscreen" },
  tags: ["autodocs"],
} satisfies Meta<typeof DataSourcesPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Normal: Story = { args: { state: "normal" } };
export const DarkTheme: Story = { args: { state: "normal" }, globals: { theme: "dark" } };
export const Loading: Story = { args: { state: "loading" } };
export const Empty: Story = { args: { state: "empty" } };
export const TechnicalError: Story = { args: { correlationId: "story-correlation", state: "error" } };
export const Unauthorized: Story = { args: { state: "unauthorized" } };
export const LongContent: Story = { args: { state: "long-content" } };

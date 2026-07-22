import type { Meta, StoryObj } from "@storybook/react-vite";
import { DashboardPage } from "./DashboardPage";

const meta = {
  title: "Dashboard/Genel Bakış",
  component: DashboardPage,
  parameters: { layout: "fullscreen" },
  tags: ["autodocs"],
} satisfies Meta<typeof DashboardPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Normal: Story = { args: { state: "normal" } };
export const DarkTheme: Story = { args: { state: "normal" }, globals: { theme: "dark" } };
export const Loading: Story = { args: { state: "loading" } };
export const Empty: Story = { args: { state: "empty" } };
export const TechnicalError: Story = { args: { state: "error" } };
export const Unauthorized: Story = { args: { state: "unauthorized" } };
export const LongContent: Story = { args: { state: "long-content" } };

import type { Meta, StoryObj } from "@storybook/react-vite";
import { ReportsPage } from "./ReportsPage";

const meta = {
  title: "Alan Ekranları/Raporlar",
  component: ReportsPage,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof ReportsPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Normal: Story = {};
export const Loading: Story = { args: { state: "loading" } };
export const Empty: Story = { args: { state: "empty" } };
export const Error: Story = {
  args: { correlationId: "storybook-report-error", state: "error" },
};
export const Unauthorized: Story = { args: { state: "unauthorized" } };
export const LongContent: Story = { args: { state: "long-content" } };

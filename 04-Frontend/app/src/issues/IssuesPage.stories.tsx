import type { Meta, StoryObj } from "@storybook/react-vite";
import { IssuesPage } from "./IssuesPage";

const meta = {
  title: "Alan Ekranları/Sorunlar",
  component: IssuesPage,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof IssuesPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Normal: Story = {};
export const Loading: Story = { args: { state: "loading" } };
export const Empty: Story = { args: { state: "empty" } };
export const Error: Story = { args: { correlationId: "storybook-issue-error", state: "error" } };
export const Unauthorized: Story = { args: { state: "unauthorized" } };
export const LongContent: Story = { args: { state: "long-content" } };

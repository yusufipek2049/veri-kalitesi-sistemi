import type { Meta, StoryObj } from "@storybook/react-vite";
import { IssuesPage } from "./IssuesPage";

const meta = {
  title: "Alan Ekranları/Sorunlar",
  component: IssuesPage,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof IssuesPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Normal: Story = {
  args: {
    onLoadAssignmentOptions: async () => [
      {
        userId: "4ec96cb4-d150-45d2-9565-c1879d135f08",
        displayName: "Veri Sorumlusu A",
      },
      {
        userId: "d6b099c7-0b6d-4ae5-8f58-6978050c434f",
        displayName: "Veri Sorumlusu B",
      },
    ],
    onReassign: async () => undefined,
    onStartInvestigation: async () => undefined,
  },
};
export const Loading: Story = { args: { state: "loading" } };
export const Empty: Story = { args: { state: "empty" } };
export const Error: Story = { args: { correlationId: "storybook-issue-error", state: "error" } };
export const Unauthorized: Story = { args: { state: "unauthorized" } };
export const LongContent: Story = { args: { state: "long-content" } };

import type { Meta, StoryObj } from "@storybook/react-vite";
import { ExecutionsPage } from "./ExecutionsPage";

const meta = {
  title: "Alan Ekranları/Çalıştırmalar",
  component: ExecutionsPage,
  parameters: { layout: "fullscreen" },
  tags: ["autodocs"],
} satisfies Meta<typeof ExecutionsPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Normal: Story = { args: { state: "normal" } };
export const DarkTheme: Story = { args: { state: "normal" }, globals: { theme: "dark" } };
export const Loading: Story = { args: { state: "loading" } };
export const Empty: Story = { args: { state: "empty" } };
export const TechnicalError: Story = { args: { correlationId: "story-correlation", state: "error" } };
export const Unauthorized: Story = { args: { state: "unauthorized" } };
export const LongContent: Story = { args: { state: "long-content" } };

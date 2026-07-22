import type { Meta, StoryObj } from "@storybook/react-vite";
import { Box } from "@mui/material";
import { StatusBadge } from "./StatusBadge";

const meta = {
  title: "Ortak/Status Badge",
  component: StatusBadge,
  decorators: [(Story) => <Box sx={{ p: 4 }}><Story /></Box>],
  args: { label: "Başarılı", tone: "success" },
} satisfies Meta<typeof StatusBadge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Success: Story = {};
export const Critical: Story = { args: { label: "Kritik İhlal", tone: "critical" } };
export const Technical: Story = { args: { label: "Teknik Hata", tone: "technical" } };
export const Warning: Story = { args: { label: "Sınırlı Kapsam", tone: "warning" } };
export const Info: Story = { args: { label: "Bilgi", tone: "info" } };
export const NoData: Story = { args: { label: "Veri Yok", tone: "unknown" } };

import { render, screen } from "@testing-library/react";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { describe, expect, it } from "vitest";
import { appTheme } from "../theme/theme";
import { StatusBadge } from "./StatusBadge";

function renderBadge(label: string, tone: "critical" | "technical") {
  return render(
    <ThemeProvider theme={appTheme}>
      <CssBaseline />
      <StatusBadge label={label} tone={tone} />
    </ThemeProvider>,
  );
}

describe("StatusBadge", () => {
  it("kritik kalite ihlalini yazılı ve erişilebilir olarak gösterir", () => {
    renderBadge("Kritik İhlal", "critical");

    expect(screen.getByLabelText("Durum: Kritik İhlal")).toHaveTextContent("Kritik İhlal");
  });

  it("teknik hatayı kalite ihlalinden ayrı adlandırır", () => {
    renderBadge("Teknik Hata", "technical");

    expect(screen.getByLabelText("Durum: Teknik Hata")).toHaveTextContent("Teknik Hata");
    expect(screen.queryByText("Kritik İhlal")).not.toBeInTheDocument();
  });
});

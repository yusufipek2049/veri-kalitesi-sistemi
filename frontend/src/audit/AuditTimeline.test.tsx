import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ThemeModeProvider } from "../theme/ThemeModeProvider";
import { AuditTimeline } from "./AuditTimeline";
import { syntheticAuditPage } from "./model";

function timelineItems() {
  return [
    { ...syntheticAuditPage.items[0], correlationId: "group-a", occurredAt: "2026-08-11T11:00:00Z" },
    { ...syntheticAuditPage.items[1], correlationId: "group-a", occurredAt: "2026-08-11T09:00:00Z" },
    { ...syntheticAuditPage.items[2], correlationId: "group-b", occurredAt: "2026-08-11T10:00:00Z" },
  ];
}

describe("AuditTimeline", () => {
  it("olayları correlation gruplarında kronolojik sıralar ve deterministik renklendirir", () => {
    const { container } = render(
      <ThemeModeProvider><AuditTimeline items={timelineItems()} onSelect={vi.fn()} /></ThemeModeProvider>,
    );

    const eventIds = [...container.querySelectorAll("[data-event-id]")]
      .map((element) => element.getAttribute("data-event-id"));
    expect(eventIds).toEqual(["audit-2", "audit-1", "audit-3"]);
    const groupColors = [...container.querySelectorAll("[data-group-color]")]
      .map((element) => element.getAttribute("data-group-color"));
    expect(groupColors).toHaveLength(2);
    expect(new Set(groupColors).size).toBe(2);
  });

  it("düğüme tıklanınca olayı seçer ve grup başlığını kopyalanabilir sunar", () => {
    const onSelect = vi.fn();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    render(
      <ThemeModeProvider><AuditTimeline items={timelineItems()} onSelect={onSelect} /></ThemeModeProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /LDAP_AUTHENTICATION/ }));
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ eventId: "audit-1" }));
    fireEvent.click(screen.getByRole("button", { name: "group-a ilişki kodunu kopyala" }));
    expect(writeText).toHaveBeenCalledWith("group-a");
  });
});

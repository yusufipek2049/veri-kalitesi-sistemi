import { describe, expect, it, vi } from "vitest";
import { copyTableToClipboard } from "./exportTable";

function mockClipboard() {
  if (!navigator.clipboard) {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn() },
      writable: true,
      configurable: true,
    });
  }
  return vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);
}

describe("copyTableToClipboard", () => {
  it("null skorları '—' olarak dışa aktarır (AC-04)", async () => {
    const spy = mockClipboard();
    await copyTableToClipboard(
      ["Alan", "Skor"],
      [{ cells: ["Finans", "94,2"] }, { cells: ["Operasyon", "—"] }],
    );
    expect(spy).toHaveBeenCalledWith("Alan\tSkor\nFinans\t94,2\nOperasyon\t—");
    spy.mockRestore();
  });

  it("durum etiketlerini boş hücreye dönüştürmez (AC-04)", async () => {
    const spy = mockClipboard();
    await copyTableToClipboard(
      ["Alan", "Durum"],
      [{ cells: ["Risk", "Hesaplanmadı"] }],
    );
    const text = spy.mock.calls[0][0] as string;
    expect(text).toContain("Hesaplanmadı");
    expect(text).not.toContain("\t\t");
    spy.mockRestore();
  });

  it("TSV biçiminde başlık ve satırları birleştirir", async () => {
    const spy = mockClipboard();
    await copyTableToClipboard(
      ["A", "B"],
      [{ cells: ["1", "2"] }, { cells: ["3", "4"] }],
    );
    expect(spy).toHaveBeenCalledWith("A\tB\n1\t2\n3\t4");
    spy.mockRestore();
  });

  it("boş satır listesinde yalnız başlığı yazar", async () => {
    const spy = mockClipboard();
    await copyTableToClipboard(["A", "B"], []);
    expect(spy).toHaveBeenCalledWith("A\tB");
    spy.mockRestore();
  });
});

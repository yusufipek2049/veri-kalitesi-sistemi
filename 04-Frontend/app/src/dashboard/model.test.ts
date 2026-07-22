import { describe, expect, it } from "vitest";
import { trendObservations } from "./model";

describe("dashboard trend modeli", () => {
  it("provizyonel ve teknik sonuçları resmî trendden dışlar", () => {
    const official = trendObservations.filter((item) => item.official);

    expect(official).toHaveLength(6);
    expect(official.every((item) => item.technicalStatus !== "Teknik Hata")).toBe(true);
    expect(official.some((item) => item.qualification === "ProvisionallyQualified")).toBe(false);
  });

  it("teknik hatayı sıfır skor olarak üretmez", () => {
    const technicalFailure = trendObservations.find((item) => item.technicalStatus === "Teknik Hata");

    expect(technicalFailure?.rawScore).toBeNull();
    expect(technicalFailure?.finalScore).toBeNull();
  });
});

import { describe, expect, it } from "vitest";
import { dataSourcesFromApi } from "./model";

describe("veri kaynakları görünüm modeli", () => {
  it("yalnız veri-minimum alanları istemci modeline taşır", () => {
    const items = dataSourcesFromApi({
      api_version: "v1",
      data_origin: "test",
      correlation_id: "correlation",
      items: [{ data_source_id: "source-a", name: "Kaynak A", source_type: "CSV", status: "ACTIVE", last_test_at: null }],
    });

    expect(items).toEqual([{ id: "source-a", name: "Kaynak A", sourceType: "CSV", status: "ACTIVE", lastTestAt: undefined }]);
  });
});

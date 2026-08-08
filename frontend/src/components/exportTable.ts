/**
 * FR-058 erişilebilir tablo dışa aktarımı.
 * Yalnız kullanıcıya zaten gösterilen veriyi panoya kopyalar;
 * veri-minimum korunur, maskeli alan maskeli dışa aktarılır.
 */

export interface ExportTableRow {
  readonly cells: ReadonlyArray<string>;
}

/**
 * Tablo verisini sekme-ayrımlı metin olarak panoya kopyalar.
 * Bilinmeyen/provizyonel durumlar "—" veya durum etiketi olarak korunur;
 * sayısal sıfıra veya boş hücreye dönüştürülmez (AC-04).
 */
export async function copyTableToClipboard(
  headers: ReadonlyArray<string>,
  rows: ReadonlyArray<ExportTableRow>,
): Promise<void> {
  const lines: string[] = [headers.join("\t")];
  for (const row of rows) {
    lines.push(row.cells.join("\t"));
  }
  await navigator.clipboard.writeText(lines.join("\n"));
}

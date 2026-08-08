"""Rapor disa aktarma servisi — PDF/XLSX/CSV.

CSV: Python csv modulu ile yazilir.
XLSX: openpyxl ile workbook olusturulur.
PDF: reportlab ile PDF olusturulur.

Watermark tum formatlara uygulanir (metin alt bilgi / footer).
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Protocol

from veri_kalitesi.reporting.models import ReportExportPolicy, ReportFormat, ReportType


@dataclass(frozen=True)
class GeneratedFile:
    content: bytes
    filename: str
    mime_type: str
    size_bytes: int


class ReportDataProvider(Protocol):
    """Rapor verisini saglayan protocol.

    36G kapsaminda once basit satir/sutun verisi doner;
    ileride domain sorgulariyla zenginlestirilir.
    """

    def fetch_report_data(
        self,
        report_type: ReportType,
        parameters: dict,
    ) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
        """(headers, rows) doner. headers sutun adlari, rows veri satirlari."""
        ...


def generate_report(
    report_type: ReportType,
    fmt: ReportFormat,
    parameters: dict,
    data_provider: ReportDataProvider,
    policy: ReportExportPolicy | None,
    *,
    watermark_text: str | None = None,
) -> GeneratedFile:
    """Raporu belirtilen formatta uretir."""
    headers, rows = data_provider.fetch_report_data(report_type, parameters)

    if fmt == ReportFormat.CSV:
        return _generate_csv(headers, rows, watermark_text)
    elif fmt == ReportFormat.XLSX:
        return _generate_xlsx(headers, rows, watermark_text)
    elif fmt == ReportFormat.PDF:
        return _generate_pdf(headers, rows, watermark_text)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def _generate_csv(
    headers: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
    watermark_text: str | None,
) -> GeneratedFile:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    if watermark_text:
        writer.writerow([])
        writer.writerow([f"-- {watermark_text} --"])

    content = buffer.getvalue().encode("utf-8-sig")
    return GeneratedFile(
        content=content,
        filename="report.csv",
        mime_type="text/csv; charset=utf-8",
        size_bytes=len(content),
    )


def _generate_xlsx(
    headers: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
    watermark_text: str | None,
) -> GeneratedFile:
    try:
        # Gerekce: openpyxl stub paketi ortamda kurulu degil (types-openpyxl).
        import openpyxl  # type: ignore[import-untyped]
        from openpyxl.styles import Font  # type: ignore[import-untyped]
    except ImportError:
        raise RuntimeError("openpyxl is required for XLSX export")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report"

    # Header row
    ws.append(list(headers))
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Data rows
    for row in rows:
        ws.append(list(row))

    # Watermark
    if watermark_text:
        ws.append([])
        ws.append([f"-- {watermark_text} --"])

    buffer = io.BytesIO()
    wb.save(buffer)
    content = buffer.getvalue()
    return GeneratedFile(
        content=content,
        filename="report.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        size_bytes=len(content),
    )


def _generate_pdf(
    headers: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
    watermark_text: str | None,
) -> GeneratedFile:
    try:
        # Gerekce: reportlab stub paketi ortamda kurulu degil (types-reportlab).
        from reportlab.lib import colors  # type: ignore[import-untyped]
        from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
        from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import-untyped]
        from reportlab.platypus import (  # type: ignore[import-untyped]
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        raise RuntimeError("reportlab is required for PDF export")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements: list[object] = []

    elements.append(Paragraph("Data Quality Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    # Table
    table_data: list[list[str]] = [list(headers)]
    for row in rows:
        table_data.append(list(row))

    if table_data:
        pdf_table = Table(table_data, repeatRows=1)
        pdf_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elements.append(pdf_table)

    # Watermark
    if watermark_text:
        elements.append(Spacer(1, 24))
        elements.append(Paragraph(f"-- {watermark_text} --", styles["Normal"]))

    doc.build(elements)
    content = buffer.getvalue()
    return GeneratedFile(
        content=content,
        filename="report.pdf",
        mime_type="application/pdf",
        size_bytes=len(content),
    )

#!/usr/bin/env python3
"""scripts/compact_segment.py

Katmanlı sıkıştırma bütçesi — tek-segment sıkıştırıcı (S09).

stdin'den okur, stdout'a yazar. Uzunluk-tabanlı kırpma yapar; yapısal
bloklar (kod blokları, tablolar) --preserve-structured ile korunur.

Kullanım:
    python3 scripts/compact_segment.py --ratio 50 [--preserve-structured]

Oranlar (yüzde):
    100 = sıkıştırma yok
     50 = yarıya indir
     30 = %30'unu koru

Yapısal koruma (--preserve-structured):
    - ``` ile çevrili kod blokları olduğu gibi korunur.
    - | ile başlayan tablo satırları olduğu gibi korunur.
    - Korunan bloklar hedef uzunluk hesabına dahil edilmez; önce
      ayrılıp sonra geri yerleştirilir.

Basit perplexity yaklaşımı (gelecek iterasyon):
    Şu anki sürüm uzunluk-tabanlıdır. Gerçek perplexity entegrasyonu
    için model çağrısı gerekir; bu script o bağımlılığı kasten almaz.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field


@dataclass
class Block:
    """Prompt'un yapısal veya serbest metin bloğu."""

    kind: str  # "code", "table", "prose"
    lines: list[str] = field(default_factory=list)

    @property
    def size(self) -> int:
        return sum(len(line) for line in self.lines)


def parse_blocks(text: str) -> list[Block]:
    """Metni kod blokları, tablolar ve serbest metin bloklarına ayırır."""
    blocks: list[Block] = []
    lines = text.splitlines(keepends=True)
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Kod bloğu başlangıcı (``` ile)
        if line.startswith("```"):
            block_lines = [line]
            i += 1
            while i < n and not lines[i].startswith("```"):
                block_lines.append(lines[i])
                i += 1
            if i < n:
                block_lines.append(lines[i])
                i += 1
            blocks.append(Block(kind="code", lines=block_lines))
            continue

        # Tablo satırı (| ile başlayan satırların ardışık grubu)
        if line.startswith("|"):
            block_lines = [line]
            i += 1
            while i < n and lines[i].startswith("|"):
                block_lines.append(lines[i])
                i += 1
            blocks.append(Block(kind="table", lines=block_lines))
            continue

        # Serbest metin satırı
        if line.strip():
            # Bitişik boş-satır-olmayan satırları aynı blokta topla
            block_lines = [line]
            i += 1
            while i < n and lines[i].strip() and not lines[i].startswith("```") and not lines[i].startswith("|"):
                block_lines.append(lines[i])
                i += 1
            blocks.append(Block(kind="prose", lines=block_lines))
            continue

        # Boş satır: tek başına bir blok
        blocks.append(Block(kind="prose", lines=[line]))
        i += 1

    return blocks


def compact_prose_lines(lines: list[str], keep_ratio: float) -> list[str]:
    """Serbest metin satırlarını head-biased kırpma ile indirir.

    Head-biased: başlangıç satırları daha önemlidir (özet genelde baştadır).
    İlk satır her zaman korunur; kalan kota son satırlardan ortalanır.
    """
    if keep_ratio >= 1.0:
        return lines
    if not lines:
        return lines

    total = len(lines)
    keep_count = max(1, int(total * keep_ratio))

    if keep_count >= total:
        return lines

    # İlk satır her zaman korunur; kota kalanına dağıtılır.
    head_keep = max(1, keep_count // 2)
    tail_keep = keep_count - head_keep

    result = lines[:head_keep]
    if tail_keep > 0:
        result.extend(lines[-tail_keep:])

    # Kırpma belirtgesi (bilgi kaybı şeffaftır)
    skipped = total - keep_count
    result.insert(head_keep, f"\n[... {skipped} satır sıkıştırıldı ...]\n")

    return result


def compact_segment(text: str, keep_ratio: float, preserve_structured: bool) -> str:
    """Tek segmenti sıkıştırır."""
    if keep_ratio >= 1.0:
        return text

    if not preserve_structured:
        # Basit mod: tüm satırlara head-biased kırpma uygula
        lines = text.splitlines(keepends=True)
        compacted = compact_prose_lines(lines, keep_ratio)
        return "".join(compacted)

    # Yapısal koruma modu: kod ve tablo blokları korunur, yalnız prose kırpılır.
    blocks = parse_blocks(text)
    structured_size = sum(b.size for b in blocks if b.kind != "prose")
    total_size = sum(b.size for b in blocks) or 1

    # Yapısal bloklar zaten yer kaplıyor; prose için efektif oranı ayarla.
    prose_size = total_size - structured_size
    if prose_size <= 0:
        # Tüm içerik yapısal: sıkıştırma yok
        return text

    # Hedef: toplam boyutun keep_ratio'su. Yapısal bloklar sabit, prose değişken.
    target_total = int(total_size * keep_ratio)
    target_prose = max(0, target_total - structured_size)
    effective_ratio = target_prose / prose_size if prose_size > 0 else 1.0

    result_parts: list[str] = []
    for block in blocks:
        if block.kind in ("code", "table"):
            result_parts.append("".join(block.lines))
        else:
            compacted = compact_prose_lines(block.lines, effective_ratio)
            result_parts.append("".join(compacted))

    return "".join(result_parts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tek-segment sıkıştırıcı (uzunluk-tabanlı)"
    )
    parser.add_argument(
        "--ratio",
        type=int,
        default=100,
        help="Koruma oranı (yüzde): 100=sıkıştırma yok, 50=yarıya indir",
    )
    parser.add_argument(
        "--preserve-structured",
        action="store_true",
        help="Kod blokları ve tabloları olduğu gibi koru",
    )
    args = parser.parse_args()

    keep_ratio = max(0, min(100, args.ratio)) / 100.0
    text = sys.stdin.read()

    result = compact_segment(text, keep_ratio, args.preserve_structured)
    sys.stdout.write(result)


if __name__ == "__main__":
    main()

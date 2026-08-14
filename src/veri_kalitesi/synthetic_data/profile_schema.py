"""Versiyonlu profil artefaktı şeması ve gizlilik kapısı.

Faz 4: Gerçek veriden yalnız agregat istatistik taşıyan versiyonlu bir profil
JSON şeması + gizlilik kapısı. PyYAML bağımlılığı olmadığından JSON tabanlı.

Gizlilik kuralları:
  - Kova bastırma: n < k (k varsayılan 20) olan kova yazılmaz.
  - min/max ASLA yazılmaz: p1/p99 kullanılır.
  - Oranlar 4 ondalık basamağa yuvarlanır; ham sayı yazılmaz (row_count hariç).
  - Serbest metin yok: yalnız uzunluk ve desen sınıfı çıkar.
  - Satır listesi yok: profil hiçbir şekilde satır verisi taşıyamaz.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from veri_kalitesi.synthetic_data.errors import SyntheticDataValidationError

PROFILE_SCHEMA_VERSION = "SYNTHETIC_PROFILE_V1"

# Gizlilik kapısı sabitleri
DEFAULT_SUPPRESSION_THRESHOLD = 20
RATIO_DECIMAL_PLACES = 4

# Profil şemasında yasaklı alan adları — örnek değer, satır listesi, serbest metin
# veya min/max taşıyabilecek her alan.
_FORBIDDEN_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "sample",
        "sample_value",
        "sample_values",
        "examples",
        "example_values",
        "raw_value",
        "raw_values",
        "row",
        "rows",
        "row_list",
        "row_data",
        "data",
        "values",
        "free_text",
        "text",
        "content",
        "minimum",
        "maximum",
        "minimum_measure",
        "maximum_measure",
        "min",
        "max",
    }
)

# Profil şemasında izin verilen üst düzey anahtarlar.
_ALLOWED_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "profile_schema_version",
        "tables",
        "system_wide",
    }
)

# Tablo profili için izin verilen anahtarlar.
_ALLOWED_TABLE_KEYS: frozenset[str] = frozenset(
    {
        "table_name",
        "row_count",
        "columns",
    }
)

# Kolon profili için izin verilen anahtarlar.
_ALLOWED_COLUMN_KEYS: frozenset[str] = frozenset(
    {
        "column_name",
        "column_type",
        "null_ratio",
        "distinct_ratio",
        "length_histogram",
        "deciles",
        "share_distribution",
    }
)

# Deciles için izin verilen anahtarlar.
_ALLOWED_DECILE_KEYS: frozenset[str] = frozenset(
    {
        "p10",
        "p25",
        "p50",
        "p75",
        "p90",
        "p99",
    }
)

# Sistem geneli için izin verilen anahtarlar.
_ALLOWED_SYSTEM_KEYS: frozenset[str] = frozenset(
    {
        "volume_curve",
        "latency_distribution",
        "defect_clustering_coefficient",
    }
)

# Geçerli kolon tipleri.
_VALID_COLUMN_TYPES: frozenset[str] = frozenset(
    {
        "numeric",
        "categorical",
        "text",
        "date",
        "boolean",
    }
)


@dataclass(frozen=True)
class LengthBucket:
    """Uzunluk histogramı kovası.

    length: karakter uzunluğu.
    share: bu uzunluğa sahip değerlerin oranı (0–1, 4 ondalık).
    count: bu kovadaki gözlem sayısı (bastırma kontrolü için).
    """

    length: int
    share: float
    count: int


@dataclass(frozen=True)
class DecileValues:
    """Sayısal kolon için desil değerleri.

    p10, p25, p50, p75, p90, p99 — minimum ve maksimum ASLA yazılmaz.
    """

    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    p99: float


@dataclass(frozen=True)
class ShareBucket:
    """Kategorik kolon için pay dağılımı kovası.

    value_class: değer sınıfı (desen veya kategori adı, örnek değer değil).
    share: bu sınıfın oranı (0–1, 4 ondalık).
    count: bu kovadaki gözlem sayısı (bastırma kontrolü için).
    """

    value_class: str
    share: float
    count: int


@dataclass(frozen=True)
class ColumnProfile:
    """Tek kolonun agregat profil istatistikleri."""

    column_name: str
    column_type: str  # "numeric", "categorical", "text", "date", "boolean"
    null_ratio: float
    distinct_ratio: float
    length_histogram: tuple[LengthBucket, ...] = ()
    deciles: DecileValues | None = None
    share_distribution: tuple[ShareBucket, ...] = ()


@dataclass(frozen=True)
class TableProfile:
    """Tek tablonun profil artefaktı."""

    table_name: str
    row_count: int
    columns: tuple[ColumnProfile, ...]


@dataclass(frozen=True)
class VolumePoint:
    """Hacim eğrisi veri noktası."""

    period: str  # "daily" veya "hourly"
    key: str  # gün adı veya saat aralığı
    share: float  # 0–1, 4 ondalık


@dataclass(frozen=True)
class LatencyDistribution:
    """Gecikme dağılımı — p50, p90, p99."""

    p50: float
    p90: float
    p99: float


@dataclass(frozen=True)
class SystemWideProfile:
    """Sistem geneli agregat istatistikler."""

    volume_curve: tuple[VolumePoint, ...] = ()
    latency_distribution: LatencyDistribution | None = None
    defect_clustering_coefficient: float = 0.0


@dataclass(frozen=True)
class SyntheticProfileArtifact:
    """Versiyonlu profil artefaktı — tam dosya yapısı."""

    profile_schema_version: str
    tables: tuple[TableProfile, ...]
    system_wide: SystemWideProfile = field(default_factory=SystemWideProfile)


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------


def _round_ratio(value: float) -> float:
    """Oranı 4 ondalık basamağa yuvarlar."""
    return float(Decimal(str(value)).quantize(Decimal("0.0001")))


def _bucket_is_suppressed(count: int, k: int) -> bool:
    """Kova bastırma kontrolü: n < k ise bastırılır."""
    return count < k


def _deserialize_length_bucket(raw: Mapping[str, Any]) -> LengthBucket:
    return LengthBucket(
        length=int(raw["length"]),
        share=_round_ratio(float(raw["share"])),
        count=int(raw["count"]),
    )


def _deserialize_deciles(raw: Mapping[str, Any]) -> DecileValues:
    return DecileValues(
        p10=float(raw["p10"]),
        p25=float(raw["p25"]),
        p50=float(raw["p50"]),
        p75=float(raw["p75"]),
        p90=float(raw["p90"]),
        p99=float(raw["p99"]),
    )


def _deserialize_share_bucket(raw: Mapping[str, Any]) -> ShareBucket:
    return ShareBucket(
        value_class=str(raw["value_class"]),
        share=_round_ratio(float(raw["share"])),
        count=int(raw["count"]),
    )


def _deserialize_column(raw: Mapping[str, Any]) -> ColumnProfile:
    length_histogram = tuple(_deserialize_length_bucket(b) for b in raw.get("length_histogram", []))
    deciles_raw = raw.get("deciles")
    deciles = _deserialize_deciles(deciles_raw) if deciles_raw else None
    share_distribution = tuple(
        _deserialize_share_bucket(b) for b in raw.get("share_distribution", [])
    )
    return ColumnProfile(
        column_name=str(raw["column_name"]),
        column_type=str(raw["column_type"]),
        null_ratio=_round_ratio(float(raw["null_ratio"])),
        distinct_ratio=_round_ratio(float(raw["distinct_ratio"])),
        length_histogram=length_histogram,
        deciles=deciles,
        share_distribution=share_distribution,
    )


def _deserialize_table(raw: Mapping[str, Any]) -> TableProfile:
    return TableProfile(
        table_name=str(raw["table_name"]),
        row_count=int(raw["row_count"]),
        columns=tuple(_deserialize_column(c) for c in raw.get("columns", [])),
    )


def _deserialize_volume_point(raw: Mapping[str, Any]) -> VolumePoint:
    return VolumePoint(
        period=str(raw["period"]),
        key=str(raw["key"]),
        share=_round_ratio(float(raw["share"])),
    )


def _deserialize_latency(raw: Mapping[str, Any]) -> LatencyDistribution:
    return LatencyDistribution(
        p50=float(raw["p50"]),
        p90=float(raw["p90"]),
        p99=float(raw["p99"]),
    )


def _deserialize_system_wide(raw: Mapping[str, Any]) -> SystemWideProfile:
    volume_curve = tuple(_deserialize_volume_point(v) for v in raw.get("volume_curve", []))
    latency_raw = raw.get("latency_distribution")
    latency = _deserialize_latency(latency_raw) if latency_raw else None
    return SystemWideProfile(
        volume_curve=volume_curve,
        latency_distribution=latency,
        defect_clustering_coefficient=float(raw.get("defect_clustering_coefficient", 0.0)),
    )


# ---------------------------------------------------------------------------
# Profil yükleme
# ---------------------------------------------------------------------------


def load_profile(path: str | Path) -> SyntheticProfileArtifact:
    """JSON profil dosyasını yükler ve gizlilik kapısından geçirir.

    Kapı ihlali durumunda SyntheticDataValidationError fırlatır —
    üretim uyarıyla devam etmez, tamamen durur.
    """
    resolved = Path(path)
    if not resolved.exists():
        raise SyntheticDataValidationError(f"Profil dosyası bulunamadı: {resolved}")
    try:
        raw_text = resolved.read_text(encoding="utf-8")
        payload: dict[str, Any] = json.loads(raw_text)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SyntheticDataValidationError(f"Profil dosyası okunamadı: {exc}") from exc

    validate_profile(payload)
    return _deserialize_artifact(payload)


def _deserialize_artifact(payload: Mapping[str, Any]) -> SyntheticProfileArtifact:
    """Doğrulanmış payload'dan artefakt oluşturur."""
    tables = tuple(_deserialize_table(t) for t in payload.get("tables", []))
    system_raw = payload.get("system_wide", {})
    system_wide = _deserialize_system_wide(system_raw)
    return SyntheticProfileArtifact(
        profile_schema_version=str(payload["profile_schema_version"]),
        tables=tables,
        system_wide=system_wide,
    )


# ---------------------------------------------------------------------------
# Gizlilik kapısı
# ---------------------------------------------------------------------------


def validate_profile(
    payload: Mapping[str, Any],
    *,
    k: int = DEFAULT_SUPPRESSION_THRESHOLD,
) -> None:
    """Profil payload'ını gizlilik kapısından geçirir.

    İhlal durumunda SyntheticDataValidationError fırlatır.
    """
    _validate_version(payload)
    _validate_allowed_keys(payload, _ALLOWED_TOP_LEVEL_KEYS, context="root")
    _validate_no_forbidden_keys(payload, context="root")
    _validate_tables(payload, k=k)
    _validate_system_wide(payload)


def _validate_version(payload: Mapping[str, Any]) -> None:
    version = payload.get("profile_schema_version")
    if version != PROFILE_SCHEMA_VERSION:
        raise SyntheticDataValidationError(
            f"Profil şema sürümü uyumsuz: beklenen {PROFILE_SCHEMA_VERSION!r}, alınan {version!r}"
        )


def _validate_no_forbidden_keys(
    mapping: Mapping[str, Any],
    *,
    context: str,
) -> None:
    """Yasaklı alan adlarını denetler — recursive olarak tüm iç içe mapping'lerde."""
    for key in mapping:
        lowered = key.lower()
        if lowered in _FORBIDDEN_FIELD_NAMES:
            raise SyntheticDataValidationError(
                f"Gizlilik kapısı ihlali ({context}): yasaklı alan {key!r} bulundu"
            )
        value = mapping[key]
        if isinstance(value, dict):
            _validate_no_forbidden_keys(value, context=f"{context}.{key}")
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    _validate_no_forbidden_keys(item, context=f"{context}.{key}[{i}]")


def _validate_tables(payload: Mapping[str, Any], *, k: int) -> None:
    tables = payload.get("tables")
    if not isinstance(tables, list):
        raise SyntheticDataValidationError("Profil 'tables' alanı bir liste olmalı")
    for idx, table in enumerate(tables):
        ctx = f"tables[{idx}]"
        _validate_table(table, ctx=ctx, k=k)


def _validate_table(table: Mapping[str, Any], *, ctx: str, k: int) -> None:
    _validate_allowed_keys(table, _ALLOWED_TABLE_KEYS, context=ctx)

    if "table_name" not in table or "row_count" not in table:
        raise SyntheticDataValidationError(f"{ctx}: 'table_name' ve 'row_count' zorunlu")
    if not isinstance(table["row_count"], int) or table["row_count"] < 0:
        raise SyntheticDataValidationError(f"{ctx}: 'row_count' negatif olmayan tam sayı olmalı")

    columns = table.get("columns", [])
    if not isinstance(columns, list):
        raise SyntheticDataValidationError(f"{ctx}: 'columns' liste olmalı")
    for ci, col in enumerate(columns):
        _validate_column(col, ctx=f"{ctx}.columns[{ci}]", k=k)


def _validate_column(column: Mapping[str, Any], *, ctx: str, k: int) -> None:
    _validate_allowed_keys(column, _ALLOWED_COLUMN_KEYS, context=ctx)

    for required in ("column_name", "column_type", "null_ratio", "distinct_ratio"):
        if required not in column:
            raise SyntheticDataValidationError(f"{ctx}: zorunlu alan {required!r} eksik")

    if column["column_type"] not in _VALID_COLUMN_TYPES:
        raise SyntheticDataValidationError(f"{ctx}: geçersiz column_type {column['column_type']!r}")

    _validate_ratio(column["null_ratio"], ctx=f"{ctx}.null_ratio")
    _validate_ratio(column["distinct_ratio"], ctx=f"{ctx}.distinct_ratio")

    # Uzunluk histogramı — kova bastırma kontrolü.
    for bi, bucket in enumerate(column.get("length_histogram", [])):
        bctx = f"{ctx}.length_histogram[{bi}]"
        _validate_length_bucket(bucket, ctx=bctx, k=k)

    # Desil değerleri — min/max içermediğinden emin ol.
    deciles = column.get("deciles")
    if deciles is not None:
        _validate_deciles(deciles, ctx=f"{ctx}.deciles")

    # Pay dağılımı — kova bastırma kontrolü.
    for bi, bucket in enumerate(column.get("share_distribution", [])):
        bctx = f"{ctx}.share_distribution[{bi}]"
        _validate_share_bucket(bucket, ctx=bctx, k=k)


def _validate_length_bucket(bucket: Mapping[str, Any], *, ctx: str, k: int) -> None:
    for required in ("length", "share", "count"):
        if required not in bucket:
            raise SyntheticDataValidationError(f"{ctx}: zorunlu alan {required!r} eksik")
    count = int(bucket["count"])
    if _bucket_is_suppressed(count, k):
        raise SyntheticDataValidationError(f"{ctx}: kova bastırma ihlali — count={count} < k={k}")
    _validate_ratio(bucket["share"], ctx=f"{ctx}.share")


def _validate_deciles(deciles: Mapping[str, Any], *, ctx: str) -> None:
    _validate_allowed_keys(deciles, _ALLOWED_DECILE_KEYS, context=ctx)
    for key in _ALLOWED_DECILE_KEYS:
        if key not in deciles:
            raise SyntheticDataValidationError(f"{ctx}: zorunlu desil {key!r} eksik")
    # Desiller sıralı olmalı: p10 <= p25 <= p50 <= p75 <= p90 <= p99.
    prev = float(deciles["p10"])
    for key in ("p25", "p50", "p75", "p90", "p99"):
        current = float(deciles[key])
        if current < prev:
            raise SyntheticDataValidationError(f"{ctx}: desiller sıralı değil — {key} < önceki")
        prev = current


def _validate_share_bucket(bucket: Mapping[str, Any], *, ctx: str, k: int) -> None:
    for required in ("value_class", "share", "count"):
        if required not in bucket:
            raise SyntheticDataValidationError(f"{ctx}: zorunlu alan {required!r} eksik")
    count = int(bucket["count"])
    if _bucket_is_suppressed(count, k):
        raise SyntheticDataValidationError(f"{ctx}: kova bastırma ihlali — count={count} < k={k}")
    _validate_ratio(bucket["share"], ctx=f"{ctx}.share")

    # value_class serbest metin değil, desen/kategori sınıfı olmalı.
    value_class = str(bucket["value_class"])
    if not value_class or len(value_class) > 128:
        raise SyntheticDataValidationError(f"{ctx}: value_class boş veya çok uzun")


def _validate_system_wide(payload: Mapping[str, Any]) -> None:
    system_wide = payload.get("system_wide")
    if system_wide is None:
        return
    if not isinstance(system_wide, dict):
        raise SyntheticDataValidationError("system_wide bir mapping olmalı")
    _validate_allowed_keys(system_wide, _ALLOWED_SYSTEM_KEYS, context="system_wide")

    # Hacim eğrisi.
    for vi, vol in enumerate(system_wide.get("volume_curve", [])):
        vctx = f"system_wide.volume_curve[{vi}]"
        for required in ("period", "key", "share"):
            if required not in vol:
                raise SyntheticDataValidationError(f"{vctx}: zorunlu alan {required!r} eksik")
        _validate_ratio(vol["share"], ctx=f"{vctx}.share")

    # Gecikme dağılımı.
    latency = system_wide.get("latency_distribution")
    if latency is not None:
        lctx = "system_wide.latency_distribution"
        for required in ("p50", "p90", "p99"):
            if required not in latency:
                raise SyntheticDataValidationError(f"{lctx}: zorunlu alan {required!r} eksik")
        p50 = float(latency["p50"])
        p90 = float(latency["p90"])
        p99 = float(latency["p99"])
        if not (p50 <= p90 <= p99):
            raise SyntheticDataValidationError(f"{lctx}: gecikme desilleri sıralı değil")


def _validate_ratio(value: Any, *, ctx: str) -> None:
    """Oran 0–1 arasında ve 4 ondalıktan hassas değil."""
    if not isinstance(value, (int, float)):
        raise SyntheticDataValidationError(f"{ctx}: sayı olmalı")
    fval = float(value)
    if fval < 0.0 or fval > 1.0:
        raise SyntheticDataValidationError(f"{ctx}: oran 0–1 arasında olmalı, alınan {fval}")
    # 4 ondalıktan fazla hassasiyet kontrolü.
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise SyntheticDataValidationError(f"{ctx}: çözümlenemeyen sayı")
    if dec.as_tuple().exponent < -RATIO_DECIMAL_PLACES:
        raise SyntheticDataValidationError(
            f"{ctx}: oran {RATIO_DECIMAL_PLACES} ondalıktan hassas olamaz"
        )


def _validate_allowed_keys(
    mapping: Mapping[str, Any],
    allowed: frozenset[str],
    *,
    context: str,
) -> None:
    """Yalnızca izin verilen anahtarların bulunduğunu doğrular."""
    for key in mapping:
        if key not in allowed:
            raise SyntheticDataValidationError(f"{context}: izin verilmeyen anahtar {key!r}")


# ---------------------------------------------------------------------------
# Artefakt'tan JSON serializasyon
# ---------------------------------------------------------------------------


def artifact_to_dict(artifact: SyntheticProfileArtifact) -> dict[str, Any]:
    """Artefaktı JSON-uyumlu dict'e çevirir."""
    result = asdict(artifact)
    # Tuple'ları listeye çevir (asdict zaten yapar ama garanti).
    return json.loads(json.dumps(result))

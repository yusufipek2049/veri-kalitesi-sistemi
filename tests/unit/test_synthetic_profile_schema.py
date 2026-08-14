"""Faz 4: Profil şeması ve gizlilik kapısı testleri.

Kabul kriterleri:
1. Gizlilik kapısının her kuralı için hem geçen hem reddedilen test.
2. Şema örnek değer, satır listesi veya serbest metin taşıyamaz — doğrulayan test.
3. Örnek profil dosyası elle yazılmış sentetik sayılardan oluşuyor.
4. Kapı ihlali SyntheticDataValidationError fırlatıyor.
5. Geçerli profil dosyası kapıdan geçiyor.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from veri_kalitesi.synthetic_data.errors import SyntheticDataValidationError
from veri_kalitesi.synthetic_data.profile_schema import (
    DEFAULT_SUPPRESSION_THRESHOLD,
    PROFILE_SCHEMA_VERSION,
    ColumnProfile,
    DecileValues,
    LatencyDistribution,
    LengthBucket,
    ShareBucket,
    SyntheticProfileArtifact,
    SystemWideProfile,
    TableProfile,
    VolumePoint,
    _round_ratio,
    artifact_to_dict,
    load_profile,
    validate_profile,
)

_EXAMPLE_PROFILE_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "database" / "synthetic-profile-example.json"
)


# ---------------------------------------------------------------------------
# Yardımcı: geçerli bir temel profil payload'ı oluşturur
# ---------------------------------------------------------------------------


def _valid_column(
    name: str = "activity_score",
    col_type: str = "numeric",
    null_ratio: float = 0.02,
    distinct_ratio: float = 0.5,
    count: int = DEFAULT_SUPPRESSION_THRESHOLD,
) -> dict[str, Any]:
    """Geçerli bir kolon profili dict'i döndürür."""
    col: dict[str, Any] = {
        "column_name": name,
        "column_type": col_type,
        "null_ratio": null_ratio,
        "distinct_ratio": distinct_ratio,
    }
    if col_type == "numeric":
        col["deciles"] = {
            "p10": 5.0,
            "p25": 18.0,
            "p50": 45.0,
            "p75": 72.0,
            "p90": 90.0,
            "p99": 99.0,
        }
    if col_type == "categorical":
        col["share_distribution"] = [
            {"value_class": "ACTIVE", "share": 0.75, "count": count},
            {"value_class": "INACTIVE", "share": 0.25, "count": count},
        ]
    if col_type in ("text", "categorical"):
        col["length_histogram"] = [
            {"length": 12, "share": 0.6, "count": count},
            {"length": 18, "share": 0.4, "count": count},
        ]
    return col


def _valid_table(
    name: str = "synthetic_customers",
    row_count: int = 19000,
    columns: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Geçerli bir tablo profili dict'i döndürür."""
    if columns is None:
        columns = [_valid_column()]
    return {
        "table_name": name,
        "row_count": row_count,
        "columns": columns,
    }


def _valid_payload(
    tables: list[dict[str, Any]] | None = None,
    system_wide: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Geçerli bir profil payload'ı döndürür."""
    payload: dict[str, Any] = {
        "profile_schema_version": PROFILE_SCHEMA_VERSION,
        "tables": tables if tables is not None else [_valid_table()],
    }
    if system_wide is not None:
        payload["system_wide"] = system_wide
    return payload


# ===========================================================================
# Kabul Kriteri 5: Geçerli profil dosyası kapıdan geçiyor
# ===========================================================================


class TestGecerliProfilKapidanGecer:
    """Geçerli profil payload'ları kapıdan geçmeli."""

    def test_minimal_gecerli_payload(self) -> None:
        """Minimum geçerli payload kapıdan geçer."""
        payload = _valid_payload()
        validate_profile(payload)  # İstisna fırlatmamalı.

    def test_tam_gecerli_payload(self) -> None:
        """Tüm alanları dolu geçerli payload kapıdan geçer."""
        payload = _valid_payload(
            tables=[
                _valid_table(
                    columns=[
                        _valid_column("col_num", "numeric"),
                        _valid_column("col_cat", "categorical"),
                        _valid_column("col_txt", "text"),
                        _valid_column("col_date", "date"),
                        _valid_column("col_bool", "boolean"),
                    ]
                )
            ],
            system_wide={
                "volume_curve": [
                    {"period": "daily", "key": "monday", "share": 0.22},
                    {"period": "daily", "key": "tuesday", "share": 0.78},
                ],
                "latency_distribution": {
                    "p50": 120.0,
                    "p90": 1800.0,
                    "p99": 14400.0,
                },
                "defect_clustering_coefficient": 0.6,
            },
        )
        validate_profile(payload)

    def test_example_profile_file_passes_gate(self) -> None:
        """Örnek profil dosyası kapıdan geçer — AK 5."""
        if not _EXAMPLE_PROFILE_PATH.exists():
            pytest.skip("Örnek profil dosyası bulunamadı")
        artifact = load_profile(_EXAMPLE_PROFILE_PATH)
        assert artifact.profile_schema_version == PROFILE_SCHEMA_VERSION
        assert len(artifact.tables) >= 1
        assert artifact.system_wide is not None


# ===========================================================================
# Kabul Kriteri 4: Kapı ihlali SyntheticDataValidationError fırlatıyor
# ===========================================================================


class TestKapiIhlaliHataFirlatir:
    """Kapı ihlalleri SyntheticDataValidationError fırlatmalı."""

    def test_versiyon_uyumsuz(self) -> None:
        payload = _valid_payload()
        payload["profile_schema_version"] = "WRONG_VERSION"
        with pytest.raises(SyntheticDataValidationError, match="sürümü uyumsuz"):
            validate_profile(payload)

    def test_versiyon_yok(self) -> None:
        payload = _valid_payload()
        del payload["profile_schema_version"]
        with pytest.raises(SyntheticDataValidationError, match="sürümü uyumsuz"):
            validate_profile(payload)

    def test_tables_liste_degil(self) -> None:
        payload = _valid_payload()
        payload["tables"] = "not_a_list"
        with pytest.raises(SyntheticDataValidationError, match="liste olmalı"):
            validate_profile(payload)

    def test_row_count_negatif(self) -> None:
        payload = _valid_payload(tables=[_valid_table(row_count=-1)])
        with pytest.raises(SyntheticDataValidationError, match="negatif olmayan"):
            validate_profile(payload)

    def test_oran_0_1_disinda(self) -> None:
        payload = _valid_payload(tables=[_valid_table(columns=[_valid_column(null_ratio=1.5)])])
        with pytest.raises(SyntheticDataValidationError, match="0–1 arasında"):
            validate_profile(payload)

    def test_oran_negatif(self) -> None:
        payload = _valid_payload(
            tables=[_valid_table(columns=[_valid_column(distinct_ratio=-0.1)])]
        )
        with pytest.raises(SyntheticDataValidationError, match="0–1 arasında"):
            validate_profile(payload)

    def test_oran_hassasiyet_ihlali(self) -> None:
        """4 ondalıktan hassas oran reddedilir."""
        payload = _valid_payload(tables=[_valid_table(columns=[_valid_column(null_ratio=0.12345)])])
        with pytest.raises(SyntheticDataValidationError, match="ondalıktan hassas"):
            validate_profile(payload)

    def test_desiller_sirasiz(self) -> None:
        payload = _valid_payload(
            tables=[
                _valid_table(
                    columns=[
                        _valid_column(
                            col_type="numeric",
                        )
                    ]
                )
            ]
        )
        # p25 < p10 yap — sıralama ihlali.
        payload["tables"][0]["columns"][0]["deciles"]["p25"] = 1.0
        with pytest.raises(SyntheticDataValidationError, match="sıralı değil"):
            validate_profile(payload)

    def test_desil_eksik(self) -> None:
        payload = _valid_payload(tables=[_valid_table(columns=[_valid_column(col_type="numeric")])])
        del payload["tables"][0]["columns"][0]["deciles"]["p99"]
        with pytest.raises(SyntheticDataValidationError, match="p99"):
            validate_profile(payload)

    def test_gecersiz_column_type(self) -> None:
        payload = _valid_payload(
            tables=[_valid_table(columns=[_valid_column(col_type="unknown_type")])]
        )
        with pytest.raises(SyntheticDataValidationError, match="geçersiz column_type"):
            validate_profile(payload)

    def test_dosya_bulunamadi(self, tmp_path: Path) -> None:
        with pytest.raises(SyntheticDataValidationError, match="bulunamadı"):
            load_profile(tmp_path / "nonexistent.json")

    def test_bozuk_json(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid json", encoding="utf-8")
        with pytest.raises(SyntheticDataValidationError, match="okunamadı"):
            load_profile(bad)

    def test_izin_verilmeyen_ust_seviye_anahtar(self) -> None:
        payload = _valid_payload()
        payload["unknown_field"] = "should not be here"
        with pytest.raises(SyntheticDataValidationError, match="izin verilmeyen"):
            validate_profile(payload)

    def test_izin_verilmeyen_tablo_anahtari(self) -> None:
        payload = _valid_payload()
        payload["tables"][0]["extra_column"] = "nope"
        with pytest.raises(SyntheticDataValidationError, match="izin verilmeyen"):
            validate_profile(payload)

    def test_latency_sirali_degil(self) -> None:
        payload = _valid_payload(
            system_wide={"latency_distribution": {"p50": 500.0, "p90": 100.0, "p99": 1000.0}}
        )
        with pytest.raises(SyntheticDataValidationError, match="sıralı değil"):
            validate_profile(payload)


# ===========================================================================
# Kabul Kriteri 1: Gizlilik kapısının her kuralı için test
# ===========================================================================


class TestKovaBastirma:
    """Kova bastırma: n < k olan kova yazılmaz."""

    def test_bastirilmis_length_histogram_kovasi_reddedilir(self) -> None:
        """count < k olan length histogram kovası reddedilir."""
        k = DEFAULT_SUPPRESSION_THRESHOLD
        payload = _valid_payload(
            tables=[
                _valid_table(
                    columns=[
                        _valid_column(
                            col_type="text",
                            count=k,  # Geçerli kova
                        )
                    ]
                )
            ]
        )
        # Bir kovanın count'unu k'nın altına düşür.
        payload["tables"][0]["columns"][0]["length_histogram"][0]["count"] = k - 1
        with pytest.raises(SyntheticDataValidationError, match="kova bastırma"):
            validate_profile(payload)

    def test_bastirilmis_share_distribution_kovasi_reddedilir(self) -> None:
        """count < k olan share distribution kovası reddedilir."""
        k = DEFAULT_SUPPRESSION_THRESHOLD
        payload = _valid_payload(
            tables=[
                _valid_table(
                    columns=[
                        _valid_column(
                            col_type="categorical",
                            count=k,
                        )
                    ]
                )
            ]
        )
        payload["tables"][0]["columns"][0]["share_distribution"][0]["count"] = k - 1
        with pytest.raises(SyntheticDataValidationError, match="kova bastırma"):
            validate_profile(payload)

    def test_k_esik_deger_gecerli(self) -> None:
        """count == k olan kova geçerli (bastırılmaz)."""
        k = DEFAULT_SUPPRESSION_THRESHOLD
        payload = _valid_payload(
            tables=[_valid_table(columns=[_valid_column(col_type="text", count=k)])]
        )
        validate_profile(payload)

    def test_ozel_k_esigi(self) -> None:
        """Özel k eşiği ile bastırma kontrolü."""
        payload = _valid_payload(
            tables=[_valid_table(columns=[_valid_column(col_type="text", count=5)])]
        )
        # k=10 ile count=5 bastırılmalı.
        with pytest.raises(SyntheticDataValidationError, match="kova bastırma"):
            validate_profile(payload, k=10)


class TestMinMaxYasak:
    """min/max ASLA yazılmaz: p1/p99 kullanılır."""

    def test_minimum_measure_yasakli(self) -> None:
        payload = _valid_payload()
        payload["tables"][0]["columns"][0]["minimum_measure"] = 0.01
        with pytest.raises(SyntheticDataValidationError, match="yasaklı alan"):
            validate_profile(payload)

    def test_maximum_measure_yasakli(self) -> None:
        payload = _valid_payload()
        payload["tables"][0]["columns"][0]["maximum_measure"] = 999999.99
        with pytest.raises(SyntheticDataValidationError, match="yasaklı alan"):
            validate_profile(payload)

    def test_min_yasakli(self) -> None:
        payload = _valid_payload()
        payload["tables"][0]["columns"][0]["min"] = 0.01
        with pytest.raises(SyntheticDataValidationError, match="yasaklı alan"):
            validate_profile(payload)

    def test_max_yasakli(self) -> None:
        payload = _valid_payload()
        payload["tables"][0]["columns"][0]["max"] = 999999.99
        with pytest.raises(SyntheticDataValidationError, match="yasaklı alan"):
            validate_profile(payload)


class TestOranYuvarlama:
    """Oranlar 4 ondalık basamağa yuvarlanır; ham sayı yazılmaz."""

    def test_dort_ondalik_gecerli(self) -> None:
        payload = _valid_payload(tables=[_valid_table(columns=[_valid_column(null_ratio=0.1234)])])
        validate_profile(payload)

    def test_bes_ondalik_reddedilir(self) -> None:
        payload = _valid_payload(tables=[_valid_table(columns=[_valid_column(null_ratio=0.12345)])])
        with pytest.raises(SyntheticDataValidationError, match="ondalıktan hassas"):
            validate_profile(payload)

    def test_round_ratio_dogru_yuvarlar(self) -> None:
        # Python Decimal banker's rounding: 0.12345 → 0.1234 (4 çift).
        assert _round_ratio(0.12345) == 0.1234
        assert _round_ratio(0.12355) == 0.1236
        assert _round_ratio(0.10000) == 0.1
        assert _round_ratio(0.0) == 0.0


class TestSerbestMetinYok:
    """Serbest metin yok: yalnız uzunluk ve desen sınıfı çıkar."""

    def test_sample_value_yasakli(self) -> None:
        payload = _valid_payload()
        payload["tables"][0]["columns"][0]["sample_value"] = "John Doe"
        with pytest.raises(SyntheticDataValidationError, match="yasaklı alan"):
            validate_profile(payload)

    def test_examples_yasakli(self) -> None:
        payload = _valid_payload()
        payload["tables"][0]["columns"][0]["examples"] = ["a", "b"]
        with pytest.raises(SyntheticDataValidationError, match="yasaklı alan"):
            validate_profile(payload)

    def test_free_text_yasakli(self) -> None:
        payload = _valid_payload()
        payload["tables"][0]["columns"][0]["free_text"] = "some text"
        with pytest.raises(SyntheticDataValidationError, match="yasaklı alan"):
            validate_profile(payload)

    def test_content_yasakli(self) -> None:
        payload = _valid_payload()
        payload["tables"][0]["columns"][0]["content"] = "raw content"
        with pytest.raises(SyntheticDataValidationError, match="yasaklı alan"):
            validate_profile(payload)


class TestSatirListesiYok:
    """Satır listesi yok: profil hiçbir şekilde satır verisi taşıyamaz."""

    def test_rows_yasakli(self) -> None:
        payload = _valid_payload()
        payload["tables"][0]["rows"] = [{"id": 1}]
        with pytest.raises(SyntheticDataValidationError, match="yasaklı alan"):
            validate_profile(payload)

    def test_row_list_yasakli(self) -> None:
        payload = _valid_payload()
        payload["tables"][0]["row_list"] = [{"id": 1}]
        with pytest.raises(SyntheticDataValidationError, match="yasaklı alan"):
            validate_profile(payload)

    def test_data_yasakli(self) -> None:
        payload = _valid_payload()
        payload["tables"][0]["data"] = [{"id": 1}]
        with pytest.raises(SyntheticDataValidationError, match="yasaklı alan"):
            validate_profile(payload)

    def test_values_yasakli(self) -> None:
        payload = _valid_payload()
        payload["tables"][0]["columns"][0]["values"] = [1, 2, 3]
        with pytest.raises(SyntheticDataValidationError, match="yasaklı alan"):
            validate_profile(payload)


# ===========================================================================
# Kabul Kriteri 2: Şema örnek değer/satır listesi/serbest metin taşıyamaz
# ===========================================================================


class TestSemaYapisi:
    """Şema tanımı örnek değer, satır listesi veya serbest metin barındırmaz."""

    def test_dataclass_fieldlerinde_yasakli_ad_yok(self) -> None:
        """Dataclass alan adlarında yasaklı isim yok."""
        from dataclasses import fields

        for cls in (
            ColumnProfile,
            LengthBucket,
            ShareBucket,
            DecileValues,
            TableProfile,
            SyntheticProfileArtifact,
            SystemWideProfile,
            VolumePoint,
            LatencyDistribution,
        ):
            for f in fields(cls):
                assert f.name.lower() not in {
                    "sample",
                    "sample_value",
                    "sample_values",
                    "examples",
                    "rows",
                    "row_list",
                    "data",
                    "values",
                    "free_text",
                    "text",
                    "content",
                    "minimum",
                    "maximum",
                }, f"{cls.__name__}.{f.name} yasaklı alan adıyla çakışıyor"

    def test_artifact_to_dict_yasakli_anahtar_icermiyor(self) -> None:
        """Serializasyon sonrası dict'te yasaklı anahtar yok."""
        artifact = SyntheticProfileArtifact(
            profile_schema_version=PROFILE_SCHEMA_VERSION,
            tables=(
                TableProfile(
                    table_name="synthetic_customers",
                    row_count=19000,
                    columns=(
                        ColumnProfile(
                            column_name="activity_score",
                            column_type="numeric",
                            null_ratio=0.02,
                            distinct_ratio=0.5,
                            deciles=DecileValues(
                                p10=5.0,
                                p25=18.0,
                                p50=45.0,
                                p75=72.0,
                                p90=90.0,
                                p99=99.0,
                            ),
                        ),
                    ),
                ),
            ),
            system_wide=SystemWideProfile(
                volume_curve=(VolumePoint(period="daily", key="monday", share=0.22),),
                latency_distribution=LatencyDistribution(p50=120.0, p90=1800.0, p99=14400.0),
                defect_clustering_coefficient=0.6,
            ),
        )
        result = artifact_to_dict(artifact)
        _assert_no_forbidden_keys_recursive(result)


def _assert_no_forbidden_keys_recursive(obj: Any, path: str = "root") -> None:
    """Rekursif olarak yasaklı anahtar olmadığını doğrular."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            assert key.lower() not in {
                "sample",
                "sample_value",
                "sample_values",
                "examples",
                "raw_value",
                "raw_values",
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
            }, f"Yasaklı anahtar {key!r} bulundu ({path})"
            _assert_no_forbidden_keys_recursive(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _assert_no_forbidden_keys_recursive(item, f"{path}[{i}]")


# ===========================================================================
# Kabul Kriteri 3: Örnek profil dosyası sentetik sayılardan oluşuyor
# ===========================================================================


class TestOrnekProfilSentetik:
    """Örnek profil dosyası elle yazılmış sentetik sayılardan oluşuyor."""

    def test_example_file_exists(self) -> None:
        assert _EXAMPLE_PROFILE_PATH.exists()

    def test_example_file_is_valid_json(self) -> None:
        raw = _EXAMPLE_PROFILE_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        assert isinstance(data, dict)

    def test_example_file_has_correct_version(self) -> None:
        raw = _EXAMPLE_PROFILE_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        assert data["profile_schema_version"] == PROFILE_SCHEMA_VERSION

    def test_example_file_no_real_data_markers(self) -> None:
        """Gerçek veri belirteci (TC kimlik, gerçek isim vb.) yok."""
        raw = _EXAMPLE_PROFILE_PATH.read_text(encoding="utf-8")
        # Gerçek veri belirteçleri: TC kimlik no paterni (11 haneli sayı),
        # gerçek isim paterni, gerçek adres paterni.
        import re

        # 11 haneli sayı (TC kimlik benzeri) — sentetik profilde olmamalı.
        tc_pattern = re.compile(r"\b\d{11}\b")
        assert not tc_pattern.search(raw), "Olası TC kimlik numarası bulundu"

    def test_example_file_passes_validation(self) -> None:
        """Örnek dosya validasyon'dan geçer."""
        raw = _EXAMPLE_PROFILE_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        validate_profile(data)


# ===========================================================================
# Load profile ve round-trip testleri
# ===========================================================================


class TestLoadProfile:
    """load_profile fonksiyonu testleri."""

    def test_load_valid_file(self, tmp_path: Path) -> None:
        payload = _valid_payload()
        f = tmp_path / "profile.json"
        f.write_text(json.dumps(payload), encoding="utf-8")
        artifact = load_profile(f)
        assert artifact.profile_schema_version == PROFILE_SCHEMA_VERSION
        assert len(artifact.tables) == 1
        assert artifact.tables[0].table_name == "synthetic_customers"
        assert artifact.tables[0].row_count == 19000

    def test_load_with_system_wide(self, tmp_path: Path) -> None:
        payload = _valid_payload(
            system_wide={
                "volume_curve": [
                    {"period": "daily", "key": "monday", "share": 0.22},
                ],
                "latency_distribution": {
                    "p50": 120.0,
                    "p90": 1800.0,
                    "p99": 14400.0,
                },
                "defect_clustering_coefficient": 0.6,
            }
        )
        f = tmp_path / "profile.json"
        f.write_text(json.dumps(payload), encoding="utf-8")
        artifact = load_profile(f)
        assert artifact.system_wide.latency_distribution is not None
        assert artifact.system_wide.latency_distribution.p50 == 120.0
        assert artifact.system_wide.defect_clustering_coefficient == 0.6
        assert len(artifact.system_wide.volume_curve) == 1

    def test_load_rejects_invalid(self, tmp_path: Path) -> None:
        payload = _valid_payload()
        payload["profile_schema_version"] = "WRONG"
        f = tmp_path / "bad.json"
        f.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(SyntheticDataValidationError):
            load_profile(f)


class TestArtifactToDict:
    """artifact_to_dict round-trip testleri."""

    def test_roundtrip(self) -> None:
        artifact = SyntheticProfileArtifact(
            profile_schema_version=PROFILE_SCHEMA_VERSION,
            tables=(
                TableProfile(
                    table_name="synthetic_test",
                    row_count=1000,
                    columns=(
                        ColumnProfile(
                            column_name="score",
                            column_type="numeric",
                            null_ratio=0.01,
                            distinct_ratio=0.5,
                            deciles=DecileValues(
                                p10=1.0,
                                p25=25.0,
                                p50=50.0,
                                p75=75.0,
                                p90=90.0,
                                p99=99.0,
                            ),
                        ),
                    ),
                ),
            ),
        )
        d = artifact_to_dict(artifact)
        assert d["profile_schema_version"] == PROFILE_SCHEMA_VERSION
        assert d["tables"][0]["table_name"] == "synthetic_test"
        assert d["tables"][0]["columns"][0]["deciles"]["p50"] == 50.0


# ===========================================================================
# İç içe yasaklı anahtar taraması
# ===========================================================================


class TestIceIceYasakliAnahtar:
    """İç içe mapping'lerde yasaklı anahtar taraması."""

    def test_system_wide_icice_yasakli(self) -> None:
        payload = _valid_payload(
            system_wide={
                "latency_distribution": {
                    "p50": 120.0,
                    "p90": 1800.0,
                    "p99": 14400.0,
                    "sample": 999.0,  # İç içe yasaklı
                }
            }
        )
        with pytest.raises(SyntheticDataValidationError, match="yasaklı alan"):
            validate_profile(payload)

    def test_liste_icinde_yasakli(self) -> None:
        payload = _valid_payload()
        payload["tables"][0]["columns"][0]["length_histogram"] = [
            {"length": 12, "share": 0.6, "count": 100, "raw_value": "secret"}
        ]
        with pytest.raises(SyntheticDataValidationError, match="yasaklı alan"):
            validate_profile(payload)


# ===========================================================================
# Zorunlu alan eksikliği testleri
# ===========================================================================


class TestZorunluAlanEksikligi:
    """Zorunlu alanların eksikliği reddedilir."""

    def test_column_name_eksik(self) -> None:
        col = _valid_column()
        del col["column_name"]
        payload = _valid_payload(tables=[_valid_table(columns=[col])])
        with pytest.raises(SyntheticDataValidationError, match="column_name"):
            validate_profile(payload)

    def test_table_name_eksik(self) -> None:
        table = _valid_table()
        del table["table_name"]
        payload = _valid_payload(tables=[table])
        with pytest.raises(SyntheticDataValidationError, match="table_name"):
            validate_profile(payload)

    def test_row_count_eksik(self) -> None:
        table = _valid_table()
        del table["row_count"]
        payload = _valid_payload(tables=[table])
        with pytest.raises(SyntheticDataValidationError, match="row_count"):
            validate_profile(payload)

    def test_share_bucket_value_class_eksik(self) -> None:
        col = _valid_column(col_type="categorical")
        col["share_distribution"] = [{"share": 0.5, "count": 100}]
        payload = _valid_payload(tables=[_valid_table(columns=[col])])
        with pytest.raises(SyntheticDataValidationError, match="value_class"):
            validate_profile(payload)

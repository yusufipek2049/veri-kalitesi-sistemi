# Faz 5: Profilden Üretim

## Bağlam

Bir bankanın veri kalitesi sisteminde sentetik veri üreticisini gerçekçileştiriyorsun.
Hedef dosya: `src/veri_kalitesi/synthetic_data/postgresql_dataset.py` (~1800+ satır).
Testler: `tests/unit/test_synthetic_postgresql_dataset.py`, `tests/unit/test_synthetic_generator.py`.

### Tamamlanan Önceki Fazlar

- **Faz 1 (Kusur Kümelenmesi):** V2. Küme bazlı kusur dağılımı, `SCENARIO_CLUSTER_INTENSITY`.
- **Faz 2 (Kolon Dağılımları):** V3. `MeasureDistribution` dataclass, `MEASURE_DISTRIBUTIONS`, genelleştirilmiş `_measure()`.
- **Faz 3 (Takvim Gerçekçiliği):** V4. Gerçek takvim ekseni, hafta içi/sonu, mesai saati, ay sonu, late-arriving.
- **Faz 4 (Profil Şeması + Gizlilik Kapısı):** `SYNTHETIC_PROFILE_V1` şeması, gizlilik kapısı (kova bastırma, p1/p99, oran yuvarlama, serbest metin yok), örnek profil dosyası.

### Problem

Faz 1–3'ün parametreleri kod içi sabit. Faz 4'ün profil şeması hazır. Şimdi bu profilden üretim yapacağız — ama profil **opsiyonel** olacak. Profil verilmezse mevcut kod içi varsayılanlarla çalışmaya devam edecek.

## Görev

### 1. Faz 2 ve 3 Parametrelerini Profilden Oku

- `MEASURE_DISTRIBUTIONS` (Faz 2) profil dosyasından override edilebilsin.
- Takvim parametreleri (Faz 3: hafta içi/sonu ağırlıkları, mesai profili, ay sonu katsayısı, gecikme dağılımı) profil dosyasından override edilebilsin.
- Kusur kümelenme katsayısı (Faz 1) profil dosyasından override edilebilsin.
- **Profil verilmezse** mevcut kod içi varsayılanlarla çalışmaya devam etsin — profil zorunlu bağımlılık olmasın.

### 2. Profil Yükleme ve Gizlilik Kapısı

- Profil dosyası yolu CLI argümanı olarak eklensin: `--profile PATH`.
- Yükleme sırasında Faz 4'teki gizlilik kapısından geçir.
- Kapı ihlali → `SyntheticDataValidationError`, üretim dursun.

### 3. Soyağacı İzlenebilirliği

- Kullanılan profilin sürümünü (`profile_schema_version`) ve hash'ini (SHA-256) `GenerationSummary`'ye yaz.
- Yeni alanlar: `profile_version: str | None`, `profile_sha256: str | None`.
- Profil kullanılmadıysa bu alanlar `None` kalsın.
- `generation_runs` tablosuna da yazılsın.

### 4. Kusur Enjeksiyonu Profilden ETKİLENMESİN

- DefectTruth üretimi, kusur enjeksiyonu, `_selected_defects` mekaniği — bunlar **yalnız** senaryo ve seed'e bağlı kalsın.
- Profilden yalnız oranlar ve dağılımlar gelsin (Faz 1 küme katsayısı, Faz 2 ölçü dağılımları, Faz 3 takvim parametreleri).
- Ground truth bütünlüğü korunmalı: FP==0, FN==0.

## Invariantlar

- **Determinizm:** aynı (seed, scenario, row_count, profile) aynı canonical_sha256. random/time.time() yasak.
- **Ground truth:** FP==0, FN==0 tüm senaryolarda.
- **Sürüm:** GENERATOR_VERSION artırılmalı (V4 → V5). Testlerde güncelleme.
- **Gizlilik:** example.invalid, SYN- önekleri korunacak.
- **17 tablo sözleşmesi korunacak.**
- **Profil opsiyonel:** Profilsiz çalıştırma çıktısı bozulmamış (Faz 4'ün varsayılanlarıyla aynı).
- **Kod stili:** Türkçe docstring, `from __future__ import annotations`, frozen dataclass, Decimal.
- **Üçüncü parti bağımlılık yok.**

## Kabul Kriterleri

1. **Profilsiz çalıştırma** çıktısı bozulmamış — Faz 4 sonrasıyla aynı canonical_sha256 (veya en azından aynı istatistiksel özellikler).
2. **Aynı profil + aynı seed** aynı canonical_sha256 üretiyor — determinizm testi.
3. **GenerationSummary** profil sürümü ve hash'ini içeriyor (profil varsa), `None` (profilsiz).
4. **Ground truth** FP==0, FN==0 tüm senaryolarda.
5. **Gizlilik kapısı** ihlali → üretim dursun.
6. **CLI** `--profile PATH` argümanı eklendi.

## Teslim Formatı

- **Kod:** Değiştirilen dosyalar ve gerekçesi.
- **Testler:** Kabul kriterlerinin her birini karşılayan test adları.
- **Test çıktısı:** Ham test sonucu.
- **Invariant raporu:** Determinizm, ground truth, sürüm.
- **Varsayımlar:** Yapılan varsayımlar ve açık kalan sorular.

## Çalışma Kuralları

- Mevcut kod stiline uy.
- Yeni üçüncü parti bağımlılık ekleme.
- Testleri çalıştır ve sonucu olduğu gibi bildir.
- Belirsizlik varsa varsayımını açıkça yaz ve devam et.

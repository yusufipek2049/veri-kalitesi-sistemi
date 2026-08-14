# Faz 4: Profil Artefaktı Şeması ve Gizlilik Kapısı

## Bağlam

Bir bankanın veri kalitesi sisteminde sentetik veri üreticisini gerçekçileştiriyorsun.
Hedef dosya: `src/veri_kalitesi/synthetic_data/postgresql_dataset.py` (~1700+ satır).
Testler: `tests/unit/test_synthetic_postgresql_dataset.py`, `tests/unit/test_synthetic_generator.py`.

### Tamamlanan Önceki Fazlar

- **Faz 1 (Kusur Kümelenmesi):** GENERATOR_VERSION = V2. Küme bazlı kusur dağılımı.
- **Faz 2 (Kolon Dağılımları):** GENERATOR_VERSION = V3. `MeasureDistribution` dataclass, `MEASURE_DISTRIBUTIONS`, genelleştirilmiş `_measure()`.
- **Faz 3 (Takvim Gerçekçiliği):** GENERATOR_VERSION = V4. Gerçek takvim ekseni, hafta içi/sonu, mesai saati, ay sonu yığılması, late-arriving dağılımı.

### Problem

Faz 1–3'ün parametreleri tahmin. Ölçüme dayanmaları gerekiyor, ama gerçek satır repoya giremez.
Çözüm: Gerçek veriden yalnız **agregat istatistik** taşıyan versiyonlu bir profil YAML şeması + gizlilik kapısı.

### Mevcut `ProfileMetric`

```python
@dataclass(frozen=True)
class ProfileMetric:
    table_name: str
    row_count: int
    required_value_null_count: int
    distinct_business_key_count: int
    minimum_measure: Decimal | None
    maximum_measure: Decimal | None
    profiling_duration_seconds: float
```

## Görev

### 1. Versiyonlu Profil YAML Şeması Tasarla

İçerik:
- **Tablo başına:** kolon başına null oranı, distinct oranı, uzunluk histogramı (uzunluk + pay), sayısallar için decile'lar (p10, p25, p50, p75, p90, p99), kategorikler için pay dağılımı (değer sınıfı + pay).
- **Sistem geneli:** tablo başına günlük/saatlik hacim eğrisi, gecikme dağılımı (p50, p90, p99), kusur kümelenme katsayısı.
- **Versiyon alanı:** `profile_schema_version: "SYNTHETIC_PROFILE_V1"`.

### 2. Gizlilik Kapısı Yaz

Zorunlu kurallar:
- **Kova bastırma:** n < k (k varsayılan 20) olan kova bastırılır — ya yazılmaz ya da `"<k"` olarak işaretlenir.
- **min/max ASLA yazılmaz:** p1/p99 kullanılır. `minimum_measure` / `maximum_measure` profil artefaktına taşınmaz.
- **Oranlar yuvarlanır:** 4 ondalık basamak. Ham sayı yazılmaz (row_count hariç — o da zaten agregat).
- **Serbest metin yok:** Yalnız uzunluk ve desen sınıfı çıkar. Örnek değer çıkmaz.
- **Satır listesi yok:** Profil hiçbir şekilde satır verisi taşıyamaz.

### 3. Kapı İhlali = Üretim DURSUN

Kapıyı ihlal eden bir profil dosyası yüklenmeye çalışıldığında üretim **uyarıyla devam etmesin**, tamamen dursun. `SyntheticDataValidationError` fırlat.

### 4. ProfileMetric Genişletme

`minimum_measure` / `maximum_measure` alanlarının profil artefaktına taşınmadığından emin ol. Bu alanlar mevcut davranışlarında kalır (runtime profilleme), profil YAML'ya yazılmaz.

## Örnek Profil Dosyası

`docs/database/synthetic-profile-example.yaml` olarak bir örnek oluştur. Tamamen elle yazılmış sentetik sayılardan oluşsun — hiçbir gerçek veri türevi içermesin.

## Invariantlar

- **Determinizm:** Korunuyor.
- **Ground truth:** FP==0, FN==0.
- **Sürüm:** GENERATOR_VERSION değişmez (bu faz üretim mantığını değiştirmez, yalnız şema ve kapı ekler).
- **Gizlilik:** example.invalid, SYN- önekleri korunacak.
- **Kod stili:** Türkçe docstring, `from __future__ import annotations`, frozen dataclass.
- **Üçüncü parti bağımlılık yok.** PyYAML zaten projede varsa kullan, yoksa JSON tabanlı şema düşünülebilir.

## Kabul Kriterleri

1. Gizlilik kapısının her kuralı için hem geçen hem reddedilen bir örnek dosyayla test var.
2. Şema örnek değer, satır listesi veya serbest metin taşıyabilecek hiçbir alan tanımlamıyor — bunu doğrulayan bir test var.
3. Repoya hiçbir gerçek veri türevi eklenmemiş; örnek profil dosyası elle yazılmış sentetik sayılardan oluşuyor.
4. Kapı ihlali `SyntheticDataValidationError` fırlatıyor — test.
5. Geçerli profil dosyası kapıdan geçiyor — test.

## Teslim Formatı

- **Kod:** Değiştirilen/yeni dosyalar ve gerekçesi.
- **Testler:** Kabul kriterlerinin her birini karşılayan test adları.
- **Test çıktısı:** Ham test sonucu.
- **Invariant raporu:** Determinizm, ground truth, sürüm.
- **Varsayımlar:** Yapılan varsayımlar ve açık kalan sorular.

## Çalışma Kuralları

- Mevcut kod stiline uy.
- Yeni üçüncü parti bağımlılık ekleme.
- Testleri çalıştır ve sonucu olduğu gibi bildir.
- Belirsizlik varsa varsayımını açıkça yaz ve devam et.

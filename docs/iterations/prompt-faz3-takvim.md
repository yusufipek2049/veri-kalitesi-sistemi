# Faz 3: Takvim Gerçekçiliği

## Bağlam

Bir bankanın veri kalitesi sisteminde sentetik veri üreticisini gerçekçileştiriyorsun.
Hedef dosya: `src/veri_kalitesi/synthetic_data/postgresql_dataset.py` (~1645+ satır).
Testler: `tests/unit/test_synthetic_postgresql_dataset.py`, `tests/unit/test_synthetic_generator.py`.

### Tamamlanan Önceki Fazlar

- **Faz 1 (Kusur Kümelenmesi):** `GENERATOR_VERSION` = V2. `CLUSTERS_PER_TABLE=8`, `SCENARIO_CLUSTER_INTENSITY`, `_cluster_index()`, `_cluster_multiplier()` (normalize), `_selected_defects()` kümelenme entegrasyonu. 24 test geçiyor.
- **Faz 2 (Kolon Dağılımları):** `GENERATOR_VERSION` = V3. `MeasureDistribution` dataclass, `MEASURE_DISTRIBUTIONS` eşlemesi, genelleştirilmiş `_measure()`. Kolon başına farklı dağılım.

### Mevcut `_event_time` Fonksiyonu (Değiştirilecek)

```python
def _event_time(seed: int, table_name: str, index: int) -> datetime:
    day_offset = _entropy(seed, f"{table_name}:event-day", index) % 180
    seasonal_boost = 21 if index % 10 < 3 else 0
    second_offset = _entropy(seed, f"{table_name}:event-second", index) % 86_400
    return REFERENCE_TIME - timedelta(
        days=max(0, int(day_offset) - seasonal_boost), seconds=int(second_offset)
    )
```

**Sorunlar:**
- `index % 10 < 3` mevsimselliği satır sırasının artefaktı, gerçek takvimle ilgisi yok.
- Hafta sonu / hafta içi ayrımı yok.
- Mesai saati yoğunluğu yok.
- Ay sonu yığılması yok.
- `stale_record` kusuru takvimden bağımsız üretiliyor.
- Late-arriving kayıt (source_created_at ile ingestion arası gecikme) yok.

### Sabitler

```python
REFERENCE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)
STALE_THRESHOLD = REFERENCE_TIME - timedelta(days=365)
```

180 günlük pencere: `REFERENCE_TIME - 180 gün` ile `REFERENCE_TIME` arası.

## Görev

1. **Gerçek takvim ekseni.** Zaman damgasını gerçek takvime oturt:
   - Hafta içi/hafta sonu ağırlığı (hafta sonu hacmi düşük).
   - Mesai saati yoğunluğu (09:00–18:00 arası yüksek, gece düşük).
   - Ay sonu yığılması (ayın son 3 günü hacim artışı).

2. **Late-arriving kayıt dağılımı.** `source_created_at` ile `ingestion_time` arasında gecikme ekle. Çoğu kayıt hızlı gelir (dakikalar), ama kuyruklu bir dağılımla bazıları saatler/günler sonra gelir. Deterministik, indeksten türetilmiş.

3. **Timeliness kusurlarıyla tutarlılık.** `stale_record` kusuru takvimden bağımsız kalmasın. Eğer bir kayıt hafta sonuna denk geliyorsa veya ay sonunda yığılıyorsa, stale_record olasılığı da bu takvimle tutarlı olsun.

## Invariantlar

- **Determinizm:** aynı (seed, scenario, row_count) aynı canonical_sha256. random/time.time() yasak.
- **Ground truth:** FP==0, FN==0 tüm senaryolarda.
- **Sürüm:** `GENERATOR_VERSION` artırılmalı (V3 → V4). Testlerde güncelleme aynı commit'te.
- **REFERENCE_TIME ve STALE_THRESHOLD ile tutarlılık bozulmamalı.**
- **Gizlilik:** example.invalid, SYN- önekleri korunacak.
- **17 tablo sözleşmesi korunacak.**
- **Kod stili:** Türkçe docstring, `from __future__ import annotations`, frozen dataclass.
- **Üçüncü parti bağımlılık yok.**

## Kabul Kriterleri

1. Hafta sonu hacmi hafta içinin ölçülebilir şekilde altında — bunu doğrulayan test.
2. Ay sonu günlerinde (ayın son 3 günü) hacim yığılması var — test.
3. Mesai saatleri (09–18) dışı hacim düşük — test.
4. Late-arriving dağılımı kuyruklu — median düşük, max yüksek — test.
5. `REFERENCE_TIME` ve `STALE_THRESHOLD` ile tutarlılık bozulmamış.
6. Determinizm testi geçiyor.
7. Ground truth FP==0, FN==0.

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

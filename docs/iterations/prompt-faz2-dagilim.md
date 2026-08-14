# Faz 2: Kolon Başına Dağılım Parametreleri

## Bağlam

Bir bankanın veri kalitesi sisteminde sentetik veri üreticisini gerçekçileştiriyorsun.
Hedef dosya: `src/veri_kalitesi/synthetic_data/postgresql_dataset.py` (~1645 satır).
Testler: `tests/unit/test_synthetic_postgresql_dataset.py`, `tests/unit/test_synthetic_generator.py`.

### Tamamlanan Faz 1 (Kusur Kümelenmesi)

- `GENERATOR_VERSION` = `"RELATIONAL_BANKING_GENERATOR_V2"`
- `CLUSTERS_PER_TABLE = 8` ve `SCENARIO_CLUSTER_INTENSITY` mapping'i eklendi.
- `_cluster_index()`, `_cluster_multiplier()` (normalize, ortalama=1.0) eklendi.
- `_selected_defects()` kümelenme entegrasyonu yapıldı.
- 8 yeni kümelenme testi eklendi, 24 test geçiyor.

### Mevcut `_measure` Fonksiyonu (Değiştirilecek)

```python
def _measure(seed: int, table_name: str, index: int) -> Decimal:
    first = max(_uniform(seed, f"{table_name}:normal-a", index), 1e-12)
    second = _uniform(seed, f"{table_name}:normal-b", index)
    normal = math.sqrt(-2.0 * math.log(first)) * math.cos(2.0 * math.pi * second)
    value = min(math.exp(7.0 + normal), 1_000_000.0)
    return Decimal(f"{value:.2f}")
```

Bu fonksiyon 17 tablonun tamamında aynı lognormal(7, 1) dağılımını kullanıyor.
İşlem tutarı, kredi limiti, aktivite skoru — hepsi aynı eğriden geliyor. Bu gerçekçi değil.

### Mevcut 17 Tablo ve measure_column'ları

| Tablo | measure_column | Gerçekçi dağılım önerisi |
|---|---|---|
| synthetic_customers | activity_score | uniform [0, 100] |
| synthetic_customer_contacts | verification_score | beta-benzeri, [0, 1] ağırlıklı |
| synthetic_customer_addresses | location_score | beta-benzeri, [0, 1] |
| synthetic_accounts | current_balance | lognormal(mu=7, sigma=1.5), clip [0.01, 500000] |
| synthetic_account_balances | closing_balance | lognormal(mu=7, sigma=1.2), clip [0, 1000000] |
| synthetic_transactions | transaction_amount | lognormal(mu=5, sigma=1.5), clip [0.01, 50000] |
| synthetic_cards | card_limit | lognormal(mu=8, sigma=1), clip [100, 200000] |
| synthetic_card_transactions | card_transaction_amount | lognormal(mu=4.5, sigma=1.5), clip [0.01, 30000] |
| synthetic_loans | principal_amount | lognormal(mu=9, sigma=1), clip [1000, 1000000] |
| synthetic_loan_installments | installment_amount | lognormal(mu=6, sigma=1), clip [50, 100000] |
| synthetic_payments | payment_amount | lognormal(mu=5.5, sigma=1.5), clip [0.01, 100000] |
| synthetic_beneficiaries | transfer_limit | lognormal(mu=7, sigma=1), clip [100, 500000] |
| synthetic_merchants | merchant_risk_score | uniform [0, 100] |
| synthetic_merchant_transactions | settlement_amount | lognormal(mu=6, sigma=1.5), clip [0.01, 200000] |
| synthetic_customer_risk_profiles | risk_score | uniform [0, 100] |
| synthetic_service_requests | resolution_hours | lognormal(mu=2, sigma=1.5), clip [0.1, 500] |
| synthetic_data_events | lag_seconds | lognormal(mu=3, sigma=2), clip [1, 86400] |

Bu öneriler başlangıç noktasıdır; implementasyonda gözden geçirilebilir.

## Görev

1. **Dağılım tanım veri yapısı oluştur.** `MeasureDistribution` adında bir frozen dataclass veya eşleme tablosu tanımla. İçerik: dağılım ailesi (`"lognormal"`, `"uniform"`, `"bounded_normal"`), parametreler (mu, sigma, low, high), kırpma sınırları.

2. **`MEASURE_DISTRIBUTIONS` sabitini oluştur.** 17 tablonun her biri için yukarıdaki önerilere uygun dağılım tanımı. Tanımlanmamış kolonlar için fallback mevcut lognormal(7, 1) davranışı.

3. **`_measure`'ı genelle.** Yeni imza: `_measure(seed, table_name, index, *, distribution=None)` veya eşlemeyi otomatik oku. Parametre tanımlıysa o dağılımı kullan, değilse mevcut davranış.

4. **Veri yapısını dışarıdan doldurulabilir tasarla.** Faz 4'te profil YAML dosyasından beslenecek. Şimdilik kod içi sabit, ama yapı genişletilebilir olmalı.

## Invariantlar (Bozulmaması Gerekenler)

- **Determinizm:** aynı (seed, scenario, row_count) aynı canonical_sha256 üretmeli. random/time.time() yasak.
- **Ground truth:** FP==0, FN==0 tüm senaryolarda. Kusur enjeksiyonu değişmiyor.
- **Sürüm:** `GENERATOR_VERSION` artırılmalı (V2 → V3). Testlerdeki versiyon sabitleri aynı commit'te güncellenmeli.
- **Gizlilik:** example.invalid, SYN- önekleri, SYN para birimi korunacak.
- **17 tablo sözleşmesi:** Yeni tablo eklenemez, mevcut yeniden adlandırılamaz.
- **Kod stili:** Türkçe docstring, `from __future__ import annotations`, frozen dataclass, Decimal parasal değer.
- **Üçüncü parti bağımlılık yok:** numpy, scipy, faker vb. ekleme. Box-Muller zaten mevcut.

## Kabul Kriterleri

1. Her tablo için üretilen değerlerin p10/p50/p90'ı tanımlanan parametrelerle uyumlu — bunu doğrulayan test(ler).
2. Tanım eklenmemiş kolonların çıktısı değişmemiş (fallback davranışı testi).
3. Determinizm testi geçiyor.
4. Ground truth FP==0, FN==0 tüm 6 senaryoda.
5. `GENERATOR_VERSION` V3'e yükseltilmiş ve testlerde güncellenmiş.

## Teslim Formatı

- **Kod:** Değiştirilen dosyalar ve gerekçesi.
- **Testler:** Kabul kriterlerinin her birini karşılayan test adları.
- **Test çıktısı:** Çalıştırılmış test sonucunun ham özeti.
- **Invariant raporu:** Determinizm, ground truth (FP/FN), sürüm artırma durumu.
- **Varsayımlar:** Yapılan varsayımlar ve açık kalan sorular.

## Çalışma Kuralları

- Mevcut kod stiline uy.
- Yeni üçüncü parti bağımlılık ekleme.
- Testleri çalıştır ve sonucu olduğu gibi bildir.
- Belirsizlik varsa varsayımını açıkça yaz ve devam et.

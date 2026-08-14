---
iteration: 40
status: planned
completed_at: null
decision_reference: USER-DECLARATION-2026-08-CAPABILITY-UPLIFT
---

# İterasyon 40 — Takvim Farkındalıklı Eşik Önerisi

## Amaç

Profil karşılaştırma eşikleri bugün **tek skaler değerdir** ve takvim
boyutu taşımaz. Banka verisi gün sonu, ay sonu, çeyrek sonu ve yıl sonu
döngüsüyle yaşar; ay sonunda hacim iki katına çıkar, gün içinde tablolar
boşalır. Sabit eşik bu dönemlerde yalancı alarm üretir, alarm gürültüsü
sistemin güvenilirliğini yok eder.

Bu iterasyon, geçmiş profil snapshot'larından takvim sınıfı bazlı referans
dağılım üretir ve eşiği **önerir** — otomatik uygulamaz.

## Kullanıcı / Sistem Değeri

- Ay sonu hacim artışı drift olarak raporlanmaz; gerçek bozulma görünür kalır.
- Eşik belirleme, uzmanın tahminine değil ölçülen geçmişe dayanır.
- Öneri maker-checker onayından geçtiği için otomatik eşik kayması olmaz.

## Mevcut FR/UC/RULE

| Kod | Ad |
| --- | --- |
| FR-021 | Profil karşılaştırma |
| FR-022 | Şema değişikliği algılama |
| FR-103 | Drift ve nedensellik sınıflı teşhis |
| FR-107 | Adaptif ve risk bazlı tarama |
| RULE-012, RULE-018, RULE-022 | Tarama stratejisi ve kaynak kullanım kuralları |

## Mevcut Durum Analizi

[`ProfileAnalysisPolicy`](../../src/veri_kalitesi/data_sources/models.py#L388)
düz bir eşik listesidir:

```
comparison_window: int
minimum_history: int
volume_ratio_threshold: float
null_ratio_delta_threshold: float
distinct_ratio_delta_threshold: float
category_loss_ratio_threshold: float
numeric_mean_ratio_threshold: float
numeric_median_ratio_threshold: float
freshness_delay_seconds_threshold: float
```

[`compare_profile_snapshots`](../../src/veri_kalitesi/data_sources/profiling.py#L322)
bu eşikleri sinyal üreticilerine
(`_append_ratio_signal`, `_append_delta_signal`, `_append_category_signal`,
`_append_numeric_signals`, `_append_freshness_signal`) doğrudan aktarır.
Karşılaştırma penceresi kronolojiktir; takvim sınıfı kavramı yoktur.

`_quantile` yardımcı fonksiyonu
([profiling.py:764](../../src/veri_kalitesi/data_sources/profiling.py))
zaten mevcuttur ve öneri motorunda yeniden kullanılacaktır.

## Mimari Yaklaşım

Mevcut profil mimarisi genişletilir; rakip bir modül oluşturulmaz.

```
┌──────────────────────┐
│ ProfileSnapshot      │  geçmiş snapshot'lar
│ (mevcut)             │
└──────────┬───────────┘
           │  takvim sınıflandırıcı
           ▼
┌──────────────────────┐
│ CalendarClass        │  ORDINARY | MONTH_END | QUARTER_END |
│ (yeni, deterministik)│  YEAR_END | DAY_START | HOLIDAY_ADJACENT
└──────────┬───────────┘
           │  sınıf bazlı kuantil
           ▼
┌──────────────────────┐       ┌──────────────────────┐
│ ThresholdProposal    │──────▶│ Maker-checker onayı  │
│ (öneri + kanıt)      │       │ (mevcut akış)        │
└──────────────────────┘       └──────────┬───────────┘
                                          │ onaylanırsa
                                          ▼
                               ┌──────────────────────┐
                               │ ProfileAnalysisPolicy│
                               │ yeni sürüm           │
                               └──────────────────────┘
```

Kritik tasarım kararı: **eşik otomatik uygulanmaz.** Öneri, kanıtıyla
birlikte sunulur; yürürlüğe girmesi mevcut politika sürümleme ve onay
akışından geçer. Bu, FR-107'nin "politika yoksa otomatik strateji
değişmemelidir" kabul kriterini korur.

## Yapılacak Değişiklikler

### Backend

| Dosya | Değişiklik |
| --- | --- |
| `src/veri_kalitesi/data_sources/calendar.py` (yeni) | `CalendarClass` enum'u; `classify(occurred_at, calendar_policy) -> CalendarClass`. Takvim tanımı **dışarıdan** gelir (tatil listesi, mali dönem sonu); kod içi varsayılan takvim yoktur. |
| `src/veri_kalitesi/data_sources/models.py` | `CalendarPolicy` (sürüm, tatil günleri, mali dönem tanımı, sınıf tanımları); `ProfileAnalysisPolicy`'ye `calendar_policy_version: str \| None` ve `thresholds_by_calendar_class: Mapping[CalendarClass, ThresholdSet] \| None` alanları. Alanlar opsiyoneldir — mevcut skaler davranış varsayılan kalır. |
| `src/veri_kalitesi/data_sources/profiling.py` | `compare_profile_snapshots` karşılaştırma penceresini takvim sınıfına göre filtreler; sınıf eşiği tanımlıysa onu, değilse mevcut skaleri kullanır. Üretilen sinyale `calendar_class` ve `threshold_source` (`CLASS` \| `SCALAR`) alanları eklenir. |
| `src/veri_kalitesi/data_sources/threshold_proposals.py` (yeni) | `propose_thresholds(snapshots, *, calendar_policy, proposal_policy) -> ThresholdProposal`. Sınıf başına kuantil hesabı (`_quantile` yeniden kullanılır), minimum örnek sayısı kapısı, güven ve kapsama kanıtı. |
| `src/veri_kalitesi/data_sources/postgresql_repository.py` | Öneri kalıcılığı ve takvim politikası okuma. |
| `alembic/versions/2026xxxx_24_calendar_thresholds.py` (yeni) | `calendar_policies`, `threshold_proposals` tabloları; `profile_analysis_policies` üzerine takvim sürüm kolonu. |
| `src/veri_kalitesi/api/data_sources_router.py` | `GET /api/v1/datasets/{dataset_ref}/threshold-proposals`, `POST /api/v1/threshold-proposals/{id}/approval` |

### Frontend

| Dosya | Değişiklik |
| --- | --- |
| `frontend/src/catalog/DatasetDetailPage.tsx` | "Eşik Önerileri" bölümü: sınıf bazlı önerilen eşik, mevcut eşik, dayanak örnek sayısı, güven. |
| `frontend/src/catalog/model.ts`, `api.ts` | Öneri tipleri ve çağrıları. |
| Drift sinyali gösteren tüm görünümler | Sinyalin hangi takvim sınıfında ve hangi eşik kaynağıyla üretildiğini rozet olarak gösterir. |

## Takvim Sınıfları

| Sınıf | Tanım | Neden ayrı |
| --- | --- | --- |
| `ORDINARY` | Sıradan iş günü | Referans taban |
| `MONTH_END` | Mali ay sonu (takvim politikasından) | Hacim ve mutabakat yükü zirvesi |
| `QUARTER_END` | Çeyrek sonu | Raporlama yükü, ek tablo doluluğu |
| `YEAR_END` | Yıl sonu | Kapanış kayıtları, olağandışı hacim |
| `DAY_START` | Gün başı / batch öncesi pencere | Tablolar henüz dolmamış; freshness ve doluluk düşük |
| `HOLIDAY_ADJACENT` | Resmî tatil bitişiği | İşlem hacmi düşük, boşluk normaldir |

Sınıflandırma **deterministiktir** ve yalnız onaylı `CalendarPolicy`'den
türetilir. Politika yoksa tüm snapshot'lar `ORDINARY` sayılır ve sistem
mevcut skaler davranışını sürdürür.

## Kabul Kriterleri

- [ ] `CalendarPolicy` yokken davranış bugünküyle **birebir aynıdır**
      (regresyon testiyle kanıtlanır).
- [ ] Aynı girdi ve aynı politika sürümü aynı sınıflandırmayı ve aynı öneriyi
      üretir (determinizm testi).
- [ ] Sınıf başına örnek sayısı `minimum_history` altındaysa öneri
      üretilmez; `INSUFFICIENT_CLASS_HISTORY` reason code'u döner.
- [ ] Öneri hiçbir koşulda yürürlükteki politikayı otomatik değiştirmez.
- [ ] Onay akışı maker-checker'dır; öneren ile onaylayan aynı aktör olamaz.
- [ ] Üretilen drift sinyali `calendar_class` ve `threshold_source` taşır.
- [ ] Ay sonu senaryosunda hacim artışı `MONTH_END` eşiğiyle
      değerlendirildiğinde sinyal üretmez; aynı artış `ORDINARY` gününde
      sinyal üretir.
- [ ] Öneri kabulü/reddi audit'e yazılır.

## Eklenen Testler

| Test | Kapsam |
| --- | --- |
| `test_calendar_policy_absent_preserves_scalar_behaviour` | Geri uyumluluk |
| `test_classification_is_deterministic_for_policy_version` | Determinizm |
| `test_month_end_volume_spike_suppressed_with_class_threshold` | Ana senaryo |
| `test_same_spike_on_ordinary_day_raises_signal` | Yanlış bastırma yok |
| `test_insufficient_class_history_blocks_proposal` | Yetersiz veri kapısı |
| `test_proposal_never_mutates_active_policy` | Otomatik kayma yok |
| `test_maker_cannot_approve_own_proposal` | Görevler ayrılığı |
| `test_signal_carries_calendar_class_and_threshold_source` | Kanıt taşıma |

## Kalan Risk

- Takvim politikası (tatil listesi, mali dönem tanımı) kurumsal bir girdidir;
  yanlış takvim yanlış bastırma üretir. Politika sürümü her sinyalde
  taşınmalı ve denetlenebilir olmalıdır.
- Sınıf bazlı eşik, sınıf içi örnek sayısı azken oynaktır. `YEAR_END` sınıfı
  yılda bir örnek üretir; bu sınıf için öneri pratikte birkaç yıl veri
  birikene kadar `INSUFFICIENT_CLASS_HISTORY` kalacaktır. Bu kabul edilen
  davranıştır.
- Takvim farkındalığı gerçek bozulmayı maskeleme riski taşır: ay sonunda
  gerçekten bozulan veri, geniş `MONTH_END` eşiği yüzünden görünmeyebilir.
  Azaltım: sınıf eşiği hiçbir zaman skaler eşiğin bir üst sınır katsayısını
  aşamaz; katsayı politikada tanımlıdır.

## Geri Alma Yaklaşımı

- `CalendarPolicy` kayıtları pasifleştirilir; sistem skaler eşik davranışına
  döner. Kod geri alımı gerekmez.
- Tam geri alım için `profiling.py` içindeki sınıf filtresi kaldırılır ve
  migration `downgrade` ile yeni tablolar düşürülür.

## Sınır

Bu doküman planlama kaydıdır. Kalibrasyon, gerçek banka takvimi ve üretim
hacmiyle doğrulama gerektirir; `ApprovedByBank` iddiası değildir.

## Sonraki İterasyon

[İterasyon 41 — Profil Tabanlı Kural Önerisi ve Shadow Backfill](Iterasyon-41-Profil-Tabanli-Kural-Onerisi-ve-Shadow-Backfill.md)

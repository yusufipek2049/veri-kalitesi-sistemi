---
iteration: 41
status: planned
completed_at: null
decision_reference: USER-DECLARATION-2026-08-CAPABILITY-UPLIFT
---

# İterasyon 41 — Profil Tabanlı Kural Önerisi ve Shadow Backfill

## Amaç

Kural yazmak bugün tamamen elle yapılır. Uzman tabloyu tanımak, eşiği tahmin
etmek ve kuralın üretimde ne kadar gürültü üreteceğini bilmeden onaya
göndermek zorundadır. Bu belirsizlik kural sayısını düşük tutar; düşük kural
sayısı kapsama boşluğu demektir.

Bu iterasyon iki şey ekler:

1. **Kural önerisi** — mevcut profil metriklerinden aday kural üretimi.
2. **Shadow backfill** — aday kuralın geçmiş veriye karşı çalıştırılıp
   "aktif olsaydı ne olurdu" kanıtının üretilmesi.

## Kullanıcı / Sistem Değeri

- Uzman boş ekrandan başlamaz; profilin işaret ettiği aday kuralları görür.
- Kuralı onaya göndermeden önce "son 6 ayda kaç issue açardı, kaç yalancı
  alarm üretirdi" sayısı elindedir.
- Kural ekleme korkusu ortadan kalktığı için kapsama artar.

## Mevcut FR/UC/RULE

| Kod | Ad |
| --- | --- |
| FR-016–FR-019 | Profilleme metrikleri, dağılım/desen, tekrarlı kayıt, aykırı değer |
| FR-023 | Hazır kural şablonları |
| FR-027 | Eşik, ağırlık ve kritiklik tanımlama |
| FR-031 | Kural test çalıştırması |
| FR-035 | Kural onay akışı |
| FR-106 | Veri sözleşmesi yaşam döngüsü |
| FR-109 | Kalite borcu yönetimi |

## Mevcut Durum Analizi

Gerekli altyapının büyük kısmı hazırdır:

| Yetenek | Konum | Durum |
| --- | --- | --- |
| 11 kural şablonu ve IR plan üretimi | [`rules/templates.py:19`](../../src/veri_kalitesi/rules/templates.py) `build_rule_plan` | Hazır |
| `OFFICIAL` / `SHADOW` yürütme modu | [`executions/models.py:22`](../../src/veri_kalitesi/executions/models.py) `ExecutionMode` | Hazır — SHADOW sonuçları resmî skor/bildirim/SLA dışında |
| Profil sözleşmesi üretimi | [`profiling.py:274`](../../src/veri_kalitesi/data_sources/profiling.py) `build_profile_contract` | Hazır |
| Gelişmiş alan metrikleri | [`profiling.py:188`](../../src/veri_kalitesi/data_sources/profiling.py) `build_advanced_field_metrics` | Hazır |
| Tip/format çıkarımı | [`profiling.py:149`](../../src/veri_kalitesi/data_sources/profiling.py) `infer_value_type`, `infer_format` | Hazır |
| Watermark/checkpoint ile artımlı yürütme | [`executions/strategy_engine.py:117`](../../src/veri_kalitesi/executions/strategy_engine.py) `ExecutionStrategyEngine` | Hazır — backfill penceresi için yeniden kullanılacak |

Eksik olan yalnız iki köprüdür: profil → aday kural, ve aday kural → geçmiş
pencere üzerinde SHADOW yürütme.

## Mimari Yaklaşım

```
┌──────────────────┐
│ DataProfile      │  mevcut profil metrikleri
│ + advanced       │
└────────┬─────────┘
         │ RuleCandidateGenerator (yeni, deterministik)
         ▼
┌──────────────────┐
│ RuleCandidate    │  rule_type + parameters + confidence + evidence
│ status=PROPOSED  │  (henüz RuleVersion değil)
└────────┬─────────┘
         │ backfill talebi
         ▼
┌──────────────────┐   mevcut ExecutionMode.SHADOW
│ Backfill job     │──▶ geçmiş pencere üzerinde çalıştırma
│ (yeni iş tipi)   │    resmî skor/bildirim/SLA'ya dokunmaz
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ BackfillReport   │  ihlal sayısı, dönem dağılımı, tahmini issue sayısı
└────────┬─────────┘
         │ uzman kabul ederse
         ▼
   mevcut kural oluşturma + FR-035 onay akışı
```

Kritik tasarım kararı: `RuleCandidate` bir `RuleVersion` **değildir.**
Aday kural, kural envanterine girmez, skorlamaya katılmaz, kural sayacı
şişirmez. Yalnız kabul edildiğinde mevcut `POST /api/v1/rules` akışına
dönüştürülür ve normal maker-checker onayından geçer.

## Aday Kural Üretim Kuralları

Üretim **deterministiktir**; istatistiksel çıkarım yapılır, model
çalıştırılmaz.

| Profil gözlemi | Önerilen kural | Güven belirleyicisi |
| --- | --- | --- |
| `null_ratio == 0` ve örnek sayısı yeterli | `REQUIRED` | Gözlem penceresi uzunluğu |
| `distinct_ratio == 1.0` | `UNIQUE` | Satır sayısı |
| Sayısal alanda kararlı min/max | `RANGE` | Kuantil kararlılığı |
| `infer_format` tek desende yakınsıyor | `FORMAT_CHECK` veya `REGEX` | Desen kapsama oranı |
| Düşük kardinalite, kararlı kategori kümesi | `ALLOWED_VALUES` | Kategori kümesi kararlılığı |
| Uzunluk dağılımı dar | `LENGTH_CHECK` | Uzunluk varyansı |
| Zaman alanında düzenli tazelenme | `FRESHNESS` | Gecikme dağılımının kuyruğu |
| Kolon adı/tip eşleşmesi ile FK adayı | `REFERENTIAL_INTEGRITY` | Eşleşme oranı |

Her aday `evidence` alanı taşır: dayanak metrik, gözlem penceresi, örnek
sayısı ve — [İterasyon 40](Iterasyon-40-Takvim-Farkindalikli-Esik-Onerisi.md)
uygulanmışsa — takvim sınıfı kapsaması.

`CUSTOM_SQL` ve `CROSS_TABLE_CONSISTENCY` aday üretimine **dahil değildir**;
bu türler iş anlamı gerektirir ve profilden türetilemez.

## Yapılacak Değişiklikler

### Backend

| Dosya | Değişiklik |
| --- | --- |
| `src/veri_kalitesi/rules/candidates.py` (yeni) | `RuleCandidate`, `CandidatePolicy`, `generate_candidates(profile, *, policy) -> tuple[RuleCandidate, ...]`. Politika yoksa aday üretilmez (fail-closed). |
| `src/veri_kalitesi/rules/models.py` | `RuleCandidateStatus` (`PROPOSED` / `BACKFILLED` / `ACCEPTED` / `REJECTED`); aday kabul edildiğinde oluşan `RuleVersion`'a `origin_candidate_id` izi. |
| `src/veri_kalitesi/executions/backfill.py` (yeni) | `BackfillRequest`, `BackfillReport`. Geçmiş pencereyi `ExecutionStrategyEngine` watermark sözleşmesi üzerinden böler; her dilimi `ExecutionMode.SHADOW` ile yürütür. |
| `src/veri_kalitesi/jobs/` | `RULE_BACKFILL` iş tipi; kaynak kullanım kotası mevcut `source_usage_policies` kapısından geçer. |
| `src/veri_kalitesi/rules/postgresql_repository.py` | Aday ve backfill raporu kalıcılığı. |
| `alembic/versions/2026xxxx_25_rule_candidates.py` (yeni) | `rule_candidates`, `backfill_reports` tabloları. |
| `src/veri_kalitesi/api/rules_router.py` | `GET /api/v1/datasets/{dataset_ref}/rule-candidates`, `POST /api/v1/rule-candidates/{id}/backfill`, `GET /api/v1/rule-candidates/{id}/backfill-report`, `POST /api/v1/rule-candidates/{id}/acceptance` |

### Frontend

| Dosya | Değişiklik |
| --- | --- |
| `frontend/src/catalog/DatasetDetailPage.tsx` | "Önerilen Kurallar" bölümü; aday listesi, güven rozeti, dayanak metrik. |
| `frontend/src/rules/RulesPage.tsx` | Aday kabul akışı; kabul mevcut kural oluşturma dialoguna önceden doldurulmuş olarak akar. |
| `frontend/src/rules/BackfillReportPanel.tsx` (yeni) | Backfill sonucu: dönem bazlı ihlal grafiği, tahmini issue sayısı, en çok ihlal üreten dönem. |
| `frontend/src/rules/model.ts`, `api.ts` | Aday ve backfill tipleri/çağrıları. |

## Kabul Kriterleri

- [ ] `CandidatePolicy` yokken hiç aday üretilmez; sessiz varsayılan yoktur.
- [ ] Aynı profil ve aynı politika sürümü aynı aday kümesini üretir
      (determinizm testi).
- [ ] `RuleCandidate` kural envanterinde görünmez, skorlamaya katılmaz,
      kural sayacına dahil olmaz.
- [ ] Backfill yürütmeleri **tamamı** `ExecutionMode.SHADOW`'dur; resmî skor,
      bildirim, SLA ve otomatik issue üretimi tetiklenmez (negatif testle
      kanıtlanır).
- [ ] Backfill kaynak kullanım kotasına tabidir; kota reddi işi
      `REJECTED_BY_QUOTA` ile sonlandırır, kaynağı zorlamaz.
- [ ] Backfill raporu dönem bazlı ihlal sayısı ve tahmini issue sayısı taşır.
- [ ] Aday kabulü yeni bir `RuleVersion` üretir ve **mevcut FR-035 onay
      akışına** girer; onayı atlamaz.
- [ ] `CUSTOM_SQL` ve `CROSS_TABLE_CONSISTENCY` aday olarak üretilmez.
- [ ] Aday üretimi, backfill ve kabul/ret audit'e yazılır.

## Eklenen Testler

| Test | Kapsam |
| --- | --- |
| `test_no_policy_produces_no_candidates` | Fail-closed |
| `test_candidate_generation_is_deterministic` | Determinizm |
| `test_candidate_absent_from_rule_inventory` | İzolasyon |
| `test_backfill_runs_are_all_shadow_mode` | Mod izolasyonu |
| `test_backfill_emits_no_notification_or_issue` | Negatif test |
| `test_backfill_respects_source_usage_quota` | Kaynak koruması |
| `test_accepted_candidate_enters_approval_flow` | Onay atlanmaz |
| `test_custom_sql_never_proposed` | Kapsam sınırı |
| `test_backfill_report_period_breakdown` | Rapor içeriği |

## Kalan Risk

- Backfill geçmiş veriye erişim gerektirir. Kaynak sistemde partition
  saklama süresi kısa ise pencere daralır; rapor kapsama oranını açıkça
  bildirmelidir, eksik pencereyi "temiz" saymamalıdır.
- Backfill okuma yükü üretir. Salt okunur erişim korunur ancak kaynak
  sistemde yük penceresi banka operasyonuyla anlaşılmalıdır. Kota kapısı
  zorunludur.
- Aday kural üretimi geçmiş veriyi "doğru" varsayar. Geçmişte de bozuk olan
  bir alan için `REQUIRED` önerilmez — bu doğru davranıştır ama kapsama
  boşluğu olarak kalır; FR-109 kalite borcu kaydı ile izlenmelidir.
- Güven skoru istatistiksel bir göstergedir, garanti değildir. Ekranda
  "öneri" dili korunmalı, "tespit" dili kullanılmamalıdır.

## Geri Alma Yaklaşımı

- Aday üretimi `CandidatePolicy` pasifleştirilerek durdurulur; kod geri
  alımı gerekmez.
- `RULE_BACKFILL` iş tipi kuyruktan çıkarılır; devam eden işler mevcut iptal
  akışıyla sonlandırılır.
- Kabul edilmiş adaylardan doğan `RuleVersion` kayıtları standart kural
  pasifleştirme ile devre dışı bırakılır; `origin_candidate_id` izi sayesinde
  toplu tespit edilebilir.
- Migration `downgrade` ile aday tabloları düşürülür; üretilmiş kurallar
  etkilenmez.

## Sınır

Bu doküman planlama kaydıdır. Gerçek kaynak sistem hacmi, saklama penceresi
ve operasyon yük anlaşması ayrıca doğrulanmalıdır; `ApprovedByBank` iddiası
değildir.

## Sonraki İterasyon

[İterasyon 42 — Sentetik Veriyle Kural Kanıtı](Iterasyon-42-Sentetik-Veriyle-Kural-Kaniti.md)

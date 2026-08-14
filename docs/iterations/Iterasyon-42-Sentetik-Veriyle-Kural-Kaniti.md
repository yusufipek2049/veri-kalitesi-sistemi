---
iteration: 42
status: planned
completed_at: null
decision_reference: USER-DECLARATION-2026-08-CAPABILITY-UPLIFT
---

# İterasyon 42 — Sentetik Veriyle Kural Kanıtı

## Amaç

Denetçinin "kuralınız gerçekten çalışıyor mu?" sorusunun bugün mekanik bir
cevabı yoktur. Kural test çalıştırması (FR-031) kuralın **hata vermeden
çalıştığını** gösterir; yakalaması gereken hatayı **yakaladığını**
göstermez. İkisi farklı iddialardır.

Bu iterasyon, her kural sürümü için kontrollü kusur enjeksiyonuyla üretilmiş
sentetik veri üzerinde bir **etkinlik kanıtı** (`RuleEffectivenessProof`)
üretir: kural, iddia ettiği kusuru yakaladı mı, geçerli uç değerleri yanlışlıkla
işaretledi mi.

## Kullanıcı / Sistem Değeri

- Her kural sürümü, ne yakaladığının ve ne yakalamadığının kanıtıyla birlikte
  yaşar.
- Denetim sorusu insan beyanıyla değil, yeniden üretilebilir kanıtla yanıtlanır.
- Kural değişikliği etkinliği düşürüyorsa onay öncesinde görünür.

## Mevcut FR/UC/RULE

| Kod | Ad |
| --- | --- |
| FR-088 | Politika kontrollü sentetik üretim |
| FR-089 | Şema, kısıt ve iş anlamı üretimi |
| FR-091 | Kontrollü kusur enjeksiyonu ve geçerli uç ayrımı |
| FR-092 | Bağımsız ground truth ve sonuç karşılaştırması |
| FR-093 | Deterministik üretim ve veri soy ağacı |
| FR-095 | Gizlilik değerlendirmesi ve ortam izolasyonu |
| FR-031 | Kural test çalıştırması |
| FR-035 | Kural onay akışı |

## Mevcut Durum Analizi

[`synthetic_data/`](../../src/veri_kalitesi/synthetic_data/) modülü on bir
dosya ve beş test dosyasıyla mevcuttur; hiçbir API route'u veya worker
handler'ı ona ulaşmaz.

| Sembol | Konum | Rolü |
| --- | --- | --- |
| `GoldenRelationalGenerator` | [generator.py:44](../../src/veri_kalitesi/synthetic_data/generator.py) | Deterministik ilişkisel üretim (`seed` tabanlı) |
| `GoldenStructuralOracle` | [oracle.py:47](../../src/veri_kalitesi/synthetic_data/oracle.py) | Bağımsız ground truth karşılaştırması |
| `DeterministicTemporalGenerator` | [temporal.py:32](../../src/veri_kalitesi/synthetic_data/temporal.py) | Zamansal gerçekçilik |
| `TemporalSemanticValidator` | [temporal.py:79](../../src/veri_kalitesi/synthetic_data/temporal.py) | Zamansal tutarlılık doğrulaması |
| `SyntheticGenerationRegistryService` | [service.py:30](../../src/veri_kalitesi/synthetic_data/service.py) | Politika/senaryo/koşu kaydı |
| `SyntheticRunFinalizationService` | [finalization.py:37](../../src/veri_kalitesi/synthetic_data/finalization.py) | Lineage ve kanonik bütünlük kapanışı |
| `authorize_synthetic_actor` | [authorization.py:22](../../src/veri_kalitesi/synthetic_data/authorization.py) | Aktör yetkilendirmesi |
| `SyntheticDatasetPolicy`, `SyntheticScenario`, `SyntheticGenerationRun` | [models.py](../../src/veri_kalitesi/synthetic_data/models.py) | Sürümlü politika ve koşu modeli |

Yani üretim, oracle, determinizm, yetkilendirme ve kapanış hazırdır. Eksik
olan tek şey **kural ile oracle arasındaki köprüdür**.

## Mimari Yaklaşım

```
┌────────────────────┐
│ RuleVersion        │  kanıtı üretilecek kural
│ (IR planı ile)     │
└─────────┬──────────┘
          │ kuralın türü ve parametreleri
          ▼
┌────────────────────┐
│ DefectScenario     │  kuralın yakalaması GEREKEN kusur +
│ (yeni, kuraldan    │  yakalamaMASI gereken geçerli uç
│  türetilir)        │
└─────────┬──────────┘
          │ mevcut SyntheticScenario'ya çevrilir
          ▼
┌────────────────────┐      ┌────────────────────┐
│ GoldenRelational   │─────▶│ İzole sentetik     │
│ Generator (mevcut) │      │ şema (üretim dışı) │
└────────────────────┘      └─────────┬──────────┘
                                      │ ExecutionMode.SHADOW
                                      ▼
┌────────────────────┐      ┌────────────────────┐
│ GoldenStructural   │◀─────│ Kural yürütme      │
│ Oracle (mevcut)    │      │ sonucu             │
└─────────┬──────────┘      └────────────────────┘
          │ karşılaştırma
          ▼
┌────────────────────────────────────────────┐
│ RuleEffectivenessProof                     │
│ detection_rate / false_positive_rate /     │
│ uncovered_defect_codes / digest            │
└────────────────────────────────────────────┘
```

Kritik tasarım kararı: sentetik veri **üretim veri kaynağına asla
yazılmaz.** Üretim izole bir sentetik şemada yapılır; sistemin salt okunur
üretim erişimi sözleşmesi ([README](../../README.md)) korunur.

İkinci kritik karar: kanıt **kuralı geçersiz kılmaz.** Düşük etkinlik onay
akışında görünür bir uyarıdır; kuralı otomatik reddetmez. Ret kararı
insanındır (FR-035).

## Kusur Senaryosu Türetimi

Her kural türü için, yakalaması gereken kusur ve yakalamaması gereken
geçerli uç değer çifti tanımlanır:

| Kural türü | Enjekte edilen kusur | Geçerli uç (yakalanmamalı) |
| --- | --- | --- |
| `REQUIRED` | Null değer | Boş string (politika ayrımına göre) |
| `UNIQUE` | Yinelenen anahtar | Farklı ama benzer anahtar |
| `RANGE` | Sınır dışı değer | Tam sınır değeri |
| `REGEX` | Desen dışı değer | Sınırda geçerli desen |
| `ALLOWED_VALUES` | Küme dışı kategori | Kümenin en nadir üyesi |
| `LENGTH_CHECK` | Sınır aşan uzunluk | Tam sınır uzunluğu |
| `FORMAT_CHECK` | Bozuk format | Alternatif geçerli format |
| `FRESHNESS` | Eşiği aşan gecikme | Eşiğin hemen altındaki gecikme |
| `REFERENTIAL_INTEGRITY` | Yetim kayıt | Null FK (izinliyse) |
| `CROSS_TABLE_CONSISTENCY` | Tutarsız çapraz değer | Senaryodan türetilir |
| `CUSTOM_SQL` | Türetilemez | — |

`CUSTOM_SQL` için kusur senaryosu otomatik türetilemez; bu türde kanıt
yalnız kural sahibinin elle tanımladığı senaryo ile üretilir ve senaryo
yoksa `PROOF_UNAVAILABLE_CUSTOM_SQL` durumu kaydedilir. Bu, kanıtın
sessizce "başarılı" sayılmasını engeller.

## Yapılacak Değişiklikler

### Backend

| Dosya | Değişiklik |
| --- | --- |
| `src/veri_kalitesi/rules/effectiveness.py` (yeni) | `DefectScenario`, `RuleEffectivenessProof`, `derive_defect_scenarios(rule_version, *, policy)`. Politika yoksa senaryo üretilmez. |
| `src/veri_kalitesi/synthetic_data/rule_proof.py` (yeni) | `RuleProofService` — senaryoyu `SyntheticScenario`'ya çevirir, `GoldenRelationalGenerator` ile üretir, kuralı SHADOW modda yürütür, `GoldenStructuralOracle` ile karşılaştırır. |
| `src/veri_kalitesi/jobs/` | `RULE_EFFECTIVENESS_PROOF` iş tipi. |
| `src/veri_kalitesi/synthetic_data/repository.py` | Kanıt kalıcılığı; `rule_version_id` ↔ `proof` bağı. |
| `alembic/versions/2026xxxx_26_rule_effectiveness_proofs.py` (yeni) | `rule_effectiveness_proofs` tablosu; izole sentetik şema tanımı. |
| `src/veri_kalitesi/api/rules_router.py` | `POST /api/v1/rules/{rule_version_id}/effectiveness-proof`, `GET /api/v1/rules/{rule_version_id}/effectiveness-proof` |
| `src/veri_kalitesi/api/app.py`, `composition.py` | Servis kablolaması; `authorize_synthetic_actor` yetkilendirme zincirine bağlanır. |

### Frontend

| Dosya | Değişiklik |
| --- | --- |
| `frontend/src/rules/RulesPage.tsx` | Kural detayında "Etkinlik Kanıtı" bölümü; tespit oranı, yalancı pozitif oranı, kapsanmayan kusur kodları. |
| `frontend/src/rules/EffectivenessProofPanel.tsx` (yeni) | Kanıt görünümü; kanıtı olmayan kural açıkça "kanıtsız" etiketlenir. |
| Kural onay ekranı | Etkinlik kanıtı yoksa veya tespit oranı politika eşiğinin altındaysa onaylayana uyarı gösterilir (bloke etmez). |

## Kabul Kriterleri

- [ ] Sentetik veri **üretim veri kaynağına yazılmaz**; izole şema kullanılır
      (negatif testle kanıtlanır).
- [ ] Aynı `seed` ve aynı politika sürümü aynı sentetik veriyi ve aynı kanıtı
      üretir (determinizm testi).
- [ ] Kanıt, enjekte edilen kusurların hangilerinin yakalandığını
      **kusur kodu bazında** raporlar; toplam oran tek başına yeterli değildir.
- [ ] Geçerli uç değerler yakalanırsa `false_positive_rate` içinde raporlanır.
- [ ] Kural yürütmeleri `ExecutionMode.SHADOW`'dur; resmî skor, bildirim ve
      issue üretmez.
- [ ] Düşük etkinlik kuralı **otomatik reddetmez**; yalnız onay ekranında
      uyarı üretir.
- [ ] `CUSTOM_SQL` için elle senaryo yoksa `PROOF_UNAVAILABLE_CUSTOM_SQL`
      kaydedilir; kanıt "başarılı" sayılmaz.
- [ ] Sentetik koşu `SyntheticRunFinalizationService` üzerinden kapatılır;
      lineage ve kanonik bütünlük doğrulanır.
- [ ] Yetkisiz aktör sentetik koşu başlatamaz; `authorize_synthetic_actor`
      kapısı zorunludur.
- [ ] Kanıt üretimi audit'e yazılır; `digest` alanı yeniden hesaplanabilir.

## Eklenen Testler

| Test | Kapsam |
| --- | --- |
| `test_synthetic_data_never_written_to_production_source` | İzolasyon (kritik) |
| `test_proof_is_deterministic_for_seed_and_policy` | Determinizm |
| `test_proof_reports_uncovered_defect_codes` | Kusur bazlı raporlama |
| `test_valid_edge_values_counted_as_false_positive` | Geçerli uç ayrımı |
| `test_proof_runs_are_shadow_mode_only` | Mod izolasyonu |
| `test_low_effectiveness_does_not_auto_reject_rule` | Karar insanındır |
| `test_custom_sql_without_scenario_marks_proof_unavailable` | Sessiz başarı yok |
| `test_unauthorized_actor_cannot_start_synthetic_run` | Yetkilendirme |
| `test_finalization_validates_lineage_and_canonical_integrity` | Kapanış |

## Kalan Risk

- Sentetik veri gerçek veriyi temsil etmez. Kanıt, kuralın **tanımlanmış
  kusuru** yakaladığını gösterir; üretimde karşılaşılacak tüm kusurları
  yakalayacağını göstermez. Ekran ve rapor dili bu sınırı açıkça taşımalıdır.
- Kusur senaryosu üretimi kural türünden türetilir; kuralın iş anlamını
  bilmez. `RANGE` kuralı için sınır dışı değer üretmek kolaydır, iş anlamı
  olarak "yanlış ama sınır içi" değer üretmek değildir.
- İzole sentetik şema, üretim şemasıyla eşleşmezse kanıt geçersizleşir. Şema
  sürümü kanıtta taşınmalı, uyuşmazlıkta kanıt bayatlamış sayılmalıdır.
- FR-095 gizlilik değerlendirmesi: sentetik üretim gerçek veriden
  türetilmemelidir. Bu iterasyon yalnız politika/şema tabanlı üretim kullanır;
  gerçek kayıt örneklemesi kapsam dışıdır.

## Geri Alma Yaklaşımı

- `RULE_EFFECTIVENESS_PROOF` iş tipi kuyruktan çıkarılır; devam eden işler
  mevcut iptal akışıyla sonlandırılır.
- Route'lar `rules_router.py`'den, servis `composition.py`'den kaldırılır.
- İzole sentetik şema düşürülür; üretim şeması etkilenmez.
- Kanıt kayıtları migration `downgrade` ile düşürülür; `RuleVersion`
  kayıtları değişmez.

## Sınır

Bu doküman planlama kaydıdır. Sentetik veri gerçekçiliği, gizlilik
değerlendirmesi ve ortam izolasyonu banka bilgi güvenliği kararıyla
doğrulanmalıdır; `ApprovedByBank` iddiası değildir.

## Sonraki İterasyon

[İterasyon 43 — Regülasyon Eşlemesi ve Uyum Raporu](Iterasyon-43-Regulasyon-Eslemesi-ve-Uyum-Raporu.md)

---
iteration: 39A-39C
status: planned
completed_at: null
decision_reference: USER-DECLARATION-2026-08-CAPABILITY-UPLIFT
---

# İterasyon 39A–39C — Kanıt Yüzeyi Kablolaması

## Amaç

Domain kodu ve birim testleri mevcut olan üç yetenek (etki/kök neden, skor
yeniden üretimi, raporlama) hiçbir runtime yüzeyinden erişilebilir değildir.
Bu iterasyon grubu, yeni domain mantığı yazmadan bu üç yeteneği API ve
frontend'e taşır.

### Ön tespit — `known-gaps.md` güncel değildir

Kod tabanı 2026-08-13 tarihinde doğrulandığında
[`documentation/known-gaps.md`](../../documentation/known-gaps.md) ile
gerçek durum arasında üç sapma bulunmuştur:

| `known-gaps.md` iddiası | Doğrulanan durum |
| --- | --- |
| `GET /api/v1/dashboard/summary` 503 döner | Route adı `/api/v1/dashboard/overview`'dur ve **bağlıdır**; `DashboardQueryService` [composition.py:482](../../src/veri_kalitesi/api/composition.py) içinde kurulur, [composition.py:538](../../src/veri_kalitesi/api/composition.py) içinde geçirilir |
| Rapor route'ları kayıtlı ama servis `None` | `/api/v1/reports/*` route'ları **hiç kayıtlı değildir**; `register_reports_routes` benzeri bir fonksiyon yoktur |
| Reproduction / profile-comparison / lineage route'ları kayıtlı ama servis `None` | Bu route string'leri `src/` altında hiç geçmemektedir |

`create_dashboard_api` imzası ([app.py:136](../../src/veri_kalitesi/api/app.py))
`score_publication_service`, rapor servisleri ve lineage reader'ları için
parametre taşımaz. Dolayısıyla iş "`None` değerini doldurmak" değil,
**HTTP yüzeyini kurmak ve kompozisyon kökünden bağlamaktır**.

**39D olarak `known-gaps.md` bu iterasyon grubunun kapanışında yeniden
üretilmelidir.**

## Kullanıcı / Sistem Değeri

- Denetçi "bu skor neden bu değerde?" sorusunu sistem üzerinden, yeniden
  hesaplatarak yanıtlayabilir.
- Sorun listesi "500 kayıt" olmaktan çıkıp etki sırasına dizilir.
- Periyodik uyum raporları elle üretilmekten çıkar.

## Mevcut FR/UC/RULE

| Kod | Ad | İterasyon |
| --- | --- | --- |
| FR-098 | Skor bileşeni ve metrik kanıtı | 39B |
| FR-099 | Çalıştırma manifesti ve yeniden üretim | 39B |
| FR-100 | Kaynaklı etki değerlendirmesi | 39A |
| FR-102 | Lineage ve değişiklik olayı görünümü | 39A |
| FR-103 | Drift ve nedensellik sınıflı teşhis | 39A |
| FR-104 | Kanıtlı öneri | 39A |
| FR-072–FR-076 | Raporlama gereksinimleri | 39C |
| UC-018 | Yeniden üretim ve tarama stratejisi senaryosu | 39B |

---

## İterasyon 39A — Etki Değerlendirmesi ve Kök Neden Hipotezi

**Durum:** `Planned`

**Amaç:** [`lineage/impact.py`](../../src/veri_kalitesi/lineage/impact.py)
içindeki saf fonksiyonları issue yaşam döngüsüne bağlamak.

### Mevcut domain yüzeyi

| Sembol | Konum | İmza özeti |
| --- | --- | --- |
| `assess_impact` | [impact.py:132](../../src/veri_kalitesi/lineage/impact.py) | `(components, *, policy) -> dict` — bileşenleri `SOURCED`/`ESTIMATED`/`UNKNOWN` sınıflar, birim bazında ayrı toplar |
| `root_cause_hypothesis` | [impact.py:165](../../src/veri_kalitesi/lineage/impact.py) | `(*, subject_ref, timeline, lineage_snapshot, impact_assessment, recommendations, ...) -> dict` |
| `PostgreSQLLineageEvidenceRepository` | [postgresql_lineage.py:60](../../src/veri_kalitesi/lineage/postgresql_lineage.py) | Snapshot okuma |
| `PostgreSQLGovernanceProfileReader` | [postgresql_lineage.py:168](../../src/veri_kalitesi/lineage/postgresql_lineage.py) | Yönetişim profili okuma |

Her iki fonksiyon da **yalnız hipotez üretir**; kesin nedensellik iddia etmez
ve `MISSING_RECOMMENDATION_POLICY`, `NO_OBSERVED_DETERIORATION`,
`NO_LINEAGE_SNAPSHOT` gibi reason code'larla eksik girdiyi açıkça bildirir.
Bu davranış korunmalıdır.

### Yapılacak değişiklikler

**Backend**

1. `src/veri_kalitesi/lineage/service.py` (yeni) — `ImpactAssessmentService`:
   - `assess(issue_id, actor_context)` → issue'nun dataset referansından
     `ImpactComponent` listesi kurar, `assess_impact` çağırır.
   - `hypothesize(issue_id, actor_context)` → audit + execution + lineage
     olaylarından `TimelineEvent` dizisi kurar, `root_cause_hypothesis` çağırır.
   - Yetkilendirme mevcut `authorization_service` üzerinden; politika yoksa
     fail-closed.
2. `src/veri_kalitesi/api/lineage_router.py` (yeni) —
   `register_lineage_routes`:
   - `GET /api/v1/issues/{issue_id}/impact`
   - `GET /api/v1/issues/{issue_id}/root-cause`
   - `GET /api/v1/lineage/snapshots/{snapshot_id}`
   - `GET /api/v1/governance/{asset_ref}/projection`
3. `src/veri_kalitesi/api/app.py` — `create_dashboard_api` imzasına
   `impact_assessment_service`, `lineage_evidence_repository`,
   `governance_profile_reader` parametreleri; `register_lineage_routes` çağrısı.
4. `src/veri_kalitesi/api/composition.py` — repository ve servis örnekleri
   kurulur ve geçirilir.
5. `src/veri_kalitesi/api/models.py` — `ImpactAssessmentResponse`,
   `RootCauseHypothesisResponse` (reason code dizileri ve `digest` alanı dahil).
6. Politika ayarları — `ImpactSourcePolicy` ve `RecommendationPolicy`
   `ApplicationSettings` üzerinden sürümlü çözülür; kod içi varsayılan yoktur.

**Frontend**

7. `frontend/src/issues/model.ts` — etki/kök neden tipleri ve dönüşümleri.
8. `frontend/src/issues/api.ts` — `fetchIssueImpact`, `fetchIssueRootCause`.
9. `frontend/src/issues/IssuesPage.tsx` — sorun detayında "Etki" ve
   "Kök Neden Hipotezi" sekmeleri; `UNKNOWN` bileşenler ve reason code'lar
   gizlenmeden, gerekçesiyle gösterilir.
10. `frontend/src/issues/IssuesPage.stories.tsx` — `WithImpactAssessment` ve
    `WithIncompleteLineage` story'leri.

### Kabul kriterleri

- [ ] Politika yokken servis fail-closed davranır; sessizce varsayılan üretmez.
- [ ] `UNKNOWN` ve `ESTIMATED` bileşenler toplam değere karışmaz;
      `total_impact_reason_code` API yanıtında görünür.
- [ ] Eksik lineage snapshot durumunda ekran "yetersiz kanıt" durumunu
      açıkça gösterir, boş liste göstermez.
- [ ] Yetkisiz aktör 403 alır; erişim denemesi audit'e yazılır.
- [ ] `digest` alanı yanıtta taşınır ve yeniden hesaplanabilir.

---

## İterasyon 39B — Skor Yeniden Üretimi ve Kanıt Zinciri

**Durum:** `Planned`

**Amaç:** [`scoring/publication.py:201`](../../src/veri_kalitesi/scoring/publication.py)
içindeki `reproduce_score` metodunu denetçi erişimine açmak.

### Mevcut domain yüzeyi

`ScorePublicationService.reproduce_score(quality_score_id)` orijinal skoru
**değiştirmeden** yeniden hesaplar ve `ScoreReproductionResult` döner:
`matches`, `delta_value`, `delta_level` ve `reason_codes`
(`SCORE_VALUE_MISMATCH`, `LEVEL_MISMATCH`, `STATUS_MISMATCH`).

Kısıt: yalnız `rule_version_id` taşıyan kural seviyesi skorlar yeniden
üretilebilir; toplu (dataset/kaynak/kurum) skorlar için
`ScoringValidationError` yükseltilir.

### Yapılacak değişiklikler

**Backend**

1. `src/veri_kalitesi/api/scores_router.py` —
   `POST /api/v1/scores/{quality_score_id}/reproduction` route'u.
   - Yalnız `DATA_STEWARD` ve `AUDITOR` rolleri.
   - Yanıt: `matches`, `delta_value`, `delta_level`, `reason_codes`,
     yeniden üretilen skorun manifest alanları.
2. `src/veri_kalitesi/api/app.py` — `register_scores_routes` imzasına
   `score_publication_service` parametresi.
3. `src/veri_kalitesi/api/composition.py` — `ScorePublicationService`
   örneği kurulur ve geçirilir.
4. `src/veri_kalitesi/api/models.py` — `ScoreReproductionResponse`.
5. Toplu skorlar için `409` + `SCORE_NOT_DIRECTLY_REPRODUCIBLE` kodu;
   `500` değil.

**Frontend**

6. `frontend/src/scores/` — skor detayında "Yeniden Üret" aksiyonu;
   sonuç eşleşiyorsa yeşil doğrulama, eşleşmiyorsa delta ve reason code
   tablosu.
7. Toplu skorlarda buton görünmez; sebebi tooltip ile açıklanır.

### Kabul kriterleri

- [ ] Yeniden üretim orijinal `QualityScore` kaydını **değiştirmez**
      (regresyon testiyle kanıtlanır).
- [ ] Eşleşme durumunda `matches=true` ve boş `reason_codes` döner.
- [ ] Kural sürümü veya çalıştırma sonucu bulunamazsa `ScoreReproductionError`
      → `409`, teknik hata gövdesi sızmaz.
- [ ] Yeniden üretim talebi audit'e yazılır (aktör, skor id, sonuç).
- [ ] Toplu skorda `409` döner.

---

## İterasyon 39C — Raporlama Yüzeyi

**Durum:** `Planned`

**Amaç:** [`reporting/`](../../src/veri_kalitesi/reporting/) altındaki dokuz
modülü HTTP yüzeyine taşımak.

### Mevcut domain yüzeyi

`reporting/` içinde `service.py`, `scheduling.py`, `export.py`, `policies.py`,
`repository.py`, `worker.py` mevcuttur. Development kompozisyonunda
`report_tables` ve `_create_development_report_repository`
([development_composition.py:146](../../src/veri_kalitesi/api/development_composition.py))
zaten kullanılmaktadır — yani şema tarafı hazırdır, eksik olan production
kablolamasıdır.

### Yapılacak değişiklikler

1. `src/veri_kalitesi/api/reports_router.py` (yeni) —
   `register_reports_routes`:
   - `POST /api/v1/reports` — üretim talebi (asenkron iş kuyruğuna girer)
   - `GET /api/v1/reports` / `GET /api/v1/reports/{id}` — durum ve metadata
   - `GET /api/v1/reports/{id}/content` — imzalı, süreli indirme
   - `GET|POST /api/v1/report-schedules` — zamanlama yönetimi
2. `src/veri_kalitesi/jobs/` — `REPORT_GENERATION` iş tipi;
   `reporting/worker.py` handler olarak kaydedilir.
3. `src/veri_kalitesi/api/app.py` ve `composition.py` — servis kablolaması.
4. `frontend/src/reports/` (yeni dizin) — rapor listesi, üretim dialogu,
   zamanlama ekranı, indirme aksiyonu.
5. `frontend/src/components/AppShell.tsx` — "Raporlar" navigasyon girdisi.

### Kabul kriterleri

- [ ] Rapor üretimi API isteğini bloke etmez; iş kuyruğu üzerinden yürür.
- [ ] İndirme bağlantısı süreli ve aktöre bağlıdır; süresi geçen bağlantı
      `410` döner.
- [ ] Rapor içeriği aktörün yetki kapsamının dışındaki veri kaynaklarını
      içermez (negatif testle kanıtlanır).
- [ ] Üretim ve indirme olayları audit'e yazılır.
- [ ] Zamanlanmış rapor başarısızlığı bildirim üretir, sessizce düşmez.

---

## İterasyon 39D — `known-gaps.md` Yeniden Üretimi

**Durum:** `Planned`

39A–39C kapandıktan sonra
[`documentation/known-gaps.md`](../../documentation/known-gaps.md) kompozisyon
kökünden **otomatik** doğrulanacak biçimde yeniden üretilir.

- `scripts/` altına route ↔ servis kablolama denetleyicisi eklenir; kayıtlı
  her route için backing servisin `None` olmadığı doğrulanır.
- CI'da blocking iş olarak çalışır; doküman ile kod arasındaki sapma
  tekrarlanmaz.

### Kabul kriterleri

- [ ] Denetleyici, dokümanda geçen ama kayıtlı olmayan route'u hata olarak
      raporlar.
- [ ] `documentation/known-gaps.md` doğrulanmış çıktıdan üretilir.

## Eklenen Testler

| Alan | Test |
| --- | --- |
| 39A | Politika yokluğunda fail-closed; `UNKNOWN` bileşen toplama karışmaz; yetkisiz erişim 403 + audit |
| 39A | Eksik lineage snapshot'ta `NO_LINEAGE_SNAPSHOT` reason code'u yanıtta görünür |
| 39B | Yeniden üretim orijinal kaydı değiştirmez; toplu skor 409; audit yazımı |
| 39C | Yetki kapsamı dışı veri rapora sızmaz; süresi geçmiş indirme 410 |
| 39D | Kablolanmamış route CI'da hata üretir |

## Kalan Risk

- `ImpactSourcePolicy` ve `RecommendationPolicy` kalibrasyonu bankanın
  onaylı politika setine bağlıdır; kalibre edilmemiş politika ile üretilen
  etki değerlendirmesi karar desteği olarak kullanılmamalıdır.
- Rapor içeriği veri sınıflandırma envanterine
  ([17.05](../srs/17-Bankacilik-Uyum/17.05-Veri-Siniflandirma-ve-Isleme-Envanteri.md))
  göre maskeleme gerektirebilir; bu iterasyon maskeleme politikası üretmez.
- Yeniden üretim yalnız kural seviyesi skorları kapsar; toplu skor
  yeniden üretimi ayrı bir iterasyondur.

## Geri Alma Yaklaşımı

Her alt iterasyon bağımsız geri alınabilir: ilgili `register_*_routes`
çağrısı `app.py`'den, servis örneği `composition.py`'den kaldırılır.
Domain modülleri dokunulmadığı için geri alma veri kaybı üretmez.
Migration eklenmediğinden şema geri alımı gerekmez.

## Sınır

Bu doküman planlama kaydıdır. Production ölçek/yük kanıtı, kurumsal politika
kalibrasyonu ve banka onayı üretmez; `ApprovedByBank` iddiası değildir.

## Sonraki İterasyon

[İterasyon 40 — Takvim Farkındalıklı Eşik Önerisi](Iterasyon-40-Takvim-Farkindalikli-Esik-Onerisi.md)

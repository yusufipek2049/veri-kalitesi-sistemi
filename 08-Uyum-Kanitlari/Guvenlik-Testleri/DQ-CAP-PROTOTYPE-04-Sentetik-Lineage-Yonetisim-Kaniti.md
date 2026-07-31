---
type: technical-evidence
status: PrototypeVerified
compliance_status: ComplianceReviewRequired
data_origin: SYNTHETIC
environment: LOCAL
control_ids:
  - FR-100
  - FR-101
  - FR-102
  - FR-009
  - FR-010
  - DQ-CAP-007
  - DQ-CAP-010
version: DQ_CAP_PROTOTYPE_04
date: 2026-07-31
producer_role: Qoder
---

# DQ-CAP-PROTOTYPE-04 Sentetik Lineage ve Yönetişim Profili Kanıtı

## Kapsam

- Backend: `lineage/` domain modülü (OpenLineage uyumlu sürümlü olay, sürümlü
  yönetişim profili ve etkinlik aralığı, kaynaklı etki bileşenleri, kök neden
  hipotezi, öneri mekanizma filtresi), `PostgreSQLLineageEvidenceRepository`
  (değişmez snapshot + aynı transaction audit outbox) ve
  `PostgreSQLGovernanceProfileReader` (snapshot → profil deserialization).
- API: `api/app.py` salt okunur `GET /api/v1/lineage/snapshots/{id}` ve
  `GET /api/v1/governance/{asset_ref}/projection` uçları; `api/development.py`
  composition root'unda `governance_reader` ve `lineage_evidence_repository`
  bağlantısı (kanıt yoksa 503 fail-closed).
- Veri: yalnız sentetik registry ve sentetik lineage olayları; migration
  `20260730_14` (`lineage_evidence_snapshots`).

## Sonuç

- Yönetişim profili etkinlik aralığıyla sürümlenir; canonical digest ile değişmez
  snapshot'a yazılır. Zorunlu routing alanı yoksa atama fail-closed
  (`NO_ACTIVE_GOVERNANCE_PROFILE`) olur.
- Mevcut sahiplik alanları (`data_sources`, `data_protection/inventory`,
  `retention`) referanslanır, kopyalanmaz; çelişen ikinci sahip kaydı üretilmez.
- Lineage olayı OpenLineage uyumlu ve W3C PROV'ye eşlenebilir; eksik/eski
  kapsama durumu (`coverage_status`, freshness) snapshot'ta saklanır.
- Etki bileşenleri `Observed`/`Calculated`/`Estimated`/`Unknown` + kaynak/formül/
  veri zamanı/güven taşır; desteklenmeyenler tek toplam etkide birleştirilmez.
- Kök neden çıktısı hipotezdir; korelasyon doğrulanmış neden olarak sunulmaz ve
  insan `root_cause` kaydını ezmez.
- Öneriler yalnız `DeterministicRule`/`IncidentSimilarity`/auditli `ExpertInput`
  (`LLMAssisted` kapalı); minimum kanıt, mekanizma sürümü, bağımsız güven ve
  karşı kanıt zorunludur. `IncidentSimilarity` karşı kanıt yoksa
  `MISSING_COUNTER_EVIDENCE`, `ExpertInput` audit referansı yoksa
  `MISSING_AUDIT_REFERENCE` ile reddedilir.
- Kritik asset/risk/SLA durumu kanıt varsa profilden beslenir, yoksa `UNKNOWN`
  kalır; salt okunur uçlar kanıt yokluğu güvenli 503 üretir.

## Doğrulama

- Komut: `python3 -m pytest -q 06-Testler/01-Birim`
  Ortam: yerel, sentetik. Beklenen: exit 0. Gerçekleşen: `1276 passed`.
- Komut: `npx vitest run src/dashboard/model.test.ts`
  Ortam: yerel (Node v24). Gerçekleşen: `8 passed`.
- Komut: `DATA_QUALITY_POSTGRES_TEST_URL=... python3 -m pytest -q
  06-Testler/02-Entegrasyon/test_postgresql_lineage_evidence.py`
  Ortam: test PostgreSQL şeması. Gerçekleşen: skipsiz `3 passed`.
- Komut: tam entegrasyon paketi (`DATA_QUALITY_POSTGRES_TEST_URL` +
  `SYNTHETIC_POSTGRES_TEST=1`). Gerçekleşen: skipsiz `92 passed`.
- Komut: `python3 -m compileall` (lineage, api, migration). Gerçekleşen: exit 0.
- Sonuç: PASS (prototip; production readiness/banka onayı değildir).

## Güvenlik ve Sınırlar

- Snapshot, fixture, log ve hata yüzeylerinde gerçek banka/müşteri verisi,
  secret, token veya hassas veri yoktur; veri seti tümüyle sentetiktir.
- Eklenen uçlar salt okunurdur; kaynak sistemine veya kanıt kayıtlarına
  değiştirici çağrı yapmaz, `Cache-Control: no-store` taşır.
- Kritik yazım audit/outbox ile atomiktir; politika veya kanıt eksikse güvenli
  olumlu sonuç üretilmez (fail-closed).
- Kurumsal veri kataloğu, gerçek lineage kaynağı, Finans/Risk otoriter etki
  kaynağı ve banka onayı `ExternalDependency` olarak açık kalır.
- `api/app.py` önceden bulunan modül seviyesi F821 ruff bulguları görev kapsamı
  dışındadır (HEAD'de aynı küme); yeni eşik, ağırlık veya iş kuralı uydurulmaz,
  kaynağı olmayan alan `UNKNOWN` kalır.

## Onaylar

- Teknik doğrulayan: Qoder (uygulayıcı/testçi)
- Bilgi güvenliği: `ComplianceReviewRequired`
- İç kontrol: `ComplianceReviewRequired`
- Hukuk/uyum: `ComplianceReviewRequired`
- İş sahibi: `ComplianceReviewRequired`

Onay yoksa `ComplianceReviewRequired` yazılır. Reviewer (Claude) onayı bu
kanıtın production uygunluğu değil, prototip doğrulama adımıdır.

---
type: iteration-record
status: PrototypeVerified
work_package: DQ-CAP-PROTOTYPE-04
completed_at: 2026-07-31
---

# DQ-CAP-PROTOTYPE-04 — Sentetik Lineage, Sahiplik Profili ve Kaynaklı Etki Hipotezi

## Sonuç

`DQ-CAP-007` (lineage, kök neden ve etki) ile `DQ-CAP-010` (sahiplik ve
yönetişim) prototip kararları yeni `lineage/` domain modülü ve mevcut scoring/
dashboard mimarisi genişletilerek uygulandı. Sonuç yalnız yerel/sentetik
prototip kanıtıdır; production readiness veya `ApprovedByBank` değildir.

- Sürümlü `DataAssetGovernanceProfile` etkinlik aralığıyla üretilir; canonical
  digest ile değişmez snapshot'a yazılır. Zorunlu routing alanı yoksa otomatik
  atama fail-closed (`NO_ACTIVE_GOVERNANCE_PROFILE`) olur.
- Mevcut sahiplik alanları (`data_sources`, `data_protection/inventory`,
  `retention`) `build_governance_profile_from_sources` ile **referanslanır,
  kopyalanmaz**; çelişen ikinci sahip kaydı üretilmez.
- OpenLineage uyumlu, W3C PROV'ye eşlenebilir sürümlü lineage olayı değişmez
  snapshot/digest ile saklanır; eksik/eski kapsama durumu (`coverage_status`,
  freshness) kaydedilir. Snapshot ve hazırlanmış audit olayı aynı transaction
  içindeki audit outbox'a yazılır.
- Etki bileşenleri `Observed`/`Calculated`/`Estimated`/`Unknown` durumu, kaynağı,
  formülü, veri zamanı ve güvenini taşır; desteklenmeyen bileşenler tek toplam
  etkide birleştirilmez. Parasal değer otoriter kaynak/onaylı formül yoksa
  `Unknown` kalır.
- Kök neden çıktısı yalnız hipotezdir; korelasyon doğrulanmış neden olarak
  sunulmaz ve insan tarafından girilen `root_cause` alanını ezmez.
- Öneriler yalnız `DeterministicRule`, `IncidentSimilarity` ve auditli
  `ExpertInput`; `LLMAssisted` kapalıdır. Her öneri minimum kanıt, mekanizma
  sürümü, bağımsız güven ve karşı kanıt taşır; kanıtı eksik mekanizma yayımlanmaz.
- Kritik asset/risk/SLA durumu, kanıt varsa yönetişim profilinden beslenir;
  yoksa `UNKNOWN` kalır. `api/app.py`'ye salt okunur snapshot ve yönetişim
  projeksiyonu ucu eklendi; `api/development.py` composition root'unda
  `governance_reader` ve `lineage_evidence_repository` bağlandı (kanıt yoksa
  503 fail-closed).
- Yeni migration `20260730_14` (`down_revision = 20260730_13`, tek head);
  `downgrade()` bilinçli `RuntimeError` fırlatır (12/13 konvansiyonu).

## Doğrulama

- `python3 -m pytest -q 06-Testler/01-Birim` → `1276 passed`
  (lineage/yönetişim 19, dashboard API lineage uçları 3 test dahil).
- `npx vitest run src/dashboard/model.test.ts` → `8 passed`
  (yönetişim özeti ve `governanceNote()` davranışı dahil).
- `DATA_QUALITY_POSTGRES_TEST_URL=... python3 -m pytest -q
  06-Testler/02-Entegrasyon/test_postgresql_lineage_evidence.py` → skipsiz
  `3 passed` (migration, değişmez snapshot/audit outbox ve yönetişim
  projeksiyon ucu).
- Tam entegrasyon paketi (`DATA_QUALITY_POSTGRES_TEST_URL` +
  `SYNTHETIC_POSTGRES_TEST=1`) → skipsiz `92 passed`.
- `python3 -m compileall` (lineage, api, migration) → exit `0`.

Canlı test yalnız controller'ın sağladığı test PostgreSQL şemasında migration,
değişmez snapshot, audit/outbox atomikliği ve yönetişim projeksiyon ucunu
doğrular. Bu kayıt production PostgreSQL uygunluğu iddia etmez. Kurumsal veri
kataloğu, gerçek lineage kaynağı, Finans/Risk otoriter etki kaynağı ve banka
onayı `ExternalDependency` olarak açık kalır.

`api/app.py` içinde önceden bulunan modül seviyesi endpoint F821 ruff bulguları
değişmeden korunmuştur (görev kapsamı dışı, HEAD'de aynı küme); eklenen lineage
uçları `create_dashboard_api` içinde doğru kapsamda tanımlıdır.

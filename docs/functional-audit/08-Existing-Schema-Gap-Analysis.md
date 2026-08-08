---
type: functional-audit
stage: "08 — Mevcut Şema GAP Analizi"
scope: existing-vs-target-schema
inputs:
  - alembic/versions/ (14 migration)
  - 07-Target-Data-Model.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-04
---

# 08 — Mevcut Şema ve Hedef Model Karşılaştırması

> Mevcut 14 migration'ın ürettiği şema, [07-Target-Data-Model.md](07-Target-Data-Model.md)
> kanonik hedef modeliyle karşılaştırılır. Kanıtlar migration dosyalarından ve
> repository kodundan bu oturumda okunmuştur.

---

## 1. Sayısal özet

| Ölçüt | Değer |
|---|---|
| Mevcut migration | 14 (`20260723_01` → `20260730_14`, doğrusal zincir) |
| Mevcut tablo | **31** |
| Hedef tablo | **119** (118 domain + 1 ortak `approval_requests`) |
| Hedefe birebir/kısmen karşılık gelen mevcut tablo | **29** |
| Hedefte karşılığı olmayan mevcut tablo (ek katman) | **2** (`lineage_evidence_snapshots`, `data_processing_inventory_versions`) |
| Hedefte tanımlı ama mevcut olmayan tablo | **90** |
| Kolon düzeyinde fark bulunan mevcut tablo | **13** (§4) |

---

## 2. Mevcut şema envanteri (14 migration, 31 tablo)

| Migration | Tablolar |
|---|---|
| `20260723_01` issue baseline | `data_quality_issues`, `issue_history`, `issue_resolutions`, `issue_verifications`, `issue_relationships`, `audit_outbox` |
| `20260723_02` rule baseline | `quality_rules`, `rule_versions`, `rule_test_results`, `rule_approval_requests` |
| `20260724_03` data source baseline | `data_sources`, `connection_test_results`, `datasets`, `data_fields`, `metadata_discovery_results`, `data_profiles`, `data_processing_inventory_versions`, `data_source_connection_revisions`, `data_source_activation_requests` |
| `20260724_04` execution baseline | `rule_executions`, `execution_attempts`, `rule_execution_results` |
| `20260724_05` scheduling/policy | `schedules`, `source_usage_policies` |
| `20260724_06` reporting | `reports` |
| `20260724_07` report schedules | `report_schedules` |
| `20260728_08` job queue | `background_jobs` |
| `20260729_09` job lifecycle | `job_dead_letters` + `background_jobs` iptal kolonları |
| `20260729_10` policy deadlines | `source_usage_policies` + 2 kolon |
| `20260729_11` profile comparisons | `profile_comparisons` + `data_profiles` method/status genişletmesi |
| `20260730_12` IR/shadow evidence | `rule_executions.execution_mode`, `rule_execution_results` uygunluk+kanıt kolonları |
| `20260730_13` contribution graphs | `score_contribution_graphs` |
| `20260730_14` lineage evidence | `lineage_evidence_snapshots` |

---

## 3. Yapısal ve adlandırma uyuşmazlıkları

### 3.1 Tablo adı eşleşmeleri

| Mevcut ad | Hedef ad | Not |
|---|---|---|
| `background_jobs` | `persistent_jobs` | Ad farkı; kolon seti büyük ölçüde uyumlu, durum modeli farklı (§4.3) |
| `job_dead_letters` | `dead_letter_records` | Ad farkı + `CLOSED` durumu ve kapatma kolonları eksik (§4.12) |
| `data_quality_issues` | `issues` | Ad farkı + kolon/durum farkları (§4.7) |

### 3.2 Şema adı tutarsızlığı — açık soru değil, doğrulanmış wiring hatası

Bu madde daha önce koşullu ("bakarsa … çalışmaz") yazılmıştı. Tutarsızlık
statik olarak doğrulanmıştır ve tek bir çalıştırılabilir bileşimin **içinde**
mevcuttur:

| Bileşen | Hedeflediği şema | Kanıt |
|---|---|---|
| Alembic | `dq` | `alembic.ini` → `data_quality_schema = dq`; `alembic/env.py:24` |
| Persistence varsayılanı | `dq` | `persistence/database.py:15` `DEFAULT_SCHEMA_NAME = "dq"` |
| `run_dev.py` ayarları ve audit outbox | `data_quality` | `run_dev.py:11,21,33` (`PostgreSQLTransactionalAudit(..., schema=SCHEMA)`) |
| Execution ve job repository'leri | `dq` | `api/development.py:1332-1333` — `schema=` argümanı **verilmiyor** |

Belirleyici ayrıntı: `DatabaseSettings.schema` session'a `search_path` olarak
uygulanmaz (`create_session_factory` yalnız engine bağlar); tablolar
`MetaData(schema=…)` ile açıkça niteliklendirilir. Dolayısıyla `run_dev.py`
ile başlatılan uygulamada iş verisi `dq`, audit outbox satırı `data_quality`
şemasına yazılır — ikisi aynı transaction'da olsa bile **aynı şemada
değildir**. `run_dev.py:26` yalnız `CREATE SCHEMA IF NOT EXISTS` çalıştırır;
`data_quality` şemasına hiçbir migration uygulanmaz.

Aynı satırlardaki ikinci hata: `run_dev.py:14-19` `_FakePreparedRepo` yalnız
`store()` tanımlar, oysa `PostgreSQLTransactionalAudit.publish_pending`
`repository.append()` çağırır (`audit/postgresql_outbox.py:99`). Oluşan
`AttributeError` `:102`'deki `except Exception` ile yutulur; satır `PENDING`
kalır, `last_error_code="AUDIT_REPOSITORY_UNAVAILABLE"` yazılır ve metod
hata fırlatmadan döner.

**Şema adı tek kaynağa bağlanmalı ve bileşimde açıkça geçirilmelidir.**
Bu madde aşama 1'in Q-13 sorusunu kapatır; GAP-001'de kayıtlıdır.

### 3.3 Kesitsel (tüm şema) eksikler

| Konu | Mevcut | Hedef |
|---|---|---|
| `retention_until` kolonu | Hiçbir tabloda yok | Saklama kapsamındaki tüm varlıklarda (`D13.C03.W01.A02`) |
| Partition | Hiç yok | `audit_events`, `rule_execution_results`, `lineage_events`, `notification_events/deliveries` aylık RANGE |
| JSON/JSONB | `prepared_event`, `definition`, `payload` vb. `JSON` | `JSONB` |
| PK tipi | `CHAR(36)` metin | `UUID` (taşıma süresince metin korunabilir) |
| `users` FK'leri | Aktör kolonları serbest `String(128)` | `users`/servis hesabına FK (GAP-022 sonrası) |
| Ortak onay tablosu | Yalnız alan tabloları (`rule_approval_requests`, `data_source_activation_requests`) | Yeni akışlar için ortak `approval_requests` |

### 3.4 Doğrulanmayan referans kolonları

Başlık daha önce "sarkan yabancı anahtarlar" idi; bu teknik olarak yanlıştır.
Aşağıdaki kolonlar **`ForeignKey` değildir** — hedefi düşmüş bir FK kısıtı
veritabanında mevcut değildir. Sorun, veritabanının hiçbir şekilde
doğrulamadığı bir referansın taşınmasıdır:

| Kolon | Tablo | Tanım | Sorun |
|---|---|---|---|
| `retention_policy_id` | `data_processing_inventory_versions` (migration 03) | `sa.Column("retention_policy_id", sa.String(40), nullable=False)` — `:225`; tablodaki tek `ForeignKeyConstraint` (`:231-234`) `data_fields.data_field_id` içindir | `retention_policies` tablosu hiçbir migration'da yok; `NOT NULL` olduğu için her kayıt doğrulanamayan bir değer taşımak **zorunda** |
| `retention_policy_id` | `reports` (migration 06) | `sa.Column("retention_policy_id", sa.String(36))` — `:34`, nullable; tabloda hiç `ForeignKeyConstraint` yok | Aynı — hedef tablo yok |

Ayrım pratikte önemlidir: sarkan bir FK migration'ı bozar ve hemen fark
edilir; doğrulanmayan bir metin kolonu sessizce tutarsız veri biriktirir.
Saklama zinciri (GAP-011) kurulurken bu kolonların gerçek FK'ye çevrilmesi
ve `NOT NULL` kısıtının veri geçişiyle birlikte ele alınması gerekir.

### 3.5 Eksik bırakılmış FK bağları

| Kolon | Tablo | Eksik |
|---|---|---|
| `rule_version_id` | `rule_execution_results` | `rule_versions`'a FK tanımlı değil (yalnız metin kolon) |
| `dataset_id` | `quality_rules` | `datasets`'e FK tanımlı değil |
| `schedule_id` | `rule_executions` | Kolon da yok; hedefte `schedules`'a FK |

---

## 4. Tablo bazında karşılaştırma (mevcut 29 eşlenik)

Durum kodları: `UYUMLU` — hedefle uyumlu · `KISMİ` — kolon/durum farkı var.

### 4.1 `audit_outbox` — KISMİ
`prepared_event` `JSON` yerine `JSONB` olmalı; `attempt_count`/`last_error_code`
mevcut ve hedefle uyumlu. Kalıcı defter (`audit_events`) hiç yok — §5 D13.

### 4.2 `background_jobs` → `persistent_jobs` — KISMİ
- Ad ve hedef `ST-Job` durum kümesi farklı: mevcut `QUEUED/RUNNING/CANCEL_REQUESTED/SUCCESS/TECHNICAL_ERROR/TIMEOUT/CANCELLED`; hedef `AVAILABLE/CLAIMED/RUNNING/COMPLETED/DEAD_LETTERED/BLOCKED/CANCELLED`. Mevcut enum iş **sonucunu**, hedef kuyruk **konumunu** modeller.
- Eksik kolon: `progress` (0-100).
- `version` mevcut ✓; claim/lease/heartbeat kolonları mevcut ✓; idempotency UQ mevcut ✓.

### 4.3 `connection_test_results` — UYUMLU (küçük fark)
Hedefteki `tested_by` kolonu mevcut değil. Append-only yapı ve FK doğru.

### 4.4 `data_fields` — KISMİ
- `classification` 9 sınıf ve politika sürümü mevcut ✓ (hedefle uyumlu).
- Eksik: alan yaşam döngüsü için `status`; hedef `classification_candidates` ayrı tablo (§5 D04).

### 4.5 `data_processing_inventory_versions` — EK KATMAN
Hedef 119 listesinde yok (bankacılık/KVKK kapsamı); korunur. Doğrulanmayan
`retention_policy_id NOT NULL` kolonu giderilmeli (§3.4).

### 4.6 `data_profiles` — KISMİ
- Mevcut durum kümesi `COMPLETED/NO_DATA/TECHNICAL_ERROR` **sonuç odaklı**;
  hedef `ST-Profile` talep yaşam döngüsünü ister: `QUEUED/RUNNING/SUCCESS/PARTIAL/CANCEL_REQUESTED/CANCELLED` (+ `TECHNICAL_ERROR`).
- Eksik kolonlar: `sample_seed`, `policy_version`, `requested_by`, `cancelled_by`.
- `metrics` tek `JSON` kolonu; hedefte `profile_field_metrics`, `profile_distributions`, `profile_outliers` olarak normalize edilir (§5 D05).

### 4.7 `data_quality_issues` → `issues` — KISMİ
- Ad farkı (§3.1).
- `source_event_type` CHECK'i yalnız `QUALITY/TECHNICAL` kabul eder; hedef `CONTRACT` ve `MANUAL` ekler (GAP-006/010).
- `trigger_type` CHECK'inde `MANUAL` karşılığı yok.
- Eksik kolonlar: `investigation_started_at`, `hold_reason`, `expected_resolution_at`, `sla_paused_at`, `cancel_reason` (GAP-014/akış 8 bekletme).
- `deduplication_key_digest` **tüm tabloda UNIQUE**; hedef tekilleştirme açık
  sorunlar arasında çalışır (`BR-D09-003`), kapalı sorunun tekrarında yeniden
  açma penceresi vardır (`BR-D09-007`). Mevcut global UNIQUE, ikinci bir açık
  olmayan tekrar kaydını engeller — kısmi index'e (`status` açıkken) taşınması
  değerlendirilmelidir.
- `assignee_user_id NOT NULL`; hedefte atama öncesi `NULL` olabilir.
- `occurrence_count`, `payload_digest`, `version`, `last_seen_at` mevcut ✓.

### 4.8 `data_source_activation_requests` — UYUMLU (küçük fark)
Maker-checker kolonları ve `INVALIDATED` dahil durum kümesi hedefle uyumlu.
Hedefteki "aynı nesne için tek PENDING" kısmi UNIQUE'si bu tabloda yok
(`data_source_id` + `data_source_revision` için eklenmeli).

### 4.9 `data_source_connection_revisions` — KISMİ
Mevcut durum kümesi `PENDING_TEST/PROMOTED/TEST_FAILED/REJECTED`; hedef
`ST-ConnectionRevision` `DRAFT/TESTED/EFFECTIVE/SUPERSEDED/ROLLED_BACK`.
Adlandırma ve geri alma (rollback) kolu hedefle örtüşmüyor.

### 4.10 `data_sources` — UYUMLU (küçük fark)
`ST-DataSource` 6 durumu mevcut ✓; `revision` iyimser kilit ✓; `secret_reference`
✓. Eksik: `owner_user_id` için `users` FK'si (GAP-022 sonrası).

### 4.11 `datasets` — KISMİ
Hedef `ST-Dataset` durum makinesi (`ACTIVE/SUSPECTED_REMOVED/ARCHIVED`) için
**`status` kolonu yok**; ölçüm askıya alma davranışı modellenemiyor.

### 4.12 `job_dead_letters` → `dead_letter_records` — KISMİ
Ad farkı; durum kümesi `OPEN/REPROCESSED` — hedefte `CLOSED` ve
`closure_reason`, `closed_at`, `measurement_gap_marked` kolonları eksik
(ölçüm boşluğu işaretleme `BR-D07-013` benzeri davranış).

### 4.13 `lineage_evidence_snapshots` — EK KATMAN
Hedef 119 listesinde yok; kanıt paketi deposu olarak korunur. Hedefin
`lineage_events`/`lineage_edges` alım katmanının yerini **tutmaz** (§5 D10).

### 4.14 `metadata_discovery_results` — KISMİ
Mevcut `succeeded` boolean + `error_class`; hedef `ST` durum kümesi
(`RUNNING/SUCCESS/PARTIAL/TECHNICAL_ERROR`) ve `requested_by` yok. Keşif
tetikleme yüzeyi GAP-004.

### 4.15 `profile_comparisons` — UYUMLU (küçük fark)
Deterministik karşılaştırma hedefle uyumlu; drift hükmü `result` JSON'u içinde
taşınıyor — hedefte ayrı `drift_judgments` tablosu (§5 D05).

### 4.16 `quality_rules` — KISMİ
Durum kümesi hedefle birebir ✓ (`DRAFT/ACTIVE/PASSIVE/REVIEW_REQUIRED/ARCHIVED`).
Eksik: `version` (iyimser kilit), `created_at/updated_at`, `datasets` FK'si.

### 4.17 `report_schedules` — KISMİ
`is_active INT` yerine hedef `status` (`ACTIVE/PAUSED/DELETED`) + `paused_until`,
`deleted_at` ister. Tetikleme daemon'u yok (GAP-015).

### 4.18 `reports` — KISMİ
- Durum adları farklı: mevcut `QUEUED/RUNNING/READY/FAILED/EXPIRED`; hedef
  `ST-ReportJob` `PENDING/GENERATING/READY/FAILED/CANCELLED/EXPIRED`.
  `CANCELLED` ve iptal akışı yok (hedef `D11.C03.W02.A02`).
- `retention_policy_id` doğrulanmayan referans — FK değil (§3.4).
- `retention_until` ve `downloaded_by` izleme (`report_downloads`) yok (§5 D11).

### 4.19 `rule_approval_requests` — UYUMLU
Durum kümesi, maker/checker kolonları, kısmi UNIQUE (`PENDING` başına tek
talep) ve süre aşımı index'i hedef `ST-ApprovalRequest` ile uyumlu. Süre
aşımı geçişini tetikleyen zamanlayıcı yok (GAP-003 altyapısı).

### 4.20 `rule_execution_results` — KISMİ
Sekiz sayaç + `measurement_status` + uygunluk bayrakları + `evidence` mevcut ✓.
Eksik: `recorded_at` (partition anahtarı), `rule_version_digest` (`BR-D06-015`),
`rule_versions` FK'si (§3.5).

### 4.21 `rule_executions` — UYUMLU (küçük fark)
Durum kümesi hedef `ST-RuleExecution` ile birebir ✓; `execution_mode` SHADOW ✓;
idempotency UQ ✓. Eksik: `schedule_id` FK (§3.5).

### 4.22 `rule_test_results` — UYUMLU
Sayaçlar, `official_score_included` ve `error_class` hedefle uyumlu.

### 4.23 `rule_versions` — KISMİ (kritik)
- **`status` kolonu yok.** Hedef `ST-RuleVersion` (`DRAFT/SEALED/PENDING_APPROVAL/APPROVED/ACTIVE/SUPERSEDED`) veritabanında temsil edilmiyor; yaşam döngüsü yalnız servis mantığında.
- `definition_digest` yok — `BR-D06-015` (her sonuç sürüm özeti taşır) uygulanamıyor.
- `template_id` yok (GAP-020 şablon bağı).
- `threshold/weight` `FLOAT`; hedef `NUMERIC`.
- Aşama 1 §3.7'deki "migration 12 IR digest kolonları rule_versions'da" ifadesi
  bu okumayla **doğrulanamadı**; migration 12 kolonları `rule_executions` ve
  `rule_execution_results`'a eklemiştir (aşama 1 düzeltme notu).

### 4.24 `schedules` — KISMİ
`is_active INT` yerine hedef `status` (`ACTIVE/PAUSED/DELETED`) + `paused_until`,
`deleted_at`; `schedule_id → rule_executions.schedule_id` bağı ters yönde eksik.
Tetikleyici daemon yok (GAP-003).

### 4.25 `score_contribution_graphs` — UYUMLU
`JSONB` kullanan tek mevcut tablo; scope CHECK'i hedefle uyumlu. `quality_scores`
tablosu olmadığı için PK bağı mantıksal (§5 D08).

**`quality_scores` hakkında açıklama.** Bu ad kod tabanında geçer, fakat
PostgreSQL şemasında **yoktur**: yalnız `scoring/repository.py:48` içinde
SQLite `CREATE TABLE IF NOT EXISTS quality_scores (…)` DDL'i olarak
tanımlıdır ve SQLite'a özgü bakım kodu (`PRAGMA table_info`, `ALTER TABLE …
RENAME`) taşır. `score_publications` ise hiçbir kodda geçmez; yalnız hedef
model belgelerinde vardır. Dolayısıyla §7'deki "yok" hükmü PostgreSQL şeması
için doğrudur ve `PostgreSQLContributionGraphRepository`
(`scoring/postgresql_contributions.py:47`) mevcut olsa da bileşime bağlı
değildir (GAP-008).

### 4.26 `source_usage_policies` — UYUMLU
Kota/pencere/zaman aşımı kolonları (migration 10 dahil) hedef `D03.C03` ile
uyumlu. Hedef politika yaşam döngüsü (`D01.C04` ortak `policies`) ile
bütünleşmesi ileride değerlendirilebilir.

### 4.27–4.29 Issue tarih tabloları (`issue_history`, `issue_resolutions`, `issue_verifications`, `issue_relationships`) — UYUMLU
Identity `sequence_no` + append-only yapı, içerik CHECK'leri (uzunluk/no-HTML),
`RECURRENCE` UQ'su hedefle uyumlu. `issue_resolutions`'a hedefteki
`remediation_action_id` kolonu eklenecek (GAP-013 sonrası).

---

## 5. Hedefte tanımlı, mevcut olmayan tablolar (90)

Domain bazında; her satır ilgili GAP kaydına bağlanır.

| Domain | Eksik tablolar | Bağlı GAP |
|---|---|---|
| **D01** (13) | `org_units`, `business_domains`, `data_domains`, `domain_asset_assignments`, `asset_ownerships`, `glossary_terms`, `glossary_term_mappings`, `governance_scan_runs`, `policies`, `policy_rollbacks`, `system_config`, `system_config_history`, `feature_flags` | GAP-026 |
| **D02** (11) | `users`, `service_accounts`, `roles`, `permissions`, `role_permissions`, `role_assignments`, `assignment_scopes`, `segregation_rules`, `sessions`, `access_review_campaigns`, `access_review_items` | GAP-022 |
| **D03** (1) | `source_health_checks` | GAP-024 |
| **D04** (4) | `discovery_scopes`, `metadata_diffs`, `classification_candidates`, `schema_changes` | GAP-004, GAP-019 |
| **D05** (5) | `profile_field_metrics`, `profile_distributions`, `profile_outliers`, `profile_baselines`, `drift_judgments` | GAP-005 |
| **D06** (3) | `rule_templates`, `rule_dependencies`, `rule_conflicts` | GAP-020 |
| **D07** (3) | `execution_partitions`, `schedule_missed_runs`, `workers` | GAP-002, GAP-003 |
| **D08** (5) | `failure_samples`, `measurement_qualifications`, `quality_scores`, `score_publications`, `risk_ratings` | GAP-008 |
| **D09** (9) | `issue_comments`, `issue_slas`, `issue_escalations`, `exceptions`, `exception_suppressions`, `diagnosis_hypotheses`, `recommendations`, `remediation_actions`, `remediation_impacts` | GAP-006, GAP-009, GAP-013, GAP-014 |
| **D10** (9) | `lineage_events`, `lineage_edges`, `column_lineage_edges`, `impact_analyses`, `impact_simulations`, `data_contracts`, `contract_compliance`, `contract_breaches`, `quality_debts` | GAP-010, GAP-012, GAP-013 |
| **D11** (2) | `report_downloads`, `export_records` | GAP-016 |
| **D12** (6) | `notification_events`, `notification_subscriptions`, `notification_channels`, `notification_deliveries`, `integration_records`, `rate_limit_counters` | GAP-007, GAP-023 |
| **D13** (7) | `audit_events`, `audit_integrity_checks`, `audit_export_cursors`, `retention_policies`, `disposal_jobs`, `legal_holds`, `archive_recalls` | GAP-011 (+ audit defteri) |
| **D14** (5) | `component_health`, `operational_incidents`, `incident_updates`, `maintenance_windows`, `backfill_jobs` | GAP-024 |
| **D15** (6) | `synthetic_profiles`, `synthetic_runs`, `ground_truth_defects`, `expected_results`, `control_validations`, `control_experiments` | GAP-025 |
| **Ortak** (1) | `approval_requests` | GAP-009/010/026 onay akışları |

---

## 6. Bulguların özet sıralaması

Etki × bağımlılık açısından şema düzeyindeki en kritik bulgular:

| # | Bulgu | Neden kritik |
|---|---|---|
| 1 | `quality_scores` ve `score_publications` yok | Skor kalıcılığı/yayımı olmadan ölçüm zinciri kanıt üretemez (GAP-008) |
| 2 | `audit_events` kalıcı defteri yok; outbox `publish_pending()` no-op depoya yazıyor | Runtime'da audit izi oluşmuyor; hash zinciri kanıtlanamıyor |
| 3 | Doğrulanmayan `retention_policy_id` referansları (`NOT NULL` dahil, FK değil) | Veri bütünlüğü tanımsız ve DB tarafından hiç denetlenmiyor; retention zinciri başlayamıyor (GAP-011) |
| 4 | `rule_versions.status` yok | Kural yaşam döngüsü DB'de temsil edilmiyor; SEALED değişmezliği yapısal değil |
| 5 | `issues` durum/kolon farkları + `background_jobs` durum modeli | Otomatik üretim, SLA ve bekletme zinciri şemada karşılık bulamıyor |
| 6 | D02 tabloları hiç yok | Aktör kolonları serbest metin; hiçbir FK/SoD denetimi yapısal değil |
| 7 | Şema ayrışması (`dq` vs `data_quality`) — **doğrulanmış** | `run_dev.py` ile başlatılan uygulamada iş verisi `dq`, audit outbox `data_quality` şemasına yazılır; ayrıca `_FakePreparedRepo` protokol uyuşmazlığı audit yayımını sessizce başarısız kılar (§3.2) |
| 8 | Partition ve retention altyapısı hiç yok | Yüksek hacimli kanıt tabloları hedef davranışı karşılayamaz |

## 7. Kanıt sınırları

- Karşılaştırma migration kaynak kodu ve repository `Table()` tanımları
  üzerinden yapılmıştır; canlı veritabanı introspeksiyonu çalıştırılmamıştır.
- Uygulama katmanının (repository/servis) kolon kullanımı her tabloda tek tek
  doğrulanmamış; migration-şema ekseni esas alınmıştır.
- Mevcut şemada downgrade 12 migration'da kapalıdır (ileri düzeltme politikası);
  hedefe taşıma yalnız ileri migration'larla yapılmalıdır.

---
type: functional-audit
stage: "07 — Hedef Veri Modeli"
scope: target-canonical-data-model
inputs:
  - 02-Target-Capability-Hierarchy.md
  - 04-Functional-Gap-Inventory.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-04
---

# 07 — Hedef Kanonik PostgreSQL Veri Modeli

> Aşama 2'nin §6.5 katalogundaki **119 tablo + 1 ortak tablo** için kolon
> düzeyinde kanonik tasarım. Bu belge hedef durumu tanımlar; mevcut şemayla
> karşılaştırma [08-Existing-Schema-Gap-Analysis.md](08-Existing-Schema-Gap-Analysis.md)
> belgesindedir.

---

## 1. Genel sözleşmeler

### 1.1 Tip ve adlandırma

| Konu | Kanonik karar |
|---|---|
| Şema | Tek şema: `dq` (yapılandırılabilir; `alembic.ini` `data_quality_schema` — mevcut `run_dev.py`'deki `data_quality` adıyla tutarsızlık giderilmelidir) |
| Birincil anahtar | `UUID` (gen_random_uuid). Mevcut tablolardaki `CHAR(36)` metin temsili taşımada korunabilir; yeni tablolarda `UUID` |
| Zaman | Tüm zaman damgaları `TIMESTAMPTZ` |
| Yapısal yük | `JSONB` (mevcut `JSON` kolonları hedefte `JSONB`'ye taşınır) |
| Durum alanları | `TEXT` + `CHECK IN (...)` — durum makineleri §6.1'den alınır; PG enum tipi kullanılmaz (evrim esnekliği) |
| Skor/oran | `NUMERIC(7,4)`; sayaçlar `BIGINT CHECK >= 0` |
| Aktör kimliği | `actor_ref TEXT` — `users.user_id` veya servis hesabı referansı; serbest dize roller kabul edilmez (GAP-022) |

### 1.2 Ortak kolonlar

Saklama kapsamındaki tüm varlık tablolarında:

| Kolon | Tip | Amaç |
|---|---|---|
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | Oluşum anı |
| `created_by` | `TEXT NOT NULL` | Oluşturan aktör |
| `retention_until` | `TIMESTAMPTZ` | `D13.C03.W01.A02` — politika çözümüyle doldurulur; `NULL` = politika çözümlenmedi (fail-closed: en uzun süre uygulanır) |
| `version` | `BIGINT NOT NULL DEFAULT 1` | İyimser kilit — yazan her komut `WHERE version = :beklenen` ile artırır |

### 1.3 Partition ilkesi

Yüksek hacimli, append-only ve zamana göre sorgulanan tablolar **aylık RANGE
partition** ile kurulur; sıcak kuyruk tabloları partition'lanmaz:

| Tablo | Partition anahtarı |
|---|---|
| `audit_events` | `occurred_at` |
| `rule_execution_results` | `recorded_at` |
| `lineage_events` | `occurred_at` |
| `notification_events` | `published_at` |
| `notification_deliveries` | `created_at` |

### 1.4 Retention kategorileri

Her tablo kartındaki `Retention` alanı şu kategorilerden birini taşır; somut
süreler `retention_policies` tablosunda yönetilir (`D13.C03.W01.A01`):

| Kategori | Anlam |
|---|---|
| `R-AUDIT` | Denetim kaydı — asgari kurumsal/bankacılık süresi; imha dış toplayıcı kanıtından sonra |
| `R-EVIDENCE` | Ölçüm/skor kanıtı — politika süresi (varsayılan uzun) |
| `R-OPS` | Operasyonel kayıt — tamamlanmadan sonra kısa süre (ör. 90 gün) arındırma |
| `R-NOTIF` | Bildirim kaydı — politika süresi (varsayılan 1 yıl) |
| `R-REPORT` | Rapor — `expires_at` dosya imhası, metadata kalır (`BR-D11-010`) |
| `R-CATALOG` | Katalog/politik kayıt — aktif olduğu sürece; arşivleme sonrası politika |

### 1.5 Audit, kilit ve değişmezlik sözleşmeleri

- **Audit:** her mutasyon, iş transaction'ıyla aynı oturumda `audit_outbox`'a
  `PENDING` olay yazar (`D13.C01.W01.A01`, fail-closed). Kartların `Audit`
  alanı olay adını verir; olay kataloğu aşama 2 §6.3'tür.
- **Optimistic locking:** durum değiştiren her tabloda `version` kolonu;
  istemci uçlarında `If-Match` karşılığı.
- **Immutable davranış:** "değişmez" işaretli tablolarda `UPDATE` uygulama
  katmanında yasaklanır; DB düzeyinde tetikleyici (`BEFORE UPDATE → raise`)
  önerilir. Ham ölçüm (`rule_execution_results`), sonuç, skor ve audit
  kayıtları hiçbir istisna tarafından değiştirilemez (`BR-D09-011`).
- **Maker-checker:** ortak `approval_requests` tablosu + alan tablolarındaki
  `maker_actor_id`/`checker_actor_id` kolonları; `CHECK (checker <> maker)`
  karar anında uygulanır.
- **Idempotency:** kuyruk, çalıştırma ve entegrasyon tablolarında
  `idempotency_key` üzerinde (kısmi) UNIQUE.

---

## 2. Domain tabloları

### D01 — Yönetişim, Organizasyon ve Politika

#### `org_units`
- **Amaç:** Kurumsal organizasyon birimlerinin kök kaydı (`D01.C01.W01`).
- **Kolonlar:** `org_unit_id UUID PK` · `code TEXT NN UQ` · `name TEXT NN` · `parent_org_unit_id UUID NULL` · `status TEXT NN DEFAULT 'ACTIVE'` · ortak kolonlar
- **PK/FK:** PK `org_unit_id`; FK `parent_org_unit_id → org_units`
- **Unique/Check:** UQ(code); CK status ∈ {ACTIVE, INACTIVE}
- **Index:** GIN name araması opsiyonel
- **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `ORG_UNIT_CREATED/CHANGED` · **Optimistic locking:** `version` · **Immutable:** —
- **Yazan:** yönetişim yönetim servisi · **Okuyan:** domain/sahiplik atama, scope çözümleme

#### `business_domains`
- **Amaç:** İş domain'i tanımı; dataset'lerin iş kırılımı (`D01.C01.W02`).
- **Kolonlar:** `business_domain_id UUID PK` · `org_unit_id UUID NN` · `code TEXT NN UQ` · `name TEXT NN` · `status TEXT NN` · ortak kolonlar
- **PK/FK:** FK → `org_units`
- **Unique/Check:** UQ(code); CK status
- **Index:** (org_unit_id) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** domain olayları · **Optimistic locking:** `version` · **Immutable:** —
- **Yazan:** yönetişim servisi · **Okuyan:** skor toplulaştırma (`D08.C03.W02.A03`), dashboard

#### `data_domains`
- **Amaç:** Veri domain'i tanımı (`D01.C01.W03`).
- **Kolonlar:** `data_domain_id UUID PK` · `business_domain_id UUID NULL` · `code TEXT NN UQ` · `name TEXT NN` · `status TEXT NN` · ortak kolonlar
- **PK/FK:** FK → `business_domains`
- **Unique/Check:** UQ(code) · **Index:** — · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** domain olayları · **Optimistic locking:** `version` · **Immutable:** —
- **Yazan:** yönetişim servisi · **Okuyan:** katalog, sahiplik

#### `domain_asset_assignments`
- **Amaç:** Dataset/kaynak varlıklarının veri domain'lerine atanması (`D01.C01`).
- **Kolonlar:** `assignment_id UUID PK` · `data_domain_id UUID NN` · `asset_type TEXT NN` · `asset_id UUID NN` · `assigned_by TEXT NN` · `assigned_at TIMESTAMPTZ NN` · ortak kolonlar
- **PK/FK:** FK → `data_domains`
- **Unique/Check:** UQ(asset_type, asset_id, data_domain_id); CK asset_type ∈ {DATASET, SOURCE}
- **Index:** (asset_type, asset_id) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `DOMAIN_ASSET_ASSIGNED` · **Optimistic locking:** — (append) · **Immutable:** atama geçmişi korunur
- **Yazan:** yönetişim servisi · **Okuyan:** kapsam çözümleme, skor domain toplulaştırma

#### `asset_ownerships`
- **Amaç:** Varlık sahipliği ataması (`D01.C02.W01.A01`); sahiplik tüm SLA/bildirim zincirinin girişidir.
- **Kolonlar:** `ownership_id UUID PK` · `asset_type TEXT NN` · `asset_id UUID NN` · `owner_user_id UUID NN` · `role TEXT NN` (DATA_OWNER/TECHNICAL_STEWARD) · `valid_from TIMESTAMPTZ NN` · `valid_to TIMESTAMPTZ NULL` · ortak kolonlar
- **PK/FK:** FK `owner_user_id → users`
- **Unique/Check:** UQ(asset_type, asset_id, role) WHERE valid_to IS NULL (kısmi); CK role
- **Index:** (owner_user_id) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `OWNERSHIP_ASSIGNED/CHANGED` · **Optimistic locking:** `version` · **Immutable:** geçmiş kayıtlar
- **Yazan:** sahiplik servisi · **Okuyan:** sorun atama adayları, bildirim abone çözümü, sahipsiz varlık taraması

#### `glossary_terms`
- **Amaç:** İş sözlüğü terim yaşam döngüsü (`D01.C03.W01`).
- **Kolonlar:** `term_id UUID PK` · `code TEXT NN UQ` · `name TEXT NN` · `definition TEXT NN` · `status TEXT NN` (DRAFT/PUBLISHED/DEPRECATED) · `steward_user_id UUID NULL` · ortak kolonlar
- **PK/FK:** FK steward → users
- **Unique/Check:** UQ(code); CK status
- **Index:** — · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** terim olayları · **Optimistic locking:** `version` · **Immutable:** PUBLISHED tanım değişimi yeni sürümle
- **Yazan:** sözlük servisi · **Okuyan:** katalog UI, terim eşleme

#### `glossary_term_mappings`
- **Amaç:** Terim–varlık eşlemesi (`D01.C03.W02`).
- **Kolonlar:** `mapping_id UUID PK` · `term_id UUID NN` · `asset_type TEXT NN` · `asset_id UUID NN` · ortak kolonlar
- **PK/FK:** FK → glossary_terms
- **Unique/Check:** UQ(term_id, asset_type, asset_id)
- **Index:** (asset_type, asset_id) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** terim olayları · **Immutable:** —
- **Yazan:** sözlük servisi · **Okuyan:** katalog detayı

#### `governance_scan_runs`
- **Amaç:** Sahipsiz varlık ve yönetişim boşluğu tarama koşuları (`D01.C02.W03`).
- **Kolonlar:** `scan_run_id UUID PK` · `started_at / finished_at TIMESTAMPTZ` · `orphan_asset_count BIGINT NN DEFAULT 0` · `result JSONB NN` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** — · **Index:** (started_at DESC)
- **Partition:** yok · **Retention:** `R-OPS`
- **Audit:** tarama olayı · **Immutable:** koşu sonucu değişmez
- **Yazan:** yönetişim tarama işi · **Okuyan:** yönetişim panosu

#### `policies`
- **Amaç:** Sistem politikalarının sürümlü ve onaylı kaydı (`D01.C04.W01/W02`); ST-Policy durum makinesi. Tüm `policy_version` damgalarının gerçek hedefi.
- **Kolonlar:** `policy_id UUID PK` · `policy_type TEXT NN` (SCORING/PROFILING/CLASSIFICATION/RETENTION/NOTIFICATION/…) · `version_no BIGINT NN` · `content JSONB NN` · `status TEXT NN` (DRAFT/IN_REVIEW/APPROVED/EFFECTIVE/SUPERSEDED/ROLLED_BACK) · `effective_from TIMESTAMPTZ NULL` · `approved_by TEXT NULL` · ortak kolonlar
- **PK/FK:** onay bağı → `approval_requests`
- **Unique/Check:** UQ(policy_type, version_no); CK status; CK EFFECTIVE iken effective_from NOT NULL (uygulama düzeyinde)
- **Index:** (policy_type, status) kısmi WHERE status='EFFECTIVE'
- **Partition:** yok · **Retention:** `R-CATALOG` (politik geçmiş denetim kanıtıdır)
- **Audit:** `POLICY_DRAFT_CREATED/SUBMITTED/APPROVAL_DECIDED/MADE_EFFECTIVE/ROLLED_BACK`
- **Optimistic locking:** `version` · **Immutable:** APPROVED sonrası content değişmez
- **Yazan:** politika servisi · **Okuyan:** tüm politika çözümleyiciler (skorlama, profilleme, sınıflandırma, retention)

#### `policy_rollbacks`
- **Amaç:** Politika geri alma kaydı (`D01.C04`).
- **Kolonlar:** `rollback_id UUID PK` · `policy_id UUID NN` · `from_version_no BIGINT NN` · `to_version_no BIGINT NN` · `reason TEXT NN` · `performed_by TEXT NN` · `performed_at TIMESTAMPTZ NN`
- **PK/FK:** FK → policies
- **Unique/Check:** CK to_version_no < from_version_no
- **Index:** (policy_id) · **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** `POLICY_ROLLED_BACK` · **Immutable:** evet (append-only)
- **Yazan:** politika servisi · **Okuyan:** denetim

#### `system_config`
- **Amaç:** Sistem konfigürasyon anahtarları (`D01.C05.W01/W02`).
- **Kolonlar:** `config_key TEXT PK` · `config_value JSONB NN` · `description TEXT NULL` · ortak kolonlar
- **PK/FK:** PK config_key
- **Unique/Check:** — · **Index:** — · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `SYSTEM_CONFIG_CHANGED` · **Optimistic locking:** `version` · **Immutable:** —
- **Yazan:** konfigürasyon servisi (maker-checker) · **Okuyan:** tüm servisler

#### `system_config_history`
- **Amaç:** Konfigürasyon değişiklik geçmişi (append-only).
- **Kolonlar:** `sequence_no BIGINT IDENTITY PK` · `config_key TEXT NN` · `old_value JSONB NULL` · `new_value JSONB NN` · `changed_by TEXT NN` · `changed_at TIMESTAMPTZ NN`
- **PK/FK:** — · **Unique/Check:** — · **Index:** (config_key, changed_at DESC)
- **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** olayın kendisi · **Immutable:** evet
- **Yazan:** konfigürasyon servisi · **Okuyan:** denetim ekranı

#### `feature_flags`
- **Amaç:** Özellik anahtarı yönetimi (`D01.C05.W02`).
- **Kolonlar:** `flag_key TEXT PK` · `enabled BOOLEAN NN DEFAULT FALSE` · `rollout JSONB NN DEFAULT '{}'` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** — · **Index:** —
- **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `FEATURE_FLAG_CHANGED` · **Optimistic locking:** `version` · **Immutable:** —
- **Yazan:** konfigürasyon servisi · **Okuyan:** tüm servisler

### D02 — Kimlik, Rol ve Erişim Yönetimi

#### `users`
- **Amaç:** Dışsal dizinde doğrulanmış kimliğin sistem içi yetki taşıyıcısı hesabı (`D02.C01.W01`); ST-User.
- **Kolonlar:** `user_id UUID PK` · `external_identity_ref TEXT NN` · `display_name TEXT NN` · `status TEXT NN DEFAULT 'ACTIVE'` · ortak kolonlar
- **PK/FK:** PK user_id
- **Unique/Check:** UQ(external_identity_ref); CK status ∈ {ACTIVE, INACTIVE}
- **Index:** — (UQ yeter) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `USER_PROVISIONED/DEACTIVATED/REACTIVATED`
- **Optimistic locking:** `version` · **Immutable:** external_identity_ref değişmez
- **Yazan:** kimlik sağlama servisi (dizin senkronu idempotent) · **Okuyan:** scope çözümleme, atama adayları, audit aktör çözümleme

#### `service_accounts`
- **Amaç:** Programatik entegrasyon hesabı; süreli ve dar kapsamlı (`D02.C01.W02`).
- **Kolonlar:** `service_account_id UUID PK` · `name TEXT NN` · `purpose TEXT NN` · `owner_user_id UUID NN` · `credential_ref TEXT NN` · `expires_at TIMESTAMPTZ NN` · `previous_credential_ref TEXT NULL` · `rotation_grace_until TIMESTAMPTZ NULL` · `status TEXT NN` · ortak kolonlar
- **PK/FK:** FK owner → users
- **Unique/Check:** UQ(name); CK expires_at > now() oluşturuda; CK status
- **Index:** (status) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `SERVICE_ACCOUNT_CREATED/CREDENTIAL_ROTATED`
- **Optimistic locking:** `version` · **Immutable:** sır değeri asla yazılmaz, yalnız referans (`BR-D12-004` benzeri)
- **Yazan:** kimlik servisi · **Okuyan:** API kimliklendirme (`D12.C04.W01.A01`)

#### `roles`
- **Amaç:** İş sorumluluğuna karşılık yetki paketi (`D02.C02.W01.A01`).
- **Kolonlar:** `role_id UUID PK` · `code TEXT NN UQ` · `name TEXT NN` · `status TEXT NN` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** UQ(code); CK status
- **Index:** — · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `ROLE_DEFINED` · **Optimistic locking:** `version` · **Immutable:** —
- **Yazan:** kimlik yönetim servisi · **Okuyan:** izin çözümleme

#### `permissions`
- **Amaç:** İzin kataloğu — sistemin koruduğu her işlemin kaydı (`D02.C02.W02.A01`).
- **Kolonlar:** `permission_code TEXT PK` · `description TEXT NN` · `domain_code TEXT NN` · `scope_kind TEXT NN` (SOURCE/DATASET/ENTERPRISE/NONE)
- **PK/FK:** — · **Unique/Check:** CK scope_kind
- **Index:** (domain_code) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** erişim kaydı `PERMISSION_CATALOG_VIEWED` · **Immutable:** kod değişmez
- **Yazan:** migrasyon/katalog seed + yönetim servisi · **Okuyan:** yetki kararları, denetim görünümü

#### `role_permissions`
- **Amaç:** Rol→izin eşlemesi (`D02.C02.W01.A02`).
- **Kolonlar:** `role_id UUID NN` · `permission_code TEXT NN` · `granted_at TIMESTAMPTZ NN` · `granted_by TEXT NN` · PK(role_id, permission_code)
- **PK/FK:** FK → roles, → permissions
- **Unique/Check:** PK bileşik · **Index:** (permission_code)
- **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `ROLE_PERMISSIONS_CHANGED` · **Immutable:** satır değişmez; kaldırma silme + audit
- **Yazan:** rol yönetim servisi · **Okuyan:** yetki çözümleme

#### `role_assignments`
- **Amaç:** Kullanıcıya kapsam dahil rol (`D02.C02.W03.A01`); ST-RoleAssignment.
- **Kolonlar:** `assignment_id UUID PK` · `user_id UUID NN` · `role_id UUID NN` · `scope_type TEXT NN` · `scope_id UUID NULL` · `valid_from TIMESTAMPTZ NN` · `valid_to TIMESTAMPTZ NULL` · `status TEXT NN` (ACTIVE/REVOKED/EXPIRED) · `revoked_by TEXT NULL` · `reason_code TEXT NULL` · ortak kolonlar
- **PK/FK:** FK → users, → roles
- **Unique/Check:** CK status; kısmi UQ(user_id, role_id, scope_type, scope_id) WHERE status='ACTIVE'
- **Index:** (user_id, status) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `ROLE_ASSIGNED/ROLE_ASSIGNMENT_REVOKED`
- **Optimistic locking:** `version` · **Immutable:** REVOKED kayıt değişmez
- **Yazan:** rol atama servisi (SoD denetimli) · **Okuyan:** scope çözümleme, erişim gözden geçirme

#### `assignment_scopes`
- **Amaç:** Kapsam atamalarının ayrıntılı kaydı (`D02.C03.W01`).
- **Kolonlar:** `scope_id UUID PK` · `assignment_id UUID NN` · `scope_kind TEXT NN` (SOURCE/DATASET/DOMAIN/ENTERPRISE) · `target_id UUID NULL` · ortak kolonlar
- **PK/FK:** FK → role_assignments
- **Unique/Check:** UQ(assignment_id, scope_kind, target_id)
- **Index:** (scope_kind, target_id) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** atama audit'ine gömülü · **Immutable:** —
- **Yazan:** atama servisi · **Okuyan:** `ActorContext` çözümleme

#### `segregation_rules`
- **Amaç:** Görev ayrılığı çakışma çiftleri (`D02.C02.W02.A02`).
- **Kolonlar:** `rule_id UUID PK` · `permission_a TEXT NN` · `permission_b TEXT NN` · `enforcement_level TEXT NN` (WARN/BLOCK) · `reason TEXT NN` · `status TEXT NN` · ortak kolonlar
- **PK/FK:** FK → permissions (a,b)
- **Unique/Check:** UQ(permission_a, permission_b); CK enforcement_level; CK a <> b
- **Index:** — · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `SOD_RULE_DEFINED` · **Optimistic locking:** `version` · **Immutable:** —
- **Yazan:** kimlik yönetim servisi · **Okuyan:** atama anında SoD denetimi

#### `sessions`
- **Amaç:** Oturum yaşam döngüsü (`D02.C04.W01`); ST-Session.
- **Kolonlar:** `session_id UUID PK` · `user_id UUID NN` · `status TEXT NN` (ACTIVE/TERMINATED/EXPIRED) · `established_at TIMESTAMPTZ NN` · `expires_at TIMESTAMPTZ NN` · `terminated_at TIMESTAMPTZ NULL` · `context_digest TEXT NN` · ortak kolonlar
- **PK/FK:** FK → users
- **Unique/Check:** CK status
- **Index:** (user_id, status) kısmi WHERE status='ACTIVE'
- **Partition:** yok · **Retention:** `R-NOTIF` kategorisi benzeri kısa süreli operasyonel kayıt
- **Audit:** `SESSION_ESTABLISHED/TERMINATED` · **Immutable:** sonlanan oturum değişmez
- **Yazan:** `BffSessionBoundary` (GAP-022 ile üretime bağlanır) · **Okuyan:** yetki çözümleme

#### `access_review_campaigns`
- **Amaç:** Periyodik erişim sertifikasyonu kampanyası (`D02.C05.W01`).
- **Kolonlar:** `campaign_id UUID PK` · `name TEXT NN` · `period TEXT NN` · `status TEXT NN` (RUNNING/COMPLETED) · `due_at TIMESTAMPTZ NN` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** CK status
- **Index:** (status) · **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** `ACCESS_REVIEW_STARTED` · **Optimistic locking:** `version`
- **Yazan:** erişim gözden geçirme servisi · **Okuyan:** kampanya ekranı

#### `access_review_items`
- **Amaç:** Kampanya kalemi — her rol atamasının sertifikasyonu; ST-AccessReviewItem.
- **Kolonlar:** `item_id UUID PK` · `campaign_id UUID NN` · `assignment_id UUID NN` · `status TEXT NN` (PENDING/CERTIFIED/REVOKED/AUTO_REVOKED) · `decided_by TEXT NULL` · `decided_at TIMESTAMPTZ NULL` · `decision_reason TEXT NULL` · ortak kolonlar
- **PK/FK:** FK → campaigns, → role_assignments
- **Unique/Check:** UQ(campaign_id, assignment_id); CK status; CK karar veren ≠ atama sahibi (uygulama düzeyinde)
- **Index:** (campaign_id, status) · **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** `ACCESS_REVIEW_DECIDED` · **Immutable:** karar sonrası değişmez
- **Yazan:** gözden geçirme servisi · **Okuyan:** kampanya ekranı, denetim kanıtı

### D03 — Veri Kaynağı ve Bağlantı Yönetimi

#### `data_sources`
- **Amaç:** Bağlantı politikasıyla yönetilen, salt okunur erişilen kaynak kaydı (`D03.C01.W01.A01`); ST-DataSource.
- **Kolonlar:** `data_source_id UUID PK` · `name TEXT NN` · `source_type TEXT NN` · `connection_config JSONB NN` (sır değeri içermez) · `secret_reference TEXT NN` · `owner_user_id UUID NULL` · `status TEXT NN` (TEST_PENDING/TEST_SUCCEEDED/TEST_FAILED/ACTIVE/INACTIVE/ARCHIVED) · `revision BIGINT NN DEFAULT 1` · `last_test_at TIMESTAMPTZ NULL` · ortak kolonlar
- **PK/FK:** owner → users
- **Unique/Check:** UQ(name); CK source_type; CK status
- **Index:** (status) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `DATA_SOURCE_CREATED/ACTIVATION_DECIDED/DEACTIVATED/ARCHIVED`
- **Optimistic locking:** `revision` · **Immutable:** sır değeri hiçbir kolonda tutulmaz
- **Yazan:** `DataSourceService` (GAP-001 ile PG'ye bağlanır) · **Okuyan:** keşif, çalıştırma, kota

#### `connection_test_results`
- **Amaç:** Bağlantı testi sonuç kanıtı (`D03.C01.W03.A01`); append-only.
- **Kolonlar:** `test_result_id BIGINT IDENTITY PK` · `data_source_id UUID NN` · `succeeded BOOLEAN NN` · `duration_ms INT NN` · `error_class TEXT NULL` · `message TEXT NN` · `source_info JSONB NN` (veri-minimum) · `data_source_revision BIGINT NN` · `tested_at TIMESTAMPTZ NN` · `tested_by TEXT NN`
- **PK/FK:** FK → data_sources
- **Unique/Check:** CK error_class sınıflı (TIMEOUT/AUTH/NETWORK/…)
- **Index:** (data_source_id, tested_at DESC) · **Partition:** yok · **Retention:** `R-OPS`
- **Audit:** `CONNECTION_TESTED` · **Immutable:** evet
- **Yazan:** kaynak mutasyon servisi · **Okuyan:** kaynak detayı, aktivasyon ön koşulu

#### `data_source_activation_requests`
- **Amaç:** Aktivasyon maker-checker talebi (`D03.C02.W01`); ST-ApprovalRequest.
- **Kolonlar:** `activation_request_id UUID PK` · `data_source_id UUID NN` · `data_source_revision BIGINT NN` · `maker_actor_id TEXT NN` · `checker_actor_id TEXT NULL` · `policy_version TEXT NN` · `status TEXT NN` (PENDING/APPROVED/REJECTED/WITHDRAWN/EXPIRED/INVALIDATED) · `decision_reason_code TEXT NULL` · `requested_at TIMESTAMPTZ NN` · `target_at TIMESTAMPTZ NULL` · `expires_at TIMESTAMPTZ NULL` · `business_calendar_version TEXT NULL` · `decided_at TIMESTAMPTZ NULL`
- **PK/FK:** FK → data_sources
- **Unique/Check:** CK status; CK checker_actor_id <> maker_actor_id (karar anında); kısmi UQ(data_source_id) WHERE status='PENDING'
- **Index:** (status) kısmi PENDING · **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** `DATA_SOURCE_ACTIVATION_REQUESTED/DECIDED` · **Immutable:** karar sonrası değişmez
- **Yazan:** kaynak mutasyon servisi · **Okuyan:** onay kuyruğu

#### `data_source_connection_revisions`
- **Amaç:** Bağlantı değişikliği ve geri alma (`D03.C04.W01`); ST-ConnectionRevision.
- **Kolonlar:** `connection_revision_id UUID PK` · `data_source_id UUID NN` · `revision BIGINT NN` · `base_revision BIGINT NN` · `connection_config JSONB NN` · `secret_reference TEXT NN` · `prepared_by_actor_id TEXT NN` · `policy_version TEXT NN` · `reason_code TEXT NN` · `status TEXT NN` (DRAFT/TESTED/EFFECTIVE/SUPERSEDED/ROLLED_BACK) · `created_at TIMESTAMPTZ NN` · `tested_at TIMESTAMPTZ NULL`
- **PK/FK:** FK → data_sources
- **Unique/Check:** UQ(data_source_id, revision); CK revision > 0; CK status
- **Index:** (data_source_id, revision) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `CONNECTION_REVISION_CREATED/APPLIED/ROLLED_BACK`
- **Optimistic locking:** revizyon sırası · **Immutable:** EFFECTIVE sonrası config değişmez
- **Yazan:** kaynak mutasyon servisi · **Okuyan:** bağlantı çözümleme, geri alma

#### `source_usage_policies`
- **Amaç:** Kaynak kullanım politikası — kota, pencere, zaman aşımı (`D03.C03.W01`).
- **Kolonlar:** `policy_id UUID PK` · `policy_version BIGINT NN` · `status TEXT NN` (DRAFT/PENDING_APPROVAL/ACTIVE/RETIRED) · `source_id UUID NULL` · `source_type TEXT NULL` · `max_concurrent_queries INT NN` · `max_workers INT NN` · `query_timeout_seconds INT NN` · `connection_timeout_seconds INT NN DEFAULT 15` · `total_job_timeout_seconds INT NN DEFAULT 3600` · `retry_count INT NN` · `retry_delay_seconds NUMERIC NN` · `rate_limit JSONB NN` · `allowed_windows JSONB NN` · `blocked_windows JSONB NN` · `cpu_limit_percent NUMERIC NULL` · `io_limit_percent NUMERIC NULL` · `peak_hours_behavior TEXT NN` · `timeout_cancel_behavior TEXT NN` · `approved_by TEXT NULL` · `audit_reference TEXT NULL`
- **PK/FK:** source_id → data_sources
- **Unique/Check:** UQ(policy_version, source_id, source_type); CK NOT(source_id AND source_type dolu); CK status
- **Index:** (source_id, source_type) kısmi WHERE status='ACTIVE'
- **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** politika onay olayları · **Optimistic locking:** sürüm · **Immutable:** ACTIVE sürüm değişmez
- **Yazan:** politika servisi · **Okuyan:** `ExecutionStrategyEngine`, job claim kota denetimi

#### `source_health_checks`
- **Amaç:** Periyodik erişilebilirlik kontrolü sonuçları (`D03.C05.W01`).
- **Kolonlar:** `check_id BIGINT IDENTITY PK` · `data_source_id UUID NN` · `reachable BOOLEAN NN` · `latency_ms INT NULL` · `error_class TEXT NULL` · `checked_at TIMESTAMPTZ NN`
- **PK/FK:** FK → data_sources
- **Unique/Check:** — · **Index:** (data_source_id, checked_at DESC)
- **Partition:** yok · **Retention:** `R-OPS`
- **Audit:** sağlık değişiminde `COMPONENT_HEALTH_CHANGED` · **Immutable:** evet
- **Yazan:** sağlık kontrol işi · **Okuyan:** operasyon panosu (GAP-024), kaynak durumu

### D04 — Metadata, Katalog ve Varlık Yönetimi

#### `datasets`
- **Amaç:** Kaynak içinde ölçüm yapılabilen mantıksal veri kümesi (`D04.C02.W01`); ST-Dataset.
- **Kolonlar:** `dataset_id UUID PK` · `data_source_id UUID NN` · `namespace TEXT NN` · `name TEXT NN` · `dataset_type TEXT NN` (TABLE/VIEW/FILE/API/OTHER) · `criticality TEXT NN` (LOW/MEDIUM/HIGH/CRITICAL) · `owner_user_id UUID NULL` · `estimated_row_count BIGINT NULL` · `status TEXT NN DEFAULT 'ACTIVE'` (ACTIVE/SUSPECTED_REMOVED/ARCHIVED) · ortak kolonlar
- **PK/FK:** FK → data_sources, owner → users
- **Unique/Check:** UQ(data_source_id, namespace, name); CK type; CK criticality; CK status
- **Index:** (data_source_id); (status) kısmi WHERE status <> 'ARCHIVED'
- **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `DATASET_UPSERTED/ARCHIVED` · **Optimistic locking:** `version` · **Immutable:** kimlik üçlüsü değişmez
- **Yazan:** keşif uzlaştırma servisi (`D04.C01.W02`) · **Okuyan:** kural formu, profil talebi, katalog

#### `data_fields`
- **Amaç:** Dataset kolonu; sınıflandırma ve hassasiyet taşıyıcısı (`D04.C03`).
- **Kolonlar:** `data_field_id UUID PK` · `dataset_id UUID NN` · `name TEXT NN` · `native_data_type TEXT NN` · `is_nullable BOOLEAN NN` · `is_sensitive BOOLEAN NN` · `classification TEXT NN DEFAULT 'UNCLASSIFIED'` · `classification_policy_version TEXT NN` · `status TEXT NN DEFAULT 'ACTIVE'` · ortak kolonlar
- **PK/FK:** FK → datasets
- **Unique/Check:** UQ(dataset_id, name); CK classification (9 sınıf: UNCLASSIFIED…BANK_SECRET)
- **Index:** (dataset_id); (classification) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `FIELD_CLASSIFICATION_CHANGED` · **Optimistic locking:** `version` · **Immutable:** —
- **Yazan:** keşif uzlaştırma + sınıflandırma servisi · **Okuyan:** maskeleme, kural kapsamı, veri-minimum kanıt

#### `discovery_scopes`
- **Amaç:** Keşif kapsamı — dâhil/hariç örüntüleri (`D04.C01.W01.A02`).
- **Kolonlar:** `scope_id UUID PK` · `data_source_id UUID NN` · `include_patterns JSONB NN DEFAULT '[]'` · `exclude_patterns JSONB NN DEFAULT '[]'` · ortak kolonlar
- **PK/FK:** FK → data_sources
- **Unique/Check:** UQ(data_source_id) WHERE etkin · **Index:** —
- **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `DISCOVERY_SCOPE_CHANGED` · **Optimistic locking:** `version` · **Immutable:** —
- **Yazan:** keşif servisi · **Okuyan:** keşif yürütücü

#### `metadata_discovery_results`
- **Amaç:** Keşif koşusu kaydı ve durum makinesi (`D04.C01.W01.A01`).
- **Kolonlar:** `discovery_id BIGINT IDENTITY PK` · `data_source_id UUID NN` · `status TEXT NN` (RUNNING/SUCCESS/PARTIAL/TECHNICAL_ERROR) · `duration_ms INT NULL` · `scanned_object_count INT NN DEFAULT 0` · `error_class TEXT NULL` · `message TEXT NULL` · `changes JSONB NN DEFAULT '{}'` · `discovered_at TIMESTAMPTZ NN` · `requested_by TEXT NN`
- **PK/FK:** FK → data_sources
- **Unique/Check:** CK status; CK error_class sınıflı
- **Index:** (data_source_id, discovery_id DESC) · **Partition:** yok · **Retention:** `R-OPS`
- **Audit:** `METADATA_DISCOVERY_STARTED/COMPLETED` · **Immutable:** SUCCESS/PARTIAL sonrası değişmez
- **Yazan:** keşif orkestratörü (GAP-004) · **Okuyan:** fark hesaplama, kaynak detayı

#### `metadata_diffs`
- **Amaç:** Keşif farkı — eklenen/kaldırılan/değişen (`D04.C01.W02.A01/A02`).
- **Kolonlar:** `diff_id UUID PK` · `discovery_id BIGINT NN` · `added JSONB NN` · `removed JSONB NN` · `changed JSONB NN` · `status TEXT NN` (PENDING_REVIEW/AUTO_APPLIED/APPLIED) · `applied_by TEXT NULL` · `applied_at TIMESTAMPTZ NULL` · ortak kolonlar
- **PK/FK:** FK → metadata_discovery_results
- **Unique/Check:** CK status · **Index:** (discovery_id)
- **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `METADATA_DIFF_COMPUTED/APPLIED` · **Optimistic locking:** `version` · **Immutable:** APPLIED sonrası fark içeriği değişmez
- **Yazan:** fark hesaplama servisi · **Okuyan:** katalog değişiklik ekranı, şema değişimi zinciri

#### `classification_candidates`
- **Amaç:** Alan sınıflandırma önerileri ve karar kaydı (`D04.C03.W02`).
- **Kolonlar:** `candidate_id UUID PK` · `data_field_id UUID NN` · `proposed_classification TEXT NN` · `confidence NUMERIC(5,4) NULL` · `evidence JSONB NN` · `status TEXT NN` (PROPOSED/CONFIRMED/REJECTED) · `decided_by TEXT NULL` · ortak kolonlar
- **PK/FK:** FK → data_fields
- **Unique/Check:** CK status · **Index:** (data_field_id, status)
- **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `FIELD_CLASSIFICATION_CHANGED` · **Immutable:** karar sonrası değişmez
- **Yazan:** sınıflandırma öneri motoru · **Okuyan:** sınıflandırma ekranı

#### `schema_changes`
- **Amaç:** Şema değişikliği tespiti, sınıflandırma ve kararı (`D04.C04`); ST-SchemaChange.
- **Kolonlar:** `schema_change_id UUID PK` · `data_source_id UUID NN` · `dataset_id UUID NULL` · `data_field_id UUID NULL` · `change_type TEXT NN` (COLUMN_ADDED/COLUMN_REMOVED/TYPE_NARROWED/NULLABILITY_TIGHTENED/…) · `classification TEXT NN` (ADDITIVE/BREAKING/NEUTRAL) · `status TEXT NN` (PENDING_DECISION/ACCEPTED/BLOCKED/AUTO_BLOCKED) · `decided_by TEXT NULL` · `decided_at TIMESTAMPTZ NULL` · `decision_reason TEXT NULL` · ortak kolonlar
- **PK/FK:** FK → data_sources/datasets/data_fields
- **Unique/Check:** CK change_type; CK classification; CK status
- **Index:** (status) kısmi PENDING_DECISION; (data_source_id, created_at DESC)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `SCHEMA_CHANGE_CLASSIFIED/DECIDED` · **Optimistic locking:** `version` · **Immutable:** karar sonrası değişmez
- **Yazan:** şema fark sınıflandırıcı (GAP-019) · **Okuyan:** ölçüm blokajı, kural `REVIEW_REQUIRED` tetikleyici

### D05 — Profilleme ve Veri Karakterizasyonu

#### `data_profiles`
- **Amaç:** Profil çalıştırması kaydı (`D05.C01`); ST-Profile.
- **Kolonlar:** `profile_id UUID PK` · `dataset_id UUID NN` · `execution_id UUID NULL` · `method TEXT NN` (FULL/SAMPLE/PARTITION/AGGREGATE) · `sample_ratio NUMERIC(5,4) NULL` · `sample_seed BIGINT NULL` · `policy_version TEXT NN` · `status TEXT NN` (QUEUED/RUNNING/SUCCESS/PARTIAL/TECHNICAL_ERROR/CANCEL_REQUESTED/CANCELLED) · `duration_ms INT NULL` · `error_class TEXT NULL` · `message TEXT NULL` · `requested_by TEXT NN` · `started_at TIMESTAMPTZ NULL` · `finished_at TIMESTAMPTZ NULL` · `cancelled_by TEXT NULL` · ortak kolonlar
- **PK/FK:** FK → datasets
- **Unique/Check:** CK method; CK status · **Index:** (dataset_id, started_at DESC); (status) kısmi RUNNING
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `PROFILE_REQUESTED/CANCELLED` · **Optimistic locking:** `version` · **Immutable:** SUCCESS sonrası metrikler değişmez
- **Yazan:** profil yürütme orkestratörü (GAP-005) · **Okuyan:** metrik tabloları, baseline, karşılaştırma

#### `profile_field_metrics`
- **Amaç:** Alan bazlı temel metrikler — normalize edilmiş (`D05.C02.W01`).
- **Kolonlar:** `metric_id BIGINT IDENTITY PK` · `profile_id UUID NN` · `data_field_id UUID NN` · `metrics JSONB NN` (null oranı, tekil sayı, min/max, boş sayı…) · ortak kolonlar yok (türetilmiş kanıt)
- **PK/FK:** FK → data_profiles, → data_fields
- **Unique/Check:** UQ(profile_id, data_field_id) · **Index:** (profile_id)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** profil kaydına gömülü · **Immutable:** evet
- **Yazan:** profil yürütücü · **Okuyan:** snapshot detayı, karşılaştırma

#### `profile_distributions`
- **Amaç:** Değer dağılımları — Top-N, maskeli (`D05.C02.W02.A01`).
- **Kolonlar:** `distribution_id BIGINT IDENTITY PK` · `profile_id UUID NN` · `data_field_id UUID NN` · `top_values JSONB NN` (maskeli) · `histogram JSONB NULL` · ortak kolonlar yok
- **PK/FK:** FK → data_profiles, → data_fields
- **Unique/Check:** UQ(profile_id, data_field_id) · **Index:** (profile_id)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** profil kaydına gömülü · **Immutable:** evet · Veri-minimum: ham değer değil maske özet
- **Yazan:** profil yürütücü · **Okuyan:** inceleme kanıtı (`D09.C02.W02.A02`)

#### `profile_outliers`
- **Amaç:** Aykırı değer adayları (`D05.C02.W02.A02`).
- **Kolonlar:** `outlier_id BIGINT IDENTITY PK` · `profile_id UUID NN` · `data_field_id UUID NN` · `candidates JSONB NN` (maskeli) · ortak kolonlar yok
- **PK/FK:** FK → data_profiles
- **Unique/Check:** — · **Index:** (profile_id)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** profil kaydına gömülü · **Immutable:** evet
- **Yazan:** profil yürütücü (`_outlier_candidates`) · **Okuyan:** inceleme kanıtı

#### `profile_baselines`
- **Amaç:** Onaylı ve sürümlü baseline varlığı (`D05.C03`); ST-ProfileBaseline.
- **Kolonlar:** `baseline_id UUID PK` · `dataset_id UUID NN` · `profile_id UUID NN` · `status TEXT NN` (ACTIVE/SUPERSEDED/INVALIDATED) · `set_by TEXT NN` · `set_at TIMESTAMPTZ NN` · `invalidated_by TEXT NULL` · `invalidated_at TIMESTAMPTZ NULL` · `reason TEXT NULL` · ortak kolonlar
- **PK/FK:** FK → datasets, → data_profiles
- **Unique/Check:** CK status; kısmi UQ(dataset_id) WHERE status='ACTIVE'
- **Index:** (dataset_id, status) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `PROFILE_BASELINE_SET/INVALIDATED` · **Optimistic locking:** `version` · **Immutable:** geçmiş baseline kayıtları
- **Yazan:** baseline servisi (GAP-005) · **Okuyan:** drift hükmü (`BR-D05-008`)

#### `profile_comparisons`
- **Amaç:** İki profilin deterministik karşılaştırması (`D05.C04.W01`).
- **Kolonlar:** `comparison_id UUID PK` · `dataset_id UUID NN` · `baseline_profile_id UUID NN` · `current_profile_id UUID NN` · `policy_version TEXT NULL` · `status TEXT NN` (COMPLETED/CONFIGURATION_ERROR/INSUFFICIENT_HISTORY/INCOMPATIBLE) · `anomaly_candidate BOOLEAN NULL` · `result JSONB NN` · `message TEXT NULL` · `requested_by TEXT NULL` · ortak kolonlar
- **PK/FK:** FK → datasets, → data_profiles (2 kez)
- **Unique/Check:** CK status · **Index:** (dataset_id, created_at DESC)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** karşılaştırma olayı · **Immutable:** evet (sonuç değişmez)
- **Yazan:** `ProfileComparisonService` · **Okuyan:** drift hükmü, profil sayfası

#### `drift_judgments`
- **Amaç:** Drift hükmü ve sınıflandırma kaydı (`D05.C04.W02`).
- **Kolonlar:** `judgment_id UUID PK` · `comparison_id UUID NN` · `verdict TEXT NN` (7 aile) · `severity TEXT NN` · `basis JSONB NN` · `judged_at TIMESTAMPTZ NN` · ortak kolonlar
- **PK/FK:** FK → profile_comparisons
- **Unique/Check:** CK verdict; UQ(comparison_id) · **Index:** (judged_at DESC)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** drift olayı · **Immutable:** evet · Drift'ten sorun üretimi GAP-006'ya bağlanır
- **Yazan:** drift değerlendirici · **Okuyan:** profil sayfası, sorun üretimi

### D06 — Kalite Kural Yönetimi

#### `rule_templates`
- **Amaç:** Kural şablonu kütüphanesi (`D06.C01.W02`); ST-RuleTemplate. Mevcut `templates.py` kod sabiti yerine yönetilebilir varlık.
- **Kolonlar:** `template_id UUID PK` · `code TEXT NN UQ` · `name TEXT NN` · `rule_type TEXT NN` · `parameter_schema JSONB NN` · `status TEXT NN` (DRAFT/PUBLISHED/DEPRECATED) · `published_by TEXT NULL` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** UQ(code); CK status
- **Index:** (status) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `RULE_TEMPLATE_DRAFTED/PUBLISHED/DEPRECATED`
- **Optimistic locking:** `version` · **Immutable:** PUBLISHED parametre şeması değişmez (kritik hatada `REVIEW_REQUIRED` tetiklenir, `BR-D06-012`)
- **Yazan:** şablon servisi (GAP-020) · **Okuyan:** kural oluşturma (`BR-D06-001`)

#### `quality_rules`
- **Amaç:** Kuralın kimlik ve yaşam döngüsü taşıyıcısı (`D06.C02.W01`); ST-QualityRule.
- **Kolonlar:** `quality_rule_id UUID PK` · `code TEXT NN UQ` · `name TEXT NN` · `dataset_id UUID NN` · `field_ids JSONB NN` · `primary_dimension TEXT NN` (7 boyut) · `owner_user_id TEXT NN` · `status TEXT NN` (DRAFT/ACTIVE/PASSIVE/REVIEW_REQUIRED/ARCHIVED) · ortak kolonlar
- **PK/FK:** dataset_id → datasets (FK hedefte eklenir)
- **Unique/Check:** UQ(code); CK dimension; CK status
- **Index:** (dataset_id); (status) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `QUALITY_RULE_CREATED/DEACTIVATED/ARCHIVED`, `RULE_VERSION_ACTIVATED`
- **Optimistic locking:** `version` (hedefte eklenir) · **Immutable:** code değişmez
- **Yazan:** `RuleCreatorService`/`RuleMutationService` · **Okuyan:** çalıştırma planı, katalog

#### `rule_versions`
- **Amaç:** Kuralın değişmez, onaylanabilir, çalıştırılabilir sürümü (`D06.C02.W02`); ST-RuleVersion.
- **Kolonlar:** `rule_version_id UUID PK` · `quality_rule_id UUID NN` · `version_no INT NN` · `rule_type TEXT NN` (8 tip) · `definition JSONB NN` · `definition_digest TEXT NN` · `threshold NUMERIC NN` · `weight NUMERIC NN` · `criticality TEXT NN` · `template_id UUID NULL` · `status TEXT NN` (DRAFT/SEALED/PENDING_APPROVAL/APPROVED/ACTIVE/SUPERSEDED) · `prepared_by_actor_id TEXT NN` · `sealed_at TIMESTAMPTZ NULL` · ortak kolonlar
- **PK/FK:** FK → quality_rules, → rule_templates
- **Unique/Check:** UQ(quality_rule_id, version_no); CK rule_type; CK criticality; CK status
- **Index:** (quality_rule_id, version_no DESC); (status) kısmi ACTIVE
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `RULE_VERSION_CREATED`, onay olayları, `RULE_VERSION_ACTIVATED`
- **Optimistic locking:** `version` · **Immutable:** SEALED sonrası definition/threshold/weight değişmez (`BR-D06-003`); `definition_digest` sonuçlara damgalanır (`BR-D06-015`)
- **Yazan:** `RuleMutationService` · **Okuyan:** çalıştırma motoru, skorlama

#### `rule_test_results`
- **Amaç:** Sınırlı veriyle test sonucu kanıtı (`D06.C02.W03`).
- **Kolonlar:** `rule_test_result_id UUID PK` · `rule_version_id UUID NN` · `status TEXT NN` (SUCCESS/TECHNICAL_ERROR) · `record_limit INT NN` · `checked_count INT NN` · `passed_count INT NN` · `failed_count INT NN` · `not_evaluated_count INT NN` · `success_rate NUMERIC(7,4) NULL` · `preview_score NUMERIC(7,4) NULL` · `official_score_included INT NN DEFAULT 0` · `error_class TEXT NULL` · `message TEXT NN` · ortak kolonlar
- **PK/FK:** FK → rule_versions
- **Unique/Check:** CK status; CK official_score_included ∈ {0,1}
- **Index:** (rule_version_id, created_at DESC) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** test olayı · **Immutable:** evet · `BR-D06-008`: resmî skora girmez
- **Yazan:** `RuleMutationService.test` · **Okuyan:** onay ön koşulu (`BR-D06-005`), kural detayı

#### `rule_approval_requests`
- **Amaç:** Kural sürümü maker-checker onayı (`D06.C02.W04`); ST-ApprovalRequest.
- **Kolonlar:** `approval_request_id UUID PK` · `rule_version_id UUID NN` · `maker_actor_id TEXT NN` · `checker_actor_id TEXT NULL` · `policy_version TEXT NN` · `status TEXT NN` (PENDING/APPROVED/REJECTED/WITHDRAWN/EXPIRED) · `decision_reason_code TEXT NULL` · `requested_at TIMESTAMPTZ NN` · `target_at TIMESTAMPTZ NULL` · `expires_at TIMESTAMPTZ NULL` · `business_calendar_version TEXT NULL` · `decided_at TIMESTAMPTZ NULL`
- **PK/FK:** FK → rule_versions
- **Unique/Check:** CK status; CK checker <> maker; kısmi UQ(rule_version_id) WHERE status='PENDING'
- **Index:** (status, expires_at) kısmi PENDING
- **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** `RULE_APPROVAL_REQUESTED/DECIDED/WITHDRAWN/EXPIRED`
- **Immutable:** karar sonrası değişmez · Süre aşımı geçişi zamanlayıcı gerektirir (GAP-003 altyapısı)
- **Yazan:** `RuleMutationService` · **Okuyan:** onay kuyruğu UI

#### `rule_dependencies`
- **Amaç:** Kurallar arası bağımlılık grafı (`D06.C04.W01`).
- **Kolonlar:** `dependency_id UUID PK` · `from_rule_id UUID NN` · `to_rule_id UUID NN` · `dependency_type TEXT NN` · ortak kolonlar
- **PK/FK:** FK → quality_rules (2 kez)
- **Unique/Check:** UQ(from_rule_id, to_rule_id); CK from <> to; döngü uygulama düzeyinde reddedilir (`BR-D06-010`)
- **Index:** (to_rule_id) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** bağımlılık olayı · **Immutable:** —
- **Yazan:** bağımlılık çözümleyici (GAP-020) · **Okuyan:** şema değişikliği etki analizi

#### `rule_conflicts`
- **Amaç:** Çakışma/mükerrerlik tespit kaydı (`D06.C04.W02`).
- **Kolonlar:** `conflict_id UUID PK` · `rule_a_id UUID NN` · `rule_b_id UUID NN` · `conflict_type TEXT NN` (DUPLICATE/OVERLAPPING) · `evidence JSONB NN` · `status TEXT NN` (DETECTED/RESOLVED) · ortak kolonlar
- **PK/FK:** FK → quality_rules (2 kez)
- **Unique/Check:** UQ(rule_a_id, rule_b_id, conflict_type) WHERE status='DETECTED'
- **Index:** (status) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** çakışma olayı · **Immutable:** tespit kanıtı değişmez
- **Yazan:** çakışma dedektörü (`BR-D06-011`) · **Okuyan:** kural formu uyarıları

### D07 — Yürütme, Zamanlama ve İş Kuyruğu

#### `rule_executions`
- **Amaç:** Çalıştırma kaydı (`D07.C01`); ST-RuleExecution.
- **Kolonlar:** `execution_id UUID PK` · `execution_type TEXT NN` (MANUAL/SCHEDULED) · `schedule_id UUID NULL` · `status TEXT NN` (QUEUED/RUNNING/CANCEL_REQUESTED/SUCCESS/PARTIAL/TECHNICAL_ERROR/TIMEOUT/CANCELLED) · `execution_mode TEXT NN DEFAULT 'OFFICIAL'` (OFFICIAL/SHADOW) · `idempotency_key_hash TEXT NN UQ` · `payload_hash TEXT NN` · `rule_version_ids JSONB NN` · `scope JSONB NN` · `triggered_by TEXT NN` · `correlation_id UUID NN` · `source_ids JSONB NN` · `workload_class TEXT NN` (HEAVY/LIGHT) · `error_class TEXT NULL` · `attempt_count INT NN` · `created_at / started_at / finished_at / cancelled_at TIMESTAMPTZ` · `cancel_requested_by TEXT NULL` · `cancel_reason TEXT NULL` · ortak kolonlar (version hariç — durum geçişleri worker tarafından sürüm kontrolüyle)
- **PK/FK:** schedule_id → schedules
- **Unique/Check:** UQ(idempotency_key_hash); CK type/status/workload_class/execution_mode
- **Index:** (status); (created_at DESC); (schedule_id)
- **Partition:** yok (sıcak sorgu) · **Retention:** `R-EVIDENCE`
- **Audit:** `EXECUTION_STARTED/TECHNICAL_ERROR/TIMED_OUT/CANCEL_REQUESTED/CANCELLED`
- **Optimistic locking:** durum geçişlerinde koşullu UPDATE · **Immutable:** idempotency/payload alanları
- **Yazan:** `PostgreSQLExecutionStartService/CancelService`, zamanlayıcı (GAP-003) · **Okuyan:** çalıştırma listesi, sonuç kaydı

#### `execution_attempts`
- **Amaç:** Çalıştırma deneme kayıtları (`D07.C04.W01`).
- **Kolonlar:** `attempt_id UUID PK` · `execution_id UUID NN` · `attempt_no INT NN` · `status TEXT NN` · `error_class TEXT NULL` · `retryable INT NN` · ortak kolonlar
- **PK/FK:** FK → rule_executions
- **Unique/Check:** UQ(execution_id, attempt_no); CK status
- **Index:** (execution_id) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** retry olayları · **Immutable:** evet
- **Yazan:** yürütme motoru · **Okuyan:** teknik hata analizi

#### `execution_partitions`
- **Amaç:** Bölümlü yürütme planı ve checkpoint (`D07.C05`).
- **Kolonlar:** `partition_id UUID PK` · `execution_id UUID NN` · `partition_no INT NN` · `scope JSONB NN` · `status TEXT NN` (PENDING/RUNNING/COMPLETED/FAILED) · `checkpoint JSONB NULL` · `completed_at TIMESTAMPTZ NULL` · ortak kolonlar
- **PK/FK:** FK → rule_executions
- **Unique/Check:** UQ(execution_id, partition_no); CK status
- **Index:** (execution_id) · **Partition:** yok · **Retention:** `R-OPS`
- **Audit:** çalıştırma audit'ine gömülü · **Immutable:** tamamlanan bölüm
- **Yazan:** bölüm planlayıcı · **Okuyan:** devam/checkpoint kurtarma

#### `schedules`
- **Amaç:** Kural çalıştırma zamanlaması (`D07.C02.W01`); ST-Schedule.
- **Kolonlar:** `schedule_id UUID PK` · `name TEXT NN UQ` · `schedule_type TEXT NN` (ONCE/DAILY/WEEKLY/MONTHLY) · `timezone_name TEXT NN` · `rule_version_ids JSONB NN` · `created_by TEXT NN` · `local_time TEXT NULL` · `once_at TIMESTAMPTZ NULL` · `day_of_week INT NULL` · `day_of_month INT NULL` · `status TEXT NN DEFAULT 'ACTIVE'` (ACTIVE/PAUSED/DELETED) · `paused_until TIMESTAMPTZ NULL` · `deleted_at TIMESTAMPTZ NULL` · `next_run_at TIMESTAMPTZ NULL` · `last_triggered_at TIMESTAMPTZ NULL` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** UQ(name); CK type; CK status
- **Index:** (next_run_at) kısmi WHERE status='ACTIVE'
- **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `SCHEDULE_CREATED/STATE_CHANGED/DELETED/TRIGGERED`
- **Optimistic locking:** `version` · **Immutable:** DELETED kayıt geçmiş bağı korunur
- **Yazan:** zamanlama servisi (GAP-003) · **Okuyan:** zamanlayıcı daemon

#### `schedule_missed_runs`
- **Amaç:** Kaçırılan çalışma kararı (`D07.C02.W02.A02`).
- **Kolonlar:** `missed_run_id BIGINT IDENTITY PK` · `schedule_id UUID NN` · `missed_at TIMESTAMPTZ NN` · `decision TEXT NN` (COMPENSATE/SKIP/RUN_ONCE) · `policy_version TEXT NN` · ortak kolonlar yok
- **PK/FK:** FK → schedules
- **Unique/Check:** CK decision · **Index:** (schedule_id, missed_at DESC)
- **Partition:** yok · **Retention:** `R-OPS`
- **Audit:** `SCHEDULE_RUN_MISSED` · **Immutable:** evet
- **Yazan:** zamanlayıcı daemon · **Okuyan:** operasyon panosu

#### `persistent_jobs`
- **Amaç:** Kalıcı iş kuyruğu (`D07.C03.W01.A01`); ST-Job. Mevcut `background_jobs` tablosunun hedef karşılığı.
- **Kolonlar:** `job_id UUID PK` · `job_type TEXT NN` · `payload JSONB NN` · `status TEXT NN` (AVAILABLE/CLAIMED/RUNNING/COMPLETED/DEAD_LETTERED/BLOCKED/CANCELLED) · `priority INT NN DEFAULT 0` · `idempotency_key TEXT NULL` · `available_at TIMESTAMPTZ NN` · `claimed_by TEXT NULL` · `lease_expires_at TIMESTAMPTZ NULL` · `last_heartbeat_at TIMESTAMPTZ NULL` · `progress INT NULL` (0-100) · `attempt_count INT NN DEFAULT 0` · `completion_outcome TEXT NULL` · `completed_at TIMESTAMPTZ NULL` · `cancel_requested_at TIMESTAMPTZ NULL` · `cancel_requested_by TEXT NULL` · `cancel_reason_code TEXT NULL` · `last_error_class TEXT NULL` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** UQ(job_type, idempotency_key); CK status; CK priority >= 0; CK progress 0-100
- **Index:** (status, priority DESC, available_at, created_at, job_id) claim sırası; (status, lease_expires_at) kurtarma
- **Partition:** yok (sıcak kuyruk) · **Retention:** `R-OPS` — tamamlanan işler politika süresi sonra arındırılır
- **Audit:** `JOB_ENQUEUED/CLAIMED/RETRY_SCHEDULED/LEASE_RECLAIMED/DEAD_LETTERED/MANUALLY_INTERVENED`
- **Optimistic locking:** `version` · **Immutable:** payload ve idempotency değişmez
- **Yazan:** `PostgreSQLJobQueueRepository`, `PersistentJobWorker` · **Okuyan:** operasyon yüzeyi (GAP-018)

#### `dead_letter_records`
- **Amaç:** Dead-letter kaydı (`D07.C04.W04`); ST-DeadLetterRecord. Mevcut `job_dead_letters` karşılığı.
- **Kolonlar:** `dead_letter_id UUID PK` · `job_id UUID NN` · `error_class TEXT NN` · `attempt_count INT NN` · `status TEXT NN` (OPEN/REPROCESSED/CLOSED) · `reprocessed_at TIMESTAMPTZ NULL` · `reprocessed_by TEXT NULL` · `closed_at TIMESTAMPTZ NULL` · `closure_reason TEXT NULL` · `measurement_gap_marked BOOLEAN NN DEFAULT FALSE` · `audit_event_id UUID NULL` · ortak kolonlar
- **PK/FK:** FK → persistent_jobs
- **Unique/Check:** CK status; CK attempt_count > 0; CK CLOSED iken closure_reason NOT NULL
- **Index:** (status, created_at, dead_letter_id) · **Partition:** yok · **Retention:** `R-OPS`
- **Audit:** `DEAD_LETTER_REPROCESSED/CLOSED` · **Optimistic locking:** `version` · **Immutable:** hata kanıtı alanları
- **Yazan:** worker (taşıma), operasyon servisi (GAP-018) · **Okuyan:** operasyon yüzeyi

#### `workers`
- **Amaç:** Worker kayıt ve sağlık durumu (`D07.C04.W03.A02`).
- **Kolonlar:** `worker_id UUID PK` · `hostname TEXT NN` · `capacity INT NN` · `supported_job_types JSONB NN` · `state TEXT NN` (STARTING/ACTIVE/DRAINING/STOPPED/STALE) · `last_seen_at TIMESTAMPTZ NN` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** CK state
- **Index:** (state) · **Partition:** yok · **Retention:** `R-OPS`
- **Audit:** `WORKER_STATE_CHANGED` · **Immutable:** —
- **Yazan:** worker süreci (GAP-002) · **Okuyan:** operasyon panosu

### D08 — Ölçüm, Sonuç ve Skorlama

#### `rule_execution_results`
- **Amaç:** Kural sonucu — sayaçlar, yeterlilik ve veri-minimum kanıt (`D08.C01.W01.A01`).
- **Kolonlar:** `rule_result_id UUID PK` · `execution_id UUID NN` · `rule_version_id UUID NN` · `rule_version_digest TEXT NN` · `population_count BIGINT` · `eligible_count BIGINT` · `evaluated_count BIGINT` · `passed_count BIGINT` · `failed_count BIGINT` · `excluded_count BIGINT` · `technical_error_count BIGINT` · `unknown_count BIGINT` · `measurement_status TEXT` (QUALIFIED/PARTIALLY_QUALIFIED/NOT_QUALIFIED) · `completed_partitions JSONB NN` · `eligible_for_official_scoring INT NN` · `eligible_for_notification INT NN DEFAULT 1` · `eligible_for_sla INT NN DEFAULT 1` · `eligible_for_auto_issue INT NN DEFAULT 1` · `evidence JSONB NN DEFAULT '{}'` · `recorded_at TIMESTAMPTZ NN` · ortak kolonlar yok (değişmez kanıt)
- **PK/FK:** FK → rule_executions; FK → rule_versions (hedefte eklenir)
- **Unique/Check:** UQ(execution_id, rule_version_id)
- **Index:** (execution_id); (rule_version_id, recorded_at DESC)
- **Partition:** aylık RANGE(`recorded_at`) · **Retention:** `R-EVIDENCE`
- **Audit:** `RULE_RESULT_RECORDED` · **Immutable:** evet — istisna dahil hiçbir yol değiştiremez (`BR-D09-011`); bastırma `exception_suppressions`'a yazılır
- **Yazan:** sonuç yazıcı (worker) · **Okuyan:** yeterlilik, skorlama, sorun üretimi, inceleme kanıtı

#### `failure_samples`
- **Amaç:** Maskeli başarısız kayıt örneği (`D08.C01.W02.A01`).
- **Kolonlar:** `sample_id UUID PK` · `rule_result_id UUID NN` · `masked_values JSONB NN` · `sample_count INT NN` · ortak kolonlar yok
- **PK/FK:** FK → rule_execution_results
- **Unique/Check:** veri-minimum doğrulaması uygulama düzeyinde
- **Index:** (rule_result_id) · **Partition:** aylık (result ile eş) · **Retention:** `R-EVIDENCE`
- **Audit:** kanıt erişimi `ISSUE_EVIDENCE_VIEWED` hassas sınıf · **Immutable:** evet
- **Yazan:** sonuç yazıcı · **Okuyan:** inceleme kanıtı (`evidence.sample.read`)

#### `measurement_qualifications`
- **Amaç:** Ölçüm yeterliliği hükmünün kalıcı kaydı (`D08.C02.W02.A01`).
- **Kolonlar:** `qualification_id UUID PK` · `rule_result_id UUID NN UQ` · `verdict TEXT NN` (QUALIFIED/PARTIALLY_QUALIFIED/NOT_QUALIFIED) · `coverage JSONB NN` · `technical_health NUMERIC(7,4) NN` · `policy_version TEXT NN` · ortak kolonlar yok
- **PK/FK:** FK → rule_execution_results
- **Unique/Check:** UQ(rule_result_id); CK verdict
- **Index:** — · **Partition:** aylık · **Retention:** `R-EVIDENCE`
- **Audit:** `MEASUREMENT_QUALIFICATION_ISSUED` · **Immutable:** evet
- **Yazan:** yeterlilik değerlendirici · **Okuyan:** skorlama, dashboard yeterlilik göstergesi

#### `quality_scores`
- **Amaç:** Kalite skoru kaydı — tüm kapsam seviyeleri (`D08.C03`); ST-QualityScore. Mevcut sistemde **tablo yoktur**.
- **Kolonlar:** `quality_score_id UUID PK` · `publication_id UUID NULL` · `scope_type TEXT NN` (RULE/DATASET/DIMENSION/DOMAIN/ENTERPRISE) · `scope_id UUID NULL` · `score_value NUMERIC(7,4) NULL` · `score_status TEXT NN` (CALCULATED/NOT_QUALIFIED/NO_DATA/PUBLISHED/SUPERSEDED) · `qualification_verdict TEXT NULL` · `rule_version_digest TEXT NULL` · `policy_version TEXT NN` · `veto_applied BOOLEAN NN DEFAULT FALSE` · `veto_rule_version_id UUID NULL` · `raw_score_value NUMERIC(7,4) NULL` · `included_component_count INT NULL` · `excluded_component_count INT NULL` · `calculated_at TIMESTAMPTZ NN` · ortak kolonlar yok (değişmez)
- **PK/FK:** FK → score_publications
- **Unique/Check:** CK scope_type; CK score_status; CK veto ise raw_score dolu
- **Index:** (scope_type, scope_id, calculated_at DESC); (publication_id)
- **Partition:** aylık RANGE(calculated_at) · **Retention:** `R-EVIDENCE`
- **Audit:** `RULE_SCORE_CALCULATED/SCORE_AGGREGATED/CRITICAL_VETO_APPLIED`
- **Immutable:** evet — skor düzeltilmez, yeni hesap yeni kayıttır
- **Yazan:** `ScoringService` + yayım servisi (GAP-008) · **Okuyan:** skor API, dashboard, rapor

#### `score_publications`
- **Amaç:** Atomik skor yayımı dönem kaydı (`D08.C03.W03.A01`).
- **Kolonlar:** `publication_id UUID PK` · `period TEXT NN` · `status TEXT NN` (PUBLISHED/SUPERSEDED) · `published_at TIMESTAMPTZ NN` · `policy_version TEXT NN` · ortak kolonlar yok
- **PK/FK:** — · **Unique/Check:** CK status; UQ(period) WHERE status='PUBLISHED'
- **Index:** (published_at DESC) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `SCORE_PUBLISHED` · **Immutable:** evet
- **Yazan:** yayım servisi · **Okuyan:** dönem karşılaştırma (`D08.C04.W02`)

#### `score_contribution_graphs`
- **Amaç:** Açıklanabilir katkı grafı (`D08.C04.W01.A01`).
- **Kolonlar:** `quality_score_id UUID PK` · `execution_id UUID NN` · `scope_type TEXT NN` · `scope_id TEXT NULL` · `graph JSONB NN` · ortak kolonlar yok
- **PK/FK:** FK → quality_scores (hedefte)
- **Unique/Check:** CK scope_type ∈ {RULE,DATASET,DIMENSION,SOURCE,ENTERPRISE}
- **Index:** (execution_id, scope_type, scope_id)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `SCORE_CONTRIBUTION_GRAPH_BUILT` · **Immutable:** evet
- **Yazan:** `contributions.py` · **Okuyan:** skor detayı, yeniden üretim doğrulaması

#### `risk_ratings`
- **Amaç:** Risk derecelendirmesi (`D08.C05.W02.A01`).
- **Kolonlar:** `rating_id UUID PK` · `scope_type TEXT NN` · `scope_id UUID NN` · `risk_level TEXT NN` (LOW/MEDIUM/HIGH/CRITICAL) · `factors JSONB NN` · `rated_at TIMESTAMPTZ NN` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** CK risk_level
- **Index:** (scope_type, scope_id, rated_at DESC) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** risk olayı · **Immutable:** geçmiş kayıtlar
- **Yazan:** risk hesaplayıcı (GAP-006 öncelik girişi) · **Okuyan:** sorun önceliği, dashboard

### D09 — Sorun, İstisna ve Remediation

#### `issues`
- **Amaç:** Kalite/teknik/sözleşme sorunu (`D09.C01/W02`); ST-Issue. Mevcut `data_quality_issues` karşılığı.
- **Kolonlar:** `issue_id UUID PK` · `issue_no TEXT NN UQ` · `source_event_id UUID NULL` · `source_event_type TEXT NN` (QUALITY/TECHNICAL/CONTRACT/MANUAL) · `trigger_type TEXT NN` · `scope_type TEXT NN` · `scope_id UUID NN` · `status TEXT NN` (NEW/ASSIGNED/INVESTIGATING/WAITING_FOR_RESOLUTION/RESOLVED/VERIFIED/CLOSED/CANCELLED) · `priority TEXT NN` (LOW/MEDIUM/HIGH/CRITICAL) · `assignee_user_id UUID NULL` · `deduplication_key_digest TEXT NN` · `payload_digest TEXT NN` · `occurrence_count BIGINT NN DEFAULT 1` · `investigation_started_at TIMESTAMPTZ NULL` · `hold_reason TEXT NULL` · `expected_resolution_at TIMESTAMPTZ NULL` · `sla_paused_at TIMESTAMPTZ NULL` · `last_seen_at TIMESTAMPTZ NN` · `cancel_reason TEXT NULL` · ortak kolonlar
- **PK/FK:** assignee → users
- **Unique/Check:** UQ(issue_no); CK source_event_type (MANUAL/CONTRACT hedefte eklenir); CK trigger_type; CK status; CK priority; CK occurrence_count >= 1; CK WAITING iken hold_reason NOT NULL
- **Index:** (scope_type, scope_id, updated_at DESC); (assignee_user_id, status, updated_at DESC); (deduplication_key_digest) WHERE status açık
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `ISSUE_CREATED/ASSIGNED/INVESTIGATION_STARTED/PUT_ON_HOLD/RESOLVED/VERIFIED/CLOSED/REOPENED/RECURRENCE_RECORDED`
- **Optimistic locking:** `version` · **Immutable:** dedup anahtarı, payload_digest
- **Yazan:** sorun üretim servisi (GAP-006), issue mutasyon servisleri · **Okuyan:** sorun listesi, SLA, bildirim

#### `issue_history`
- **Amaç:** Sorun durum/atama geçiş geçmişi — append-only (`D09.C02`).
- **Kolonlar:** `sequence_no BIGINT IDENTITY PK` · `history_id UUID NN UQ` · `issue_id UUID NN` · `action TEXT NN` · `actor_id TEXT NN` · `old_status / new_status TEXT` · `old_assignee_user_id / new_assignee_user_id UUID` · `old_priority / new_priority TEXT` · `resolution_id UUID NULL` · `verification_id UUID NULL` · `occurred_at TIMESTAMPTZ NN`
- **PK/FK:** FK → issues
- **Unique/Check:** CK durum/priority değerleri · **Index:** (issue_id, sequence_no)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** geçişin kendisi audit olayıdır · **Immutable:** evet
- **Yazan:** issue servisleri · **Okuyan:** sorun detayı, denetim

#### `issue_comments`
- **Amaç:** Sorun yorumları (`D09.C02.W02.A03`).
- **Kolonlar:** `comment_id UUID PK` · `issue_id UUID NN` · `body TEXT NN` · `created_by TEXT NN` · ortak kolonlar
- **PK/FK:** FK → issues
- **Unique/Check:** CK length(body) 1..4000 ve zararlı içerik taraması uygulama düzeyinde
- **Index:** (issue_id, created_at) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `ISSUE_COMMENT_ADDED` · **Immutable:** yorum düzenlenmez
- **Yazan:** issue yorum servisi · **Okuyan:** sorun detayı

#### `issue_resolutions`
- **Amaç:** Çözüm kaydı — append-only (`D09.C02.W03.A01`).
- **Kolonlar:** `sequence_no BIGINT IDENTITY PK` · `resolution_id UUID NN UQ` · `issue_id UUID NN` · `root_cause TEXT NN` · `corrective_action TEXT NN` · `evidence_reference_id UUID NN` · `remediation_action_id UUID NULL` · `completed_at TIMESTAMPTZ NN` · `protection_policy_version TEXT NN` · `created_by TEXT NN` · ortak kolonlar
- **PK/FK:** FK → issues
- **Unique/Check:** CK root_cause/corrective_action 1..2000, `<`/`>` içermez
- **Index:** (issue_id, sequence_no) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `ISSUE_RESOLVED` · **Immutable:** evet
- **Yazan:** issue çözüm servisi · **Okuyan:** doğrulama, denetim

#### `issue_verifications`
- **Amaç:** Bağımsız doğrulama kaydı — append-only (`D09.C02.W04.A01`).
- **Kolonlar:** `sequence_no BIGINT IDENTITY PK` · `verification_id UUID NN UQ` · `issue_id UUID NN` · `verification_reference_id UUID NN UQ` · `execution_id UUID NN` · `score_id UUID NULL` · `scope_type TEXT NN` · `scope_id UUID NN` · `outcome TEXT NN` (QUALITY_FAILED/PARTIAL/TECHNICAL_ERROR/QUALITY_PASSED) · `completed_at TIMESTAMPTZ NN` · `recorded_by TEXT NN` · ortak kolonlar
- **PK/FK:** FK → issues
- **Unique/Check:** CK outcome; CK recorded_by ≠ çözüm sahibi (uygulama + audit)
- **Index:** (issue_id, sequence_no) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `ISSUE_VERIFIED` · **Immutable:** evet
- **Yazan:** issue doğrulama servisi · **Okuyan:** kapatma ön koşulu

#### `issue_relationships`
- **Amaç:** Sorun ilişkileri — RECURRENCE (`D09.C02.W05.A02`).
- **Kolonlar:** `sequence_no BIGINT IDENTITY PK` · `relationship_id UUID NN UQ` · `predecessor_issue_id UUID NN` · `successor_issue_id UUID NN` · `relationship_type TEXT NN` (RECURRENCE/…) · ortak kolonlar
- **PK/FK:** FK → issues (2 kez)
- **Unique/Check:** UQ(predecessor, successor, type) · **Index:** (predecessor_issue_id, sequence_no)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `ISSUE_REOPENED` · **Immutable:** evet
- **Yazan:** sorun üretim servisi (GAP-006 ile tetiklenir) · **Okuyan:** yeniden açma

#### `issue_slas`
- **Amaç:** SLA hedef ve durumu (`D09.C03.W01`); mevcut sistemde hiç yok.
- **Kolonlar:** `issue_id UUID PK` · `first_response_due_at TIMESTAMPTZ NN` · `resolution_due_at TIMESTAMPTZ NN` · `calendar_version TEXT NN` · `policy_version TEXT NN` · `paused_duration INTERVAL NN DEFAULT '0'` · `status TEXT NN` (ON_TRACK/AT_RISK/BREACHED) · `breached_at TIMESTAMPTZ NULL` · ortak kolonlar
- **PK/FK:** PK = FK → issues
- **Unique/Check:** CK status · **Index:** (status, resolution_due_at)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `ISSUE_SLA_BREACHED` (yalnız ihlal anında)
- **Optimistic locking:** `version` · **Immutable:** hedef zamanları atanınca değişmez
- **Yazan:** SLA hesaplayıcı (GAP-014) · **Okuyan:** sorun listesi, eskalasyon

#### `issue_escalations`
- **Amaç:** Eskalasyon kaydı (`D09.C03.W02.A01`).
- **Kolonlar:** `escalation_id UUID PK` · `issue_id UUID NN` · `level INT NN` · `escalated_to_role TEXT NN` · `reason TEXT NN` · ortak kolonlar
- **PK/FK:** FK → issues
- **Unique/Check:** UQ(issue_id, level); CK level > 0
- **Index:** (issue_id) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `ISSUE_ESCALATED` · **Immutable:** evet
- **Yazan:** eskalasyon motoru (bildirimle birlikte) · **Okuyan:** eskalasyon panosu

#### `exceptions`
- **Amaç:** İstisna kaydı (`D09.C04`); ST-Exception. Mevcut sistemde hiç yok.
- **Kolonlar:** `exception_id UUID PK` · `scope_type TEXT NN` · `scope_id UUID NN` · `reason TEXT NN` · `compensating_control TEXT NN` · `valid_until TIMESTAMPTZ NN` · `maker_actor_id TEXT NN` · `checker_actor_id TEXT NULL` · `status TEXT NN` (PENDING/ACTIVE/REJECTED/EXPIRED/REVOKED) · `revocation_reason TEXT NULL` · `expired_at TIMESTAMPTZ NULL` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** CK status; CK valid_until > now() talepte (`BR-D09-009`); CK checker <> maker; CK REVOKED iken revocation_reason NOT NULL
- **Index:** (status) kısmi ACTIVE; (scope_type, scope_id)
- **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** `EXCEPTION_REQUESTED/DECIDED/EXPIRED/REVOKED`
- **Optimistic locking:** `version` · **Immutable:** maker alanları karar sonrası değişmez
- **Yazan:** istisna servisi (GAP-009) · **Okuyan:** bastırma motoru, kalite borcu tetikleyici

#### `exception_suppressions`
- **Amaç:** İstisnanın bastırdığı olay kaydı (`D09.C04.W02.A02`).
- **Kolonlar:** `suppression_id BIGINT IDENTITY PK` · `exception_id UUID NN` · `rule_result_id UUID NN` · `suppressed_at TIMESTAMPTZ NN`
- **PK/FK:** FK → exceptions, → rule_execution_results
- **Unique/Check:** UQ(exception_id, rule_result_id) · **Index:** (exception_id)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `EXCEPTION_SUPPRESSED_ALERT` · **Immutable:** evet — ham sonuç asla değişmez
- **Yazan:** bastırma motoru · **Okuyan:** istisna detayı (bastırılan olay sayısı)

#### `diagnosis_hypotheses`
- **Amaç:** Kök neden hipotezi (`D09.C05.W01`).
- **Kolonlar:** `hypothesis_id UUID PK` · `issue_id UUID NN` · `hypothesis_type TEXT NN` · `evidence_refs JSONB NN` · `confidence NUMERIC(5,4) NULL` · `rank INT NN` · `status TEXT NN` (PROPOSED/CONFIRMED/REJECTED) · `decided_by TEXT NULL` · `decision_reason TEXT NULL` · ortak kolonlar
- **PK/FK:** FK → issues
- **Unique/Check:** CK status · **Index:** (issue_id, rank)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `DIAGNOSIS_HYPOTHESES_GENERATED/HYPOTHESIS_DECIDED`
- **Immutable:** kanıt referansları değişmez · `BR-D09-013/014`
- **Yazan:** teşhis motoru (`lineage/impact.py`, GAP-013) · **Okuyan:** inceleme ekranı

#### `recommendations`
- **Amaç:** Kanıtlı düzeltme önerisi (`D09.C05.W02.A01`).
- **Kolonlar:** `recommendation_id UUID PK` · `issue_id UUID NN` · `recommendation_type TEXT NN` · `parameters JSONB NN` · `expected_impact TEXT NULL` · `evidence_refs JSONB NN` · `status TEXT NN` (PROPOSED/ACCEPTED/REJECTED) · ortak kolonlar
- **PK/FK:** FK → issues
- **Unique/Check:** CK status · **Index:** (issue_id)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `RECOMMENDATION_GENERATED` · **Immutable:** kanıt referansları
- **Yazan:** öneri motoru · **Okuyan:** inceleme ekranı, remediation türetme

#### `remediation_actions`
- **Amaç:** Düzeltme aksiyonu yaşam döngüsü (`D09.C06.W01`); ST-RemediationAction.
- **Kolonlar:** `action_id UUID PK` · `issue_id UUID NN` · `action_type TEXT NN` · `description TEXT NN` · `owner_user_id UUID NN` · `due_at TIMESTAMPTZ NN` · `status TEXT NN` (PLANNED/IN_PROGRESS/COMPLETED/FAILED/CANCELLED) · `source_recommendation_id UUID NULL` · `auto_executed BOOLEAN NN DEFAULT FALSE` · `policy_version TEXT NULL` · `completed_at TIMESTAMPTZ NULL` · `evidence_reference_id UUID NULL` · ortak kolonlar
- **PK/FK:** FK → issues, → recommendations
- **Unique/Check:** CK status; CK COMPLETED iken evidence_reference_id NOT NULL (`BR-D09-016`)
- **Index:** (issue_id); (owner_user_id, status)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `REMEDIATION_ACTION_CREATED/COMPLETED/AUTO_EXECUTED`
- **Optimistic locking:** `version` · **Immutable:** kanıt referansı tamamlandıktan sonra
- **Yazan:** remediation servisi (GAP-006/013 sonrası) · **Okuyan:** sorun detayı, etki ölçümü

#### `remediation_impacts`
- **Amaç:** Düzeltme sonrası etki ölçümü (`D09.C06.W02.A01`).
- **Kolonlar:** `impact_id UUID PK` · `action_id UUID NN UQ` · `before_result_id UUID NN` · `after_result_id UUID NN` · `improvement NUMERIC(7,4) NULL` · `verdict TEXT NN` (IMPROVED/INEFFECTIVE/UNKNOWN) · ortak kolonlar
- **PK/FK:** FK → remediation_actions, → rule_execution_results (2 kez)
- **Unique/Check:** CK verdict · **Index:** (action_id)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `REMEDIATION_IMPACT_MEASURED` · **Immutable:** evet
- **Yazan:** etki ölçüm servisi · **Okuyan:** sorun detayı

### D10 — Lineage, Etki ve Veri Sözleşmesi

#### `lineage_events`
- **Amaç:** Lineage olayı alım kaydı (`D10.C01.W01.A01`).
- **Kolonlar:** `event_id UUID PK` · `job_name TEXT NN` · `run_id TEXT NN` · `event_type TEXT NN` · `source_system TEXT NN` · `payload JSONB NN` · `occurred_at TIMESTAMPTZ NN` · `ingested_at TIMESTAMPTZ NN DEFAULT now()`
- **PK/FK:** — · **Unique/Check:** UQ(run_id, event_type) idempotency (`BR-D10-001`)
- **Index:** (job_name, occurred_at DESC)
- **Partition:** aylık RANGE(occurred_at) · **Retention:** `R-EVIDENCE`
- **Audit:** `LINEAGE_EVENT_INGESTED` · **Immutable:** evet
- **Yazan:** alım servisi (GAP-012; servis hesabı `lineage.write`) · **Okuyan:** kenar üretimi, graf sorgusu

#### `lineage_edges`
- **Amaç:** Varlık düzeyi soy ağacı kenarı (`D10.C01.W01.A01`).
- **Kolonlar:** `edge_id UUID PK` · `from_asset_ref TEXT NN` · `to_asset_ref TEXT NN` · `transformation TEXT NULL` · `is_external BOOLEAN NN DEFAULT FALSE` · `first_seen_at TIMESTAMPTZ NN` · `last_seen_at TIMESTAMPTZ NN`
- **PK/FK:** — (asset_ref katalog varlığına mantıksal bağ)
- **Unique/Check:** UQ(from_asset_ref, to_asset_ref, transformation)
- **Index:** (to_asset_ref); (from_asset_ref)
- **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** alım olayına gömülü · **Immutable:** — (upsert ile `last_seen_at` tazelenir)
- **Yazan:** alım servisi (`BR-D10-002` harici varlık) · **Okuyan:** graf sorgulama (`BR-D10-003/005`), etki analizi

#### `column_lineage_edges`
- **Amaç:** Kolon düzeyi kenar (`D10.C01.W01.A02`).
- **Kolonlar:** `edge_id UUID PK` · `from_field_ref TEXT NN` · `to_field_ref TEXT NN` · `transformation_type TEXT NULL` · `confidence NUMERIC(5,4) NULL` · `last_seen_at TIMESTAMPTZ NN`
- **PK/FK:** — · **Unique/Check:** UQ(from_field_ref, to_field_ref)
- **Index:** (to_field_ref) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** alım olayına gömülü · **Immutable:** — (upsert)
- **Yazan:** alım servisi · **Okuyan:** alan düzeyi etki

#### `impact_analyses`
- **Amaç:** Aşağı akış etki analizi kaydı (`D10.C02.W01.A01`).
- **Kolonlar:** `analysis_id UUID PK` · `source_asset_ref TEXT NN` · `impacted_refs JSONB NN` · `breadth INT NN` · `coverage_note TEXT NULL` (lineage yoksa `UNKNOWN`, `BR-D10-004`) · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** CK breadth >= 0
- **Index:** (source_asset_ref, created_at DESC) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `IMPACT_ANALYSIS_COMPUTED` · **Immutable:** evet
- **Yazan:** `assess_impact` üretim bağı (GAP-013) · **Okuyan:** sorun detayı, önceliklendirme

#### `impact_simulations`
- **Amaç:** Değişiklik etki simülasyonu (`D10.C02.W02.A01`).
- **Kolonlar:** `simulation_id UUID PK` · `change_spec JSONB NN` · `impacted_refs JSONB NN` · `breaking_refs JSONB NN` · `coverage_note TEXT NULL` · `requested_by TEXT NN` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** —
- **Index:** (created_at DESC) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `IMPACT_SIMULATION_RUN` · **Immutable:** evet
- **Yazan:** simülasyon servisi · **Okuyan:** şema değişikliği kararı (GAP-019)

#### `data_contracts`
- **Amaç:** Veri sözleşmesi (`D10.C03.W01`); ST-DataContract. Mevcut sistemde sıfır kod.
- **Kolonlar:** `contract_id UUID PK` · `dataset_id UUID NN` · `version_no INT NN` · `producer_owner_id UUID NN` · `consumers JSONB NN` · `commitments JSONB NN` (her taahhüt kurala bağlı, `BR-D10-006`) · `status TEXT NN` (DRAFT/PENDING_ACCEPTANCE/ACTIVE/BREACHED/TERMINATED/SUPERSEDED) · `producer_accepted_at TIMESTAMPTZ NULL` · `consumer_accepted_at TIMESTAMPTZ NULL` · `terminated_at TIMESTAMPTZ NULL` · `termination_reason TEXT NULL` · ortak kolonlar
- **PK/FK:** FK → datasets, owner → users
- **Unique/Check:** UQ(dataset_id, version_no); CK status
- **Index:** (status); (dataset_id)
- **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `DATA_CONTRACT_DRAFTED/ACCEPTED/TERMINATED/BREACHED/RECOVERED`
- **Optimistic locking:** `version` · **Immutable:** ACTIVE taahhütler yeni sürümle değişir
- **Yazan:** sözleşme servisi (GAP-010) · **Okuyan:** uyum ölçümü, ihlal değerlendirici

#### `contract_compliance`
- **Amaç:** Taahhüt bazlı uyum ölçümü (`D10.C03.W02.A01`).
- **Kolonlar:** `compliance_id UUID PK` · `contract_id UUID NN` · `commitment_key TEXT NN` · `measured_value NUMERIC(12,4) NULL` · `committed_value NUMERIC(12,4) NN` · `verdict TEXT NN` (MET/NOT_MET/NOT_MEASURED) · `measured_at TIMESTAMPTZ NN`
- **PK/FK:** FK → data_contracts
- **Unique/Check:** CK verdict · **Index:** (contract_id, measured_at DESC)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `CONTRACT_COMPLIANCE_MEASURED` · **Immutable:** evet
- **Yazan:** uyum ölçüm işi · **Okuyan:** uyum panosu, ihlal tetikleyici

#### `contract_breaches`
- **Amaç:** İhlal kaydı (`D10.C03.W03`).
- **Kolonlar:** `breach_id UUID PK` · `contract_id UUID NN` · `commitment_key TEXT NN` · `measured_value NUMERIC(12,4) NN` · `issue_id UUID NULL` · `status TEXT NN` (OPEN/CLOSED) · `breached_at TIMESTAMPTZ NN` · `closed_at TIMESTAMPTZ NULL`
- **PK/FK:** FK → data_contracts, → issues
- **Unique/Check:** CK status; UQ(contract_id, commitment_key) WHERE status='OPEN'
- **Index:** (contract_id, breached_at DESC) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `DATA_CONTRACT_BREACHED/RECOVERED` · **Immutable:** ihlal anı kanıtı
- **Yazan:** ihlal değerlendirici (`BR-D10-008/009`) · **Okuyan:** sözleşme detayı

#### `quality_debts`
- **Amaç:** Kalite borcu kaydı (`D10.C04`).
- **Kolonlar:** `debt_id UUID PK` · `scope_type TEXT NN` · `scope_id UUID NN` · `description TEXT NN` · `estimated_impact TEXT NULL` · `target_period TEXT NN` (`BR-D10-010`) · `owner_user_id UUID NN` · `status TEXT NN` (OPEN/CLOSED/ACCEPTED) · `source_ref TEXT NULL` (istisna/dead-letter/sorun) · `closed_at TIMESTAMPTZ NULL` · `closure_evidence_ref UUID NULL` · ortak kolonlar
- **PK/FK:** owner → users
- **Unique/Check:** CK status; CK CLOSED iken closure_evidence_ref NOT NULL (`BR-D10-012`)
- **Index:** (status, target_period) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `QUALITY_DEBT_RECORDED/CLOSED` · **Optimistic locking:** `version`
- **Yazan:** kalite borcu servisi (GAP-009; `BR-D10-011` istisnadan otomatik) · **Okuyan:** portföy ekranı

### D11 — Analitik, Dashboard ve Raporlama

#### `reports`
- **Amaç:** Rapor talebi ve yaşam döngüsü (`D11.C03.W01.A01`); ST-ReportJob.
- **Kolonlar:** `report_id UUID PK` · `report_type TEXT NN` (7 tip) · `format TEXT NN` (PDF/XLSX/CSV) · `requested_by TEXT NN` · `parameters JSONB NN` · `status TEXT NN` (PENDING/GENERATING/READY/FAILED/CANCELLED/EXPIRED) · `sensitivity_level TEXT NULL` · `retention_policy_id UUID NULL` → `retention_policies` (hedefte gerçek FK) · `online_file_reference TEXT NULL` · `file_size BIGINT NULL` · `expires_at TIMESTAMPTZ NULL` · `retention_until TIMESTAMPTZ NULL` · `failure_reason TEXT NULL` · ortak kolonlar
- **PK/FK:** FK → retention_policies
- **Unique/Check:** CK report_type; CK format; CK status (CANCELLED hedefte eklenir)
- **Index:** (requested_by, created_at DESC); (status, expires_at)
- **Partition:** yok · **Retention:** `R-REPORT` — dosya imha, metadata kalır
- **Audit:** `REPORT_REQUESTED/GENERATED/CANCELLED/FILE_DESTROYED`
- **Optimistic locking:** `version` · **Immutable:** talep parametreleri
- **Yazan:** `ReportService` · **Okuyan:** rapor listesi, indirme politikası

#### `report_schedules`
- **Amaç:** Zamanlanmış rapor tanımı (`D11.C03.W03.A01`).
- **Kolonlar:** `schedule_id UUID PK` · `name TEXT NN UQ` · `report_type TEXT NN` · `format TEXT NN` · `parameters JSONB NN` · `sensitivity_level TEXT NULL` · `recipients JSONB NN` · `schedule_type TEXT NN` · `timezone_name TEXT NN` · `local_time TEXT NULL` · `once_at TIMESTAMPTZ NULL` · `day_of_week INT NULL` · `day_of_month INT NULL` · `status TEXT NN DEFAULT 'ACTIVE'` (ACTIVE/PAUSED/DELETED) · `next_run_at TIMESTAMPTZ NULL` · `last_triggered_at TIMESTAMPTZ NULL` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** UQ(name); CK type/format/schedule_type/status
- **Index:** (next_run_at) kısmi ACTIVE
- **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** zamanlama olayları · **Optimistic locking:** `version`
- **Yazan:** `ReportScheduleService` · **Okuyan:** tetikleme daemon'u (GAP-015)

#### `report_downloads`
- **Amaç:** İndirme ve erişim kaydı (`D11.C04.W02.A01`) — hassas erişim sınıfı.
- **Kolonlar:** `download_id BIGINT IDENTITY PK` · `report_id UUID NN` · `downloaded_by TEXT NN` · `downloaded_at TIMESTAMPTZ NN DEFAULT now()` · `access_outcome TEXT NN` (GRANTED/DENIED/EXPIRED)
- **PK/FK:** FK → reports
- **Unique/Check:** CK access_outcome · **Index:** (report_id, downloaded_at DESC)
- **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** indirme erişim kaydı (hassas) · **Immutable:** evet
- **Yazan:** indirme ucu · **Okuyan:** denetim

#### `export_records`
- **Amaç:** Dışa aktarım kaydı (DLP/watermark kanıtı, `D11.C04`).
- **Kolonlar:** `export_id UUID PK` · `report_id UUID NULL` · `export_type TEXT NN` · `policy_version TEXT NN` · `outcome TEXT NN` · ortak kolonlar
- **PK/FK:** FK → reports
- **Unique/Check:** CK outcome · **Index:** (created_at DESC)
- **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** dışa aktarım olayı · **Immutable:** evet
- **Yazan:** dışa aktarım servisi · **Okuyan:** denetim kanıtı

### D12 — Bildirim ve Dış Entegrasyon

#### `notification_events`
- **Amaç:** Bildirim olayı (`D12.C01.W01.A01`); iş transaction'ıyla atomik yazılır (`BR-D12-001`).
- **Kolonlar:** `event_id UUID PK` · `event_type TEXT NN` · `source_ref TEXT NN` · `payload JSONB NN` (veri-minimum, `BR-D12-002/003`) · `published_at TIMESTAMPTZ NN DEFAULT now()`
- **PK/FK:** — · **Unique/Check:** CK event_type katalogda tanımlı
- **Index:** (event_type, published_at DESC)
- **Partition:** aylık RANGE(published_at) · **Retention:** `R-NOTIF`
- **Audit:** `NOTIFICATION_EVENT_PUBLISHED` · **Immutable:** evet
- **Yazan:** olay yayım servisi (GAP-007) · **Okuyan:** teslimat çözümleyici

#### `notification_subscriptions`
- **Amaç:** Abonelik ve tercih (`D12.C01.W02.A01`).
- **Kolonlar:** `subscription_id UUID PK` · `user_id UUID NN` · `event_type TEXT NN` · `scope_type TEXT NULL` · `scope_id UUID NULL` · `channel TEXT NN` · `status TEXT NN` (ACTIVE/INACTIVE) · ortak kolonlar
- **PK/FK:** FK → users
- **Unique/Check:** UQ(user_id, event_type, scope_type, scope_id, channel) WHERE ACTIVE; CK zorunlu tiplerden çıkılamaz (`BR-D12-007`, uygulama)
- **Index:** (event_type, status) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `NOTIFICATION_SUBSCRIPTION_CHANGED` · **Optimistic locking:** `version`
- **Yazan:** abonelik servisi · **Okuyan:** teslimat çözümleyici

#### `notification_channels`
- **Amaç:** Kanal yapılandırması (`D12.C02.W01.A01`).
- **Kolonlar:** `channel_id UUID PK` · `channel_type TEXT NN` (EMAIL/WEBHOOK/SMS/IN_APP) · `target_config JSONB NN` · `secret_ref TEXT NN` (sır değeri asla, `BR-D12-004`) · `allowed_event_types JSONB NULL` · `status TEXT NN` (ACTIVE/INACTIVE) · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** CK channel_type; CK status
- **Index:** (status) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `NOTIFICATION_CHANNEL_CONFIGURED` (sır asla) · **Optimistic locking:** `version`
- **Yazan:** kanal yönetim servisi · **Okuyan:** teslimat worker'ı

#### `notification_deliveries`
- **Amaç:** Teslimat durum makinesi (`D12.C02.W02`); ST-NotificationDelivery.
- **Kolonlar:** `delivery_id UUID PK` · `event_id UUID NN` · `recipient_user_id UUID NN` · `channel_id UUID NN` · `status TEXT NN` (PENDING/SENDING/DELIVERED/FAILED/UNDELIVERABLE/REROUTED/READ) · `attempt_count INT NN DEFAULT 0` · `last_error_class TEXT NULL` · `rerouted_to_channel_id UUID NULL` · `read_at TIMESTAMPTZ NULL` · ortak kolonlar
- **PK/FK:** FK → notification_events, users, channels
- **Unique/Check:** CK status; UQ(event_id, recipient_user_id, channel_id) idempotent teslimat
- **Index:** (status) kısmi PENDING/FAILED; (recipient_user_id, status)
- **Partition:** aylık RANGE(created_at) · **Retention:** `R-NOTIF`
- **Audit:** `NOTIFICATION_DELIVERY_ATTEMPTED/UNDELIVERABLE`
- **Optimistic locking:** `version` · **Immutable:** olay bağı
- **Yazan:** teslimat worker'ı (GAP-002 kuyruğu) · **Okuyan:** bildirim paneli, operasyon izleme

#### `integration_records`
- **Amaç:** Dış sistem (bilet) kaydı (`D12.C03.W01`); ST-IntegrationRecord.
- **Kolonlar:** `record_id UUID PK` · `integration_id UUID NN` · `source_ref TEXT NN` (sorun referansı) · `external_id TEXT NULL` · `status TEXT NN` (PENDING/SENT/FAILED/UPDATED/ORPHANED) · `idempotency_key TEXT NN` · `attempt_count INT NN DEFAULT 0` · `last_synced_at TIMESTAMPTZ NULL` · `last_inbound_at TIMESTAMPTZ NULL` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** UQ(integration_id, idempotency_key) (`BR-D12-008`); CK status
- **Index:** (source_ref); (status) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `INTEGRATION_RECORD_SENT/UPDATED/INBOUND_RECONCILED`
- **Optimistic locking:** `version` · **Immutable:** idempotency anahtarı
- **Yazan:** ServiceNow entegrasyon servisi (GAP-023) · **Okuyan:** sorun detayı

#### `rate_limit_counters`
- **Amaç:** API hız sınırı sayacı (`D12.C04.W02.A01`).
- **Kolonlar:** `client_ref TEXT NN` · `window_start TIMESTAMPTZ NN` · `request_count BIGINT NN DEFAULT 0` · PK(client_ref, window_start)
- **PK/FK:** PK bileşik · **Unique/Check:** CK request_count >= 0
- **Index:** — · **Partition:** yok · **Retention:** `R-OPS` — kısa süreli arındırma
- **Audit:** `RATE_LIMIT_EXCEEDED` · **Immutable:** —
- **Yazan:** hız sınırı middleware'i · **Okuyan:** aynı

### D13 — Audit, Kanıt ve Saklama

#### `audit_outbox`
- **Amaç:** İş transaction'ıyla atomik audit hazırlığı (`D13.C01.W01.A01`).
- **Kolonlar:** `event_id UUID PK` · `prepared_event JSONB NN` · `policy_version TEXT NN` · `status TEXT NN` (PENDING/PUBLISHED) · `attempt_count INT NN DEFAULT 0` · `last_error_code TEXT NULL` · `created_at TIMESTAMPTZ NN` · `published_at TIMESTAMPTZ NULL`
- **PK/FK:** — · **Unique/Check:** CK status
- **Index:** (status, created_at, event_id)
- **Partition:** yok (sıcak) · **Retention:** `R-OPS` — PUBLISHED kayıtlar `audit_events`'e aktarılınca arındırılır
- **Audit:** olayın kendisi; yayım hatasında `AUDIT_OUTBOX_PUBLISH_FAILED`
- **Immutable:** prepared_event redaksiyon sonrası değişmez
- **Yazan:** tüm mutasyon servisleri (fail-closed) · **Okuyan:** yayım döngüsü

#### `audit_events`
- **Amaç:** Kalıcı audit defteri — hash zincirli (`D13.C01.W01.A02/W02/W03`). Mevcut sistemde sorgu tarafı SQLite'dır; hedef PostgreSQL defteridir.
- **Kolonlar:** `sequence_no BIGINT IDENTITY PK` · `event_id UUID NN UQ` · `event_type TEXT NN` · `actor_id TEXT NN` · `object_type TEXT NULL` · `object_id TEXT NULL` · `action TEXT NN` · `result TEXT NN` · `old_value_summary JSONB NULL` · `new_value_summary JSONB NULL` · `old_value_digest TEXT NULL` · `new_value_digest TEXT NULL` · `redacted_fields JSONB NULL` · `redaction_policy_version TEXT NULL` · `policy_version TEXT NN` · `event_hash TEXT NN` · `previous_event_hash TEXT NN` · `occurred_at TIMESTAMPTZ NN`
- **PK/FK:** — · **Unique/Check:** UQ(event_id); hash zincir bütünlüğü uygulama düzeyinde
- **Index:** (actor_id, occurred_at DESC); (object_type, object_id, occurred_at DESC); (event_type, occurred_at DESC)
- **Partition:** aylık RANGE(occurred_at) · **Retention:** `R-AUDIT` (kurumsal asgari süre; dış toplayıcı kanıtı)
- **Audit:** sorgunun kendisi `AUDIT_QUERY_EXECUTED`; ret `AUDIT_ACCESS_DENIED`; zincir kopması `AUDIT_CHAIN_BROKEN`
- **Immutable:** evet — UPDATE/DELETE yasak (DB tetikleyicisi önerilir)
- **Yazan:** outbox yayım döngüsü · **Okuyan:** `AuditQueryService`, bütünlük doğrulama

#### `audit_integrity_checks`
- **Amaç:** Zincir bütünlük doğrulama koşusu (`D13.C01.W03.A01`).
- **Kolonlar:** `check_id UUID PK` · `range_start BIGINT NN` · `range_end BIGINT NN` · `verdict TEXT NN` (PASSED/FAILED) · `mismatch_count INT NN` · `verified_at TIMESTAMPTZ NN` · `verified_by TEXT NN`
- **PK/FK:** — · **Unique/Check:** CK verdict
- **Index:** (verified_at DESC) · **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** `AUDIT_INTEGRITY_VERIFIED` · **Immutable:** evet
- **Yazan:** doğrulama servisi · **Okuyan:** denetim ekranı

#### `audit_export_cursors`
- **Amaç:** Dış toplayıcı aktarım imleci (`D13.C02.W02.A01`).
- **Kolonlar:** `target TEXT PK` · `last_exported_sequence_no BIGINT NN` · `last_exported_at TIMESTAMPTZ NN`
- **PK/FK:** — · **Unique/Check:** — · **Index:** —
- **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** `AUDIT_EXPORT_COMPLETED/FAILED` · **Immutable:** —
- **Yazan:** aktarım döngüsü · **Okuyan:** aynı

#### `retention_policies`
- **Amaç:** Saklama politikası (`D13.C03.W01.A01`); mevcut şemada **yoktur** ama iki tablo bu tabloya sarkan referans taşır.
- **Kolonlar:** `policy_id UUID PK` · `data_category TEXT NN` · `retention_period INTERVAL NN` · `disposal_method TEXT NN` · `trigger_event TEXT NN` · `status TEXT NN` (DRAFT/IN_REVIEW/EFFECTIVE/SUPERSEDED) · ortak kolonlar
- **PK/FK:** onay → `approval_requests`
- **Unique/Check:** CK status; UQ(data_category) WHERE status='EFFECTIVE'
- **Index:** (status) · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** `RETENTION_POLICY_DRAFTED` ve yaşam döngüsü olayları
- **Optimistic locking:** `version` · **Immutable:** EFFECTIVE politika yeni sürümle değişir
- **Yazan:** retention yönetim servisi (GAP-011) · **Okuyan:** `RetentionEvaluator`, `retention_until` çözümleme

#### `disposal_jobs`
- **Amaç:** İmha işi ve kanıtı (`D13.C03.W02`).
- **Kolonlar:** `disposal_job_id UUID PK` · `scope_id TEXT NN` · `payload_digest TEXT NN` · `status TEXT NN` (PREPARED/RUNNING/COMPLETED/FAILED) · `result_evidence JSONB NULL` · `prepared_by TEXT NN` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** CK status; fail-closed hazırlık (`DisposalJobService` deseni)
- **Index:** (status) · **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** imha hazırlık/sonuç olayları · **Immutable:** hazırlanan digest ve sonuç kanıtı
- **Yazan:** `DisposalJobService` (PG'ye taşınır) · **Okuyan:** imha kanıtı ekranı

#### `legal_holds`
- **Amaç:** Yasal muhafaza (`D13.C04.W01`); ST-LegalHold.
- **Kolonlar:** `hold_id UUID PK` · `scope_type TEXT NN` · `scope_id UUID NN` · `reason TEXT NN` · `status TEXT NN` (ACTIVE/RELEASED) · `applied_by TEXT NN` · `applied_at TIMESTAMPTZ NN` · `released_by TEXT NULL` · `released_at TIMESTAMPTZ NULL` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** CK status; UQ(scope_type, scope_id) WHERE ACTIVE
- **Index:** (status) · **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** `LEGAL_HOLD_APPLIED/RELEASED` · **Optimistic locking:** `version` · **Immutable:** gerekçe
- **Yazan:** `LegalHoldService` (PG'ye taşınır) · **Okuyan:** imha koruması

#### `archive_recalls`
- **Amaç:** Arşivden geri çağırma talep ve kararı (`D13.C04.W02`).
- **Kolonlar:** `recall_id UUID PK` · `scope_id TEXT NN` · `request_reason TEXT NN` · `decision TEXT NN` (PENDING/APPROVED/DENIED) · `decided_by TEXT NULL` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** CK decision
- **Index:** (status) · **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** geri çağırma olayları · **Immutable:** karar kanıtı
- **Yazan:** `ArchiveRecallService` (PG'ye taşınır) · **Okuyan:** denetim

### D14 — Operasyon ve Platform Sağlığı

#### `component_health`
- **Amaç:** Bileşen sağlık durumu (`D14.C01.W01.A01`).
- **Kolonlar:** `component TEXT PK` · `state TEXT NN` (HEALTHY/DEGRADED/UNAVAILABLE/UNKNOWN) · `detail TEXT NULL` · `checked_at TIMESTAMPTZ NN` · `changed_at TIMESTAMPTZ NULL`
- **PK/FK:** — · **Unique/Check:** CK state (`BR-D14-001`: UNKNOWN sağlıklı sayılmaz)
- **Index:** (state) · **Partition:** yok · **Retention:** `R-OPS`
- **Audit:** `COMPONENT_HEALTH_CHANGED` · **Immutable:** —
- **Yazan:** sağlık toplayıcı (GAP-024) · **Okuyan:** operasyon panosu

#### `operational_incidents`
- **Amaç:** Operasyonel olay (`D14.C03.W01`); ST-OperationalIncident. Kalite sorunlarından ayrı yaşam döngüsü (`BR-D14-008`).
- **Kolonlar:** `incident_id UUID PK` · `title TEXT NN` · `severity TEXT NN` · `affected_components JSONB NN` · `impact TEXT NULL` · `owner_user_id UUID NULL` · `status TEXT NN` (OPEN/MITIGATED/CLOSED) · `opened_at TIMESTAMPTZ NN` · `mitigated_at TIMESTAMPTZ NULL` · `closed_at TIMESTAMPTZ NULL` · `root_cause TEXT NULL` · ortak kolonlar
- **PK/FK:** owner → users
- **Unique/Check:** CK status; CK CLOSED iken root_cause NOT NULL (`BR-D14-006`)
- **Index:** (status, severity) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** `OPERATIONAL_INCIDENT_OPENED/UPDATED/CLOSED`
- **Optimistic locking:** `version`
- **Yazan:** olay servisi (GAP-024) · **Okuyan:** operasyon ekranı

#### `incident_updates`
- **Amaç:** Olay zaman çizelgesi notları (`D14.C03.W01.A02`).
- **Kolonlar:** `update_id BIGINT IDENTITY PK` · `incident_id UUID NN` · `note TEXT NN` · `created_by TEXT NN` · ortak kolonlar
- **PK/FK:** FK → operational_incidents
- **Unique/Check:** — · **Index:** (incident_id, created_at)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** olay audit'ine gömülü · **Immutable:** evet
- **Yazan:** olay servisi · **Okuyan:** olay detayı

#### `maintenance_windows`
- **Amaç:** Bakım penceresi (`D14.C04.W01.A01`).
- **Kolonlar:** `window_id UUID PK` · `starts_at TIMESTAMPTZ NN` · `ends_at TIMESTAMPTZ NN` · `scope TEXT NN` · `description TEXT NN` · `status TEXT NN` (SCHEDULED/ACTIVE/COMPLETED) · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** CK status; CK ends_at > starts_at
- **Index:** (status, starts_at) · **Partition:** yok · **Retention:** `R-OPS`
- **Audit:** `MAINTENANCE_WINDOW_SCHEDULED` (`BR-D14-005` bastırma/duraklatma yan etkisi)
- **Optimistic locking:** `version`
- **Yazan:** bakım servisi · **Okuyan:** uyarı bastırma, zamanlayıcı

#### `backfill_jobs`
- **Amaç:** Toplu telafi koşusu (`D14.C04.W02.A01`).
- **Kolonlar:** `backfill_id UUID PK` · `period_start TIMESTAMPTZ NN` · `period_end TIMESTAMPTZ NN` · `scope JSONB NN` · `job_count INT NN` · `status TEXT NN` (RUNNING/COMPLETED/PARTIAL) · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** CK status (`BR-D14-007` kademelendirme uygulama düzeyinde)
- **Index:** (created_at DESC) · **Partition:** yok · **Retention:** `R-OPS`
- **Audit:** `BACKFILL_STARTED/COMPLETED` · **Immutable:** kapsam tanımı
- **Yazan:** telafi orkestratörü · **Okuyan:** operasyon ekranı

### D15 — Test Verisi ve Ground Truth

#### `synthetic_profiles`
- **Amaç:** Sentetik üretim profili tanımı (`D15.C01.W02`).
- **Kolonlar:** `profile_id UUID PK` · `name TEXT NN UQ` · `definition JSONB NN` · `status TEXT NN` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** UQ(name); CK status
- **Index:** — · **Partition:** yok · **Retention:** `R-CATALOG`
- **Audit:** profil olayları · **Optimistic locking:** `version`
- **Yazan:** sentetik veri servisi (GAP-025) · **Okuyan:** üretim koşuları

#### `synthetic_runs`
- **Amaç:** Üretim çalıştırması (`D15.C01.W01`).
- **Kolonlar:** `run_id UUID PK` · `profile_id UUID NN` · `status TEXT NN` (QUEUED/RUNNING/SUCCESS/FAILED) · `output_ref TEXT NULL` · `canonical_digest TEXT NULL` · ortak kolonlar
- **PK/FK:** FK → synthetic_profiles
- **Unique/Check:** CK status · **Index:** (profile_id, created_at DESC)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** run olayları · **Immutable:** tamamlanan run kanıtı
- **Yazan:** generator/finalization · **Okuyan:** doğrulama zinciri

#### `ground_truth_defects`
- **Amaç:** Bilinen doğruluk kümesi — kusur tanımları (`D15.C02.W01`).
- **Kolonlar:** `defect_id UUID PK` · `dataset_ref TEXT NN` · `defect_type TEXT NN` · `specification JSONB NN` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** CK defect_type
- **Index:** (dataset_ref) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** ground truth olayları · **Immutable:** sürümlü tanım
- **Yazan:** ground truth servisi · **Okuyan:** doğruluk ölçümü

#### `expected_results`
- **Amaç:** Beklenen sonuç kaydı (`D15.C02.W02`).
- **Kolonlar:** `expected_id UUID PK` · `defect_id UUID NN` · `run_id UUID NN` · `expected JSONB NN` · ortak kolonlar
- **PK/FK:** FK → ground_truth_defects, synthetic_runs
- **Unique/Check:** UQ(defect_id, run_id) · **Index:** (run_id)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** ground truth olayları · **Immutable:** evet
- **Yazan:** ground truth servisi · **Okuyan:** karşılaştırma

#### `control_validations`
- **Amaç:** Tespit doğruluğu ölçümü (`D15.C03.W01`).
- **Kolonlar:** `validation_id UUID PK` · `run_id UUID NN` · `sensitivity NUMERIC(7,4) NULL` · `false_alarm_rate NUMERIC(7,4) NULL` · `details JSONB NN` · ortak kolonlar
- **PK/FK:** FK → synthetic_runs
- **Unique/Check:** — · **Index:** (run_id)
- **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** doğrulama olayları · **Immutable:** evet
- **Yazan:** doğruluk ölçüm servisi · **Okuyan:** kanıt raporu

#### `control_experiments`
- **Amaç:** Kontrol yeterliliği (chaos) deneyi (`D15.C03.W02`).
- **Kolonlar:** `experiment_id UUID PK` · `scope JSONB NN` · `verdict TEXT NN` · `evidence JSONB NN` · ortak kolonlar
- **PK/FK:** — · **Unique/Check:** CK verdict
- **Index:** (created_at DESC) · **Partition:** yok · **Retention:** `R-EVIDENCE`
- **Audit:** deney olayları · **Immutable:** evet
- **Yazan:** deney servisi · **Okuyan:** denetim kanıtı

### Ortak

#### `approval_requests`
- **Amaç:** Politika, sözleşme ve genel onay akışları için ortak talep tablosu (aşama 2 §6.5 Ortak); ST-ApprovalRequest. Kural onayı ve kaynak aktivasyonu mevcut alan tablolarında kalabilir; yeni onay akışları (politika, istisna, sözleşme, retention) bu ortak tabloyu kullanır.
- **Kolonlar:** `approval_request_id UUID PK` · `object_type TEXT NN` (POLICY/EXCEPTION/CONTRACT/RETENTION_POLICY/…) · `object_id UUID NN` · `maker_actor_id TEXT NN` · `checker_actor_id TEXT NULL` · `policy_version TEXT NN` · `status TEXT NN` (PENDING/APPROVED/REJECTED/WITHDRAWN/EXPIRED) · `decision_reason_code TEXT NULL` · `requested_at TIMESTAMPTZ NN` · `expires_at TIMESTAMPTZ NULL` · `decided_at TIMESTAMPTZ NULL`
- **PK/FK:** — (object bağı mantıksal) · **Unique/Check:** CK status; CK checker <> maker; kısmi UQ(object_type, object_id) WHERE status='PENDING'
- **Index:** (status, expires_at) kısmi PENDING
- **Partition:** yok · **Retention:** `R-AUDIT`
- **Audit:** `*_REQUESTED/DECIDED/WITHDRAWN/EXPIRED` · **Immutable:** karar sonrası
- **Yazan:** ilgili domain servisleri · **Okuyan:** onay kuyruğu

---

## 3. Mevcut şemadan bağımsız kanıt tabloları

Aşağıdaki mevcut tablolar hedef 119 listesinde yer almaz ancak kanıt katmanı
olarak korunur:

| Mevcut tablo | Değerlendirme |
|---|---|
| `lineage_evidence_snapshots` | Kanıt paket deposu; hedef `lineage_events`/`lineage_edges` ile birlikte yaşamayı sürdürür (kanıt katmanı) |
| `data_processing_inventory_versions` | Bankacılık/KVKK işleme envanteri; hedef D-domain listesinde yok ancak 17.x uyum kapsamının parçası — korunur, sarkan `retention_policy_id` GAP-011 ile gerçek tabloya bağlanır |

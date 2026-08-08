---
type: functional-audit-work
stage: "11 — DS-02 Değişiklik Envanteri"
scope: slice-ds02-change-inventory
inputs:
  - 10-Second-Slice-Decision.md
  - 09-Slice-S1-Change-Inventory.md
  - 07-Implementation-Waves.md
  - ../04-Functional-Gap-Inventory.md
  - ../13-Implementation-Roadmap.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-05
---

# 11 — DS-02 Değişiklik Envanteri

> Seçilen ikinci dilim: **DS-02 — Kalıcı kaynak, kural ve sorun (GAP-001)**.
> Bu belge uygulanacak kaynak değişikliklerini dosya ve sembol düzeyinde belirler.
>
> Uygulama iki fazda tamamlanmıştır. **Faz A** query wiring, production composition,
> `RuleCommandAdapter` ve investigation/closure akışıdır. **Faz B** rule write
> endpoint'leri ile issue assignment, resolution ve verification zinciridir.
> Faz B dış sistemleri fake/no-op ile ikame etmez: production factory trusted
> executor, directory, protector, verification ve notification provider'larını
> zorunlu girdi olarak alır; ortak composition bu eksiksiz set verilmeden Faz B
> endpoint'lerini açmaz.

---

## 1. Envanter özeti

| Katman | Karar |
|---|---|
| Yeni tablo | **Yok** |
| Yeni/değişen kolon | **Yok** |
| Yeni migration | **Yok**; mevcut migration head `20260805_15` kullanılacak |
| Ana değişiklik | Mevcut PostgreSQL repository ve domain servislerini ortak `create_application` composition'ına bağlamak |
| Yeni endpoint | **Yok** |
| Endpoint sözleşmesi | Normal durumda korunur; eksik rule authorization bağlamı ayrı giriş engelidir (§7.1) |
| Yeni ekran | **Yok** |
| Frontend davranışı | Mevcut ekranlar gerçek API/PG sonucunu gösterir; sentetik fallback eklenmez |
| Production veri yolu | PostgreSQL-only; SQLite/in-memory/fake fallback yok |
| Worker | Kapsam dışı; DS-03'e aittir |

DS-02 bir DDL veya yeni özellik yüzeyi dilimi değildir. Ana değişiklik
`api/composition.py` ve onu besleyen application adapter'larındadır.

---

## 2. Tablolar ve kolonlar

### 2.1 DDL değişiklik listesi

**Değişecek tablo: yok. Değişecek kolon: yok.**

Aşağıdaki migration dosyaları bu dilimde değiştirilmez:

- `alembic/versions/20260723_01_issue_baseline.py`
- `alembic/versions/20260723_02_rule_baseline.py`
- `alembic/versions/20260724_03_data_source_baseline.py`
- `alembic/versions/20260724_04_execution_baseline.py`
- `alembic/versions/20260730_12_rule_ir_shadow_evidence.py`
- `alembic/versions/20260730_13_score_contribution_graphs.py`
- `alembic/versions/20260730_14_lineage_governance_evidence.py`
- `alembic/versions/20260805_15_data_source_command_slice.py`

Migration 15'in `audit_events` tablosu ve S1 kısıtları yeniden kullanılır. DS-02
için migration 16 oluşturmak gereksizdir. Uygulama sırasında gerçek bir model/DDL
farkı kanıtlanırsa bu envanter önce revize edilmeden migration yazılmaz.

### 2.2 Runtime'da bağlanacak mevcut tablolar

Bu tabloların şeması değişmez; yalnız executable application'ın gerçek okuma/yazma
yolu haline gelirler.

| Domain | Mevcut tablolar | Kullanılan başlıca mevcut kolonlar | Sahip migration |
|---|---|---|---|
| Kural | `quality_rules` | `quality_rule_id`, `code`, `name`, `dataset_id`, `field_ids`, `primary_dimension`, `owner_user_id`, `status` | `20260723_02_rule_baseline.py` |
| Kural sürümü | `rule_versions` | `rule_version_id`, `quality_rule_id`, `version_no`, `rule_type`, `definition`, `threshold`, `weight`, `criticality`, `prepared_by_actor_id`, `created_at` | `20260723_02_rule_baseline.py` |
| Kural testi | `rule_test_results` | `rule_test_result_id`, `rule_version_id`, `status`, sayaçlar, `success_rate`, `preview_score`, `error_class`, `message`, `created_at` | `20260723_02_rule_baseline.py` |
| Kural onayı | `rule_approval_requests` | `approval_request_id`, `rule_version_id`, `maker_actor_id`, `checker_actor_id`, `policy_version`, `status`, `decision_reason_code`, tarih kolonları | `20260723_02_rule_baseline.py` |
| Sorun ana kayıt | `data_quality_issues` | kimlik/kaynak/kapsam kolonları; `status`, `priority`, `assignee_user_id`, `occurrence_count`, `version`, zaman damgaları | `20260723_01_issue_baseline.py` |
| Sorun geçmişi | `issue_history` | `history_id`, `issue_id`, `action`, `actor_id`, eski/yeni durum-atama-öncelik alanları, `occurred_at` | `20260723_01_issue_baseline.py` |
| Çözüm | `issue_resolutions` | `resolution_id`, `issue_id`, `root_cause`, `corrective_action`, `evidence_reference_id`, koruma ve oluşturma alanları | `20260723_01_issue_baseline.py` |
| Doğrulama | `issue_verifications` | `verification_id`, `issue_id`, `execution_id`, `score_id`, kapsam, `outcome`, zaman/aktör alanları | `20260723_01_issue_baseline.py` |
| Sorun ilişkisi | `issue_relationships` | predecessor/successor kimlikleri, `relationship_type`, `created_at` | `20260723_01_issue_baseline.py` |
| Execution okuma | `rule_executions` | `execution_id`, `status`, `rule_version_ids`, `source_ids`, `triggered_by`, `correlation_id`, zaman ve hata alanları | `20260724_04_execution_baseline.py` |
| Katkı grafiği | `score_contribution_graphs` | `quality_score_id`, `execution_id`, `scope_type`, `scope_id`, `graph`, `created_at` | `20260730_13_score_contribution_graphs.py` |
| Transactional audit | `audit_outbox` | `event_id`, `prepared_event`, `policy_version`, `status`, attempt/hata/yayım alanları | `20260723_01_issue_baseline.py` |
| Kalıcı audit defteri | `audit_events` | zincir kimlik/hash alanları, aktör/aksiyon/nesne/sonuç, redacted özetler, politika sürümü | `20260805_15_data_source_command_slice.py` |
| Kural metadata doğrulaması | `data_sources`, `datasets`, `data_fields` | kaynak durumu ve dataset/field kapsam kimlikleri | `20260724_03_data_source_baseline.py` |

`api/composition.py:REQUIRED_TABLES` kümesi DS-02'de yukarıdaki production-kritik
tabloları kapsayacak biçimde genişletilir. Bu bir veritabanı şema değişikliği değil,
startup preflight değişikliğidir.

### 2.3 Değişmeyecek tablolar

`background_jobs`, `dead_letter_records`, execution attempt/result kolonları,
`workers`, skor snapshot tabloları, bildirim tabloları ve IAM tabloları DS-02'de
değişmez. `workers` tablosu henüz yoktur ve yalnız DS-03 migration'ında ele alınır.

---

## 3. Backend servis ve repository envanteri

### 3.1 Kesin değişecek dosyalar

| Dosya | Sembol | Planlanan değişiklik |
|---|---|---|
| `src/veri_kalitesi/api/composition.py` | `REQUIRED_TABLES` | Rule/issue/execution ve gerekli destek tablolarını preflight'a ekle |
| aynı | `create_application` | Aynı `SessionFactory`, schema, `PostgreSQLTransactionalAudit` ve `PostgreSQLAuditRepository` ile rule, issue ve execution query zincirlerini kur; `create_dashboard_api` portlarına geçir |
| aynı | `app.state.*` | Composition testinin doğrulayabilmesi için gerçek rule/issue/execution repository referanslarını yayımla; iş mantığı taşıma |
| `src/veri_kalitesi/api/settings.py` | `ApplicationSettings` | Rule approval ve issue access policy sürümlerini açık, boş olamaz settings olarak taşı; DB/secret ekleme |
| `src/veri_kalitesi/api/rule_commands.py` | yeni `RuleCommandAdapter` | `RuleService` dönüşlerini mevcut `RuleCreatorService`/`RuleMutationService` API portlarına adapte et; re-read yapabilir fakat state/permission kuralı yazmaz |
| `src/veri_kalitesi/api/identity.py` | `DevelopmentActorContextResolver` | Enterprise development aktörünün runtime PostgreSQL dataset scope'unu güvenilir composition provider'ından almasını sağla |
| `src/veri_kalitesi/executions/query.py` | `ExecutionQueryService.list_executions` | PostgreSQL teknik hatasını güvenli query hatasına eşle |
| `src/veri_kalitesi/persistence/__init__.py` | `SCHEMA_ENV` export'u | Alembic production env yolunun mevcut sabiti aynı paketten kullanmasını sağla |
| `alembic/env.py`, `alembic.ini` | schema çözümleme | Test/CI tarafından açık verilen Alembic schema'sını environment fallback'inden öncele; version/DDL değiştirme |

Yeni `RuleCommandAdapter` yeni bir domain abstraction değildir. Gereklidir çünkü
`RuleService.create_version`, `passivate_rule`, `activate_rule` ve approval metodları
domain nesnesi döndürürken `api/app.py:RuleMutationService` güncel
`(QualityRule, RuleVersion)` çifti bekler. Bu uyumsuzluğu domain servisini HTTP için
bozarak gidermek yerine ince application adapter'ı kullanılmalıdır.

### 3.2 Composition'a bağlanacak, yeniden yazılmayacak semboller

| Dosya | Mevcut sembol | Kullanım |
|---|---|---|
| `rules/postgresql_repository.py` | `PostgreSQLRuleRepository` | Rule command + query tek kalıcı repository |
| `rules/service.py` | `RuleService` | Kural state machine, onay ve transaction sınırı |
| `rules/query.py` | `RuleQueryService` | `permitted_dataset_ids` ile backend okuma scope'u |
| `data_sources/postgresql_repository.py` | `PostgreSQLDataSourceRepository` | `MetadataCatalog` portundaki `get_dataset`, `list_data_fields`, `get_data_source` metodlarını sağlar |
| `issues/postgresql_repository.py` | `PostgreSQLIssueRepository` | Sorun aggregate, history, resolution, verification ve audit-outbox atomikliği |
| `issues/service.py` | `IssueService` | Sorun state machine, rol/scope/SoD ve optimistic version kontrolü |
| `issues/query.py` | `IssueQueryService` | Source/dataset scope kontrollü liste |
| `executions/postgresql_repository.py` | `PostgreSQLExecutionRepository` | Mevcut `ExecutionReader.list_executions_for_sources` portunu doğrudan uygular |
| `executions/query.py` | `ExecutionQueryService` | Scope kontrollü execution listesi |
| `audit/postgresql_outbox.py` | `PostgreSQLTransactionalAudit` | İş kaydı + outbox aynı transaction |
| `audit/postgresql_repository.py` | `PostgreSQLAuditRepository` | Kalıcı audit append/read; fake prepared repository kullanılmaz |
| `audit/service.py` | `AuditService`, `AuditQueryService` | Audit hazırlama/yayım ve yetkili sorgu |

Bu repository dosyalarında öngörülen kaynak değişikliği yoktur. Composition sırasında
kanıtlanan gerçek bir protocol uyumsuzluğu olmadıkça yeni metot eklenmez.

### 3.3 Koşullu application adapter'ları

Aşağıdaki portların repository içinde production implementasyonu yoktur. Bunlar
fake/no-op ile geçilemez ve doğrudan repository çağrısıyla bypass edilemez:

| Port | Tanım | Gerekli gerçek kaynak | Dosya kararı |
|---|---|---|---|
| `RuleTestExecutor` | `rules/service.py` | Aktif kaynağa secret resolver üzerinden bağlanan gerçek rule test executor | Mevcut gerçek adapter bulunmadan `/rules/{id}/test` bağlanmaz; bulunursa composition'a enjekte edilir, yoksa ayrı plan gerekir |
| `IssueAssigneeDirectory` | `issues/service.py` | Trusted identity/IAM assignee profili ve scope'u | Production provider `create_production_app` girdisi olur; hard-coded kullanıcı yazılmaz |
| `IssueResolutionProtector` | `issues/service.py` | Çözüm metni/evidence koruma politikası | Gerçek provider enjekte edilir; düz metni “korunmuş” sayan adapter yazılmaz |
| `IssueVerificationResolver` | `issues/service.py` | Execution/score sonucundan güvenilir doğrulama | Mevcut PostgreSQL execution/score kaynağına dayalı adapter ayrıca tasarlanmalı |
| `IssueNotificationPublisher` | `issues/service.py` | Kalıcı bildirim hattı | DS-09 gelmeden reassign/create yan etkisi için gerçek producer yoktur; no-op yasaktır |
| `IssueAssigneeOptionProvider` | `api/app.py` | Aynı trusted directory'den API projection | Gerekirse `api/issue_assignment_options.py` içinde ince projection adapter'ı; yeni directory abstraction'ı yok |

Bu portlar çözülmeden bütün issue mutation uçlarını production'a bağlamak güvenli
değildir. Özellikle `IssueService.reassign` mutation commit'inden sonra notification
üretir; no-op publisher kullanmak kullanıcıya başarılı fakat eksik bir akış gösterir.

### 3.4 Değişmeyecek backend dosyaları

- `rules/postgresql_repository.py`
- `issues/postgresql_repository.py`
- `executions/postgresql_repository.py`
- `scoring/postgresql_contributions.py`
- `audit/postgresql_repository.py`
- `audit/postgresql_outbox.py`
- `api/models.py` — response/request sözleşmesi değişmez
- `api/development.py` — tarihsel/unit-test fixture composition'ıdır; executable
  yol `development_runtime.py` olduğu için production wiring'e dönüştürülmez
- `api/postgresql_execution.py` — start/cancel DS-03'e aittir
- `jobs/**` — worker kapsam dışıdır

---

## 4. Endpoint envanteri

### 4.1 Yeni endpoint yok

DS-02 mevcut endpoint'lerin arkasındaki portları değiştirir. URL, HTTP method,
payload ve response modelleri korunur.

### 4.2 Doğrudan yeniden bağlanacak endpoint'ler

| Method ve path | Route sembolü (`api/app.py`) | Yeni runtime bağı |
|---|---|---|
| `GET /api/v1/rules` | `get_rules` | `RuleQueryService(PostgreSQLRuleRepository, authorization)` |
| `GET /api/v1/issues` | `get_issues` | `IssueQueryService(PostgreSQLIssueRepository, authorization)` |
| `POST /api/v1/issues/{issue_id}/investigation` | `start_issue_investigation` | `IssueService.start_investigation` |
| `POST /api/v1/issues/{issue_id}/closure` | `close_issue` | `IssueService.close` |
| `GET /api/v1/executions` | `get_executions` | `ExecutionQueryService(PostgreSQLExecutionRepository, authorization)` |
| `GET /api/v1/audit/events` | `get_audit_events` | Zaten `PostgreSQLAuditRepository`; değiştirilmez, DS-02 olaylarıyla doğrulanır |

### 4.3 Rule command prerequisite'i geçince bağlanacak endpoint'ler

| Method ve path | Domain çağrısı |
|---|---|
| `POST /api/v1/rules` | `RuleService.create_rule` |
| `POST /api/v1/rules/{quality_rule_id}/versions` | `RuleService.create_version` |
| `POST /api/v1/rules/{quality_rule_id}/test` | `RuleService.test_rule` + gerçek `RuleTestExecutor` |
| `POST /api/v1/rules/{quality_rule_id}/activation` | `RuleService.activate_rule` |
| `POST /api/v1/rules/{quality_rule_id}/approval` | `RuleService.request_rule_approval` |
| `POST /api/v1/rules/approval/{approval_request_id}/decide` | `RuleService.decide_rule_approval` |
| `POST /api/v1/rules/approval/{approval_request_id}/withdraw` | `RuleService.withdraw_rule_approval` |
| `POST /api/v1/rules/{quality_rule_id}/passivation` | `RuleService.passivate_rule` |

Bu uçlar ancak §7.1'deki actor-context ve scope açığı kapandıktan sonra composition'a
alınır. Kalıcı repository'ye geçiş permission bypass'ını kabul edilebilir yapmaz.

### 4.4 Gerçek provider sağlanınca bağlanacak issue endpoint'leri

| Method ve path | Eksik bağımlılık |
|---|---|
| `GET /api/v1/issues/{issue_id}/assignment-options` | `IssueAssigneeDirectory` + projection adapter |
| `POST /api/v1/issues/{issue_id}/assignment` | `IssueAssigneeDirectory`, `IssueNotificationPublisher`, system notification actor context |
| `POST /api/v1/issues/{issue_id}/resolution` | `IssueResolutionProtector` |
| `POST /api/v1/issues/{issue_id}/verification` | `IssueVerificationResolver` |

`GET /api/v1/issues/{issue_id}/investigation/evidence` bu dilimin kalıcılık halkası
değildir; mevcut evidence servisi korunur ve DS-02 adına yeniden yazılmaz.

### 4.5 Kapsam dışı endpoint'ler

- `POST /api/v1/executions`
- `POST /api/v1/executions/{execution_id}/cancel`
- job/worker operasyon uçları
- yeni contribution-graph endpoint'i

`GET /api/v1/dashboard/summary` de DS-02'de yeniden yazılmaz.
`PostgreSQLContributionGraphRepository`, `DashboardQueryService.ScoreReader`
protokolünü uygulamaz ve mevcut API'de doğrudan consumer'ı yoktur. Yalnız repository'yi
instantiate etmek dashboard'ı gerçek yapmaz. Katkı grafiğinin kullanıcı yüzeyine
bağlanması DS-06 skor kalıcılığıyla birlikte ele alınmalı veya ayrı bir teknik planla
açıkça tanımlanmalıdır.

---

## 5. Frontend ekran ve çağrı envanteri

### 5.1 Davranışı doğrulanacak mevcut ekranlar

| Ekran | Component | API dosyası | DS-02 beklentisi |
|---|---|---|---|
| Kurallar | `frontend/src/rules/RulesPage.tsx` | `rules/api.ts` | Liste ve güvenli biçimde bağlanan mutasyonlar restart sonrası aynı kayıtları gösterir |
| Sorunlar | `frontend/src/issues/IssuesPage.tsx` | `issues/api.ts` | Liste ve bağlanan yaşam döngüsü aksiyonları PG sonucu gösterir |
| Çalıştırmalar | `frontend/src/executions/ExecutionsPage.tsx` | `executions/api.ts` | `GET /executions` ile PG'deki kaydı gösterir; yeni başlat/iptal UI yok |
| Denetim | `frontend/src/audit/AuditPage.tsx` | `audit/api.ts` | Kural/sorun mutation olayını gerçek `audit_events` kaynağından gösterir |

### 5.2 Planlanan frontend kaynak değişikliği

**Yok.** Mevcut API modülleri doğru endpoint'lere çağrı yapmaktadır. Yeni endpoint,
model alanı, buton veya sayfa eklenmez. Kaynak doğrulaması:

- `frontend/src/App.tsx:RulesRoute`, `ExecutionsRoute`, `IssuesRoute` ve
  `AuditRoute` içinde `fixtureState` yalnız `import.meta.env.DEV` doğruysa seçilir.
- Fixture seçilmediyse başlangıç durumu `loading`'dir ve gerçek API çağrısı yapılır.
- API hatası catch yolları `unauthorized`, `scope-forbidden` veya `error` state'ine
  geçer; `normal`/başarılı fixture verisine fallback yoktur.

Dolayısıyla production API hatası sentetik veriyi başarılı sonuç gibi göstermez.

Şu dosyalar yalnız test kanıtı için okunur, değişiklik beklenmez:

- `frontend/src/App.tsx`
- `frontend/src/rules/{api,model}.ts`
- `frontend/src/issues/{api,model}.ts`
- `frontend/src/executions/{api,model}.ts`
- `frontend/src/audit/{api,model}.ts`

Dashboard ve `ScoreContributionPanel.tsx` DS-02 ekran kapsamına alınmaz; backend'de
gerçek `ScoreReader` bulunmadan frontend'i değiştirmek sentetik/boş başarı üretir.

---

## 6. Test envanteri

### 6.1 Değişecek test dosyaları

| Dosya | Eklenecek doğrulama |
|---|---|
| `tests/integration/test_application_composition.py` | Ortak factory'nin rule/issue/execution/audit repository'lerini aynı session factory ve schema ile kurması; `REQUIRED_TABLES` preflight'ı; hiçbir runtime fallback olmaması |
| `tests/unit/test_rule_api.py` | Rule route'larının trusted `ActorContext`'i command portuna iletmesi; scope dışı ve rolü eksik aktörün `403` alması |
| `tests/unit/test_rules.py` | DS-02'de açılacak her rule command için backend rol/scope negatifleri; mevcut state machine'in değişmediği regresyonları |
| `tests/unit/test_issue_api.py` | Gerçek `IssueService` port şekliyle actor/scope/version hata eşlemesi; eksik provider'ın `503/422` ile fail-closed olması, başarıya dönüşmemesi |
| `tests/unit/test_execution_api.py` | PG reader'a iletilen boş/dar source scope'un sonuç sızdırmaması |

### 6.2 Yeni test dosyaları

| Yeni dosya | Amaç |
|---|---|
| `tests/unit/test_rule_commands.py` | `RuleCommandAdapter` yalnız dönüş/re-read adaptasyonu yapıyor; actor context'i kaybetmiyor; state machine kopyalamıyor |
| `tests/integration/test_ds02_persistent_application.py` | Gerçek migration head + ortak production composition ile rule/issue/execution sorgularını, investigation/closure mutation'larını, transactional audit'i, scope reddini ve app reconstruction sonrası kalıcılığı doğrula |

`test_ds02_transaction_boundaries.py` ve `persistent-core-live.spec.ts` Faz A'da
oluşturulmaz. Outbox rollback davranışı mevcut
`test_postgresql_issue_mutations.py` içinde korunur; rule write ve tam browser
mutation zinciri Faz B kabul testidir.

### 6.3 Korunacak mevcut repository testleri

Bu testler lower-level repository kanıtıdır; production composition testinin yerine
geçmez, fakat yeniden yazılmaz:

- `tests/integration/test_postgresql_rule_mutations.py`
- `tests/integration/test_postgresql_issue_persistence.py`
- `tests/integration/test_postgresql_issue_mutations.py`
- `tests/integration/test_postgresql_issue_migration.py`
- `tests/integration/test_postgresql_execution_persistence.py`
- `tests/integration/test_postgresql_score_contributions.py`
- `tests/integration/test_postgresql_audit_repository.py`

Bu dosyalardaki `FakePreparedAuditRepository` izole repository testi için kalabilir.
Ancak `test_ds02_persistent_application.py` ve composition çıkış kapısı yalnız
`PostgreSQLAuditRepository` kullanır; fake ile geçen test DS-02'yi kapatmaz.

### 6.4 Frontend unit/contract testleri

Endpoint ve model sözleşmesi değişmediği için aşağıdaki mevcut testler korunur;
yalnız gerçek API failure'ın fixture veriye düşmediği eksikse ilgili test genişletilir:

- `frontend/src/rules/api.test.ts`
- `frontend/src/rules/RulesPage.test.tsx`
- `frontend/src/issues/api.test.ts`
- `frontend/src/issues/IssuesPage.test.tsx`
- `frontend/src/executions/api.test.ts`
- `frontend/src/executions/ExecutionsPage.test.tsx`
- `frontend/src/audit/api.test.ts`
- `frontend/src/audit/AuditPage.test.tsx`

### 6.5 CI ve test altyapısı

`.github/workflows/quality.yml` zaten PostgreSQL 16 servis konteyneri sağlar ve
integration işinde `skipped=0` koşulunu zorlar; değişiklik beklenmez. Yeni DS-02
integration testleri bu dizinde normal biçimde toplanmalı ve skip edilmeden geçmelidir.
`infra/development/compose.yaml` da `postgres → migrate → api` sırasını
zaten uygular; yeni servis eklenmez.

Çıkışta çalıştırılacak hedefler:

```text
pytest -q tests/unit/test_rule_commands.py
pytest -q tests/unit/test_execution_api.py
pytest -q tests/integration/test_application_composition.py tests/integration/test_ds02_persistent_application.py
pytest -q docs/testing/02-Entegrasyon
npm --prefix frontend test
ruff check .
ruff format --check .
mypy docs/backend/src
```

---

## 7. Faz B engellerinin çözümü

### 7.1 Rule command authorization engeli

`api/app.py:RuleMutationService` imzaları tutarsızdır: `test_rule` ve
`activate_rule` yalnız `actor_id: str`, `passivate_rule` yalnız
`actor_context: ActorContext | None`, `create_version` ise ikisini birden taşır.
Route'lar test/activation aktörünü `actor_id` dizesine indiriyor.
`RuleService.create_rule` da ordinary/non-critical kural için dataset scope'unu
koşulsuz zorlamıyor. İlk S1 uygulaması bilinçli olarak yalnız veri kaynağı komut
ailesini kapattığı için bu açık halen GAP-027 kapsamındadır.

Faz A'daki `RuleCommandAdapter` bu imza farklarını iki yönde karşılar: actor-id-only
test/activation çağrısını trusted `ActorContext` olmadan fail-closed bırakır ve
passivation için mevcut actor-context çağrısının yanı sıra geçiş dönemi actor-id +
actor-context çağrısını da doğrular. Faz B'de eksiksiz `PhaseBProviders` setiyle
rule endpoint'lerine bağlanır.

Çözüm: HTTP portları `test_rule` ve `activate_rule` için trusted `ActorContext`
taşır. `RuleCommandAdapter` actor-id/context eşleşmesini ve dataset scope'unu
doğrular; production `RuleService` de `enforce_command_authorization=True` ile
aynı sınırı domain katmanında uygular. Rule write portları yalnız
`PhaseBProviders.rule_test_executor` sağlandığında composition'a bağlanır.

- `src/veri_kalitesi/api/app.py`
- `src/veri_kalitesi/rules/service.py`
- `tests/unit/test_rule_api.py`
- `tests/unit/test_rules.py`

Critical rule maker-checker akışı PostgreSQL acceptance testinde farklı aktörlerle
doğrulanmıştır. Approval response'u devam çağrısında kullanılacak
`pending_approval_request_id` değerini döndürür.

### 7.2 Issue provider engeli

`IssueService` mevcut state machine ve transaction koduyla yeniden kullanılmıştır.
Repository içinde bulunmayan dış sistemler `PhaseBProviders` üzerinden zorunlu
trusted production portlarıdır: `IssueAssigneeDirectory`, API option provider,
`IssueResolutionProtector`, `IssueVerificationResolver`,
`IssueNotificationPublisher` ve service actor provider. `create_production_app`
bu seti zorunlu alır; `create_application` provider seti yoksa assignment,
resolution ve verification uçlarını fail-closed bırakır. Development store veya
no-op adapter production yolu değildir.

### 7.3 Katkı grafiği consumer engeli

`PostgreSQLContributionGraphRepository` yalnız `add_score/get` sağlar.
`DashboardQueryService` ise `QualityScore` döndüren `ScoreReader` ister. Mevcut
endpoint hiçbir yerde contribution repository'yi tüketmez. Bu yüzden DS-02'de:

- yeni dashboard repository abstraction'ı yazılmaz;
- fake score reader bağlanmaz;
- dashboard'ın kalıcı olduğu iddia edilmez.

Bu madde DS-06 ile birleştirilmeli veya ayrı endpoint/query service kararıyla
yeniden planlanmalıdır.

---

## 8. Kesin dosya değişikliği özeti

### Değişecek

- `src/veri_kalitesi/api/composition.py`
- `src/veri_kalitesi/api/settings.py`
- `src/veri_kalitesi/api/identity.py`
- `src/veri_kalitesi/executions/query.py`
- `src/veri_kalitesi/persistence/__init__.py`
- `src/veri_kalitesi/api/rule_commands.py` — yeni
- `alembic.ini`
- `alembic/env.py`
- `tests/integration/test_application_composition.py`
- `tests/unit/test_execution_api.py`
- `tests/unit/test_rule_commands.py` — yeni
- `tests/integration/test_ds02_persistent_application.py` — yeni

### Faz B'de tamamlanan güvenlik prerequisite'i

- `src/veri_kalitesi/api/app.py`
- `src/veri_kalitesi/rules/service.py`
- `tests/unit/test_rule_api.py`
- `tests/unit/test_rules.py`

Bu prerequisite tamamlanmış ve production rule mutation wiring'inden önce
uygulanmıştır.

### Koşullu değişecek

- `src/veri_kalitesi/api/issue_assignment_options.py` — yalnız gerçek
  trusted directory kaynağı belirlendiğinde ince projection adapter'ı
- Production concrete provider'ın bulunduğu dosyalar — §7.2 kararı verilmeden dosya
  adı uydurulmaz

### Değişmeyecek

- Bütün Alembic version dosyaları
- PostgreSQL rule/issue/execution/contribution/audit repository'leri
- `api/models.py` ve endpoint URL/payload/response sözleşmeleri
- Rules/Issues/Executions/Audit React component ve API modülleri
- `api/development.py` test fixture yolu
- `api/postgresql_execution.py`, `jobs/**`, worker tabloları
- `.github/workflows/quality.yml`
- `infra/development/compose.yaml`

---

## 9. Envanter kararı

DS-02'nin **query, composition, restart persistence ve audit** bölümü mevcut kodla
uygulanmıştır. Investigation ve closure mevcut gerçek PostgreSQL repository,
state-machine ve transactional audit ile production composition'a bağlıdır.

Bütün rule ve issue mutation zincirini kapsayan Faz B tamamlanmıştır. Dış provider
implementasyonlarının sahipliği composition dışında kalır ve production startup'ta
zorunludur. Yeni tablo/kolon veya migration gerekmemiştir. PostgreSQL acceptance
testi rule ve issue state-machine'lerini, transactional audit'i, permission/scope'u,
maker-checker ayrımını ve application reconstruction sonrası kalıcılığı doğrular.

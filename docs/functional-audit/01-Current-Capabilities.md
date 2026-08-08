---
type: functional-audit
stage: "01 — Mevcut Yetenekler"
scope: as-is-only
project: Veri Kalitesi İzleme ve Skorlama Sistemi
audit_prompt: docs/audit-instructions/COMPREHENSIVE_FUNCTIONAL_AUDIT_PROMPT.md
branch: agent/36h1-persistent-job-core
created_at: 2026-08-04
---

# 01 — Mevcut Yetenekler (Current Capabilities)

> **Kapsam sınırı.** Bu dosya yalnız repository'nin **bugün sahip olduğu** durumu
> kaydeder. Hedef sistem tasarımı, eksiklik çözümü, öneri, tablo tasarımı ve yol
> haritası bu aşamanın kapsamı dışındadır ve bilinçli olarak yazılmamıştır.

---

## 1. Kapsam ve yöntem

### 1.1 Ne doğrulandı

Denetim prompt'unun §2 kuralı gereği dokümantasyon beyanı kanıt sayılmadı.
Bir yeteneğin "uygulanmış" sayılması için şu zincir kod üzerinden izlendi:

```
domain → migration → repository → service → API → frontend → permission → audit → test
```

Kaynak olarak `docs/functional-audit/evidence-inventory/` altındaki yedi mekanik
envanter dosyası okundu, ancak **her kritik iddia bu oturumda yeniden
doğrulandı**. Envanterle çelişen noktalar §10.2'de ayrıca listelenmiştir.

### 1.2 Çift eksenli durum modeli — neden gerekli

Mevcut envanter "zincirin en az 3 halkası doğrulandıysa `IMPLEMENTED`" kuralını
kullanmış ve **composition root erişilebilirliğini hiç kontrol etmemiştir**. Bu
oturumda tespit edilen temel olgu, bu kuralı tek başına yanıltıcı kılıyor:

> `PostgreSQLIssueRepository`, `PostgreSQLRuleRepository`,
> `PostgreSQLDataSourceRepository` ve `PostgreSQLContributionGraphRepository`
> **hiçbir çalıştırılabilir uygulamada örneklenmiyor**; yalnız `docs/testing/`
> altında instantiate ediliyor.

Yani bu kodlar yazılmış, test edilmiş ve migration'ı mevcut; ama kullanıcı
tarafından erişilebilir hiçbir yolda yer almıyor. Tek bir durum etiketi bu iki
gerçeği aynı anda taşıyamaz. Bu nedenle her yetenek **iki eksende** raporlanır:

| Eksen | Soru | Kanıt kaynağı |
|---|---|---|
| **A — Kod zinciri** | Zincirin halkaları kodda var mı? | Modül dosyaları, migration'lar, testler |
| **B — Runtime erişilebilirliği** | `run_dev.py` ile ayağa kalkan uygulamadan uçtan uca kullanılabiliyor mu? | `create_development_app()` bileşim tablosu (§2.2) |

Durum sınıfları denetim prompt'u §3'ten alınmıştır: `IMPLEMENTED`, `PARTIAL`,
`DOC_ONLY`, `MODEL_ONLY`, `BACKEND_ONLY`, `FRONTEND_ONLY`, `API_ONLY`,
`MOCK_ONLY`, `STUB`, `BROKEN`, `MISSING`, `EXTERNAL_DEPENDENCY`,
`NOT_APPLICABLE`. Her satırda ayrıca `yüksek` / `orta` / `düşük` kanıt güveni
verilir.

### 1.3 Ne doğrulanmadı

- Hiçbir test koşulmadı. Test **varlığı** dosya ve `pytestmark` seviyesinde
  doğrulandı; **geçtiği** doğrulanmadı.
- Uygulama ayağa kaldırılmadı; runtime davranışı kod okumasından çıkarıldı.
- Canlı PostgreSQL, Compose lab veya Playwright koşusu yapılmadı.
- Denetim bu worktree'de (`agent/36h1-persistent-job-core`, 40+ commit edilmemiş
  dosya) yapıldı; `main` ile farkı ölçülmedi (bkz. `work/01-Unresolved-Evidence-Questions.md`, Q-11).

### 1.4 Sayısal iddiaların yeniden üretimi

Aşağıdaki sayılar bu oturumda komutla üretilmiştir:

| İddia | Değer | Komut |
|---|---|---|
| API endpoint | **44** | `grep -cE '^\s+@app\.(get\|post\|put\|patch\|delete)' src/veri_kalitesi/api/app.py` |
| Alembic migration | **14** | `ls alembic/versions/*.py \| wc -l` |
| Frontend `<Route>` | **11** (9 fonksiyonel + `/unauthorized` + `*`) | `grep -cE '<Route ' frontend/src/App.tsx` |
| Backend Python dosyası | **174** | `find docs/backend/src -name '*.py' \| wc -l` |
| Birim test dosyası | **57** | `ls tests/unit/test_*.py \| wc -l` |
| Entegrasyon test dosyası | **11** | `ls tests/integration/test_*.py \| wc -l` |
| Playwright E2E spec | **7** | `ls frontend/e2e/*.spec.ts \| wc -l` |

> Envanter `05-Test-Inventory.md` "13 entegrasyon testi" ve
> `01-Backend-Module-Inventory.md` "176 backend dosyası" diyor; ölçülen değerler
> 11 ve 174'tür. Fark, `conftest.py` ve `__init__.py` sayımından kaynaklanıyor
> olabilir. Kanıt güveni: yüksek (komut çıktısı).

---

## 2. Çalıştırılabilir sistem sınırı

Bu bölüm, dokümanın geri kalanının okunma biçimini belirler.

### 2.1 Tek çalıştırılabilir giriş noktası

`pyproject.toml` içinde `console_scripts` / entry point **yok**. Repository'de
uygulamayı ayağa kaldıran tek dosya:

**[run_dev.py](../../scripts/run_dev.py)** → `create_development_app(session_factory, transactional_audit)`

- Veritabanı URL'i dosyaya sabit yazılmış: `postgresql+psycopg://dqtest:dqtest@127.0.0.1:55432/data_quality` ([run_dev.py:10](../../scripts/run_dev.py#L10))
- Audit prepared-event deposu `_FakePreparedRepo` — **no-op**, hiçbir şey saklamıyor ([run_dev.py:14-18](../../scripts/run_dev.py#L14-L18))
- Üretim için ayrı bir composition root **kanıt bulunamadı**. `create_dashboard_api()` 26+ opsiyonel bağımlılık alır ve hepsi `None` varsayılanıyla fail-closed'dur ([app.py:376-416](../../src/veri_kalitesi/api/app.py#L376-L416)); bu fonksiyonu dolduran yalnız iki çağıran vardır: `create_development_app()` ve birim testleri.

### 2.2 `create_development_app()` bileşim tablosu

[development.py:1134-1404](../../src/veri_kalitesi/api/development.py#L1134-L1404) okunarak çıkarılmıştır.

| Enjekte edilen bağımlılık | Bağlanan implementasyon | Kalıcılık gerçeği |
|---|---|---|
| `dashboard_service` | `DashboardQueryService(SQLiteScoreRepository, …)` | **Bellek içi SQLite**, seed skorlarla dolduruluyor ([L1147-L1216](../../src/veri_kalitesi/api/development.py#L1147-L1216)) |
| `data_source_query_service` | `DataSourceQueryService(DevelopmentDataSourceReader, …)` | **Statik demet** `DEVELOPMENT_SOURCES` |
| `data_source_mutation_service` | `DevelopmentDataSourceStore` | **Bellek içi dict + RLock**, audit yok ([L885-L891](../../src/veri_kalitesi/api/development.py#L885-L891)) |
| `rule_query_service` / `rule_creator_service` | `DevelopmentRuleReader` / `DevelopmentRuleStore` | **Bellek içi**, audit yok |
| `issue_query_service` + 6 issue mutasyon servisi | `DevelopmentIssueStore` (tek nesne, altısına birden) | **Bellek içi dict + RLock**, audit yok ([L603-L607](../../src/veri_kalitesi/api/development.py#L603-L607)) |
| `execution_query_service` | `ExecutionQueryService(DevelopmentExecutionReader, …)` | **Statik demet** `DEVELOPMENT_EXECUTIONS` ([L585-L600](../../src/veri_kalitesi/api/development.py#L585-L600)) |
| `execution_start_service` | `PostgreSQLExecutionStartService` | **Gerçek PostgreSQL** + job kuyruğuna enqueue ([L1332-L1339](../../src/veri_kalitesi/api/development.py#L1332-L1339)) |
| `execution_cancel_service` | `PostgreSQLExecutionCancelService` | **Gerçek PostgreSQL** ([L1340-L1344](../../src/veri_kalitesi/api/development.py#L1340-L1344)) |
| `report_service` | `ReportService(PostgreSQLReportRepository, …, inline_processing=True)` | PostgreSQL tablo; **kuyruk atlanıyor**, istek içinde üretim |
| Rapor veri sağlayıcısı | `_DevDataProvider` | **Sabit kodlanmış 4 satır**; gerçek skoru okumaz ([L1109-L1130](../../src/veri_kalitesi/api/development.py#L1109-L1130)) |
| `report_preview_service` | `ReportPreviewService(SQLiteReportPreviewReader, …)` | **Bellek içi SQLite** |
| `audit_query_service` | `AuditQueryService(SQLiteAuditRepository, …)` | **Bellek içi SQLite**, sentetik olaylarla dolduruluyor ([L1217-L1292](../../src/veri_kalitesi/api/development.py#L1217-L1292)) |
| `lineage_evidence_repository` / `governance_profile_reader` | PostgreSQL implementasyonları | **Gerçek PostgreSQL** (session factory verildiyse) |
| `actor_context_resolver` | `DevelopmentActorContextResolver` | Kimlik **istemcinin** gönderdiği `X-Development-User-Id` başlığıyla seçiliyor ([identity.py:246](../../src/veri_kalitesi/api/identity.py#L246)); kayıtta sekiz farklı rol/kapsam profili var ([identity.py:117-181](../../src/veri_kalitesi/api/identity.py#L117-L181)), `dev-privileged-user` dâhil ([L1316-L1325](../../src/veri_kalitesi/api/development.py#L1316-L1325)) |
| `rule_mutation_service` | **verilmiyor** | Kural sürüm/test/onay/aktivasyon uçları `503` döndürüyor ([app.py:554-564](../../src/veri_kalitesi/api/app.py#L554-L564)); yalnız `rule_creator_service` bağlı ([L1351](../../src/veri_kalitesi/api/development.py#L1351)) |
| `bff_session_boundary` | **verilmiyor** | Üretim auth yolu bağlı değil |

**Sonuç:** çalıştırılabilir uygulamada gerçek PostgreSQL'e giden yalnız dört yol
vardır — execution start/cancel, job kuyruğu enqueue, rapor kaydı ve lineage
kanıtı. Diğer her şey bellek içi veya sabit veridir.

**İki ek uyarı.** (1) Bu dört yoldan execution/job repository'leri `schema=`
argümanı almadıkları için `dq` şemasını, `run_dev.py` ile kurulan audit outbox
ise `data_quality` şemasını hedefler — aynı bileşimde şema ayrışması vardır
([08 §3.2](08-Existing-Schema-Gap-Analysis.md)). (2) Bağlanmayan portlar iki
farklı biçimde başarısız olur: `rule_mutation_service` gibi hiç verilmeyenler
`503` döndürür; `data_source_mutation_service` gibi **development store'a**
bağlananlar ise isteği kabul eder ve gerçek servisin onay/kapsam kontrollerini
atlar (GAP-027). İkincisi sessiz olduğu için daha risklidir.

### 2.3 Örneklenmeyen üretim bileşenleri

`grep -rl` ile tüm repo tarandı. Şu sınıflar **yalnız kendi modülünde, `__init__`
export'unda ve test dosyalarında** görünüyor:

| Sınıf | Örneklendiği yer |
|---|---|
| `PostgreSQLIssueRepository` | `tests/integration/test_postgresql_issue_{persistence,mutations}.py` |
| `PostgreSQLRuleRepository` | `tests/unit/test_postgresql_rule_repository.py`, `.../test_postgresql_rule_mutations.py` |
| `PostgreSQLDataSourceRepository` | `tests/unit/test_postgresql_data_source_repository.py`, `.../test_postgresql_data_source_persistence.py` |
| `PostgreSQLContributionGraphRepository` | `tests/integration/test_postgresql_score_contributions.py:82` |
| `BffSessionBoundary` | `tests/unit/test_bff_session_api.py:318` |
| `create_persistent_job_runtime()` | **hiçbir yerde çağrılmıyor** — yalnız tanım ve export |

`PersistentJobWorker.run_forever()` ([jobs/worker.py:76](../../src/veri_kalitesi/jobs/worker.py#L76)) tanımlı, ancak
çağıran bir daemon, script veya entry point **kanıt bulunamadı**.

---

## 3. Yetenek envanteri

Her yetenek için zincir halkaları, iki eksenli durum ve "zincirin ilk kırıldığı
nokta" verilir.

### 3.1 Dashboard ve genel bakış

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | [dashboard/models.py](../../src/veri_kalitesi/dashboard/models.py) — `DashboardOverview`, `DashboardScoreTrend`, `DashboardFilterParams`, `DashboardOperationalIndicators`, `DashboardMeasurementQualificationIndicator` | ✅ |
| migration | Kendi tablosu yok; `score_contribution_graphs` (migration 13) üzerinden okur | ⚠️ kısmi |
| repository | `SQLiteScoreRepository` (dev) — PostgreSQL karşılığı kanıt bulunamadı | ⚠️ |
| service | [dashboard/service.py](../../src/veri_kalitesi/dashboard/service.py) — `DashboardQueryService.get_overview()` | ✅ |
| API | `GET /api/v1/dashboard/summary` ([app.py:907](../../src/veri_kalitesi/api/app.py#L907)) | ✅ |
| frontend | [DashboardPage.tsx](../../frontend/src/dashboard/DashboardPage.tsx), `fetchDashboardSummary()` | ✅ |
| permission | `DashboardAuthorizationPolicy` + `can_view_enterprise` / scope filtresi ([service.py:161,174,199,348](../../src/veri_kalitesi/dashboard/service.py#L161)) | ✅ |
| audit | Doğrudan audit çağrısı kanıt bulunamadı | ❌ |
| test | `test_dashboard.py`, `test_dashboard_api.py`, `test_dashboard_filters.py`, `test_trend_components.py`; E2E `dashboard.spec.ts` | ✅ |

- **Eksen A:** `PARTIAL` — skor kalıcılığı SQLite üzerinde, `quality_scores` tablosu yok.
- **Eksen B:** `PARTIAL` — çalışıyor, fakat gösterdiği skorlar `create_development_app()` içinde üretilen seed verilerdir.
- **Kanıt güveni:** yüksek.
- **Zincirin ilk kırıldığı nokta:** repository — skorlar için PostgreSQL kalıcılığı yok, dashboard bellek içi SQLite'tan besleniyor.

### 3.2 Veri kaynağı onboarding ve yaşam döngüsü

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | [data_sources/models.py](../../src/veri_kalitesi/data_sources/models.py) — `DataSource`, `DataSourceStatus` (6 durum), `ConnectionTestResult` | ✅ |
| migration | `20260724_03_data_source_baseline.py` — `data_sources`, `connection_test_results`, `data_source_connection_revisions`, `data_source_activation_requests` | ✅ |
| repository | `PostgreSQLDataSourceRepository` — **yalnız testlerde örnekleniyor** | ⚠️ |
| service | `DataSourceQueryService` ([query.py](../../src/veri_kalitesi/data_sources/query.py)), mutasyon servisi [service.py](../../src/veri_kalitesi/data_sources/service.py) | ✅ |
| API | 5 endpoint: `GET/POST /data-sources`, `POST /{id}/test`, `/{id}/activation`, `/{id}/passivation` | ✅ |
| frontend | [DataSourcesPage.tsx](../../frontend/src/dataSources/DataSourcesPage.tsx); `api.ts` içinde 5 fonksiyonun tamamı | ✅ |
| permission | `permitted_source_ids` scope filtresi ([query.py:72,101,156](../../src/veri_kalitesi/data_sources/query.py#L72)); `AuthorizationError` | ✅ |
| audit | Servis katmanında var; **dev bileşiminde `DevelopmentDataSourceStore` audit almıyor** | ⚠️ |
| test | `test_data_sources.py`, `test_data_source_api.py`, `test_postgresql_data_source_repository.py`, `test_postgresql_data_source_persistence.py` (skip-gated), E2E `data-sources.spec.ts` | ✅ |

- **Eksen A:** `IMPLEMENTED` (maker-checker aktivasyon tabloları dahil).
- **Eksen B:** `MOCK_ONLY` — çalışabilir uygulamada `DevelopmentDataSourceStore` (bellek içi) bağlı; süreç yeniden başlayınca oluşturulan kaynak kaybolur, audit üretilmez.
- **Kanıt güveni:** yüksek.
- **Zincirin ilk kırıldığı nokta:** composition root — PostgreSQL repository hiçbir çalışabilir bileşime bağlanmamış.

### 3.3 Metadata keşfi ve veri kataloğu

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `MetadataDiscoveryResult`, `MetadataDiscoveryOptions`, `Dataset`, `DataField` ([models.py](../../src/veri_kalitesi/data_sources/models.py)) | ✅ |
| migration | `datasets`, `data_fields`, `metadata_discovery_results` (migration 03) | ✅ |
| repository | Tablolar mevcut; `PostgreSQLDataSourceRepository.replace_metadata` ([postgresql_repository.py:1145](../../src/veri_kalitesi/data_sources/postgresql_repository.py#L1145)) metadata yazımı + audit outbox'ı tek transaction'da yapar | ✅ |
| service | **Orkestrasyon seviyesinde:** `DataSourceService.discover_metadata` ([service.py:763](../../src/veri_kalitesi/data_sources/service.py#L763)) bağlantı durumunu denetler, hataları sınıflandırır, kimlikleri koruyarak normalize eder ve `_diff_metadata` ([service.py:1559](../../src/veri_kalitesi/data_sources/service.py#L1559)) ile fark üretir. Connector tanımları ([postgresql.py:73,137,226](../../src/veri_kalitesi/data_sources/postgresql.py#L73)) bunun altındaki katmandır | ✅ |
| API | **kanıt bulunamadı** — keşif tetikleyen veya dataset/kolon listeleyen endpoint yok | ❌ |
| frontend | **kanıt bulunamadı** — katalog sayfası yok | ❌ |
| permission | Servis `ActorContext` değil `actor_id` alır; HTTP yüzeyi olmadığı için uygulanmıyor | ⚠️ |
| audit | Gerçek PG yolunda outbox'a yazılıyor, fakat bu yol bileşime bağlı değil | ⚠️ |
| test | `test_data_sources.py` içinde **servis düzeyi** keşif/fark/profil testleri: `:843`, `:876`, `:892`, `:942`, outbox rollback `:523,548,573` | ✅ |

- **Eksen A:** `BACKEND_ONLY` — orkestrasyon, fark hesabı ve atomik kalıcılık
  var; HTTP yüzeyi yok. *(Düzeltme: bu satır daha önce keşfi "connector
  seviyesinde" gösteriyordu; servis düzeyi orkestrasyon mevcuttur.)*
- **Eksen B:** `MISSING` — kullanıcı metadata keşfi tetikleyemez, dataset/kolon göremez.
- **Kanıt güveni:** yüksek.
- **Zincirin ilk kırıldığı nokta:** API — keşif hiçbir endpoint'ten tetiklenemiyor.

### 3.4 Profilleme, snapshot ve drift

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `DataProfile`, `ProfileComparison`, `ProfileAnalysisPolicy`, `ProfileOptions` | ✅ |
| migration | `data_profiles` (03), `profile_comparisons` (11) | ✅ |
| repository | `profile_comparisons` tablosu + snapshot okuma | ✅ |
| service | `ProfileSnapshotQueryService`, `ProfileComparisonService`, [profiling.py](../../src/veri_kalitesi/data_sources/profiling.py) `compare_profile_snapshots`, `ProfilePolicyResolver` **ve yürütücü** `DataSourceService.run_profile` ([service.py:901](../../src/veri_kalitesi/data_sources/service.py#L901)) — CSV/PostgreSQL profil yürütücülerini çağırır ve sonucu kalıcılaştırır | ✅ |
| API | 4 endpoint: `POST /profile-comparisons`, `GET /profile-snapshots`, `/{id}`, `/{id}/drift` | ✅ |
| frontend | [ProfilingPage.tsx](../../frontend/src/profiling/ProfilingPage.tsx) — **yalnız 3 GET**; `POST /profile-comparisons` için istemci fonksiyonu **kanıt bulunamadı** | ⚠️ |
| permission | Politika sürümü yoksa fail-closed (hüküm üretilmez) | ✅ |
| audit | **kanıt bulunamadı** | ❌ |
| test | `test_profile_analysis.py`, `test_profile_snapshot_query.py` ve `test_data_sources.py` içinde `run_profile` testleri (`:968,1015,1117,1159,1175,1242,1313,1397,1464`, outbox rollback `:573`); E2E **yok** | ✅ |

- **Eksen A:** `PARTIAL` — profil yürütücüsü ve karşılaştırma mantığı var;
  profil **talep etme** ucu (`POST /datasets/{id}/profiles`) ve karşılaştırma
  yaratma UI'ı yok. *(Düzeltme: "profil yürütücüsü yok" değerlendirmesi
  yanlıştır; `run_profile` mevcut ve testlidir — eksik olan onu çağıran
  HTTP ucu ve kuyruk bağıdır.)*
- **Eksen B:** `PARTIAL` — kullanıcı mevcut snapshot'ları ve drift hükmünü görebilir, yeni profil veya karşılaştırma başlatamaz.
- **Kanıt güveni:** yüksek.
- **Zincirin ilk kırıldığı nokta:** API/frontend — `run_profile` için hiç uç
  yok; `POST /profile-comparisons` `API_ONLY`.

### 3.5 Kural yaşam döngüsü

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | [rules/models.py](../../src/veri_kalitesi/rules/models.py) — `QualityRule`, `RuleVersion`, `RuleStatus` (5), `RuleType` (8), `QualityDimension` (7), `RuleCriticality` (4) | ✅ |
| migration | `20260723_02_rule_baseline.py` — `quality_rules`, `rule_versions`, `rule_test_results` | ✅ |
| repository | `PostgreSQLRuleRepository` — **yalnız testlerde örnekleniyor** | ⚠️ |
| service | `RuleQueryService`, `RuleCreatorService`, `RuleMutationService` ([rules/service.py](../../src/veri_kalitesi/rules/service.py)) | ✅ |
| API | 9 endpoint (create, version, test, activation, passivation, approval, decide, withdraw, list) | ✅ |
| frontend | [RulesPage.tsx](../../frontend/src/rules/RulesPage.tsx); `rules/api.ts` içinde 9 fonksiyonun **tamamı** kullanılıyor | ✅ |
| permission | Rol kontrolü: `context.roles.isdisjoint(stewards)` ([service.py:402,797](../../src/veri_kalitesi/rules/service.py#L402)) | ✅ |
| audit | `RuleTransactionalAudit` protokolü ([rules/contracts.py:22](../../src/veri_kalitesi/rules/contracts.py#L22)) | ✅ |
| test | `test_rules.py`, `test_rule_api.py`, `test_postgresql_rule_repository.py`, `test_postgresql_rule_mutations.py` (skip-gated), E2E `rules.spec.ts` | ✅ |

- **Eksen A:** `IMPLEMENTED` — zincirin dokuz halkası da mevcut. Repository'de en eksiksiz yetenek.
- **Eksen B:** `MOCK_ONLY` — çalışabilir uygulamada `DevelopmentRuleStore` (bellek içi) bağlı.
- **Kanıt güveni:** yüksek.
- **Zincirin ilk kırıldığı nokta:** composition root.

### 3.6 Kural onayı (maker-checker)

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `RuleApprovalRequest`, `RuleApprovalPolicy`, `RuleApprovalStatus` (5 durum) | ✅ |
| migration | `rule_approval_requests` — kısmi UNIQUE: `rule_version_id WHERE status='PENDING'`; partial index `ix_dq_rule_approval_requests_pending_expires` | ✅ |
| repository | Migration 02 içinde; PostgreSQL repository test-only | ⚠️ |
| service | `RuleMutationService` approve/reject/withdraw; `policy.expiry_service_roles` kontrolü ([service.py:763](../../src/veri_kalitesi/rules/service.py#L763)) | ✅ |
| API | `POST /rules/{id}/approval`, `/rules/approval/{id}/decide`, `/rules/approval/{id}/withdraw` | ✅ |
| frontend | `RulesPage` içinde satır içi; `requestRuleApproval`, `decideRuleApproval`, `withdrawRuleApproval` | ✅ |
| permission | Maker ≠ checker ayrımı `maker_actor_id` / `checker_actor_id` kolonlarıyla; rol kontrolü servis içinde | ✅ |
| audit | Transactional audit protokolü üzerinden | ✅ |
| test | `test_rules.py`, `test_rule_api.py`, `test_postgresql_rule_mutations.py` | ✅ |

- **Eksen A:** `IMPLEMENTED` — maker-checker veri tabanı seviyesinde constraint'le korunmuş.
- **Eksen B:** `MOCK_ONLY`.
- **Kanıt güveni:** yüksek.

### 3.7 Kural IR ve SHADOW modu

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `ExecutionMode.SHADOW` ([executions/models.py:22](../../src/veri_kalitesi/executions/models.py#L22)) | ✅ |
| migration | `20260730_12_rule_ir_shadow_evidence.py` — `rule_versions`'a IR shadow kanıt kolonları | ✅ |
| repository | ALTER edilen tablo üzerinden | ✅ |
| service | Kanıt kısmi; DQ-CAP-PROTOTYPE-02 çıktısı | ⚠️ |
| API | **kanıt bulunamadı** — SHADOW çalıştırma tetikleyen endpoint yok | ❌ |
| frontend | **kanıt bulunamadı** | ❌ |
| permission | **kanıt bulunamadı** | ❌ |
| audit | **kanıt bulunamadı** | ❌ |
| test | `test_prototype_05_capabilities.py` içinde kısmi | ⚠️ |

- **Eksen A:** `PARTIAL` — migration ve enum var, kullanıcı yolu yok.
- **Eksen B:** `MISSING`.
- **Kanıt güveni:** orta — prototip kapsamı dağınık.

### 3.8 Çalıştırma başlatma, iptal ve sonuç

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `RuleExecution`, `RuleExecutionResult`, `ExecutionAttempt`, `RetryPolicy`, `ConcurrencyPolicy`, `ExecutionStatus` (8 durum) | ✅ |
| migration | `20260724_04_execution_baseline.py` — `rule_executions` (idempotency_key_hash unique), `execution_attempts`, `rule_execution_results` | ✅ |
| repository | `PostgreSQLExecutionRepository` — **çalışabilir bileşimde kullanılıyor** | ✅ |
| service | `PostgreSQLExecutionStartService`, `PostgreSQLExecutionCancelService` ([api/postgresql_execution.py](../../src/veri_kalitesi/api/postgresql_execution.py)), `ExecutionStrategyEngine` | ✅ |
| API | `GET /executions`, `POST /executions`, `POST /executions/{id}/cancel` | ✅ |
| frontend | [executions/api.ts](../../frontend/src/executions/api.ts) **yalnız `fetchExecutions`** içeriyor; `ExecutionsPage` salt okunur liste + arama + yenile | ❌ |
| permission | `ExecutionQueryService` scope filtresi | ✅ |
| audit | `ExecutionTransactionalAudit` protokolü ([executions/contracts.py:21](../../src/veri_kalitesi/executions/contracts.py#L21)); PostgreSQL outbox'a staged | ✅ |
| test | `test_executions.py`, `test_execution_api.py`, `test_postgresql_execution_repository.py`, `test_postgresql_execution_persistence.py` (skip-gated), E2E `executions.spec.ts` | ✅ |

- **Eksen A:** `PARTIAL` — backend tam, frontend komut yüzeyi yok.
- **Eksen B:** `BROKEN`. **Bu, repository'deki en somut kopuk zincirdir:**
  `POST /api/v1/executions` gerçek PostgreSQL'e yazarken, `GET /api/v1/executions`
  statik `DEVELOPMENT_EXECUTIONS` demetinden okur
  ([DevelopmentExecutionReader](../../src/veri_kalitesi/api/development.py#L585-L600)).
  Başlatılan bir çalıştırma listede **hiçbir zaman görünmez**.
- **Kanıt güveni:** yüksek.
- **Zincirin ilk kırıldığı nokta:** frontend (komut yok) ve dev bileşimi (yazma/okuma farklı kaynağa gidiyor).

### 3.9 Zamanlama (schedule)

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `Schedule` (`:71`), `ScheduleType` (`:63`) ([executions/scheduling.py](../../src/veri_kalitesi/executions/scheduling.py)) | ✅ |
| migration | `20260724_05_scheduling_and_policy_baseline.py` — `schedules` (`next_run_at`, `is_active`, cron alanları) | ✅ |
| repository | `SQLiteScheduleRepository` (`scheduling.py:92`) ve `PostgreSQLScheduleRepository` ([postgresql_scheduling.py:64](../../src/veri_kalitesi/executions/postgresql_scheduling.py#L64)); due sorgusu L109-L124 — **claim/lock protokolü yok** | ⚠️ |
| service | `SchedulingService` (`scheduling.py:218`): `create_schedule` (`:234`), `trigger_due` (`:303`), `preview_runs` (`:343`); zaman dilimi doğrulaması, DST'de var olmayan yerel saatlerin elenmesi (`:383`) ve `schedule:{id}:{scheduled_for}` idempotency anahtarı (`:311`) | ✅ |
| API | **kanıt bulunamadı** — `/api/v1/schedules` yok | ❌ |
| frontend | **kanıt bulunamadı** | ❌ |
| permission | Servis güvenilir `ActorContext` değil yalnız `actor_id` alır | ⚠️ |
| audit | `SCHEDULE_CREATED` üretilir; outbox hatasında oluşturma geri alınır (testli). Durum değişimi/silme/tetikleme olayları yok | ⚠️ |
| test | **10 birim testi** ([test_executions.py](../../tests/unit/test_executions.py) `:643-1005`): günlük/haftalık/aylık zamanlama, önizleme, idempotent tetikleme (`:804`), audit kesintisinde dayanıklılık (`:678`), outbox rollback (`:707`), DST (`:978`), geçersiz tanım ve pasif kural senaryoları | ✅ |

- **Eksen A:** `BACKEND_ONLY` — servis, iki repository ve kapsamlı birim
  testleri var; çağıran süreç ve HTTP yüzeyi yok. *(Düzeltme: bu satır daha
  önce `MODEL_ONLY` ve "test kanıtı yok" diyordu; her ikisi de yanlıştı.)*
- **Eksen B:** `MISSING` — zamanlanmış çalıştırma imkânsız; **hiçbir scheduler daemon'ı kanıt bulunamadı**.
- **Kanıt güveni:** yüksek.
- **Zincirin ilk kırıldığı nokta:** daemon/bileşim — `SchedulingService.trigger_due`
  üretimde hiçbir yerden çağrılmıyor. İkinci sırada, PG due sorgusunda
  `FOR UPDATE SKIP LOCKED` olmadığı için çok zamanlayıcılı tek kazanan
  garantisi yok.

### 3.10 Kalıcı iş kuyruğu, lease, heartbeat ve dead-letter

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `BackgroundJob`, `JobStatus`, `DeadLetterRecord`, `JobLeasePolicy`, `JobRetryPolicy` | ✅ |
| migration | `20260728_08_job_queue.py` (`persistent_jobs`: lease_expires_at, last_heartbeat_at, version), `20260729_09_job_lifecycle.py` (`dead_letter_records`, cancel kolonları) | ✅ |
| repository | `PostgreSQLJobQueueRepository` — çalışabilir bileşimde **enqueue için** kullanılıyor | ✅ |
| service | `PersistentJobWorker` (claim/heartbeat/`run_forever`), `DeadLetterReprocessService`, `ExecutionJobHandler` + `ReportJobHandler` ([jobs/handlers.py](../../src/veri_kalitesi/jobs/handlers.py)) | ✅ |
| API | **kanıt bulunamadı** — job listeleme, dead-letter görüntüleme/replay endpoint'i yok | ❌ |
| frontend | **kanıt bulunamadı** — operasyon ekranı yok | ❌ |
| permission | `JobAuthorizationError` + `lifecycle.py:57` `allowed_roles` kontrolü | ✅ |
| audit | Terminal/cancel/dead-letter geçişlerinde `PostgreSQLTransactionalAudit` ([jobs/worker.py:362](../../src/veri_kalitesi/jobs/worker.py#L362)). **Sahiplenme audit'siz:** `claim_next` ([postgresql_repository.py:271](../../src/veri_kalitesi/jobs/postgresql_repository.py#L271)) audit/outbox parametresi almaz ve `stage` çağırmaz | ⚠️ |
| test | `test_job_queue.py`, `test_persistent_job_worker.py`, `test_persistent_job_handlers.py`, `test_postgresql_job_queue.py` (skip-gated). `create_persistent_job_runtime` için test **yok** | ✅ |

- **Eksen A:** `BACKEND_ONLY` — kuyruk çekirdeği geniş ölçüde yazılmış, fakat
  hedefe göre **eksiksiz değil**: (a) `claim_next` `JOB_CLAIMED` audit'i
  üretmez, dolayısıyla "durum geçişi + audit aynı transaction'da" garantisi
  sahiplenme için yoktur; (b) uygulanan `JobStatus` kümesi
  (`QUEUED`/`RUNNING`/`CANCEL_REQUESTED` + sonuç durumları) hedefteki
  `AVAILABLE`/`CLAIMED`/`BLOCKED`/`DEAD_LETTERED` ayrımını taşımaz —
  `QUEUED` doğrudan `RUNNING` olur ve `BLOCKED` karşılığı yoktur. Operatör
  yüzeyi de yok.
- **Eksen B:** `BROKEN` — `create_persistent_job_runtime()` **hiç çağrılmıyor** (testler dâhil; testler `PersistentJobWorker`'ı elle kurar), `run_forever()` için entry point yok; `pyproject.toml`'da `[project.scripts]` tablosu yok. Execution start job'u kuyruğa yazar; **hiçbir şey işlemez**. Job `QUEUED` durumunda kalır.
- **Kanıt güveni:** yüksek.
- **Zincirin ilk kırıldığı nokta:** composition/deployment — worker süreci başlatılmıyor.

### 3.11 Skorlama ve katkı grafiği

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `QualityScore`, `ScoringConfiguration`, `ThresholdSet`, `ScoreStatus`, `ScoreLevel` ([scoring/models.py](../../src/veri_kalitesi/scoring/models.py)) | ✅ |
| migration | `20260730_13_score_contribution_graphs.py` — yalnız `score_contribution_graphs`. **`quality_scores` tablosu yok** | ⚠️ |
| repository | `PostgreSQLContributionGraphRepository` ([postgresql_contributions.py:47](../../src/veri_kalitesi/scoring/postgresql_contributions.py#L47)) — **yalnız testte örnekleniyor**; skorların kendisi `SQLiteScoreRepository`'de | ⚠️ |
| service | [scoring/service.py](../../src/veri_kalitesi/scoring/service.py), [contributions.py](../../src/veri_kalitesi/scoring/contributions.py), [partial_score_policies.py](../../src/veri_kalitesi/scoring/partial_score_policies.py), [trends.py](../../src/veri_kalitesi/scoring/trends.py) | ✅ |
| API | **kanıt bulunamadı** — `/api/v1/scores` yok; skorlar yalnız dashboard özeti içinde | ❌ |
| frontend | Ayrı skor sayfası yok; `ScoreContributionPanel.tsx`, `FieldScoreComparison.tsx` dashboard içinde | ⚠️ |
| permission | `partial_score_policies.py:617-619` — rol + dataset scope kontrolü | ✅ |
| audit | `SQLiteTransactionalAudit` üzerinden ([partial_score_policies.py:477,527,581](../../src/veri_kalitesi/scoring/partial_score_policies.py#L477)) — **PostgreSQL outbox değil** | ⚠️ |
| test | `test_scoring.py`, `test_score_contributions.py`, `test_partial_score_policies.py`, `test_postgresql_score_contributions.py` (skip-gated) | ✅ |

- **Eksen A:** `PARTIAL` — hesaplama mantığı zengin, kalıcılık yarım (katkı grafiği PostgreSQL, skorun kendisi SQLite), doğrudan API yok.
- **Eksen B:** `PARTIAL` — kullanıcı skoru yalnız dashboard toplamı olarak görür, tekil skor kaydına ulaşamaz.
- **Kanıt güveni:** yüksek.
- **Zincirin ilk kırıldığı nokta:** migration — hesaplanan skoru saklayan tablo yok.

### 3.12 Issue (sorun) yaşam döngüsü

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `DataQualityIssue`, `IssueStatus` (8 durum), `IssueResolutionDraft`, `IssueVerificationRecord`, `IssueRelationship` | ✅ |
| migration | `20260723_01_issue_baseline.py` — `data_quality_issues`, `issue_history`, `issue_resolutions`, `issue_verifications`, `issue_relationships`, `audit_outbox` | ✅ |
| repository | `PostgreSQLIssueRepository` — **yalnız testlerde örnekleniyor** | ⚠️ |
| service | [issues/service.py](../../src/veri_kalitesi/issues/service.py) — investigation, assignment, resolution, verification, closure servisleri **ve üretici** `IssueService.create_for_trigger` ([:139](../../src/veri_kalitesi/issues/service.py#L139)): güvenilir servis bağlamı zorunlu, deterministik tekilleştirme (`uuid5`, `:165`), yinelenme ilişkisi ve `DATA_QUALITY_ISSUE_REOPENED` audit'i (`:194-260`) | ✅ |
| API | 8 endpoint | ✅ |
| frontend | [IssuesPage.tsx](../../frontend/src/issues/IssuesPage.tsx) — 7 mutasyon fonksiyonunun tamamı bağlı | ✅ |
| permission | Scope filtresi + farklı aktörle doğrulama kuralı; `issues/models.py:92,233` | ✅ |
| audit | `transactional_audit.publish_pending()` altı ayrı akışta ([service.py:304,399,496,604,718,805](../../src/veri_kalitesi/issues/service.py#L304)) | ✅ |
| test | `test_issues.py`, `test_issue_api.py`, `test_investigation_evidence.py` + üç PostgreSQL entegrasyon dosyası (skip-gated), E2E `issues.spec.ts` | ✅ |

- **Eksen A:** `IMPLEMENTED` — zincirin dokuz halkası da doğrulandı.
- **Eksen B:** `MOCK_ONLY` — `DevelopmentIssueStore` tek nesne olarak altı mutasyon servisine birden bağlanmış; bellek içi, audit üretmiyor.
- **Kanıt güveni:** yüksek.
- **Ek tespit (düzeltilmiş):** üretici **servis vardır** (yukarıya bakınız) ve
  `PostgreSQLIssueRepository.add_or_increment`
  ([:234](../../src/veri_kalitesi/issues/postgresql_repository.py#L234))
  advisory lock + satır kilidiyle issue/history/ilişki yazımını ve audit
  outbox'ı tek transaction'da yapar; her ikisinin de birim ve PG testleri
  vardır. Eksik olan **çağrıdır**: `create_for_trigger` repo genelinde yalnız
  tanım ve iki test çağrısı olarak geçer, üretim kodunda çağıran yoktur.
  Issue'lar bu nedenle yalnız seed veriden gelir.
- **Ek tespit — uygunluk kapısı yok:** `RuleExecutionResult.eligible_for_auto_issue`
  ([executions/models.py:168](../../src/veri_kalitesi/executions/models.py#L168))
  hesaplanır ve kalıcılaştırılır, fakat `IssueTrigger` bu alanı taşımaz ve
  `create_for_trigger` onu doğrulamaz — `issues/` altında bu ad hiç geçmez.
  Yani yalnız bir çağıran eklemek, uygunsuz sonuçların kalite sorunu
  üretmesini engellemeye yetmez (GAP-006).

### 3.13 İnceleme kanıtı (investigation evidence)

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `InvestigationEvidence` ([issues/investigation.py](../../src/veri_kalitesi/issues/investigation.py)) | ✅ |
| migration | Kendi tablosu yok; execution/result tablolarından okur | ⚠️ |
| repository | Okuma yolu servis içinde | ✅ |
| service | `IssueInvestigationEvidenceService` | ✅ |
| API | `GET /issues/{id}/investigation/evidence` | ✅ |
| frontend | [InvestigationPage.tsx](../../frontend/src/issues/InvestigationPage.tsx) + `/investigation` route | ✅ |
| permission | Scope üzerinden | ✅ |
| audit | Kanıt bulunamadı | ❌ |
| test | `test_investigation_evidence.py`; E2E **yok** | ⚠️ |

- **Eksen A:** `IMPLEMENTED`.
- **Eksen B:** `PARTIAL` — dev store'daki seed issue'lar üzerinden çalışır.
- **Kanıt güveni:** yüksek.

### 3.14 Raporlama ve güvenli indirme

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `Report`, `ReportType`, `ReportStatus`, `ReportFormat`, `ReportPreview`, `ReportSummaryRow` | ✅ |
| migration | `20260724_06_reporting_baseline.py` — `reports` (sensitivity_level, expires_at, online_file_reference, version) | ✅ |
| repository | `PostgreSQLReportRepository` — **çalışabilir bileşimde kullanılıyor** | ✅ |
| service | `ReportService`, `ReportPreviewService`, `ReportWorker` | ✅ |
| API | 5 endpoint: summary, create, list, get, download | ✅ |
| frontend | [ReportsPage.tsx](../../frontend/src/reports/ReportsPage.tsx); create/list/download bağlı | ✅ |
| permission | `ReportPreviewAccessPolicy`, `ReportExportPolicy` — hassasiyet seviyesine göre fail-closed | ✅ |
| audit | `audit_service` enjekte ediliyor | ✅ |
| test | `test_reporting.py`, `test_report_api.py`, `test_postgresql_report_lifecycle.py` (skip-gated), E2E `reports.spec.ts` | ✅ |

- **Eksen A:** `IMPLEMENTED`.
- **Eksen B:** `PARTIAL` — üç kısıt: (1) `inline_processing=True` ile kuyruk atlanıyor, rapor istek içinde üretiliyor; (2) veri sağlayıcı `_DevDataProvider` **sabit 4 satır** döndürüyor, gerçek skoru okumuyor; (3) dosya deposu `/tmp/reports-dev`.
- **Kanıt güveni:** yüksek.
- **Zincirin ilk kırıldığı nokta:** veri sağlayıcı — üretilen rapor gerçek sistem verisini içermiyor.

### 3.15 Rapor zamanlaması

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `ReportSchedule` | ✅ |
| migration | `20260724_07_report_schedules.py` — `report_schedules` (next_run_at, recipients, cron alanları) | ✅ |
| repository | PostgreSQL tablo | ✅ |
| service | `ReportScheduleService` ([reporting/scheduling.py](../../src/veri_kalitesi/reporting/scheduling.py)) | ✅ |
| API | 4 endpoint: list, create, delete, `POST /report-schedules/trigger-due` | ✅ |
| frontend | `reports/api.ts` içinde `fetchSchedules`, `createSchedule`, `deleteSchedule` **var**; `ReportsPage` `scheduleItems`, `onCreateSchedule`, `onDeleteSchedule` **props'larını tanımlıyor** ([ReportsPage.tsx:59-65](../../frontend/src/reports/ReportsPage.tsx#L59-L65)) — **ancak `ReportsRoute` bu fonksiyonları import edip hiç kullanmıyor** ([App.tsx:61](../../frontend/src/App.tsx#L61) import, [App.tsx:620-675](../../frontend/src/App.tsx#L620-L675) kullanım yok) | ❌ |
| permission | CSRF + actor scope | ✅ |
| audit | `audit_service` üzerinden | ✅ |
| test | `reports/api.test.ts:182-269` üç zamanlama fonksiyonunu test ediyor; backend testi **kanıt bulunamadı** | ⚠️ |

- **Eksen A:** `PARTIAL`.
- **Eksen B:** `BROKEN` — `ReportsPage` varsayılan olarak `scheduleItems = syntheticSchedules` ([ReportsPage.tsx:747](../../frontend/src/reports/ReportsPage.tsx#L747)) kullanır. Kullanıcı **sentetik zamanlama listesi görür**, gerçek olanları görmez; oluşturma/silme handler'ları `undefined` olduğu için işlem yapılamaz.
- **Kanıt güveni:** yüksek.
- **Zincirin ilk kırıldığı nokta:** route bağlantısı — istemci ve props hazır, `ReportsRoute` bağlamamış.
- **Ek tespit:** `trigger-due` endpoint'i için frontend istemcisi **kanıt bulunamadı**; zamanlanmış raporu tetikleyen daemon da yok — yalnız manuel HTTP çağrısıyla çalışır.

### 3.16 Audit ve outbox

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `AuditEvent`, `PreparedAuditEvent`, `AuditQuery`, `AuditQueryPage`, `AuditRedactionPolicy` | ✅ |
| migration | `audit_outbox` (migration 01) — `prepared_event` JSON, status PENDING/PUBLISHED, partial index | ✅ |
| repository | `PostgreSQLTransactionalAudit` (prepare/stage/publish_pending) ([postgresql_outbox.py:47-135](../../src/veri_kalitesi/audit/postgresql_outbox.py#L47-L135)) | ✅ |
| service | `AuditService`, `AuditQueryService` ([audit/service.py](../../src/veri_kalitesi/audit/service.py)) | ✅ |
| API | `GET /api/v1/audit/events` — cursor pagination + actor/action/object/result filtresi | ✅ |
| frontend | [AuditPage.tsx](../../frontend/src/audit/AuditPage.tsx) | ✅ |
| permission | `policy.required_role not in context.roles` ([service.py:342](../../src/veri_kalitesi/audit/service.py#L342)); erişim reddi de audit'leniyor (`_record_denial`, `_record_view`) | ✅ |
| audit | Zincir bütünlüğü: `previous_event_hash`, `event_hash`, `verify_integrity()` | ✅ |
| test | `test_audit.py`, `test_audit_api.py`; E2E `audit.spec.ts` | ✅ |

- **Eksen A:** `IMPLEMENTED` — outbox, redaction, hash zinciri ve erişim audit'i mevcut.
- **Eksen B:** `MOCK_ONLY` — çalışabilir uygulamada sorgu tarafı `SQLiteAuditRepository` (bellek içi, sentetik olaylarla dolu); `run_dev.py`'de prepared-event deposu `_FakePreparedRepo` **no-op**. Yani `publish_pending()` çağrıldığında olay hiçbir kalıcı yere yazılmaz.
- **Kanıt güveni:** yüksek.
- **Ek tespit:** `app.py` içinde **hiç audit çağrısı yok** (0 eşleşme). Audit tamamen servis katmanında, transaction içinde staged edilir. Bu mimari olarak doğrudur; ancak audit almayan servisler (dev store'lar, dashboard, profilleme) HTTP yüzeyinden de audit üretmez.

### 3.17 Kimlik, oturum ve yetkilendirme

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `ActorContext` (actor_id, roles, permitted_source_ids, permitted_dataset_ids, can_view_enterprise, privileged), `DashboardAuthorizationPolicy` | ✅ |
| migration | **`users`, `roles`, `permissions`, `sessions` tabloları kanıt bulunamadı** | ❌ |
| repository | `identity/sessions.py` oturum deposu (SQLite tabanlı), `identity/ldap.py` dizin adaptörü, `identity/throttling.py` | ⚠️ |
| service | `SessionService`, `PolicyAuthorizationService`, `BffSessionBoundary` ([api/bff.py](../../src/veri_kalitesi/api/bff.py)) | ✅ |
| API | `POST /api/v1/session/logout`, `GET /api/v1/development/users` | ⚠️ |
| frontend | [DevelopmentLoginPage.tsx](../../frontend/src/development/DevelopmentLoginPage.tsx) + `UserContext` — **dev kullanıcı seçici**; üretim login ekranı yok | ⚠️ |
| permission | **Okuma yolunda uygulanıyor:** `PolicyAuthorizationService` kararındaki izinli kimlikler dört sorgu servisinde reader filtresine taşınıyor ve boş kapsam dört testle sabitlenmiş. **Komut yolunda uygulanmıyor:** veri kaynağı route'ları aktör bağlamını porta iletmiyor (`app.py:2017-2110`) | ⚠️ |
| audit | Oturum olayları `identity/service.py:178`; yetki kararları ALLOW/DENY olarak audit'leniyor | ✅ |
| test | `test_identity.py` (42 test), `test_bff_session_api.py`, kapsam testleri | ✅ |

- **Eksen A:** `PARTIAL` — kimlik doğrulama sınırı, SQLite oturum deposu ve
  LDAP adaptörü kodda var; kullanıcı/rol kalıcılığı yok.
- **Eksen B:** `MOCK_ONLY` — `DevelopmentActorContextResolver`,
  `X-Development-User-Id` başlığıyla çalışır. *(Düzeltme: roller sabit tek bir
  küme değildir.)* `api/identity.py:91 build_default_development_users`
  **sekiz** profil tanımlar (`:117-181`): viewer, steward, owner, governance,
  engineer, `dev-audit-viewer` (`can_view_enterprise=False`),
  `dev-limited-steward` (kısıtlı kaynak/dataset kapsamı) ve
  `dev-privileged-user`. Belirleyici sorun rol çeşitliliği değil, **profilin
  istemci tarafından seçilmesidir**: başlık bir güven sınırı değildir.
  `BffSessionBoundary` çalışabilir hiçbir bileşime bağlı değil
  (`api/app.py:380` opsiyonel parametre, verilmezse `:416`
  `UnavailableActorContextResolver`'a düşer; tek örnekleme yeri
  `test_bff_session_api.py:318`).
- **Kanıt güveni:** yüksek.
- **Zincirin ilk kırıldığı nokta:** migration — kullanıcı/rol/izin kalıcılığı hiç yok.
- **İkinci kırılma:** komut yolunda yetkilendirme. Kimlik middleware'de
  çözülüyor (`app.py:433-453`), fakat route'lar bunu mutation portuna
  iletmiyor; dolayısıyla durum "kimlik yok" değil **"kimlik var, yetki
  denetimi yok"**tur (GAP-027).

### 3.18 Lineage ve yönetişim profili

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `LineageEvent`, `ColumnLineageEdge` ([lineage/events.py](../../src/veri_kalitesi/lineage/events.py)), `DataAssetGovernanceProfile`, `GovernanceRoutingPolicy` ([lineage/governance.py](../../src/veri_kalitesi/lineage/governance.py)) | ✅ |
| migration | `20260730_14_lineage_governance_evidence.py` — `lineage_evidence_snapshots` (snapshot_kind, subject_ref, digest, payload JSONB). **`LineageEvent` için ayrı tablo yok** | ⚠️ |
| repository | `PostgreSQLLineageEvidenceRepository` — **çalışabilir bileşimde kullanılıyor** | ✅ |
| service | `GovernanceProfileReader` | ✅ |
| API | `GET /lineage/snapshots/{id}`, `GET /governance/{asset_ref}/projection` | ✅ |
| frontend | `issues/api.ts` içinde `fetchLineageSnapshot`, `fetchGovernanceProjection`; [InvestigationPage.tsx:377-378](../../frontend/src/issues/InvestigationPage.tsx#L377-L378) her ikisini de **çağırıyor** | ✅ |
| permission | Actor resolve + fail-closed yönlendirme | ✅ |
| audit | Kanıt bulunamadı | ❌ |
| test | `test_lineage_governance.py`, `test_postgresql_lineage_evidence.py` (skip-gated) | ✅ |

- **Eksen A:** `PARTIAL` — salt okunur kanıt yüzeyi tam; etki analizi (`lineage/impact.py`) için API/UI yok.
- **Eksen B:** `PARTIAL` — inceleme sayfası içinde çalışır; bağımsız lineage/etki ekranı yok.
- **Kanıt güveni:** yüksek.
- **Envanter düzeltmesi:** `07-Implementation-Status-Matrix.md` bu alanı "`BE_ONLY` — API var, UI yok" diyor. **Kod kanıtı aksini gösteriyor**: `InvestigationPage` her iki endpoint'i de kullanıyor.

### 3.19 Bildirim

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `NotificationEvent`, `Notification`, `NotificationAccessPolicy` ([notifications/models.py](../../src/veri_kalitesi/notifications/models.py)) | ✅ |
| migration | **kanıt bulunamadı** | ❌ |
| repository | `notifications/repository.py` — SQLite/protokol tabanlı | ⚠️ |
| service | `notifications/service.py`, `channel_adapters.py` (email/webhook/SMS) | ✅ |
| API | **kanıt bulunamadı** | ❌ |
| frontend | **kanıt bulunamadı** | ❌ |
| permission | `NotificationAuthorizationError` tanımlı | ⚠️ |
| audit | **kanıt bulunamadı** | ❌ |
| test | `test_notifications.py`, `test_prototype_05_capabilities.py` | ⚠️ |

- **Eksen A:** `MODEL_ONLY`.
- **Eksen B:** `MISSING` — **`NotificationService` modül dışında hiçbir yerden çağrılmıyor.** Kural başarısızlığı, issue oluşumu veya SLA aşımı bildirim üretmez.
- **Kanıt güveni:** yüksek.
- **Zincirin ilk kırıldığı nokta:** çağrı noktası — servis yazılmış, tetikleyicisi yok.

### 3.20 Saklama, imha, legal hold ve arşiv geri çağırma

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `RetentionPolicy`, `LegalHold`, `DisposalJob`, `ArchiveRecallDecision` | ✅ |
| migration | **kanıt bulunamadı** | ❌ |
| repository | `retention/repository.py`, `disposal_repository.py`, `archive_recall_repository.py` — SQLite | ⚠️ |
| service | `RetentionService`, `DisposalService`, `ArchiveRecallService` | ✅ |
| API | **kanıt bulunamadı** | ❌ |
| frontend | **kanıt bulunamadı** | ❌ |
| permission | Rol kesişimi kontrolü ([service.py:220](../../src/veri_kalitesi/retention/service.py#L220), `disposal_service.py:318`, `archive_recall_service.py:246`) | ✅ |
| audit | SQLite audit üzerinden | ⚠️ |
| test | `test_retention.py`, `test_retention_disposal_job.py`, `test_retention_legal_hold.py`, `test_retention_archive_recall.py` | ✅ |

- **Eksen A:** `MODEL_ONLY` — dört test dosyası olmasına rağmen PostgreSQL kalıcılığı ve HTTP yüzeyi yok.
- **Eksen B:** `MISSING`.
- **Kanıt güveni:** yüksek.

### 3.21 Sentetik veri ve ground truth

| Halka | Kanıt | Var mı |
|---|---|---|
| domain | `SyntheticGenerationRun`, `SyntheticGroundTruth`, `SyntheticValidationResult` | ✅ |
| migration | **kanıt bulunamadı** | ❌ |
| repository | `synthetic_data/postgresql_dataset.py` (üretilen dataset için), `repository.py` SQLite | ⚠️ |
| service | `SyntheticDataService`, `generator.py`, `oracle.py`, `temporal.py`, `finalization.py`, `canonical` | ✅ |
| API | **kanıt bulunamadı** | ❌ |
| frontend | **kanıt bulunamadı** | ❌ |
| permission | `synthetic_data/authorization.py:22-49` — rol + dataset scope | ✅ |
| audit | `SQLiteTransactionalAudit` ([oracle.py:139,146](../../src/veri_kalitesi/synthetic_data/oracle.py#L139)) | ⚠️ |
| test | 5 birim + `test_synthetic_postgresql_integration.py` (skip-gated) | ✅ |
| scripts | `scripts/generate_synthetic_test_data.py`, `scripts/reset_synthetic_test_data.py` | ✅ |

- **Eksen A:** `BACKEND_ONLY` — CLI script üzerinden kullanılabilir, HTTP yüzeyi yok.
- **Eksen B:** `MISSING` (uygulama içinden), `PARTIAL` (script ile).
- **Kanıt güveni:** yüksek.

### 3.22 ServiceNow, olay müdahalesi, veri koruma envanteri

| Yetenek | domain | migration | service | API | frontend | Eksen A | Eksen B |
|---|---|---|---|---|---|---|---|
| ServiceNow entegrasyonu | ✅ | ❌ | ✅ (`SERVICENOW_TICKET_PRODUCER` rol kontrolü, [service.py:837](../../src/veri_kalitesi/servicenow/service.py#L837)) | ❌ | ❌ | `MODEL_ONLY` | `MISSING` |
| Olay müdahalesi (KVKK ihlal) | ✅ | ❌ | ✅ ([service.py:691](../../src/veri_kalitesi/incident_response/service.py#L691) rol kontrolü) | ❌ | ❌ | `MODEL_ONLY` | `MISSING` |
| Veri işleme envanteri | ✅ | ✅ `data_processing_inventory_versions` (migration 03) | ✅ `InventoryCoverageService` | ❌ | ❌ | `PARTIAL` | `MISSING` |
| Secure SDLC (SAST/SBOM/pentest) | ✅ | ❌ | ✅ (9 dosya, 8 test dosyası) | ❌ | ❌ | `NOT_APPLICABLE` — geliştirme zamanı aracı, çalışma zamanı yeteneği değil | — |
| Ortam güvenliği | ✅ | ❌ | ✅ `EnvironmentConfiguration` | ❌ | ❌ | `MODEL_ONLY` | `MISSING` |
| Kurumsal lab adaptörleri | ✅ | ❌ | ✅ [enterprise_lab/adapters.py](../../src/veri_kalitesi/enterprise_lab/adapters.py), `gate.py` | ❌ | ❌ | `EXTERNAL_DEPENDENCY` | `MISSING` — çalışabilir bileşime bağlı değil |

Kanıt güveni: hepsi yüksek.

### 3.23 Hiç kod karşılığı bulunmayan alanlar

Aşağıdaki alanlar için domain modeli dahil **hiçbir kanıt bulunamadı** —
`MISSING`, kanıt güveni yüksek:

| Alan | Arama |
|---|---|
| İstisna / waiver / override yönetimi | `Exception`, `Waiver`, `Override` sınıfı yok |
| Data contract ve kalite taahhüdü | `DataContract` yok |
| Remediation aksiyonu | `RemediationAction` yok |
| Kullanıcı/rol yönetimi (CRUD) | `users`/`roles` tablosu ve endpoint yok |
| Sistem konfigürasyonu yönetimi | `system_config` yok |
| SLA ve eskalasyon | Issue'da SLA kolonu/servisi yok |
| Kritiklik/risk skorlaması (ayrı) | `RuleCriticality` enum'u dışında model yok |
| Operasyon/incident ekranı | Route ve endpoint yok |
| Teşhis / öneri (recommendation) | `lineage/impact.py` dışında yok |

---

## 4. Uçtan uca akış durumu

Denetim prompt'u §6'daki sekiz akış, çalıştırılabilir uygulama üzerinden izlendi.

### A. Yeni kaynak onboarding
`Kaynak oluştur ✅ → secret referansı ✅(kolon) → bağlantı testi ✅ → onay ✅(tablo+API) → metadata keşfi ❌ → dataset/kolon oluşumu ❌ → sahiplik/sınıflandırma ⚠️ → ilk profil ❌ → baseline ❌`

- **İlk kırılma:** metadata keşfi. Keşfi tetikleyen endpoint yok (§3.3); dolayısıyla dataset/kolon hiçbir zaman otomatik oluşmaz, profil için hedef yoktur.
- **Runtime ek kırılma:** oluşturulan kaynak `DevelopmentDataSourceStore`'a (bellek içi) yazılır, yeniden başlatmada kaybolur.
- Durum: `PARTIAL` / runtime `MOCK_ONLY`.

### B. Kural yaşam döngüsü
`Dataset seçimi ⚠️ → kural oluşturma ✅ → validasyon ✅ → test ✅ → örnek hata ✅ → sürüm ✅ → onay ✅ → aktivasyon ✅ → zamanlama ❌ → çalıştırma ⚠️ → sonuç ⚠️ → skor ⚠️`

- **İlk kırılma:** dataset seçimi — katalog UI'ı olmadığı için dataset id'leri elle girilir.
- **İkinci kırılma:** zamanlama. `schedules` tablosu var, tetikleyen daemon yok (§3.9).
- Kod ekseninde kural yaşam döngüsü repository'deki **en eksiksiz akıştır**; runtime ekseninde bellek içi store üzerinde yürür.
- Durum: `PARTIAL` / runtime `MOCK_ONLY`.

### C. Kalite problemi
`Kural başarısızlığı ⚠️ → sonuç ✅ → skor ⚠️ → bildirim ❌ → duplicate önlemeli issue ❌ → atama ✅ → SLA ❌ → inceleme ✅ → kök neden ✅ → çözüm ✅ → farklı aktörle doğrulama ✅ → kapatma ✅ → tekrarında yeniden açma ✅`

- **İlk kırılma:** bildirim ve otomatik issue üretimi. `NotificationService` çağrılmıyor (§3.19); başarısız çalıştırmadan issue yaratan kod **kanıt bulunamadı** (§3.12).
- Sonuç: akışın ikinci yarısı (atama→kapatma) eksiksiz çalışır ama **birinci yarısı ona hiç bağlanmaz**. Issue'lar yalnız seed veriden veya elle gelir.
- `deduplication_key_digest` ve `occurrence_count` kolonları tabloda mevcut, ancak bunları dolduran otomatik yol yok.
- SLA için model/kolon **kanıt bulunamadı**.
- Durum: `PARTIAL` / runtime `MOCK_ONLY`.

### D. Teknik hata
`Bağlantı/timeout ✅ → kalite hatasından ayrım ✅ (IssueSourceEventType.TECHNICAL, ExecutionStatus.TECHNICAL_ERROR) → retry ✅ (RetryPolicy, execution_attempts) → kota ✅ (source_usage_policies) → worker recovery ✅ (lease/heartbeat) → dead-letter ✅ (dead_letter_records) → operatör inceleme ❌ → replay ❌ → audit ✅ → bildirim ❌`

- **İlk kırılma:** operatör inceleme. Job/dead-letter için API ve UI yok (§3.10).
- **Runtime kırılma daha erken:** worker süreci hiç başlatılmadığı için retry/lease/dead-letter mantığı **çalışma zamanında hiç yürümez**. `create_persistent_job_runtime()` çağrılmıyor.
- Durum: kod `BACKEND_ONLY` / runtime `BROKEN`.

### E. Schema drift
`Metadata yenileme ❌ → fark ⚠️ → sınıflandırma ✅ (7 drift ailesi) → etkilenen kurallar/raporlar ❌ → gerekirse blokaj ❌ → bildirim ❌ → kabul/düzeltme/exception ❌`

- **İlk kırılma:** metadata yenileme yok (§3.3). Mevcut `profile_comparisons` **veri dağılımı** driftini karşılaştırır; **şema değişikliği** tespiti ayrı bir yetenek olarak kanıt bulunamadı.
- Exception/waiver mekanizması hiç yok (§3.23).
- Durum: `PARTIAL` / runtime `PARTIAL` (yalnız mevcut snapshot'lar üzerinden drift hükmü).

### F. Skor güvenilirliği
`Kısmi/örneklemeli çalışma ✅ → coverage ✅ (population/eligible/evaluated/passed/failed/excluded sayaçları) → teknik sağlık ✅ → measurement qualification ✅ (measurement_status, eligible_for_official_scoring) → ham skor ⚠️ → kritiklik/risk ⚠️ → açıklanabilirlik ✅ (score_contribution_graphs)`

- Bu, **kod ekseninde en olgun akıştır**: `rule_execution_results` tablosu ölçüm yeterliliği için gereken bütün sayaçları taşıyor.
- **İlk kırılma:** ham skor kalıcılığı — `quality_scores` tablosu yok, skor bellek içi hesaplanıp SQLite'a yazılıyor (§3.11).
- Durum: `PARTIAL` / runtime `PARTIAL`.

### G. İstisna ve override
`Talep ❌ → gerekçe/bitiş ❌ → maker-checker ❌ → ham sonucu değiştirmeme ❌ → görünür etki ❌ → otomatik sona erme ❌ → audit ❌`

- Durum: `MISSING`, kanıt güveni yüksek. Hiçbir halkada kod yok.

### H. Raporlama
`Rapor seçimi ✅ → filtre ✅ → yetki ✅ → asenkron üretim ⚠️ → maskeleme ✅ (ReportExportPolicy fail-closed) → format ✅ (PDF/XLSX/CSV) → durum ✅ → güvenli indirme ✅ → audit ✅ → dosya imhası ⚠️ → metadata saklama ✅`

- **İlk kırılma:** asenkron üretim. `REPORT` job tipi ve `ReportJobHandler` var, ama dev bileşimi `inline_processing=True` ile kuyruğu atlar; worker da zaten çalışmaz.
- **İkinci kırılma:** üretilen rapor içeriği `_DevDataProvider`'ın **sabit 4 satırı**dır; gerçek skor/sonuç okunmaz.
- Dosya imhası `expires_at` kolonu ile modellenmiş; imhayı yürüten job **kanıt bulunamadı**.
- Durum: `PARTIAL` / runtime `PARTIAL`.

---

## 5. İzlenebilirlik matrisi

| Fonksiyon | Aktör | UI | UI işlemi | API | Servis | Domain | Tablo | Audit | Test | Eksen A | Eksen B |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Dashboard özeti | Viewer/Steward | `/` | görüntüle, filtrele | `GET /dashboard/summary` | `DashboardQueryService` | `DashboardOverview` | `score_contribution_graphs` | ❌ | U+E2E | `PARTIAL` | `PARTIAL` |
| Kaynak listeleme | Steward | `/data-sources` | listele | `GET /data-sources` | `DataSourceQueryService` | `DataSource` | `data_sources` | ❌ | U+E2E | `IMPLEMENTED` | `MOCK_ONLY` |
| Kaynak oluşturma | Steward | `/data-sources` | form | `POST /data-sources` | mutation svc | `DataSource` | `data_sources` | ⚠️ | U | `IMPLEMENTED` | `MOCK_ONLY` |
| Bağlantı testi | Steward | `/data-sources` | buton | `POST /{id}/test` | mutation svc | `ConnectionTestResult` | `connection_test_results` | ⚠️ | U | `IMPLEMENTED` | `MOCK_ONLY` |
| Kaynak aktivasyon | Owner/Checker | `/data-sources` | buton | `POST /{id}/activation` | mutation svc | `DataSource` | `data_source_activation_requests` | ⚠️ | U | `IMPLEMENTED` | `MOCK_ONLY` |
| Metadata keşfi | Steward | ❌ | — | ❌ | `DataSourceService.discover_metadata` + `_diff_metadata` | `MetadataDiscoveryResult` | `metadata_discovery_results` | ⚠️ | U+I | `BACKEND_ONLY` | `MISSING` |
| Dataset/kolon gezinme | Steward | ❌ | — | ❌ | query svc | `Dataset`,`DataField` | `datasets`,`data_fields` | ❌ | ⚠️ | `BACKEND_ONLY` | `MISSING` |
| Profil snapshot görüntüleme | Steward | `/profiling` | listele/detay | `GET /profile-snapshots*` | `ProfileSnapshotQueryService` | `DataProfile` | `data_profiles` | ❌ | U | `IMPLEMENTED` | `PARTIAL` |
| Profil karşılaştırma başlatma | Steward | ❌ | — | `POST /profile-comparisons` | `ProfileComparisonService` | `ProfileComparison` | `profile_comparisons` | ❌ | U | `API_ONLY` | `MISSING` |
| Drift hükmü | Steward | `/profiling` | görüntüle | `GET /{id}/drift` | profiling | — | `profile_comparisons` | ❌ | U | `IMPLEMENTED` | `PARTIAL` |
| Kural oluşturma | Rule Author | `/rules` | form | `POST /rules` | `RuleCreatorService` | `QualityRule` | `quality_rules` | ✅ | U+E2E | `IMPLEMENTED` | `MOCK_ONLY` |
| Kural sürümü | Rule Author | `/rules` | form | `POST /{id}/versions` | `RuleMutationService` | `RuleVersion` | `rule_versions` | ✅ | U+I | `IMPLEMENTED` | `MOCK_ONLY` |
| Kural testi | Rule Author | `/rules` | buton | `POST /{id}/test` | `RuleMutationService` | `RuleTestResult` | `rule_test_results` | ✅ | U | `IMPLEMENTED` | `MOCK_ONLY` |
| Onay talebi | Maker | `/rules` | buton | `POST /{id}/approval` | `RuleMutationService` | `RuleApprovalRequest` | `rule_approval_requests` | ✅ | U+I | `IMPLEMENTED` | `MOCK_ONLY` |
| Onay kararı | Checker | `/rules` | buton | `POST /approval/{id}/decide` | `RuleMutationService` | `RuleApprovalRequest` | `rule_approval_requests` | ✅ | U+I | `IMPLEMENTED` | `MOCK_ONLY` |
| Kural aktivasyon | Steward | `/rules` | buton | `POST /{id}/activation` | `RuleMutationService` | `QualityRule` | `quality_rules` | ✅ | U+E2E | `IMPLEMENTED` | `MOCK_ONLY` |
| Çalıştırma listeleme | Ops/Steward | `/executions` | listele/ara | `GET /executions` | `ExecutionQueryService` | `RuleExecution` | `rule_executions` | ❌ | U+E2E | `IMPLEMENTED` | `BROKEN` |
| Manuel çalıştırma başlatma | Ops | ❌ | — | `POST /executions` | `PostgreSQLExecutionStartService` | `RuleExecution` | `rule_executions`,`persistent_jobs` | ✅ | U+I | `API_ONLY` | `BROKEN` |
| Çalıştırma iptali | Ops | ❌ | — | `POST /{id}/cancel` | `PostgreSQLExecutionCancelService` | `RuleExecution` | `rule_executions` | ✅ | U | `API_ONLY` | `BROKEN` |
| Zamanlanmış çalıştırma | Sistem | ❌ | — | ❌ | `SchedulingService` var, daemon yok | `Schedule` | `schedules` | ⚠️ | U | `BACKEND_ONLY` | `MISSING` |
| Job işleme | Sistem | ❌ | — | ❌ | `PersistentJobWorker` | `BackgroundJob` | `persistent_jobs` | ✅ | U+I | `BACKEND_ONLY` | `BROKEN` |
| Dead-letter replay | Ops | ❌ | — | ❌ | `DeadLetterReprocessService` | `DeadLetterRecord` | `dead_letter_records` | ✅ | U | `BACKEND_ONLY` | `MISSING` |
| Skor görüntüleme | Yönetici/Mühendis | `/` (panel) | görüntüle | ❌ ayrı endpoint | `ScoringService` | `QualityScore` | ❌ (`quality_scores` yok) | ⚠️ | U+I | `PARTIAL` | `PARTIAL` |
| Katkı grafiği | Mühendis | `/` (panel) | görüntüle | `GET /dashboard/summary` içinde | `ContributionService` | — | `score_contribution_graphs` | ⚠️ | U+I | `IMPLEMENTED` | `PARTIAL` |
| Issue listeleme | Assignee | `/issues` | listele | `GET /issues` | `IssueQueryService` | `DataQualityIssue` | `data_quality_issues` | ✅ | U+I+E2E | `IMPLEMENTED` | `MOCK_ONLY` |
| Issue otomatik oluşumu | Sistem | — | — | ❌ | ❌ çağrı yok | `DataQualityIssue` | `data_quality_issues` | — | ❌ | `MISSING` | `MISSING` |
| İnceleme başlatma | Assignee | `/issues` | buton | `POST /{id}/investigation` | issue svc | `IssueStatus` | `issue_history` | ✅ | U+I | `IMPLEMENTED` | `MOCK_ONLY` |
| Yeniden atama | Steward | `/issues` | dialog | `POST /{id}/assignment` | issue svc | — | `issue_history` | ✅ | U+I | `IMPLEMENTED` | `MOCK_ONLY` |
| Çözüm kaydı | Assignee | `/issues` | form | `POST /{id}/resolution` | issue svc | `IssueResolutionDraft` | `issue_resolutions` | ✅ | U+I | `IMPLEMENTED` | `MOCK_ONLY` |
| Doğrulama | Verifier (farklı aktör) | `/issues` | buton | `POST /{id}/verification` | issue svc | `IssueVerificationRecord` | `issue_verifications` | ✅ | U+I | `IMPLEMENTED` | `MOCK_ONLY` |
| Kapatma | Verifier | `/issues` | buton | `POST /{id}/closure` | issue svc | — | `issue_history` | ✅ | U+I | `IMPLEMENTED` | `MOCK_ONLY` |
| İnceleme kanıtı | Assignee | `/investigation` | görüntüle | `GET /{id}/investigation/evidence` | evidence svc | `InvestigationEvidence` | (türetilmiş) | ❌ | U | `IMPLEMENTED` | `PARTIAL` |
| Lineage snapshot | Assignee | `/investigation` | görüntüle | `GET /lineage/snapshots/{id}` | lineage repo | `LineageEvent` | `lineage_evidence_snapshots` | ❌ | U+I | `IMPLEMENTED` | `PARTIAL` |
| Yönetişim projeksiyonu | Assignee | `/investigation` | görüntüle | `GET /governance/{ref}/projection` | `GovernanceProfileReader` | `DataAssetGovernanceProfile` | `lineage_evidence_snapshots` | ❌ | U+I | `IMPLEMENTED` | `PARTIAL` |
| Rapor talebi | Report Consumer | `/reports` | form | `POST /reports/` | `ReportService` | `Report` | `reports` | ✅ | U+I+E2E | `IMPLEMENTED` | `PARTIAL` |
| Rapor indirme | Report Consumer | `/reports` | buton | `GET /{id}/download` | `ReportService` | `Report` | `reports` | ✅ | U+E2E | `IMPLEMENTED` | `PARTIAL` |
| Rapor zamanlaması | Report Consumer | `/reports` (bağlanmamış) | — | `GET/POST/DELETE /report-schedules` | `ReportScheduleService` | `ReportSchedule` | `report_schedules` | ✅ | FE-U | `PARTIAL` | `BROKEN` |
| Audit sorgulama | Auditor | `/audit` | filtrele/sayfala | `GET /audit/events` | `AuditQueryService` | `AuditEvent` | `audit_outbox` | ✅ | U+E2E | `IMPLEMENTED` | `MOCK_ONLY` |
| Oturum kapatma | Tüm | (shell) | buton | `POST /session/logout` | `BffSessionBoundary` | — | ❌ | ✅ | U | `PARTIAL` | `MISSING` |
| Dev kullanıcı seçimi | Geliştirici | login | seç | `GET /development/users` | dev registry | — | ❌ | ❌ | U | `IMPLEMENTED` | `IMPLEMENTED` |
| Bildirim | Tüm | ❌ | — | ❌ | çağrılmıyor | `Notification` | ❌ | ❌ | U | `MODEL_ONLY` | `MISSING` |
| Saklama/imha | Auditor | ❌ | — | ❌ | `RetentionService` | `RetentionPolicy` | ❌ | ⚠️ | U | `MODEL_ONLY` | `MISSING` |
| Sentetik veri üretimi | Geliştirici | ❌ | — | ❌ | `SyntheticDataService` | `SyntheticGenerationRun` | ❌ | ⚠️ | U+I | `BACKEND_ONLY` | `MISSING` |

> `U`=birim, `I`=entegrasyon (skip-gated), `E2E`=Playwright, `FE-U`=frontend Vitest.

### 5.1 Prompt §7'deki kopukluk tipleri — tespit edilenler

| Kopukluk tipi | Repository'de karşılığı |
|---|---|
| ekran var, API yok | **kanıt bulunamadı** |
| API var, servis yok | **kanıt bulunamadı** |
| servis var, repository yok | Bildirim, saklama, ServiceNow, olay müdahalesi, sentetik veri (§3.19–3.22) |
| repository var, migration yok | Bildirim, saklama, ServiceNow, olay müdahalesi, sentetik veri |
| **migration var, production composition root bağlantısı yok** | **Issue, kural, veri kaynağı, katkı grafiği (§2.3)** — en yaygın kopukluk |
| domain varlığı var, kullanılmıyor | `LineageEvent`, `ColumnLineageEdge`, `SecurityIncident`, `SyntheticGroundTruth` |
| audit olayı var, outbox/transaction bağlantısı yok | Scoring, sentetik veri, saklama — `SQLiteTransactionalAudit` kullanıyor |
| test var, production adapter test edilmiyor | 11 PostgreSQL entegrasyon testinin tamamı `skipif` ile kapalı (§9.2) |
| durum geçişi var, yetki kontrolü yok | Dev bileşiminde issue/kaynak mutasyonları — `DevelopmentIssueStore`/`DevelopmentDataSourceStore` yalnız rol dizesi kontrol ediyor ([development.py:767,798,823](../../src/veri_kalitesi/api/development.py#L767)) |
| **backend var, kullanıcı akışı yok** | Metadata keşfi, zamanlama, job/dead-letter, skor detayı, bildirim, saklama, sentetik veri |
| **sonuç var, skor/dashboard/issue bağlantısı yok** | `rule_execution_results` → issue otomatik oluşumu yok; rapor `_DevDataProvider` sabit veri kullanıyor |

---

## 6. API yüzeyi

44 endpoint doğrulandı. Aşağıda frontend kullanımı ve dev bileşimindeki
implementasyon eşlemesi verilmiştir.

### 6.1 Frontend'den çağrılan endpoint'ler (31)

Dashboard (1), veri kaynakları (5), profilleme (3), kurallar (9), çalıştırma
listeleme (1), issue (7), lineage/governance (2), rapor (4: summary/create/list/download),
audit (1), oturum kapatma ve dev kullanıcıları (2 — shell/login içinde).

### 6.2 Frontend'den hiç çağrılmayan endpoint'ler (13)

| Endpoint | Durum | Not |
|---|---|---|
| `POST /api/v1/profile-comparisons` | `API_ONLY` | İstemci fonksiyonu yok |
| `POST /api/v1/executions` | `API_ONLY` | `executions/api.ts` yalnız `fetchExecutions` içeriyor |
| `POST /api/v1/executions/{id}/cancel` | `API_ONLY` | Aynı |
| `GET /api/v1/report-schedules` | `API_ONLY`* | İstemci **var**, route bağlamamış |
| `POST /api/v1/report-schedules` | `API_ONLY`* | Aynı |
| `DELETE /api/v1/report-schedules/{id}` | `API_ONLY`* | Aynı |
| `POST /api/v1/report-schedules/trigger-due` | `API_ONLY` | İstemci fonksiyonu yok, daemon da yok |
| `GET /api/v1/reports/{id}` | `API_ONLY` | `getReport()` tanımlı ama `ReportsRoute` kullanmıyor |

\* İstemci fonksiyonu ve `ReportsPage` props'ları mevcut; eksik olan tek halka
`ReportsRoute` içindeki bağlantıdır (§3.15).

### 6.3 Ortak sözleşme özellikleri

| Özellik | Durum |
|---|---|
| Actor çözümleme | Her endpoint'te tek tek `resolver.resolve(request)`; merkezi dependency yerine satır içi çağrı ([app.py:933 vd.](../../src/veri_kalitesi/api/app.py#L933)) |
| CSRF | Durum değiştiren isteklerde; `CSRF_HEADER_NAME` CORS allow/expose listesinde ([app.py:429-430](../../src/veri_kalitesi/api/app.py#L429-L430)) |
| Correlation ID | Middleware; yanıt başlığı `X-Correlation-ID` |
| Hata eşlemesi | 30+ exception handler; RFC7807 benzeri `_problem()` ([app.py:2439](../../src/veri_kalitesi/api/app.py#L2439)) |
| Fail-closed | Servis `None` ise `UnavailableActorContextResolver` ve 26+ opsiyonel bağımlılık kapalı davranır |
| Idempotency | Yalnız execution: `rule_executions.idempotency_key_hash` UNIQUE |
| Pagination | Audit (cursor), reports (limit/offset), executions/issues (limit); data-sources ve rules'ta **yok** |
| Filtreleme | Audit ve dashboard'da var; data-sources, rules, executions, issues'ta **yok** |
| Sıralama | Hiçbir endpoint'te istemci kontrollü sıralama **kanıt bulunamadı** |
| API sürümleme | Tüm yollar `/api/v1/`; sürüm müzakeresi veya deprecation mekanizması **kanıt bulunamadı** |

---

## 7. Kalıcılık gerçeği

### 7.1 Migration zinciri

14 migration, `20260723_01` → `20260730_14` doğrusal zincir. Şema adı
`alembic.ini` ile yapılandırılıyor (`dq`); `run_dev.py` ise `data_quality`
şemasını kullanıyor.

### 7.2 Tablosu olmayan domain modelleri

| Domain grubu | Modül | Tablo |
|---|---|---|
| `Notification`, `NotificationEvent` | `notifications/` | ❌ |
| `RetentionPolicy`, `LegalHold`, `DisposalJob`, `ArchiveRecallDecision` | `retention/` | ❌ |
| `LineageEvent`, `ColumnLineageEdge` | `lineage/events.py` | ❌ (yalnız snapshot tablosu) |
| `ServiceNowTicketCommand`, `ServiceNowRetryJob` | `servicenow/` | ❌ |
| `SyntheticGenerationRun`, `SyntheticGroundTruth` | `synthetic_data/` | ❌ |
| `SecurityIncident`, `PersonalDataBreachSuspicion` | `incident_response/` | ❌ |
| `QualityScore` | `scoring/` | ❌ (yalnız `score_contribution_graphs`) |
| Kullanıcı, rol, izin, oturum | `identity/` | ❌ |
| Secure SDLC modelleri | `secure_sdlc/` | ❌ (geliştirme zamanı — `NOT_APPLICABLE`) |

### 7.3 SQLite kalıntısı

README ve `Mevcut-Durum.md` "PostgreSQL-only" yönünü kanonik ilan ediyor. Kod
kanıtı:

```
grep -rl "SQLite\|sqlite" --include=*.py src/veri_kalitesi/ | wc -l  → 59 dosya
grep -rn "SQLite" --include=*.py src/veri_kalitesi/ | wc -l          → 205 satır
```

PostgreSQL'e taşınmış modüller: `issues`, `rules`, `data_sources`, `executions`,
`jobs`, `reporting` (kısmi), `lineage`, `scoring` (yalnız katkı grafiği),
`synthetic_data` (yalnız dataset).

Hâlâ SQLite birincil olan modüller: `scoring` (skorun kendisi), `notifications`,
`retention`, `servicenow`, `incident_response`, `identity/sessions`,
`identity/throttling`, `audit` (sorgu tarafı).

### 7.4 Veri bütünlüğü kontrolleri (mevcut olanlar)

Migration'larda tespit edilen koruma mekanizmaları — bunlar repository'nin güçlü
yanıdır:

- Optimistic locking: `data_quality_issues.version`, `reports.version`, `persistent_jobs.version`, `data_sources.revision`
- Kısmi UNIQUE: `rule_approval_requests` `WHERE status='PENDING'` — aynı sürüm için ikinci bekleyen onay engelleniyor
- Idempotency: `rule_executions.idempotency_key_hash` UNIQUE
- CHECK constraint'ler: durum enum'ları tabloda da zorunlu (issue 8 durum, execution 8 durum, rule 5 durum, kaynak 6 durum)
- İçerik doğrulaması: `issue_resolutions` `root_cause`/`corrective_action` için uzunluk ve no-HTML CHECK'i
- Audit hash zinciri: `previous_event_hash` / `event_hash`
- Immutable geçmiş: `issue_history`, `issue_resolutions`, `issue_verifications` Identity PK ile append-only

---

## 8. Yetki ve audit gerçeği

### 8.1 Yetkilendirme modeli

Mevcut model **scope tabanlı**dır, RBAC izin kaydı değildir:

```python
ActorContext(actor_id, roles, permitted_source_ids,
             permitted_dataset_ids, can_view_enterprise, privileged)
```
([identity/models.py:20-28](../../src/veri_kalitesi/identity/models.py#L20-L28))

- Kaynak/dataset erişimi `permitted_*_ids` kümeleriyle filtrelenir; `can_view_enterprise` kurumsal toplamı açar.
- Rol kontrolleri **dağınık string karşılaştırmalarıdır**, merkezi bir izin kaydı yoktur. Örnekler: `{"DATA_STEWARD","DATA_GOVERNANCE_SPECIALIST"}` ([development.py:767](../../src/veri_kalitesi/api/development.py#L767)), `"SERVICENOW_TICKET_PRODUCER"` ([servicenow/service.py:837](../../src/veri_kalitesi/servicenow/service.py#L837)), `"DATA_ENGINEER"` ([dashboard/service.py:260](../../src/veri_kalitesi/dashboard/service.py#L260)), `policy.required_role` ([audit/service.py:342](../../src/veri_kalitesi/audit/service.py#L342)).
- Denetim prompt'u §12'deki 15 rolün hiçbiri veri tabanında tanımlı değildir; roller `ActorContext` içinde serbest dize kümesidir.
- Maker-checker yalnız iki yerde veri tabanı seviyesinde korunur: `rule_approval_requests` ve `data_source_activation_requests` (`maker_actor_id` / `checker_actor_id`). Issue doğrulaması "farklı aktör" kuralını servis seviyesinde uygular.

### 8.2 Audit mimarisi

- API katmanında **hiç audit çağrısı yok** — `grep 'transactional_audit\|record_event' app.py` → 0 eşleşme. Bu bilinçli bir katman kararıdır: audit servis içinde, iş transaction'ıyla aynı session'da `stage()` edilir, sonra `publish_pending()` ile outbox'tan yayımlanır.
- PostgreSQL outbox'a bağlı modüller: `issues` (6 akış), `rules`, `executions`, `jobs`.
- Hâlâ `SQLiteTransactionalAudit` kullanan modüller: `scoring/partial_score_policies.py`, `scoring/repository.py`, `synthetic_data/oracle.py`, `retention/*`, `executions/scheduling.py`.
- Audit erişiminin kendisi audit'lenir (`_record_view`, `_record_denial`).
- **Çalışabilir uygulamada:** `run_dev.py` prepared-event deposu olarak `_FakePreparedRepo` verir — `store()` metodu `pass`. Dolayısıyla yayımlanan olaylar hiçbir kalıcı depoya gitmez; `AuditPage`'de görünen olaylar `create_development_app()` içinde üretilen sentetik kayıtlardır.

---

## 9. Test kapsamı gerçeği

### 9.1 Sayılar

57 birim + 11 entegrasyon + 7 E2E spec. Frontend tarafında modül başına
`api.test.ts` / `model.test.ts` / komponent testi mevcut.

### 9.2 Entegrasyon testlerinin tamamı koşul altında

11 PostgreSQL entegrasyon dosyasının **hepsinde** aynı desen var:

```python
POSTGRES_TEST_URL = os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="DATA_QUALITY_POSTGRES_TEST_URL is required for PostgreSQL integration.",
)
```

`conftest.py` proje kökündeki `.env` dosyasını yükler; bu dosya `.gitignore`
altındadır ve **bu worktree'de mevcut değildir** (`ls -a | grep -i env` → boş).

Sonuç: varsayılan bir `pytest` koşusunda PostgreSQL entegrasyon testlerinin
tamamı **atlanır**. `Mevcut-Durum.md`'deki "1125 passed, 27 skipped" baseline'ı bu
skip davranışıyla tutarlıdır.

### 9.3 Yalnız test içinde yaşayan yetenekler

`PostgreSQLIssueRepository`, `PostgreSQLRuleRepository`,
`PostgreSQLDataSourceRepository`, `PostgreSQLContributionGraphRepository` ve
`BffSessionBoundary` yalnız test dosyalarında örneklenir (§2.3). Bu bileşenlerin
davranışı **yalnız skip-gated entegrasyon testleri koşulduğunda** doğrulanır.

### 9.4 Test kanıtı bulunamayan alanlar

Zamanlama (`schedules`), rapor zamanlaması (backend), veri koruma envanteri,
metadata keşfi HTTP yüzeyi, profilleme entegrasyonu ve E2E'si, job/dead-letter
E2E'si.

### 9.5 E2E kapsamı

`playwright.config.ts` `webServer: npm run dev` ile yalnız **frontend** dev
sunucusunu ayağa kaldırır ([playwright.config.ts:16-20](../../frontend/playwright.config.ts#L16-L20)). Backend'in nasıl sağlandığı
konfigürasyonda yer almıyor; spec'lerin gerçek API'ye mi yoksa fixture/mock'a mı
bağlandığı bu okuma ile kesinleştirilemedi (bkz. Q-06).

---

## 10. Dokümantasyon–kod tutarsızlıkları

Bu bölüm yargı değil, karşılaştırmadır.

### 10.1 Kırık doküman bağlantıları

| Beyan | Gerçek |
|---|---|
Repository'nin **kendi** doküman kontrolü (`python3 scripts/check_documentation.py`)
bu oturumda çalıştırıldı. Bu denetimden **bağımsız olarak var olan** hatalar:

```
ERROR: missing required document: DOCUMENTATION_INDEX.md
ERROR: missing required document: DOCUMENTATION_AUDIT.md
ERROR: README.md: broken link -> DOCUMENTATION_INDEX.md          (2 kez)
ERROR: README.md: broken link -> DOCUMENTATION_AUDIT.md
ERROR: README.md: broken link -> NEXT_STEP.md                    (2 kez)
ERROR: docs/memory/Bankacilik-Gecis-Durumu.md   -> ../NEXT_STEP.md
ERROR: docs/testing/TEST-INDEX.md                        -> ../NEXT_STEP.md
ERROR: docs/iterations/              -> ../NEXT_STEP.md
ERROR: docs/iterations/Iterasyon-36-*.md                -> ../NEXT_STEP.md
ERROR: docs/iterations/Kalan-Iterasyonlar-*.md          -> ../NEXT_STEP.md
ERROR: docs/testing/AGENTS.md                            -> ../AGENTS.md
ERROR: docs/backend/01-Kimlik-ve-Yetki/AGENTS.md         -> ../../AGENTS.md
ERROR: docs/architecture/Ajan-Orkestrasyon-Mimarisi.md         -> ../.agent/config/agents.yaml
ERROR: docs/architecture/Ajan-Orkestrasyon-Mimarisi.md         -> ../.qoder/rules/
```

Özet: `DOCUMENTATION_INDEX.md`, `DOCUMENTATION_AUDIT.md`, `NEXT_STEP.md` ve kök
`AGENTS.md` **yoktur**; bunlara toplam **12 kırık bağlantı** işaret eder.
`NEXT_STEP.md`, denetim prompt'u §2'nin ve README "Başlangıç" bölümünün
"son tamamlanan çalışma paketi" kanonik kaynağı olarak gösterdiği dosyadır.

> Not: bu hatalar bu denetimden önce de mevcuttu; bu bölümde yeni tespit
> edilmemiş, yalnız kayda geçirilmiştir.

### 10.2 Envanter ile kod kanıtı arasındaki farklar

| Envanter beyanı | Kod kanıtı |
|---|---|
| `07-Matrix`: Lineage `BE_ONLY` — "API var, UI yok" | `InvestigationPage.tsx:377-378` her iki endpoint'i de çağırıyor → UI **var** |
| `03-Frontend`: "Report Schedules — API exists, no page" | İstemci fonksiyonları **var**, `ReportsPage` props'ları **var**; eksik olan `ReportsRoute` bağlantısı |
| `05-Test`: "13 entegrasyon test dosyası" | Ölçülen: **11** (`test_*.py`) |
| `01-Backend`: "176 backend Python dosyası" | Ölçülen: **174** |
| `07-Matrix`: Issue yaşam döngüsü `IMPL` | Kod ekseninde doğru; runtime ekseninde `MOCK_ONLY` — PostgreSQL repository hiçbir çalışabilir bileşimde yok |
| `07-Matrix`: Veri kaynağı onboarding `IMPL` | Aynı düzeltme geçerli |
| `01-Backend`: "Dev entry: `run_dev.py` → PostgreSQL" | Doğru ama eksik: yalnız execution/job/rapor/lineage PostgreSQL'e gider; issue/kural/kaynak/audit/skor bellek içi |

### 10.3 Proje hafızası beyanları ile kod kanıtı

| Beyan | Kaynak | Kod kanıtı |
|---|---|---|
| "Issue domaini PostgreSQL-only yola taşınmış" | `README.md:18` | Repository yazılmış ve test edilmiş; **çalışabilir bileşimde bağlı değil** |
| "36H1 kalıcı kuyruk çekirdeği ve 36H2 iş yürütme yaşam döngüsü `TechnicallyVerified`" | `README.md:22-26` | Kuyruk ve worker kodu tam; **worker süreci hiçbir yerde başlatılmıyor**, `create_persistent_job_runtime()` çağrılmıyor |
| "36G güvenli PDF/XLSX/CSV üretimi 36H2 ile kalıcı `REPORT` kuyruğuna bağlandı; istek-içi worker yalnız açık geliştirme modundadır" | `Mevcut-Durum.md:19` | Doğru; çalıştırılabilir tek yol geliştirme modu olduğu için pratikte **her zaman istek-içi** |
| "Çalıştırma ve rapor ekranları 36E/36G kapanış kanıtlarıyla uyumludur" | `Mevcut-Durum.md:20` | Çalıştırma ekranında başlat/iptal komutu **yok**; rapor ekranında zamanlama bağlanmamış |
| "DQ-CAP-PROTOTYPE-05 … modüller henüz composition'a bağlı değil" | `iterations/:14` | Kod kanıtıyla **doğrulandı** — `notifications/channel_adapters.py` ve `executions/strategy_engine.py` bağlı değil (strategy engine yalnız dev execution start içinde kullanılıyor) |
| "PostgreSQL issue mutasyon testleri (2/2) ve tüm entegrasyon paketi (44/44) gerçek PostgreSQL 16.13 üzerinde doğrulanmıştır" | `Mevcut-Durum.md:16` | Testler `skipif` ile kapalı; bu doğrulamanın `.env` sağlanmış bir ortamda yapıldığı anlaşılıyor, bu worktree'de yeniden üretilemez |

---

## 11. Özet tablo

| # | Yetenek | Eksen A (kod) | Eksen B (runtime) | Güven |
|---|---|---|---|---|
| 1 | Dashboard | `PARTIAL` | `PARTIAL` | yüksek |
| 2 | Veri kaynağı onboarding | `IMPLEMENTED` | `MOCK_ONLY` | yüksek |
| 3 | Metadata keşfi / katalog | `BACKEND_ONLY` | `MISSING` | yüksek |
| 4 | Profilleme ve drift | `PARTIAL` | `PARTIAL` | yüksek |
| 5 | Kural yaşam döngüsü | `IMPLEMENTED` | `MOCK_ONLY` | yüksek |
| 6 | Kural onayı (maker-checker) | `IMPLEMENTED` | `MOCK_ONLY` | yüksek |
| 7 | Kural IR / SHADOW | `PARTIAL` | `MISSING` | orta |
| 8 | Çalıştırma başlat/iptal | `PARTIAL` | `BROKEN` | yüksek |
| 9 | Zamanlama | `BACKEND_ONLY` | `MISSING` | yüksek |
| 10 | Kalıcı iş kuyruğu / dead-letter | `BACKEND_ONLY` | `BROKEN` | yüksek |
| 11 | Skorlama ve katkı grafiği | `PARTIAL` | `PARTIAL` | yüksek |
| 12 | Issue yaşam döngüsü | `IMPLEMENTED` | `MOCK_ONLY` | yüksek |
| 13 | İnceleme kanıtı | `IMPLEMENTED` | `PARTIAL` | yüksek |
| 14 | Raporlama | `IMPLEMENTED` | `PARTIAL` | yüksek |
| 15 | Rapor zamanlaması | `PARTIAL` | `BROKEN` | yüksek |
| 16 | Audit ve outbox | `IMPLEMENTED` | `MOCK_ONLY` | yüksek |
| 17 | Kimlik / oturum / yetki | `PARTIAL` | `MOCK_ONLY` | yüksek |
| 18 | Lineage ve yönetişim | `PARTIAL` | `PARTIAL` | yüksek |
| 19 | Bildirim | `MODEL_ONLY` | `MISSING` | yüksek |
| 20 | Saklama / imha / legal hold | `MODEL_ONLY` | `MISSING` | yüksek |
| 21 | Sentetik veri | `BACKEND_ONLY` | `MISSING` | yüksek |
| 22 | ServiceNow | `MODEL_ONLY` | `MISSING` | yüksek |
| 23 | Olay müdahalesi (KVKK) | `MODEL_ONLY` | `MISSING` | yüksek |
| 24 | Veri işleme envanteri | `PARTIAL` | `MISSING` | yüksek |
| 25 | Ortam güvenliği | `MODEL_ONLY` | `MISSING` | yüksek |
| 26 | Kurumsal lab adaptörleri | `EXTERNAL_DEPENDENCY` | `MISSING` | yüksek |
| 27 | Secure SDLC | `NOT_APPLICABLE` | — | yüksek |
| 28 | İstisna / waiver / override | `MISSING` | `MISSING` | yüksek |
| 29 | Data contract | `MISSING` | `MISSING` | yüksek |
| 30 | Remediation | `MISSING` | `MISSING` | yüksek |
| 31 | Kullanıcı/rol yönetimi | `MISSING` | `MISSING` | yüksek |
| 32 | Sistem konfigürasyonu | `MISSING` | `MISSING` | yüksek |
| 33 | SLA / eskalasyon | `MISSING` | `MISSING` | yüksek |
| 34 | Operasyon ekranı / incident | `MISSING` | `MISSING` | yüksek |

---

## 12. Açık konular

Bu denetim sırasında kalan belirsizlikler ve doğrulama planları ayrı dosyadadır:
[work/01-Unresolved-Evidence-Questions.md](work/01-Unresolved-Evidence-Questions.md)

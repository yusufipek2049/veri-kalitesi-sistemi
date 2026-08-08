---
title: "14 — Bağımsız Kod Doğrulaması"
stage: "14 — Independent Code Verification"
created_at: 2026-08-04
status: independent-verification
scope:
  - 04-Functional-Gap-Inventory.md
  - 08-Existing-Schema-Gap-Analysis.md
  - 09-State-Machines.md
  - 10-Roles-and-Permissions.md
  - 11-Test-Coverage-Gaps.md
---

# 14 — Bağımsız Kod Doğrulaması

## 1. Amaç, kapsam ve yöntem

Bu çalışma mevcut fonksiyonel denetimi desteklemek amacıyla değil, rapordaki
iddiaları repository'nin mevcut çalışma ağacına karşı bağımsız olarak sınamak
amacıyla yapılmıştır. Yeni hedef mimari tasarlanmamış ve kaynak kodda değişiklik
yapılmamıştır.

İnceleme kapsamı:

- öncelikli olarak `04-Functional-Gap-Inventory.md`,
  `08-Existing-Schema-Gap-Analysis.md`, `09-State-Machines.md`,
  `10-Roles-and-Permissions.md` ve `11-Test-Coverage-Gaps.md`;
- domain modelleri, Alembic migration'ları, repository ve servisler;
- çalıştırılabilir kök olan `run_dev.py`, `create_development_app` ve genel API
  fabrikası `create_dashboard_api`;
- FastAPI route'ları, frontend API çağrıları ve sayfa bağları;
- kimlik/yetki/scope, transactional audit ve test kaynakları.

Rapor GAP kayıtlarında doğrudan `P0`/`P1` etiketi tanımlamıyor. Bu nedenle
`11-Test-Coverage-Gaps.md` §10 ve §12'deki öncelikler esas alınarak
`Kritik = P0`, `Yüksek = P1` eşlemesi kullanıldı. Bu, raporun açıkça tanımladığı
bir sınıflandırma değil, bu doğrulamanın operasyonel eşlemesidir. Dolayısıyla
P0/P1 kümesinin kendisi için kanıt durumu `INSUFFICIENT_EVIDENCE`'tır; aşağıdaki
önerilen öncelikler bağımsız değerlendirmedir.

İncelenen P0/P1 kümesi:

- P0: GAP-001, GAP-022
- P1: GAP-002, GAP-003, GAP-004, GAP-006, GAP-008, GAP-009, GAP-014,
  GAP-026

Zincir hücrelerinde `VAR`, `KISMİ`, `YOK`, `BAĞLI DEĞİL` ve `BYPASS` ifadeleri
kullanılmıştır. `VAR`, yalnız kodun bulunmasını değil ilgili katmanın iddia
edilen işlevi taşımasını; `BAĞLI DEĞİL`, kodun production/executable composition
root'tan erişilememesini; `BYPASS`, endpoint'in beklenen servis veya durum
makinesini atlamasını ifade eder.

## 2. Yönetici özeti

| Kayıt | Bağımsız değerlendirme | Doğru durum sınıfı | Önerilen öncelik | Güven |
|---|---|---|---|---|
| GAP-001 | Kalıcı repository'lerin büyük bölümü çalıştırılabilir köke bağlı değil; yürütme yazma yolu PG'ye bağlansa da okuma yolu sentetik | `CONFIRMED` | P0 | Yüksek |
| GAP-022 | Kalıcı üretim IAM/RBAC yok; fakat çok kullanıcılı dev resolver, BFF boundary, LDAP ve backend read-scope kodu raporda eksik/yanlış temsil edilmiş | `CORRECTION_REQUIRED` | P0 | Yüksek |
| GAP-002 | Worker entrypoint/daemon yok; fakat worker, handler ve PG runtime composition mevcut. Hedef state/audit tamamlandı beyanı doğru değil | `CORRECTION_REQUIRED` | P1 | Yüksek |
| GAP-003 | Scheduling yalnız model/sorgu değildir; SQLite ve PG repository ile çalışan servis ve birim testleri vardır. Runtime/API/UI yoktur | `CORRECTION_REQUIRED` | P1 | Yüksek |
| GAP-004 | Metadata discovery, diff, kalıcılık ve profiling orkestrasyonu serviste vardır. Production bağ, API ve UI yoktur | `CORRECTION_REQUIRED` | P1 | Yüksek |
| GAP-006 | Otomatik issue üretim/dedup/recurrence servisi vardır. Execution-result bağlayıcısı ve eligibility kapısı yoktur | `CORRECTION_REQUIRED` | P1 | Yüksek |
| GAP-008 | PG skor/sürüm-yayım deposu yok; yalnız SQLite skor deposu ve PG katkı grafiği vardır | `CONFIRMED` | P1 | Yüksek |
| GAP-009 | İstisna/waiver/suppression/quality-debt yaşam döngüsü gerçekten yoktur; mevcut bağımlılıklar nedeniyle mevcut P1 sırası gerekçelendirilmemiştir | `SEVERITY_CHANGE_REQUIRED` | P2 | Orta |
| GAP-014 | Issue SLA ve escalation yaşam döngüsü gerçekten yoktur; issue üretim ve teslimat hattından önce P1 yapılması bağımlılık sırasıyla uyumsuzdur | `SEVERITY_CHANGE_REQUIRED` | P2 | Orta |
| GAP-026 | Organizasyon/domain/politika yönetim yaşam döngüsü yoktur; lineage kanıt projeksiyonları bu işlevin yerine geçmez | `CONFIRMED` | P1 | Yüksek |

En kritik yeni bulgular şunlardır:

1. Çalışan development API'de veri kaynağı aktivasyonu `DataSourceService` ve
   maker-checker akışını atlayarak `DevelopmentDataSourceStore.activate` ile
   doğrudan `TEST_SUCCEEDED -> ACTIVE` geçişi yapar. Frontend bu endpoint'i
   kullanır ve birim testi bu bypass'ı başarılı davranış olarak sabitler.
2. Read sorgularında scope backend'de uygulanır; buna karşılık data-source,
   rule ve manual execution mutasyonlarında actor role/scope kontrolü ya yoktur
   ya da bağlanan development store tarafından uygulanmaz. Bu nedenle “scope
   yalnız frontend'de” genellemesi yanlış, fakat komut tarafında P0 güvenlik
   boşluğu vardır.
3. `run_dev.py` audit outbox'ı `data_quality` şemasına, PG execution/job
   repository'lerini varsayılan `dq` şemasına yönlendirir. Bu bir soru/risk
   değil, statik olarak doğrulanabilen şema ayrışmasıdır. Ayrıca no-op prepared
   repository `store` sağlarken publisher `append` çağırır; ledger yayımı
   başarısız kalır.
4. Raporun scheduling, metadata discovery/profiling ve issue producer için
   “kod/test yok” alt iddiaları yanlıştır. Bu kodlar vardır ve kapsamlı birim
   testleri bulunmaktadır; asıl eksik production bağlantısı ve kullanıcı
   yüzeyidir.

## 3. P0 doğrulamaları

### 3.1 GAP-001 — Production composition root eksikliği

**Mevcut iddia:** PostgreSQL Issue, Rule, DataSource ve ContributionGraph
repository'leri yazılmış olmasına rağmen production composition root'a bağlı
değildir; uygulama in-memory/sentetik store'larla çalışır ve gerçek audit zinciri
tamamlanmaz.

**Gerçek repository kanıtı:** İddianın çekirdeği doğrudur. Repository sınıfları
tanımlı olmakla birlikte production kodunda örneklenmez. Çalıştırılabilir
`run_dev.py`, `create_development_app` çağırır. Bu composition yalnız execution
ve job queue yazma yollarını PG'ye bağlar; issue, rule ve data source komutları
development store'larda, score ve audit okuma yolları SQLite/sentetik kalır.
Execution komutu PG'ye yazarken `ExecutionQueryService` hâlâ
`DevelopmentExecutionReader` okur; aynı kullanıcı akışında write/read
ayrışması vardır.

| Zincir | Kanıt ve sonuç |
|---|---|
| Domain | `issues/models.py`, `rules/models.py`, `data_sources/models.py`, `executions/models.py`, `scoring/models.py` — `VAR` |
| Migration | `20260723_01_issue_baseline.py`, `_02_rule_baseline.py`, `_03_data_source_baseline.py`, `_04_execution_baseline.py`, `_13_score_contribution_graphs.py` — `VAR/KISMİ` |
| Repository | `PostgreSQLIssueRepository` (`issues/postgresql_repository.py:221`), `PostgreSQLRuleRepository` (`rules/postgresql_repository.py:148`), `PostgreSQLDataSourceRepository` (`data_sources/postgresql_repository.py:347`), `PostgreSQLContributionGraphRepository` (`scoring/postgresql_contributions.py:47`) — `VAR` |
| Production composition root | `run_dev.py:36`, `api/development.py:create_development_app` (`1134`, `1326-1369`) — Issue/Rule/DataSource/Contribution `BAĞLI DEĞİL`; yalnız execution/job write yolu PG |
| Service | Gerçek domain servisleri vardır; executable root bunların yerine `DevelopmentIssueStore`, `DevelopmentRuleStore`, `DevelopmentDataSourceStore` bağlar — `BAĞLI DEĞİL` |
| API | Route'lar vardır; enjekte edilen development store'lara gider. PG execution start sonucu sentetik reader'da görünmez — `KISMİ` |
| Frontend | Data source/rule/issue/dashboard yüzeyleri vardır ve bu API'leri çağırır — `VAR`, fakat production kalıcılığı göstermez |
| Permission/scope | Query servisleri `PolicyAuthorizationService` kararlarını repository filtrelerine taşır; command tarafı tutarlı değildir — `KISMİ/BYPASS` |
| Audit | PG repository'lerde business write + outbox aynı SQLAlchemy transaction'ında stage edilir. Development store'lar audit üretmez; UI audit verisi ayrı sentetik SQLite kaynağıdır — `KISMİ` |
| Test | Repository ve transaction testleri vardır fakat PG testleri environment-gated'dir; composition smoke/E2E yoktur — `KISMİ` |

**Dosya ve semboller:** `run_dev.py:_FakePreparedRepo`,
`api/development.py:create_development_app`,
`api/development.py:DevelopmentExecutionReader`,
`api/development.py:DevelopmentIssueStore`,
`api/development.py:DevelopmentRuleStore`,
`api/development.py:DevelopmentDataSourceStore`, yukarıdaki PG repository
sınıfları.

**Değerlendirme:** Raporun ana boşluk iddiası doğrulanmıştır. Ancak “PG yolu
hiç bağlı değil” şeklinde okunmamalıdır: execution start/cancel ve job queue
PG'ye bağlanmıştır; problem karışık ve kendi içinde tutarsız composition'dır.

- Doğru durum sınıfı: `CONFIRMED`
- Önerilen öncelik: P0
- Güven seviyesi: Yüksek

### 3.2 GAP-022 — Kalıcı kimlik, rol, scope ve oturum yönetimi

**Mevcut iddia:** users/roles/permissions/sessions kalıcılığı ve production BFF
bağlantısı yoktur; dev kimliği sabit rollü header tabanlıdır; rol/scope
modeli fiilen yoktur.

**Gerçek repository kanıtı:** Production IAM/RBAC persistence eksikliği
doğrudur. Alembic migration'larında `users`, `roles`, `permissions`,
`role_assignments`, `assignment_scopes`, `sessions` ve access-review tabloları
yoktur. Bununla birlikte rapor mevcut kodu eksik saymıştır:

- `identity/sessions.py` içinde SQLite tabanlı session repository ve session
  lifecycle kodu;
- `identity/ldap.py` içinde LDAP assertion ve grant-to-scope eşlemesi;
- `api/bff.py:BffSessionBoundary` ve API'de opsiyonel BFF sınırı;
- `api/identity.py:build_default_development_users` içinde sekiz farklı rol/scope
  profili ve `DevelopmentActorContextResolver` içinde
  `X-Development-User-Id` seçimi;
- issue/rule/execution/data-source query servislerinde backend scope filtreleri
  vardır.

Bu bileşenler production root'a bağlanan kalıcı IAM değildir. Header istemci
tarafından seçilebildiği için dev resolver bir güven sınırı sayılamaz.

| Zincir | Kanıt ve sonuç |
|---|---|
| Domain | `identity/models.py`, `identity/sessions.py`, `identity/ldap.py` — user/context/session kavramları `VAR`, hedef rol atama/access review domaini `YOK` |
| Migration | D02 tabloları `YOK` |
| Repository | SQLite session repository `VAR`; PostgreSQL IAM/RBAC repository `YOK` |
| Production composition root | `BffSessionBoundary` testlerde örneklenir; executable root dev resolver kullanır — `BAĞLI DEĞİL` |
| Service | `PolicyAuthorizationService`, LDAP ve session servisleri `VAR`; rol/izin yönetim servisi `YOK` |
| API | BFF hook'ları ve dev-user list/login yüzeyi `KISMİ`; kalıcı user/role/session yönetim API'si `YOK` |
| Frontend | `DevelopmentLoginPage` ve `DevelopmentUserSwitcher` `VAR`; production IAM yönetim akışı `YOK` |
| Permission/scope | Read path backend filtreleri `VAR`; data-source/rule/execution command kontrolleri `KISMİ/BYPASS` |
| Audit | Kalıcı IAM değişimi olmadığı için rol/atama/session yönetim audit zinciri `YOK` |
| Test | `test_identity.py`, `test_bff_session_api.py` ve query scope testleri `VAR`; production PG IAM/E2E `YOK` |

**Dosya ve semboller:** `api/identity.py:build_default_development_users`,
`api/identity.py:DevelopmentActorContextResolver.resolve`,
`api/bff.py:BffSessionBoundary`, `identity/service.py:PolicyAuthorizationService`,
`identity/sessions.py`, `identity/ldap.py`,
`tests/unit/test_bff_session_api.py`.

**Değerlendirme:** GAP geçerlidir, fakat “sabit tek dev rolü” ve “backend scope
yok” alt iddiaları mevcut çalışma ağacıyla uyumlu değildir. Asıl P0 problem
production trust boundary/persistence yokluğu ile command authorization
tutarsızlığıdır.

- Doğru durum sınıfı: `CORRECTION_REQUIRED`
- Önerilen öncelik: P0
- Güven seviyesi: Yüksek

## 4. P1 doğrulamaları

### 4.1 GAP-002 — Kalıcı worker runtime

**Mevcut iddia:** Kalıcı queue/worker kodu tamamdır, ancak worker entrypoint ve
daemon olmadığı için runtime çalışmaz.

**Gerçek repository kanıtı:** `PersistentJobWorker.run_forever`, execution ve
report handler'ları, dead-letter reprocess servisi ve
`create_persistent_job_runtime` vardır. Production/test dışı hiçbir çağıran ve
console script yoktur; bu nedenle runtime eksikliği doğrulanır. Ancak “kod
tamam” iddiası hedef state machine bakımından doğru değildir:

- repository durumları `QUEUED`, `RUNNING`, `CANCEL_REQUESTED`, terminal
  durumları kullanır; raporun hedefindeki `AVAILABLE`, `CLAIMED`, `BLOCKED`,
  `DEAD_LETTERED` birebir uygulanmaz;
- `PostgreSQLJobQueueRepository.claim_next` `FOR UPDATE SKIP LOCKED`, lease ve
  quota uygular, fakat audit event/outbox parametresi almaz. Bu nedenle raporun
  istediği `CLAIMED + JOB_CLAIMED + lease` aynı transaction garantisi mevcut
  değildir;
- terminal/cancel/dead-letter geçişlerinde transactional outbox desteği vardır.

| Zincir | Kanıt ve sonuç |
|---|---|
| Domain | `jobs/models.py:BackgroundJob`, `JobStatus`, dead-letter modelleri — `VAR/KISMİ` |
| Migration | `20260728_08_job_queue.py`, `20260729_09_job_lifecycle.py` — `VAR` |
| Repository | `jobs/postgresql_repository.py:PostgreSQLJobQueueRepository`, `claim_next` — `VAR`, claim-audit `YOK` |
| Production composition root | `jobs/composition.py:create_persistent_job_runtime` tanımlı; production çağıranı yok — `BAĞLI DEĞİL` |
| Service | `PersistentJobWorker`, handlers, lifecycle/reprocess servisleri — `VAR` |
| API | Queue operasyon/dead-letter yönetim yüzeyi `YOK`; execution start yalnız job enqueue eder |
| Frontend | Worker/dead-letter operasyon yüzeyi `YOK` |
| Permission/scope | Reprocess policy kodu vardır; daemon claim'i servis kimliği/trust boundary'siyle bağlı değildir — `KISMİ` |
| Audit | Enqueue ve terminal geçişler `VAR`; claim geçişi `YOK` |
| Test | PG concurrency/lease/dead-letter testleri `VAR` fakat skip-gated; daemon/E2E `YOK` |

**Dosya ve semboller:** `jobs/worker.py:PersistentJobWorker.run_forever`,
`jobs/composition.py:create_persistent_job_runtime`,
`jobs/postgresql_repository.py:claim_next`, `pyproject.toml`,
`tests/integration/test_postgresql_job_queue.py`.

**Değerlendirme:** Runtime bağlantısı eksiktir; backend'in hedefe göre tamam
olduğu ve claim audit atomikliğinin var olduğu kabulü düzeltilmelidir.

- Doğru durum sınıfı: `CORRECTION_REQUIRED`
- Önerilen öncelik: P1
- Güven seviyesi: Yüksek

### 4.2 GAP-003 — Scheduling

**Mevcut iddia:** Scheduling `MODEL_ONLY`/migration+sorgu düzeyindedir; servis,
tetikleme ve test yoktur.

**Gerçek repository kanıtı:** Bu iddia önemli ölçüde yanlıştır.
`executions/scheduling.py` içinde `Schedule`, `SQLiteScheduleRepository` ve
`SchedulingService` bulunur. `create_schedule`, timezone doğrulama/preview,
due schedule tetikleme ve idempotent execution üretimi uygular.
`executions/postgresql_scheduling.py:PostgreSQLScheduleRepository` kalıcı
schedule okuma/yazma ve due sorgusu sağlar. Birim testlerinde aynı due için tek
idempotent execution üretildiği doğrulanır. Eksik olan production scheduler
loop, composition, API, frontend ve çoklu scheduler yarış garantisidir; PG due
sorgusunda claim/lock protokolü yoktur.

| Zincir | Kanıt ve sonuç |
|---|---|
| Domain | `executions/scheduling.py:Schedule`, `ScheduleType` — `VAR` |
| Migration | `20260724_05_scheduling_and_policy_baseline.py:schedules` — `VAR` |
| Repository | `SQLiteScheduleRepository`, `PostgreSQLScheduleRepository` — `VAR` |
| Production composition root | Scheduler örneği/loop çağıranı `YOK` |
| Service | `SchedulingService.create_schedule`, `trigger_due` — `VAR` |
| API | Schedule CRUD/preview/trigger endpoint'i `YOK` |
| Frontend | Schedule kullanıcı akışı `YOK` |
| Permission/scope | Servis yalnız `actor_id` alır; trusted ActorContext/role/scope enforcement `YOK` |
| Audit | Schedule creation audit'i vardır; due advancement/execution üretimi için hedef kapsamda tam audit zinciri `KISMİ` |
| Test | `test_executions.py` satır 646-951 civarında scheduling testleri `VAR`; PG concurrency/E2E `YOK` |

**Dosya ve semboller:** `executions/scheduling.py:SchedulingService`,
`executions/postgresql_scheduling.py:PostgreSQLScheduleRepository`,
`tests/unit/test_executions.py:test_fr_037_uc_007_due_schedule_creates_one_idempotent_scheduled_execution`.

**Değerlendirme:** Kullanılabilir sistem kabiliyeti hâlâ eksiktir; ancak servis
ve testlerin yok olduğu alt iddiası yanlış pozitiftir. GAP “scheduler runtime ve
yüzey yokluğu” olarak yeniden yazılmalıdır.

- Doğru durum sınıfı: `CORRECTION_REQUIRED`
- Önerilen öncelik: P1
- Güven seviyesi: Yüksek

### 4.3 GAP-004 — Metadata discovery ve katalog

**Mevcut iddia:** Yalnız connector seviyesinde discovery vardır; orkestrasyon,
metadata diff, uygulama, API/UI ve test yoktur.

**Gerçek repository kanıtı:** `DataSourceService.discover_metadata` connection
durumunu kontrol eder, secret/connector kullanır, hataları sınıflandırır,
metadata'yı normalize eder, kimlikleri korur, `_diff_metadata` ile fark üretir
ve dataset/field/result'i repository'ye yazar. PG repository
`replace_metadata` ile metadata ve audit outbox'ı aynı transaction'da yazar.
Serviste `run_profile` da bulunmaktadır. Buna rağmen bu servis production
composition'a bağlı değildir; discovery/catalog API ve frontend akışı yoktur.
PG replace yaklaşımı snapshot'ı silip yeniden kurar; rapordaki hedef PARTIAL
discovery ve güvenli removal karar akışını sağlamaz.

| Zincir | Kanıt ve sonuç |
|---|---|
| Domain | Dataset, DataField, discovery result/diff modelleri — `VAR/KISMİ` |
| Migration | `20260724_03_data_source_baseline.py` dataset/field/profile tabloları — `VAR`; ayrı metadata-diff/schema-change lifecycle `YOK` |
| Repository | `PostgreSQLDataSourceRepository.replace_metadata` — `VAR/KISMİ` |
| Production composition root | Gerçek `DataSourceService` yerine `DevelopmentDataSourceStore` bağlı — `BAĞLI DEĞİL` |
| Service | `discover_metadata`, `_diff_metadata`, `run_profile` — `VAR` |
| API | List/create/test/activate/passivate ve profile-comparison vardır; discovery/catalog yönetim endpoint'i `YOK` |
| Frontend | Data source yönetimi vardır; discovery/diff/catalog kullanıcı akışı `YOK` |
| Permission/scope | Query scope backend'de `VAR`; discovery komutu trusted ActorContext yerine `actor_id` alır — `KISMİ` |
| Audit | Gerçek PG replace + outbox aynı transaction'da `VAR`; executable path'e bağlı değil |
| Test | Çok sayıda discovery/diff/profile birim testi ve PG persistence testi `VAR`; production/E2E `YOK` |

**Dosya ve semboller:** `data_sources/service.py:DataSourceService.discover_metadata`
(`763`), `DataSourceService.run_profile` (`901`),
`data_sources/postgresql_repository.py:replace_metadata`,
`tests/unit/test_data_sources.py:test_fr_011_fr_015_uc_004_csv_metadata_discovery_persists_dataset_fields_and_audit`,
`test_fr_022_ac_025_postgresql_metadata_change_requires_rule_review`.

**Değerlendirme:** Orkestrasyon ve test yokluğu alt iddiası yanlıştır. Gerçek
boşluk production binding, kullanıcı yüzeyi ve hedef lifecycle'ın tamamıdır.

- Doğru durum sınıfı: `CORRECTION_REQUIRED`
- Önerilen öncelik: P1
- Güven seviyesi: Yüksek

### 4.4 GAP-006 — Execution sonucu → otomatik issue üretimi

**Mevcut iddia:** Issue producer çağrı noktası ve servisi yoktur; yalnız issue
repository/lifecycle vardır; otomatik üretim ve test yoktur.

**Gerçek repository kanıtı:** `IssueService.create_for_trigger` trusted service
context ister, assignment çözer, deterministik dedup anahtarıyla issue oluşturur
veya occurrence artırır, kapanmış issue için recurrence davranışı uygular,
history/audit/notification üretir. `PostgreSQLIssueRepository.add_or_increment`
aynı transaction'da issue/history ve audit outbox'ı stage eder. Bu davranışların
kapsamlı birim ve PG integration testleri vardır.

Eksik olan execution result'tan bu servise production çağrısıdır. Dahası
`RuleExecutionResult` üzerinde `eligible_for_auto_issue` bulunmasına rağmen
`IssueTrigger` bu alanı taşımaz ve `create_for_trigger` eligibility doğrulamaz.
Bu yüzden yalnız bir caller eklenmesi, teknik/partial/uygunsuz sonuçların issue
üretmesini engelleyen güvenilir kapıyı garanti etmez. API'de manual issue create
endpoint'i ve frontend create akışı da yoktur; lifecycle mutasyonları vardır.

| Zincir | Kanıt ve sonuç |
|---|---|
| Domain | `issues/models.py:IssueTrigger`, Issue ve history modelleri — `VAR`; result eligibility bağı `YOK` |
| Migration | `20260723_01_issue_baseline.py` issue/history tabloları — `VAR` |
| Repository | `PostgreSQLIssueRepository.add_or_increment` — `VAR` |
| Production composition root | `IssueService` producer olarak örneklenmez; development issue store bağlı — `BAĞLI DEĞİL` |
| Service | `IssueService.create_for_trigger` — `VAR`; execution-result adapter/gate `YOK` |
| API | Issue read/lifecycle endpoint'leri `VAR`; POST create `YOK` |
| Frontend | Issue lifecycle kullanıcı akışı `VAR`; create akışı `YOK` |
| Permission/scope | Lifecycle servislerinde trusted context/scope `VAR`; producer standard trusted service context ister; eligibility enforcement `YOK` |
| Audit | PG issue write/history + outbox aynı transaction'da `VAR`; development route'larında `KISMİ/YOK` |
| Test | `test_issues.py` create/dedup/recurrence/audit testleri ve PG transaction testi `VAR`; execution→issue E2E `YOK` |

**Dosya ve semboller:** `issues/service.py:IssueService.create_for_trigger`
(`139`), `issues/postgresql_repository.py:add_or_increment` (`234`),
`executions/models.py:RuleExecutionResult.eligible_for_auto_issue` (`168`),
`tests/unit/test_issues.py:test_fr_064_fr_065_ac_015_creates_assigned_issue_and_notification_within_five_minutes`,
`tests/integration/test_postgresql_issue_mutations.py:test_fr_064_070_issue_lifecycle_and_audit_share_postgresql_transactions`.

**Değerlendirme:** “Producer servisi/testi yok” iddiası yanlış pozitiftir.
Production bridge ve eligibility enforcement yokluğu ise gerçek ve raporda
eksik tarif edilmiş bir boşluktur.

- Doğru durum sınıfı: `CORRECTION_REQUIRED`
- Önerilen öncelik: P1
- Güven seviyesi: Yüksek

### 4.5 GAP-008 — Kalıcı skor ve atomik yayım

**Mevcut iddia:** Skorlama domain/service kodu ve SQLite repository vardır;
`quality_scores`/`score_publications` PG tabloları ve production binding yoktur;
dashboard sentetik skor gösterir.

**Gerçek repository kanıtı:** Alembic zincirinde yalnız
`score_contribution_graphs` eklenmiştir. `quality_scores` ve
`score_publications` yoktur. `ScoringService`, `SQLiteScoreRepository` ile
çalışır. PG katkı grafiği repository'si vardır ve audit atomikliği test edilir,
fakat production composition'a bağlı değildir. Dashboard composition SQLite
score repository'yi sentetik değerlerle seed eder; `/api/v1/scores` yazma/yayım
yüzeyi yoktur.

| Zincir | Kanıt ve sonuç |
|---|---|
| Domain | `scoring/models.py` ve `ScoringService` — `VAR` |
| Migration | Contribution graph `VAR`; score/publication tabloları `YOK` |
| Repository | `SQLiteScoreRepository` ve PG contribution graph `VAR`; PG score/publication repository `YOK` |
| Production composition root | SQLite sentetik score bağlı; PG contribution graph bağlı değil — `KISMİ` |
| Service | Skor hesaplama/yayım mantığı `VAR`, production persistence `YOK` |
| API | Dashboard read projection `VAR`; score lifecycle/yayım API'si `YOK` |
| Frontend | Dashboard skor gösterimi `VAR`; yönetim/yayım akışı `YOK` |
| Permission/scope | Dashboard read scope backend kararıyla filtrelenir — `VAR`; publish command sınırı production'da yok |
| Audit | SQLite servis audit'i `KISMİ`; PG katkı grafiği outbox `VAR`; score publication PG atomikliği `YOK` |
| Test | SQLite skor testleri ve tek PG contribution graph atomiklik testi `VAR`; PG score publication/E2E `YOK` |

**Dosya ve semboller:** `scoring/repository.py:SQLiteScoreRepository`,
`scoring/service.py:ScoringService`,
`scoring/postgresql_contributions.py:PostgreSQLContributionGraphRepository`,
`api/development.py:create_development_app` (`1147`),
`20260730_13_score_contribution_graphs.py`,
`test_postgresql_score_contributions.py:test_graph_snapshot_and_audit_outbox_are_atomic_and_immutable`.

**Değerlendirme:** Raporun ana iddiası doğrulanmıştır.

- Doğru durum sınıfı: `CONFIRMED`
- Önerilen öncelik: P1
- Güven seviyesi: Yüksek

### 4.6 GAP-009 — İstisna, suppression ve kalite borcu

**Mevcut iddia:** Exception/waiver/override, suppression ve quality-debt
capability'si tüm katmanlarda yoktur.

**Gerçek repository kanıtı:** Domain, migration, repository, service, API,
frontend ve test taramalarında bu yaşam döngüsüne ait bir uygulama bulunmadı.
`ExecutionStatus.SUPPRESSED_BY_EXCEPTION` yalnız sonuç durum değeridir; istisna
nesnesi, onay, süre, scope, bastırma kaydı veya debt üretimi sağlamaz.

| Zincir | Kanıt ve sonuç |
|---|---|
| Domain | Exception/waiver/debt modeli `YOK` |
| Migration | `exceptions`, `exception_suppressions`, `quality_debts` `YOK` |
| Repository | `YOK` |
| Production composition root | `YOK` |
| Service | `YOK` |
| API | `YOK` |
| Frontend | `YOK` |
| Permission/scope | İstisna maker-checker/scope `YOK` |
| Audit | İstisna/debt audit olayı `YOK` |
| Test | `YOK` |

**Dosya ve semboller:** Negatif kanıt, 14 Alembic version dosyası ile
`docs/backend/src`, `frontend/src` ve `tests` üzerinde ilgili domain
terimlerinin taranmasına dayanır; tek yakın eşleşme
`executions/models.py:SUPPRESSED_BY_EXCEPTION`'dır.

**Değerlendirme:** Fonksiyonel eksiklik doğrulanmıştır. Bununla birlikte rapor
P1 sırasını risk/bağımlılık metriğiyle gerekçelendirmez. İşlev, production issue
producer (GAP-006), scheduling (GAP-003) ve notification delivery (GAP-007)
tamamlanmadan kullanılamaz. Bağımsız uygulama sırası açısından P2 önerilir.

- Doğru durum sınıfı: `SEVERITY_CHANGE_REQUIRED`
- Önerilen öncelik: P2
- Güven seviyesi: Orta

### 4.7 GAP-014 — Issue SLA ve escalation

**Mevcut iddia:** SLA atama, pause/resume, breach ve escalation modeli/servisi
yoktur.

**Gerçek repository kanıtı:** Issue history ve bazı deadline/policy kavramları
bulunsa da `issue_slas`, `issue_escalations`, SLA clock, breach evaluator,
escalation service/API/UI/test zinciri yoktur. Issue modelindeki mevcut
timestamp'ler hedef SLA state machine'in yerine geçmez.

| Zincir | Kanıt ve sonuç |
|---|---|
| Domain | Issue lifecycle `VAR`; SLA/escalation domaini `YOK` |
| Migration | Issue/history tabloları `VAR`; `issue_slas`/`issue_escalations` `YOK` |
| Repository | SLA/escalation repository `YOK` |
| Production composition root | `YOK` |
| Service | SLA clock/breach/escalation evaluator `YOK` |
| API | `YOK` |
| Frontend | SLA yönetim/ihlâl akışı `YOK` |
| Permission/scope | SLA override/escalation permission'ları runtime'da `YOK` |
| Audit | SLA/escalation audit `YOK` |
| Test | `YOK` |

**Dosya ve semboller:** `issues/models.py`,
`20260723_01_issue_baseline.py`; negatif kanıt tüm backend/frontend/migration/test
taramasına dayanır.

**Değerlendirme:** Eksiklik doğrudur; ancak P1 sırası kanıtlanmamıştır. İşlev
otomatik issue üretimi ve gerçek notification delivery'ye bağımlı olduğundan
P2 önerilir.

- Doğru durum sınıfı: `SEVERITY_CHANGE_REQUIRED`
- Önerilen öncelik: P2
- Güven seviyesi: Orta

### 4.8 GAP-026 — Organizasyon, domain ve politika yönetimi

**Mevcut iddia:** Org unit, business/data domain, ownership, glossary ve ortak
policy lifecycle tüm katmanlarda yoktur.

**Gerçek repository kanıtı:** İlgili domain modelleri, Alembic tabloları,
repository/service, API, frontend ve test bulunmadı. Migration 14'teki lineage
governance evidence tabloları mevcut lineage çıktısının kanıt projeksiyonudur;
organizasyon/domain/policy CRUD, approval, rollback veya ownership yaşam
döngüsü değildir. `PolicyAuthorizationService` ise yetkilendirme karar
servisidir; yönetilen ortak policy aggregate'i değildir.

| Zincir | Kanıt ve sonuç |
|---|---|
| Domain | Org/domain/glossary/common-policy aggregate'leri `YOK` |
| Migration | D01 yönetim tabloları `YOK`; yalnız lineage governance evidence `VAR` ama kapsam dışı |
| Repository | `YOK` |
| Production composition root | `YOK` |
| Service | `YOK` |
| API | `YOK` |
| Frontend | `YOK` |
| Permission/scope | Mevcut ID-set scope `VAR`; yönetilen domain/ownership scope kaynağı `YOK` |
| Audit | D01 değişim audit'i `YOK` |
| Test | `YOK` |

**Dosya ve semboller:** `20260730_14_lineage_governance_evidence.py`,
`identity/service.py:PolicyAuthorizationService`; negatif kanıt backend,
frontend, migration ve test taramasına dayanır.

**Değerlendirme:** Ana iddia doğrulanmıştır. Bu boşluk production scope ve
ownership modelinin güvenilir kaynağını etkilediği için P1 korunmalıdır.

- Doğru durum sınıfı: `CONFIRMED`
- Önerilen öncelik: P1
- Güven seviyesi: Yüksek

## 5. Raporun kaçırdığı yanlış negatifler

### 5.1 FN-001 — Data-source maker-checker endpoint tarafından atlanıyor

**İlgili bölüm:** GAP-001, GAP-022, `09-State-Machines.md` ST-DataSource,
`10-Roles-and-Permissions.md` SoD matrisi.

**Mevcut iddia:** Data-source state machine kod ekseninde mevcut; maker ve
checker farklı aktör olmalıdır. Rapor bunu daha çok production binding/test
boşluğu olarak ele alır.

**Gerçek kanıt:** Gerçek `DataSourceService.decide_activation`,
`request.maker_actor_id == context.actor_id` olduğunda reddeder
(`data_sources/service.py:461-500`). Ancak executable API
`POST /api/v1/data-sources/{id}/activation` ActorContext çözmeden doğrudan
`data_source_mutation_service.activate(id)` çağırır (`api/app.py:2073-2082`).
Composition bu porta `DevelopmentDataSourceStore` bağlar
(`api/development.py:1367`); store `TEST_SUCCEEDED -> ACTIVE` geçişini maker,
checker, role, scope veya audit olmadan yapar (`951-968`). Frontend
`dataSources/api.ts:activateDataSource` üzerinden endpoint'i çağırır ve
`test_data_source_write_successful_activate_passivate_flow` bu doğrudan geçiş
için 200 bekler.

**Değerlendirme:** Bu yalnız eksik test değil, erişilebilir command yüzeyinde
onay adımı bypass'ıdır.

- Doğru durum sınıfı: `FALSE_NEGATIVE`
- Önerilen öncelik: P0
- Güven seviyesi: Yüksek

### 5.2 FN-002 — Mutasyonlarda role/scope enforcement tutarsız

**İlgili bölüm:** GAP-001, GAP-022, `10-Roles-and-Permissions.md`,
`11-Test-Coverage-Gaps.md` authorization matrisi.

**Mevcut iddia:** Scope modelinin eksikliği ağırlıkla kalıcı IAM yokluğu olarak
anlatılır; mevcut query authorization ile command authorization ayrımı açıkça
raporlanmaz.

**Gerçek kanıt:** Query servisleri backend filtrelerini gerçekten uygular:
`IssueQueryService`, `RuleQueryService`, `ExecutionQueryService` ve
`DataSourceQueryService`, `PolicyAuthorizationService` kararındaki izinli
ID'leri reader'a iletir. Buna karşılık:

- data-source create/test/activate/passivate route'ları ActorContext'i mutation
  portuna hiç iletmez (`api/app.py:2017-2110`);
- `DevelopmentRuleStore.create_rule` yalnız context'in `None` olmamasını kontrol
  eder; rol ve dataset kapsamını doğrulamaz (`development.py:837-882`);
- adı `create_rule_without_dataset_scope_returns_403` olan test, yorumda fake
  servisin kontrol yapmadığını kabul eder ve gerçekte `201` assert eder
  (`test_rule_api.py:405-433`);
- manual execution endpoint'i yalnız `actor_id` geçirir; bağlanan
  `PostgreSQLExecutionStartService.start_manual` arbitrary rule version/source
  ID'lerinin kapsamını, aktifliğini veya aktör rolünü doğrulamaz
  (`api/app.py:2120-2137`, `api/postgresql_execution.py:63-110`).

**Değerlendirme:** “Scope yalnız frontend'de” demek yanlış olur; read path
backend kontrollüdür. Fakat command path'teki bypass ayrıca raporlanması gereken
P0 yanlış negatiftir. Yanıltıcı test adı da boşluğu görünmez kılar.

- Doğru durum sınıfı: `FALSE_NEGATIVE`
- Önerilen öncelik: P0
- Güven seviyesi: Yüksek

### 5.3 FN-003 — Şema ayrışması belirsiz risk değil, mevcut wiring hatası

**İlgili bölüm:** GAP-001, `08-Existing-Schema-Gap-Analysis.md` Q-13.

**Mevcut iddia:** `dq` ile `data_quality` arasında şema tutarsızlığı olabilir
ve PG yollarını çalışmaz kılabilir.

**Gerçek kanıt:** Alembic environment varsayılanı `dq`'dur
(`alembic/env.py:24`); persistence varsayılanı da
`DEFAULT_SCHEMA_NAME = "dq"` (`persistence/database.py:15`). `run_dev.py` ise
settings ve `PostgreSQLTransactionalAudit` için açıkça `data_quality` kullanır
(`10-33`). `create_development_app`, execution ve job repository'lerini schema
argümanı vermeden kurar (`development.py:1332-1333`), dolayısıyla bunlar `dq`
kullanır. Aynı command akışında business/job ve audit outbox farklı şemalara
yönelir.

Ek olarak `run_dev.py:_FakePreparedRepo` yalnız `store` metoduna sahiptir;
`PostgreSQLTransactionalAudit.publish_pending` ise `repository.append` çağırır
(`audit/postgresql_outbox.py:82-116`). Hata yakalanıp outbox satırı PENDING
bırakılır; immutable audit ledger'a yayın gerçekleşmez.

**Değerlendirme:** Rapor doğru sinyali bulmuş, fakat bunu açık soru olarak
bırakmış ve çalıştırılabilir wiring üzerindeki kesin etkisini göstermemiştir.

- Doğru durum sınıfı: `CORRECTION_REQUIRED`
- Önerilen öncelik: P0 (GAP-001 altında)
- Güven seviyesi: Yüksek

### 5.4 FN-004 — Job claim hedef state/audit atomikliğini sağlamıyor

**İlgili bölüm:** GAP-002, `09-State-Machines.md` ST-Job,
`11-Test-Coverage-Gaps.md` §8.

**Mevcut iddia:** Worker backend'i tamamlanmış; eksik esasen runtime/entrypoint
ve buna ait testtir.

**Gerçek kanıt:** `claim_next` atomik row claim/lease uygular fakat audit
parametresi yoktur; `QUEUED` satırı doğrudan `RUNNING` olur. Hedef rapordaki
`AVAILABLE -> CLAIMED` ve aynı transaction'da `JOB_CLAIMED` olayı yoktur.
Terminal geçişlerdeki audit desteği claim boşluğunu kapatmaz.

**Değerlendirme:** Backend completeness beyanının kaçırdığı bir fonksiyonel ve
audit boşluğudur.

- Doğru durum sınıfı: `FALSE_NEGATIVE`
- Önerilen öncelik: P1
- Güven seviyesi: Yüksek

### 5.5 FN-005 — Auto-issue eligibility sınırı producer sözleşmesinde yok

**İlgili bölüm:** GAP-006, `09-State-Machines.md` ST-RuleExecution/ST-Issue.

**Mevcut iddia:** Eksik olan producer implementasyonu/call point'tir.

**Gerçek kanıt:** Producer implementasyonu vardır; fakat execution result'taki
`eligible_for_auto_issue` alanı `IssueTrigger` sözleşmesine taşınmaz ve
`IssueService.create_for_trigger` tarafından doğrulanmaz. Sonuçtan trigger'a
güvenilir adapter/caller da yoktur.

**Değerlendirme:** Eksik sadece bir çağrı değildir; yanlış sonuç sınıfının issue
üretmesini engelleyecek trust boundary de tanımlı değildir.

- Doğru durum sınıfı: `FALSE_NEGATIVE`
- Önerilen öncelik: P1
- Güven seviyesi: Yüksek

## 6. Yanlış pozitif ve kanıtsız alt iddialar

| İlgili rapor iddiası | Repository kanıtı | Değerlendirme | Doğru sınıf | Öncelik | Güven |
|---|---|---|---|---|---|
| GAP-003: schedule servis/tetikleme/test yok | `SchedulingService.create_schedule/trigger_due`, SQLite+PG repository ve `test_executions.py` scheduling testleri var | Kullanıcı kabiliyeti yok, fakat backend/test yokluğu yanlış | `FALSE_POSITIVE` | P1 GAP metni düzeltilmeli | Yüksek |
| GAP-004: discovery orkestrasyon/diff/test yok | `DataSourceService.discover_metadata`, `_diff_metadata`, `replace_metadata` ve kapsamlı unit/PG testleri var | Orkestrasyonun yok sayılması yanlış | `FALSE_POSITIVE` | P1 GAP metni düzeltilmeli | Yüksek |
| GAP-005 ve ST-Profile: profiler executor yok | `DataSourceService.run_profile` CSV/PG profile executor'larını çağırır; profile ve comparison testleri var | Runtime/API/baseline boşluğu var, executor/test yokluğu yanlış | `FALSE_POSITIVE` | P2 | Yüksek |
| GAP-006: issue producer servisi ve otomatik dedup/recurrence testi yok | `IssueService.create_for_trigger`, `add_or_increment` ve `test_issues.py` mevcuttur | Missing bridge, mevcut producer ile karıştırılmış | `FALSE_POSITIVE` | P1 GAP metni düzeltilmeli | Yüksek |
| `09-State-Machines.md`: ST-ApprovalRequest tamamen yok | `rule_approval_requests` ve `data_source_activation_requests` migration/model/service/repository/test zincirleri var | Ortak generic approval ve diğer domain onayları yok; “tamamen yok” yanlış | `CORRECTION_REQUIRED` | P1 (domain bazında ayrıştırılmalı) | Yüksek |
| `11-Test-Coverage-Gaps.md`: gerçek PG transaction'ında durum+audit atomikliği test edilmiyor | Execution, issue, score contribution ve lineage PG testleri aynı transaction rollback/atomic write kontrolü içeriyor | Testler skip-gated olsa da kaynakta gerçek PG testleri var; “0” yanlış | `FALSE_POSITIVE` | P1 test çalıştırma kanıtı ayrı yazılmalı | Yüksek |
| `08-Existing-Schema-Gap-Analysis.md`: `retention_policy_id` sarkan FK | Migration 03 ve 06 kolonları String'dir; `retention_policies` tablosuna `ForeignKey` tanımlı değildir | Semantik olarak doğrulanmayan referans var, fakat sarkan DB FK yok | `CORRECTION_REQUIRED` | P2 | Yüksek |

### 6.1 Retention referansı ayrıntısı

`20260724_03_data_source_baseline.py` içindeki
`data_processing_inventory_versions.retention_policy_id` `NOT NULL String(40)`
kolonudur. Aynı tablodaki tanımlı FK `data_field_id` içindir. Benzer şekilde
`20260724_06_reporting_baseline.py` içindeki `reports.retention_policy_id`
nullable `String(36)` kolonudur ve FK değildir. `retention_policies` tablosunun
olmaması semantik bütünlük boşluğudur; veritabanında “hedefi düşmüş foreign key”
olarak tanımlanması teknik olarak yanlıştır.

### 6.2 ApprovalRequest ayrıntısı

Ortak `approval_requests` tablosu yoktur ve exception/contract/policy onayları
da yoktur. Buna karşılık rule ve data-source için domain-specific approval
aggregate'leri, maker/checker alanları, servis kuralları ve PG tabloları vardır.
Bu yüzden ST-ApprovalRequest değerlendirmesi tek bir `YOK` hücresiyle değil,
domain bazında `KISMİ` olarak gösterilmelidir.

## 7. Maker-checker, scope ve audit sonucu

### 7.1 Maker-checker gerçekten farklı aktör mü?

Servis seviyesinde evet:

- `DataSourceService.decide_activation` maker ile checker aynıysa reddeder;
- `RuleService.decide_rule_approval` maker ile checker aynıysa reddeder;
- issue verification servisinde çözümü oluşturan aktörün kendi çözümünü
  doğrulaması reddedilir ve bunun birim testleri vardır.

Veritabanı seviyesinde maker/checker kolonları bulunur, fakat aktör eşitsizliğini
zorlayan DB `CHECK` constraint'i yoktur. Güvence service boundary'ye bağlıdır.
Executable development API data-source activation'da bu boundary'yi tamamen
atlar. Dolayısıyla sistem bütünü için cevap “tutarlı biçimde hayır”dır.

### 7.2 Dataset/domain scope yalnız frontend'de mi?

Hayır. Read path'te scope backend'de uygulanır. Query service'ler izinli
dataset/source ID'lerini reader'a geçirir ve empty scope'un unscoped sorguya
dönüşmemesi test edilir. Ancak command path'te uygulama tutarlı değildir:
data-source mutation'ları context almaz, development rule store kapsam kontrolü
yapmaz ve manual execution start kaynak/kural kapsamını doğrulamaz. Sorun
“frontend-only scope” değil, read/command authorization ayrışmasıdır.

### 7.3 Audit iş verisiyle aynı transaction'da mı?

Gerçek PostgreSQL repository yollarının önemli bir bölümünde iş verisi ile
**audit outbox satırı** aynı SQLAlchemy transaction'ındadır. Issue mutasyonları,
execution create, score contribution graph ve lineage kanıtında bunu sınayan PG
testleri vardır. Immutable ledger'a `publish_pending` ile aktarım ayrı
transaction'dır; bu outbox deseninin doğal sonucudur ve “ledger ile business
row aynı transaction” olarak anlatılmamalıdır.

Executable development yollarında ise bu garanti yoktur:

- Issue/Rule/DataSource development store'ları outbox stage etmez;
- audit API ayrı sentetik `SQLiteAuditRepository` okur;
- `run_dev.py` şema ayrışması ve yanlış prepared-repository protokolü nedeniyle
  PG audit yayımı tamamlanmaz.

Bu nedenle “repository kodunda atomik outbox vardır” ile “çalışan uygulamada
audit zinciri tamamdır” aynı durum değildir.

## 8. Test doğrulaması

### 8.1 Statik sayım

2026-08-04 tarihinde mevcut çalışma ağacında:

| Ölçüm | Sonuç |
|---|---:|
| Unit `test_*.py` dosyası | 57 |
| Integration `test_*.py` dosyası | 11 |
| Unit test fonksiyonu/metodu | 1057 |
| Integration test fonksiyonu/metodu | 92 |
| Toplam test fonksiyonu/metodu | 1149 |
| Pytest tarafından parametrizasyon sonrası collect edilen test | 1505 |
| E2E test | 0 |

`11-Test-Coverage-Gaps.md` içindeki 57 unit dosyası ve toplam 1149 test
fonksiyonu yeniden üretilebilir; “12 integration test dosyası” ancak
`conftest.py` gibi test olmayan Python dosyası sayılırsa elde edilir. Unit
`~1037`, integration `~112` dağılımı mevcut ağaç için yanlıştır; doğru dağılım
1057/92'dir. Pytest test-adedi ise parametrizasyon nedeniyle 1505'tir.

### 8.2 Çalıştırma sonucu ve test double sınıfı

Kritik bulgulara temas eden seçili unit suite çalıştırması:

```text
pytest -q \
  tests/unit/test_data_sources.py \
  tests/unit/test_executions.py \
  tests/unit/test_issues.py \
  tests/unit/test_bff_session_api.py \
  tests/unit/test_data_source_api.py \
  tests/unit/test_rule_api.py \
  tests/unit/test_execution_api.py

297 passed
```

Integration suite, `DATA_QUALITY_POSTGRES_TEST_URL` tanımlı olmadığı için:

```text
pytest -q docs/testing/02-Entegrasyon

92 skipped
```

Sonuç olarak integration test kaynakları mock/in-memory değildir; gerçek
PostgreSQL URL'si ve schema oluşturarak çalışan testlerdir. Ancak bu doğrulama
ortamında hiçbiri yürümemiştir. Bu repository'de PG davranışına yönelik test
**kodu** bulunduğunu kanıtlar, standard pipeline'da veya bu çalışma ağacında
başarıyla **çalıştırıldığını** kanıtlamaz. Rapor bu iki durumu ayırmalıdır.

Örnek gerçek PG atomiklik testleri:

- `test_postgresql_execution_persistence.py:test_audit_outbox_atomic_write`
- `test_postgresql_issue_mutations.py:test_fr_064_070_issue_lifecycle_and_audit_share_postgresql_transactions`
- `test_postgresql_issue_mutations.py:test_nfr_rel_006_audit_conflict_rolls_back_issue_and_history`
- `test_postgresql_score_contributions.py:test_graph_snapshot_and_audit_outbox_are_atomic_and_immutable`

E2E yokluğu doğrulanmıştır: `tests/e2e/` altında executable test
değil yalnız strateji dokümanı vardır. Dolayısıyla domain→frontend zincirlerinin
tamamını aynı testte doğrulayan kanıt yoktur.

## 9. Dokümantasyondaki “tamamlandı” beyanlarının sonucu

| Beyan | Sonuç | Gerekçe |
|---|---|---|
| Worker backend tamam, yalnız entrypoint eksik | `CORRECTION_REQUIRED` | Claim audit ve hedef state modeli tamam değil |
| Scheduling model-only/test yok | `FALSE_POSITIVE` | Service, SQLite/PG repository ve due-trigger unit testleri var |
| Metadata discovery yalnız connector | `FALSE_POSITIVE` | Servis orkestrasyonu, diff, PG replace ve testler var |
| Profile executor yok | `FALSE_POSITIVE` | `DataSourceService.run_profile` ve testleri var; runtime/yüzey yok |
| Issue producer servisi yok | `FALSE_POSITIVE` | `IssueService.create_for_trigger` var; execution bridge/eligibility yok |
| ST-ApprovalRequest tamamen yok | `CORRECTION_REQUIRED` | Rule/data-source domain-specific approval'ları var; generic/diğer domainler yok |
| PG transaction audit testi sıfır | `FALSE_POSITIVE` | Gerçek PG test kaynakları var, fakat bu ortamda 92'si de skip |
| Production composition eksik | `CONFIRMED` | PG sınıflarının çoğu executable root'a bağlı değil; bağlı bölümde write/read/schema ayrışması var |
| Kalıcı production IAM/RBAC yok | `CONFIRMED` | D02 migration/repository/root yok; mevcut dev/BFF/LDAP kodu bunu tamamlamıyor |

## 10. Nihai bağımsız kanaat

Raporun ana yönü — production composition, kalıcı IAM, skor yayımı ve büyük
yönetişim yaşam döngülerinin eksik olduğu — repository kanıtıyla büyük ölçüde
uyumludur. Bununla birlikte rapor backend kodunun varlığı ile production'da
erişilebilir kullanıcı kabiliyetini birçok yerde birbirine karıştırmıştır.
Scheduling, metadata discovery/profiling ve issue producer için mevcut kodu
yanlışlıkla “yok” sayarken; development API'nin gerçek servis/state-machine
sınırlarını bypass etmesini ve command authorization ayrışmasını atlamıştır.

En önemli düzeltme, GAP'leri yalnız “dosya/sınıf var mı?” üzerinden değil,
production composition ve trust boundary üzerinden sınıflandırmaktır. Bu ölçüte
göre mevcut backend parçaları rapordaki bazı `MISSING` iddialarını çürütür, fakat
uçtan uca production kabiliyetini kanıtlamaz. Tersine endpoint'in varlığı da
maker-checker, scope ve audit zinciri atlanabildiğinde kabiliyetin tamamlandığı
anlamına gelmez.

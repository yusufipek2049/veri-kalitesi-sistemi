---
type: functional-audit-work
stage: "19 — DS-06 Değişiklik Envanteri"
scope: slice-ds06-change-inventory
inputs:
  - 18-Sixth-Slice-Decision.md
  - 17-Slice-DS05-Change-Inventory.md
  - 17-Slice-DS05-Plan-Validation.md
  - 07-Implementation-Waves.md
  - ../04-Functional-Gap-Inventory.md
  - ../07-Target-Data-Model.md
  - ../09-State-Machines.md
  - ../13-Implementation-Roadmap.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-06
---

# 19 — DS-06 Değişiklik Envanteri

> Seçilen altıncı dilim: **DS-06 — Skor kalıcılığı ve yayım (GAP-008)**.
> Bu belge değişecek tablo, kolon, servis, endpoint, ekran ve testleri gerçek
> repository yolları ve sembolleriyle belirler. Uygulama veya kaynak kod
> değişikliği içermez.

---

## 1. Envanter özeti

| Katman | Karar |
|---|---|
| Yeni migration | `alembic/versions/20260806_19_score_publication.py` |
| Ana yeni tablolar | `quality_scores`, `score_publications` |
| Production politika tabloları | `scoring_configurations`, `scoring_configuration_approvals`, `dataset_partial_score_policies` |
| Kısıtı değişecek tablo | `score_contribution_graphs` — `quality_score_id` FK ve indeks/check parity |
| Yeniden kullanılacak tablolar | `rule_executions`, `rule_execution_results`, `quality_rules`, `rule_versions`, `datasets`, `data_sources`, `background_jobs`, `audit_outbox`, `audit_events` |
| Yeni job type | `SCORE_PUBLICATION`; mevcut `background_jobs` ve worker altyapısı kullanılır |
| Ana backend değişikliği | Persisted execution result → tam skor seti → atomik PostgreSQL yayımı → sorgu/reproduction |
| Yeni endpoint | Beş skor endpoint'i: liste, detay, kural geçmişi, karşılaştırma, reproduction |
| Frontend | Yeni `/scores`, `/scores/:id`, `/scores/comparison`; mevcut dashboard backend'de PG reader'a bağlanır |
| Production kanıtı | Gerçek execution result → durable score job → hesap/yayım → PG → API/dashboard/UI → audit → reproduction |

Mevcut Alembic head `20260806_18`'dir. DS-06 forward revision'ı
`20260806_19` olur; migration 01–18 değiştirilmez.

## 2. Repository kanıtı ve plan düzeltmeleri

### 2.1 Doğrudan yeniden kullanılacak mevcut yapı

| Kanıt | Mevcut dosya/simge | Sonuç |
|---|---|---|
| Çok seviyeli hesaplama vardır | `scoring/service.py:ScoringService` | Yeni skor motoru yazılmaz; formüller batch hesaplamaya ayrıştırılır |
| Kural skoru vardır | `ScoringService.calculate_execution`, `_score_rule` | Persisted `RuleExecutionResult` sayaçları kullanılır |
| Dataset/boyut/kaynak/kurum agregasyonu vardır | `calculate_dataset_score`, `calculate_dimension_score`, `calculate_source_score`, `calculate_enterprise_score` | Mevcut hesap mantığı korunur |
| Resmî kısmi skor kararı vardır | `partial_score_policies.py:DatasetPartialScorePolicyService.evaluate` | Official/provisional ayrımı yeniden icat edilmez |
| Katkı ve karşılaştırma vardır | `scoring/contributions.py:contribution_graph`, `compare_scores` | Detay ve karşılaştırma endpoint'leri bu fonksiyonları kullanır |
| Trend hesabı vardır | `scoring/trends.py:compute_trend_components` | İkinci trend motoru yazılmaz |
| PG katkı grafiği vardır | `scoring/postgresql_contributions.py:PostgreSQLContributionGraphRepository` | Mevcut tablo korunur ve publication transaction'ına katılabilir hâle getirilir |
| Dashboard scope-safe query vardır | `dashboard/service.py:DashboardQueryService`, `ScoreReader` | Yeni dashboard servisi yazılmaz |
| Dashboard gerçek API çağrısı yapar | `dashboard/api.ts:fetchDashboardSummary` → `/api/v1/dashboard/summary` | Frontend dashboard'u `/scores` endpoint'ine çevrilmez |
| Worker/queue kalıcıdır | `jobs/worker.py:PersistentJobWorker`, `jobs/postgresql_repository.py:enqueue` | Yeni queue veya daemon kurulmaz |

### 2.2 Roadmap'te düzeltilmesi gereken varsayımlar

1. **Yalnız iki tablo yeterli değildir.** `ScoringService._configuration()` aktif
   konfigürasyonu `SQLiteScoreRepository.get_active_configuration()` üzerinden
   okur. `ScoringConfigurationService` ve approval kayıtları da aynı SQLite
   connection'a bağlıdır. Production skorlama ve yeniden üretim için
   `scoring_configurations` ile `scoring_configuration_approvals` PostgreSQL'e
   taşınmalıdır.
2. **Partial policy yalnız SQLite'dadır.** Roadmap'in “audit'i PostgreSQL outbox'a
   taşı” koşulu, `SQLiteDatasetPartialScorePolicyRepository` üzerinde atomik
   uygulanamaz. `dataset_partial_score_policies` için PostgreSQL repository ve
   migration gerekir.
3. **Kritik veto mevcut değildir ve DS-06 kapsamı dışındadır.** `ScoringService`
   içinde veto uygulayan kod veya `CRITICAL_VETO_APPLIED` olayı yoktur. Bu nedenle
   veto kolonu, policy alanı, audit olayı, UI alanı ve testi eklenmez.
4. **DOMAIN seviyesi mevcut değildir.** `ScoreScopeType` ve `ScoringService`
   `RULE/DATASET/DIMENSION/SOURCE/ENTERPRISE` destekler. Repository'de
   `business_domains` veya dataset→domain eşlemesi yoktur. DS-06 sahte `DOMAIN`
   skoru üretmez; domain agregasyonu gerçek mapping sahibi ayrı yönetişim
   dilimine bırakılır.
5. **Dashboard frontend'i zaten API'ye bağlıdır.** Değişmesi gereken esas yol
   `api/composition.py` içindeki `UnavailableDashboardService`; production'da
   `DashboardQueryService(PostgreSQLScoreRepository, ...)` bağlanmalıdır.

Bu düzeltmeler yapılmadan yalnız `quality_scores` tablosu eklemek production
çıkış kapısını karşılamaz.

### 2.3 Uygulama öncesi A–G kararları

| Madde | Kesin karar | Envantere etkisi |
|---|---|---|
| A — `NOT_QUALIFIED` | Yeni enum değeri eklenmez. Uygun olmayan sonuç mevcut `ScoreStatus.NOT_CALCULATED`, null `score_value` ve `RuleExecutionResult.eligible_for_official_scoring=false` ile temsil edilir. Dışlama nedeni bounded `calculation_details` içinde saklanır. | `qualification_verdict` kolonu ve yeni status kaldırıldı. |
| B — `CRITICAL_VETO_APPLIED` | Repository'de çalışan veto state-machine'i olmadığından DS-06'dan çıkarıldı. | Veto kolonları, config alanı, audit olayı, DTO/UI ve testleri yoktur. |
| C — `score.read` | Yeni action/permission tanımlanmaz. Mevcut trusted/expiry/policy-version kapısı ile source/dataset/enterprise scope yetkilendirmesi yeniden kullanılır. | Yeni `ScoreAccessPolicy` ve rol tablosu yoktur. |
| D — `scoring_configurations` | PostgreSQL'e taşınır; aktif config olmadan production hesaplama ve immutable reproduction mümkün değildir. Approval tablosu da parity için taşınır. | Revision 19 ve `REQUIRED_TABLES` kapsamındadır; CRUD UI/API kapsam dışıdır. |
| E — `score.reproduce` | Yeni action/rol tanımlanmaz. Normal okuma scope'una ek olarak trusted ve süresi geçmemiş `ActorContext.privileged=true` zorunludur; POST için CSRF uygulanır. | `privileged=false` 403; reproduction score/publication state'ini değiştirmez. |
| F — Phase B / Phase C | `api/composition.py:PhaseBProviders` değişmez. Score publication actor-context sağlayıcısı mevcut `jobs/production.py:ProductionWorkerProviders` içine eklenir ve worker/Phase C composition sınırında kullanılır. | Yeni provider dataclass'ı kurulmaz; API query/config repository'leri doğrudan production composition'da kurulur ve score provider Issue/Phase B'ye karıştırılmaz. |
| G — veto kapsamı | Veto mekanizması bütünüyle sonraki, ayrı politika dilimine ertelenir. | Placeholder kolon veya kapalı özellik olarak dahi DS-06'ya alınmaz. |

## 3. Tablolar, kolonlar ve migration

### 3.1 Yeni `score_publications` tablosu

| Kolon/kısıt | Tip / davranış | Amaç |
|---|---|---|
| `publication_id` | `String(36)` PK | Yayın kimliği |
| `execution_id` | `String(36)` NN, FK → `rule_executions.execution_id`, unique | Kaynak execution ve retry idempotency'si |
| `period` | `String(80)` NN | Kanonik UTC yayın dönemi |
| `input_digest` | `String(71)` NN (`sha256:<64hex>`) | Result/config/rule snapshot replay bütünlüğü |
| `status` | `String(20)` NN; `PUBLISHED`, `SUPERSEDED` | ST-QualityScore yayın durumu |
| `policy_version` | `String(80)` NN | Kullanılan scoring configuration sürümü |
| `published_at` | timestamptz NN | Yayın zamanı |
| `superseded_at` | nullable timestamptz | Yeni yayınla geçersiz kılınma zamanı |
| current partial unique | `UNIQUE(period) WHERE status='PUBLISHED'` | Aynı dönemde tek güncel yayın |
| consistency check | `SUPERSEDED` ise `superseded_at` dolu; `PUBLISHED` ise null | Yarım state geçişini engelleme |

İndeksler: `published_at DESC`, `(period, status)` ve `execution_id`. Yeni yayın
aynı period satırlarını kilitler; önceki yayın ile ona bağlı skorlar aynı
transaction'da supersede edilir. `score_publications` job durumu değildir;
`PENDING/RUNNING/FAILED` için mevcut `background_jobs` kullanılır.

### 3.2 Yeni `quality_scores` tablosu

| Kolon/kısıt | Tip / davranış | Amaç |
|---|---|---|
| `quality_score_id` | `String(36)` PK | Değişmez skor kimliği |
| `publication_id` | nullable FK → `score_publications.publication_id` | Yalnız yayımlanan skorun yayın bağı |
| `execution_id` | NN FK → `rule_executions.execution_id` | Kaynak çalıştırma |
| `rule_result_id` | nullable FK → `rule_execution_results.rule_result_id` | Kural skorunun sayaç kanıtı |
| `rule_version_id` | nullable FK → `rule_versions.rule_version_id` | Kural seviyesi referansı |
| `scope_type` | `RULE/DATASET/DIMENSION/SOURCE/ENTERPRISE` | Mevcut `ScoreScopeType` parity |
| `scope_id` | nullable `String(128)` | Enterprise için null; diğer seviyelerde dolu |
| `score_value` | nullable `Numeric(7,4)`, `0..100` | `NOT_CALCULATED/NO_DATA` sıfıra çevrilmez |
| `score_status` | mevcut `ScoreStatus` değerleri | Hesap durumu; publication durumuyla karıştırılmaz |
| `measurement_status` | nullable `String(30)` | Mevcut `MeasurementStatus` projection'ı |
| `level` | nullable `GOOD/ACCEPTABLE/RISKY/CRITICAL` | Mevcut skor sınıfı |
| `rule_version_digest` | nullable `String(71)` (`sha256:<64hex>`) | Rule IR/version bütünlük kanıtı |
| `policy_version` | `String(80)` NN | Scoring configuration sürümü |
| `included_component_count` | nullable integer, `>=0` | Açıklanabilirlik özeti |
| `excluded_component_count` | nullable integer, `>=0` | Dışlanan bileşen özeti |
| `calculation_details` | JSONB NN | Sayaç/ağırlık/formül/sürüm snapshot'ı ve reproduction girdisi |
| `calculated_at` | timestamptz NN | Değişmez hesap zamanı |

Kısıtlar ve indeksler:

- unique `(execution_id, scope_type, COALESCE(scope_id, ''))` — mevcut SQLite
  `idx_quality_scores_execution_scope` semantiği;
- `(scope_type, scope_id, calculated_at DESC)` ve `(publication_id)` indeksleri;
- enterprise dışındaki scope'ta `scope_id` zorunlu;
- `score_value` null ise `level` null;
- `publication_id` dolu skor resmî ve sayısal olmalıdır;
- `NO_DATA/NOT_CALCULATED_*` skorları yayına bağlanamaz;
- resmî hesaplamaya uygun olmayan result yeni enum/kolonla değil,
  `eligible_for_official_scoring=false`, `ScoreStatus.NOT_CALCULATED` ve null
  skorla korunur.

`score_status` için hedef dokümandaki `PUBLISHED/SUPERSEDED` değerleri
eklenmez; bunlar `score_publications.status` sahibidir. Böylece hesap durumu ile
yayın yaşam döngüsü tek kolonda çakışmaz.

### 3.3 Yeni production policy tabloları

#### `scoring_configurations`

Mevcut SQLite şemasının PostgreSQL karşılığıdır:

- `configuration_id` PK, `version` unique;
- `threshold_version`, üç threshold `Numeric(7,4)`;
- `dimension_weights` JSONB, `criticality_weights` JSONB;
- `created_by`, `created_at`, `is_active`, `activated_at`;
- `UNIQUE(is_active) WHERE is_active=true`.

Konfigürasyon migration içinde örtük biçimde “aktif” yaratılmaz. Development/live
test verisi `scripts/seed_database.py` ile açık sürüm olarak eklenir; production
preflight ayarlardaki sürüm yoksa fail-fast olur.

#### `scoring_configuration_approvals`

Mevcut `ScoringConfigurationApproval` parity'si:

- `approval_id` PK;
- `configuration_id` unique FK → `scoring_configurations`;
- `maker_actor_id`, nullable `checker_actor_id`, `policy_version`;
- `status` (`PENDING/APPROVED/REJECTED`), nullable `decision_reason_code`;
- `requested_at`, nullable `decided_at`;
- maker ≠ checker uygulama ve DB check'i. Kullanıcı FK'ları DS-10'a kadar
  eklenmez.

#### `dataset_partial_score_policies`

`SQLiteDatasetPartialScorePolicyRepository` şemasının PostgreSQL karşılığıdır:

- `policy_id` PK, `dataset_id` FK → `datasets`;
- `policy_version`, `allow_official_partial_score`;
- dört oran kolonu `Numeric(7,6)`;
- `required_critical_rule_ids` ve `required_partitions` JSONB;
- `effective_from`, `approval_status`, `created_by`, nullable `approved_by`,
  nullable `audit_reference`, `created_at`;
- unique `(dataset_id, policy_version)`; oran `0..1` check'leri; maker ≠ checker.

Bu tabloya API/UI yönetim ekranı eklemek DS-06 kapsamında değildir. Mevcut
lifecycle servisi ve test/operasyon seed yolu production repository'ye taşınır.

### 3.4 Değişecek mevcut `score_contribution_graphs`

Migration 13'te tablo, `quality_scores` henüz olmadığı için FK'siz yaratılmıştır.
Revision 19:

- `quality_score_id` için FK → `quality_scores.quality_score_id` ekler;
- mevcut `(execution_id, scope_type, scope_id)` indeksini korur;
- scope check'ini runtime `ScoreScopeType` ile eşit tutar;
- grafiğin skorla aynı publication transaction'ında yazılmasını sağlar.

Yeni katkı, açıklanabilirlik, dönem farkı veya reproduction snapshot tablosu
eklenmez.

### 3.5 Değişmeyecek tablolar

- `rule_execution_results`: mevcut count, measurement ve
  `eligible_for_official_scoring` alanları okunur; DS-06 kolonu eklenmez.
- `rule_executions`, `rule_versions`, `quality_rules`, `datasets`, `data_sources`:
  FK/scope/config girdisi olarak okunur; şemaları değişmez.
- `background_jobs`, `job_dead_letters`, `workers`: yeni `SCORE_PUBLICATION` type
  mevcut string job sözleşmesinde çalışır; DDL değişmez.
- `audit_outbox`, `audit_events`: mevcut PostgreSQL transactional audit yolu
  kullanılır.
- `report_*`: DS-12 kapsamıdır.
- `risk_ratings`: DS-14 kapsamıdır.

### 3.6 Migration sırası

1. `scoring_configurations`, ardından `scoring_configuration_approvals` oluştur.
2. `dataset_partial_score_policies` oluştur.
3. `score_publications` oluştur.
4. `quality_scores` oluştur; önce publication/execution/rule FK'ları ve check'ler.
5. `score_contribution_graphs.quality_score_id` FK'sini ekle.
6. İndeks ve partial unique constraint'leri ekle.
7. Runtime SQLAlchemy table metadata'larını migration ile eşitle.
8. `api/composition.py:CURRENT_MIGRATION_HEAD` değerini `20260806_19` yap;
   beş yeni tabloyu `REQUIRED_TABLES` içine ekle.

Migration 01–18 ve SQLite dosyaları production şeması gibi değiştirilmez.

## 4. Backend servis, repository ve worker envanteri

### 4.1 Değişecek mevcut scoring dosyaları

| Dosya | Sembol | Planlanan değişiklik |
|---|---|---|
| `src/veri_kalitesi/scoring/models.py` | `QualityScore`, `ScoreScopeType`, `ScoreStatus`, `ScoringConfiguration`; yeni `ScorePublication`, `ScorePublicationStatus` | Publication ve kalıcı kanıt alanları; hesap/yayın statüsü ayrımı; mevcut status değerlerini koruma |
| `src/veri_kalitesi/scoring/service.py` | `ScoringService`, `_score_rule`, agregasyon yardımcıları | SQLite somut tipini dar repository protocol'üne çevirme; tam score-set'i persistence öncesi üretme; persisted eligibility kapısı; deterministik rule digest |
| `src/veri_kalitesi/scoring/repository.py` | `SQLiteScoreRepository` | Development/test adapter parity; yeni production sınıfı burada yazılmaz |
| `src/veri_kalitesi/scoring/partial_score_policies.py` | repository protocol, `DatasetPartialScorePolicyService`, lifecycle service | SQLite somut bağımlılığını porta çevirme; PostgreSQL outbox ile aynı transaction sözleşmesi |
| `src/veri_kalitesi/scoring/postgresql_contributions.py` | `PostgreSQLContributionGraphRepository` | Dış transaction session'ında stage edebilme; standalone mevcut `add_score` davranışını koruma |
| `src/veri_kalitesi/scoring/contributions.py` | `contribution_graph`, `compare_scores` | Yeni motor yok; persisted publication/policy/digest alanlarını graph version snapshot'ına dahil etme |
| `src/veri_kalitesi/scoring/__init__.py` | exports | Yeni PG repository, publication/query/job modellerini export etme |
| `src/veri_kalitesi/audit/policies.py` | `build_default_redaction_policy` | Yeni score calculation/publication/reproduction olayları için veri-minimum allowlist |

`ScoringService` mevcut formülleri korur fakat bugün her seviye sonunda
`repository.add_or_get` çağırdığı için atomik publication kuramaz. Yeni batch
metodu bütün skorları bellekte üretir; repository'ye yazma ve graph/audit staging
tek publication transaction'ında yapılır. Eski tek-seviye metotlar SQLite unit
test uyumu için bu ortak saf hesap yardımcılarına delegate eder; ikinci formül
ailesi oluşmaz.

### 4.2 Yeni dar kapsamlı backend dosyaları

| Yeni dosya | Sembol | Tek sorumluluk |
|---|---|---|
| `src/veri_kalitesi/scoring/postgresql_repository.py` | `PostgreSQLScoreRepository`, table metadata/mappers | Skor, publication, configuration ve partial-policy PostgreSQL persistence; query; lock/idempotency; audit stage |
| `src/veri_kalitesi/scoring/publication.py` | `ScorePublicationService`, `ScorePublicationCommand`, `ScoreReproductionResult` | Tam skor setini üretme, publication invariant'ı, publish/supersede ve reproduction doğrulaması |
| `src/veri_kalitesi/scoring/query.py` | `ScoreQueryService`, filter/page/detail DTO'ları | ActorContext rol+scope filtreli liste, detay, rule history ve comparison |
| `src/veri_kalitesi/scoring/jobs.py` | `ScorePublicationJobCommand`, `PostgreSQLScoreJobEnqueuer` | Execution completion → durable `SCORE_PUBLICATION` job ve job → publication service adapter'ı |

Bu dosyalar yeni hesap motoru, event bus veya generic unit-of-work framework'ü
değildir. PostgreSQL repository, mevcut `transactional_session` ve
`PostgreSQLTransactionalAudit` desenini kullanır.

### 4.3 Dayanıklı production tetikleme yolu

Skor hesaplaması yalnız API çağrısı veya proses-içi callback ile tetiklenmez:

1. `executions/postgresql_repository.py:complete_success` official execution
   result'larını yazdığı transaction içinde session-aware
   `PostgreSQLScoreJobEnqueuer` çağırır.
2. Enqueuer mevcut `PostgreSQLJobQueueRepository.enqueue(..., session=session)`
   yoluyla `SCORE_PUBLICATION` job'ı ekler. Idempotency key execution ID'den
   deterministik üretilir; veri-minimum payload `execution_id`, kanonik `period`
   ve enqueue anında sabitlenen `configuration_version` taşır.
3. Execution result veya job enqueue başarısızsa aynı transaction rollback olur;
   “execution tamamlandı ama skor işi kayboldu” penceresi bırakılmaz.
4. `ScorePublicationJobHandler` persisted execution/result/rule/source/config
   kayıtlarını okuyup `ScorePublicationService.publish_execution` çağırır.
5. Score set, contribution graph, publication state ve audit outbox kısa tek
   PostgreSQL transaction'ında yazılır.
6. Retry/restart aynı execution job'ını görür; aynı input digest mevcut yayını
   döndürür, farklı digest conflict üretir.

Gerekli mevcut dosya değişiklikleri:

| Dosya | Sembol | Değişiklik |
|---|---|---|
| `src/veri_kalitesi/executions/postgresql_repository.py` | constructor, `complete_success` | Constructor'a yalnız PG yolunda session-aware score-job enqueuer; result ve job enqueue atomikliği; genel execution contract'ı değişmez |
| `src/veri_kalitesi/jobs/handlers.py` | yeni `ScorePublicationJobHandler` | `execution_id` payload validation ve command çağrısı |
| `src/veri_kalitesi/jobs/composition.py` | `create_persistent_job_runtime` | Opsiyonel score command verilince handler map'e `SCORE_PUBLICATION` ekleme |
| `src/veri_kalitesi/jobs/production.py` | `create_production_worker`, mevcut `ProductionWorkerProviders` | Mevcut provider kümesine score publisher actor-context provider'ı ekleme; PG scoring/config repositories, publication service ve durable enqueuer wiring |
| `src/veri_kalitesi/jobs/settings.py` | `PersistentJobSettings` | Score/audit/actor policy sürümleri ve service actor ID fail-fast doğrulaması |

`PersistentExecutionCommandAdapter` içine fire-and-forget score callback eklenmez.
Mevcut queue tablosu ve lease/retry/dead-letter mekanizması yeniden kullanılır.
`api/composition.py:PhaseBProviders` değiştirilmez. Dış sistemden gelen score
publisher actor context'i mevcut `ProductionWorkerProviders` içinde worker/Phase C
girdisidir; yeni bir provider abstraction'ı eklenmez.
`create_production_worker(..., providers=...)` production DS-06 yolunda bu alan
verilmediyse fail-fast olur. API query/config servisleri ise somut PostgreSQL
repository'leriyle doğrudan API composition root'unda kurulur.

### 4.4 Publication ve reproduction transaction'ı

`PostgreSQLScoreRepository.publish_score_set` tek session içinde:

1. period için advisory/row lock alır;
2. aynı execution/idempotency kaydını kontrol eder;
3. tam score set invariant'ını ve resmî eligibility'yi doğrular;
4. score satırlarını ve contribution graph'larını immutable yazar;
5. önceki current publication'ı `SUPERSEDED` yapar;
6. yeni publication'ı `PUBLISHED` yapar ve score'lara bağlar;
7. `RULE_SCORE_CALCULATED`, `SCORE_AGGREGATED` ve tek `SCORE_PUBLISHED` olayını
   outbox'a stage eder.

Herhangi bir insert/update/audit stage hatasında tamamı rollback olur.
`publish_pending()` repository transaction'ı kapandıktan sonra çağrılır.

Reproduction mevcut publication'ı değiştirmez. Saklanan rule digest, config,
counts, weights ve component graph ile saf hesap yeniden çalıştırılır; değer,
status, level ve graph birebir karşılaştırılır. Sonuç
`SCORE_REPRODUCTION_VERIFIED` olarak ayrı kısa transaction'da audit edilir.

### 4.5 Production API composition

| Dosya | Sembol | Değişiklik |
|---|---|---|
| `src/veri_kalitesi/api/settings.py` | `ApplicationSettings` | `scoring_configuration_version`; boş/uyumsuz sürüm fail-fast. Reproduction mevcut `actor_policy_version` ve `ActorContext.privileged` kullanır |
| `src/veri_kalitesi/api/composition.py` | `CURRENT_MIGRATION_HEAD`, `REQUIRED_TABLES`, `create_application` | PG score repo/query/reproduction ve gerçek `DashboardQueryService` wiring; `app.state.score_*` görünürlüğü |
| `src/veri_kalitesi/api/production.py` | `create_production_app` | Dashboard service dışarıdan verilmezse unavailable bırakmak yerine gerçek PG scoring composition kullanma |
| `src/veri_kalitesi/api/development.py` | `create_development_app` ve score seed çevresi | Mevcut SQLite adapter ile skor endpoint'leri; yalnız açık development sentetik origin |
| `src/veri_kalitesi/dashboard/service.py` | `DashboardQueryService.get_overview`, `_read_score_tree` hata sınırı | SQLite'a özel exception catch yerine PG repository teknik hatasını güvenli `DashboardQueryError`'a çevirme; scope/filtre mantığı değişmez |
| `scripts/seed_database.py` | scoring seed bölümü | Açık sürümlü active config ve bağımsız oracle'lı score live-test corpus'u; published score doğrudan seed edilmez |

`dashboard_service` test override'ı gerekiyorsa açık test parametresi olarak
kalabilir; production default'u `UnavailableDashboardService` olamaz.

## 5. Endpoint envanteri

### 5.1 Yeni endpoint'ler

| Endpoint | HTTP ve sözleşme |
|---|---|
| `/api/v1/scores` | `GET`; `scope_type`, `scope_id`, `period_start`, `period_end`, `limit`, cursor; yalnız actor kapsamındaki published/resmî skorlar |
| `/api/v1/scores/rules/{rule_version_id}` | `GET`; rule→dataset→source zincirini backend'de çözüp yetkili geçmişi döndürür |
| `/api/v1/scores/comparison` | `GET`; `current_score_id`, `previous_score_id`; iki skor için ayrı scope kontrolü ve `compare_scores` sonucu |
| `/api/v1/scores/{quality_score_id}` | `GET`; score/status, publication, measurement, policy/digest, component graph ve reproduction availability |
| `/api/v1/scores/{quality_score_id}/reproduction` | `POST`; CSRF + trusted/süresi geçmemiş USER + okuma scope'u + `ActorContext.privileged=true`; saklanan kanıtı doğrular, kaydı değiştirmez |

Static `/rules/...` ve `/comparison` route'ları dinamik `/{quality_score_id}`
route'undan önce tanımlanır. Ham `calculation_details`, secret, sample değer veya
connection bilgisi response'a verilmez; bounded DTO kullanılır.

### 5.2 Değişecek API dosyaları

| Dosya | Sembol | Değişiklik |
|---|---|---|
| `src/veri_kalitesi/api/models.py` | yeni score list/detail/comparison/reproduction response modelleri | Decimal, enum, publication, graph ve available-actions projection'ları |
| `src/veri_kalitesi/api/app.py` | `create_dashboard_api`; yeni `ScoreQueryService` ve `ScoreReproductionService` portları/routes/error handlers | İnce HTTP adapter, actor aktarımı, no-store, 400/401/403/404/409/422/503 mapping |
| `src/veri_kalitesi/scoring/errors.py` | query/publication/reproduction hata sınıfları | Güvenli category ve correlation mapping |

Mevcut `GET /api/v1/dashboard/summary` endpoint'i değişmez. Onu besleyen reader
production'da PostgreSQL olur. Dashboard frontend'inin doğrudan `/scores`
çağırması önerilmez; mevcut dashboard DTO/filtre sözleşmesi korunur.

## 6. Frontend ekran ve çağrı envanteri

### 6.1 Yeni Skorlar bölümü

| Yeni dosya | Ekran/sorumluluk |
|---|---|
| `frontend/src/scores/model.ts` | API DTO doğrulama, filtre/list/detail/comparison view-model'leri; null score ≠ zero |
| `frontend/src/scores/api.ts` | `fetchScores`, `fetchScore`, `fetchRuleScores`, `compareScores`, `verifyScoreReproduction`; credentials/CSRF/safe error mapping |
| `frontend/src/scores/ScoresPage.tsx` | Dönem ve kapsam filtreli published skor listesi; empty/error/unauthorized durumları |
| `frontend/src/scores/ScoreDetailPage.tsx` | Score status, measurement, policy/digest ve katkı grafiği; backend `available_actions` ile gösterilen privileged reproduction aksiyonu |
| `frontend/src/scores/ScoreComparisonPage.tsx` | İki skor/dönem seçimi, comparable/not-comparable/unknown sonucu ve alan farkları |

### 6.2 Değişecek mevcut frontend dosyaları

| Dosya | Değişiklik |
|---|---|
| `frontend/src/App.tsx` | Lazy score sayfaları; `/scores`, `/scores/:scoreId`, `/scores/comparison` route ve gerçek API loading/error state'leri |
| `frontend/src/components/AppShell.tsx` | ANALİZ grubuna **Skorlar** linki; production'da koşulsuz “Sentetik görünüm/SENTETİK VERİ” etiketi göstermeme |
| `frontend/src/components/ScoreContributionPanel.tsx` | Değişmez veya yalnız yeni score detail DTO adapter'ına bağlanır; ikinci contribution component yazılmaz |
| `frontend/src/components/FieldScoreComparison.tsx` | Mevcut karşılaştırma sunumu yeniden kullanılır; business logic eklenmez |
| `frontend/src/dashboard/model.ts` | Production origin'de yalnız gerçek PG observation; score status/publication notlarının DTO'dan gösterimi; sentetik sabitler yalnız dev/story/test |

`dashboard/api.ts:fetchDashboardSummary` ve `/api/v1/dashboard/summary` çağrısı
korunur. API hatasında `syntheticDashboardViewModel` başarılı production verisi
olarak render edilmez; mevcut `DashboardRoute` error state davranışı test edilir.

## 7. Permission, scope ve audit

### 7.1 Backend permission sözleşmesi

DS-06 yeni `score.read`, `score.reproduce` veya `score.publish` action'ı, rolü ya
da `ScoreAccessPolicy` modeli tanımlamaz. Okuma endpoint'leri mevcut
`PolicyAuthorizationService.authorize_dashboard` trusted, expiry ve
policy-version kapısını; ardından mevcut source/dataset/enterprise scope
çözümlemesini kullanır. `ScoreQueryService` nesne hiyerarşisini backend'de
çözer ve yalnız yetkili skorları döndürür.

Kural skorunda `rule_version_id → quality_rule → dataset → data_source`;
dataset skorunda dataset→source; source skorunda exact source; enterprise skorunda
`can_view_enterprise` repository'den doğrulanır. Request'teki `scope_id` veya
frontend action yetkinin yerine geçmez. Yetkisiz erişim existence oracle
oluşturmaz.

Reproduction aynı okuma kontrolüne ek olarak `ActorContext.privileged is True`
koşulunu gerektirir. Actor trusted değilse, context süresi geçmişse, policy
version uyuşmuyorsa, scope dışındaysa veya `privileged=false` ise backend 403
döndürür. POST ayrıca mevcut CSRF kontrolünden geçer. `available_actions`
yalnız bu backend kararının projection'ıdır; frontend kendi başına yetki vermez.

Yayın kullanıcı endpoint'i değildir. Worker, production composition root'un
verdiği trusted ve süresi geçmemiş SERVICE `ActorContext` ile çalışır; execution'ın
persisted dataset/source scope'u publication service içinde yeniden doğrulanır.

### 7.2 Audit olayları

| Olay | Aynı transaction'daki kayıt |
|---|---|
| `RULE_SCORE_CALCULATED` | Rule-level `quality_scores` + graph |
| `SCORE_AGGREGATED` | Dataset/dimension/source/enterprise score + graph |
| `SCORE_PUBLISHED` | Yeni publication + önceki supersede + tüm score bağları |
| `SCORE_REPRODUCTION_VERIFIED` | Immutable verification sonucu; yayın değişmez |
| Mevcut `PARTIAL_SCORE_POLICY_*` | Policy create/decision/withdraw + PG outbox |
| Mevcut scoring configuration approval olayları | Configuration/approval state + PG outbox |

Audit summary'leri ham calculation JSON, rule definition, sample veya field value
taşımaz; yalnız ID, enum, sayım, sürüm ve digest içerir.

## 8. Test envanteri

`docs/testing/AGENTS.md` gereği yeni testler FR/UC/AC kimlikleri taşır; kalite
başarısızlığı, `NO_DATA`, teknik hata ve yetki reddi ayrı beklenen sonuçlardır.

### 8.1 Değişecek backend testleri

| Dosya | Eklenecek/doğrulanacak senaryo |
|---|---|
| `tests/unit/test_scoring.py` | Batch score-set determinizmi; persisted eligibility; digest/config stamps; official/provisional partial; ineligible result için mevcut `NOT_CALCULATED` + null score; score yokluğu ≠ zero |
| `tests/unit/test_partial_score_policies.py` | Repository protocol parity; PG lifecycle semantics; maker-checker/scope ve outbox rollback |
| `tests/unit/test_score_contributions.py` | Publication/policy/digest graph alanları; reproduction equality; non-comparable version sınırları |
| `tests/unit/test_dashboard.py` | PG reader-compatible protocol; yalnız published/resmî source/enterprise; forbidden scope ve no-data |
| `tests/unit/test_dashboard_api.py` | Production origin, null score, publication/status projection ve no-store |
| `tests/unit/test_persistent_job_handlers.py` | `SCORE_PUBLICATION` payload, success/retry/permanent failure/cancellation |
| `tests/unit/test_persistent_job_worker.py` | Score handler registration, lease/restart/idempotency/dead-letter |
| `tests/unit/test_audit.py` | Yeni score olaylarında yalnız izinli ID/enum/sayım/sürüm/digest alanları; hassas calculation payload redaksiyonu |
| `tests/integration/test_postgresql_score_contributions.py` | Existing graph immutable/audit testi; quality-score FK ve shared transaction |
| `tests/integration/test_application_composition.py` | PG score/config/policy repositories, real dashboard service, app.state, head 19/preflight |

### 8.2 Yeni backend testleri

| Yeni dosya | Amaç |
|---|---|
| `tests/unit/test_score_publication.py` | Tam set kapısı; ineligible/partial/no-data reddi; supersede state-machine; reproduction mismatch; audit payload minimization |
| `tests/unit/test_score_query.py` | Mevcut trusted/expiry/policy-version kapısı ve rule/dataset/source/enterprise scope; list/detail/history/comparison; existence leak yok |
| `tests/unit/test_score_api.py` | Beş endpoint contract'ı; CSRF; reproduction için `privileged` true/false; 401/403/404/409/422/503; available actions; null score |
| `tests/unit/test_score_jobs.py` | Deterministik job payload/idempotency ve command adapter |
| `tests/integration/test_postgresql_score_migration.py` | 18→19 upgrade; tablo/kolon/FK/check/index/partial unique ve graph FK |
| `tests/integration/test_postgresql_score_persistence.py` | Score/config/partial-policy persistence; concurrency; retry conflict; audit rollback; restart |
| `tests/integration/test_ds06_score_publication.py` | Gerçek PG execution result → durable job → worker → publish/supersede → API/dashboard → audit → reproduction |

`test_ds06_score_publication.py` yalnız `SQLiteScoreRepository`, fake score
repository veya doğrudan `ScorePublicationService` çağrısıyla geçerse production
kanıtı sayılmaz. En az bir supported template rule gerçek source PostgreSQL'de
`failed_count>0`; ayrı senaryo `NO_DATA` veya ineligible result üretmelidir.

### 8.3 Frontend testleri

| Dosya | Senaryo |
|---|---|
| `frontend/src/scores/model.test.ts` (yeni) | Decimal/null, mevcut score status/publication ve comparison mapping; invalid response fail-closed |
| `frontend/src/scores/api.test.ts` (yeni) | Beş çağrı, query encoding, CSRF ve safe error mapping |
| `frontend/src/scores/ScoresPage.test.tsx` (yeni) | Loading/empty/data/error/unauthorized, filters ve accessible list |
| `frontend/src/scores/ScoreDetailPage.test.tsx` (yeni) | Graph/versions, backend available-actions projection'ı, reproduction pending/success/mismatch |
| `frontend/src/scores/ScoreComparisonPage.test.tsx` (yeni) | Comparable/not-comparable/unknown ve null delta |
| `frontend/src/dashboard/DashboardPage.test.tsx` | Production API skoru, empty/error'da sentetik fallback olmaması |
| `frontend/src/components/AppShell.test.tsx` | Skorlar navigation ve production sentetik etiketinin kaldırılması |
| `frontend/e2e/scores.spec.ts` (yeni) | Mock contract ile list→detail→comparison→reproduction interaction; production kanıtı değil |
| `frontend/e2e/scores-live.spec.ts` (yeni) | Gerçek compose/PG/worker üzerinde yayın görünürlüğü ve reproduction smoke |

### 8.4 Korunacak testler

- `tests/unit/test_scoring.py` içindeki mevcut kural/dataset/dimension/
  source/enterprise, config approval ve restart testleri.
- `tests/unit/test_partial_score_policies.py` içindeki resmî/provizyonel
  karar ve lifecycle testleri.
- `tests/unit/test_dashboard.py`, `test_dashboard_filters.py` ve
  `test_dashboard_api.py` mevcut scope/trend/filter testleri.
- `tests/integration/test_postgresql_score_contributions.py` immutable
  graph ve transactional audit testi.
- `tests/integration/test_postgresql_execution_persistence.py` result ve
  eligibility kalıcılık testleri.
- `tests/integration/test_postgresql_job_queue.py` queue/lease/retry/
  dead-letter testleri.
- Mevcut dashboard/frontend contribution, comparison ve trend testleri.

### 8.5 Çalıştırılacak test grupları

- Scoring, partial policy, contribution, score publication/query/API/job unit
  testleri.
- Dashboard unit/API/filter regresyon testleri.
- PostgreSQL revision 19 migration, score persistence/contribution,
  execution/job queue ve application composition entegrasyon testleri.
- Gerçek `DATA_QUALITY_POSTGRES_TEST_URL` ile DS-06 production-chain testi.
- `cd frontend && npm test -- --run`
- `cd frontend && npm run build`
- `cd frontend && npx playwright test e2e/scores.spec.ts`
- Development compose üzerinde `e2e/scores-live.spec.ts`.

## 9. Kesin dosya değişikliği özeti

### 9.1 Yeni

- `alembic/versions/20260806_19_score_publication.py`
- `src/veri_kalitesi/scoring/{postgresql_repository,publication,query,jobs}.py`
- `frontend/src/scores/{model,api,ScoresPage,ScoreDetailPage,ScoreComparisonPage}.ts(x)`
- §8.2 ve §8.3'teki yeni test dosyaları

### 9.2 Değişecek

- `src/veri_kalitesi/scoring/{models,service,repository,partial_score_policies,postgresql_contributions,contributions,__init__}.py`
- `src/veri_kalitesi/executions/postgresql_repository.py`
- `src/veri_kalitesi/jobs/{handlers,composition,production,settings}.py`
- `src/veri_kalitesi/api/{models,app,settings,composition,production,development}.py`
- `src/veri_kalitesi/audit/policies.py`
- `src/veri_kalitesi/dashboard/service.py` — yalnız PG teknik hata mapping'i
- `frontend/src/{App.tsx,components/AppShell.tsx,dashboard/model.ts}`
- `scripts/seed_database.py`
- `infra/development/compose.yaml` — score worker/policy sürüm ayarları; production fake provider yok
- §8.1 ve §8.3'teki mevcut test dosyaları

### 9.3 Değişmeyecek

- Migration 01–18
- `scoring/trends.py` hesap motoru
- `dashboard/service.py:DashboardQueryService` ana sorgu/authorization ve filtre
  davranışı; yalnız PG teknik hata mapping'i ve reader composition'ı değişir
- `dashboard/api.ts` ve `/api/v1/dashboard/summary` çağrı sözleşmesi
- `jobs/worker.py` ve `jobs/postgresql_repository.py` queue çekirdeği
- `rule_execution_results` ve `rule_executions` tablo kolonları
- Issue state-machine, notification delivery, report generation ve risk rating
- Production'da SQLite/in-memory/fake score, config, policy veya executor fallback'i
- Gerçek domain mapping olmadan `DOMAIN` score üretimi

## 10. Kesin uygulama sırası

1. Revision 19 migration ve runtime table metadata parity testleri.
2. `ScorePublication`/policy modelleri ve repository protocol'leri.
3. `PostgreSQLScoreRepository`: config/partial-policy/score/publication read-write.
4. `ScoringService` saf batch hesap refactor'ı, persisted eligibility ve digest.
5. Graph staging ile score/publication/audit tek transaction'ı.
6. Publication idempotency, concurrency, supersede ve rollback testleri.
7. Reproduction doğrulaması ve testleri.
8. `SCORE_PUBLICATION` durable enqueue/handler ve execution completion atomikliği.
9. Production worker settings/providers/composition ve restart/dead-letter testleri.
10. Scope-aware `ScoreQueryService`, API modelleri ve beş endpoint.
11. API production composition'da gerçek PG dashboard reader ve preflight/head 19.
12. Backend permission/scope/API/application-chain testleri.
13. Frontend score model/API ve liste/detay/karşılaştırma ekranları.
14. App route/navigation ve dashboard production-origin düzeltmeleri.
15. Seed/live corpus; frontend unit/build/mock E2E.
16. Gerçek compose live E2E: negative result, publication, supersede, dashboard,
    unauthorized scope, audit ve reproduction.

Migration ve PG repository testleri geçmeden worker wiring'e; publication
atomikliği geçmeden API'ye; backend scope testleri geçmeden frontend'e; gerçek
negative-result production yolu geçmeden live kabul testine ilerlenmez.

## 11. Envanter kararı

**GO — DS-06 dosya envanteri uygulamaya hazırdır.** Bölüm 2.3'teki A–G
kararları dondurulmuştur: yeni `NOT_QUALIFIED` değeri ve ayrı qualification
kolonu yoktur; veto bütünüyle kapsam dışıdır; okuma mevcut scope yetkisini,
reproduction ise buna ek olarak `ActorContext.privileged` kapısını kullanır;
configuration/approval PostgreSQL'e taşınır; score provider mevcut
`ProductionWorkerProviders` içinde Phase C worker composition sınırında yer alır.

Uygulamanın normal giriş kapıları şunlardır:

1. Revision 19, scoring configuration/approval ve partial-policy tablolarını
   kapsamalı; production preflight aktif ve beklenen sürümde config bulamazsa
   fail-fast olmalıdır.
2. `ScoringService` içindeki seviye başına anlık persistence, tam batch
   publication öncesinde saf hesap sınırına ayrıştırılmalıdır.
3. Execution completion ile `SCORE_PUBLICATION` job enqueue aynı PostgreSQL
   transaction'ında olmalıdır; proses-içi callback kabul edilmez.
4. `api/composition.py:PhaseBProviders` değiştirilmemeli; mevcut worker
   `ProductionWorkerProviders` içindeki score publisher Phase C girdisi
   production'da zorunlu olmalıdır.
5. DOMAIN seviyesi için gerçek business-domain mapping yoktur. Bu dilimde fake
   domain skoru üretilmemeli; mevcut RULE/DATASET/DIMENSION/SOURCE/ENTERPRISE
   zinciri açıkça teslim edilmelidir.

Bu kapılardan biri SQLite production fallback'i, doğrudan frontend scope filtresi,
audit dışı transaction, yalnız yüzde 100 başarılı fixture veya sentetik dashboard
ile geçilirse dilim **NO-GO** olur.

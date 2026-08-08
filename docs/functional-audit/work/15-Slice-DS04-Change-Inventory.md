---
type: functional-audit-work
stage: "15 — DS-04 Değişiklik Envanteri"
scope: slice-ds04-change-inventory
inputs:
  - 14-Fourth-Slice-Decision.md
  - 13-Slice-DS03-Change-Inventory.md
  - 07-Implementation-Waves.md
  - ../04-Functional-Gap-Inventory.md
  - ../13-Implementation-Roadmap.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-05
---

# 15 — DS-04 Değişiklik Envanteri

> Seçilen dördüncü dilim: **DS-04 — Katalog ve metadata keşfi (GAP-004)**.
> Bu belge değişecek tablo, kolon, servis, endpoint, ekran ve testleri gerçek
> repository yolları ve sembolleriyle belirler. Uygulama veya kaynak kod
> değişikliği içermez.

---

## 1. Envanter özeti

| Katman | Karar |
|---|---|
| Yeni migration | `alembic/versions/20260805_17_catalog_metadata_discovery.py` |
| Yeni tablolar | `discovery_scopes`, `metadata_diffs` |
| Genişleyecek tablolar | `metadata_discovery_results`, `datasets`, `data_fields` |
| Yeniden kullanılacak tablolar | `data_sources`, `background_jobs`, `workers`, `audit_outbox`, `audit_events` |
| Yeni queue tablosu | Yok; DS-03 `background_jobs` kullanılır |
| Yeni connector ailesi | Yok; mevcut `ConnectorRegistry`, `PostgreSQLConnector` ve `CSVConnector` kullanılır |
| Ana backend değişikliği | Synchronous tam-snapshot replace yolunu kalıcı request → worker → candidate diff → güvenli apply zincirine dönüştürmek |
| Yeni endpoint | Dokuz katalog/keşif endpoint'i |
| Yeni frontend alanı | `/catalog`, dataset detayı ve field detayı; kaynak ekranında keşif aksiyonu |
| Production kanıtı | Gerçek PostgreSQL migration + API + persistent worker + gerçek PostgreSQL metadata driver + katalog API/UI |

Mevcut Alembic head `20260805_16`'dır. Roadmap'teki “Migration 16” DS-03
tarafından kullanılmıştır; DS-04 revision 17 olarak ilerler.

## 2. Tablolar ve kolonlar

### 2.1 Yeni `discovery_scopes` tablosu

**Sahip migration:**
`alembic/versions/20260805_17_catalog_metadata_discovery.py`

| Kolon | Tip / kısıt | Amaç |
|---|---|---|
| `data_source_id` | `String(36)`, PK, FK → `data_sources` | Her kaynak için tek etkin keşif kapsamı |
| `include_patterns` | JSON, not null | İzin verilen namespace/nesne glob örüntüleri |
| `exclude_patterns` | JSON, not null | Hariç tutulan namespace/nesne glob örüntüleri |
| `page_size` | integer, `1..10000` | Connector sayfalama limiti |
| `max_objects` | integer, `1..100000` | Tek keşifte güvenli üst sınır |
| `timeout_seconds` | integer, `1..3600` | Toplam metadata keşif sınırı |
| `policy_version` | `String(100)`, not null | Kapsam politikasının sürümü |
| `updated_by_actor_id` | `String(128)`, not null | Son güvenilir kullanıcı aktörü |
| `updated_at` | timestamptz, not null | Son güncelleme |
| `version` | integer, not null, `>= 1` | Optimistic concurrency |

Yeni scope-history tablosu açılmaz. Sürüm numarası concurrency içindir; önceki
değerler transactional audit olayında tutulur. Pattern'ler raw SQL değildir;
kanonik glob sözleşmesi olarak doğrulanıp connector'a güvenli parametreler halinde
aktarılır.

### 2.2 Yeni `metadata_diffs` tablosu

| Kolon | Tip / kısıt | Amaç |
|---|---|---|
| `metadata_diff_id` | `String(36)`, PK | Kalıcı fark kimliği |
| `discovery_id` | bigint, unique FK → `metadata_discovery_results` | Farkı üreten keşif |
| `data_source_id` | `String(36)`, FK → `data_sources` | Scope sorgusu ve indeks |
| `added_objects` | JSON, not null | Stable ID ve güvenli metadata taşıyan eklemeler |
| `changed_objects` | JSON, not null | Eski/yeni metadata imzaları |
| `removed_objects` | JSON, not null | Yalnız tam keşifte kanıtlanan kaldırmalar |
| `status` | string check | `PENDING`, `APPLIED` |
| `requires_rule_review` | boolean, not null | DS-13 tarafından tüketilecek sinyal; bu dilim kural state'i değiştirmez |
| `created_at` | timestamptz, not null | Fark üretim zamanı |
| `applied_at` | timestamptz, nullable | Uzlaştırma zamanı |
| `applied_by_actor_id` | `String(128)`, nullable | Farkı uygulayan kullanıcı |
| `version` | integer, not null, `>= 1` | Apply yarışını önleyen optimistic guard |

İndeksler: `(data_source_id, status, created_at)` ve unique `discovery_id`.
`schema_changes` tablosu açılmaz; resmî şema değişikliği/karar kaydı DS-13'tür.
Candidate metadata ayrı staging tablolarına bölünmez; tam ekleme/değişiklik
payload'ı veri-minimum kurallı diff JSON'ında tutulur. Örnek veri/satır içeriği bu
JSON'a giremez.

### 2.3 `metadata_discovery_results` değişiklikleri

Mevcut tablo `20260724_03_data_source_baseline.py` tarafından oluşturulmuştur ve
`succeeded`, `duration_ms`, `scanned_object_count`, `error_class`, `message`,
`changes` ve `discovered_at` kolonlarıyla senkron terminal sonucu temsil eder.
Bu kolonların hiçbiri drop edilmez. Async/partial yaşam döngüsü için migration 03
değiştirilmeden şu kolonlar eklenir:

| Kolon/kısıt | Değişiklik |
|---|---|
| `status` | `QUEUED`, `RUNNING`, `SUCCESS`, `PARTIAL`, `TECHNICAL_ERROR`, `CANCELLED` check'i |
| `job_id` | nullable unique FK → `background_jobs`; legacy satırlar nedeniyle nullable |
| `requested_by_actor_id` | nullable `String(128)`; yeni satırlarda zorunlu servis kuralı |
| `correlation_id` | nullable `String(128)`; request/job/audit zinciri |
| `scope_version` | nullable integer; kullanılan scope snapshot sürümü |
| `completed_scope` | JSON, not null, default boş nesne; yalnız tamamlanan kapsam |
| `partial_reason_code` | `String(100)`, nullable; yalnız `PARTIAL` |
| `started_at` | timestamptz, nullable |
| `finished_at` | timestamptz, nullable |
| `version` | integer, not null, default `1`, `>= 1` |
| `succeeded` | legacy compatibility için nullable yapılır; state-machine kaynağı artık `status` |
| `changes` | drop edilmez; legacy immutable özet olarak kalır, yeni authoritative fark `metadata_diffs` olur |

Mevcut kolonların yeni yaşam döngüsündeki kesin rolleri şöyledir:

| Mevcut kolon | Korunacak rol |
|---|---|
| `discovered_at` | Discovery request/satır oluşturma zamanı; `started_at` veya `finished_at` yerine kullanılmaz ve transition'larda yeniden yazılmaz |
| `duration_ms` | Yalnız terminal durumda `started_at`–`finished_at` süresinin geriye uyumlu sayısal karşılığı; queued/running durumda `0` |
| `scanned_object_count` | Terminal sonuçta gerçekten tamamlanan kapsam içinde taranan nesne sayısı; talep edilen toplam sayı değildir |
| `error_class` | `TECHNICAL_ERROR`/`PARTIAL` için veri-minimum teknik sınıf; ham connector mesajı veya secret taşımaz |
| `message` | Kullanıcıya gösterilebilir güvenli terminal özet; state-machine veya hata sınıfı kaynağı değildir |
| `succeeded` | Legacy projection: `SUCCESS → true`, diğer terminal durumlar → `false`, terminal öncesi `NULL`; authoritative kaynak `status` |
| `changes` | Legacy immutable fark özeti; yeni discovery'lerde authoritative kayıt `metadata_diffs.diff_payload` |

Eski satırlar `succeeded = true → SUCCESS`, `false → TECHNICAL_ERROR` olarak
backfill edilir. Eski `changes` verisi yeni bir uygulanabilir fark gibi sunulmaz;
tarihsel veri olarak korunur.

### 2.4 `datasets` değişiklikleri

| Yeni kolon | Tip / kısıt | Amaç |
|---|---|---|
| `status` | `ACTIVE` / `INACTIVE`, not null, default `ACTIVE` | Silmeden katalog yaşam döngüsü |
| `first_seen_discovery_id` | nullable FK → `metadata_discovery_results` | İlk gözlem kanıtı |
| `last_seen_discovery_id` | nullable FK → `metadata_discovery_results` | Son tam/kısmi gözlem |
| `updated_at` | timestamptz, not null | Katalog değişim zamanı |
| `version` | integer, not null, default `1`, `>= 1` | Fark uygulama concurrency guard'ı |

Mevcut natural-key unique constraint
`(data_source_id, namespace, name)` korunur. Yeniden görülen pasif dataset yeni ID
açmaz; aynı satır ve stable `dataset_id` tekrar aktive edilir.

Mevcut `ck_datasets_dataset_type` ayrıca düzeltilir. Domain modeli
`data_sources/models.py:DatasetType` içinde `TABLE`, `VIEW`, `FILE_SHEET` ve
`API_COLLECTION` kullanırken migration 03/repository metadata'sı `FILE`, `API`,
`OTHER` beklemektedir. Revision 17:

- mevcut `FILE` değerini `FILE_SHEET`, `API` değerini `API_COLLECTION` yapar;
- mevcut `OTHER` satırı varsa anlam uydurmak yerine fail-fast preflight ile
  remediation ister;
- check constraint'i domain enum'uyla aynı dört değere çevirir;
- `data_source_tables()` metadata'sını aynı constraint ile günceller.

Bu düzeltme yapılmadan CSV discovery sonucu PostgreSQL'e güvenilir biçimde
yazılamaz.

### 2.5 `data_fields` değişiklikleri

| Yeni kolon | Tip / kısıt | Amaç |
|---|---|---|
| `status` | `ACTIVE` / `INACTIVE`, not null, default `ACTIVE` | Silmeden alan yaşam döngüsü |
| `first_seen_discovery_id` | nullable FK → `metadata_discovery_results` | İlk gözlem kanıtı |
| `last_seen_discovery_id` | nullable FK → `metadata_discovery_results` | Son gözlem |
| `updated_at` | timestamptz, not null | Metadata değişim zamanı |
| `version` | integer, not null, default `1`, `>= 1` | Optimistic guard |

Mevcut `(dataset_id, name)` unique constraint, classification ve sensitivity
kolonları korunur. Metadata yeniden keşfi kullanıcı/politika tarafından verilmiş
classification değerini sıfırlamaz.

### 2.6 Değişmeyecek tablolar

- `data_sources`: mevcut status/revision/source scope kaynağıdır; kolon eklenmez.
- `background_jobs`: `job_type = METADATA_DISCOVERY` ve güvenli payload
  `{discovery_id, source_ids}` ile yeniden kullanılır; DDL değişmez.
- `workers`: handler listesinde yeni job type ilan edilir; DDL değişmez.
- `audit_outbox`, `audit_events`: mevcut transactional audit yolu kullanılır.
- `quality_rules`, `rule_versions`: DS-04 hiçbir kural durumunu değiştirmez.
- `data_profiles`, `profile_comparisons`: DS-08 kapsamıdır.

### 2.7 Migration sırası

1. `discovery_scopes` oluşturulur.
2. `metadata_discovery_results` yeni nullable/default-safe kolonlarla genişletilir.
3. Legacy discovery status/version/completed-scope backfill'i yapılır.
4. `metadata_diffs` oluşturulur.
5. Legacy dataset type değerleri dönüştürülür; çözümlenemeyen `OTHER` için
   migration fail-fast çıkar ve dataset-type check domain enum'uyla eşitlenir.
   Aynı adımda
   `data_sources/postgresql_repository.py:data_source_tables()` içindeki runtime
   `ck_ds_dataset_type` metadata constraint'i de `TABLE`, `VIEW`, `FILE_SHEET`,
   `API_COLLECTION` değerlerine güncellenir; migration DDL'i ile runtime metadata
   farklı bırakılamaz.
6. `datasets` ve `data_fields` lifecycle kolonları eklenir; mevcut kayıtlar
   `ACTIVE`, `version = 1` olarak backfill edilir.
7. Check, FK ve query indeksleri eklenir.
8. `api/composition.py:CURRENT_MIGRATION_HEAD` `20260805_17` yapılır;
   `REQUIRED_TABLES` kümesine `metadata_discovery_results`, `discovery_scopes` ve
   `metadata_diffs` eklenir.

Migration 01–16 dosyaları değiştirilmez.

## 3. Backend servis ve repository envanteri

### 3.1 Kesin değişecek dosyalar

| Dosya | Sembol | Planlanan değişiklik |
|---|---|---|
| `src/veri_kalitesi/data_sources/models.py` | `Dataset`, `DataField`, `MetadataDiscoveryResult`; yeni discovery/diff status ve scope modelleri | Lifecycle, partial sonucu, stable reconciliation ve optimistic version alanları |
| `src/veri_kalitesi/data_sources/contracts.py` | `DataSourceRepository` | Discovery request/state, scope, diff ve reconcile metotları; `replace_metadata` authoritative production yazma yolu olmaktan çıkar |
| `src/veri_kalitesi/data_sources/postgresql_repository.py` | `DataSourceTables`, `data_source_tables`, `ck_ds_dataset_type`, row mapper'lar | Migration 17 kolonları; runtime dataset-type check'ini `TABLE`, `VIEW`, `FILE_SHEET`, `API_COLLECTION` ile eşitleme; yeni modeller |
| aynı | yeni discovery/scope/diff/reconcile metotları | Her transition'da expected version; apply sırasında dataset/field upsert/passivation + diff + audit tek transaction |
| `src/veri_kalitesi/data_sources/repository.py` | SQLite test/prototype karşılığı | Domain contract değişikliğini karşılar; production composition yolu olmaz |
| `src/veri_kalitesi/data_sources/service.py` | `DataSourceService.discover_metadata`, `_diff_metadata`, `_persist_metadata_result` | Uzun connector çalışmasını request yolundan ayır; persisted discovery ID/scope ile çalıştır; partial removals engelle; doğrudan tam sil-yaz yapma |
| `src/veri_kalitesi/data_sources/connectors.py` | `DataSourceConnector.discover_metadata`, `CSVConnector` | Tuple yerine completeness, completed scope ve partial reason taşıyan typed sonuç; cancel/progress aktarımı |
| `src/veri_kalitesi/data_sources/postgresql.py` | `PostgreSQLDriver`, `PostgreSQLConnector.discover_metadata` | Yeni typed sonucu, cancellation ve progress'i driver'a aktar |
| `src/veri_kalitesi/data_sources/postgresql_driver.py` | `SQLAlchemyPostgreSQLDriver.discover_metadata` | Şu anki `DriverConnectionError("...not configured")` yerine gerçek read-only PostgreSQL katalog sorgusu, scope, pagination, timeout ve hata sınıflandırması |
| `src/veri_kalitesi/data_sources/query.py` | `DataSourceQueryService._available_actions` | Yalnız ACTIVE + doğru rol/scope için `DISCOVER_METADATA`; frontend için güvenlik kararı üretir |
| `src/veri_kalitesi/api/data_source_commands.py` | `DataSourceCommandAdapter` | Discovery action projection/error mapping; connector'ı doğrudan çağırmaz |
| `src/veri_kalitesi/api/models.py` | yeni discovery/scope/diff/catalog request-response modelleri | API validation ve veri-minimum response sözleşmesi |
| `src/veri_kalitesi/api/app.py` | yeni metadata/catalog service protocol'leri ve route'lar | İnce HTTP adapter; ActorContext'i backend servise geçirir |
| `src/veri_kalitesi/api/composition.py` | head/preflight, `create_application`, `app.state.*` | Aynı schema/session/audit/job queue ile metadata command ve catalog query servislerini bağla |
| `src/veri_kalitesi/api/settings.py` | `ApplicationSettings` | Katalog/discovery policy version; boş olamaz/fail-fast environment alanı |
| `src/veri_kalitesi/jobs/handlers.py` | yeni `CancellableMetadataDiscoveryCommand`, `MetadataDiscoveryJobHandler` | `discovery_id` payload doğrulama; timeout/cancel/progress aktarımı |
| `src/veri_kalitesi/jobs/composition.py` | `create_persistent_job_runtime` | Opsiyonel gerçek metadata command verildiğinde `METADATA_DISCOVERY` handler kaydet; supported types handler map'inden türemeye devam eder |
| `src/veri_kalitesi/jobs/production.py` | `ProductionWorkerProviders`, `create_production_worker` | API ile aynı PG catalog repository ve gerçek connector üzerinden metadata command oluştur; injected secret resolver ve trusted metadata service-context provider'ını gerçekten kullan |
| `src/veri_kalitesi/jobs/__init__.py`, `src/veri_kalitesi/data_sources/__init__.py` | exports | Yeni modeller/servis/handler export'ları |

### 3.2 Yeni, dar kapsamlı application servisleri

| Önerilen dosya | Sembol | Sorumluluk |
|---|---|---|
| `src/veri_kalitesi/api/postgresql_metadata.py` | `PostgreSQLMetadataCommandService` | Request + job + audit atomikliği; scope update; diff apply; trusted user ActorContext/role/source kontrolü |
| `src/veri_kalitesi/data_sources/catalog.py` | `CatalogQueryService` | Scope-safe dataset, field, discovery ve diff okuma projeksiyonları |
| `src/veri_kalitesi/jobs/metadata_command.py` | `PersistentMetadataDiscoveryCommandAdapter` | Worker portunu `DataSourceService` execution metoduna bağlar; state-machine kuralını handler'a taşımaz |

Bu üç sınır genel bir repository/service framework değildir. HTTP transaction,
connector execution ve salt-okunur katalog sorgusunu birbirinden ayırmak için
gereklidir. İkinci data-source domain servisi veya yeni queue abstraction'ı
oluşturulmaz.

### 3.3 Production PostgreSQL discovery driver

`SQLAlchemyPostgreSQLDriver.discover_metadata` mevcut production engelidir: metod
doğrudan “metadata driver is not configured” hatası verir. DS-04 içinde gerçek
implementation zorunludur.

Driver yalnız sistem kataloglarını/read-only view'ları sorgular; aşağıdakileri
döndürür:

- izinli schema/table/view adları;
- alan adı, ordinal sıra, native veri tipi ve nullable bilgisi;
- güvenli ve mevcutsa tahmini satır sayısı;
- tamamlanan scope, toplam taranan nesne ve completeness sonucu.

`max_objects` veya toplam zaman sınırı bazı nesneler okunduktan sonra aşılırsa
başarılı boş sonuç değil `PARTIAL` üretilir. Hiç güvenilir metadata alınamayan
connection/authentication/TLS/permission/driver hataları `TECHNICAL_ERROR` olur.
Raw include/exclude pattern SQL metnine eklenmez; parametrelenmiş katalog sorgusu
ve doğrulanmış glob eşlemesi kullanılır.

Glob sözleşmesi `data_sources/service.py:validate_discovery_pattern(pattern: str)
-> str` ile tek yerde tanımlanır. Fonksiyon whitespace'i normalize edilmiş
canonical pattern döndürür; boş/yalnız-whitespace değer, kontrol karakteri, boş
segment, `..`, `/` veya `\\`, SQL comment/statement ayırıcıları ve desteklenmeyen
glob yapıları reddedilir. Desteklenen sözdizimi yalnız noktayla ayrılmış
`namespace` veya `namespace.object` segmentlerinde literal karakterler ile `*`
ve `?` wildcard'larıdır; canonical pattern uzunluğu `1..255` karakterdir. Include
ve exclude girdileri scope
yazılmadan önce bu fonksiyondan geçer, driver aynı doğrulamayı savunmacı olarak
tekrarlar ve pattern hiçbir durumda SQL identifier/metin parçası yapılmaz.

Geçersiz pattern mevcut `data_sources.errors.ValidationError` ailesinde
`DISCOVERY_SCOPE_PATTERN_INVALID` API hata koduna çevrilir ve HTTP 422 üretir.
Connector çağrılmaz; scope version, discovery/job kaydı ve başarı audit olayı
oluşturulmaz. Normalize edilmiş duplicate pattern'ler tekilleştirilir; aynı nesne
hem include hem exclude ile eşleşirse exclude önceliklidir.

### 3.4 Discovery transaction sınırları

Connector ağı/veri kaynağı çağrısı boyunca açık database transaction tutulmaz.
Kesin sınırlar:

1. API request: discovery `QUEUED` + background job + request audit tek transaction.
2. Worker claim: job claim/lease + `JOB_CLAIMED` DS-03 transaction'ı.
3. Execution start: discovery `RUNNING` + started audit tek kısa transaction.
4. Connector çağrısı: transaction dışı, cancellation/progress kontrollü.
5. Completion: discovery terminal durumu + `metadata_diffs` + completion audit
   tek transaction; mevcut katalog henüz silinmez.
6. İlk bootstrap veya yetkili apply: dataset/field upsert/passivation + diff
   `APPLIED` + apply audit tek transaction.

Audit stage başarısızsa ilgili state/catalog transaction'ı rollback olur. Audit
publish gecikmesi business transaction'ı fake başarıya çeviremez.

### 3.5 Yeniden kullanılacak, yeniden yazılmayacak yapı

- `DataSourceService` içindeki source-state, secret, connector error mapping,
  classification normalization ve stable natural-key eşleme mantığı.
- `_diff_metadata` algoritmasının ADDED/CHANGED/REMOVED temeli; yalnız completeness
  girdisi ve persisted diff çıktısı eklenir.
- `PostgreSQLDataSourceRepository.list_datasets`, `list_data_fields`, `get_dataset`,
  `get_data_field`, `list_metadata_snapshot`.
- `ConnectorRegistry`, `PostgreSQLConnector`, `CSVConnector`.
- DS-03 `PostgreSQLJobQueueRepository`, `PersistentJobWorker`, progress/lease,
  retry/timeout/dead-letter ve worker registry.
- `PostgreSQLTransactionalAudit` ve outbox publish yolu.
- `PolicyAuthorizationService` source/dataset scope kararı.

## 4. Permission, scope ve audit

### 4.1 Policy değişiklikleri

`data_sources/models.py:DataSourceCommandPolicy` mevcut komut kapısı olarak
genişletilir; ayrı IAM tablosu veya frontend permission motoru açılmaz:

| Policy alanı | Önerilen roller | Kullanım |
|---|---|---|
| `metadata_discovery_roles` | `TECHNICAL_DATA_STEWARD`, `DATA_STEWARD` | Keşif talebi |
| `metadata_scope_configurer_roles` | `TECHNICAL_DATA_STEWARD` | Include/exclude ve limitler |
| `metadata_diff_applier_roles` | `DATA_OWNER`, `DATA_STEWARD` | Fark uzlaştırma |
| `metadata_worker_roles` | `METADATA_DISCOVERY_WORKER` | Worker execution service context |

User komutları trusted `ActorContext`, doğru policy version, user actor type,
non-privileged workflow, rol ve `permitted_source_ids` gerektirir. Worker komutu
ayrı trusted `ActorType.SERVICE` ve worker rolü gerektirir. Request body'deki
`data_source_id` veya dataset listesi actor scope'unun yerine geçmez.

`jobs/production.py:ProductionWorkerProviders` bu nedenle en az gerçek
`secret_resolver` ve `metadata_service_actor_context_provider` bağımlılıklarını
zorunlu alır; `create_production_worker(settings, providers)` bunları kullanır.
Entrypoint kendi başına user/service context uydurmaz ve bir `Protocol` sınıfını
runtime resolver gibi instantiate etmez.

Provider sözleşmesi
`metadata_service_actor_context_provider(data_source_id, correlation_id) ->
ActorContext` olarak sabitlenir. Dönüş değeri trusted ve süresi geçmemiş olmalı;
`actor_type == ActorType.SERVICE`, roller içinde tam olarak yetkilendirmede aranan
`METADATA_DISCOVERY_WORKER`, `permitted_source_ids` içinde hedef source ve
discovery policy version bulunmalıdır. Correlation ID persisted discovery/job
correlation değeriyle aynı olmalıdır. Bu şartlardan biri sağlanmazsa connector
çalışmadan authorization/fail-fast hatası üretilir.

Development composition bu context'i mevcut `identity.ActorContextIssuer` ile,
development worker kimliği ve yalnız hedef source scope'u için üretir. Testler de
aynı issuer üzerinden fixture provider enjekte eder; doğrudan `ActorContext`
dataclass'ı uydurmaz. Production'da provider dış identity/service-account
adapter'ından zorunlu olarak enjekte edilir; yoksa worker composition fail-fast
çıkar. Development/test kolaylığı production için header, fake resolver veya
geniş enterprise scope fallback'i oluşturmaz.

Catalog GET sorguları `can_view_enterprise` veya izinli source/dataset kümelerini
PostgreSQL sorgusuna taşır. Boş iki küme sıfır sonuçtur; “tüm katalog” anlamına
gelmez. Field detail önce parent dataset/source kapsamını doğrular.

### 4.2 Audit olayları

Repository'de mevcut olay adı `DATA_SOURCE_METADATA_DISCOVERED`'dır. Event
consumer/test kırmamak için başarı/partial completion olayı bu adla korunur;
yaşam döngüsü olayları aynı adlandırma ailesinde eklenir:

| Olay | Aktör | Aynı transaction'daki kayıt |
|---|---|---|
| `DATA_SOURCE_METADATA_DISCOVERY_REQUESTED` | USER | discovery `QUEUED` + job enqueue |
| `DATA_SOURCE_DISCOVERY_SCOPE_CHANGED` | USER | `discovery_scopes` version update |
| `DATA_SOURCE_METADATA_DISCOVERY_STARTED` | SERVICE | discovery `RUNNING` |
| `DATA_SOURCE_METADATA_DISCOVERED` | SERVICE | `SUCCESS/PARTIAL` terminal update + diff; `DIFF_COMPUTED` ile aynı transaction |
| `DATA_SOURCE_METADATA_DISCOVERY_FAILED` | SERVICE | `TECHNICAL_ERROR/CANCELLED` |
| `DATA_SOURCE_METADATA_DIFF_COMPUTED` | SERVICE | `metadata_diffs` insert; `DISCOVERED` ile aynı outbox transaction |
| `DATA_SOURCE_METADATA_DIFF_APPLIED` | USER | catalog reconcile + diff `APPLIED` |

`SUCCESS` veya `PARTIAL` completion'da discovery terminal update'i,
`metadata_diffs` insert'i ve hem `DATA_SOURCE_METADATA_DISCOVERED` hem
`DATA_SOURCE_METADATA_DIFF_COMPUTED` outbox kayıtları **aynı database
transaction'ında** stage edilir. Boş fark hesaplanmışsa da `DIFF_COMPUTED` sıfır
sayılı özetle yazılır. Bu kayıtlardan biri stage edilemezse terminal update ve
diff dahil transaction bütünüyle rollback olur. `TECHNICAL_ERROR`/`CANCELLED`
durumunda diff ve bu iki başarı olayı yazılmaz; yalnız failure olayı terminal
update ile aynı transaction'dadır. Outbox `publish_pending` çağrısı commit'ten
sonradır ve ikinci bir business-state transaction'ı değildir.

Job tarafındaki `JOB_ENQUEUED`, `JOB_CLAIMED`, progress, retry, timeout ve
dead-letter olayları DS-03 yolundan değişmeden üretilir. Secret, connection config,
örnek satır ve alan değerleri audit özetine girmez.

## 5. Endpoint envanteri

### 5.1 Yeni endpoint'ler

| Endpoint | HTTP | Servis / davranış |
|---|---|---|
| `/api/v1/data-sources/{data_source_id}/metadata-discoveries` | `POST`, 202 | İdempotency anahtarlı discovery/job request; ACTIVE + rol/scope |
| `/api/v1/data-sources/{data_source_id}/discovery-scope` | `PUT`, 200 | Include/exclude/limitler + expected version |
| `/api/v1/metadata-discoveries/{discovery_id}` | `GET`, 200 | Scope-safe status, progress, teknik sonuç ve correlation |
| `/api/v1/metadata-discoveries/{discovery_id}/diff` | `GET`, 200 | Veri-minimum added/changed/removed farkı |
| `/api/v1/metadata-diffs/{metadata_diff_id}/application` | `POST`, 200 | Expected version + reason code ile safe reconcile |
| `/api/v1/datasets` | `GET`, 200 | Yetkili dataset listesi; source/status/name filtreleri ve bounded limit |
| `/api/v1/datasets/{dataset_id}` | `GET`, 200 | Dataset detail ve son discovery kanıtı |
| `/api/v1/datasets/{dataset_id}/fields` | `GET`, 200 | Scope-safe aktif/pasif field listesi |
| `/api/v1/fields/{data_field_id}` | `GET`, 200 | Parent dataset/source scope doğrulanmış field detail |

State-changing endpoint'ler mevcut BFF/CSRF boundary'den geçer. GET response'ları
`Cache-Control: no-store` kullanır; development CSRF proof mevcut veri kaynağı GET
yoluyla veya katalog bootstrap GET'iyle alınır.

### 5.2 Mevcut endpoint değişikliği

`GET /api/v1/data-sources` response'undaki `available_actions` değerine yalnız
backend policy izin veriyorsa `DISCOVER_METADATA` eklenir. Başka mevcut data-source,
rule veya execution endpoint yolu değiştirilmez.

### 5.3 Açılmayacak endpoint'ler

- Profil request/cancel/baseline endpoint'leri: DS-08.
- Şema değişikliği accept/reject ve impact endpoint'leri: DS-13/DS-14.
- Classification approval, glossary ve ownership endpoint'leri: sonraki
  yönetişim dilimleri.
- Queue/dead-letter operasyon endpoint'leri: DS-11.

## 6. Frontend ekran ve çağrı envanteri

### 6.1 Yeni katalog dosyaları

| Önerilen dosya | Sorumluluk |
|---|---|
| `frontend/src/catalog/api.ts` | Dataset/field/discovery/diff GET'leri; scope/apply/start command'ları; mevcut CSRF deseni |
| `frontend/src/catalog/model.ts` | API contract, mapper, lifecycle/diff/action tipleri |
| `frontend/src/catalog/CatalogPage.tsx` | Yetkili dataset listesi, source/status/name filtreleri, loading/empty/error/unauthorized |
| `frontend/src/catalog/DatasetDetailPage.tsx` | Dataset metadata, alanlar, son keşif ve fark özeti |
| `frontend/src/catalog/FieldDetailPage.tsx` | Tip/nullability/sensitivity/classification; örnek değer yok |
| `frontend/src/catalog/DiscoveryStatusPanel.tsx` | QUEUED/RUNNING/progress/PARTIAL/technical result ve refresh/polling |
| `frontend/src/catalog/MetadataDiffPanel.tsx` | Added/changed/removed görünümü ve backend `available_actions` ile apply |
| `frontend/src/catalog/RuleTargetSelector.tsx` | Kural tipine göre dataset ve field seçimi; raw ID girişi değil |
| Aynı klasörde `*.test.ts(x)` ve `*.stories.tsx` | State/interaction/accessibility kanıtı |

### 6.2 Değişecek mevcut frontend dosyaları

| Dosya | Değişiklik |
|---|---|
| `frontend/src/components/AppShell.tsx` | “Katalog” navigasyonu |
| `frontend/src/App.tsx` | `/catalog`, `/catalog/datasets/:id`, `/catalog/fields/:id` route'ları; API state ve bounded polling |
| `frontend/src/dataSources/model.ts` | `DISCOVER_METADATA` action ve son discovery projection'ı |
| `frontend/src/dataSources/api.ts` | Start discovery çağrısı; mevcut CSRF/error mapping'i yeniden kullan |
| `frontend/src/dataSources/DataSourcesPage.tsx` | ACTIVE kaynak satırında backend izinli “Metadata keşfet” aksiyonu ve status linki |
| `frontend/src/rules/RulesPage.tsx` | Serbest `dataset_id` alanını katalog seçicisiyle değiştir; rule type'a göre field hedefleri |
| `frontend/src/rules/model.ts` | Formun seçilmiş dataset/field hedeflerini mevcut API payload'ına map etmesi |

Katalog ekranı `synthetic-development` fixture'larını yalnız açık development
story/`?state=` yolunda kullanabilir. Production API hatasında katalog veya kural
formu sentetik dataset/field başarı verisi göstermez.

## 7. Test envanteri

### 7.1 Değişecek backend testleri

| Dosya | Eklenecek/doğrulanacak senaryo |
|---|---|
| `tests/unit/test_data_sources.py` | Typed connector result; SUCCESS/PARTIAL/TECHNICAL_ERROR; stable ID; partial removal yasağı; classification korunması; canonical/invalid glob ve exclude precedence |
| `tests/unit/test_postgresql_data_source_repository.py` | Yeni table metadata, `ck_ds_dataset_type` dört domain değeri, row mapping ve reconcile SQL/state/version guard'ları |
| `tests/unit/test_data_source_commands.py` | Discovery/scope/apply rol ve source-scope negatifleri; idempotency/conflict/error mapping |
| `tests/unit/test_data_source_api.py` | Dokuz endpoint contract'ı; 202/200/401/403/404/409/422/5xx; CSRF |
| `tests/unit/test_persistent_job_handlers.py` | Metadata payload, timeout/cancel/progress ve error sınıflandırması |
| `tests/unit/test_persistent_job_worker.py` | `METADATA_DISCOVERY` handler lifecycle; retry/timeout/dead-letter; lease kaybında eski worker'ın completion yazamaması |
| `tests/integration/test_postgresql_data_source_persistence.py` | Scope/diff/discovery persistence; apply atomikliği; restart ve stable IDs |
| `tests/integration/test_postgresql_job_queue.py` | Metadata discovery enqueue/claim/audit ve idempotency |
| `tests/integration/test_application_composition.py` | API/worker aynı schema/session/audit/catalog repository ve gerçek handler wiring'i; production provider yoksa fail-fast; issuer tabanlı development/test SERVICE context'i |

Mevcut metadata/audit testleri korunur ve yeni state-machine'e uyarlanır:
`test_data_sources.py` içindeki discovery success, connection prerequisite,
technical timeout, audit rollback, rule-review sinyali ve inventory-ID survival
senaryoları kaldırılmaz.

### 7.2 Yeni backend testleri

| Önerilen dosya | Amaç |
|---|---|
| `tests/integration/test_postgresql_catalog_migration.py` | 16→17 upgrade, tüm legacy discovery kolonlarının korunması ve lifecycle backfill'i, FILE/API dönüşümü, OTHER fail-fast, DDL/runtime dataset-type check eşliği, FK/index ve existing catalog korunması |
| `tests/unit/test_catalog_query.py` | Source/dataset scope, empty scope, field parent scope ve response minimization |
| `tests/unit/test_postgresql_metadata_driver.py` | Catalog query, include/exclude, pagination, quoting, cancellation, timeout ve PARTIAL sonucu |
| `tests/integration/test_postgresql_metadata_discovery.py` | Gerçek PostgreSQL kaynak katalogundan dataset/field keşfi; secret/TLS/read-only boundary |
| `tests/integration/test_ds04_catalog_application.py` | API request → queue → worker → discovery/diff → apply → catalog GET + audit zinciri; DISCOVERED ve DIFF_COMPUTED aynı transaction/outbox atomikliği ve rollback testi |

Entegrasyon testindeki dış kaynak veritabanı kontrollü bir PostgreSQL fixture olabilir;
ancak application DB repository, queue, worker, transactional audit ve composition
fake ile değiştirilmez.

### 7.3 Frontend testleri

| Dosya | Senaryo |
|---|---|
| `frontend/src/catalog/api.test.ts` | Dokuz endpoint, CSRF, polling, error/problem mapping |
| `frontend/src/catalog/model.test.ts` | Discovery/diff/catalog mapper ve PARTIAL/status/action tipleri |
| `frontend/src/catalog/CatalogPage.test.tsx` | Scope-safe list, filtreler, tüm UI state'leri ve klavye erişimi |
| `frontend/src/catalog/DatasetDetailPage.test.tsx` | Field navigation, inactive işareti, hassas veri-minimum görünümü |
| `frontend/src/catalog/DiscoveryStatusPanel.test.tsx` | Progress, PARTIAL, technical failure ve polling stop koşulları |
| `frontend/src/catalog/MetadataDiffPanel.test.tsx` | Diff grupları, apply confirm, backend action yoksa buton yok |
| `frontend/src/catalog/RuleTargetSelector.test.tsx` | Dataset/field seçimi, rule type gereksinimleri ve raw ID fallback olmaması |
| `frontend/src/dataSources/DataSourcesPage.test.tsx` | DISCOVER_METADATA action ve mutation feedback |
| `frontend/src/rules/RulesPage.test.tsx` | Katalog seçicili create payload ve katalog hatasında fail-closed form |
| `frontend/src/components/AppShell.test.tsx` | Katalog navigasyonu |

### 7.4 E2E testleri

| Dosya | Rol |
|---|---|
| `frontend/e2e/catalog.spec.ts` | Mock'lu responsive/accessibility/UI-state regresyonu |
| `frontend/e2e/catalog-live.spec.ts` | Route interception olmadan gerçek API + PG + worker + source PostgreSQL smoke |
| `frontend/e2e/data-sources.spec.ts` | Yeni keşif action'ı için mevcut fixture güncellemesi |
| `frontend/e2e/rules.spec.ts` | Raw dataset ID yerine katalog selector akışı |

Canlı test: ACTIVE source → discovery request → worker progress → terminal sonuç →
catalog görünümü → rule target seçimi zincirini; ayrıca unauthorized source ve
PARTIAL no-removal senaryolarını doğrular. Mock'lu `catalog.spec.ts` production
kanıtı sayılmaz.

### 7.5 Çalıştırılacak test komutları

- `python3 -m pytest -q tests/unit/test_data_sources.py`
- `python3 -m pytest -q tests/unit/test_data_source_commands.py tests/unit/test_data_source_api.py`
- `python3 -m pytest -q tests/unit/test_catalog_query.py tests/unit/test_postgresql_metadata_driver.py`
- `python3 -m pytest -q tests/unit/test_persistent_job_handlers.py tests/unit/test_persistent_job_worker.py`
- PostgreSQL test URL ile migration, persistence, metadata discovery, job queue,
  composition ve DS-04 application integration testleri.
- `cd frontend && npm test -- --run`
- `cd frontend && npm run build`
- `cd frontend && npx playwright test e2e/catalog.spec.ts`
- Canlı compose profiliyle `npx playwright test e2e/catalog-live.spec.ts`.

## 8. Kesin dosya değişikliği özeti

### Değişecek

- `alembic/versions/20260805_17_catalog_metadata_discovery.py` (yeni)
- `src/veri_kalitesi/data_sources/{models,contracts,postgresql_repository,repository,service,connectors,postgresql,postgresql_driver,query,__init__}.py`
- `src/veri_kalitesi/data_sources/catalog.py` (yeni)
- `src/veri_kalitesi/api/{models,app,composition,settings,data_source_commands}.py`
- `src/veri_kalitesi/api/postgresql_metadata.py` (yeni)
- `src/veri_kalitesi/jobs/{handlers,composition,production,__init__}.py`
- `src/veri_kalitesi/jobs/metadata_command.py` (yeni)
- `frontend/src/catalog/*` (yeni)
- `frontend/src/{App.tsx,components/AppShell.tsx}`
- `frontend/src/dataSources/{api,model,DataSourcesPage}.ts(x)`
- `frontend/src/rules/{model,RulesPage}.ts(x)`
- §7'de listelenen backend/frontend/E2E testleri

### Değişmeyecek

- Migration 01–16 dosyaları
- Data-source activation maker-checker state-machine'i
- Execution/job queue DDL ve worker lease/progress çekirdeği
- Rule approval state-machine'i; DS-04 yalnız `requires_rule_review` sinyali üretir
- Profil/baseline, issue, score, schedule, lineage ve notification tabloları/ekranları
- Yeni message broker, search engine veya ayrı katalog veritabanı
- Production'da SQLite/in-memory/fake repository veya connector fallback'i

## 9. Uygulama sırası

1. Migration 17 ve migration/backfill testi.
2. Domain discovery/scope/diff/lifecycle modelleri ve repository metadata'sı.
3. PostgreSQL repository state transition ve safe reconcile metotları.
4. Typed connector result ve gerçek `SQLAlchemyPostgreSQLDriver.discover_metadata`.
5. `DataSourceService` worker execution refactor'ü; PARTIAL/removal invariant'ı.
6. Metadata job handler, command adapter ve production worker composition.
7. API request/scope/apply command servisi; catalog query servisi.
8. `api/app.py` modelleri/route'ları ve `create_application` production wiring'i.
9. Backend unit + PostgreSQL integration + application-chain testleri.
10. Catalog frontend model/API ve sayfaları.
11. DataSources discovery action ve Rules catalog selector bağlantısı.
12. Frontend unit/build/mock E2E.
13. Gerçek compose/live E2E ve audit zinciri doğrulaması.

Frontend, backend contract ve scope testleri geçmeden production smoke'a geçilmez.
Driver gerçeklenmeden fake connector ile composition başarıya zorlanmaz.

## 10. Envanter kararı

**GO — envanter uygulanabilir.** Mevcut PostgreSQL data-source repository,
connector registry, DS-03 persistent worker ve transactional audit yolu yeniden
kullanılabilir.

Uygulama öncesi doğrulamada bulunan beş eksik bu revizyonda kapatılmıştır:

- `metadata_discovery_results` içindeki yedi mevcut kolon korunmuş ve
  `discovered_at`/`started_at`/`finished_at` zaman rolleri ayrılmıştır.
- Migration DDL'i ile `postgresql_repository.py:data_source_tables()` runtime
  `ck_ds_dataset_type` constraint'inin birlikte değişeceği kesinleştirilmiştir.
- `validate_discovery_pattern` arayüzü, canonical glob sınırı, precedence ve 422
  hata sınıflandırması tanımlanmıştır.
- Worker context provider'ın `ActorContext`/`ActorType.SERVICE`/worker rolü/source
  scope sözleşmesi ile development, test ve production sağlama yolları
  tanımlanmıştır.
- `DATA_SOURCE_METADATA_DISCOVERED` ile
  `DATA_SOURCE_METADATA_DIFF_COMPUTED` olaylarının aynı completion/outbox
  transaction'ında yazılacağı kesinleştirilmiştir.

Uygulamadaki en yüksek risk `SQLAlchemyPostgreSQLDriver.discover_metadata`'nın şu
an somut olmamasıdır; bu bir external dependency değil, DS-04 içinde yazılması
gereken production adapter'dır. Driver yerine fake/no-op bağlanırsa, PARTIAL
sonuç full snapshot gibi uygulanırsa veya `replace_metadata` tam sil-yaz yolu
production'da bırakılırsa dilim **NO-GO** olur.

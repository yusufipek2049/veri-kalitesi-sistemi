---
type: functional-audit
stage: "04 — Fonksiyonel GAP Envanteri"
scope: gap-records
inputs:
  - 01-Current-Capabilities.md
  - 02-Target-Capability-Hierarchy.md
  - 03-End-to-End-Workflow-Audit.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-04
---

# 04 — Fonksiyonel GAP Envanteri

> Mevcut kabiliyetler (aşama 1), hedef kabiliyet modeli (aşama 2) ve uçtan uca
> akış denetimi (aşama 3) karşılaştırılarak üretilmiş **benzersiz** fonksiyonel
> GAP kayıtları. Her kayıt tek bir eksikliği tanımlar; aynı eksiklik farklı
> adlarla tekrarlanmaz.

---

## 1. Kapsam ve yöntem

### 1.1 Girdiler

| Girdi | Rol |
|---|---|
| [01-Current-Capabilities.md](01-Current-Capabilities.md) | Çift eksenli mevcut durum (kod zinciri / runtime erişilebilirliği) |
| [02-Target-Capability-Hierarchy.md](02-Target-Capability-Hierarchy.md) | 271 yaprak fonksiyonlu hedef referans modeli; yaprak kodları ve izin/audit adları buradan alınır |
| [03-End-to-End-Workflow-Audit.md](03-End-to-End-Workflow-Audit.md) | 13 denetlenmiş akış, kök nedenler (K1–K8) ve kaskad etkileri |

### 1.2 Benzersizlik kuralı

Bir GAP, **tek bir kök eksikliğe** bağlanır. Aynı kök eksiklik birden çok akışı
kırıyor olsa bile tek kayıtta tutulur; etkilenen akışlar kaydın içinde
listelenir. Bu kuralın uygulandığı birleştirmeler:

| Birleştirme | Gerekçe |
|---|---|
| Dört PostgreSQL repository'sinin bileşime bağlanmaması → **GAP-001** | Tek kök neden (K2); akış 1, 4, 7, 8'i aynı anda kırar |
| Kalite borcu (D10.C04) → **GAP-009** içinde ikincil hedef | Akış 9'un adım tablosunda istisna zincirinin parçasıdır (`BR-D10-011`) |
| Rapor dosyası imhası (D11.C04.W03.A01) → **GAP-011** içinde | Akış 13'ün adım tablosunda retention zincirine bağlıdır |
| Teşhis ve kanıtlı öneri (D09.C05) → **GAP-013** içinde | Aynı motor (`lineage/impact.py`) ve aynı kopukluk (yalnız testte çağrılma) |
| Veri sahibi atama (D01.C02.W01.A01) → **GAP-004** bağımlı etki, **GAP-026** yetenek kaydı | Atanacak varlık katalogla oluşur; yönetim yeteneği yönetişim GAP'ına aittir |

### 1.3 Bu oturumda yeniden doğrulanan kanıtlar

Aşama 1 ve 3'ün kritik iddiaları bu oturumda komutla yeniden üretildi:

| İddia | Doğrulama |
|---|---|
| `/api/v1/schedules` yok; 39 benzersiz `/api/v1/*` yolu içinde metadata keşfi, skor, istisna, sözleşme, bildirim endpoint'i yok | `grep -oE '"/api/v1/[^"]*"' api/app.py \| sort -u` |
| `create_persistent_job_runtime()` yalnız tanım ve export; çağıran yok | `grep -rn` → `jobs/composition.py:33`, `jobs/__init__.py` |
| `NotificationService` modülü dışında hiçbir dosyada geçmiyor | `grep -rln` → yalnız `notifications/service.py`, `notifications/__init__.py` |
| `create_issue` / `from_execution` benzeri otomatik sorun üretim yolu sıfır | `grep -rn` → boş |
| `DeadLetterReprocessService` yalnız `create_persistent_job_runtime()` içinde örnekleniyor | `grep -rn` → `jobs/composition.py` |
| `GET /api/v1/issues` var, `POST /api/v1/issues` (manuel sorun açma) yok | `app.py:1146` yalnız `@app.get` |
| `retention_policy_id` migration 03 ve 06'da var; `retention_policies` tablosu hiçbir migration'da yok | `grep` migrations |
| `users` / `roles` tablosu hiçbir migration'da yok | `grep` migrations |
| `Waiver`, `DataContract`, `RemediationAction`, `QualityDebt` sınıfları sıfır | `grep -rn "class …"` → boş |
| Zamanlama tetikleme sorgusu yazılı (`postgresql_scheduling.py:118`), çağıran yok | `grep -rn "next_run_at <= "` |
| Rapor zamanlama istemcileri `reports/api.ts:137,155,179`'da mevcut, `App.tsx:61`'de import ediliyor; `ReportsRoute` bağlamıyor | aşama 1 §3.15 ile tutarlı |
| `executions/api.ts` yalnız `fetchExecutions` export ediyor | `grep -n export` |
| Şema adı tutarsızlığı: `alembic.ini` → `dq`, `run_dev.py:11` → `data_quality` | aşama 1 §7.1 ile tutarlı; Q-13 açık |

### 1.4 Kapsam dışı bırakılanlar

Aşağıdaki mevcut-durum bulguları hedef hiyerarşide yaprak karşılığı olmadığı için
bu envantere GAP olarak alınmamıştır; aşama 1'deki kayıtları geçerlidir:

- KVKK olay müdahalesi (`incident_response/`) — hedef modelde yaprak yok (banka uyum kapsamı, 17.x belgeleri)
- Veri işleme envanteri yüzeyi — hedef yaprak yok; `D13` altında değil
- Ortam güvenliği konfigürasyonu — hedef yaprak yok
- Kurumsal lab adaptörleri — `EXTERNAL_DEPENDENCY`
- Secure SDLC — `NOT_APPLICABLE` (geliştirme zamanı aracı)

### 1.5 Kayıt şablonu

Her GAP sabit on dört alanla tanımlanır: hedef fonksiyon, mevcut durum,
repository kanıtı, eksik aşama, eksik UI, eksik API, eksik servis, eksik
tablo/kolon, yetki, audit, test, kullanıcı etkisi, iş etkisi, önerilen kabul
kriterleri. İzin kodları ve audit olay adları hedef modelden (aşama 2) alınır;
mevcut sistemde merkezi izin kataloğu olmadığı için bu kodlar **tanımlanmamış**
durumdadır (ayrıca bkz. GAP-022).

---

## 2. GAP özet tablosu

| Kod | Ad | Birincil hedef | Kök neden | Kırılan akışlar | Kod | RT |
|---|---|---|---|---|---|---|
| GAP-001 | Üretim bileşim kökü: PostgreSQL repository bağlantıları | `D09.C02` / `D06.C02` / `D03.C01` runtime'ı | K2 | 1, 3, 4, 7, 8 | ✅ | 🔴 |
| GAP-002 | Kalıcı iş worker süreci | `D07.C03.W02.A01` | K1 | 5, 6, 7, 10 | ✅ | 🔴 |
| GAP-003 | Zamanlayıcı daemon ve zamanlama yüzeyi | `D07.C02.W02.A01` | K5 | 5, 10 | ✅ | 🔴 |
| GAP-004 | Metadata keşfi ve katalog yüzeyi | `D04.C01.W01.A01` | K4 | 1, 2, 3, 4 | ✅ | ❌ |
| GAP-005 | Profil çalıştırma talebi ve baseline | `D05.C01.W01.A01` | yüzey yok | 3 | ✅ | ⚠️ |
| GAP-006 | Otomatik sorun üretimi, tekilleştirme, manuel sorun | `D09.C01.W01.A01` | K6 | 7, 8, 12 | ⚠️ | ❌ |
| GAP-007 | Bildirim olayı ve teslimat hattı | `D12.C01.W01.A01` | K3+K7 | 2, 6, 7, 10 | ⚠️ | ❌ |
| GAP-008 | Skor kalıcılığı, atomik yayım ve skor API'si | `D08.C03.W03.A01` | K7 | 7 | ⚠️ | ⚠️ |
| GAP-009 | İstisna/override ve kalite borcu | `D09.C04.W01.A01` | K7 | 9 | ❌ | ❌ |
| GAP-010 | Veri sözleşmesi yaşam döngüsü | `D10.C03.W01.A01` | K7 | 12 | ❌ | ❌ |
| GAP-011 | Saklama, imha, legal hold ve arşiv geri çağırma | `D13.C03.W01.A01` | K7+K8 | 13 | ⚠️ | ❌ |
| GAP-012 | Lineage olay alımı ve graf sorgulama | `D10.C01.W01.A01` | K7 | 11 | ⚠️ | ❌ |
| GAP-013 | Etki analizi, simülasyon, teşhis ve öneri yüzeyi | `D10.C02.W01.A01` | K8 | 2, 8, 11 | ⚠️ | ❌ |
| GAP-014 | Sorun SLA ve eskalasyon | `D09.C03.W01.A01` | K7 | 8 | ❌ | ❌ |
| GAP-015 | Rapor zamanlama UI bağlantısı ve tetikleme | `D11.C03.W03.A01` | bağlantı kopuk | 10 | ⚠️ | 🔴 |
| GAP-016 | Rapor asenkron üretimi ve gerçek içerik | `D11.C03.W02.A01` | K1+K2 | 10 | ⚠️ | ⚠️ |
| GAP-017 | Çalıştırma başlat/iptal komut yüzeyi | `D07.C01.W01.A01` (UI) | UI yok | 5 | ⚠️ | ❌ |
| GAP-018 | Kuyruk ve dead-letter operasyon yüzeyi | `D07.C04.W04.A02` | K8 | 6 | ⚠️ | ❌ |
| GAP-019 | Şema değişimi tespiti ve kararı | `D04.C04.W01.A01` | K7 | 2 | ❌ | ❌ |
| GAP-020 | Kural şablonları, bağımlılık ve çakışma tespiti | `D06.C01.W02.A01` | K7 | 4 | ❌ | ❌ |
| GAP-021 | Gölge (shadow) yürütme kullanıcı yolu | `D06.C05.W01.A01` | yüzey yok | 4 | ⚠️ | ❌ |
| GAP-022 | Kullanıcı, rol, izin yönetimi ve üretim oturumu | `D02.C01.W01.A01` | K7 | (D02 akışı) | ⚠️ | ⚠️ |
| GAP-023 | ServiceNow giden entegrasyon yüzeyi | `D12.C03.W01.A01` | K7+K8 | (D12 akışı) | ⚠️ | ❌ |
| GAP-024 | Operasyon: sağlık, olay, bakım | `D14.C01.W01.A01` | K7 | (D14 akışı) | ❌ | ❌ |
| GAP-025 | Sentetik veri uygulama yüzeyi ve kontrol doğrulama | `D15.C01.W01.A01` | K7+K8 | (D15 akışı) | ⚠️ | ❌ |
| GAP-026 | Yönetişim yapısı, iş sözlüğü ve politika yaşam döngüsü | `D01.C01.W01.A01` | K7 | (D01 akışı) | ❌ | ❌ |
| GAP-027 | Komut yolunda onay ve kapsam bypass'ı | `D03.C02.W01.A02` / `D06.C02.W01.A01` | K9 | 1, 4, 5 | ⚠️ | 🔴 |

> `Kod`/`RT` sütunları aşama 3 sözlüğüyle aynıdır: kod ekseninde ✅ tam,
> ⚠️ kısmi, ❌ yok; runtime'da 🔴 kopuk, ❌ yol yok.

> **`Kod` sütunu ne ölçer?** Yalnız hedef davranışı taşıyan servis/repository
> kodunun ve testinin varlığını. `✅` bir GAP'in kapandığı anlamına **gelmez**;
> GAP'i belirleyen `RT` sütunudur. GAP-003, GAP-004, GAP-005 ve GAP-006 için
> backend kodu ve kapsamlı birim testleri mevcuttur — eksik olan production
> bağlantısı ve kullanıcı yüzeyidir. Bu ayrım yapılmadığında "kod yok" ile
> "kullanıcı bunu yapamıyor" birbirine karışır; bu envanterin önceki
> sürümünde dört kayıtta bu karışıklık vardı.

---

## 3. GAP kayıtları

### GAP-001 — Üretim bileşim kökü: PostgreSQL repository bağlantıları

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D03.C01.W01.A01` kaynak kaydı, `D06.C02.W01.A01` kural oluşturma, `D09.C02.W01.A01` sorun atama ve tüm issue mutasyonları, `D08.C04` katkı grafiği okuma — hepsinin **runtime** bağımlılığı |
| Mevcut durum | Kod ekseninde zincirler `IMPLEMENTED`; runtime **karışık ve kendi içinde tutarsız** (aşama 1 §3.2, §3.5, §3.12). Tek çalıştırılabilir giriş `run_dev.py` → `create_development_app()`. Bu bileşim `MOCK_ONLY` değildir: execution ve job queue **yazma** yolu PostgreSQL'e bağlıdır; issue/kural/kaynak komutları bellek içi store'lara, skor ve audit okuma yolu SQLite'a bağlıdır |
| Repository kanıtı | `PostgreSQLIssueRepository`, `PostgreSQLRuleRepository`, `PostgreSQLDataSourceRepository`, `PostgreSQLContributionGraphRepository` yalnız `docs/testing/` içinde örnekleniyor (aşama 1 §2.3); buna karşılık `PostgreSQLExecutionRepository`, `PostgreSQLJobQueueRepository`, `PostgreSQLExecutionStartService`/`CancelService`, `PostgreSQLGovernanceProfileReader`, `PostgreSQLLineageEvidenceRepository` ve `PostgreSQLReportRepository` **bağlıdır** (`development.py:1300-1340`); `run_dev.py:14-18` `_FakePreparedRepo.store()` → `pass`; `development.py` `DevelopmentIssueStore`/`DevelopmentRuleStore`/`DevelopmentDataSourceStore` (bellek içi) |
| Yazma/okuma ayrışması | `execution_start_service` PG'ye yazar (`development.py:1334`), fakat `ExecutionQueryService` `DevelopmentExecutionReader()` okur (`development.py:1359`); reader modül düzeyindeki sabit `DEVELOPMENT_EXECUTIONS` demetini filtreler ve `session_factory`'ye hiç dokunmaz. Başlatılan çalıştırma kalıcı olur ama listede **hiçbir zaman** görünmez |
| Şema ayrışması (Q-13 kapanışı) | Açık soru değil, statik olarak doğrulanmış bir wiring hatasıdır. `run_dev.py:11,21,33` audit outbox'ı `data_quality` şemasına yönlendirir; `development.py:1332-1333` execution ve job repository'lerini `schema=` argümanı vermeden kurar, bunlar `persistence/database.py:15` gereği `dq` kullanır. Alembic de `dq`'yu hedefler (`alembic/env.py:24`). `DatabaseSettings.schema` session'a `search_path` olarak uygulanmaz — tablolar açıkça niteliklendirilir. Sonuç: aynı komut akışında iş verisi ile audit outbox **farklı şemalara** yazılır |
| Audit yayım hatası | `run_dev.py:_FakePreparedRepo` yalnız `store()` tanımlar; `PostgreSQLTransactionalAudit.publish_pending` ise `repository.append()` çağırır (`audit/postgresql_outbox.py:99`). Oluşan `AttributeError` satır 102'deki `except Exception` ile yutulur, satır `PENDING` bırakılır ve `last_error_code="AUDIT_REPOSITORY_UNAVAILABLE"` yazılır; metod exception fırlatmadan döner. Yerel geliştirmede hiçbir audit olayı değişmez deftere geçmez ve çağıran bunu **başarı** olarak görür |
| Eksik aşama | Composition root — kod doğru ve testli, çalıştırılabilir uygulamaya bağlanmıyor |
| Eksik UI | — (ekranlar mevcut; sahte veri üzerinde çalışıyor) |
| Eksik API | — (endpoint'ler mevcut) |
| Eksik servis | Üretim composition root (`create_development_app` karşılığı üretim bileşimi); execution yazma/okuma asimetrisini gideren gerçek `ExecutionReader` (liste şu an statik `DEVELOPMENT_EXECUTIONS`'tan okunuyor) |
| Eksik tablo/kolon | — (tablolar mevcut; şema adı tutarsızlığı `dq` vs `data_quality` yukarıda kapatıldı, çözülmesi gerekir) |
| Yetki | Okuma yolunda scope backend'de uygulanır (`PolicyAuthorizationService` kararı reader filtresine taşınır, boş kapsam testli). Komut yolunda tutarsızdır: data-source route'ları `ActorContext`'i mutation portuna hiç iletmez (`api/app.py:2017-2110`), `DevelopmentRuleStore.create_rule` yalnız bağlamın `None` olmadığına bakar. "Scope yalnız frontend'de" ifadesi yanlıştır; sorun okuma/komut ayrışmasıdır |
| Audit | Dev store'lar audit üretmiyor; `_FakePreparedRepo` no-op olduğundan `publish_pending()` olayları hiçbir kalıcı yere yazılmıyor; `AuditPage` sentetik olayları gösteriyor |
| Test | PG repository'leri yalnız skip-gated entegrasyon testlerinde (`DATA_QUALITY_POSTGRES_TEST_URL`); bileşim düzeyi smoke testi yok |
| Kullanıcı etkisi | Oluşturulan kaynak/kural/sorun süreç yeniden başlayınca kayboluyor; başlatılan çalıştırma kalıcı olsa bile listede görünmüyor; audit ekranı gerçek olayları göstermiyor |
| İş etkisi | "Kod ekseninde IMPLEMENTED" beş yetenek runtime'da sahte veriyle çalışıyor; maker-checker, görev ayrılığı ve audit zinciri pratikte doğrulanamıyor (K2 → 5 akış) |
| Önerilen kabul kriterleri | 1) Çalıştırılabilir bileşimde issue/kural/kaynak mutasyonları PostgreSQL'e yazıyor. 2) Süreç yeniden başlatıldığında kayıtlar korunuyor. 3) Mutasyonlar `audit_outbox`'a aynı transaction'da yazıyor ve `GET /api/v1/audit/events`'te görünüyor. 4) Başlatılan execution listeden okunabiliyor (yazma/okuma aynı kaynak). 5) Bileşim için skip-gated olmayan bir smoke testi var. 6) İş verisi ve audit outbox **tek bir şemada**; bileşimde şema argümanı açıkça geçiliyor. 7) `publish_pending` gerçek bir `PreparedAuditRepository` ile çalışıyor; protokol uyuşmazlığı sessizce yutulmuyor. |

---

### GAP-002 — Kalıcı iş worker süreci

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D07.C03.W02.A01` işi sahiplen (birincil); `D07.C03.W03.A01` heartbeat, `D07.C04.W01.A01` retry, `D07.C04.W02.A01` zaman aşımı, `D07.C04.W03.A01` lease geri alma, `D07.C04.W04.A01` dead-letter'a taşıma; bağımlı: `D11.C03.W02.A01` asenkron rapor |
| Mevcut durum | Kod ekseninde kuyruk çekirdeği geniş ölçüde yazılmış (`BACKEND_ONLY`), fakat **hedefe göre eksiksiz değil** (aşağıya bakınız); runtime `BROKEN` — enqueue çalışıyor, dequeue hiç çalışmıyor |
| Repository kanıtı | `create_persistent_job_runtime()` yalnız tanım/export; çağıran **hiç yoktur — testler dâhil** (testler `PersistentJobWorker`'ı elle kurar); `PersistentJobWorker.run_forever()` (`jobs/worker.py:76`) için entry point, konsol betiği veya daemon yok; `pyproject.toml`'da `[project.scripts]` tablosu yok |
| Durum modeli farkı | Hedefteki `AVAILABLE`/`CLAIMED`/`BLOCKED`/`DEAD_LETTERED` isimleri uygulanmamıştır. `jobs/models.py:20-27` `JobStatus` üyeleri: `QUEUED`, `RUNNING`, `CANCEL_REQUESTED`, `SUCCESS`, `TECHNICAL_ERROR`, `TIMEOUT`, `CANCELLED`. Dead-letter ayrı bir enum'dur (`DeadLetterStatus`: `OPEN`/`REPROCESSED`). `BLOCKED` (kota/pencere ertelemesi) karşılığı hiç yoktur |
| Claim audit boşluğu | `PostgreSQLJobQueueRepository.claim_next` (`jobs/postgresql_repository.py:271`) `FOR UPDATE SKIP LOCKED` (`:354`), lease (`:297,384`), kota ve optimistic version guard uygular; ancak imzasında audit/outbox parametresi **yoktur** ve gövdesi `audit_outbox.stage` çağırmaz. `QUEUED` satırı doğrudan `RUNNING` olur. Hedefin istediği "`CLAIMED` + `JOB_CLAIMED` + lease aynı transaction'da" garantisi bu nedenle **kodda mevcut değildir**; terminal geçişlerdeki outbox desteği bu boşluğu kapatmaz |
| Eksik aşama | `AVAILABLE` → `CLAIMED` → `RUNNING` → sonuç yazımı; retry/timeout/lease/dead-letter mantığının tümü runtime'da yürümüyor |
| Eksik UI | — (operatör yüzeyi ayrı kayıt: GAP-018) |
| Eksik API | — (iç süreç) |
| Eksik servis | Worker sürecini başlatan entry point (konsol betiği/supervisor tanımı); worker kayıt ve sağlık bildirimi (`D07.C04.W03.A02`) |
| Eksik tablo/kolon | `workers` (worker_id, hostname, capacity, supported_job_types, state, last_seen_at) |
| Yetki | Sistem aktörü |
| Audit | `JOB_LEASE_LOST` ve `JOB_DEAD_LETTERED` için outbox desteği vardır fakat runtime'da üretilmez; `JOB_CLAIMED` ise **kodda da yoktur** (yukarıdaki claim audit boşluğu) |
| Test | Birim + skip-gated entegrasyon mevcut; kuyruğa giren işin uçtan uca tamamlandığını gösteren smoke testi yok. `create_persistent_job_runtime` için hiç test yoktur |
| Kullanıcı etkisi | Manuel başlatılan çalıştırma ve kuyruğa alınan rapor üretimi sonsuza dek `QUEUED`/`AVAILABLE` kalıyor |
| İş etkisi | Asenkron ölçüm ve rapor üretimi tamamen duruk; `persistent_jobs` tek yönlü birikiyor; teknik hata toleransı hiç sınanmıyor (K1 → 4 akış) |
| Önerilen kabul kriterleri | 1) Kuyruğa yazılan `EXECUTION` işi tanımlı süre içinde sahiplenilip işleniyor ve `rule_execution_results`'a yazıyor. 2) Heartbeat lease'i uzatıyor; lease kaybında worker sonucu yazmıyor. 3) Deneme sınırı aşılan iş `dead_letter_records`'a düşüyor. 4) Düzgün kapatmada (drain) açık işler yarıda kesilmiyor. 5) Worker kimliği `workers` tablosunda izleniyor. 6) `claim_next` durum geçişini `JOB_CLAIMED` audit olayı ve lease yazımıyla **aynı transaction'da** yapıyor. 7) Kota/pencere ertelemesi için ayrı bir durum (`BLOCKED` karşılığı) operatöre görünür. |

---

### GAP-003 — Zamanlayıcı daemon ve zamanlama yüzeyi

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D07.C02.W02.A01` vadesi geleni tetikle (birincil); `D07.C02.W02.A02` kaçırılan çalışma, `D07.C02.W01.A01-A03` zamanlama yaşam döngüsü |
| Mevcut durum | Eksen A `BACKEND_ONLY`, Eksen B `MISSING` (aşama 1 §3.9). **Düzeltme:** bu kayıt daha önce `MODEL_ONLY` idi; zamanlama yalnız tablo + sorgu değildir, çalışan bir servis ve birim testleri vardır |
| Repository kanıtı | `schedules` tablosu migration 05'te (`next_run_at`, `is_active`). `executions/scheduling.py` içinde `ScheduleType` (`:63`), `Schedule` (`:71`), `SQLiteScheduleRepository` (`:92`) ve `SchedulingService` (`:218`) bulunur; servis `create_schedule` (`:234`), `trigger_due` (`:303`) ve `preview_runs` (`:343`) uygular — timezone doğrulaması, DST'de var olmayan yerel saatlerin elenmesi (`:383`) ve `idempotency_key=f"schedule:{id}:{scheduled_for}"` ile idempotent çalıştırma açma (`:311`) dâhil. `executions/postgresql_scheduling.py:64 PostgreSQLScheduleRepository` kalıcı okuma/yazma ve due sorgusu sağlar. Çağıran daemon/loop sıfırdır; `/api/v1/schedules` endpoint'i yoktur |
| Yarış koşulu boşluğu | `PostgreSQLScheduleRepository.due` (`:109-124`) düz bir `SELECT`'tir — `with_for_update(skip_locked=True)` veya claim kolonu **yoktur**. Aynı dosyadaki iş kuyruğu ve outbox yolları bunu kullanır, dolayısıyla eksiklik bilinçli bir tercih değildir. Çok zamanlayıcılı ortamda tek kazanan garantisi yalnız aşağı akıştaki idempotency anahtarına dayanır |
| Eksik aşama | Zamanlama tanımı → tetikleme → idempotency anahtarıyla çalıştırma açma → `next_run_at` ilerletme adımlarının **servis karşılığı vardır**; eksik olan bunları çağıran süreç ve kullanıcı yüzeyidir |
| Eksik UI | Zamanlamalar listesi/yeni/detay; son tetikleme görünürlüğü |
| Eksik API | `POST /schedules`, `POST /schedules/{id}/state`, `DELETE /schedules/{id}`; sürekli çalışan zamanlayıcı döngüsü |
| Eksik servis | Zamanlayıcı daemon (sürekli döngü ve bileşim bağı); kaçırılan çalışma politikası; PG due sorgusunda claim/lock protokolü. Sonraki çalışma anı hesabı ve zaman dilimi/yaz saati mantığı **mevcuttur** |
| Eksik tablo/kolon | `schedule_missed_runs` (schedule_id, missed_at, decision, policy_version); `schedules`'a `status`, `deleted_at`, `paused_until` |
| Yetki | `schedule.manage`, `schedule.trigger.execute` + dataset/kaynak kapsamı tanımlı değil; `SchedulingService` güvenilir bir `ActorContext` değil yalnız `actor_id` dizesi alır |
| Audit | `SCHEDULE_CREATED` üretilir ve outbox hatasında oluşturma geri alınır (testli); `SCHEDULE_STATE_CHANGED`, `SCHEDULE_DELETED`, `SCHEDULE_TRIGGERED`, `SCHEDULE_RUN_MISSED` yoktur |
| Test | **Düzeltme: "kanıt yok" yanlıştı.** `tests/unit/test_executions.py:643-1005` arasında 10 zamanlama testi vardır: `test_fr_037_uc_007_daily_schedule_persists_and_previews_next_five_runs` (`:643`), `test_fr_037_uc_007_due_schedule_creates_one_idempotent_scheduled_execution` (`:804`), `test_fr_077_bfr_aud_004_schedule_is_durably_buffered_on_audit_outage` (`:678`), `test_bfr_aud_004_outbox_failure_rolls_back_schedule_creation` (`:707`), `test_fr_037_uc_007_preview_skips_nonexistent_dst_local_time` (`:978`) ve geçersiz tanım/pasif kural senaryoları. Hepsi `SQLiteScheduleRepository` kullanır; `PostgreSQLScheduleRepository.due` için test yoktur, E2E yoktur |
| Kullanıcı etkisi | Aktive edilen hiçbir kural kendiliğinden çalışmıyor; ölçüm tamamen manuel tetiklemeye bağımlı |
| İş etkisi | Düzenli ölçüm olmadığı için skor zaman serisi birikmiyor; trend ve dönem karşılaştırması beslenemiyor; kaçırılan ölçüm telafisi yok (K5 → 2 akış) |
| Önerilen kabul kriterleri | 1) Tanımlanan zamanlama vadesinde tam bir kez çalıştırma açıyor (idempotency anahtarıyla). 2) `next_run_at` tetikleme sonrası ilerliyor. 3) Kaçırılan çalışma politikaya göre telafi/atlanıyor ve `SCHEDULE_RUN_MISSED` audit'leniyor. 4) Çok zamanlayıcılı ortamda aynı vade için tek kazanan var. 5) Duraklat/sürdür/sil işlemleri durum makinesi ve audit ile çalışıyor. |

---

### GAP-004 — Metadata keşfi ve katalog yüzeyi

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D04.C01.W01.A01` metadata keşfini başlat (birincil); `D04.C01.W01.A02` kapsam yapılandırma, `D04.C01.W02.A01-A02` fark hesaplama/uygulama, `D04.C02` dataset yaşam döngüsü, `D04.C03.W01/W02` alan ve sınıflandırma, `D04.C05` katalog arama/gezinme; bağımlı: `D01.C02.W01.A01` sahiplik atama (yönetim yeteneği GAP-026'da) |
| Mevcut durum | Eksen A `BACKEND_ONLY`, Eksen B `MISSING` (aşama 1 §3.3) |
| Repository kanıtı | **Düzeltme: keşif yalnız connector düzeyinde değildir.** `DataSourceService.discover_metadata` (`data_sources/service.py:763`) bağlantı durumunu kontrol eder, sır/connector kullanır, hataları sınıflandırır, metadata'yı normalize ederek kimlikleri korur, `_diff_metadata` (`service.py:1559`, modül düzeyi fonksiyon; `:881`'den çağrılır) ile fark üretir ve sonucu repository'ye yazar. Connector tanımları (`data_sources/postgresql.py:73,137,226`) bu orkestrasyonun altındaki katmandır. `metadata_discovery_results`, `datasets`, `data_fields` tabloları migration 03'tedir. Eksik olan: 44 endpoint'in hiçbiri keşif tetiklemiyor; katalog sayfası yok |
| Kalıcılık kanıtı | `PostgreSQLDataSourceRepository.replace_metadata` (`postgresql_repository.py:1145`) dataset/alan yazımı ile `audit_outbox.stage` çağrısını **tek transaction'da** yapar (`:1154-1198`) |
| Hedef davranış farkı | `replace_metadata` bir **anlık görüntü değiştirmedir**: mevcut dataset ve alanları silip yeniden ekler (`:1157-1196`), dolayısıyla surrogate ID'ler yenilenir. Hedefteki `PARTIAL` keşif ve "kısmi keşifte kaldırma çıkarımı yapma" kuralı bu yaklaşımla sağlanamaz — kısmi bir keşif, görünmeyen nesneleri silinmiş gibi ele alır |
| Eksik aşama | Keşif tetikleme → fark hesaplama → fark uygulama → dataset/alan kaydı oluşumu adımlarının **servis karşılığı vardır**; eksik olan production bağı, `PARTIAL` keşif semantiği, sınıflandırma ve ilk profil hedefidir |
| Eksik UI | Kaynak detayı metadata sekmesi; Katalog (arama, dataset/alan detayı, değişiklikler) |
| Eksik API | `POST /data-sources/{id}/metadata-discoveries`; `PUT /data-sources/{id}/discovery-scope`; `GET /metadata-discoveries/{id}/diff`; `POST /metadata-diffs/{id}/application`; dataset/alan listeleme uçları |
| Eksik servis | Keşfin kuyruğa bağlanması ve `RUNNING`/`SUCCESS`/`PARTIAL`/`TECHNICAL_ERROR` durum makinesi; `PARTIAL` keşifte kaldırma çıkarmayan fark uzlaştırma; katalog okuma servisi. Temel keşif ve fark hesabı orkestrasyonu **mevcuttur**, bileşime bağlı değildir (gerçek `DataSourceService` yerine `DevelopmentDataSourceStore` bağlıdır) |
| Eksik tablo/kolon | `discovery_scopes` (include/exclude örüntüleri, version); `metadata_diffs` (added, removed, changed, status) |
| Yetki | `catalog.discovery.execute`, `catalog.discovery.configure`, `catalog.diff.apply` + kaynak kapsamı — kod tanımlı değil |
| Audit | `METADATA_DISCOVERY_STARTED/COMPLETED`, `DISCOVERY_SCOPE_CHANGED`, `METADATA_DIFF_COMPUTED`, `METADATA_DIFF_APPLIED` |
| Test | **Düzeltme: "connector düzeyi kısmi" ifadesi eksikti.** `test_data_sources.py` içinde servis düzeyi keşif/fark testleri vardır: `test_fr_011_fr_015_uc_004_csv_metadata_discovery_persists_dataset_fields_and_audit` (`:843`), `test_fr_011_uc_004_metadata_discovery_requires_successful_connection` (`:876`), `test_fr_022_ac_025_postgresql_metadata_change_requires_rule_review` (`:892`), `test_fr_011_uc_004_metadata_timeout_is_classified_without_secret` (`:942`), outbox rollback testleri (`:523,548,573`) ve envanter sürümleme testi (`:1842`). Gerçekten eksik olanlar: HTTP yüzeyi testi, `PARTIAL` keşif davranışı ve E2E |
| Kullanıcı etkisi | Kullanıcı dataset/kolon göremiyor; kural yazarken kimlikleri elle giriyor, geçersiz referans ancak çalıştırma anında ortaya çıkıyor |
| İş etkisi | Onboarding akışı 4. adımda kopuyor; sahiplik/sınıflandırma/baseline kurulamıyor; sınıflandırma yokluğunda tüm alanlar hassas varsayılmalı (`BR-D04-006`) (K4 → 4 akış) |
| Önerilen kabul kriterleri | 1) `ACTIVE` kaynakta keşif tetiklenince `datasets`/`data_fields` doluyor ve katalog UI'da görünüyor. 2) Keşif hatası `TECHNICAL_ERROR` sınıfında kaydediliyor, kalite hatasıyla karışmıyor. 3) İkinci keşif fark üretiyor; `PARTIAL` keşifte kaldırma çıkarımı yapılmıyor. 4) Fark uygulaması etkilenen kuralları `REVIEW_REQUIRED` yapıyor ve kritik kuralda açık onay istiyor. 5) Tüm adımlar audit outbox'a yazıyor. |

---

### GAP-005 — Profil çalıştırma talebi ve baseline yönetimi

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D05.C01.W01.A01` profil çalıştırmasını talep et (birincil); `D05.C01.W01.A02` iptal; `D05.C03.W01.A01` baseline belirleme, `A02` geçersiz kılma |
| Mevcut durum | Eksen A `PARTIAL`, Eksen B `PARTIAL` (aşama 1 §3.4) — okuma yüzeyi eksiksiz, üretim yüzeyi yok |
| Repository kanıtı | 3 GET endpoint + `/profiling` sayfası mevcut; `POST /datasets/{id}/profiles` benzeri üretim ucu yok. **Düzeltme:** profil yürütücüsü vardır — `DataSourceService.run_profile` (`data_sources/service.py:901`) CSV/PostgreSQL profil yürütücülerini çağırır ve sonucu kalıcılaştırır; `ProfilePolicyResolver` ve `build_advanced_field_metrics` bu yolun parçasıdır. Eksik olan, bu servisi çağıran HTTP ucu ve kuyruk bağıdır. Baseline hâlâ örtüktür: `sorted_profiles[idx - 1]` (`data_sources/query.py:229-260`) |
| Eksik aşama | Profil talebi → politika çözümleme → iş → metrik kaydı; bilinçli baseline atama |
| Eksik UI | Dataset detayından profil çalıştırma ve iptal; baseline belirleme/geçersiz kılma |
| Eksik API | `POST /datasets/{id}/profiles` (idempotency); `POST /profiles/{id}/cancellation`; baseline uçları |
| Eksik servis | Profil talebinin kuyruğa bağlanması ve yürütme durum makinesi (GAP-002'ye bağlı); baseline servisi. Profil **yürütücüsünün kendisi mevcuttur** |
| Eksik tablo/kolon | `data_profiles`'a yürütme durum kolonları (`status`, `started_at`, `finished_at`, `cancelled_by`); `profile_baselines` veya baseline durum kolonları (`ACTIVE` → `SUPERSEDED`/`INVALIDATED`) |
| Yetki | `profile.execute`, `profile.cancel` + dataset kapsamı — kod tanımlı değil |
| Audit | `PROFILE_REQUESTED`, `PROFILE_CANCELLED`, baseline olayları |
| Test | Metrik hesaplama ve `run_profile` yürütme testleri var (`test_data_sources.py:968,1015,1117,1159,1175,1242,1313,1397,1464` ve profil outbox rollback testi `:573`); iptal, baseline atama ve E2E için test yok |
| Kullanıcı etkisi | Yeni snapshot üretilemiyor; drift hükmü ancak elle doldurulmuş veriyle anlam kazanıyor; "normal" tanımı kayan bir referansa göre ölçülüyor |
| İş etkisi | Kademeli bozulma görünmez kalıyor; meşru iş değişikliğinden sonra baseline geçersiz kılınamadığı için `BR-D05-008` (`NOT_QUALIFIED`) davranışı işlemiyor; akış 3 başlamıyor |
| Önerilen kabul kriterleri | 1) Profil talebi `data_profiles`'a `QUEUED` → `RUNNING` → `SUCCESS` akışıyla yazıyor. 2) Politika yoksa talep fail-closed reddediliyor. 3) Çalışan profil iptal edilebiliyor. 4) Baseline onaylanarak atanıyor ve sürümleniyor; drift baseline'a göre ölçülüyor. 5) Baseline geçersiz kılınıncaya kadar yeni ölçümler `NOT_QUALIFIED` işaretlenebiliyor. |

---

### GAP-006 — Otomatik sorun üretimi, tekilleştirme ve manuel sorun açma

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D09.C01.W01.A01` kalite ihlalinden sorun üret (birincil); `D09.C01.W01.A02` teknik hata, `D09.C01.W01.A03` sözleşme ihlali (GAP-010'a bağlı), `D09.C01.W02.A01-A02` tekilleştirme/yinelenme, `D09.C01.W03.A01` manuel sorun açma |
| Mevcut durum | Eksen A `BACKEND_ONLY`, Eksen B `MISSING`. **Düzeltme:** bu kayıt daha önce `MISSING`/`MISSING` idi. Üretici servis vardır; eksik olan onu çağıran köprüdür |
| Repository kanıtı | **Düzeltme: "sorun üretim servisi yok" yanlıştı.** `IssueService.create_for_trigger` (`issues/service.py:139`) güvenilir servis bağlamı ister (`:145-149`, varsayılan `ActorType.SERVICE`), atama çözer, `uuid5(namespace, digest(deduplication_key))` ile deterministik tekilleştirme uygular (`:165`), kapanmış sorun için `RECURRENCE` ilişkisi ve `DATA_QUALITY_ISSUE_REOPENED` audit'i üretir (`:194-260`). `PostgreSQLIssueRepository.add_or_increment` (`issues/postgresql_repository.py:234`) advisory lock + `SELECT … FOR UPDATE` ile issue/history/ilişki yazımını ve `audit_outbox.stage`'i tek transaction'da yapar (`:249-355`). Doğru olan alt iddia: bu servisi **çağıran production kodu yoktur** — `create_for_trigger` için repo genelinde yalnız tanım ve iki test çağrısı vardır. `POST /api/v1/issues` yok; `/api/v1/issues` yalnız `@app.get` (`app.py:1146`) |
| Uygunluk (eligibility) kapısı yok | `RuleExecutionResult.eligible_for_auto_issue` (`executions/models.py:168`) hesaplanır, kalıcılaştırılır (SQLite + PG) ve migration 12'de kolonu vardır; ancak `IssueTrigger` (`issues/models.py:72-79`) bu alanı **taşımaz** ve `create_for_trigger` onu doğrulamaz — `issues/` altında `eligible_for_auto_issue` hiç geçmez. Bu nedenle yalnız bir çağıran eklemek yetmez: `NOT_QUALIFIED`/teknik sonuçların kalite sorunu üretmesini engelleyecek güven sınırı sözleşmede tanımlı değildir |
| Eksik aşama | Sonuç → eşik/yeterlilik değerlendirme → **sorun üretimine köprü**; üretim, atama, tekilleştirme ve yinelenme adımlarının servis karşılığı mevcuttur |
| Eksik UI | Yeni sorun formu (kapsam, başlık, öncelik, benzer sorun önerisi); sorun-sürüm-sonuç bağı görünümü |
| Eksik API | `POST /api/v1/issues` (manuel); otomatik üretim iç servis |
| Eksik servis | Execution sonucundan `IssueTrigger` üreten adapter/çağıran; `eligible_for_auto_issue` bilgisini trigger sözleşmesine taşıyıp doğrulayan uygunluk kapısı. Üretim servisi, tekilleştirme anahtarı ve yinelenme sayacı **mevcuttur** |
| Eksik tablo/kolon | — (`issues` kolonları modellenmiş; üretici yok) |
| Yetki | Sistem aktörü; manuel açmada `issue.create` + kapsam — kod tanımlı değil |
| Audit | `ISSUE_CREATED`, `ISSUE_RECURRENCE_RECORDED` |
| Test | **Düzeltme:** üretici servisin testleri vardır — `test_issues.py` içinde oluşturma, tekilleştirme, yinelenme, atama ve audit testleri (ör. `test_fr_064_fr_065_ac_015_creates_assigned_issue_and_notification_within_five_minutes`), PG tarafında `test_postgresql_issue_mutations.py:53` ve `:327`. Test edilmeyen: execution → issue köprüsü, uygunluk kapısı ve E2E (bu davranışlar kodda da yok) |
| Kullanıcı etkisi | Kalite bozulması kimseye ulaşmıyor; sorun listesi yalnız seed veriden besleniyor; kullanıcı elle sorun açamıyor |
| İş etkisi | Sorun yaşam döngüsü (akış 8) eksiksiz ama beslenmiyor; yeniden açma mekanizması tetiklenemiyor; risk derecesi ve SLA zincirinin girişi yok (K6 → 4 akış) |
| Önerilen kabul kriterleri | 1) Eşiği aşan `QUALIFIED` başarısızlık `NEW` sorun üretiyor ve sahibe atanıyor. 2) Aynı anahtarla ikinci bozulma yeni sorun açmıyor, `occurrence_count` artırıyor (`BR-D09-003`). 3) `NOT_QUALIFIED` ölçümden kalite sorunu açılmıyor (`BR-D09-001`); teknik hata ayrı tipte (`BR-D09-002`). 4) Manuel sorun açma kapsam yetkisi ve içerik doğrulamasıyla çalışıyor. 5) Tekilleştirme anahtarı hassas veri içermiyor (`BR-D09-004`). |

---

### GAP-007 — Bildirim olayı ve teslimat hattı

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D12.C01.W01.A01` bildirim olayı yayımla (birincil); `D12.C01.W01.A02` veri-minimum yük, `D12.C01.W02.A01` abonelik, `D12.C01.W02.A02` görüntüleme, `D12.C02.W01.A01` kanal yapılandırma, `D12.C02.W02.A01-A02` teslimat/yeniden deneme, `D12.C02.W03.A01` teslimat izleme |
| Mevcut durum | Eksen A `MODEL_ONLY`, Eksen B `MISSING` (aşama 1 §3.19) |
| Repository kanıtı | `NotificationService`, kanal adaptörleri ve dispatch mantığı yazılı (`notifications/service.py`, `channel_adapters.py`); **modül dışında çağıran sıfır** (bu oturumda yeniden doğrulandı); migration yok; API/UI yok; composition'a bağlı değil |
| Eksik aşama | Olay yayımı → abone çözümü → teslimat → durum izleme (tamamı) |
| Eksik UI | Üst çubuk bildirim paneli; Yönetim > Bildirim Kanalları; Operasyon > Teslimat |
| Eksik API | `GET /notifications`, `POST /notifications/{id}/read`, `POST /notification-channels`, `GET /notification-deliveries`, `PUT /users/{id}/notification-subscriptions`, `POST /notification-deliveries/{id}/reroute` |
| Eksik servis | Olay yayım entegrasyonu (iş transaction'ıyla atomik yazım); teslimat worker'ı (GAP-002 kuyruğunda); abonelik çözümleyici |
| Eksik tablo/kolon | `notification_events`, `notification_channels`, `notification_subscriptions`, `notification_deliveries` |
| Yetki | `notification.channel.manage`, `notification.subscription.manage(.all)`, `notification.delivery.read/manage` — kod tanımlı değil |
| Audit | `NOTIFICATION_EVENT_PUBLISHED`, `NOTIFICATION_PAYLOAD_REJECTED`, `NOTIFICATION_DELIVERY_ATTEMPTED`, `NOTIFICATION_UNDELIVERABLE` |
| Test | `test_notifications.py` birim var; entegrasyon/E2E yok |
| Kullanıcı etkisi | Sorun açılışı, atama, SLA riski, rapor hazırlığı, dead-letter gibi olayların hiçbiri kimseye ulaşmıyor |
| İş etkisi | Sahiplendirme fiilen çalışmıyor; operatör dead-letter'dan habersiz; zamanlanmış rapor alıcıları çıktıyı bilmiyor (K3 → 4 akış) |
| Önerilen kabul kriterleri | 1) Bildirim olayı doğuran iş transaction'ıyla aynı anda yazılıyor (`BR-D12-001`). 2) Yük veri-minimum; hassas alan tespitinde yayımlanmıyor (`BR-D12-002/003`). 3) Kanal kimlik bilgisi yalnız sır referansı (`BR-D12-004`). 4) Teslimat ayrı durum makinesi: `PENDING` → `DELIVERED` / `UNDELIVERABLE`; teslim edilemeyen kritik bildirim alternatif kanala düşüyor (`BR-D12-006`). 5) Zorunlu tiplerden çıkılamıyor (`BR-D12-007`). |

---

### GAP-008 — Skor kalıcılığı, atomik yayım ve skor API'si

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D08.C03.W03.A01` skoru atomik yayımla (birincil); `D08.C03.W01.A01` kural skoru, `W02.A01-A03` toplulaştırma/veto, `D08.C04.W01.A02` yeniden üretim, `D08.C04.W02.A01` dönem karşılaştırma |
| Mevcut durum | Eksen A `PARTIAL`, Eksen B `PARTIAL` (aşama 1 §3.11) |
| Repository kanıtı | Hesaplama mantığı zengin (`scoring/service.py`, `contributions.py`, `partial_score_policies.py`); **`quality_scores` tablosu yok** — migration 13 yalnız `score_contribution_graphs` yaratıyor; skorlar `SQLiteScoreRepository`'de (dev'de seed dolu); `PostgreSQLContributionGraphRepository` yalnız testte; `/api/v1/scores` endpoint'i yok; partial policy audit'i PostgreSQL outbox değil `SQLiteTransactionalAudit` |
| Eksik aşama | Skor kalıcılığı → atomik yayım (`SUPERSEDED` zinciri) → dönem karşılaştırma → yeniden üretim doğrulaması |
| Eksik UI | Skor detay sayfası (şu an yalnız dashboard panelleri); karşılaştırma ekranı |
| Eksik API | `GET /scores` (kapsam parametreli), `GET /scores/{id}`, `GET /scores/rules/{ruleVersionId}`, `POST /scores/{id}/reproduction`, `GET /scores/comparison` |
| Eksik servis | PostgreSQL skor repository'si; yayım servisi (tek transaction, tüm seviyeler); kısmi skor politikalarının outbox'a taşınması |
| Eksik tablo/kolon | `quality_scores` (scope_type, score_value, score_status, qualification_verdict, rule_version_digest, policy_version, veto_applied, publication_id); `score_publications` (period, status, published_at) |
| Yetki | `score.read`, `score.reproduce` + kapsam — kod tanımlı değil |
| Audit | `RULE_SCORE_CALCULATED`, `SCORE_AGGREGATED`, `CRITICAL_VETO_APPLIED`, `SCORE_PUBLISHED`, `SCORE_REPRODUCTION_VERIFIED` |
| Test | `test_scoring.py` ve katkı testleri güçlü; PostgreSQL skor kalıcılık testi yok |
| Kullanıcı etkisi | Skor yalnız dashboard toplamı olarak ve seed veriden görünüyor; tekil skor kaydına, geçmişe ve karşılaştırmaya erişilemiyor |
| İş etkisi | Trend ve dönem karşılaştırması için yayım kaydı yok; "skor yeniden üretilebilir" ilkesi (aşama 2 §2.4) kanıtlanamıyor; dashboard runtime'da sahte veri gösteriyor |
| Önerilen kabul kriterleri | 1) Hesaplanan skor politika ve kural sürümü damgalarıyla PostgreSQL'e yazıyor. 2) Yayımlama tüm seviyeleri tek transaction'da yapıyor; kısmi hesapta yayım yok (`BR-D08-010` benzeri). 3) Önceki yayım `SUPERSEDED`, yenisi `PUBLISHED`. 4) Yeniden üretim, saklanan sayaç/ağırlık/politikayla birebir aynı sonucu veriyor. 5) `NOT_QUALIFIED` kapsamda skor iddiası üretilmiyor. |

---

### GAP-009 — İstisna/override ve kalite borcu

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D09.C04.W01.A01` istisna talep et (birincil); `W02.A01` karar, `W02.A02` ham ölçüm garantisi, `W03.A01` otomatik sonlanma, `W03.A02` erken iptal, `W03.A03` liste; ikincil: `D10.C04.W01.A01-A03` kalite borcu (akış 9 adım tablosunun parçası) |
| Mevcut durum | `MISSING` / `MISSING` — hiçbir halkada kod yok (aşama 1 §3.23, akış 9) |
| Repository kanıtı | `Exception`/`Waiver`/`Override` varlığı repo genelinde sıfır (bu oturumda yeniden doğrulandı); tek yakın desen `LegalHoldService` (konusu saklama, GAP-011) |
| Eksik aşama | Talep → maker-checker karar → bastırma → otomatik sona erme → kalite borcu kaydı (tamamı) |
| Eksik UI | İstisnalar listesi/yeni/detay; onay kuyruğu; Kalite Borcu listesi/detay |
| Eksik API | `POST /exceptions`, `POST /exceptions/{id}/decision` (`If-Match`), `POST /exceptions/{id}/revocation`, `GET /exceptions`; `POST /quality-debts`, `GET /quality-debts`, `POST /quality-debts/{id}/closure` |
| Eksik servis | İstisna servisi; süre denetimi zamanlayıcısı (GAP-003 altyapısı); bastırma motoru (sorun üretimi ve bildirimi engeller, ham sonucu değiştirmez); kalite borcu servisi |
| Eksik tablo/kolon | `exceptions` (scope, reason, compensating_control, valid_until, maker/checker_actor_id, status, version); `exception_suppressions`; `quality_debts` |
| Yetki | `exception.request/decide/revoke/read`, `quality-debt.manage/read` + kapsam; görev ayrılığı zorunlu — kod tanımlı değil |
| Audit | `EXCEPTION_REQUESTED/DECIDED/SUPPRESSED_ALERT/EXPIRED/REVOKED/LIST_VIEWED`; `QUALITY_DEBT_RECORDED/CLOSED` |
| Test | Kanıt yok |
| Kullanıcı etkisi | Bilinen bozulma için tek seçenek kuralı pasifleştirmek: süresiz, gerekçesiz, ölçümü tamamen durduran zayıf kontrol |
| İş etkisi | Kabul edilen risklerin kurumsal envanteri yok; `BR-D09-009..012` uygulanamıyor; akış 2'nin "kırıcı değişikliği istisnayla kabul" kolu karşılıksız; kalite borcu birikimi izlenemiyor |
| Önerilen kabul kriterleri | 1) Süresiz ve bitiş tarihsiz talep reddediliyor (`BR-D09-009`). 2) Maker ≠ checker veri tabanı düzeyinde korunuyor (`BR-D09-010`). 3) Aktif istisna ham sonucu değiştirmiyor; yalnız uyarıyı bastırıyor ve skor görünümünde işaretleniyor (`BR-D09-011`). 4) `valid_until` geçince istisna otomatik `EXPIRED` oluyor, bastırma kalkıyor ve birikmiş bozulmalar için sorun üretiliyor (`BR-D09-012`). 5) Onaylanan istisna kalite borcu kaydı üretiyor (`BR-D10-011`); borç kanıtsız kapatılamıyor (`BR-D10-012`). |

---

### GAP-010 — Veri sözleşmesi yaşam döngüsü

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D10.C03.W01.A01` sözleşme taslağı (birincil); `W01.A02` karşılıklı onay, `W01.A03` sonlandırma, `D10.C03.W02.A01-A02` uyum ölçümü/panosu, `D10.C03.W03.A01-A02` ihlal ilanı/geri kazanım; bağımlı: `D09.C01.W01.A03` sözleşme ihlalinden sorun (GAP-006) |
| Mevcut durum | `MISSING` / `MISSING` (akış 12; zincir ilk adımda kopuyor) |
| Repository kanıtı | `DataContract` veya `data_contract` adlı sınıf/tablo/endpoint/ekran/test sıfır (`grep -rl` boş, bu oturumda doğrulandı); `ST-DataContract` durum makinesi hedef modelde tanımlı |
| Eksik aşama | Taslak → çift taraf onayı → uyum ölçümü → ihlal → geri kazanım (tamamı) |
| Eksik UI | Veri Sözleşmeleri listesi/yeni/detay; uyum panosu |
| Eksik API | `POST /data-contracts`, `POST /data-contracts/{id}/acceptance`, `POST /data-contracts/{id}/termination`, `GET /data-contracts/{id}/compliance`, `GET /data-contracts`, `GET /data-contracts/{id}/breaches`, `POST /contract-breaches/{id}/closure` |
| Eksik servis | Sözleşme servisi (ölçülebilirlik doğrulaması); uyum ölçüm işi (kural sonuçlarından); ihlal değerlendirici (tolerans penceresi + yeterlilik ön koşulu) |
| Eksik tablo/kolon | `data_contracts` (dataset_id, version_no, consumers, commitments, status, taraf onay zamanları); `contract_compliance`; `contract_breaches` |
| Yetki | `contract.manage/accept/read` + taraf sahipliği; karşılıklı onay görev ayrılığı — kod tanımlı değil |
| Audit | `DATA_CONTRACT_DRAFTED/ACCEPTED/TERMINATED`, `CONTRACT_COMPLIANCE_MEASURED`, `DATA_CONTRACT_BREACHED/RECOVERED` |
| Test | Kanıt yok |
| Kullanıcı etkisi | Üretici-tüketici kalite beklentisi sözlü kalıyor; tüketici bağlı olduğu verinin taahhüde uyup uymadığını göremiyor |
| İş etkisi | Şema/güncellik/hacim taahhüt ihlalleri tespit edilemiyor; ihlalden sorun üretimi (`D09.C01.W01.A03`) karşılıksız; lineage eksikliğiyle birleşince tüketici tarafı tamamen kör |
| Önerilen kabul kriterleri | 1) Ölçülemeyen taahhüt reddediliyor (`BR-D10-006`). 2) Sözleşme yalnız iki tarafın onayıyla `ACTIVE` oluyor (`BR-D10-007`). 3) Yeterlilik düşükse ihlal ilan edilmiyor (`BR-D10-008`). 4) İhlal otomatik sorun açıyor ve tüm taraflara bildiriyor (`BR-D10-009`, GAP-006/007 ile birlikte). 5) Ardışık uyumlu ölçüm sözleşmeyi `BREACHED` → `ACTIVE` yapıyor. |

---

### GAP-011 — Saklama, imha, legal hold ve arşiv geri çağırma

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D13.C03.W01.A01` saklama politikası tanımla (birincil); `W01.A02` kayıtlara uygulama, `D13.C03.W02.A01-A02` imha işi/kanıtı, `D13.C04.W01.A01-A02` muhafaza uygulama/kaldırma, `D13.C04.W02.A01` geri çağırma; bağımlı: `D11.C04.W03.A01` süresi dolan rapor dosyası imhası |
| Mevcut durum | Eksen A `MODEL_ONLY`, Eksen B `MISSING` (aşama 1 §3.20, akış 13) |
| Repository kanıtı | Servis katmanı olgun: `LegalHoldService` (`retention/service.py:77,134`), `RetentionEvaluator` (`:271`), `DisposalJobService` (`disposal_service.py:63,171`), arşiv geri çağırma; 4 birim test dosyası; **tablolar hiçbir migration'da yok**; **sarkan FK:** `retention_policy_id` migration 03 (`nullable=False`) ve 06'da, hedef `retention_policies` tablosu yok (bu oturumda yeniden doğrulandı); servisler `SQLiteTransactionalAudit` kullanıyor |
| Eksik aşama | Politika tanımı → onay → kayıtlara uygulama → imha → kanıt → muhafaza → geri çağırma (tamamı) |
| Eksik UI | Yönetim > Saklama Politikaları; imha kanıtı görünümü; muhafaza ve geri çağırma ekranları |
| Eksik API | `POST /retention-policies` ve yaşam döngüsü uçları; imha işi ve kanıt uçları; muhafaza ve geri çağırma uçları |
| Eksik servis | Mevcut servislerin PostgreSQL kalıcılığına taşınması ve composition'a bağlanması; imha zamanlayıcısı (`reports.expires_at` dahil) |
| Eksik tablo/kolon | `retention_policies`, `legal_holds`, `disposal_jobs` (+ sonuç kanıtı), `archive_recall_requests/decisions`; `reports`/`data_processing_inventory_versions` FK'larının gerçek hedefe bağlanması |
| Yetki | `retention.policy.manage`, imha ve muhafaza rolleri (servislerde `_authorize_actor`/`_authorize_scope` mevcut ama merkezî katalog yok) |
| Audit | `RETENTION_POLICY_DRAFTED`, imha hazırlık/sonuç olayları, `LEGAL_HOLD_PLACED/RELEASED`; mevcut implementasyon SQLite audit'te — outbox'a taşınmalı |
| Test | 4 birim dosyası var; entegrasyon ve yüzey testi yok |
| Kullanıcı etkisi | Hiçbir kayda saklama süresi atanamıyor; yasal muhafaza uygulanamıyor; arşivden geri çağırma kullanılamıyor |
| İş etkisi | Hassas veri süresiz saklanıyor ve imha kanıtı denetimde gösterilemiyor (KVKK); rapor dosyaları `expires_at` sonrası erişilebilir kalıyor (`BR-D11-010`); `data_processing_inventory_versions` var olmayan tabloya `NOT NULL` referans veriyor (veri bütünlüğü tanımsız) |
| Önerilen kabul kriterleri | 1) Politika onay zinciriyle `EFFECTIVE` oluyor; kayıtlara `retention_until` yazılıyor. 2) İmha işi fail-closed hazırlanıyor ve kanıt üretiyor. 3) Legal hold kapsamındaki kayıt imha edilmiyor. 4) Süresi dolan rapor dosyası imha ediliyor, metadata korunuyor. 5) Sarkan `retention_policy_id` referansları gerçek tabloya bağlanıyor. |

---

### GAP-012 — Lineage olay alımı ve graf sorgulama

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D10.C01.W01.A01` lineage olayını al ve kaydet (birincil); `D10.C01.W01.A02` kolon düzeyi kenar, `D10.C01.W02.A01` yukarı/aşağı akış sorgulama |
| Mevcut durum | Eksen A `PARTIAL` (tüketim tarafı çalışır), üretim/alım tarafı `MISSING` (akış 11) |
| Repository kanıtı | `lineage/events.py` modelleri (`LineageEvent`, `ColumnLineageEdge`) var ama tabloları yok; tek tablo `lineage_evidence_snapshots` (migration 14) — gezilebilir graf değil, kanıt deposu; `POST /lineage/events` ve `GET /lineage/graph` yok; çalışan uçlar: `GET /lineage/snapshots/{id}` ve `GET /governance/{ref}/projection` (`InvestigationPage.tsx:377-378`) |
| Eksik aşama | Olay alımı → kenar upsert → graf sorgulama |
| Eksik UI | Lineage > Grafik; Katalog varlık detayında akış görünümü |
| Eksik API | `POST /lineage/events` (idempotency anahtarı); `GET /lineage/graph` (yön, derinlik) |
| Eksik servis | Alım servisi (şema doğrulama + katalog eşleştirme); graf gezinme servisi (derinlik sınırı + döngü kırma + kapsam maskeleme) |
| Eksik tablo/kolon | `lineage_events` (event_id, job_name, run_id, event_type, occurred_at); `lineage_edges` (from/to_asset_ref, transformation, last_seen_at); `column_lineage_edges` |
| Yetki | `lineage.write` (servis hesabı), `lineage.read` + varlık kapsamı — kod tanımlı değil |
| Audit | `LINEAGE_EVENT_INGESTED`, `LINEAGE_GRAPH_VIEWED` |
| Test | `test_lineage_governance.py` mevcut (kanıt tarafı); alım ve graf için test yok |
| Kullanıcı etkisi | "Bu veri nereden geliyor, nereye gidiyor?" sorusu yanıtlanamıyor; inceleme ekranı yalnız önceden hazırlanmış snapshot'ları gösterebiliyor |
| İş etkisi | Etki analizi (GAP-013), sözleşme tüketici listesi (GAP-010) ve kök neden teşhisi beslenemiyor; `BR-D10-001..005` uygulanacak mekanizma bulamıyor |
| Önerilen kabul kriterleri | 1) Aynı `run_id` ile tekrar gelen olay kenarları çoğaltmıyor (`BR-D10-001`). 2) Katalogda olmayan varlık "harici" kaydediliyor (`BR-D10-002`). 3) Graf sorgusunda derinlik sınırı ve döngü kırma çalışıyor (`BR-D10-003`). 4) Kapsam dışı düğümler maskeli dönüyor (`BR-D10-005`). 5) Alım ve sorgu erişimleri audit'leniyor. |

---

### GAP-013 — Etki analizi, simülasyon, teşhis ve kanıtlı öneri yüzeyi

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D10.C02.W01.A01` aşağı akış etki (birincil); `D10.C02.W02.A01` değişiklik simülasyonu; ikincil (aynı motor): `D09.C05.W01.A01-A02` kök neden hipotezi, `D09.C05.W02.A01` düzeltme önerisi |
| Mevcut durum | Kod `⚠️` — motor zengin ama yalnız testte; runtime `❌` (akış 11 + akış 8 incelme tablosu) |
| Repository kanıtı | `lineage/impact.py`: `assess_impact`, `ImpactComponent`, `Recommendation`, `CausalityStatus` vb.; **tek çağıran `test_lineage_governance.py`** (aşama 3 yeni doğrulama); üretim yolunda çağrı yok; API/UI yok |
| Eksik aşama | Sorun/bozulma → etki hesaplama → hipotez üretimi → öneri → insan kararı |
| Eksik UI | Sorunlar > İnceleme > Etki/Teşhis/Öneriler; Lineage > Etki Simülasyonu |
| Eksik API | `GET /lineage/impact`; `POST /lineage/impact-simulations`; `GET /issues/{id}/diagnosis`; `POST /diagnosis-hypotheses/{id}/decision`; `GET /issues/{id}/recommendations` |
| Eksik servis | Motorun üretim yoluna bağlanması (sorun açılışı/inceleme tetikleyicileri); hipotez ve öneri politikaları |
| Eksik tablo/kolon | `impact_analyses`, `impact_simulations`, `diagnosis_hypotheses`, `recommendations` |
| Yetki | `lineage.impact.read/simulate`, `issue.investigate` + kapsam — kod tanımlı değil |
| Audit | `IMPACT_ANALYSIS_COMPUTED`, `IMPACT_SIMULATION_RUN`, `DIAGNOSIS_HYPOTHESES_GENERATED`, `DIAGNOSIS_HYPOTHESIS_DECIDED`, `RECOMMENDATION_GENERATED` |
| Test | `test_lineage_governance.py` motor birim testleri var; yüzey ve entegrasyon testi yok |
| Kullanıcı etkisi | İnceleyen boş sayfayla başlıyor; "kimi etkiliyor?" sorusu tahminle yanıtlanıyor; hipotez otomatik kök nedene dönüşme riski olmadan sunul(a)mıyor |
| İş etkisi | Sorun önceliklendirmesi iş etkisinden yoksun; kırıcı şema değişikliğinin sonucu önceden görülemiyor; `BR-D09-013/014` ve `BR-D10-004` uygulanamıyor |
| Önerilen kabul kriterleri | 1) Lineage yoksa etki `UNKNOWN` raporlanıyor, sıfır sayılmıyor (`BR-D10-004`). 2) Kanıt yoksa hipotez/öneri üretilmiyor (`BR-D09-014`). 3) Hipotez insan kararı olmadan doğrulanmış kök neden sayılmıyor (`BR-D09-013`). 4) Simülasyon kırıcı etkileri ayrı işaretliyor ve düşük kapsamda uyarı veriyor. 5) Tüm üretim ve görüntülemeler audit'leniyor. |

---

### GAP-014 — Sorun SLA ve eskalasyon

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D09.C03.W01.A01` SLA hedeflerini belirle (birincil); `D09.C03.W01.A02` SLA durumu hesaplama/gösterme, `D09.C03.W02.A01` eskalasyon tetikleme |
| Mevcut durum | `MISSING` / `MISSING` (aşama 1 §3.23; akış 8 tablosunda üç adım da `❌`) |
| Repository kanıtı | SLA için model/kolon/servis kanıtı yok; `issue_history` zaman damgaları mevcut ama hedef/sayaç üretimi yok; bekletme (`WAITING_FOR_RESOLUTION`) geçişi de olmadığı için SLA duraklatma zemini eksik (bekletme ucu `D09.C02.W03.A02` bu kaydın parçası sayılır) |
| Eksik aşama | Hedef atama → durum hesaplama (`ON_TRACK`/`AT_RISK`/`BREACHED`) → eskalasyon → bekletmede duraklatma |
| Eksik UI | Sorun listesinde SLA durumu; Genel Bakış > Eskalasyonlar; bekletme dialog'u |
| Eksik API | `GET /issues` SLA alanı; `GET /issues/{id}/escalations`; `POST /issues/{id}/hold` |
| Eksik servis | SLA hesaplayıcı (iş takvimi + öncelik matrisi); eskalasyon motoru (zincir politikası); bekletme durum geçişi |
| Eksik tablo/kolon | `issue_slas` (first_response_due_at, resolution_due_at, calendar_version, policy_version, paused_duration, status, breached_at); `issue_escalations`; `issues`'a `hold_reason`, `expected_resolution_at`, `sla_paused_at` |
| Yetki | `issue.read` + kapsam; eskalasyon sistem aktörü — kod tanımlı değil |
| Audit | `ISSUE_SLA_BREACHED` (yalnız ihlal anında), `ISSUE_ESCALATED`, `ISSUE_PUT_ON_HOLD` |
| Test | Kanıt yok |
| Kullanıcı etkisi | Hangi sorunun geciktiği bilinmiyor; bekleyen sorunlar görünürde `INVESTIGATING` kalıyor |
| İş etkisi | Geciken bozulmalar kimse fark etmeden bekliyor; `BR-D09-017` (SLA yalnız tanımlı gerekçeyle duraklatılır) uygulanamıyor; yönetim raporlarında yanıt/çözüm süreleri yok |
| Önerilen kabul kriterleri | 1) Sorun oluşumunda öncelik ve iş takviminden SLA hedefleri atanıyor. 2) Durum listede gerçek zamanlı görünüyor; bekletmede sayaç duruyor. 3) `AT_RISK` ve `BREACHED` durumlarında zincire bildirim gidiyor (GAP-007). 4) Bekletme gerekçesiz reddediliyor ve audit'leniyor. 5) İhlal anı kalıcı olarak kaydediliyor. |

---

### GAP-015 — Rapor zamanlama UI bağlantısı ve tetikleme

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D11.C03.W03.A01` rapor zamanlaması tanımla (birincil); `D11.C03.W03.A02` vadesi geleni tetikle |
| Mevcut durum | Eksen A `PARTIAL`, Eksen B `BROKEN` (aşama 1 §3.15) |
| Repository kanıtı | Backend tam: 4 endpoint (`GET/POST/DELETE /report-schedules`, `POST /trigger-due`); istemci fonksiyonları `reports/api.ts:137,155,179`'da mevcut ve `App.tsx:61`'de import ediliyor (bu oturumda yeniden doğrulandı); **`ReportsRoute` bunları hiç bağlamıyor**; `ReportsPage.tsx:747` `syntheticSchedules` varsayılanı — kullanıcı sahte zamanlama listesi görüyor; `trigger-due` için istemci ve daemon yok; backend testi kanıtı yok |
| Eksik aşama | Route bağlantısı → gerçek liste/oluşturma/silme → zamanlayıcı tetikleme |
| Eksik UI | Rapor zamanlaması bölümünün gerçek veri ve handler'larla bağlanması (props'lar hazır) |
| Eksik API | — (endpoint'ler mevcut); eksik olan zamanlayıcı daemon |
| Eksik servis | `trigger-due`'yu periyodik çağıran zamanlayıcı (GAP-003 altyapısıyla ortak); `ReportsRoute` props bağlama |
| Eksik tablo/kolon | — (`report_schedules` mevcut) |
| Yetki | CSRF + actor scope mevcut |
| Audit | `audit_service` üzerinden mevcut |
| Test | Frontend `reports/api.test.ts:182-269` üç fonksiyonu test ediyor; backend ve route testi yok |
| Kullanıcı etkisi | Kullanıcı gerçek olmayan zamanlama listesi görüyor; oluşturma/silme butonları çalışmıyor |
| İş etkisi | Zamanlanmış rapor üretilemiyor; alıcılar düzenli çıktı almıyor; sahte veri gösterimi güven sorunu yaratıyor |
| Önerilen kabul kriterleri | 1) `ReportsPage` gerçek zamanlamaları listeliyor; sentetik fallback kaldırılıyor. 2) Oluşturma ve silme uçtan uca çalışıyor ve audit'leniyor. 3) Vadesi gelen zamanlama otomatik rapor üretiyor. 4) Backend zamanlama servisi için test ekleniyor. |

---

### GAP-016 — Rapor asenkron üretimi ve gerçek veri içeriği

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D11.C03.W02.A01` raporu asenkron üret (birincil); `D11.C03.W02.A02` üretim iptali; içerik bütünlüğü ön koşulu |
| Mevcut durum | Eksen A `PARTIAL`, Eksen B `PARTIAL` (aşama 1 §3.14, akış 10) |
| Repository kanıtı | `REPORT` iş tipi ve `ReportJobHandler` mevcut; dev bileşimi `inline_processing=True` ile kuyruğu atlıyor; veri sağlayıcı `_DevDataProvider` **sabit kodlanmış 4 satır** döndürüyor (`development.py:1109-1130`); dosya deposu `/tmp/reports-dev`; worker süreci zaten çalışmıyor (GAP-002) |
| Eksik aşama | Kuyruk yolu → asenkron üretim → durum ilerlemesi (`PENDING`→`GENERATING`→`READY`) → gerçek içerik |
| Eksik UI | Üretim durumu takibi (mevcut liste yeterli; durum akışı gerçek veriye bağlanmalı) |
| Eksik API | `POST /reports/{id}/cancellation` (üretim iptali) |
| Eksik servis | Gerçek veri sağlayıcı (skor/sonuç/sorun okuyan, GAP-008 kalıcılığına bağlı); kuyruk yolunun üretim bileşiminde açılması |
| Eksik tablo/kolon | — (`reports` mevcut) |
| Yetki | `ReportExportPolicy` fail-closed mevcut; iptal için talep sahipliği eklenmeli |
| Audit | Mevcut; iptal olayı eklenmeli |
| Test | `test_reporting.py`, `test_report_api.py`, skip-gated yaşam döngüsü var; gerçek içerik doğrulama testi yok |
| Kullanıcı etkisi | İndirilen rapor sistemin ölçümleriyle ilgisiz sabit veri içeriyor; büyük raporlar istek zaman aşımına takılabilir |
| İş etkisi | Raporlama kanıt değeri taşımıyor; `inline_processing` üretim modeli istek ölçeğinde tıkanıyor; "rapor gerçek skoru okumaz" durumu yönetim raporlarını geçersiz kılıyor |
| Önerilen kabul kriterleri | 1) Üretim bileşiminde rapor kuyruk üzerinden üretiliyor; istek-içi yol yalnız geliştirme modunda kalıyor. 2) Rapor içeriği gerçek skor/sonuç verisinden üretiliyor (doğrulama testiyle). 3) Büyük rapor istek zaman aşımına takılmıyor; durum ekranından izleniyor. 4) Üretim iptali çalışıyor ve audit'leniyor. 5) Dosya deposu yapılandırılabilir ve erişim kontrollü. |

---

### GAP-017 — Çalıştırma başlat/iptal komut yüzeyi

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D07.C01.W01.A01` manuel çalıştırma — UI katmanı (birincil); `D07.C01.W03.A01` çalıştırma iptali — UI katmanı |
| Mevcut durum | Backend `IMPLEMENTED` (gerçek PostgreSQL), frontend `API_ONLY` (aşama 1 §3.8, §6.2) |
| Repository kanıtı | `POST /api/v1/executions` ve `POST /api/v1/executions/{id}/cancel` mevcut ve gerçek PostgreSQL'e yazıyor; `executions/api.ts` **yalnız `fetchExecutions` export ediyor** (bu oturumda yeniden doğrulandı); `ExecutionsPage` salt okunur liste. Not: liste okumasının farklı kaynaktan gelmesi (yazma/okuma asimetrisi) GAP-001 kapsamındadır, burada tekrarlanmaz |
| Eksik aşama | UI'dan başlat/iptal komutu |
| Eksik UI | Çalıştırma başlatma formu (kapsam, kural sürümü seçimi, idempotency); satır bazlı iptal |
| Eksik API | — (iki endpoint de mevcut) |
| Eksik servis | — |
| Eksik tablo/kolon | — |
| Yetki | `ExecutionQueryService` scope mevcut; komut tarafı için rol kontrolü netleştirilmeli |
| Audit | `ExecutionTransactionalAudit` outbox'a staged — komutlar kullanılmadığı için pratikte üretilmiyor |
| Test | `test_execution_api.py` var; UI akışı için E2E yok |
| Kullanıcı etkisi | Kullanıcı arayüzünden hiçbir çalıştırma başlatamıyor veya iptal edemiyor |
| İş etkisi | Manuel ölçüm tek yol olan API'ye (curl/araç) bağımlı; operasyonel kullanım gerçekçi değil |
| Önerilen kabul kriterleri | 1) UI'dan başlatılan çalıştırma gerçek PostgreSQL'e yazıyor ve listede görünüyor (GAP-001 sonrası). 2) Aynı idempotency anahtarıyla ikinci başlatma mükerrer çalıştırma açmıyor. 3) İptal, kuyruktaki/çalışan işe işaretini ulaştırıyor. 4) Komutlar audit'leniyor. 5) E2E test akışı kapsıyor. |

---

### GAP-018 — Kuyruk ve dead-letter operasyon yüzeyi

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D07.C04.W04.A02` dead-letter inceleme (birincil); `W04.A03` yeniden işleme, `W04.A04` kapatma; `D14.C02.W01.A01-A02` kuyruk görüntüleme/müdahale; `D07.C03.W01.A02` öncelik yükseltme |
| Mevcut durum | Kod ekseninde servisler var (`BACKEND_ONLY`), yüzey `MISSING` (aşama 1 §3.10, akış 6) |
| Repository kanıtı | `DeadLetterReprocessService` yalnız `create_persistent_job_runtime()` içinde örnekleniyor — o da hiç çağrılmıyor (bu oturumda doğrulandı); `dead_letter_records` tablosu mevcut ama runtime'da hiç dolmuyor; `/operations/*` endpoint'i yok |
| Eksik aşama | Operatör inceleme → yeniden işleme/kapatma → ölçüm boşluğu işaretleme |
| Eksik UI | Operasyon > Kuyruk; Operasyon > Dead-letter |
| Eksik API | `GET /operations/jobs`; `POST /operations/jobs/{id}/intervention`; `PATCH /jobs/{id}/priority`; `GET /operations/dead-letters`; `POST /operations/dead-letters/{id}/reprocessing`; `POST /operations/dead-letters/{id}/closure` |
| Eksik servis | Yüzey servisleri; yeniden işleme politikası rol kapısı; ölçüm boşluğu işaretleyici |
| Eksik tablo/kolon | — (`persistent_jobs`, `dead_letter_records` mevcut) |
| Yetki | `operations.queue.read/manage`, `operations.dead-letter.read/reprocess/close`, `job.priority.override` + kurum geneli scope — kod tanımlı değil |
| Audit | `DEAD_LETTER_LIST_VIEWED`, `DEAD_LETTER_REPROCESSED`, `DEAD_LETTER_CLOSED`, `JOB_MANUALLY_INTERVENED`, `JOB_PRIORITY_OVERRIDDEN` |
| Test | `DeadLetterReprocessService` birim testi var; yüzey testi yok |
| Kullanıcı etkisi | Operatör biriken işleri ve başarısızlık nedenlerini göremiyor; düzeltilen kök nedenden sonra işi geri kazandıramıyor |
| İş etkisi | Dead-letter oluşumu sessiz; kaçan ölçümler yeterliliğe yansımıyor (`BR-D07-013` benzeri davranış yok), skor olduğundan güvenilir görünüyor |
| Önerilen kabul kriterleri | 1) Kuyruk durum/tip/öncelik/bekleme süresiyle filtrelenebilir listeleniyor. 2) Dead-letter yeniden işleme gerekçe + rol kapısıyla çalışıyor ve yeni idempotency anahtarı üretiyor. 3) Kapatma ölçüm boşluğunu işaretliyor. 4) Tüm müdahaleler audit'leniyor (`BR-D14-002`). |

---

### GAP-019 — Şema değişimi tespiti ve kararı

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D04.C04.W01.A01` şema farkı tespiti (birincil); `D04.C04.W02.A01` kabul/blokaj kararı; bağımlı: `BR-D04-008` karar verilmezse ölçüm blokajı, `RuleStatus.REVIEW_REQUIRED` tetikleme |
| Mevcut durum | `MISSING` / `MISSING` (akış 2 kritik ayrım; aşama 1 §3.7 değil — dağılım drifti ile karıştırılmamalı) |
| Repository kanıtı | `profile_comparisons` ve `compare_profile_snapshots` **veri dağılımı** driftini karşılaştırır; kolon ekleme/kaldırma, tip daralması, boş geçilebilirlik sıkılaşması tespiti ve `ADDITIVE`/`BREAKING`/`NEUTRAL` sınıflandırması için kod yok; `schema_changes` benzeri tablo hiçbir migration'da yok; `RuleStatus.REVIEW_REQUIRED` enum'da tanımlı ama tetikleyen yol yok (aşama 3 §5.4) |
| Eksik aşama | Keşif farkından (GAP-004) şema değişikliği çıkarma → sınıflandırma → etki simülasyonu (GAP-013) → karar → blokaj/kabul |
| Eksik UI | Katalog > Şema Değişiklikleri; karar ekranı |
| Eksik API | Şema değişikliği listeleme/karar uçları |
| Eksik servis | Şema fark sınıflandırıcı; karar beklerken ölçüm blokajı; etkilenen kuralları `REVIEW_REQUIRED` yapma |
| Eksik tablo/kolon | `schema_changes` (source, dataset/field, change_type, classification, status, decided_by, decided_at) |
| Yetki | Karar için Data Owner; `catalog.diff.apply` ile aynı kapsam modeli |
| Audit | Şema değişikliği tespit ve karar olayları |
| Test | Kanıt yok |
| Kullanıcı etkisi | Kaynakta kolon değişse bile sistem fark etmiyor; kurallar sessizce yanlış şeyi ölçüyor veya teknik hata veriyor |
| İş etkisi | Kırıcı değişiklik bildirimi, ölçüm blokajı ve `REVIEW_REQUIRED` geçişi işlemiyor; akış 2'nin karar kolu tamamen karşılıksız |
| Önerilen kabul kriterleri | 1) Keşif farkındaki kolon ekleme/kaldırma/tip daralması tespit edilip sınıflandırılıyor. 2) `BREAKING` değişiklik sahibine bildiriliyor (GAP-007). 3) Karar verilmezse ilgili ölçüm bloklanıyor (`BR-D04-008`). 4) Etkilenen aktif kurallar `REVIEW_REQUIRED` durumuna geçiyor. 5) Kabul kararı gerekçeyle audit'leniyor. |

---

### GAP-020 — Kural şablonları, bağımlılık ve çakışma tespiti

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D06.C01.W02.A01-A02` kural şablonu yaşam döngüsü (birincil); `D06.C04.W01.A01` bağımlılık çözümleme, `D06.C04.W02.A01` çakışma/mükerrerlik tespiti |
| Mevcut durum | `MISSING` / `MISSING` (akış 4 çevresel kırılmalar tablosu) |
| Repository kanıtı | `RuleType` enum'undaki sekiz tip kod içinde sabit — yönetilebilir şablon kütüphanesi yok; bağımlılık grafı ve çakışma tespiti için kod yok (aşama 3 akış 4) |
| Eksik aşama | Şablon taslağı → yayımlama → şablondan kural üretimi; kayıt anında bağımlılık/çakışma denetimi |
| Eksik UI | Şablon kütüphanesi; kural formunda çakışma uyarısı |
| Eksik API | Şablon CRUD uçları; çakışma sorgusu |
| Eksik servis | Şablon servisi (`DRAFT`→`PUBLISHED`→`DEPRECATED`); bağımlılık çözümleyici (döngü reddi); çakışma dedektörü (aynı kapsam+tanım) |
| Eksik tablo/kolon | `rule_templates`; bağımlılık/çakışma kayıtları |
| Yetki | Şablon yayımlama Governance Admin; kural yazarı kullanım |
| Audit | Şablon yaşam döngüsü ve çakışma tespiti olayları |
| Test | Kanıt yok |
| Kullanıcı etkisi | Her kural sıfırdan tanımlanıyor; aynı kontrolü ölçen mükerrer kurallar fark edilmiyor |
| İş etkisi | Mükerrer kurallar skorda iki kez sayılıyor; `BR-D06-001` (yalnız `PUBLISHED` şablon), `BR-D06-010` (döngü yasağı), `BR-D06-011` (birebir mükerrer yasağı), `BR-D06-012` (şablon değişiminde `REVIEW_REQUIRED`) uygulanamıyor |
| Önerilen kabul kriterleri | 1) Yalnız `PUBLISHED` şablonlardan kural üretiliyor. 2) Dairesel bağımlılık reddediliyor. 3) Birebir aynı kapsam+tanımda ikinci kural reddediliyor. 4) Şablon değişikliği bağlı kuralları `REVIEW_REQUIRED` yapıyor. 5) Yaşam döngüsü audit'leniyor. |

---

### GAP-021 — Gölge (shadow) yürütme kullanıcı yolu

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D06.C05.W01.A01` kural sürümünü gölge modda çalıştır (birincil); `D06.C05.W01.A02` gölge-resmî karşılaştırma |
| Mevcut durum | Eksen A `PARTIAL`, Eksen B `MISSING` (aşama 1 §3.7) |
| Repository kanıtı | `ExecutionMode.SHADOW` (`executions/models.py:22`) ve migration 12'nin IR shadow kanıt kolonları mevcut; SHADOW çalıştırma tetikleyen endpoint/UI/permission/audit kanıtı yok |
| Eksik aşama | Gölge başlatma → resmî akıştan dışlama → süre sonu → karşılaştırma raporu |
| Eksik UI | Kurallar > Sürüm Detayı > Gölge |
| Eksik API | `POST /rule-versions/{id}/shadow-runs`; `GET /rule-versions/{id}/shadow-comparison` |
| Eksik servis | Gölge orkestrasyonu (zamanlayıcıyla otomatik sonlanma); karşılaştırma üretici |
| Eksik tablo/kolon | — (`rule_executions.execution_mode`, `rule_execution_results.eligible_for_official_scoring` mevcut) |
| Yetki | `rule.shadow.execute/read` + dataset kapsamı — kod tanımlı değil |
| Audit | `SHADOW_EXECUTION_STARTED`, `SHADOW_COMPARISON_VIEWED` |
| Test | `test_prototype_05_capabilities.py` kısmi |
| Kullanıcı etkisi | Yeni kural üretim veri üzerindeki davranışı skoru etkilemeden gözlemlenemiyor |
| İş etkisi | Kural değişiklikleri üretimde deneme-yanılma riski taşıyor; `BR-D06-008/009` (test/gölge sonucu resmî skora girmez) davranışı tetiklenecek yol bulamıyor |
| Önerilen kabul kriterleri | 1) Gölge çalıştırma başlatılabiliyor ve `SHADOW` işaretli sonuç üretiyor. 2) Gölge sonuçlar resmî skor ve sorun akışından dışlanıyor (`eligible_for_official_scoring=false`). 3) Gölge sonucu resmî işaretlenirse skorlama fail-closed reddediyor. 4) Karşılaştırma raporu yanlış alarm tahminiyle üretiliyor. |

---

### GAP-022 — Kullanıcı, rol, izin yönetimi ve üretim oturumu

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D02.C01.W01.A01-A03` kullanıcı yaşam döngüsü (birincil); `D02.C01.W02.A01-A02` servis hesabı, `D02.C02.W01.A01-W03.A02` rol/izin/atama, `D02.C02.W02.A02` görev ayrılığı kuralları, `D02.C04` oturum, `D02.C05.W01` erişim gözden geçirme |
| Mevcut durum | Eksen A `PARTIAL`, Eksen B `MOCK_ONLY` (aşama 1 §3.17; denetlenmemiş akışlar tablosu) |
| Repository kanıtı | `users`/`roles`/`permissions`/`role_assignments`/`assignment_scopes`/`sessions` ve erişim gözden geçirme tabloları 14 migration'ın hiçbirinde yok (bu oturumda doğrulandı; migration'ların yarattığı 31 tablo §2'de listelidir). Roller `ActorContext` içinde serbest dize kümesidir. `BffSessionBoundary` yalnız testte örnekleniyor (`test_bff_session_api.py:318`); `api/app.py:380` onu opsiyonel parametre olarak alır ve verilmediğinde `UnavailableActorContextResolver`'a düşer (`:416`); `api/development.py` içinde hiç referansı yoktur |
| Mevcut kimlik kodu (rapor eksik göstermişti) | `identity/sessions.py` SQLite tabanlı `SQLiteSessionRepository` (`:112`) ve `SessionService` (`:350`) ile tam bir oturum yaşam döngüsü içerir (`open_authenticated_session`, `validate`, `validate_csrf`, `logout`). `identity/ldap.py` `LdapAuthenticationService` (`:70`) ve `LdapGroupRoleScopePolicy` (`:48`) ile grup → rol/kapsam eşlemesi sağlar. Hiçbiri çalıştırılabilir bileşime bağlı değildir |
| Dev kimliği (düzeltme) | "Sabit tek rol kümesi" ifadesi **yanlıştı**. `api/identity.py:91 build_default_development_users` **sekiz** farklı profil tanımlar (`:117-181`): `dev-data-viewer`, `dev-data-steward`, `dev-data-owner`, `dev-data-governance`, `dev-data-engineer`, `dev-audit-viewer` (`can_view_enterprise=False`), `dev-limited-steward` (kısıtlı kaynak/dataset kapsamı) ve `dev-privileged-user`. Seçim istemcinin gönderdiği `X-Development-User-Id` başlığıyla yapılır (`api/identity.py:246`). Asıl sorun rol çeşitliliğinin yokluğu değil, **seçimin istemciye bırakılmış olmasıdır**: başlık bir güven sınırı değildir ve `privileged=True` profil dâhil her kimlik serbestçe seçilebilir |
| Eksik aşama | Hesap sağlama → rol/izin atama → kapsam çözümleme → oturum → periyodik gözden geçirme (tamamı) |
| Eksik UI | Yönetim > Kullanıcılar/Roller/İzinler/Görev Ayrılığı; üretim login akışı; erişim gözden geçirme ekranı |
| Eksik API | `POST /users`, pasifleştirme/yeniden etkinleştirme; `POST /roles`, `PUT /roles/{id}/permissions`; `POST /users/{id}/role-assignments`; `GET /permissions`; `POST /segregation-rules` |
| Eksik servis | Hesap sağlama (dizin senkronizasyonu ile); rol atama ve SoD denetimi; üretim oturum sınırının composition'a bağlanması |
| Eksik tablo/kolon | `users`, `roles`, `permissions`, `role_permissions`, `role_assignments`, `sessions`, `segregation_rules`, `service_accounts` |
| Yetki | `identity.user.manage`, `identity.role.manage/assign`, `identity.sod.manage` — kod tanımlı değil |
| Audit | `USER_PROVISIONED/DEACTIVATED/REACTIVATED`, `ROLE_DEFINED`, `ROLE_PERMISSIONS_CHANGED`, `ROLE_ASSIGNED`, `ROLE_ASSIGNMENT_REVOKED`, `SOD_RULE_DEFINED` |
| Test | `test_identity.py`, `test_bff_session_api.py` ve sorgu kapsam testleri var (boş kapsamın kapsamsız sorguya dönüşmediğini sabitleyen dört test — bkz. 11 §6.2); kalıcılık, rol atama ve yönetim yüzeyi testi yok |
| Kullanıcı etkisi | Kimlik istemci tarafından seçilebildiği için yetki reddi **üretimde anlamlı bir güvence sağlamıyor**; okuma kapsamı gerçekten uygulanırken komut yolunda rol/kapsam kontrolü yok (bkz. GAP-001 "Yetki" satırı) |
| İş etkisi | Hedef modelin 15 rolü ve görev ayrılığı çiftleri uygulanamıyor; erişim gözden geçirme kanıtı üretilemiyor; üretim geçişinin (kurumsal IdP) ön koşulu yok |
| Önerilen kabul kriterleri | 1) Kullanıcı dış kimlik referansıyla idempotent sağlanıyor; pasifleştirmede oturumlar ve roller atomik kapanıyor. 2) Rol ataması kapsam ve SoD kontrolüyle çalışıyor; `BLOCK` çakışma reddediliyor. 3) Kapsam çözümlemesi atama kayıtlarından üretiliyor (serbest dize roller kalkıyor). 4) Üretim bileşiminde `BffSessionBoundary` bağlı; dev başlığı üretim yolunda kapalı. 5) Erişim gözden geçirme kampanyası kanıt üretiyor. |

---

### GAP-023 — ServiceNow giden entegrasyon yüzeyi

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D12.C03.W01.A01` dış sistemde bilet oluştur (birincil); `D12.C03.W01.A02` dış kayıt güncelleme, `D12.C03.W02.A01` gelen geri bildirim uzlaştırma |
| Mevcut durum | Eksen A `MODEL_ONLY`, Eksen B `MISSING` (aşama 1 §3.22) |
| Repository kanıtı | `servicenow/` modülü devre kesici, retry işi ve `SERVICENOW_TICKET_PRODUCER` rol kontrolüyle yazılı (`service.py:837`); migration, API ve UI yok; composition'a bağlı değil |
| Eksik aşama | Eşleşme kuralı → idempotent gönderim → dış kimlik bağlama → durum senkronizasyonu → gelen uzlaştırma |
| Eksik UI | Sorunlar > Detay > Entegrasyon; entegrasyon yapılandırma ekranı |
| Eksik API | `POST /issues/{id}/integrations`; `POST /integrations/{id}/callbacks` |
| Eksik servis | Alan eşleme servisi; entegrasyon kaydı yaşam döngüsü; composition bağlantısı (kurumsal lab adaptörleriyle ilişkili — dış bağımlılık) |
| Eksik tablo/kolon | `integration_records` (integration_id, source_ref, external_id, status, idempotency_key, attempt_count, last_synced_at) |
| Yetki | `integration.outbound.execute/trigger`, `integration.inbound.write` — kod tanımlı değil |
| Audit | `INTEGRATION_RECORD_SENT/UPDATED`, `INTEGRATION_INBOUND_RECONCILED` |
| Test | Servis birim testleri var (fixture'larla); entegrasyon yüzeyi testi yok |
| Kullanıcı etkisi | Kalite sorunları kurumun iş takip sürecine giremiyor; dış sistemdeki ilerleme sisteme yansımıyor |
| İş etkisi | `BR-D12-008/009` (idempotency, izinli alan) uygulanamıyor; operasyonel sahiplik çift kayıtla bölünüyor |
| Önerilen kabul kriterleri | 1) Uygun sorun için idempotency anahtarıyla tek bilet açılıyor. 2) Geçici hata retry, kalıcı hata `FAILED` + operatör bildirimi üretiyor. 3) Sorun durumu değişince dış kayıt güncelleniyor. 4) Gelen geri bildirim yalnız izinli alanları değiştiriyor; çakışmada sistem durumu korunuyor. |

---

### GAP-024 — Operasyon: bileşen sağlığı, operasyonel olay ve bakım

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D14.C01.W01.A01` bileşen sağlığı (birincil); `D14.C01.W01.A02` sağlık uyarısı, `D14.C01.W02.A01` kapasite, `D14.C03.W01.A01-A02` operasyonel olay, `D14.C04.W01.A01` bakım penceresi, `D14.C04.W02.A01` toplu telafi. Not: kuyruk/dead-letter yüzeyi GAP-018'de tutulur, burada tekrarlanmaz |
| Mevcut durum | `MISSING` / `MISSING` (aşama 1 §3.23; denetlenmemiş akışlar tablosu) |
| Repository kanıtı | Sağlık toplama, operasyonel olay ve bakım penceresi için hiçbir kod kanıtı yok; `incident_response/` modülü KVKK ihlali odaklıdır, platform kesintisi yönetimi karşılığı değildir (aşama 3 §6) |
| Eksik aşama | Sağlık toplama → uyarı → olay açma/izleme → bakım bastırması → kesinti sonrası telafi (tamamı) |
| Eksik UI | Operasyon > Sistem Sağlığı / Kapasite / Olaylar / Bakım / Telafi |
| Eksik API | `GET /operations/health`; `GET /operations/capacity`; `POST /operations/incidents` + güncelleme/kapatma; `POST /operations/maintenance-windows`; `POST /operations/backfills` |
| Eksik servis | Sağlık toplayıcı (depo, kuyruk, worker, zamanlayıcı, kanal, outbox); olay yaşam döngüsü servisi; bakım penceresi yöneticisi; telafi orkestratörü |
| Eksik tablo/kolon | `component_health`, `operational_incidents`, `incident_updates`, `maintenance_windows`, `backfill_jobs` |
| Yetki | `operations.health.read`, `operations.incident.manage`, `operations.maintenance.manage`, `operations.backfill.execute` — kod tanımlı değil |
| Audit | `PLATFORM_HEALTH_VIEWED`, `COMPONENT_HEALTH_CHANGED`, `OPERATIONAL_INCIDENT_OPENED/UPDATED/CLOSED`, `MAINTENANCE_WINDOW_SCHEDULED`, `BACKFILL_STARTED/COMPLETED` |
| Test | Kanıt yok |
| Kullanıcı etkisi | Operatör sistemin hangi parçasının sorunlu olduğunu göremiyor; kesintiler koordinasyonsuz yönetiliyor |
| İş etkisi | `BR-D14-001..008` uygulanamıyor; planlı bakım gereksiz alarm üretiyor; kesinti sonrası ölçüm boşlukları kapatılamıyor; `BR-D14-008` gereği operasyonel olaylar kalite sorunlarından ayrı izlenemiyor |
| Önerilen kabul kriterleri | 1) Sağlık bilgisi alınamayan bileşen `UNKNOWN` gösteriliyor, sağlıklı sayılmıyor. 2) Operasyonel olay kök neden kaydedilmeden kapatılamıyor. 3) Bakım penceresi boyunca uyarılar bastırılıyor ve zamanlamalar duraklatılıyor. 4) Telafi işleri kota korumasıyla kademelendiriliyor. 5) Tüm müdahaleler gerekçeyle audit'leniyor. |

---

### GAP-025 — Sentetik veri uygulama yüzeyi ve kontrol doğrulama

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D15.C01.W01.A01` sentetik üretim çalıştırması (birincil); `D15.C01.W02` profil yönetimi, `D15.C02.W01.A01-W02` ground truth ve beklenen sonuç, `D15.C03.W01.A01-W02` tespit doğruluğu ve yeterlilik deneyi |
| Mevcut durum | Eksen A `BACKEND_ONLY` (CLI script), uygulama içinden `MISSING` (aşama 1 §3.21; denetlenmemiş akışlar tablosu) |
| Repository kanıtı | Servis, generator, oracle, temporal ve finalization katmanı + 5 birim ve skip-gated entegrasyon testi mevcut; run/dataset tabloları yok; HTTP yüzeyi yok; kullanım `scripts/generate_synthetic_test_data.py` üzerinden |
| Eksik aşama | Run yönetimi → ground truth kaydı → tespit doğruluğu ölçümü → yeterlilik deneyi |
| Eksik UI | Sentetik üretim run listesi/detay; ground truth kaydı; doğruluk raporu |
| Eksik API | Run başlatma/listeleme; ground truth ve beklenen sonuç uçları; doğruluk ölçüm ucu |
| Eksik servis | Mevcut servislerin uygulama bileşimine bağlanması; doğruluk karşılaştırma servisi |
| Eksik tablo/kolon | Sentetik run ve ground truth kalıcılığı (PostgreSQL'e taşıma); doğruluk ölçüm kayıtları |
| Yetki | `synthetic_data/authorization.py:22-49` rol + dataset scope mevcut; yüzey yetkisi tanımlanmalı |
| Audit | `SQLiteTransactionalAudit` üzerinden (`oracle.py:139,146`) — outbox'a taşınmalı |
| Test | 5 birim + skip-gated entegrasyon var; yüzey testi yok |
| Kullanıcı etkisi | Kontrol doğrulama yalnız geliştirici CLI'ıyla yapılabiliyor; denetim ekipleri doğruluk kanıtına uygulama üzerinden ulaşamıyor |
| İş etkisi | "Kontroller gerçekten tespit ediyor mu?" sorusu (chaos/yeterlilik deneyi) kurumsal kanıta dönüşemiyor; DQ-CAP prototiplerinin çıktısı kalıcı yüzey bulamıyor |
| Önerilen kabul kriterleri | 1) Üretim run'ı uygulama üzerinden başlatılıp izlenebiliyor. 2) Ground truth ve beklenen sonuçlar sürümlü kaydediliyor. 3) Tespit doğruluğu sayısal raporlanıyor (duyarlılık/yanlış alarm). 4) Yeterlilik deneyi kanıtı denetimde gösterilebilir biçimde saklanıyor. 5) Audit olayları outbox'a yazıyor. |

---

### GAP-026 — Yönetişim yapısı, iş sözlüğü ve politika yaşam döngüsü

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D01.C01.W01.A01` organizasyon birimi (birincil); `D01.C01.W02-W03` iş/veri domaini, `D01.C02.W01.A01` varlık sahipliği (yönetim yeteneği; bağımlılık GAP-004'te), `D01.C02.W03` sahipsiz varlık takibi, `D01.C03` iş sözlüğü, `D01.C04` politika yaşam döngüsü, `D01.C05` sistem konfigürasyonu |
| Mevcut durum | `MISSING` / `MISSING` (aşama 1 §3.23; denetlenmemiş akışlar tablosu) |
| Repository kanıtı | Organizasyon, domain, sahiplik ve terim yönetimi için hiçbir halkada kod yok; politika **sürümü** birçok yerde damgalanıyor (`policy_version` kolonları) ama politikayı tanımlayan/onaylayan/yürürlüğe alan yaşam döngüsü yok — sürümler kod içinde sabit (aşama 3 §6); `system_config` tablosu yok |
| Eksik aşama | Organizasyon/domain kurulumu → sahiplik atama → politika taslak/onay/yürürlük → konfigürasyon değişimi (tamamı) |
| Eksik UI | Yönetim > Organizasyon/Domainler/Sahiplik/Sözlük/Politikalar/Konfigürasyon |
| Eksik API | Organizasyon, domain, sahiplik, terim, politika ve konfigürasyon CRUD uçları |
| Eksik servis | Sahiplik servisi (katalog varlıklarına bağlanır); politika yaşam döngüsü servisi; sahipsiz varlık izleyici |
| Eksik tablo/kolon | `organizational_units`, `business_domains`, `data_domains`, `asset_ownerships`, `glossary_terms`, `policies` (+ sürümler), `system_config` |
| Yetki | Governance Admin ve Security Admin rolleri — kod tanımlı değil |
| Audit | Organizasyon, sahiplik ve politika olayları |
| Test | Kanıt yok |
| Kullanıcı etkisi | Varlıkların sahibi atanamıyor; roller ve politikalar kodda sabit kaldığı için davranış değişikliği sürüm gerektiriyor |
| İş etkisi | Tüm scope/sahiplik zincirinin ön koşulu eksik (D01, aşama 2 §3.1'e göre tüm domainlerin ön koşulu); politika sürümü damgalanıyor ama denetimde "hangi politika ne zaman yürürlükteydi" kanıtlanamıyor; fail-closed davranışların dayandığı politikalar yönetilemiyor |
| Önerilen kabul kriterleri | 1) Organizasyon birimi ve iş/veri domain'i oluşturulup varlıklara bağlanıyor. 2) Katalog varlığına sahip atanabiliyor (GAP-004 sonrası); sahipsiz varlıklar listeleniyor. 3) Politika taslak → onay → yürürlük yaşam döngüsü çalışıyor ve `policy_version` damgaları gerçek kayda işaret ediyor. 4) Konfigürasyon değişikliği maker-checker ile audit'leniyor. |

---

### GAP-027 — Komut yolunda onay ve kapsam bypass'ı

| Alan | Değer |
|---|---|
| Hedef fonksiyon | `D03.C02.W01.A02` aktivasyon kararı (birincil); `D06.C02.W01.A01` kural oluşturma, `D07.C01.W01.A01` manuel çalıştırma başlatma — her birinin **yetki ve onay sınırı** |
| Mevcut durum | Eksen A `PARTIAL`, Eksen B `BROKEN` — endpoint çalışır, arkasındaki kontrol çalışmaz |
| Neden ayrı kayıt? | GAP-001 kalıcılığın, GAP-022 kalıcı IAM'in eksikliğidir. Bu kayıt farklı bir kök nedeni tanımlar: **kontroller kodda vardır, erişilebilir komut yüzeyi onları atlar.** GAP-001 ve GAP-022 çözülse bile bu route'lar aktör bağlamını porta iletmediği sürece bypass sürer |
| Aktivasyon bypass'ı | Gerçek `DataSourceService.decide_activation` (`data_sources/service.py:461+`) checker rolünü, talep süresini, politika sürümünü, bayat revizyonu ve `request.maker_actor_id == context.actor_id` eşitliğini denetler (`:487-488`) ve audit üretir. Çalıştırılabilir yol ise `POST /api/v1/data-sources/{id}/activation` → `data_source_mutation_service.activate(data_source_id)` (`api/app.py:2073-2082`) → `DevelopmentDataSourceStore.activate` (`api/development.py:951-968`, bağ: `:1367`). Bu store yalnız `TEST_SUCCEEDED` guard'ı uygular; maker/checker, rol, kapsam ve audit yoktur. `activate(self, data_source_id: str)` imzası aktör taşıyacak bir parametre bile içermez — eksik olan bir `if` değil, **port sözleşmesidir** |
| Kimlik doğrulanıyor, yetkilendirilmiyor | Aktör bağlamı `app.py:433-453`'teki durum değiştirme middleware'inde çözülür ve `request.state.actor_context`'e konur (401/403 üretir). Sorun bağlamın çözülmemesi değil, route'un onu porta **iletmemesidir**. Doğru tanım: kimliği doğrulanmış, yetkisi denetlenmemiş komut |
| Diğer bypass noktaları | `POST /api/v1/data-sources` (`app.py:2017-2026`) sahibi (`owner_user_id`) **istek gövdesinden** alır, oturumdaki aktörden değil; `/test` (`:2051`) ve `/passivation` (`:2095`) de bağlam iletmez. `DevelopmentRuleStore.create_rule` yalnız bağlamın `None` olmadığına bakar (`development.py:837-882`). Manuel çalıştırma ucu bağlamı `actor_id` dizesine indirger ve aktör yoksa `"unknown"` yazar (`app.py:2133`); `PostgreSQLExecutionStartService.start_manual` (`api/postgresql_execution.py:63-110`) kural sürümü/kaynak kimliklerinin varlığını, aktifliğini veya kapsamını doğrulamaz, `scope` sabit boştur |
| Eksik UI | — (yüzey mevcut; sorun arkasındaki kontrolde) |
| Eksik API | — (endpoint'ler mevcut; sözleşmeleri aktör bağlamı taşımalı) |
| Eksik servis | Mutation port'larının `ActorContext` alacak biçimde yeniden tanımlanması; development store'ların gerçek servis kurallarını uygulaması veya bu route'ların gerçek servislere bağlanması |
| Eksik tablo/kolon | — |
| Yetki | Bu kaydın kendisi yetki boşluğudur |
| Audit | Bypass edilen geçişler audit üretmez; `DATA_SOURCE_ACTIVATION_DECIDED` çalıştırılabilir yolda hiç yazılmaz |
| Test | **Boşluk iki testle sabitlenmiştir.** `test_data_source_api.py:360 test_data_source_write_successful_activate_passivate_flow` onaysız `TEST_SUCCEEDED -> ACTIVE` geçişi için `200` bekler. `test_rule_api.py:405 test_fr_031_create_rule_without_dataset_scope_returns_403` adına ve docstring'ine rağmen `201` assert eder; yorumu fake servisin kapsam kontrolü yapmadığını kabul eder. Her ikisi de kapsam sayımında "yetki testi" görünür |
| Kullanıcı etkisi | Tek bir kullanıcı, ikinci bir onaycı olmadan veri kaynağını aktive edebiliyor; kapsamı dışındaki dataset'e kural yazabiliyor; yetkisi olmayan kaynakta çalıştırma başlatabiliyor |
| İş etkisi | Görev ayrılığı beyanı çalışan ürün için geçersiz: kontroller yalnız servis testlerinde vardır. Denetimde "maker-checker uygulanıyor" iddiası bu yolla çürütülebilir (K9) |
| Önerilen kabul kriterleri | 1) Her komut endpoint'i çözülmüş `ActorContext`'i mutation portuna iletiyor. 2) `activate`/`passivate` gerçek `decide_activation` üzerinden geçiyor; maker = checker reddediliyor. 3) Kural oluşturma dataset kapsamı dışında `403` **döndürüyor** ve test bunu assert ediyor. 4) Manuel çalıştırma kural sürümü/kaynak kimliklerini varlık, aktiflik ve kapsam için doğruluyor; `"unknown"` aktör kabul edilmiyor. 5) Kaynak sahibi istek gövdesinden değil oturumdan alınıyor. 6) Yanıltıcı iki test gerçek beklentiyi assert edecek şekilde düzeltiliyor. |

---

## 4. Çapraz bağımlılık haritası

GAP'lar bağımsız değildir; uygulama sıralaması planlanırken şu bağımlılıklar
dikkate alınmalıdır:

| GAP | Bağımlı olduğu GAP'lar |
|---|---|
| GAP-002 (worker) | GAP-001 (composition root) |
| GAP-003 (zamanlayıcı) | GAP-002 (iş kuyruğu çalışmadan tetikleme anlamsız) |
| GAP-005 (profil yürütme) | GAP-002, GAP-004 (hedef dataset) |
| GAP-006 (sorun üretimi) | GAP-002 (sonuç akışı), GAP-001 |
| GAP-007 (bildirim) | GAP-002 (teslimat işi) |
| GAP-008 (skor kalıcılığı) | GAP-001, GAP-002 |
| GAP-013 (etki/teşhis) | GAP-012 (lineage) |
| GAP-015 (rapor zamanlama) | GAP-003 altyapısı |
| GAP-016 (rapor içeriği) | GAP-002, GAP-008 |
| GAP-018 (operasyon yüzeyi) | GAP-002 |
| GAP-019 (şema değişimi) | GAP-004, GAP-013 |
| GAP-021 (gölge) | GAP-002, GAP-017 |
| GAP-014 (SLA) | GAP-006, GAP-007 |
| GAP-022 (kimlik) | Diğer tüm GAP'ların yetki kodları bu kayda bağlıdır |
| GAP-027 (komut bypass'ı) | Bağımsız olarak kapatılabilir — GAP-001 ve GAP-022'yi **beklemez** |

**Uygulama sırası uyarısı.** GAP-009 (istisna/kalite borcu) ve GAP-014 (SLA)
işlevsel olarak gerçekten yoktur; ancak ikisi de GAP-006 (sorun üretimi) ve
GAP-007 (bildirim) tamamlanmadan kullanılabilir hale gelmez. Bu kayıtların
"eksik" olması onları erken uygulanacak kayıtlar yapmaz. Buna karşılık
GAP-027 herhangi bir kayda bağımlı değildir ve mevcut kodda çalışan bir
güvenlik kontrolünün atlanmasını tarif eder.

## 5. Kanıt sınırları

- Runtime değerlendirmeleri kod okumasına dayanır; uygulama bu oturumda
  ayağa kaldırılmamıştır.
- Test koşumu yapılmıştır: seçili birim suite **297 passed**;
  `docs/testing/02-Entegrasyon` **92 skipped** (PG ortam değişkeni yok);
  `pytest --collect-only` **1505** test toplar. Ayrıntı: 11 §13.
- §1.3'te listelenen iddialar bu oturumda komutla yeniden doğrulanmıştır;
  kalan kanıtlar aşama 1/3'ten devralınmıştır.
- Aşama 1'in **Q-13** sorusu (şema adı tutarsızlığı) kapanmıştır: tutarsızlık
  `run_dev.py` ile `create_development_app` arasında statik olarak
  doğrulanmıştır ve GAP-001 içinde kayıtlıdır — artık açık bir soru değildir.
  **Q-01** (üretim composition root repo dışında mı?) açıktır; "evet" yanıtı
  GAP-001, GAP-002, GAP-003 ve GAP-007'nin runtime eksenlerini değiştirir.
- Kabul kriterleri öneridir; önceliklendirme ve iterasyon planı bu belgenin
  kapsamı dışındadır.

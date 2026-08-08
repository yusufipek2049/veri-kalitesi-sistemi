---
type: functional-audit-work
stage: "Doğrulama itirazlarının çözümü"
scope: verification-resolution
inputs:
  - 14-Independent-Code-Verification.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-04
---

# 02 — Bağımsız Doğrulama İtirazlarının Çözümü

Bu belge, [14-Independent-Code-Verification.md](../14-Independent-Code-Verification.md)
içindeki her önemli itirazın **repository kanıtına karşı yeniden sınanmasını** ve
sonucunu kaydeder. Doğrulama raporu kaynak kabul edilmemiş, her iddia için
dosya/satır düzeyinde bağımsız kontrol yapılmıştır.

## 1. Yöntem

| İlke | Uygulama |
|---|---|
| Kanıt önceliği | Doğrulama raporunun beyanı değil, dosyanın kendisi okundu |
| Karar seti | `KABUL EDİLDİ` · `KISMEN KABUL EDİLDİ` · `REDDEDİLDİ` |
| Kabul ölçütü | İddia dosya/satır kanıtıyla birebir doğrulanıyorsa kabul; kapsamı veya nedeni yanlışsa kısmen kabul; kanıt çürütüyorsa ret |
| Test iddiaları | Statik sayımla **ve** koşumla doğrulandı (§4) |

Bu oturumda koşulan komutlar ve sonuçları:

```text
ls tests/unit/test_*.py | wc -l            → 57
ls tests/integration/test_*.py | wc -l      → 11
grep -rE "^\s*(async )?def test_" 01-Birim   | wc -l → 1057
grep -rE "^\s*(async )?def test_" 02-Entegrasyon    → 92
python3 -m pytest --collect-only -q                 → 1505 tests collected
python3 -m pytest -q <7 seçili birim dosyası>       → 297 passed
python3 -m pytest -q docs/testing/02-Entegrasyon      → 92 skipped
```

## 2. Karar özeti

| # | İtiraz | Karar | Etkilenen dosya |
|---|---|---|---|
| A-01 | GAP-003 scheduling servis ve testleri var; `MODEL_ONLY`/"test yok" yanlış | **KABUL EDİLDİ** | 01, 03, 04, 09, 11 |
| A-02 | GAP-004 metadata keşif orkestrasyonu, diff ve testleri var | **KABUL EDİLDİ** | 01, 03, 04, 06, 09 |
| A-03 | GAP-005 profil yürütücüsü (`run_profile`) ve testleri var | **KABUL EDİLDİ** | 01, 04, 09 |
| A-04 | GAP-006 issue üretici servisi, dedup/recurrence ve testleri var | **KABUL EDİLDİ** | 01, 03, 04, 09, 11 |
| A-05 | `eligible_for_auto_issue` trigger sözleşmesine taşınmıyor, doğrulanmıyor | **KABUL EDİLDİ** | 01, 03, 04 |
| A-06 | `claim_next` audit/outbox almıyor; `JOB_CLAIMED` kodda yok | **KABUL EDİLDİ** | 01, 04, 09, 11 |
| A-07 | Hedef `AVAILABLE`/`CLAIMED`/`BLOCKED`/`DEAD_LETTERED` uygulanmıyor | **KABUL EDİLDİ** | 01, 04, 09 |
| A-08 | GAP-022 "sabit tek rol kümesi" yanlış; sekiz dev profili var | **KABUL EDİLDİ** | 01, 03, 04, 10 |
| A-09 | Okuma yolunda scope backend'de uygulanıyor; "yalnız frontend" yanlış | **KABUL EDİLDİ** | 04, 10, 11 |
| A-10 | Komut yolunda rol/kapsam kontrolü yok (yanlış negatif) | **KABUL EDİLDİ** | 03, 04, 06, 10, 11 |
| A-11 | Veri kaynağı aktivasyonu maker-checker'ı atlıyor (yanlış negatif) | **KABUL EDİLDİ** | 03, 04, 06, 09, 10, 11 |
| A-12 | `test_fr_031_..._returns_403` gerçekte `201` assert ediyor | **KABUL EDİLDİ** | 04, 11 |
| A-13 | ST-ApprovalRequest "tamamen yok" yanlış; domain bazında var | **KABUL EDİLDİ** | 09, 11 |
| A-14 | PG transaction audit atomiklik testi "sıfır" yanlış | **KABUL EDİLDİ** | 11 |
| A-15 | Test sayıları 57/11/1057/92/1149; "12 dosya, ~1037/~112" yanlış | **KABUL EDİLDİ** | 11 |
| A-16 | Şema ayrışması açık soru değil, doğrulanmış wiring hatası | **KABUL EDİLDİ** | 03, 04, 08 |
| A-17 | `_FakePreparedRepo.store` ↔ `publish_pending → append` uyuşmazlığı | **KABUL EDİLDİ** | 04, 08 |
| A-18 | Execution yazma PG'ye, okuma sentetik reader'a gidiyor | **KABUL EDİLDİ** | 04 |
| B-01 | "Aktivasyon route'u ActorContext çözmüyor" | **KISMEN KABUL EDİLDİ** | 04, 06, 10 |
| B-02 | "PG repository'leri yalnız testlerde örnekleniyor" | **KISMEN KABUL EDİLDİ** | 04 |
| B-03 | `retention_policy_id` "sarkan FK" nitelemesi | **KISMEN KABUL EDİLDİ** | 08 |
| B-04 | "GAP-006 için üretim yolu testi yok" | **KISMEN KABUL EDİLDİ** | 04 |
| B-05 | `create_persistent_job_runtime` "production/test dışı çağıranı yok" | **KISMEN KABUL EDİLDİ** | 01, 04 |
| B-06 | Issue self-verification SoD'si tam uygulanıyor | **KISMEN KABUL EDİLDİ** | 09, 10 |
| C-01 | GAP-009 ve GAP-014 önceliği P1 → P2 düşürülmeli | **REDDEDİLDİ** | 04, 11 (gerekçe notu eklendi) |
| C-02 | P0/P1 sınıflandırmasının rapora atfedilmesi | **REDDEDİLDİ** | — |
| C-03 | "Rapor `quality_scores` yok derken yanılıyor" ihtimali | **REDDEDİLDİ** | 08 (açıklama eklendi) |

Bu denetimde ayrıca **doğrulama raporunun da kaçırdığı** iki bulgu tespit
edilmiştir; §5'te kayıtlıdır.

## 3. Kabul edilen itirazlar — kanıt ve uygulanan düzeltme

### A-01 · Scheduling backend'i ve testleri var

**İtiraz.** Rapor GAP-003'ü `MODEL_ONLY` sayıyor ve "test kanıtı yok
(birim/entegrasyon sıfır)" diyor; oysa servis ve testler mevcut.

**Bağımsız kanıt.** `executions/scheduling.py`: `ScheduleType` (`:63`),
`Schedule` (`:71`), `SQLiteScheduleRepository` (`:92`), `SchedulingService`
(`:218`) — `create_schedule` (`:234`), `trigger_due` (`:303`), `preview_runs`
(`:343`), DST filtresi (`:383`), idempotency anahtarı (`:311`).
`executions/postgresql_scheduling.py:64` `PostgreSQLScheduleRepository`.
`test_executions.py:643-1005` arasında 10 test.

**Karar: KABUL EDİLDİ.** Eksen A `MODEL_ONLY` → `BACKEND_ONLY`; "test kanıtı
yok" satırı testlerin listesiyle değiştirildi; GAP-003 özet tablosunda `Kod`
sütunu ⚠️ → ✅.

**Kabulü aşan ek tespit.** `PostgreSQLScheduleRepository.due` (`:109-124`) düz
`SELECT`'tir; `with_for_update(skip_locked=True)` yoktur. Aynı katmandaki iş
kuyruğu (`jobs/postgresql_repository.py:354`) ve outbox
(`audit/postgresql_outbox.py:92`) bunu kullanır, dolayısıyla eksiklik
stilistik değildir. 09 §7.1'e "çok zamanlayıcılı tek kazanan garantisi bugün
yok" notu eklendi.

### A-02 · Metadata keşfi connector düzeyinde değil

**İtiraz.** Rapor keşfi "connector seviyesinde üç tanım" olarak gösteriyor;
orkestrasyon, diff ve testler yok sayılıyor.

**Bağımsız kanıt.** `data_sources/service.py:763` `discover_metadata`;
`:1559` `_diff_metadata` (modül düzeyi fonksiyon, `:881`'den çağrılıyor);
`postgresql_repository.py:1145` `replace_metadata` — dataset/alan yazımı ve
`audit_outbox.stage` tek `transactional_session` içinde (`:1154-1198`).
Testler: `test_data_sources.py:843,876,892,942` ve outbox rollback
`:523,548,573`.

**Karar: KABUL EDİLDİ.** 01 §3.3, 03 akış 1 ve K4, 04 GAP-004, 06 hedef
endpoint notu güncellendi.

**Kabulü aşan ek tespit.** `replace_metadata` anlık görüntüyü silip yeniden
kurar (`:1157-1196`), surrogate ID'ler yenilenir. Hedefteki `PARTIAL` keşif ve
"kısmi keşifte kaldırma çıkarımı yapma" kuralı bu yaklaşımla sağlanamaz —
GAP-004'e ayrı satır olarak eklendi.

### A-03 · Profil yürütücüsü var

**Kanıt.** `data_sources/service.py:901` `run_profile`; testler
`test_data_sources.py:968,1015,1117,1159,1175,1242,1313,1397,1464` ve
`:573`.

**Karar: KABUL EDİLDİ.** 01 §3.4 Eksen A açıklaması, 04 GAP-005 ve 09 §14
ST-Profile satırı düzeltildi.

### A-04 · Issue üretici servisi var

**Kanıt.** `issues/service.py:139` `create_for_trigger` — güvenilir servis
bağlamı (`:145-149`, varsayılan `ActorType.SERVICE`), `uuid5` dedup (`:165`),
yinelenme ilişkisi ve `DATA_QUALITY_ISSUE_REOPENED` (`:194-260`).
`issues/postgresql_repository.py:234` `add_or_increment` — advisory lock
(`:250-257`), `SELECT … FOR UPDATE` (`:258-271`), `occurrence_count + 1`
(`:331`), history (`:338-352`) ve `audit_outbox.stage` (`:353`) tek
transaction'da. Testler: `test_issues.py`, `test_postgresql_issue_mutations.py:53,327`.

**Karar: KABUL EDİLDİ.** GAP-006 `MISSING`/`MISSING` → `BACKEND_ONLY`/`MISSING`.

**Ayakta kalan alt iddia.** "Çağrı noktası yok" **doğrudur**:
`create_for_trigger` için repo genelinde yalnız tanım ve iki test çağrısı
vardır. Kabul, boşluğun varlığını değil **yerini** değiştirir.

### A-05 · Uygunluk kapısı yok

**Kanıt.** `executions/models.py:168` `eligible_for_auto_issue` hesaplanıyor
(`executions/service.py:322,374`), SQLite ve PG'de kalıcılaştırılıyor,
migration 12'de kolonu var. Buna karşılık `issues/models.py:72-79`
`IssueTrigger` alanları yalnız `trigger_type, scope_type, scope_id,
deduplication_key, occurred_at, correlation_id, event_id`; `issues/` altında
`eligible_for_auto_issue` **hiç geçmiyor**.

**Karar: KABUL EDİLDİ.** 01 §3.12, 03 akış 7, 04 GAP-006'ya "uygunluk kapısı
yok" satırı eklendi. Sonuç: yalnız bir çağıran eklemek `BR-D09-001`/`002`
davranışını garanti etmez.

### A-06 · `claim_next` audit üretmiyor

**Kanıt.** `jobs/postgresql_repository.py:271` imzası (`:271-280`) audit veya
outbox parametresi almıyor; gövde `audit_outbox.stage` çağırmıyor. Aynı
dosyada `release_expired_claims` outbox alıyor. `FOR UPDATE SKIP LOCKED`
(`:354`), lease (`:297,384`), kota (`:301-332`) ve version guard (`:378`)
gerçekten var.

**Karar: KABUL EDİLDİ.** Bu, "worker backend'i tamam, yalnız entrypoint
eksik" beyanını geçersiz kılar. 04 GAP-002'ye "Claim audit boşluğu" satırı,
09 §7.2'ye uygulama farkı tablosu, 11 §8.3 eklendi.

### A-07 · Hedef durum kümesi uygulanmıyor

**Kanıt.** `jobs/models.py:20-27` `JobStatus`: `QUEUED`, `RUNNING`,
`CANCEL_REQUESTED`, `SUCCESS`, `TECHNICAL_ERROR`, `TIMEOUT`, `CANCELLED`.
`AVAILABLE`, `CLAIMED`, `BLOCKED`, `DEAD_LETTERED` yok; dead-letter ayrı
enum (`DeadLetterStatus`, `:43`).

**Karar: KABUL EDİLDİ.** 09 §7.2'ye hedef ↔ uygulama eşleme tablosu eklendi.

### A-08 · Sekiz dev kullanıcı profili

**Kanıt.** `api/identity.py:91` `build_default_development_users` → 8 profil
(`:117-181`), aralarında `dev-audit-viewer` (`can_view_enterprise=False`),
`dev-limited-steward` (kısıtlı kapsam) ve `dev-privileged-user`. Seçim
`api/identity.py:246` `request.headers.get("X-Development-User-Id")`.

**Karar: KABUL EDİLDİ.** "Sabit `{DATA_VIEWER, DATA_STEWARD, AUDIT_VIEWER}`"
ifadesi 01 §3.17, 03 §5.2 ve 04 GAP-022'den kaldırıldı.

**Vurgu kaydırması.** Kabul, boşluğu küçültmez: asıl sorun rol çeşitliliği
değil, **kimliğin istemci tarafından seçilebilmesidir**. Düzeltilen metinler
bunu açıkça söylüyor.

### A-09 · Okuma yolunda scope backend'de

**Kanıt.** `identity/service.py:90` `PolicyAuthorizationService` kararı
`permitted_source_ids`/`permitted_dataset_ids` ile dönüyor (`:124-129`).
Tüketiciler: `issues/query.py:57,64-66`, `rules/query.py:46,52`,
`executions/query.py:54,61-62`, `data_sources/query.py:66,72`.
Boş kapsam testleri: `test_data_source_api.py:66`, `test_rule_api.py:83`,
`test_execution_api.py:81`, `test_issue_api.py:92`.

**Karar: KABUL EDİLDİ.** 10 §6.1.1 ve 11 §6.2 eklendi; 04 GAP-001 "Yetki"
satırı yeniden yazıldı.

### A-10 · Komut yolunda yetkilendirme yok

**Kanıt.** `api/app.py:2017-2110` — dört veri kaynağı route'u aktör bağlamını
mutation portuna iletmiyor; `create` sahibi **istek gövdesinden** alıyor
(`:2026`). `api/development.py:837-882` `create_rule` yalnız `None` kontrolü.
`api/app.py:2120-2137` manuel çalıştırma `actor_id` dizesine indirgiyor,
aktör yoksa `"unknown"` (`:2133`). `api/postgresql_execution.py:63-110`
`start_manual` kural sürümü/kaynak kimliklerini doğrulamıyor, `scope` sabit
boş (`:75`).

**Karar: KABUL EDİLDİ.** Yeni kayıt **GAP-027** açıldı; kök neden **K9**
olarak 03 §4'e eklendi.

### A-11 · Aktivasyon maker-checker bypass'ı

**Kanıt.** Gerçek servis `data_sources/service.py:461+` checker rolü
(`:472-476`), süre (`:479-482`), politika sürümü (`:483-484`), bayat revizyon
(`:485-486`) ve `request.maker_actor_id == context.actor_id` (`:487-488`)
denetliyor, audit üretiyor (`:515+`). Çalışan yol:
`api/app.py:2073-2082` → `data_source_mutation_service.activate(id)`;
bağlanan port `api/development.py:1367` → `DevelopmentDataSourceStore.activate`
(`:951-968`) yalnız `TEST_SUCCEEDED` guard'ı. İmza `activate(self,
data_source_id: str)` — aktör taşıyacak parametre **yok**. Frontend çağırıyor
(`dataSources/api.ts:106-111`); `test_data_source_api.py:360` bu geçiş için
`200` assert ediyor (`:369-370`).

**Karar: KABUL EDİLDİ.** GAP-027'nin çekirdeği; 06'da endpoint `MEVCUT` →
`KISMİ`, 09 §14 ST-DataSource satırı ve §6.4 uyarısı, 10 §4.4 eklendi.

### A-12 · Yanıltıcı test adı

**Kanıt.** `test_rule_api.py:405`
`test_fr_031_create_rule_without_dataset_scope_returns_403`; kurulum kapsam
dışı (`:411-412`), assertion `:431` `== 201`; yorum `:429-430` "Fake servis
kapsam kontrolu yapmaz, bu nedenle 201 doner." Docstring 403 bekliyor.

**Karar: KABUL EDİLDİ.** 04 GAP-027 ve 11 §6.3'e kaydedildi; kabul kriteri
"bu iki test gerçek beklentiyi assert edecek şekilde düzeltilir" eklendi.

### A-13 · ST-ApprovalRequest domain bazında var

**Kanıt.** `rule_approval_requests` (migration 02, `:144`) ve
`data_source_activation_requests` (migration 03) için model, servis,
repository, PG repository ve testler mevcut. Ortak `approval_requests` tablosu
yok. maker ≠ checker: `rules/service.py:542-545`,
`data_sources/service.py:487-488`, `issues/service.py:646-649`.

**Karar: KABUL EDİLDİ.** 09 §6.4'e uygulama tablosu, §14 satırı `❌ Yok` →
`⚠️ Domain bazında`; 11 §5 satırı ve SoD sütunu düzeltildi.

### A-14 · PG audit atomiklik testleri var

**Kanıt.** `test_postgresql_execution_persistence.py:592`,
`test_postgresql_issue_mutations.py:53` ve `:327`,
`test_postgresql_score_contributions.py:79`,
`test_postgresql_lineage_evidence.py`.

**Karar: KABUL EDİLDİ.** 11 §8.1 tablosuna eklendi; §8.2'deki "entegrasyon
testi **sıfır**" hükmü, "test kodu var / bu ortamda hiç koşmadı" ayrımıyla
değiştirildi. Koşum kanıtı: `92 skipped`.

### A-15 · Test sayıları

**Kanıt.** §1'deki komut çıktıları. Doğrulama raporunun 57/11/1057/92/1149,
1505 ve 297 rakamlarının **tamamı** yeniden üretildi.

**Karar: KABUL EDİLDİ.** 11 §1.1, §2.1, §2.2, §11.2 ve §13 düzeltildi.
"12 entegrasyon dosyası" sayımı `conftest.py`'yi test dosyası saydığı için
oluşmuştu.

### A-16 · Şema ayrışması

**Kanıt.** `run_dev.py:11,21,33` → `data_quality`;
`api/development.py:1332-1333` `PostgreSQLExecutionRepository(session_factory)`
ve `PostgreSQLJobQueueRepository(session_factory)` — `schema=` argümanı yok,
varsayılan `persistence/database.py:15` `DEFAULT_SCHEMA_NAME = "dq"`.
Alembic hedefi `dq` (`alembic/env.py:24`). Belirleyici ayrıntı:
`create_session_factory` `search_path` ayarlamaz; tablolar
`MetaData(schema=…)` ile açıkça niteliklendirilir.

**Karar: KABUL EDİLDİ.** 08 §3.2 koşullu ifadeden doğrulanmış tabloya
çevrildi; Q-13 kapatıldı (03 §7.2, 04 §5).

**Kapsam sınırı.** Aynı bileşimdeki şema ayrışması statik olarak kesindir.
"Tüm PG yolları çalışmaz" sonucu ise uygulamanın ayağa kaldırılmasını
gerektirir; bu oturumda uygulama çalıştırılmadı ve bu iddia yazılmadı.

### A-17 · Prepared repository protokol uyuşmazlığı

**Kanıt.** `run_dev.py:14-19` yalnız `store()`;
`audit/postgresql_outbox.py:99` `self.repository.append(...)`; `:102`
`except Exception` yutuyor, satır `PENDING` kalıyor,
`last_error_code="AUDIT_REPOSITORY_UNAVAILABLE"` (`:103-114`); metod
`:133`'te hata fırlatmadan dönüyor.

**Karar: KABUL EDİLDİ.** 04 GAP-001 "Audit yayım hatası" satırı ve 08 §3.2
eklendi. Kritik yan sonuç: çağıran (ör. `SchedulingService.create_schedule`)
bunu **başarı** olarak görür.

### A-18 · Yazma/okuma ayrışması

**Kanıt.** `api/development.py:1334` PG start service; `:1359`
`ExecutionQueryService(DevelopmentExecutionReader(), authorization)`;
`DevelopmentExecutionReader` (`:585-600`) modül düzeyi sabit
`DEVELOPMENT_EXECUTIONS`'ı (`:301`) filtreler, `session_factory`'ye hiç
dokunmaz.

**Karar: KABUL EDİLDİ.** 04 GAP-001'e ayrı satır olarak eklendi.

## 4. Kısmen kabul edilen itirazlar

### B-01 · "Route ActorContext çözmüyor"

**İtirazın yanlış kısmı.** Aktör bağlamı **çözülüyor**: `api/app.py:433-453`
durum değiştiren her isteği `state_change_boundary.protect_state_changing`
ile koruyor ve `request.state.actor_context`'e yazıyor (401/403 üretiyor).

**İtirazın doğru kısmı.** Route bu bağlamı mutation portuna **iletmiyor**;
port imzası da onu alamıyor.

**Karar: KISMEN KABUL EDİLDİ.** Belgelere "ActorContext çözülmüyor" değil
**"kimliği doğrulanmış, yetkisi denetlenmemiş komut"** ifadesi yazıldı
(04 GAP-027, 06 §3.2 uyarısı, 10 §6.1.2). Bu ayrım önemlidir: sorun kimlik
doğrulama katmanında değil, port sözleşmesindedir; düzeltme de oradadır.

### B-02 · "PG repository'leri yalnız testlerde"

**İtirazın doğru kısmı.** `PostgreSQLIssueRepository`,
`PostgreSQLRuleRepository`, `PostgreSQLDataSourceRepository`,
`PostgreSQLContributionGraphRepository` için doğru.

**İtirazın yanlış kısmı.** `PostgreSQLExecutionRepository`,
`PostgreSQLJobQueueRepository`, `PostgreSQLExecutionStartService`/
`CancelService`, `PostgreSQLGovernanceProfileReader`,
`PostgreSQLLineageEvidenceRepository` ve `PostgreSQLReportRepository`
`create_development_app` içinde **gerçekten bağlanıyor** (`:1300-1340`).

**Karar: KISMEN KABUL EDİLDİ.** 04 GAP-001 "Mevcut durum" satırındaki
`MOCK_ONLY` nitelemesi "karışık ve kendi içinde tutarsız" ile değiştirildi;
bağlı olan PG bileşenleri listelendi. 01 §2.3 zaten yalnız dört sınıfı
sayıyordu ve doğruydu — değiştirilmedi.

### B-03 · `retention_policy_id` "sarkan FK"

**İtirazın doğru kısmı.** `retention_policies` tablosu hiçbir migration'da
yok; her iki kolon da doğrulanmayan referans taşıyor.

**İtirazın yanlış kısmı.** Bunlar **`ForeignKey` değil**: migration 03 `:225`
`sa.Column(..., sa.String(40), nullable=False)`, tablodaki tek
`ForeignKeyConstraint` (`:231-234`) `data_fields` içindir; migration 06 `:34`
nullable `String(36)` ve `reports` tablosunda hiç FK yoktur. "Hedefi düşmüş
FK" veritabanında mevcut değildir.

**Karar: KISMEN KABUL EDİLDİ.** 08 §3.4 başlığı "Sarkan yabancı anahtarlar"
→ "Doğrulanmayan referans kolonları"; tabloya kolon tanımları eklendi. Ayrım
pratiktir: sarkan FK migration'ı bozar ve hemen görülür; doğrulanmayan metin
kolonu sessizce tutarsız veri biriktirir. §4.5, §4.x ve §7 satırları da
uyumlandı.

### B-04 · "GAP-006 için üretim yolu testi yok"

**İtirazın doğru kısmı.** Execution → issue köprüsü ve uygunluk kapısı için
test yoktur.

**İtirazın yanlış kısmı.** Bunun nedeni test eksikliği değil, **davranışın
kodda hiç olmamasıdır**. Üretici servisin kendi testleri kapsamlıdır.

**Karar: KISMEN KABUL EDİLDİ.** 04 GAP-006 "Test" satırı, var olan testleri
listeleyip eksik olanı "kodda da yok" notuyla ayırıyor.

### B-05 · `create_persistent_job_runtime` çağıranı

**İtirazın ifadesi.** "Production/test dışı hiçbir çağıran yok."

**Kanıt daha güçlü.** Çağıran **hiç yok — testler dâhil**. Testler
`PersistentJobWorker`'ı elle kuruyor
(`test_persistent_job_worker.py:206,349`, `test_postgresql_job_queue.py:699`).

**Karar: KISMEN KABUL EDİLDİ** (lehte güçlendirilerek). 01 §3.10 ve 04
GAP-002 "testler dâhil" ibaresiyle güncellendi; ayrıca `pyproject.toml`'da
`[project.scripts]` tablosunun hiç olmadığı doğrulandı.

### B-06 · Issue self-verification SoD'si

**İtirazın doğru kısmı.** `issues/service.py:646-649` çözümü oluşturanın
kendi çözümünü doğrulamasını reddediyor ve testi var
(`test_issues.py:961`).

**Eksik kalan ayrıntı.** Guard `if result.outcome is
IssueVerificationOutcome.QUALITY_PASSED:` bloğunun içindedir (`:638`).
Çözen aktör kendi çözümü için `QUALITY_FAILED`, `PARTIAL` veya
`TECHNICAL_ERROR` doğrulaması **girebilir**.

**Karar: KISMEN KABUL EDİLDİ.** 09 §6.4, 10 §4.4 ve 03 §5.2'ye bu sınırlama
eklendi.

## 5. Reddedilen itirazlar

### C-01 · GAP-009 ve GAP-014 için P1 → P2 önerisi

**İtiraz.** Bu işlevler GAP-006 ve GAP-007'ye bağımlı olduğundan mevcut P1
sırası gerekçesizdir; P2 önerilir.

**Ret gerekçesi.**

1. **Karşılaştırılan şeyler aynı değil.** 04 hiçbir GAP'e P0/P1/P2 önceliği
   atamaz; 11 §10'daki `Kritik/Yüksek/Orta/Düşük` sütunu **test riskini**
   derecelendirir, uygulama sırasını değil. Doğrulama raporu kendi kurduğu
   `Kritik = P0, Yüksek = P1` eşlemesini rapora atfetmiş ve bu eşlemeyi
   kendisi de `INSUFFICIENT_EVIDENCE` olarak işaretlemiştir. Var olmayan bir
   önceliklendirme düşürülemez.
2. **Bağımlılık argümanı zaten kayıtlı.** 04 §4 çapraz bağımlılık haritası
   `GAP-014 (SLA) → GAP-006, GAP-007` satırını içeriyordu.
3. **Boşluğun kendisi tartışmalı değil.** İstisna/waiver/quality-debt ve
   SLA/escalation için model, migration, servis, API, UI ve test yoktur;
   `ExecutionStatus.SUPPRESSED_BY_EXCEPTION` (`executions/models.py:46`) tek
   referansı `test_scoring.py:327` olan bir enum değeridir. Bu doğrulandı.

**Uygulanan telafi.** İtirazın altındaki geçerli endişe — "eksik olması erken
yapılması gerektiği anlamına gelmez" — kabul edildi ve iki yere açık not
olarak yazıldı: 04 §4 "Uygulama sırası uyarısı" ve 11 §10 "Öncelik sütunu ≠
uygulama sırası". Yani karar reddedilmiş, endişe belgeye geçmiştir.

### C-02 · P0/P1 sınıflandırmasının rapora atfedilmesi

**Ret gerekçesi.** Doğrulama raporunun kendi §1'i bu eşlemenin "raporun açıkça
tanımladığı bir sınıflandırma değil, bu doğrulamanın operasyonel eşlemesi"
olduğunu söylüyor. Buna rağmen §2 yönetici özeti ve bölüm başlıkları
("P0 doğrulamaları", "P1 doğrulamaları") sınıflandırmayı rapora aitmiş gibi
sunuyor. Denetim belgelerine bu çerçeve taşınmadı; öncelik ifadeleri kendi
tanımlı ölçekleriyle bırakıldı.

### C-03 · `quality_scores` hakkındaki belirsizlik

**Ret gerekçesi.** Raporun "`quality_scores` tablosu yok" hükmü PostgreSQL
şeması için doğrudur. Ad kod tabanında geçer, fakat yalnız
`scoring/repository.py:48` içinde SQLite `CREATE TABLE IF NOT EXISTS` DDL'i
olarak; SQLite'a özgü bakım kodu (`PRAGMA table_info` `:168`,
`ALTER TABLE … RENAME` `:173`) taşır. `score_publications` hiçbir kodda
geçmez. Düzeltme gerekmedi; karışıklığı önlemek için 08 §4.25'e açıklama
eklendi.

## 6. Bu denetimde bulunan, doğrulama raporunun da kaçırdığı bulgular

### D-01 · Kural mutasyon uçları çalışan bileşimde `503`

**Kanıt.** `create_development_app` yalnız `rule_creator_service=rule_store`
bağlar (`api/development.py:1351`); **`rule_mutation_service` hiç
geçirilmez** (dosyada bu ad hiç geçmiyor). Route'lar portu `None` bulunca
`RuleQueryTechnicalError` fırlatır (`api/app.py:1772,1807,1836,1895`), handler
bunu `503 "Rules temporarily unavailable"` yapar (`app.py:554-564`).

**Etki.** Çalıştırılabilir uygulamada kural oluşturulabilir; sürüm eklenemez,
test edilemez, onaya gönderilemez, onaylanamaz, aktive veya pasifleştirilemez.
Kural yaşam döngüsü akışı ilk adımdan sonra tamamen durur.

**Neden iki tarafça da kaçırıldı.** Rapor akış 4 için "kod ekseninde kırılma
yok, runtime bellek içi store" diyordu; doğrulama raporu da bu akışı
sorgulamadı. İkisi de portun **hiç bağlanmadığını** kontrol etmedi.

**Kaydedildiği yer.** 03 akış 4 "Runtime ek kırılması" ve akış özet tablosu
(RT ⚠️ → 🔴); 06 kural tablosu satır 14-19 `MEVCUT` → `KISMİ` + uyarı bloğu.

### D-02 · "Maker-checker veritabanı seviyesinde korunur" ifadesi yanlıştı

**Kanıt.** 03 akış 4 bu güvenceyi `rule_approval_requests` üzerindeki kısmi
UNIQUE'e dayandırıyordu. O kısıt aynı nesne için birden çok açık talebi
engeller; maker ile checker'ın farklı aktörler olmasını zorlamaz. 14
migration'ın hiçbirindeki `CheckConstraint` kolon-kolon karşılaştırması
yapmaz (hepsi enum whitelist, sayısal sınır veya digest öneki).

**Kaydedildiği yer.** 03 akış 4 düzeltme bloğu; 09 §6.4 ve 10 §4.4 "DB
düzeyinde zorlama yok" satırları.

## 7. Kanıt sınırları

- Uygulama **ayağa kaldırılmadı**; `run_dev.py` ile ilgili tespitler statik
  okumaya dayanır. Şema ayrışması ve `_FakePreparedRepo` uyuşmazlığı statik
  olarak kesindir; bunların çalışan sistemdeki net sonucu (hangi isteğin hangi
  hatayla döneceği) ölçülmemiştir.
- `503` bulgusu (D-01) bağlama kodunun okunmasıyla tespit edilmiştir; HTTP
  isteğiyle doğrulanmamıştır.
- Entegrasyon testleri bu ortamda **hiç yürümedi** (`92 skipped`). PG
  davranışına ilişkin tüm değerlendirmeler test **kodunun** okunmasına
  dayanır.
- Frontend tarafında yalnız `dataSources/api.ts` çağrı zinciri doğrulandı;
  kapsamlı bir frontend denetimi yapılmadı.

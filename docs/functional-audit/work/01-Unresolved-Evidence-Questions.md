---
type: functional-audit-work
stage: "01 — Çözülmemiş Kanıt Soruları"
parent: ../01-Current-Capabilities.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-04
---

# 01 — Çözülmemiş Kanıt Soruları

> [01-Current-Capabilities.md](../01-Current-Capabilities.md) yazılırken statik kod
> okumasıyla kesinleştirilemeyen konular. Her madde, sonraki denetim aşamasının
> doğrudan yürütebileceği bir doğrulama planı içerir.
>
> Bu dosya **soru** kaydeder; çözüm veya tasarım önerisi içermez.

## Öncelik ölçeği

| Öncelik | Anlamı |
|---|---|
| **P-A** | Yanıtı, `01-Current-Capabilities.md` içindeki bir durum etiketini değiştirir |
| **P-B** | Yanıtı, bir bulgunun kapsamını veya güven düzeyini değiştirir |
| **P-C** | Bağlam netleştirir, mevcut bulguyu değiştirmez |

---

### Q-01 — Üretim composition root gerçekten yok mu?

- **İlgili yetenek / bulgu:** §2.1, §2.3 — çalıştırılabilir sistem sınırı
- **Soru:** `create_dashboard_api()`'yi PostgreSQL repository'leriyle dolduran bir
  üretim bileşimi repository dışında mı tutuluyor, yoksa hiç yazılmadı mı?
- **Şu ana kadarki kanıt:**
  `create_dashboard_api` çağıranlar: [development.py](../../../src/veri_kalitesi/api/development.py),
  `tests/unit/test_*_api.py` (9 dosya),
  `tests/integration/test_postgresql_lineage_evidence.py`.
  `pyproject.toml`'da `console_scripts` yok. Üretim Dockerfile yok.
- **Neden çözülemedi:** Repository dışı deployment yapılandırması bu denetimin
  görüş alanında değil. `agent-loop` altyapısının repo dışında tutulduğu proje
  hafızasında kayıtlı; benzer bir ayrım burada da geçerli olabilir.
- **Doğrulama planı:**
  1. `git log --all --oneline -- '*composition*' '*bootstrap*' '*main.py*' '*asgi*'`
  2. `grep -rn "create_dashboard_api" archive/ infra/ tools/ 2>/dev/null`
  3. `docs/memory/Alinan-Kararlar.md` içinde deployment/composition kararı arama
  4. Kullanıcıya sorulması: üretim bileşimi ayrı bir depoda mı?
- **Hangi bulguyu değiştirir:** Eksen B etiketlerinin tamamı. Repo dışında bir
  üretim bileşimi varsa, `MOCK_ONLY` etiketleri "bu repo içinde doğrulanamaz"
  olarak yeniden ifade edilmelidir.
- **Öncelik:** **P-A**

---

### Q-02 — PostgreSQL entegrasyon testleri en son ne zaman gerçekten koştu?

- **İlgili yetenek / bulgu:** §9.2 — test kapsamı gerçeği
- **Soru:** 11 skip-gated entegrasyon dosyası `DATA_QUALITY_POSTGRES_TEST_URL` ile
  koşturulduğunda geçiyor mu? `Mevcut-Durum.md:16`'daki "44/44 gerçek PostgreSQL
  16.13 üzerinde" iddiası bugün yeniden üretilebilir mi?
- **Şu ana kadarki kanıt:** Her dosyada `pytestmark = pytest.mark.skipif(not POSTGRES_TEST_URL, …)`.
  `conftest.py` kökteki `.env`'i yüklüyor; `.env` bu worktree'de yok
  (`ls -a | grep -i env` → boş çıktı).
- **Neden çözülemedi:** Canlı PostgreSQL örneği ve `.env` bu oturumda mevcut
  değildi; denetim salt okunur yürütüldü.
- **Doğrulama planı:**
  1. `docker run -d -p 55432:5432 -e POSTGRES_USER=dqtest -e POSTGRES_PASSWORD=dqtest -e POSTGRES_DB=data_quality postgres:16.13-alpine3.22`
  2. `export DATA_QUALITY_POSTGRES_TEST_URL=postgresql+psycopg://dqtest:dqtest@127.0.0.1:55432/data_quality`
  3. `cd . && alembic upgrade head`
  4. `pytest docs/testing/02-Entegrasyon -v` → geçen/atlanan/başarısız sayımı kaydet
- **Hangi bulguyu değiştirir:** §9.3 "yalnız test içinde yaşayan yetenekler"in
  kanıt gücü. Testler bugün kırıksa, PostgreSQL repository'lerinin Eksen A durumu
  `IMPLEMENTED`'dan `BROKEN`'a düşer.
- **Öncelik:** **P-A**

---

### Q-03 — Doğrulama baseline'ı bugün üretilebiliyor mu?

- **İlgili yetenek / bulgu:** §1.3, §9.1
- **Soru:** `Mevcut-Durum.md:35-38`'deki backend `1125 passed, 27 skipped` ve
  frontend `95` Vitest sayıları bu worktree'de yeniden üretilebiliyor mu?
- **Şu ana kadarki kanıt:** Belge, bu baseline'ın 24 Temmuz 2026 oturumunda
  bağımlılık/servis erişimi nedeniyle **bağımsız yeniden üretilemediğini** zaten
  kaydediyor. Aradan geçen sürede 297 dosya değişmiş (Q-11).
- **Neden çözülemedi:** Bu denetimde hiçbir test koşulmadı (bilinçli kapsam kararı).
- **Doğrulama planı:**
  1. `pytest tests -q --tb=no` → sayım
  2. `cd frontend && npm ci && npm run test -- --run` → sayım
  3. `npm run typecheck && npm run build`
  4. Sonuçları tarih damgasıyla kaydet
- **Hangi bulguyu değiştirir:** §9 bölümünün tamamının güven düzeyi.
- **Öncelik:** **P-B**

---

### Q-04 — `run_dev.py` gerçekten ayağa kalkıyor mu; hangi endpoint'ler patlıyor?

- **İlgili yetenek / bulgu:** §2.1, §2.2, tüm Eksen B etiketleri
- **Soru:** Migration'ları uygulanmış bir PostgreSQL varken uygulama başlıyor mu?
  Başlamıyorsa Eksen B etiketleri `MOCK_ONLY` değil `BROKEN` olmalıdır.
  Ayrıca §3.8'deki "başlatılan çalıştırma listede görünmez" tespiti canlı olarak
  doğrulanmalıdır.
- **Şu ana kadarki kanıt:** [run_dev.py:10](../../../scripts/run_dev.py) sabit URL;
  [development.py:1332-1344](../../../src/veri_kalitesi/api/development.py)
  PostgreSQL execution servisi; [development.py:585-600](../../../src/veri_kalitesi/api/development.py)
  statik `DevelopmentExecutionReader`.
- **Neden çözülemedi:** Uygulama bu oturumda ayağa kaldırılmadı.
- **Doğrulama planı:**
  1. Q-02 adım 1–3 ile PostgreSQL hazırla
  2. `python run_dev.py` (veya `uvicorn run_dev:app`)
  3. `GET /api/v1/openapi.json` → 44 endpoint doğrula
  4. Her endpoint'e dev kullanıcı başlığıyla smoke isteği; 5xx dönenleri listele
  5. **Kritik senaryo:** `POST /api/v1/executions` ile bir çalıştırma başlat →
     `GET /api/v1/executions` yanıtında görünüyor mu? → `persistent_jobs`
     tablosunda job `QUEUED`'da mı kalıyor?
- **Hangi bulguyu değiştirir:** §3.8 ve §3.10'un `BROKEN` etiketleri kesinleşir
  veya düşer; §4/D ve §4/H akış tespitleri doğrulanır.
- **Öncelik:** **P-A**

---

### Q-05 — Job worker hiç çalışmıyorsa kuyruğa giren iş ne oluyor?

- **İlgili yetenek / bulgu:** §3.10, §4/D
- **Soru:** `create_persistent_job_runtime()` hiç çağrılmadığına göre, execution
  start ile enqueue edilen `EXECUTION` job'u ve rapor için `REPORT` job'u
  kuyrukta süresiz mi kalıyor? Lease timeout / dead-letter yolu üretimde hiç
  yürümüyor mu? Rapor akışında `inline_processing=True` kuyruğu tamamen mi
  atlıyor, yoksa hem enqueue edip hem inline mı üretiyor (çift işlem riski)?
- **Şu ana kadarki kanıt:**
  [jobs/composition.py](../../../src/veri_kalitesi/jobs/composition.py)
  tanımlı ama çağrılmıyor; [worker.py:76](../../../src/veri_kalitesi/jobs/worker.py)
  `run_forever` çağrısız; `reporting/service.py` içinde `PostgreSQLJobQueueRepository`
  referansı var ve dev bileşiminde `inline_processing=True`.
- **Neden çözülemedi:** `ReportService.inline_processing` bayrağının enqueue
  davranışını tamamen atlayıp atlamadığı okunmadı.
- **Doğrulama planı:**
  1. `src/veri_kalitesi/reporting/service.py` içinde `inline_processing`
     kullanım noktalarını oku
  2. Q-04 ortamında bir rapor talep et → `persistent_jobs` tablosunda `REPORT`
     satırı oluşuyor mu kontrol et
  3. Bir execution başlat → `SELECT status, attempt_count, lease_expires_at FROM
     dq.persistent_jobs` ile 10 dakika sonra tekrar bak
- **Hangi bulguyu değiştirir:** §3.10 ve §3.14; çift işlem varsa yeni bir
  veri bütünlüğü bulgusu doğar.
- **Öncelik:** **P-A**

---

### Q-06 — Playwright E2E spec'leri gerçek backend'e mi bağlanıyor?

- **İlgili yetenek / bulgu:** §9.5
- **Soru:** 7 E2E spec, çalışan bir FastAPI'ye mi yoksa `page.route()` ile
  yakalanan mock yanıtlara mı karşı koşuyor? İkincisi ise E2E kanıtı uçtan uca
  değil, yalnız frontend render kanıtıdır.
- **Şu ana kadarki kanıt:**
  [playwright.config.ts:16-20](../../../frontend/playwright.config.ts) yalnız
  `npm run dev` (Vite) ayağa kaldırıyor; backend `webServer` tanımı yok.
  `App.tsx` içinde `?state=` query parametresiyle DEV modunda fixture durumları
  seçilebiliyor (`fixtureState` deseni, örn. `ReportsRoute`).
- **Neden çözülemedi:** Spec dosyalarının içeriği okunmadı.
- **Doğrulama planı:**
  1. `grep -rn "page.route\|?state=\|mock\|intercept" frontend/e2e/`
  2. `grep -rn "VITE_API" frontend/` ile proxy/base URL yapılandırması
  3. `frontend/vite.config.ts` içinde `server.proxy` kontrolü
- **Hangi bulguyu değiştirir:** §5 matrisindeki `E2E` işaretlerinin anlamı;
  fixture tabanlıysa E2E sütunu "render kanıtı" olarak yeniden etiketlenmelidir.
- **Öncelik:** **P-B**

---

### Q-07 — `enterprise_lab/` adaptörleri hangi çalışabilir bileşime bağlı?

- **İlgili yetenek / bulgu:** §3.22, §10.3
- **Soru:** ENTERPRISE-LAB-03 "sekiz healthy servis ve gerçek container ağında
  doğrulandı" diyor. Bu doğrulama uygulamanın kendisini mi kapsıyor, yoksa yalnız
  `adapter-e2e` container'ının adaptör sınıflarını doğrudan çağırmasını mı?
  `enterprise_lab/adapters.py` çalışabilir hiçbir API bileşimine bağlı değil.
- **Şu ana kadarki kanıt:**
  `infra/enterprise-lab/compose.yaml` içinde `adapter-e2e` servisi
  (profile: acceptance); `create_development_app()` içinde hiçbir lab adaptörü
  referansı yok; `test_enterprise_lab.py` ve `test_enterprise_lab_adapters.py`
  birim testleri mevcut.
- **Neden çözülemedi:** Compose kabul kapısının ne çalıştırdığı okunmadı.
- **Doğrulama planı:**
  1. `infra/enterprise-lab/compose.yaml` `adapter-e2e` servisinin
     `command`/`entrypoint`'ini oku
  2. `docs/iterations/ENTERPRISE-LAB-03-Canli-Compose-Uctan-Uca-Dogrulama.md`
     kapanış kanıtı bölümünü oku
  3. Keycloak'ın gerçekten `BffSessionBoundary` üzerinden mi yoksa doğrudan
     adaptör çağrısıyla mı doğrulandığını belirle
- **Hangi bulguyu değiştirir:** §3.17 (kimlik) ve §3.22 satırları; "kurumsal
  kimlik doğrulama doğrulandı" iddiasının kapsamı.
- **Öncelik:** **P-B**

---

### Q-08 — `DOCUMENTATION_INDEX.md`, `DOCUMENTATION_AUDIT.md`, `NEXT_STEP.md`, `AGENTS.md` silindi mi, hiç yazılmadı mı?

- **İlgili yetenek / bulgu:** §10.1
- **Soru:** README ve denetim prompt'unun atıf yaptığı bu dört dosya bir zamanlar
  var mıydı? Silindiyse hangi commit'te ve neden?
- **Şu ana kadarki kanıt:** Dördü de bugün yok. `README.md:10,12,32,45,49` ve
  `iterations/:26` bunlara bağlantı veriyor.
- **Neden çözülemedi:** Git geçmişi taranmadı.
- **Doğrulama planı:**
  1. `git log --all --diff-filter=D --name-only -- DOCUMENTATION_INDEX.md DOCUMENTATION_AUDIT.md NEXT_STEP.md AGENTS.md`
  2. `git log --all --oneline -- NEXT_STEP.md | head`
  3. `ls archive/` altında taşınmış olabilecek karşılıklarını ara
- **Hangi bulguyu değiştirir:** §10.1'in niteliği — "kırık bağlantı" mı yoksa
  "arşive taşınmış, README güncellenmemiş" mi.
- **Öncelik:** **P-C**

---

### Q-09 — Prototip modüllerinin composition'a bağlanmaması kalıcı bir durum mu?

- **İlgili yetenek / bulgu:** §3.19, §3.7, §10.3
- **Soru:** `DQ-CAP-PROTOTYPE-05` kaydı "modüller henüz composition'a bağlı değil
  ve bağımsız review `CHANGES_REQUESTED`" diyor. Bu geçici bir ara durum mu,
  yoksa prototip modüllerinin bilinçli olarak bağlanmadığı kalıcı bir tasarım
  kararı mı? `CHANGES_REQUESTED` review'ı kapatıldı mı?
- **Şu ana kadarki kanıt:**
  `iterations/:14`; `notifications/channel_adapters.py` yalnız
  `notifications/__init__.py` export'unda ve `test_prototype_05_capabilities.py`
  içinde görünüyor. Buna karşılık `ExecutionStrategyEngine` **bağlanmış**
  ([development.py:1338](../../../src/veri_kalitesi/api/development.py)) —
  yani beş prototipin çıktıları eşit muamele görmemiş.
- **Neden çözülemedi:** Review kararının güncel durumu ve backlog niyeti
  okunmadı.
- **Doğrulama planı:**
  1. `docs/iterations/DQ-CAP-PROTOTYPE-05-Bildirim-Kanal-Lab-Kapisi-Strateji-Motoru.md`
     tam okuma
  2. `docs/memory/Sonraki-Adimlar.md` içinde ilgili backlog maddesi
  3. `docs/memory/Acik-Konular.md` içinde bağlantılı açık karar
- **Hangi bulguyu değiştirir:** §3.19'un `MODEL_ONLY` etiketi kalır ama nedeni
  "eksiklik" yerine "planlı prototip sınırı" olarak nitelenebilir.
- **Öncelik:** **P-C**

---

### Q-10 — Skorlama neden PostgreSQL cutover'ın dışında kaldı?

- **İlgili yetenek / bulgu:** §3.11, §7.3
- **Soru:** 36E-PG-CUTOVER kapsamı skorlamayı içeriyor muydu? `quality_scores`
  tablosunun yokluğu bilinçli bir kapsam kararı mı, yoksa atlanmış bir iş mi?
  Katkı grafiği (migration 13) PostgreSQL'e taşınırken skorun kendisinin SQLite'ta
  kalması tutarlı mı?
- **Şu ana kadarki kanıt:** `20260730_13_score_contribution_graphs.py` yalnız
  `score_contribution_graphs` tablosunu yaratıyor;
  [scoring/repository.py](../../../src/veri_kalitesi/scoring/repository.py)
  ve `partial_score_policies.py` `SQLiteTransactionalAudit` kullanıyor;
  `PostgreSQLContributionGraphRepository` yalnız testte örnekleniyor.
- **Neden çözülemedi:** 36E iterasyon kaydı okunmadı (aktif yedi iterasyon
  listesinde değil, arşivde).
- **Doğrulama planı:**
  1. `grep -rl "36E" docs/iterations/ archive/iterations/`
  2. Bulunan kaydın kapsam ve kapsam-dışı bölümlerini oku
  3. `docs/memory/Karar-Kayitlari/` altında skorlama kalıcılığı kararı ara
- **Hangi bulguyu değiştirir:** §3.11'in `PARTIAL` etiketi kalır; "eksiklik" mi
  "bilinçli kapsam dışı" mı ayrımı netleşir.
- **Öncelik:** **P-B**

---

### Q-11 — Denetim `main`'i mi bu worktree'yi mi esas almalı?

- **İlgili yetenek / bulgu:** §1.3 — kapsam sınırı
- **Soru:** Denetim prompt'u "repository'nin güncel ana branch'ini esas al" diyor.
  Bu denetim `agent/36h1-persistent-job-core` worktree'sinde yapıldı ve
  `git diff main --stat` **297 dosya, +24498/−2486 satır** fark gösteriyor.
  68 dosya ayrıca commit edilmemiş. Bulgular `main`'de de geçerli mi?
- **Şu ana kadarki kanıt:** `git status --porcelain | wc -l` → 68;
  `git rev-parse --abbrev-ref HEAD` → `agent/36h1-persistent-job-core`;
  `git diff main --stat` → 297 dosya.
- **Neden çözülemedi:** Fark bu oturumda incelenmedi; kullanıcı talimatı bu
  çalışma alanını işaret ediyordu.
- **Doğrulama planı:**
  1. `git diff main --stat -- src/veri_kalitesi/api/development.py run_dev.py src/veri_kalitesi/jobs/`
     → §2 bulgularının `main`'de de geçerli olup olmadığı
  2. `git show main:src/veri_kalitesi/api/development.py | grep -n "DevelopmentIssueStore\|PostgreSQLExecutionStartService"`
  3. `git show main:run_dev.py` ile bileşim farkı
  4. Kullanıcıya sorulması: denetim hangi referansa göre raporlanmalı?
- **Hangi bulguyu değiştirir:** Potansiyel olarak dokümanın tamamının geçerlilik
  sınırı. En azından üst bilgiye açık bir "bu referans üzerinde geçerlidir" notu
  gerekir (şu an frontmatter'da `branch` alanı var).
- **Öncelik:** **P-A**

---

### Q-12 — `ReportService.inline_processing` ve `ReportsRoute` bağlantısızlığı bilinçli mi?

- **İlgili yetenek / bulgu:** §3.15, §6.2
- **Soru:** `ReportsPage` zamanlama props'ları (`scheduleItems`,
  `onCreateSchedule`, `onDeleteSchedule`) ve `reports/api.ts` istemci
  fonksiyonları yazılmış, Vitest ile test edilmiş; ama `ReportsRoute` bunları
  bağlamamış. Bu yarım kalmış bir iş mi, yoksa bilinçli olarak devre dışı
  bırakılmış bir yüzey mi?
- **Şu ana kadarki kanıt:**
  [App.tsx:61](../../../frontend/src/App.tsx) import var, kullanım yok;
  [ReportsPage.tsx:59-65](../../../frontend/src/reports/ReportsPage.tsx) props tanımlı;
  [ReportsPage.tsx:747](../../../frontend/src/reports/ReportsPage.tsx)
  `scheduleItems = syntheticSchedules` varsayılanı — kullanıcı sentetik veri görür;
  `reports/api.test.ts:182-269` üç fonksiyonu da test ediyor.
- **Neden çözülemedi:** İlgili iterasyon kaydının kapsam-dışı bölümü okunmadı.
  Ayrıca lint'in kullanılmayan import'u neden yakalamadığı belirsiz.
- **Doğrulama planı:**
  1. `cd frontend && npm run lint` → kullanılmayan import uyarısı var mı?
  2. `git log -p --follow -- frontend/src/reports/ReportsPage.tsx | grep -n "scheduleItems"` ile ne zaman eklendiği
  3. 36G iterasyon kaydında rapor zamanlaması UI'ının kapsam içi olup olmadığı
- **Hangi bulguyu değiştirir:** §3.15'in `BROKEN` etiketi; bilinçli devre
  dışıysa `PARTIAL`'a düşebilir. Ayrıca "kullanıcı sentetik zamanlama görüyor"
  tespitinin ciddiyeti.
- **Öncelik:** **P-B**

---

### Q-13 — Şema adı tutarsızlığı sorun üretiyor mu?

- **İlgili yetenek / bulgu:** §7.1
- **Soru:** `alembic.ini` şema adı olarak `dq` kullanıyor
  (envanter kaydı), `run_dev.py:11` ise `SCHEMA = "data_quality"` tanımlıyor ve
  `CREATE SCHEMA IF NOT EXISTS "data_quality"` çalıştırıyor. Migration'lar `dq`
  şemasına yazıyorsa, uygulama `data_quality` şemasında boş tablolar mı arıyor?
- **Şu ana kadarki kanıt:** [run_dev.py:11,26](../../../scripts/run_dev.py);
  `persistence/database.py` içinde `DEFAULT_SCHEMA_NAME`;
  `04-Database-Schema-Inventory.md` "Schema: `dq` (configurable via `alembic.ini`)".
- **Neden çözülemedi:** `alembic.ini` ve `DEFAULT_SCHEMA_NAME` değeri
  okunmadı.
- **Doğrulama planı:**
  1. `grep -n "schema" alembic.ini alembic/env.py`
  2. `grep -n "DEFAULT_SCHEMA_NAME" src/veri_kalitesi/persistence/*.py`
  3. Q-04 ortamında `\dn` ve `\dt dq.*` / `\dt data_quality.*` ile hangi şemada
     tablo olduğunu doğrula
- **Hangi bulguyu değiştirir:** Doğrulanırsa §3.8/§3.10'un `BROKEN` etiketleri
  için ek bir kök neden; `run_dev.py` hiç çalışmıyor olabilir.
- **Öncelik:** **P-A**

---

### Q-14 — `data_sources/postgresql.py` ile `postgresql_driver.py` arasındaki üç `discover_metadata` tanımı ne anlama geliyor?

- **İlgili yetenek / bulgu:** §3.3
- **Soru:** `postgresql.py` içinde üç ayrı `discover_metadata` tanımı var
  (L73, L137, L226). Bunlar protokol + implementasyon + delegasyon mu, yoksa
  mükerrer/çelişkili bir model mi? (Denetim prompt'u §1.12: "mükerrer, çelişkili
  veya parçalanmış modeller")
- **Şu ana kadarki kanıt:**
  `grep -n "discover_metadata" src/veri_kalitesi/data_sources/postgresql.py`
  → L73, L137, L226, L232 (`return self.driver.discover_metadata(...)`).
- **Neden çözülemedi:** Dosya tam okunmadı; §3.3'ün odağı API eksikliğiydi.
- **Doğrulama planı:**
  1. `src/veri_kalitesi/data_sources/postgresql.py` tam okuma
  2. `connectors.py` ve `postgresql_driver.py` ile sorumluluk ayrımını çıkar
  3. Aynı desenin diğer connector tipleri (CSV, MSSQL, Oracle, MySQL, REST) için
     var olup olmadığını kontrol et — `SourceType` yedi değer içeriyor ama kaç
     connector gerçekten uygulanmış?
- **Hangi bulguyu değiştirir:** §3.2/§3.3; yalnız PostgreSQL connector'ı
  uygulanmışsa "veri kaynağı onboarding `IMPLEMENTED`" etiketi kaynak tipine göre
  daraltılmalıdır.
- **Öncelik:** **P-B**

---

### Q-15 — Dev bileşimindeki rol kontrolleri gerçek yetki kapısı mı?

- **İlgili yetenek / bulgu:** §5.1, §8.1
- **Soru:** `DevelopmentActorContextResolver` her kullanıcıya sabit
  `{DATA_VIEWER, DATA_STEWARD, AUDIT_VIEWER}` rollerini ve
  `can_view_enterprise=True` veriyor. Dev store'lardaki rol kontrolleri
  ([development.py:767,798,823](../../../src/veri_kalitesi/api/development.py))
  bu sabit kümeyle her zaman geçiyor mu? Öyleyse çalışabilir uygulamada **hiçbir
  yetki reddi senaryosu test edilemiyor** demektir.
- **Şu ana kadarki kanıt:** [development.py:1316-1325](../../../src/veri_kalitesi/api/development.py)
  sabit rol kümesi; L767 `{"DATA_STEWARD","DATA_GOVERNANCE_SPECIALIST"}` kesişimi
  → `DATA_STEWARD` her zaman mevcut, kontrol her zaman geçer.
- **Neden çözülemedi:** `DEVELOPMENT_USER_REGISTRY` içindeki kullanıcıların rol
  ve scope farklılıkları okunmadı (L133-L141 üç kullanıcı tanımlı).
- **Doğrulama planı:**
  1. `sed -n '120,150p' src/veri_kalitesi/api/development.py` ile
     kullanıcı kayıt defterini oku
  2. `DevelopmentActorContextResolver.resolve()` gövdesini oku — registry
     kullanıcısının rolleri sabit kümeyi eziyor mu?
  3. Q-04 ortamında farklı `X-Development-User-Id` başlıklarıyla 403 alınabiliyor
     mu dene
- **Hangi bulguyu değiştirir:** §5.1'deki "durum geçişi var, yetki kontrolü yok"
  satırının ciddiyeti ve §8.1'in sonucu.
- **Öncelik:** **P-B**

---

## Özet

| Öncelik | Sorular |
|---|---|
| **P-A** — durum etiketini değiştirir | Q-01, Q-02, Q-04, Q-05, Q-11, Q-13 |
| **P-B** — kapsam/güven değiştirir | Q-03, Q-06, Q-07, Q-10, Q-12, Q-14, Q-15 |
| **P-C** — bağlam netleştirir | Q-08, Q-09 |

P-A sorularının çoğu **tek bir ortam kurulumuyla** (canlı PostgreSQL + `.env` +
`alembic upgrade head` + `run_dev.py`) birlikte yanıtlanabilir: Q-02, Q-04, Q-05
ve Q-13 aynı oturumda çözülür.

---
type: functional-audit-work
stage: "08 — İlk Dilim Kararı"
scope: first-slice-decision
inputs:
  - 07-Implementation-Waves.md
  - 06-Vertical-Slice-Candidates.md
  - ../04-Functional-Gap-Inventory.md
  - ../12-Prioritized-Backlog.md
  - ../06-API-Inventory-and-Gaps.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-05
---

# 08 — İlk Dilim Kararı

> `07-Implementation-Waves.md` D1 dalgasına iki dilim koydu: **S1** (GAP-027, komut
> yolu güvenliği) ve **S2** (GAP-001 + GAP-002, kalıcılık ve worker). İkisi de
> topolojik seviye 0'da ve `P0`. Uygulamaya tek dilimle başlanacaksa hangisinin
> **önce** geldiği kararı verilmemişti. Bu belge o kararı verir; seçilen dilimin
> gerekçesini, kapsamını ve kabul kriterlerini yazar.
>
> Bu belge yeni GAP veya yeni dilim tanımlamaz; `07`'nin D1 dalgasının içini açar.

---

## 1. Karar

**İlk uygulanacak dilim: S1 — Veri kaynağı komut yolu güvenliği (GAP-027).**

Kapsam, `07 §5`'teki S1 tanımından bir noktada daralmıştır: bu iterasyonda GAP-027'nin
yalnız **veri kaynağı komut ailesi** ele alınır. Kural oluşturmada kapsam `403`'ü ve
manuel çalıştırma doğrulaması (GAP-027 kriter 3-4) ayrı bir kaleme bırakılmıştır (§4.2).

---

## 2. Seçim gerekçesi

### 2.1 Karşılaştırma

| Ölçüt | S1 (GAP-027) | S2 (GAP-001 + GAP-002) | Kaynak |
|---|---|---|---|
| Aciliyet | 19 | 29 / 26 | `12 §2` |
| Karmaşıklık | **2** | 4 / 3 | `12 §2` |
| Mimari uyum | 5 | 5 | `12 §2` |
| Migration | Yok — tablolar hazır | Yok | `04`; migration 03 |
| Açık kanıt sorusu | Yok | **Q-01 açık** | `04 §5` |
| Erken kazanım listesinde | **Evet** | Hayır | `12 §2.2` |

Aciliyet puanı S2'yi işaret eder, karmaşıklık ve risk S1'i. Karar aşağıdaki dört
gerekçeyle S1 lehine verilmiştir.

### 2.2 Sıra, yeniden yapılan işi belirliyor

S1 **port sözleşmesini** düzeltir: `DataSourceMutationService.activate(data_source_id)`
imzası bir aktör parametresi bile taşımaz (`api/app.py:335`). S2 ise aynı sözleşmenin
*arkasındaki* repository'yi değiştirir (bellek içi store → PostgreSQL).

- S1 önce yapılırsa: S2, aktör bağlamını zaten taşıyan doğru sözleşmeye bağlanır.
- S2 önce yapılırsa: aynı dört route ve aynı protokol ikinci kez elden geçirilir.

### 2.3 S2 bypass'ı kapatmıyor

`06 §3`'ün S2 kaydındaki not açıktır: *"Bu dilim tamamlandığında dahi komut yolu
yetki denetimi çalışmaz; S1 ayrıca ele alınmalıdır."* Nedeni kanıtlanabilir —
`POST /api/v1/data-sources/{id}/activation` route'u (`api/app.py:2073-2082`)
çözülmüş `ActorContext`'i porta iletmez. Repository'nin PostgreSQL olması bunu
değiştirmez; eksik olan bir `if` değil, sözleşmenin kendisidir.

Buna karşılık aynı dosyadaki kural ve sorun route'ları bağlamı **iletir**
(`app.py:1838-1841`). Yani bu bir tasarım tercihi değil, tutarsızlıktır.

### 2.4 S1 açık kanıt sorusuna bağımlı değil

`04 §5`'teki **Q-01** — üretim composition root'unun repo dışında olup olmadığı —
hâlâ açıktır ve "evet" yanıtı GAP-001, GAP-002, GAP-003 ve GAP-007'nin runtime
eksenini değiştirir. S2 bugün başlarsa kapsamı bu yanıta bağlı kalır. S1'in böyle
bir bağı yoktur; `04 §4` GAP-027'yi açıkça bağımsız olarak işaretler
(*"GAP-001 ve GAP-022'yi beklemez"*).

### 2.5 Yanlış güvence her gün maliyet üretiyor

İki test bypass'ı **doğru davranış olarak sabitliyor**:

| Test | Sorun |
|---|---|
| `test_data_source_api.py:360` | Onaysız `TEST_SUCCEEDED → ACTIVE` geçişi için `200` bekliyor |
| `test_rule_api.py:405` | Adı `..._returns_403` olduğu halde `201` assert ediyor; yorumu fake servisin kapsam kontrolü yapmadığını kabul ediyor |

İkisi de kapsam sayımında "yetki testi" olarak görünüyor. Bu, denetim yüzeyinde
gerçekte olmayan bir kontrolün var gibi durmasıdır (`04` K9).

### 2.6 Karşı argüman ve yanıtı

**Karşı argüman:** S2'nin aciliyeti daha yüksek (29 vs 19) ve diğer tüm dilimleri
bloke ediyor; ilk yapılması gereken odur.

**Yanıt:** "İlk" ile "en değerli" aynı şey değildir. S1 karmaşıklık 2'lik,
migration'sız, tek iterasyondan kısa bir iştir ve S2'yi kayda değer biçimde
geciktirmez. `07 §5`'te D1'in iki dilimi zaten paralel yürütülebilir olarak
işaretlenmiştir; tek takımla çalışılıyorsa S1'in önce gelmesi §2.2'deki yeniden
işi ortadan kaldırır.

---

## 3. Sıfırdan yazılmayacak olanlar

Denetim prompt'u §18'in "mevcut güçlü parçaların gereksiz yeniden yazılmaması"
kuralının bu dilimdeki somut karşılığı:

| Parça | Yer | Durum |
|---|---|---|
| Maker-checker kural kütlesi | `data_sources/service.py:390` `request_activation`, `:461` `decide_activation`, `:588` `withdraw_activation`, `:659` `expire_due_activations` | Yazılı ve testli |
| Yetki kontrolü | `service.py:1310` `_authorize_activation_actor` — rol, kapsam, politika sürümü, bağlam geçerlilik süresi, aktör tipi | Yazılı |
| Maker ≠ checker kuralı | `service.py:487-488` | Yazılı |
| Aynı transaction'da audit | `service.py:534-540` — `decide_activation_request(..., audit_event=prepare(event), audit_outbox=...)` ve ardından `publish_pending()` | Yazılı |
| PostgreSQL kalıcılığı | `data_sources/postgresql_repository.py:998` `add_activation_request`, `:1032` `decide_activation_request`, `:1119` `withdraw`, `:1132` `expire`, `:479` `count_pending_activation_requests_except` | Yazılı |
| Tablolar | `alembic/versions/20260724_03_data_source_baseline.py:297` `data_source_activation_requests` | **Hazır — yeni migration yok** |
| Bağlam iletme deseni | `api/app.py:1838-1841` (kural aktivasyonu) | Kopyalanacak desen |
| Çok kullanıcılı aktör | `api/identity.py:91` `build_default_development_users`; `X-Development-User-Id` header'ı | Yazılı; frontend zaten gönderiyor (`development/fetch.ts`) |

Bu dilimde yazılacak olan yeni iş kuralı **yoktur**; yazılacak olan, mevcut kuralları
çalıştırılabilir komut yüzeyine bağlayan sözleşme ve bileşimdir.

---

## 4. Kapsam

### 4.1 Dahil

**(a) Bileşim — gerçek veritabanı.** `DevelopmentDataSourceStore`
(`api/development.py:885-985`) kaldırılır. Yerine gerçek `DataSourceService` kurulur:

| Bileşim yolu | Repository |
|---|---|
| `session_factory` verildiğinde (`run_dev.py`) | `PostgreSQLDataSourceRepository`, açık `schema=` argümanıyla |
| `session_factory` verilmediğinde (birim testleri) | `SQLiteDataSourceRepository(":memory:")` |

İkinci yol bir "dev store" değildir: aynı servis, aynı kurallar, yalnız repository
farklıdır. Kural kütlesi hiçbir yerde ikinci kez yazılmaz.

> **Varsayım.** "Yalnız PostgreSQL, fallback yok" tercih edilirse mevcut veri
> kaynağı API testlerinin tümü PG'ye bağımlı (skip-gated) hale gelir. Bu belge
> fallback'li yolu varsayar.

**(b) Aktivasyon iki adıma ayrılır.** `06-API-Inventory-and-Gaps.md:96` mevcut ucu
zaten `D03.C02.W01.A01` *aktivasyon talebi* olarak tanımlıyor:

| Uç | Aktör | Servis çağrısı |
|---|---|---|
| `POST /data-sources/{id}/activation` (mevcut) | maker | `request_activation` |
| `POST /data-sources/{id}/activation-decision` (**yeni**) | checker | `decide_activation` |

**(c) Aktivasyon politikası** bileşimde tanımlanır: `actor_policy_version=POLICY_VERSION`,
`maker_roles={"DATA_STEWARD"}`, `checker_roles={"DATA_OWNER"}`,
`allowed_actor_types={"USER"}`. `target_business_days` ve `expiration_business_days`
`None` bırakılır — iş takvimi bağımlılığı bu dilime girmez.

**(d) Audit gerçekten yazılır.** `run_dev.py:14` `_FakePreparedRepo.store()` no-op'tur;
`publish_pending` ise `repository.append()` çağırır (`audit/postgresql_outbox.py:99`)
ve oluşan `AttributeError` satır 102'deki `except Exception` ile yutulur. Gerçek bir
`SQLiteAuditRepository` konur ve `create_development_app` içindeki `audit_repository`
(`development.py:1217`) ile **aynı örnek** paylaştırılır — aksi halde olay yazılır
ama `GET /api/v1/audit/events` göstermez.

**(e) Şema tutarlılığı.** Veri kaynağı repository'si ile audit outbox aynı şemaya
yazar ve şema bileşimde açıkça geçilir. Bugün `run_dev.py:11` audit'i `data_quality`
şemasına, `development.py` ise repository'leri `schema=` vermeden `dq`'ya yönlendirir
(`persistence/database.py:15`).

**(f) Seed.** Gerçek veritabanı boş başlar. `DEVELOPMENT_SOURCES`'taki dört kaynak
(`source-core-banking`, `source-customer-file`, `source-risk-mart`,
`source-regulatory-api`) idempotent biçimde yazılır; dev kullanıcıların
`permitted_source_ids` kapsamı bu kimliklere bakar (`identity.py:97-104`).

**(g) Hata eşlemesi.** Domain hataları API hatalarına çevrilir:
`data_sources/errors.py` `AuthorizationError` → `DataSourceQueryAuthorizationError`
(403), `ValidationError` → `DataSourceQueryValidationError`.

**(h) UI.** `DataSourcesPage`: "Aktive et" → "Aktivasyon talep et"; "Onay bekliyor
(talep eden: X)" durumu; farklı aktör için "Onayla"/"Reddet"; aynı aktör onaylamayı
denediğinde dönen `403` anlamlı mesaja çevrilir. `dataSources/api.ts`'e karar çağrısı
eklenir.

**(i) Testler.** §2.5'teki iki yanıltıcı test gerçek beklentiyi assert edecek biçimde
düzeltilir; yeni testler §5'teki kriterleri kapsar.

### 4.2 Hariç

| Konu | Neden |
|---|---|
| Kural oluşturmada kapsam `403`'ü (GAP-027 kriter 3) | Ayrı kalem; `test_rule_api.py:405`'te yalnız assert ve docstring düzeltilir |
| Manuel çalıştırma doğrulaması ve `"unknown"` aktör reddi (GAP-027 kriter 4) | Ayrı kalem |
| Kalıcı IAM, rol/izin tabloları | S3a (`07` D3); bu dilimde dev kullanıcı kayıt defteri kullanılır |
| Worker, iş kuyruğu, execution kalıcılığı | S2 (`07` D1) |
| Yeni rol tanımı | Mevcut `DATA_STEWARD` / `DATA_OWNER` kullanılır |
| Yeni migration | Gerekmiyor — tablolar migration 03'te |

---

## 5. Kabul kriterleri

| # | Kriter | Nasıl doğrulanır |
|---|---|---|
| K1 | `DataSourceMutationService` protokolünün dört metodu `actor_context` alır; dört route çözülmüş bağlamı porta iletir | `app.py:333-337` imzaları; route testleri |
| K2 | Aktivasyon iki adımlıdır: talep `201` döner ve kaynak hâlâ `TEST_SUCCEEDED` kalır; karar ayrı uçtan verilir | API testi |
| K3 | **maker = checker → `403`** ve kaynak `ACTIVE` olmaz | Aynı `X-Development-User-Id` ile talep + karar |
| K4 | Checker rolü olmayan aktör `403`; kapsam dışı kaynak `403`; bayat revizyon ve politika sürümü değişimi reddedilir | `dev-data-viewer` ve `dev-limited-steward` ile |
| K5 | Onaylanan kaynak veritabanında `ACTIVE`; talep `APPROVED` ve `checker_actor_id` dolu; **süreç yeniden başlatıldığında korunuyor** | PG'ye bağlı entegrasyon testi + elle yeniden başlatma |
| K6 | `DATA_SOURCE_ACTIVATION_DECIDED` aynı transaction'da outbox'a yazılıyor ve `GET /api/v1/audit/events`'te görünüyor | API testi; kod tabanında `_FakePreparedRepo` kalmamış olmalı |
| K7 | İş verisi ve audit outbox tek şemada; şema bileşimde açıkça geçiliyor | Bileşim okuması + veritabanında tablo kontrolü |
| K8 | `POST /data-sources` sahibi oturumdan alıyor; gövdedeki `owner_user_id` yetkiyi belirlemiyor | API testi: gövdede başka sahip verildiğinde oturum sahibi kazanır |
| K9 | UI'dan talep açılıp ikinci kullanıcıyla onaylanabiliyor; aynı kullanıcı denediğinde hata görünüyor | Frontend testi + elle tarayıcı doğrulaması |
| K10 | §2.5'teki iki test gerçek beklentiyi assert ediyor | `test_data_source_api.py:360`, `test_rule_api.py:405` |

**Dilim ancak K1-K10 birlikte sağlandığında bitmiş sayılır.** K3 ve K6 dilimin
özüdür: yetki reddi gözlenebilir olmalı ve reddin kanıtı değişmez deftere geçmelidir.
Diğerleri bu ikisinin gerçek olmasını sağlayan koşullardır.

### 5.1 Kapanan kök neden

Bu dilim tamamlandığında `03-End-to-End-Workflow-Audit.md`'deki **K9** (komut
yolunda onay ve kapsam bypass'ı) veri kaynağı ailesi için kapanır; kural ve
çalıştırma aileleri için §4.2'deki ayrı kalem beklenir.

---

## 6. Dokunulacak dosyalar

| Dosya | Değişiklik |
|---|---|
| `src/veri_kalitesi/api/app.py` | `DataSourceMutationService` protokolü (`:333-337`); dört route (`:2010-2110`) bağlam iletir; yeni `activation-decision` ucu; domain → API hata eşlemesi |
| `src/veri_kalitesi/api/development.py` | `DevelopmentDataSourceStore` (`:885-985`) kaldırılır; `:1328` ve `:1367` gerçek `DataSourceService`'e bağlanır; aktivasyon politikası; `audit_repository` enjekte edilebilir olur; seed |
| `run_dev.py` | `_FakePreparedRepo` → gerçek `SQLiteAuditRepository`; audit repo paylaşımı; şema tutarlılığı |
| `frontend/src/dataSources/{api,model}.ts`, `DataSourcesPage.tsx` | Talep/karar ayrımı, onay bekliyor durumu, karar butonları |
| `tests/unit/test_data_source_api.py` | `:360` düzeltilir; K1-K4, K6, K8 testleri |
| `tests/unit/test_rule_api.py` | `:405` yalnız assert ve docstring düzeltmesi |
| `tests/integration/` | K5 ve K7 için PostgreSQL'e bağlı test |

Yeni migration **yok**.

---

## 7. Kanıt sınırları

- Seçim gerekçesi `12 §2` puanlarına, `04 §4` bağımlılık haritasına ve `07 §5` dalga
  planına dayanır; bu üç girdinin ötesinde yeni bir ölçüt kullanılmamıştır.
- §2 ve §3'teki kod atıfları bu oturumda dosya üzerinde doğrulanmıştır; satır
  numaraları çalışma ağacındaki güncel duruma aittir ve sonraki değişikliklerle
  kayabilir.
- Kabul kriteri K5 ve K7 çalışan bir PostgreSQL örneği gerektirir; bu örneğin
  kurulumu bu belgenin kapsamı dışındadır ve operatör kararıdır.
- `04 §5`'teki **Q-01** açıktır. S1 bu soruya bağımlı değildir; ancak S2
  planlanmadan önce yanıtlanması gerekir.
- Kapsam daraltması (§4.2) GAP-027'yi kapatmaz, yalnız veri kaynağı ailesi için
  kapatır. GAP kaydı, kural ve çalıştırma aileleri tamamlanana kadar açık kalır.

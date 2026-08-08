stage: "06 — API Envanteri ve GAP'ler"
scope: api-inventory-and-gaps
inputs:
  - 02-Target-Capability-Hierarchy.md
  - 03-End-to-End-Workflow-Audit.md
  - 04-Functional-Gap-Inventory.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-04
---

# 06 — API Envanteri ve GAP'ler

> Fonksiyonel GAP envanteri (aşama 4), hedef kabiliyet hiyerarşisi (aşama 2) ve
> mevcut `app.py` route yüzeyi karşılaştırılarak üretilmiş **hedef API
> envanteri**. Her endpoint en az bir hedef fonksiyona (L4 yaprak) ve bir
> kullanıcı akışına bağlanır.

---

## 1. Kapsam ve yöntem

### 1.1 İlkeler

| İlke | Açıklama |
|---|---|
| Fonksiyon izlenebilirliği | Her endpoint ≥ 1 L4 yaprak kodu taşır |
| Akış bütünlüğü | §7'deki 8 akışın her adımı ya mevcut ya da hedef endpoint ile karşılanır |
| Sözleşme kalitesi | Hedef endpoint'ler idempotency, optimistic locking (`If-Match`), fail-closed ve veri-minimum ilkelerini taşır |
| Mevcut korunumu | Çalışan endpoint'ler korunur; eksik endpoint'ler eklenir |

### 1.2 Durum kodları

| Kod | Anlam |
|---|---|
| `MEVCUT` | Endpoint çalışır durumda (aşama 1 `app.py` doğrulaması) |
| `KISMİ` | Endpoint var; ancak bileşim, veri veya davranış eksikliği var |
| `HEDEF` | Endpoint yok; hedef model gereği oluşturulacak |

> **`MEVCUT` ne ölçer?** Yalnız endpoint'in tanımlı olduğunu ve yanıt
> verdiğini. Arkasındaki durum makinesinin, onay adımının veya kapsam
> kontrolünün çalıştığını **göstermez**. Denetim açısından belirleyici karşıt
> örnek `POST /data-sources/{id}/activation`'dır: endpoint çalışır, `200`
> döner ve testi geçer — fakat maker-checker onayını tamamen atlar (§3.2,
> GAP-027). Bu nedenle aşağıdaki tabloda, kontrolü atlayan uçlar `MEVCUT`
> değil `KISMİ` işaretlenmiştir.

### 1.3 Akış kısaltmaları

| Kod | Akış |
|---|---|
| A | Yeni kaynak onboarding |
| B | Kural yaşam döngüsü |
| C | Kalite problemi |
| D | Teknik hata |
| E | Şema drifti |
| F | Skor güvenilirliği |
| G | İstisna ve override |
| H | Raporlama |
| I | Kimlik ve yetki altyapısı (D02) |
| J | Yönetişim altyapısı (D01) |
| K | Veri sözleşmesi yaşam döngüsü (D10.C03) |
| L | Sentetik doğrulama (D15) |
| M | Bildirim altyapısı (D12) |

---

## 2. Sayısal özet

| Ölçüt | Değer |
|---|---|
| Mevcut endpoint (HTTP route) | **43** (22 GET, 19 POST, 1 DELETE, 1 POST session) |
| Hedefte tanımlı ek endpoint | **~85** |
| Toplam hedef endpoint | **~128** |
| GAP-001 etkisi | Mevcut endpoint'lerin yazma tarafı sahte depoda; PG'ye bağlanması gerekli |

---

## 3. Mevcut endpoint envanteri

Mevcut 43 route, `app.py` içindeki tanım sırasıyla.

### 3.1 Dashboard

| # | Yöntem | Yol | Fonksiyon | Akış | Durum |
|---|---|---|---|---|---|
| 1 | GET | `/dashboard/summary` | `D11.C01.W01.A01` yönetici görünümü | C, F | `KISMİ` — seed veri; GAP-008 |

### 3.2 Veri kaynakları

| # | Yöntem | Yol | Fonksiyon | Akış | Durum |
|---|---|---|---|---|---|
| 2 | GET | `/data-sources` | `D03.C01.W01.A01` kaynak listesi | A | `MEVCUT` |
| 3 | POST | `/data-sources` | `D03.C01.W01.A01` kaynak kaydı oluştur | A | `KISMİ` — PG composition (GAP-001); sahip **istek gövdesinden** alınıyor, aktör bağlamı iletilmiyor (GAP-027) |
| 4 | POST | `/data-sources/{id}/test` | `D03.C01.W03.A01` bağlantı testi | A | `KISMİ` — aktör bağlamı iletilmiyor (GAP-027) |
| 5 | POST | `/data-sources/{id}/activation` | `D03.C02.W01.A01` aktivasyon talep | A | `KISMİ` — **onay adımını atlıyor**; maker-checker, rol, kapsam ve audit yok (GAP-027) |
| 6 | POST | `/data-sources/{id}/passivation` | `D03.C02.W02.A01` pasifleştirme | A | `KISMİ` — aktör bağlamı iletilmiyor (GAP-027) |

> **Veri kaynağı komut ailesi uyarısı.** Bu dört route çözülen `ActorContext`'i
> mutation portuna iletmez (`api/app.py:2017-2110`). Bağlanan
> `DevelopmentDataSourceStore.activate` (`api/development.py:951-968`) yalnız
> `TEST_SUCCEEDED` guard'ı uygular; gerçek `DataSourceService.decide_activation`
> (`data_sources/service.py:461+`) ise checker rolü, süre, politika sürümü,
> bayat revizyon ve maker ≠ checker denetler. Aynı dosyadaki kural ve sorun
> route'ları bağlamı **iletir** (`app.py:984-986`, `1017-1019`, `1190-1192`),
> dolayısıyla bu bir tasarım tercihi değil tutarsızlıktır. `MEVCUT` etiketi
> endpoint'in yanıt vermesini ölçer; arkasındaki kontrolün çalıştığını değil.

### 3.3 Profilleme

| # | Yöntem | Yol | Fonksiyon | Akış | Durum |
|---|---|---|---|---|---|
| 7 | GET | `/profile-comparisons` | `D05.C04.W01.A01` profil karşılaştırma | E | `MEVCUT` |
| 8 | GET | `/profile-snapshots` | `D05.C01.W01.A01` profil listesi | A, E | `MEVCUT` |
| 9 | GET | `/profile-snapshots/{id}` | `D05.C02.W01.A01` profil detayı | A, E | `MEVCUT` |
| 10 | GET | `/profile-snapshots/{id}/drift` | `D05.C04.W02.A01` drift hükmü | E | `MEVCUT` |

### 3.4 Kurallar

| # | Yöntem | Yol | Fonksiyon | Akış | Durum |
|---|---|---|---|---|---|
| 11 | GET | `/rules` | `D06.C02.W01.A01` kural listesi | B | `MEVCUT` |
| 12 | GET | `/rules/{id}/versions` | `D06.C02.W02.A01` sürüm listesi | B | `MEVCUT` |
| 13 | POST | `/rules` | `D06.C02.W01.A01` kural oluştur | B | `KISMİ` — PG composition; kapsam denetlenmiyor (GAP-027) |
| 14 | POST | `/rules/{id}/test` | `D06.C02.W03.A01` kural testi | B | `KISMİ` — çalışan bileşimde **503** |
| 15 | POST | `/rules/{id}/activation` | `D06.C02.W05.A01` sürüm aktive | B | `KISMİ` — çalışan bileşimde **503** |
| 16 | POST | `/rules/{id}/approval` | `D06.C02.W04.A01` onaya gönder | B | `KISMİ` — çalışan bileşimde **503** |
| 17 | POST | `/rules/approval/{id}/decide` | `D06.C02.W04.A02` onay kararı | B | `KISMİ` — çalışan bileşimde **503** |
| 18 | POST | `/rules/approval/{id}/withdraw` | Onay geri çekme | B | `KISMİ` — çalışan bileşimde **503** |
| 19 | POST | `/rules/{id}/passivation` | `D06.C02.W06.A01` arşivleme | B | `KISMİ` — çalışan bileşimde **503** |

> **Kural mutasyon ailesi — bu denetimde tespit edildi.**
> `create_development_app` yalnız `rule_creator_service=rule_store` bağlar
> (`api/development.py:1351`); **`rule_mutation_service` hiç geçirilmez**.
> Route'lar bu portu `None` bulunca `RuleQueryTechnicalError` fırlatır
> (`api/app.py:1772,1807,1836,1895` …), bu da `503 "Rules temporarily
> unavailable"` olarak yanıtlanır (`app.py:554-564`). Sonuç: çalıştırılabilir
> uygulamada kural **oluşturulabilir**, fakat sürüm eklenemez, test edilemez,
> onaya gönderilemez, onaylanamaz ve aktive edilemez. Kural yaşam döngüsü
> akışı (B) `POST /rules`'tan sonra kullanıcı için tamamen durur.
>
> Bu, veri kaynağı aktivasyonundaki durumun **tersidir**: orada kontrol
> atlanarak işlem yapılır (GAP-027), burada işlem hiç yapılamaz. İkisi de
> `MEVCUT` etiketiyle görünmezdi.

### 3.5 Çalıştırmalar

| # | Yöntem | Yol | Fonksiyon | Akış | Durum |
|---|---|---|---|---|---|
| 20 | GET | `/executions` | `D07.C01.W01.A01` çalıştırma listesi | B, D | `KISMİ` — okuma kaynağı farklı (GAP-001) |
| 21 | POST | `/executions` | `D07.C01.W01.A01` manuel çalıştırma | B, D | `KISMİ` — UI bağlamıyor (GAP-017); kural sürümü/kaynak kapsamı ve aktifliği doğrulanmıyor, aktör yoksa `"unknown"` yazılıyor (GAP-027) |
| 22 | POST | `/executions/{id}/cancel` | `D07.C01.W03.A01` iptal | D | `KISMİ` — UI bağlamıyor |

### 3.6 Sorunlar

| # | Yöntem | Yol | Fonksiyon | Akış | Durum |
|---|---|---|---|---|---|
| 23 | GET | `/issues` | `D09.C01.W03.A01` sorun listesi | C | `KISMİ` — manuel açma yok (GAP-006) |
| 24 | POST | `/issues/{id}/investigation` | `D09.C02.W02.A01` inceleme başlat | C | `MEVCUT` |
| 25 | GET | `/issues/{id}/investigation/evidence` | `D09.C02.W02.A02` kanıt göster | C | `MEVCUT` |
| 26 | GET | `/issues/{id}/assignment-options` | `D09.C02.W01.A01` atama adayları | C | `MEVCUT` |
| 27 | POST | `/issues/{id}/assignment` | `D09.C02.W01.A01` sorun ata | C | `MEVCUT` |
| 28 | POST | `/issues/{id}/resolution` | `D09.C02.W03.A01` çözüm kaydet | C | `MEVCUT` |
| 29 | POST | `/issues/{id}/verification` | `D09.C02.W04.A01` doğrula | C | `MEVCUT` |
| 30 | POST | `/issues/{id}/closure` | `D09.C02.W05.A01` kapat | C | `MEVCUT` |

### 3.7 Raporlar

| # | Yöntem | Yol | Fonksiyon | Akış | Durum |
|---|---|---|---|---|---|
| 31 | GET | `/reports/summary` | `D11.C04.W02.A02` rapor liste özeti | H | `MEVCUT` |
| 32 | GET | `/reports/` | `D11.C04.W02.A02` rapor listesi | H | `MEVCUT` |
| 33 | POST | `/reports/` | `D11.C03.W01.A01` rapor talep | H | `KISMİ` — içerik sahte (GAP-016) |
| 34 | GET | `/reports/{id}` | Rapor detay | H | `MEVCUT` |
| 35 | GET | `/reports/{id}/download` | `D11.C04.W02.A01` güvenli indir | H | `MEVCUT` |

### 3.8 Rapor zamanlamaları

| # | Yöntem | Yol | Fonksiyon | Akış | Durum |
|---|---|---|---|---|---|
| 36 | GET | `/report-schedules` | `D11.C03.W03.A01` zamanlama listesi | H | `KISMİ` — UI bağlı değil (GAP-015) |
| 37 | POST | `/report-schedules` | `D11.C03.W03.A01` zamanlama oluştur | H | `KISMİ` |
| 38 | DELETE | `/report-schedules/{id}` | `D11.C03.W03.A01` zamanlama sil | H | `KISMİ` |
| 39 | POST | `/report-schedules/trigger-due` | `D11.C03.W03.A02` vadesi geleni tetikle | H | `KISMİ` — daemon yok |

### 3.9 Denetim

| # | Yöntem | Yol | Fonksiyon | Akış | Durum |
|---|---|---|---|---|---|
| 40 | GET | `/audit/events` | `D13.C01.W02.A01` audit sorgulama | Tüm akışlar | `KISMİ` — sentetik olay (GAP-001) |

### 3.10 Lineage / Yönetişim (salt okunur)

| # | Yöntem | Yol | Fonksiyon | Akış | Durum |
|---|---|---|---|---|---|
| 41 | GET | `/lineage/snapshots/{id}` | Kanıt snapshot görüntüleme | E, C | `MEVCUT` |
| 42 | GET | `/governance/{ref}/projection` | Yönetişim projeksiyonu | A, E | `MEVCUT` |

### 3.11 Geliştirme / Oturum

| # | Yöntem | Yol | Fonksiyon | Akış | Durum |
|---|---|---|---|---|---|
| 43 | POST | `/session/logout` | `D02.C04.W01.A01` oturum sonlandırma | I | `MEVCUT` |
| 44 | GET | `/development/users` | Geliştirme kullanıcı listesi | I (dev) | `MEVCUT` |

---

## 4. Hedef endpoint GAP'leri

Her GAP, fonksiyonel GAP envanterindeki "Eksik API" alanından türetilmiştir.

### 4.1 D03 — Metadata keşfi ve katalog (GAP-004)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| POST | `/data-sources/{id}/metadata-discoveries` | `D04.C01.W01.A01` keşif başlat | A |
| PUT | `/data-sources/{id}/discovery-scope` | `D04.C01.W01.A02` kapsam yapılandır | A |
| GET | `/metadata-discoveries/{id}/diff` | `D04.C01.W02.A01` fark hesapla | A, E |
| POST | `/metadata-diffs/{id}/application` | `D04.C01.W02.A02` fark uygula | A, E |
| GET | `/datasets` | `D04.C02.W01.A01` dataset listesi | A |
| GET | `/datasets/{id}` | `D04.C05.W02.A01` varlık detay | A |
| GET | `/datasets/{id}/fields` | `D04.C03.W01.A01` alan listesi | A |
| PUT | `/datasets/{id}/criticality` | `D04.C02.W02.A01` kritiklik belirle | A |
| PUT | `/fields/{id}/classification` | `D04.C03.W02.A01` alan sınıflandır | A |

### 4.2 D04 — Şema değişimi (GAP-019)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| GET | `/schema-changes` | `D04.C04.W01.A01` değişiklik listesi | E |
| GET | `/schema-changes/{id}` | Değişiklik detay | E |
| POST | `/schema-changes/{id}/decision` | `D04.C04.W02.A01` karar ver (kabul/blokla) | E |

### 4.3 D05 — Profil üretimi ve baseline (GAP-005)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| POST | `/datasets/{id}/profiles` | `D05.C01.W01.A01` profil talep et (idempotent) | A |
| POST | `/profiles/{id}/cancellation` | `D05.C01.W01.A02` profil iptal | A |
| POST | `/profiles/{id}/baseline` | `D05.C03.W01.A01` baseline belirle | A |
| POST | `/baselines/{id}/invalidation` | `D05.C03.W01.A02` baseline geçersiz kıl | E |

### 4.4 D06 — Kural şablonları ve bağımlılık (GAP-020)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| GET | `/rule-templates` | `D06.C01.W02.A01` şablon listesi | B |
| POST | `/rule-templates` | Şablon oluştur | B |
| GET | `/rule-templates/{id}` | Şablon detay | B |
| POST | `/rule-templates/{id}/publish` | Şablon yayımla | B |
| POST | `/rules/from-template/{id}` | `D06.C02.W01.A01` şablondan kural üret | B |
| GET | `/rules/{id}/dependencies` | `D06.C04.W01.A01` bağımlılık grafiği | B |
| GET | `/rules/{id}/conflicts` | `D06.C04.W02.A01` çakışma tespiti | B |

### 4.5 D06 — Gölge yürütme (GAP-021)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| POST | `/rule-versions/{id}/shadow-runs` | `D06.C05.W01.A01` gölge çalıştır | B |
| GET | `/rule-versions/{id}/shadow-comparison` | `D06.C05.W01.A02` gölge karşılaştırma | B |

### 4.6 D07 — Zamanlama (GAP-003)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| GET | `/schedules` | `D07.C02.W01.A01` zamanlama listesi | B |
| POST | `/schedules` | Zamanlama oluştur | B |
| GET | `/schedules/{id}` | Zamanlama detay | B |
| POST | `/schedules/{id}/state` | `D07.C02.W01.A02` duraklat/sürdür | B |
| DELETE | `/schedules/{id}` | `D07.C02.W01.A03` sil | B |

### 4.7 D08 — Skor kalıcılığı ve API (GAP-008)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| GET | `/scores` | `D08.C03.W03.A01` skor listesi (kapsam parametreli) | F |
| GET | `/scores/{id}` | Skor detay | F |
| GET | `/scores/rules/{ruleVersionId}` | Kural sürümü skorları | F |
| POST | `/scores/{id}/reproduction` | `D08.C04.W01.A02` yeniden üretim doğrulama | F |
| GET | `/scores/comparison` | `D08.C04.W02.A01` dönem karşılaştırma | F |

### 4.8 D09 — Otomatik sorun üretimi ve manuel açma (GAP-006)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| POST | `/issues` | `D09.C01.W03.A01` manuel sorun aç | C |

> Not: Otomatik sorun üretimi (`D09.C01.W01.A01`) iç servis çağrısıdır; HTTP
> endpoint değil. Tekilleştirme (`D09.C01.W02.A01`) dahildir.

### 4.9 D09 — SLA ve eskalasyon (GAP-014)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| GET | `/issues/{id}/escalations` | `D09.C03.W02.A01` eskalasyon listesi | C |
| POST | `/issues/{id}/hold` | `D09.C02.W03.A02` bekletme | C |

> Not: SLA hedef atama (`D09.C03.W01.A01`) ve durum hesaplama
> (`D09.C03.W01.A02`) dahili servis çağrısıdır; `GET /issues` yanıtında SLA
> alanları döner.

### 4.10 D09 — İstisna ve kalite borcu (GAP-009)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| GET | `/exceptions` | `D09.C04.W03.A03` istisna listesi | G |
| POST | `/exceptions` | `D09.C04.W01.A01` istisna talep | G |
| GET | `/exceptions/{id}` | İstisna detay | G |
| POST | `/exceptions/{id}/decision` | `D09.C04.W02.A01` karar (`If-Match`) | G |
| POST | `/exceptions/{id}/revocation` | `D09.C04.W03.A02` erken iptal | G |
| GET | `/quality-debts` | `D10.C04.W01.A01` borç listesi | G |
| POST | `/quality-debts` | Borç kaydı oluştur | G |
| GET | `/quality-debts/{id}` | Borç detay | G |
| POST | `/quality-debts/{id}/closure` | `D10.C04.W01.A03` borç kapat | G |

### 4.11 D10 — Lineage alımı ve graf (GAP-012)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| POST | `/lineage/events` | `D10.C01.W01.A01` olay al (idempotency) | E |
| GET | `/lineage/graph` | `D10.C01.W02.A01` graf sorgula (yön, derinlik) | E, C |

### 4.12 D10 — Etki analizi ve simülasyon (GAP-013)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| GET | `/lineage/impact` | `D10.C02.W01.A01` etki hesaplama | E |
| POST | `/lineage/impact-simulations` | `D10.C02.W02.A01` simülasyon çalıştır | E |
| GET | `/issues/{id}/diagnosis` | `D09.C05.W01.A01` hipotez listesi | C |
| POST | `/diagnosis-hypotheses/{id}/decision` | `D09.C05.W01.A02` hipotez kararı | C |
| GET | `/issues/{id}/recommendations` | `D09.C05.W02.A01` öneri listesi | C |

### 4.13 D10 — Veri sözleşmesi (GAP-010)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| GET | `/data-contracts` | `D10.C03.W01.A01` sözleşme listesi | K |
| POST | `/data-contracts` | Taslak oluştur | K |
| GET | `/data-contracts/{id}` | Sözleşme detay | K |
| POST | `/data-contracts/{id}/acceptance` | `D10.C03.W01.A02` karşılıklı onay | K |
| POST | `/data-contracts/{id}/termination` | `D10.C03.W01.A03` sonlandırma | K |
| GET | `/data-contracts/{id}/compliance` | `D10.C03.W02.A01` uyum ölçümü | K |
| GET | `/data-contracts/{id}/breaches` | `D10.C03.W03.A01` ihlal listesi | K |
| POST | `/contract-breaches/{id}/closure` | `D10.C03.W03.A02` ihlal kapat | K |

### 4.14 D11 — Rapor üretimi iptali (GAP-016)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| POST | `/reports/{id}/cancellation` | `D11.C03.W02.A02` üretim iptali | H |

### 4.15 D12 — Bildirim ve teslimat (GAP-007)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| GET | `/notifications` | `D12.C01.W02.A01` bildirim listesi | C, D, G, M |
| POST | `/notifications/{id}/read` | Okundu işaretle | C, D, G, M |
| GET | `/notification-channels` | `D12.C02.W01.A01` kanal listesi | M |
| POST | `/notification-channels` | Kanal yapılandır | M |
| GET | `/notification-deliveries` | `D12.C02.W03.A01` teslimat listesi | M |
| POST | `/notification-deliveries/{id}/reroute` | Yeniden yönlendir | M |
| PUT | `/users/{id}/notification-subscriptions` | `D12.C01.W02.A01` abonelik yönetimi | C, D, G, M |

### 4.16 D12 — ServiceNow entegrasyonu (GAP-023)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| POST | `/issues/{id}/integrations` | `D12.C03.W01.A01` dış bilet oluştur | C |
| POST | `/integrations/{id}/callbacks` | `D12.C03.W02.A01` gelen geri bildirim | C |

### 4.17 D13 — Saklama, imha, muhafaza (GAP-011)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| GET | `/retention-policies` | `D13.C03.W01.A01` politika listesi | H |
| POST | `/retention-policies` | Politika oluştur | H |
| PUT | `/retention-policies/{id}` | Politika güncelle | H |
| GET | `/disposal-jobs` | `D13.C03.W02.A01` imha listesi | H |
| GET | `/disposal-jobs/{id}/evidence` | İmha kanıtı | H |
| GET | `/legal-holds` | `D13.C04.W01.A01` muhafaza listesi | H |
| POST | `/legal-holds` | Muhafaza uygula | H |
| POST | `/legal-holds/{id}/release` | `D13.C04.W01.A02` muhafaza kaldır | H |
| POST | `/archive-recalls` | `D13.C04.W02.A01` geri çağırma talebi | H |

### 4.18 D14 — Operasyon yüzeyi (GAP-018, GAP-024)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| GET | `/operations/health` | `D14.C01.W01.A01` bileşen sağlığı | D |
| GET | `/operations/capacity` | `D14.C01.W02.A01` kapasite | D |
| GET | `/operations/jobs` | `D14.C02.W01.A01` kuyruk listesi | D |
| POST | `/operations/jobs/{id}/intervention` | `D14.C02.W01.A02` kuyruk müdahale | D |
| PATCH | `/jobs/{id}/priority` | `D07.C03.W01.A02` öncelik yükselt | D |
| GET | `/operations/dead-letters` | `D07.C04.W04.A02` dead-letter listesi | D |
| POST | `/operations/dead-letters/{id}/reprocessing` | `D07.C04.W04.A03` yeniden işle | D |
| POST | `/operations/dead-letters/{id}/closure` | `D07.C04.W04.A04` kapat | D |
| GET | `/operations/incidents` | `D14.C03.W01.A01` olay listesi | D |
| POST | `/operations/incidents` | Olay aç | D |
| POST | `/operations/incidents/{id}/updates` | Olay güncelle | D |
| POST | `/operations/incidents/{id}/closure` | Olay kapat | D |
| GET | `/operations/maintenance-windows` | `D14.C04.W01.A01` bakım listesi | D |
| POST | `/operations/maintenance-windows` | Bakım penceresi oluştur | D |
| POST | `/operations/backfills` | `D14.C04.W02.A01` toplu telafi | D |

### 4.19 D15 — Sentetik veri (GAP-025)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| POST | `/synthetic-runs` | `D15.C01.W01.A01` üretim çalıştırması | L |
| GET | `/synthetic-runs` | Run listesi | L |
| GET | `/synthetic-runs/{id}` | Run detay | L |
| POST | `/ground-truth` | `D15.C02.W01.A01` ground truth kaydı | L |
| POST | `/expected-results` | `D15.C02.W02.A01` beklenen sonuç | L |
| GET | `/accuracy-reports` | `D15.C03.W01.A01` tespit doğruluğu | L |
| POST | `/control-experiments` | `D15.C03.W02.A01` yeterlilik deneyi | L |

### 4.20 D02 — Kimlik ve yetki (GAP-022)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| GET | `/users` | `D02.C01.W01.A01` kullanıcı listesi | I |
| POST | `/users` | Kullanıcı sağla | I |
| POST | `/users/{id}/deactivation` | Pasifleştir | I |
| POST | `/users/{id}/reactivation` | Yeniden etkinleştir | I |
| GET | `/roles` | `D02.C02.W01.A01` rol listesi | I |
| POST | `/roles` | Rol tanımla | I |
| PUT | `/roles/{id}/permissions` | `D02.C02.W02.A01` izin eşleme | I |
| POST | `/users/{id}/role-assignments` | `D02.C02.W03.A01` rol ata | I |
| DELETE | `/role-assignments/{id}` | Atama kaldır | I |
| GET | `/permissions` | `D02.C02.W02.A01` izin kataloğu | I |
| POST | `/segregation-rules` | `D02.C02.W02.A02` SoD kuralı | I |
| GET | `/access-review-campaigns` | `D02.C05.W01.A01` gözden geçirme | I |
| POST | `/access-review-campaigns` | Kampanya başlat | I |

### 4.21 D01 — Yönetişim (GAP-026)

| Yöntem | Yol | Fonksiyon | Akış |
|---|---|---|---|
| CRUD | `/org-units` | `D01.C01.W01.A01` organizasyon birimi | A, J |
| CRUD | `/business-domains` | `D01.C01.W02.A01` iş domaini | A, J |
| CRUD | `/data-domains` | `D01.C01.W03.A01` veri domaini | A, J |
| CRUD | `/asset-ownerships` | `D01.C02.W01.A01` sahiplik atama | A, J |
| CRUD | `/glossary-terms` | `D01.C03.W01.A01` terim yönetimi | A, J |
| CRUD | `/policies` | `D01.C04.W01.A01` politika yaşam döngüsü | J |
| POST | `/policies/{id}/approval` | Politika onaya gönder | J |
| POST | `/policies/{id}/make-effective` | `D01.C04.W02.A01` yürürlüğe al | J |
| CRUD | `/system-config` | `D01.C05.W01.A01` konfigürasyon | J |
| CRUD | `/feature-flags` | `D01.C05.W02.A01` özellik anahtarı | J |

---

## 5. Endpoint–fonksiyon izlenebilirlik matrisi

Mevcut (M) ve hedef (H) endpoint'lerin akışlara dağılımı.

| Domain | M | H | A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|---|---|---|
| D03 Kaynak | 5 | 0 | ● | | | | | | | |
| D04 Katalog | 0 | 9 | ● | | | | ● | | | |
| D04 Şema | 0 | 3 | | | | | ● | | | |
| D05 Profil | 4 | 4 | ● | | | | ● | | | |
| D06 Kural | 8 | 9 | | ● | | | | | | |
| D06 Gölge | 0 | 2 | | ● | | | | | | |
| D07 Zamanlama | 0 | 5 | | ● | | | | | | |
| D07 Çalıştırma | 3 | 0 | | ● | | ● | | | | |
| D07 Operasyon | 0 | 15 | | | | ● | | | | |
| D08 Skor | 0 | 5 | | | | | | ● | | |
| D09 Sorun | 8 | 2 | | | ● | | | | ● | |
| D09 SLA | 0 | 2 | | | ● | | | | | |
| D09 İstisna | 0 | 9 | | | | | | | ● | |
| D10 Lineage | 2 | 7 | | | | | ● | | | |
| D10 Etki | 0 | 5 | | | ● | | ● | | | |
| D10 Sözleşme | 0 | 8 | | | | | | | | |
| D10 Borç | 0 | 4 | | | | | | | ● | |
| D11 Rapor | 5 | 1 | | | | | | | | ● |
| D12 Bildirim | 0 | 7 | | | ● | ● | | | ● | ● |
| D12 Entegrasyon | 0 | 2 | | | ● | | | | | |
| D13 Saklama | 1 | 9 | | | | | | | | ● |
| D15 Sentetik | 0 | 7 | | | | | | | | |
| D02 Kimlik | 1 | 13 | | | | | | | | |
| D01 Yönetişim | 0 | 10 | ● | | | | | | | |
| **Toplam** | **43** | **~128** | | | | | | | | |

---

## 6. Öncelik sıralaması

API GAP'lerinin bağımlılık ve etki açısından öncelik sırası:

| # | GAP | Neden öncelikli |
|---|---|---|
| 1 | GAP-001 (composition root) | Mevcut 43 endpoint'in yazma tarafı sahte depoda; PG'ye bağlanmadan hiçbir yeni endpoint anlamlı değil |
| 2 | GAP-004 (katalog API) | Onboarding akışı (A) 4. adımda kopuyor; dataset/alan endpoint'leri olmadan kural yazılamıyor |
| 3 | GAP-008 (skor API) | Skor kalıcılığı olmadan F akışı (skor güvenilirliği) ve dashboard gerçek verisi yok |
| 4 | GAP-006 (sorun üretimi + manuel açma) | C akışının giriş kapısı; `POST /issues` yoksa sorun yaşam döngüsü beslenemiyor |
| 5 | GAP-003 (zamanlama API) | B akışının otomatik tetikleme adımı; zamanlama endpoint'leri ve daemon olmadan düzenli ölçüm yok |
| 6 | GAP-005 (profil API) | A akışının baseline adımı; profil üretimi olmadan drift tespiti başlamıyor |
| 7 | GAP-007 (bildirim API) | C, D, G akışlarının bildirim adımı; bildirim olmadan sahiplik ve eskalasyon çalışmıyor |
| 8 | GAP-022 (kimlik API) | Tüm endpoint'lerin yetki kodları bu kayda bağlı; serbest dize rolleri kaldırılmadan gerçek yetki uygulanamıyor |

**Sıralamada gözden kaçan kayıt: GAP-027.** Yukarıdaki liste yeni endpoint
ihtiyacına göre sıralanmıştır ve tamamı yeni yüzey gerektirir. GAP-027 ise
**yeni endpoint gerektirmez**: mevcut dört veri kaynağı komutunun aktör
bağlamını porta iletmesi ve gerçek servise bağlanması yeterlidir. Bağımlılığı
olmadığı ve hâlihazırda çalışan bir onay kontrolünün atlanmasını tarif ettiği
için, yeni yüzey çalışmalarından **önce** ele alınabilir.

**Hedef endpoint'ler için not — arka uç çoğu yerde hazır.** Aşağıdaki
`HEDEF` uçların bir bölümü sıfırdan servis yazmayı değil, mevcut servisi
HTTP'ye açmayı gerektirir:

| Hedef endpoint grubu | Mevcut arka uç |
|---|---|
| `/schedules` CRUD ve tetikleme | `SchedulingService.create_schedule` / `trigger_due` / `preview_runs` (`executions/scheduling.py:234,303,343`) — `PAUSED`/`DELETED` durumları eksik |
| `/data-sources/{id}/metadata-discoveries`, `/metadata-discoveries/{id}/diff` | `DataSourceService.discover_metadata` (`data_sources/service.py:763`) ve `_diff_metadata` (`:1559`) |
| `/datasets/{id}/profiles` | `DataSourceService.run_profile` (`data_sources/service.py:901`) |
| `POST /issues` ve otomatik üretim | `IssueService.create_for_trigger` (`issues/service.py:139`) — uygunluk kapısı eksik (GAP-006) |

---

## 7. Kanıt sınırları

- Mevcut endpoint listesi `app.py` route tanımlarından (43 route)
  çıkarılmıştır; bu oturumda uygulama ayağa kaldırılmamıştır.
- Hedef endpoint'ler GAP envanterinin "Eksik API" alanlarından
  türetilmiştir; her biri en az bir L4 yaprak koduna bağlanmıştır.
- URL yol adları ve HTTP yöntemleri öneridir; kesin sözleşme
  implementasyon aşamasında netleşir.
- Idempotency, optimistic locking ve veri-minimum yük ilkeleri her
  endpoint için geçerlidir; detaylı sözleşme ayrı belgelerle
  tanımlanacaktır.
- İç servis çağrıları (otomatik sorun üretimi, skor hesaplama,
  bildirim yayımı) HTTP endpoint değil, uygulama içi servis
  arayüzü olarak kalır; bu envanterde yer almaz.

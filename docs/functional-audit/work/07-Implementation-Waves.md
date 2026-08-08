---
type: functional-audit-work
stage: "07 — Uygulama Dalgaları"
scope: implementation-waves
inputs:
  - 06-Vertical-Slice-Candidates.md
  - ../04-Functional-Gap-Inventory.md
  - ../12-Prioritized-Backlog.md
  - ../13-Implementation-Roadmap.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-05
---

# 07 — Uygulama Dalgaları

> `06-Vertical-Slice-Candidates.md`'de sınıflandırılan dikey dilimlerin
> **bağımlılık topolojisi ve aciliyet önceliğine göre sıralanması**. Bu aşamada
> **yeni GAP, yeni dilim veya yeni kapsam eklenmez**; yalnız mevcut dilimler
> normalize edilir ve uygulama sırasına konur.
>
> Bir dalga, tamamlandığında ürünün yapabildiği işin ölçülebilir biçimde
> genişlediği dilim kümesidir. Dalga bir takvim birimi değildir; bir çıkış
> kapısıdır.

---

## 1. Kapsam ve yöntem

### 1.1 Sıralama kuralı

Sıra üç ölçütle, bu öncelikle belirlenir:

| # | Ölçüt | Kaynak |
|---|---|---|
| 1 | **Hard bağımlılık topolojisi** — ihlal edilemez | `04 §4` GAP bağımlılık haritası; `06 §6` dilim grafiği |
| 2 | **Aciliyet puanı** — aynı topolojik seviyede yüksek olan önce | `12 §2` puanlama tablosu |
| 3 | **Bağımlılık merkeziyeti** — eşitlikte daha çok dilimi açan önce | `04 §4` |

**Dilim aciliyeti**, üye GAP'ların `12 §2`'deki en yüksek aciliyet puanıdır.
Alt dilimler (`S3a`, `S6b`, `S16c` …) tek bir GAP kaydından türediği için
nominal olarak aynı puanı taşır; bu durumda dalga içi sıra kapsam genişliği
ve bağımlılık yönüyle belirlenir ve ilgili satırda belirtilir.

### 1.2 Hard ve soft bağımlılık ayrımı

| Tür | Anlam | Sonuç |
|---|---|---|
| **Hard** | Bağımlı dilim olmadan hedef dilim **tamamlanamaz**; çıkış kapısı üretilemez | Önceki dalgada bitmiş olmalı |
| **Soft** | Hedef dilim çalışır, ancak nihai biçimini bağımlı dilim tamamlanınca alır | Aynı veya sonraki dalgada retrofit kalemi olarak açık kalır |

Bu ayrım, `06 §6` grafiğinde ayrışmadığı için bu belgede açıkça yapılır.
En belirgin örnek yetki katmanıdır: `S4`, `S5` ve `S6a` yetki kodunu `S3a`'dan
alır, ancak `S1`'in `ActorContext` kapısıyla `S3a` beklenmeden tamamlanabilir.

### 1.3 Bu belge neyi yapmaz

- Yeni GAP tanımlamaz; 27 GAP kaydı `04`'ten devralınır.
- Kolon/migration tasarımı yapmaz; boyut tahminleri tablo sayısına dayanır.
- Takvim veya adam/gün tahmini vermez; dalga uzunluğu ekip büyüklüğüne bağlıdır.
- `13-Implementation-Roadmap.md`'yi geçersiz kılmaz; §7'de eşlenir.

---

## 2. Normalize dilim kümesi

`06`'nın kendi sınıflandırma kararları uygulandığında planlanabilir birim
sayısı 16'dan 21'e çıkar:

| Birim | GAP'lar | Aciliyet | Sınıf | Normalize kararı |
|---|---|---:|---|---|
| S1 | GAP-027 | 19 | `P0` | `READY` — değişiklik yok |
| S2 | GAP-001, GAP-002 | 29 | `P0` | `READY` — değişiklik yok |
| S3a | GAP-022 (rol, izin, atama, kapsam çözümleme) | 22 | `P1` | `SPLIT_REQUIRED` → alt dilim |
| S3b | GAP-022 (SoD zorlama, oturum, servis hesabı) | 22 | `P1` | `SPLIT_REQUIRED` → alt dilim |
| S3c | GAP-022 (erişim gözden geçirme kampanyası) | 22 | `P1` | `SPLIT_REQUIRED` → alt dilim |
| S4 | GAP-004, GAP-005, GAP-019 | 23 | `P1` | `READY` — değişiklik yok |
| S5 | GAP-003, GAP-017, GAP-020, GAP-021 | 20 | `P1` | `DEPENDENCY_MISSING` → GAP-017 atandı, `READY` |
| S6a | GAP-006, GAP-009 | 23 | `P1` | `SPLIT_REQUIRED` + S8 `MERGE_REQUIRED` |
| S6b | GAP-007 | 20 | `P1` | `SPLIT_REQUIRED` → alt dilim |
| S6c | GAP-014 | 15 | `P2` | `SPLIT_REQUIRED` → alt dilim |
| S7 | GAP-008 | 21 | `P1` | `READY` — değişiklik yok |
| S9 | GAP-018, GAP-024 | 15 | `P2` | `READY` — değişiklik yok |
| S10 | GAP-015, GAP-016 | 16 | `P2` | `READY` — değişiklik yok |
| S11 | GAP-011 | 15 | `P2` | `READY` — değişiklik yok |
| S12 | GAP-012, GAP-013 | 12 | `P3` | `READY` — değişiklik yok |
| S13 | GAP-010 | 11 | `P3` | `DEPENDENCY_MISSING` → bağımlılıkları D1–D3'te karşılanır |
| S14 | GAP-023 | 8 | `P4` | `DEFER` → D6 |
| S15 | GAP-025 | 8 | `P4` | `DEFER` → D6 |
| S16a | GAP-026 (organizasyon, domain, sahiplik) | 16 | `P2` | `SPLIT_REQUIRED` → alt dilim |
| S16b | GAP-026 (iş sözlüğü) | 16 | `P2` | `SPLIT_REQUIRED` → alt dilim |
| S16c | GAP-026 (politika, sistem konfigürasyonu) | 16 | `P2` | `SPLIT_REQUIRED` → alt dilim |

**S8 kalkmıştır.** `06`'daki `MERGE_REQUIRED` kararı gereği GAP-009
(istisna/kalite borcu) S6a'ya taşınmıştır; ikisi de D09 domainine aittir ve
istisna, sorun üretimi olmadan anlamsızdır.

### 2.1 GAP kapsama denetimi

| Dalga | Kapsanan GAP'lar | Adet |
|---|---|---:|
| D1 | 027, 001, 002 | 3 |
| D2 | 006, 009, 004, 005, 019, 008 | 6 |
| D3 | 022 (a), 007, 003, 017, 020, 021, 014 | 7 |
| D4 | 022 (b), 015, 016, 018, 024, 011 | 6 |
| D5 | 026, 012, 013, 022 (c) | 4 |
| D6 | 010, 025, 023 | 3 |
| | **Toplam benzersiz** | **27** |

GAP-022 üç alt dilime, GAP-026 üç alt dilime bölünmüştür; benzersiz kayıt
sayısı 27'dir ve hiçbir GAP birden fazla birime atanmamıştır.

---

## 3. Bağımlılık matrisi

| Birim | Hard bağımlılık | Soft bağımlılık | Kaynak |
|---|---|---|---|
| S1 | — | — | `04 §4`: GAP-027 bağımsız |
| S2 | — | — | `06 §3`: kök dilim |
| S3a | S2 | S1 (komut yolu kapısını devralır) | `06 §3 S3` |
| S3b | S3a, S1 | — | SoD, komut yolu kapısı üzerine kurulur |
| S3c | S3a, S3b | — | Kampanya, atama ve oturum verisi ister |
| S4 | S2 | S1 (aktivasyon kapısı), S3a (yetki), S12 (GAP-019 etki tümleşimi) | `04 §4`: GAP-005 → GAP-004; GAP-019 → GAP-004, GAP-013 |
| S5 | S2 | S1, S3a | `04 §4`: GAP-003 → GAP-002; GAP-021 → GAP-002, GAP-017 (birim içi) |
| S6a | S2 | S1, S3a | `04 §4`: GAP-006 → GAP-001, GAP-002 |
| S6b | S2, S6a | S3a | `04 §4`: GAP-007 → GAP-002; teslimat sorun olayına bağlanır |
| S6c | S6a, S6b | S3a | `04 §4`: GAP-014 → GAP-006, GAP-007 |
| S7 | S2 | — | `04 §4`: GAP-008 → GAP-001, GAP-002 |
| S9 | S2 | S3a | `04 §4`: GAP-018 → GAP-002 |
| S10 | S2, S5, S7 | S3a | `04 §4`: GAP-015 → GAP-003 altyapısı; GAP-016 → GAP-002, GAP-008 |
| S11 | S2, S3a | S16c (politika bağı) | `06 §3 S11`; legal hold onayı rol ister |
| S12 | S2, S4 | — | `04 §4`: GAP-013 → GAP-012; GAP-012 katalog yüzeyine bağlanır |
| S13 | S2, S3a, S3b, S6a, S7 | S6b | `06 §3 S13`: iki taraflı onay + ihlalden sorun + uyum ölçümü |
| S14 | S2, S6a, S6b | — | `06 §3 S14`; `13` DS-23 |
| S15 | S2 | S7 | `06 §3 S15` |
| S16a | S2, S3a | — | Sahiplik ataması kimlik kaydına bağlanır |
| S16b | S16a | — | Sözlük terimi domain/varlığa bağlanır |
| S16c | S16a | — | Politika, organizasyon kapsamına bağlanır |

**Dairesel bağımlılık — S4 ↔ S12.** GAP-019 (S4) → GAP-013 (S12) ve
GAP-012 (S12) → GAP-004 (S4). Çözüm: GAP-019'un **temel şema değişikliği
yüzeyi** (tespit, diff, karar kaydı) S4 ile D2'de tamamlanır; **etki analizi
tümleşimi** S12 ile D5'te eklenir. Bu, S4'ün çıkış kapısını daraltır ve §8'de
açık kalem olarak izlenir.

---

## 4. Topolojik seviyeler

Hard bağımlılıklara göre hesaplanan seviye (seviye = en uzun hard zincirdeki
konum). Seviye, bir birimin **en erken** yapılabileceği yeri gösterir; dalga
ataması buna öncelik uygulanmış halidir.

| Seviye | Birimler | Aciliyet aralığı |
|---|---|---|
| 0 | S1, S2 | 19–29 |
| 1 | S3a, S4, S5, S6a, S7, S9, S15 | 8–23 |
| 2 | S3b, S6b, S10, S11, S12, S16a | 12–22 |
| 3 | S3c, S6c, S13, S14, S16b, S16c | 8–22 |

Seviye 1'de yedi birimin bulunması, D1 tamamlandıktan sonra planın topolojiyle
değil **öncelikle** yönetildiği anlamına gelir: S2 sonrası neredeyse her şey
teknik olarak başlatılabilir; hangisinin önce yapılacağı `12 §2` puanına ve
kritik yola bakılarak seçilir.

---

## 5. Dalga planı

| Dalga | Birimler (dalga içi sırayla) | Sınıf | Dalga sonunda ürün ne yapabiliyor |
|---|---|---|---|
| **D1 — Güvenli çekirdek** | S1 ∥ S2 | `P0` | Kayıtlar süreç yeniden başlatınca duruyor; iş kuyruğa girip işleniyor; maker = checker aktivasyonu `403` dönüyor |
| **D2 — Ölçüm ve sorun zinciri** | S6a, S4, S7 | `P1` | Eşiği aşan ihlal atanmış sorun üretiyor; skor `quality_scores`'tan okunuyor; katalogda dataset/alan görünüyor |
| **D3 — Otomasyon, teslimat ve yetki temeli** | S3a, S6b, S5, S6c | `P1` | Zamanlama vadesinde çalıştırma açıyor; bildirim sahibine ulaşıyor; SLA ve eskalasyon işliyor; yetki `role_assignments`'tan çözülüyor |
| **D4 — Kurumsal kapı ve operasyon** | S3b, S10, S9, S11 | `P1`/`P2` | SoD hem serviste hem DB kısıtında zorlanıyor; rapor asenkron üretilip indiriliyor; dead-letter ve sağlık yüzeyi var; saklama/imha çalışıyor |
| **D5 — Yönetişim ve analitik** | S16a, S16b, S16c, S12, S3c | `P2`/`P3` | Sahiplik atanmış, sözlük ve politika yürürlükte; lineage grafı ve etki simülasyonu çalışıyor; erişim gözden geçirme kampanyası kapanıyor |
| **D6 — Olgunluk** | S13, S15, S14 | `P3`/`P4` | Sözleşme ihlali sorun açıyor; kontrol doğrulama raporu üretiliyor; ServiceNow bileti oluşup geri bildirim yansıyor |

---

### D1 — Güvenli çekirdek

| Alan | Değer |
|---|---|
| Birimler | S1 (GAP-027), S2 (GAP-001, GAP-002) |
| Giriş koşulu | Yok — grafiğin kökü |
| Dalga içi sıra | **Paralel.** S1 ve S2 farklı dosyalara dokunur ve birbirini beklemez |
| Çıkış kapısı | (a) Süreç yeniden başlatıldıktan sonra kaynak/kural/sorun kayıtları duruyor; (b) kuyruğa giren iş worker tarafından işleniyor; (c) `POST /data-sources/{id}/activation` maker = checker ise `403`; `"unknown"` aktör reddediliyor; (d) audit olayı outbox'tan gerçekten üretiliyor |
| Migration | Yok — tablolar mevcut |
| Taşınan risk | `04 §5`'teki **Q-01** açık: üretim composition root'unun repo dışında olması GAP-001/002/003/007'nin runtime eksenini değiştirir. Bu soru D1 başlarken kapatılmalıdır |

**Pazarlık konusu değildir.** D1 tamamlanmadan sistemin hiçbir çıktısı — skor,
sorun, rapor — kanıt değeri taşımaz; sonraki her dalganın çıkış kapısı D1'in
kalıcılığına dayanır.

---

### D2 — Ölçüm ve sorun zinciri

| Alan | Değer |
|---|---|
| Birimler | S6a (GAP-006, GAP-009), S4 (GAP-004, GAP-005, GAP-019), S7 (GAP-008) |
| Giriş koşulu | D1 tamamlandı |
| Dalga içi sıra | S6a → S4 → S7. S6a ile S4 aciliyette eşittir (23); S6a bağımlılık merkeziyeti daha yüksek olduğu için (S6b, S6c, S13, S14 buna bağlı) önce gelir. S7 (21) bağımsızdır ve üçü de paralel yürütülebilir |
| Çıkış kapısı | (a) Eşiği aşan uygun başarısızlık atanmış sorun üretiyor, uygunsuz olan üretmiyor; (b) onaylı istisna süresi boyunca bastırma uyguluyor, süre dolunca kalkıyor; (c) dashboard skoru seed'den değil `quality_scores`'tan okuyor; (d) aktif kaynakta keşif tetiklenince dataset/alan katalogda görünüyor; (e) şema değişikliği tespit edilip karar bekliyor |
| Migration | `exceptions`, `exception_suppressions`, `quality_debts`, `metadata_discovery_results`, `discovery_scopes`, `metadata_diffs`, `classification_candidates`, `quality_scores`, `score_publications` |
| Taşınan risk | S4'ün GAP-019 kapsamı **daralmıştır**: etki analizi tümleşimi D5'e (S12) sarkar. S4'ün çıkış kapısı "şema değişikliği tespit edilip karar bekliyor" ile sınırlıdır; "değişikliğin aşağı akış etkisi gösteriliyor" D5'in kapısıdır |

---

### D3 — Otomasyon, teslimat ve yetki temeli

| Alan | Değer |
|---|---|
| Birimler | S3a (GAP-022 kısmı), S6b (GAP-007), S5 (GAP-003, GAP-017, GAP-020, GAP-021), S6c (GAP-014) |
| Giriş koşulu | D1 tamamlandı; S6a (D2) tamamlandı — S6b ve S6c için zorunlu |
| Dalga içi sıra | S3a **ilk başlatılır** (`12 §2`: karmaşıklık 5, en uzun kalem). Ardından S6b → S6c zinciri; S5 bunlardan bağımsız ve paralel. S6c dalga sonunda kapanır, çünkü hem S6a hem S6b ister |
| Çıkış kapısı | (a) Yetki `role_assignments`'tan çözülüyor; dev başlığı üretim profilinde kapalı; (b) sorun ataması alıcının kanalında görünüyor; teslimat başarısızlığı yeniden denemeye giriyor; (c) tanımlı zamanlama vadesinde **tam bir kez** çalıştırma açıyor; (d) UI'dan çalıştırma başlatılıp iptal edilebiliyor; (e) gölge yürütme sonucu üretimle karşılaştırılabiliyor; (f) SLA hedefi aşıldığında eskalasyon bildirimi çıkıyor |
| Migration | `users`, `roles`, `permissions`, `role_permissions`, `role_assignments`, `assignment_scopes`, `notification_events`, `notification_subscriptions`, `notification_channels`, `notification_deliveries`, `rule_templates`, `rule_dependencies`, `rule_conflicts`, `schedule_missed_runs`, `issue_slas`, `issue_escalations` |
| Taşınan risk | S3a, D2'de soft bağımlılık olarak bırakılan yetki retrofitlerini de kapatmak zorundadır: S4, S5, S6a yüzeylerinin `ActorContext` kapısından gerçek rol çözümlemesine geçirilmesi **S3a'nın kapsamındadır** (§8) |

S6c'nin S6b'den sonra gelmesi zorunludur: `04 §4`'e göre GAP-014 hem GAP-006'ya
hem GAP-007'ye bağımlıdır — eskalasyon, teslimat hattı olmadan gözlenebilir
sonuç üretemez.

---

### D4 — Kurumsal kapı ve operasyon

| Alan | Değer |
|---|---|
| Birimler | S3b (GAP-022 kısmı), S10 (GAP-015, GAP-016), S9 (GAP-018, GAP-024), S11 (GAP-011) |
| Giriş koşulu | S3a, S5 ve S7 tamamlandı |
| Dalga içi sıra | S3b (22) → S10 (16) → S9 (15) → S11 (15). S9 ile S11 aciliyette eşittir; S9 iki GAP kapattığı ve operatör personasını tamamladığı için önce gelir. Dördü de birbirinden bağımsızdır |
| Çıkış kapısı | (a) SoD ihlali hem serviste hem DB kısıtında reddediliyor; oturum süresi doluyor; servis hesabı ayrı yetkilendiriliyor; (b) rapor asenkron üretilip indirilebiliyor ve zamanlanmış rapor kendiliğinden oluşuyor; (c) operatör dead-letter kaydını görüp yeniden işleyebiliyor; bileşen sağlığı ve bakım penceresi görünüyor; (d) saklama süresi dolan veri imha işiyle siliniyor, legal hold varsa silinmiyor |
| Migration | `segregation_rules`, `sessions`, `service_accounts`, `component_health`, `operational_incidents`, `incident_updates`, `maintenance_windows`, `backfill_jobs`, `retention_policies`, `disposal_jobs`, `legal_holds`, `archive_recalls`; `reports` genişletme |
| Taşınan risk | S11'in politika bağı (S16c) henüz yok; saklama politikası bu dalgada tablo tabanlı tanımlanır, politika yaşam döngüsüne bağlanması D5'te yapılır |

---

### D5 — Yönetişim ve analitik

| Alan | Değer |
|---|---|
| Birimler | S16a, S16b, S16c (GAP-026), S12 (GAP-012, GAP-013), S3c (GAP-022 kalanı) |
| Giriş koşulu | S3a, S3b ve S4 tamamlandı |
| Dalga içi sıra | S16a → S16b ∥ S16c → S12 → S3c. S16b ve S16c yalnız S16a'ya bağlıdır ve paralel yürütülebilir. S3c, GAP-022'nin en düşük aciliyetli kalanıdır ve dalganın sonunda kapanır |
| Çıkış kapısı | (a) Organizasyon/domain yapısı tanımlı ve varlık sahipliği atanmış; (b) sözlük terimi alanla eşleşmiş; (c) politika yürürlüğe girip geri alınabiliyor; (d) lineage grafı sorgulanabiliyor ve şema değişikliğinin aşağı akış etkisi simüle edilebiliyor; (e) erişim gözden geçirme kampanyası açılıp onaysız atamalar otomatik sonlandırılıyor |
| Migration | `organizational_units`, `business_domains`, `data_domains`, `domain_asset_assignments`, `asset_ownerships`, `glossary_terms`, `glossary_term_mappings`, `policies`, `policy_rollbacks`, `system_config`, `system_config_history`, `feature_flags`, `lineage_events`, `lineage_edges`, `column_lineage_edges`, `impact_analyses`, `access_review_campaigns`, `access_review_items` |
| Taşınan risk | **S4'ün GAP-019 etki tümleşimi bu dalgada kapanır.** S12 tamamlandığında şema değişikliği kararı ekranı etki analizini göstermeye başlar; bu, D2'de bilerek açık bırakılan kalemdir |

---

### D6 — Olgunluk

| Alan | Değer |
|---|---|
| Birimler | S13 (GAP-010), S15 (GAP-025), S14 (GAP-023) |
| Giriş koşulu | S3b, S6a, S6b ve S7 tamamlandı |
| Dalga içi sıra | S13 (11) → S15 (8) → S14 (8). S15 ile S14 aciliyette eşittir; `12 §2` sıralamasında GAP-025 GAP-023'ten öncedir. Üçü de birbirinden bağımsızdır |
| Çıkış kapısı | (a) Üretici ve tüketici sözleşmeyi kabul ediyor; ihlal sorun ve bildirim üretiyor; (b) sentetik run başlatılıp tespit doğruluk raporu üretiliyor ve deney kanıtı saklanıyor; (c) sorun ServiceNow'da bilet açıyor, aynı sorun için ikinci bilet açılmıyor, geri bildirim sisteme yansıyor |
| Migration | `data_contracts`, `contract_compliance`, `contract_breaches`, `synthetic_profiles`, `synthetic_runs`, `ground_truth_defects`, `expected_results`, `control_validations`, `control_experiments`, `integration_records`, `rate_limit_counters` |
| Taşınan risk | S14'ün gerçek ServiceNow örneğine erişimi `13 §5`'te `ExternalDependency`'dir; dilim stub adaptörle uçtan uca çalışacak biçimde kapanır |

---

## 6. Kritik yol ve paralellik

**Kritik yol (en uzun hard zincir):**

```
S2 (kalıcılık + worker)
  └── S6a (sorun üretimi + istisna)
        └── S6b (bildirim teslimatı)
              ├── S6c (SLA + eskalasyon)
              └── S14 (ServiceNow)
```

**En uzun paralel zincir (yetki ekseni):**

```
S2 ── S3a (rol/izin/kapsam) ── S3b (SoD/oturum) ── S3c (erişim gözden geçirme)
                                    └── S13 (veri sözleşmesi)
```

Bu iki zincir D1'den sonra birbirinden bağımsız ilerler ve planın iki doğal
iş kolunu oluşturur.

### 6.1 Ekip senaryosuna göre sıra

| Senaryo | Sonuç |
|---|---|
| **Tek takım (seri)** | Dalga içi sıra aynen izlenir. S3a'nın D3'ün başında olması kritiktir; geciktiği her dalga, sonraki dilimlerin yetki retrofit borcunu büyütür |
| **İki takım (paralel)** | Takım A kritik yolu sürer (S2 → S6a → S6b → S6c), takım B yetki eksenini sürer (S3a → S3b) ve boşta kaldığında S4/S7/S9'u alır. Bu düzende D3 ile D4 kısmen örtüşebilir |
| **Üç takım** | Üçüncü takım S4 → S12 (katalog/lineage) eksenini alır; D5'in analitik kısmı D4 ile örtüşür. S16 ve S11 en son takıma verilmemelidir; ikisi de S3a'ya bağlıdır |

### 6.2 Neden S3a D3'e alındı

S3a topolojik olarak seviye 1'dedir; yani D2'de de yapılabilirdi. D3'e
alınmasının nedeni `12 §2`'de GAP-022'nin karmaşıklık 5, mimari uyum 3 ile en
pahalı kalem olması ve D2'nin üç `P1` diliminin (S6a, S4, S7) ölçüm zincirini
görünür kılmasıdır. Buna karşılık **D3'ten daha geç bırakılamaz**: S3a'dan
sonraki her dilim aksi halde yetki retrofit borcu üretir ve S10, S11, S16a,
S13 doğrudan bloke olur.

---

## 7. `13-Implementation-Roadmap.md` eşlemesi

Bu belge `13`'ü geçersiz kılmaz; `13` GAP tabanlı 23 dilim (DS) tanımlar,
bu belge `06`'nın dikey dilim (S) kümesini sıralar. İki kümenin eşlemesi:

| Birim | Karşılık gelen DS | Not |
|---|---|---|
| S1 | DS-01 | Birebir |
| S2 | DS-02 + DS-03 (GAP-002 kısmı) | DS-03'ün GAP-017 kısmı S5'tedir |
| S3a, S3b, S3c | DS-10 | `13` bu GAP'ı bölmez; bu belge üçe böler |
| S4 | DS-04 + DS-08 + DS-13 | `13` üç dilime ayırır; `06` tek dikey dilimde toplar |
| S5 | DS-07 (GAP-003) + DS-03 (GAP-017) + DS-17 + DS-18 | GAP-015 DS-07'de, ancak burada S10'dadır |
| S6a | DS-05 + DS-15 | S8 birleşmesinin karşılığı |
| S6b | DS-09 | Birebir |
| S6c | DS-16 | Birebir |
| S7 | DS-06 | Birebir |
| S9 | DS-11 | Birebir |
| S10 | DS-12 + DS-07 (GAP-015) | Rapor zamanlaması `13`'te zamanlama dilimindedir |
| S11 | DS-20 | Birebir |
| S12 | DS-14 | Birebir |
| S13 | DS-19 | Birebir |
| S14 | DS-23 | Birebir |
| S15 | DS-22 | Birebir |
| S16a, S16b, S16c | DS-21 | `13` bu GAP'ı bölmez; bu belge üçe böler |

### 7.1 İki dalga planı arasındaki farklar

| Konu | `13 §4` | Bu belge | Gerekçe |
|---|---|---|---|
| Dalga sayısı | 7 | 6 | S kümesi daha az sayıda, daha geniş dikey dilim kullanır |
| Kimlik (GAP-022) | Dalga 4 (DS-10) | D3 (S3a), D4 (S3b), D5 (S3c) | En uzun kalem; geciktikçe retrofit borcu büyür (§6.2) |
| Katalog (GAP-004) | Dalga 2 (DS-04) | D2 (S4) | Aynı konum |
| SLA (GAP-014) | Dalga 6 (DS-16) | D3 (S6c) | Bildirim hattıyla aynı dalgada kapanması hard bağımlılığı (GAP-014 → GAP-007) daha kısa yoldan karşılar |
| İstisna (GAP-009) | Dalga 6 (DS-15) | D2 (S6a) | `06`'nın `MERGE_REQUIRED` kararı gereği sorun üretimiyle birleşti |
| Erteleme | Dalga 7 | D6 | Aynı içerik (sözleşme, sentetik, ServiceNow) |

`13`'ün "Dalga 1 ve 2 pazarlık konusu değildir" kuralı burada D1 ve D2'ye
karşılık gelir.

---

## 8. Ertelenen ve koşullu kalemler

| Kalem | Nereye ertelendi | Koşul |
|---|---|---|
| S4 → GAP-019 etki analizi tümleşimi | D5 (S12 ile) | S4'ün D2 çıkış kapısı "değişiklik tespit edilip karar bekliyor" ile sınırlıdır; "aşağı akış etkisi gösteriliyor" D5'in kapısıdır |
| S4, S5, S6a yetki retrofiti | D3 (S3a kapsamında) | Bu üç dilim D2–D3'te `S1`'in `ActorContext` kapısıyla çalışır; gerçek rol çözümlemesi S3a ile devreye alınır |
| S11 → politika bağı | D5 (S16c ile) | Saklama politikası D4'te tablo tabanlı tanımlanır; politika yaşam döngüsüne bağlanması S16c'yi bekler |
| S14 (ServiceNow) | D6 | `06 §3`: entegrasyon yüzeyi, sorun üretimi ve bildirim tamamlanmadan anlamsızdır. `DEFER`, "gereksiz" değil "temel akışlar önce" demektir |
| S15 (sentetik doğrulama) | D6 | Aynı gerekçe; generator ve oracle kod ekseninde mevcuttur, eksik olan uygulama yüzeyi ve kalıcılıktır |
| S13 (veri sözleşmesi) | D6 | `06`'da `DEPENDENCY_MISSING`; dört bağımlılığı da (S2, S3a/b, S6a, S7) D1–D3'te karşılandığı için D6'da `READY` sayılır |

---

## 9. Kanıt sınırları

- Dalga ataması `04 §4` GAP bağımlılık haritası, `06 §6` dilim grafiği ve
  `12 §2` aciliyet puanlarına dayanır; bu üç girdinin ötesinde yeni bir
  önceliklendirme ekseni kullanılmamıştır.
- Alt dilim sınırları (`S3a/b/c`, `S6a/b/c`, `S16a/b/c`) `06 §3`'ün önerilerinden
  devralınmıştır ve yaklaşıktır; migration kapsamı netleştiğinde yeniden
  bölünebilirler.
- Dalga bir takvim birimi değildir. Dalga uzunluğu ekip sayısına bağlıdır ve
  §6.1'deki senaryolara göre değişir; bu belge adam/gün tahmini vermez.
- Migration listeleri `06 §3`'teki tablo adlarından türetilmiştir; kolon
  tasarımı ve mevcut tabloların genişletilme kapsamı bu belgenin dışındadır.
- Hard/soft bağımlılık ayrımı bu belgede yapılmıştır; `06` bu ayrımı içermez.
  Soft olarak işaretlenen her bağımlılık §8'de açık kalem olarak izlenir —
  "soft" hiçbir yerde "gerekmez" anlamına gelmez.
- `04 §5`'teki **Q-01** (üretim composition root'unun repo dışında olması)
  hâlâ açıktır. "Evet" yanıtı D1'in kapsamını ve dolayısıyla tüm dalga
  zincirinin başlangıcını değiştirir.
- `DEFER` sınıfındaki iki dilim (S14, S15) bu belgede D6'ya yerleştirilmiştir;
  bu, `06`'nın `DEFER` kararını iptal etmez, dalga diline çevirir.

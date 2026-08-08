---
type: functional-audit-work
stage: "06 — Dikey Dilim Adayları"
scope: vertical-slice-candidates
inputs:
  - ../04-Functional-Gap-Inventory.md
  - ../09-State-Machines.md
  - ../10-Roles-and-Permissions.md
  - ../11-Test-Coverage-Gaps.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-04
---

# 06 — Dikey Dilim Adayları ve Değerlendirme

> 27 GAP kaydının dikey dilimlere (vertical slice) gruplandırılması ve her
> dilimin aşağıdaki ölçütlerle değerlendirilmesi. Bu aşamada **yeni özellik
> veya yeni GAP eklenmez**; yalnız mevcut GAP'lar gruplandırılır ve
> değerlendirilir.
>
> Her dilim, tamamlanınca gözlenebilir bir sonuç üreten; domain, persistence,
> API, yetki, audit, test ve (gerekiyorsa) UI zincirini kapsayan bir birimdir.

---

## 1. Değerlendirme ölçütleri

### 1.1 Boyut kuralı

İdeal bir dikey dilim:

- 1 ana kullanıcı/sistem akışı
- 3–8 ilişkili GAP
- 1 ana domain sınırı
- Sınırlı sayıda migration
- Tamamlanabilir API/UI/test zinciri

Bir dilim **15–20 GAP taşıyorsa** fazla büyüktür. Tek GAP taşıyorsa, o GAP'ın
gerçekten bağımsız bir değer üretip üretmediği değerlendirilir.

### 1.2 Nitel ölçütler

| # | Soru | Ölçüt |
|---|---|---|
| Q1 | Tek ve açık bir kullanıcı/sistem değeri üretiyor mu? | "Evet" veya "Hayır" — belirsiz kabul edilmez |
| Q2 | Başlangıç tetikleyicisi açık mı? | Bir olay, zamanlama veya kullanıcı eylemiyle başlar |
| Q3 | Tamamlandığında gözlenebilir bir sonuç oluşuyor mu? | API yanıtı, UI ekranı, audit kaydı veya bildirim |
| Q4 | Domain → persistence → API → yetki → audit → test → (UI) zinciri tamamlanıyor mu? | Her katmanda eksik olmayan bir yol |
| Q5 | Bir iterasyonda tamamlanabilecek büyüklükte mi? | Makul bir iterasyonda (2–4 hafta) bitirilebilir |
| Q6 | Başka bir dilimin işini gereksiz biçimde tekrar ediyor mu? | Çakışma yok |
| Q7 | Kapsadığı GAP kayıtları doğru mu? | Her GAP bu dilimin akışına ait |
| Q8 | Hard dependency eksik mi? | Bağımlı olduğu dilim ya aynı anda ya da daha önce tamamlanır |
| Q9 | Teknik katman işi olarak mı kalmış, yoksa gerçek dikey dilim mi? | Yalnız altyapı değişikliği değil |
| Q10 | Kapsam dışı sınırı yeterince açık mı? | Neyi yapmadığı belirtilmiş |

### 1.3 Sınıflar

| Sınıf | Anlam |
|---|---|
| `READY` | Ölçütleri karşılıyor; iterasyon planına alınabilir |
| `SPLIT_REQUIRED` | Fazla geniş; alt dilimlere bölünmeli |
| `MERGE_REQUIRED` | Çok dar; başka bir dilimle birleştirilmeli |
| `DEPENDENCY_MISSING` | Bağımlı olduğu dilim belirsiz veya sıralama çelişkili |
| `TOO_TECHNICAL` | Yalnız teknik katman işi; kullanıcı/sistem değeri yok |
| `TOO_BROAD` | Birden fazla domain/akış kapsıyor; bölünmeli |
| `DEFER` | Şu aşamada iterasyona alınamaz; bağımlılık veya kapsam belirsiz |

---

## 2. GAP dağılım özeti

27 GAP'ın 16 dilime dağıtımı:

| Dilim | GAP'lar | GAP sayısı | Birincil domain |
|---|---|---|---|
| S1 | GAP-027 | 1 | D03/D06/D07 (cross-cutting) |
| S2 | GAP-001, GAP-002 | 2 | D07 (altyapı) |
| S3 | GAP-022 | 1 | D02 |
| S4 | GAP-004, GAP-005, GAP-019 | 3 | D04, D05 |
| S5 | GAP-020, GAP-021, GAP-003 | 3 | D06, D07 |
| S6 | GAP-006, GAP-014, GAP-007 | 3 | D09, D12 |
| S7 | GAP-008 | 1 | D08 |
| S8 | GAP-009 | 1 | D09 |
| S9 | GAP-018, GAP-024 | 2 | D07, D14 |
| S10 | GAP-015, GAP-016 | 2 | D11 |
| S11 | GAP-011 | 1 | D13 |
| S12 | GAP-012, GAP-013 | 2 | D10 |
| S13 | GAP-010 | 1 | D10 |
| S14 | GAP-023 | 1 | D12 |
| S15 | GAP-025 | 1 | D15 |
| S16 | GAP-026 | 1 | D01 |
| | **Toplam** | **27** | |

---

## 3. Dilim değerlendirmeleri

### S1 — Komut yolu güvenliği

| Alan | Değer |
|---|---|
| GAP'lar | GAP-027 |
| Domain | D03, D06, D07 (cross-cutting) |
| Akış | A, B, D |
| Değer | Çalışan komut yüzeyindeki yetki ve onay bypass'ını kapatır |
| Tetikleyici | Denetim bulgusu (K9) — güvenlik açığı |
| Gözlenebilir sonuç | `POST /data-sources/{id}/activation` maker ≠ checker ise `403` döner; `"unknown"` aktör reddedilir |
| Migration | Yok |
| Bağımlılık | **Bağımsız** — GAP-001 ve GAP-022'yi beklemez |

**Zincir değerlendirmesi:**

| Katman | Durum | Not |
|---|---|---|
| Domain | ✅ | `DataSourceService.decide_activation`, `RuleService.decide_rule_approval` mevcut |
| Persistence | ✅ | Migration ve tablo var |
| API | ⚠️ | Route'lar var; `ActorContext` iletilmesi gerekiyor |
| Yetki | ⚠️ | Servis kuralı var; porta taşınması gerekiyor |
| Audit | ⚠️ | Olay tanımlı; bypass nedeniyle üretilmiyor |
| Test | ⚠️ | İki yanıltıcı test düzeltilmeli |
| UI | — | Değişiklik yok |

**Ölçüt yanıtları:**

| # | Soru | Yanıt |
|---|---|---|
| Q1 | Tek değer? | Evet — güvenlik bypass'ını kapatır |
| Q2 | Tetikleyici? | Evet — denetim bulgusu |
| Q3 | Gözlenebilir sonuç? | Evet — `403` yanıtı, audit kaydı |
| Q4 | Zincir tam mı? | Evet — servis var, yalnız port ve route değişikliği |
| Q5 | Tek iterasyon? | Evet — migration yok, küçük değişiklik |
| Q6 | Çakışma? | Yok |
| Q7 | GAP doğru mu? | Evet |
| Q8 | Bağımlılık? | Bağımsız |
| Q9 | Teknik iş mi? | **Sınırda.** Yalnız port sözleşmesi ve route wiring değişikliği; yeni kullanıcı değeri üretmez, mevcut değerin güvenliğini sağlar. Ancak denetim açısından kritiktir ve "teknik iş" değil "güvenlik düzeltmesi"dir |
| Q10 | Kapsam dışı? | Evet — yeni endpoint veya rol eklenmez |

**Sınıf: `READY`**

Tek GAP'lı olmasına rağmen bağımsız değer üretir (güvenlik), tetikleyicisi
açık (denetim), gözlenebilir sonucu vardır (`403`), bir iterasyonda
tamamlanır ve başka bir dilimin işini tekrar etmez. "Teknik iş" sınırında
olmakla birlikte, güvenlik düzeltmesi niteliği `TOO_TECHNICAL` sınıflandırmasını
engeller.

---

### S2 — Runtime temel: Bileşim kökü ve worker

| Alan | Değer |
|---|---|
| GAP'lar | GAP-001, GAP-002 |
| Domain | D07 (altyapı) |
| Akış | A, B, C, D, F, H |
| Değer | Kod ekseninde var olan yeteneklerin runtime'da çalışmasını sağlar |
| Tetikleyici | Tüm asenkron akışların durması |
| Gözlenebilir sonuç | PG'ye yazılan kural/sorun/kaynak süreç yeniden başlatıldığında korunuyor; iş kuyruğa girip işleniyor |
| Migration | Yok (tablolar mevcut) |
| Bağımlılık | Bağımsız (diğer tüm dilimler buna bağımlı) |

**Zincir değerlendirmesi:**

| Katman | Durum | Not |
|---|---|---|
| Domain | ✅ | Servisler mevcut |
| Persistence | ✅ | PG repository'ler kod ekseninde |
| API | ⚠️ | Route'lar var; composition root'a bağlanması gerekiyor |
| Yetki | ⚠️ | GAP-027 (S1) ayrıca ele alınmalı |
| Audit | ⚠️ | Outbox var; composition'a bağlanması gerekiyor |
| Test | ⚠️ | PG testleri skip-gated; smoke testi yok |
| UI | — | Değişiklik yok |

**Ölçüt yanıtları:**

| # | Soru | Yanıt |
|---|---|---|
| Q1 | Tek değer? | Evet — runtime kalıcılık ve asenkron işleme |
| Q2 | Tetikleyici? | Evet — tüm asenkron akışların durması |
| Q3 | Gözlenebilir sonuç? | Evet — kalıcı kayıtlar, işlenen işler |
| Q4 | Zincir tam mı? | Evet — domain → persistence → API → test |
| Q5 | Tek iterasyon? | **Sınırda.** İki GAP ancak sıkı bağımlı; composition root + worker entry point + smoke test |
| Q6 | Çakışma? | Yok |
| Q7 | GAP doğru mu? | Evet |
| Q8 | Bağımlılık? | Bağımsız; diğer dilimler buna bağımlı |
| Q9 | Teknik iş mi? | **Evet, büyük ölçüde.** Yalnız altyapı wiring'i; doğrudan kullanıcı değeri üretmez. Ancak diğer tüm dilimlerin ön koşuludur |
| Q10 | Kapsam dışı? | Evet — IAM (S3) ve komut güvenliği (S1) bu dilimin kapsamı dışında |

**Sınıf: `READY`**

İki GAP birbirine sıkı bağımlı (GAP-002 → GAP-001) ve birlikte tek bir
değer üretir: "kod eksenindeki yeteneklerin runtime'da çalışması." Teknik
iş niteliği baskın olsa da, diğer tüm dilimlerin ön koşulu olması ve
gözlenebilir sonuç (kalıcı kayıtlar, işlenen işler) üretmesi `READY`
sınıflandırmasını haklı kılar.

**Not:** Bu dilim tamamlandığında dahi komut yolu yetki denetimi çalışmaz;
S1 ayrıca ele alınmalıdır.

---

### S3 — Kimlik, rol, izin ve kapsam

| Alan | Değer |
|---|---|
| GAP'lar | GAP-022 |
| Domain | D02 |
| Akış | I |
| Değer | Rol tabanlı yetki sistemi; kapsam çözümleme; SoD zorlama |
| Tetikleyici | Tüm akışların yetki gereksinimi |
| Gözlenebilir sonuç | Rol atama, kapsam tabanlı filtreleme, SoD engelleme, oturum yönetimi |
| Migration | `users`, `roles`, `permissions`, `role_permissions`, `role_assignments`, `assignment_scopes`, `segregation_rules`, `sessions`, `access_review_campaigns`, `access_review_items`, `service_accounts` |
| Bağımlılık | S2 (runtime temel); S1 (komut yolu) ile birlikte çalışmalı |

**Zincir değerlendirmesi:**

| Katman | Durum | Not |
|---|---|---|
| Domain | ❌ | Rol, izin, kapsam servisi yok |
| Persistence | ❌ | Tablolar yok (migration gerekli) |
| API | ❌ | IAM endpoint'leri yok |
| Yetki | ❌ | Kod tanımlı değil |
| Audit | ⚠️ | Olay adları tanımlı; üreten yok |
| Test | ⚠️ | `test_identity.py` (42 test) kimlik doğrulama; rol/izin testi yok |
| UI | ❌ | IAM ekranları yok |

**Ölçüt yanıtları:**

| # | Soru | Yanıt |
|---|---|---|
| Q1 | Tek değer? | Evet — merkezi yetki sistemi |
| Q2 | Tetikleyici? | Evet — tüm akışların yetki gereksinimi |
| Q3 | Gözlenebilir sonuç? | Evet — rol atama, `403` yanıtları, audit |
| Q4 | Zincir tam mı? | Evet — sıfırdan tam dikey |
| Q5 | Tek iterasyon? | **Hayır.** 11+ tablo, 13 rol, 100+ izin, SoD, oturum, erişim gözden geçirme — çok geniş |
| Q6 | Çakışma? | Yok |
| Q7 | GAP doğru mu? | Evet — tek GAP ancak çok geniş |
| Q8 | Bağımlılık? | S2'ye bağımlı |
| Q9 | Teknik iş mi? | Hayır — kullanıcı ve audit değeri var |
| Q10 | Kapsam dışı? | **Belirsiz.** 15 rolün tümü, erişim gözden geçirme, servis hesabı ve oturum yönetimi tek dilimde mi? |

**Sınıf: `SPLIT_REQUIRED`**

Tek GAP (GAP-022) ancak kapsamı çok geniş: 11+ yeni tablo, 13 rol, 100+
izin, 12 SoD çifti, erişim gözden geçirme ve oturum yönetimi. Tek
iterasyonda tamamlanamaz.

**Önerilen alt bölme (uygulama aşamasında yapılmalıdır):**

| Alt dilim | Kapsam | Migration |
|---|---|---|
| S3a | Rol/izin/atanma tanımı + temel scope çözümleme + dev profillerinden geçiş | `roles`, `permissions`, `role_permissions`, `role_assignments`, `assignment_scopes`, `users` |
| S3b | SoD zorlama (servis + DB constraint) + oturum yönetimi + servis hesabı | `segregation_rules`, `sessions`, `service_accounts` |
| S3c | Erişim gözden geçirme kampanyası + otomatik sonlandırma | `access_review_campaigns`, `access_review_items` |

Bu belge alt dilimleri sınıflandırmaz; uygulama aşamasında yapılmalıdır.
Ana dilim `SPLIT_REQUIRED` olarak işaretlenir.

---

### S4 — Kaynak onboarding: Katalog, profil ve şema

| Alan | Değer |
|---|---|
| GAP'lar | GAP-004, GAP-005, GAP-019 |
| Domain | D04, D05 |
| Akış | A, E |
| Değer | Veri kaynağı eklendikten sonra metadata keşfi, profilleme ve şema değişikliği yönetimini tamamlar |
| Tetikleyici | Kaynak aktivasyonundan sonraki adım |
| Gözlenebilir sonuç | Katalog'da dataset/alan görünür; profil çalışır; schema değişikliği karar bekliyor |
| Migration | `metadata_discovery_results`, `discovery_scopes`, `metadata_diffs`, `classification_candidates` (bazıları mevcut) |
| Bağımlılık | S2 (runtime), S1 (komut güvenliği), **S12 (GAP-019 → GAP-013)** |

> **Dairesel bağımlılık uyarısı:** S4'ün GAP-019 (şema değişikliği) S12'deki
> GAP-013'e (etki analizi) bağımlıdır (§4 bağımlılık haritası). S12 ise
> GAP-012 (lineage) için S4'ün katalog yüzeyine (GAP-004) bağımlıdır.
> Uygulama aşamasında çözüm: GAP-019 temel şema değişikliği yüzeyiyle önce
> implemente edilir; etki analizi tümleşimi S12 tamamlandığında eklenir.

**Zincir değerlendirmesi:**

| Katman | Durum | Not |
|---|---|---|
| Domain | ⚠️ | Keşif connector'ü var; profil yürütücü var; diff servisi kısmi |
| Persistence | ⚠️ | Migration'lar kısmi |
| API | ❌ | Keşif tetikleme, profil talebi, şema kararı endpoint'leri yok |
| Yetki | ❌ | Kod tanımlı değil (S3'e bağımlı) |
| Audit | ⚠️ | Olay adları tanımlı |
| Test | ❌ | Keşif/profil/şema testi yok |
| UI | ❌ | Katalog ekranı yok |

**Ölçüt yanıtları:**

| # | Soru | Yanıt |
|---|---|---|
| Q1 | Tek değer? | Evet — kaynak onboarding'in devamı |
| Q2 | Tetikleyici? | Evet — kaynak aktivasyonu (A akışı) |
| Q3 | Gözlenebilir sonuç? | Evet — katalog, profil, şema kararı |
| Q4 | Zincir tam mı? | Evet — domain → persistence → API → test → UI |
| Q5 | Tek iterasyon? | **Sınırda.** 3 GAP, 2 domain, migration + API + UI + test |
| Q6 | Çakışma? | Yok |
| Q7 | GAP doğru mu? | Evet — üçü de A/E akışına ait |
| Q8 | Bağımlılık? | S2, S1 ve **S12'ye** bağımlı (GAP-019 → GAP-013; dairesel — S12 de S4'e bağımlı) |
| Q9 | Teknik iş mi? | Hayır — kullanıcı değeri (katalog ekranı) var |
| Q10 | Kapsam dışı? | Evet — sahiplik atama (S16) kapsam dışı |

**Sınıf: `READY`**

3 GAP, 2 domain (D04 + D05), tek akış (A → E). Boyut olarak ideal
aralıkta. Migration, API, UI ve test zinciri tamamlanabilir. İki domain
kapsaması (`D04` + `D05`) tek akışta birleştiği için `TOO_BROAD` değildir.

---

### S5 — Kural yaşam döngüsü: Şablon, gölge ve zamanlama

| Alan | Değer |
|---|---|
| GAP'lar | GAP-020, GAP-021, GAP-003 |
| Domain | D06, D07 |
| Akış | B |
| Değer | Kural şablonlarından üretim, gölge yürütme ve zamanlama ile kuralların otomatik çalışmasını sağlar |
| Tetikleyici | Kural onayından sonraki adım |
| Gözlenebilir sonuç | Şablon yayımlanabilir; gölge sonuç karşılaştırılabilir; zamanlama tanımlanıp tetiklenebilir |
| Migration | `rule_templates`, `rule_dependencies`, `rule_conflicts`, `schedule_missed_runs`; `schedules` genişletme |
| Bağımlılık | S2 (runtime), S1 (komut güvenliği), **S8 (GAP-016 → GAP-008)** |

**Zincir değerlendirmesi:**

| Katman | Durum | Not |
|---|---|---|
| Domain | ⚠️ | Zamanlama servisi var; şablon ve gölge servisi yok |
| Persistence | ⚠️ | `schedules` tablosu var; şablon tablosu yok |
| API | ❌ | Şablon, gölge, zamanlama endpoint'leri yok |
| Yetki | ❌ | Kod tanımlı değil |
| Audit | ⚠️ | Olay adları tanımlı |
| Test | ⚠️ | Zamanlama testleri var; şablon/gölge yok |
| UI | ❌ | Zamanlama, şablon ve gölge ekranları yok |

**Ölçüt yanıtları:**

| # | Soru | Yanıt |
|---|---|---|
| Q1 | Tek değer? | Evet — kural yaşam döngüsünün otomasyonu |
| Q2 | Tetikleyici? | Evet — kural onayı |
| Q3 | Gözlenebilir sonuç? | Evet — zamanlama tetikleniyor, gölge sonuç görünüyor |
| Q4 | Zincir tam mı? | Evet |
| Q5 | Tek iterasyon? | **Sınırda.** 3 GAP, 2 domain, şablon sıfırdan |
| Q6 | Çakışma? | Yok |
| Q7 | GAP doğru mu? | **Sınırda.** GAP-003 (zamanlama) D07'ye ait; GAP-020/021 D06'ya. İki domain |
| Q8 | Bağımlılık? | S2'ye bağımlı; **GAP-021 → GAP-017 (atanmamış)**; S4 ile çakışan migration yok |
| Q9 | Teknik iş mi? | Hayır — kullanıcı değeri var (zamanlama ekranı) |
| Q10 | Kapsam dışı? | Evet — kural onayı (mevcut) ve kural yürütme (S2) kapsam dışı |

> **Eksik GAP uyarısı:** GAP-021 (gölge yürütme), GAP-017'ye (çalıştırma
> başlat/iptal komut yüzeyi) bağımlıdır (§4 bağımlılık haritası). GAP-017 bu
> belgedeki hiçbir dilime atanmamıştır. GAP-017 (hedef API §4.6'da endpoint'ler
> tanımlı; mevcut durum: UI bağlamıyor, GAP-017) gölge yürütmenin ön koşuludur.
> GAP-017 mantıksal olarak S5'e dahil edilebilir (3→4 GAP, hâlâ ideal aralıkta).
> Bu atama yapılmadan S5 tamamlanamaz.

**Sınıf: `DEPENDENCY_MISSING`**

GAP-021 (gölge yürütme) GAP-017'ye (çalıştırma başlat/iptal komut yüzeyi)
bağımlıdır ve GAP-017 hiçbir dilime atanmamıştır. GAP-017 mantıksal olarak
S5'e dahil edilebilir; bu atama yapıldığında dilim `READY`'ye terfi eder.

---

### S6 — Sorun yaşam döngüsü: Üretim, SLA ve bildirim

| Alan | Değer |
|---|---|
| GAP'lar | GAP-006, GAP-014, GAP-007 |
| Domain | D09, D12 |
| Akış | C |
| Değer | Kalite ihlalinden sorun üretimini, SLA yönetimini ve bildirim teslimatını tamamlar |
| Tetikleyici | Kural sonucu kaydedildiğinde |
| Gözlenebilir sonuç | Otomatik sorun açılıyor; SLA hedefleri var; bildirim teslim ediliyor |
| Migration | `issue_slas`, `issue_escalations`, `notification_events`, `notification_subscriptions`, `notification_channels`, `notification_deliveries` |
| Bağımlılık | S2 (runtime), S1 (komut güvenliği) |

**Zincir değerlendirmesi:**

| Katman | Durum | Not |
|---|---|---|
| Domain | ⚠️ | Issue üretici servisi var; SLA servisi yok; bildirim servisi kısmi |
| Persistence | ⚠️ | Issue tabloları var; SLA ve bildirim tabloları yok |
| API | ⚠️ | Issue API var; SLA ve bildirim API yok |
| Yetki | ❌ | Kod tanımlı değil |
| Audit | ⚠️ | Olay adları tanımlı |
| Test | ⚠️ | Issue birim testleri var; SLA/bildirim yok |
| UI | ❌ | SLA ve bildirim ekranları yok |

**Ölçüt yanıtları:**

| # | Soru | Yanıt |
|---|---|---|
| Q1 | Tek değer? | Evet — sorun yaşam döngüsü |
| Q2 | Tetikleyici? | Evet — kural sonucu |
| Q3 | Gözlenebilir sonuç? | Evet — sorun, SLA, bildirim |
| Q4 | Zincir tam mı? | Evet |
| Q5 | Tek iterasyon? | **Hayır — fazla geniş.** 3 GAP, 2 domain (D09 + D12), 6+ yeni tablo, SLA + eskalasyon + bildirim kanalları + teslimat hattı |
| Q6 | Çakışma? | Yok |
| Q7 | GAP doğru mu? | Evet — üçü de C akışına ait |
| Q8 | Bağımlılık? | S2'ye bağımlı |
| Q9 | Teknik iş mi? | Hayır |
| Q10 | Kapsam dışı? | **Belirsiz.** Bildirim altyapısı (kanal, abonelik, teslimat) ayrı bir altyapı dilimi mi olmalı? |

**Sınıf: `SPLIT_REQUIRED`**

3 GAP, tek akış (C) ancak kapsamı geniş: otomatik sorun üretimi + SLA
hedefleri + eskalasyon + bildirim olayı + kanal yönetimi + teslimat hattı.
6+ yeni tablo ve 2 domain. Tek iterasyonda tamamlanması zor.

**Önerilen alt bölme:**

| Alt dilim | Kapsam |
|---|---|
| S6a | Otomatik sorun üretimi + tekilleştirme + SLA hedefleri (GAP-006 + GAP-014) |
| S6b | Bildirim olayı + teslimat hattı + kanal yönetimi (GAP-007) |

S6b bağımsız bir altyapı dilimi olarak da düşünülebilir; ancak C akışının
bildirim adımı S6a olmadan anlamsızdır. Bu nedenle ana dilim
`SPLIT_REQUIRED` olarak işaretlenir.

---

### S7 — Skor kalıcılığı ve atomik yayım

| Alan | Değer |
|---|---|
| GAP'lar | GAP-008 |
| Domain | D08 |
| Akış | F |
| Değer | Kalite skorlarının kalıcı olarak saklanması, atomik yayımı ve katkı grafiği |
| Tetikleyici | Çalıştırma tamamlandığında |
| Gözlenebilir sonuç | Skor API'si yanıt veriyor; katkı grafiği görüntülenebilir; skor yeniden üretilebilir |
| Migration | `quality_scores`, `score_publications`, `score_contribution_graphs` genişletme |
| Bağımlılık | S2 (runtime) |

> **Not:** GAP-008 bağımsız değer üretir (skor API'si); S2 sonrası küçük
> iterasyon olarak planlanabilir. Farklı domain (D08) nedeniyle S2 veya S4'le
> birleştirme yapay olur.

**Ölçüt yanıtları:**

| # | Soru | Yanıt |
|---|---|---|
| Q1 | Tek değer? | Evet — skor kalıcılığı |
| Q2 | Tetikleyici? | Evet — çalıştırma tamamlanması |
| Q3 | Gözlenebilir sonuç? | Evet — skor API'si |
| Q4 | Zincir tam mı? | Evet |
| Q5 | Tek iterasyon? | Evet — tek GAP, sınırlı migration |
| Q6 | Çakışma? | Yok |
| Q7 | GAP doğru mu? | Evet |
| Q8 | Bağımlılık? | S2'ye bağımlı |
| Q9 | Teknik iş mi? | **Sınırda.** Kalıcılık değişikliği; ancak skor API'si kullanıcı değeri üretir |
| Q10 | Kapsam dışı? | Evet |

**Sınıf: `READY`**

Tek GAP, sınırlı kapsam. Ancak bağımsız kullanıcı değeri üretir (skor API'si)
ve tek başına gözlenebilir sonuç oluşturur. S2 sonrası küçük iterasyon olarak
planlanabilir. Farklı domain (D08) nedeniyle başka bir dilimle birleştirme
yapay olur.

---

### S8 — İstisna ve kalite borcu

| Alan | Değer |
|---|---|
| GAP'lar | GAP-009 |
| Domain | D09 |
| Akış | G |
| Değer | Kalite kuralı istisnası ve kalite borcu takibi |
| Tetikleyici | Veri sahibi istisna talep ettiğinde |
| Gözlenebilir sonuç | İstisna onaylanıyor; kalite borcu kaydı oluşuyor; süre dolunca bastırma kalkıyor |
| Migration | `exceptions`, `exception_suppressions`, `quality_debts` |
| Bağımlılık | S2, S6 (sorun üretimi) |

**Ölçüt yanıtları:**

| # | Soru | Yanıt |
|---|---|---|
| Q1 | Tek değer? | Evet — istisna yönetimi |
| Q2 | Tetikleyici? | Evet — istisna talebi |
| Q3 | Gözlenebilir sonuç? | Evet — istisna onayı, borç kaydı |
| Q4 | Zincir tam mı? | Evet |
| Q5 | Tek iterasyon? | Evet — tek GAP, sınırlı |
| Q6 | Çakışma? | Yok |
| Q7 | GAP doğru mu? | Evet |
| Q8 | Bağımlılık? | S6'ya bağımlı (sorun üretimi olmadan istisna anlamsız) |
| Q9 | Teknik iş mi? | Hayır |
| Q10 | Kapsam dışı? | Evet |

**Sınıf: `MERGE_REQUIRED`**

Tek GAP, dar kapsam. S6 (sorun yaşam döngüsü) ile doğal birleşme noktası
var (her ikisi de D09). S6 bölündüğünde S6a ile birleştirilebilir.

---

### S9 — Operasyon yüzeyi: Kuyruk, dead-letter ve platform sağlığı

| Alan | Değer |
|---|---|
| GAP'lar | GAP-018, GAP-024 |
| Domain | D07, D14 |
| Akış | D |
| Değer | Operasyonel görünürlük: kuyruk, dead-letter, sağlık, olay, bakım |
| Tetikleyici | Operatörün sistemi izleme gereksinimi |
| Gözlenebilir sonuç | Operasyon dashboard'ı; dead-letter listesi; olay kayıtları |
| Migration | `component_health`, `operational_incidents`, `incident_updates`, `maintenance_windows`, `backfill_jobs` |
| Bağımlılık | S2 (runtime) |

**Ölçüt yanıtları:**

| # | Soru | Yanıt |
|---|---|---|
| Q1 | Tek değer? | Evet — operasyonel görünürlük |
| Q2 | Tetikleyici? | Evet — operatör izleme |
| Q3 | Gözlenebilir sonuç? | Evet — dashboard, listeler |
| Q4 | Zincir tam mı? | Evet |
| Q5 | Tek iterasyon? | **Sınırda.** 2 GAP, 2 domain, 5+ yeni tablo |
| Q6 | Çakışma? | Yok |
| Q7 | GAP doğru mu? | Evet — ikisi de operasyonel |
| Q8 | Bağımlılık? | S2'ye bağımlı |
| Q9 | Teknik iş mi? | **Sınırda.** Operatör değeri var; ancak son kullanıcı değeri yok |
| Q10 | Kapsam dışı? | Evet |

**Sınıf: `READY`**

2 GAP, tek akış (D), iki domain (D07 + D14) ancak tek kullanıcı personası
(operatör) altında birleşiyor. 5+ yeni tablo boyut olarak sınırda ancak
tamamlanabilir.

---

### S10 — Raporlama: Asenkron üretim ve zamanlama

| Alan | Değer |
|---|---|
| GAP'lar | GAP-015, GAP-016 |
| Domain | D11 |
| Akış | H |
| Değer | Raporların asenkron üretimi, indirilmesi ve zamanlanması |
| Tetikleyici | Kullanıcı rapor talep ettiğinde |
| Gözlenebilir sonuç | Rapor üretilip indirilebilir; zamanlanmış raporlar otomatik oluşuyor |
| Migration | Yok (tablolar mevcut); `reports` genişletme |
| Bağımlılık | S2 (runtime), S3 (zamanlama altyapısı — S5 ile ilişki) |

**Ölçüt yanıtları:**

| # | Soru | Yanıt |
|---|---|---|
| Q1 | Tek değer? | Evet — raporlama |
| Q2 | Tetikleyici? | Evet — rapor talebi |
| Q3 | Gözlenebilir sonuç? | Evet — rapor dosyası |
| Q4 | Zincir tam mı? | Evet |
| Q5 | Tek iterasyon? | Evet — 2 GAP, tek domain |
| Q6 | Çakışma? | Yok |
| Q7 | GAP doğru mu? | Evet |
| Q8 | Bağımlılık? | S2, S5 ve **S8'e** bağımlı (GAP-016 → GAP-008); S5 ile zamanlama altyapısını paylaşır |
| Q9 | Teknik iş mi? | Hayır — kullanıcı değeri var |
| Q10 | Kapsam dışı? | Evet |

**Sınıf: `READY`**

2 GAP, tek domain (D11), tek akış (H). İdeal boyutta.

---

### S11 — Saklama, imha, legal hold ve arşiv

| Alan | Değer |
|---|---|
| GAP'lar | GAP-011 |
| Domain | D13 |
| Akış | J (yönetişim) |
| Değer | Veri saklama politikası, otomatik imha, yasal muhafaza ve arşiv geri çağırma |
| Tetikleyici | Saklama süresi dolduğunda veya yasal muhafaza gerektiğinde |
| Gözlenebilir sonuç | İmha job'ları çalışıyor; legal hold uygulanıyor; arşiv geri çağrılıyor |
| Migration | `retention_policies`, `disposal_jobs`, `legal_holds`, `archive_recalls` |
| Bağımlılık | S2 (runtime), S3 (yetki) |

**Ölçüt yanıtları:**

| # | Soru | Yanıt |
|---|---|---|
| Q1 | Tek değer? | Evet — veri yaşam döngüsü yönetimi |
| Q2 | Tetikleyici? | Evet — saklama süresi / yasal gereksinim |
| Q3 | Gözlenebilir sonuç? | Evet — imha kaydı, muhafaza, geri çağırma |
| Q4 | Zincir tam mı? | Evet |
| Q5 | Tek iterasyon? | **Sınırda.** 4 alt özellik (saklama, imha, muhafaza, arşiv); migration + servis + API + UI |
| Q6 | Çakışma? | Yok |
| Q7 | GAP doğru mu? | Evet |
| Q8 | Bağımlılık? | S2, S3'e bağımlı |
| Q9 | Teknik iş mi? | Hayır — uyum değeri var |
| Q10 | Kapsam dışı? | Evet |

**Sınıf: `READY`**

Tek GAP ancak 4 alt özellik içeriyor. Boyut olarak sınırda; ancak tek
domain (D13) ve tek akış (J) altında birleşiyor. İmha ve legal hold
kodunun kısmi mevcut olması riski azaltır.

---

### S12 — Lineage, etki analizi ve teşhis

| Alan | Değer |
|---|---|
| GAP'lar | GAP-012, GAP-013 |
| Domain | D10 |
| Akış | E |
| Değer | Lineage grafı, etki simülasyonu, kök neden teşhisi ve kanıtlı öneri |
| Tetikleyici | Şema değişikliği veya kalite sorunu |
| Gözlenebilir sonuç | Lineage grafı görüntülenebilir; etki simülasyonu çalışabilir; teşhis önerisi üretilebilir |
| Migration | `lineage_events`, `lineage_edges`, `column_lineage_edges`, `impact_analyses`, `impact_simulations` genişletme |
| Bağımlılık | S2 (runtime), S4 (katalog) |

**Ölçüt yanıtları:**

| # | Soru | Yanıt |
|---|---|---|
| Q1 | Tek değer? | Evet — veri akışı görünürlüğü |
| Q2 | Tetikleyici? | Evet — şema değişikliği / sorun |
| Q3 | Gözlenebilir sonuç? | Evet — graf, simülasyon, teşhis |
| Q4 | Zincir tam mı? | Evet |
| Q5 | Tek iterasyon? | Evet — 2 GAP, tek domain |
| Q6 | Çakışma? | Yok |
| Q7 | GAP doğru mu? | Evet — GAP-013 → GAP-012 bağımlılığı doğru |
| Q8 | Bağımlılık? | S2, S4'e bağımlı (**dairesel:** S4 → S12 GAP-019/013, S12 → S4 GAP-012 katalog) |
| Q9 | Teknik iş mi? | Hayır |
| Q10 | Kapsam dışı? | Evet — sözleşme (S13) kapsam dışı |

**Sınıf: `READY`**

2 GAP, tek domain (D10), tek akış (E). GAP-013'ün GAP-012'ye bağımlılığı
çapraz bağımlılık haritasında kayıtlı. İdeal boyutta.

---

### S13 — Veri sözleşmesi yaşam döngüsü

| Alan | Değer |
|---|---|
| GAP'lar | GAP-010 |
| Domain | D10 |
| Akış | K |
| Değer | Üretici-tüketici veri sözleşmesi tanımı, kabulü, izlenmesi ve ihlal yönetimi |
| Tetikleyici | İki taraf sahipleri sözleşme tanımladığında |
| Gözlenebilir sonuç | Sözleşme aktif; ihlal durumunda bildirim ve sorun açılıyor |
| Migration | `data_contracts`, `contract_compliance`, `contract_breaches` |
| Bağımlılık | S2, S3, S6 (sorun üretimi), S7 (skor) |

> **Not:** S7 artık `READY` olarak sınıflandırılmıştır; bağımlılık karşılandığında
> S13 planlanabilir.

**Sınıf: `DEPENDENCY_MISSING`**

Tek GAP ancak bağımlılığı geniş: S2 (runtime), S3 (yetki — iki taraf
onayı), S6 (sorun üretimi — ihlalden sorun), S7 (skor — uyum ölçümü).
Dört dilime bağımlı tek GAP'lı bir dilim, sıralama açısından risklidir.
Bağımlılıkları karşılanan dilimler tamamlandığında `READY`'ye
terfi edebilir.

---

### S14 — ServiceNow giden entegrasyon

| Alan | Değer |
|---|---|
| GAP'lar | GAP-023 |
| Domain | D12 |
| Akış | M |
| Değer | Kalite sorunlarının ServiceNow'a otomatik iletilmesi |
| Tetikleyici | Sorun açıldığında veya güncellendiğinde |
| Gözlenebilir sonuç | ServiceNow'da bilet oluşuyor; geri bildirim yansıyor |
| Migration | `integration_records`, `rate_limit_counters` |
| Bağımlılık | S2, S6 (sorun üretimi) |

**Sınıf: `DEFER`**

Entegrasyon yüzeyi, temel akışlar (sorun üretimi, bildirim) tamamlanmadan
anlamlı değildir. ServiceNow adaptörü kod ekseninde mevcut
(`test_servicenow.py` — 38 test); ancak HTTP yüzeyi, idempotency ve geri
bildirim yansıması eksik. Temel akışlar tamamlandıktan sonra planlanabilir.

---

### S15 — Sentetik veri ve kontrol doğrulama

| Alan | Değer |
|---|---|
| GAP'lar | GAP-025 |
| Domain | D15 |
| Akış | L |
| Değer | Sentetik veri üretimi, ground truth kaydı, tespit doğruluğu ve yeterlilik deneyi |
| Tetikleyici | Kontrol doğrulama gereksinimi |
| Gözlenebilir sonuç | Run başlatılabilir; doğruluk raporu üretilebilir; deney kanıtı saklanıyor |
| Migration | `synthetic_profiles`, `synthetic_runs`, `ground_truth_defects`, `expected_results`, `control_validations`, `control_experiments` |
| Bağımlılık | S2 (runtime) |

**Sınıf: `DEFER`**

Sentetik veri ve kontrol doğrulama, temel kalite akışları (kural, sorun,
skor) tamamlanmadan öncelikli değildir. Generator ve oracle kod ekseninde
mevcut (5 birim + skip-gated entegrasyon testi); ancak uygulama yüzeyi ve
kalıcılık eksik. DQ-CAP prototiplerinin çıktısı için değerli ancak
iterasyon planında sonradan planlanabilir.

---

### S16 — Yönetişim: Organizasyon, domain, sözlük ve politika

| Alan | Değer |
|---|---|
| GAP'lar | GAP-026 |
| Domain | D01 |
| Akış | J |
| Değer | Organizasyon yapısı, veri domaini, sahiplik atama, iş sözlüğü ve politika yaşam döngüsü |
| Tetikleyici | Sistem kurulumu / yönetişim gereksinimi |
| Gözlenebilir sonuç | Organizasyon yapısı tanımlı; sahiplik atanmış; politika yürürlükte |
| Migration | `organizational_units`, `business_domains`, `data_domains`, `domain_asset_assignments`, `asset_ownerships`, `glossary_terms`, `glossary_term_mappings`, `policies`, `policy_rollbacks`, `system_config`, `system_config_history`, `feature_flags` |
| Bağımlılık | S2, S3 |

**Ölçüt yanıtları:**

| # | Soru | Yanıt |
|---|---|---|
| Q1 | Tek değer? | Evet — yönetişim altyapısı |
| Q2 | Tetikleyici? | Evet — sistem kurulumu |
| Q3 | Gözlenebilir sonuç? | Evet — organizasyon yapısı, politika |
| Q4 | Zincir tam mı? | Evet |
| Q5 | Tek iterasyon? | **Hayır — çok geniş.** 12+ tablo, organizasyon + domain + sahiplik + sözlük + politika + konfigürasyon |
| Q6 | Çakışma? | Yok |
| Q7 | GAP doğru mu? | Evet — tek GAP ancak çok geniş |
| Q8 | Bağımlılık? | S2, S3'e bağımlı |
| Q9 | Teknik iş mi? | Hayır — yönetişim değeri var |
| Q10 | Kapsam dışı? | **Belirsiz.** 6 alt özellik tek dilimde |

**Sınıf: `SPLIT_REQUIRED`**

GAP-026 tek kayıt ancak 6 alt özellik içeriyor: organizasyon birimi,
iş/veri domaini, sahiplik atama, iş sözlüğü, politika yaşam döngüsü ve
sistem konfigürasyonu. 12+ yeni tablo. Tek iterasyonda tamamlanamaz.

**Önerilen alt bölme:**

| Alt dilim | Kapsam |
|---|---|
| S16a | Organizasyon + domain + sahiplik atama (D01.C01 + D01.C02) |
| S16b | İş sözlüğü (D01.C03) |
| S16c | Politika yaşam döngüsü + sistem konfigürasyonu (D01.C04 + D01.C05) |

---

## 4. Atanmamış GAP: GAP-017

Aşağıdaki GAP, fonksiyonel GAP envanterinde (§2) kayıtlı olmasına rağmen
hiçbir dikey dilime atanmamıştır:

| Alan | Değer |
|---|---|
| GAP | GAP-017 — Çalıştırma başlat/iptal komut yüzeyi |
| Hedef | `D07.C01.W01.A01` (UI) |
| Mevcut durum | Endpoint var (`POST /executions`, `POST /executions/{id}/cancel`); UI bağlamıyor (GAP-017); backend doğrulama eksik |
| Bağımlılık | GAP-021 (gölge yürütme) → GAP-017 (§4 bağımlılık haritası) |
| Etkilenen dilim | **S5** — GAP-021 (gölge yürütme) GAP-017'ye bağımlıdır |
| Öneri | GAP-017, S5'e dahil edilebilir (S5: 3→4 GAP, hâlâ ideal aralıkta). Bu atama yapıldığında S5 `READY`'ye terfi eder |

> **Not:** Bu belge yeni GAP eklemez; yalnız mevcut GAP'ları gruplandırır.
> GAP-017'nin atanması, uygulama aşamasında S5'in kapsamını genişletir.

---

## 5. Sınıf dağılım özeti

| Sınıf | Dilim sayısı | Dilimler |
|---|---|---|
| `READY` | 8 | S1, S2, S4, S7, S9, S10, S11, S12 |
| `SPLIT_REQUIRED` | 3 | S3, S6, S16 |
| `MERGE_REQUIRED` | 1 | S8 |
| `DEPENDENCY_MISSING` | 2 | S5, S13 |
| `TOO_TECHNICAL` | 0 | — |
| `TOO_BROAD` | 0 | — |
| `DEFER` | 2 | S14, S15 |

---

## 6. Bağımlılık sıralaması

Dilimler arası bağımlılık grafiği:

```
S1 (komut güvenliği) ──── bağımsız, ilk yapılabilir
  │
S2 (runtime temel) ────── bağımsız, S1 ile paralel veya ardından
  │
  ├── S3 (IAM) ─────────── S2'ye bağımlı
  │     │
  │     ├── S4 (katalog/profil) ──── S1, S2, S3
  │     ├── S5 (kural yaşam) ─────── S1, S2, GAP-017 (atanmamış)
  │     ├── S6 (sorun/SLA/bildirim) ─ S1, S2
  │     │     │
  │     │     ├── S7 (skor) ────────── S2
  │     │     ├── S8 (istisna/borç) ── S6
  │     │     └── S13 (sözleşme) ───── S2, S3, S6, S7
  │     │
  │     ├── S9 (operasyon) ─────────── S2
  │     ├── S10 (raporlama) ────────── S2, S5, S8
  │     ├── S11 (saklama) ──────────── S2, S3
  │     ├── S12 (lineage/etki) ─────── S2, S4
  │     └── S16 (yönetişim) ────────── S2, S3
  │
  ├── S14 (ServiceNow) ──── S2, S6 → DEFER
  └── S15 (sentetik) ────── S2 → DEFER
```

**Kritik yol:** S1 → S2 → S3 → S4/S6 → S7/S8/S12 (S5, GAP-017 çözümlenene kadar engelli)

---

## 7. Özet tablosu

| Dilim | GAP'lar | Sınıf | Değişiklik | Gerekçe |
|---|---|---|---|---|
| S1 | GAP-027 | `READY` | — | Bağımsız güvenlik düzeltmesi; tek iterasyon; gözlenebilir sonuç |
| S2 | GAP-001, GAP-002 | `READY` | — | Sıkı bağımlı ikili; runtime temel; diğer dilimlerin ön koşulu |
| S3 | GAP-022 | `SPLIT_REQUIRED` | S3a/S3b/S3c'ye böl | 12+ tablo, 13 rol, 100+ izin; tek iterasyonda tamamlanamaz |
| S4 | GAP-004, GAP-005, GAP-019 | `READY` | — | 3 GAP, 2 domain, tek akış; ideal boyut |
| S5 | GAP-020, GAP-021, GAP-003 | `DEPENDENCY_MISSING` | GAP-017 eksik; S5'e ata | GAP-021 → GAP-017 bağımlılığı; GAP-017 atanmamış |
| S6 | GAP-006, GAP-014, GAP-007 | `SPLIT_REQUIRED` | S6a/S6b'ye böl | 3 GAP, 2 domain, 6+ tablo; bildirim altyapısı ayrılmalı |
| S7 | GAP-008 | `READY` | — | Bağımsız değer (skor API); küçük iterasyon |
| S8 | GAP-009 | `MERGE_REQUIRED` | S6a ile birleştir | Tek GAP; S6 ile aynı domain (D09) |
| S9 | GAP-018, GAP-024 | `READY` | — | 2 GAP, tek persona (operatör); sınırda ancak tamamlanabilir |
| S10 | GAP-015, GAP-016 | `READY` | — | 2 GAP, tek domain (D11), tek akış (H) |
| S11 | GAP-011 | `READY` | — | Tek GAP, 4 alt özellik; sınırda ancak tek domain |
| S12 | GAP-012, GAP-013 | `READY` | — | 2 GAP, tek domain (D10), tek akış (E) |
| S13 | GAP-010 | `DEPENDENCY_MISSING` | 4 dilime bağımlı; sıralama netleştir | Tek GAP, geniş bağımlılık; riskli |
| S14 | GAP-023 | `DEFER` | Temel akışlar sonrası planla | Entegrasyon yüzeyi; temel olmadan anlamsız |
| S15 | GAP-025 | `DEFER` | Temel akışlar sonrası planla | Sentetik doğrulama; öncelik dışı |
| S16 | GAP-026 | `SPLIT_REQUIRED` | S16a/S16b/S16c'ye böl | 12+ tablo, 6 alt özellik; tek iterasyonda tamamlanamaz |

---

## 8. Kanıt sınırları

- Dikey dilim gruplandırması, GAP envanterindeki bağımlılık haritasına ve
  domain/akış ilişkilerine dayanır.
- `SPLIT_REQUIRED` dilimlerin alt bölme önerileri yaklaşıktır; uygulama
  aşamasında migration kapsamı ve ekip büyüklüğüne göre yeniden
  değerlendirilmelidir.
- `DEFER` sınıflandırması "gerekli değil" anlamına gelmez; "temel akışlar
  tamamlanmadan iterasyon planına alınamaz" anlamındadır.
- GAP-027'nin bağımsız olarak ilk sırada ele alınabileceği tespiti,
  GAP envanteri §4'teki bağımlılık haritasıyla tutarlıdır.
- **GAP-017 hiçbir dilime atanmamıştır.** S5 (GAP-021 → GAP-017) bu
  nedenle `DEPENDENCY_MISSING` olarak işaretlenmiştir. GAP-017'nin S5'e
  atanması, uygulama aşamasında dilimin `READY`'ye terfi etmesiyle
  sonuçlanır.
- **S4 ↔ S12 dairesel bağımlılığı:** GAP-019 (S4) → GAP-013 (S12) ve
  GAP-012 (S12) → GAP-004 (S4). Uygulama aşamasında GAP-019'un temel
  yüzeyi önce implemente edilir; etki analizi tümleşimi S12 sonra eklenir.
- Boyut değerlendirmeleri migration sayısı ve tablo tahminine dayanır;
  kesin kolon tasarımı bu belgenin kapsamı dışındadır.

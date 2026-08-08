---
type: functional-audit
stage: "12 — Öncelikli Backlog"
scope: prioritized-backlog
inputs:
  - 03-End-to-End-Workflow-Audit.md
  - 04-Functional-Gap-Inventory.md
  - 09-State-Machines.md
  - 10-Roles-and-Permissions.md
  - 11-Test-Coverage-Gaps.md
  - work/02-Verification-Resolution.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-05
---

# 12 — Öncelikli Backlog

> [04-Functional-Gap-Inventory.md](04-Functional-Gap-Inventory.md) içindeki
> **27 GAP kaydının** sekiz eksende puanlanması ve `P0`–`P4` sınıflarına
> ayrılması. Bu belge "ne eksik" sorusunu değil, **"önce hangisi"** sorusunu
> yanıtlar. Puanlar bu denetimin yargısıdır; SRS'den veya proje
> dokümantasyonundan türetilmemiştir.

---

## 1. Kapsam ve yöntem

### 1.1 Puanlama eksenleri

Denetim prompt'unun §14 kuralı gereği sekiz eksen kullanılır. İlk altısı
**etkiyi**, son ikisi **uygulanabilirliği** ölçer:

| Eksen | Aralık | Ne ölçer |
|---|---|---|
| Temel akışı bloke etme | 0–5 | 13 kanonik akıştan kaçının ilerlemesini durduruyor veya yanlış yürütüyor |
| Veri bütünlüğü riski | 0–5 | Yanlış, kayıp veya doğrulanamayan veri üretme olasılığı |
| Uyum etkisi | 0–5 | Bankacılık/KVKK denetiminde doğrudan bulgu üretme potansiyeli |
| Kullanıcı etkisi | 0–5 | Son kullanıcının işini yapamaması veya yanlış bilgiyle karar vermesi |
| Operasyonel risk | 0–5 | Çalışan sistemde sessiz birikme, tıkanma veya müdahale edilemezlik |
| Bağımlılık merkeziyeti | 0–5 | Kaç başka GAP'in kapanmasının buna bağlı olduğu |
| Uygulama karmaşıklığı | 1–5 | İşin büyüklüğü (5 = en zor) |
| Mevcut mimariyle uyum | 1–5 | Mevcut kodun ne kadarının yeniden kullanılabildiği (5 = tam uyum) |

### 1.2 Toplam nasıl hesaplanır

**Aciliyet puanı = ilk altı eksenin toplamı (0–30).** Son iki eksen toplama
**dâhil edilmez** ve edilmemelidir: karmaşıklık bir işi daha az önemli
yapmaz, mimari uyum da daha önemli yapmaz. Bu ikisi sıralama içinde
tie-breaker ve dilim tasarımı girdisi olarak kullanılır, ayrı sütunlarda
raporlanır.

Bu ayrım pratik bir sonuç doğurur: yüksek aciliyet + düşük karmaşıklık +
yüksek mimari uyum taşıyan kayıtlar (GAP-027, GAP-003, GAP-006) erken
kazanımlardır; yüksek aciliyet + yüksek karmaşıklık taşıyanlar (GAP-022)
erken **başlatılmalı** ama tek dilimde bitmez.

### 1.3 Sınıf tanımları

Denetim prompt'u §14'ten:

| Sınıf | Tanım |
|---|---|
| `P0` | Çekirdek doğruluğu veya sürekliliği bloke ediyor |
| `P1` | Kurumsal kullanım için zorunlu |
| `P2` | Operasyonel bütünlük ve ölçek |
| `P3` | Gelişmiş ürün kabiliyeti |
| `P4` | İyileştirme/optimizasyon |

**Sınıf, aciliyet puanının mekanik bir fonksiyonu değildir.** Puan sıralamayı
verir; sınıf, puanın yanında niteliksel bir yargı taşır. Puanla sınıfın
ayrıştığı üç kayıt §4'te ayrıca gerekçelendirilmiştir.

### 1.4 Sınıf ≠ uygulama sırası

Bu belge önem sıralamasıdır, takvim değildir. Bir kaydın `P2` olması geç
yapılacağı anlamına gelmez; `P1` olması da hemen başlanabileceği anlamına
gelmez — bağımlılıklar bunu değiştirir (§5). Uygulama sırası
[13-Implementation-Roadmap.md](13-Implementation-Roadmap.md) belgesindedir.

### 1.5 Puanların kanıta bağlanması

Her puan, denetimin önceki aşamalarındaki bir tespite dayanır. Örnek:
GAP-027'nin `uyum etkisi = 5` puanı [10-Roles-and-Permissions.md](10-Roles-and-Permissions.md)
§4.4'teki "çalışan komut yüzeyi ❌ atlanıyor" satırına;
`uygulama karmaşıklığı = 2` puanı ise [06-API-Inventory-and-Gaps.md](06-API-Inventory-and-Gaps.md)
§6'daki "yeni endpoint gerektirmez" tespitine dayanır. §3'te her kayıt için
belirleyici eksenin gerekçesi verilmiştir.

---

## 2. Puanlama tablosu

Aciliyet puanına göre azalan sıralama. Eşitlikte bağımlılık merkeziyeti,
sonra mimari uyum belirleyicidir.

| # | GAP | Akış | Bütün. | Uyum | Kull. | Oper. | Bağ. | **Aciliyet** | Karm. | Mim. | Sınıf |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | GAP-001 Üretim bileşim kökü | 5 | 5 | 5 | 5 | 4 | 5 | **29** | 4 | 5 | `P0` |
| 2 | GAP-002 Kalıcı iş worker süreci | 5 | 3 | 3 | 5 | 5 | 5 | **26** | 3 | 5 | `P0` |
| 3 | GAP-004 Metadata keşfi ve katalog | 5 | 3 | 3 | 5 | 3 | 4 | **23** | 3 | 5 | `P1` |
| 4 | GAP-006 Otomatik sorun üretimi | 5 | 3 | 3 | 5 | 4 | 3 | **23** | 2 | 5 | `P1` |
| 5 | GAP-022 Kullanıcı, rol, izin ve oturum | 3 | 3 | 5 | 3 | 3 | 5 | **22** | 5 | 3 | `P1` |
| 6 | GAP-008 Skor kalıcılığı ve atomik yayım | 4 | 4 | 4 | 4 | 2 | 3 | **21** | 3 | 4 | `P1` |
| 7 | GAP-003 Zamanlayıcı daemon ve yüzeyi | 4 | 2 | 2 | 5 | 4 | 3 | **20** | 2 | 5 | `P1` |
| 8 | GAP-007 Bildirim olayı ve teslimat | 4 | 2 | 2 | 5 | 4 | 3 | **20** | 4 | 4 | `P1` |
| 9 | GAP-027 Komut yolunda onay/kapsam bypass'ı | 3 | 4 | 5 | 2 | 3 | 2 | **19** | 2 | 5 | `P0` |
| 10 | GAP-019 Şema değişimi tespiti ve kararı | 3 | 4 | 2 | 3 | 3 | 2 | **17** | 3 | 4 | `P2` |
| 11 | GAP-016 Rapor asenkron üretimi | 3 | 2 | 3 | 3 | 3 | 2 | **16** | 3 | 4 | `P2` |
| 12 | GAP-009 İstisna/override ve kalite borcu | 3 | 3 | 4 | 3 | 2 | 1 | **16** | 4 | 3 | `P2` |
| 13 | GAP-026 Yönetişim, sözlük ve politika | 2 | 2 | 4 | 2 | 2 | 4 | **16** | 4 | 3 | `P2` |
| 14 | GAP-005 Profil talebi ve baseline | 3 | 3 | 1 | 4 | 2 | 2 | **15** | 3 | 4 | `P2` |
| 15 | GAP-018 Kuyruk ve dead-letter yüzeyi | 2 | 2 | 2 | 3 | 5 | 1 | **15** | 2 | 5 | `P2` |
| 16 | GAP-014 Sorun SLA ve eskalasyon | 3 | 1 | 3 | 4 | 3 | 1 | **15** | 3 | 4 | `P2` |
| 17 | GAP-011 Saklama, imha ve legal hold | 2 | 3 | 5 | 1 | 3 | 1 | **15** | 4 | 3 | `P2` |
| 18 | GAP-024 Operasyon: sağlık, olay, bakım | 1 | 1 | 2 | 2 | 5 | 1 | **12** | 3 | 3 | `P2` |
| 19 | GAP-012 Lineage olay alımı ve graf | 2 | 2 | 3 | 2 | 1 | 2 | **12** | 4 | 3 | `P3` |
| 20 | GAP-017 Çalıştırma başlat/iptal yüzeyi | 2 | 1 | 1 | 4 | 2 | 1 | **11** | 1 | 5 | `P2` |
| 21 | GAP-013 Etki analizi ve simülasyon | 2 | 1 | 2 | 3 | 2 | 1 | **11** | 4 | 3 | `P3` |
| 22 | GAP-020 Kural şablonları ve çakışma | 2 | 3 | 1 | 3 | 1 | 1 | **11** | 3 | 4 | `P3` |
| 23 | GAP-010 Veri sözleşmesi yaşam döngüsü | 2 | 2 | 3 | 2 | 1 | 1 | **11** | 4 | 3 | `P3` |
| 24 | GAP-015 Rapor zamanlama UI bağlantısı | 2 | 1 | 1 | 3 | 2 | 1 | **10** | 1 | 5 | `P2` |
| 25 | GAP-021 Gölge yürütme kullanıcı yolu | 1 | 1 | 1 | 3 | 2 | 1 | **9** | 2 | 4 | `P3` |
| 26 | GAP-025 Sentetik veri yüzeyi | 1 | 1 | 2 | 2 | 1 | 1 | **8** | 2 | 4 | `P4` |
| 27 | GAP-023 ServiceNow giden entegrasyon | 1 | 1 | 1 | 2 | 2 | 1 | **8** | 4 | 3 | `P4` |

### 2.1 Sınıf dağılımı

| Sınıf | Adet | GAP'ler |
|---|---:|---|
| `P0` | 3 | GAP-001, GAP-002, GAP-027 |
| `P1` | 6 | GAP-003, GAP-004, GAP-006, GAP-007, GAP-008, GAP-022 |
| `P2` | 11 | GAP-005, GAP-009, GAP-011, GAP-014, GAP-015, GAP-016, GAP-017, GAP-018, GAP-019, GAP-024, GAP-026 |
| `P3` | 5 | GAP-010, GAP-012, GAP-013, GAP-020, GAP-021 |
| `P4` | 2 | GAP-023, GAP-025 |

### 2.2 Erken kazanım profili

Aciliyeti yüksek, karmaşıklığı düşük ve mimari uyumu tam olan kayıtlar —
yani mevcut kodun büyük bölümünün yeniden kullanılabildiği işler:

| GAP | Aciliyet | Karm. | Mim. | Neden ucuz |
|---|---:|---:|---:|---|
| GAP-027 | 19 | 2 | 5 | Yeni endpoint yok; gerçek servis (`decide_activation`) zaten yazılı ve testli |
| GAP-003 | 20 | 2 | 5 | `SchedulingService.create_schedule`/`trigger_due` yazılı ve 10 birim testi var |
| GAP-006 | 23 | 2 | 5 | `create_for_trigger` + `add_or_increment` yazılı ve testli; köprü ve kapı eksik |
| GAP-017 | 11 | 1 | 5 | Endpoint mevcut; yalnız frontend istemcisi yok |
| GAP-015 | 10 | 1 | 5 | Backend zamanlama servisi mevcut; UI bağı kopuk |
| GAP-018 | 15 | 2 | 5 | `DeadLetterReprocessService` yazılı; operatör yüzeyi yok |

Bu tablo, denetim prompt'u §18'in "mevcut güçlü parçaların gereksiz yeniden
yazılmaması" kuralının somut karşılığıdır. Bu altı kayıt için sıfırdan servis
yazılmamalıdır.

---

## 3. Sınıf bazında backlog ve gerekçeler

### 3.1 `P0` — Çekirdek doğruluğu veya sürekliliği bloke ediyor

#### GAP-001 — Üretim bileşim kökü · aciliyet 29

**Belirleyici eksenler.** Altı eksenin dördü `5`. Kayıt kaybı (`kullanıcı 5`),
audit zincirinin tamamlanmaması (`uyum 5`), şema ayrışması (`bütünlük 5`) ve
diğer GAP'lerin çoğunun buna bağlı olması (`bağımlılık 5`) bir arada.

**Neden `P0`.** Kalıcılık olmadan hiçbir yeteneğin "çalıştığı"
gösterilemez. `03 §4`'e göre K2 tek başına beş akışı kırar. Ayrıca bu kayıt
üç ayrı somut defekt içerir ve üçü de sessizdir: şema ayrışması
(`dq` ↔ `data_quality`), `_FakePreparedRepo` protokol uyuşmazlığı nedeniyle
audit yayımının hatasız başarısız olması, ve execution yazma/okuma
ayrışması. Sessiz hata sınıfı, bu kaydı puanının da ötesinde önemli kılar.

**Karmaşıklık 4 / mimari uyum 5.** Repository'lerin tamamı yazılı ve testli;
iş bağlama, şema birleştirme ve gerçek `PreparedAuditRepository` sağlamaktan
ibaret. Yeniden yazım gerekmiyor.

#### GAP-002 — Kalıcı iş worker süreci · aciliyet 26

**Belirleyici eksenler.** `operasyonel 5` — kuyruk tek yönlü birikiyor;
`kullanıcı 5` — başlatılan çalıştırma sonsuza dek `QUEUED` kalıyor;
`bağımlılık 5` — skor, sorun, bildirim ve rapor zincirlerinin tamamı worker'a
bağlı.

**Neden `P0`.** Sistemin ana işi ölçüm yapmaktır ve bugün hiçbir ölçüm
tamamlanmıyor. K1 dört akışı kırıyor.

**Puanın gizlediği ayrıntı.** `veri bütünlüğü 3` ve `uyum 3` puanları
"backend tamam" varsayımından değil, doğrulanmış eksiklikten geliyor:
`claim_next` audit parametresi almıyor, dolayısıyla `JOB_CLAIMED` olayı
**kodda da yok** (`work/02-Verification-Resolution.md` A-06). Worker
başlatmak tek başına bu boşluğu kapatmaz.

#### GAP-027 — Komut yolunda onay ve kapsam bypass'ı · aciliyet 19

**Neden puanı düşükken `P0`.** Aciliyet puanı sıralamada dokuzuncu, sınıfı
`P0`. Gerekçe:

1. **Nitelik farkı.** Diğer 26 kayıtta bir adım *gerçekleşmiyor*; burada adım
   gerçekleşiyor ama **kuralsız** gerçekleşiyor (`03 §4.2`, K9). Eksik
   özellik ile devre dışı kalmış kontrol aynı sınıfta değerlendirilemez.
2. **Uyum etkisi 5.** Görev ayrılığı beyanı çalışan ürün için geçersiz.
   `10 §4.4`: maker ≠ checker servis katmanında ve testlerde var, veritabanı
   düzeyinde hiç yok, çalışan komut yüzeyinde ise atlanıyor. Denetimde bu
   yolla tek adımda çürütülebilir.
3. **Sessizlik.** Bypass edilen geçiş audit üretmiyor; kaynak `ACTIVE` oluyor
   ve bunun kaydı kalmıyor. `kullanıcı 2` puanı düşük çünkü kullanıcı bunu
   **fark etmiyor** — bu bir hafifletici değil, ağırlaştırıcı etkendir.
4. **Bağımsızlık.** `04 §4`: GAP-001 ve GAP-022'yi beklemez, yeni endpoint
   gerektirmez. Kapatılmaması için sıra gerekçesi yok.

### 3.2 `P1` — Kurumsal kullanım için zorunlu

| GAP | Aciliyet | Belirleyici gerekçe |
|---|---:|---|
| GAP-004 Metadata keşfi ve katalog | 23 | Onboarding akışı burada duruyor; kural yazarı dataset/alan kimliklerini elle giriyor ve geçersiz referans ancak çalıştırma anında ortaya çıkıyor. Sınıflandırma yokluğunda `BR-D04-006` gereği tüm alanlar hassas varsayılmak zorunda |
| GAP-006 Otomatik sorun üretimi | 23 | Kalite bozulması hiç kimseye ulaşmıyor; sorun listesi yalnız seed veriden besleniyor. `bütünlük 3` puanı uygunluk kapısının yokluğundan: `eligible_for_auto_issue` trigger sözleşmesine taşınmıyor, bu yüzden köprü tek başına yanlış sonuç sınıfının sorun üretmesini engellemiyor |
| GAP-022 Kullanıcı, rol, izin ve oturum | 22 | `uyum 5` — erişim gözden geçirme kanıtı üretilemiyor, roller serbest dize. `bağımlılık 5` — diğer tüm GAP'lerin yetki kodları buna bağlı. `karmaşıklık 5` — tek dilimde bitmez, dış IdP bağımlılığı taşır |
| GAP-008 Skor kalıcılığı ve atomik yayım | 21 | Ürünün adı "skorlama"; skor kalıcı değil. `bütünlük 4`/`uyum 4` — "skor yeniden üretilebilir" ilkesi kanıtlanamıyor, dashboard sentetik değer gösteriyor |
| GAP-003 Zamanlayıcı daemon ve yüzeyi | 20 | Aktive edilen hiçbir kural kendiliğinden çalışmıyor; ölçüm tamamen manuel tetiklemeye bağlı, dolayısıyla skor zaman serisi birikmiyor. Erken kazanım (karm. 2 / mim. 5) |
| GAP-007 Bildirim olayı ve teslimat | 20 | Sahiplendirme fiilen çalışmıyor: sorun açılışı, atama, SLA riski ve dead-letter olaylarının hiçbiri kimseye ulaşmıyor. `karmaşıklık 4` broker dış bağımlılığından |

**`P1` sınıfının ortak özelliği.** Bu altı kaydın hiçbiri olmadan sistem
"kurumsal bir veri kalitesi platformu" olarak kullanılamaz; ancak hiçbiri
`P0`'lar kapanmadan tek başına değer üretmez. GAP-004 dışındakiler doğrudan
veya dolaylı olarak GAP-001/GAP-002'ye bağlıdır.

### 3.3 `P2` — Operasyonel bütünlük ve ölçek

| GAP | Aciliyet | Belirleyici gerekçe |
|---|---:|---|
| GAP-019 Şema değişimi | 17 | `bütünlük 4` — sessiz şema kayması yanlış ölçüm üretir ve kimse fark etmez |
| GAP-016 Rapor asenkron üretimi | 16 | Rapor istek içinde üretiliyor ve içeriği sabit; hassasiyet/DLP kararları gerçek veriye uygulanmıyor |
| GAP-009 İstisna ve kalite borcu | 16 | `uyum 4` — bilinen ve kabul edilmiş sapma yönetilemiyor, ham ölçüm garantisi yok |
| GAP-026 Yönetişim, sözlük, politika | 16 | `bağımlılık 4` — kapsam ve sahiplik modelinin güvenilir kaynağı; `uyum 4` — "hangi politika ne zaman yürürlükteydi" kanıtlanamıyor |
| GAP-005 Profil talebi ve baseline | 15 | Baseline örtük (`sorted_profiles[idx-1]`); "normal" tanımı kayan bir referansa göre ölçülüyor |
| GAP-018 Kuyruk ve dead-letter yüzeyi | 15 | `operasyonel 5` — operatör sıkışan işten habersiz; erken kazanım (karm. 2 / mim. 5) |
| GAP-014 Sorun SLA ve eskalasyon | 15 | Geciken sorun görünmez; yönetim raporlarında yanıt/çözüm süresi yok |
| GAP-011 Saklama, imha, legal hold | 15 | `uyum 5` — KVKK saklama süresi zorunluluğu; `retention_policies` tablosu hiç yok |
| GAP-024 Operasyon: sağlık, olay, bakım | 12 | `operasyonel 5` — platform sağlığı görünürlüğü hiç yok |
| GAP-017 Çalıştırma başlat/iptal yüzeyi | 11 | Endpoint mevcut, UI yok; en ucuz kayıt (karm. 1) |
| GAP-015 Rapor zamanlama UI bağlantısı | 10 | Backend mevcut, UI bağı kopuk; en ucuz kayıtlardan (karm. 1) |

### 3.4 `P3` — Gelişmiş ürün kabiliyeti

| GAP | Aciliyet | Belirleyici gerekçe |
|---|---:|---|
| GAP-012 Lineage olay alımı | 12 | `uyum 3` — veri soyu bankacılıkta beklenen bir yetenek, ancak çekirdek ölçüm zincirinin dışında |
| GAP-013 Etki analizi ve simülasyon | 11 | GAP-012'ye bağımlı; kanıt yoksa `UNKNOWN` raporlanmalı (`BR-D10-004`) |
| GAP-020 Kural şablonları ve çakışma | 11 | `bütünlük 3` — mükerrer kural skorda iki kez sayılır (`BR-D06-011`) |
| GAP-010 Veri sözleşmesi | 11 | Tam bir domain; çekirdek çalışmadan değer üretmez |
| GAP-021 Gölge yürütme yüzeyi | 9 | Backend mevcut, yalnız kullanıcı yolu yok |

### 3.5 `P4` — İyileştirme/optimizasyon

| GAP | Aciliyet | Belirleyici gerekçe |
|---|---:|---|
| GAP-025 Sentetik veri yüzeyi | 8 | Servis, generator ve oracle mevcut; CLI ile kullanılabiliyor. HTTP yüzeyi bir kolaylık, engel değil |
| GAP-023 ServiceNow entegrasyonu | 8 | Dış sistem bağımlılığı; `Sonraki-Adimlar.md`'de zaten `ExternalDependency` olarak kayıtlı |

---

## 4. Puan ile sınıfın ayrıştığı kayıtlar

Sınıf mekanik olarak puandan türetilmediği için üç kayıtta ayrışma vardır.
Şeffaflık için açıkça listelenir:

| GAP | Aciliyet sırası | Sınıf | Ayrışmanın gerekçesi |
|---|---:|---|---|
| GAP-027 | 9. | `P0` | Eksik özellik değil, **devre dışı kalmış kontrol**. Nitelik farkı puanla ifade edilemiyor (§3.1) |
| GAP-017 | 20. | `P2` | Puanı düşük ama karmaşıklığı `1`; `P3`'e bırakmak, bir günlük işi yıllara ertelemek olurdu |
| GAP-015 | 24. | `P2` | Aynı gerekçe: karmaşıklık `1`, mimari uyum `5`. Backend zaten var, yalnız UI bağı kopuk |

Buna karşılık GAP-011 (`uyum 5`) bilinçli olarak `P2` bırakıldı: uyum etkisi
en yüksek eksende olsa da saklama zinciri, üzerinde çalışacağı kalıcı veri
üretilmeden başlatılamaz.

---

## 5. Bağımlılıkla çelişen öncelikler

Yüksek sınıfta olup **önce gelemeyecek** kayıtlar. Bu tablo, sınıfı bir
takvim olarak okuyan bir planlamayı engellemek için vardır.

| GAP | Sınıf | Neden hemen başlatılamaz | Beklediği kayıt |
|---|---|---|---|
| GAP-006 | `P1` | Sorun üretecek başarısız ölçüm sonucu yok | GAP-002 (worker), GAP-001 |
| GAP-008 | `P1` | Skorlanacak sonuç üretilmiyor | GAP-002, GAP-001 |
| GAP-003 | `P1` | Tetiklediği iş işlenmeyecek | GAP-002 |
| GAP-007 | `P1` | Teslimat işi kuyrukta işlenmeli | GAP-002 |
| GAP-009 | `P2` | Bastıracağı sorun üretilmiyor | GAP-006, GAP-007 |
| GAP-014 | `P2` | SLA atanacak sorun üretilmiyor | GAP-006, GAP-007 |
| GAP-013 | `P3` | Analiz edecek lineage verisi yok | GAP-012 |
| GAP-019 | `P2` | Karşılaştıracak metadata anlık görüntüsü yok | GAP-004, GAP-013 |
| GAP-005 | `P2` | Profillenecek dataset kaydı yok | GAP-004, GAP-002 |

**Tersine bağımsız olanlar.** GAP-027 hiçbir kaydı beklemez ve yeni endpoint
gerektirmez. GAP-001 ve GAP-004 de bağımsız başlatılabilir. Bu üçü, uygulama
sırasının başındaki üç dilimi oluşturur ([13 §2](13-Implementation-Roadmap.md)).

**GAP-022 istisnası.** `bağımlılık merkeziyeti 5` puanı "her şey buna bağlı"
demektir, ancak bu ters yönde de okunmalıdır: kalıcı IAM olmadan diğer
GAP'lerin yetki kodları **yazılamaz**, fakat yazılabilir hâle gelmeleri için
IAM'in tamamının bitmesi gerekmez. Yetki port'unun sözleşmesi erken
sabitlenirse (GAP-027 kapsamında), diğer dilimler bu sözleşmeye karşı
yazılabilir ve IAM implementasyonu paralel ilerleyebilir.

---

## 6. Kanıt sınırları

- **Puanlar bu denetimin yargısıdır.** Paydaş görüşü, kullanım sıklığı
  ölçümü veya iş etkisi analizi girdisi yoktur. Bankanın öncelikleri bu
  sıralamayı değiştirebilir; özellikle `uyum etkisi` ekseni kurumun kendi
  denetim takvimine göre yeniden ağırlıklandırılmalıdır.
- **`uygulama karmaşıklığı` bir efor tahmini değildir.** Repository'de
  story point, gün veya hafta tahmini konvansiyonu yoktur ve bu belge de
  üretmemiştir. `1–5` ölçeği yalnız kayıtlar arası göreli büyüklüğü verir.
- Puanlar 27 GAP'in **mevcut tanımına** göre verilmiştir. GAP tanımları
  `work/02-Verification-Resolution.md` sonrası güncellenmiştir; daha eski bir
  sürümle karşılaştırılmamalıdır.
- `bağımlılık merkeziyeti` ekseni `04 §4` haritasından türetilmiştir; o
  harita da bu denetimin çıkarımıdır, çalıştırma kanıtı değildir.
- Aciliyet puanları arasındaki `1–2` puanlık farklar anlamlı kabul
  edilmemelidir. Sıralama, sınıf içindeki kaba gruplama için güvenilirdir;
  bitişik iki kaydın kesin sırası için değil.

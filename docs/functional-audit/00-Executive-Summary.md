---
type: functional-audit
stage: "00 — Yönetici Özeti"
scope: executive-summary
inputs:
  - 01-Current-Capabilities.md
  - 03-End-to-End-Workflow-Audit.md
  - 04-Functional-Gap-Inventory.md
  - 12-Prioritized-Backlog.md
  - 13-Implementation-Roadmap.md
  - 14-Independent-Code-Verification.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-05
---

# 00 — Yönetici Özeti

> On dört aşamalı fonksiyonel denetimin karar vericiye yönelik özeti.
> Ayrıntılar ilgili aşama belgelerindedir; buradaki her iddia bir kanıta
> bağlıdır.

---

## 1. Teknik olmayan özet

Sistem, bir veri kalitesi platformunun ihtiyaç duyduğu **iş mantığının büyük
bölümüne sahiptir**. Kural yazma, ölçüm yapma, sorun üretme, skor hesaplama,
zamanlama ve denetim izi bırakma mantığı yazılmış ve önemli ölçüde test
edilmiştir. Bu, hafife alınmaması gereken bir varlıktır.

Buna karşılık bu parçaların çoğu **çalışan uygulamaya bağlanmamıştır.**
Denetim, 13 uçtan uca iş akışının 161 adımını tek tek izledi ve akışların
**hiçbirinin baştan sona yürümediğini** tespit etti. Somut karşılıkları:

- Kullanıcının oluşturduğu veri kaynağı veya kural, uygulama yeniden
  başladığında **kaybolur**.
- Başlatılan bir ölçüm **hiçbir zaman tamamlanmaz**; iş kuyruğa girer ve
  orada kalır, çünkü işi alacak süreç hiç başlatılmamıştır.
- Kalite bozulduğunda **kimseye haber gitmez**; sorun listesi örnek veriyle
  doludur.
- Ekrandaki kalite skoru **gerçek ölçümden gelmez**, örnek veriden gelir.
- Bir kişi, ikinci bir onaycıya gerek kalmadan bir veri kaynağını **tek
  başına aktive edebilir** ve bu işlemin denetim kaydı oluşmaz.

Sonuncusu diğerlerinden farklıdır ve en kritik bulgudur: burada eksik olan
bir özellik değil, **yazılmış ve test edilmiş bir kontrolün devre dışı
kalmasıdır**. Kod maker-checker (iki farklı kişi onayı) kuralını uygular;
kullanıcının eriştiği yol bu kuralı hiç çağırmaz.

**Genel değerlendirme.** Sistem bir prototip olgunluğundadır. Kurumsal
kullanım için gereken mesafe, sıfırdan yazmak değil, **var olanı bağlamak,
eksik yüzeyi eklemek ve devre dışı kalmış kontrolleri devreye almaktır.**
Bu, iyi bir haberdir: [13-Implementation-Roadmap.md](13-Implementation-Roadmap.md)
belgesindeki 23 dilimin büyük bölümü mevcut kodu yeniden kullanır.

---

## 2. Sistemin genel durumu

| Alan | Değerlendirme | Kanıt |
|---|---|---|
| İş mantığı (domain servisleri) | **Güçlü** — kural, ölçüm, sorun, skor, zamanlama, keşif mantığı yazılı ve testli | `01 §3`, `14 §6` |
| Uçtan uca çalışırlık | **Yok** — 13 akıştan hiçbiri baştan sona yürümüyor | `03 §2` (161 adım denetlendi) |
| Kalıcılık | **Kısmi** — 31 tablo ve PostgreSQL repository'leri var; çoğu çalışan bileşime bağlı değil | `01 §2.3`, `04` GAP-001 |
| Yetkilendirme — okuma | **Çalışıyor** — kapsam filtresi backend'de uygulanıyor, boş kapsam testli | `10 §6.1.1`, `11 §6.2` |
| Yetkilendirme — komut | **Yok** — aktör bağlamı komut portuna hiç geçmiyor | `10 §6.1.2`, `04` GAP-027 |
| Görev ayrılığı (maker-checker) | **Serviste var, çalışan üründe atlanıyor** | `10 §4.4`, `09 §6.4` |
| Denetim izi (audit) | **Kısmi** — repository katmanında atomik; çalışan uygulamada yayımlanmıyor | `04` GAP-001, `08 §3.2` |
| Kimlik ve rol yönetimi | **Yok** — kullanıcı/rol/izin tablosu hiçbir migration'da yok | `04` GAP-022 |
| Kullanıcı arayüzü | **Dar** — hedef 41 ekrandan 3'ü tam, 6'sı kısmi | `05 §3` |
| API yüzeyi | **Dar** — 44 mevcut uç, 118 hedef uç | `06 §3`, `§4` |
| Test | **Nicelik yüksek, kanıt değeri sınırlı** — 1149 test fonksiyonu; 92 entegrasyon testinin tamamı atlanıyor, E2E test yok | `11 §2.1`, `§8.2` |
| Veri modeli | **Kısmi** — 31 mevcut tablo, 119 hedef; skor, saklama, istisna, sözleşme tabloları yok | `08 §1` |

### 2.1 Sayısal görünüm

| Ölçüt | Değer |
|---|---:|
| Denetlenen uçtan uca akış | 13 |
| Denetlenen akış adımı | 161 |
| Baştan sona yürüyen akış | **0** |
| Tespit edilen fonksiyonel GAP | 27 |
| Kök kırılma nedeni | 9 |
| `P0` sınıfı GAP | 3 |
| `P1` sınıfı GAP | 6 |
| Mevcut tablo / hedef tablo | 31 / 119 |
| Mevcut endpoint / hedef endpoint | 44 / 118 |
| Mevcut ekran / hedef ekran | 9 (3 tam + 6 kısmi) / 41 |
| Test fonksiyonu (parametrizasyonla) | 1149 (1505) |
| Bu ortamda koşan entegrasyon testi | **0** (92 atlandı) |
| Uçtan uca (E2E) test | **0** |

---

## 3. En kritik beş bulgu

### 3.1 Onay adımı çalışan üründe atlanıyor

Veri kaynağı aktivasyonu, kodda yazılı ve test edilmiş onay kontrollerini
**hiç çağırmıyor**. Gerçek servis checker rolünü, talep süresini, politika
sürümünü ve maker ≠ checker kuralını denetler; kullanıcının eriştiği uç ise
yalnız bir durum kontrolü yapan geliştirme deposuna bağlıdır. Sonuç: bir
kişi tek başına kaynağı `ACTIVE` yapar ve bu işlemin **denetim kaydı
oluşmaz**.

Bu bulgu, denetim raporunun ilk sürümünde yoktu; bağımsız doğrulama sırasında
tespit edildi. Ayrıca iki test bu davranışı **başarılı sayarak sabitliyor** —
biri adında `403` beklendiğini söylerken kodda `201` doğruluyor.

> **Neden en kritik.** Diğer bulgularda bir işlem *gerçekleşmiyor*; burada
> gerçekleşiyor ama kuralsız gerçekleşiyor ve sessiz. Görev ayrılığı beyanı
> çalışan ürün için geçersiz. → `GAP-027`, dilim `DS-01`

### 3.2 Kayıtlar kalıcı değil, denetim izi yayımlanmıyor

Yazılmış PostgreSQL repository'lerinin önemli bölümü çalıştırılabilir
uygulamaya bağlı değildir; kaynak, kural ve sorun bellek içi depolarda
tutulur ve süreç yeniden başladığında kaybolur. Buna üç sessiz defekt eşlik
eder: iş verisi ile denetim kaydı **farklı veritabanı şemalarına** yazılır,
denetim yayımı bir protokol uyuşmazlığı nedeniyle **hata vermeden başarısız
olur**, ve başlatılan ölçüm veritabanına yazıldığı hâlde **listede
görünmez**.

> **Neden kritik.** Kalıcılık olmadan hiçbir yeteneğin çalıştığı
> gösterilemez; denetim izi olmadan hiçbir işlem kanıtlanamaz.
> → `GAP-001`, dilim `DS-02`

### 3.3 Ölçümler hiç tamamlanmıyor

Kalıcı iş kuyruğu yazılmış ve testlidir, ancak işi alıp yürütecek süreç
**hiçbir yerden başlatılmıyor** — ne üretimde, ne testlerde. Başlatılan her
çalıştırma kuyrukta birikir. Ayrıca işin sahiplenilmesi denetim olayı
üretmez; bu, "kuyruk tarafı tamam, yalnız süreç eksik" değerlendirmesinin
düzeltilmesini gerektiren bir kod eksikliğidir.

> **Neden kritik.** Sistemin ana işi ölçüm yapmaktır ve bugün hiçbir ölçüm
> tamamlanmıyor. → `GAP-002`, dilim `DS-03`

### 3.4 Kalite bozulması kimseye ulaşmıyor

Sorun üreten servis — tekilleştirme, yinelenme sayımı ve denetim kaydı
dâhil — yazılmış ve kapsamlı biçimde test edilmiştir. Eksik olan, başarısız
ölçümü bu servise bağlayan **köprüdür**. Dahası, ölçüm sonucunda "bu sonuç
otomatik sorun üretmeye uygun mu" bilgisi hesaplanıp saklanıyor fakat sorun
üretim sözleşmesine hiç taşınmıyor; yani köprüyü eklemek tek başına
teknik hataların kalite sorunu olarak açılmasını engellemez.

> **Neden kritik.** Ölçüm zincirinin çıktısı hiçbir insana ulaşmıyor.
> → `GAP-006`, dilim `DS-05`

### 3.5 Ekrandaki skor gerçek değil

Ürünün adı skorlamadır; skor hesaplama mantığı zengin ve testlidir. Ancak
skorları saklayacak PostgreSQL tablosu **yoktur** ve dashboard değerleri
örnek veriden okur. Skorun yayımlanması, geçmişe dönük karşılaştırılması ve
yeniden üretilerek doğrulanması bugün mümkün değildir.

> **Neden kritik.** "Skor yeniden üretilebilir" ilkesi denetimde
> kanıtlanamaz; yönetim kararları örnek veriye bakarak alınır.
> → `GAP-008`, dilim `DS-06`

### 3.6 Ek bulgu — kural yönetimi ilk adımdan sonra duruyor

Beş ana bulgunun dışında, kullanıcı açısından en görünür defekt budur:
çalıştırılabilir uygulamada kural **oluşturulabiliyor**, fakat sürüm
eklenemiyor, test edilemiyor, onaya gönderilemiyor ve aktive edilemiyor —
ilgili uçların tamamı `503` dönüyor, çünkü kural mutasyon bileşeni
uygulamaya hiç bağlanmamış. Bu bulgu ne denetim raporunun ilk sürümünde ne
de bağımsız doğrulamada vardı; bu oturumda bağlama kodu okunarak tespit
edildi. → dilim `DS-01`

---

## 4. Ne çalışıyor — yeniden yazılmaması gerekenler

Denetimin en sık yanlış okunan sonucu, "her şeyin eksik olduğu"dur. Bu doğru
değildir ve yanlış bir çıkarım pahalı bir yeniden yazıma yol açar. Aşağıdaki
parçalar **çalışıyor, testli ve korunmalıdır**:

| Parça | Durum |
|---|---|
| Kural yaşam döngüsü ve maker-checker mantığı | Servis düzeyinde tam; onay, sürüm değişmezliği ve reddetme kuralları testli |
| Sorun yaşam döngüsü | Atama, inceleme, çözüm, doğrulama, kapatma; PostgreSQL'de tek transaction'da denetim kaydıyla |
| Zamanlama servisi | Zaman dilimi ve yaz saati doğrulaması, önizleme, idempotent tetikleme; 10 birim testi |
| Metadata keşif orkestrasyonu | Bağlantı denetimi, hata sınıflandırma, fark hesaplama, atomik kalıcılık |
| Profil yürütücüsü | CSV ve PostgreSQL profil üretimi, gelişmiş alan metrikleri |
| İş kuyruğu çekirdeği | `FOR UPDATE SKIP LOCKED`, lease, kota, iyimser kilit — eksik olan yalnız süreç ve sahiplenme denetimi |
| Okuma yolu yetkilendirmesi | Kapsam filtresi backend'de; boş kapsamın kapsamsız sorguya dönüşmediği dört testle sabit |
| Denetim outbox deseni | İş verisi ve denetim kaydı aynı transaction'da — repository katmanında doğru kurulmuş |
| Kimlik altyapısı parçaları | Oturum yaşam döngüsü, LDAP eşlemesi, BFF sınırı — yazılı, yalnız bağlanmamış |
| Sentetik veri üreteci | Servis, generator ve ground truth; komut satırından çalışıyor |

`12 §2.2`, bu parçaların altısını **erken kazanım** olarak işaretler: yüksek
etki, düşük karmaşıklık, mevcut mimariyle tam uyum.

---

## 5. Yol haritası özeti

27 GAP, **23 uçtan uca dikey dilime** dönüştürülmüştür. Dilimler teknik
katmana göre değil, bir kullanıcının baştan sona tamamlayabildiği işe göre
kesilmiştir — bu tercih, denetimin ana bulgusunun doğrudan sonucudur:
katman katman ilerlemek, bugünkü "sekiz halka yazılmış, hiçbir zincir
tamamlanmamış" durumunu yeniden üretir.

| Dalga | Dilimler | Dalga sonunda ürün ne yapabiliyor |
|---|---|---|
| 1 — Güvenli çekirdek | DS-01, DS-02 | Kayıtlar kalıcı; onay atlanamıyor; kural yaşam döngüsü işliyor; denetim izi gerçek |
| 2 — Ölçüm | DS-03, DS-04 | Çalıştırma tamamlanıyor ve görünüyor; kural gerçek dataset'e yazılıyor |
| 3 — Değer zinciri | DS-05, DS-06, DS-07 | Bozulma sorun üretiyor; skor kalıcı ve gerçek; ölçüm kendiliğinden tekrarlanıyor |
| 4 — Ulaşılabilirlik | DS-09, DS-10, DS-11 | Olaylar sahibine ulaşıyor; yetki gerçek; operatör müdahale edebiliyor |
| 5 — Genişleme | DS-08, DS-12, DS-13, DS-20 | Profil/baseline, gerçek raporlar, şema kayması, saklama uyumu |
| 6 — Yönetişim | DS-14, DS-15, DS-16, DS-17, DS-21 | Etki analizi, istisna, SLA, şablonlar, kurumsal yönetişim |
| 7 — Olgunluk | DS-18, DS-19, DS-22, DS-23 | Gölge yürütme, veri sözleşmeleri, kontrol doğrulama, ITSM |

### 5.1 İlk üç dilim

| Dilim | Neden önce | Çıkış kapısı |
|---|---|---|
| **DS-01** Komut yolu bütünlüğü | Hiçbir şeyi beklemez, yeni endpoint gerektirmez ve devre dışı kalmış bir güvenlik kontrolünü devreye alır. Ayrıca kural yaşam döngüsünü `503`'ten kurtarır | Aktivasyon maker=checker ile reddediliyor ve kural mutasyon uçlarının hiçbiri `503` dönmüyor |
| **DS-02** Kalıcılık | Beş akışın ortak kök nedeni; DS-01 ile paralel yürütülebilir | Süreç yeniden başlatıldığında kayıtlar duruyor ve denetim ekranı gerçek olayları gösteriyor |
| **DS-03** Çalıştırma uçtan uca | Dört akışın kök nedeni; skor, sorun, bildirim ve rapor zincirlerinin tamamı buna bağlı | Arayüzden başlatılan çalıştırma işlenip tamamlanıyor ve sonucu aynı listede görünüyor |

**Dalga 1 ve 2 pazarlık konusu değildir.** Bu dört dilim tamamlanmadan
sistemin hiçbir çıktısı — skor, sorun, rapor — kanıt değeri taşımaz.

### 5.2 Efor tahmini neden yok

Bu yol haritası süre, adam-gün veya hikâye puanı içermez. Repository'de
böyle bir konvansiyon yoktur; iterasyonlar **çıkış kapısı** cümlesiyle
boyutlandırılır. Kayıtlar arası göreli büyüklük için
[12-Prioritized-Backlog.md](12-Prioritized-Backlog.md)'deki
`uygulama karmaşıklığı` ekseni (1–5) kullanılabilir; bu bir efor tahmini
değil, göreli zorluk göstergesidir.

---

## 6. Karar bekleyen konular

| Konu | Neden karar gerekiyor |
|---|---|
| Dış bağımlılıklar | Gerçek kimlik sağlayıcı, sır yöneticisi, mesaj broker'ı, SIEM/WORM, ServiceNow ve harici dosya deposu banka tarafındaki kararlara bağlıdır. Yol haritası bunları **port sınırıyla** ele alır: her ilgili dilim dahili implementasyonla uçtan uca çalışır, gerçek sistem yapılandırmayla devreye alınır |
| `main` dalına birleştirme | Çalışma dalında 2026-07-27'den bu yana birikmiş commit'ler var ve hiç birleştirme yapılmamış. Bu bir ajan görevi değil, operatör kararıdır (`docs/memory/Sonraki-Adimlar.md`) |
| Entegrasyon testlerinin CI'da koşması | 92 entegrasyon testi bir PostgreSQL ortam değişkeni tanımlı olmadığı için **hiç koşmuyor**; `.env` sürüm kontrolünde değil. Bu değişken sağlanmadan PostgreSQL davranışına dair hiçbir test kanıtı üretilmiyor |
| Öncelik ağırlıkları | `12`'deki puanlama bu denetimin yargısıdır. Bankanın denetim takvimi, özellikle `uyum etkisi` ekseninin ağırlığını değiştirebilir |

---

## 7. Kanıt sınırları

- **Uygulama bu denetimde ayağa kaldırılmadı.** Çalışma zamanı
  değerlendirmeleri kod ve bileşim okumasına dayanır. Şema ayrışması, denetim
  yayım hatası ve kural uçlarının `503` dönmesi statik olarak kesindir;
  bunların çalışan sistemdeki tam görünümü ölçülmemiştir.
- **Entegrasyon testleri hiç yürümedi** (`92 skipped`). PostgreSQL
  davranışına ilişkin her değerlendirme test **kodunun** okunmasına dayanır;
  "PostgreSQL davranışı doğrulanmıştır" biçiminde okunmamalıdır. Koşulan
  seçili birim suite: `297 passed`.
- **Puanlama ve öncelikler bu denetimin yargısıdır**; paydaş görüşü, kullanım
  ölçümü veya iş etkisi analizi girdisi yoktur.
- **Yol haritası bir plandır**, tamamlanma iddiası değildir. Hiçbir dilim
  uygulanmamıştır. Sonraki dalgaların içeriği, önceki dilimlerin tasarım
  kararları netleştikçe değişecektir.
- Denetimin ilk sürümündeki bazı iddialar bağımsız doğrulama sonrası
  düzeltilmiştir; hangi itirazın kabul, kısmen kabul veya reddedildiği
  [work/02-Verification-Resolution.md](work/02-Verification-Resolution.md)
  belgesinde gerekçesiyle kayıtlıdır. Bu özet **düzeltilmiş** duruma göre
  yazılmıştır.

---

## 8. Belge haritası

| Aşama | Belge | İçerik |
|---|---|---|
| 01 | [Current Capabilities](01-Current-Capabilities.md) | Mevcut yetenekler, çift eksenli durum (kod / çalışma zamanı) |
| 02 | [Target Capability Hierarchy](02-Target-Capability-Hierarchy.md) | 15 domain, 271 yaprak fonksiyonlu hedef model |
| 03 | [End-to-End Workflow Audit](03-End-to-End-Workflow-Audit.md) | 13 akış, 161 adım, 9 kök neden |
| 04 | [Functional Gap Inventory](04-Functional-Gap-Inventory.md) | 27 GAP kaydı ve bağımlılık haritası |
| 05 | [UI Information Architecture](05-UI-Information-Architecture.md) | 41 hedef ekran kartı |
| 06 | [API Inventory and Gaps](06-API-Inventory-and-Gaps.md) | 44 mevcut, 118 hedef endpoint |
| 07 | [Target Data Model](07-Target-Data-Model.md) | 119 tabloluk hedef veri modeli |
| 08 | [Existing Schema Gap Analysis](08-Existing-Schema-Gap-Analysis.md) | 31 mevcut tablo, kolon farkları, şema ayrışması |
| 09 | [State Machines](09-State-Machines.md) | 29 durum makinesi, yasak geçişler |
| 10 | [Roles and Permissions](10-Roles-and-Permissions.md) | 15 rol, izin matrisi, görev ayrılığı |
| 11 | [Test Coverage Gaps](11-Test-Coverage-Gaps.md) | Test niteliği, altyapı ve kapsam boşlukları |
| 12 | [Prioritized Backlog](12-Prioritized-Backlog.md) | 8 eksenli puanlama, `P0`–`P4` |
| 13 | [Implementation Roadmap](13-Implementation-Roadmap.md) | 23 dikey dilim, 7 dalga |
| 14 | [Independent Code Verification](14-Independent-Code-Verification.md) | Bağımsız doğrulama ve itirazlar |
| — | [work/02-Verification-Resolution.md](work/02-Verification-Resolution.md) | İtirazların kabul/ret kararları |

---
type: functional-audit
stage: "02 — Hedef Yetenek Hiyerarşisi"
scope: target-reference-model
model_kind: generic-enterprise
project: Veri Kalitesi İzleme ve Skorlama Sistemi
created_at: 2026-08-04
---

# 02 — Hedef Yetenek Hiyerarşisi (Target Capability Hierarchy)

> **Bu belge bir hedef referans modelidir.** Kurumsal bir veri kalitesi yönetim
> sisteminin uçtan uca çalışabilmesi için ihtiyaç duyduğu fonksiyonları,
> herhangi bir uygulamanın sınırlarından bağımsız olarak tanımlar.

---

## 1. Kapsam ve yöntem

### 1.1 Bu belge nedir

Kurumsal ölçekte veri kalitesi yönetimi yapan bir sistemin **olması gereken**
fonksiyon kümesi. Model, veri yönetişimi ve kalite yönetimi disiplininin
gerektirdiği yetenekler üzerine kurulur; bir gereksinim dokümanı, ürün özellik
listesi veya mevcut bir uygulama modeli sınırlayıcı kabul edilmez.

Model üç şeyi aynı anda karşılamak zorundadır:

1. **İş değeri** — her fonksiyon bir aktörün gerçek bir görevini tamamlar.
2. **Kontrol edilebilirlik** — her durum değiştiren fonksiyonun yetkisi, görev
   ayrılığı gereksinimi ve audit izi tanımlıdır.
3. **Çalıştırılabilirlik** — her fonksiyonun API, ekran, veri ve test ihtiyacı
   belirtilmiştir; hiçbir fonksiyon soyut bir yetenek beyanı olarak bırakılmaz.

### 1.2 Bu belge ne değildir

| Değildir | Gerekçe |
|---|---|
| Uygulama durumu değerlendirmesi | Hangi fonksiyonun nerede karşılandığı bu belgenin konusu değildir; model saf hedef olarak kurulur |
| Gereksinim dokümanı türevi | Model, mevcut gereksinim setinin yeniden düzenlenmiş hâli değildir; kapsamı bağımsız belirlenmiştir |
| Sektöre özgü model | Belirli bir sektörün düzenleyici çerçevesi modele girmez. Görev ayrılığı, değişmez audit izi, veri sınıflandırması ve saklama politikası **genel kurumsal kontroller** olarak yer alır |
| Veri modeli tasarımı | Yapraklar tablo ve ayırt edici kolonları adlandırır; tam şema tasarımı ayrı bir aşamanın konusudur |
| Yol haritası | Öncelik, sıra, maliyet ve iterasyon planı bu belgede yoktur |

### 1.3 Hiyerarşi tanımı

| Seviye | Anlam | Örnek |
|---|---|---|
| **L0** | Sistem | Veri Kalitesi Yönetim Sistemi |
| **L1** | Ana domain | Kalite Kural Yönetimi |
| **L2** | Kabiliyet | Kural yaşam döngüsü ve onayı |
| **L3** | Fonksiyon / iş akışı | Kural sürümü onay akışı |
| **L4** | Atomik kullanıcı/sistem işlemi — **yaprak** | Onay kararı ver |
| **L5** | İş kuralı, validasyon, durum geçişi | Karar veren, talebi açandan farklı olmak zorundadır |

### 1.4 Kodlama şeması

```
L0   DQ                         Sistem
L1   D06                        Domain
L2   D06.C02                    Kabiliyet
L3   D06.C02.W01                Fonksiyon / iş akışı
L4   D06.C02.W01.A03            Atomik işlem              ← yaprak
L5   BR-D06-014                 İş kuralı / validasyon
     ST-QualityRule             Durum makinesi
     PERM rule.approval.decide  İzin kodu
     EVT  RULE_APPROVAL_DECIDED Audit olayı
```

Yaprak kodları belge boyunca benzersizdir ve kalıcıdır.

### 1.5 Yaprak fonksiyon şablonu

Her L4 yaprak, on iki alanlı sabit bir blokla tanımlanır:

| Alan | İçerik |
|---|---|
| Amaç | Fonksiyonun sağladığı iş değeri, tek cümle |
| Aktör | İşlemi yapan rol(ler); sistem tetiklemesinde `Sistem` |
| Tetikleyici | İşlemi başlatan olay, kullanıcı eylemi veya zamanlayıcı |
| Ön koşul | İşlemin yapılabilmesi için sağlanması gereken durum |
| Akış | **Temel**, **Alternatif** ve **Hata** akışları |
| Durum geçişi | Etkilenen varlıkların durum değişimi; yoksa `—` |
| Yetki | `izin kodu` + scope; görev ayrılığı gerekiyorsa açıkça |
| Audit | Üretilen audit olayı ve taşıdığı ayırt edici alanlar |
| API | Yöntem + yol + sözleşme özelliği (idempotency, concurrency) |
| Ekran | Fonksiyonun sunulduğu ekran(lar) |
| Tablo | Yazılan/okunan tablolar ve ayırt edici kolonlar |
| Test | Gerekli test **tipleri** |

### 1.6 Okuma kılavuzu

- Bölüm 4 tam ağacı verir; bir yeteneği aramak için oradan başlanır.
- Bölüm 5 gövdedir; domain → kabiliyet → iş akışı → yaprak sırasıyla ilerler.
- Bölüm 6 kesişen katalogları toplar: durum makineleri, rol/izin matrisi, audit
  olay kataloğu, bildirim kataloğu, hedef veri varlıkları.
- Bölüm 7 uçtan uca akışları yalnız yaprak kodu dizisi olarak gösterir.

---

## 2. L0 — Sistem tanımı

### 2.1 Amaç

Kurumun veri varlıklarının kalitesini **ölçülebilir**, **açıklanabilir** ve
**yönetilebilir** kılmak; kalite bozulmalarını tespit edip sahibine ulaştırmak,
düzeltilmesini uçtan uca izlemek ve tüm bu sürecin denetlenebilir kanıtını
üretmek.

### 2.2 Sistem sınırları

| Sınır | Tanım |
|---|---|
| **Kaynak veriye erişim** | Salt okunur. Sistem kaynak üretim verisini değiştirmez; yalnız okur, ölçer ve örnekler |
| **Sistemin sahibi olduğu veri** | Metadata, katalog, politika, kural, çalıştırma, sonuç, skor, sorun, sözleşme, bildirim, rapor ve audit kayıtları — bunlar yazılabilirdir |
| **Kimlik kaynağı** | Kurumsal dizin/kimlik sağlayıcı dışsaldır; sistem kimliği doğrulamaz, doğrulanmış kimliği tüketir ve kendi yetki modelini uygular |
| **Sır yönetimi** | Bağlantı sırları dışsal bir sır yöneticisinde tutulur; sistem yalnız **referans** saklar, sır değerini saklamaz |
| **Bildirim taşıyıcıları** | E-posta, mesajlaşma, biletleme gibi kanallar dışsaldır; sistem olayı üretir ve teslimatı izler |

### 2.3 Temel varlık kavramları

| Kavram | Tanım |
|---|---|
| **Veri kaynağı** | Bağlantı politikasıyla yönetilen, salt okunur erişilen bir sistem |
| **Dataset** | Kaynak içinde ölçüm yapılabilen mantıksal veri kümesi |
| **Alan (field)** | Dataset içindeki kolon; sınıflandırma ve hassasiyet taşır |
| **Profil** | Bir dataset'in belirli bir andaki istatistiksel karakterizasyonu |
| **Kalite kuralı** | Bir kalite boyutunda ölçülebilir bir beklentinin tanımı |
| **Kural sürümü** | Kuralın değişmez, onaylanabilir ve çalıştırılabilir bir hâli |
| **Çalıştırma** | Bir veya çok kural sürümünün belirli bir kapsamda yürütülmesi |
| **Sonuç** | Çalıştırmanın ürettiği sayaçlar, ölçüm yeterliliği ve kanıt |
| **Skor** | Sonuçlardan türetilen, açıklanabilir ve yeniden üretilebilir kalite ölçüsü |
| **Sorun (issue)** | Sahiplenilip çözülmesi gereken, izlenen bir kalite veya teknik bozulma |
| **İstisna** | Bilinen bir bozulmanın süreli ve gerekçeli olarak kabul edilmesi |
| **Veri sözleşmesi** | Üretici ile tüketici arasındaki, ölçülebilir kalite taahhüdü |
| **Politika** | Sistemin davranışını belirleyen, sürümlenmiş ve onaylanmış kural kümesi |

### 2.4 Modelin kurucu ilkeleri

| İlke | Sonucu |
|---|---|
| **Teknik hata ≠ kalite ihlali** | Bağlantı/timeout hataları sıfır kalite skoru üretmez; ayrı yaşam döngüsüne girer |
| **Ölçüm yeterliliği skordan önce gelir** | Yetersiz kapsamla ölçülen veri için skor iddia edilmez, `NOT_QUALIFIED` üretilir |
| **Fail-closed** | Politika, yetki veya kanıt yoksa sistem hüküm üretmez; varsayılan izin vermez |
| **Değişmez kanıt** | Kural sürümü, sonuç, skor ve audit kaydı üretildikten sonra değiştirilmez |
| **Veri minimizasyonu** | Kanıt ve bildirimler ihlali göstermeye yetecek en az veriyi taşır |
| **Görev ayrılığı** | Üretime etki eden değişiklikler talep eden ve onaylayan farklı aktörler ister |
| **Yeniden üretilebilirlik** | Her skor ve sonuç, sürüm referanslarıyla yeniden hesaplanabilir |
| **Açıklanabilirlik** | Her skor, katkı bileşenlerine kadar geriye izlenebilir |

---

## 3. L1 domain haritası

| Kod | Domain | Sorumluluk |
|---|---|---|
| **D01** | Yönetişim, Organizasyon ve Politika | Organizasyon yapısı, iş/veri domainleri, sahiplik, iş sözlüğü, sistem politikaları ve konfigürasyon |
| **D02** | Kimlik, Rol ve Erişim Yönetimi | Kullanıcı, servis hesabı, rol, izin, kapsam ve oturum yönetimi |
| **D03** | Veri Kaynağı ve Bağlantı Yönetimi | Kaynak onboarding, sır referansı, bağlantı politikası, yaşam döngüsü |
| **D04** | Metadata, Katalog ve Varlık Yönetimi | Metadata keşfi, katalog, dataset/alan yönetimi, sınıflandırma, şema değişimi |
| **D05** | Profilleme ve Veri Karakterizasyonu | Profil çalıştırma, metrik üretimi, baseline, drift tespiti |
| **D06** | Kalite Kural Yönetimi | Kalite boyutları, şablon kütüphanesi, kural yaşam döngüsü, sürümleme, test, onay |
| **D07** | Yürütme, Zamanlama ve İş Kuyruğu | Çalıştırma orkestrasyonu, zamanlama, kalıcı kuyruk, worker, retry, iptal, dead-letter |
| **D08** | Ölçüm, Sonuç ve Skorlama | Sonuç ve kanıt, ölçüm yeterliliği, skor hesaplama, kritiklik ve risk |
| **D09** | Sorun, İstisna ve Remediation | Sorun yaşam döngüsü, SLA ve eskalasyon, istisna/override, teşhis, öneri, düzeltme |
| **D10** | Lineage, Etki ve Veri Sözleşmesi | Soy ağacı, etki analizi, veri sözleşmesi yaşam döngüsü, kalite borcu |
| **D11** | Analitik, Dashboard ve Raporlama | Rol bazlı görünümler, trend ve karşılaştırma, rapor üretimi ve güvenli dağıtım |
| **D12** | Bildirim ve Dış Entegrasyon | Bildirim olayları, kanal yönetimi, teslimat izleme, dış sistem entegrasyonu |
| **D13** | Audit, Kanıt ve Saklama | Audit izi, outbox, dışa aktarım, saklama politikası, yasal muhafaza, imha |
| **D14** | Operasyon ve Platform Sağlığı | Sistem sağlığı, kuyruk operasyonu, kapasite, olay yönetimi, bakım |
| **D15** | Test Verisi ve Ground Truth | Sentetik veri üretimi, bilinen doğruluk kümesi, kontrol doğrulama |

### 3.1 Domainler arası bağımlılık

```
D01 Yönetişim ─────┬──────────────────────────────────────────────┐
                   │                                              │
D02 Kimlik ────────┼──► (tüm domainlere yetki sağlar)             │
                   │                                              ▼
                   ▼                                        D13 Audit
D03 Kaynak ──► D04 Katalog ──► D05 Profil ──┐                   ▲
                   │                         │                   │
                   └────────► D06 Kural ─────┤                   │
                                             ▼                   │
                                    D07 Yürütme ──► D08 Skorlama │
                                             │           │       │
                                             ▼           ▼       │
                                       D14 Operasyon  D09 Sorun ─┤
                                                         │       │
                              D10 Lineage/Sözleşme ◄─────┤       │
                                                         ▼       │
                                              D11 Analitik/Rapor─┤
                                                         │       │
                                              D12 Bildirim ──────┘

D15 Test Verisi ──► (D05, D06, D08 doğrulamasını besler)
```

**Okunuşu:** D01 ve D02 tüm domainlerin ön koşuludur. Veri akışı
kaynak → katalog → profil/kural → yürütme → skor → sorun yönünde ilerler.
D13 her domainden olay alır. D15 ölçüm doğruluğunu bağımsız olarak sınar.

---

## 4. L1 → L2 → L3 tam ağaç

### D01 — Yönetişim, Organizasyon ve Politika
- **D01.C01** Organizasyon ve domain yapısı
  - `W01` Organizasyon birimi yönetimi · `W02` İş domaini yönetimi · `W03` Veri domaini yönetimi
- **D01.C02** Sahiplik ve yönetişim atamaları
  - `W01` Varlık sahipliği atama · `W02` Yönetişim rolü devri · `W03` Sahipsiz varlık takibi
- **D01.C03** İş sözlüğü ve terim yönetimi
  - `W01` Terim yaşam döngüsü · `W02` Terim–varlık eşlemesi
- **D01.C04** Politika yönetimi
  - `W01` Politika yaşam döngüsü · `W02` Politika sürümleme ve yürürlük
- **D01.C05** Sistem konfigürasyonu
  - `W01` Konfigürasyon yönetimi · `W02` Özellik anahtarı yönetimi

### D02 — Kimlik, Rol ve Erişim Yönetimi
- **D02.C01** Kimlik ve hesap yönetimi
  - `W01` Kullanıcı hesabı yaşam döngüsü · `W02` Servis hesabı yaşam döngüsü
- **D02.C02** Rol ve izin yönetimi
  - `W01` Rol tanımı yönetimi · `W02` İzin kataloğu yönetimi · `W03` Rol atama
- **D02.C03** Kapsam (scope) yönetimi
  - `W01` Kapsam ataması · `W02` Kapsam çözümleme
- **D02.C04** Oturum ve erişim denetimi
  - `W01` Oturum yaşam döngüsü · `W02` Yetki kararı ve reddi
- **D02.C05** Erişim gözden geçirme
  - `W01` Periyodik erişim sertifikasyonu

### D03 — Veri Kaynağı ve Bağlantı Yönetimi
- **D03.C01** Kaynak onboarding
  - `W01` Kaynak kaydı oluşturma · `W02` Bağlantı sırrı referansı bağlama · `W03` Bağlantı testi
- **D03.C02** Kaynak onayı ve aktivasyonu
  - `W01` Aktivasyon onay akışı · `W02` Pasifleştirme ve arşivleme
- **D03.C03** Bağlantı politikası ve kota
  - `W01` Kullanım politikası yönetimi · `W02` Erişim penceresi yönetimi
- **D03.C04** Bağlantı revizyon yönetimi
  - `W01` Bağlantı değişikliği ve geri alma
- **D03.C05** Kaynak sağlık izleme
  - `W01` Periyodik erişilebilirlik kontrolü

### D04 — Metadata, Katalog ve Varlık Yönetimi
- **D04.C01** Metadata keşfi
  - `W01` Keşif çalıştırma · `W02` Keşif sonucu uzlaştırma
- **D04.C02** Dataset yönetimi
  - `W01` Dataset yaşam döngüsü · `W02` Dataset kritikliği ve sahipliği
- **D04.C03** Alan (field) yönetimi
  - `W01` Alan yaşam döngüsü · `W02` Alan sınıflandırması ve hassasiyet
- **D04.C04** Şema değişimi yönetimi
  - `W01` Şema farkı tespiti · `W02` Şema değişikliği kararı
- **D04.C05** Katalog arama ve gezinme
  - `W01` Katalog arama · `W02` Varlık detay görünümü

### D05 — Profilleme ve Veri Karakterizasyonu
- **D05.C01** Profil çalıştırma
  - `W01` Profil talebi · `W02` Profil yöntemi ve örnekleme
- **D05.C02** Profil metrikleri
  - `W01` Temel metrik üretimi · `W02` Dağılım ve aykırı değer analizi
- **D05.C03** Baseline yönetimi
  - `W01` Baseline belirleme ve onaylama
- **D05.C04** Drift tespiti
  - `W01` Profil karşılaştırma · `W02` Drift hükmü ve sınıflandırma

### D06 — Kalite Kural Yönetimi
- **D06.C01** Kalite boyutu ve şablon kütüphanesi
  - `W01` Kalite boyutu yönetimi · `W02` Kural şablonu yaşam döngüsü
- **D06.C02** Kural yaşam döngüsü ve onayı
  - `W01` Kural oluşturma · `W02` Kural sürümü oluşturma · `W03` Kural testi
  - `W04` Onay akışı · `W05` Aktivasyon ve pasifleştirme · `W06` Arşivleme
- **D06.C03** Kural kapsamı ve parametreleri
  - `W01` Kapsam tanımlama · `W02` Eşik ve ağırlık yönetimi
- **D06.C04** Kural bağımlılıkları ve çakışma
  - `W01` Bağımlılık çözümleme · `W02` Çakışma ve mükerrerlik tespiti
- **D06.C05** Gölge (shadow) yürütme
  - `W01` Gölge mod yaşam döngüsü

### D07 — Yürütme, Zamanlama ve İş Kuyruğu
- **D07.C01** Çalıştırma orkestrasyonu
  - `W01` Manuel çalıştırma · `W02` Çalıştırma planı üretimi · `W03` Çalıştırma iptali
- **D07.C02** Zamanlama
  - `W01` Zamanlama tanımı yaşam döngüsü · `W02` Vadesi gelen zamanlamanın tetiklenmesi
- **D07.C03** Kalıcı iş kuyruğu
  - `W01` İş kuyruğa alma · `W02` İş sahiplenme (lease) · `W03` Heartbeat ve lease yenileme
- **D07.C04** Hata toleransı ve kurtarma
  - `W01` Yeniden deneme · `W02` Zaman aşımı yönetimi · `W03` Worker kurtarma
  - `W04` Dead-letter yönetimi
- **D07.C05** Bölümlü ve artımlı yürütme
  - `W01` Bölüm (partition) planlama · `W02` Checkpoint ve devam

### D08 — Ölçüm, Sonuç ve Skorlama
- **D08.C01** Sonuç ve kanıt
  - `W01` Sonuç kaydı · `W02` Başarısız kayıt örneği üretimi
- **D08.C02** Ölçüm yeterliliği
  - `W01` Kapsam ve teknik sağlık değerlendirmesi · `W02` Yeterlilik hükmü
- **D08.C03** Skor hesaplama
  - `W01` Kural düzeyi skor · `W02` Toplulaştırma · `W03` Skor yayımlama
- **D08.C04** Skor açıklanabilirliği
  - `W01` Katkı grafiği üretimi · `W02` Dönem karşılaştırması
- **D08.C05** Kritiklik ve risk
  - `W01` Kritiklik modeli yönetimi · `W02` Risk derecelendirme

### D09 — Sorun, İstisna ve Remediation
- **D09.C01** Sorun oluşumu ve tekilleştirme
  - `W01` Otomatik sorun üretimi · `W02` Tekilleştirme ve yinelenme · `W03` Manuel sorun açma
- **D09.C02** Sorun yaşam döngüsü
  - `W01` Atama · `W02` İnceleme · `W03` Çözüm · `W04` Doğrulama · `W05` Kapatma ve yeniden açma
- **D09.C03** SLA ve eskalasyon
  - `W01` SLA hesaplama · `W02` Eskalasyon tetikleme
- **D09.C04** İstisna ve override
  - `W01` İstisna talebi · `W02` İstisna onayı · `W03` İstisna sona ermesi
- **D09.C05** Teşhis ve öneri
  - `W01` Kök neden hipotezi üretimi · `W02` Kanıtlı öneri üretimi
- **D09.C06** Remediation
  - `W01` Düzeltme aksiyonu yaşam döngüsü · `W02` Düzeltme etkisinin doğrulanması

### D10 — Lineage, Etki ve Veri Sözleşmesi
- **D10.C01** Soy ağacı (lineage)
  - `W01` Lineage olayı alımı · `W02` Lineage grafı sorgulama
- **D10.C02** Etki analizi
  - `W01` Aşağı akış etki hesaplama · `W02` Değişiklik etki simülasyonu
- **D10.C03** Veri sözleşmesi
  - `W01` Sözleşme yaşam döngüsü · `W02` Sözleşme uyum ölçümü · `W03` Sözleşme ihlali
- **D10.C04** Kalite borcu
  - `W01` Kalite borcu kaydı ve takibi

### D11 — Analitik, Dashboard ve Raporlama
- **D11.C01** Rol bazlı dashboard
  - `W01` Yönetici görünümü · `W02` Sahip/steward görünümü · `W03` Mühendis görünümü
- **D11.C02** Analitik sorgulama
  - `W01` Trend analizi · `W02` Dönem ve kapsam karşılaştırması · `W03` Sıralama ve kırılım
- **D11.C03** Rapor üretimi
  - `W01` Rapor talebi · `W02` Asenkron rapor üretimi · `W03` Rapor zamanlaması
- **D11.C04** Güvenli dağıtım
  - `W01` Maskeleme ve hassasiyet kontrolü · `W02` İndirme ve erişim kaydı · `W03` Dosya yaşam sonu

### D12 — Bildirim ve Dış Entegrasyon
- **D12.C01** Bildirim olayı üretimi
  - `W01` Olay yayımlama · `W02` Abonelik ve tercih yönetimi
- **D12.C02** Kanal ve teslimat
  - `W01` Kanal yapılandırması · `W02` Teslimat ve yeniden deneme · `W03` Teslimat izleme
- **D12.C03** Dış sistem entegrasyonu
  - `W01` Giden entegrasyon (bilet/olay) · `W02` Gelen geri bildirim uzlaştırma
- **D12.C04** Programatik erişim
  - `W01` API anahtarı/servis hesabı erişimi · `W02` Kota ve hız sınırı

### D13 — Audit, Kanıt ve Saklama
- **D13.C01** Audit izi
  - `W01` Audit olayı kaydı · `W02` Audit sorgulama · `W03` Bütünlük doğrulama
- **D13.C02** Olay dışa aktarımı
  - `W01` Outbox yayımlama · `W02` Dış toplayıcıya aktarım
- **D13.C03** Saklama ve imha
  - `W01` Saklama politikası yönetimi · `W02` İmha işi yürütme
- **D13.C04** Yasal muhafaza ve geri çağırma
  - `W01` Muhafaza uygulama ve kaldırma · `W02` Arşivden geri çağırma

### D14 — Operasyon ve Platform Sağlığı
- **D14.C01** Sistem sağlığı
  - `W01` Bileşen sağlık görünümü · `W02` Kapasite ve yük görünümü
- **D14.C02** Kuyruk ve worker operasyonu
  - `W01` Kuyruk görünümü ve müdahale · `W02` Worker yönetimi
- **D14.C03** Olay (incident) yönetimi
  - `W01` Operasyonel olay yaşam döngüsü
- **D14.C04** Bakım ve değişiklik
  - `W01` Bakım penceresi yönetimi · `W02` Toplu yeniden işleme

### D15 — Test Verisi ve Ground Truth
- **D15.C01** Sentetik veri üretimi
  - `W01` Üretim çalıştırması · `W02` Üretim profili yönetimi
- **D15.C02** Bilinen doğruluk kümesi
  - `W01` Ground truth tanımlama · `W02` Beklenen sonuç kaydı
- **D15.C03** Kontrol doğrulama
  - `W01` Tespit doğruluğu ölçümü · `W02` Kontrol yeterliliği deneyi

---

## 5. Domain gövdesi

### D01 — Yönetişim, Organizasyon ve Politika

Sistemin üzerine oturduğu yönetişim iskeleti: kim hangi veriden sorumlu, hangi
terim ne anlama geliyor, sistem hangi politikalarla davranıyor. Diğer tüm
domainler sahiplik, kapsam ve politika çözümlemesi için buraya bağlanır.

#### D01.C01 — Organizasyon ve domain yapısı

Kalite sorumluluğunun dağıtılabilmesi için kurumsal yapının ve veri domainlerinin
sistemde temsil edilmesi.

##### D01.C01.W01 — Organizasyon birimi yönetimi

###### D01.C01.W01.A01 — Organizasyon birimi oluştur

| Alan | Değer |
|---|---|
| Amaç | Kalite sorumluluğunun ve raporlama kırılımının bağlanacağı kurumsal birimi tanımlamak |
| Aktör | Platform Admin |
| Tetikleyici | Yönetim ekranından birim oluşturma |
| Ön koşul | Üst birim varsa `ACTIVE`; birim kodu kurum içinde benzersiz |
| Akış | **Temel:** kod/ad/üst birim gir → benzersizlik ve döngü kontrolü → kaydet → audit. **Alternatif:** kök birim üst birimsiz oluşturulur. **Hata:** mükerrer kod → reddet; kendini üst gösterme → reddet |
| Durum geçişi | `—` → `ACTIVE` |
| Yetki | `org.unit.manage` + kurum geneli scope |
| Audit | `ORG_UNIT_CREATED` (birim kodu, üst birim, aktör) |
| API | `POST /org-units` — idempotency anahtarı destekler |
| Ekran | Yönetim > Organizasyon |
| Tablo | `org_units`(org_unit_id, code, name, parent_org_unit_id, status, version) |
| Test | benzersizlik; hiyerarşi döngüsü; yetki; audit |

###### D01.C01.W01.A02 — Organizasyon birimi güncelle

| Alan | Değer |
|---|---|
| Amaç | Yeniden yapılanmada birim adı ve hiyerarşi konumunu güncel tutmak |
| Aktör | Platform Admin |
| Tetikleyici | Yönetim ekranından düzenleme |
| Ön koşul | Birim `ACTIVE`; iyimser kilit sürümü eşleşmeli |
| Akış | **Temel:** alan değiştir → hiyerarşi doğrula → sürüm artır → audit. **Alternatif:** üst birim değişimi alt ağacı taşır. **Hata:** eşzamanlı değişiklik → sürüm çakışması; döngü → reddet |
| Durum geçişi | `—` |
| Yetki | `org.unit.manage` + kurum geneli scope |
| Audit | `ORG_UNIT_UPDATED` (değişen alanlar, eski/yeni özet) |
| API | `PATCH /org-units/{id}` — `If-Match` zorunlu |
| Ekran | Yönetim > Organizasyon |
| Tablo | `org_units`(name, parent_org_unit_id, version, updated_at) |
| Test | eşzamanlılık; hiyerarşi döngüsü; yetki; audit |

###### D01.C01.W01.A03 — Organizasyon birimini pasifleştir

| Alan | Değer |
|---|---|
| Amaç | Kullanımdan kalkan birimi, geçmiş kayıtları bozmadan devre dışı bırakmak |
| Aktör | Platform Admin |
| Tetikleyici | Yönetim ekranından pasifleştirme |
| Ön koşul | Birime bağlı `ACTIVE` alt birim ve açık sahiplik ataması bulunmamalı |
| Akış | **Temel:** bağımlılık kontrolü → `INACTIVE` → audit. **Alternatif:** bağımlılık varsa devir hedefi istenir. **Hata:** açık sahiplik varsa → reddet, bağımlılık listesi döndür |
| Durum geçişi | `ACTIVE` → `INACTIVE` |
| Yetki | `org.unit.manage` + kurum geneli scope |
| Audit | `ORG_UNIT_DEACTIVATED` (bağımlılık özeti, gerekçe kodu) |
| API | `POST /org-units/{id}/deactivation` |
| Ekran | Yönetim > Organizasyon |
| Tablo | `org_units`(status, version); `asset_ownerships`(okuma) |
| Test | bağımlılık reddi; durum-makinesi; yetki; audit |

##### D01.C01.W02 — İş domaini yönetimi

###### D01.C01.W02.A01 — İş domaini tanımla

| Alan | Değer |
|---|---|
| Amaç | Kalite skorunun ve raporlamanın iş anlamıyla kırılabilmesi için iş domaini tanımlamak |
| Aktör | Data Governance Admin |
| Tetikleyici | Yönetişim ekranından domain oluşturma |
| Ön koşul | Sahip organizasyon birimi `ACTIVE` |
| Akış | **Temel:** kod/ad/sahip birim/kritiklik gir → doğrula → kaydet → audit. **Alternatif:** üst domain altında alt domain oluşturulur. **Hata:** mükerrer kod → reddet |
| Durum geçişi | `—` → `ACTIVE` |
| Yetki | `governance.domain.manage` + kurum geneli scope |
| Audit | `BUSINESS_DOMAIN_CREATED` (domain kodu, sahip birim, kritiklik) |
| API | `POST /business-domains` |
| Ekran | Yönetişim > İş Domainleri |
| Tablo | `business_domains`(business_domain_id, code, name, org_unit_id, criticality, status) |
| Test | benzersizlik; hiyerarşi; yetki; audit |

###### D01.C01.W02.A02 — İş domainine varlık ata

| Alan | Değer |
|---|---|
| Amaç | Dataset ve kaynakları iş anlamına bağlayarak domain bazlı skor üretilebilir kılmak |
| Aktör | Data Governance Admin; Data Owner |
| Tetikleyici | Katalog veya yönetişim ekranından atama |
| Ön koşul | Varlık `ACTIVE`; domain `ACTIVE`; aktörün varlık üzerinde kapsamı var |
| Akış | **Temel:** varlık seç → domain seç → çakışma kontrolü → kaydet → audit. **Alternatif:** toplu atama listeyle yapılır. **Hata:** varlık başka domaine bağlıysa devir onayı istenir |
| Durum geçişi | `—` |
| Yetki | `governance.domain.assign` + varlık kapsamı |
| Audit | `DOMAIN_ASSET_ASSIGNED` (varlık referansı, eski domain, yeni domain) |
| API | `POST /business-domains/{id}/assets` — toplu gövde destekler |
| Ekran | Yönetişim > İş Domainleri; Katalog > Varlık Detayı |
| Tablo | `domain_asset_assignments`(business_domain_id, asset_type, asset_id, assigned_at) |
| Test | çakışan atama; toplu işlem; kapsam yetkisi; audit |

##### D01.C01.W03 — Veri domaini yönetimi

###### D01.C01.W03.A01 — Veri domaini tanımla

| Alan | Değer |
|---|---|
| Amaç | Teknik veri gruplarını (müşteri, ürün, işlem gibi) tutarlı kural ve politika uygulanabilir kümelerde toplamak |
| Aktör | Data Governance Admin |
| Tetikleyici | Yönetişim ekranından tanımlama |
| Ön koşul | Bağlı iş domaini `ACTIVE` |
| Akış | **Temel:** kod/ad/iş domaini/varsayılan politika gir → doğrula → kaydet → audit. **Hata:** mükerrer kod → reddet; iş domaini pasif → reddet |
| Durum geçişi | `—` → `ACTIVE` |
| Yetki | `governance.domain.manage` + kurum geneli scope |
| Audit | `DATA_DOMAIN_CREATED` (domain kodu, iş domaini, varsayılan politika) |
| API | `POST /data-domains` |
| Ekran | Yönetişim > Veri Domainleri |
| Tablo | `data_domains`(data_domain_id, code, name, business_domain_id, default_policy_id, status) |
| Test | benzersizlik; politika referansı; yetki; audit |

#### D01.C02 — Sahiplik ve yönetişim atamaları

Her veri varlığının sorumlu bir sahibi ve teknik yöneticisi olmasını garanti eden
kabiliyet; sahipsiz varlık kalite yönetiminin en yaygın kör noktasıdır.

##### D01.C02.W01 — Varlık sahipliği atama

###### D01.C02.W01.A01 — Veri sahibi ata

| Alan | Değer |
|---|---|
| Amaç | Bir veri varlığının kalite hesabını verecek iş sorumlusunu belirlemek |
| Aktör | Data Governance Admin |
| Tetikleyici | Katalog ekranından atama; veya sahipsiz varlık uyarısından |
| Ön koşul | Aday kullanıcı `ACTIVE` ve `Data Owner` rolüne sahip; varlık `ACTIVE` |
| Akış | **Temel:** varlık + aday seç → rol ve kapsam doğrula → önceki sahibi sonlandır → kaydet → bildir → audit. **Alternatif:** vekil sahip süreli atanır. **Hata:** aday rolü yoksa → reddet; pasif kullanıcı → reddet |
| Durum geçişi | Önceki atama `ACTIVE` → `SUPERSEDED`; yeni atama `—` → `ACTIVE` |
| Yetki | `governance.ownership.assign` + varlık kapsamı |
| Audit | `ASSET_OWNER_ASSIGNED` (varlık, eski sahip, yeni sahip, geçerlilik) |
| API | `POST /assets/{type}/{id}/ownership` |
| Ekran | Katalog > Varlık Detayı; Yönetişim > Sahiplik |
| Tablo | `asset_ownerships`(asset_type, asset_id, owner_user_id, ownership_kind, valid_from, valid_to, status) |
| Test | rol ön koşulu; süreli atama; devir zinciri; yetki; audit |

###### D01.C02.W01.A02 — Teknik yönetici (steward) ata

| Alan | Değer |
|---|---|
| Amaç | Varlığın teknik kalite işlerini yürütecek sorumluyu belirlemek |
| Aktör | Data Owner; Data Governance Admin |
| Tetikleyici | Katalog ekranından atama |
| Ön koşul | Aday `Technical Data Steward` rolüne sahip; varlığın sahibi tanımlı |
| Akış | **Temel:** aday seç → rol doğrula → kaydet → bildir → audit. **Alternatif:** birden çok steward atanabilir. **Hata:** sahip tanımsızsa → önce sahip atanması istenir |
| Durum geçişi | `—` → `ACTIVE` |
| Yetki | `governance.ownership.assign` + varlık kapsamı |
| Audit | `ASSET_STEWARD_ASSIGNED` (varlık, steward, atayan) |
| API | `POST /assets/{type}/{id}/stewards` |
| Ekran | Katalog > Varlık Detayı |
| Tablo | `asset_ownerships`(ownership_kind='STEWARD', owner_user_id, status) |
| Test | rol ön koşulu; çoklu atama; sıralı ön koşul; yetki; audit |

##### D01.C02.W02 — Yönetişim rolü devri

###### D01.C02.W02.A01 — Sahipliği devret

| Alan | Değer |
|---|---|
| Amaç | Sorumlu kişi değiştiğinde açık işlerin sahipsiz kalmamasını sağlamak |
| Aktör | Data Owner (mevcut); Data Governance Admin |
| Tetikleyici | Kullanıcı ayrılışı; organizasyon değişikliği; manuel devir |
| Ön koşul | Devralan `ACTIVE` ve uygun role sahip |
| Akış | **Temel:** devralan seç → açık sorun/onay listesi çıkar → devret → her kalemi yeniden ata → bildir → audit. **Alternatif:** yalnız sahiplik devri, açık işler ayrı bırakılır. **Hata:** devralan kapsamı yetersizse → kapsam genişletme talebi üretilir |
| Durum geçişi | Eski atama `ACTIVE` → `TRANSFERRED`; yeni atama `ACTIVE` |
| Yetki | `governance.ownership.transfer` + varlık kapsamı |
| Audit | `OWNERSHIP_TRANSFERRED` (varlık, devreden, devralan, taşınan kalem sayısı) |
| API | `POST /assets/{type}/{id}/ownership/transfer` |
| Ekran | Yönetişim > Sahiplik > Devir |
| Tablo | `asset_ownerships`(status); `issues`(assignee_user_id); `approval_requests`(checker_actor_id) |
| Test | toplu yeniden atama; kapsam yetersizliği; işlem atomikliği; audit |

##### D01.C02.W03 — Sahipsiz varlık takibi

###### D01.C02.W03.A01 — Sahipsiz varlıkları listele

| Alan | Değer |
|---|---|
| Amaç | Yönetişim boşluğunu görünür kılmak ve kapatılmasını takip etmek |
| Aktör | Data Governance Admin; Auditor |
| Tetikleyici | Yönetişim ekranı açılışı; periyodik yönetişim taraması |
| Ön koşul | Katalogda `ACTIVE` varlık bulunması |
| Akış | **Temel:** aktif varlıklar × sahiplik atamaları farkını hesapla → kritikliğe göre sırala → döndür. **Alternatif:** yalnız kritik varlıklar filtrelenir. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `governance.ownership.read` + kapsam |
| Audit | Erişim kaydı: `GOVERNANCE_GAP_VIEWED` (filtre, sonuç sayısı) |
| API | `GET /governance/ownership-gaps` — sayfalama ve filtre |
| Ekran | Yönetişim > Sahiplik Boşlukları |
| Tablo | `datasets`, `data_sources`, `asset_ownerships`(okuma) |
| Test | fark hesabı doğruluğu; kapsam filtresi; sayfalama; erişim kaydı |

###### D01.C02.W03.A02 — Sahipsiz varlık uyarısı üret

| Alan | Değer |
|---|---|
| Amaç | Yönetişim boşluğunun fark edilmeden sürmesini engellemek |
| Aktör | Sistem |
| Tetikleyici | Periyodik yönetişim taraması zamanlayıcısı |
| Ön koşul | Yönetişim politikası tanımlı ve tolerans süresi aşılmış |
| Akış | **Temel:** boşlukları tespit et → tolerans süresini aşanları seç → bildirim olayı üret → audit. **Alternatif:** kritik varlıkta eskalasyon seviyesi yükseltilir. **Hata:** politika yoksa → hüküm üretilmez, çalışma `NOT_QUALIFIED` sonlanır |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü; `governance.scan.execute` |
| Audit | `GOVERNANCE_GAP_DETECTED` (varlık sayısı, kritik sayısı, politika sürümü) |
| API | `—` (zamanlanmış iş) |
| Ekran | Yönetişim > Sahiplik Boşlukları (sonuç görünümü) |
| Tablo | `governance_scan_runs`(run_id, policy_version, gap_count, executed_at) |
| Test | politika yokluğunda fail-closed; tolerans hesabı; bildirim üretimi; audit |

#### D01.C03 — İş sözlüğü ve terim yönetimi

Kalite kurallarının ve raporların aynı kavramı aynı biçimde adlandırmasını
sağlayan ortak dil katmanı.

##### D01.C03.W01 — Terim yaşam döngüsü

###### D01.C03.W01.A01 — İş terimi öner

| Alan | Değer |
|---|---|
| Amaç | Kurum genelinde tutarlı bir kavram tanımını sözlüğe kazandırmak |
| Aktör | Data Steward; Data Owner |
| Tetikleyici | Sözlük ekranından öneri |
| Ön koşul | Aynı ada sahip `APPROVED` terim bulunmamalı |
| Akış | **Temel:** ad/tanım/eş anlamlı/domain gir → benzerlik kontrolü → `DRAFT` kaydet → audit. **Alternatif:** benzer terim bulunursa birleştirme önerilir. **Hata:** boş tanım → reddet |
| Durum geçişi | `—` → `DRAFT` |
| Yetki | `glossary.term.propose` + domain kapsamı |
| Audit | `GLOSSARY_TERM_PROPOSED` (terim, domain, öneren) |
| API | `POST /glossary/terms` |
| Ekran | İş Sözlüğü > Yeni Terim |
| Tablo | `glossary_terms`(term_id, name, definition, data_domain_id, status, version) |
| Test | benzerlik tespiti; benzersizlik; yetki; audit |

###### D01.C03.W01.A02 — İş terimini onayla

| Alan | Değer |
|---|---|
| Amaç | Sözlüğe giren tanımın yetkili bir onaydan geçmesini sağlamak |
| Aktör | Data Governance Admin (öneren kişiden farklı) |
| Tetikleyici | Sözlük onay kuyruğundan karar |
| Ön koşul | Terim `DRAFT` veya `IN_REVIEW`; onaylayan ≠ öneren |
| Akış | **Temel:** incele → onayla → `APPROVED` → yayımla → audit. **Alternatif:** düzeltme talebiyle `DRAFT`a döndürülür. **Hata:** öneren=onaylayan → reddet |
| Durum geçişi | `DRAFT`\|`IN_REVIEW` → `APPROVED` \| `DRAFT` |
| Yetki | `glossary.term.approve` + domain kapsamı; görev ayrılığı zorunlu |
| Audit | `GLOSSARY_TERM_APPROVED` (terim, öneren, onaylayan, sürüm) |
| API | `POST /glossary/terms/{id}/approval` — `If-Match` |
| Ekran | İş Sözlüğü > Onay Kuyruğu |
| Tablo | `glossary_terms`(status, approved_by, approved_at, version) |
| Test | görev ayrılığı; durum-makinesi; eşzamanlılık; audit |

###### D01.C03.W01.A03 — İş terimini kullanımdan kaldır

| Alan | Değer |
|---|---|
| Amaç | Geçerliliğini yitiren tanımın yeni kullanıma girmesini engellemek, geçmişi korumak |
| Aktör | Data Governance Admin |
| Tetikleyici | Sözlük ekranından kullanımdan kaldırma |
| Ön koşul | Terim `APPROVED`; halef terim belirtilmişse `APPROVED` |
| Akış | **Temel:** halef terim seç → bağlı varlık sayısını göster → `DEPRECATED` → bildir → audit. **Alternatif:** halefsiz kaldırma gerekçe ister. **Hata:** aktif veri sözleşmesi referansı varsa → uyar ve onay iste |
| Durum geçişi | `APPROVED` → `DEPRECATED` |
| Yetki | `glossary.term.manage` + domain kapsamı |
| Audit | `GLOSSARY_TERM_DEPRECATED` (terim, halef, bağlı varlık sayısı) |
| API | `POST /glossary/terms/{id}/deprecation` |
| Ekran | İş Sözlüğü > Terim Detayı |
| Tablo | `glossary_terms`(status, superseded_by_term_id) |
| Test | bağımlılık uyarısı; halef zinciri; durum-makinesi; audit |

##### D01.C03.W02 — Terim–varlık eşlemesi

###### D01.C03.W02.A01 — Terimi veri alanına bağla

| Alan | Değer |
|---|---|
| Amaç | Teknik kolonun hangi iş kavramını taşıdığını netleştirerek kural ve rapor yorumunu tekilleştirmek |
| Aktör | Data Steward; Technical Data Steward |
| Tetikleyici | Katalog alan detayından bağlama |
| Ön koşul | Terim `APPROVED`; alan `ACTIVE` |
| Akış | **Temel:** alan + terim seç → tip uyumluluğunu bilgilendir → kaydet → audit. **Alternatif:** bir alana birden çok terim bağlanabilir, biri birincil işaretlenir. **Hata:** `DEPRECATED` terim → reddet |
| Durum geçişi | `—` |
| Yetki | `glossary.mapping.manage` + dataset kapsamı |
| Audit | `GLOSSARY_TERM_MAPPED` (terim, alan referansı, birincil mi) |
| API | `POST /data-fields/{id}/glossary-terms` |
| Ekran | Katalog > Alan Detayı |
| Tablo | `glossary_term_mappings`(term_id, data_field_id, is_primary) |
| Test | deprecated terim reddi; çoklu eşleme; birincil tekilliği; audit |

#### D01.C04 — Politika yönetimi

Sistemin kararlarını (skorlama ağırlıkları, drift eşikleri, SLA süreleri,
maskeleme kuralları, saklama süreleri) veriye gömmek yerine sürümlenmiş
politikalarda toplayan kabiliyet. **Politika yoksa sistem hüküm üretmez.**

##### D01.C04.W01 — Politika yaşam döngüsü

###### D01.C04.W01.A01 — Politika taslağı oluştur

| Alan | Değer |
|---|---|
| Amaç | Sistem davranışını belirleyen parametre kümesini denetlenebilir bir nesne olarak tanımlamak |
| Aktör | Data Governance Admin; Platform Admin |
| Tetikleyici | Politika ekranından yeni taslak veya mevcut politikadan kopyalama |
| Ön koşul | Politika tipi kataloğunda tanımlı; aktörün tip üzerinde yetkisi var |
| Akış | **Temel:** tip seç → parametreleri gir → şema doğrula → `DRAFT` kaydet → audit. **Alternatif:** yürürlükteki sürümden kopyalanarak başlanır. **Hata:** şema dışı parametre → alan bazlı hata döndür |
| Durum geçişi | `—` → `DRAFT` |
| Yetki | `policy.draft.create` + politika tipi kapsamı |
| Audit | `POLICY_DRAFT_CREATED` (politika tipi, temel alınan sürüm) |
| API | `POST /policies` |
| Ekran | Yönetim > Politikalar > Yeni |
| Tablo | `policies`(policy_id, policy_type, parameters, status, version_no, based_on_version) |
| Test | şema doğrulama; kopyalama; yetki; audit |

###### D01.C04.W01.A02 — Politikayı onaya gönder

| Alan | Değer |
|---|---|
| Amaç | Politika değişikliğinin görev ayrılığı altında incelenmesini başlatmak |
| Aktör | Data Governance Admin (maker) |
| Tetikleyici | Politika detayından onaya gönderme |
| Ön koşul | Politika `DRAFT`; parametreler şemaya uygun; etki özeti hesaplanmış |
| Akış | **Temel:** etki özeti üret → onay talebi aç → `IN_REVIEW` → onaylayıcıya bildir → audit. **Alternatif:** yüksek etkili değişiklikte ikinci onaylayıcı istenir. **Hata:** aynı politika için açık talep varsa → reddet |
| Durum geçişi | `DRAFT` → `IN_REVIEW`; `ApprovalRequest` `—` → `PENDING` |
| Yetki | `policy.submit` + politika tipi kapsamı |
| Audit | `POLICY_SUBMITTED_FOR_APPROVAL` (politika, etki özeti, maker) |
| API | `POST /policies/{id}/submission` |
| Ekran | Yönetim > Politikalar > Detay |
| Tablo | `policies`(status); `approval_requests`(object_type='POLICY', maker_actor_id, status) |
| Test | mükerrer talep reddi; etki özeti üretimi; durum-makinesi; audit |

###### D01.C04.W01.A03 — Politika kararı ver

| Alan | Değer |
|---|---|
| Amaç | Politika değişikliğini yetkilendirmek veya gerekçeyle geri çevirmek |
| Aktör | Security Admin veya ikinci Data Governance Admin (maker'dan farklı) |
| Tetikleyici | Onay kuyruğundan karar |
| Ön koşul | Talep `PENDING`; checker ≠ maker; checker politika tipinde yetkili |
| Akış | **Temel:** etki özetini incele → karar + gerekçe → geçiş → audit → bildir. **Alternatif:** red gerekçe kodu zorunlu, politika `DRAFT`a döner. **Hata:** maker=checker → reddet; eşzamanlı karar → sürüm çakışması |
| Durum geçişi | `PENDING` → `APPROVED` \| `REJECTED`; politika `IN_REVIEW` → `APPROVED` \| `DRAFT` |
| Yetki | `policy.approve` + politika tipi kapsamı; görev ayrılığı zorunlu |
| Audit | `POLICY_APPROVAL_DECIDED` (karar, gerekçe kodu, maker, checker) |
| API | `POST /policy-approvals/{id}/decision` — `If-Match` |
| Ekran | Yönetim > Onay Kuyruğu |
| Tablo | `approval_requests`(status, checker_actor_id, decided_at, reason_code, version) |
| Test | görev ayrılığı; eşzamanlı karar; durum-makinesi; audit atomikliği |

##### D01.C04.W02 — Politika sürümleme ve yürürlük

###### D01.C04.W02.A01 — Politikayı yürürlüğe al

| Alan | Değer |
|---|---|
| Amaç | Onaylanmış politikanın belirli bir andan itibaren sistem kararlarını yönetmesini sağlamak |
| Aktör | Platform Admin; Data Governance Admin |
| Tetikleyici | Manuel yürürlüğe alma; veya planlanmış yürürlük zamanı |
| Ön koşul | Politika `APPROVED`; yürürlük zamanı geçmişte olmamalı |
| Akış | **Temel:** yürürlük zamanı belirle → önceki yürürlük sürümünü sonlandır → `EFFECTIVE` → ilgili rollere bildir → audit. **Alternatif:** ileri tarihli yürürlük zamanlanır. **Hata:** çakışan yürürlük aralığı → reddet |
| Durum geçişi | `APPROVED` → `EFFECTIVE`; önceki `EFFECTIVE` → `SUPERSEDED` |
| Yetki | `policy.activate` + politika tipi kapsamı |
| Audit | `POLICY_MADE_EFFECTIVE` (politika sürümü, yürürlük zamanı, önceki sürüm) |
| API | `POST /policies/{id}/effectiveness` |
| Ekran | Yönetim > Politikalar > Detay |
| Tablo | `policies`(status, effective_from, effective_to, version_no) |
| Test | aralık çakışması; ileri tarihli yürürlük; durum-makinesi; audit |

###### D01.C04.W02.A02 — Yürürlükteki politikayı çözümle

| Alan | Değer |
|---|---|
| Amaç | Bir karar anında hangi politika sürümünün geçerli olduğunu belirsizliğe yer bırakmadan saptamak |
| Aktör | Sistem |
| Tetikleyici | Skorlama, drift, SLA, maskeleme veya saklama kararı gerektiren her işlem |
| Ön koşul | Politika tipi ve kapsam belirtilmiş olmalı |
| Akış | **Temel:** tip + kapsam + zaman ile `EFFECTIVE` sürümü bul → sürüm etiketiyle döndür. **Alternatif:** kapsama özgü sürüm yoksa kurum varsayılanına düşülür. **Hata:** hiçbir yürürlük sürümü yoksa → çözümleme başarısız, çağıran işlem fail-closed sonlanır |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü; çağıran işlemin yetkisi devralınır |
| Audit | Çağıran işlemin audit kaydına `policy_version` alanı olarak gömülür |
| API | `—` (iç servis) |
| Ekran | `—` |
| Tablo | `policies`(policy_type, scope_type, scope_id, effective_from, effective_to)(okuma) |
| Test | zaman bazlı çözümleme; varsayılana düşme; politika yokluğunda fail-closed |

###### D01.C04.W02.A03 — Politikayı geri al

| Alan | Değer |
|---|---|
| Amaç | Hatalı politika değişikliğinin etkisini hızla sonlandırmak |
| Aktör | Platform Admin |
| Tetikleyici | Operasyonel olay; hatalı yürürlük tespiti |
| Ön koşul | Politika `EFFECTIVE`; geri dönülecek önceki sürüm `SUPERSEDED` |
| Akış | **Temel:** hedef sürüm seç → gerekçe gir → mevcut sürümü sonlandır → hedefi `EFFECTIVE` yap → bildir → audit. **Alternatif:** geri alma acil yolla tek onayla yapılır, sonradan gözden geçirilir. **Hata:** hedef sürüm yoksa → reddet |
| Durum geçişi | `EFFECTIVE` → `ROLLED_BACK`; hedef `SUPERSEDED` → `EFFECTIVE` |
| Yetki | `policy.rollback` + kurum geneli scope |
| Audit | `POLICY_ROLLED_BACK` (geri alınan sürüm, dönülen sürüm, gerekçe) |
| API | `POST /policies/{id}/rollback` |
| Ekran | Yönetim > Politikalar > Sürüm Geçmişi |
| Tablo | `policies`(status, effective_to); `policy_rollbacks`(rollback_id, from_version, to_version, reason_code) |
| Test | geri alma zinciri; acil yol yetkisi; durum-makinesi; audit |

#### D01.C05 — Sistem konfigürasyonu

Politikadan ayrı olarak, sistemin teknik davranışını belirleyen ayarların
denetlenebilir yönetimi.

##### D01.C05.W01 — Konfigürasyon yönetimi

###### D01.C05.W01.A01 — Konfigürasyon değeri değiştir

| Alan | Değer |
|---|---|
| Amaç | Sistemin teknik parametrelerini yeniden dağıtım gerektirmeden, izlenebilir biçimde ayarlamak |
| Aktör | Platform Admin |
| Tetikleyici | Yönetim ekranından değişiklik |
| Ön koşul | Anahtar konfigürasyon kataloğunda tanımlı; değer tip ve aralık şemasına uygun |
| Akış | **Temel:** anahtar seç → yeni değer gir → şema doğrula → uygula → audit. **Alternatif:** yeniden başlatma gerektiren anahtarlar işaretlenir ve uyarı verilir. **Hata:** aralık dışı değer → reddet; hassas anahtar → ek onay iste |
| Durum geçişi | `—` |
| Yetki | `system.config.manage` + kurum geneli scope |
| Audit | `SYSTEM_CONFIG_CHANGED` (anahtar, eski/yeni değer özeti — hassas değer maskeli) |
| API | `PUT /system-config/{key}` — `If-Match` |
| Ekran | Yönetim > Sistem Konfigürasyonu |
| Tablo | `system_config`(config_key, value, value_type, is_sensitive, version, updated_by) |
| Test | şema doğrulama; hassas değer maskeleme; eşzamanlılık; yetki; audit |

###### D01.C05.W01.A02 — Konfigürasyon geçmişini görüntüle

| Alan | Değer |
|---|---|
| Amaç | Bir davranış değişikliğinin hangi ayar değişikliğinden kaynaklandığını geriye izlemek |
| Aktör | Platform Admin; Auditor |
| Tetikleyici | Yönetim ekranından geçmiş görüntüleme |
| Ön koşul | Anahtar üzerinde okuma yetkisi |
| Akış | **Temel:** anahtar seç → zaman sıralı değişiklik listesi → hassas değerler maskeli döndür. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `system.config.read` + kurum geneli scope |
| Audit | Erişim kaydı: `SYSTEM_CONFIG_HISTORY_VIEWED` (anahtar) |
| API | `GET /system-config/{key}/history` — sayfalama |
| Ekran | Yönetim > Sistem Konfigürasyonu > Geçmiş |
| Tablo | `system_config_history`(config_key, old_value, new_value, changed_by, changed_at) |
| Test | maskeleme; sayfalama; yetki; erişim kaydı |

##### D01.C05.W02 — Özellik anahtarı yönetimi

###### D01.C05.W02.A01 — Özellik anahtarını değiştir

| Alan | Değer |
|---|---|
| Amaç | Yeni yeteneklerin kademeli açılmasını ve sorun hâlinde hızla kapatılmasını sağlamak |
| Aktör | Platform Admin |
| Tetikleyici | Yönetim ekranından açma/kapama; acil kapatma |
| Ön koşul | Anahtar kataloğunda tanımlı |
| Akış | **Temel:** anahtar seç → durum ve hedef kitle belirle → uygula → audit. **Alternatif:** yüzdesel veya rol bazlı kademeli açılış. **Hata:** bağımlı anahtar kapalıysa → uyar ve reddet |
| Durum geçişi | `DISABLED` ↔ `ENABLED` \| `PARTIAL` |
| Yetki | `system.feature.manage` + kurum geneli scope |
| Audit | `FEATURE_FLAG_CHANGED` (anahtar, eski/yeni durum, hedef kitle) |
| API | `PUT /feature-flags/{key}` |
| Ekran | Yönetim > Özellik Anahtarları |
| Tablo | `feature_flags`(flag_key, state, rollout_rule, version, updated_by) |
| Test | bağımlılık kontrolü; kademeli açılış; acil kapatma; audit |

##### L5 — D01 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D01-001` | Organizasyon ve domain hiyerarşilerinde döngü oluşturulamaz |
| `BR-D01-002` | Aktif alt birimi veya açık sahiplik ataması olan birim pasifleştirilemez |
| `BR-D01-003` | Bir varlığın aynı anda yalnız bir `ACTIVE` veri sahibi bulunur; steward birden çok olabilir |
| `BR-D01-004` | Sahiplik devrinde devralan, devredilen varlıkların kapsamını karşılamak zorundadır |
| `BR-D01-005` | `DEPRECATED` iş terimi yeni eşlemede kullanılamaz; mevcut eşlemeler korunur |
| `BR-D01-006` | Bir terimi öneren aktör, aynı terimi onaylayamaz |
| `BR-D01-007` | Politika değişikliğini talep eden aktör, aynı talebi onaylayamaz |
| `BR-D01-008` | Aynı politika tipi ve kapsamı için yürürlük aralıkları çakışamaz |
| `BR-D01-009` | Yürürlükte politika bulunmayan bir karar noktası hüküm üretmez; işlem fail-closed sonlanır |
| `BR-D01-010` | Her sistem kararı, dayandığı politika sürümünü audit kaydında taşır |
| `BR-D01-011` | Hassas işaretli konfigürasyon değerleri hiçbir okuma yüzeyinde açık gösterilmez |
| `BR-D01-012` | Politika ve konfigürasyon geçmişi değiştirilemez; yalnız yeni kayıt eklenir |

---

### D02 — Kimlik, Rol ve Erişim Yönetimi

Sistemin tüm yetki kararlarının dayandığı katman. Kimlik doğrulama dışsaldır;
bu domain doğrulanmış kimliği alır, sistem içi yetki ve kapsamını çözümler,
erişim kararlarını denetlenebilir kılar.

#### D02.C01 — Kimlik ve hesap yönetimi

##### D02.C01.W01 — Kullanıcı hesabı yaşam döngüsü

###### D02.C01.W01.A01 — Kullanıcı hesabı sağla (provision)

| Alan | Değer |
|---|---|
| Amaç | Dışsal dizinde doğrulanmış bir kimliğe sistem içi yetki taşıyıcısı bir hesap karşılığı vermek |
| Aktör | Security Admin; veya dizin senkronizasyonu ile `Sistem` |
| Tetikleyici | Manuel oluşturma; ilk başarılı oturum açma; dizin senkronizasyon işi |
| Ön koşul | Dışsal kimlik referansı benzersiz; kimlik doğrulanmış |
| Akış | **Temel:** dış kimlik referansı + görünen ad al → yerel hesap oluştur → varsayılan rolsüz `ACTIVE` → audit. **Alternatif:** dizin senkronizasyonu toplu sağlar. **Hata:** mükerrer dış referans → mevcut hesabı döndür, yeni oluşturma |
| Durum geçişi | `—` → `ACTIVE` |
| Yetki | `identity.user.manage` + kurum geneli scope; sistem senkronizasyonunda servis yetkisi |
| Audit | `USER_PROVISIONED` (dış kimlik referansı, kaynak, aktör) |
| API | `POST /users` — idempotent (dış referansa göre) |
| Ekran | Yönetim > Kullanıcılar |
| Tablo | `users`(user_id, external_identity_ref, display_name, status, created_at, version) |
| Test | idempotency; mükerrer dış referans; toplu senkronizasyon; audit |

###### D02.C01.W01.A02 — Kullanıcıyı pasifleştir

| Alan | Değer |
|---|---|
| Amaç | Ayrılan veya erişimi kaldırılan kullanıcının sistem üzerindeki tüm etkisini sonlandırmak |
| Aktör | Security Admin; veya dizin senkronizasyonu ile `Sistem` |
| Tetikleyici | Manuel pasifleştirme; dizinde hesap kapanışı |
| Ön koşul | Kullanıcı `ACTIVE` |
| Akış | **Temel:** açık oturumları sonlandır → rol atamalarını `REVOKED` yap → açık sorumluluk listesi üret → `INACTIVE` → audit. **Alternatif:** açık sorumluluklar için devir akışı başlatılır. **Hata:** devredilmemiş kritik sorumluluk varsa → uyar, zorlama seçeneği sun |
| Durum geçişi | `ACTIVE` → `INACTIVE`; tüm `role_assignments` `ACTIVE` → `REVOKED`; tüm `sessions` `ACTIVE` → `TERMINATED` |
| Yetki | `identity.user.manage` + kurum geneli scope |
| Audit | `USER_DEACTIVATED` (kullanıcı, sonlandırılan oturum sayısı, iptal edilen rol sayısı, açık sorumluluk sayısı) |
| API | `POST /users/{id}/deactivation` |
| Ekran | Yönetim > Kullanıcılar > Detay |
| Tablo | `users`(status); `role_assignments`(status); `sessions`(status) |
| Test | işlem atomikliği; oturum sonlandırma; açık sorumluluk uyarısı; audit |

###### D02.C01.W01.A03 — Kullanıcıyı yeniden etkinleştir

| Alan | Değer |
|---|---|
| Amaç | Geçici olarak kapatılmış erişimi, geçmiş yetkileri otomatik geri vermeden yeniden açmak |
| Aktör | Security Admin |
| Tetikleyici | Yönetim ekranından yeniden etkinleştirme |
| Ön koşul | Kullanıcı `INACTIVE`; dışsal kimlik hâlâ geçerli |
| Akış | **Temel:** dış kimliği doğrula → `ACTIVE` → roller **geri verilmez**, yeniden atanması gerekir → audit. **Alternatif:** önceki rol seti öneri olarak sunulur, açık onayla atanır. **Hata:** dış kimlik geçersizse → reddet |
| Durum geçişi | `INACTIVE` → `ACTIVE` |
| Yetki | `identity.user.manage` + kurum geneli scope |
| Audit | `USER_REACTIVATED` (kullanıcı, önceki pasifleştirme tarihi) |
| API | `POST /users/{id}/reactivation` |
| Ekran | Yönetim > Kullanıcılar > Detay |
| Tablo | `users`(status, version) |
| Test | rolün otomatik geri verilmemesi; dış kimlik doğrulama; durum-makinesi; audit |

##### D02.C01.W02 — Servis hesabı yaşam döngüsü

###### D02.C01.W02.A01 — Servis hesabı oluştur

| Alan | Değer |
|---|---|
| Amaç | Programatik entegrasyonların insan hesabı kullanmadan, dar kapsamlı ve izlenebilir erişmesini sağlamak |
| Aktör | Security Admin |
| Tetikleyici | Entegrasyon talebi |
| Ön koşul | Sahip kullanıcı `ACTIVE`; amaç ve kapsam tanımlı; geçerlilik süresi zorunlu |
| Akış | **Temel:** ad/amaç/sahip/kapsam/son kullanma gir → hesap oluştur → kimlik bilgisi referansı üret → `ACTIVE` → audit. **Alternatif:** salt okunur amaçlı hesap için yazma izinleri bloklanır. **Hata:** süresiz hesap talebi → reddet |
| Durum geçişi | `—` → `ACTIVE` |
| Yetki | `identity.service-account.manage` + kurum geneli scope |
| Audit | `SERVICE_ACCOUNT_CREATED` (hesap, sahip, amaç, kapsam, son kullanma) |
| API | `POST /service-accounts` |
| Ekran | Yönetim > Servis Hesapları |
| Tablo | `service_accounts`(service_account_id, name, purpose, owner_user_id, credential_ref, expires_at, status) |
| Test | süresiz hesap reddi; kimlik bilgisi referansı (değer saklanmaması); yetki; audit |

###### D02.C01.W02.A02 — Servis hesabı kimlik bilgisini döndür (rotate)

| Alan | Değer |
|---|---|
| Amaç | Uzun ömürlü kimlik bilgilerinin sürekli kullanımından doğan riski kesmek |
| Aktör | Security Admin; hesap sahibi |
| Tetikleyici | Manuel döndürme; son kullanma yaklaşma uyarısı; ihlal şüphesi |
| Ön koşul | Hesap `ACTIVE` |
| Akış | **Temel:** yeni kimlik bilgisi referansı üret → geçiş süresi boyunca ikisini de kabul et → eskiyi iptal et → audit. **Alternatif:** acil döndürmede geçiş süresi sıfırlanır. **Hata:** aktif geçiş süreci varsa → reddet |
| Durum geçişi | `—` (kimlik bilgisi referansı değişir) |
| Yetki | `identity.service-account.rotate` + hesap sahipliği veya kurum geneli scope |
| Audit | `SERVICE_ACCOUNT_CREDENTIAL_ROTATED` (hesap, geçiş süresi, acil mi) |
| API | `POST /service-accounts/{id}/credential-rotation` |
| Ekran | Yönetim > Servis Hesapları > Detay |
| Tablo | `service_accounts`(credential_ref, previous_credential_ref, rotation_grace_until) |
| Test | geçiş süresi davranışı; acil döndürme; eşzamanlı döndürme reddi; audit |

#### D02.C02 — Rol ve izin yönetimi

##### D02.C02.W01 — Rol tanımı yönetimi

###### D02.C02.W01.A01 — Rol tanımla

| Alan | Değer |
|---|---|
| Amaç | İzinleri tek tek atamak yerine, iş sorumluluğuna karşılık gelen tutarlı yetki paketleri kurmak |
| Aktör | Security Admin |
| Tetikleyici | Yönetim ekranından rol oluşturma |
| Ön koşul | Rol kodu benzersiz; seçilen izinler izin kataloğunda tanımlı |
| Akış | **Temel:** kod/ad/izin seti gir → izin geçerliliğini doğrula → görev ayrılığı çakışması kontrol et → kaydet → audit. **Alternatif:** mevcut rolden kopyalanarak oluşturulur. **Hata:** çakışan izin çifti içeriyorsa → uyar ve açık onay iste |
| Durum geçişi | `—` → `ACTIVE` |
| Yetki | `identity.role.manage` + kurum geneli scope |
| Audit | `ROLE_DEFINED` (rol kodu, izin sayısı, çakışma onayı) |
| API | `POST /roles` |
| Ekran | Yönetim > Roller |
| Tablo | `roles`(role_id, code, name, status, version); `role_permissions`(role_id, permission_code) |
| Test | izin geçerliliği; görev ayrılığı çakışması; benzersizlik; audit |

###### D02.C02.W01.A02 — Rol izinlerini değiştir

| Alan | Değer |
|---|---|
| Amaç | Sorumluluk değiştiğinde yetki paketini, etkisini görerek güncellemek |
| Aktör | Security Admin |
| Tetikleyici | Yönetim ekranından düzenleme |
| Ön koşul | Rol `ACTIVE`; iyimser kilit sürümü eşleşmeli |
| Akış | **Temel:** izin ekle/çıkar → etkilenen kullanıcı sayısını göster → onayla → uygula → audit. **Alternatif:** yüksek etkili değişiklikte ikinci onay istenir. **Hata:** görev ayrılığı çakışması → reddet; eşzamanlı değişiklik → sürüm çakışması |
| Durum geçişi | `—` |
| Yetki | `identity.role.manage` + kurum geneli scope |
| Audit | `ROLE_PERMISSIONS_CHANGED` (rol, eklenen/çıkarılan izinler, etkilenen kullanıcı sayısı) |
| API | `PUT /roles/{id}/permissions` — `If-Match` |
| Ekran | Yönetim > Roller > Detay |
| Tablo | `role_permissions`(role_id, permission_code); `roles`(version) |
| Test | etki hesabı; çakışma reddi; eşzamanlılık; audit |

##### D02.C02.W02 — İzin kataloğu yönetimi

###### D02.C02.W02.A01 — İzin kataloğunu görüntüle

| Alan | Değer |
|---|---|
| Amaç | Sistemin koruduğu her işlemin hangi izinle korunduğunu tek listede görünür kılmak |
| Aktör | Security Admin; Auditor |
| Tetikleyici | Yönetim veya denetim ekranından görüntüleme |
| Ön koşul | Okuma yetkisi |
| Akış | **Temel:** izin kodu, açıklama, domain, kapsam tipi ve hangi rollere verildiği ile listele. **Alternatif:** role veya domaine göre filtrelenir. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `identity.permission.read` + kurum geneli scope |
| Audit | Erişim kaydı: `PERMISSION_CATALOG_VIEWED` (filtre) |
| API | `GET /permissions` — filtre ve sayfalama |
| Ekran | Yönetim > İzinler; Denetim > Yetki Görünümü |
| Tablo | `permissions`(permission_code, description, domain_code, scope_kind)(okuma) |
| Test | filtre; sayfalama; yetki; erişim kaydı |

###### D02.C02.W02.A02 — Görev ayrılığı çakışma çiftlerini yönet

| Alan | Değer |
|---|---|
| Amaç | Aynı kişide birleşmesi kontrol zafiyeti yaratan izin çiftlerini tanımlı ve zorlanabilir kılmak |
| Aktör | Security Admin |
| Tetikleyici | Yönetim ekranından çakışma kuralı tanımlama |
| Ön koşul | Her iki izin de katalogda tanımlı |
| Akış | **Temel:** izin çifti + gerekçe + zorlama seviyesi gir → mevcut ihlalleri tara → kaydet → audit. **Alternatif:** yalnız uyarı seviyesinde tanımlanır. **Hata:** mevcut ihlal varsa ve seviye `BLOCK` ise → ihlal listesi döndürülür, çözülmeden kaydedilmez |
| Durum geçişi | `—` → `ACTIVE` |
| Yetki | `identity.sod.manage` + kurum geneli scope |
| Audit | `SOD_RULE_DEFINED` (izin çifti, seviye, mevcut ihlal sayısı) |
| API | `POST /segregation-rules` |
| Ekran | Yönetim > Görev Ayrılığı |
| Tablo | `segregation_rules`(rule_id, permission_a, permission_b, enforcement_level, status) |
| Test | mevcut ihlal taraması; zorlama seviyesi davranışı; yetki; audit |

##### D02.C02.W03 — Rol atama

###### D02.C02.W03.A01 — Kullanıcıya rol ata

| Alan | Değer |
|---|---|
| Amaç | Bir kullanıcıya, belirli bir kapsam içinde geçerli olacak yetki paketi vermek |
| Aktör | Security Admin |
| Tetikleyici | Yönetim ekranından atama; erişim talebi onayı |
| Ön koşul | Kullanıcı `ACTIVE`; rol `ACTIVE`; kapsam geçerli |
| Akış | **Temel:** kullanıcı + rol + kapsam + geçerlilik gir → görev ayrılığı kontrolü → kaydet → bildir → audit. **Alternatif:** süreli atama otomatik sona erer. **Hata:** `BLOCK` seviyeli çakışma → reddet ve çakışan atamayı göster |
| Durum geçişi | `—` → `ACTIVE` |
| Yetki | `identity.role.assign` + kurum geneli scope |
| Audit | `ROLE_ASSIGNED` (kullanıcı, rol, kapsam, geçerlilik, çakışma kontrolü sonucu) |
| API | `POST /users/{id}/role-assignments` |
| Ekran | Yönetim > Kullanıcılar > Detay |
| Tablo | `role_assignments`(assignment_id, user_id, role_id, scope_type, scope_id, valid_from, valid_to, status) |
| Test | görev ayrılığı zorlaması; süreli atama sonu; kapsam geçerliliği; audit |

###### D02.C02.W03.A02 — Rol atamasını iptal et

| Alan | Değer |
|---|---|
| Amaç | Gerekmeyen yetkiyi gecikmeden kaldırmak |
| Aktör | Security Admin |
| Tetikleyici | Manuel iptal; erişim gözden geçirme kararı; görev değişikliği |
| Ön koşul | Atama `ACTIVE` |
| Akış | **Temel:** gerekçe gir → `REVOKED` → aktif oturumların yetkisini yeniden çözümle → bildir → audit. **Alternatif:** toplu iptal listeyle yapılır. **Hata:** son kalan yönetici rolü iptal ediliyorsa → uyar ve engelle |
| Durum geçişi | `ACTIVE` → `REVOKED` |
| Yetki | `identity.role.assign` + kurum geneli scope |
| Audit | `ROLE_ASSIGNMENT_REVOKED` (kullanıcı, rol, kapsam, gerekçe kodu) |
| API | `DELETE /role-assignments/{id}` |
| Ekran | Yönetim > Kullanıcılar > Detay |
| Tablo | `role_assignments`(status, revoked_at, revoked_by, reason_code) |
| Test | son yönetici koruması; oturum yetkisinin tazelenmesi; toplu iptal; audit |

#### D02.C03 — Kapsam (scope) yönetimi

Yetkinin **ne yapabildiğini** izinler, **nerede yapabildiğini** kapsam belirler.

##### D02.C03.W01 — Kapsam ataması

###### D02.C03.W01.A01 — Kapsam ata

| Alan | Değer |
|---|---|
| Amaç | Kullanıcının yetkisini yalnız sorumlu olduğu veri kümesiyle sınırlamak |
| Aktör | Security Admin; Data Governance Admin |
| Tetikleyici | Rol ataması sırasında; veya kapsam düzenleme |
| Ön koşul | Kapsam hedefi (domain, kaynak, dataset) `ACTIVE` |
| Akış | **Temel:** kapsam tipi + hedef seç → hiyerarşik genişlemeyi göster → kaydet → audit. **Alternatif:** kurum geneli kapsam ayrı ve daha yüksek yetki ister. **Hata:** kurum geneli kapsam yetkisi yoksa → reddet |
| Durum geçişi | `—` |
| Yetki | `identity.scope.assign` + kurum geneli scope |
| Audit | `SCOPE_ASSIGNED` (kullanıcı, kapsam tipi, hedef, genişleyen varlık sayısı) |
| API | `POST /role-assignments/{id}/scopes` |
| Ekran | Yönetim > Kullanıcılar > Kapsam |
| Tablo | `assignment_scopes`(assignment_id, scope_type, scope_id, includes_descendants) |
| Test | hiyerarşik genişleme; kurum geneli kapsam koruması; yetki; audit |

##### D02.C03.W02 — Kapsam çözümleme

###### D02.C03.W02.A01 — Aktör kapsamını çözümle

| Alan | Değer |
|---|---|
| Amaç | Her istekte, aktörün hangi varlıklara erişebildiğini tek ve tutarlı biçimde belirlemek |
| Aktör | Sistem |
| Tetikleyici | Kimliği doğrulanmış her istek |
| Ön koşul | Aktif oturum veya geçerli servis hesabı kimliği |
| Akış | **Temel:** aktif rol atamalarını topla → kapsamları birleştir → hiyerarşiyi genişlet → izin kümesi + erişilebilir varlık kümesi üret → istek bağlamına yerleştir. **Alternatif:** kurum geneli kapsamlı aktörde varlık kümesi genişletilmez, bayrak taşınır. **Hata:** hiçbir aktif atama yoksa → boş yetki, tüm korumalı işlemler reddedilir |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | Reddedilen erişimlerde `AUTHORIZATION_DENIED`; başarılı çözümleme çağıran işlemin kaydına gömülür |
| API | `—` (istek ara katmanı) |
| Ekran | `—` |
| Tablo | `role_assignments`, `assignment_scopes`, `role_permissions`(okuma) |
| Test | boş yetkide fail-closed; hiyerarşik genişleme; süresi geçmiş atamanın dışlanması; performans |

###### D02.C03.W02.A02 — Kapsam dışı erişimi reddet

| Alan | Değer |
|---|---|
| Amaç | Yetkisiz erişim denemelerini tutarlı biçimde engellemek ve kayıt altına almak |
| Aktör | Sistem |
| Tetikleyici | Aktörün kapsamı dışındaki bir varlığa erişim denemesi |
| Ön koşul | Kapsam çözümlemesi tamamlanmış |
| Akış | **Temel:** hedef varlığı kapsamla karşılaştır → dışarıdaysa reddet → varlığın varlığını sızdırmayan hata döndür → audit. **Alternatif:** liste uçlarında sessiz filtreleme yapılır, hata döndürülmez. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `AUTHORIZATION_DENIED` (aktör, izin kodu, hedef tipi, gerekçe — hedef kimliği maskeli) |
| API | Tüm korumalı uçlarda ortak davranış |
| Ekran | Yetkisiz erişim sayfası; liste ekranlarında sessiz filtre |
| Tablo | `audit_events`(action='AUTHORIZATION_DENIED') |
| Test | varlık sızdırmama; liste filtreleme; audit; hata sözleşmesi tutarlılığı |

#### D02.C04 — Oturum ve erişim denetimi

##### D02.C04.W01 — Oturum yaşam döngüsü

###### D02.C04.W01.A01 — Oturum kur

| Alan | Değer |
|---|---|
| Amaç | Doğrulanmış kimliği, sınırlı ömürlü ve iptal edilebilir bir sistem oturumuna dönüştürmek |
| Aktör | Tüm kullanıcı rolleri |
| Tetikleyici | Dışsal kimlik doğrulama başarısı |
| Ön koşul | Kullanıcı hesabı `ACTIVE`; kimlik doğrulama kanıtı geçerli |
| Akış | **Temel:** kimlik kanıtını doğrula → hesabı çözümle → oturum kaydı oluştur → yetki bağlamını hazırla → oturum belirteci ver → audit. **Alternatif:** ilk girişte hesap sağlama tetiklenir. **Hata:** pasif hesap → reddet; kanıt süresi geçmiş → reddet |
| Durum geçişi | `—` → `ACTIVE` |
| Yetki | Kimlik doğrulama sonrası; ek izin gerekmez |
| Audit | `SESSION_ESTABLISHED` (kullanıcı, oturum kimliği özeti, kaynak bilgisi) |
| API | Kimlik doğrulama geri dönüş ucu |
| Ekran | Giriş akışı |
| Tablo | `sessions`(session_id, user_id, established_at, expires_at, status) |
| Test | pasif hesap reddi; süre geçmiş kanıt; oturum sabitleme koruması; audit |

###### D02.C04.W01.A02 — Oturumu sonlandır

| Alan | Değer |
|---|---|
| Amaç | Kullanıcının veya yöneticinin erişimi anında kesebilmesini sağlamak |
| Aktör | Oturum sahibi; Security Admin |
| Tetikleyici | Çıkış eylemi; yönetici iptali; süre dolumu; hesap pasifleştirme |
| Ön koşul | Oturum `ACTIVE` |
| Akış | **Temel:** oturumu `TERMINATED` yap → belirteci geçersizleştir → audit. **Alternatif:** kullanıcının tüm oturumları toplu sonlandırılır. **Hata:** zaten sonlanmış oturum → idempotent başarı |
| Durum geçişi | `ACTIVE` → `TERMINATED` \| `EXPIRED` |
| Yetki | Oturum sahipliği veya `identity.session.terminate` |
| Audit | `SESSION_TERMINATED` (oturum, sonlandırma nedeni, sonlandıran) |
| API | `POST /sessions/logout`; `DELETE /users/{id}/sessions` |
| Ekran | Üst çubuk > Çıkış; Yönetim > Kullanıcılar > Oturumlar |
| Tablo | `sessions`(status, terminated_at, termination_reason) |
| Test | idempotency; toplu sonlandırma; belirteç geçersizliği; audit |

###### D02.C04.W01.A03 — Aktif oturumları görüntüle

| Alan | Değer |
|---|---|
| Amaç | Beklenmeyen veya uzun süreli erişimlerin fark edilebilmesini sağlamak |
| Aktör | Security Admin; Auditor; oturum sahibi (kendi oturumları) |
| Tetikleyici | Yönetim veya profil ekranından görüntüleme |
| Ön koşul | Okuma yetkisi veya oturum sahipliği |
| Akış | **Temel:** aktif oturumları kullanıcı, başlangıç, son etkinlik ve kaynak bilgisiyle listele. **Alternatif:** kullanıcı yalnız kendi oturumlarını görür. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `identity.session.read` + kurum geneli scope; veya oturum sahipliği |
| Audit | Erişim kaydı: `SESSION_LIST_VIEWED` (kapsam) |
| API | `GET /sessions` — filtre ve sayfalama |
| Ekran | Yönetim > Oturumlar; Profil > Oturumlarım |
| Tablo | `sessions`(okuma) |
| Test | sahiplik filtresi; sayfalama; yetki; erişim kaydı |

##### D02.C04.W02 — Yetki kararı ve reddi

###### D02.C04.W02.A01 — İzin kontrolü uygula

| Alan | Değer |
|---|---|
| Amaç | Her korumalı işlemin, tanımlı bir izin koduna karşı tek biçimde denetlenmesini sağlamak |
| Aktör | Sistem |
| Tetikleyici | Korumalı bir işleme yapılan her çağrı |
| Ön koşul | Kapsam çözümlemesi tamamlanmış |
| Akış | **Temel:** işlemin gerektirdiği izin kodunu al → aktörün izin kümesinde ara → yoksa reddet → varsa kapsam kontrolüne geç. **Alternatif:** görev ayrılığı gerektiren işlemlerde ek aktör karşılaştırması yapılır. **Hata:** izin kodu katalogda tanımsızsa → işlem reddedilir (yapılandırma hatası fail-closed) |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | Ret durumunda `AUTHORIZATION_DENIED` (izin kodu, aktör, işlem) |
| API | Tüm korumalı uçlarda ortak ara katman |
| Ekran | `—` |
| Tablo | `permissions`, `role_permissions`(okuma) |
| Test | tanımsız izin kodunda fail-closed; görev ayrılığı kontrolü; ret kaydı; kapsamlı/kapsamsız yol |

#### D02.C05 — Erişim gözden geçirme

##### D02.C05.W01 — Periyodik erişim sertifikasyonu

###### D02.C05.W01.A01 — Erişim gözden geçirme kampanyası başlat

| Alan | Değer |
|---|---|
| Amaç | Yetkilerin zamanla birikmesini önlemek ve her erişimin hâlâ gerekli olduğunu teyit ettirmek |
| Aktör | Security Admin |
| Tetikleyici | Periyodik zamanlayıcı; manuel başlatma |
| Ön koşul | Gözden geçirme politikası yürürlükte; kapsam ve son tarih tanımlı |
| Akış | **Temel:** kapsamdaki tüm aktif atamaları topla → onaylayıcıya göre gruplandır → kampanya kalemleri oluştur → onaylayıcılara bildir → audit. **Alternatif:** yalnız yüksek riskli izinler kapsanır. **Hata:** politika yoksa → başlatma reddedilir |
| Durum geçişi | Kampanya `—` → `IN_PROGRESS` |
| Yetki | `identity.access-review.manage` + kurum geneli scope |
| Audit | `ACCESS_REVIEW_STARTED` (kampanya, kapsam, kalem sayısı, son tarih) |
| API | `POST /access-reviews` |
| Ekran | Yönetim > Erişim Gözden Geçirme |
| Tablo | `access_review_campaigns`(campaign_id, scope, due_at, status); `access_review_items`(campaign_id, assignment_id, reviewer_user_id, decision, status) |
| Test | kalem üretimi; politika yokluğunda ret; bildirim; audit |

###### D02.C05.W01.A02 — Erişim kalemi kararı ver

| Alan | Değer |
|---|---|
| Amaç | Her yetkinin devamı ya da kaldırılması konusunda sorumlu bir karar kaydı üretmek |
| Aktör | Data Owner; Security Admin (kendi atamasını gözden geçiremez) |
| Tetikleyici | Gözden geçirme kuyruğundan karar |
| Ön koşul | Kalem `PENDING`; gözden geçiren ≠ atama sahibi |
| Akış | **Temel:** kalemi incele → onayla veya kaldır → kararı kaydet → kaldırmada rol iptalini tetikle → audit. **Alternatif:** karar verilmeyen kalemler son tarihte politikaya göre otomatik kaldırılır. **Hata:** kendi atamasını gözden geçirme → reddet |
| Durum geçişi | Kalem `PENDING` → `CERTIFIED` \| `REVOKED` \| `AUTO_REVOKED` |
| Yetki | `identity.access-review.decide` + kapsam; görev ayrılığı zorunlu |
| Audit | `ACCESS_REVIEW_DECIDED` (kalem, karar, gözden geçiren, gerekçe) |
| API | `POST /access-review-items/{id}/decision` |
| Ekran | Yönetim > Erişim Gözden Geçirme > Kuyruk |
| Tablo | `access_review_items`(decision, decided_by, decided_at, status) |
| Test | kendi atamasını gözden geçirme reddi; otomatik kaldırma; rol iptali zinciri; audit |

##### L5 — D02 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D02-001` | Sistem kimlik doğrulaması yapmaz; yalnız dışsal olarak doğrulanmış kimliği tüketir |
| `BR-D02-002` | Yeniden etkinleştirilen kullanıcıya önceki rolleri otomatik geri verilmez |
| `BR-D02-003` | Pasifleştirilen kullanıcının tüm aktif oturumları ve rol atamaları aynı işlemde sonlandırılır |
| `BR-D02-004` | Servis hesapları süresiz olamaz; her hesabın son kullanma tarihi bulunur |
| `BR-D02-005` | Kimlik bilgisinin kendisi saklanmaz; yalnız dışsal sır yöneticisindeki referansı saklanır |
| `BR-D02-006` | `BLOCK` seviyeli görev ayrılığı çakışması yaratan rol ataması yapılamaz |
| `BR-D02-007` | Yetki, izin kümesi ve kapsam kümesinin kesişimidir; ikisinden biri boşsa erişim yoktur |
| `BR-D02-008` | Katalogda tanımsız bir izin koduyla korunan işlem, çağrıldığında reddedilir |
| `BR-D02-009` | Kapsam dışı varlığa erişim, varlığın varlığını sızdırmayan bir hatayla reddedilir |
| `BR-D02-010` | Liste uçlarında kapsam dışı kayıtlar hata döndürmeden sessizce filtrelenir |
| `BR-D02-011` | Bir aktör kendi rol atamasını erişim gözden geçirmesinde onaylayamaz |
| `BR-D02-012` | Sistemde en az bir aktif yönetici rolü ataması kalmalıdır; son atama iptal edilemez |
| `BR-D02-013` | Süresi geçmiş rol atamaları kapsam çözümlemesine dâhil edilmez |

---

### D03 — Veri Kaynağı ve Bağlantı Yönetimi

Kalite ölçümünün fiziksel giriş kapısı. Kaynağa erişimin salt okunur, sırların
referansla yönetilen ve kaynak üzerindeki yükün politikayla sınırlanan olmasını
garanti eder.

#### D03.C01 — Kaynak onboarding

##### D03.C01.W01 — Kaynak kaydı oluşturma

###### D03.C01.W01.A01 — Veri kaynağı kaydı oluştur

| Alan | Değer |
|---|---|
| Amaç | Kalite ölçümü yapılacak bir sistemi, bağlantı ve sahiplik bilgisiyle envantere almak |
| Aktör | Technical Data Steward; Data Owner |
| Tetikleyici | Kaynak ekranından yeni kaynak |
| Ön koşul | Kaynak adı benzersiz; sahip kullanıcı `ACTIVE`; veri domaini seçili |
| Akış | **Temel:** ad/tip/bağlantı parametreleri/sahip/domain gir → parametre şemasını tipe göre doğrula → `TEST_PENDING` kaydet → audit. **Alternatif:** mevcut kaynaktan şablon olarak kopyalanır. **Hata:** şema dışı parametre → alan bazlı hata; sır değeri gövdede gelirse → reddet |
| Durum geçişi | `—` → `TEST_PENDING` |
| Yetki | `datasource.create` + veri domaini kapsamı |
| Audit | `DATA_SOURCE_CREATED` (kaynak, tip, domain, sahip — bağlantı parametreleri maskeli) |
| API | `POST /data-sources` — idempotency anahtarı |
| Ekran | Veri Kaynakları > Yeni Kaynak |
| Tablo | `data_sources`(data_source_id, name, source_type, connection_config, secret_ref, owner_user_id, data_domain_id, status, revision) |
| Test | tip bazlı şema doğrulama; sır sızdırma reddi; benzersizlik; audit maskeleme |

###### D03.C01.W01.A02 — Kaynak erişim modunu salt okunur olarak zorla

| Alan | Değer |
|---|---|
| Amaç | Sistemin kaynak üretim verisini hiçbir koşulda değiştirememesini yapısal olarak garantilemek |
| Aktör | Sistem |
| Tetikleyici | Her bağlantı kurulumu |
| Ön koşul | Bağlantı parametreleri çözümlenmiş |
| Akış | **Temel:** bağlantıyı salt okunur modda aç → oturum düzeyinde yazma yasağı uygula → yalnız okuma ifadelerine izin ver. **Alternatif:** sürücü salt okunur modu desteklemiyorsa ifade düzeyi süzgeci uygulanır. **Hata:** salt okunur mod kurulamazsa → bağlantı açılmaz, `READ_ONLY_UNAVAILABLE` |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `READ_ONLY_ENFORCEMENT_FAILED` yalnız başarısızlıkta |
| API | `—` (bağlantı katmanı) |
| Ekran | `—` |
| Tablo | `—` |
| Test | yazma ifadesi reddi; salt okunur mod kurulamama yolu; sürücü bazlı davranış |

##### D03.C01.W02 — Bağlantı sırrı referansı bağlama

###### D03.C01.W02.A01 — Sır referansı bağla

| Alan | Değer |
|---|---|
| Amaç | Bağlantı kimlik bilgilerinin sistemde saklanmadan, dışsal sır yöneticisinden çözümlenmesini sağlamak |
| Aktör | Technical Data Steward; Security Admin |
| Tetikleyici | Kaynak detayından sır bağlama |
| Ön koşul | Sır referansı biçimsel olarak geçerli; kaynak `TEST_PENDING` veya `ACTIVE` |
| Akış | **Temel:** referansı gir → biçim doğrula → çözümlenebilirliğini sına (değeri saklamadan) → referansı kaydet → audit. **Alternatif:** referans döndürüldüğünde yeni sürüm bağlanır. **Hata:** çözümlenemeyen referans → reddet; sır değeri girilirse → reddet |
| Durum geçişi | `—` |
| Yetki | `datasource.secret.bind` + kaynak kapsamı |
| Audit | `SECRET_REFERENCE_BOUND` (kaynak, referans kimliği — değer asla) |
| API | `PUT /data-sources/{id}/secret-reference` |
| Ekran | Veri Kaynakları > Detay > Bağlantı |
| Tablo | `data_sources`(secret_ref, secret_bound_at) |
| Test | değer sızdırma reddi; çözümlenebilirlik sınaması; referans döndürme; audit |

###### D03.C01.W02.A02 — Sırrı çalıştırma anında çözümle

| Alan | Değer |
|---|---|
| Amaç | Sır değerinin yalnız kullanıldığı an bellekte bulunmasını, hiçbir yerde kalıcılaşmamasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Bağlantı kurulumu gereken her işlem |
| Ön koşul | Sır referansı bağlı; sır yöneticisi erişilebilir |
| Akış | **Temel:** referansı sır yöneticisinden çöz → bağlantıyı kur → kullanım sonrası bellekten temizle. **Alternatif:** kısa ömürlü önbellek politikayla sınırlı tutulur. **Hata:** sır yöneticisi erişilemezse → işlem `TECHNICAL_ERROR` ile sonlanır, kalite hatası sayılmaz |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü; çağıran işlemin yetkisi |
| Audit | `SECRET_RESOLUTION_FAILED` yalnız başarısızlıkta (referans kimliği, hata sınıfı) |
| API | `—` (iç servis) |
| Ekran | `—` |
| Tablo | `—` |
| Test | değer kalıcılaşmaması; erişilemezlikte teknik hata sınıflandırması; önbellek süresi |

##### D03.C01.W03 — Bağlantı testi

###### D03.C01.W03.A01 — Bağlantıyı test et

| Alan | Değer |
|---|---|
| Amaç | Kaynağın erişilebilir, yetkilerin yeterli ve salt okunur kısıtın geçerli olduğunu aktivasyon öncesi kanıtlamak |
| Aktör | Technical Data Steward |
| Tetikleyici | Kaynak detayından test; aktivasyon öncesi zorunlu adım |
| Ön koşul | Sır referansı bağlı; kaynak `TEST_PENDING`, `TEST_FAILED` veya `ACTIVE` |
| Akış | **Temel:** sırrı çöz → bağlan → sürüm ve yetki bilgisini oku → salt okunurluğu doğrula → sonucu kaydet → audit. **Alternatif:** başarılı testte kaynak `TEST_SUCCEEDED` olur. **Hata:** zaman aşımı, kimlik hatası, yetki yetersizliği ve ağ hatası ayrı hata sınıfları olarak kaydedilir |
| Durum geçişi | `TEST_PENDING`\|`TEST_FAILED` → `TEST_SUCCEEDED` \| `TEST_FAILED` |
| Yetki | `datasource.test.execute` + kaynak kapsamı |
| Audit | `CONNECTION_TESTED` (kaynak, sonuç, süre, hata sınıfı, revizyon) |
| API | `POST /data-sources/{id}/connection-test` |
| Ekran | Veri Kaynakları > Detay |
| Tablo | `connection_test_results`(test_result_id, data_source_id, succeeded, duration_ms, error_class, source_info, data_source_revision, tested_at) |
| Test | hata sınıfı ayrımı; zaman aşımı; salt okunur doğrulaması; durum-makinesi; audit |

###### D03.C01.W03.A02 — Test geçmişini görüntüle

| Alan | Değer |
|---|---|
| Amaç | Aralıklı bağlantı sorunlarının örüntüsünü görebilmek |
| Aktör | Technical Data Steward; Operations User |
| Tetikleyici | Kaynak detayından geçmiş görüntüleme |
| Ön koşul | Kaynak üzerinde okuma kapsamı |
| Akış | **Temel:** zaman sıralı test sonuçlarını sonuç, süre ve hata sınıfıyla listele. **Alternatif:** yalnız başarısızlıklar filtrelenir. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `datasource.read` + kaynak kapsamı |
| Audit | Erişim kaydı: `CONNECTION_TEST_HISTORY_VIEWED` (kaynak) |
| API | `GET /data-sources/{id}/connection-tests` — sayfalama |
| Ekran | Veri Kaynakları > Detay > Test Geçmişi |
| Tablo | `connection_test_results`(okuma) |
| Test | sayfalama; filtre; kapsam yetkisi; erişim kaydı |

#### D03.C02 — Kaynak onayı ve aktivasyonu

##### D03.C02.W01 — Aktivasyon onay akışı

###### D03.C02.W01.A01 — Kaynak aktivasyonu talep et

| Alan | Değer |
|---|---|
| Amaç | Üretim verisine erişecek bir kaynağın devreye alınmasını görev ayrılığıyla denetlemek |
| Aktör | Technical Data Steward (maker) |
| Tetikleyici | Kaynak detayından aktivasyon talebi |
| Ön koşul | Kaynak `TEST_SUCCEEDED`; son başarılı test güncel revizyona ait; sahip atanmış |
| Akış | **Temel:** gerekçe gir → talep aç → `PENDING` → onaylayıcıya bildir → audit. **Alternatif:** revizyon değişikliği sonrası yeniden talep gerekir. **Hata:** açık talep varsa → reddet; test bayatsa → yeniden test iste |
| Durum geçişi | `ApprovalRequest` `—` → `PENDING` |
| Yetki | `datasource.activation.request` + kaynak kapsamı |
| Audit | `DATA_SOURCE_ACTIVATION_REQUESTED` (kaynak, revizyon, maker, gerekçe) |
| API | `POST /data-sources/{id}/activation-requests` |
| Ekran | Veri Kaynakları > Detay |
| Tablo | `data_source_activation_requests`(activation_request_id, data_source_id, data_source_revision, maker_actor_id, status, requested_at) |
| Test | bayat test reddi; mükerrer talep; durum-makinesi; audit |

###### D03.C02.W01.A02 — Kaynak aktivasyon kararı ver

| Alan | Değer |
|---|---|
| Amaç | Kaynağın üretim kullanımına açılmasını yetkilendirmek veya gerekçeyle geri çevirmek |
| Aktör | Data Owner (maker'dan farklı) |
| Tetikleyici | Onay kuyruğundan karar |
| Ön koşul | Talep `PENDING`; checker ≠ maker; kaynak revizyonu değişmemiş |
| Akış | **Temel:** test kanıtını incele → karar + gerekçe → onayda kaynağı `ACTIVE` yap → bildir → audit. **Alternatif:** redde kaynak `TEST_SUCCEEDED` kalır. **Hata:** maker=checker → reddet; revizyon değişmişse → talebi `EXPIRED` yap |
| Durum geçişi | Talep `PENDING` → `APPROVED` \| `REJECTED` \| `EXPIRED`; kaynak `TEST_SUCCEEDED` → `ACTIVE` |
| Yetki | `datasource.activation.decide` + kaynak kapsamı; görev ayrılığı zorunlu |
| Audit | `DATA_SOURCE_ACTIVATION_DECIDED` (karar, gerekçe kodu, maker, checker, revizyon) |
| API | `POST /data-source-activation-requests/{id}/decision` — `If-Match` |
| Ekran | Onay Kuyruğu; Veri Kaynakları > Detay |
| Tablo | `data_source_activation_requests`(status, checker_actor_id, decided_at, reason_code); `data_sources`(status) |
| Test | görev ayrılığı; revizyon değişiminde süre aşımı; eşzamanlılık; audit |

##### D03.C02.W02 — Pasifleştirme ve arşivleme

###### D03.C02.W02.A01 — Kaynağı pasifleştir

| Alan | Değer |
|---|---|
| Amaç | Sorunlu veya kullanımdan kalkan bir kaynağa yeni çalıştırma gönderilmesini durdurmak |
| Aktör | Data Owner; Operations User |
| Tetikleyici | Manuel pasifleştirme; kalıcı bağlantı hatası eşiği aşımı |
| Ön koşul | Kaynak `ACTIVE` |
| Akış | **Temel:** gerekçe gir → yeni çalıştırma kabulünü durdur → devam eden çalıştırmaları bitmeye bırak → `INACTIVE` → etkilenen kural sahiplerine bildir → audit. **Alternatif:** acil pasifleştirmede devam eden çalıştırmalar iptal edilir. **Hata:** `—` |
| Durum geçişi | `ACTIVE` → `INACTIVE` |
| Yetki | `datasource.deactivate` + kaynak kapsamı |
| Audit | `DATA_SOURCE_DEACTIVATED` (kaynak, gerekçe, etkilenen kural sayısı, açık çalıştırma sayısı) |
| API | `POST /data-sources/{id}/deactivation` |
| Ekran | Veri Kaynakları > Detay |
| Tablo | `data_sources`(status, version) |
| Test | devam eden çalıştırma davranışı; acil yol; bildirim; audit |

###### D03.C02.W02.A02 — Kaynağı arşivle

| Alan | Değer |
|---|---|
| Amaç | Kullanımdan tamamen kalkan kaynağın envanterden çıkarılırken geçmiş kanıtının korunmasını sağlamak |
| Aktör | Data Owner; Data Governance Admin |
| Tetikleyici | Kaynak detayından arşivleme |
| Ön koşul | Kaynak `INACTIVE`; bağlı `ACTIVE` kural bulunmamalı; açık sorun bulunmamalı |
| Akış | **Temel:** bağımlılık kontrolü → `ARCHIVED` → bağlı dataset'leri arşivle → audit. **Alternatif:** bağlı kurallar önce arşivlenmek üzere listelenir. **Hata:** açık sorun varsa → reddet ve listeyi döndür |
| Durum geçişi | `INACTIVE` → `ARCHIVED`; bağlı dataset'ler `ACTIVE` → `ARCHIVED` |
| Yetki | `datasource.archive` + kaynak kapsamı |
| Audit | `DATA_SOURCE_ARCHIVED` (kaynak, arşivlenen dataset sayısı) |
| API | `POST /data-sources/{id}/archival` |
| Ekran | Veri Kaynakları > Detay |
| Tablo | `data_sources`(status); `datasets`(status) |
| Test | bağımlılık reddi; ardışık arşivleme; geçmiş korunumu; audit |

#### D03.C03 — Bağlantı politikası ve kota

##### D03.C03.W01 — Kullanım politikası yönetimi

###### D03.C03.W01.A01 — Kaynak kullanım politikası tanımla

| Alan | Değer |
|---|---|
| Amaç | Kalite ölçümünün kaynak sistem üzerinde kabul edilemez yük oluşturmasını engellemek |
| Aktör | Technical Data Steward; Platform Admin |
| Tetikleyici | Kaynak detayından politika tanımlama |
| Ön koşul | Kaynak `ACTIVE` veya `TEST_SUCCEEDED` |
| Akış | **Temel:** eşzamanlı sorgu, worker sayısı, sorgu zaman aşımı, yeniden deneme ve hız sınırı gir → doğrula → onaya gönder → audit. **Alternatif:** kaynak tipi için kurum varsayılanından türetilir. **Hata:** kaynak kapasitesinin üstünde değer → uyar |
| Durum geçişi | Politika `—` → `DRAFT` |
| Yetki | `datasource.policy.manage` + kaynak kapsamı |
| Audit | `SOURCE_USAGE_POLICY_DRAFTED` (kaynak, parametre özeti) |
| API | `POST /data-sources/{id}/usage-policies` |
| Ekran | Veri Kaynakları > Detay > Kullanım Politikası |
| Tablo | `source_usage_policies`(policy_id, data_source_id, max_concurrent_queries, max_workers, query_timeout_seconds, retry_count, rate_limit, status, policy_version) |
| Test | sınır doğrulama; varsayılandan türetme; onay zinciri; audit |

###### D03.C03.W01.A02 — Kota aşımında çalıştırmayı sınırla

| Alan | Değer |
|---|---|
| Amaç | Kaynak üzerindeki anlık yükü politika sınırları içinde tutmak |
| Aktör | Sistem |
| Tetikleyici | Kaynağa sorgu gönderecek her iş sahiplenmesi |
| Ön koşul | Yürürlükte kullanım politikası bulunmalı |
| Akış | **Temel:** kaynak için aktif sorgu sayısını al → sınır altındaysa izin ver → üstündeyse işi ertele ve kuyrukta bırak. **Alternatif:** hız sınırı aşımında iş gecikmeli yeniden planlanır. **Hata:** politika yoksa → iş sahiplenilmez, fail-closed |
| Durum geçişi | İş `CLAIMED` → `AVAILABLE` (erteleme durumunda) |
| Yetki | Sistem aktörü |
| Audit | `SOURCE_QUOTA_THROTTLED` (kaynak, sınır, anlık değer, ertelenen iş) |
| API | `—` (worker sahiplenme yolu) |
| Ekran | Operasyon > Kuyruk (erteleme görünürlüğü) |
| Tablo | `source_usage_policies`(okuma); `persistent_jobs`(status, available_at) |
| Test | sınır davranışı; erteleme; politika yokluğunda fail-closed; eşzamanlılık |

##### D03.C03.W02 — Erişim penceresi yönetimi

###### D03.C03.W02.A01 — İzinli/yasaklı zaman penceresi tanımla

| Alan | Değer |
|---|---|
| Amaç | Kaynağın yoğun iş saatlerinde veya bakım pencerelerinde ölçüm yüküyle karşılaşmasını engellemek |
| Aktör | Technical Data Steward |
| Tetikleyici | Politika ekranından pencere tanımlama |
| Ön koşul | Kullanım politikası mevcut |
| Akış | **Temel:** zaman dilimi, gün ve saat aralıklarını gir → çakışma kontrolü → kaydet → audit. **Alternatif:** yasaklı pencere izinli pencereye göre önceliklidir. **Hata:** tüm zamanı yasaklayan tanım → uyar ve açık onay iste |
| Durum geçişi | `—` |
| Yetki | `datasource.policy.manage` + kaynak kapsamı |
| Audit | `SOURCE_ACCESS_WINDOW_CHANGED` (kaynak, pencere özeti) |
| API | `PUT /source-usage-policies/{id}/windows` |
| Ekran | Veri Kaynakları > Detay > Kullanım Politikası |
| Tablo | `source_usage_policies`(allowed_windows, blocked_windows, timezone_name) |
| Test | zaman dilimi doğruluğu; çakışma önceliği; tümünü yasaklama uyarısı; audit |

###### D03.C03.W02.A02 — Pencere dışı çalıştırmayı ertele

| Alan | Değer |
|---|---|
| Amaç | Yasaklı pencerede kaynağa erişilmemesini garanti etmek |
| Aktör | Sistem |
| Tetikleyici | İş sahiplenme anı |
| Ön koşul | Kaynak için pencere tanımı mevcut |
| Akış | **Temel:** şu anki zamanı pencerelerle karşılaştır → izinliyse devam → değilse bir sonraki izinli ana ertele. **Alternatif:** acil öncelikli işler pencere kısıtından muaf tutulabilir (politikayla). **Hata:** hiç izinli pencere yoksa → iş `BLOCKED` ile işaretlenir ve operatöre görünür |
| Durum geçişi | İş `CLAIMED` → `AVAILABLE` \| `BLOCKED` |
| Yetki | Sistem aktörü |
| Audit | `SOURCE_WINDOW_DEFERRED` (kaynak, sonraki izinli an, iş) |
| API | `—` |
| Ekran | Operasyon > Kuyruk |
| Tablo | `persistent_jobs`(status, available_at) |
| Test | zaman dilimi sınırları; muafiyet; izinli pencere yokluğu; erteleme doğruluğu |

#### D03.C04 — Bağlantı revizyon yönetimi

##### D03.C04.W01 — Bağlantı değişikliği ve geri alma

###### D03.C04.W01.A01 — Bağlantı revizyonu oluştur

| Alan | Değer |
|---|---|
| Amaç | Bağlantı bilgisi değişikliğinin, çalışan yapılandırmayı bozmadan hazırlanıp sınanmasını sağlamak |
| Aktör | Technical Data Steward |
| Tetikleyici | Kaynak detayından bağlantı değişikliği |
| Ön koşul | Kaynak `ACTIVE` veya `INACTIVE`; açık `DRAFT` revizyon bulunmamalı |
| Akış | **Temel:** mevcut revizyondan kopyala → parametreleri değiştir → yeni revizyon `DRAFT` → test edilmeden yürürlüğe alınamaz → audit. **Alternatif:** sır referansı da revizyonla değişebilir. **Hata:** açık taslak revizyon varsa → reddet |
| Durum geçişi | Revizyon `—` → `DRAFT` |
| Yetki | `datasource.connection.revise` + kaynak kapsamı |
| Audit | `CONNECTION_REVISION_CREATED` (kaynak, temel revizyon, yeni revizyon — parametreler maskeli) |
| API | `POST /data-sources/{id}/connection-revisions` |
| Ekran | Veri Kaynakları > Detay > Bağlantı |
| Tablo | `data_source_connection_revisions`(connection_revision_id, data_source_id, revision, base_revision, connection_config, secret_ref, status) |
| Test | tek açık taslak kısıtı; kopyalama doğruluğu; maskeleme; audit |

###### D03.C04.W01.A02 — Bağlantı revizyonunu yürürlüğe al

| Alan | Değer |
|---|---|
| Amaç | Sınanmış bağlantı değişikliğini, geri dönüş yolu açık kalacak biçimde devreye almak |
| Aktör | Technical Data Steward; Data Owner |
| Tetikleyici | Revizyon detayından yürürlüğe alma |
| Ön koşul | Revizyon `TESTED`; kaynak üzerinde devam eden çalıştırma yok veya bitmesi beklenmiş |
| Akış | **Temel:** önceki revizyonu `SUPERSEDED` yap → yeniyi `EFFECTIVE` yap → kaynak revizyon sayacını artır → açık aktivasyon taleplerini `EXPIRED` yap → audit. **Alternatif:** devam eden çalıştırmalar eski revizyonla tamamlanır. **Hata:** test edilmemiş revizyon → reddet |
| Durum geçişi | Revizyon `TESTED` → `EFFECTIVE`; önceki `EFFECTIVE` → `SUPERSEDED` |
| Yetki | `datasource.connection.apply` + kaynak kapsamı |
| Audit | `CONNECTION_REVISION_APPLIED` (kaynak, eski/yeni revizyon, iptal edilen talep sayısı) |
| API | `POST /connection-revisions/{id}/application` — `If-Match` |
| Ekran | Veri Kaynakları > Detay > Bağlantı |
| Tablo | `data_source_connection_revisions`(status); `data_sources`(revision, connection_config, secret_ref) |
| Test | test ön koşulu; devam eden çalıştırma davranışı; talep süre aşımı; audit |

###### D03.C04.W01.A03 — Bağlantı revizyonunu geri al

| Alan | Değer |
|---|---|
| Amaç | Hatalı bağlantı değişikliğinden hızla dönmek |
| Aktör | Operations User; Technical Data Steward |
| Tetikleyici | Yürürlük sonrası bağlantı hatası |
| Ön koşul | Önceki revizyon `SUPERSEDED` ve geri alınabilir durumda |
| Akış | **Temel:** hedef revizyon seç → gerekçe gir → yürürlüğü değiştir → audit → bildir. **Hata:** hedef revizyon bulunamazsa → reddet |
| Durum geçişi | Mevcut `EFFECTIVE` → `ROLLED_BACK`; hedef `SUPERSEDED` → `EFFECTIVE` |
| Yetki | `datasource.connection.apply` + kaynak kapsamı |
| Audit | `CONNECTION_REVISION_ROLLED_BACK` (kaynak, geri alınan, dönülen, gerekçe) |
| API | `POST /data-sources/{id}/connection-revisions/rollback` |
| Ekran | Veri Kaynakları > Detay > Bağlantı Geçmişi |
| Tablo | `data_source_connection_revisions`(status); `data_sources`(revision) |
| Test | geri alma zinciri; durum-makinesi; audit |

#### D03.C05 — Kaynak sağlık izleme

##### D03.C05.W01 — Periyodik erişilebilirlik kontrolü

###### D03.C05.W01.A01 — Periyodik sağlık kontrolü yürüt

| Alan | Değer |
|---|---|
| Amaç | Kaynak erişim sorunlarını, zamanlanmış bir kalite çalıştırması başarısız olmadan önce fark etmek |
| Aktör | Sistem |
| Tetikleyici | Sağlık kontrolü zamanlayıcısı |
| Ön koşul | Kaynak `ACTIVE`; sağlık kontrol aralığı politikada tanımlı |
| Akış | **Temel:** hafif bir erişim sorgusu çalıştır → gecikme ve sonucu kaydet → eşik aşımında sağlık durumunu düşür → bildir → audit. **Alternatif:** ardışık başarısızlık eşiği aşılırsa kaynak otomatik pasifleştirme önerilir. **Hata:** kontrolün kendisi zaman aşarsa başarısızlık sayılır |
| Durum geçişi | Sağlık `HEALTHY` → `DEGRADED` → `UNAVAILABLE` (ve geri) |
| Yetki | Sistem aktörü; `datasource.healthcheck.execute` |
| Audit | `SOURCE_HEALTH_CHANGED` (kaynak, eski/yeni sağlık, ardışık başarısızlık) |
| API | `—` (zamanlanmış iş) |
| Ekran | Operasyon > Kaynak Sağlığı; Veri Kaynakları > Liste |
| Tablo | `source_health_checks`(check_id, data_source_id, healthy, latency_ms, error_class, checked_at) |
| Test | eşik davranışı; durum-makinesi; bildirim; audit |

###### D03.C05.W01.A02 — Kaynak sağlık görünümünü sun

| Alan | Değer |
|---|---|
| Amaç | Operatörün tüm kaynakların erişim durumunu tek ekranda görmesini sağlamak |
| Aktör | Operations User; Technical Data Steward |
| Tetikleyici | Operasyon ekranı açılışı |
| Ön koşul | Okuma kapsamı |
| Akış | **Temel:** kaynakları sağlık durumu, son kontrol zamanı ve gecikme ile listele → bozuk olanları öne al. **Alternatif:** yalnız `DEGRADED`/`UNAVAILABLE` filtrelenir. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `datasource.read` + kapsam |
| Audit | Erişim kaydı: `SOURCE_HEALTH_VIEWED` (filtre) |
| API | `GET /data-sources/health` — filtre |
| Ekran | Operasyon > Kaynak Sağlığı |
| Tablo | `source_health_checks`, `data_sources`(okuma) |
| Test | sıralama; filtre; kapsam; erişim kaydı |

##### L5 — D03 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D03-001` | Kaynak bağlantıları yalnız salt okunur modda açılır; mod kurulamıyorsa bağlantı açılmaz |
| `BR-D03-002` | Sır değeri hiçbir tabloda, günlükte, audit kaydında veya API yanıtında bulunmaz; yalnız referans saklanır |
| `BR-D03-003` | Aktivasyon için güncel revizyona ait başarılı bir bağlantı testi zorunludur |
| `BR-D03-004` | Aktivasyonu talep eden aktör, aynı aktivasyonu onaylayamaz |
| `BR-D03-005` | Bağlantı revizyonu değiştiğinde açık aktivasyon talepleri süre aşımına uğrar |
| `BR-D03-006` | Bir kaynağın aynı anda yalnız bir `DRAFT` bağlantı revizyonu bulunur |
| `BR-D03-007` | Test edilmemiş bağlantı revizyonu yürürlüğe alınamaz |
| `BR-D03-008` | Yürürlükte kullanım politikası bulunmayan kaynağa çalıştırma gönderilmez |
| `BR-D03-009` | Yasaklı zaman penceresi, izinli pencereye göre önceliklidir |
| `BR-D03-010` | Bağlantı ve sır hataları teknik hata olarak sınıflandırılır; kalite skorunu düşürmez |
| `BR-D03-011` | Açık sorunu veya aktif kuralı bulunan kaynak arşivlenemez |

---

### D04 — Metadata, Katalog ve Varlık Yönetimi

Ölçülecek şeyin ne olduğunu tanımlayan katman. Kaynaktaki fiziksel yapıyı keşfeder,
kataloğa dönüştürür, sınıflandırır ve şema değişimlerini yönetir.

#### D04.C01 — Metadata keşfi

##### D04.C01.W01 — Keşif çalıştırma

###### D04.C01.W01.A01 — Metadata keşfini başlat

| Alan | Değer |
|---|---|
| Amaç | Kaynaktaki dataset ve alanları elle girmeden, otomatik ve tekrarlanabilir biçimde kataloğa almak |
| Aktör | Technical Data Steward; Sistem (zamanlanmış) |
| Tetikleyici | Kaynak detayından keşif; zamanlanmış keşif; aktivasyon sonrası ilk keşif |
| Ön koşul | Kaynak `ACTIVE`; bağlantı sağlıklı; kullanım politikası yürürlükte |
| Akış | **Temel:** kapsam (şema/nesne örüntüsü) belirle → keşif işini kuyruğa al → çalıştır → ham metadata topla → sonucu kaydet. **Alternatif:** artımlı keşif yalnız değişenleri tarar. **Hata:** zaman aşımı ve yetki hatası ayrı sınıflarda kaydedilir; kısmi keşif `PARTIAL` işaretlenir |
| Durum geçişi | Keşif `—` → `RUNNING` → `SUCCESS` \| `PARTIAL` \| `TECHNICAL_ERROR` |
| Yetki | `catalog.discovery.execute` + kaynak kapsamı |
| Audit | `METADATA_DISCOVERY_STARTED` / `METADATA_DISCOVERY_COMPLETED` (kaynak, kapsam, taranan nesne sayısı, sonuç) |
| API | `POST /data-sources/{id}/metadata-discoveries` |
| Ekran | Veri Kaynakları > Detay > Metadata; Katalog |
| Tablo | `metadata_discovery_results`(discovery_id, data_source_id, succeeded, scanned_object_count, changes, error_class, discovered_at) |
| Test | kısmi sonuç; zaman aşımı; artımlı mod; kota uyumu; audit |

###### D04.C01.W01.A02 — Keşif kapsamını yapılandır

| Alan | Değer |
|---|---|
| Amaç | Çok büyük kaynaklarda yalnız ilgili nesnelerin kataloglanmasını sağlamak |
| Aktör | Technical Data Steward |
| Tetikleyici | Kaynak detayından kapsam düzenleme |
| Ön koşul | Kaynak `ACTIVE` |
| Akış | **Temel:** dâhil/hariç örüntüleri gir → örüntüleri sına ve eşleşecek nesne sayısını göster → kaydet → audit. **Alternatif:** varsayılan kapsam kaynak tipine göre önerilir. **Hata:** hiçbir nesneyle eşleşmeyen kapsam → uyar |
| Durum geçişi | `—` |
| Yetki | `catalog.discovery.configure` + kaynak kapsamı |
| Audit | `DISCOVERY_SCOPE_CHANGED` (kaynak, örüntü özeti, eşleşen nesne sayısı) |
| API | `PUT /data-sources/{id}/discovery-scope` |
| Ekran | Veri Kaynakları > Detay > Metadata |
| Tablo | `discovery_scopes`(data_source_id, include_patterns, exclude_patterns, version) |
| Test | örüntü eşleştirme; boş kapsam uyarısı; önizleme sayımı; audit |

##### D04.C01.W02 — Keşif sonucu uzlaştırma

###### D04.C01.W02.A01 — Keşif farkını hesapla

| Alan | Değer |
|---|---|
| Amaç | Kataloğu körlemesine ezmek yerine, neyin eklendiğini/kaldırıldığını/değiştiğini görünür kılmak |
| Aktör | Sistem |
| Tetikleyici | Başarılı keşif tamamlanması |
| Ön koşul | Keşif `SUCCESS` veya `PARTIAL`; önceki katalog durumu mevcut |
| Akış | **Temel:** keşfedilen nesneleri kataloğa karşı karşılaştır → eklenen/kaldırılan/değişen listelerini üret → farkı kaydet. **Alternatif:** ilk keşifte tümü "eklenen" sayılır. **Hata:** `PARTIAL` keşifte kaldırma çıkarımı yapılmaz — eksik tarama silme sanılmaz |
| Durum geçişi | Fark `—` → `PENDING_REVIEW` \| `AUTO_APPLIED` |
| Yetki | Sistem aktörü |
| Audit | `METADATA_DIFF_COMPUTED` (kaynak, eklenen/kaldırılan/değişen sayıları) |
| API | `GET /metadata-discoveries/{id}/diff` |
| Ekran | Katalog > Değişiklikler |
| Tablo | `metadata_diffs`(diff_id, discovery_id, added, removed, changed, status) |
| Test | kısmi keşifte silme çıkarımının engellenmesi; ilk keşif; fark doğruluğu |

###### D04.C01.W02.A02 — Keşif farkını uygula

| Alan | Değer |
|---|---|
| Amaç | Katalog değişikliklerinin, etkisi bilinerek ve kontrollü biçimde yürürlüğe girmesini sağlamak |
| Aktör | Technical Data Steward; Sistem (politika izin veriyorsa) |
| Tetikleyici | Katalog değişiklik ekranından uygulama; veya otomatik uygulama politikası |
| Ön koşul | Fark `PENDING_REVIEW`; etkilenen kural listesi hesaplanmış |
| Akış | **Temel:** etkilenen kural/sözleşme listesini göster → onayla → dataset ve alanları güncelle → etkilenen kuralları `REVIEW_REQUIRED` yap → bildir → audit. **Alternatif:** yalnız ekleme içeren fark politikayla otomatik uygulanır. **Hata:** kaldırılan alan aktif kritik kuralda kullanılıyorsa → açık onay zorunlu |
| Durum geçişi | Fark `PENDING_REVIEW` → `APPLIED`; etkilenen kurallar `ACTIVE` → `REVIEW_REQUIRED` |
| Yetki | `catalog.diff.apply` + kaynak kapsamı |
| Audit | `METADATA_DIFF_APPLIED` (fark, uygulanan değişiklik sayısı, etkilenen kural sayısı) |
| API | `POST /metadata-diffs/{id}/application` |
| Ekran | Katalog > Değişiklikler |
| Tablo | `datasets`, `data_fields`(yazma); `quality_rules`(status) |
| Test | etkilenen kural tespiti; otomatik uygulama sınırı; kritik kural koruması; audit |

#### D04.C02 — Dataset yönetimi

##### D04.C02.W01 — Dataset yaşam döngüsü

###### D04.C02.W01.A01 — Dataset kaydını oluştur veya güncelle

| Alan | Değer |
|---|---|
| Amaç | Ölçüm yapılabilen her veri kümesinin katalogda tekil ve kararlı bir kimlikle temsil edilmesini sağlamak |
| Aktör | Sistem (keşiften); Technical Data Steward (manuel) |
| Tetikleyici | Keşif farkının uygulanması; manuel dataset tanımı |
| Ön koşul | Kaynak `ACTIVE`; ad üçlüsü (kaynak, ad alanı, ad) benzersiz |
| Akış | **Temel:** kimlik üçlüsünü çözümle → varsa güncelle, yoksa oluştur → tahmini satır sayısı ve tipini kaydet → audit. **Alternatif:** manuel dataset görünüm/sorgu tabanlı tanımlanır. **Hata:** ad çakışması → mevcut kaydı güncelle, mükerrer oluşturma |
| Durum geçişi | `—` → `ACTIVE` |
| Yetki | `catalog.dataset.manage` + kaynak kapsamı |
| Audit | `DATASET_UPSERTED` (dataset, kaynak, işlem tipi) |
| API | `PUT /datasets` (upsert); `GET /datasets` |
| Ekran | Katalog > Dataset Listesi |
| Tablo | `datasets`(dataset_id, data_source_id, namespace, name, dataset_type, criticality, owner_user_id, estimated_row_count, status) |
| Test | upsert idempotency; benzersizlik; manuel tanım; audit |

###### D04.C02.W01.A02 — Dataset'i arşivle

| Alan | Değer |
|---|---|
| Amaç | Kaynaktan kalkan dataset'i, geçmiş ölçüm kanıtını yok etmeden kullanımdan çıkarmak |
| Aktör | Technical Data Steward |
| Tetikleyici | Keşifte kaldırılan nesne; manuel arşivleme |
| Ön koşul | Bağlı `ACTIVE` kural yok veya birlikte arşivlenmek üzere onaylanmış |
| Akış | **Temel:** bağlı kural ve sözleşmeleri listele → onayla → `ARCHIVED` → bağlı kuralları `ARCHIVED` yap → bildir → audit. **Alternatif:** geçici kayboluş şüphesinde arşiv yerine `SUSPECTED_REMOVED` işaretlenir. **Hata:** aktif veri sözleşmesi varsa → reddet |
| Durum geçişi | `ACTIVE` → `SUSPECTED_REMOVED` → `ARCHIVED` |
| Yetki | `catalog.dataset.manage` + kaynak kapsamı |
| Audit | `DATASET_ARCHIVED` (dataset, arşivlenen kural sayısı, tetikleyen) |
| API | `POST /datasets/{id}/archival` |
| Ekran | Katalog > Dataset Detayı |
| Tablo | `datasets`(status); `quality_rules`(status) |
| Test | sözleşme koruması; ardışık arşivleme; geçici kayboluş yolu; audit |

##### D04.C02.W02 — Dataset kritikliği ve sahipliği

###### D04.C02.W02.A01 — Dataset kritikliğini belirle

| Alan | Değer |
|---|---|
| Amaç | Kalite bozulmasının iş etkisini önceliklendirmede kullanılabilir hâle getirmek |
| Aktör | Data Owner; Data Governance Admin |
| Tetikleyici | Katalog detayından kritiklik atama; periyodik gözden geçirme |
| Ön koşul | Dataset `ACTIVE`; kritiklik modeli politikada tanımlı |
| Akış | **Temel:** kritiklik seviyesi + gerekçe gir → model kriterlerine göre doğrula → kaydet → etkilenen SLA ve eşikleri yeniden çözümle → audit. **Alternatif:** kritiklik iş domaininden miras alınır. **Hata:** kritiklik modeli yoksa → hüküm üretilmez |
| Durum geçişi | `—` |
| Yetki | `catalog.dataset.classify` + dataset kapsamı |
| Audit | `DATASET_CRITICALITY_SET` (dataset, eski/yeni seviye, gerekçe, model sürümü) |
| API | `PUT /datasets/{id}/criticality` |
| Ekran | Katalog > Dataset Detayı |
| Tablo | `datasets`(criticality, criticality_reason, criticality_model_version) |
| Test | model yokluğunda fail-closed; miras alma; SLA yeniden çözümleme; audit |

#### D04.C03 — Alan (field) yönetimi

##### D04.C03.W01 — Alan yaşam döngüsü

###### D04.C03.W01.A01 — Alan kaydını oluştur veya güncelle

| Alan | Değer |
|---|---|
| Amaç | Kolon düzeyinde kural yazılabilmesi ve profil üretilebilmesi için alanların katalogda temsil edilmesi |
| Aktör | Sistem (keşiften); Technical Data Steward |
| Tetikleyici | Keşif farkının uygulanması |
| Ön koşul | Dataset `ACTIVE`; alan adı dataset içinde benzersiz |
| Akış | **Temel:** ad, yerel tip, boş geçilebilirlik ve sıra bilgisini çözümle → upsert → tip değişimini işaretle → audit. **Alternatif:** türetilmiş alanlar manuel tanımlanır. **Hata:** tip değişimi varsa → bağlı kuralları `REVIEW_REQUIRED` yap |
| Durum geçişi | `—` → `ACTIVE`; tip değişiminde bağlı kural `ACTIVE` → `REVIEW_REQUIRED` |
| Yetki | `catalog.field.manage` + dataset kapsamı |
| Audit | `DATA_FIELD_UPSERTED` (alan, eski/yeni tip, etkilenen kural sayısı) |
| API | `PUT /datasets/{id}/fields` |
| Ekran | Katalog > Dataset Detayı > Alanlar |
| Tablo | `data_fields`(data_field_id, dataset_id, name, native_data_type, is_nullable, ordinal, status) |
| Test | tip değişimi zinciri; benzersizlik; upsert; audit |

##### D04.C03.W02 — Alan sınıflandırması ve hassasiyet

###### D04.C03.W02.A01 — Alanı sınıflandır

| Alan | Değer |
|---|---|
| Amaç | Hangi verinin kanıtta, örnekte ve raporda açık gösterilebileceğini belirlemek |
| Aktör | Data Steward; Data Governance Admin |
| Tetikleyici | Katalog alan detayından sınıflandırma; otomatik sınıflandırma önerisi |
| Ön koşul | Alan `ACTIVE`; sınıflandırma politikası yürürlükte |
| Akış | **Temel:** sınıf + hassasiyet seç → politika sürümünü damgala → kaydet → maskeleme kurallarını yeniden çözümle → audit. **Alternatif:** ad ve profil örüntüsünden otomatik öneri sunulur, onay gerektirir. **Hata:** politika yoksa → sınıflandırma yapılamaz |
| Durum geçişi | `—` |
| Yetki | `catalog.field.classify` + dataset kapsamı |
| Audit | `DATA_FIELD_CLASSIFIED` (alan, eski/yeni sınıf, politika sürümü, otomatik mi) |
| API | `PUT /data-fields/{id}/classification` |
| Ekran | Katalog > Alan Detayı |
| Tablo | `data_fields`(classification, is_sensitive, classification_policy_version, classified_by) |
| Test | politika yokluğunda fail-closed; otomatik öneri onayı; maskeleme zinciri; audit |

###### D04.C03.W02.A02 — Sınıflandırılmamış hassas alan adaylarını tespit et

| Alan | Değer |
|---|---|
| Amaç | Hassas verinin sınıflandırılmadığı için kanıt ve raporlarda açığa çıkmasını önlemek |
| Aktör | Sistem |
| Tetikleyici | Profil tamamlanması; periyodik sınıflandırma taraması |
| Ön koşul | Profil metrikleri mevcut; tespit örüntüleri politikada tanımlı |
| Akış | **Temel:** ad ve değer örüntülerini politikayla eşleştir → aday listesi üret → steward'a bildir → audit. **Alternatif:** yüksek güvenli eşleşmelerde alan geçici olarak hassas kabul edilir. **Hata:** örüntü politikası yoksa → tarama yapılmaz |
| Durum geçişi | Alan geçici `is_sensitive=true` (yüksek güvende) |
| Yetki | Sistem aktörü; `catalog.classification.scan` |
| Audit | `SENSITIVE_CANDIDATE_DETECTED` (alan sayısı, güven seviyesi, politika sürümü) |
| API | `—` (zamanlanmış iş) |
| Ekran | Katalog > Sınıflandırma Boşlukları |
| Tablo | `classification_candidates`(data_field_id, matched_pattern, confidence, status) |
| Test | yanlış pozitif oranı; geçici hassas işaretleme; politika yokluğu; audit |

#### D04.C04 — Şema değişimi yönetimi

##### D04.C04.W01 — Şema farkı tespiti

###### D04.C04.W01.A01 — Şema değişikliğini sınıflandır

| Alan | Değer |
|---|---|
| Amaç | Her şema değişikliğini aynı ciddiyette ele almak yerine, kırıcı olanları ayırt etmek |
| Aktör | Sistem |
| Tetikleyici | Metadata farkının hesaplanması |
| Ön koşul | Fark hesaplanmış; sınıflandırma kuralları politikada tanımlı |
| Akış | **Temel:** her değişikliği `ADDITIVE` / `BREAKING` / `NEUTRAL` olarak sınıflandır → etkilenen kural, sözleşme ve raporları hesapla → kaydet. **Alternatif:** tip daralması ve boş geçilebilirlik sıkılaşması `BREAKING` sayılır. **Hata:** sınıflandırılamayan değişiklik → güvenli tarafta `BREAKING` kabul edilir |
| Durum geçişi | Değişiklik `—` → sınıf atanmış |
| Yetki | Sistem aktörü |
| Audit | `SCHEMA_CHANGE_CLASSIFIED` (kaynak, kırıcı sayısı, etkilenen varlık sayısı) |
| API | `GET /schema-changes` — filtre |
| Ekran | Katalog > Şema Değişiklikleri |
| Tablo | `schema_changes`(change_id, dataset_id, change_type, classification, impacted_rule_ids, detected_at) |
| Test | sınıflandırma doğruluğu; bilinmeyende güvenli taraf; etki hesabı |

##### D04.C04.W02 — Şema değişikliği kararı

###### D04.C04.W02.A01 — Şema değişikliğini kabul et veya blokla

| Alan | Değer |
|---|---|
| Amaç | Kırıcı şema değişikliğinin sessizce yanlış ölçüme dönüşmesini engellemek |
| Aktör | Data Owner; Technical Data Steward |
| Tetikleyici | Kırıcı şema değişikliği bildirimi |
| Ön koşul | Değişiklik `BREAKING` sınıfında ve karar bekliyor |
| Akış | **Temel:** etkilenen varlıkları incele → kabul et (kuralları güncelle) veya blokla (ölçümü durdur) → karar gerekçesi → audit → bildir. **Alternatif:** istisna talebiyle süreli kabul edilir. **Hata:** karar verilmezse politikadaki süre sonunda ölçüm otomatik bloklanır |
| Durum geçişi | Değişiklik `PENDING_DECISION` → `ACCEPTED` \| `BLOCKED` \| `AUTO_BLOCKED` |
| Yetki | `catalog.schema-change.decide` + dataset kapsamı |
| Audit | `SCHEMA_CHANGE_DECIDED` (değişiklik, karar, gerekçe, etkilenen kural sayısı) |
| API | `POST /schema-changes/{id}/decision` |
| Ekran | Katalog > Şema Değişiklikleri |
| Tablo | `schema_changes`(status, decided_by, decision_reason); `quality_rules`(status) |
| Test | otomatik bloklama; istisna yolu; kural durumu zinciri; audit |

#### D04.C05 — Katalog arama ve gezinme

##### D04.C05.W01 — Katalog arama

###### D04.C05.W01.A01 — Katalogda ara

| Alan | Değer |
|---|---|
| Amaç | Kullanıcının ilgilendiği veri varlığını ada, terime, sahibe veya domaine göre hızla bulmasını sağlamak |
| Aktör | Tüm okuma yetkili roller |
| Tetikleyici | Katalog arama kutusu |
| Ön koşul | Okuma kapsamı |
| Akış | **Temel:** arama terimini ad, açıklama, iş terimi ve etiketlerde ara → kapsamla filtrele → alaka sırasıyla döndür. **Alternatif:** kaynak, domain, sahip, kritiklik ve sınıflandırmaya göre yönlü filtreleme. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `catalog.read` + kapsam |
| Audit | Erişim kaydı: `CATALOG_SEARCHED` (sorgu özeti, sonuç sayısı) |
| API | `GET /catalog/search` — sayfalama, filtre, sıralama |
| Ekran | Katalog > Arama |
| Tablo | `datasets`, `data_fields`, `glossary_terms`(okuma) |
| Test | kapsam filtreleme; alaka sıralaması; sayfalama; erişim kaydı |

##### D04.C05.W02 — Varlık detay görünümü

###### D04.C05.W02.A01 — Varlık detayını görüntüle

| Alan | Değer |
|---|---|
| Amaç | Bir veri varlığı hakkındaki tüm yönetişim, kalite ve teknik bilgiyi tek yerde toplamak |
| Aktör | Tüm okuma yetkili roller |
| Tetikleyici | Katalogdan varlık seçimi |
| Ön koşul | Varlık üzerinde okuma kapsamı |
| Akış | **Temel:** teknik metadata, sahiplik, sınıflandırma, bağlı kurallar, güncel skor, açık sorunlar, son profil ve sözleşmeleri birleştirip döndür. **Alternatif:** hassas alanlar rolüne göre maskeli gösterilir. **Hata:** kapsam dışıysa → yetkisiz |
| Durum geçişi | `—` |
| Yetki | `catalog.read` + varlık kapsamı |
| Audit | Erişim kaydı: `CATALOG_ASSET_VIEWED` (varlık) |
| API | `GET /datasets/{id}` — birleşik görünüm |
| Ekran | Katalog > Dataset Detayı |
| Tablo | `datasets`, `data_fields`, `asset_ownerships`, `quality_rules`, `quality_scores`, `issues`(okuma) |
| Test | birleşik görünüm bütünlüğü; maskeleme; kapsam; erişim kaydı |

##### L5 — D04 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D04-001` | Dataset kimliği (kaynak, ad alanı, ad) üçlüsüyle tekildir ve yeniden keşifte kararlı kalır |
| `BR-D04-002` | Kısmi keşif sonucundan nesne kaldırma çıkarımı yapılmaz |
| `BR-D04-003` | Katalog değişiklikleri fark olarak hesaplanır; kataloğa doğrudan yazılmaz |
| `BR-D04-004` | Alan tipi değişen kural otomatik olarak `REVIEW_REQUIRED` durumuna geçer |
| `BR-D04-005` | Sınıflandırma politikası yürürlükte değilse alan sınıflandırılamaz |
| `BR-D04-006` | Sınıflandırılmamış alan, hassas kabul edilerek maskeli işlenir |
| `BR-D04-007` | Sınıflandırılamayan şema değişikliği `BREAKING` kabul edilir |
| `BR-D04-008` | Kırıcı şema değişikliğinde karar verilmezse ölçüm politikadaki süre sonunda bloklanır |
| `BR-D04-009` | Aktif veri sözleşmesi bulunan dataset arşivlenemez |
| `BR-D04-010` | Katalog okumaları kapsam dışı varlıkları sessizce filtreler |

---

### D05 — Profilleme ve Veri Karakterizasyonu

Kural yazılmadan önce verinin ne olduğunu anlamayı sağlayan katman. Profil hem
kural tasarımının girdisidir hem de kuralsız bozulma tespitinin (drift) temelidir.

#### D05.C01 — Profil çalıştırma

##### D05.C01.W01 — Profil talebi

###### D05.C01.W01.A01 — Profil çalıştırması talep et

| Alan | Değer |
|---|---|
| Amaç | Bir dataset'in belirli bir andaki istatistiksel karakterini ölçmek |
| Aktör | Data Steward; Technical Data Steward; Sistem (zamanlanmış) |
| Tetikleyici | Katalog ekranından profil talebi; zamanlanmış profil; ilk katalog girişi sonrası |
| Ön koşul | Dataset `ACTIVE`; kaynak sağlıklı; profil politikası yürürlükte |
| Akış | **Temel:** kapsam ve yöntem seç → politikayla sınırla → işi kuyruğa al → çalıştır → metrikleri kaydet. **Alternatif:** yalnız seçili alanlar profillenir. **Hata:** politika yoksa → talep reddedilir; kota aşımında iş ertelenir |
| Durum geçişi | Profil `—` → `QUEUED` → `RUNNING` → `SUCCESS` \| `PARTIAL` \| `TECHNICAL_ERROR` |
| Yetki | `profile.execute` + dataset kapsamı |
| Audit | `PROFILE_REQUESTED` (dataset, yöntem, kapsam, politika sürümü) |
| API | `POST /datasets/{id}/profiles` — idempotency anahtarı |
| Ekran | Katalog > Dataset Detayı; Profiller |
| Tablo | `data_profiles`(profile_id, dataset_id, method, sample_ratio, status, policy_version, started_at, finished_at) |
| Test | politika yokluğunda ret; idempotency; kısmi sonuç; kota uyumu; audit |

###### D05.C01.W01.A02 — Profil çalıştırmasını iptal et

| Alan | Değer |
|---|---|
| Amaç | Kaynağa beklenmedik yük bindiren uzun profil işini durdurabilmek |
| Aktör | Operations User; talebi açan kullanıcı |
| Tetikleyici | Profil listesinden iptal |
| Ön koşul | Profil `QUEUED` veya `RUNNING` |
| Akış | **Temel:** iptal işaretle → çalışan sorguyu sonlandır → `CANCELLED` → audit. **Alternatif:** kuyruktaki iş doğrudan kaldırılır. **Hata:** tamamlanmış profil → idempotent başarı |
| Durum geçişi | `QUEUED`\|`RUNNING` → `CANCEL_REQUESTED` → `CANCELLED` |
| Yetki | `profile.cancel` + dataset kapsamı veya talep sahipliği |
| Audit | `PROFILE_CANCELLED` (profil, iptal eden, aşama) |
| API | `POST /profiles/{id}/cancellation` |
| Ekran | Profiller > Liste |
| Tablo | `data_profiles`(status, cancelled_at, cancelled_by) |
| Test | çalışan sorgunun sonlandırılması; idempotency; durum-makinesi; audit |

##### D05.C01.W02 — Profil yöntemi ve örnekleme

###### D05.C01.W02.A01 — Profil yöntemini politikadan çözümle

| Alan | Değer |
|---|---|
| Amaç | Büyük dataset'lerde tam tarama yerine, güvenilirliği bilinen bir örnekleme kullanmak |
| Aktör | Sistem |
| Tetikleyici | Profil çalıştırmasının başlaması |
| Ön koşul | Profil politikası yürürlükte; dataset boyut tahmini mevcut |
| Akış | **Temel:** dataset boyutuna göre `FULL` / `SAMPLE` / `AGGREGATE` seç → örnekleme oranı ve tohumu belirle → deterministik olacak biçimde damgala. **Alternatif:** kullanıcı politika sınırları içinde yöntemi zorlayabilir. **Hata:** politika sınırı dışında yöntem → reddet |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | Profil kaydına gömülür: yöntem, oran, tohum, politika sürümü |
| API | `—` (iç servis) |
| Ekran | Profiller > Detay (yöntem gösterimi) |
| Tablo | `data_profiles`(method, sample_ratio, sample_seed, policy_version) |
| Test | boyut eşikleri; determinizm (aynı tohum → aynı örnek); politika sınırı zorlaması |

#### D05.C02 — Profil metrikleri

##### D05.C02.W01 — Temel metrik üretimi

###### D05.C02.W01.A01 — Alan düzeyi temel metrikleri hesapla

| Alan | Değer |
|---|---|
| Amaç | Tamlık, benzersizlik ve tip uygunluğu gibi temel kalite göstergelerini kuralsız olarak elde etmek |
| Aktör | Sistem |
| Tetikleyici | Profil çalıştırmasının yürütülmesi |
| Ön koşul | Bağlantı açık; alan listesi çözümlenmiş |
| Akış | **Temel:** her alan için satır sayısı, boş sayısı, farklı değer sayısı, min/maks ve tip uygunluk oranını hesapla → kaydet. **Alternatif:** örneklemede metrikler oran olarak işaretlenir. **Hata:** alan bazlı hata diğer alanları durdurmaz; profil `PARTIAL` olur |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | Profil tamamlanma kaydına dâhil |
| API | `GET /profiles/{id}` |
| Ekran | Profiller > Detay |
| Tablo | `data_profiles`(metrics); `profile_field_metrics`(profile_id, data_field_id, row_count, null_count, distinct_count, min_value, max_value) |
| Test | boş dataset; tümü boş alan; tip uyumsuzluğu; kısmi hata izolasyonu |

###### D05.C02.W01.A02 — Dataset düzeyi metrikleri hesapla

| Alan | Değer |
|---|---|
| Amaç | Hacim ve güncellik gibi dataset ölçeğindeki göstergeleri elde etmek |
| Aktör | Sistem |
| Tetikleyici | Profil çalıştırmasının yürütülmesi |
| Ön koşul | Güncellik alanı politikada tanımlıysa mevcut olmalı |
| Akış | **Temel:** toplam satır sayısı, tahmini boyut ve (tanımlıysa) en güncel zaman damgasını hesapla → kaydet. **Alternatif:** güncellik alanı yoksa güncellik metriği üretilmez, eksik işaretlenir. **Hata:** hacim okunamazsa `PARTIAL` |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | Profil tamamlanma kaydına dâhil |
| API | `GET /profiles/{id}` |
| Ekran | Profiller > Detay |
| Tablo | `data_profiles`(metrics: row_count, freshness_timestamp, size_estimate) |
| Test | güncellik alanı yokluğu; büyük hacim; kısmi sonuç |

##### D05.C02.W02 — Dağılım ve aykırı değer analizi

###### D05.C02.W02.A01 — Değer dağılımını çıkar

| Alan | Değer |
|---|---|
| Amaç | Verinin şeklini görerek anlamlı eşik ve kural tasarlanabilmesini sağlamak |
| Aktör | Sistem |
| Tetikleyici | Profil çalıştırmasında dağılım analizinin etkin olması |
| Ön koşul | Dağılım politikası yürürlükte; alan sınıflandırması bilinir |
| Akış | **Temel:** kategorik alanlarda en sık N değer, sayısal alanlarda çeyreklikler ve histogram üret → hassas alanlarda değerleri maskele → kaydet. **Alternatif:** yüksek kardinaliteli alanda yalnız özet üretilir. **Hata:** politika yoksa dağılım üretilmez |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `PROFILE_DISTRIBUTION_COMPUTED` (dataset, alan sayısı, maskelenen alan sayısı) |
| API | `GET /profiles/{id}/distributions` |
| Ekran | Profiller > Detay > Dağılım |
| Tablo | `profile_distributions`(profile_id, data_field_id, top_values, quantiles, histogram, masked) |
| Test | hassas alan maskeleme; yüksek kardinalite; politika yokluğu; determinizm |

###### D05.C02.W02.A02 — Aykırı değer adaylarını işaretle

| Alan | Değer |
|---|---|
| Amaç | Kural yazılmamış alanlarda bile beklenmedik değerleri görünür kılmak |
| Aktör | Sistem |
| Tetikleyici | Dağılım analizinin tamamlanması |
| Ön koşul | Sayısal veya tarih alanı; yeterli örnek büyüklüğü |
| Akış | **Temel:** politika yöntemine göre aykırı sınırlarını hesapla → sınır dışı değer sayısını ve maskeli örneklerini kaydet. **Alternatif:** yetersiz örnekte hüküm üretilmez. **Hata:** politika yoksa analiz yapılmaz |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `PROFILE_OUTLIERS_FLAGGED` (alan sayısı, aday sayısı, politika sürümü) |
| API | `GET /profiles/{id}/outliers` |
| Ekran | Profiller > Detay > Aykırı Değerler |
| Tablo | `profile_outliers`(profile_id, data_field_id, method, lower_bound, upper_bound, outlier_count) |
| Test | yetersiz örnekte hüküm üretmeme; maskeleme; yöntem determinizmi |

#### D05.C03 — Baseline yönetimi

##### D05.C03.W01 — Baseline belirleme ve onaylama

###### D05.C03.W01.A01 — Profili baseline olarak belirle

| Alan | Değer |
|---|---|
| Amaç | "Normal"in ne olduğunu açıkça sabitleyerek drift ölçümünü anlamlı kılmak |
| Aktör | Data Steward; Data Owner |
| Tetikleyici | Profil detayından baseline işaretleme |
| Ön koşul | Profil `SUCCESS`; profil kapsamı dataset'in tamamını temsil ediyor |
| Akış | **Temel:** profili seç → temsil yeterliliğini doğrula → önceki baseline'ı `SUPERSEDED` yap → yeni baseline `ACTIVE` → audit. **Alternatif:** dönemsel baseline (aylık/çeyreklik) ayrı etiketle tutulur. **Hata:** `PARTIAL` profil baseline olamaz |
| Durum geçişi | Baseline `—` → `ACTIVE`; önceki `ACTIVE` → `SUPERSEDED` |
| Yetki | `profile.baseline.manage` + dataset kapsamı |
| Audit | `PROFILE_BASELINE_SET` (dataset, profil, önceki baseline, gerekçe) |
| API | `POST /datasets/{id}/baselines` |
| Ekran | Profiller > Detay |
| Tablo | `profile_baselines`(baseline_id, dataset_id, profile_id, label, status, valid_from) |
| Test | kısmi profil reddi; temsil yeterliliği; devir zinciri; audit |

###### D05.C03.W01.A02 — Baseline'ı geçersiz kıl

| Alan | Değer |
|---|---|
| Amaç | Veri karakteri meşru biçimde değiştiğinde eski normale göre yanlış alarm üretilmesini durdurmak |
| Aktör | Data Steward; Data Owner |
| Tetikleyici | Kabul edilen iş değişikliği; şema değişikliği kabulü |
| Ön koşul | Baseline `ACTIVE` |
| Akış | **Temel:** gerekçe gir → baseline'ı `INVALIDATED` yap → yeni baseline talebi üret → drift hükümlerini durdur → audit. **Hata:** yeni baseline atanana kadar drift hükmü `NOT_QUALIFIED` üretilir |
| Durum geçişi | `ACTIVE` → `INVALIDATED` |
| Yetki | `profile.baseline.manage` + dataset kapsamı |
| Audit | `PROFILE_BASELINE_INVALIDATED` (dataset, baseline, gerekçe) |
| API | `POST /baselines/{id}/invalidation` |
| Ekran | Profiller > Baseline |
| Tablo | `profile_baselines`(status, invalidated_at, reason_code) |
| Test | drift hükmünün durması; yeni baseline talebi; durum-makinesi; audit |

#### D05.C04 — Drift tespiti

##### D05.C04.W01 — Profil karşılaştırma

###### D05.C04.W01.A01 — İki profili karşılaştır

| Alan | Değer |
|---|---|
| Amaç | Verinin karakterindeki değişimi ölçülebilir biçimde ortaya koymak |
| Aktör | Sistem; Data Steward (manuel karşılaştırma) |
| Tetikleyici | Yeni profil tamamlanması; manuel karşılaştırma talebi |
| Ön koşul | Her iki profil `SUCCESS`; aynı dataset; uyumlu kapsam ve yöntem |
| Akış | **Temel:** hacim, boş oranı, farklı değer oranı, kategori kümesi, sayısal özet ve güncellik farklarını hesapla → sonucu kaydet. **Alternatif:** kullanıcı iki profili elle seçer. **Hata:** kapsam/yöntem uyumsuzsa → karşılaştırma yapılmaz, `INCOMPARABLE` |
| Durum geçişi | Karşılaştırma `—` → `COMPUTED` \| `INCOMPARABLE` |
| Yetki | `profile.compare` + dataset kapsamı |
| Audit | `PROFILE_COMPARISON_COMPUTED` (dataset, baz/güncel profil, uyumluluk) |
| API | `POST /profile-comparisons` |
| Ekran | Profiller > Karşılaştırma |
| Tablo | `profile_comparisons`(comparison_id, dataset_id, baseline_profile_id, current_profile_id, result, status, policy_version) |
| Test | uyumsuz kapsamda ret; her metrik ailesi; determinizm; audit |

##### D05.C04.W02 — Drift hükmü ve sınıflandırma

###### D05.C04.W02.A01 — Drift hükmü üret

| Alan | Değer |
|---|---|
| Amaç | Farkın "gürültü" mü yoksa "bozulma" mı olduğuna politikaya dayalı ve tekrarlanabilir biçimde karar vermek |
| Aktör | Sistem |
| Tetikleyici | Profil karşılaştırmasının tamamlanması |
| Ön koşul | Karşılaştırma `COMPUTED`; drift politikası yürürlükte; asgari geçmiş sayısı sağlanmış |
| Akış | **Temel:** her drift ailesi için eşiği politikadan çöz → farkı eşikle karşılaştır → aile bazlı hüküm üret → genel hükmü belirle → kaydet. **Alternatif:** asgari geçmiş yoksa `NOT_QUALIFIED` üretilir. **Hata:** politika yoksa → hüküm üretilmez, fail-closed |
| Durum geçişi | Hüküm `—` → `NO_DRIFT` \| `DRIFT_SUSPECTED` \| `DRIFT_CONFIRMED` \| `NOT_QUALIFIED` |
| Yetki | Sistem aktörü |
| Audit | `DRIFT_JUDGMENT_ISSUED` (dataset, hüküm, tetikleyen aileler, politika sürümü) |
| API | `GET /profile-comparisons/{id}/drift` |
| Ekran | Profiller > Drift |
| Tablo | `drift_judgments`(judgment_id, comparison_id, verdict, triggered_families, policy_version) |
| Test | politika yokluğunda fail-closed; asgari geçmiş; her aile eşiği; determinizm |

###### D05.C04.W02.A02 — Drift hükmünden sorun üret

| Alan | Değer |
|---|---|
| Amaç | Doğrulanmış bozulmanın kaybolmadan bir sahibe ulaşmasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | `DRIFT_CONFIRMED` hükmü |
| Ön koşul | Dataset sahibi tanımlı; sorun üretim politikası yürürlükte |
| Akış | **Temel:** tekilleştirme anahtarı üret → açık sorun varsa yinelenme sayacını artır → yoksa yeni sorun aç → sahibe bildir → audit. **Alternatif:** kritikliğe göre öncelik belirlenir. **Hata:** sahip yoksa → yönetişim boşluğu uyarısı üretilir, sorun `UNASSIGNED` açılır |
| Durum geçişi | Sorun `—` → `NEW`; veya mevcut sorunda `occurrence_count` artışı |
| Yetki | Sistem aktörü |
| Audit | `ISSUE_CREATED_FROM_DRIFT` (dataset, hüküm, sorun, yinelenme mi) |
| API | `—` (iç akış) |
| Ekran | Sorunlar > Liste |
| Tablo | `issues`(source_event_type='DRIFT', deduplication_key_digest, occurrence_count) |
| Test | tekilleştirme; yinelenme sayacı; sahipsiz varlık yolu; audit |

##### L5 — D05 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D05-001` | Profil politikası yürürlükte değilse profil çalıştırılmaz |
| `BR-D05-002` | Örneklemeli profil deterministiktir; aynı tohum aynı örneği verir |
| `BR-D05-003` | Kısmi profil baseline olarak belirlenemez |
| `BR-D05-004` | Hassas alanların dağılım değerleri maskelenmeden saklanmaz ve gösterilmez |
| `BR-D05-005` | Sınıflandırılmamış alan hassas kabul edilerek maskelenir |
| `BR-D05-006` | Kapsam veya yöntem uyumsuz profiller karşılaştırılamaz |
| `BR-D05-007` | Drift politikası veya asgari geçmiş yoksa hüküm üretilmez |
| `BR-D05-008` | Baseline geçersiz kılındıktan sonra yeni baseline atanana kadar drift hükmü `NOT_QUALIFIED` olur |
| `BR-D05-009` | Profil kayıtları değişmezdir; düzeltme yeni profil çalıştırmasıyla yapılır |
| `BR-D05-010` | Alan bazlı profil hatası tüm profili başarısız kılmaz; sonuç `PARTIAL` olur |

---

### D06 — Kalite Kural Yönetimi

Kalite beklentisinin ölçülebilir bir nesneye dönüştüğü domain. Kuralın kendisi
değil, **onaylanmış ve değişmez sürümü** çalıştırılır; bu, sonuçların yeniden
üretilebilirliğinin temelidir.

#### D06.C01 — Kalite boyutu ve şablon kütüphanesi

##### D06.C01.W01 — Kalite boyutu yönetimi

###### D06.C01.W01.A01 — Kalite boyutunu tanımla ve ağırlıklandır

| Alan | Değer |
|---|---|
| Amaç | Kalitenin hangi eksenlerde ölçüldüğünü ve toplam skora nasıl katıldığını açık kılmak |
| Aktör | Data Governance Admin |
| Tetikleyici | Yönetişim ekranından boyut yapılandırması |
| Ön koşul | Skorlama politikası taslak durumunda |
| Akış | **Temel:** boyut kodu/ad/tanım/varsayılan ağırlık gir → ağırlık toplamını doğrula → politika taslağına ekle → onaya gönder. **Alternatif:** domaine özgü ağırlık geçersiz kılma tanımlanır. **Hata:** ağırlık toplamı geçersizse → reddet |
| Durum geçişi | Politika taslağı üzerinden |
| Yetki | `quality.dimension.manage` + kurum geneli scope |
| Audit | `QUALITY_DIMENSION_CONFIGURED` (boyut, ağırlık, kapsam) |
| API | `PUT /policies/{id}/quality-dimensions` |
| Ekran | Yönetişim > Kalite Boyutları |
| Tablo | `policies`(policy_type='SCORING', parameters.dimensions) |
| Test | ağırlık toplamı doğrulaması; domain geçersiz kılma; onay zinciri; audit |

##### D06.C01.W02 — Kural şablonu yaşam döngüsü

###### D06.C01.W02.A01 — Kural şablonu tanımla

| Alan | Değer |
|---|---|
| Amaç | Sık kullanılan kontrolleri her seferinde sıfırdan yazmadan, doğruluğu sınanmış biçimde kullanılabilir kılmak |
| Aktör | Data Governance Admin; Rule Author |
| Tetikleyici | Şablon kütüphanesinden yeni şablon |
| Ön koşul | Şablon kodu benzersiz; parametre şeması geçerli |
| Akış | **Temel:** kod/ad/boyut/parametre şeması/üretim mantığı gir → örnek veriyle olumlu-olumsuz sına → `DRAFT` kaydet → audit. **Alternatif:** mevcut şablondan türetilir. **Hata:** sınama başarısız → yayımlanamaz |
| Durum geçişi | `—` → `DRAFT` |
| Yetki | `rule.template.manage` + kurum geneli scope |
| Audit | `RULE_TEMPLATE_DRAFTED` (şablon, boyut, parametre sayısı) |
| API | `POST /rule-templates` |
| Ekran | Kurallar > Şablon Kütüphanesi |
| Tablo | `rule_templates`(template_id, code, name, dimension, parameter_schema, generation_spec, status, version) |
| Test | parametre şeması doğrulama; olumlu-olumsuz sınama; benzersizlik; audit |

###### D06.C01.W02.A02 — Kural şablonunu yayımla

| Alan | Değer |
|---|---|
| Amaç | Yalnız doğruluğu kanıtlanmış şablonların kural üretiminde kullanılmasını sağlamak |
| Aktör | Data Governance Admin (şablonu yazandan farklı) |
| Tetikleyici | Şablon detayından yayımlama |
| Ön koşul | Şablon `DRAFT`; sınama sonuçları başarılı; yayımlayan ≠ yazan |
| Akış | **Temel:** sınama kanıtını incele → `PUBLISHED` → kütüphanede kullanılabilir yap → audit. **Alternatif:** yeni sürüm eskisini geçersiz kılmaz, ikisi birlikte yaşar. **Hata:** görev ayrılığı ihlali → reddet |
| Durum geçişi | `DRAFT` → `PUBLISHED` |
| Yetki | `rule.template.publish` + kurum geneli scope; görev ayrılığı zorunlu |
| Audit | `RULE_TEMPLATE_PUBLISHED` (şablon, sürüm, yazan, yayımlayan) |
| API | `POST /rule-templates/{id}/publication` |
| Ekran | Kurallar > Şablon Kütüphanesi |
| Tablo | `rule_templates`(status, published_by, published_at) |
| Test | görev ayrılığı; sınama ön koşulu; çoklu sürüm; audit |

###### D06.C01.W02.A03 — Kural şablonunu kullanımdan kaldır

| Alan | Değer |
|---|---|
| Amaç | Hatalı veya eskimiş şablonun yeni kural üretiminde kullanılmasını durdurmak |
| Aktör | Data Governance Admin |
| Tetikleyici | Şablon hatası tespiti; halef şablon yayımlanması |
| Ön koşul | Şablon `PUBLISHED` |
| Akış | **Temel:** halef şablon (varsa) seç → `DEPRECATED` → şablonu kullanan aktif kuralları listele ve sahiplerine bildir → audit. **Alternatif:** kritik hata durumunda kurallar da `REVIEW_REQUIRED` yapılır. **Hata:** `—` |
| Durum geçişi | `PUBLISHED` → `DEPRECATED`; kritik hatada bağlı kurallar `ACTIVE` → `REVIEW_REQUIRED` |
| Yetki | `rule.template.manage` + kurum geneli scope |
| Audit | `RULE_TEMPLATE_DEPRECATED` (şablon, halef, etkilenen kural sayısı, kritik mi) |
| API | `POST /rule-templates/{id}/deprecation` |
| Ekran | Kurallar > Şablon Kütüphanesi |
| Tablo | `rule_templates`(status, superseded_by); `quality_rules`(status) |
| Test | etkilenen kural tespiti; kritik hata zinciri; bildirim; audit |

#### D06.C02 — Kural yaşam döngüsü ve onayı

##### D06.C02.W01 — Kural oluşturma

###### D06.C02.W01.A01 — Şablondan kural oluştur

| Alan | Değer |
|---|---|
| Amaç | Kalite beklentisini, sınanmış bir şablon üzerinden hızlı ve tutarlı biçimde tanımlamak |
| Aktör | Rule Author; Data Steward |
| Tetikleyici | Kurallar ekranından yeni kural |
| Ön koşul | Şablon `PUBLISHED`; hedef dataset/alan `ACTIVE`; aktörün dataset kapsamı var |
| Akış | **Temel:** şablon seç → parametreleri gir → tip ve kapsam uyumunu doğrula → kural + ilk sürüm `DRAFT` oluştur → audit. **Alternatif:** birden çok alana toplu kural üretilir. **Hata:** parametre tip uyumsuzluğu → alan bazlı hata; `DEPRECATED` şablon → reddet |
| Durum geçişi | Kural `—` → `DRAFT`; sürüm `—` → `DRAFT` |
| Yetki | `rule.create` + dataset kapsamı |
| Audit | `QUALITY_RULE_CREATED` (kural, şablon, dataset, boyut) |
| API | `POST /rules` |
| Ekran | Kurallar > Yeni Kural |
| Tablo | `quality_rules`(quality_rule_id, code, name, dataset_id, primary_dimension, owner_user_id, status); `rule_versions`(rule_version_id, version_no, definition, status) |
| Test | tip uyumu; deprecated şablon reddi; toplu üretim; kapsam yetkisi; audit |

###### D06.C02.W01.A02 — Özel sorgu tabanlı kural oluştur

| Alan | Değer |
|---|---|
| Amaç | Şablonların karşılamadığı karmaşık kontrolleri, güvenlik sınırları içinde tanımlayabilmek |
| Aktör | Rule Author (özel sorgu yetkisi olan) |
| Tetikleyici | Kurallar ekranından özel kural |
| Ön koşul | Aktörde özel sorgu yetkisi; hedef dataset kapsamda |
| Akış | **Temel:** sorgu metnini gir → yalnız okuma olduğunu ayrıştırıcıyla doğrula → sonuç eşlemesini tanımla → zaman aşımı belirle → `DRAFT` kaydet → audit. **Alternatif:** sorgu şablona dönüştürülmek üzere önerilir. **Hata:** veri değiştiren ifade, çoklu ifade veya yasaklı yapı → reddet |
| Durum geçişi | Kural `—` → `DRAFT` |
| Yetki | `rule.create.custom-query` + dataset kapsamı |
| Audit | `CUSTOM_QUERY_RULE_CREATED` (kural, sorgu özeti, reddedilen yapı varsa) |
| API | `POST /rules` (tip: özel sorgu) |
| Ekran | Kurallar > Yeni Kural > Özel Sorgu |
| Tablo | `rule_versions`(definition.query, definition.timeout, definition.result_mapping) |
| Test | veri değiştiren ifade reddi; çoklu ifade reddi; enjeksiyon denemeleri; zaman aşımı; audit |

##### D06.C02.W02 — Kural sürümü oluşturma

###### D06.C02.W02.A01 — Yeni kural sürümü oluştur

| Alan | Değer |
|---|---|
| Amaç | Kural değişikliğinin geçmiş sonuçları geriye dönük bozmamasını sağlamak |
| Aktör | Rule Author |
| Tetikleyici | Kural detayından sürüm oluşturma |
| Ön koşul | Kural `DRAFT`, `ACTIVE` veya `REVIEW_REQUIRED`; açık `DRAFT` sürüm bulunmamalı |
| Akış | **Temel:** mevcut sürümden kopyala → tanım, eşik, ağırlık ve kritikliği değiştir → sürüm numarasını artır → `DRAFT` kaydet → audit. **Alternatif:** yalnız eşik değişikliği "küçük sürüm" olarak işaretlenir. **Hata:** açık taslak sürüm varsa → reddet |
| Durum geçişi | Sürüm `—` → `DRAFT` |
| Yetki | `rule.version.create` + dataset kapsamı |
| Audit | `RULE_VERSION_CREATED` (kural, yeni sürüm no, temel sürüm, değişen alanlar) |
| API | `POST /rules/{id}/versions` |
| Ekran | Kurallar > Kural Detayı > Sürümler |
| Tablo | `rule_versions`(rule_version_id, quality_rule_id, version_no, definition, threshold, weight, criticality, status) |
| Test | tek açık taslak; sürüm numarası artışı; kopyalama doğruluğu; audit |

###### D06.C02.W02.A02 — Kural sürümünü değişmez kıl

| Alan | Değer |
|---|---|
| Amaç | Onaylanmış bir sürümün sonradan değiştirilerek geçmiş sonuçların anlamını bozmasını engellemek |
| Aktör | Sistem |
| Tetikleyici | Sürümün onaya gönderilmesi |
| Ön koşul | Sürüm `DRAFT` |
| Akış | **Temel:** tanımın özetini (digest) hesapla → sürümü değişmez işaretle → sonraki değişiklikler yeni sürüm gerektirir. **Hata:** değişmez sürüme yazma denemesi → reddet |
| Durum geçişi | Sürüm `DRAFT` → `SEALED` |
| Yetki | Sistem aktörü |
| Audit | Sürüm gönderim kaydına `definition_digest` olarak gömülür |
| API | `—` (iç akış) |
| Ekran | Kurallar > Sürüm Detayı (değişmez rozeti) |
| Tablo | `rule_versions`(definition_digest, sealed_at, status) |
| Test | değişmezlik zorlaması; özet kararlılığı; durum-makinesi |

##### D06.C02.W03 — Kural testi

###### D06.C02.W03.A01 — Kural sürümünü sınırlı veriyle test et

| Alan | Değer |
|---|---|
| Amaç | Kuralın gerçekten doğru şeyi ölçtüğünü, üretime çıkmadan ve kaynağı yormadan görmek |
| Aktör | Rule Author |
| Tetikleyici | Sürüm detayından test |
| Ön koşul | Sürüm `DRAFT` veya `SEALED`; kaynak sağlıklı; test kayıt sınırı politikada tanımlı |
| Akış | **Temel:** kayıt sınırıyla çalıştır → geçen/kalan sayıları ve önizleme skorunu üret → maskeli başarısız örnekleri göster → sonucu kaydet. **Alternatif:** sentetik veri kümesine karşı test edilir. **Hata:** zaman aşımı ve sorgu hatası `TECHNICAL_ERROR` olarak sınıflandırılır, kalite sonucu üretilmez |
| Durum geçişi | Test `—` → `SUCCESS` \| `TECHNICAL_ERROR` |
| Yetki | `rule.test.execute` + dataset kapsamı |
| Audit | `RULE_VERSION_TESTED` (sürüm, sonuç, kayıt sınırı, süre, hata sınıfı) |
| API | `POST /rule-versions/{id}/test` |
| Ekran | Kurallar > Sürüm Detayı > Test |
| Tablo | `rule_test_results`(rule_test_result_id, rule_version_id, status, record_limit, checked_count, passed_count, failed_count, preview_score, error_class) |
| Test | kayıt sınırı zorlaması; teknik hata ayrımı; maskeleme; zaman aşımı; audit |

###### D06.C02.W03.A02 — Test sonucunun resmî skora katılmadığını garanti et

| Alan | Değer |
|---|---|
| Amaç | Test amaçlı çalıştırmaların üretim skorunu kirletmesini engellemek |
| Aktör | Sistem |
| Tetikleyici | Test sonucunun kaydedilmesi |
| Ön koşul | Sonuç test bağlamında üretilmiş |
| Akış | **Temel:** sonucu `official_scoring_included=false` işaretle → skor toplulaştırmasından dışla. **Hata:** işaretsiz test sonucu bulunursa → skorlama fail-closed reddeder |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | Test kaydına gömülü |
| API | `—` |
| Ekran | Kurallar > Sürüm Detayı > Test (rozet) |
| Tablo | `rule_test_results`(official_score_included=false) |
| Test | toplulaştırmadan dışlama; işaretsiz kayıtta fail-closed |

##### D06.C02.W04 — Onay akışı

###### D06.C02.W04.A01 — Kural sürümünü onaya gönder

| Alan | Değer |
|---|---|
| Amaç | Üretim ölçümüne girecek kuralın bağımsız bir gözden geçirmeden geçmesini sağlamak |
| Aktör | Rule Author (maker) |
| Tetikleyici | Sürüm detayından onaya gönderme |
| Ön koşul | Sürüm `SEALED`; başarılı test sonucu mevcut ve güncel; açık onay talebi yok |
| Akış | **Temel:** talep aç → sürümü `PENDING_APPROVAL` yap → onaylayıcı havuzunu çözümle → bildir → audit. **Alternatif:** kritik kurallarda iki onaylayıcı istenir. **Hata:** test yoksa veya bayatsa → reddet; açık talep varsa → reddet |
| Durum geçişi | Sürüm `SEALED` → `PENDING_APPROVAL`; talep `—` → `PENDING` |
| Yetki | `rule.approval.request` + dataset kapsamı |
| Audit | `RULE_APPROVAL_REQUESTED` (sürüm, maker, test referansı, politika sürümü) |
| API | `POST /rule-versions/{id}/approval-requests` |
| Ekran | Kurallar > Sürüm Detayı |
| Tablo | `rule_approval_requests`(approval_request_id, rule_version_id, maker_actor_id, status, requested_at, expires_at) |
| Test | test ön koşulu; bayat test; mükerrer talep; durum-makinesi; audit |

###### D06.C02.W04.A02 — Onay kararı ver

| Alan | Değer |
|---|---|
| Amaç | Görev ayrılığı altında kural sürümünün üretime çıkışını yetkilendirmek |
| Aktör | Rule Approver (checker) — maker'dan farklı olmak zorunda |
| Tetikleyici | Onay kuyruğundan karar |
| Ön koşul | Talep `PENDING`; checker ≠ maker; checker dataset kapsamında yetkili |
| Akış | **Temel:** tanım, test kanıtı ve etkiyi incele → karar + gerekçe → geçiş → audit → bildir. **Alternatif:** red gerekçe kodu zorunlu, sürüm `DRAFT`a döner. **Hata:** maker=checker → reddet; eşzamanlı karar → sürüm çakışması |
| Durum geçişi | Talep `PENDING` → `APPROVED` \| `REJECTED`; sürüm `PENDING_APPROVAL` → `APPROVED` \| `DRAFT` |
| Yetki | `rule.approval.decide` + dataset kapsamı; görev ayrılığı zorunlu |
| Audit | `RULE_APPROVAL_DECIDED` (karar, gerekçe kodu, maker, checker, politika sürümü) |
| API | `POST /rule-approvals/{id}/decision` — `If-Match` |
| Ekran | Onay Kuyruğu; Kurallar > Sürüm Detayı |
| Tablo | `rule_approval_requests`(status, checker_actor_id, decided_at, reason_code, version) |
| Test | görev ayrılığı; eşzamanlı karar; durum-makinesi; audit atomikliği |

###### D06.C02.W04.A03 — Onay talebini geri çek

| Alan | Değer |
|---|---|
| Amaç | Yanlış gönderilmiş talebin onaylayıcıyı meşgul etmesini önlemek |
| Aktör | Rule Author (talebi açan) |
| Tetikleyici | Sürüm detayından geri çekme |
| Ön koşul | Talep `PENDING`; geri çeken = maker |
| Akış | **Temel:** gerekçe gir → talep `WITHDRAWN` → sürüm `DRAFT`a döner → audit. **Hata:** karar verilmiş talep → reddet |
| Durum geçişi | Talep `PENDING` → `WITHDRAWN`; sürüm `PENDING_APPROVAL` → `DRAFT` |
| Yetki | `rule.approval.request` + talep sahipliği |
| Audit | `RULE_APPROVAL_WITHDRAWN` (talep, gerekçe, maker) |
| API | `POST /rule-approvals/{id}/withdrawal` |
| Ekran | Kurallar > Sürüm Detayı |
| Tablo | `rule_approval_requests`(status, withdrawn_at) |
| Test | sahiplik kontrolü; karar sonrası ret; durum-makinesi; audit |

###### D06.C02.W04.A04 — Süresi geçen onay talebini kapat

| Alan | Değer |
|---|---|
| Amaç | Karara bağlanmayan taleplerin süresiz açık kalmasını engellemek |
| Aktör | Sistem |
| Tetikleyici | Onay süresi aşım zamanlayıcısı |
| Ön koşul | Talep `PENDING`; son karar tarihi geçmiş |
| Akış | **Temel:** süresi geçen talepleri bul → `EXPIRED` yap → sürümü `DRAFT`a döndür → maker'a bildir → audit. **Hata:** aynı anda karar veriliyorsa → karar önceliklidir |
| Durum geçişi | Talep `PENDING` → `EXPIRED`; sürüm `PENDING_APPROVAL` → `DRAFT` |
| Yetki | Sistem aktörü; `rule.approval.expire` |
| Audit | `RULE_APPROVAL_EXPIRED` (talep, süre, politika sürümü) |
| API | `—` (zamanlanmış iş) |
| Ekran | Onay Kuyruğu (süresi geçen görünümü) |
| Tablo | `rule_approval_requests`(status, expires_at) |
| Test | karar-süre aşımı yarışı; toplu işlem; bildirim; audit |

##### D06.C02.W05 — Aktivasyon ve pasifleştirme

###### D06.C02.W05.A01 — Kural sürümünü aktive et

| Alan | Değer |
|---|---|
| Amaç | Onaylanmış sürümün resmî ölçüme dâhil olmasını sağlamak |
| Aktör | Data Steward; Rule Author |
| Tetikleyici | Sürüm detayından aktivasyon; onay sonrası otomatik aktivasyon politikası |
| Ön koşul | Sürüm `APPROVED`; hedef dataset `ACTIVE`; kaynak `ACTIVE` |
| Akış | **Temel:** önceki aktif sürümü `SUPERSEDED` yap → yeniyi `ACTIVE` yap → kuralı `ACTIVE` yap → zamanlamalara dâhil et → audit. **Alternatif:** ileri tarihli aktivasyon zamanlanır. **Hata:** dataset pasifse → reddet |
| Durum geçişi | Sürüm `APPROVED` → `ACTIVE`; önceki `ACTIVE` → `SUPERSEDED`; kural → `ACTIVE` |
| Yetki | `rule.activate` + dataset kapsamı |
| Audit | `RULE_VERSION_ACTIVATED` (kural, sürüm, önceki sürüm, yürürlük zamanı) |
| API | `POST /rule-versions/{id}/activation` |
| Ekran | Kurallar > Sürüm Detayı |
| Tablo | `rule_versions`(status, activated_at); `quality_rules`(status, active_version_id) |
| Test | tek aktif sürüm kısıtı; ileri tarihli aktivasyon; durum-makinesi; audit |

###### D06.C02.W05.A02 — Kuralı pasifleştir

| Alan | Değer |
|---|---|
| Amaç | Yanlış alarm üreten veya geçici olarak geçersiz kuralı ölçümden çıkarmak |
| Aktör | Data Steward; Data Owner |
| Tetikleyici | Kural detayından pasifleştirme; yüksek yanlış alarm oranı uyarısı |
| Ön koşul | Kural `ACTIVE` |
| Akış | **Temel:** gerekçe ve süre gir → `PASSIVE` yap → zamanlamalardan çıkar → skor kapsamındaki değişikliği işaretle → bildir → audit. **Alternatif:** süreli pasifleştirme sonunda otomatik yeniden aktive edilir. **Hata:** kritik kural pasifleştirmede ek onay istenir |
| Durum geçişi | Kural `ACTIVE` → `PASSIVE` |
| Yetki | `rule.deactivate` + dataset kapsamı; kritik kuralda görev ayrılığı |
| Audit | `QUALITY_RULE_DEACTIVATED` (kural, gerekçe, süre, kritik mi) |
| API | `POST /rules/{id}/deactivation` |
| Ekran | Kurallar > Kural Detayı |
| Tablo | `quality_rules`(status, deactivated_until, reason_code) |
| Test | kritik kural ek onayı; süreli pasifleştirme; skor kapsamı etkisi; audit |

##### D06.C02.W06 — Arşivleme

###### D06.C02.W06.A01 — Kuralı arşivle

| Alan | Değer |
|---|---|
| Amaç | Kullanımdan kalkan kuralı, geçmiş sonuç ve skor kanıtını koruyarak listeden çıkarmak |
| Aktör | Data Owner |
| Tetikleyici | Kural detayından arşivleme; dataset arşivlenmesi |
| Ön koşul | Kural `PASSIVE`; açık sorun bulunmamalı |
| Akış | **Temel:** bağımlılık kontrolü → `ARCHIVED` → geçmiş sürüm ve sonuçlar korunur → audit. **Hata:** açık sorun varsa → reddet |
| Durum geçişi | Kural `PASSIVE` → `ARCHIVED` |
| Yetki | `rule.archive` + dataset kapsamı |
| Audit | `QUALITY_RULE_ARCHIVED` (kural, sürüm sayısı) |
| API | `POST /rules/{id}/archival` |
| Ekran | Kurallar > Kural Detayı |
| Tablo | `quality_rules`(status, archived_at) |
| Test | açık sorun reddi; geçmiş korunumu; durum-makinesi; audit |

#### D06.C03 — Kural kapsamı ve parametreleri

##### D06.C03.W01 — Kapsam tanımlama

###### D06.C03.W01.A01 — Kural kapsamını tanımla

| Alan | Değer |
|---|---|
| Amaç | Kuralın hangi veri kümesine, hangi filtre altında uygulanacağını kesin belirlemek |
| Aktör | Rule Author |
| Tetikleyici | Kural veya sürüm oluşturma sırasında |
| Ön koşul | Hedef varlıklar `ACTIVE` ve aktörün kapsamında |
| Akış | **Temel:** kapsam tipini (alan, dataset, dataset'ler arası, kaynak) seç → hedefleri belirle → filtre koşulu gir → referans geçerliliğini doğrula → kaydet. **Alternatif:** dinamik kapsam etiketle tanımlanır. **Hata:** geçersiz nesne referansı → reddet; kaynaklar arası erişim kapsamı yoksa → reddet |
| Durum geçişi | `—` |
| Yetki | `rule.version.create` + tüm hedeflerin kapsamı |
| Audit | Sürüm kaydına gömülü: kapsam tipi, hedefler, filtre özeti |
| API | Sürüm oluşturma gövdesinin parçası |
| Ekran | Kurallar > Sürüm Düzenleme > Kapsam |
| Tablo | `rule_versions`(definition.scope_type, definition.target_refs, definition.filter) |
| Test | geçersiz referans; kaynaklar arası kapsam yetkisi; filtre ayrıştırma; dinamik kapsam |

##### D06.C03.W02 — Eşik ve ağırlık yönetimi

###### D06.C03.W02.A01 — Kural eşiğini ve ağırlığını belirle

| Alan | Değer |
|---|---|
| Amaç | Kuralın ne zaman "başarısız" sayılacağını ve skora ne kadar etki edeceğini açık kılmak |
| Aktör | Rule Author; Data Owner |
| Tetikleyici | Sürüm oluşturma; eşik ayarlama |
| Ön koşul | Profil verisi mevcut (eşik önerisi için) |
| Akış | **Temel:** eşik tipi (mutlak/oransal) ve değer gir → profil dağılımına göre öneri göster → ağırlık ve kritiklik ata → doğrula → kaydet. **Alternatif:** eşik geçmiş sonuçlardan otomatik önerilir, onay gerektirir. **Hata:** politika sınırları dışında ağırlık → reddet |
| Durum geçişi | `—` |
| Yetki | `rule.version.create` + dataset kapsamı |
| Audit | Sürüm kaydına gömülü: eşik, ağırlık, kritiklik, öneri kullanıldı mı |
| API | Sürüm oluşturma gövdesinin parçası |
| Ekran | Kurallar > Sürüm Düzenleme > Eşik |
| Tablo | `rule_versions`(threshold, threshold_type, weight, criticality) |
| Test | politika sınırı; öneri hesabı; kritiklik etkisi; audit |

#### D06.C04 — Kural bağımlılıkları ve çakışma

##### D06.C04.W01 — Bağımlılık çözümleme

###### D06.C04.W01.A01 — Kural bağımlılık grafiğini çıkar

| Alan | Değer |
|---|---|
| Amaç | Bir kuralın hangi veri varlıklarına ve diğer kurallara bağlı olduğunu görünür kılmak |
| Aktör | Sistem; Rule Author (görüntüleme) |
| Tetikleyici | Sürüm kaydedilmesi; kural detayı açılışı |
| Ön koşul | Kapsam tanımlı |
| Akış | **Temel:** kapsam referanslarından dataset/alan bağımlılıklarını çıkar → önkoşul kuralları çözümle → grafı kaydet. **Alternatif:** dairesel bağımlılık tespit edilirse işaretlenir. **Hata:** dairesel bağımlılık → sürüm kaydedilemez |
| Durum geçişi | `—` |
| Yetki | `rule.read` + dataset kapsamı |
| Audit | Erişim kaydı: `RULE_DEPENDENCY_VIEWED` (kural) |
| API | `GET /rules/{id}/dependencies` |
| Ekran | Kurallar > Kural Detayı > Bağımlılıklar |
| Tablo | `rule_dependencies`(rule_version_id, depends_on_type, depends_on_id) |
| Test | dairesel bağımlılık reddi; graf doğruluğu; erişim kaydı |

##### D06.C04.W02 — Çakışma ve mükerrerlik tespiti

###### D06.C04.W02.A01 — Mükerrer veya çelişen kuralları tespit et

| Alan | Değer |
|---|---|
| Amaç | Aynı kontrolün birden çok kez sayılarak skoru çarpıtmasını ve çelişkili kuralların kafa karıştırmasını önlemek |
| Aktör | Sistem |
| Tetikleyici | Sürüm kaydedilmesi; periyodik kural sağlığı taraması |
| Ön koşul | Aynı dataset üzerinde başka aktif kural bulunması |
| Akış | **Temel:** kapsam ve tanım özetlerini karşılaştır → örtüşen/çelişen adayları listele → yazara uyarı göster → kaydet. **Alternatif:** yüksek benzerlikte birleştirme önerilir. **Hata:** birebir aynı kural → kaydetme reddedilir |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `RULE_CONFLICT_DETECTED` (kural, çakışan kurallar, benzerlik) |
| API | `GET /rules/{id}/conflicts` |
| Ekran | Kurallar > Kural Detayı > Çakışmalar |
| Tablo | `rule_conflicts`(rule_version_id, conflicting_version_id, conflict_type, similarity) |
| Test | birebir mükerrer reddi; kısmi örtüşme; çelişki tespiti; audit |

#### D06.C05 — Gölge (shadow) yürütme

##### D06.C05.W01 — Gölge mod yaşam döngüsü

###### D06.C05.W01.A01 — Kural sürümünü gölge modda çalıştır

| Alan | Değer |
|---|---|
| Amaç | Yeni veya değiştirilmiş kuralın gerçek veri üzerindeki davranışını, skoru etkilemeden gözlemlemek |
| Aktör | Rule Author; Data Steward |
| Tetikleyici | Sürüm detayından gölge mod başlatma |
| Ön koşul | Sürüm `APPROVED` veya `SEALED`; gölge mod politikası izin veriyor |
| Akış | **Temel:** gölge modda çalıştırma planla → sonuçları `SHADOW` işaretiyle üret → resmî skor ve sorun akışından dışla → karşılaştırma raporu üret. **Alternatif:** gölge süresi sonunda otomatik sonlanır. **Hata:** gölge sonucu resmî olarak işaretlenirse → skorlama fail-closed reddeder |
| Durum geçişi | Çalıştırma modu `SHADOW`; kural durumu değişmez |
| Yetki | `rule.shadow.execute` + dataset kapsamı |
| Audit | `SHADOW_EXECUTION_STARTED` (sürüm, süre, kapsam) |
| API | `POST /rule-versions/{id}/shadow-runs` |
| Ekran | Kurallar > Sürüm Detayı > Gölge |
| Tablo | `rule_executions`(execution_mode='SHADOW'); `rule_execution_results`(eligible_for_official_scoring=false) |
| Test | skordan dışlama; sorun üretmeme; süre sonu; fail-closed işaretleme |

###### D06.C05.W01.A02 — Gölge ile resmî sonucu karşılaştır

| Alan | Değer |
|---|---|
| Amaç | Kural değişikliğinin etkisini, üretime alınmadan sayısal olarak görmek |
| Aktör | Rule Author; Data Steward |
| Tetikleyici | Gölge çalıştırma dönemi sonu |
| Ön koşul | Aynı kapsamda hem gölge hem resmî sonuç bulunması |
| Akış | **Temel:** başarısız kayıt sayısı, oran ve önizleme skor farkını hesapla → yanlış alarm tahminini üret → raporu göster. **Alternatif:** kapsam farklıysa karşılaştırma yapılmaz. **Hata:** resmî sonuç yoksa → karşılaştırma `INCOMPARABLE` |
| Durum geçişi | `—` |
| Yetki | `rule.shadow.read` + dataset kapsamı |
| Audit | Erişim kaydı: `SHADOW_COMPARISON_VIEWED` (sürüm) |
| API | `GET /rule-versions/{id}/shadow-comparison` |
| Ekran | Kurallar > Sürüm Detayı > Gölge |
| Tablo | `rule_execution_results`(okuma) |
| Test | kapsam uyumsuzluğu; fark hesabı; erişim kaydı |

##### L5 — D06 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D06-001` | Yalnız `PUBLISHED` şablonlardan kural üretilir |
| `BR-D06-002` | Özel sorgu kuralları yalnız salt okunur ifade içerebilir; veri değiştiren yapı reddedilir |
| `BR-D06-003` | Onaya gönderilen kural sürümü değişmez hâle gelir; değişiklik yeni sürüm gerektirir |
| `BR-D06-004` | Bir kuralın aynı anda yalnız bir `DRAFT` ve bir `ACTIVE` sürümü bulunur |
| `BR-D06-005` | Onay öncesi güncel ve başarılı bir test sonucu zorunludur |
| `BR-D06-006` | Onay talebini açan aktör, aynı talebi onaylayamaz |
| `BR-D06-007` | Kritik kurallarda onay için ikinci bir onaylayıcı istenir |
| `BR-D06-008` | Test ve gölge sonuçları resmî skor toplulaştırmasına dâhil edilmez |
| `BR-D06-009` | Resmî işaretlenmemiş sonuç skorlamaya girerse skorlama fail-closed reddeder |
| `BR-D06-010` | Dairesel kural bağımlılığı oluşturulamaz |
| `BR-D06-011` | Birebir aynı kapsam ve tanıma sahip ikinci kural kaydedilemez |
| `BR-D06-012` | Bağlı şablon veya alan tipi değişen kural `REVIEW_REQUIRED` durumuna geçer |
| `BR-D06-013` | Kritik kuralın pasifleştirilmesi görev ayrılığı gerektirir |
| `BR-D06-014` | Açık sorunu bulunan kural arşivlenemez |
| `BR-D06-015` | Her sonuç, üretildiği kural sürümünün özetini (digest) taşır |

---

### D07 — Yürütme, Zamanlama ve İş Kuyruğu

Kuralların gerçekten çalıştığı, kaynak yükünün yönetildiği ve teknik hataların
kalite sonucundan ayrıldığı domain. Buradaki dayanıklılık mekanizmaları
(kalıcı kuyruk, lease, heartbeat, dead-letter) ölçümün sürekliliğinin temelidir.

#### D07.C01 — Çalıştırma orkestrasyonu

##### D07.C01.W01 — Manuel çalıştırma

###### D07.C01.W01.A01 — Manuel çalıştırma başlat

| Alan | Değer |
|---|---|
| Amaç | Kullanıcının zamanlamayı beklemeden, seçtiği kapsamda ölçüm başlatabilmesini sağlamak |
| Aktör | Data Steward; Operations User |
| Tetikleyici | Çalıştırma ekranından başlatma |
| Ön koşul | Seçilen kural sürümleri `ACTIVE`; kaynak `ACTIVE` ve sağlıklı; kullanım politikası yürürlükte |
| Akış | **Temel:** kapsam ve kural seç → idempotency anahtarı üret → çalıştırma kaydı aç → planı üret → işleri kuyruğa al → `QUEUED` → audit. **Alternatif:** aynı anahtarla tekrar istek mevcut çalıştırmayı döndürür. **Hata:** kaynak pasif veya politika yoksa → reddet; kural yoksa → boş kapsam hatası |
| Durum geçişi | Çalıştırma `—` → `QUEUED` |
| Yetki | `execution.start` + dataset ve kaynak kapsamı |
| Audit | `EXECUTION_STARTED` (çalıştırma, tetikleyici tipi, kural sürüm sayısı, kapsam, idempotency anahtarı) |
| API | `POST /executions` — idempotency anahtarı zorunlu |
| Ekran | Çalıştırmalar > Yeni Çalıştırma |
| Tablo | `rule_executions`(execution_id, execution_type, status, idempotency_key_hash, rule_version_ids, scope, triggered_by, correlation_id, workload_class) |
| Test | idempotency; boş kapsam; politika yokluğunda ret; kapsam yetkisi; audit |

###### D07.C01.W01.A02 — Çalıştırma listesini ve durumunu görüntüle

| Alan | Değer |
|---|---|
| Amaç | Ölçümlerin ilerleyişini ve sonucunu takip edebilmek |
| Aktör | Data Steward; Operations User; Data Owner |
| Tetikleyici | Çalıştırmalar ekranı açılışı; otomatik yenileme |
| Ön koşul | Kapsam içinde çalıştırma bulunması |
| Akış | **Temel:** kapsamla filtrelenmiş çalıştırmaları durum, süre, tetikleyici ve sonuç özetiyle listele → sayfala. **Alternatif:** duruma, kaynağa ve tarihe göre filtrelenir. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `execution.read` + kaynak/dataset kapsamı |
| Audit | Erişim kaydı: `EXECUTION_LIST_VIEWED` (filtre, sonuç sayısı) |
| API | `GET /executions` — sayfalama, filtre, sıralama |
| Ekran | Çalıştırmalar > Liste |
| Tablo | `rule_executions`, `rule_execution_results`(okuma) |
| Test | kapsam filtreleme; sayfalama; sıralama; erişim kaydı |

###### D07.C01.W01.A03 — Çalıştırma detayını ve ilerlemesini görüntüle

| Alan | Değer |
|---|---|
| Amaç | Uzun süren çalıştırmalarda nerede olunduğunu ve hangi kuralın ne sonuç verdiğini görmek |
| Aktör | Data Steward; Operations User |
| Tetikleyici | Listeden çalıştırma seçimi |
| Ön koşul | Çalıştırma üzerinde okuma kapsamı |
| Akış | **Temel:** kural bazlı sonuçları, tamamlanan bölüm oranını, deneme geçmişini ve hata sınıflarını birleştirip döndür. **Alternatif:** devam eden çalıştırmada canlı ilerleme gösterilir. **Hata:** kapsam dışıysa → yetkisiz |
| Durum geçişi | `—` |
| Yetki | `execution.read` + kapsam |
| Audit | Erişim kaydı: `EXECUTION_DETAIL_VIEWED` (çalıştırma) |
| API | `GET /executions/{id}` |
| Ekran | Çalıştırmalar > Detay |
| Tablo | `rule_executions`, `rule_execution_results`, `execution_attempts`(okuma) |
| Test | canlı ilerleme; kapsam; birleşik görünüm; erişim kaydı |

##### D07.C01.W02 — Çalıştırma planı üretimi

###### D07.C01.W02.A01 — Çalıştırma planını üret

| Alan | Değer |
|---|---|
| Amaç | Kuralları gelişigüzel değil, bağımlılık ve kaynak kısıtlarını gözeten bir sırayla çalıştırmak |
| Aktör | Sistem |
| Tetikleyici | Çalıştırma kaydının açılması |
| Ön koşul | Kural sürümleri çözümlenmiş; kaynak politikası okunmuş |
| Akış | **Temel:** kuralları kaynağa ve dataset'e göre grupla → bağımlılık sırasını çöz → eşzamanlılık sınırına göre parçala → iş birimlerini üret. **Alternatif:** tek dataset'e ait kurallar tek sorguda birleştirilir. **Hata:** dairesel bağımlılık → çalıştırma `TECHNICAL_ERROR` ile açılmadan sonlanır |
| Durum geçişi | Çalıştırma `QUEUED` (planlı) |
| Yetki | Sistem aktörü |
| Audit | `EXECUTION_PLAN_BUILT` (çalıştırma, iş birimi sayısı, gruplama stratejisi) |
| API | `—` (iç servis) |
| Ekran | Çalıştırmalar > Detay > Plan |
| Tablo | `persistent_jobs`(job_type='EXECUTION', payload) |
| Test | bağımlılık sırası; sorgu birleştirme; eşzamanlılık parçalama; dairesel bağımlılık |

###### D07.C01.W02.A02 — İş yükü sınıfını belirle

| Alan | Değer |
|---|---|
| Amaç | Ağır çalıştırmaların hafif olanları kuyrukta bloke etmesini engellemek |
| Aktör | Sistem |
| Tetikleyici | Plan üretimi |
| Ön koşul | Dataset boyut tahmini ve kural tipleri bilinir |
| Akış | **Temel:** tahmini veri hacmi ve kural karmaşıklığından `LIGHT` / `HEAVY` sınıfını belirle → işleri sınıfa göre etiketle. **Alternatif:** kullanıcı politika sınırları içinde sınıfı zorlayabilir. **Hata:** tahmin yoksa güvenli tarafta `HEAVY` kabul edilir |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | Çalıştırma kaydına gömülü: `workload_class` |
| API | `—` |
| Ekran | Çalıştırmalar > Detay |
| Tablo | `rule_executions`(workload_class); `persistent_jobs`(priority) |
| Test | sınıflandırma eşikleri; bilinmeyende güvenli taraf; kuyruk ayrımı |

##### D07.C01.W03 — Çalıştırma iptali

###### D07.C01.W03.A01 — Çalıştırma iptali talep et

| Alan | Değer |
|---|---|
| Amaç | Yanlış başlatılmış veya kaynağı aşırı yoran ölçümü durdurabilmek |
| Aktör | Operations User; çalıştırmayı başlatan kullanıcı |
| Tetikleyici | Çalıştırma detayından iptal |
| Ön koşul | Çalıştırma `QUEUED` veya `RUNNING` |
| Akış | **Temel:** iptal gerekçesi gir → `CANCEL_REQUESTED` işaretle → bekleyen işleri kuyruktan çıkar → çalışan işlere iptal sinyali gönder → audit. **Alternatif:** yalnız kuyruktaysa doğrudan `CANCELLED`. **Hata:** tamamlanmış çalıştırma → idempotent başarı |
| Durum geçişi | `QUEUED`\|`RUNNING` → `CANCEL_REQUESTED` |
| Yetki | `execution.cancel` + kapsam veya başlatma sahipliği |
| Audit | `EXECUTION_CANCEL_REQUESTED` (çalıştırma, gerekçe, iptal eden, aşama) |
| API | `POST /executions/{id}/cancellation` |
| Ekran | Çalıştırmalar > Detay |
| Tablo | `rule_executions`(status, cancel_requested_at, cancel_requested_by, cancel_reason_code); `persistent_jobs`(status) |
| Test | idempotency; kuyruk/çalışan ayrımı; sahiplik yetkisi; audit |

###### D07.C01.W03.A02 — İptal sinyalini işleyip çalıştırmayı sonlandır

| Alan | Değer |
|---|---|
| Amaç | İptalin gerçekten uygulanmasını ve kısmi sonucun tutarlı kalmasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Worker'ın iptal sinyalini görmesi |
| Ön koşul | Çalıştırma `CANCEL_REQUESTED` |
| Akış | **Temel:** aktif sorguyu sonlandır → o ana kadarki sonuçları `PARTIAL` olarak sakla → çalıştırmayı `CANCELLED` yap → sonuçları resmî skordan dışla → audit. **Alternatif:** iptal öncesi tamamlanan kural sonuçları geçerli sayılır ama ölçüm yeterliliği düşer. **Hata:** sorgu sonlandırılamazsa zaman aşımına bırakılır |
| Durum geçişi | `CANCEL_REQUESTED` → `CANCELLED` |
| Yetki | Sistem aktörü |
| Audit | `EXECUTION_CANCELLED` (çalıştırma, tamamlanan kural sayısı, süre) |
| API | `—` |
| Ekran | Çalıştırmalar > Detay |
| Tablo | `rule_executions`(status, cancelled_at); `rule_execution_results`(eligible_for_official_scoring) |
| Test | kısmi sonuç tutarlılığı; skordan dışlama; sorgu sonlandırma; audit |

#### D07.C02 — Zamanlama

##### D07.C02.W01 — Zamanlama tanımı yaşam döngüsü

###### D07.C02.W01.A01 — Zamanlama tanımla

| Alan | Değer |
|---|---|
| Amaç | Ölçümün insan müdahalesi olmadan, öngörülebilir aralıklarla tekrarlanmasını sağlamak |
| Aktör | Data Steward; Operations User |
| Tetikleyici | Zamanlama ekranından yeni tanım |
| Ön koşul | Kural sürümleri `ACTIVE`; zaman dilimi geçerli; kaynak erişim penceresiyle uyumlu |
| Akış | **Temel:** ad, kapsam, tekrar deseni, zaman dilimi ve pencere gir → sonraki çalışma anını hesapla → `ACTIVE` kaydet → audit. **Alternatif:** tek seferlik zamanlama tanımlanır. **Hata:** kaynak yasaklı penceresiyle çakışan tanım → uyar |
| Durum geçişi | `—` → `ACTIVE` |
| Yetki | `schedule.manage` + dataset ve kaynak kapsamı |
| Audit | `SCHEDULE_CREATED` (zamanlama, desen, zaman dilimi, sonraki çalışma) |
| API | `POST /schedules` |
| Ekran | Zamanlamalar > Yeni |
| Tablo | `schedules`(schedule_id, name, schedule_type, timezone_name, rule_version_ids, is_active, next_run_at, created_by) |
| Test | zaman dilimi ve yaz saati; sonraki an hesabı; pencere çakışması; audit |

###### D07.C02.W01.A02 — Zamanlamayı duraklat veya sürdür

| Alan | Değer |
|---|---|
| Amaç | Bakım veya sorun dönemlerinde tekrarlayan ölçümü tanımı silmeden durdurmak |
| Aktör | Operations User; Data Steward |
| Tetikleyici | Zamanlama detayından duraklatma/sürdürme |
| Ön koşul | Zamanlama `ACTIVE` veya `PAUSED` |
| Akış | **Temel:** gerekçe gir → durumu değiştir → sürdürmede sonraki çalışma anını yeniden hesapla → audit. **Alternatif:** süreli duraklatma sonunda otomatik sürer. **Hata:** `—` |
| Durum geçişi | `ACTIVE` ↔ `PAUSED` |
| Yetki | `schedule.manage` + kapsam |
| Audit | `SCHEDULE_STATE_CHANGED` (zamanlama, eski/yeni durum, gerekçe, süre) |
| API | `POST /schedules/{id}/state` |
| Ekran | Zamanlamalar > Detay |
| Tablo | `schedules`(is_active, paused_until, next_run_at) |
| Test | sonraki an yeniden hesabı; süreli duraklatma; durum-makinesi; audit |

###### D07.C02.W01.A03 — Zamanlamayı sil

| Alan | Değer |
|---|---|
| Amaç | Gereksiz zamanlamaların kuyruğu kirletmesini önlemek |
| Aktör | Data Steward |
| Tetikleyici | Zamanlama detayından silme |
| Ön koşul | Zamanlamadan tetiklenmiş devam eden çalıştırma yok |
| Akış | **Temel:** devam eden çalıştırma kontrolü → `DELETED` işaretle (geçmiş çalıştırma bağı korunur) → audit. **Hata:** devam eden çalıştırma varsa → önce iptal istenir |
| Durum geçişi | `ACTIVE`\|`PAUSED` → `DELETED` |
| Yetki | `schedule.manage` + kapsam |
| Audit | `SCHEDULE_DELETED` (zamanlama, geçmiş çalıştırma sayısı) |
| API | `DELETE /schedules/{id}` |
| Ekran | Zamanlamalar > Detay |
| Tablo | `schedules`(status, deleted_at) |
| Test | devam eden çalıştırma koruması; geçmiş bağı korunumu; audit |

##### D07.C02.W02 — Vadesi gelen zamanlamanın tetiklenmesi

###### D07.C02.W02.A01 — Vadesi gelen zamanlamaları tetikle

| Alan | Değer |
|---|---|
| Amaç | Tanımlı zamanlamaların gerçekten ve tam bir kez çalışmasını garanti etmek |
| Aktör | Sistem |
| Tetikleyici | Zamanlayıcı döngüsü (sürekli çalışan) |
| Ön koşul | Zamanlayıcı süreci çalışır durumda |
| Akış | **Temel:** `next_run_at <= şimdi` ve `ACTIVE` olanları kilitleyerek seç → her biri için idempotency anahtarıyla çalıştırma aç → sonraki çalışma anını ilerlet → audit. **Alternatif:** kaçırılan çalışmalarda politika telafi veya atlama belirler. **Hata:** çalıştırma açılamazsa sonraki an ilerletilmez, yeniden denenir |
| Durum geçişi | Çalıştırma `—` → `QUEUED` |
| Yetki | Sistem aktörü; `schedule.trigger.execute` |
| Audit | `SCHEDULE_TRIGGERED` (zamanlama, çalıştırma, planlanan/gerçek an, gecikme) |
| API | `—` (sürekli çalışan zamanlayıcı) |
| Ekran | Zamanlamalar > Liste (son tetikleme görünürlüğü) |
| Tablo | `schedules`(next_run_at, last_triggered_at); `rule_executions`(execution_type='SCHEDULED') |
| Test | tam-bir-kez tetikleme; çoklu zamanlayıcı yarışı; kaçırılan çalışma telafisi; gecikme ölçümü |

###### D07.C02.W02.A02 — Kaçırılan çalışmayı ele al

| Alan | Değer |
|---|---|
| Amaç | Sistem durduğunda kaçan ölçümlerin sessizce kaybolmamasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Zamanlayıcının, `next_run_at`'ın tolerans süresinden fazla geçmiş olduğunu görmesi |
| Ön koşul | Telafi politikası yürürlükte |
| Akış | **Temel:** gecikmeyi hesapla → politikaya göre telafi et, atla veya tek sefer çalıştır → kararı kaydet → operatöre bildir → audit. **Alternatif:** üst üste kaçırmalarda yalnız en son çalıştırılır. **Hata:** politika yoksa → atla ve uyarı üret |
| Durum geçişi | Zamanlama `next_run_at` ilerletilir |
| Yetki | Sistem aktörü |
| Audit | `SCHEDULE_RUN_MISSED` (zamanlama, kaçırılan sayı, alınan karar, politika sürümü) |
| API | `—` |
| Ekran | Operasyon > Zamanlama Sağlığı |
| Tablo | `schedule_missed_runs`(schedule_id, missed_at, decision, policy_version) |
| Test | telafi/atlama politikası; üst üste kaçırma; bildirim; audit |

#### D07.C03 — Kalıcı iş kuyruğu

##### D07.C03.W01 — İş kuyruğa alma

###### D07.C03.W01.A01 — İşi kuyruğa al

| Alan | Değer |
|---|---|
| Amaç | Çalıştırmanın, süreç çökse bile kaybolmayacak biçimde kalıcı olarak kaydedilmesini sağlamak |
| Aktör | Sistem |
| Tetikleyici | Çalıştırma planının üretilmesi; rapor talebi; imha işi |
| Ön koşul | İş tipi kayıtlı bir işleyiciye sahip |
| Akış | **Temel:** iş tipi, yük, öncelik ve idempotency anahtarıyla kaydı **iş transaction'ıyla aynı anda** yaz → `AVAILABLE` → audit. **Alternatif:** ileri tarihli iş `available_at` ile ertelenir. **Hata:** aynı idempotency anahtarı varsa → mevcut işi döndür, mükerrer oluşturma |
| Durum geçişi | İş `—` → `AVAILABLE` |
| Yetki | Sistem aktörü |
| Audit | `JOB_ENQUEUED` (iş, tip, öncelik, idempotency anahtarı, kaynak nesne) |
| API | `—` (iç servis) |
| Ekran | Operasyon > Kuyruk |
| Tablo | `persistent_jobs`(job_id, job_type, payload, status, priority, idempotency_key, available_at, attempt_count, version) |
| Test | transaction atomikliği; idempotency; ertelenmiş iş; işleyicisiz tip reddi |

###### D07.C03.W01.A02 — İş önceliğini belirle

| Alan | Değer |
|---|---|
| Amaç | Acil ve kritik işlerin arka plan yığını arkasında beklememesini sağlamak |
| Aktör | Sistem; Operations User (manuel yükseltme) |
| Tetikleyici | Kuyruğa alma; operatör müdahalesi |
| Ön koşul | Öncelik politikası yürürlükte |
| Akış | **Temel:** kritiklik, iş yükü sınıfı ve tetikleyici tipinden önceliği hesapla → işi etiketle. **Alternatif:** operatör açık gerekçeyle önceliği yükseltir. **Hata:** politika yoksa varsayılan öncelik uygulanır |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü; manuel yükseltmede `job.priority.override` |
| Audit | Manuel değişimde `JOB_PRIORITY_OVERRIDDEN` (iş, eski/yeni öncelik, gerekçe) |
| API | `PATCH /jobs/{id}/priority` |
| Ekran | Operasyon > Kuyruk |
| Tablo | `persistent_jobs`(priority) |
| Test | öncelik hesabı; manuel yükseltme yetkisi; kuyruk sırası; audit |

##### D07.C03.W02 — İş sahiplenme (lease)

###### D07.C03.W02.A01 — İşi sahiplen

| Alan | Değer |
|---|---|
| Amaç | Aynı işin iki worker tarafından birlikte çalıştırılmasını yapısal olarak engellemek |
| Aktör | Sistem (worker) |
| Tetikleyici | Worker'ın iş arama döngüsü |
| Ön koşul | Worker kayıtlı ve sağlıklı; kaynak kotası ve zaman penceresi uygun |
| Akış | **Temel:** `AVAILABLE` ve `available_at <= şimdi` işlerden önceliğe göre birini **atomik olarak** kilitle → `CLAIMED` yap, worker kimliği ve lease bitişini yaz → işleyiciyi çağır. **Alternatif:** kota veya pencere uygun değilse iş `AVAILABLE` bırakılır. **Hata:** eşzamanlı sahiplenmede yalnız biri kazanır, diğeri sıradaki işe geçer |
| Durum geçişi | İş `AVAILABLE` → `CLAIMED` → `RUNNING` |
| Yetki | Sistem aktörü |
| Audit | `JOB_CLAIMED` (iş, worker, lease bitişi, deneme numarası) |
| API | `—` (worker döngüsü) |
| Ekran | Operasyon > Kuyruk |
| Tablo | `persistent_jobs`(status, claimed_by, lease_expires_at, attempt_count, version) |
| Test | eşzamanlı sahiplenme (tek kazanan); öncelik sırası; kota/pencere ertelemesi; audit |

##### D07.C03.W03 — Heartbeat ve lease yenileme

###### D07.C03.W03.A01 — Heartbeat gönder ve lease'i yenile

| Alan | Değer |
|---|---|
| Amaç | Uzun süren işlerin, worker hâlâ çalışıyorken kaybolmuş sayılıp yeniden başlatılmasını önlemek |
| Aktör | Sistem (worker) |
| Tetikleyici | Heartbeat aralığı zamanlayıcısı |
| Ön koşul | İş `RUNNING`; lease worker'a ait |
| Akış | **Temel:** son heartbeat zamanını güncelle → lease bitişini ilerlet → ilerleme yüzdesini kaydet. **Alternatif:** iptal işareti görülürse iptal akışına geçilir. **Hata:** lease başka worker'a geçmişse → mevcut worker işi bırakır, sonucu yazmaz |
| Durum geçişi | `—` (lease süresi uzar) |
| Yetki | Sistem aktörü |
| Audit | Yalnız lease kaybında `JOB_LEASE_LOST` (iş, worker, yeni sahip) |
| API | `—` |
| Ekran | Operasyon > Kuyruk (son heartbeat sütunu) |
| Tablo | `persistent_jobs`(last_heartbeat_at, lease_expires_at, progress) |
| Test | lease kaybında sonuç yazmama; heartbeat aralığı; iptal işareti; ilerleme kaydı |

#### D07.C04 — Hata toleransı ve kurtarma

##### D07.C04.W01 — Yeniden deneme

###### D07.C04.W01.A01 — Geçici hatada yeniden dene

| Alan | Değer |
|---|---|
| Amaç | Geçici altyapı hatalarının kalıcı ölçüm kaybına dönüşmesini engellemek |
| Aktör | Sistem |
| Tetikleyici | İşleyicinin geçici (retryable) hata bildirmesi |
| Ön koşul | Deneme sayısı politika sınırının altında |
| Akış | **Temel:** hatayı geçici/kalıcı olarak sınıflandır → geçiciyse üstel geri çekilmeyle `available_at` belirle → `AVAILABLE`a döndür → deneme sayacını artır → denemeyi kaydet. **Alternatif:** sınır aşılırsa dead-letter akışına geçilir. **Hata:** kalıcı hata hiç yeniden denenmez |
| Durum geçişi | İş `RUNNING` → `AVAILABLE` (yeniden deneme) \| `DEAD_LETTERED` |
| Yetki | Sistem aktörü |
| Audit | `JOB_RETRY_SCHEDULED` (iş, deneme no, hata sınıfı, sonraki deneme anı) |
| API | `—` |
| Ekran | Operasyon > Kuyruk |
| Tablo | `persistent_jobs`(status, attempt_count, available_at, last_error_class); `execution_attempts`(attempt_no, status, error_class, retryable) |
| Test | geçici/kalıcı sınıflandırma; üstel geri çekilme; sınır aşımı; deneme kaydı |

###### D07.C04.W01.A02 — Hatayı teknik veya kalite olarak sınıflandır

| Alan | Değer |
|---|---|
| Amaç | Altyapı hatalarının kalite skorunu düşürerek yanlış tablo çizmesini engellemek |
| Aktör | Sistem |
| Tetikleyici | Herhangi bir çalıştırma hatası |
| Ön koşul | Hata sınıfı kataloğu tanımlı |
| Akış | **Temel:** bağlantı, kimlik, zaman aşımı, kota ve sorgu hatalarını `TECHNICAL_ERROR` olarak sınıflandır → kalite ölçümü üretme → sonucu skordan dışla. **Alternatif:** kural mantığı hatası da teknik sayılır. **Hata:** sınıflandırılamayan hata güvenli tarafta teknik kabul edilir |
| Durum geçişi | Çalıştırma → `TECHNICAL_ERROR`; sonuç `eligible_for_official_scoring=false` |
| Yetki | Sistem aktörü |
| Audit | `EXECUTION_TECHNICAL_ERROR` (çalıştırma, hata sınıfı, kural sürümü) |
| API | `—` |
| Ekran | Çalıştırmalar > Detay |
| Tablo | `rule_executions`(status, error_class); `rule_execution_results`(technical_error_count) |
| Test | her hata sınıfı; skordan dışlama; bilinmeyende güvenli taraf; audit |

##### D07.C04.W02 — Zaman aşımı yönetimi

###### D07.C04.W02.A01 — Zaman aşımını uygula

| Alan | Değer |
|---|---|
| Amaç | Tek bir sorgunun kaynağı ve worker'ı süresiz meşgul etmesini engellemek |
| Aktör | Sistem |
| Tetikleyici | Sorgu süresinin politika sınırını aşması |
| Ön koşul | Kullanım politikasında sorgu zaman aşımı tanımlı |
| Akış | **Temel:** sorguyu sonlandır → `TIMEOUT` hata sınıfıyla işaretle → geçici hata sayarak yeniden deneme değerlendir → audit. **Alternatif:** tekrarlayan zaman aşımında iş kalıcı hata sayılır. **Hata:** sorgu sonlandırılamazsa bağlantı kapatılır |
| Durum geçişi | Çalıştırma → `TIMEOUT` |
| Yetki | Sistem aktörü |
| Audit | `EXECUTION_TIMED_OUT` (çalıştırma, süre, sınır, kural sürümü) |
| API | `—` |
| Ekran | Çalıştırmalar > Detay |
| Tablo | `rule_executions`(status, error_class='TIMEOUT'); `execution_attempts` |
| Test | sınır uygulaması; sorgu sonlandırma; tekrarlayan zaman aşımı; audit |

##### D07.C04.W03 — Worker kurtarma

###### D07.C04.W03.A01 — Süresi geçmiş lease'i geri al

| Alan | Değer |
|---|---|
| Amaç | Çöken bir worker'ın elinde kalan işlerin sonsuza dek asılı kalmasını engellemek |
| Aktör | Sistem (kurtarma döngüsü) |
| Tetikleyici | Lease süresi denetimi zamanlayıcısı |
| Ön koşul | İş `RUNNING`; `lease_expires_at` geçmiş |
| Akış | **Temel:** süresi geçmiş lease'leri bul → işi `AVAILABLE`a döndür → deneme sayacını artır → eski worker'ın sonuç yazmasını engelle → audit. **Alternatif:** sınır aşılmışsa doğrudan dead-letter. **Hata:** eski worker aynı anda sonuç yazmaya çalışırsa sürüm kontrolü reddeder |
| Durum geçişi | İş `RUNNING` → `AVAILABLE` \| `DEAD_LETTERED` |
| Yetki | Sistem aktörü |
| Audit | `JOB_LEASE_RECLAIMED` (iş, eski worker, lease bitişi, deneme no) |
| API | `—` |
| Ekran | Operasyon > Kuyruk |
| Tablo | `persistent_jobs`(status, claimed_by, lease_expires_at, attempt_count, version) |
| Test | zombie worker sonuç yazamaması; sürüm kontrolü; sınır aşımı; audit |

###### D07.C04.W03.A02 — Worker kaydını ve sağlığını yönet

| Alan | Değer |
|---|---|
| Amaç | Hangi worker'ların canlı olduğunu bilmek ve kapasiteyi görebilmek |
| Aktör | Sistem (worker); Operations User (görüntüleme) |
| Tetikleyici | Worker başlatma/durdurma; sağlık raporu aralığı |
| Ön koşul | `—` |
| Akış | **Temel:** worker kendini kimlik, kapasite ve desteklediği iş tipleriyle kaydeder → düzenli sağlık raporu gönderir → rapor kesilirse `STALE` işaretlenir. **Alternatif:** düzgün kapanışta `DRAINING` moduna geçip mevcut işleri bitirir. **Hata:** `—` |
| Durum geçişi | Worker `STARTING` → `ACTIVE` → `DRAINING` → `STOPPED`; rapor kesilince `STALE` |
| Yetki | Sistem aktörü; görüntülemede `operations.worker.read` |
| Audit | `WORKER_STATE_CHANGED` (worker, eski/yeni durum, kapasite) |
| API | `GET /operations/workers` |
| Ekran | Operasyon > Worker'lar |
| Tablo | `workers`(worker_id, hostname, capacity, supported_job_types, state, last_seen_at) |
| Test | düzgün kapanış; bayat tespiti; kapasite raporu; audit |

##### D07.C04.W04 — Dead-letter yönetimi

###### D07.C04.W04.A01 — İşi dead-letter'a taşı

| Alan | Değer |
|---|---|
| Amaç | Tekrar tekrar başarısız olan işin kuyruğu tıkamasını önlemek, ama kaybolmasına da izin vermemek |
| Aktör | Sistem |
| Tetikleyici | Deneme sınırının aşılması; kalıcı hata |
| Ön koşul | İş `RUNNING` veya `AVAILABLE`; deneme sınırı aşılmış |
| Akış | **Temel:** işi `DEAD_LETTERED` yap → hata sınıfı, deneme sayısı ve son yükle dead-letter kaydı oluştur → operatöre bildir → audit. **Alternatif:** kaynak nesne (çalıştırma/rapor) da başarısız işaretlenir. **Hata:** `—` |
| Durum geçişi | İş → `DEAD_LETTERED`; dead-letter kaydı `—` → `OPEN` |
| Yetki | Sistem aktörü |
| Audit | `JOB_DEAD_LETTERED` (iş, hata sınıfı, deneme sayısı, kaynak nesne) |
| API | `—` |
| Ekran | Operasyon > Dead-letter |
| Tablo | `persistent_jobs`(status); `dead_letter_records`(dead_letter_id, job_id, error_class, attempt_count, status, created_at) |
| Test | sınır davranışı; kaynak nesne işaretleme; bildirim; audit |

###### D07.C04.W04.A02 — Dead-letter kayıtlarını incele

| Alan | Değer |
|---|---|
| Amaç | Operatörün başarısız işleri ve nedenlerini tek yerde görmesini sağlamak |
| Aktör | Operations User |
| Tetikleyici | Operasyon ekranı açılışı; dead-letter bildirimi |
| Ön koşul | Okuma yetkisi |
| Akış | **Temel:** açık dead-letter kayıtlarını iş tipi, hata sınıfı, deneme sayısı ve yaşla listele → hata sınıfına göre grupla. **Alternatif:** kaynak nesneye göre filtrelenir. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `operations.dead-letter.read` + kurum geneli scope |
| Audit | Erişim kaydı: `DEAD_LETTER_LIST_VIEWED` (filtre, sonuç sayısı) |
| API | `GET /operations/dead-letters` — sayfalama, filtre |
| Ekran | Operasyon > Dead-letter |
| Tablo | `dead_letter_records`, `persistent_jobs`(okuma) |
| Test | gruplama; sayfalama; yetki; erişim kaydı |

###### D07.C04.W04.A03 — Dead-letter işini yeniden işle

| Alan | Değer |
|---|---|
| Amaç | Kök nedeni giderilen işlerin ölçüm boşluğu bırakmadan tamamlanmasını sağlamak |
| Aktör | Operations User |
| Tetikleyici | Dead-letter ekranından yeniden işleme |
| Ön koşul | Kayıt `OPEN`; yeniden işleme politikası izin veriyor; aktörün rolü politikada tanımlı |
| Akış | **Temel:** gerekçe gir → yeni idempotency anahtarıyla işi yeniden kuyruğa al → kaydı `REPROCESSED` yap → audit. **Alternatif:** toplu yeniden işleme hata sınıfına göre yapılır. **Hata:** politika izin vermiyorsa veya rol uygun değilse → reddet |
| Durum geçişi | Dead-letter `OPEN` → `REPROCESSED`; yeni iş `—` → `AVAILABLE` |
| Yetki | `operations.dead-letter.reprocess` + kurum geneli scope |
| Audit | `DEAD_LETTER_REPROCESSED` (kayıt, yeni iş, gerekçe, aktör) |
| API | `POST /operations/dead-letters/{id}/reprocessing` |
| Ekran | Operasyon > Dead-letter |
| Tablo | `dead_letter_records`(status, reprocessed_at, reprocessed_by); `persistent_jobs` |
| Test | politika/rol kapısı; toplu işlem; idempotency; audit |

###### D07.C04.W04.A04 — Dead-letter kaydını kapat

| Alan | Değer |
|---|---|
| Amaç | Yeniden işlenmeyecek işlerin açık listede birikmesini engellemek |
| Aktör | Operations User |
| Tetikleyici | Dead-letter ekranından kapatma |
| Ön koşul | Kayıt `OPEN` |
| Akış | **Temel:** kapatma gerekçesi gir → `CLOSED` → ölçüm boşluğunu işaretle → audit. **Alternatif:** ölçüm boşluğu ilgili dönemin yeterliliğini düşürür. **Hata:** `—` |
| Durum geçişi | Dead-letter `OPEN` → `CLOSED` |
| Yetki | `operations.dead-letter.close` + kurum geneli scope |
| Audit | `DEAD_LETTER_CLOSED` (kayıt, gerekçe, ölçüm boşluğu işaretlendi mi) |
| API | `POST /operations/dead-letters/{id}/closure` |
| Ekran | Operasyon > Dead-letter |
| Tablo | `dead_letter_records`(status, closed_at, closure_reason) |
| Test | ölçüm boşluğu zinciri; durum-makinesi; yetki; audit |

#### D07.C05 — Bölümlü ve artımlı yürütme

##### D07.C05.W01 — Bölüm (partition) planlama

###### D07.C05.W01.A01 — Çalıştırmayı bölümlere ayır

| Alan | Değer |
|---|---|
| Amaç | Çok büyük dataset'lerin tek bir dev sorguya sığmadan, parça parça ölçülebilmesini sağlamak |
| Aktör | Sistem |
| Tetikleyici | Plan üretiminde dataset boyutunun eşiği aşması |
| Ön koşul | Bölümleme anahtarı tanımlı veya çıkarılabilir |
| Akış | **Temel:** bölümleme anahtarına göre aralıkları hesapla → her aralık için ayrı iş üret → bölüm listesini çalıştırmaya bağla. **Alternatif:** doğal bölüm yoksa aralık taraması kullanılır. **Hata:** anahtar çıkarılamazsa bölümleme yapılmaz, tek iş olarak çalışır |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `EXECUTION_PARTITIONED` (çalıştırma, bölüm sayısı, anahtar) |
| API | `—` |
| Ekran | Çalıştırmalar > Detay > Bölümler |
| Tablo | `execution_partitions`(partition_id, execution_id, partition_key, range_start, range_end, status) |
| Test | aralık hesabı; anahtarsız yol; bölüm sayısı sınırı; audit |

##### D07.C05.W02 — Checkpoint ve devam

###### D07.C05.W02.A01 — Bölüm tamamlanmasını kaydet (checkpoint)

| Alan | Değer |
|---|---|
| Amaç | Yarıda kesilen uzun çalıştırmanın baştan başlamak zorunda kalmamasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Her bölümün tamamlanması |
| Ön koşul | Bölüm `RUNNING` |
| Akış | **Temel:** bölüm sonucunu ve sayaçlarını yaz → bölümü `COMPLETED` işaretle → çalıştırma ilerlemesini güncelle. **Alternatif:** bölüm başarısızsa `FAILED` işaretlenir, diğerleri devam eder. **Hata:** `—` |
| Durum geçişi | Bölüm `RUNNING` → `COMPLETED` \| `FAILED` |
| Yetki | Sistem aktörü |
| Audit | Çalıştırma sonucuna gömülü: `completed_partitions` |
| API | `—` |
| Ekran | Çalıştırmalar > Detay > Bölümler |
| Tablo | `execution_partitions`(status, completed_at); `rule_execution_results`(completed_partitions) |
| Test | kısmi başarısızlık izolasyonu; ilerleme doğruluğu; sayaç toplama |

###### D07.C05.W02.A02 — Kesilen çalıştırmayı kaldığı yerden sürdür

| Alan | Değer |
|---|---|
| Amaç | Yeniden denemede tamamlanmış bölümlerin gereksiz yere yeniden ölçülmesini önlemek |
| Aktör | Sistem |
| Tetikleyici | Bölümlü bir çalıştırma işinin yeniden denenmesi |
| Ön koşul | Checkpoint kayıtları mevcut; kural sürümü ve kapsam değişmemiş |
| Akış | **Temel:** tamamlanmış bölümleri atla → yalnız eksik olanları çalıştır → sonuçları birleştir. **Alternatif:** kural sürümü değiştiyse tüm bölümler yeniden çalışır. **Hata:** checkpoint tutarsızsa baştan başlanır |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `EXECUTION_RESUMED` (çalıştırma, atlanan bölüm sayısı, kalan bölüm sayısı) |
| API | `—` |
| Ekran | Çalıştırmalar > Detay |
| Tablo | `execution_partitions`(okuma); `rule_execution_results` |
| Test | atlama doğruluğu; sürüm değişiminde tam yeniden çalışma; tutarsız checkpoint; audit |

##### L5 — D07 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D07-001` | Her çalıştırma bir idempotency anahtarı taşır; aynı anahtarla ikinci istek yeni çalıştırma açmaz |
| `BR-D07-002` | İş kaydı, onu doğuran iş transaction'ıyla aynı anda yazılır; ikisinden biri başarısızsa hiçbiri kalıcı olmaz |
| `BR-D07-003` | Bir iş aynı anda yalnız bir worker tarafından sahiplenilebilir |
| `BR-D07-004` | Lease'i kaybeden worker sonuç yazamaz; sürüm kontrolü yazmayı reddeder |
| `BR-D07-005` | Deneme sınırı aşılan iş dead-letter'a taşınır, sessizce kaybolmaz |
| `BR-D07-006` | Kalıcı olarak sınıflandırılan hata yeniden denenmez |
| `BR-D07-007` | Sınıflandırılamayan hata güvenli tarafta teknik hata kabul edilir |
| `BR-D07-008` | Teknik hata kalite sonucu üretmez ve resmî skoru düşürmez |
| `BR-D07-009` | Yürürlükte kaynak kullanım politikası yoksa iş sahiplenilmez |
| `BR-D07-010` | İptal edilen çalıştırmanın kısmi sonuçları resmî skordan dışlanır |
| `BR-D07-011` | Zamanlama tetiklemesi tam bir kez gerçekleşir; çoklu zamanlayıcı mükerrer çalıştırma açamaz |
| `BR-D07-012` | Kaçırılan zamanlanmış çalışma için telafi politikası yoksa çalışma atlanır ve uyarı üretilir |
| `BR-D07-013` | Kapatılan dead-letter kaydı ilgili dönemde ölçüm boşluğu olarak işaretlenir |
| `BR-D07-014` | Kural sürümü değişen bölümlü çalıştırma checkpoint'ten sürdürülemez, baştan çalışır |

---

### D08 — Ölçüm, Sonuç ve Skorlama

Çalıştırmanın ürettiği ham sayıların, güvenilirliği bilinen ve açıklanabilir bir
kalite ölçüsüne dönüştüğü domain. **Ölçüm yeterliliği skordan önce gelir:**
yetersiz kapsamla ölçülen veri için skor iddia edilmez.

#### D08.C01 — Sonuç ve kanıt

##### D08.C01.W01 — Sonuç kaydı

###### D08.C01.W01.A01 — Kural sonucunu kaydet

| Alan | Değer |
|---|---|
| Amaç | Ölçümün ham sayaçlarını, sonradan yeniden yorumlanabilir biçimde saklamak |
| Aktör | Sistem |
| Tetikleyici | Bir kural sürümünün çalıştırma içinde tamamlanması |
| Ön koşul | Çalıştırma `RUNNING`; kural sürümü çözümlenmiş |
| Akış | **Temel:** popülasyon, uygun, değerlendirilen, geçen, kalan, dışlanan, teknik hatalı ve bilinmeyen sayaçlarını yaz → kural sürümü özetini damgala → sonucu değişmez kaydet. **Alternatif:** bölümlü çalıştırmada sayaçlar bölümlerden toplanır. **Hata:** sayaç tutarsızsa (toplam ≠ popülasyon) → sonuç `INCONSISTENT` işaretlenir ve skora girmez |
| Durum geçişi | Sonuç `—` → `RECORDED` \| `INCONSISTENT` |
| Yetki | Sistem aktörü |
| Audit | `RULE_RESULT_RECORDED` (çalıştırma, kural sürümü, sayaç özeti, tutarlılık) |
| API | `GET /executions/{id}/results` |
| Ekran | Çalıştırmalar > Detay > Sonuçlar |
| Tablo | `rule_execution_results`(rule_result_id, execution_id, rule_version_id, population_count, eligible_count, evaluated_count, passed_count, failed_count, excluded_count, technical_error_count, unknown_count, rule_version_digest) |
| Test | sayaç tutarlılığı; bölüm toplama; değişmezlik; audit |

###### D08.C01.W01.A02 — Sonuç geçmişini sorgula

| Alan | Değer |
|---|---|
| Amaç | Bir kuralın zaman içindeki davranışını görerek eşik ve kural kalitesini değerlendirmek |
| Aktör | Rule Author; Data Steward; Data Owner |
| Tetikleyici | Kural detayından geçmiş görüntüleme |
| Ön koşul | Kural üzerinde okuma kapsamı |
| Akış | **Temel:** kural sürümüne göre zaman sıralı sonuçları başarısızlık oranı ve yeterlilikle listele → sürüm değişim noktalarını işaretle. **Alternatif:** dönem ve kapsam filtrelenir. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `execution.read` + dataset kapsamı |
| Audit | Erişim kaydı: `RULE_RESULT_HISTORY_VIEWED` (kural, dönem) |
| API | `GET /rules/{id}/results` — sayfalama, dönem filtresi |
| Ekran | Kurallar > Kural Detayı > Geçmiş |
| Tablo | `rule_execution_results`, `rule_versions`(okuma) |
| Test | sürüm sınırı işaretleme; dönem filtresi; sayfalama; erişim kaydı |

##### D08.C01.W02 — Başarısız kayıt örneği üretimi

###### D08.C01.W02.A01 — Maskeli başarısız kayıt örneği üret

| Alan | Değer |
|---|---|
| Amaç | Sorunu inceleyecek kişinin neyin bozuk olduğunu, hassas veriyi görmeden anlamasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Kural sonucunda başarısız kayıt bulunması |
| Ön koşul | Kanıt politikası yürürlükte; alan sınıflandırmaları bilinir |
| Akış | **Temel:** politikadaki örnek sayısı kadar başarısız kayıt seç → hassas alanları maskele → ihlali gösteren en az alanı sakla → kanıt kaydı oluştur. **Alternatif:** yalnız ihlale konu alan ve anahtar tutulur. **Hata:** politika yoksa örnek üretilmez, yalnız sayaç saklanır |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `FAILURE_SAMPLE_GENERATED` (sonuç, örnek sayısı, maskelenen alan sayısı, politika sürümü) |
| API | `GET /rule-results/{id}/samples` |
| Ekran | Sorunlar > İnceleme; Çalıştırmalar > Detay |
| Tablo | `failure_samples`(sample_id, rule_result_id, masked_payload, masking_policy_version, retention_until) |
| Test | maskeleme doğruluğu; politika yokluğunda üretmeme; örnek sayısı sınırı; saklama süresi |

###### D08.C01.W02.A02 — Başarısız kayıt örneğini görüntüle

| Alan | Değer |
|---|---|
| Amaç | Kanıtın yalnız yetkili kişiye ve iz bırakarak gösterilmesini sağlamak |
| Aktör | Issue Assignee; Data Steward; Technical Data Steward |
| Tetikleyici | İnceleme ekranından kanıt görüntüleme |
| Ön koşul | Kanıt saklama süresi dolmamış; aktörün dataset kapsamı var |
| Akış | **Temel:** örnekleri maskeli döndür → her görüntülemeyi kaydet. **Alternatif:** ek yetkisi olan aktör için maskeleme seviyesi politikayla gevşetilebilir. **Hata:** saklama süresi dolmuşsa → örnek yok, yalnız sayaç gösterilir |
| Durum geçişi | `—` |
| Yetki | `evidence.sample.read` + dataset kapsamı |
| Audit | `FAILURE_SAMPLE_VIEWED` (örnek, aktör, maskeleme seviyesi) — hassas erişim sınıfı |
| API | `GET /rule-results/{id}/samples` |
| Ekran | Sorunlar > İnceleme |
| Tablo | `failure_samples`(okuma) |
| Test | maskeleme seviyeleri; süre dolumu; hassas erişim kaydı; kapsam |

#### D08.C02 — Ölçüm yeterliliği

##### D08.C02.W01 — Kapsam ve teknik sağlık değerlendirmesi

###### D08.C02.W01.A01 — Ölçüm kapsamını hesapla

| Alan | Değer |
|---|---|
| Amaç | Skorun verinin ne kadarına dayandığını sayısal olarak bilinir kılmak |
| Aktör | Sistem |
| Tetikleyici | Kural sonucunun kaydedilmesi |
| Ön koşul | Sonuç `RECORDED` |
| Akış | **Temel:** değerlendirilen / popülasyon oranını hesapla → örnekleme ve bölüm tamamlanma oranını dâhil et → kapsam oranını kaydet. **Alternatif:** tam tarama kapsamı 1.0 kabul edilir. **Hata:** popülasyon bilinmiyorsa kapsam hesaplanamaz, yeterlilik `UNKNOWN` |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | Yeterlilik kaydına gömülü |
| API | `GET /rule-results/{id}/qualification` |
| Ekran | Çalıştırmalar > Detay; Skorlar > Detay |
| Tablo | `measurement_qualifications`(qualification_id, rule_result_id, coverage_ratio, partition_completion_ratio) |
| Test | örnekleme kapsamı; kısmi bölüm; bilinmeyen popülasyon; hesap doğruluğu |

###### D08.C02.W01.A02 — Teknik sağlık oranını hesapla

| Alan | Değer |
|---|---|
| Amaç | Ölçümün ne kadarının teknik hatayla bozulduğunu görünür kılmak |
| Aktör | Sistem |
| Tetikleyici | Kural sonucunun kaydedilmesi |
| Ön koşul | Sonuç `RECORDED` |
| Akış | **Temel:** teknik hatalı ve bilinmeyen sayaçların değerlendirilene oranını hesapla → sağlık oranını kaydet. **Hata:** oran politikadaki sınırı aşarsa yeterlilik düşürülür |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | Yeterlilik kaydına gömülü |
| API | `GET /rule-results/{id}/qualification` |
| Ekran | Çalıştırmalar > Detay |
| Tablo | `measurement_qualifications`(technical_health_ratio) |
| Test | oran hesabı; sınır aşımı etkisi; sıfır bölme koruması |

##### D08.C02.W02 — Yeterlilik hükmü

###### D08.C02.W02.A01 — Ölçüm yeterliliği hükmü ver

| Alan | Değer |
|---|---|
| Amaç | Güvenilmeyecek kadar dar veya bozuk ölçümlerin skora dönüşmesini engellemek |
| Aktör | Sistem |
| Tetikleyici | Kapsam ve teknik sağlık hesaplarının tamamlanması |
| Ön koşul | Yeterlilik politikası yürürlükte |
| Akış | **Temel:** kapsam ve sağlık oranlarını politika eşikleriyle karşılaştır → `QUALIFIED` / `PARTIALLY_QUALIFIED` / `NOT_QUALIFIED` hükmü ver → gerekçeyi kaydet. **Alternatif:** kritik kurallarda eşikler daha sıkıdır. **Hata:** politika yoksa → hüküm üretilmez, sonuç skora girmez |
| Durum geçişi | Yeterlilik `—` → `QUALIFIED` \| `PARTIALLY_QUALIFIED` \| `NOT_QUALIFIED` |
| Yetki | Sistem aktörü |
| Audit | `MEASUREMENT_QUALIFICATION_ISSUED` (sonuç, hüküm, kapsam, sağlık, politika sürümü) |
| API | `GET /rule-results/{id}/qualification` |
| Ekran | Skorlar > Detay; Çalıştırmalar > Detay |
| Tablo | `measurement_qualifications`(verdict, reason_code, policy_version) |
| Test | her eşik sınırı; kritik kural sıkılığı; politika yokluğunda fail-closed; audit |

#### D08.C03 — Skor hesaplama

##### D08.C03.W01 — Kural düzeyi skor

###### D08.C03.W01.A01 — Kural düzeyi skoru hesapla

| Alan | Değer |
|---|---|
| Amaç | Tek bir kalite beklentisinin karşılanma derecesini standart bir ölçeğe indirmek |
| Aktör | Sistem |
| Tetikleyici | Yeterlilik hükmünün verilmesi |
| Ön koşul | Yeterlilik `QUALIFIED` veya `PARTIALLY_QUALIFIED`; skorlama politikası yürürlükte |
| Akış | **Temel:** geçen / değerlendirilen oranını hesapla → eşiğe göre normalize et → kural skorunu üret → kural sürümü ve politika sürümünü damgala. **Alternatif:** `PARTIALLY_QUALIFIED` sonuçta skor üretilir ama güven işareti taşır. **Hata:** `NOT_QUALIFIED` sonuçta skor üretilmez |
| Durum geçişi | Skor `—` → `CALCULATED` \| `NOT_QUALIFIED` |
| Yetki | Sistem aktörü |
| Audit | `RULE_SCORE_CALCULATED` (kural sürümü, skor, yeterlilik, politika sürümü) |
| API | `GET /scores/rules/{ruleVersionId}` |
| Ekran | Skorlar > Kural Detayı |
| Tablo | `quality_scores`(quality_score_id, scope_type='RULE', scope_id, score_value, score_status, qualification_verdict, rule_version_digest, policy_version, calculated_at) |
| Test | normalize hesabı; yetersiz ölçümde skor üretmeme; damgalama; determinizm |

##### D08.C03.W02 — Toplulaştırma

###### D08.C03.W02.A01 — Boyut ve dataset düzeyinde toplulaştır

| Alan | Değer |
|---|---|
| Amaç | Tek tek kural skorlarını, karar verilebilir bir dataset ve kalite boyutu görünümüne çevirmek |
| Aktör | Sistem |
| Tetikleyici | Kural skorlarının hesaplanması |
| Ön koşul | En az bir `QUALIFIED` kural skoru; ağırlıklar politikada tanımlı |
| Akış | **Temel:** kural skorlarını boyutlara göre grupla → ağırlıklı ortalama al → dataset skorunu boyut skorlarından ağırlıklı hesapla → dâhil/dışlanan bileşenleri kaydet. **Alternatif:** yeterlilik düşük kurallar ağırlığı azaltılarak katılır. **Hata:** hiçbir uygun kural yoksa → dataset skoru `NO_DATA` |
| Durum geçişi | Skor `—` → `CALCULATED` \| `NO_DATA` |
| Yetki | Sistem aktörü |
| Audit | `SCORE_AGGREGATED` (kapsam, dâhil kural sayısı, dışlanan sayısı, politika sürümü) |
| API | `GET /scores?scope=dataset` |
| Ekran | Skorlar > Dataset Görünümü |
| Tablo | `quality_scores`(scope_type='DATASET'\|'DIMENSION', score_value, included_component_count, excluded_component_count) |
| Test | ağırlıklı ortalama; dışlama mantığı; boş kapsam; determinizm |

###### D08.C03.W02.A02 — Kritik kural vetosunu uygula

| Alan | Değer |
|---|---|
| Amaç | Kritik bir kontrolün başarısızlığının, ortalama içinde erimesini engellemek |
| Aktör | Sistem |
| Tetikleyici | Toplulaştırma sırasında kritik kural başarısızlığı |
| Ön koşul | Kritik kural tanımlı; veto politikası yürürlükte |
| Akış | **Temel:** kritik kural eşiği aşılmışsa toplu skoru politika tavanına indir → veto gerekçesini kaydet. **Alternatif:** veto yerine ağır ceza uygulanabilir (politikaya göre). **Hata:** veto politikası yoksa veto uygulanmaz |
| Durum geçişi | Skor değeri değişir; `veto_applied=true` |
| Yetki | Sistem aktörü |
| Audit | `CRITICAL_VETO_APPLIED` (kapsam, veto eden kural, ham skor, tavan skor) |
| API | `GET /scores/{id}` (veto göstergesi) |
| Ekran | Skorlar > Detay |
| Tablo | `quality_scores`(veto_applied, veto_rule_version_id, raw_score_value) |
| Test | veto eşiği; ham skorun korunması; politika yokluğu; audit |

###### D08.C03.W02.A03 — Domain ve kurum düzeyinde toplulaştır

| Alan | Değer |
|---|---|
| Amaç | Yönetimin kalite durumunu iş kırılımıyla tek bakışta görmesini sağlamak |
| Aktör | Sistem |
| Tetikleyici | Dataset skorlarının hesaplanması |
| Ön koşul | Dataset'ler iş domainlerine atanmış; domain ağırlıkları tanımlı |
| Akış | **Temel:** dataset skorlarını kritikliğe göre ağırlıklandır → iş domaini skorunu üret → domain skorlarından kurum skorunu üret. **Alternatif:** domaine atanmamış dataset'ler ayrı "atanmamış" grubunda raporlanır. **Hata:** ağırlık tanımı yoksa eşit ağırlık kullanılmaz, hesap yapılmaz |
| Durum geçişi | Skor `—` → `CALCULATED` |
| Yetki | Sistem aktörü |
| Audit | `SCORE_AGGREGATED` (kapsam='DOMAIN'\|'ENTERPRISE', dâhil dataset sayısı) |
| API | `GET /scores?scope=domain` |
| Ekran | Genel Bakış |
| Tablo | `quality_scores`(scope_type='DOMAIN'\|'ENTERPRISE') |
| Test | kritiklik ağırlığı; atanmamış grubu; ağırlık yokluğunda fail-closed |

##### D08.C03.W03 — Skor yayımlama

###### D08.C03.W03.A01 — Skoru atomik olarak yayımla

| Alan | Değer |
|---|---|
| Amaç | Kullanıcıların yarım hesaplanmış, tutarsız bir skor görmesini engellemek |
| Aktör | Sistem |
| Tetikleyici | Tüm toplulaştırma seviyelerinin tamamlanması |
| Ön koşul | Kural, boyut, dataset, domain ve kurum skorları hesaplanmış |
| Akış | **Temel:** tüm seviyeleri **tek transaction'da** yaz → önceki yayımı `SUPERSEDED` yap → yeni yayımı `PUBLISHED` yap → audit. **Alternatif:** kısmi hesapta yayım yapılmaz. **Hata:** herhangi bir seviye başarısızsa hiçbiri yayımlanmaz |
| Durum geçişi | Skor yayımı `—` → `PUBLISHED`; önceki → `SUPERSEDED` |
| Yetki | Sistem aktörü |
| Audit | `SCORE_PUBLISHED` (yayım, kapsam sayısı, hesap dönemi, politika sürümü) |
| API | `GET /scores` |
| Ekran | Genel Bakış; Skorlar |
| Tablo | `score_publications`(publication_id, period, status, published_at); `quality_scores`(publication_id) |
| Test | transaction atomikliği; kısmi hesapta yayımlamama; devir zinciri; audit |

#### D08.C04 — Skor açıklanabilirliği

##### D08.C04.W01 — Katkı grafiği üretimi

###### D08.C04.W01.A01 — Skor katkı grafiğini üret

| Alan | Değer |
|---|---|
| Amaç | "Skor neden bu?" sorusunun, tahmin yürütmeden ve bileşenlere kadar yanıtlanabilmesini sağlamak |
| Aktör | Sistem |
| Tetikleyici | Skor yayımı |
| Ön koşul | Toplulaştırma bileşenleri kaydedilmiş |
| Akış | **Temel:** her seviye için katkıda bulunan bileşenleri, ağırlıklarını ve katkı miktarlarını graf olarak üret → dışlanan bileşenleri gerekçesiyle ekle → sürüm referanslarını damgala. **Alternatif:** veto uygulanmışsa veto yolu ayrıca işaretlenir. **Hata:** bileşen kaydı eksikse graf üretilmez, skor açıklanamaz işaretlenir |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `SCORE_CONTRIBUTION_GRAPH_BUILT` (skor, düğüm sayısı, dışlanan sayısı) |
| API | `GET /scores/{id}/contributions` |
| Ekran | Skorlar > Detay > Katkı |
| Tablo | `score_contribution_graphs`(quality_score_id, graph, created_at) |
| Test | graf bütünlüğü; dışlanan bileşen gerekçesi; veto yolu; yeniden üretilebilirlik |

###### D08.C04.W01.A02 — Skoru yeniden üret ve doğrula

| Alan | Değer |
|---|---|
| Amaç | Bir skorun geçmişte nasıl hesaplandığının bugün kanıtlanabilmesini sağlamak |
| Aktör | Auditor; Data Owner |
| Tetikleyici | Skor detayından yeniden üretme talebi |
| Ön koşul | Katkı grafiği ve tüm sürüm referansları mevcut |
| Akış | **Temel:** kaydedilmiş sayaç, ağırlık ve politika sürümüyle hesabı tekrarla → sonucu saklanan skorla karşılaştır → eşleşmeyi raporla. **Alternatif:** eşleşmezse fark bileşen bazında gösterilir. **Hata:** referans eksikse yeniden üretme yapılamaz |
| Durum geçişi | `—` |
| Yetki | `score.reproduce` + kapsam |
| Audit | `SCORE_REPRODUCTION_VERIFIED` (skor, eşleşti mi, fark özeti) |
| API | `POST /scores/{id}/reproduction` |
| Ekran | Skorlar > Detay > Katkı |
| Tablo | `score_contribution_graphs`, `quality_scores`, `rule_execution_results`(okuma) |
| Test | determinizm; fark tespiti; eksik referans; audit |

##### D08.C04.W02 — Dönem karşılaştırması

###### D08.C04.W02.A01 — İki dönemin skorunu karşılaştır

| Alan | Değer |
|---|---|
| Amaç | Kalitenin iyileşip kötüleştiğini ve bunun hangi bileşenden geldiğini görmek |
| Aktör | Data Owner; Data Steward; yönetici roller |
| Tetikleyici | Skor ekranından dönem karşılaştırması |
| Ön koşul | Her iki dönemde yayımlanmış skor mevcut |
| Akış | **Temel:** aynı kapsam için iki yayımı karşılaştır → seviye bazlı farkları ve en çok katkı yapan değişimleri üret. **Alternatif:** kural kümesi veya politika sürümü değiştiyse karşılaştırma "sınırda" işaretlenir. **Hata:** kapsam veya model uyumsuzsa → `INCOMPARABLE`, fark üretilmez |
| Durum geçişi | `—` |
| Yetki | `score.read` + kapsam |
| Audit | Erişim kaydı: `SCORE_COMPARISON_VIEWED` (kapsam, dönemler, uyumluluk) |
| API | `GET /scores/comparison` |
| Ekran | Skorlar > Karşılaştırma |
| Tablo | `quality_scores`, `score_publications`, `score_contribution_graphs`(okuma) |
| Test | uyumsuz modelde fail-closed; fark sıralaması; sınırda işaretleme; erişim kaydı |

#### D08.C05 — Kritiklik ve risk

##### D08.C05.W01 — Kritiklik modeli yönetimi

###### D08.C05.W01.A01 — Kritiklik modelini tanımla

| Alan | Değer |
|---|---|
| Amaç | Kritikliğin kişisel yargı yerine tanımlı kriterlere dayanmasını sağlamak |
| Aktör | Data Governance Admin |
| Tetikleyici | Yönetişim ekranından model tanımlama |
| Ön koşul | Politika taslağı mevcut |
| Akış | **Temel:** kritiklik seviyelerini ve her seviyenin kriterlerini (kullanım yaygınlığı, aşağı akış etkisi, iş süreci bağımlılığı) tanımla → onaya gönder. **Alternatif:** kriterlerden otomatik kritiklik önerisi üretilir. **Hata:** çakışan kriter tanımı → reddet |
| Durum geçişi | Politika taslağı üzerinden |
| Yetki | `risk.model.manage` + kurum geneli scope |
| Audit | `CRITICALITY_MODEL_CONFIGURED` (seviye sayısı, kriter özeti) |
| API | `PUT /policies/{id}/criticality-model` |
| Ekran | Yönetişim > Kritiklik Modeli |
| Tablo | `policies`(policy_type='CRITICALITY', parameters) |
| Test | çakışan kriter; otomatik öneri; onay zinciri; audit |

##### D08.C05.W02 — Risk derecelendirme

###### D08.C05.W02.A01 — Varlık risk derecesini hesapla

| Alan | Değer |
|---|---|
| Amaç | Kalite skorunu iş etkisiyle birleştirerek nereye önce müdahale edileceğini belirlemek |
| Aktör | Sistem |
| Tetikleyici | Skor yayımı; kritiklik değişimi |
| Ön koşul | Kritiklik ve skor mevcut; risk politikası yürürlükte |
| Akış | **Temel:** skor açığı × kritiklik × aşağı akış etki genişliğinden risk derecesini hesapla → dereceyi kaydet → eşik aşımında bildir. **Alternatif:** açık istisna varsa risk derecesi işaretlenerek düşürülür. **Hata:** politika yoksa risk hesaplanmaz |
| Durum geçişi | Risk `—` → `LOW` \| `MEDIUM` \| `HIGH` \| `CRITICAL` |
| Yetki | Sistem aktörü |
| Audit | `RISK_RATING_CALCULATED` (varlık, derece, bileşenler, politika sürümü) |
| API | `GET /risk-ratings` — filtre |
| Ekran | Genel Bakış > Risk; Katalog > Varlık Detayı |
| Tablo | `risk_ratings`(rating_id, asset_type, asset_id, rating, score_gap, criticality, impact_breadth, policy_version) |
| Test | bileşen hesabı; istisna etkisi; politika yokluğu; eşik bildirimi |

###### D08.C05.W02.A02 — Risk sıralamasını görüntüle

| Alan | Değer |
|---|---|
| Amaç | Sınırlı kaynağın en yüksek riskli varlıklara yönlendirilmesini sağlamak |
| Aktör | Data Owner; Data Governance Admin; yönetici roller |
| Tetikleyici | Genel bakış ekranı; risk raporu |
| Ön koşul | Risk dereceleri hesaplanmış; okuma kapsamı |
| Akış | **Temel:** kapsam içindeki varlıkları risk derecesine göre sırala → skor, kritiklik ve açık sorun sayısıyla birlikte göster. **Alternatif:** domain veya sahibe göre gruplanır. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `risk.read` + kapsam |
| Audit | Erişim kaydı: `RISK_RANKING_VIEWED` (filtre, sonuç sayısı) |
| API | `GET /risk-ratings` — sayfalama, sıralama, filtre |
| Ekran | Genel Bakış > Risk |
| Tablo | `risk_ratings`, `quality_scores`, `issues`(okuma) |
| Test | sıralama; kapsam filtreleme; gruplama; erişim kaydı |

##### L5 — D08 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D08-001` | Sonuç kayıtları değişmezdir; düzeltme yeni çalıştırmayla yapılır |
| `BR-D08-002` | Sayaç toplamı popülasyonla tutarsızsa sonuç skora dâhil edilmez |
| `BR-D08-003` | Her sonuç, üretildiği kural sürümünün ve politika sürümünün özetini taşır |
| `BR-D08-004` | Başarısız kayıt örnekleri veri minimizasyonu ilkesiyle, ihlali gösteren en az alanla üretilir |
| `BR-D08-005` | Sınıflandırılmamış veya hassas alanlar kanıt örneklerinde maskelenir |
| `BR-D08-006` | Kanıt örneği görüntüleme hassas erişim olarak ayrıca kaydedilir |
| `BR-D08-007` | Yeterlilik politikası yürürlükte değilse skor üretilmez |
| `BR-D08-008` | `NOT_QUALIFIED` ölçümden skor üretilmez; skor yokluğu sıfır skor değildir |
| `BR-D08-009` | Test ve gölge sonuçları hiçbir toplulaştırmaya girmez |
| `BR-D08-010` | Skor yayımı atomiktir; seviyelerden biri hesaplanamazsa hiçbiri yayımlanmaz |
| `BR-D08-011` | Kritik kural vetosunda ham skor da saklanır; veto ham ölçümü değiştirmez |
| `BR-D08-012` | Her skor, katkı grafiğiyle bileşenlerine kadar geriye izlenebilir olmalıdır |
| `BR-D08-013` | Katkı grafiği üretilemeyen skor "açıklanamaz" olarak işaretlenir |
| `BR-D08-014` | Farklı kural kümesi, model veya politika sürümüne sahip dönemler karşılaştırılamaz |
| `BR-D08-015` | Risk derecesi skoru değiştirmez; ayrı bir öncelik göstergesidir |

---

### D09 — Sorun, İstisna ve Remediation

Ölçümün insan eylemine dönüştüğü domain. Bir bozulmanın tespit edilmesi tek
başına değer üretmez; sahiplenilmesi, çözülmesi, bağımsız doğrulanması ve
tekrarında yeniden açılması gerekir.

#### D09.C01 — Sorun oluşumu ve tekilleştirme

##### D09.C01.W01 — Otomatik sorun üretimi

###### D09.C01.W01.A01 — Kalite ihlalinden sorun üret

| Alan | Değer |
|---|---|
| Amaç | Başarısız ölçümün bir sahibe ulaşmadan kaybolmasını engellemek |
| Aktör | Sistem |
| Tetikleyici | Kural sonucunun eşiği aşacak biçimde başarısız olması |
| Ön koşul | Sonuç yeterliliği `QUALIFIED` veya `PARTIALLY_QUALIFIED`; sorun üretim politikası yürürlükte |
| Akış | **Temel:** tekilleştirme anahtarını üret → açık sorun varsa yinelenmeye yönlendir → yoksa sorun aç, önceliği kritiklik ve risk derecesinden hesapla → sahibe ata → bildir → audit. **Alternatif:** açık istisna kapsamındaysa sorun açılmaz, istisna kaydına sayaç eklenir. **Hata:** yeterlilik `NOT_QUALIFIED` ise kalite sorunu açılmaz; teknik hata yolu izlenir |
| Durum geçişi | Sorun `—` → `NEW` |
| Yetki | Sistem aktörü |
| Audit | `ISSUE_CREATED` (sorun, kaynak sonuç, kural sürümü, öncelik, tekilleştirme anahtarı) |
| API | `GET /issues` (sonuç görünürlüğü) |
| Ekran | Sorunlar > Liste |
| Tablo | `issues`(issue_id, issue_no, source_event_type='QUALITY', trigger_type, scope_type, scope_id, status, priority, assignee_user_id, deduplication_key_digest, occurrence_count, version) |
| Test | yetersiz ölçümde sorun açmama; istisna kapsamı; öncelik hesabı; audit |

###### D09.C01.W01.A02 — Teknik hatadan sorun üret

| Alan | Değer |
|---|---|
| Amaç | Ölçümün yapılamamasının, kalite ihlaliyle karıştırılmadan ama görmezden de gelinmeden ele alınmasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Tekrarlayan teknik hata; dead-letter kaydı |
| Ön koşul | Teknik hata eşiği politikada tanımlı ve aşılmış |
| Akış | **Temel:** teknik sorun aç → kaynağın teknik sahibine ata → kalite skorundan bağımsız işaretle → bildir → audit. **Alternatif:** aynı hata sınıfı için açık sorun varsa yinelenme sayılır. **Hata:** eşik tanımlı değilse sorun açılmaz |
| Durum geçişi | Sorun `—` → `NEW` (source_event_type='TECHNICAL') |
| Yetki | Sistem aktörü |
| Audit | `ISSUE_CREATED` (sorun, hata sınıfı, kaynak, tekrar sayısı) |
| API | `GET /issues?sourceEventType=TECHNICAL` |
| Ekran | Sorunlar > Liste; Operasyon |
| Tablo | `issues`(source_event_type='TECHNICAL', trigger_type='TECHNICAL_ERROR') |
| Test | eşik davranışı; kalite skorundan bağımsızlık; teknik sahibe atama; audit |

###### D09.C01.W01.A03 — Sözleşme ihlalinden sorun üret

| Alan | Değer |
|---|---|
| Amaç | Veri sözleşmesi taahhüdünün karşılanmamasını tüketiciye karşı hesabı verilebilir kılmak |
| Aktör | Sistem |
| Tetikleyici | Sözleşme uyum ölçümünün taahhüdün altına düşmesi |
| Ön koşul | Sözleşme `ACTIVE`; ihlal eşiği aşılmış |
| Akış | **Temel:** sorun aç → üretici tarafın sahibine ata → tüketici taraflara bildir → önceliği sözleşme kritikliğinden al → audit. **Alternatif:** yumuşak eşik aşımında yalnız uyarı üretilir. **Hata:** ölçüm yeterliliği düşükse ihlal ilan edilmez |
| Durum geçişi | Sorun `—` → `NEW`; sözleşme `ACTIVE` → `BREACHED` |
| Yetki | Sistem aktörü |
| Audit | `ISSUE_CREATED` (sorun, sözleşme, taahhüt, ölçülen değer) |
| API | `GET /issues?sourceEventType=CONTRACT` |
| Ekran | Sorunlar > Liste; Veri Sözleşmeleri > Detay |
| Tablo | `issues`(source_event_type='CONTRACT'); `data_contracts`(status) |
| Test | yumuşak/sert eşik; yeterlilik ön koşulu; tüketici bildirimi; audit |

##### D09.C01.W02 — Tekilleştirme ve yinelenme

###### D09.C01.W02.A01 — Tekilleştirme anahtarını üret

| Alan | Değer |
|---|---|
| Amaç | Aynı bozulmanın her çalıştırmada yeni bir sorun açarak listeyi boğmasını engellemek |
| Aktör | Sistem |
| Tetikleyici | Sorun üretim girişimi |
| Ön koşul | Kaynak olay bilgileri çözümlenmiş |
| Akış | **Temel:** kural, kapsam, ihlal tipi ve (varsa) alan bileşenlerinden kararlı bir özet üret → hassas değer içermediğini garanti et → anahtarı döndür. **Alternatif:** politikayla anahtar bileşenleri daraltılıp genişletilebilir. **Hata:** bileşen eksikse tekilleştirme yapılmaz, yeni sorun açılır |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | Sorun kaydına gömülü: `deduplication_key_digest` |
| API | `—` (iç servis) |
| Ekran | `—` |
| Tablo | `issues`(deduplication_key_digest) |
| Test | anahtar kararlılığı; hassas değer sızdırmama; politika bileşenleri; eksik bileşen yolu |

###### D09.C01.W02.A02 — Yinelenmeyi kaydet

| Alan | Değer |
|---|---|
| Amaç | Bir sorunun ne kadar süredir ve kaç kez tekrarladığını görünür kılmak |
| Aktör | Sistem |
| Tetikleyici | Aynı tekilleştirme anahtarıyla yeni bozulma tespiti |
| Ön koşul | Aynı anahtarla açık sorun mevcut |
| Akış | **Temel:** yinelenme sayacını artır → son görülme zamanını güncelle → yeni kanıtı bağla → sayaç eşiği aşılırsa önceliği yükselt. **Alternatif:** kapalı sorun varsa yeniden açma akışına geçilir. **Hata:** eşzamanlı yinelenmede sürüm kontrolü çakışmayı çözer |
| Durum geçişi | `—` (occurrence_count artar); eşik aşımında `priority` yükselir |
| Yetki | Sistem aktörü |
| Audit | `ISSUE_RECURRENCE_RECORDED` (sorun, yeni sayaç, öncelik değişimi) |
| API | `—` |
| Ekran | Sorunlar > Detay |
| Tablo | `issues`(occurrence_count, last_seen_at, priority, version) |
| Test | sayaç artışı; eşzamanlılık; öncelik yükseltme; kapalı soruna yönlendirme |

##### D09.C01.W03 — Manuel sorun açma

###### D09.C01.W03.A01 — Manuel sorun aç

| Alan | Değer |
|---|---|
| Amaç | Otomatik ölçümün yakalayamadığı kalite problemlerinin de sisteme girmesini sağlamak |
| Aktör | Data Steward; Data Owner; Report Consumer |
| Tetikleyici | Sorunlar ekranından yeni sorun |
| Ön koşul | Kapsam varlığı `ACTIVE`; aktörün kapsamı var |
| Akış | **Temel:** kapsam, başlık, açıklama, öncelik ve kanıt bağlantısı gir → benzer açık sorunları göster → kaydet → sahibe ata → bildir → audit. **Alternatif:** mevcut soruna bağlanarak açılabilir. **Hata:** boş açıklama veya kapsam dışı varlık → reddet |
| Durum geçişi | Sorun `—` → `NEW` |
| Yetki | `issue.create` + kapsam |
| Audit | `ISSUE_CREATED` (sorun, manuel, açan, kapsam) |
| API | `POST /issues` |
| Ekran | Sorunlar > Yeni Sorun |
| Tablo | `issues`(source_event_type='MANUAL', created_by) |
| Test | benzer sorun önerisi; kapsam yetkisi; içerik doğrulama; audit |

#### D09.C02 — Sorun yaşam döngüsü

##### D09.C02.W01 — Atama

###### D09.C02.W01.A01 — Sorunu ata veya yeniden ata

| Alan | Değer |
|---|---|
| Amaç | Her sorunun adı belli bir sorumlusu olmasını ve devrin izlenebilmesini sağlamak |
| Aktör | Data Steward; Data Owner; mevcut atanan |
| Tetikleyici | Sorun detayından atama; otomatik sahiplik ataması |
| Ön koşul | Sorun kapalı değil; aday `ACTIVE` ve kapsamı yeterli |
| Akış | **Temel:** aday seç → kapsam ve rol doğrula → atamayı değiştir → geçmişe yaz → yeni atanana bildir → audit. **Alternatif:** aday listesi kapsam ve rolle filtrelenmiş olarak sunulur. **Hata:** kapsamı yetersiz aday → reddet; eşzamanlı atama → sürüm çakışması |
| Durum geçişi | Sorun `NEW` → `ASSIGNED`; diğer durumlarda atama değişir |
| Yetki | `issue.assign` + kapsam |
| Audit | `ISSUE_ASSIGNED` (sorun, eski/yeni atanan, atayan, gerekçe) |
| API | `POST /issues/{id}/assignment` — `If-Match` |
| Ekran | Sorunlar > Detay |
| Tablo | `issues`(assignee_user_id, status, version); `issue_history`(action, old_assignee, new_assignee) |
| Test | kapsam yetersizliği; eşzamanlılık; geçmiş kaydı; audit |

###### D09.C02.W01.A02 — Atama adaylarını listele

| Alan | Değer |
|---|---|
| Amaç | Atayanın, gerçekten yetkili ve ilgili kişiler arasından seçim yapmasını sağlamak |
| Aktör | Data Steward; Data Owner |
| Tetikleyici | Atama diyaloğunun açılması |
| Ön koşul | Sorun kapsamı çözümlenmiş |
| Akış | **Temel:** sorun kapsamını içeren aktif rol atamalarına sahip kullanıcıları bul → mevcut iş yüküyle birlikte listele. **Alternatif:** varlık sahibi ve steward'lar öne alınır. **Hata:** uygun aday yoksa → boş liste ve yönetişim boşluğu uyarısı |
| Durum geçişi | `—` |
| Yetki | `issue.assign` + kapsam |
| Audit | Erişim kaydı: `ISSUE_ASSIGNEE_OPTIONS_VIEWED` (sorun, aday sayısı) |
| API | `GET /issues/{id}/assignment-options` |
| Ekran | Sorunlar > Detay > Atama |
| Tablo | `role_assignments`, `assignment_scopes`, `asset_ownerships`, `issues`(okuma) |
| Test | kapsam eşleştirme; iş yükü hesabı; boş aday yolu; erişim kaydı |

##### D09.C02.W02 — İnceleme

###### D09.C02.W02.A01 — İncelemeyi başlat

| Alan | Değer |
|---|---|
| Amaç | Sorunun gerçekten ele alındığını ve ne zaman başlandığını kayıt altına almak |
| Aktör | Issue Assignee |
| Tetikleyici | Sorun detayından inceleme başlatma |
| Ön koşul | Sorun `NEW` veya `ASSIGNED`; aktör atanan kişi |
| Akış | **Temel:** durumu `INVESTIGATING` yap → başlangıç zamanını kaydet → SLA sayacını işaretle → audit. **Alternatif:** atanmamış sorunda başlatan kişi otomatik atanır. **Hata:** atanan olmayan aktör → reddet |
| Durum geçişi | `NEW`\|`ASSIGNED` → `INVESTIGATING` |
| Yetki | `issue.investigate` + kapsam ve atama sahipliği |
| Audit | `ISSUE_INVESTIGATION_STARTED` (sorun, aktör, ilk yanıt süresi) |
| API | `POST /issues/{id}/investigation` — `If-Match` |
| Ekran | Sorunlar > Detay |
| Tablo | `issues`(status, investigation_started_at, version); `issue_history` |
| Test | atama sahipliği; ilk yanıt SLA'i; durum-makinesi; audit |

###### D09.C02.W02.A02 — İnceleme kanıtını topla ve göster

| Alan | Değer |
|---|---|
| Amaç | İnceleyenin ekranlar arasında dolaşmadan, kararı verecek tüm kanıtı tek yerde görmesini sağlamak |
| Aktör | Issue Assignee; Technical Data Steward |
| Tetikleyici | İnceleme ekranı açılışı |
| Ön koşul | Sorun `INVESTIGATING` veya sonrası; kapsam yetkisi |
| Akış | **Temel:** kural tanımını, beklenen/gerçekleşen değerleri, maskeli başarısız örnekleri, ilgili profil dağılımını, aşağı akış etkisini, benzer geçmiş sorunları ve kök neden hipotezlerini birleştirip döndür. **Alternatif:** eksik bileşenler "kanıt yok" olarak işaretlenir, gizlenmez. **Hata:** kanıt saklama süresi dolmuşsa yalnız özet gösterilir |
| Durum geçişi | `—` |
| Yetki | `issue.investigate` + kapsam; kanıt için `evidence.sample.read` |
| Audit | `ISSUE_EVIDENCE_VIEWED` (sorun, gösterilen bileşenler) — hassas erişim sınıfı |
| API | `GET /issues/{id}/investigation/evidence` |
| Ekran | Sorunlar > İnceleme |
| Tablo | `issues`, `rule_execution_results`, `failure_samples`, `data_profiles`, `lineage_edges`, `diagnosis_hypotheses`(okuma) |
| Test | eksik bileşen gösterimi; maskeleme; süre dolumu; hassas erişim kaydı |

###### D09.C02.W02.A03 — Sorun yorumu ekle

| Alan | Değer |
|---|---|
| Amaç | İnceleme sürecindeki bulguların ve iletişimin sorunla birlikte kalmasını sağlamak |
| Aktör | Issue Assignee; Data Steward; Data Owner |
| Tetikleyici | Sorun detayından yorum ekleme |
| Ön koşul | Sorun kapalı değil; kapsam yetkisi |
| Akış | **Temel:** yorum metnini doğrula (uzunluk, zararlı içerik) → kaydet → bahsedilen kullanıcılara bildir → audit. **Alternatif:** yoruma kanıt referansı eklenebilir. **Hata:** hassas veri içeren yorum politika taramasıyla uyarılır |
| Durum geçişi | `—` |
| Yetki | `issue.comment` + kapsam |
| Audit | `ISSUE_COMMENT_ADDED` (sorun, yorum kimliği, aktör) |
| API | `POST /issues/{id}/comments` |
| Ekran | Sorunlar > Detay |
| Tablo | `issue_comments`(comment_id, issue_id, body, created_by, created_at) |
| Test | içerik doğrulama; hassas veri uyarısı; bahsetme bildirimi; audit |

##### D09.C02.W03 — Çözüm

###### D09.C02.W03.A01 — Çözümü kaydet

| Alan | Değer |
|---|---|
| Amaç | Neyin, nasıl düzeltildiğinin kalıcı ve denetlenebilir kaydını üretmek |
| Aktör | Issue Assignee |
| Tetikleyici | Sorun detayından çözüm kaydetme |
| Ön koşul | Sorun `INVESTIGATING` veya `WAITING_FOR_RESOLUTION`; aktör atanan kişi |
| Akış | **Temel:** kök neden, düzeltici aksiyon ve kanıt referansını gir → içerik kurallarını doğrula → çözümü kaydet → durumu `RESOLVED` yap → doğrulayıcıya bildir → audit. **Alternatif:** çözüm bir düzeltme aksiyonuna bağlanabilir. **Hata:** boş veya biçimsiz kök neden → reddet |
| Durum geçişi | `INVESTIGATING`\|`WAITING_FOR_RESOLUTION` → `RESOLVED` |
| Yetki | `issue.resolve` + kapsam ve atama sahipliği |
| Audit | `ISSUE_RESOLVED` (sorun, çözüm, kök neden sınıfı, aktör) |
| API | `POST /issues/{id}/resolution` — `If-Match` |
| Ekran | Sorunlar > Detay > Çözüm |
| Tablo | `issue_resolutions`(resolution_id, issue_id, root_cause, corrective_action, evidence_reference_id, created_by); `issues`(status, version) |
| Test | içerik doğrulama; atama sahipliği; durum-makinesi; eşzamanlılık; audit |

###### D09.C02.W03.A02 — Çözümü bekletmeye al

| Alan | Değer |
|---|---|
| Amaç | Dış bağımlılık nedeniyle ilerleyemeyen sorunların SLA'ini gerçekçi tutmak |
| Aktör | Issue Assignee |
| Tetikleyici | Sorun detayından bekletme |
| Ön koşul | Sorun `INVESTIGATING`; bekletme gerekçesi ve beklenen tarih verilmiş |
| Akış | **Temel:** gerekçe ve beklenen çözülme tarihini gir → `WAITING_FOR_RESOLUTION` yap → SLA sayacını politikaya göre duraklat → audit. **Alternatif:** beklenen tarih geçtiğinde otomatik hatırlatma üretilir. **Hata:** gerekçesiz bekletme → reddet |
| Durum geçişi | `INVESTIGATING` → `WAITING_FOR_RESOLUTION` |
| Yetki | `issue.resolve` + atama sahipliği |
| Audit | `ISSUE_PUT_ON_HOLD` (sorun, gerekçe, beklenen tarih, SLA duraklatıldı mı) |
| API | `POST /issues/{id}/hold` |
| Ekran | Sorunlar > Detay |
| Tablo | `issues`(status, hold_reason, expected_resolution_at, sla_paused_at) |
| Test | SLA duraklatma politikası; hatırlatma; durum-makinesi; audit |

##### D09.C02.W04 — Doğrulama

###### D09.C02.W04.A01 — Çözümü bağımsız doğrula

| Alan | Değer |
|---|---|
| Amaç | Düzeltmenin gerçekten işe yaradığının, düzelten kişiden bağımsız olarak kanıtlanmasını sağlamak |
| Aktör | Issue Verifier — çözümü kaydedenden farklı olmak zorunda |
| Tetikleyici | Doğrulama kuyruğundan seçim; çözüm sonrası yeni ölçüm sonucu |
| Ön koşul | Sorun `RESOLVED`; doğrulayıcı ≠ çözen; doğrulama kanıtı (yeni çalıştırma veya skor) mevcut |
| Akış | **Temel:** çözüm sonrası ölçüm kanıtını incele → doğrulama sonucunu (`PASSED`/`FAILED`) kaydet → başarılıysa `VERIFIED`, başarısızsa `INVESTIGATING`a döndür → audit → bildir. **Alternatif:** kanıt yoksa doğrulama çalıştırması tetiklenir. **Hata:** çözen=doğrulayan → reddet |
| Durum geçişi | `RESOLVED` → `VERIFIED` \| `INVESTIGATING` |
| Yetki | `issue.verify` + kapsam; görev ayrılığı zorunlu |
| Audit | `ISSUE_VERIFIED` (sorun, sonuç, doğrulayıcı, çözen, kanıt referansı) |
| API | `POST /issues/{id}/verification` — `If-Match` |
| Ekran | Sorunlar > Doğrulama Kuyruğu; Sorunlar > Detay |
| Tablo | `issue_verifications`(verification_id, issue_id, verification_reference_id, execution_id, score_id, outcome, recorded_by); `issues`(status) |
| Test | görev ayrılığı; kanıt ön koşulu; başarısız doğrulama dönüşü; audit |

##### D09.C02.W05 — Kapatma ve yeniden açma

###### D09.C02.W05.A01 — Sorunu kapat

| Alan | Değer |
|---|---|
| Amaç | Tamamlanmış işin listeden çıkmasını, ama izinin kalmasını sağlamak |
| Aktör | Issue Verifier; Data Owner |
| Tetikleyici | Sorun detayından kapatma; doğrulama sonrası otomatik kapatma politikası |
| Ön koşul | Sorun `VERIFIED`; veya iptal gerekçesiyle herhangi bir açık durumda |
| Akış | **Temel:** kapatma gerekçesini gir → `CLOSED` yap → SLA sayacını durdur → kapanış kanıtını sabitle → audit → bildir. **Alternatif:** geçersiz/yinelenen sorun `CANCELLED` olarak kapatılır. **Hata:** doğrulanmamış sorun kapatılmak isteniyorsa → gerekçe ve ek yetki istenir |
| Durum geçişi | `VERIFIED` → `CLOSED`; herhangi açık durum → `CANCELLED` |
| Yetki | `issue.close` + kapsam |
| Audit | `ISSUE_CLOSED` (sorun, gerekçe, çözüm süresi, SLA karşılandı mı) |
| API | `POST /issues/{id}/closure` — `If-Match` |
| Ekran | Sorunlar > Detay |
| Tablo | `issues`(status, closed_at, closure_reason, version); `issue_history` |
| Test | doğrulanmamış kapatma yolu; iptal yolu; SLA sonlandırma; audit |

###### D09.C02.W05.A02 — Aynı bozulmada sorunu yeniden aç

| Alan | Değer |
|---|---|
| Amaç | Kapatıldığı hâlde tekrar eden bir problemin, "çözülmüş" görünerek kaybolmasını engellemek |
| Aktör | Sistem; Data Steward (manuel) |
| Tetikleyici | Kapalı bir sorunun tekilleştirme anahtarıyla yeni bozulma tespiti |
| Ön koşul | Sorun `CLOSED`; yeniden açma penceresi politikada tanımlı ve içinde |
| Akış | **Temel:** kapalı sorunu bul → yeniden açma ilişkisi kur → durumu `NEW` yap → önceki çözümü geçmişte bırak → önceki atanana ve sahibe bildir → audit. **Alternatif:** pencere dışındaysa yeni sorun açılır ve önceki ile `RECURRENCE` ilişkisi kurulur. **Hata:** `CANCELLED` sorun yeniden açılmaz |
| Durum geçişi | `CLOSED` → `NEW` (yeniden açık) |
| Yetki | Sistem aktörü; manuelde `issue.reopen` + kapsam |
| Audit | `ISSUE_REOPENED` (sorun, önceki kapanış, geçen süre, tetikleyen kanıt) |
| API | `POST /issues/{id}/reopening` |
| Ekran | Sorunlar > Detay |
| Tablo | `issues`(status, reopened_count); `issue_relationships`(predecessor_issue_id, successor_issue_id, relationship_type='RECURRENCE') |
| Test | pencere içi/dışı davranış; iptal edilmiş sorun; ilişki kurulumu; audit |

#### D09.C03 — SLA ve eskalasyon

##### D09.C03.W01 — SLA hesaplama

###### D09.C03.W01.A01 — Sorun SLA hedeflerini belirle

| Alan | Değer |
|---|---|
| Amaç | Her sorun için ne kadar sürede yanıt ve çözüm beklendiğini baştan netleştirmek |
| Aktör | Sistem |
| Tetikleyici | Sorun açılması; öncelik veya kritiklik değişimi |
| Ön koşul | SLA politikası yürürlükte; iş takvimi tanımlı |
| Akış | **Temel:** öncelik, kritiklik ve domainden ilk yanıt ve çözüm hedeflerini çöz → iş takvimine göre hedef anlarını hesapla → sorunla ilişkilendir. **Alternatif:** öncelik değişiminde hedefler yeniden hesaplanır. **Hata:** SLA politikası yoksa hedef atanmaz, sorun "SLA'sız" işaretlenir |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `ISSUE_SLA_ASSIGNED` (sorun, ilk yanıt hedefi, çözüm hedefi, politika sürümü) |
| API | `GET /issues/{id}` (SLA alanları) |
| Ekran | Sorunlar > Detay |
| Tablo | `issue_slas`(issue_id, first_response_due_at, resolution_due_at, calendar_version, policy_version, paused_duration) |
| Test | iş takvimi hesabı; öncelik değişimi; politika yokluğu; duraklatma etkisi |

###### D09.C03.W01.A02 — SLA durumunu hesapla ve göster

| Alan | Değer |
|---|---|
| Amaç | Hangi sorunların gecikmekte olduğunu, gecikmeden önce görebilmek |
| Aktör | Issue Assignee; Data Owner; yönetici roller |
| Tetikleyici | Sorun listesi/detay açılışı; periyodik SLA değerlendirmesi |
| Ön koşul | SLA hedefleri atanmış |
| Akış | **Temel:** kalan süreyi hesapla → `ON_TRACK` / `AT_RISK` / `BREACHED` durumunu üret → listede göster. **Alternatif:** bekletilen sorunlarda duraklatılmış süre düşülür. **Hata:** SLA'sız sorunlarda durum `—` gösterilir |
| Durum geçişi | SLA durumu `ON_TRACK` → `AT_RISK` → `BREACHED` |
| Yetki | `issue.read` + kapsam |
| Audit | `ISSUE_SLA_BREACHED` yalnız ihlal anında (sorun, hedef, gecikme) |
| API | `GET /issues` (SLA durumu alanı) |
| Ekran | Sorunlar > Liste; Genel Bakış |
| Tablo | `issue_slas`(status, breached_at) |
| Test | duraklatma düşümü; risk eşiği; ihlal kaydı; iş takvimi |

##### D09.C03.W02 — Eskalasyon tetikleme

###### D09.C03.W02.A01 — SLA riskinde ve ihlalinde eskale et

| Alan | Değer |
|---|---|
| Amaç | Geciken sorunların, kimse fark etmeden beklemesini engellemek |
| Aktör | Sistem |
| Tetikleyici | SLA durumunun `AT_RISK` veya `BREACHED` olması |
| Ön koşul | Eskalasyon zinciri politikada tanımlı |
| Akış | **Temel:** eskalasyon seviyesini belirle → zincirdeki bir sonraki role bildir → eskalasyon kaydı oluştur → seviyeyi artır → audit. **Alternatif:** kritik varlıklarda zincir atlanarak üst seviyeye çıkılır. **Hata:** zincir tanımsızsa yalnız sahibe bildirilir |
| Durum geçişi | Eskalasyon `—` → `LEVEL_1` → `LEVEL_2` → … |
| Yetki | Sistem aktörü |
| Audit | `ISSUE_ESCALATED` (sorun, seviye, bildirilen rol, gecikme) |
| API | `GET /issues/{id}/escalations` |
| Ekran | Sorunlar > Detay; Genel Bakış > Eskalasyonlar |
| Tablo | `issue_escalations`(escalation_id, issue_id, level, escalated_to_role, escalated_at, reason) |
| Test | zincir ilerlemesi; kritik atlama; zincir yokluğu; bildirim; audit |

#### D09.C04 — İstisna ve override

##### D09.C04.W01 — İstisna talebi

###### D09.C04.W01.A01 — İstisna talep et

| Alan | Değer |
|---|---|
| Amaç | Bilinen ve kabul edilen bir bozulmanın, sürekli alarm üretmeden ve gerekçesi kayda geçerek yönetilmesini sağlamak |
| Aktör | Data Owner; Data Steward (maker) |
| Tetikleyici | Sorun detayından veya kural detayından istisna talebi |
| Ön koşul | Kapsam ve gerekçe verilmiş; **bitiş tarihi zorunlu** |
| Akış | **Temel:** kapsam (kural/dataset/alan), gerekçe, telafi edici kontrol ve bitiş tarihini gir → süre politikadaki üst sınırı aşmıyorsa talebi aç → `PENDING` → onaylayıcıya bildir → audit. **Alternatif:** mevcut istisnanın süresi uzatma talebi olarak açılır. **Hata:** süresiz istisna → reddet; üst sınır aşımı → reddet |
| Durum geçişi | İstisna `—` → `PENDING` |
| Yetki | `exception.request` + kapsam |
| Audit | `EXCEPTION_REQUESTED` (istisna, kapsam, gerekçe, bitiş, maker) |
| API | `POST /exceptions` |
| Ekran | İstisnalar > Yeni; Sorunlar > Detay |
| Tablo | `exceptions`(exception_id, scope_type, scope_id, reason, compensating_control, valid_until, maker_actor_id, status) |
| Test | süresiz talep reddi; üst sınır; uzatma yolu; kapsam yetkisi; audit |

##### D09.C04.W02 — İstisna onayı

###### D09.C04.W02.A01 — İstisna kararı ver

| Alan | Değer |
|---|---|
| Amaç | Riskin bilinçli olarak kabul edilmesini, yetkili ve bağımsız bir onaya bağlamak |
| Aktör | Data Governance Admin; Data Owner (maker'dan farklı) |
| Tetikleyici | İstisna onay kuyruğundan karar |
| Ön koşul | Talep `PENDING`; checker ≠ maker |
| Akış | **Temel:** kapsamı, gerekçeyi ve telafi edici kontrolü incele → karar + gerekçe → onayda `ACTIVE`, redde `REJECTED` → kapsamdaki sorun üretimini bastır → audit → bildir. **Alternatif:** onay süreyi kısaltarak verilebilir. **Hata:** maker=checker → reddet |
| Durum geçişi | İstisna `PENDING` → `ACTIVE` \| `REJECTED` |
| Yetki | `exception.decide` + kapsam; görev ayrılığı zorunlu |
| Audit | `EXCEPTION_DECIDED` (istisna, karar, gerekçe, maker, checker, geçerlilik) |
| API | `POST /exceptions/{id}/decision` — `If-Match` |
| Ekran | Onay Kuyruğu; İstisnalar > Detay |
| Tablo | `exceptions`(status, checker_actor_id, decided_at, valid_until, version) |
| Test | görev ayrılığı; süre kısaltma; sorun bastırma zinciri; audit |

###### D09.C04.W02.A02 — İstisnanın ham ölçümü değiştirmediğini garanti et

| Alan | Değer |
|---|---|
| Amaç | İstisnanın gerçeği gizlemek yerine yalnız uyarıyı bastırdığını garanti etmek |
| Aktör | Sistem |
| Tetikleyici | İstisna kapsamındaki bir ölçümün tamamlanması |
| Ön koşul | Aktif istisna kapsamı çözümlenmiş |
| Akış | **Temel:** ham sonucu ve ham skoru değiştirmeden kaydet → yalnız sorun üretimini ve bildirimi bastır → istisna kapsamındaki bileşeni skor görünümünde ayrıca işaretle. **Hata:** ham değeri değiştirme girişimi → sistem hatası, işlem reddedilir |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `EXCEPTION_SUPPRESSED_ALERT` (istisna, sonuç, bastırılan bildirim sayısı) |
| API | `—` |
| Ekran | Skorlar > Detay (istisna rozeti) |
| Tablo | `rule_execution_results`(değişmez); `exception_suppressions`(exception_id, rule_result_id, suppressed_at) |
| Test | ham değerin korunması; bastırma sayacı; görünürlük işareti; audit |

##### D09.C04.W03 — İstisna sona ermesi

###### D09.C04.W03.A01 — Süresi dolan istisnayı otomatik sonlandır

| Alan | Değer |
|---|---|
| Amaç | Geçici olarak verilen kabullerin kalıcı körlüğe dönüşmesini engellemek |
| Aktör | Sistem |
| Tetikleyici | İstisna süre denetimi zamanlayıcısı |
| Ön koşul | İstisna `ACTIVE`; `valid_until` geçmiş |
| Akış | **Temel:** istisnayı `EXPIRED` yap → bastırmayı kaldır → kapsamda bekleyen bozulmalar için sorun üret → sahibe ve onaylayana bildir → audit. **Alternatif:** bitişe yaklaşırken önceden uyarı gönderilir. **Hata:** `—` |
| Durum geçişi | İstisna `ACTIVE` → `EXPIRED` |
| Yetki | Sistem aktörü |
| Audit | `EXCEPTION_EXPIRED` (istisna, süre, bastırılan toplam olay sayısı) |
| API | `—` (zamanlanmış iş) |
| Ekran | İstisnalar > Liste |
| Tablo | `exceptions`(status, expired_at) |
| Test | otomatik sonlanma; bastırma kaldırma; birikmiş sorun üretimi; ön uyarı; audit |

###### D09.C04.W03.A02 — İstisnayı erken iptal et

| Alan | Değer |
|---|---|
| Amaç | Gerekçesi ortadan kalkan kabulü beklemeden geri almak |
| Aktör | Data Governance Admin; istisnayı onaylayan |
| Tetikleyici | İstisna detayından iptal |
| Ön koşul | İstisna `ACTIVE` |
| Akış | **Temel:** iptal gerekçesi gir → `REVOKED` yap → bastırmayı kaldır → bildir → audit. **Hata:** `—` |
| Durum geçişi | İstisna `ACTIVE` → `REVOKED` |
| Yetki | `exception.revoke` + kapsam |
| Audit | `EXCEPTION_REVOKED` (istisna, gerekçe, iptal eden, kalan süre) |
| API | `POST /exceptions/{id}/revocation` |
| Ekran | İstisnalar > Detay |
| Tablo | `exceptions`(status, revoked_at, revocation_reason) |
| Test | bastırma kaldırma; yetki; durum-makinesi; audit |

###### D09.C04.W03.A03 — Aktif istisnaları görüntüle

| Alan | Değer |
|---|---|
| Amaç | Kurumun hangi riskleri bilinçli olarak kabul ettiğini tek listede görünür kılmak |
| Aktör | Data Governance Admin; Auditor; Data Owner |
| Tetikleyici | İstisna ekranı açılışı; denetim incelemesi |
| Ön koşul | Okuma kapsamı |
| Akış | **Temel:** aktif istisnaları kapsam, gerekçe, onaylayan, bitiş tarihi ve bastırılan olay sayısıyla listele → bitişe yakın olanları öne al. **Alternatif:** süresi geçmiş ve iptal edilenler geçmiş sekmesinde. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `exception.read` + kapsam |
| Audit | Erişim kaydı: `EXCEPTION_LIST_VIEWED` (filtre, sonuç sayısı) |
| API | `GET /exceptions` — sayfalama, filtre |
| Ekran | İstisnalar > Liste |
| Tablo | `exceptions`, `exception_suppressions`(okuma) |
| Test | sıralama; kapsam filtreleme; sayfalama; erişim kaydı |

#### D09.C05 — Teşhis ve öneri

##### D09.C05.W01 — Kök neden hipotezi üretimi

###### D09.C05.W01.A01 — Kök neden hipotezleri üret

| Alan | Değer |
|---|---|
| Amaç | İnceleyene boş sayfa yerine, kanıta dayalı başlangıç noktaları sunmak |
| Aktör | Sistem |
| Tetikleyici | Sorun açılması veya inceleme başlatılması |
| Ön koşul | Teşhis politikası yürürlükte; ilgili kanıt kaynakları erişilebilir |
| Akış | **Temel:** zamansal olarak yakın şema değişikliklerini, yukarı akış bozulmalarını, hacim/drift sinyallerini ve kural değişikliklerini tara → her hipotezi kanıt referansı ve güven seviyesiyle üret → sırala. **Alternatif:** benzer geçmiş sorunların çözümleri hipotez olarak sunulur. **Hata:** kanıt yoksa hipotez üretilmez — tahmin yapılmaz |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `DIAGNOSIS_HYPOTHESES_GENERATED` (sorun, hipotez sayısı, kanıt kaynakları) |
| API | `GET /issues/{id}/diagnosis` |
| Ekran | Sorunlar > İnceleme > Teşhis |
| Tablo | `diagnosis_hypotheses`(hypothesis_id, issue_id, hypothesis_type, evidence_refs, confidence, rank) |
| Test | kanıtsız hipotez üretmeme; sıralama; her hipotez tipi; audit |

###### D09.C05.W01.A02 — Hipotezi doğrula veya reddet

| Alan | Değer |
|---|---|
| Amaç | Otomatik önerinin insan onayı olmadan "doğrulanmış neden" sayılmasını engellemek |
| Aktör | Issue Assignee |
| Tetikleyici | Teşhis panelinden hipotez değerlendirme |
| Ön koşul | Hipotez `PROPOSED`; sorun `INVESTIGATING` |
| Akış | **Temel:** hipotezi kabul veya reddet → gerekçe gir → kabul edilirse çözüm formuna kök neden olarak taşı → audit. **Alternatif:** kısmen doğru olarak işaretlenip düzenlenebilir. **Hata:** hipotez otomatik olarak kök nedene dönüşmez |
| Durum geçişi | Hipotez `PROPOSED` → `CONFIRMED` \| `REJECTED` |
| Yetki | `issue.investigate` + atama sahipliği |
| Audit | `DIAGNOSIS_HYPOTHESIS_DECIDED` (hipotez, karar, aktör, gerekçe) |
| API | `POST /diagnosis-hypotheses/{id}/decision` |
| Ekran | Sorunlar > İnceleme > Teşhis |
| Tablo | `diagnosis_hypotheses`(status, decided_by, decision_reason) |
| Test | otomatik kök nedene dönüşmeme; karar kaydı; durum-makinesi; audit |

##### D09.C05.W02 — Kanıtlı öneri üretimi

###### D09.C05.W02.A01 — Düzeltme önerisi üret

| Alan | Değer |
|---|---|
| Amaç | Tespitten eyleme geçişi hızlandırmak, ama kararı insanda bırakmak |
| Aktör | Sistem |
| Tetikleyici | Hipotezin doğrulanması; sorun inceleme |
| Ön koşul | Doğrulanmış hipotez veya yeterli kanıt; öneri politikası yürürlükte |
| Akış | **Temel:** hipotez tipine karşılık gelen öneri şablonunu seç → somut parametrelerle doldur → beklenen etkiyi ve kanıtı ekle → öneriyi sun. **Alternatif:** birden çok öneri fayda/maliyetle sıralanır. **Hata:** politika veya kanıt yoksa öneri üretilmez |
| Durum geçişi | Öneri `—` → `PROPOSED` |
| Yetki | Sistem aktörü |
| Audit | `RECOMMENDATION_GENERATED` (sorun, öneri sayısı, kanıt referansları) |
| API | `GET /issues/{id}/recommendations` |
| Ekran | Sorunlar > İnceleme > Öneriler |
| Tablo | `recommendations`(recommendation_id, issue_id, recommendation_type, parameters, expected_impact, evidence_refs, status) |
| Test | kanıtsız öneri üretmeme; sıralama; her öneri tipi; audit |

#### D09.C06 — Remediation

##### D09.C06.W01 — Düzeltme aksiyonu yaşam döngüsü

###### D09.C06.W01.A01 — Düzeltme aksiyonu oluştur

| Alan | Değer |
|---|---|
| Amaç | Düzeltmenin sözde kalmayıp planlanan, sahipli ve izlenen bir işe dönüşmesini sağlamak |
| Aktör | Issue Assignee; Data Owner |
| Tetikleyici | Öneriden kabul; sorun incelemesinden manuel oluşturma |
| Ön koşul | Sorun açık; aksiyon tipi ve sahibi belirlenmiş |
| Akış | **Temel:** aksiyon tipi, açıklama, sahip ve hedef tarih gir → soruna bağla → `PLANNED` kaydet → sahibe bildir → audit. **Alternatif:** öneriden oluşturulan aksiyon kanıt referansını taşır. **Hata:** hedef tarihsiz aksiyon → reddet |
| Durum geçişi | Aksiyon `—` → `PLANNED` |
| Yetki | `remediation.manage` + kapsam |
| Audit | `REMEDIATION_ACTION_CREATED` (aksiyon, sorun, tip, sahip, hedef tarih) |
| API | `POST /issues/{id}/remediation-actions` |
| Ekran | Sorunlar > Detay > Düzeltme |
| Tablo | `remediation_actions`(action_id, issue_id, action_type, description, owner_user_id, due_at, status, source_recommendation_id) |
| Test | hedef tarih zorunluluğu; öneriden türetme; bildirim; audit |

###### D09.C06.W01.A02 — Düzeltme aksiyonunu yürüt ve tamamla

| Alan | Değer |
|---|---|
| Amaç | Aksiyonun ilerleyişinin ve tamamlanma kanıtının kayıtlı olmasını sağlamak |
| Aktör | Aksiyon sahibi |
| Tetikleyici | Aksiyon detayından ilerleme/tamamlama |
| Ön koşul | Aksiyon `PLANNED` veya `IN_PROGRESS`; aktör sahip |
| Akış | **Temel:** durumu ilerlet → tamamlamada kanıt referansı zorunlu → `COMPLETED` yap → doğrulama tetikle → audit. **Alternatif:** aksiyon iptal edilebilir, gerekçe zorunlu. **Hata:** kanıtsız tamamlama → reddet |
| Durum geçişi | `PLANNED` → `IN_PROGRESS` → `COMPLETED` \| `CANCELLED` |
| Yetki | `remediation.execute` + aksiyon sahipliği |
| Audit | `REMEDIATION_ACTION_COMPLETED` (aksiyon, kanıt, süre, hedefe uyum) |
| API | `POST /remediation-actions/{id}/state` — `If-Match` |
| Ekran | Sorunlar > Detay > Düzeltme |
| Tablo | `remediation_actions`(status, completed_at, evidence_reference_id) |
| Test | kanıt zorunluluğu; sahiplik; durum-makinesi; audit |

###### D09.C06.W01.A03 — Otomatik düzeltmeyi politika altında çalıştır

| Alan | Değer |
|---|---|
| Amaç | Tekrarlayan ve düşük riskli düzeltmelerin insan beklemeden yapılabilmesini, ama sınırların korunmasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Otomatik düzeltmeye uygun işaretlenmiş aksiyon |
| Ön koşul | Otomatik düzeltme politikası yürürlükte; aksiyon tipi izinli listede; kaynak yazma kapsamı **dışında** |
| Akış | **Temel:** politikayı doğrula → yalnız sistemin sahibi olduğu veri üzerinde işlem yap → sonucu kaydet → doğrulama tetikle → audit. **Alternatif:** onay gerektiren tiplerde önce insan onayı istenir. **Hata:** kaynak veriye yazma gerektiren aksiyon → **her koşulda reddedilir** |
| Durum geçişi | Aksiyon `PLANNED` → `IN_PROGRESS` → `COMPLETED` \| `FAILED` |
| Yetki | Sistem aktörü; `remediation.auto.execute` politikayla sınırlı |
| Audit | `REMEDIATION_AUTO_EXECUTED` (aksiyon, tip, sonuç, politika sürümü) |
| API | `—` (iç akış) |
| Ekran | Sorunlar > Detay > Düzeltme |
| Tablo | `remediation_actions`(status, auto_executed, policy_version) |
| Test | kaynak veriye yazma reddi; izinli liste; onay gerektiren tip; audit |

##### D09.C06.W02 — Düzeltme etkisinin doğrulanması

###### D09.C06.W02.A01 — Düzeltme sonrası etkiyi ölç

| Alan | Değer |
|---|---|
| Amaç | Düzeltmenin gerçekten kaliteyi iyileştirip iyileştirmediğini sayısal olarak göstermek |
| Aktör | Sistem |
| Tetikleyici | Düzeltme aksiyonunun tamamlanması |
| Ön koşul | Düzeltme öncesi ölçüm mevcut |
| Akış | **Temel:** düzeltme sonrası doğrulama çalıştırması tetikle → önce/sonra sonuçlarını karşılaştır → etki raporu üret → soruna bağla. **Alternatif:** iyileşme yoksa aksiyon etkisiz işaretlenir ve sorun `INVESTIGATING`a döner. **Hata:** karşılaştırılabilir ölçüm yoksa etki `UNKNOWN` |
| Durum geçişi | Sorun doğrulama akışına girer |
| Yetki | Sistem aktörü |
| Audit | `REMEDIATION_IMPACT_MEASURED` (aksiyon, önce/sonra, iyileşme, etkili mi) |
| API | `GET /remediation-actions/{id}/impact` |
| Ekran | Sorunlar > Detay > Düzeltme |
| Tablo | `remediation_impacts`(action_id, before_result_id, after_result_id, improvement, verdict) |
| Test | önce/sonra karşılaştırma; etkisiz aksiyon dönüşü; karşılaştırılamaz durum; audit |

##### L5 — D09 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D09-001` | Yeterliliği `NOT_QUALIFIED` olan ölçümden kalite sorunu açılmaz |
| `BR-D09-002` | Teknik hata sorunu, kalite sorunundan ayrı tiptedir ve kalite skorunu etkilemez |
| `BR-D09-003` | Aynı tekilleştirme anahtarına sahip açık sorun için ikinci sorun açılmaz; yinelenme sayılır |
| `BR-D09-004` | Tekilleştirme anahtarı hassas veri değeri içermez |
| `BR-D09-005` | Çözümü kaydeden aktör, aynı çözümü doğrulayamaz |
| `BR-D09-006` | Doğrulama için çözüm sonrası bağımsız bir ölçüm kanıtı zorunludur |
| `BR-D09-007` | Kapatılan sorun, yeniden açma penceresi içinde aynı bozulma görülürse yeniden açılır |
| `BR-D09-008` | `CANCELLED` sorun yeniden açılamaz; yeni sorun açılır |
| `BR-D09-009` | İstisna süresiz olamaz; bitiş tarihi ve gerekçe zorunludur |
| `BR-D09-010` | İstisna talep eden aktör, aynı istisnayı onaylayamaz |
| `BR-D09-011` | İstisna ham ölçümü ve ham skoru değiştirmez; yalnız sorun üretimini ve bildirimi bastırır |
| `BR-D09-012` | Süresi dolan istisna otomatik sonlanır ve bastırma kalkar |
| `BR-D09-013` | Kök neden hipotezi, insan onayı olmadan doğrulanmış kök neden sayılmaz |
| `BR-D09-014` | Kanıt bulunmayan durumda hipotez veya öneri üretilmez |
| `BR-D09-015` | Otomatik düzeltme yalnız sistemin sahibi olduğu veri üzerinde çalışır; kaynak veriye yazamaz |
| `BR-D09-016` | Düzeltme aksiyonu kanıt referansı olmadan tamamlanmış sayılmaz |
| `BR-D09-017` | SLA sayacı yalnız tanımlı bekletme gerekçesiyle duraklatılabilir |

---

### D10 — Lineage, Etki ve Veri Sözleşmesi

Bir veri varlığının nereden geldiğini, kimin kullandığını ve kime ne söz
verildiğini yöneten domain. Kalite probleminin gerçek etkisi ancak burada ölçülür.

#### D10.C01 — Soy ağacı (lineage)

##### D10.C01.W01 — Lineage olayı alımı

###### D10.C01.W01.A01 — Lineage olayını al ve kaydet

| Alan | Değer |
|---|---|
| Amaç | Veri akışının haritasını, elle çizilmeye bağlı kalmadan oluşturmak |
| Aktör | Integration Service Account; Sistem |
| Tetikleyici | Dış işleme sisteminden lineage olayı bildirimi |
| Ön koşul | Servis hesabı `ACTIVE` ve lineage yazma yetkisine sahip; olay şeması geçerli |
| Akış | **Temel:** olayı doğrula → girdi/çıktı varlıklarını katalogla eşleştir → kenarları upsert et → olay kaydını sakla → audit. **Alternatif:** katalogda bulunmayan varlıklar "harici" olarak kaydedilir. **Hata:** şema dışı olay → reddet ve hata döndür |
| Durum geçişi | `—` |
| Yetki | `lineage.write` + kaynak kapsamı |
| Audit | `LINEAGE_EVENT_INGESTED` (olay, iş adı, girdi/çıktı sayısı, kaynak sistem) |
| API | `POST /lineage/events` — idempotency anahtarı |
| Ekran | Lineage > Olay Akışı |
| Tablo | `lineage_events`(event_id, job_name, run_id, event_type, occurred_at); `lineage_edges`(from_asset_ref, to_asset_ref, transformation, last_seen_at) |
| Test | şema doğrulama; idempotency; harici varlık; upsert; audit |

###### D10.C01.W01.A02 — Kolon düzeyi lineage kenarını kaydet

| Alan | Değer |
|---|---|
| Amaç | Etkinin dataset değil, alan düzeyinde izlenebilmesini sağlamak |
| Aktör | Integration Service Account; Sistem |
| Tetikleyici | Kolon eşleme bilgisi içeren lineage olayı |
| Ön koşul | İlgili dataset kenarı mevcut |
| Akış | **Temel:** kaynak ve hedef alanları çözümle → dönüşüm tipini kaydet → kenarı upsert et. **Alternatif:** çözümlenemeyen alan eşlemeleri "belirsiz" işaretlenir. **Hata:** dataset kenarı yoksa önce o oluşturulur |
| Durum geçişi | `—` |
| Yetki | `lineage.write` + kaynak kapsamı |
| Audit | Lineage olay kaydına gömülü: kolon kenar sayısı |
| API | `POST /lineage/events` (kolon bölümü) |
| Ekran | Lineage > Grafik |
| Tablo | `column_lineage_edges`(from_field_ref, to_field_ref, transformation_type, confidence) |
| Test | alan çözümleme; belirsiz eşleme; upsert; ardışık oluşturma |

##### D10.C01.W02 — Lineage grafı sorgulama

###### D10.C01.W02.A01 — Yukarı ve aşağı akışı sorgula

| Alan | Değer |
|---|---|
| Amaç | Bir varlığın neye dayandığını ve neyi beslediğini görünür kılmak |
| Aktör | Data Steward; Technical Data Steward; Issue Assignee |
| Tetikleyici | Katalog veya inceleme ekranından lineage görüntüleme |
| Ön koşul | Varlık üzerinde okuma kapsamı |
| Akış | **Temel:** verilen varlıktan belirtilen derinliğe kadar yukarı/aşağı kenarları gez → grafı döndür → kapsam dışı düğümleri maskeli göster. **Alternatif:** kolon düzeyi ayrıntı istenebilir. **Hata:** derinlik sınırı aşılırsa kısaltılmış graf ve uyarı döndürülür |
| Durum geçişi | `—` |
| Yetki | `lineage.read` + varlık kapsamı |
| Audit | Erişim kaydı: `LINEAGE_GRAPH_VIEWED` (varlık, yön, derinlik, düğüm sayısı) |
| API | `GET /lineage/graph` — yön, derinlik, ayrıntı parametreleri |
| Ekran | Lineage > Grafik; Katalog > Varlık Detayı |
| Tablo | `lineage_edges`, `column_lineage_edges`(okuma) |
| Test | derinlik sınırı; döngü koruması; kapsam maskeleme; erişim kaydı |

#### D10.C02 — Etki analizi

##### D10.C02.W01 — Aşağı akış etki hesaplama

###### D10.C02.W01.A01 — Kalite probleminin aşağı akış etkisini hesapla

| Alan | Değer |
|---|---|
| Amaç | "Bu bozulma kimi etkiliyor?" sorusunu tahminle değil, soy ağacıyla yanıtlamak |
| Aktör | Sistem |
| Tetikleyici | Sorun açılması; etki analizi talebi |
| Ön koşul | Lineage kenarları mevcut |
| Akış | **Temel:** bozulan varlıktan aşağı akışı gez → etkilenen dataset, rapor ve sözleşmeleri topla → her birini kritikliğiyle listele → etki genişliğini hesapla. **Alternatif:** alan düzeyi bozulmada yalnız o alanı kullanan akışlar dâhil edilir. **Hata:** lineage yoksa etki `UNKNOWN` olarak işaretlenir, sıfır sayılmaz |
| Durum geçişi | `—` |
| Yetki | `lineage.impact.read` + kapsam |
| Audit | `IMPACT_ANALYSIS_COMPUTED` (kaynak varlık, etkilenen sayı, genişlik, lineage kapsama) |
| API | `GET /lineage/impact` |
| Ekran | Sorunlar > İnceleme > Etki; Lineage > Etki |
| Tablo | `impact_analyses`(analysis_id, source_asset_ref, impacted_refs, breadth, coverage_note) |
| Test | alan düzeyi daraltma; lineage yokluğunda `UNKNOWN`; genişlik hesabı; audit |

##### D10.C02.W02 — Değişiklik etki simülasyonu

###### D10.C02.W02.A01 — Planlanan değişikliğin etkisini simüle et

| Alan | Değer |
|---|---|
| Amaç | Şema veya kural değişikliğinin kimi kıracağını, değişiklik yapılmadan önce görmek |
| Aktör | Technical Data Steward; Rule Author |
| Tetikleyici | Etki simülasyonu ekranından talep; şema değişikliği kararı öncesi |
| Ön koşul | Değişiklik tanımı verilmiş; lineage mevcut |
| Akış | **Temel:** önerilen değişikliği al → etkilenecek kural, rapor, sözleşme ve aşağı akış varlıklarını çıkar → kırıcı olanları ayrı işaretle → simülasyon raporu üret. **Alternatif:** birden çok değişiklik birlikte simüle edilir. **Hata:** lineage kapsamı düşükse rapor "eksik kapsam" uyarısıyla döner |
| Durum geçişi | `—` |
| Yetki | `lineage.impact.simulate` + kapsam |
| Audit | `IMPACT_SIMULATION_RUN` (değişiklik özeti, etkilenen sayı, kırıcı sayı) |
| API | `POST /lineage/impact-simulations` |
| Ekran | Lineage > Etki Simülasyonu; Katalog > Şema Değişiklikleri |
| Tablo | `impact_simulations`(simulation_id, change_spec, impacted_refs, breaking_refs, coverage_note) |
| Test | kırıcı tespiti; çoklu değişiklik; düşük kapsam uyarısı; audit |

#### D10.C03 — Veri sözleşmesi

##### D10.C03.W01 — Sözleşme yaşam döngüsü

###### D10.C03.W01.A01 — Veri sözleşmesi taslağı oluştur

| Alan | Değer |
|---|---|
| Amaç | Üretici ile tüketici arasındaki kalite beklentisini sözlü mutabakattan ölçülebilir taahhüde çevirmek |
| Aktör | Data Owner (üretici tarafı) |
| Tetikleyici | Sözleşme ekranından yeni sözleşme |
| Ön koşul | Konu dataset `ACTIVE`; tüketici taraflar tanımlı |
| Akış | **Temel:** dataset, tüketiciler, şema taahhüdü, kalite taahhütleri (boyut ve eşik), güncellik ve hacim beklentisi gir → ölçülebilirliği doğrula (her taahhüt bir kurala bağlanabilmeli) → `DRAFT` kaydet → audit. **Alternatif:** mevcut sözleşmeden sürüm türetilir. **Hata:** ölçülemeyen taahhüt → reddet |
| Durum geçişi | Sözleşme `—` → `DRAFT` |
| Yetki | `contract.manage` + dataset kapsamı |
| Audit | `DATA_CONTRACT_DRAFTED` (sözleşme, dataset, tüketici sayısı, taahhüt sayısı) |
| API | `POST /data-contracts` |
| Ekran | Veri Sözleşmeleri > Yeni |
| Tablo | `data_contracts`(contract_id, dataset_id, version_no, producer_owner_id, consumers, commitments, status) |
| Test | ölçülebilirlik doğrulaması; sürüm türetme; kapsam; audit |

###### D10.C03.W01.A02 — Sözleşmeyi karşılıklı onayla

| Alan | Değer |
|---|---|
| Amaç | Taahhüdün tek taraflı dayatma değil, karşılıklı kabul olmasını sağlamak |
| Aktör | Tüketici tarafı Data Owner; üretici tarafı Data Owner |
| Tetikleyici | Sözleşme onay kuyruğundan karar |
| Ön koşul | Sözleşme `DRAFT`; her iki taraf temsilcisi tanımlı |
| Akış | **Temel:** her iki taraftan da onay topla → ikisi de onayladığında `ACTIVE` yap → taahhütleri izleyen kuralları bağla → audit → bildir. **Alternatif:** tüketici karşı teklifle taslağa döndürür. **Hata:** tek taraf onayı sözleşmeyi aktive etmez |
| Durum geçişi | Sözleşme `DRAFT` → `PENDING_ACCEPTANCE` → `ACTIVE` \| `DRAFT` |
| Yetki | `contract.accept` + taraf sahipliği; görev ayrılığı (iki farklı taraf) |
| Audit | `DATA_CONTRACT_ACCEPTED` (sözleşme, onaylayan taraf, tam onay mı) |
| API | `POST /data-contracts/{id}/acceptance` — `If-Match` |
| Ekran | Veri Sözleşmeleri > Detay |
| Tablo | `data_contracts`(status, producer_accepted_at, consumer_accepted_at, version) |
| Test | çift taraflı onay; karşı teklif; tek taraf yetersizliği; audit |

###### D10.C03.W01.A03 — Sözleşmeyi sonlandır

| Alan | Değer |
|---|---|
| Amaç | Geçerliliğini yitiren taahhüdün ihlal üretmeye devam etmesini engellemek |
| Aktör | Her iki tarafın Data Owner'ı |
| Tetikleyici | Sözleşme detayından sonlandırma; halef sürüm aktivasyonu |
| Ön koşul | Sözleşme `ACTIVE` veya `BREACHED` |
| Akış | **Temel:** sonlandırma gerekçesi ve tarihi gir → karşı tarafa bildir → `TERMINATED` yap → izleme kurallarını serbest bırak → audit. **Alternatif:** yeni sürüm aktive olduğunda önceki otomatik `SUPERSEDED` olur. **Hata:** açık ihlal sorunu varsa uyarı verilir |
| Durum geçişi | `ACTIVE`\|`BREACHED` → `TERMINATED` \| `SUPERSEDED` |
| Yetki | `contract.manage` + taraf sahipliği |
| Audit | `DATA_CONTRACT_TERMINATED` (sözleşme, gerekçe, sonlandıran, açık ihlal sayısı) |
| API | `POST /data-contracts/{id}/termination` |
| Ekran | Veri Sözleşmeleri > Detay |
| Tablo | `data_contracts`(status, terminated_at, termination_reason) |
| Test | halef devri; açık ihlal uyarısı; durum-makinesi; audit |

##### D10.C03.W02 — Sözleşme uyum ölçümü

###### D10.C03.W02.A01 — Sözleşme uyumunu ölç

| Alan | Değer |
|---|---|
| Amaç | Taahhüdün gerçekten tutulup tutulmadığını sürekli ve otomatik izlemek |
| Aktör | Sistem |
| Tetikleyici | Sözleşmeye bağlı kuralların çalıştırılması; periyodik uyum değerlendirmesi |
| Ön koşul | Sözleşme `ACTIVE`; taahhütlere bağlı kural sonuçları mevcut |
| Akış | **Temel:** her taahhüt için ilgili ölçümü çöz → taahhüt değeriyle karşılaştır → taahhüt bazlı uyum durumunu üret → genel uyum oranını hesapla → kaydet. **Alternatif:** ölçüm yeterliliği düşükse o taahhüt `NOT_MEASURED` işaretlenir. **Hata:** hiçbir taahhüt ölçülemiyorsa genel uyum `UNKNOWN` |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `CONTRACT_COMPLIANCE_MEASURED` (sözleşme, uyum oranı, karşılanmayan taahhüt sayısı) |
| API | `GET /data-contracts/{id}/compliance` |
| Ekran | Veri Sözleşmeleri > Detay > Uyum |
| Tablo | `contract_compliance`(compliance_id, contract_id, commitment_key, measured_value, committed_value, verdict, measured_at) |
| Test | taahhüt eşleştirme; yeterlilik etkisi; genel oran; audit |

###### D10.C03.W02.A02 — Sözleşme uyum panosunu göster

| Alan | Değer |
|---|---|
| Amaç | Tüketicinin, bağlı olduğu verinin sözüne uyup uymadığını kendisinin görebilmesini sağlamak |
| Aktör | Tüketici tarafı roller; Data Owner |
| Tetikleyici | Sözleşme ekranı açılışı |
| Ön koşul | Sözleşme tarafı olma veya okuma kapsamı |
| Akış | **Temel:** sözleşmeleri uyum durumu, son ölçüm ve açık ihlallerle listele → taahhüt bazlı ayrıntı sun. **Alternatif:** tüketici yalnız kendi taraf olduğu sözleşmeleri görür. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `contract.read` + taraf olma veya kapsam |
| Audit | Erişim kaydı: `CONTRACT_COMPLIANCE_VIEWED` (sözleşme sayısı) |
| API | `GET /data-contracts` — filtre, sayfalama |
| Ekran | Veri Sözleşmeleri > Liste |
| Tablo | `data_contracts`, `contract_compliance`(okuma) |
| Test | taraf filtreleme; taahhüt ayrıntısı; sayfalama; erişim kaydı |

##### D10.C03.W03 — Sözleşme ihlali

###### D10.C03.W03.A01 — Sözleşme ihlalini ilan et

| Alan | Değer |
|---|---|
| Amaç | Taahhüt tutulmadığında tüketicinin zamanında haberdar olmasını ve hesabın sorulmasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Uyum ölçümünün ihlal eşiğini aşması |
| Ön koşul | Sözleşme `ACTIVE`; ihlal eşiği ve toleransı tanımlı |
| Akış | **Temel:** tolerans penceresini kontrol et → aşılmışsa sözleşmeyi `BREACHED` yap → ihlal kaydı oluştur → sorun aç → tüm taraflara bildir → audit. **Alternatif:** tolerans içindeyse yalnız uyarı üretilir. **Hata:** ölçüm yeterliliği düşükse ihlal ilan edilmez |
| Durum geçişi | Sözleşme `ACTIVE` → `BREACHED` |
| Yetki | Sistem aktörü |
| Audit | `DATA_CONTRACT_BREACHED` (sözleşme, taahhüt, ölçülen/taahhüt değer, süre) |
| API | `GET /data-contracts/{id}/breaches` |
| Ekran | Veri Sözleşmeleri > Detay; Sorunlar > Liste |
| Tablo | `contract_breaches`(breach_id, contract_id, commitment_key, measured_value, breached_at, issue_id) |
| Test | tolerans penceresi; yeterlilik ön koşulu; sorun bağı; bildirim; audit |

###### D10.C03.W03.A02 — İhlali kapat ve sözleşmeyi geri kazandır

| Alan | Değer |
|---|---|
| Amaç | Düzelen durumun sözleşme statüsüne yansımasını sağlamak |
| Aktör | Sistem; Data Owner (manuel onay) |
| Tetikleyici | Uyum ölçümünün ardışık olarak taahhüdü karşılaması |
| Ön koşul | Sözleşme `BREACHED`; geri kazanım penceresi politikada tanımlı |
| Akış | **Temel:** ardışık uyumlu ölçüm sayısını kontrol et → yeterliyse ihlali kapat → sözleşmeyi `ACTIVE` yap → taraflara bildir → audit. **Alternatif:** manuel onay gerektiren sözleşmelerde owner onayı beklenir. **Hata:** `—` |
| Durum geçişi | Sözleşme `BREACHED` → `ACTIVE`; ihlal `OPEN` → `CLOSED` |
| Yetki | Sistem aktörü; manuelde `contract.manage` |
| Audit | `DATA_CONTRACT_RECOVERED` (sözleşme, ihlal süresi, ardışık uyumlu ölçüm sayısı) |
| API | `POST /contract-breaches/{id}/closure` |
| Ekran | Veri Sözleşmeleri > Detay |
| Tablo | `contract_breaches`(status, closed_at); `data_contracts`(status) |
| Test | ardışık ölçüm sayacı; manuel onay yolu; durum-makinesi; audit |

#### D10.C04 — Kalite borcu

##### D10.C04.W01 — Kalite borcu kaydı ve takibi

###### D10.C04.W01.A01 — Kalite borcu kaydı oluştur

| Alan | Değer |
|---|---|
| Amaç | Şimdi çözülmeyen ama unutulmaması gereken kalite eksikliklerini görünür bir yükümlülük olarak tutmak |
| Aktör | Data Steward; Data Owner |
| Tetikleyici | İstisna onayı; kapatılan dead-letter; çözülmeden kapatılan sorun; manuel kayıt |
| Ön koşul | Kapsam ve gerekçe verilmiş |
| Akış | **Temel:** kapsam, açıklama, tahmini etki ve hedef çözüm dönemi gir → borcu kaydet → sahibe ata → audit. **Alternatif:** istisna onayından otomatik borç kaydı üretilir. **Hata:** hedef dönemsiz borç → reddet |
| Durum geçişi | Borç `—` → `OPEN` |
| Yetki | `quality-debt.manage` + kapsam |
| Audit | `QUALITY_DEBT_RECORDED` (borç, kapsam, kaynak, hedef dönem) |
| API | `POST /quality-debts` |
| Ekran | Kalite Borcu > Yeni |
| Tablo | `quality_debts`(debt_id, scope_type, scope_id, description, estimated_impact, target_period, owner_user_id, status, source_ref) |
| Test | otomatik türetme; hedef dönem zorunluluğu; kapsam; audit |

###### D10.C04.W01.A02 — Kalite borcu portföyünü görüntüle

| Alan | Değer |
|---|---|
| Amaç | Birikmiş kalite yükümlülüğünün toplamını ve eğilimini yönetime görünür kılmak |
| Aktör | Data Governance Admin; Data Owner; yönetici roller |
| Tetikleyici | Kalite borcu ekranı açılışı; dönemsel gözden geçirme |
| Ön koşul | Okuma kapsamı |
| Akış | **Temel:** açık borçları kapsam, etki, yaş ve hedef döneme göre listele → domain bazlı toplamları ve eğilimi göster. **Alternatif:** hedef dönemi geçmiş borçlar öne alınır. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `quality-debt.read` + kapsam |
| Audit | Erişim kaydı: `QUALITY_DEBT_PORTFOLIO_VIEWED` (filtre, toplam) |
| API | `GET /quality-debts` — sayfalama, filtre, gruplama |
| Ekran | Kalite Borcu > Liste; Genel Bakış |
| Tablo | `quality_debts`(okuma) |
| Test | gruplama; yaş hesabı; gecikmiş öne alma; erişim kaydı |

###### D10.C04.W01.A03 — Kalite borcunu kapat

| Alan | Değer |
|---|---|
| Amaç | Giderilen yükümlülüğün portföyden düşmesini ve kanıtının kalmasını sağlamak |
| Aktör | Borç sahibi; Data Governance Admin |
| Tetikleyici | Borç detayından kapatma |
| Ön koşul | Borç `OPEN`; kapanış kanıtı verilmiş |
| Akış | **Temel:** kapanış gerekçesi ve kanıt referansı gir → `CLOSED` yap → audit. **Alternatif:** çözülmeden kabul edilen borç `ACCEPTED` olarak kapatılır, gerekçe zorunlu. **Hata:** kanıtsız kapatma → reddet |
| Durum geçişi | Borç `OPEN` → `CLOSED` \| `ACCEPTED` |
| Yetki | `quality-debt.manage` + kapsam |
| Audit | `QUALITY_DEBT_CLOSED` (borç, gerekçe, kanıt, açık kalma süresi) |
| API | `POST /quality-debts/{id}/closure` |
| Ekran | Kalite Borcu > Detay |
| Tablo | `quality_debts`(status, closed_at, closure_evidence_ref) |
| Test | kanıt zorunluluğu; kabul yolu; durum-makinesi; audit |

##### L5 — D10 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D10-001` | Lineage olayları idempotenttir; aynı çalıştırma kimliğiyle tekrar gelen olay kenarları çoğaltmaz |
| `BR-D10-002` | Katalogda bulunmayan lineage varlıkları "harici" olarak kaydedilir, sessizce atılmaz |
| `BR-D10-003` | Lineage grafı sorgularında derinlik sınırı uygulanır ve döngüler kırılır |
| `BR-D10-004` | Lineage kapsamı yoksa etki `UNKNOWN` olarak raporlanır; sıfır etki sayılmaz |
| `BR-D10-005` | Kullanıcının kapsamı dışındaki lineage düğümleri maskeli gösterilir |
| `BR-D10-006` | Veri sözleşmesindeki her taahhüt ölçülebilir bir kurala bağlanabilmelidir |
| `BR-D10-007` | Sözleşme yalnız üretici ve tüketici taraflarının **her ikisinin** onayıyla aktive olur |
| `BR-D10-008` | Ölçüm yeterliliği düşükse sözleşme ihlali ilan edilmez |
| `BR-D10-009` | Sözleşme ihlali otomatik olarak bir sorun açar ve tüm taraflara bildirilir |
| `BR-D10-010` | Kalite borcu hedef çözüm dönemi olmadan kaydedilemez |
| `BR-D10-011` | Onaylanan istisna, karşılık gelen bir kalite borcu kaydı üretir |
| `BR-D10-012` | Kalite borcu kanıt referansı olmadan kapatılamaz |

---

### D11 — Analitik, Dashboard ve Raporlama

Ölçümün karar verecek kişiye ulaştığı domain. Aynı veri farklı rollere farklı
soruları yanıtlayacak biçimde sunulur; dışarı çıkan her çıktı hassasiyet
kontrolünden geçer.

#### D11.C01 — Rol bazlı dashboard

##### D11.C01.W01 — Yönetici görünümü

###### D11.C01.W01.A01 — Kurum kalite özetini göster

| Alan | Değer |
|---|---|
| Amaç | Yöneticinin kurumun kalite durumunu ve eğilimini tek ekranda kavramasını sağlamak |
| Aktör | Data Governance Admin; Data Owner; yönetici roller |
| Tetikleyici | Genel bakış ekranı açılışı; dönem filtresi değişimi |
| Ön koşul | Yayımlanmış skor mevcut; okuma kapsamı |
| Akış | **Temel:** kurum ve domain skorlarını, eğilimi, açık sorun ve risk dağılımını kapsamla filtreleyerek döndür → yayım dönemini ve politika sürümünü açıkça göster. **Alternatif:** kurum geneli kapsamı olmayan aktöre yalnız kendi kapsamının toplamı gösterilir. **Hata:** yayımlanmış skor yoksa → boş durum ve nedeni gösterilir, sıfır skor gösterilmez |
| Durum geçişi | `—` |
| Yetki | `dashboard.read` + kapsam; kurum toplamı için `can_view_enterprise` |
| Audit | Erişim kaydı: `DASHBOARD_VIEWED` (görünüm tipi, kapsam, dönem) |
| API | `GET /dashboard/summary` — dönem, kapsam, kırılım parametreleri |
| Ekran | Genel Bakış |
| Tablo | `quality_scores`, `score_publications`, `issues`, `risk_ratings`(okuma) |
| Test | kapsam daraltma; boş durum; dönem filtresi; erişim kaydı |

###### D11.C01.W01.A02 — Domain kırılımını ve bozulma sıralamasını göster

| Alan | Değer |
|---|---|
| Amaç | "Nerede sorun var?" sorusunu tek tıkla yanıtlamak |
| Aktör | Data Governance Admin; Data Owner |
| Tetikleyici | Genel bakıştan kırılım seçimi |
| Ön koşul | Domain atamaları ve skorlar mevcut |
| Akış | **Temel:** domain/dataset skorlarını önceki döneme göre değişimle sırala → en çok bozulanları öne al → her satırda açık sorun ve risk göster. **Alternatif:** iyileşme sıralaması da sunulur. **Hata:** karşılaştırılamaz dönemlerde değişim `—` gösterilir |
| Durum geçişi | `—` |
| Yetki | `dashboard.read` + kapsam |
| Audit | Erişim kaydı: `DASHBOARD_VIEWED` (kırılım tipi) |
| API | `GET /dashboard/breakdown` — sıralama, kırılım |
| Ekran | Genel Bakış > Kırılım |
| Tablo | `quality_scores`, `business_domains`, `issues`(okuma) |
| Test | değişim hesabı; karşılaştırılamaz dönem; sıralama; erişim kaydı |

##### D11.C01.W02 — Sahip/steward görünümü

###### D11.C01.W02.A01 — Sorumluluk panosunu göster

| Alan | Değer |
|---|---|
| Amaç | Sahibin, kendi varlıklarında bekleyen işi ve durumu tek yerde görmesini sağlamak |
| Aktör | Data Owner; Data Steward |
| Tetikleyici | Genel bakış ekranı açılışı |
| Ön koşul | Aktöre atanmış varlık veya sorun bulunması |
| Akış | **Temel:** sahip olduğu varlıkların skorlarını, üzerine atanmış açık sorunları, SLA riski taşıyanları, bekleyen onayları ve süresi yaklaşan istisnaları birleştir → öncelik sırasıyla döndür. **Alternatif:** iş listesi türe göre gruplanır. **Hata:** atanmış varlık yoksa boş durum ve yönlendirme gösterilir |
| Durum geçişi | `—` |
| Yetki | `dashboard.read` + kapsam ve sahiplik |
| Audit | Erişim kaydı: `DASHBOARD_VIEWED` (görünüm='OWNER') |
| API | `GET /dashboard/my-work` |
| Ekran | Genel Bakış > Sorumluluklarım |
| Tablo | `asset_ownerships`, `issues`, `issue_slas`, `approval_requests`, `exceptions`(okuma) |
| Test | sahiplik filtresi; öncelik sıralaması; boş durum; erişim kaydı |

##### D11.C01.W03 — Mühendis görünümü

###### D11.C01.W03.A01 — Teknik kalite panosunu göster

| Alan | Değer |
|---|---|
| Amaç | Teknik sorumlunun ölçüm sağlığını ve kural davranışını izleyebilmesini sağlamak |
| Aktör | Technical Data Steward; Operations User |
| Tetikleyici | Genel bakıştan teknik görünüm seçimi |
| Ön koşul | Okuma kapsamı |
| Akış | **Temel:** çalıştırma başarı oranını, teknik hata dağılımını, ölçüm yeterliliği dağılımını, yanlış alarm şüphesi taşıyan kuralları ve kaynak sağlığını birleştir → döndür. **Alternatif:** kaynak veya dataset bazlı daraltma. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `dashboard.read` + kapsam |
| Audit | Erişim kaydı: `DASHBOARD_VIEWED` (görünüm='ENGINEER') |
| API | `GET /dashboard/technical` |
| Ekran | Genel Bakış > Teknik |
| Tablo | `rule_executions`, `measurement_qualifications`, `source_health_checks`, `rule_execution_results`(okuma) |
| Test | oran hesapları; yanlış alarm sezgisi; kapsam; erişim kaydı |

#### D11.C02 — Analitik sorgulama

##### D11.C02.W01 — Trend analizi

###### D11.C02.W01.A01 — Skor eğilimini sorgula

| Alan | Değer |
|---|---|
| Amaç | Kalitenin zaman içindeki gidişatını, tek noktalık ölçümlerin yanıltmasına izin vermeden görmek |
| Aktör | Data Owner; Data Steward; yönetici roller |
| Tetikleyici | Trend paneli açılışı; dönem seçimi |
| Ön koşul | En az iki yayımlanmış dönem |
| Akış | **Temel:** kapsam ve dönem aralığı için yayım serisini getir → seriyi model/politika sürüm değişim noktalarıyla işaretle → döndür. **Alternatif:** kural kümesi değişimlerinde seri kesikli çizilir. **Hata:** yeterli nokta yoksa trend üretilmez |
| Durum geçişi | `—` |
| Yetki | `analytics.read` + kapsam |
| Audit | Erişim kaydı: `TREND_QUERIED` (kapsam, dönem aralığı) |
| API | `GET /analytics/trends` — kapsam, aralık, granülerlik |
| Ekran | Genel Bakış > Trend; Skorlar > Trend |
| Tablo | `quality_scores`, `score_publications`(okuma) |
| Test | sürüm değişim işareti; kesikli seri; yetersiz nokta; erişim kaydı |

###### D11.C02.W01.A02 — Sorun ve SLA eğilimini sorgula

| Alan | Değer |
|---|---|
| Amaç | Kalite yönetimi sürecinin kendisinin iyileşip iyileşmediğini ölçmek |
| Aktör | Data Governance Admin; Data Owner |
| Tetikleyici | Analitik ekranı |
| Ön koşul | Sorun geçmişi mevcut |
| Akış | **Temel:** dönem bazlı açılan/kapanan sorun sayısı, ortalama çözüm süresi, SLA uyum oranı ve yeniden açılma oranını hesapla → seri olarak döndür. **Alternatif:** domain veya öncelik bazlı kırılım. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `analytics.read` + kapsam |
| Audit | Erişim kaydı: `ISSUE_ANALYTICS_QUERIED` (kapsam, aralık) |
| API | `GET /analytics/issues` |
| Ekran | Analitik > Sorun Eğilimi |
| Tablo | `issues`, `issue_slas`, `issue_history`(okuma) |
| Test | çözüm süresi hesabı; yeniden açılma oranı; kırılım; erişim kaydı |

##### D11.C02.W02 — Dönem ve kapsam karşılaştırması

###### D11.C02.W02.A01 — Kapsamlar arası karşılaştırma yap

| Alan | Değer |
|---|---|
| Amaç | Domainler veya kaynaklar arasındaki kalite farkını görerek önceliklendirme yapmak |
| Aktör | Data Governance Admin; yönetici roller |
| Tetikleyici | Analitik ekranından karşılaştırma |
| Ön koşul | Karşılaştırılacak kapsamlarda yayımlanmış skor mevcut |
| Akış | **Temel:** seçilen kapsamların aynı dönemdeki skorlarını, ölçüm yeterliliğini ve kural kapsamını yan yana getir → farkı ölçüm kapsamı farkıyla birlikte sun. **Alternatif:** normalize edilmiş karşılaştırma sunulur. **Hata:** kural kümeleri çok farklıysa karşılaştırma "sınırda" işaretlenir |
| Durum geçişi | `—` |
| Yetki | `analytics.read` + tüm kapsamlar |
| Audit | Erişim kaydı: `SCOPE_COMPARISON_QUERIED` (kapsamlar, dönem) |
| API | `GET /analytics/scope-comparison` |
| Ekran | Analitik > Karşılaştırma |
| Tablo | `quality_scores`, `measurement_qualifications`(okuma) |
| Test | kapsam farkı uyarısı; normalize mod; çoklu kapsam yetkisi; erişim kaydı |

##### D11.C02.W03 — Sıralama ve kırılım

###### D11.C02.W03.A01 — Analitik sonucu dışa aktar

| Alan | Değer |
|---|---|
| Amaç | Ekrandaki analizin, kontrollü biçimde başka araçlarda kullanılabilmesini sağlamak |
| Aktör | Data Owner; Data Governance Admin; Report Consumer |
| Tetikleyici | Analitik ekranından dışa aktarma |
| Ön koşul | Görüntülenen sonuç üzerinde okuma yetkisi; dışa aktarma politikası izin veriyor |
| Akış | **Temel:** görünen sonucu seçilen biçimde üret → hassas alanları maskele → indirme kaydı oluştur → audit. **Alternatif:** büyük sonuçlar asenkron rapor akışına yönlendirilir. **Hata:** hassasiyet politikası izin vermiyorsa → reddet |
| Durum geçişi | `—` |
| Yetki | `analytics.export` + kapsam |
| Audit | `ANALYTICS_EXPORTED` (kapsam, biçim, satır sayısı, maskeleme politikası) — hassas erişim sınıfı |
| API | `POST /analytics/exports` |
| Ekran | Analitik > Dışa Aktar |
| Tablo | `export_records`(export_id, actor_id, scope, format, row_count, created_at) |
| Test | maskeleme; boyut eşiği yönlendirmesi; politika reddi; audit |

#### D11.C03 — Rapor üretimi

##### D11.C03.W01 — Rapor talebi

###### D11.C03.W01.A01 — Rapor talep et

| Alan | Değer |
|---|---|
| Amaç | Belirli bir amaç için biçimlendirilmiş, paylaşılabilir bir kalite çıktısı üretmek |
| Aktör | Report Consumer; Data Owner; Auditor |
| Tetikleyici | Rapor ekranından talep |
| Ön koşul | Rapor tipi tanımlı; parametreler geçerli; aktörün kapsamı yeterli |
| Akış | **Temel:** rapor tipi, dönem, kapsam ve biçimi seç → hassasiyet seviyesini politikadan çöz → talebi `PENDING` kaydet → üretim işini kuyruğa al → audit. **Alternatif:** küçük raporlar önizleme olarak anında gösterilir. **Hata:** kapsam dışı parametre → reddet; hassasiyet politikası yoksa → reddet |
| Durum geçişi | Rapor `—` → `PENDING` |
| Yetki | `report.request` + kapsam |
| Audit | `REPORT_REQUESTED` (rapor, tip, kapsam, biçim, hassasiyet) |
| API | `POST /reports` — idempotency anahtarı |
| Ekran | Raporlar > Yeni Rapor |
| Tablo | `reports`(report_id, report_type, format, requested_by, parameters, status, sensitivity_level, retention_policy_id, version) |
| Test | kapsam doğrulama; politika yokluğunda ret; idempotency; audit |

###### D11.C03.W01.A02 — Rapor önizlemesini göster

| Alan | Değer |
|---|---|
| Amaç | Kullanıcının yanlış parametrelerle büyük rapor üretmesini önlemek |
| Aktör | Report Consumer; Data Owner |
| Tetikleyici | Rapor formunda parametre değişimi |
| Ön koşul | Parametreler geçerli |
| Akış | **Temel:** sınırlı satır sayısıyla örnek sonuç ve tahmini boyut üret → maskeli göster. **Alternatif:** çok büyük sonuçlarda yalnız tahmini boyut gösterilir. **Hata:** kapsam dışıysa → yetkisiz |
| Durum geçişi | `—` |
| Yetki | `report.preview` + kapsam |
| Audit | Erişim kaydı: `REPORT_PREVIEWED` (tip, kapsam, satır sayısı) |
| API | `GET /reports/preview` |
| Ekran | Raporlar > Yeni Rapor |
| Tablo | `quality_scores`, `issues`, `rule_execution_results`(okuma) |
| Test | satır sınırı; boyut tahmini; maskeleme; erişim kaydı |

##### D11.C03.W02 — Asenkron rapor üretimi

###### D11.C03.W02.A01 — Raporu asenkron üret

| Alan | Değer |
|---|---|
| Amaç | Büyük raporların istek zaman aşımına takılmadan ve sistemi tıkamadan üretilmesini sağlamak |
| Aktör | Sistem |
| Tetikleyici | Rapor işinin kuyruktan sahiplenilmesi |
| Ön koşul | Rapor `PENDING`; hassasiyet politikası çözümlenmiş |
| Akış | **Temel:** durumu `GENERATING` yap → veriyi talep edenin kapsamıyla sorgula → maskelemeyi uygula → dosyayı üret ve sakla → `READY` yap → talep edene bildir → audit. **Alternatif:** boş sonuçta rapor yine üretilir, boş olduğu belirtilir. **Hata:** üretim başarısızsa `FAILED` ve neden kaydedilir; iş yeniden denenir |
| Durum geçişi | Rapor `PENDING` → `GENERATING` → `READY` \| `FAILED` |
| Yetki | Sistem aktörü; talep edenin kapsamı devralınır |
| Audit | `REPORT_GENERATED` (rapor, süre, satır sayısı, dosya boyutu, maskeleme politikası) |
| API | `GET /reports/{id}` (durum takibi) |
| Ekran | Raporlar > Liste |
| Tablo | `reports`(status, file_reference, file_size, completed_at, failure_reason) |
| Test | kapsam devralma; maskeleme; boş sonuç; başarısızlık ve yeniden deneme; audit |

###### D11.C03.W02.A02 — Rapor üretimini iptal et

| Alan | Değer |
|---|---|
| Amaç | Yanlış talep edilmiş büyük raporun kaynak tüketmeye devam etmesini engellemek |
| Aktör | Talep eden; Operations User |
| Tetikleyici | Rapor listesinden iptal |
| Ön koşul | Rapor `PENDING` veya `GENERATING` |
| Akış | **Temel:** iptal işaretle → üretim işini iptal et → kısmi dosyayı sil → `CANCELLED` → audit. **Hata:** tamamlanmış rapor → idempotent başarı |
| Durum geçişi | `PENDING`\|`GENERATING` → `CANCELLED` |
| Yetki | `report.cancel` + talep sahipliği veya kurum geneli scope |
| Audit | `REPORT_CANCELLED` (rapor, aşama, iptal eden) |
| API | `POST /reports/{id}/cancellation` |
| Ekran | Raporlar > Liste |
| Tablo | `reports`(status, cancelled_at) |
| Test | kısmi dosya temizliği; idempotency; sahiplik; audit |

##### D11.C03.W03 — Rapor zamanlaması

###### D11.C03.W03.A01 — Rapor zamanlaması tanımla

| Alan | Değer |
|---|---|
| Amaç | Düzenli raporların elle talep edilmeden ve unutulmadan üretilmesini sağlamak |
| Aktör | Report Consumer; Data Owner |
| Tetikleyici | Rapor zamanlama ekranından yeni tanım |
| Ön koşul | Rapor tipi ve parametreler geçerli; alıcılar tanımlı |
| Akış | **Temel:** tip, parametre, tekrar deseni, zaman dilimi ve alıcıları gir → alıcıların kapsam yetkisini doğrula → sonraki çalışma anını hesapla → `ACTIVE` kaydet → audit. **Alternatif:** tek seferlik zamanlama. **Hata:** kapsamı yetersiz alıcı → reddet veya alıcıdan çıkar |
| Durum geçişi | Zamanlama `—` → `ACTIVE` |
| Yetki | `report.schedule.manage` + kapsam |
| Audit | `REPORT_SCHEDULE_CREATED` (zamanlama, tip, desen, alıcı sayısı) |
| API | `POST /report-schedules` |
| Ekran | Raporlar > Zamanlamalar > Yeni |
| Tablo | `report_schedules`(schedule_id, name, report_type, format, parameters, sensitivity_level, recipients, schedule_type, timezone_name, next_run_at, is_active) |
| Test | alıcı kapsam doğrulaması; zaman dilimi; sonraki an; audit |

###### D11.C03.W03.A02 — Vadesi gelen rapor zamanlamalarını tetikle

| Alan | Değer |
|---|---|
| Amaç | Zamanlanmış raporların gerçekten ve tam bir kez üretilmesini sağlamak |
| Aktör | Sistem |
| Tetikleyici | Zamanlayıcı döngüsü |
| Ön koşul | Zamanlayıcı çalışıyor |
| Akış | **Temel:** vadesi gelenleri kilitleyerek seç → her biri için rapor talebi aç → sonraki anı ilerlet → audit. **Alternatif:** kaçırılan çalışmalar politikaya göre telafi edilir veya atlanır. **Hata:** talep açılamazsa sonraki an ilerletilmez |
| Durum geçişi | Rapor `—` → `PENDING` |
| Yetki | Sistem aktörü |
| Audit | `REPORT_SCHEDULE_TRIGGERED` (zamanlama, rapor, planlanan/gerçek an) |
| API | `—` (zamanlayıcı) |
| Ekran | Raporlar > Zamanlamalar |
| Tablo | `report_schedules`(next_run_at, last_triggered_at); `reports` |
| Test | tam-bir-kez; çoklu zamanlayıcı yarışı; kaçırılan çalışma; audit |

###### D11.C03.W03.A03 — Rapor zamanlamasını duraklat veya sil

| Alan | Değer |
|---|---|
| Amaç | Gereksiz hâle gelen düzenli raporların üretilmeye devam etmesini önlemek |
| Aktör | Zamanlamayı oluşturan; Data Owner |
| Tetikleyici | Zamanlama detayından duraklatma/silme |
| Ön koşul | Zamanlama `ACTIVE` veya `PAUSED` |
| Akış | **Temel:** gerekçe gir → durumu değiştir → sürdürmede sonraki anı yeniden hesapla → audit. **Alternatif:** silme yerine duraklatma önerilir. **Hata:** `—` |
| Durum geçişi | `ACTIVE` ↔ `PAUSED`; → `DELETED` |
| Yetki | `report.schedule.manage` + sahiplik veya kapsam |
| Audit | `REPORT_SCHEDULE_STATE_CHANGED` (zamanlama, eski/yeni durum, gerekçe) |
| API | `PATCH /report-schedules/{id}`; `DELETE /report-schedules/{id}` |
| Ekran | Raporlar > Zamanlamalar |
| Tablo | `report_schedules`(is_active, status, next_run_at) |
| Test | sonraki an yeniden hesabı; sahiplik; durum-makinesi; audit |

#### D11.C04 — Güvenli dağıtım

##### D11.C04.W01 — Maskeleme ve hassasiyet kontrolü

###### D11.C04.W01.A01 — Rapor içeriğine hassasiyet politikasını uygula

| Alan | Değer |
|---|---|
| Amaç | Raporun, alıcının görmeye yetkili olmadığı veriyi taşımasını engellemek |
| Aktör | Sistem |
| Tetikleyici | Rapor üretimi |
| Ön koşul | Alan sınıflandırmaları ve dışa aktarma politikası mevcut |
| Akış | **Temel:** rapordaki her alanı sınıflandırmasıyla eşleştir → politikaya göre maskele, toplulaştır veya çıkar → uygulanan politikayı rapora damgala. **Alternatif:** yüksek hassasiyetli rapor tipi için ek onay istenir. **Hata:** sınıflandırılmamış alan → hassas kabul edilip maskelenir; politika yoksa → rapor üretilmez |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | Rapor üretim kaydına gömülü: maskelenen alan sayısı, politika sürümü |
| API | `—` |
| Ekran | Raporlar > Detay (maskeleme rozeti) |
| Tablo | `reports`(masking_policy_version, masked_field_count) |
| Test | her sınıf için davranış; sınıflandırılmamış alan; politika yokluğunda üretmeme |

##### D11.C04.W02 — İndirme ve erişim kaydı

###### D11.C04.W02.A01 — Raporu güvenli indir

| Alan | Değer |
|---|---|
| Amaç | Üretilmiş çıktının yalnız yetkili kişiye, sınırlı süreyle ve iz bırakarak ulaşmasını sağlamak |
| Aktör | Talep eden; zamanlanmış rapor alıcıları |
| Tetikleyici | Rapor listesinden indirme |
| Ön koşul | Rapor `READY`; süre dolmamış; aktör talep eden veya tanımlı alıcı |
| Akış | **Temel:** yetkiyi ve süreyi doğrula → kısa ömürlü indirme yetkisi üret → dosyayı ilet → indirme kaydı oluştur → audit. **Alternatif:** indirme sayısı politikayla sınırlanabilir. **Hata:** süresi dolmuş rapor → `EXPIRED` bilgisi ve yeniden talep önerisi |
| Durum geçişi | `—` (indirme sayacı artar) |
| Yetki | `report.download` + talep sahipliği veya alıcı olma |
| Audit | `REPORT_DOWNLOADED` (rapor, aktör, boyut, indirme sırası) — hassas erişim sınıfı |
| API | `GET /reports/{id}/download` |
| Ekran | Raporlar > Liste |
| Tablo | `reports`(download_count, last_downloaded_at); `report_downloads`(report_id, actor_id, downloaded_at) |
| Test | süre dolumu; alıcı olmayan reddi; indirme sınırı; hassas erişim kaydı |

###### D11.C04.W02.A02 — Rapor listesini ve durumunu görüntüle

| Alan | Değer |
|---|---|
| Amaç | Kullanıcının talep ettiği raporların durumunu takip edebilmesini sağlamak |
| Aktör | Report Consumer; Data Owner; Auditor |
| Tetikleyici | Raporlar ekranı açılışı |
| Ön koşul | Okuma yetkisi |
| Akış | **Temel:** aktörün talep ettiği veya alıcısı olduğu raporları durum, tip, dönem ve son kullanma ile listele. **Alternatif:** denetim rolü tüm raporların metadata'sını görebilir, içeriğini değil. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `report.read` + sahiplik/alıcılık; denetim için `report.read.all` |
| Audit | Erişim kaydı: `REPORT_LIST_VIEWED` (filtre, sonuç sayısı) |
| API | `GET /reports` — sayfalama, filtre |
| Ekran | Raporlar > Liste |
| Tablo | `reports`(okuma) |
| Test | sahiplik filtresi; denetim metadata erişimi; sayfalama; erişim kaydı |

##### D11.C04.W03 — Dosya yaşam sonu

###### D11.C04.W03.A01 — Süresi dolan rapor dosyasını imha et

| Alan | Değer |
|---|---|
| Amaç | Hassas çıktıların gereğinden uzun süre erişilebilir kalmasını engellemek |
| Aktör | Sistem |
| Tetikleyici | Rapor son kullanma denetimi zamanlayıcısı |
| Ön koşul | Rapor `READY`; `expires_at` geçmiş; yasal muhafaza yok |
| Akış | **Temel:** dosyayı geri döndürülemez biçimde sil → rapor kaydını `EXPIRED` yap → **metadata'yı sakla** (kim, ne zaman, ne talep etti) → audit. **Alternatif:** yasal muhafaza varsa imha ertelenir ve işaretlenir. **Hata:** dosya silinemezse yeniden denenir ve operatöre bildirilir |
| Durum geçişi | Rapor `READY` → `EXPIRED` |
| Yetki | Sistem aktörü |
| Audit | `REPORT_FILE_DESTROYED` (rapor, dosya referansı, saklama politikası, muhafaza var mı) |
| API | `—` (zamanlanmış iş) |
| Ekran | Raporlar > Liste (süresi dolmuş gösterimi) |
| Tablo | `reports`(status, file_reference=null, destroyed_at) |
| Test | metadata korunumu; yasal muhafaza ertelemesi; silme başarısızlığı; audit |

##### L5 — D11 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D11-001` | Dashboard ve analitik sorguları aktörün kapsamıyla daraltılır; kapsam dışı veri toplamlara girmez |
| `BR-D11-002` | Yayımlanmış skor yoksa boş durum gösterilir; sıfır skor gösterilmez |
| `BR-D11-003` | Her skor gösterimi, dayandığı yayım dönemini ve politika sürümünü taşır |
| `BR-D11-004` | Farklı kural kümesi veya politika sürümüne sahip dönemler arasındaki değişim "sınırda" işaretlenir |
| `BR-D11-005` | Rapor, talep edenin kapsamıyla üretilir; alıcı kapsamı daha darsa içerik ona göre kısılır |
| `BR-D11-006` | Dışa aktarma politikası yürürlükte değilse rapor veya dışa aktarma üretilmez |
| `BR-D11-007` | Sınıflandırılmamış alanlar raporlarda hassas kabul edilerek maskelenir |
| `BR-D11-008` | Her rapor, uygulanan maskeleme politikası sürümüyle damgalanır |
| `BR-D11-009` | Rapor indirme hassas erişim olarak ayrıca kaydedilir |
| `BR-D11-010` | Süresi dolan rapor dosyası imha edilir; talep metadata'sı saklanır |
| `BR-D11-011` | Yasal muhafaza altındaki rapor dosyası imha edilmez |
| `BR-D11-012` | Rapor zamanlaması alıcılarının kapsam yetkisi tanım anında doğrulanır |

---

### D12 — Bildirim ve Dış Entegrasyon

Sistemin dış dünyayla konuştuğu domain. Bildirimin üretilmesi ile teslim edilmesi
ayrı sorumluluklardır; teslimatın kendisi de izlenmesi gereken bir durumdur.

#### D12.C01 — Bildirim olayı üretimi

##### D12.C01.W01 — Olay yayımlama

###### D12.C01.W01.A01 — Bildirim olayı yayımla

| Alan | Değer |
|---|---|
| Amaç | Sistemde olan biteni, kanal ayrıntısından bağımsız bir olay olarak kayda geçirmek |
| Aktör | Sistem |
| Tetikleyici | Sorun açılması, atama, SLA riski, eskalasyon, onay talebi, sözleşme ihlali, rapor hazır olması gibi tanımlı olaylar |
| Ön koşul | Olay tipi bildirim kataloğunda tanımlı |
| Akış | **Temel:** olayı, kaynak nesne referansı ve veri-minimum yükle **iş transaction'ıyla aynı anda** yaz → aboneleri çöz → teslimat kayıtları üret. **Alternatif:** abonesi olmayan olay yalnız kaydedilir. **Hata:** katalogda tanımsız olay tipi → yayımlanmaz, yapılandırma hatası kaydedilir |
| Durum geçişi | Olay `—` → `PUBLISHED` |
| Yetki | Sistem aktörü |
| Audit | `NOTIFICATION_EVENT_PUBLISHED` (olay tipi, kaynak nesne, alıcı sayısı) |
| API | `GET /notifications/events` (görünürlük) |
| Ekran | Bildirimler > Olay Akışı |
| Tablo | `notification_events`(event_id, event_type, source_ref, payload, published_at) |
| Test | transaction atomikliği; abonesiz olay; tanımsız tip; veri minimizasyonu |

###### D12.C01.W01.A02 — Bildirim yükünü veri-minimum tut

| Alan | Değer |
|---|---|
| Amaç | Bildirimlerin, kanal güvenliği zayıf olsa bile hassas veri sızdırmamasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Bildirim olayı üretimi |
| Ön koşul | Bildirim maskeleme politikası yürürlükte |
| Akış | **Temel:** yüke yalnız nesne referansı, tip, önem ve sisteme dönüş bağlantısını koy → hiçbir kayıt değeri veya kanıt örneği ekleme. **Alternatif:** iç kanallarda politika izin verirse özet bilgi eklenebilir. **Hata:** yükte hassas alan tespit edilirse olay yayımlanmaz |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | İhlal girişiminde `NOTIFICATION_PAYLOAD_REJECTED` (olay tipi, tespit edilen alan) |
| API | `—` |
| Ekran | `—` |
| Tablo | `notification_events`(payload) |
| Test | hassas alan tespiti; kanal bazlı politika; referans yeterliliği |

##### D12.C01.W02 — Abonelik ve tercih yönetimi

###### D12.C01.W02.A01 — Bildirim aboneliği tanımla

| Alan | Değer |
|---|---|
| Amaç | Kullanıcıların ilgilendikleri olayları, ilgilenmediklerinin gürültüsü olmadan almasını sağlamak |
| Aktör | Tüm kullanıcı rolleri (kendi aboneliği); Platform Admin (varsayılan abonelikler) |
| Tetikleyici | Profil veya yönetim ekranından abonelik düzenleme |
| Ön koşul | Olay tipi katalogda; kanal yapılandırılmış |
| Akış | **Temel:** olay tipi, kapsam ve kanal seç → abonelik kaydet → audit. **Alternatif:** rol bazlı varsayılan abonelikler tanımlanır ve kullanıcı bunları geçersiz kılabilir. **Hata:** zorunlu bildirim tiplerinden çıkılamaz |
| Durum geçişi | Abonelik `—` → `ACTIVE` |
| Yetki | `notification.subscription.manage` (kendi) veya `notification.subscription.manage.all` |
| Audit | `NOTIFICATION_SUBSCRIPTION_CHANGED` (kullanıcı, olay tipi, kanal, kapsam) |
| API | `PUT /users/{id}/notification-subscriptions` |
| Ekran | Profil > Bildirim Tercihleri; Yönetim > Bildirimler |
| Tablo | `notification_subscriptions`(subscription_id, user_id, event_type, scope_type, scope_id, channel, status) |
| Test | zorunlu tip koruması; rol varsayılanı; geçersiz kılma; audit |

###### D12.C01.W02.A02 — Bildirimleri görüntüle ve okundu işaretle

| Alan | Değer |
|---|---|
| Amaç | Kullanıcının kendisine ulaşan bildirimleri sistem içinde takip edebilmesini sağlamak |
| Aktör | Tüm kullanıcı rolleri |
| Tetikleyici | Bildirim panelinin açılması |
| Ön koşul | Kullanıcıya teslim edilmiş bildirim bulunması |
| Akış | **Temel:** okunmamışları öne alarak listele → okundu işaretlemeyi kaydet → sayaç güncelle. **Alternatif:** toplu okundu işaretleme. **Hata:** başka kullanıcının bildirimine erişim → reddet |
| Durum geçişi | Bildirim `DELIVERED` → `READ` |
| Yetki | Bildirim sahipliği |
| Audit | Erişim kaydı gerekmez; okundu işareti bildirim kaydında tutulur |
| API | `GET /notifications`; `POST /notifications/{id}/read` |
| Ekran | Üst çubuk > Bildirimler |
| Tablo | `notification_deliveries`(status, read_at) |
| Test | sahiplik izolasyonu; toplu işaretleme; sayaç doğruluğu |

#### D12.C02 — Kanal ve teslimat

##### D12.C02.W01 — Kanal yapılandırması

###### D12.C02.W01.A01 — Bildirim kanalı yapılandır

| Alan | Değer |
|---|---|
| Amaç | Bildirimlerin kurumun kullandığı iletişim araçlarına ulaşabilmesini sağlamak |
| Aktör | Platform Admin |
| Tetikleyici | Yönetim ekranından kanal ekleme |
| Ön koşul | Kanal tipi destekleniyor; kimlik bilgisi sır referansı olarak verilmiş |
| Akış | **Temel:** kanal tipi, hedef ve sır referansını gir → bağlantıyı test et → `ACTIVE` yap → audit. **Alternatif:** kanal belirli olay tipleriyle sınırlanabilir. **Hata:** sır değeri doğrudan girilirse → reddet; test başarısızsa → `INACTIVE` |
| Durum geçişi | Kanal `—` → `ACTIVE` \| `INACTIVE` |
| Yetki | `notification.channel.manage` + kurum geneli scope |
| Audit | `NOTIFICATION_CHANNEL_CONFIGURED` (kanal, tip, test sonucu — sır asla) |
| API | `POST /notification-channels` |
| Ekran | Yönetim > Bildirim Kanalları |
| Tablo | `notification_channels`(channel_id, channel_type, target_config, secret_ref, allowed_event_types, status) |
| Test | sır sızdırma reddi; bağlantı testi; olay tipi sınırı; audit |

##### D12.C02.W02 — Teslimat ve yeniden deneme

###### D12.C02.W02.A01 — Bildirimi teslim et

| Alan | Değer |
|---|---|
| Amaç | Üretilen bildirimin gerçekten alıcıya ulaşmasını ve ulaşmadığında bunun bilinmesini sağlamak |
| Aktör | Sistem |
| Tetikleyici | Teslimat kaydının kuyruktan sahiplenilmesi |
| Ön koşul | Kanal `ACTIVE`; teslimat `PENDING` |
| Akış | **Temel:** kanal adaptörünü çağır → yanıtı değerlendir → başarıda `DELIVERED`, geçici hatada yeniden denemeye al → audit. **Alternatif:** aynı olay için birden çok kanala paralel teslimat. **Hata:** kalıcı hatada `FAILED`; deneme sınırı aşımında `UNDELIVERABLE` |
| Durum geçişi | Teslimat `PENDING` → `SENDING` → `DELIVERED` \| `FAILED` → `UNDELIVERABLE` |
| Yetki | Sistem aktörü |
| Audit | `NOTIFICATION_DELIVERY_ATTEMPTED` (teslimat, kanal, sonuç, deneme no) |
| API | `GET /notifications/deliveries` |
| Ekran | Bildirimler > Teslimat Durumu |
| Tablo | `notification_deliveries`(delivery_id, event_id, recipient_user_id, channel_id, status, attempt_count, last_error_class) |
| Test | geçici/kalıcı hata; deneme sınırı; çoklu kanal; idempotent teslimat; audit |

###### D12.C02.W02.A02 — Teslim edilemeyen bildirimi ele al

| Alan | Değer |
|---|---|
| Amaç | Kritik bildirimlerin sessizce kaybolmasını engellemek |
| Aktör | Sistem; Operations User |
| Tetikleyici | Teslimatın `UNDELIVERABLE` olması |
| Ön koşul | Deneme sınırı aşılmış |
| Akış | **Temel:** teslimatı işaretle → alternatif kanal tanımlıysa oraya yönlendir → yoksa sistem içi bildirime düşür → operatöre bildir → audit. **Alternatif:** kritik olay tiplerinde eskalasyon tetiklenir. **Hata:** `—` |
| Durum geçişi | Teslimat `FAILED` → `UNDELIVERABLE` → `REROUTED` |
| Yetki | Sistem aktörü; manuel müdahalede `notification.delivery.manage` |
| Audit | `NOTIFICATION_UNDELIVERABLE` (teslimat, kanal, hata sınıfı, yönlendirme) |
| API | `POST /notification-deliveries/{id}/reroute` |
| Ekran | Operasyon > Bildirim Teslimatı |
| Tablo | `notification_deliveries`(status, rerouted_to_channel_id) |
| Test | alternatif kanal; sistem içi düşürme; kritik eskalasyon; audit |

##### D12.C02.W03 — Teslimat izleme

###### D12.C02.W03.A01 — Teslimat durumunu izle

| Alan | Değer |
|---|---|
| Amaç | Bildirim altyapısının sağlığını ve hangi bildirimlerin ulaşmadığını görünür kılmak |
| Aktör | Operations User; Platform Admin |
| Tetikleyici | Operasyon ekranı açılışı |
| Ön koşul | Okuma yetkisi |
| Akış | **Temel:** teslimatları kanal, durum ve olay tipine göre grupla → başarısızlık oranını ve bekleyen kuyruğu göster. **Alternatif:** belirli bir olay veya kullanıcıya göre filtre. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `notification.delivery.read` + kurum geneli scope |
| Audit | Erişim kaydı: `NOTIFICATION_DELIVERY_VIEWED` (filtre) |
| API | `GET /notification-deliveries` — sayfalama, filtre, gruplama |
| Ekran | Operasyon > Bildirim Teslimatı |
| Tablo | `notification_deliveries`, `notification_channels`(okuma) |
| Test | gruplama; oran hesabı; sayfalama; erişim kaydı |

#### D12.C03 — Dış sistem entegrasyonu

##### D12.C03.W01 — Giden entegrasyon

###### D12.C03.W01.A01 — Dış sistemde kayıt (bilet) oluştur

| Alan | Değer |
|---|---|
| Amaç | Kalite sorunlarının kurumun mevcut iş takip sürecine girmesini sağlamak |
| Aktör | Sistem; Issue Assignee (manuel tetikleme) |
| Tetikleyici | Sorun açılması ve entegrasyon kuralının eşleşmesi; manuel gönderim |
| Ön koşul | Entegrasyon `ACTIVE`; alan eşlemesi tanımlı; sorun kapsamı uygun |
| Akış | **Temel:** sorun alanlarını dış şemaya eşle → veri-minimum yükle idempotency anahtarıyla gönder → dönen dış kimliği sorunla ilişkilendir → audit. **Alternatif:** eşleşme kuralı yoksa gönderim yapılmaz. **Hata:** geçici hatada yeniden denenir; kalıcı hatada entegrasyon kaydı `FAILED` ve operatöre bildirilir |
| Durum geçişi | Entegrasyon kaydı `—` → `PENDING` → `SENT` \| `FAILED` |
| Yetki | `integration.outbound.execute`; manuelde `integration.outbound.trigger` + kapsam |
| Audit | `INTEGRATION_RECORD_SENT` (entegrasyon, sorun, dış kimlik, idempotency anahtarı) |
| API | `POST /issues/{id}/integrations` |
| Ekran | Sorunlar > Detay > Entegrasyon |
| Tablo | `integration_records`(record_id, integration_id, source_ref, external_id, status, idempotency_key, attempt_count) |
| Test | idempotency (mükerrer bilet açmama); alan eşleme; veri minimizasyonu; yeniden deneme; audit |

###### D12.C03.W01.A02 — Dış kaydı güncelle

| Alan | Değer |
|---|---|
| Amaç | Sorun durumu değiştiğinde dış sistemdeki karşılığının da güncel kalmasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Sorun durumu, atama veya öncelik değişimi |
| Ön koşul | Bağlı dış kayıt mevcut ve açık |
| Akış | **Temel:** değişimi dış şemaya eşle → güncelleme gönder → sonucu kaydet. **Alternatif:** kapatmada dış kayıt da kapatılır. **Hata:** dış kayıt bulunamazsa ilişki koparılır ve işaretlenir |
| Durum geçişi | Entegrasyon kaydı `SENT` → `UPDATED` \| `ORPHANED` |
| Yetki | Sistem aktörü |
| Audit | `INTEGRATION_RECORD_UPDATED` (kayıt, değişim tipi, sonuç) |
| API | `—` (iç akış) |
| Ekran | Sorunlar > Detay > Entegrasyon |
| Tablo | `integration_records`(status, last_synced_at) |
| Test | durum eşleme; kapatma yayılımı; kopmuş ilişki; audit |

##### D12.C03.W02 — Gelen geri bildirim uzlaştırma

###### D12.C03.W02.A01 — Dış sistemden gelen güncellemeyi uzlaştır

| Alan | Değer |
|---|---|
| Amaç | Dış sistemde yapılan işin sistemde de görünmesini ve iki tarafın ayrışmamasını sağlamak |
| Aktör | Integration Service Account |
| Tetikleyici | Dış sistemden geri bildirim çağrısı; periyodik senkronizasyon |
| Ön koşul | Servis hesabı yetkili; dış kimlik bilinen bir kayda karşılık geliyor |
| Akış | **Temel:** dış kimlikten sorunu bul → izinli alan değişikliklerini uygula → çakışmada sistem durumunu koru ve işaretle → audit. **Alternatif:** yalnız yorum ve durum bilgisi kabul edilir. **Hata:** bilinmeyen dış kimlik → reddet ve kaydet |
| Durum geçişi | Sorun alanları güncellenebilir; çakışmada `RECONCILIATION_CONFLICT` işareti |
| Yetki | `integration.inbound.write` |
| Audit | `INTEGRATION_INBOUND_RECONCILED` (kayıt, uygulanan değişiklikler, çakışma var mı) |
| API | `POST /integrations/{id}/callbacks` |
| Ekran | Sorunlar > Detay > Entegrasyon |
| Tablo | `integration_records`(last_inbound_at); `issues`(güncellenen alanlar) |
| Test | izinli alan sınırı; çakışma çözümü; bilinmeyen kimlik; yetki; audit |

#### D12.C04 — Programatik erişim

##### D12.C04.W01 — Servis hesabı erişimi

###### D12.C04.W01.A01 — Programatik istemciyi kimliklendir ve yetkilendir

| Alan | Değer |
|---|---|
| Amaç | Otomasyonların sisteme, insan kullanıcılarla aynı yetki disiplini altında erişmesini sağlamak |
| Aktör | Integration Service Account |
| Tetikleyici | API çağrısı |
| Ön koşul | Servis hesabı `ACTIVE`; kimlik bilgisi geçerli ve süresi dolmamış |
| Akış | **Temel:** kimlik bilgisini doğrula → hesabın rol ve kapsamını çözümle → istek bağlamına yerleştir → normal yetki kontrolüne devam et. **Alternatif:** kimlik bilgisi döndürme geçiş süresindeyse eski değer de kabul edilir. **Hata:** süresi dolmuş hesap → reddet ve sahibine bildir |
| Durum geçişi | `—` |
| Yetki | Servis hesabına atanmış rol ve kapsam |
| Audit | Reddedilen erişimlerde `AUTHORIZATION_DENIED`; başarılı çağrılar işlem audit'ine aktör olarak yazılır |
| API | Tüm API uçlarında ortak kimliklendirme |
| Ekran | `—` |
| Tablo | `service_accounts`(okuma) |
| Test | süre dolumu; geçiş süresi; kapsam uygulaması; ret kaydı |

##### D12.C04.W02 — Kota ve hız sınırı

###### D12.C04.W02.A01 — API hız sınırını uygula

| Alan | Değer |
|---|---|
| Amaç | Tek bir istemcinin sistemi aşırı yükleyerek diğerlerini etkilemesini engellemek |
| Aktör | Sistem |
| Tetikleyici | Her API isteği |
| Ön koşul | Hız sınırı politikası yürürlükte |
| Akış | **Temel:** istemci başına pencere içindeki istek sayısını izle → sınır altındaysa geçir → aşımda reddet ve yeniden deneme süresi bildir. **Alternatif:** kritik uçlar için ayrı sınırlar. **Hata:** politika yoksa varsayılan koruyucu sınır uygulanır |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `RATE_LIMIT_EXCEEDED` (istemci, uç, pencere, sayaç) |
| API | Tüm uçlarda ortak; aşımda standart hata ve yeniden deneme başlığı |
| Ekran | `—` |
| Tablo | `rate_limit_counters`(client_ref, window_start, request_count) |
| Test | pencere kayması; uç bazlı sınır; varsayılan koruma; ret sözleşmesi; audit |

##### L5 — D12 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D12-001` | Bildirim olayı, onu doğuran iş transaction'ıyla aynı anda yazılır |
| `BR-D12-002` | Bildirim yükü veri-minimumdur; kayıt değeri veya kanıt örneği taşımaz |
| `BR-D12-003` | Yükünde hassas alan tespit edilen bildirim yayımlanmaz |
| `BR-D12-004` | Kanal kimlik bilgileri yalnız sır referansı olarak saklanır |
| `BR-D12-005` | Teslimat, bildirim üretiminden ayrı bir durum makinesine sahiptir |
| `BR-D12-006` | Teslim edilemeyen kritik bildirim alternatif kanala veya sistem içi bildirime düşürülür |
| `BR-D12-007` | Zorunlu bildirim tiplerinden abonelikten çıkılamaz |
| `BR-D12-008` | Giden entegrasyon idempotency anahtarı taşır; aynı sorun için mükerrer dış kayıt açılmaz |
| `BR-D12-009` | Gelen geri bildirim yalnız izinli alanları değiştirebilir; çakışmada sistem durumu korunur |
| `BR-D12-010` | Servis hesapları insan kullanıcılarla aynı yetki ve kapsam kontrolünden geçer |
| `BR-D12-011` | Hız sınırı politikası yoksa varsayılan koruyucu sınır uygulanır |

---

### D13 — Audit, Kanıt ve Saklama

Sistemin kendi davranışının hesabını verdiği domain. Audit izi yalnız bir günlük
değil, bütünlüğü kanıtlanabilir ve saklama süresi yönetilen bir kayıt varlığıdır.

#### D13.C01 — Audit izi

##### D13.C01.W01 — Audit olayı kaydı

###### D13.C01.W01.A01 — Audit olayını iş transaction'ıyla birlikte kaydet

| Alan | Değer |
|---|---|
| Amaç | "İş oldu ama kaydı yok" veya "kayıt var ama iş olmadı" durumlarının yapısal olarak imkânsız olmasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Durum değiştiren her işlem |
| Ön koşul | Olay tipi audit kataloğunda tanımlı; redaksiyon politikası yürürlükte |
| Akış | **Temel:** olayı hazırla → redaksiyonu uygula → **iş verisiyle aynı transaction'da** outbox'a yaz → transaction commit ile birlikte kalıcılaş. **Alternatif:** okuma işlemlerinde erişim kaydı olarak yazılır. **Hata:** audit yazılamıyorsa iş transaction'ı da geri alınır — fail-closed |
| Durum geçişi | Audit olayı `—` → `PENDING` (outbox) |
| Yetki | Sistem aktörü |
| Audit | Olayın kendisi |
| API | `—` (iç servis) |
| Ekran | `—` |
| Tablo | `audit_outbox`(event_id, prepared_event, policy_version, status, created_at) |
| Test | transaction atomikliği; audit başarısızlığında iş geri alma; redaksiyon; katalog dışı tip |

###### D13.C01.W01.A02 — Audit kaydına hash zinciri uygula

| Alan | Değer |
|---|---|
| Amaç | Audit kaydının sonradan değiştirildiğinin tespit edilebilmesini sağlamak |
| Aktör | Sistem |
| Tetikleyici | Audit olayının kalıcı deftere yazılması |
| Ön koşul | Önceki olayın hash'i bilinir |
| Akış | **Temel:** önceki olay hash'ini al → mevcut olay içeriğiyle birlikte hash hesapla → sıra numarası ve hash'lerle yaz. **Alternatif:** ilk kayıt için sabit başlangıç hash'i kullanılır. **Hata:** zincir kopukluğu tespit edilirse yazma reddedilir ve olay bildirilir |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | Zincir kopukluğunda `AUDIT_CHAIN_BROKEN` |
| API | `—` |
| Ekran | Denetim > Bütünlük |
| Tablo | `audit_events`(sequence_no, event_hash, previous_event_hash) |
| Test | zincir sürekliliği; ilk kayıt; eşzamanlı yazma sırası; kopukluk tespiti |

###### D13.C01.W01.A03 — Hassas alanları redakte et

| Alan | Değer |
|---|---|
| Amaç | Audit kaydının kendisinin bir veri sızıntısı kaynağına dönüşmesini engellemek |
| Aktör | Sistem |
| Tetikleyici | Audit olayının hazırlanması |
| Ön koşul | Redaksiyon politikası yürürlükte |
| Akış | **Temel:** eski/yeni değerleri politikayla tara → hassas alanları özet (digest) ile değiştir → redakte edilen alan listesini kaydet → politika sürümünü damgala. **Alternatif:** yapısal karşılaştırma için yalnız değişiklik olup olmadığı tutulur. **Hata:** politika yoksa olay yazılmaz |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | Olay kaydına gömülü: `redacted_fields`, `redaction_policy_version` |
| API | `—` |
| Ekran | Denetim > Olay Detayı (redaksiyon göstergesi) |
| Tablo | `audit_events`(old_value_summary, new_value_summary, old_value_digest, new_value_digest, redacted_fields) |
| Test | her hassas sınıf; digest kararlılığı; politika yokluğunda fail-closed; karşılaştırılabilirlik |

##### D13.C01.W02 — Audit sorgulama

###### D13.C01.W02.A01 — Audit olaylarını sorgula

| Alan | Değer |
|---|---|
| Amaç | Denetçinin "kim, ne zaman, neyi, neden yaptı" sorusunu bağımsız olarak yanıtlayabilmesini sağlamak |
| Aktör | Auditor; Security Admin |
| Tetikleyici | Denetim ekranından sorgu |
| Ön koşul | Denetim erişim politikası yürürlükte; aktör gerekli role sahip |
| Akış | **Temel:** aktör, işlem, nesne, sonuç ve dönem filtreleriyle sorgula → tutarlı bir anlık görüntü üzerinden sayfalayarak döndür → **sorgunun kendisini de audit'le**. **Alternatif:** imleç tabanlı sayfalama ile büyük sonuçlar gezilir. **Hata:** çok geniş sorgu → daraltma istenir; yetkisiz aktör → reddedilir ve ret de kaydedilir |
| Durum geçişi | `—` |
| Yetki | `audit.read` + politikada tanımlı zorunlu rol |
| Audit | `AUDIT_QUERY_EXECUTED` (filtre, sonuç sayısı, aktör); ret durumunda `AUDIT_ACCESS_DENIED` |
| API | `GET /audit/events` — imleç sayfalama, filtre |
| Ekran | Denetim > Olaylar |
| Tablo | `audit_events`(okuma) |
| Test | anlık görüntü tutarlılığı; imleç sayfalama; geniş sorgu koruması; erişim ve ret kaydı |

###### D13.C01.W02.A02 — Bir nesnenin tam geçmişini görüntüle

| Alan | Değer |
|---|---|
| Amaç | Tek bir kural, sorun veya kaynağın yaşam öyküsünü baştan sona izleyebilmek |
| Aktör | Auditor; Data Owner; Data Governance Admin |
| Tetikleyici | Nesne detayından geçmiş sekmesi |
| Ön koşul | Nesne üzerinde okuma kapsamı |
| Akış | **Temel:** nesne referansına ait tüm audit olaylarını zaman sıralı döndür → aktör, işlem, gerekçe ve değişiklik özetiyle göster. **Alternatif:** ilişkili nesnelerin olayları da dâhil edilebilir. **Hata:** saklama süresi dolmuş dönemler "arşivlendi" olarak işaretlenir |
| Durum geçişi | `—` |
| Yetki | `audit.read.object` + nesne kapsamı |
| Audit | Erişim kaydı: `AUDIT_OBJECT_HISTORY_VIEWED` (nesne, olay sayısı) |
| API | `GET /audit/objects/{type}/{id}/history` |
| Ekran | İlgili nesne detayı > Geçmiş |
| Tablo | `audit_events`(object_type, object_id)(okuma) |
| Test | ilişkili nesne kapsama; arşiv işareti; kapsam; erişim kaydı |

##### D13.C01.W03 — Bütünlük doğrulama

###### D13.C01.W03.A01 — Audit zincirinin bütünlüğünü doğrula

| Alan | Değer |
|---|---|
| Amaç | Audit izinin güvenilirliğinin iddia değil, gösterilebilir bir sonuç olmasını sağlamak |
| Aktör | Auditor; Sistem (periyodik) |
| Tetikleyici | Denetim ekranından doğrulama; periyodik bütünlük işi |
| Ön koşul | Audit olayları mevcut |
| Akış | **Temel:** belirtilen aralıkta hash zincirini baştan sona yeniden hesapla → uyuşmazlıkları raporla → sonucu kaydet. **Alternatif:** yalnız son dönem doğrulanır. **Hata:** uyuşmazlık bulunursa olay üretilir ve güvenlik sorumlusuna bildirilir |
| Durum geçişi | Doğrulama `—` → `PASSED` \| `FAILED` |
| Yetki | `audit.verify` + kurum geneli scope |
| Audit | `AUDIT_INTEGRITY_VERIFIED` (aralık, sonuç, uyuşmazlık sayısı) |
| API | `POST /audit/integrity-verifications` |
| Ekran | Denetim > Bütünlük |
| Tablo | `audit_integrity_checks`(check_id, range_start, range_end, verdict, mismatch_count, verified_at) |
| Test | bozulmuş kayıt tespiti; büyük aralık başarımı; bildirim; audit |

#### D13.C02 — Olay dışa aktarımı

##### D13.C02.W01 — Outbox yayımlama

###### D13.C02.W01.A01 — Bekleyen audit olaylarını yayımla

| Alan | Değer |
|---|---|
| Amaç | Audit olaylarının kalıcı deftere ve dış toplayıcılara, kayıp olmadan ulaşmasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Outbox yayım döngüsü |
| Ön koşul | Outbox'ta `PENDING` kayıt bulunması |
| Akış | **Temel:** bekleyenleri sıra korunacak biçimde al → kalıcı deftere yaz (hash zinciriyle) → `PUBLISHED` işaretle. **Alternatif:** toplu yayım sıra bütünlüğünü bozmadan yapılır. **Hata:** yayım başarısızsa kayıt `PENDING` kalır ve yeniden denenir; deneme sayacı artar |
| Durum geçişi | Outbox `PENDING` → `PUBLISHED` |
| Yetki | Sistem aktörü |
| Audit | Yayım hatalarında `AUDIT_OUTBOX_PUBLISH_FAILED` (kayıt sayısı, hata sınıfı) |
| API | `—` |
| Ekran | Operasyon > Audit Outbox |
| Tablo | `audit_outbox`(status, attempt_count, published_at, last_error_code) |
| Test | sıra korunumu; yeniden deneme; kısmi başarı; birikme uyarısı |

###### D13.C02.W01.A02 — Outbox birikmesini izle

| Alan | Değer |
|---|---|
| Amaç | Audit yayımının durduğunu, kayıtlar birikmeden fark etmek |
| Aktör | Operations User; Security Admin |
| Tetikleyici | Operasyon ekranı; periyodik eşik kontrolü |
| Ön koşul | Okuma yetkisi |
| Akış | **Temel:** bekleyen kayıt sayısını ve en eski kaydın yaşını göster → eşik aşımında uyarı üret. **Hata:** eşik aşımı kritik olay olarak eskale edilir |
| Durum geçişi | `—` |
| Yetki | `audit.outbox.read` + kurum geneli scope |
| Audit | Eşik aşımında `AUDIT_OUTBOX_BACKLOG_ALERT` (bekleyen sayı, en eski yaş) |
| API | `GET /operations/audit-outbox` |
| Ekran | Operasyon > Audit Outbox |
| Tablo | `audit_outbox`(okuma) |
| Test | eşik davranışı; yaş hesabı; eskalasyon; erişim kaydı |

##### D13.C02.W02 — Dış toplayıcıya aktarım

###### D13.C02.W02.A01 — Audit olaylarını dış toplayıcıya aktar

| Alan | Değer |
|---|---|
| Amaç | Audit izinin, sistemin kendisi ele geçse bile korunan bağımsız bir kopyasının bulunmasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Aktarım döngüsü |
| Ön koşul | Dış toplayıcı yapılandırılmış ve erişilebilir |
| Akış | **Temel:** yayımlanmış olayları sıra numarasına göre gönder → alındı onayını al → aktarım imlecini ilerlet. **Alternatif:** toplayıcı erişilemezse yerel kayıt korunur, imleç ilerlemez. **Hata:** uzun süreli erişilemezlik kritik uyarı üretir |
| Durum geçişi | Aktarım imleci ilerler |
| Yetki | Sistem aktörü |
| Audit | `AUDIT_EXPORT_COMPLETED` (aralık, kayıt sayısı, hedef); hata durumunda `AUDIT_EXPORT_FAILED` |
| API | `—` |
| Ekran | Operasyon > Audit Aktarımı |
| Tablo | `audit_export_cursors`(target, last_exported_sequence_no, last_exported_at) |
| Test | alındı onayı; imleç ilerlemesi; erişilemezlik; tekrar gönderim güvenliği |

#### D13.C03 — Saklama ve imha

##### D13.C03.W01 — Saklama politikası yönetimi

###### D13.C03.W01.A01 — Saklama politikası tanımla

| Alan | Değer |
|---|---|
| Amaç | Her veri türünün ne kadar süre saklanacağının bilinçli ve tek bir yerden yönetilmesini sağlamak |
| Aktör | Data Governance Admin |
| Tetikleyici | Yönetim ekranından politika tanımlama |
| Ön koşul | Veri kategorisi tanımlı |
| Akış | **Temel:** veri kategorisi, saklama süresi, imha yöntemi ve tetikleyici olayı gir → çakışma kontrolü → onaya gönder → audit. **Alternatif:** kategori bazlı varsayılan devralınır. **Hata:** aynı kategori için çakışan politika → reddet |
| Durum geçişi | Politika `—` → `DRAFT` |
| Yetki | `retention.policy.manage` + kurum geneli scope |
| Audit | `RETENTION_POLICY_DRAFTED` (kategori, süre, imha yöntemi) |
| API | `POST /retention-policies` |
| Ekran | Yönetim > Saklama Politikaları |
| Tablo | `retention_policies`(policy_id, data_category, retention_period, disposal_method, trigger_event, status, version) |
| Test | kategori çakışması; onay zinciri; devralma; audit |

###### D13.C03.W01.A02 — Saklama süresini kayıtlara uygula

| Alan | Değer |
|---|---|
| Amaç | Politikanın kâğıt üzerinde kalmayıp her kayda bir son kullanma tarihi olarak yansımasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Kayıt oluşturulması; politika yürürlüğe girmesi |
| Ön koşul | Kayıt kategorisi çözümlenebilir; politika `EFFECTIVE` |
| Akış | **Temel:** kaydın kategorisini çöz → tetikleyici olaydan itibaren saklama süresini ekle → `retention_until` alanını yaz. **Alternatif:** politika değiştiğinde mevcut kayıtlar yeniden hesaplanır. **Hata:** kategori çözümlenemezse en uzun saklama süresi uygulanır |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | Toplu yeniden hesaplamada `RETENTION_RECALCULATED` (kategori, etkilenen kayıt sayısı) |
| API | `—` |
| Ekran | İlgili nesne detayı (saklama bilgisi) |
| Tablo | İlgili tablolarda `retention_until` |
| Test | kategori çözümleme; politika değişiminde yeniden hesap; bilinmeyende güvenli taraf |

##### D13.C03.W02 — İmha işi yürütme

###### D13.C03.W02.A01 — Süresi dolan kayıtları imha et

| Alan | Değer |
|---|---|
| Amaç | Gereğinden uzun tutulan verinin risk oluşturmasını engellemek |
| Aktör | Sistem |
| Tetikleyici | İmha işi zamanlayıcısı |
| Ön koşul | Saklama politikası `EFFECTIVE`; imha işi onaylı |
| Akış | **Temel:** `retention_until` geçmiş ve muhafaza altında olmayan kayıtları seç → politikadaki yönteme göre sil veya anonimleştir → **imha kanıtını** kaydet → audit. **Alternatif:** kanıt niteliğindeki kayıtlarda içerik silinir, metadata korunur. **Hata:** yasal muhafaza varsa atlanır ve işaretlenir |
| Durum geçişi | İmha işi `—` → `RUNNING` → `COMPLETED` \| `PARTIAL` |
| Yetki | Sistem aktörü; `retention.disposal.execute` |
| Audit | `DATA_DISPOSED` (kategori, kayıt sayısı, yöntem, atlanan muhafaza sayısı, politika sürümü) |
| API | `GET /retention/disposal-jobs` |
| Ekran | Yönetim > İmha İşleri |
| Tablo | `disposal_jobs`(job_id, policy_id, target_category, disposed_count, skipped_hold_count, status, executed_at) |
| Test | muhafaza atlaması; anonimleştirme; metadata korunumu; imha kanıtı; audit |

###### D13.C03.W02.A02 — İmha kanıtını görüntüle

| Alan | Değer |
|---|---|
| Amaç | Verinin gerçekten ve zamanında imha edildiğinin denetimde gösterilebilmesini sağlamak |
| Aktör | Auditor; Data Governance Admin |
| Tetikleyici | Denetim incelemesi |
| Ön koşul | Okuma yetkisi |
| Akış | **Temel:** imha işlerini kategori, dönem, kayıt sayısı ve yöntemle listele → her iş için kanıt ayrıntısını sun. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `retention.disposal.read` + kurum geneli scope |
| Audit | Erişim kaydı: `DISPOSAL_EVIDENCE_VIEWED` (filtre) |
| API | `GET /retention/disposal-jobs` — sayfalama, filtre |
| Ekran | Yönetim > İmha İşleri |
| Tablo | `disposal_jobs`(okuma) |
| Test | kanıt bütünlüğü; sayfalama; yetki; erişim kaydı |

#### D13.C04 — Yasal muhafaza ve geri çağırma

##### D13.C04.W01 — Muhafaza uygulama ve kaldırma

###### D13.C04.W01.A01 — Yasal muhafaza uygula

| Alan | Değer |
|---|---|
| Amaç | İnceleme veya uyuşmazlık konusu verinin, saklama süresi dolsa bile imha edilmesini engellemek |
| Aktör | Data Governance Admin; Auditor |
| Tetikleyici | Muhafaza talebi |
| Ön koşul | Kapsam ve gerekçe verilmiş; muhafaza yetkisi |
| Akış | **Temel:** kapsam (kategori, nesne, dönem), gerekçe ve referans numarası gir → kapsamdaki kayıtları muhafaza altına al → imha işlerinden dışla → audit. **Alternatif:** muhafaza ileriye dönük yeni kayıtları da kapsayabilir. **Hata:** gerekçesiz muhafaza → reddet |
| Durum geçişi | Muhafaza `—` → `ACTIVE`; kapsamdaki kayıtlar `hold_flag=true` |
| Yetki | `retention.legal-hold.manage` + kurum geneli scope |
| Audit | `LEGAL_HOLD_APPLIED` (muhafaza, kapsam, gerekçe, etkilenen kayıt sayısı) |
| API | `POST /retention/legal-holds` |
| Ekran | Yönetim > Yasal Muhafaza |
| Tablo | `legal_holds`(hold_id, scope_type, scope_id, reason, reference_no, status, applied_at, applied_by) |
| Test | imha dışlaması; ileriye dönük kapsam; gerekçe zorunluluğu; audit |

###### D13.C04.W01.A02 — Yasal muhafazayı kaldır

| Alan | Değer |
|---|---|
| Amaç | Gerekçesi biten muhafazanın verileri süresiz tutmasını engellemek |
| Aktör | Muhafazayı uygulayan; Data Governance Admin |
| Tetikleyici | Muhafaza detayından kaldırma |
| Ön koşul | Muhafaza `ACTIVE`; kaldırma gerekçesi verilmiş |
| Akış | **Temel:** gerekçe gir → muhafazayı `RELEASED` yap → kayıtların muhafaza işaretini kaldır → süresi geçmiş kayıtları imha kuyruğuna al → audit. **Hata:** başka aktif muhafaza kapsıyorsa işaret kalkmaz |
| Durum geçişi | Muhafaza `ACTIVE` → `RELEASED` |
| Yetki | `retention.legal-hold.manage` + kurum geneli scope |
| Audit | `LEGAL_HOLD_RELEASED` (muhafaza, gerekçe, serbest kalan kayıt sayısı) |
| API | `POST /legal-holds/{id}/release` |
| Ekran | Yönetim > Yasal Muhafaza |
| Tablo | `legal_holds`(status, released_at, release_reason) |
| Test | çakışan muhafaza; imha kuyruğuna alma; yetki; audit |

##### D13.C04.W02 — Arşivden geri çağırma

###### D13.C04.W02.A01 — Arşivlenmiş kaydı geri çağır

| Alan | Değer |
|---|---|
| Amaç | Denetim veya inceleme için geçmiş kanıta, kontrollü biçimde yeniden erişebilmek |
| Aktör | Auditor; Data Governance Admin |
| Tetikleyici | Geri çağırma talebi |
| Ön koşul | Kayıt arşivde; talep gerekçesi verilmiş |
| Akış | **Temel:** kapsam ve gerekçeyle talep aç → onaya gönder → onayda arşivden süreli erişim aç → erişim penceresini kaydet → audit. **Alternatif:** onay sonrası erişim yalnız talep edene ve sınırlı süreyle verilir. **Hata:** onaysız geri çağırma yapılamaz |
| Durum geçişi | Talep `—` → `PENDING` → `APPROVED` → `ACCESSIBLE` → `EXPIRED` |
| Yetki | `retention.archive.recall` + kurum geneli scope; görev ayrılığı zorunlu |
| Audit | `ARCHIVE_RECALL_REQUESTED` / `ARCHIVE_RECALL_DECIDED` / `ARCHIVE_RECALL_ACCESSED` (talep, kapsam, gerekçe, erişim penceresi) |
| API | `POST /retention/archive-recalls`; `POST /archive-recalls/{id}/decision` |
| Ekran | Yönetim > Arşiv Geri Çağırma |
| Tablo | `archive_recalls`(recall_id, scope, reason, maker_actor_id, checker_actor_id, status, access_until) |
| Test | görev ayrılığı; süreli erişim; pencere dolumu; hassas erişim kaydı |

##### L5 — D13 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D13-001` | Audit olayı, onu doğuran iş transaction'ıyla aynı anda yazılır; audit yazılamıyorsa iş de geri alınır |
| `BR-D13-002` | Audit kayıtları değişmezdir; düzeltme yeni bir olayla yapılır |
| `BR-D13-003` | Her audit olayı hash zinciriyle bir öncekine bağlanır |
| `BR-D13-004` | Redaksiyon politikası yürürlükte değilse audit olayı yazılmaz |
| `BR-D13-005` | Hassas değerler audit kaydında açık tutulmaz; özet ve değişim göstergesi tutulur |
| `BR-D13-006` | Audit sorgusunun kendisi de audit'lenir; reddedilen erişimler ayrıca kaydedilir |
| `BR-D13-007` | Audit sorguları tutarlı bir anlık görüntü üzerinden sayfalanır |
| `BR-D13-008` | Kategorisi çözümlenemeyen kayda en uzun saklama süresi uygulanır |
| `BR-D13-009` | Yasal muhafaza altındaki kayıt, saklama süresi dolsa bile imha edilmez |
| `BR-D13-010` | İmha edilen veri için imha kanıtı üretilir ve saklanır |
| `BR-D13-011` | Kanıt niteliğindeki kayıtlarda içerik imha edilirken metadata korunur |
| `BR-D13-012` | Arşivden geri çağırma görev ayrılığı gerektirir ve süreli erişim verir |

---

### D14 — Operasyon ve Platform Sağlığı

Sistemi çalışır tutan kişilerin domaini. Ölçüm yapan bir platformun kendi
sağlığının da ölçülmesi ve müdahale edilebilir olması gerekir.

#### D14.C01 — Sistem sağlığı

##### D14.C01.W01 — Bileşen sağlık görünümü

###### D14.C01.W01.A01 — Platform bileşenlerinin sağlığını göster

| Alan | Değer |
|---|---|
| Amaç | Operatörün sistemin hangi parçasının sorunlu olduğunu tek bakışta görmesini sağlamak |
| Aktör | Operations User; Platform Admin |
| Tetikleyici | Operasyon ekranı açılışı; otomatik yenileme |
| Ön koşul | Okuma yetkisi |
| Akış | **Temel:** veri deposu, kuyruk, worker'lar, zamanlayıcı, bildirim kanalları, audit outbox ve dış entegrasyonların sağlığını topla → durum ve son kontrol zamanıyla göster. **Alternatif:** bozuk bileşenler öne alınır. **Hata:** sağlık bilgisi alınamayan bileşen `UNKNOWN` gösterilir, sağlıklı sayılmaz |
| Durum geçişi | Bileşen sağlığı `HEALTHY` \| `DEGRADED` \| `UNAVAILABLE` \| `UNKNOWN` |
| Yetki | `operations.health.read` + kurum geneli scope |
| Audit | Erişim kaydı: `PLATFORM_HEALTH_VIEWED` |
| API | `GET /operations/health` |
| Ekran | Operasyon > Sistem Sağlığı |
| Tablo | `component_health`(component, state, detail, checked_at) |
| Test | bilinmeyende sağlıklı saymama; sıralama; tüm bileşen tipleri; erişim kaydı |

###### D14.C01.W01.A02 — Sağlık bozulmasında uyarı üret

| Alan | Değer |
|---|---|
| Amaç | Operatörün ekrana bakmasa bile kritik bozulmadan haberdar olmasını sağlamak |
| Aktör | Sistem |
| Tetikleyici | Bileşen sağlığının bozulması |
| Ön koşul | Uyarı eşikleri politikada tanımlı |
| Akış | **Temel:** durum değişimini tespit et → eşiği aşan bozulmalar için bildirim olayı üret → tekrarlayan uyarıları bastır. **Alternatif:** düzelme de bildirilir. **Hata:** eşik tanımı yoksa yalnız kaydedilir |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `COMPONENT_HEALTH_CHANGED` (bileşen, eski/yeni durum, süre) |
| API | `—` |
| Ekran | Operasyon > Sistem Sağlığı |
| Tablo | `component_health`(state, changed_at) |
| Test | uyarı bastırma; düzelme bildirimi; eşik yokluğu; audit |

##### D14.C01.W02 — Kapasite ve yük görünümü

###### D14.C01.W02.A01 — Kuyruk ve kaynak yükünü göster

| Alan | Değer |
|---|---|
| Amaç | Darboğazın nerede oluştuğunu ve kapasite artırımının nereye gerektiğini görmek |
| Aktör | Operations User; Platform Admin |
| Tetikleyici | Operasyon ekranı |
| Ön koşul | Okuma yetkisi |
| Akış | **Temel:** kuyruk derinliğini iş tipine göre, bekleme süresini, worker doluluğunu ve kaynak başına aktif sorgu sayısını göster → eğilimle birlikte sun. **Alternatif:** dönemsel karşılaştırma. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `operations.health.read` + kurum geneli scope |
| Audit | Erişim kaydı: `CAPACITY_VIEWED` |
| API | `GET /operations/capacity` |
| Ekran | Operasyon > Kapasite |
| Tablo | `persistent_jobs`, `workers`, `source_usage_policies`(okuma) |
| Test | derinlik hesabı; bekleme süresi; doluluk oranı; erişim kaydı |

#### D14.C02 — Kuyruk ve worker operasyonu

##### D14.C02.W01 — Kuyruk görünümü ve müdahale

###### D14.C02.W01.A01 — Kuyruğu incele

| Alan | Değer |
|---|---|
| Amaç | Hangi işin neden beklediğini görebilmek |
| Aktör | Operations User |
| Tetikleyici | Operasyon ekranı |
| Ön koşul | Okuma yetkisi |
| Akış | **Temel:** işleri durum, tip, öncelik, deneme sayısı, bekleme süresi ve bloke nedeniyle listele → filtrele ve sırala. **Alternatif:** kaynak veya çalıştırmaya göre daraltma. **Hata:** `—` |
| Durum geçişi | `—` |
| Yetki | `operations.queue.read` + kurum geneli scope |
| Audit | Erişim kaydı: `JOB_QUEUE_VIEWED` (filtre, sonuç sayısı) |
| API | `GET /operations/jobs` — sayfalama, filtre, sıralama |
| Ekran | Operasyon > Kuyruk |
| Tablo | `persistent_jobs`(okuma) |
| Test | bloke nedeni gösterimi; sayfalama; sıralama; erişim kaydı |

###### D14.C02.W01.A02 — İşi manuel iptal et veya önceliklendir

| Alan | Değer |
|---|---|
| Amaç | Kuyruğu tıkayan veya yanlış sıradaki işlere müdahale edebilmek |
| Aktör | Operations User |
| Tetikleyici | Kuyruk ekranından müdahale |
| Ön koşul | İş `AVAILABLE`, `CLAIMED` veya `RUNNING`; müdahale gerekçesi verilmiş |
| Akış | **Temel:** gerekçe gir → iptal veya öncelik değişikliğini uygula → kaynak nesneyi bilgilendir → audit. **Alternatif:** toplu müdahale filtreyle yapılır. **Hata:** tamamlanmış iş → idempotent başarı |
| Durum geçişi | İş → `CANCELLED`; veya `priority` değişir |
| Yetki | `operations.queue.manage` + kurum geneli scope |
| Audit | `JOB_MANUALLY_INTERVENED` (iş, müdahale tipi, gerekçe, aktör) |
| API | `POST /operations/jobs/{id}/intervention` |
| Ekran | Operasyon > Kuyruk |
| Tablo | `persistent_jobs`(status, priority, version) |
| Test | toplu müdahale; idempotency; kaynak nesne bildirimi; audit |

##### D14.C02.W02 — Worker yönetimi

###### D14.C02.W02.A01 — Worker'ı boşalt (drain) veya durdur

| Alan | Değer |
|---|---|
| Amaç | Bakım veya sürüm geçişinde çalışan işlerin yarıda kesilmesini önlemek |
| Aktör | Operations User; Platform Admin |
| Tetikleyici | Bakım planı; worker sorunları |
| Ön koşul | Worker `ACTIVE` |
| Akış | **Temel:** worker'ı `DRAINING` yap → yeni iş almasını durdur → mevcut işleri bitirmesini bekle → `STOPPED` yap → audit. **Alternatif:** zorla durdurmada işler lease süresi dolunca yeniden dağıtılır. **Hata:** boşaltma zaman aşımına uğrarsa operatöre bildirilir |
| Durum geçişi | Worker `ACTIVE` → `DRAINING` → `STOPPED` |
| Yetki | `operations.worker.manage` + kurum geneli scope |
| Audit | `WORKER_DRAIN_REQUESTED` (worker, açık iş sayısı, zorla mı) |
| API | `POST /operations/workers/{id}/drain` |
| Ekran | Operasyon > Worker'lar |
| Tablo | `workers`(state, drain_requested_at) |
| Test | boşaltma tamamlanması; zorla durdurma; lease yeniden dağıtımı; audit |

#### D14.C03 — Olay (incident) yönetimi

##### D14.C03.W01 — Operasyonel olay yaşam döngüsü

###### D14.C03.W01.A01 — Operasyonel olay aç

| Alan | Değer |
|---|---|
| Amaç | Platform kesintilerinin koordineli ve izlenebilir biçimde yönetilmesini sağlamak |
| Aktör | Operations User; Sistem (otomatik) |
| Tetikleyici | Kritik sağlık bozulması; operatör tespiti |
| Ön koşul | Olay şiddeti tanımlı |
| Akış | **Temel:** başlık, şiddet, etkilenen bileşenler ve etki tanımını gir → olay aç → olay sorumlusunu ata → bildir → audit. **Alternatif:** sağlık uyarısından otomatik açılır. **Hata:** aynı bileşen için açık olay varsa yinelenme olarak bağlanır |
| Durum geçişi | Olay `—` → `OPEN` |
| Yetki | `operations.incident.manage` + kurum geneli scope |
| Audit | `OPERATIONAL_INCIDENT_OPENED` (olay, şiddet, bileşenler, otomatik mi) |
| API | `POST /operations/incidents` |
| Ekran | Operasyon > Olaylar |
| Tablo | `operational_incidents`(incident_id, title, severity, affected_components, impact, owner_user_id, status, opened_at) |
| Test | otomatik açma; yinelenme bağlama; şiddet sınıfları; audit |

###### D14.C03.W01.A02 — Olayı güncelle ve kapat

| Alan | Değer |
|---|---|
| Amaç | Olay süresince yapılanların ve sonucun kayıt altına alınmasını sağlamak |
| Aktör | Olay sorumlusu; Operations User |
| Tetikleyici | Olay detayından güncelleme/kapatma |
| Ön koşul | Olay `OPEN` veya `MITIGATED` |
| Akış | **Temel:** durum güncellemesi ve zaman damgalı not ekle → azaltma sağlandığında `MITIGATED` → kök neden ve kalıcı çözüm kaydedilince `CLOSED` → audit. **Alternatif:** kapanışta izleme aksiyonları oluşturulur. **Hata:** kök nedensiz kapatma → gerekçe istenir |
| Durum geçişi | `OPEN` → `MITIGATED` → `CLOSED` |
| Yetki | `operations.incident.manage` + kurum geneli scope |
| Audit | `OPERATIONAL_INCIDENT_UPDATED` / `OPERATIONAL_INCIDENT_CLOSED` (olay, durum, süre, kök neden) |
| API | `POST /operations/incidents/{id}/updates`; `POST /operations/incidents/{id}/closure` |
| Ekran | Operasyon > Olaylar > Detay |
| Tablo | `operational_incidents`(status, mitigated_at, closed_at, root_cause); `incident_updates`(incident_id, note, created_at) |
| Test | zaman çizelgesi bütünlüğü; kök neden zorunluluğu; izleme aksiyonu; audit |

#### D14.C04 — Bakım ve değişiklik

##### D14.C04.W01 — Bakım penceresi yönetimi

###### D14.C04.W01.A01 — Bakım penceresi planla

| Alan | Değer |
|---|---|
| Amaç | Planlı bakımın, beklenmedik kesinti gibi algılanmasını ve gereksiz alarm üretmesini önlemek |
| Aktör | Platform Admin; Operations User |
| Tetikleyici | Bakım planı |
| Ön koşul | Pencere zamanı ve kapsamı belirtilmiş |
| Akış | **Temel:** başlangıç, bitiş, kapsam ve açıklamayı gir → pencere boyunca uyarıları bastır → zamanlamaları duraklat → ilgilileri bilgilendir → audit. **Alternatif:** acil bakım geriye dönük kaydedilebilir. **Hata:** geçmişte kalan pencere planlanamaz (acil hariç) |
| Durum geçişi | Pencere `—` → `SCHEDULED` → `ACTIVE` → `COMPLETED` |
| Yetki | `operations.maintenance.manage` + kurum geneli scope |
| Audit | `MAINTENANCE_WINDOW_SCHEDULED` (pencere, kapsam, süre) |
| API | `POST /operations/maintenance-windows` |
| Ekran | Operasyon > Bakım |
| Tablo | `maintenance_windows`(window_id, starts_at, ends_at, scope, description, status) |
| Test | uyarı bastırma; zamanlama duraklatma; acil kayıt; audit |

##### D14.C04.W02 — Toplu yeniden işleme

###### D14.C04.W02.A01 — Ölçüm boşluğunu toplu yeniden işle

| Alan | Değer |
|---|---|
| Amaç | Kesinti sonrası oluşan ölçüm boşluklarının kapatılabilmesini sağlamak |
| Aktör | Operations User |
| Tetikleyici | Kesinti sonrası telafi kararı |
| Ön koşul | Boşluk dönemi ve kapsam belirlenmiş; kaynak kotası uygun |
| Akış | **Temel:** boşluk dönemini ve kapsamı seç → üretilecek iş sayısını ve tahmini yükü göster → onayla → işleri kademeli olarak kuyruğa al → ilerlemeyi izle → audit. **Alternatif:** yalnız kritik kurallar telafi edilir. **Hata:** kota aşımı riskinde kademelendirme zorunlu tutulur |
| Durum geçişi | Telafi işi `—` → `RUNNING` → `COMPLETED` \| `PARTIAL` |
| Yetki | `operations.backfill.execute` + kurum geneli scope |
| Audit | `BACKFILL_STARTED` / `BACKFILL_COMPLETED` (dönem, kapsam, iş sayısı, sonuç) |
| API | `POST /operations/backfills` |
| Ekran | Operasyon > Telafi |
| Tablo | `backfill_jobs`(backfill_id, period_start, period_end, scope, job_count, status) |
| Test | yük tahmini; kademelendirme; kota koruması; kısmi tamamlanma; audit |

##### L5 — D14 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D14-001` | Sağlık bilgisi alınamayan bileşen `UNKNOWN` gösterilir; sağlıklı kabul edilmez |
| `BR-D14-002` | Operasyonel müdahaleler gerekçe olmadan yapılamaz ve tümü audit'lenir |
| `BR-D14-003` | Worker boşaltma, çalışan işleri yarıda kesmeden tamamlanmayı bekler |
| `BR-D14-004` | Zorla durdurulan worker'ın işleri lease süresi dolunca yeniden dağıtılır |
| `BR-D14-005` | Bakım penceresi boyunca uyarılar bastırılır ve zamanlamalar duraklatılır |
| `BR-D14-006` | Operasyonel olay kök neden kaydedilmeden kapatılamaz; kapatma gerekçe ister |
| `BR-D14-007` | Toplu telafi işleri kaynak kotasını aşmayacak biçimde kademelendirilir |
| `BR-D14-008` | Operasyonel olaylar kalite sorunlarından ayrı bir yaşam döngüsüne sahiptir |

---

### D15 — Test Verisi ve Ground Truth

Kalite kontrollerinin kendisinin doğru çalıştığını kanıtlayan domain. Bilinen
hatalar içeren veri üretilir ve sistemin bunları yakalayıp yakalamadığı ölçülür.

#### D15.C01 — Sentetik veri üretimi

##### D15.C01.W01 — Üretim çalıştırması

###### D15.C01.W01.A01 — Sentetik veri üretimi çalıştır

| Alan | Değer |
|---|---|
| Amaç | Gerçek veri kullanmadan, kontrollü ve tekrarlanabilir test kümeleri oluşturmak |
| Aktör | Technical Data Steward; Platform Admin |
| Tetikleyici | Test verisi ekranından üretim talebi |
| Ön koşul | Üretim profili tanımlı; hedef ortam üretim dışı; üretim yetkisi |
| Akış | **Temel:** profil ve hacim seç → deterministik tohum belirle → veriyi üret → hedef şemaya yaz → çalıştırma kaydını tohum ve profil sürümüyle sakla → audit. **Alternatif:** mevcut çalıştırma aynı tohumla yeniden üretilebilir. **Hata:** hedef üretim ortamıysa → **reddet** |
| Durum geçişi | Üretim `—` → `RUNNING` → `COMPLETED` \| `FAILED` |
| Yetki | `synthetic.generate` + kurum geneli scope |
| Audit | `SYNTHETIC_GENERATION_RUN` (çalıştırma, profil, hacim, tohum, hedef) |
| API | `POST /synthetic-data/runs` |
| Ekran | Test Verisi > Üretim |
| Tablo | `synthetic_runs`(run_id, profile_id, volume, seed, target_ref, status, started_at) |
| Test | üretim ortamı reddi; determinizm (aynı tohum → aynı veri); hacim; audit |

###### D15.C01.W01.A02 — Sentetik veriyi temizle

| Alan | Değer |
|---|---|
| Amaç | Test verisinin ortamda birikmesini ve gerçek veriyle karışmasını önlemek |
| Aktör | Technical Data Steward |
| Tetikleyici | Test verisi ekranından temizleme; üretim çalıştırmasının saklama süresi dolumu |
| Ön koşul | Çalıştırma `COMPLETED`; veri sentetik olarak işaretli |
| Akış | **Temel:** çalıştırmaya ait kayıtları sil → çalıştırma kaydını `CLEANED` yap → audit. **Alternatif:** yalnız belirli dataset temizlenir. **Hata:** sentetik işareti taşımayan veriye dokunulmaz |
| Durum geçişi | Üretim `COMPLETED` → `CLEANED` |
| Yetki | `synthetic.manage` + kurum geneli scope |
| Audit | `SYNTHETIC_DATA_CLEANED` (çalıştırma, silinen kayıt sayısı) |
| API | `POST /synthetic-data/runs/{id}/cleanup` |
| Ekran | Test Verisi > Üretim |
| Tablo | `synthetic_runs`(status, cleaned_at) |
| Test | sentetik işareti koruması; kısmi temizlik; audit |

##### D15.C01.W02 — Üretim profili yönetimi

###### D15.C01.W02.A01 — Sentetik veri profili tanımla

| Alan | Değer |
|---|---|
| Amaç | Üretilecek verinin şeklini ve içereceği bilinen hataları önceden tanımlamak |
| Aktör | Technical Data Steward |
| Tetikleyici | Test verisi ekranından profil tanımlama |
| Ön koşul | Hedef şema bilinir |
| Akış | **Temel:** alan tipleri, dağılımlar, ilişkiler ve **kasıtlı hata enjeksiyon kuralları** tanımla → profili sürümle → kaydet → audit. **Alternatif:** mevcut dataset profilinden türetilir. **Hata:** gerçek veri örneği içeren profil → reddet |
| Durum geçişi | Profil `—` → `ACTIVE` |
| Yetki | `synthetic.profile.manage` + kurum geneli scope |
| Audit | `SYNTHETIC_PROFILE_DEFINED` (profil, alan sayısı, hata kuralı sayısı) |
| API | `POST /synthetic-data/profiles` |
| Ekran | Test Verisi > Profiller |
| Tablo | `synthetic_profiles`(profile_id, name, field_specs, defect_rules, version, status) |
| Test | gerçek veri sızma reddi; profil türetme; sürümleme; audit |

#### D15.C02 — Bilinen doğruluk kümesi

##### D15.C02.W01 — Ground truth tanımlama

###### D15.C02.W01.A01 — Bilinen hata kümesini kaydet

| Alan | Değer |
|---|---|
| Amaç | Sistemin neyi yakalaması gerektiğini önceden ve kesin olarak tanımlamak |
| Aktör | Sistem (üretimden); Technical Data Steward (manuel) |
| Tetikleyici | Sentetik üretim sırasında hata enjeksiyonu; manuel tanımlama |
| Ön koşul | Üretim çalıştırması mevcut |
| Akış | **Temel:** enjekte edilen her hatayı kayıt kimliği, alan, hata tipi ve beklenen kural eşleşmesiyle kaydet → çalıştırmaya bağla. **Alternatif:** gerçek veride bilinen hatalar manuel işaretlenir. **Hata:** beklenen kural eşleşmesi belirtilmemişse ölçüm yapılamaz |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü; manuelde `synthetic.ground-truth.manage` |
| Audit | `GROUND_TRUTH_RECORDED` (çalıştırma, hata sayısı, hata tipleri) |
| API | `GET /synthetic-data/runs/{id}/ground-truth` |
| Ekran | Test Verisi > Ground Truth |
| Tablo | `ground_truth_defects`(defect_id, run_id, record_ref, field_ref, defect_type, expected_rule_ref) |
| Test | eşleşme zorunluluğu; manuel işaretleme; çalıştırma bağı; audit |

##### D15.C02.W02 — Beklenen sonuç kaydı

###### D15.C02.W02.A01 — Beklenen ölçüm sonucunu hesapla

| Alan | Değer |
|---|---|
| Amaç | Sistemin ne sonuç üretmesi gerektiğini, sistemden bağımsız olarak bilmek |
| Aktör | Sistem |
| Tetikleyici | Ground truth kaydının tamamlanması |
| Ön koşul | Bilinen hata kümesi ve beklenen kural eşleşmeleri mevcut |
| Akış | **Temel:** her beklenen kural için kaç kaydın başarısız olması gerektiğini hesapla → beklenen sayaçları kaydet. **Alternatif:** birden çok kuralın yakalayacağı hatalar ayrı ayrı sayılır. **Hata:** hesaplanamayan beklenti işaretlenir ve doğruluk ölçümünden çıkarılır |
| Durum geçişi | `—` |
| Yetki | Sistem aktörü |
| Audit | `EXPECTED_RESULT_COMPUTED` (çalıştırma, kural sayısı, beklenen hata sayısı) |
| API | `GET /synthetic-data/runs/{id}/expectations` |
| Ekran | Test Verisi > Ground Truth |
| Tablo | `expected_results`(run_id, rule_ref, expected_failed_count, computable) |
| Test | çoklu kural eşleşmesi; hesaplanamaz durum; sayaç doğruluğu |

#### D15.C03 — Kontrol doğrulama

##### D15.C03.W01 — Tespit doğruluğu ölçümü

###### D15.C03.W01.A01 — Kontrol tespit doğruluğunu ölç

| Alan | Değer |
|---|---|
| Amaç | Kuralların gerçekten hataları yakalayıp yakalamadığını ve yanlış alarm üretip üretmediğini sayısal olarak bilmek |
| Aktör | Sistem; Technical Data Steward (talep) |
| Tetikleyici | Sentetik veri üzerinde çalıştırma tamamlanması |
| Ön koşul | Ground truth ve beklenen sonuçlar mevcut; gerçek sonuç üretilmiş |
| Akış | **Temel:** gerçek sonuçları beklenenle karşılaştır → yakalanan, kaçırılan ve yanlış alarm sayılarını üret → kural bazlı doğruluk metriklerini kaydet. **Alternatif:** kural kümesi bazında toplu doğruluk raporu. **Hata:** hesaplanamaz beklentiler dışlanır ve raporda belirtilir |
| Durum geçişi | Doğrulama `—` → `COMPLETED` |
| Yetki | `synthetic.validate.execute` + kurum geneli scope |
| Audit | `CONTROL_ACCURACY_MEASURED` (çalıştırma, kural sayısı, yakalanan, kaçırılan, yanlış alarm) |
| API | `POST /synthetic-data/runs/{id}/validation` |
| Ekran | Test Verisi > Doğrulama |
| Tablo | `control_validations`(validation_id, run_id, rule_ref, detected, missed, false_positive, verdict) |
| Test | kaçırma tespiti; yanlış alarm tespiti; dışlanan beklenti; audit |

###### D15.C03.W01.A02 — Doğrulama sonucunu kural sağlığına yansıt

| Alan | Değer |
|---|---|
| Amaç | Zayıf kuralların, gerçek veride yanlış güven vermeden önce düzeltilmesini sağlamak |
| Aktör | Sistem |
| Tetikleyici | Doğrulama tamamlanması |
| Ön koşul | Doğruluk eşikleri politikada tanımlı |
| Akış | **Temel:** eşiğin altında kalan kuralları işaretle → sahibine bildir → gerekirse kuralı `REVIEW_REQUIRED` yap → audit. **Alternatif:** yalnız uyarı üretilir (politikaya göre). **Hata:** politika yoksa yalnız sonuç kaydedilir |
| Durum geçişi | Kural `ACTIVE` → `REVIEW_REQUIRED` (eşik altındaysa) |
| Yetki | Sistem aktörü |
| Audit | `RULE_ACCURACY_BELOW_THRESHOLD` (kural, doğruluk, eşik, politika sürümü) |
| API | `GET /rules/{id}/accuracy` |
| Ekran | Kurallar > Kural Detayı > Doğruluk |
| Tablo | `control_validations`(okuma); `quality_rules`(status) |
| Test | eşik davranışı; kural durumu zinciri; bildirim; politika yokluğu |

##### D15.C03.W02 — Kontrol yeterliliği deneyi

###### D15.C03.W02.A01 — Kontrollü bozulma deneyi yürüt

| Alan | Değer |
|---|---|
| Amaç | Sistemin uçtan uca (tespit → sorun → bildirim → eskalasyon) gerçekten çalıştığını kanıtlamak |
| Aktör | Platform Admin; Technical Data Steward |
| Tetikleyici | Deney planından yürütme |
| Ön koşul | Deney üretim dışı ortamda; deney kapsamı ve geri alma planı tanımlı; onay alınmış |
| Akış | **Temel:** planlı bozulmayı sentetik veriye enjekte et → uçtan uca zincirin her adımının gerçekleşip gerçekleşmediğini ölç → süreleri kaydet → veriyi geri al → rapor üret → audit. **Alternatif:** yalnız belirli bir zincir adımı sınanır. **Hata:** üretim ortamında deney → **reddedilir** |
| Durum geçişi | Deney `—` → `RUNNING` → `COMPLETED` \| `ABORTED` |
| Yetki | `synthetic.experiment.execute` + kurum geneli scope; onay zorunlu |
| Audit | `CONTROL_EXPERIMENT_RUN` (deney, kapsam, zincir adımları, sonuç, süreler) |
| API | `POST /synthetic-data/experiments` |
| Ekran | Test Verisi > Deneyler |
| Tablo | `control_experiments`(experiment_id, plan, scope, chain_results, status, started_at, ended_at) |
| Test | üretim ortamı reddi; zincir adımı ölçümü; geri alma; onay kapısı; audit |

##### L5 — D15 iş kuralları

| Kod | Kural |
|---|---|
| `BR-D15-001` | Sentetik veri üretimi üretim ortamında çalıştırılamaz |
| `BR-D15-002` | Sentetik üretim deterministiktir; aynı profil ve tohum aynı veriyi üretir |
| `BR-D15-003` | Sentetik profiller gerçek veri örneği içeremez |
| `BR-D15-004` | Üretilen tüm veri sentetik olarak işaretlenir; temizlik yalnız işaretli veriye dokunur |
| `BR-D15-005` | Her enjekte edilen hata, beklenen bir kural eşleşmesiyle kaydedilir |
| `BR-D15-006` | Beklenen sonucu hesaplanamayan hatalar doğruluk ölçümünden dışlanır ve raporda belirtilir |
| `BR-D15-007` | Doğruluk eşiğinin altında kalan kural gözden geçirmeye alınır |
| `BR-D15-008` | Kontrollü bozulma deneyi onay ve geri alma planı olmadan yürütülemez |
| `BR-D15-009` | Sentetik veri üzerinde üretilen sonuçlar resmî skora dâhil edilmez |

---

## 6. Kesişen kataloglar

Gövdedeki 271 yaprakta geçen her durum geçişi, izin kodu, audit olayı, bildirim
ve tablo bu bölümde tanımlanır. Katalog, modelin kapanış noktasıdır: yapraklarda
adı geçip burada tanımlanmayan hiçbir referans bulunmamalıdır.

### 6.1 Durum makineleri

Yirmi dokuz varlık durum makinesine sahiptir. Her tabloda geçişi tetikleyen
komut, aktör, ön koşul, audit olayı ve yan etki verilir.

#### ST-Policy — Politika

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Taslak oluştur | `DRAFT` | Governance/Platform Admin | Tip katalogda | `POLICY_DRAFT_CREATED` | — |
| `DRAFT` | Onaya gönder | `IN_REVIEW` | Governance Admin (maker) | Şema geçerli, etki özeti var | `POLICY_SUBMITTED_FOR_APPROVAL` | Onay talebi açılır |
| `IN_REVIEW` | Onayla | `APPROVED` | Security/Governance Admin (checker≠maker) | Talep `PENDING` | `POLICY_APPROVAL_DECIDED` | — |
| `IN_REVIEW` | Reddet | `DRAFT` | Checker | Gerekçe zorunlu | `POLICY_APPROVAL_DECIDED` | — |
| `APPROVED` | Yürürlüğe al | `EFFECTIVE` | Platform Admin | Aralık çakışmıyor | `POLICY_MADE_EFFECTIVE` | Önceki sürüm `SUPERSEDED` |
| `EFFECTIVE` | Yeni sürüm yürürlüğe girer | `SUPERSEDED` | Sistem | — | `POLICY_MADE_EFFECTIVE` | — |
| `EFFECTIVE` | Geri al | `ROLLED_BACK` | Platform Admin | Hedef sürüm var | `POLICY_ROLLED_BACK` | Hedef `SUPERSEDED`→`EFFECTIVE` |

#### ST-User — Kullanıcı hesabı

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Sağla | `ACTIVE` | Security Admin / Sistem | Dış kimlik benzersiz | `USER_PROVISIONED` | — |
| `ACTIVE` | Pasifleştir | `INACTIVE` | Security Admin / Sistem | — | `USER_DEACTIVATED` | Oturumlar `TERMINATED`, roller `REVOKED` |
| `INACTIVE` | Yeniden etkinleştir | `ACTIVE` | Security Admin | Dış kimlik geçerli | `USER_REACTIVATED` | Roller **geri verilmez** |

#### ST-RoleAssignment — Rol ataması

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Ata | `ACTIVE` | Security Admin | Görev ayrılığı ihlali yok | `ROLE_ASSIGNED` | — |
| `ACTIVE` | İptal et | `REVOKED` | Security Admin | Son yönetici değil | `ROLE_ASSIGNMENT_REVOKED` | Oturum yetkisi tazelenir |
| `ACTIVE` | Süre dolar | `EXPIRED` | Sistem | `valid_to` geçti | `ROLE_ASSIGNMENT_REVOKED` | Kapsam çözümlemesinden düşer |

#### ST-Session — Oturum

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Kur | `ACTIVE` | Kullanıcı | Hesap `ACTIVE`, kimlik kanıtı geçerli | `SESSION_ESTABLISHED` | Yetki bağlamı hazırlanır |
| `ACTIVE` | Sonlandır | `TERMINATED` | Sahip / Security Admin | — | `SESSION_TERMINATED` | Belirteç geçersizleşir |
| `ACTIVE` | Süre dolar | `EXPIRED` | Sistem | `expires_at` geçti | `SESSION_TERMINATED` | — |

#### ST-AccessReviewItem — Erişim gözden geçirme kalemi

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Kampanya başlat | `PENDING` | Security Admin | Politika yürürlükte | `ACCESS_REVIEW_STARTED` | Onaylayıcılara bildirilir |
| `PENDING` | Onayla | `CERTIFIED` | Data Owner (≠ atama sahibi) | — | `ACCESS_REVIEW_DECIDED` | — |
| `PENDING` | Kaldır | `REVOKED` | Data Owner | — | `ACCESS_REVIEW_DECIDED` | Rol ataması iptal edilir |
| `PENDING` | Süre dolar | `AUTO_REVOKED` | Sistem | Son tarih geçti | `ACCESS_REVIEW_DECIDED` | Politikaya göre atama iptal edilir |

#### ST-DataSource — Veri kaynağı

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Oluştur | `TEST_PENDING` | Technical Steward | Ad benzersiz | `DATA_SOURCE_CREATED` | — |
| `TEST_PENDING` | Test et (başarılı) | `TEST_SUCCEEDED` | Technical Steward | Sır bağlı | `CONNECTION_TESTED` | — |
| `TEST_PENDING` | Test et (başarısız) | `TEST_FAILED` | Technical Steward | — | `CONNECTION_TESTED` | — |
| `TEST_FAILED` | Yeniden test et | `TEST_SUCCEEDED` | Technical Steward | — | `CONNECTION_TESTED` | — |
| `TEST_SUCCEEDED` | Aktivasyon onaylanır | `ACTIVE` | Data Owner (checker≠maker) | Test güncel revizyona ait | `DATA_SOURCE_ACTIVATION_DECIDED` | Çalıştırmaya açılır |
| `ACTIVE` | Pasifleştir | `INACTIVE` | Data Owner / Operations | — | `DATA_SOURCE_DEACTIVATED` | Yeni çalıştırma kabul edilmez |
| `INACTIVE` | Arşivle | `ARCHIVED` | Data Owner | Aktif kural ve açık sorun yok | `DATA_SOURCE_ARCHIVED` | Bağlı dataset'ler arşivlenir |

#### ST-ConnectionRevision — Bağlantı revizyonu

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Revizyon oluştur | `DRAFT` | Technical Steward | Açık taslak yok | `CONNECTION_REVISION_CREATED` | — |
| `DRAFT` | Test et | `TESTED` | Technical Steward | — | `CONNECTION_TESTED` | — |
| `TESTED` | Yürürlüğe al | `EFFECTIVE` | Technical Steward / Data Owner | — | `CONNECTION_REVISION_APPLIED` | Önceki `SUPERSEDED`; açık aktivasyon talepleri `EXPIRED` |
| `EFFECTIVE` | Geri al | `ROLLED_BACK` | Operations / Technical Steward | Hedef revizyon var | `CONNECTION_REVISION_ROLLED_BACK` | Hedef `EFFECTIVE` olur |

#### ST-Dataset — Dataset

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Keşiften oluştur | `ACTIVE` | Sistem / Technical Steward | Kimlik üçlüsü benzersiz | `DATASET_UPSERTED` | — |
| `ACTIVE` | Kaynakta bulunamadı | `SUSPECTED_REMOVED` | Sistem | Tam keşif sonucu | `METADATA_DIFF_APPLIED` | Ölçüm askıya alınır |
| `SUSPECTED_REMOVED` | Arşivle | `ARCHIVED` | Technical Steward | Aktif sözleşme yok | `DATASET_ARCHIVED` | Bağlı kurallar arşivlenir |
| `SUSPECTED_REMOVED` | Yeniden görüldü | `ACTIVE` | Sistem | — | `DATASET_UPSERTED` | Ölçüm sürer |

#### ST-SchemaChange — Şema değişikliği

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Tespit et ve sınıflandır | `PENDING_DECISION` | Sistem | Fark hesaplandı | `SCHEMA_CHANGE_CLASSIFIED` | Kırıcıysa bildirilir |
| `PENDING_DECISION` | Kabul et | `ACCEPTED` | Data Owner / Technical Steward | — | `SCHEMA_CHANGE_DECIDED` | Etkilenen kurallar `REVIEW_REQUIRED` |
| `PENDING_DECISION` | Blokla | `BLOCKED` | Data Owner | — | `SCHEMA_CHANGE_DECIDED` | Ölçüm durdurulur |
| `PENDING_DECISION` | Süre dolar | `AUTO_BLOCKED` | Sistem | Politika süresi geçti | `SCHEMA_CHANGE_DECIDED` | Ölçüm otomatik bloklanır |

#### ST-Profile — Profil çalıştırması

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Talep et | `QUEUED` | Steward / Sistem | Politika yürürlükte | `PROFILE_REQUESTED` | İş kuyruğa alınır |
| `QUEUED` | Başlat | `RUNNING` | Sistem | Kota ve pencere uygun | — | — |
| `RUNNING` | Tamamla | `SUCCESS` | Sistem | — | — | Metrikler kaydedilir |
| `RUNNING` | Kısmi tamamla | `PARTIAL` | Sistem | Alan bazlı hata | — | Baseline olamaz |
| `RUNNING` | Teknik hata | `TECHNICAL_ERROR` | Sistem | — | — | — |
| `QUEUED`\|`RUNNING` | İptal talep et | `CANCEL_REQUESTED` | Operations / talep sahibi | — | `PROFILE_CANCELLED` | Sorgu sonlandırılır |
| `CANCEL_REQUESTED` | İptali tamamla | `CANCELLED` | Sistem | — | `PROFILE_CANCELLED` | — |

#### ST-ProfileBaseline — Profil baseline'ı

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Baseline belirle | `ACTIVE` | Data Steward / Owner | Profil `SUCCESS` | `PROFILE_BASELINE_SET` | Önceki `SUPERSEDED` |
| `ACTIVE` | Yeni baseline atanır | `SUPERSEDED` | Sistem | — | `PROFILE_BASELINE_SET` | — |
| `ACTIVE` | Geçersiz kıl | `INVALIDATED` | Data Steward / Owner | — | `PROFILE_BASELINE_INVALIDATED` | Drift hükmü `NOT_QUALIFIED` olur |

#### ST-RuleTemplate — Kural şablonu

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Tanımla | `DRAFT` | Governance Admin / Rule Author | Kod benzersiz | `RULE_TEMPLATE_DRAFTED` | — |
| `DRAFT` | Yayımla | `PUBLISHED` | Governance Admin (≠ yazan) | Sınama başarılı | `RULE_TEMPLATE_PUBLISHED` | Kural üretiminde kullanılabilir |
| `PUBLISHED` | Kullanımdan kaldır | `DEPRECATED` | Governance Admin | — | `RULE_TEMPLATE_DEPRECATED` | Kritik hatada bağlı kurallar `REVIEW_REQUIRED` |

#### ST-QualityRule — Kalite kuralı

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Oluştur | `DRAFT` | Rule Author | Şablon `PUBLISHED` | `QUALITY_RULE_CREATED` | İlk sürüm `DRAFT` |
| `DRAFT` | Sürüm aktive edilir | `ACTIVE` | Data Steward | Sürüm `APPROVED` | `RULE_VERSION_ACTIVATED` | Zamanlamalara dâhil olur |
| `ACTIVE` | Bağımlılık değişti | `REVIEW_REQUIRED` | Sistem | Alan tipi/şablon değişimi | `METADATA_DIFF_APPLIED` | Ölçüm sürer, uyarı verilir |
| `REVIEW_REQUIRED` | Yeni sürüm aktive edilir | `ACTIVE` | Data Steward | — | `RULE_VERSION_ACTIVATED` | — |
| `ACTIVE`\|`REVIEW_REQUIRED` | Pasifleştir | `PASSIVE` | Data Steward / Owner | Kritikse görev ayrılığı | `QUALITY_RULE_DEACTIVATED` | Zamanlamalardan çıkar |
| `PASSIVE` | Arşivle | `ARCHIVED` | Data Owner | Açık sorun yok | `QUALITY_RULE_ARCHIVED` | Geçmiş korunur |

#### ST-RuleVersion — Kural sürümü

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Sürüm oluştur | `DRAFT` | Rule Author | Açık taslak yok | `RULE_VERSION_CREATED` | — |
| `DRAFT` | Onaya gönder | `SEALED` → `PENDING_APPROVAL` | Rule Author (maker) | Güncel başarılı test var | `RULE_APPROVAL_REQUESTED` | Tanım değişmez hâle gelir |
| `PENDING_APPROVAL` | Onayla | `APPROVED` | Rule Approver (checker≠maker) | — | `RULE_APPROVAL_DECIDED` | — |
| `PENDING_APPROVAL` | Reddet | `DRAFT` | Rule Approver | Gerekçe zorunlu | `RULE_APPROVAL_DECIDED` | — |
| `PENDING_APPROVAL` | Geri çek | `DRAFT` | Rule Author (maker) | — | `RULE_APPROVAL_WITHDRAWN` | — |
| `PENDING_APPROVAL` | Süre dolar | `DRAFT` | Sistem | Son karar tarihi geçti | `RULE_APPROVAL_EXPIRED` | — |
| `APPROVED` | Aktive et | `ACTIVE` | Data Steward | Dataset `ACTIVE` | `RULE_VERSION_ACTIVATED` | Önceki sürüm `SUPERSEDED` |
| `ACTIVE` | Yeni sürüm aktive edilir | `SUPERSEDED` | Sistem | — | `RULE_VERSION_ACTIVATED` | Geçmiş sonuçlar korunur |

#### ST-ApprovalRequest — Onay talebi (ortak)

Politika, kaynak aktivasyonu, kural sürümü, istisna ve sözleşme onaylarının
ortak davranışı.

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Talep aç | `PENDING` | Maker | Aynı nesne için açık talep yok | `*_REQUESTED` | Checker'lara bildirilir |
| `PENDING` | Onayla | `APPROVED` | Checker (≠ maker) | Nesne sürümü değişmemiş | `*_DECIDED` | Nesne durum geçişi tetiklenir |
| `PENDING` | Reddet | `REJECTED` | Checker | Gerekçe zorunlu | `*_DECIDED` | Nesne taslağa döner |
| `PENDING` | Geri çek | `WITHDRAWN` | Maker | — | `*_WITHDRAWN` | — |
| `PENDING` | Süre dolar | `EXPIRED` | Sistem | Son tarih geçti | `*_EXPIRED` | Nesne taslağa döner |

#### ST-Schedule — Zamanlama

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Tanımla | `ACTIVE` | Data Steward / Operations | Kural sürümleri `ACTIVE` | `SCHEDULE_CREATED` | `next_run_at` hesaplanır |
| `ACTIVE` | Duraklat | `PAUSED` | Operations / Steward | — | `SCHEDULE_STATE_CHANGED` | Tetikleme durur |
| `PAUSED` | Sürdür | `ACTIVE` | Operations / Steward | — | `SCHEDULE_STATE_CHANGED` | `next_run_at` yeniden hesaplanır |
| `ACTIVE`\|`PAUSED` | Sil | `DELETED` | Data Steward | Devam eden çalıştırma yok | `SCHEDULE_DELETED` | Geçmiş bağı korunur |

#### ST-Job — Kalıcı iş

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Kuyruğa al | `AVAILABLE` | Sistem | İşleyici kayıtlı | `JOB_ENQUEUED` | İş transaction'ıyla atomik |
| `AVAILABLE` | Sahiplen | `CLAIMED` | Worker | Kota ve pencere uygun | `JOB_CLAIMED` | Lease verilir |
| `CLAIMED` | Yürüt | `RUNNING` | Worker | — | — | Heartbeat başlar |
| `RUNNING` | Tamamla | `COMPLETED` | Worker | — | — | Sonuç yazılır |
| `RUNNING` | Geçici hata | `AVAILABLE` | Sistem | Deneme sınırı aşılmadı | `JOB_RETRY_SCHEDULED` | Üstel geri çekilme |
| `RUNNING` | Lease süresi dolar | `AVAILABLE` | Sistem (kurtarma) | — | `JOB_LEASE_RECLAIMED` | Eski worker sonuç yazamaz |
| `RUNNING`\|`AVAILABLE` | Sınır aşıldı / kalıcı hata | `DEAD_LETTERED` | Sistem | — | `JOB_DEAD_LETTERED` | Dead-letter kaydı açılır |
| `AVAILABLE`\|`CLAIMED`\|`RUNNING` | İptal et | `CANCELLED` | Operations / Sistem | — | `JOB_MANUALLY_INTERVENED` | Kaynak nesne bilgilendirilir |
| `CLAIMED` | Kota/pencere uygun değil | `AVAILABLE` | Sistem | — | `SOURCE_QUOTA_THROTTLED` / `SOURCE_WINDOW_DEFERRED` | `available_at` ertelenir |
| `CLAIMED` | İzinli pencere yok | `BLOCKED` | Sistem | — | `SOURCE_WINDOW_DEFERRED` | Operatöre görünür |

#### ST-DeadLetterRecord — Dead-letter kaydı

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Oluştur | `OPEN` | Sistem | İş `DEAD_LETTERED` | `JOB_DEAD_LETTERED` | Operatöre bildirilir |
| `OPEN` | Yeniden işle | `REPROCESSED` | Operations User | Politika ve rol uygun | `DEAD_LETTER_REPROCESSED` | Yeni iş kuyruğa alınır |
| `OPEN` | Kapat | `CLOSED` | Operations User | Gerekçe zorunlu | `DEAD_LETTER_CLOSED` | Ölçüm boşluğu işaretlenir |

#### ST-RuleExecution — Çalıştırma

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Başlat | `QUEUED` | Steward / Operations / Sistem | Kural ve kaynak `ACTIVE` | `EXECUTION_STARTED` | Plan üretilir, işler kuyruğa alınır |
| `QUEUED` | Yürütmeye geç | `RUNNING` | Sistem | İş sahiplenildi | — | — |
| `RUNNING` | Tamamla | `SUCCESS` | Sistem | Tüm kurallar tamamlandı | `RULE_RESULT_RECORDED` | Yeterlilik ve skor tetiklenir |
| `RUNNING` | Kısmi tamamla | `PARTIAL` | Sistem | Bazı bölüm/kural başarısız | `RULE_RESULT_RECORDED` | Yeterlilik düşer |
| `RUNNING` | Teknik hata | `TECHNICAL_ERROR` | Sistem | — | `EXECUTION_TECHNICAL_ERROR` | Kalite sonucu üretilmez |
| `RUNNING` | Zaman aşımı | `TIMEOUT` | Sistem | Sınır aşıldı | `EXECUTION_TIMED_OUT` | Yeniden deneme değerlendirilir |
| `QUEUED`\|`RUNNING` | İptal talep et | `CANCEL_REQUESTED` | Operations / başlatan | — | `EXECUTION_CANCEL_REQUESTED` | İşlere iptal sinyali |
| `CANCEL_REQUESTED` | İptali tamamla | `CANCELLED` | Sistem | — | `EXECUTION_CANCELLED` | Kısmi sonuç skordan dışlanır |

#### ST-QualityScore — Kalite skoru

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Hesapla | `CALCULATED` | Sistem | Yeterlilik `QUALIFIED`/`PARTIALLY_QUALIFIED` | `RULE_SCORE_CALCULATED` | Katkı bileşenleri kaydedilir |
| `—` | Yetersiz ölçüm | `NOT_QUALIFIED` | Sistem | Yeterlilik `NOT_QUALIFIED` | `MEASUREMENT_QUALIFICATION_ISSUED` | Skor değeri üretilmez |
| `—` | Uygun kural yok | `NO_DATA` | Sistem | Dâhil edilebilir bileşen yok | `SCORE_AGGREGATED` | — |
| `CALCULATED` | Yayımla | `PUBLISHED` | Sistem | Tüm seviyeler hesaplandı | `SCORE_PUBLISHED` | Atomik; önceki yayım `SUPERSEDED` |
| `PUBLISHED` | Yeni yayım | `SUPERSEDED` | Sistem | — | `SCORE_PUBLISHED` | Geçmiş korunur |

#### ST-Issue — Sorun

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Aç | `NEW` | Sistem / Steward | Yeterlilik uygun; istisna kapsamında değil | `ISSUE_CREATED` | SLA hedefleri atanır, bildirilir |
| `NEW` | Ata | `ASSIGNED` | Steward / Owner | Aday kapsamı yeterli | `ISSUE_ASSIGNED` | Atanana bildirilir |
| `NEW`\|`ASSIGNED` | İncelemeyi başlat | `INVESTIGATING` | Issue Assignee | Aktör atanan | `ISSUE_INVESTIGATION_STARTED` | İlk yanıt SLA'i işaretlenir |
| `INVESTIGATING` | Bekletmeye al | `WAITING_FOR_RESOLUTION` | Issue Assignee | Gerekçe ve beklenen tarih | `ISSUE_PUT_ON_HOLD` | SLA duraklatılır |
| `INVESTIGATING`\|`WAITING_FOR_RESOLUTION` | Çözümü kaydet | `RESOLVED` | Issue Assignee | Kök neden ve aksiyon dolu | `ISSUE_RESOLVED` | Doğrulayıcıya bildirilir |
| `RESOLVED` | Doğrula (başarılı) | `VERIFIED` | Issue Verifier (≠ çözen) | Bağımsız ölçüm kanıtı | `ISSUE_VERIFIED` | — |
| `RESOLVED` | Doğrula (başarısız) | `INVESTIGATING` | Issue Verifier | — | `ISSUE_VERIFIED` | Atanana geri döner |
| `VERIFIED` | Kapat | `CLOSED` | Issue Verifier / Owner | — | `ISSUE_CLOSED` | SLA durdurulur |
| herhangi açık | İptal et | `CANCELLED` | Data Owner | Gerekçe zorunlu | `ISSUE_CLOSED` | Yeniden açılamaz |
| `CLOSED` | Aynı bozulma tekrarlar | `NEW` | Sistem / Steward | Yeniden açma penceresi içinde | `ISSUE_REOPENED` | `RECURRENCE` ilişkisi kurulur |

#### ST-Exception — İstisna

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Talep et | `PENDING` | Data Owner / Steward (maker) | Bitiş tarihi zorunlu | `EXCEPTION_REQUESTED` | Onaylayıcıya bildirilir |
| `PENDING` | Onayla | `ACTIVE` | Governance Admin / Owner (≠ maker) | — | `EXCEPTION_DECIDED` | Sorun üretimi bastırılır, kalite borcu açılır |
| `PENDING` | Reddet | `REJECTED` | Checker | Gerekçe zorunlu | `EXCEPTION_DECIDED` | — |
| `ACTIVE` | Süre dolar | `EXPIRED` | Sistem | `valid_until` geçti | `EXCEPTION_EXPIRED` | Bastırma kalkar, birikmiş sorunlar açılır |
| `ACTIVE` | Erken iptal et | `REVOKED` | Governance Admin / onaylayan | Gerekçe zorunlu | `EXCEPTION_REVOKED` | Bastırma kalkar |

#### ST-RemediationAction — Düzeltme aksiyonu

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Oluştur | `PLANNED` | Issue Assignee / Owner | Hedef tarih zorunlu | `REMEDIATION_ACTION_CREATED` | Sahibe bildirilir |
| `PLANNED` | Başlat | `IN_PROGRESS` | Aksiyon sahibi | — | — | — |
| `IN_PROGRESS` | Tamamla | `COMPLETED` | Aksiyon sahibi / Sistem | Kanıt referansı zorunlu | `REMEDIATION_ACTION_COMPLETED` | Etki ölçümü tetiklenir |
| `IN_PROGRESS` | Otomatik yürütme başarısız | `FAILED` | Sistem | — | `REMEDIATION_AUTO_EXECUTED` | Sahibe bildirilir |
| `PLANNED`\|`IN_PROGRESS` | İptal et | `CANCELLED` | Aksiyon sahibi | Gerekçe zorunlu | — | — |

#### ST-DataContract — Veri sözleşmesi

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Taslak oluştur | `DRAFT` | Üretici Data Owner | Taahhütler ölçülebilir | `DATA_CONTRACT_DRAFTED` | — |
| `DRAFT` | Onaya sun | `PENDING_ACCEPTANCE` | Üretici Data Owner | — | `DATA_CONTRACT_ACCEPTED` | Taraflara bildirilir |
| `PENDING_ACCEPTANCE` | Her iki taraf onaylar | `ACTIVE` | Üretici + tüketici Owner | İkisi de onayladı | `DATA_CONTRACT_ACCEPTED` | İzleme kuralları bağlanır |
| `PENDING_ACCEPTANCE` | Karşı teklif | `DRAFT` | Tüketici Owner | — | — | — |
| `ACTIVE` | İhlal eşiği aşılır | `BREACHED` | Sistem | Yeterlilik uygun, tolerans aşıldı | `DATA_CONTRACT_BREACHED` | Sorun açılır, taraflara bildirilir |
| `BREACHED` | Ardışık uyum sağlanır | `ACTIVE` | Sistem / Owner | Geri kazanım penceresi | `DATA_CONTRACT_RECOVERED` | İhlal kaydı kapanır |
| `ACTIVE`\|`BREACHED` | Sonlandır | `TERMINATED` | Her iki taraf Owner | — | `DATA_CONTRACT_TERMINATED` | İzleme kuralları serbest kalır |
| `ACTIVE` | Yeni sürüm aktive edilir | `SUPERSEDED` | Sistem | — | `DATA_CONTRACT_ACCEPTED` | — |

#### ST-ReportJob — Rapor

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Talep et | `PENDING` | Report Consumer / Owner | Hassasiyet politikası çözümlendi | `REPORT_REQUESTED` | Üretim işi kuyruğa alınır |
| `PENDING` | Üretmeye başla | `GENERATING` | Sistem | İş sahiplenildi | — | — |
| `GENERATING` | Tamamla | `READY` | Sistem | — | `REPORT_GENERATED` | Talep edene bildirilir |
| `GENERATING` | Başarısız | `FAILED` | Sistem | — | — | Yeniden denenir |
| `PENDING`\|`GENERATING` | İptal et | `CANCELLED` | Talep eden / Operations | — | `REPORT_CANCELLED` | Kısmi dosya silinir |
| `READY` | Saklama süresi dolar | `EXPIRED` | Sistem | Yasal muhafaza yok | `REPORT_FILE_DESTROYED` | Dosya imha edilir, metadata kalır |

#### ST-NotificationDelivery — Bildirim teslimatı

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Teslimat oluştur | `PENDING` | Sistem | Abonelik eşleşti | `NOTIFICATION_EVENT_PUBLISHED` | — |
| `PENDING` | Gönder | `SENDING` | Sistem | Kanal `ACTIVE` | — | — |
| `SENDING` | Başarılı | `DELIVERED` | Sistem | — | `NOTIFICATION_DELIVERY_ATTEMPTED` | — |
| `SENDING` | Geçici hata | `FAILED` | Sistem | Deneme sınırı aşılmadı | `NOTIFICATION_DELIVERY_ATTEMPTED` | Yeniden denenir |
| `FAILED` | Sınır aşıldı | `UNDELIVERABLE` | Sistem | — | `NOTIFICATION_UNDELIVERABLE` | Operatöre bildirilir |
| `UNDELIVERABLE` | Alternatif kanala yönlendir | `REROUTED` | Sistem / Operations | Alternatif kanal var | `NOTIFICATION_UNDELIVERABLE` | — |
| `DELIVERED` | Okundu işaretle | `READ` | Alıcı | — | — | Sayaç güncellenir |

#### ST-IntegrationRecord — Entegrasyon kaydı

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Gönderim hazırla | `PENDING` | Sistem | Eşleme kuralı eşleşti | — | — |
| `PENDING` | Gönder | `SENT` | Sistem / Assignee | Entegrasyon `ACTIVE` | `INTEGRATION_RECORD_SENT` | Dış kimlik ilişkilendirilir |
| `PENDING` | Kalıcı hata | `FAILED` | Sistem | Deneme sınırı aşıldı | `INTEGRATION_RECORD_SENT` | Operatöre bildirilir |
| `SENT` | Güncelle | `UPDATED` | Sistem | Sorun değişti | `INTEGRATION_RECORD_UPDATED` | — |
| `SENT`\|`UPDATED` | Dış kayıt bulunamadı | `ORPHANED` | Sistem | — | `INTEGRATION_RECORD_UPDATED` | İlişki koparılır, işaretlenir |

#### ST-LegalHold — Yasal muhafaza

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Uygula | `ACTIVE` | Governance Admin / Auditor | Gerekçe zorunlu | `LEGAL_HOLD_APPLIED` | Kapsam imha dışına alınır |
| `ACTIVE` | Kaldır | `RELEASED` | Uygulayan / Governance Admin | Gerekçe zorunlu | `LEGAL_HOLD_RELEASED` | Süresi geçmişler imha kuyruğuna girer |

#### ST-OperationalIncident — Operasyonel olay

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Aç | `OPEN` | Operations / Sistem | Şiddet tanımlı | `OPERATIONAL_INCIDENT_OPENED` | Sorumlu atanır, bildirilir |
| `OPEN` | Azaltma sağlandı | `MITIGATED` | Olay sorumlusu | — | `OPERATIONAL_INCIDENT_UPDATED` | — |
| `MITIGATED` | Kapat | `CLOSED` | Olay sorumlusu | Kök neden kaydedildi | `OPERATIONAL_INCIDENT_CLOSED` | İzleme aksiyonları açılır |

### 6.2 Rol ve izin matrisi

#### 6.2.1 Roller

| Rol | Sorumluluk özeti | Varsayılan kapsam tipi |
|---|---|---|
| **Platform Admin** | Sistem konfigürasyonu, özellik anahtarları, altyapı ve operasyon | Kurum geneli |
| **Security Admin** | Kimlik, rol, izin, görev ayrılığı, oturum, erişim gözden geçirme | Kurum geneli |
| **Data Governance Admin** | Domain yapısı, sahiplik, sözlük, politika, saklama, istisna onayı | Kurum geneli |
| **Data Owner** | Sahip olduğu varlıkların kalitesinden ve kararlarından sorumlu | Domain / kaynak |
| **Data Steward** | Günlük kalite yönetimi: kural, sorun, profil, sınıflandırma | Domain / dataset |
| **Technical Data Steward** | Kaynak bağlantısı, metadata, şema, teknik ölçüm sağlığı | Kaynak / dataset |
| **Rule Author** | Kural ve sürüm tasarımı, test, onaya gönderme | Dataset |
| **Rule Approver** | Kural sürümü onayı (yazandan bağımsız) | Dataset |
| **Issue Assignee** | Sorun inceleme ve çözüm | Atanan sorunlar |
| **Issue Verifier** | Çözümün bağımsız doğrulanması (çözenden farklı) | Dataset / domain |
| **Report Consumer** | Rapor talebi, indirme, sözleşme tüketiciliği | Domain / dataset |
| **Auditor** | Salt okunur denetim; audit, istisna, imha kanıtı, geri çağırma | Kurum geneli (salt okunur) |
| **Operations User** | Kuyruk, worker, dead-letter, olay, bakım, telafi | Kurum geneli |
| **Integration Service Account** | Programatik erişim; lineage yazma, entegrasyon geri bildirimi | Dar, amaç bazlı |
| **Read-only Viewer** | Yalnız görüntüleme | Domain / dataset |

#### 6.2.2 İzin × rol matrisi

Kısaltmalar: **PA** Platform Admin · **SA** Security Admin · **GA** Data Governance
Admin · **DO** Data Owner · **DS** Data Steward · **TS** Technical Data Steward ·
**RA** Rule Author · **RP** Rule Approver · **IA** Issue Assignee · **IV** Issue
Verifier · **RC** Report Consumer · **AU** Auditor · **OP** Operations User ·
**IS** Integration Service Account · **RV** Read-only Viewer.

Kapsam tipi: `KG` kurum geneli · `DOM` domain · `SRC` kaynak · `DS` dataset ·
`OBJ` nesne sahipliği · `SYS` yalnız sistem aktörü.

| İzin kodu | Roller | Kapsam |
|---|---|---|
| `org.unit.manage` | PA | KG |
| `governance.domain.manage` | GA | KG |
| `governance.domain.assign` | GA, DO | DOM |
| `governance.ownership.assign` | GA, DO | DOM |
| `governance.ownership.transfer` | GA, DO | DOM |
| `governance.ownership.read` | GA, DO, AU | DOM |
| `governance.scan.execute` | — (SYS) | SYS |
| `glossary.term.propose` | DS, DO | DOM |
| `glossary.term.approve` | GA | DOM |
| `glossary.term.manage` | GA | DOM |
| `glossary.mapping.manage` | DS, TS | DS |
| `policy.draft.create` | GA, PA | KG |
| `policy.submit` | GA | KG |
| `policy.approve` | SA, GA | KG |
| `policy.activate` | PA, GA | KG |
| `policy.rollback` | PA | KG |
| `system.config.manage` | PA | KG |
| `system.config.read` | PA, AU | KG |
| `system.feature.manage` | PA | KG |
| `identity.user.manage` | SA | KG |
| `identity.service-account.manage` | SA | KG |
| `identity.service-account.rotate` | SA, OBJ sahibi | KG / OBJ |
| `identity.role.manage` | SA | KG |
| `identity.role.assign` | SA | KG |
| `identity.permission.read` | SA, AU | KG |
| `identity.sod.manage` | SA | KG |
| `identity.scope.assign` | SA, GA | KG |
| `identity.session.read` | SA, AU, OBJ sahibi | KG / OBJ |
| `identity.session.terminate` | SA, OBJ sahibi | KG / OBJ |
| `identity.access-review.manage` | SA | KG |
| `identity.access-review.decide` | DO, SA | DOM |
| `datasource.create` | TS, DO | DOM |
| `datasource.read` | TS, DS, DO, OP, AU, RV | SRC |
| `datasource.secret.bind` | TS, SA | SRC |
| `datasource.test.execute` | TS | SRC |
| `datasource.activation.request` | TS | SRC |
| `datasource.activation.decide` | DO | SRC |
| `datasource.deactivate` | DO, OP | SRC |
| `datasource.archive` | DO, GA | SRC |
| `datasource.policy.manage` | TS, PA | SRC |
| `datasource.connection.revise` | TS | SRC |
| `datasource.connection.apply` | TS, DO, OP | SRC |
| `datasource.healthcheck.execute` | — (SYS) | SYS |
| `catalog.discovery.execute` | TS | SRC |
| `catalog.discovery.configure` | TS | SRC |
| `catalog.diff.apply` | TS | SRC |
| `catalog.dataset.manage` | TS | SRC |
| `catalog.dataset.classify` | DO, GA | DS |
| `catalog.field.manage` | TS | DS |
| `catalog.field.classify` | DS, GA | DS |
| `catalog.classification.scan` | — (SYS) | SYS |
| `catalog.schema-change.decide` | DO, TS | DS |
| `catalog.read` | tüm okuma yetkili roller | DS |
| `profile.execute` | DS, TS | DS |
| `profile.cancel` | OP, OBJ sahibi | DS / OBJ |
| `profile.compare` | DS, TS | DS |
| `profile.baseline.manage` | DS, DO | DS |
| `quality.dimension.manage` | GA | KG |
| `rule.template.manage` | GA, RA | KG |
| `rule.template.publish` | GA | KG |
| `rule.create` | RA, DS | DS |
| `rule.create.custom-query` | RA | DS |
| `rule.version.create` | RA | DS |
| `rule.test.execute` | RA | DS |
| `rule.approval.request` | RA | DS |
| `rule.approval.decide` | RP | DS |
| `rule.approval.expire` | — (SYS) | SYS |
| `rule.activate` | DS, RA | DS |
| `rule.deactivate` | DS, DO | DS |
| `rule.archive` | DO | DS |
| `rule.read` | RA, RP, DS, DO, TS, AU, RV | DS |
| `rule.shadow.execute` | RA, DS | DS |
| `rule.shadow.read` | RA, DS | DS |
| `execution.start` | DS, OP | DS + SRC |
| `execution.cancel` | OP, OBJ sahibi | DS / OBJ |
| `execution.read` | DS, OP, DO, TS, AU, RV | SRC / DS |
| `schedule.manage` | DS, OP | DS + SRC |
| `schedule.trigger.execute` | — (SYS) | SYS |
| `job.priority.override` | OP | KG |
| `evidence.sample.read` | IA, DS, TS | DS |
| `score.read` | DO, DS, GA, AU, RC, RV | DOM / DS |
| `score.reproduce` | AU, DO | DOM / DS |
| `risk.model.manage` | GA | KG |
| `risk.read` | DO, GA, AU, RV | DOM |
| `issue.create` | DS, DO, RC | DS |
| `issue.read` | IA, IV, DS, DO, AU, RV | DS / DOM |
| `issue.assign` | DS, DO | DS |
| `issue.investigate` | IA | OBJ |
| `issue.comment` | IA, DS, DO | DS |
| `issue.resolve` | IA | OBJ |
| `issue.verify` | IV | DS / DOM |
| `issue.close` | IV, DO | DS |
| `issue.reopen` | DS | DS |
| `exception.request` | DO, DS | DS / DOM |
| `exception.decide` | GA, DO | DOM |
| `exception.revoke` | GA, onaylayan | DOM |
| `exception.read` | GA, AU, DO | DOM |
| `remediation.manage` | IA, DO | DS |
| `remediation.execute` | OBJ sahibi | OBJ |
| `remediation.auto.execute` | — (SYS, politikayla sınırlı) | SYS |
| `lineage.write` | IS | SRC |
| `lineage.read` | DS, TS, IA, RV | DS |
| `lineage.impact.read` | DS, TS, IA, DO | DS |
| `lineage.impact.simulate` | TS, RA | DS |
| `contract.manage` | DO | DS |
| `contract.accept` | DO (her iki taraf) | DS / DOM |
| `contract.read` | DO, RC, DS, AU, RV | DS / DOM |
| `quality-debt.manage` | DS, DO, GA | DOM |
| `quality-debt.read` | DO, GA, AU, RV | DOM |
| `dashboard.read` | tüm okuma yetkili roller | DOM / DS |
| `analytics.read` | DO, DS, GA, AU, RC | DOM |
| `analytics.export` | DO, GA, RC | DOM |
| `report.request` | RC, DO, AU | DOM / DS |
| `report.preview` | RC, DO | DOM / DS |
| `report.read` | RC, DO, AU | OBJ |
| `report.read.all` | AU | KG |
| `report.download` | RC, DO, AU | OBJ |
| `report.cancel` | OP, OBJ sahibi | KG / OBJ |
| `report.schedule.manage` | RC, DO | DOM / DS |
| `notification.subscription.manage` | tüm kullanıcı rolleri (kendi) | OBJ |
| `notification.subscription.manage.all` | PA | KG |
| `notification.channel.manage` | PA | KG |
| `notification.delivery.read` | OP, PA | KG |
| `notification.delivery.manage` | OP | KG |
| `integration.outbound.execute` | — (SYS) | SYS |
| `integration.outbound.trigger` | IA, DS | DS |
| `integration.inbound.write` | IS | SRC / DS |
| `audit.read` | AU, SA | KG |
| `audit.read.object` | AU, DO, GA | OBJ |
| `audit.verify` | AU | KG |
| `audit.outbox.read` | OP, SA | KG |
| `retention.policy.manage` | GA | KG |
| `retention.disposal.execute` | — (SYS) | SYS |
| `retention.disposal.read` | AU, GA | KG |
| `retention.legal-hold.manage` | GA, AU | KG |
| `retention.archive.recall` | AU, GA | KG |
| `operations.health.read` | OP, PA | KG |
| `operations.queue.read` | OP | KG |
| `operations.queue.manage` | OP | KG |
| `operations.worker.read` | OP | KG |
| `operations.worker.manage` | OP, PA | KG |
| `operations.dead-letter.read` | OP | KG |
| `operations.dead-letter.reprocess` | OP | KG |
| `operations.dead-letter.close` | OP | KG |
| `operations.incident.manage` | OP | KG |
| `operations.maintenance.manage` | PA, OP | KG |
| `operations.backfill.execute` | OP | KG |
| `synthetic.generate` | TS, PA | KG |
| `synthetic.manage` | TS | KG |
| `synthetic.profile.manage` | TS | KG |
| `synthetic.ground-truth.manage` | TS | KG |
| `synthetic.validate.execute` | TS | KG |
| `synthetic.experiment.execute` | PA, TS | KG |

#### 6.2.3 Görev ayrılığı çiftleri

Aynı aktörde birleşmesi kontrol zafiyeti yaratan izinler. `BLOCK` seviyesi
atamayı engeller; `WARN` uyarı üretir.

| İzin A | İzin B | Seviye | Gerekçe |
|---|---|---|---|
| `rule.approval.request` | `rule.approval.decide` | BLOCK | Kural sürümünü yazan onaylayamaz |
| `datasource.activation.request` | `datasource.activation.decide` | BLOCK | Kaynağı hazırlayan devreye alamaz |
| `policy.submit` | `policy.approve` | BLOCK | Politika değişikliğini talep eden onaylayamaz |
| `exception.request` | `exception.decide` | BLOCK | İstisnayı talep eden riski kabul edemez |
| `issue.resolve` | `issue.verify` | BLOCK | Çözümü yapan doğrulayamaz |
| `glossary.term.propose` | `glossary.term.approve` | BLOCK | Terimi öneren onaylayamaz |
| `rule.template.manage` | `rule.template.publish` | BLOCK | Şablonu yazan yayımlayamaz |
| `identity.role.assign` | `identity.access-review.decide` | BLOCK | Yetkiyi veren gözden geçiremez |
| `identity.role.manage` | `audit.read` | WARN | Yetki tanımlayan denetim izini incelememeli |
| `retention.disposal.read` | `retention.legal-hold.manage` | WARN | İmha ve muhafaza kararları ayrışmalı |
| `synthetic.generate` | `synthetic.validate.execute` | WARN | Test verisini üreten doğruluğu tek başına ölçmemeli |
| `operations.dead-letter.close` | `operations.backfill.execute` | WARN | Boşluğu kapatan telafiyi tek başına yönetmemeli |

Ek kısıtlar (izin çiftiyle ifade edilemeyen, nesne düzeyinde uygulananlar):

| Kural | Uygulama noktası |
|---|---|
| Aktör kendi rol atamasını gözden geçiremez | `D02.C05.W01.A02` |
| Sözleşmenin iki tarafını aynı aktör onaylayamaz | `D10.C03.W01.A02` |
| İstisnayı onaylayan iptal edebilir, ancak talep eden edemez | `D09.C04.W03.A02` |
| Arşiv geri çağırma talebi ve kararı farklı aktörlerde olmalıdır | `D13.C04.W02.A01` |

### 6.3 Audit olay kataloğu

Gövdedeki yapraklarda üretilen 250 audit olayı. Hassasiyet sınıfı, olayın
saklama ve erişim rejimini belirler.

| Sınıf | Anlam | Erişim |
|---|---|---|
| `STD` | Standart durum değiştiren işlem | `audit.read` |
| `SEC` | Güvenlik, kimlik veya yetki olayı | `audit.read`; güvenlik gözden geçirmesine dâhil |
| `SENS` | Hassas veri veya çıktıya erişim | `audit.read`; ayrıca hassas erişim raporlarında |
| `ACC` | Salt okuma erişim kaydı | `audit.read`; kısa saklama |
| `SYS` | Sistem/operasyon olayı | `audit.read`, `operations.*` |

#### D01 — Yönetişim, organizasyon ve politika

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `ORG_UNIT_CREATED` | STD | | `GLOSSARY_TERM_PROPOSED` | STD |
| `ORG_UNIT_UPDATED` | STD | | `GLOSSARY_TERM_APPROVED` | STD |
| `ORG_UNIT_DEACTIVATED` | STD | | `GLOSSARY_TERM_DEPRECATED` | STD |
| `BUSINESS_DOMAIN_CREATED` | STD | | `GLOSSARY_TERM_MAPPED` | STD |
| `DATA_DOMAIN_CREATED` | STD | | `POLICY_DRAFT_CREATED` | STD |
| `DOMAIN_ASSET_ASSIGNED` | STD | | `POLICY_SUBMITTED_FOR_APPROVAL` | STD |
| `ASSET_OWNER_ASSIGNED` | STD | | `POLICY_APPROVAL_DECIDED` | SEC |
| `ASSET_STEWARD_ASSIGNED` | STD | | `POLICY_MADE_EFFECTIVE` | SEC |
| `OWNERSHIP_TRANSFERRED` | STD | | `POLICY_ROLLED_BACK` | SEC |
| `GOVERNANCE_GAP_DETECTED` | SYS | | `SYSTEM_CONFIG_CHANGED` | SEC |
| `GOVERNANCE_GAP_VIEWED` | ACC | | `SYSTEM_CONFIG_HISTORY_VIEWED` | ACC |
| `FEATURE_FLAG_CHANGED` | SEC | | | |

#### D02 — Kimlik, rol ve erişim

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `USER_PROVISIONED` | SEC | | `SOD_RULE_DEFINED` | SEC |
| `USER_DEACTIVATED` | SEC | | `ROLE_ASSIGNED` | SEC |
| `USER_REACTIVATED` | SEC | | `ROLE_ASSIGNMENT_REVOKED` | SEC |
| `SERVICE_ACCOUNT_CREATED` | SEC | | `SCOPE_ASSIGNED` | SEC |
| `SERVICE_ACCOUNT_CREDENTIAL_ROTATED` | SEC | | `AUTHORIZATION_DENIED` | SEC |
| `ROLE_DEFINED` | SEC | | `SESSION_ESTABLISHED` | SEC |
| `ROLE_PERMISSIONS_CHANGED` | SEC | | `SESSION_TERMINATED` | SEC |
| `PERMISSION_CATALOG_VIEWED` | ACC | | `SESSION_LIST_VIEWED` | ACC |
| `ACCESS_REVIEW_STARTED` | SEC | | `ACCESS_REVIEW_DECIDED` | SEC |

#### D03 — Veri kaynağı ve bağlantı

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `DATA_SOURCE_CREATED` | STD | | `SOURCE_USAGE_POLICY_DRAFTED` | STD |
| `READ_ONLY_ENFORCEMENT_FAILED` | SEC | | `SOURCE_QUOTA_THROTTLED` | SYS |
| `SECRET_REFERENCE_BOUND` | SEC | | `SOURCE_ACCESS_WINDOW_CHANGED` | STD |
| `SECRET_RESOLUTION_FAILED` | SEC | | `SOURCE_WINDOW_DEFERRED` | SYS |
| `CONNECTION_TESTED` | STD | | `CONNECTION_REVISION_CREATED` | STD |
| `CONNECTION_TEST_HISTORY_VIEWED` | ACC | | `CONNECTION_REVISION_APPLIED` | SEC |
| `DATA_SOURCE_ACTIVATION_REQUESTED` | STD | | `CONNECTION_REVISION_ROLLED_BACK` | SEC |
| `DATA_SOURCE_ACTIVATION_DECIDED` | SEC | | `SOURCE_HEALTH_CHANGED` | SYS |
| `DATA_SOURCE_DEACTIVATED` | STD | | `SOURCE_HEALTH_VIEWED` | ACC |
| `DATA_SOURCE_ARCHIVED` | STD | | | |

#### D04 — Metadata, katalog ve varlık

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `METADATA_DISCOVERY_STARTED` | STD | | `DATA_FIELD_UPSERTED` | STD |
| `METADATA_DISCOVERY_COMPLETED` | STD | | `DATA_FIELD_CLASSIFIED` | SEC |
| `DISCOVERY_SCOPE_CHANGED` | STD | | `SENSITIVE_CANDIDATE_DETECTED` | SEC |
| `METADATA_DIFF_COMPUTED` | SYS | | `SCHEMA_CHANGE_CLASSIFIED` | SYS |
| `METADATA_DIFF_APPLIED` | STD | | `SCHEMA_CHANGE_DECIDED` | STD |
| `DATASET_UPSERTED` | STD | | `CATALOG_SEARCHED` | ACC |
| `DATASET_ARCHIVED` | STD | | `CATALOG_ASSET_VIEWED` | ACC |
| `DATASET_CRITICALITY_SET` | STD | | | |

#### D05 — Profilleme ve drift

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `PROFILE_REQUESTED` | STD | | `PROFILE_BASELINE_INVALIDATED` | STD |
| `PROFILE_CANCELLED` | STD | | `PROFILE_COMPARISON_COMPUTED` | SYS |
| `PROFILE_DISTRIBUTION_COMPUTED` | SENS | | `DRIFT_JUDGMENT_ISSUED` | SYS |
| `PROFILE_OUTLIERS_FLAGGED` | SENS | | `ISSUE_CREATED_FROM_DRIFT` | STD |
| `PROFILE_BASELINE_SET` | STD | | | |

#### D06 — Kural yönetimi

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `QUALITY_DIMENSION_CONFIGURED` | STD | | `RULE_APPROVAL_DECIDED` | SEC |
| `RULE_TEMPLATE_DRAFTED` | STD | | `RULE_APPROVAL_WITHDRAWN` | STD |
| `RULE_TEMPLATE_PUBLISHED` | SEC | | `RULE_APPROVAL_EXPIRED` | SYS |
| `RULE_TEMPLATE_DEPRECATED` | STD | | `RULE_VERSION_ACTIVATED` | SEC |
| `QUALITY_RULE_CREATED` | STD | | `QUALITY_RULE_DEACTIVATED` | SEC |
| `CUSTOM_QUERY_RULE_CREATED` | SEC | | `QUALITY_RULE_ARCHIVED` | STD |
| `RULE_VERSION_CREATED` | STD | | `RULE_DEPENDENCY_VIEWED` | ACC |
| `RULE_VERSION_TESTED` | STD | | `RULE_CONFLICT_DETECTED` | SYS |
| `RULE_APPROVAL_REQUESTED` | STD | | `SHADOW_EXECUTION_STARTED` | STD |
| `SHADOW_COMPARISON_VIEWED` | ACC | | | |

#### D07 — Yürütme, zamanlama ve kuyruk

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `EXECUTION_STARTED` | STD | | `JOB_ENQUEUED` | SYS |
| `EXECUTION_LIST_VIEWED` | ACC | | `JOB_PRIORITY_OVERRIDDEN` | SYS |
| `EXECUTION_DETAIL_VIEWED` | ACC | | `JOB_CLAIMED` | SYS |
| `EXECUTION_PLAN_BUILT` | SYS | | `JOB_LEASE_LOST` | SYS |
| `EXECUTION_CANCEL_REQUESTED` | STD | | `JOB_LEASE_RECLAIMED` | SYS |
| `EXECUTION_CANCELLED` | STD | | `JOB_RETRY_SCHEDULED` | SYS |
| `EXECUTION_TECHNICAL_ERROR` | SYS | | `JOB_DEAD_LETTERED` | SYS |
| `EXECUTION_TIMED_OUT` | SYS | | `DEAD_LETTER_LIST_VIEWED` | ACC |
| `EXECUTION_PARTITIONED` | SYS | | `DEAD_LETTER_REPROCESSED` | SYS |
| `EXECUTION_RESUMED` | SYS | | `DEAD_LETTER_CLOSED` | SYS |
| `SCHEDULE_CREATED` | STD | | `SCHEDULE_TRIGGERED` | SYS |
| `SCHEDULE_STATE_CHANGED` | STD | | `SCHEDULE_RUN_MISSED` | SYS |
| `SCHEDULE_DELETED` | STD | | `WORKER_STATE_CHANGED` | SYS |

#### D08 — Ölçüm, sonuç ve skorlama

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `RULE_RESULT_RECORDED` | STD | | `SCORE_AGGREGATED` | STD |
| `RULE_RESULT_HISTORY_VIEWED` | ACC | | `CRITICAL_VETO_APPLIED` | STD |
| `FAILURE_SAMPLE_GENERATED` | SENS | | `SCORE_PUBLISHED` | STD |
| `FAILURE_SAMPLE_VIEWED` | SENS | | `SCORE_CONTRIBUTION_GRAPH_BUILT` | STD |
| `MEASUREMENT_QUALIFICATION_ISSUED` | STD | | `SCORE_REPRODUCTION_VERIFIED` | STD |
| `RULE_SCORE_CALCULATED` | STD | | `SCORE_COMPARISON_VIEWED` | ACC |
| `CRITICALITY_MODEL_CONFIGURED` | STD | | `RISK_RATING_CALCULATED` | STD |
| `RISK_RANKING_VIEWED` | ACC | | | |

#### D09 — Sorun, istisna ve remediation

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `ISSUE_CREATED` | STD | | `EXCEPTION_REQUESTED` | STD |
| `ISSUE_RECURRENCE_RECORDED` | STD | | `EXCEPTION_DECIDED` | SEC |
| `ISSUE_ASSIGNED` | STD | | `EXCEPTION_SUPPRESSED_ALERT` | SYS |
| `ISSUE_ASSIGNEE_OPTIONS_VIEWED` | ACC | | `EXCEPTION_EXPIRED` | SYS |
| `ISSUE_INVESTIGATION_STARTED` | STD | | `EXCEPTION_REVOKED` | SEC |
| `ISSUE_EVIDENCE_VIEWED` | SENS | | `EXCEPTION_LIST_VIEWED` | ACC |
| `ISSUE_COMMENT_ADDED` | STD | | `DIAGNOSIS_HYPOTHESES_GENERATED` | SYS |
| `ISSUE_RESOLVED` | STD | | `DIAGNOSIS_HYPOTHESIS_DECIDED` | STD |
| `ISSUE_PUT_ON_HOLD` | STD | | `RECOMMENDATION_GENERATED` | SYS |
| `ISSUE_VERIFIED` | SEC | | `REMEDIATION_ACTION_CREATED` | STD |
| `ISSUE_CLOSED` | STD | | `REMEDIATION_ACTION_COMPLETED` | STD |
| `ISSUE_REOPENED` | STD | | `REMEDIATION_AUTO_EXECUTED` | SEC |
| `ISSUE_SLA_ASSIGNED` | SYS | | `REMEDIATION_IMPACT_MEASURED` | STD |
| `ISSUE_SLA_BREACHED` | SYS | | `ISSUE_ESCALATED` | SYS |

#### D10 — Lineage, etki ve sözleşme

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `LINEAGE_EVENT_INGESTED` | STD | | `CONTRACT_COMPLIANCE_MEASURED` | STD |
| `LINEAGE_GRAPH_VIEWED` | ACC | | `CONTRACT_COMPLIANCE_VIEWED` | ACC |
| `IMPACT_ANALYSIS_COMPUTED` | SYS | | `DATA_CONTRACT_BREACHED` | STD |
| `IMPACT_SIMULATION_RUN` | STD | | `DATA_CONTRACT_RECOVERED` | STD |
| `DATA_CONTRACT_DRAFTED` | STD | | `QUALITY_DEBT_RECORDED` | STD |
| `DATA_CONTRACT_ACCEPTED` | SEC | | `QUALITY_DEBT_PORTFOLIO_VIEWED` | ACC |
| `DATA_CONTRACT_TERMINATED` | STD | | `QUALITY_DEBT_CLOSED` | STD |

#### D11 — Analitik ve raporlama

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `DASHBOARD_VIEWED` | ACC | | `REPORT_GENERATED` | STD |
| `TREND_QUERIED` | ACC | | `REPORT_CANCELLED` | STD |
| `ISSUE_ANALYTICS_QUERIED` | ACC | | `REPORT_SCHEDULE_CREATED` | STD |
| `SCOPE_COMPARISON_QUERIED` | ACC | | `REPORT_SCHEDULE_TRIGGERED` | SYS |
| `ANALYTICS_EXPORTED` | SENS | | `REPORT_SCHEDULE_STATE_CHANGED` | STD |
| `REPORT_REQUESTED` | STD | | `REPORT_DOWNLOADED` | SENS |
| `REPORT_PREVIEWED` | ACC | | `REPORT_LIST_VIEWED` | ACC |
| `REPORT_FILE_DESTROYED` | STD | | | |

#### D12 — Bildirim ve entegrasyon

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `NOTIFICATION_EVENT_PUBLISHED` | STD | | `NOTIFICATION_DELIVERY_VIEWED` | ACC |
| `NOTIFICATION_PAYLOAD_REJECTED` | SEC | | `INTEGRATION_RECORD_SENT` | STD |
| `NOTIFICATION_SUBSCRIPTION_CHANGED` | STD | | `INTEGRATION_RECORD_UPDATED` | STD |
| `NOTIFICATION_CHANNEL_CONFIGURED` | SEC | | `INTEGRATION_INBOUND_RECONCILED` | STD |
| `NOTIFICATION_DELIVERY_ATTEMPTED` | SYS | | `RATE_LIMIT_EXCEEDED` | SEC |
| `NOTIFICATION_UNDELIVERABLE` | SYS | | | |

#### D13 — Audit, kanıt ve saklama

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `AUDIT_CHAIN_BROKEN` | SEC | | `AUDIT_EXPORT_FAILED` | SEC |
| `AUDIT_QUERY_EXECUTED` | ACC | | `RETENTION_POLICY_DRAFTED` | STD |
| `AUDIT_ACCESS_DENIED` | SEC | | `RETENTION_RECALCULATED` | SYS |
| `AUDIT_OBJECT_HISTORY_VIEWED` | ACC | | `DATA_DISPOSED` | SEC |
| `AUDIT_INTEGRITY_VERIFIED` | SEC | | `DISPOSAL_EVIDENCE_VIEWED` | ACC |
| `AUDIT_OUTBOX_PUBLISH_FAILED` | SEC | | `LEGAL_HOLD_APPLIED` | SEC |
| `AUDIT_OUTBOX_BACKLOG_ALERT` | SYS | | `LEGAL_HOLD_RELEASED` | SEC |
| `AUDIT_EXPORT_COMPLETED` | STD | | `ARCHIVE_RECALL_REQUESTED` | SEC |
| `ARCHIVE_RECALL_DECIDED` | SEC | | `ARCHIVE_RECALL_ACCESSED` | SENS |

#### D14 — Operasyon ve platform sağlığı

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `PLATFORM_HEALTH_VIEWED` | ACC | | `WORKER_DRAIN_REQUESTED` | SYS |
| `COMPONENT_HEALTH_CHANGED` | SYS | | `OPERATIONAL_INCIDENT_OPENED` | SYS |
| `CAPACITY_VIEWED` | ACC | | `OPERATIONAL_INCIDENT_UPDATED` | SYS |
| `JOB_QUEUE_VIEWED` | ACC | | `OPERATIONAL_INCIDENT_CLOSED` | SYS |
| `JOB_MANUALLY_INTERVENED` | SYS | | `MAINTENANCE_WINDOW_SCHEDULED` | SYS |
| `BACKFILL_STARTED` | SYS | | `BACKFILL_COMPLETED` | SYS |

#### D15 — Test verisi ve ground truth

| Olay | Sınıf | | Olay | Sınıf |
|---|---|---|---|---|
| `SYNTHETIC_GENERATION_RUN` | STD | | `EXPECTED_RESULT_COMPUTED` | SYS |
| `SYNTHETIC_DATA_CLEANED` | STD | | `CONTROL_ACCURACY_MEASURED` | STD |
| `SYNTHETIC_PROFILE_DEFINED` | STD | | `RULE_ACCURACY_BELOW_THRESHOLD` | SYS |
| `GROUND_TRUTH_RECORDED` | STD | | `CONTROL_EXPERIMENT_RUN` | SEC |

### 6.4 Bildirim kataloğu

Her bildirim, veri-minimum yükle üretilir: nesne referansı, tip, önem ve sisteme
dönüş bağlantısı. Kayıt değeri veya kanıt örneği taşınmaz.

| Olay | Alıcı rol | Öncelik | Kanal sınıfı | Tetikleyen yaprak |
|---|---|---|---|---|
| Sorun açıldı | Atanan; varlık sahibi | Sorun önceliğine göre | Sistem içi + e-posta | `D09.C01.W01.A01` |
| Sorun atandı | Yeni atanan | Normal | Sistem içi + e-posta | `D09.C02.W01.A01` |
| Sorun çözüldü | Doğrulayıcı havuzu | Normal | Sistem içi | `D09.C02.W03.A01` |
| Sorun doğrulandı | Çözen; sahip | Düşük | Sistem içi | `D09.C02.W04.A01` |
| Sorun yeniden açıldı | Önceki atanan; sahip | Yüksek | Sistem içi + e-posta | `D09.C02.W05.A02` |
| SLA riski | Atanan | Yüksek | Sistem içi + e-posta | `D09.C03.W01.A02` |
| SLA ihlali / eskalasyon | Eskalasyon zinciri rolü | Kritik | E-posta + mesajlaşma | `D09.C03.W02.A01` |
| Onay talebi (kural/politika/kaynak/istisna/sözleşme) | İlgili checker rolü | Normal | Sistem içi + e-posta | `D01.C04.W01.A02`, `D03.C02.W01.A01`, `D06.C02.W04.A01`, `D09.C04.W01.A01` |
| Onay kararı verildi | Maker | Normal | Sistem içi | `D06.C02.W04.A02` vb. |
| Onay süresi doldu | Maker | Normal | Sistem içi | `D06.C02.W04.A04` |
| İstisna süresi yaklaşıyor / doldu | Talep eden; onaylayan; sahip | Yüksek | Sistem içi + e-posta | `D09.C04.W03.A01` |
| Kırıcı şema değişikliği | Dataset sahibi; teknik steward | Yüksek | Sistem içi + e-posta | `D04.C04.W02.A01` |
| Drift doğrulandı | Dataset sahibi | Normal | Sistem içi | `D05.C04.W02.A02` |
| Sözleşme ihlali | Üretici sahip; tüm tüketiciler | Kritik | E-posta + mesajlaşma | `D10.C03.W03.A01` |
| Sözleşme geri kazanıldı | Taraflar | Normal | Sistem içi | `D10.C03.W03.A02` |
| Sahiplik atandı / devredildi | Yeni sahip; eski sahip | Normal | Sistem içi + e-posta | `D01.C02.W01.A01`, `D01.C02.W02.A01` |
| Yönetişim boşluğu | Governance Admin | Normal | Sistem içi | `D01.C02.W03.A02` |
| Kaynak sağlığı bozuldu | Teknik steward; operasyon | Yüksek | Sistem içi + mesajlaşma | `D03.C05.W01.A01` |
| Dead-letter oluştu | Operasyon | Yüksek | Sistem içi + mesajlaşma | `D07.C04.W04.A01` |
| Kuyruk / outbox birikmesi | Operasyon; Platform Admin | Kritik | Mesajlaşma | `D13.C02.W01.A02` |
| Bileşen sağlığı bozuldu | Operasyon; Platform Admin | Kritik | Mesajlaşma | `D14.C01.W01.A02` |
| Operasyonel olay açıldı | Operasyon; ilgili sahipler | Kritik | E-posta + mesajlaşma | `D14.C03.W01.A01` |
| Rapor hazır | Talep eden; zamanlama alıcıları | Düşük | Sistem içi + e-posta | `D11.C03.W02.A01` |
| Erişim gözden geçirme kalemi | Gözden geçiren | Normal | Sistem içi + e-posta | `D02.C05.W01.A01` |
| Rol / kapsam değişikliği | Etkilenen kullanıcı | Normal | Sistem içi | `D02.C02.W03.A01` |
| Kural doğruluğu eşik altında | Kural sahibi | Normal | Sistem içi | `D15.C03.W01.A02` |
| Teslim edilemeyen bildirim | Operasyon | Yüksek | Sistem içi | `D12.C02.W02.A02` |

Zorunlu bildirimler (abonelikten çıkılamaz): SLA ihlali/eskalasyon, sözleşme
ihlali, onay talebi, istisna süre dolumu, erişim gözden geçirme kalemi,
operasyonel olay.

### 6.5 Hedef veri varlıkları

Yapraklarda geçen 119 tablo. Kolon düzeyi tasarım bu belgenin kapsamı dışındadır;
burada her tablonun amacı ve sahibi domain verilir.

> Not: Yaprak `Tablo` satırlarında geçen `retention_until`, bağımsız bir tablo
> değil, saklama süresi uygulanan tüm tablolarda bulunan ortak bir kolondur.

| Domain | Tablolar |
|---|---|
| **D01** | `org_units` · `business_domains` · `data_domains` · `domain_asset_assignments` · `asset_ownerships` · `glossary_terms` · `glossary_term_mappings` · `governance_scan_runs` · `policies` · `policy_rollbacks` · `system_config` · `system_config_history` · `feature_flags` |
| **D02** | `users` · `service_accounts` · `roles` · `permissions` · `role_permissions` · `role_assignments` · `assignment_scopes` · `segregation_rules` · `sessions` · `access_review_campaigns` · `access_review_items` |
| **D03** | `data_sources` · `connection_test_results` · `data_source_activation_requests` · `data_source_connection_revisions` · `source_usage_policies` · `source_health_checks` |
| **D04** | `datasets` · `data_fields` · `discovery_scopes` · `metadata_discovery_results` · `metadata_diffs` · `classification_candidates` · `schema_changes` |
| **D05** | `data_profiles` · `profile_field_metrics` · `profile_distributions` · `profile_outliers` · `profile_baselines` · `profile_comparisons` · `drift_judgments` |
| **D06** | `rule_templates` · `quality_rules` · `rule_versions` · `rule_test_results` · `rule_approval_requests` · `rule_dependencies` · `rule_conflicts` |
| **D07** | `rule_executions` · `execution_attempts` · `execution_partitions` · `schedules` · `schedule_missed_runs` · `persistent_jobs` · `dead_letter_records` · `workers` |
| **D08** | `rule_execution_results` · `failure_samples` · `measurement_qualifications` · `quality_scores` · `score_publications` · `score_contribution_graphs` · `risk_ratings` |
| **D09** | `issues` · `issue_history` · `issue_comments` · `issue_resolutions` · `issue_verifications` · `issue_relationships` · `issue_slas` · `issue_escalations` · `exceptions` · `exception_suppressions` · `diagnosis_hypotheses` · `recommendations` · `remediation_actions` · `remediation_impacts` |
| **D10** | `lineage_events` · `lineage_edges` · `column_lineage_edges` · `impact_analyses` · `impact_simulations` · `data_contracts` · `contract_compliance` · `contract_breaches` · `quality_debts` |
| **D11** | `reports` · `report_schedules` · `report_downloads` · `export_records` |
| **D12** | `notification_events` · `notification_subscriptions` · `notification_channels` · `notification_deliveries` · `integration_records` · `rate_limit_counters` |
| **D13** | `audit_outbox` · `audit_events` · `audit_integrity_checks` · `audit_export_cursors` · `retention_policies` · `disposal_jobs` · `legal_holds` · `archive_recalls` |
| **D14** | `component_health` · `operational_incidents` · `incident_updates` · `maintenance_windows` · `backfill_jobs` |
| **D15** | `synthetic_profiles` · `synthetic_runs` · `ground_truth_defects` · `expected_results` · `control_validations` · `control_experiments` |
| **Ortak** | `approval_requests` (politika, sözleşme ve genel onay akışları için ortak talep tablosu) |

---

## 7. Uçtan uca akış haritası

Sekiz temel akışın hangi yaprak zincirinden geçtiği. Her satır bir adımı ve o
adımı gerçekleştiren yaprağı gösterir.

### A. Yeni kaynak onboarding

```
D03.C01.W01.A01  Kaynak kaydı oluştur
  → D03.C01.W02.A01  Sır referansı bağla
  → D03.C01.W03.A01  Bağlantıyı test et
  → D03.C03.W01.A01  Kullanım politikası tanımla
  → D03.C02.W01.A01  Aktivasyon talep et        (maker)
  → D03.C02.W01.A02  Aktivasyon kararı ver      (checker ≠ maker)
  → D04.C01.W01.A01  Metadata keşfini başlat
  → D04.C01.W02.A01  Keşif farkını hesapla
  → D04.C01.W02.A02  Keşif farkını uygula
  → D04.C02.W01.A01  Dataset kaydını oluştur
  → D04.C03.W01.A01  Alan kaydını oluştur
  → D01.C02.W01.A01  Veri sahibi ata
  → D04.C03.W02.A01  Alanı sınıflandır
  → D04.C02.W02.A01  Dataset kritikliğini belirle
  → D05.C01.W01.A01  İlk profili çalıştır
  → D05.C03.W01.A01  Profili baseline olarak belirle
```

### B. Kural yaşam döngüsü

```
D04.C05.W01.A01  Katalogda ara (dataset seç)
  → D06.C02.W01.A01  Şablondan kural oluştur      (veya .A02 özel sorgu)
  → D06.C03.W01.A01  Kural kapsamını tanımla
  → D06.C03.W02.A01  Eşik ve ağırlığı belirle
  → D06.C04.W01.A01  Bağımlılık grafiğini çıkar
  → D06.C04.W02.A01  Çakışma tespiti
  → D06.C02.W03.A01  Sürümü sınırlı veriyle test et
  → D06.C05.W01.A01  (opsiyonel) Gölge modda çalıştır
  → D06.C02.W02.A02  Sürümü değişmez kıl
  → D06.C02.W04.A01  Onaya gönder                 (maker)
  → D06.C02.W04.A02  Onay kararı ver              (checker ≠ maker)
  → D06.C02.W05.A01  Sürümü aktive et
  → D07.C02.W01.A01  Zamanlama tanımla
  → D07.C02.W02.A01  Vadesi gelen zamanlamayı tetikle
  → D08.C01.W01.A01  Sonucu kaydet
  → D08.C03.W01.A01  Kural skorunu hesapla
```

### C. Kalite problemi

```
D08.C01.W01.A01  Kural sonucunu kaydet
  → D08.C02.W02.A01  Ölçüm yeterliliği hükmü ver
  → D08.C03.W01.A01  Kural skorunu hesapla
  → D09.C01.W02.A01  Tekilleştirme anahtarını üret
  → D09.C01.W01.A01  Kalite ihlalinden sorun üret   (veya .W02.A02 yinelenme)
  → D09.C03.W01.A01  SLA hedeflerini belirle
  → D12.C01.W01.A01  Bildirim olayı yayımla
  → D12.C02.W02.A01  Bildirimi teslim et
  → D09.C02.W01.A01  Sorunu ata
  → D09.C02.W02.A01  İncelemeyi başlat
  → D09.C02.W02.A02  İnceleme kanıtını göster
  → D09.C05.W01.A01  Kök neden hipotezleri üret
  → D09.C05.W01.A02  Hipotezi doğrula
  → D09.C06.W01.A01  Düzeltme aksiyonu oluştur
  → D09.C06.W01.A02  Aksiyonu tamamla
  → D09.C02.W03.A01  Çözümü kaydet
  → D09.C06.W02.A01  Düzeltme etkisini ölç
  → D09.C02.W04.A01  Çözümü bağımsız doğrula        (verifier ≠ çözen)
  → D09.C02.W05.A01  Sorunu kapat
  → D09.C02.W05.A02  Tekrarında yeniden aç
```

### D. Teknik hata

```
D07.C01.W01.A01  Çalıştırmayı başlat
  → D07.C03.W02.A01  İşi sahiplen
  → D07.C04.W01.A02  Hatayı teknik/kalite olarak sınıflandır
  → D07.C04.W02.A01  (zaman aşımıysa) Zaman aşımını uygula
  → D07.C04.W01.A01  Geçici hatada yeniden dene
  → D03.C03.W01.A02  (kota aşımıysa) Çalıştırmayı sınırla
  → D07.C04.W03.A01  (worker çöktüyse) Süresi geçmiş lease'i geri al
  → D07.C04.W04.A01  Sınır aşımında dead-letter'a taşı
  → D09.C01.W01.A02  Teknik hatadan sorun üret
  → D07.C04.W04.A02  Dead-letter kayıtlarını incele
  → D07.C04.W04.A03  Yeniden işle     (veya .A04 kapat → ölçüm boşluğu)
  → D14.C04.W02.A01  Gerekirse toplu telafi çalıştır
```

### E. Şema drifti

```
D04.C01.W01.A01  Metadata keşfini başlat
  → D04.C01.W02.A01  Keşif farkını hesapla
  → D04.C04.W01.A01  Şema değişikliğini sınıflandır
  → D10.C02.W02.A01  Değişikliğin etkisini simüle et
  → D12.C01.W01.A01  Kırıcı değişikliği bildir
  → D04.C04.W02.A01  Kabul et veya blokla
  → D04.C01.W02.A02  Keşif farkını uygula
  → D06.C02.W02.A01  Etkilenen kurallar için yeni sürüm oluştur
  → D09.C04.W01.A01  (kabul edilemiyorsa) İstisna talep et
  → D05.C03.W01.A02  Baseline'ı geçersiz kıl
  → D05.C03.W01.A01  Yeni baseline belirle
```

### F. Skor güvenilirliği

```
D05.C01.W02.A01  Profil yöntemini politikadan çözümle
  → D07.C05.W01.A01  Çalıştırmayı bölümlere ayır
  → D07.C05.W02.A01  Bölüm tamamlanmasını kaydet
  → D08.C01.W01.A01  Sonucu sayaçlarla kaydet
  → D08.C02.W01.A01  Ölçüm kapsamını hesapla
  → D08.C02.W01.A02  Teknik sağlık oranını hesapla
  → D08.C02.W02.A01  Yeterlilik hükmü ver
  → D08.C03.W01.A01  Kural skorunu hesapla
  → D08.C03.W02.A01  Boyut ve dataset düzeyinde toplulaştır
  → D08.C03.W02.A02  Kritik kural vetosunu uygula
  → D08.C03.W02.A03  Domain ve kurum düzeyinde toplulaştır
  → D08.C05.W02.A01  Risk derecesini hesapla
  → D08.C03.W03.A01  Skoru atomik olarak yayımla
  → D08.C04.W01.A01  Katkı grafiğini üret
  → D08.C04.W01.A02  Skoru yeniden üret ve doğrula
```

### G. İstisna ve override

```
D09.C04.W01.A01  İstisna talep et            (maker; bitiş tarihi zorunlu)
  → D09.C04.W02.A01  İstisna kararı ver      (checker ≠ maker)
  → D10.C04.W01.A01  Kalite borcu kaydı oluştur
  → D09.C04.W02.A02  Ham ölçümün değişmediğini garanti et
  → D09.C04.W03.A03  Aktif istisnaları görüntüle
  → D09.C04.W03.A01  Süresi dolan istisnayı otomatik sonlandır
        (veya D09.C04.W03.A02  Erken iptal et)
  → D09.C01.W01.A01  Bastırma kalkınca birikmiş sorunları üret
  → D10.C04.W01.A03  Kalite borcunu kapat
```

### H. Raporlama

```
D11.C03.W01.A02  Rapor önizlemesini göster
  → D11.C03.W01.A01  Rapor talep et
  → D07.C03.W01.A01  Üretim işini kuyruğa al
  → D11.C03.W02.A01  Raporu asenkron üret
  → D11.C04.W01.A01  Hassasiyet politikasını uygula (maskeleme)
  → D12.C01.W01.A01  Rapor hazır bildirimi yayımla
  → D11.C04.W02.A02  Rapor listesini görüntüle
  → D11.C04.W02.A01  Raporu güvenli indir      (hassas erişim kaydı)
  → D13.C03.W01.A02  Saklama süresini uygula
  → D11.C04.W03.A01  Süresi dolan dosyayı imha et (metadata korunur)
```

Zamanlanmış rapor akışı `D11.C03.W03.A01` → `D11.C03.W03.A02` ile başlar ve
yukarıdaki zincirin `D11.C03.W02.A01` adımından devam eder.

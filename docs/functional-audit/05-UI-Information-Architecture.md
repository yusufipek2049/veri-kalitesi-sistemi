---
type: functional-audit
stage: "05 — Hedef UI Bilgi Mimarisi"
scope: ui-information-architecture
inputs:
  - 02-Target-Capability-Hierarchy.md
  - 03-End-to-End-Workflow-Audit.md
  - 04-Functional-Gap-Inventory.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-04
---

# 05 — Hedef UI Bilgi Mimarisi

> Fonksiyonel GAP envanteri (aşama 4), hedef kabiliyet hiyerarşisi (aşama 2) ve
> uçtan uca akış denetimi (aşama 3) girdilerinden türetilmiş **hedef ekran
> haritası**. Her ekran en az bir hedef fonksiyona (L4 yaprak) ve bir kullanıcı
> akışına bağlanır; mevcut durumu aşama 1 frontend incelemesinden devralınır.

---

## 1. Kapsam ve yöntem

### 1.1 İlkeler

| İlke | Açıklama |
|---|---|
| Fonksiyon izlenebilirliği | Her ekran ≥ 1 L4 yaprak kodu taşır; yapraksız ekran önerilmez |
| Akış bütünlüğü | §7'deki 8 akışın her adımı ya mevcut ya da hedef ekranda karşılık bulur |
| Rol görünürlüğü | UI navigasyon öğeleri kullanıcının yetkili scope'una göre filtrelenir; UI rol üretmez |
| Mevcut korunumu | Çalışan ekranlar (Dashboard, Kaynaklar, Kurallar, Çalıştırmalar, Sorunlar, Raporlar, Denetim) korunur; eksik yüzeyler eklenir |
| İkinci faz ayrımı | Kanıtlı olay inceleme ekranı `FR-097–FR-111` ikinci fazdır; bu belgede hedef olarak işaretlenir |

### 1.2 Durum kodları

| Kod | Anlam |
|---|---|
| `MEVCUT` | Ekran ve bağlama çalışır durumda (aşama 1 FRONTEND-INDEX) |
| `KISMİ` | Ekran var; bazı alt yüzeyler/bağlantılar eksik |
| `HEDEF` | Ekran yok; hedef model gereği oluşturulacak |
| `FAZ-2` | İkinci faz; gereksinim tanımlı, runtime değil |

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

## 2. Navigasyon iskeleti

Hedef sidebar yapısı (mevcut + yeni bölümler `★` ile):

```
Genel Bakış (Dashboard)
Kaynaklar
  └─ Kaynak Listesi / Detay
Katalog ★
  ├─ Dataset Listesi / Detay
  ├─ Alan Detay
  ├─ Şema Değişiklikleri ★
  └─ Sözlük ★
Kurallar
  ├─ Kural Listesi / Detay
  ├─ Şablon Kütüphanesi ★
  └─ Gölge Karşılaştırma ★
Çalıştırmalar
  ├─ Liste / Detay
  └─ Zamanlamalar ★
Sorunlar
  ├─ Liste / Detay
  ├─ İstisnalar ★
  ├─ Kalite Borcu ★
  └─ Onay Kuyruğu ★
Skorlar ★
  ├─ Skor Listesi / Detay
  └─ Karşılaştırma ★
Lineage ★
  ├─ Grafik
  └─ Etki Simülasyonu ★
Sözleşmeler ★
  ├─ Liste / Detay
  └─ Uyum Pano ★
Raporlar
  ├─ Liste / Detay
  └─ Zamanlamalar
Bildirimler ★
  ├─ Gelen Kutusu
  ├─ Kanallar ★
  └─ Teslimat ★
Denetim
  ├─ Olaylar
  └─ Saklama & Muhafaza ★
Operasyon ★
  ├─ Sistem Sağlığı
  ├─ Kuyruk & Dead-letter
  ├─ Olaylar
  ├─ Bakım
  └─ Telafi ★
Sentetik Veri ★
  ├─ Run Listesi
  └─ Doğruluk Raporu
Yönetim ★
  ├─ Kullanıcılar & Roller
  ├─ Organizasyon & Domain
  ├─ Sahiplik
  ├─ Politikalar
  └─ Konfigürasyon
```

---

## 3. Ekran kartları

Her kart: ekran adı, bağlı fonksiyonlar, bağlı akışlar, mevcut durum, alt
yüzeyler ve GAP referansı taşır.

### 3.1 Genel Bakış (Dashboard)

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D11.C01.W01.A01` yönetici görünümü, `D11.C01.W02.A01` sahip/steward görünümü, `D11.C01.W03.A01` mühendis görünümü, `D11.C02.W01.A01` trend analizi, `D11.C02.W02.A01` dönem karşılaştırma, `D08.C04.W01.A01` katkı grafiği |
| Bağlı akışlar | C (kalite problemi — kritik alarm), F (skor güvenilirliği — KPI) |
| Mevcut durum | `KISMİ` — Dashboard ekran sözleşmesi tanımlı; seed veri üzerinde çalışıyor; gerçek skor/skor yayımı bağlantısı eksik (GAP-008) |
| Alt yüzeyler | KPI kartları (skor, yeterlilik, kullanım kararı, kapsam, güven, kritik kural, risk), trend grafiği, alarm akışı, domain skor bar, boyut matrisi, son ihlaller tablosu |
| GAP | GAP-008 (skor kalıcılığı), GAP-001 (composition root) |

### 3.2 Kaynak Listesi / Detay

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D03.C01.W01.A01` kaynak kaydı oluştur, `D03.C01.W02.A01` sır referansı bağla, `D03.C01.W03.A01` bağlantı testi, `D03.C02.W01.A01` aktivasyon talep, `D03.C02.W01.A02` aktivasyon kararı, `D03.C03.W01.A01` kullanım politikası, `D03.C04.W01.A01` bağlantı revizyonu, `D03.C05.W01.A01` sağlık kontrolü |
| Bağlı akışlar | A (yeni kaynak onboarding) |
| Mevcut durum | `MEVCUT` — Oluşturma, test, aktivasyon/pasifleştirme çalışıyor (FRONEND-INDEX) |
| Alt yüzeyler | Liste, detay, bağlantı testi, aktivasyon onay akışı, kullanım politikası, bağlantı revizyonu, metadata sekmesi (→ Katalog) |
| GAP | GAP-004 (metadata sekmesi eksik), GAP-001 (PG composition) |

### 3.3 Katalog — Dataset Listesi / Detay ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D04.C02.W01.A01` dataset kaydı oluştur, `D04.C02.W02.A01` dataset kritikliği belirle, `D04.C03.W01.A01` alan kaydı oluştur, `D04.C03.W02.A01` alanı sınıflandır, `D04.C05.W01.A01` katalog arama, `D04.C05.W02.A01` varlık detay görünümü |
| Bağlı akışlar | A (onboarding — dataset/alan adımları) |
| Mevcut durum | `HEDEF` — Katalog sayfası yok (GAP-004) |
| Alt yüzeyler | Dataset arama/liste, dataset detay (alanlar tablosu, sınıflandırma, kritiklik), profil sekmesi (→ 3.5), lineage sekmesi (→ 3.14) |
| GAP | GAP-004 |

### 3.4 Katalog — Alan Detay ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D04.C03.W01.A01` alan kaydı, `D04.C03.W02.A01` sınıflandırma |
| Bağlı akışlar | A |
| Mevcut durum | `HEDEF` |
| Alt yüzeyler | Alan özellikleri, sınıflandırma durumu, hassasiyet etiketi, profil metrikleri, bağlı kurallar |
| GAP | GAP-004 |

### 3.5 Katalog — Şema Değişiklikleri ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D04.C04.W01.A01` şema farkı tespiti, `D04.C04.W02.A01` kabul/blokaj kararı |
| Bağlı akışlar | E (şema drifti) |
| Mevcut durum | `HEDEF` — Şema değişikliği ekranı yok (GAP-019) |
| Alt yüzeyler | Değişiklik listesi (eklenen/kaldırılan/değişen kolonlar), sınıflandırma etiketi (ADDITIVE/BREAKING/NEUTRAL), karar formu (kabul/blokla + gerekçe), etkilenen kural listesi |
| GAP | GAP-019 |

### 3.6 Katalog — İş Sözlüğü ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D01.C03.W01.A01` terim yaşam döngüsü, `D01.C03.W02.A01` terim-varlık eşlemesi |
| Bağlı akışlar | A (dolaylı — sözlük zenginleştirme), J |
| Mevcut durum | `HEDEF` (GAP-026) |
| Alt yüzeyler | Terim listesi/arama, terim detay/eşleme |
| GAP | GAP-026 |

### 3.7 Kural Listesi / Detay

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D06.C02.W01.A01` şablondan kural oluştur, `D06.C02.W01.A02` özel sorgu, `D06.C02.W02.A02` sürümü değişmez kıl, `D06.C02.W03.A01` test, `D06.C02.W04.A01` onaya gönder, `D06.C02.W04.A02` onay kararı, `D06.C02.W05.A01` aktive et, `D06.C03.W01.A01` kapsam tanımla, `D06.C03.W02.A01` eşik/ağırlık |
| Bağlı akışlar | B (kural yaşam döngüsü) |
| Mevcut durum | `MEVCUT` — Taslak, düzenleme, test, onay akışları çalışıyor |
| Alt yüzeyler | Liste, detay, sürüm geçmişi, test sonuçları, onay durumu, kapsam incelemesi |
| GAP | GAP-020 (şablon kütüphanesi bağlantısı eksik), GAP-021 (gölge sekmesi eksik) |

### 3.8 Şablon Kütüphanesi ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D06.C01.W02.A01` şablon yaşam döngüsü, `D06.C01.W02.A02` şablondan kural üretimi |
| Bağlı akışlar | B (şablondan kural oluşturma adımı) |
| Mevcut durum | `HEDEF` (GAP-020) |
| Alt yüzeyler | Şablon listesi (tip, boyut, durum filtreli), şablon detay/önizleme, şablondan kural oluşturma sihirbazı |
| GAP | GAP-020 |

### 3.9 Gölge Karşılaştırma ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D06.C05.W01.A01` gölge modda çalıştır, `D06.C05.W01.A02` gölge-resmî karşılaştırma |
| Bağlı akışlar | B (opsiyonel gölge adımı) |
| Mevcut durum | `HEDEF` (GAP-021) |
| Alt yüzeyler | Gölge başlatma formu, gölge vs resmî sonuç karşılaştırma tablosu, yanlış alarm tahmini |
| GAP | GAP-021 |

### 3.10 Çalıştırma Listesi / Detay

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D07.C01.W01.A01` manuel çalıştırma (UI), `D07.C01.W03.A01` iptal (UI), `D07.C03.W02.A01` iş sahiplenme (dolaylı), `D08.C01.W01.A01` sonuç kaydı |
| Bağlı akışlar | B (çalıştırma adımı), D (teknik hata) |
| Mevcut durum | `KISMİ` — Salt okunur liste mevcut; başlat/iptal UI'dan yapılamıyor (GAP-017) |
| Alt yüzeyler | Liste (durum, mod, zaman), detay (sonuç, kanıt, hata), başlat formu, iptal butonu |
| GAP | GAP-017 |

### 3.11 Zamanlamalar ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D07.C02.W01.A01` zamanlama tanımla, `D07.C02.W01.A02` duraklat/sürdür, `D07.C02.W01.A03` sil, `D07.C02.W02.A01` vadesi geleni tetikle |
| Bağlı akışlar | B (zamanlama adımı) |
| Mevcut durum | `HEDEF` — Zamanlama ekranı yok; backend endpoint'leri bağlı değil (GAP-003, GAP-015) |
| Alt yüzeyler | Zamanlama listesi (kural, cron, durum), yeni/düzenle formu, duraklat/sürdür/sil, son tetikleme görünümü |
| GAP | GAP-003, GAP-015 |

### 3.12 Sorun Listesi / Detay

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D09.C01.W03.A01` manuel sorun aç, `D09.C02.W01.A01` ata, `D09.C02.W02.A01` incele, `D09.C02.W02.A02` kanıt göster, `D09.C02.W03.A01` çözüm kaydet, `D09.C02.W04.A01` doğrula, `D09.C02.W05.A01` kapat, `D09.C02.W05.A02` yeniden aç, `D09.C03.W01.A02` SLA durumu |
| Bağlı akışlar | C (kalite problemi) |
| Mevcut durum | `KISMİ` — İnceleme/atama/çözüm/doğrulama/kapatma çalışıyor; manuel açma, SLA görünümü, bekletme eksik (GAP-006, GAP-014) |
| Alt yüzeyler | Liste (SLA durumu filtresi), detay (sekme: özet, kanıt, zaman çizelgesi), yeni sorun formu, bekletme dialog'u |
| GAP | GAP-006 (manuel açma), GAP-014 (SLA) |

### 3.13 İstisnalar ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D09.C04.W01.A01` istisna talep et, `D09.C04.W02.A01` istisna kararı, `D09.C04.W03.A01` otomatik sonlandır, `D09.C04.W03.A02` erken iptal, `D09.C04.W03.A03` aktif istisnaları görüntüle |
| Bağlı akışlar | G (istisna ve override) |
| Mevcut durum | `HEDEF` (GAP-009) |
| Alt yüzeyler | İstisna listesi (durum, kapsam, kalan süre), yeni talep formu (bitiş tarihi zorunlu), onay kuyruğu (maker-checker), aktif istisna görünümü |
| GAP | GAP-009 |

### 3.14 Kalite Borcu ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D10.C04.W01.A01` kalite borcu kaydı oluştur, `D10.C04.W01.A03` kalite borcu portföyü, `D10.C04.W01.A03` kapat |
| Bağlı akışlar | G (istisna → borç adımı) |
| Mevcut durum | `HEDEF` (GAP-009 ikincil hedef) |
| Alt yüzeyler | Borç listesi (kaynak, tutar, durum), detay (ilişkili istisna, kanıt), kapatma formu |
| GAP | GAP-009 |

### 3.15 Onay Kuyruğu ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | Ortak `approval_requests` tablosu üzerinden: `D03.C02.W01.A02` kaynak aktivasyon kararı, `D06.C02.W04.A02` kural onay kararı, `D01.C04.W01.A02` politika onay kararı, `D09.C04.W02.A01` istisna kararı, `D10.C03.W01.A02` sözleşme onayı |
| Bağlı akışlar | B, G, A (onay adımları) |
| Mevcut durum | `KISMİ` — Kural onayı mevcut; politika/istisna/sözleşme onayı eksik |
| Alt yüzeyler | Birleşik onay kuyruğu (tip filtresi), onay/red formu, süre dolumu uyarısı |
| GAP | GAP-009, GAP-010, GAP-026 |

### 3.16 Skor Listesi / Detay ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D08.C03.W03.A01` atomik yayım, `D08.C04.W01.A01` katkı grafiği, `D08.C04.W01.A02` yeniden üretim doğrulama, `D08.C05.W02.A01` risk derecelendirme |
| Bağlı akışlar | F (skor güvenilirliği) |
| Mevcut durum | `HEDEF` — Skor sayfası yok; yalnız dashboard panellerinde seed veri (GAP-008) |
| Alt yüzeyler | Skor listesi (kapsam, dönem, durum), detay (kural skoru, katkı grafiği, yeterlilik, veto), yeniden üretim doğrulama |
| GAP | GAP-008 |

### 3.17 Skor Karşılaştırma ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D08.C04.W02.A01` dönem karşılaştırma |
| Bağlı akışlar | F |
| Mevcut durum | `HEDEF` (GAP-008) |
| Alt yüzeyler | İki dönem yan yana skor, fark analizi, sürüm/politika değişim etiketleri |
| GAP | GAP-008 |

### 3.18 Lineage — Grafik ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D10.C01.W01.A01` lineage olayı al, `D10.C01.W02.A01` yukarı/aşağı akış sorgulama |
| Bağlı akışlar | E (şema drifti — dolaylı), C (kök neden — dolaylı) |
| Mevcut durum | `HEDEF` — Graf sorgulama yüzeyi yok; yalnız snapshot görüntüleme var (GAP-012) |
| Alt yüzeyler | İnteraktif graf (yön, derinlik), düğüm detay paneli, varlık arama |
| GAP | GAP-012 |

### 3.19 Etki Simülasyonu ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D10.C02.W01.A01` aşağı akış etki, `D10.C02.W02.A01` değişiklik etki simülasyonu |
| Bağlı akışlar | E (şema drifti — etki simülasyonu adımı) |
| Mevcut durum | `HEDEF` (GAP-013) |
| Alt yüzeyler | Simülasyon başlatma (değişiklik parametreleri), etki raporu (aşağı akış düğümleri, kırıcı işaretler), uyarı paneli |
| GAP | GAP-013 |

### 3.20 Kanıtlı Olay İnceleme (FAZ-2)

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D09.C05.W01.A01` kök neden hipotezi, `D09.C05.W01.A02` hipotez doğrula, `D09.C05.W02.A01` öneri üret, `D09.C06.W01.A01` düzeltme aksiyonu, `D09.C02.W02.A02` kanıt göster |
| Bağlı akışlar | C (kalite problemi — inceleme/teşhis/düzeltme adımları) |
| Mevcut durum | `FAZ-2` — Ekran sözleşmesi tanımlı (04-Sorun-ve-Bildirim); runtime değil |
| Alt yüzeyler | 12 sekme (özet, skor, metrik, hatalı kayıt, hesaplama, lineage, kök neden, öneriler, çalıştırmalar, değişiklikler, zaman çizelgesi, kanıt) |
| GAP | GAP-013, GAP-006 |

### 3.21 Veri Sözleşmeleri — Liste / Detay ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D10.C03.W01.A01` sözleşme taslağı, `D10.C03.W01.A02` karşılıklı onay, `D10.C03.W01.A03` sonlandırma |
| Bağlı akışlar | K (veri sözleşmesi yaşam döngüsü) |
| Mevcut durum | `HEDEF` (GAP-010) |
| Alt yüzeyler | Liste, detay (taahhütler, taraflar, durum), taslak oluşturma sihirbazı |
| GAP | GAP-010 |

### 3.22 Sözleşme Uyum Pano ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D10.C03.W02.A01` uyum ölçümü, `D10.C03.W02.A02` uyum panosu, `D10.C03.W03.A01` ihlal ilanı |
| Bağlı akışlar | K (sözleşme uyum) |
| Mevcut durum | `HEDEF` (GAP-010) |
| Alt yüzeyler | Uyum oranı göstergesi, ihlal listesi, geri kazanım durumu |
| GAP | GAP-010 |

### 3.23 Rapor Listesi / Detay

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D11.C03.W01.A01` rapor talep, `D11.C03.W01.A02` önizleme, `D11.C03.W02.A01` asenkron üret, `D11.C03.W02.A02` iptal, `D11.C04.W02.A01` güvenli indir, `D11.C04.W02.A02` liste |
| Bağlı akışlar | H (raporlama) |
| Mevcut durum | `KISMİ` — Rapor talebi ve indirme çalışıyor; gerçek içerik ve asenkron üretim eksik (GAP-016) |
| Alt yüzeyler | Liste (durum filtresi), detay, talep formu, indirme, iptal |
| GAP | GAP-016 |

### 3.24 Rapor Zamanlamaları

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D11.C03.W03.A01` rapor zamanlaması tanımla, `D11.C03.W03.A02` vadesi geleni tetikle |
| Bağlı akışlar | H (zamanlanmış rapor) |
| Mevcut durum | `KISMİ` — Backend hazır; `ReportsRoute` bağlamıyor, sentetik veri gösteriyor (GAP-015) |
| Alt yüzeyler | Zamanlama listesi, oluşturma/silme |
| GAP | GAP-015 |

### 3.25 Bildirim — Gelen Kutusu ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D12.C01.W02.A01` abonelik, `D12.C01.W02.A02` görüntüleme |
| Bağlı akışlar | C, D, G, M (bildirim adımları — dolaylı) |
| Mevcut durum | `HEDEF` (GAP-007) |
| Alt yüzeyler | Bildirim listesi (önem, tip, okundu/okunmadı), okundu işaretleme, tercih yönetimi |
| GAP | GAP-007 |

### 3.26 Bildirim — Kanallar ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D12.C02.W01.A01` kanal yapılandırma |
| Bağlı akışlar | M (bildirim altyapısı) |
| Mevcut durum | `HEDEF` (GAP-007) |
| Alt yüzeyler | Kanal listesi (e-posta, mesajlaşma, bilet), yapılandırma formu (sır referansı) |
| GAP | GAP-007 |

### 3.27 Bildirim — Teslimat İzleme ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D12.C02.W03.A01` teslimat izleme, `D12.C02.W02.A01` teslimat/yeniden deneme |
| Bağlı akışlar | M (teslimat izleme) |
| Mevcut durum | `HEDEF` (GAP-007) |
| Alt yüzeyler | Teslimat listesi (durum, kanal, zaman), yeniden yönlendirme |
| GAP | GAP-007 |

### 3.28 Denetim — Olaylar

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D13.C01.W02.A01` audit sorgulama, `D13.C01.W03.A01` bütünlük doğrulama, `D13.C02.W01.A01` outbox yayımlama |
| Bağlı akışlar | Tüm akışlar (audit izi) |
| Mevcut durum | `MEVCUT` — Salt okunur audit sayfası var; gerçek olaylar yerine sentetik (GAP-001) |
| Alt yüzeyler | Olay listesi (filtre: tip, aktör, tarih), bütünlük göstergesi, dışa aktarım |
| GAP | GAP-001 (audit outbox → PG) |

### 3.29 Denetim — Saklama & Muhafaza ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D13.C03.W01.A01` saklama politikası tanımla, `D13.C03.W02.A01` imha işi, `D13.C04.W01.A01` muhafaza uygulama, `D13.C04.W01.A02` muhafaza kaldırma, `D13.C04.W02.A01` geri çağırma |
| Bağlı akışlar | H (rapor dosya imhası — dolaylı) |
| Mevcut durum | `HEDEF` (GAP-011) |
| Alt yüzeyler | Politika listesi/düzenleme, imha kanıtı görünümü, muhafaza listesi, geri çağırma talebi |
| GAP | GAP-011 |

### 3.30 Operasyon — Sistem Sağlığı ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D14.C01.W01.A01` bileşen sağlığı, `D14.C01.W01.A02` sağlık uyarısı, `D14.C01.W02.A01` kapasite |
| Bağlı akışlar | D (teknik hata — dolaylı) |
| Mevcut durum | `HEDEF` (GAP-024) |
| Alt yüzeyler | Bileşen durum kartları (depo, kuyruk, worker, zamanlayıcı, outbox), kapasite grafiği |
| GAP | GAP-024 |

### 3.31 Operasyon — Kuyruk & Dead-letter ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D07.C04.W04.A02` dead-letter inceleme, `D07.C04.W04.A03` yeniden işleme, `D07.C04.W04.A04` kapatma, `D14.C02.W01.A01` kuyruk görüntüleme, `D14.C02.W01.A02` kuyruk müdahale, `D07.C03.W01.A02` öncelik yükseltme |
| Bağlı akışlar | D (teknik hata — dead-letter adımı) |
| Mevcut durum | `HEDEF` (GAP-018) |
| Alt yüzeyler | Kuyruk listesi (durum, tip, öncelik, bekleme), dead-letter listesi, yeniden işleme/kapatma formu, öncelik değiştirme |
| GAP | GAP-018 |

### 3.32 Operasyon — Olaylar ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D14.C03.W01.A01` operasyonel olay yaşam döngüsü |
| Bağlı akışlar | D |
| Mevcut durum | `HEDEF` (GAP-024) |
| Alt yüzeyler | Olay listesi (açık/kapalı), detay (güncellemeler, kök neden), kapatma formu |
| GAP | GAP-024 |

### 3.33 Operasyon — Bakım ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D14.C04.W01.A01` bakım penceresi yönetimi |
| Bağlı akışlar | D |
| Mevcut durum | `HEDEF` (GAP-024) |
| Alt yüzeyler | Bakım takvimi, pencere oluşturma/düzenleme |
| GAP | GAP-024 |

### 3.34 Operasyon — Telafi ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D14.C04.W02.A01` toplu telafi |
| Bağlı akışlar | D (telafi adımı) |
| Mevcut durum | `HEDEF` (GAP-024) |
| Alt yüzeyler | Telafi işi listesi, başlatma formu (kapsam, kota), ilerleme görünümü |
| GAP | GAP-024 |

### 3.35 Sentetik Veri — Run Listesi ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D15.C01.W01.A01` sentetik üretim çalıştırması, `D15.C01.W02.A01` üretim profili |
| Bağlı akışlar | L (sentetik doğrulama) |
| Mevcut durum | `HEDEF` — CLI script var; uygulama yüzeyi yok (GAP-025) |
| Alt yüzeyler | Run listesi (durum, zaman), detay (üretilen kayıt, profil) |
| GAP | GAP-025 |

### 3.36 Sentetik Veri — Doğruluk Raporu ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D15.C02.W01.A01` ground truth, `D15.C02.W02.A01` beklenen sonuç, `D15.C03.W01.A01` tespit doğruluğu, `D15.C03.W02.A01` yeterlilik deneyi |
| Bağlı akışlar | L (sentetik doğrulama) |
| Mevcut durum | `HEDEF` (GAP-025) |
| Alt yüzeyler | Ground truth kayıt formu, doğruluk raporu (duyarlılık/yanlış alarm), yeterlilik deneyi kanıtı |
| GAP | GAP-025 |

### 3.37 Yönetim — Kullanıcılar & Roller ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D02.C01.W01.A01` kullanıcı yaşam döngüsü, `D02.C01.W02.A01` servis hesabı, `D02.C02.W01.A01` rol tanımı, `D02.C02.W02.A01` izin kataloğu, `D02.C02.W03.A01` rol atama, `D02.C02.W02.A02` görev ayrılığı, `D02.C05.W01.A01` erişim gözden geçirme |
| Bağlı akışlar | I (kimlik ve yetki) |
| Mevcut durum | `HEDEF` — Tablolar yok; serbest dize roller (GAP-022) |
| Alt yüzeyler | Kullanıcı listesi, rol atama formu, izin matrisi, SoD kuralları, erişim gözden geçirme kampanyası |
| GAP | GAP-022 |

### 3.38 Yönetim — Organizasyon & Domain ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D01.C01.W01.A01` organizasyon birimi, `D01.C01.W02.A01` iş domaini, `D01.C01.W03.A01` veri domaini |
| Bağlı akışlar | A, J (domain yapısı) |
| Mevcut durum | `HEDEF` (GAP-026) |
| Alt yüzeyler | Organizasyon ağacı, domain listesi, atama |
| GAP | GAP-026 |

### 3.39 Yönetim — Sahiplik ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D01.C02.W01.A01` varlık sahipliği ata, `D01.C02.W03.A01` sahipsiz varlık takibi |
| Bağlı akışlar | A (sahiplik adımı) |
| Mevcut durum | `HEDEF` (GAP-026, GAP-004) |
| Alt yüzeyler | Sahiplik atama formu, sahipsiz varlık listesi |
| GAP | GAP-026, GAP-004 |

### 3.40 Yönetim — Politikalar ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D01.C04.W01.A01` politika yaşam döngüsü, `D01.C04.W02.A01` politika sürümleme/yürürlük |
| Bağlı akışlar | J (politika yaşam döngüsü) |
| Mevcut durum | `HEDEF` — Politika sürümleri kodda sabit; yönetim yüzeyi yok (GAP-026) |
| Alt yüzeyler | Politika listesi (tip, durum, sürüm), detay (içerik, onay), taslak/onay/yürürlük akışı |
| GAP | GAP-026 |

### 3.41 Yönetim — Konfigürasyon ★

| Alan | Değer |
|---|---|
| Bağlı fonksiyonlar | `D01.C05.W01.A01` konfigürasyon yönetimi, `D01.C05.W02.A01` özellik anahtarı |
| Bağlı akışlar | J (sistem konfigürasyonu) |
| Mevcut durum | `HEDEF` (GAP-026) |
| Alt yüzeyler | Konfigürasyon listesi, düzenleme (maker-checker), özellik anahtarı paneli |
| GAP | GAP-026 |

---

## 4. Ekran–fonksiyon izlenebilirlik matrisi

Her satır bir ekranı; her sütun bir akışı gösterir. Hücre, ekranın akıştaki
adımı gerçekleştirdiğini belirtir.

| Ekran | A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|---|
| 3.1 Dashboard | | | ● | | | ● | | |
| 3.2 Kaynaklar | ● | | | | | | | |
| 3.3 Katalog | ● | | | | | | | |
| 3.5 Şema Değişiklikleri | | | | | ● | | | |
| 3.7 Kurallar | | ● | | | | | | |
| 3.8 Şablonlar | | ● | | | | | | |
| 3.9 Gölge | | ● | | | | | | |
| 3.10 Çalıştırmalar | | ● | | ● | | | | |
| 3.11 Zamanlamalar | | ● | | | | | | |
| 3.12 Sorunlar | | | ● | | | | ● | |
| 3.13 İstisnalar | | | | | | | ● | |
| 3.14 Kalite Borcu | | | | | | | ● | |
| 3.16 Skorlar | | | | | | ● | | |
| 3.18 Lineage | | | | | ● | | | |
| 3.19 Etki Simülasyonu | | | | | ● | | | |
| 3.20 İnceleme (FAZ-2) | | | ● | | | | | |
| 3.21 Sözleşmeler | | | | | | | | |
| 3.23 Raporlar | | | | | | | | ● |
| 3.24 Rapor Zamanlamaları | | | | | | | | ● |
| 3.25 Bildirimler | | | ● | ● | | | ● | ● |
| 3.28 Denetim | ● | ● | ● | ● | ● | ● | ● | ● |
| 3.29 Saklama | | | | | | | | ● |
| 3.30 Sistem Sağlığı | | | | ● | | | | |
| 3.31 Kuyruk/DL | | | | ● | | | | |
| 3.39 Sahiplik | ● | | | | | | | |
| 3.40 Politikalar | | | | | | | | |

---

## 5. Özet sayısal tablo

| Durum | Ekran sayısı |
|---|---|
| `MEVCUT` | 5 (Dashboard, Kaynaklar, Kurallar, Denetim, Raporlar — kısmi) |
| `KISMİ` | 6 (Dashboard, Çalıştırmalar, Sorunlar, Raporlar, Rapor Zamanlamaları, Onay Kuyruğu) |
| `HEDEF` | 27 (yeni oluşturulacak) |
| `FAZ-2` | 1 (Kanıtlı Olay İnceleme) |
| **Toplam** | **39** |

## 6. Kanıt sınırları

- Mevcut durum değerlendirmeleri FRONTEND-INDEX, Dashboard Ekran Sözleşmesi ve
  Kanıtlı Olay İnceleme sözleşmesinden devralınmıştır; bu oturumda frontend
  kodu çalıştırılmamıştır.
- Hedef ekran listesi, GAP envanterindeki "Eksik UI" alanlarının her birinin en
  az bir ekran kartına映射landığı doğrulanarak oluşturulmuştur.
- Piksel tasarımı, component hiyerarşisi ve route URL yapısı bu belgenin
  kapsamı dışındadır; ekran sözleşmeleri ayrı belgelerle tanımlanacaktır.

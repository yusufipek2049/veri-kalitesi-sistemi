---
type: frontend-screen-contract
status: design-baseline
project: Veri Kalitesi İzleme ve Skorlama Sistemi
screen: dashboard
last_updated: 2026-07-20
tags:
  - frontend
  - dashboard
  - uc-010
---

# Dashboard Ekran Sözleşmesi

## İzlenebilirlik ve Sınır

Bu sözleşme `FR-054`–`FR-058`, `UC-010`, `NFR-USA-001`–`NFR-USA-006`,
`NFR-SEC-001`, `AC-010` ve `AC-011` ile birlikte uygulanır. Görsel dil için
[[04-Frontend/Gorsel-Tasarim-Sistemi|Görsel Tasarım Sistemi]] esas alınır.

Referans: [Kurumsal dashboard referansı](../references/reference-dashboard.png)

Referans görsel bilgi hiyerarşisini ve görsel yoğunluğu tarif eder; gerçek veri,
nihai API, banka onayı veya pixel-perfect implementation kanıtı değildir. Mevcut
backend yalnız güvenilir scope ile skor ağacı ve sabit son 30 günlük trend domain
sorgusunu sağlar. HTTP/API ve operasyon listeleri uygulanmadan UI bunları tahmin
etmez veya fake production sözleşmesi gibi sunmaz.

## Kullanıcı Amacı

Yetkili kullanıcı ilk bakışta kurum veya kendi kapsamındaki kalite durumunu anlamalı,
kritik kalite ihlali ile teknik çalıştırma hatasını ayırmalı ve kaynaktan veri kümesi,
kural, execution veya issue detayına güvenli drill-down yapabilmelidir.

## Bilgi Hiyerarşisi

1. Uygulama kabuğu: koyu navigasyon, üst bar, kullanıcı/kapsam bilgisi.
2. Sayfa başlığı: “Genel Bakış”, güncellik ve aktif filtre özeti.
3. KPI satırı: genel skor, kritik ihlal, aktif kural, teknik hata.
4. Birincil analiz: kalite trendi ve kritik alarm akışı.
5. Karşılaştırma: veri alanı skorları ve kalite boyutu matrisi.
6. Operasyonel detay: son ihlaller tablosu ve güvenli drill-down.

Her bölüm ayrı floating karta dönüştürülmez. Grafikler gerçek veri birimi olduğu için
sınırlı yüzey kullanabilir; sayfa başlığı, filtreler ve bölüm başlıkları unframed
yerleşimde kalır.

## Bölüm Sözleşmeleri

| Bölüm | Görsel/component örüntüsü | Veri alanları | Etkileşim |
| --- | --- | --- | --- |
| Genel Kalite Skoru | KPI | `score_value`, `score_status`, `level`, `calculated_at` | Skor ağacı/drill-down |
| Kritik İhlaller | KPI | Açık kritik issue sayısı, dönem farkı | Kritik filtreli tablo |
| Aktif Kurallar | KPI | Aktif kural sayısı, güncellik | Kural listesi |
| Teknik Hatalar | KPI, mor semantik | Teknik hata sayısı, son olay zamanı | Execution hata filtresi |
| Veri Kalitesi Trendi | Line chart + tablo görünümü | `period_start`, `period_end`, observations | Tarih/kapsam filtreleme |
| Kritik Alarm Akışı | Sıkı alarm listesi | Durum kodu, kapsam etiketi, zaman, güvenli referans | Yetkili detay |
| Veri Alanı Bazlı Skorlar | Horizontal bar | Scope etiketi, skor, durum, güncellik | Kaynak/dataset drill-down |
| Kalite Boyutu Matrisi | Heatmap + erişilebilir tablo | Alan × kalite boyutu skor/durum | Hücre detayı |
| Son İhlaller | Data table | Kapsam, kural kodu, durum, skor, zaman, issue ref | Sayfalama/sıralama/detay |

Issue, aktif kural ve operasyon listesi alanları backend sözleşmesi oluşana kadar mock
story'de sentetik veriyle gösterilebilir; production çağrısı veya alan adı olarak
kesinleştirilemez. Mock veride gerçek kurum, kullanıcı, müşteri veya kaynak adı
kullanılmaz.

## Ortak View-Model İlkesi

- Grafik ve tablo aynı normalize edilmiş view-model'den beslenir.
- `score_value`, `score_status`, `level` ve `calculated_at` ortak formatter kullanır.
- Ortak status mapper teknik hata, kalite ihlali, uyarı, başarı, bilgi ve veri yok
  anlamlarını ikon + etiket + token'a dönüştürür.
- `NO_DATA`, teknik hata ve hesaplanmamış skor `0` değerine çevrilmez; değer `—`,
  yazılı durum ve açıklamayla sunulur.
- Grafik toplamı ile tablo toplamı aynı filtre ve snapshot altında eşit olmalıdır.
- Eksik trend dönemi çizgiyi sıfıra indirmez; boşluk ve “Hesaplanmadı” durumuyla
  gösterilir.

## Filtreler

| Filtre | Başlangıç davranışı |
| --- | --- |
| Tarih | Mevcut domain sözleşmesinde son 30 UTC gün; serbest aralık API sonrası |
| Veri kaynağı | Yalnız backend tarafından yetkilendirilmiş seçenekler |
| Veri alanı/birim | Yetkili scope içinde; alan sözleşmesi kesinleşince |
| Sahip | Yetkili ve veri-minimum dizin sonucu |
| Kalite boyutu | Tanımlı yedi kalite boyutu |
| Seviye/durum | Kalite seviyesi ve teknik durum ayrı gruplar |
| Kural | Yetkili scope'a bağlı arama/seçim |

Filtreler temizlenebilir, aktif filtre özeti görünür ve URL/oturum saklama davranışı
API tasarımında açıkça kararlaştırılmalıdır. Kullanıcı girdisi yetki kapsamı üretmez.

## Grafik Sözleşmeleri

### Veri Kalitesi Trendi

- Line chart; günlük gözlemler ve belirgin veri noktaları.
- Kritik eşik kesikli çizgi ve yazılı legend ile gösterilir.
- Tooltip dönem, skor, seviye ve durum içerir.
- Teknik hata ayrı mor marker, veri yok gri boşluk olarak görünür.
- Erişilebilir tablo görünümüne segment/tab üzerinden erişilir.

### Veri Alanı Bazlı Skorlar

- Horizontal bar; skor sırası veya alfabetik sıralama açıkça belirtilir.
- Marka sarısı yalnız seçili/odaklı seriyi vurgular, tüm barları boyamaz.
- Skoru olmayan alan bar üretmez; `—` ve durum etiketi gösterir.

### Kalite Boyutu Matrisi

- Satır veri alanı, kolon kalite boyutudur.
- Renk yanında hücre etiketi veya erişilebilir değer bulunur.
- Teknik hata kırmızı kalite hücresi olarak gösterilemez.
- Ekran okuyucu için aynı matrisi temsil eden tablo sağlanır.

## Kritik Alarm Akışı

- Kritik veri kalitesi ihlalleri kırmızı; teknik sistem olayları mor badge taşır.
- Alarm satırı ikon, durum, kısa başlık, kapsam, zaman ve izinli eylem içerir.
- Ham hatalı kayıt, source SQL, stack trace, secret veya kişisel veri gösterilmez.
- İlk görünüm sınırlı sayıda kayıt sunar; “Tümünü Gör” ayrı yetki filtreli listeye gider.
- Aynı olayın tekrarları tekil alarmı çoğaltmak yerine tekrar/güncellik bilgisini
  günceller; backend deduplication sonucu esas alınır.

## Son İhlaller Tablosu

- Sticky header, sayfalama, sıralama, filtre özeti ve satır action menu kullanır.
- Varsayılan sıralama en yeni olaydır; kritik durum tek başına renkle anlatılmaz.
- Skor sütunu sayısal ve sağ hizalı; veri yoksa `—`.
- Teknik hata satırı kalite skoruna veya kritik kalite ihlaline dönüştürülmez.
- Satır seçimi kullanıcının veri scope'unu genişletemez; yetkisiz URL 403 bekler.

## Rol ve Yetki Görünürlüğü

| Yüzey | Görünürlük |
| --- | --- |
| Yetkili kapsam KPI/trend | Tüm yetkili dashboard kullanıcıları |
| Enterprise skor | Yalnız `can_view_enterprise` kararı true ise |
| Kaynak/dataset drill-down | Yalnız backend `allowed_source_ids` kapsamı |
| Operasyonel teknik hata listesi | Veri Kalitesi Uzmanı / Sistem Yöneticisi sözleşmesi sonrası |
| Issue eylemleri | İlgili rol + backend yetki kararı; yalnız gizleme yeterli değil |
| Audit bağlantısı | Denetçi/yetkili rol ve ayrı audit erişim politikası |

UI rol veya scope üretmez. Yüzeyin gizlenmesi, backend 403 ve repository filtrelemesi
yerine geçmez.

## Loading, Empty ve Error

| Durum | Davranış |
| --- | --- |
| İlk loading | KPI ve grafik ölçülerini koruyan skeleton; tablo satır skeleton'ı |
| Filtre loading | Mevcut içeriği bağlamı bozmadan pending duruma al; eski/yeni zamanı belirt |
| Tüm dashboard empty | Veri yok açıklaması, aktif filtre özeti ve izinli sonraki eylem |
| Bölüm empty | Yalnız ilgili bölümde `—`/boş durum; diğer bölümleri kapatma |
| Query timeout | Teknik hata, correlation ID ve tarih daraltma eylemi |
| Yetkisiz | Veri varlığını ifşa etmeyen 403 yüzeyi |
| Grafik render hatası | Aynı view-model'in erişilebilir tablo görünümünü koru |

## Responsive Sözleşme

- `1440×900`: dört KPI tek satır; trend/alarm ve bar/heatmap iki kolon.
- `1280×800`: alarm ve grafik alanları sıkılaşır; tablo yatay sayfa taşması üretmez.
- `1024×768`: navigasyon ikon rayına daralır; KPI iki kolon, analiz bölümleri tek
  kolon olabilir.
- `1366×768` ve `1920×1080`: `NFR-USA-004` kabul görünümüdür.
- Hero ölçekli başlık, viewport'a bağlı font büyütme ve mobil kapsam eklenmez.

## Görsel Kabul Kriterleri

1. Referans görsel ve token eşlemesi incelenmiştir.
2. Storybook story'leri normal/loading/empty/technical error/critical/no-data ve uzun
   içerik durumlarını kapsar.
3. Playwright zorunlu viewport ekran görüntüleri alınmıştır.
4. Spacing, tipografi, renk, yoğunluk ve hizalama için en az iki iyileştirme turu
   kaydedilmiştir.
5. Teknik hata mor, kritik kalite ihlali kırmızı ve uyarı turuncudur; marka sarısı
   semantik durum olarak kullanılmamıştır.
6. Grafik ve tablo aynı view-model ile aynı toplamları gösterir.
7. Klavye, focus, ARIA ve renk dışı durum işaretleri doğrulanmıştır.
8. Hassas/ham veri, secret, SQL veya stack trace görsel artifact'lara girmemiştir.

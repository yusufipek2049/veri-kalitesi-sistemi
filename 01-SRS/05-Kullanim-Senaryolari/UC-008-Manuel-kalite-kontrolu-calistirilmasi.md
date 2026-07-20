---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-008"
created_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-008
---

# UC-008 — Manuel kalite kontrolü çalıştırılması

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-008** |
| Kullanım Senaryosu Adı | Manuel kalite kontrolü çalıştırılması |
| Amaç | Seçilen kuralların talep üzerine çalıştırılması. |
| Kısa Açıklama | Kullanıcı kapsamı seçer; sistem idempotent iş oluşturup yürütür. |
| Birincil Aktör | Veri Kalitesi Uzmanı |
| İkincil Aktörler | Data Steward; Veri Kaynağı; İş Kuyruğu |
| Öncelik | Must |
| Tetikleyici | Kullanıcının manuel çalıştırma komutu vermesi. |
| Ön Koşullar | Kural ve kaynak aktif; yetki mevcut; kapasite kotası uygun olmalıdır. |

**Temel Akış**

1. Kullanıcı kural/veri kümesi ve isteğe bağlı bölüm seçer.
2. Sistem kapsam ve tahmini maliyeti gösterir.
3. Kullanıcı başlatır.
4. Sistem idempotency anahtarıyla Execution oluşturur.
5. İş kuyruğa alınır ve kaynak kotasına göre çalışır.
6. Durum ve ilerleme güncellenir.
7. Tamamlanınca sonuçlar saklanır ve skorlama tetiklenir.

**Alternatif Akışlar**

1. Bağımsız kurallar kaynak kotası içinde paralel çalışır.
2. Kullanıcı bekleyen veya çalışan işi iptal edebilir.
3. Geçici teknik hatada en fazla üç retry uygulanır.

**İstisna Akışları**

1. Aynı anahtarla tekrar isteği yeni iş oluşturmaz.
2. Kalıcı bağlantı/SQL hatası TECHNICAL_ERROR olur.
3. Timeoutta iş sonlandırılır; kısmi sonuç resmi skora katılmaz.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-002, RULE-003, RULE-011 |
| Son Koşullar | Execution geçmişi ve sonuç durumu oluşur. |
| Başarı Garantisi | Tek yürütme ve doğru durum geçişleriyle sonuç üretilir. |
| Minimum Garanti | Hata/iptalde kaynakta değişiklik olmaz; olay izlenebilir kalır. |
| İlgili Fonksiyonel Gereksinimler | FR-036, FR-038–FR-045 |
| Kabul Kriterleri | Başlatma 3 saniye içinde Execution ID döndürmeli; tekrar istek aynı ID'yi vermelidir. |

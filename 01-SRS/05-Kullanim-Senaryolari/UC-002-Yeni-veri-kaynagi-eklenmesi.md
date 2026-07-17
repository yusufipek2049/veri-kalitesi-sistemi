---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-002"
generated_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-002
---

# UC-002 — Yeni veri kaynağı eklenmesi

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-002** |
| Kullanım Senaryosu Adı | Yeni veri kaynağı eklenmesi |
| Amaç | Kalite kontrolleri için kaynak bağlantı tanımı oluşturmak. |
| Kısa Açıklama | Yetkili kullanıcı kaynak türünü, ağ bilgilerini, secret referansını ve sahibini tanımlar. |
| Birincil Aktör | Veri Mühendisi |
| İkincil Aktörler | Sistem Yöneticisi; Data Owner; Secret Manager |
| Öncelik | Must |
| Tetikleyici | Kullanıcının “Yeni Veri Kaynağı” işlemini seçmesi. |
| Ön Koşullar | Kullanıcı kaynak oluşturma yetkisine sahip olmalı; gerekli ağ bilgileri bulunmalıdır. |

**Temel Akış**

1. Kullanıcı desteklenen kaynak türünü seçer.
2. Sistem türe özgü zorunlu alanları gösterir.
3. Kullanıcı bağlantı ve sahiplik bilgilerini girer.
4. Sistem alanları ve ad benzersizliğini doğrular.
5. Gizli bilgiler secret manager'a yazılır; sistem yalnız referansı saklar.
6. Veri kaynağı pasif/test bekliyor durumunda oluşturulur.
7. İşlem audit loga yazılır.

**Alternatif Akışlar**

1. CSV/Excel için ağ hostu yerine güvenli dosya konumu ve sayfa/ayraç bilgisi alınır.
2. REST API için base URL, kimlik yöntemi, header ve sayfalama politikası tanımlanır.

**İstisna Akışları**

1. Secret manager yazma hatasında kaynak kaydı tamamlanmaz.
2. Desteklenmeyen sürücü veya geçersiz portta doğrulama hatası gösterilir.
3. Kritik kaynağa Data Owner atanmadıysa aktif etme engellenir.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-001, RULE-002, RULE-009 |
| Son Koşullar | Yeni DataSource kaydı oluşur; bağlantı henüz doğrulanmadıysa aktif değildir. |
| Başarı Garantisi | Gizli bilgi açık metin saklanmadan benzersiz kaynak oluşturulur. |
| Minimum Garanti | Başarısızlıkta yarım secret veya metadata kaydı bırakılmaz. |
| İlgili Fonksiyonel Gereksinimler | FR-007, FR-009, FR-010, FR-014, FR-080, FR-084 |
| Kabul Kriterleri | Zorunlu alanlar dolu ve secret manager erişilebilir olduğunda kaynak kaydı ve audit kaydı oluşmalıdır. |

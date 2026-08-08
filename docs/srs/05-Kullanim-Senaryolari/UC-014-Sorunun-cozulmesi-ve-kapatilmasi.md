---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-014"
created_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-014
---

# UC-014 — Sorunun çözülmesi ve kapatılması

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-014** |
| Kullanım Senaryosu Adı | Sorunun çözülmesi ve kapatılması |
| Amaç | Kök neden ve düzeltici faaliyet doğrulandıktan sonra issue yaşam döngüsünü tamamlamak. |
| Kısa Açıklama | Sorumlu çözüm bilgilerini girer; Data Owner/Steward kalite kontrolüyle doğrular ve kapatır. |
| Birincil Aktör | Data Steward |
| İkincil Aktörler | Veri Mühendisi; Data Owner; ServiceNow |
| Öncelik | Must |
| Tetikleyici | Sorumlunun çözüm faaliyeti tamamladığını bildirmesi. |
| Ön Koşullar | Issue Atandı/İnceleniyor/Çözüm Bekliyor durumunda olmalıdır. |

**Temel Akış**

1. Sorumlu kök neden, düzeltici faaliyet, kanıt ve tamamlanma bilgisini girer.
2. Issue Çözüldü durumuna alınır.
3. Sistem doğrulama kural çalıştırması başlatır veya mevcut sonucu bağlar.
4. Doğrulama başarılıysa Data Owner/Steward issue'yu Doğrulandı durumuna alır.
5. Yetkili kullanıcı issue'yu Kapatıldı durumuna geçirir.
6. Çözüm öncesi/sonrası skor farkı kaydedilir.
7. ServiceNow durumu eşlenir ve tüm geçmiş saklanır.

**Alternatif Akışlar**

1. Doğrulama kısmen başarılıysa issue Çözüm Bekliyor durumuna döner.
2. Aynı kural tekrar başarısız olursa kapalı issue yeniden açılır veya yeni olayla ilişkilendirilir.

**İstisna Akışları**

1. Doğrulama çalıştırması teknik hata verirse issue doğrulanmaz.
2. Kök neden veya düzeltici faaliyet olmadan Çözüldü geçişi reddedilir.
3. Geçersiz durum geçişi engellenir.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-003, RULE-006, RULE-007 |
| Son Koşullar | Issue kapatılır veya kontrollü biçimde önceki duruma döner. |
| Başarı Garantisi | Yalnız başarılı kalite doğrulaması sonrası kapatma yapılır; etki ölçülür. |
| Minimum Garanti | Tüm kanıt ve geçmiş korunur; teknik hata çözüm sayılmaz. |
| İlgili Fonksiyonel Gereksinimler | FR-066–FR-071, FR-074, FR-087 |
| Kabul Kriterleri | Kapatma öncesi doğrulama skoru ve zorunlu çözüm alanları bulunmalıdır. |

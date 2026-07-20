---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-013"
created_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-013
---

# UC-013 — Veri kalitesi sorununun kullanıcıya atanması

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-013** |
| Kullanım Senaryosu Adı | Veri kalitesi sorununun kullanıcıya atanması |
| Amaç | Sorunun doğru sorumlu ve öncelikle sahiplenilmesini sağlamak. |
| Kısa Açıklama | Sistem veya yetkili kullanıcı issue'yu Data Owner/Data Steward'a atar; gerekirse ServiceNow ticket açar. |
| Birincil Aktör | Data Steward |
| İkincil Aktörler | Veri Yönetişimi Uzmanı; ServiceNow |
| Öncelik | Must |
| Tetikleyici | Yeni veya sahipsiz issue görüntülenir. |
| Ön Koşullar | Issue açık ve kullanıcı atama yetkisine sahip olmalıdır. |

**Temel Akış**

1. Kullanıcı issue detayını açar.
2. Sistem önerilen sahip ve önceliği gösterir.
3. Kullanıcı atanan kişiyi, önceliği ve son tarihi seçer.
4. Sistem kapsam ve kullanıcı aktifliğini doğrular.
5. Issue Atandı durumuna geçirilir.
6. Atanan kullanıcıya sistem içi bildirim oluşturulur.
7. Politika uygunsa ServiceNow ticket idempotent biçimde oluşturulur.

**Alternatif Akışlar**

1. Kullanıcı sorunu ekip/rol kuyruğuna atayabilir.
2. ServiceNow ticket daha önce varsa yeni ticket açılmaz, bağlantı güncellenir.

**İstisna Akışları**

1. Pasif veya kapsam dışı kullanıcıya atama reddedilir.
2. ServiceNow API hatasında yerel atama tamamlanır, entegrasyon retry kuyruğuna alınır.
3. Aynı issue için çift ticket engellenir.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-006, RULE-009, RULE-011 |
| Son Koşullar | Issue sahibi, öncelik, durum ve entegrasyon referansı güncellenir. |
| Başarı Garantisi | Sorun tek sorumlu zinciri ve değişiklik geçmişiyle izlenebilir hale gelir. |
| Minimum Garanti | Entegrasyon başarısız olsa da yerel issue kaybolmaz. |
| İlgili Fonksiyonel Gereksinimler | FR-063–FR-067, FR-071, FR-087 |
| Kabul Kriterleri | Atama audit kaydı ve bildirim üretmeli; tekrar ServiceNow isteği tek ticket ile sonuçlanmalıdır. |

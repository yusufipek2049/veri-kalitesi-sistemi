---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-016"
generated_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-016
---

# UC-016 — Audit kayıtlarının incelenmesi

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-016** |
| Kullanım Senaryosu Adı | Audit kayıtlarının incelenmesi |
| Amaç | Kritik işlemler ve değişikliklerin denetim kanıtı olarak incelenmesi. |
| Kısa Açıklama | Denetçi filtrelerle audit kayıtlarını görüntüler ve yetkili biçimde dışa aktarır. |
| Birincil Aktör | Denetçi |
| İkincil Aktörler | Sistem Yöneticisi; Audit Altyapısı |
| Öncelik | Must |
| Tetikleyici | Denetçinin audit ekranını açması. |
| Ön Koşullar | Audit görüntüleme yetkisi ve kayıtlar bulunmalıdır. |

**Temel Akış**

1. Sistem denetçinin kapsamını doğrular.
2. Denetçi tarih, kullanıcı, işlem, nesne, sonuç ve istemci filtresi girer.
3. Sistem append-only audit kayıtlarını sayfalı getirir.
4. Denetçi bir kaydın eski/yeni değer, correlation ID ve ilişkili nesne detayını açar.
5. Bütünlük doğrulama sonucu görüntülenir.
6. Denetçi yetkili kayıtları dışa aktarır.
7. Dışa aktarma işlemi de audit loga yazılır.

**Alternatif Akışlar**

1. Beş yıllık geniş sorgu asenkron rapor olarak hazırlanır.
2. Hassas alanların değerleri maskeli gösterilir.

**İstisna Akışları**

1. Yetkisiz audit alanına erişim 403 ile reddedilir.
2. Bütünlük kontrolü başarısızsa güvenlik alarmı oluşur ve kayıt silinmez.
3. Audit deposu ulaşılamazsa kullanıcıya correlation ID gösterilir.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-007, RULE-008, RULE-009, RULE-010 |
| Son Koşullar | Denetim görünümü veya güvenli dışa aktarma oluşur. |
| Başarı Garantisi | Kritik değişikliklerin aktör, zaman, nesne ve sonuç bilgisi doğrulanabilir. |
| Minimum Garanti | Hata halinde audit verisi değiştirilmez ve erişim sınırı korunur. |
| İlgili Fonksiyonel Gereksinimler | FR-004, FR-044, FR-077–FR-079, FR-082 |
| Kabul Kriterleri | Kritik örnek işlemlerin %100'ü filtrelenebilir ve bütünlük kontrolünden geçmelidir. |

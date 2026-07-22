---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_section: "UC-020"
created_at: 2026-07-22
tags: [srs, uc, uc-020, remediation]
---

# UC-020 — Kanıtlı öneri ve remediation

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-020** |
| Amaç | Kanıtlı teşhisten kontrollü öneri ve doğrulanabilir iyileştirme akışı üretmek. |
| Birincil Aktör | Data Steward; Veri Kalitesi Uzmanı |
| İkincil Aktörler | Ayrı onaylayan; Veri Mühendisi; Yetkili servis hesabı |
| Öncelik | Should/Could — ikinci faz |
| Tetikleyici | Yetkili kullanıcı bir teşhis için öneri ister veya uzman önerisi ekler. |
| Ön Koşullar | Teşhis, bağlı kanıt, öneri politikası ve güvenilir aktör. |

**Temel Akış**

1. Sistem öneriyi mekanizma, sürüm, dayanak, güven, risk ve onayla oluşturur.
2. Kullanıcı kanıtları ve karşı hipotezleri inceler.
3. Sistem dry-run ve etki değerlendirmesini üretir.
4. Politika gerektiriyorsa farklı kullanıcı onaylar veya reddeder.
5. Yalnız izinli eylem canary olarak çalışır; sonuç yeniden doğrulanır.
6. Başarılı doğrulama sonrası tam uygulama veya kapanış; başarısızlıkta rollback yapılır.

**İstisna Akışları**

1. Kanıt/mekanizma/sürüm yoksa öneri yayımlanmaz.
2. Düşük güvenli veya onaysız öneri otomatik uygulanmaz.
3. Audit, canary, yeniden doğrulama veya rollback başarısızsa akış güvenli durumda durur.
4. Üretim kaynak verisini değiştiren eylem her koşulda reddedilir.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-002, RULE-005, RULE-011, RULE-019, RULE-021, RULE-023 |
| Son Koşullar | Öneri, karar, eylem, doğrulama ve rollback olayları auditli kalır. |
| İlgili Fonksiyonel Gereksinimler | FR-103–FR-105, FR-109, FR-111 |
| Kabul Kriterleri | AC-063, AC-064, AC-068, AC-071 |

---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-001"
created_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-001
---

# UC-001 — Sisteme giriş yapılması

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-001** |
| Kullanım Senaryosu Adı | Sisteme giriş yapılması |
| Amaç | Kullanıcının kimliğini doğrulayıp yetkili kapsama erişmesini sağlamak. |
| Kısa Açıklama | Kullanıcı LDAP kimliğiyle giriş yapar; sistem rol ve kapsamlarını yükler. |
| Birincil Aktör | Kurumsal Kullanıcı |
| İkincil Aktörler | LDAP; Audit Log |
| Öncelik | Must |
| Tetikleyici | Kullanıcının giriş ekranında oturum açmayı seçmesi. |
| Ön Koşullar | Kullanıcı LDAP'ta aktif olmalı; sistem LDAP'a erişebilmelidir. |

**Temel Akış**

1. Kullanıcı kullanıcı adı ve parolasını girer.
2. Sistem kimlik bilgilerini TLS üzerinden LDAP'a iletir.
3. LDAP kimliği doğrular ve grup bilgilerini döndürür.
4. Sistem kullanıcıyı yerel rol/kapsamla eşler.
5. Sistem güvenli oturum oluşturur ve giriş audit kaydı yazar.
6. Kullanıcı yetkili ana dashboarda yönlendirilir.

**Alternatif Akışlar**

1. Geçerli LDAP kullanıcısının yerel rolü yoksa sistem erişimi reddeder ve yöneticiye rol atama gereksinimini gösterir.
2. MFA kurumsal olarak etkinleştirilirse LDAP/SSO sonrası ikinci faktör adımı uygulanır.

**İstisna Akışları**

1. Kimlik bilgileri hatalıysa oturum oluşturulmaz ve genel hata gösterilir.
2. LDAP ulaşılamazsa sistem teknik hata kodu üretir; yerel acil durum hesabı yalnız güvenlik onayıyla kullanılabilir.
3. Başarısız giriş limiti aşılırsa hesap/istemci geçici olarak engellenir.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-001, RULE-009 |
| Son Koşullar | Aktif oturum veya kontrollü reddetme kaydı oluşur. |
| Başarı Garantisi | Yetkili kullanıcı doğru rol kapsamıyla sisteme erişir. |
| Minimum Garanti | Hata durumunda hiçbir yetkisiz oturum oluşmaz; deneme kaydedilir. |
| İlgili Fonksiyonel Gereksinimler | FR-001, FR-002, FR-003, FR-005, FR-006, FR-081 |
| Kabul Kriterleri | Geçerli kullanıcı 5 saniye içinde giriş yapmalı; geçersiz kullanıcı hiçbir korumalı ekrana erişememelidir. |

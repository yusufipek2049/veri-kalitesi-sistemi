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
| Kısa Açıklama | Kullanıcı LDAP destekli kurumsal IdP/SSO ve MFA ile giriş yapar; sistem grup, rol ve kapsamlarını yükler. |
| Birincil Aktör | Kurumsal Kullanıcı |
| İkincil Aktörler | Kurumsal IdP/SSO; Audit Log |
| Öncelik | Must |
| Tetikleyici | Kullanıcının giriş ekranında oturum açmayı seçmesi. |
| Ön Koşullar | Kullanıcı kurumsal dizinde aktif olmalı; IdP erişilebilir olmalı ve MFA sağlayabilmelidir. |

**Temel Akış**

1. Kullanıcı kurumsal SSO ile giriş başlatır.
2. Kurumsal IdP, LDAP destekli kimlik doğrulama ve MFA adımını yürütür.
3. IdP, doğrulanmış OIDC veya SAML beyanı ile grup bilgilerini döndürür.
4. Sistem çoklu grup üyeliğini sürümlü çatışma/ret politikasıyla yerel rol ve kapsama eşler.
5. Sistem güvenli oturum oluşturur ve giriş audit kaydı yazar.
6. Kullanıcı yetkili ana dashboarda yönlendirilir.

**Alternatif Akışlar**

1. Geçerli IdP kullanıcısının yerel rolü yoksa sistem erişimi reddeder ve yöneticiye rol atama gereksinimini gösterir.
2. Grup rolleri çatışırsa deterministik öncelik uygulanır veya politika gereği erişim reddedilir.

**İstisna Akışları**

1. Kimlik bilgileri hatalıysa oturum oluşturulmaz ve genel hata gösterilir.
2. IdP ulaşılamazsa sistem teknik hata kodu üretir ve güvenliksiz yerel girişe düşmez; yalnız kontrollü, süreli ve auditli break-glass hesabı ayrı politikayla kullanılabilir.
3. MFA eksik veya başarısızsa oturum oluşturulmaz.
4. Başarısız giriş limiti aşılırsa hesap/istemci geçici olarak engellenir.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-001, RULE-009 |
| Son Koşullar | Aktif oturum veya kontrollü reddetme kaydı oluşur. |
| Başarı Garantisi | Yetkili kullanıcı doğru rol kapsamıyla sisteme erişir. |
| Minimum Garanti | Hata durumunda hiçbir yetkisiz oturum oluşmaz; deneme kaydedilir. |
| İlgili Fonksiyonel Gereksinimler | FR-001, FR-002, FR-003, FR-005, FR-006, FR-081 |
| Kabul Kriterleri | Geçerli SSO beyanı ve MFA kanıtı olan kullanıcı 5 saniye içinde giriş yapmalı; MFA'sı eksik veya geçersiz kullanıcı hiçbir korumalı ekrana erişememelidir. |

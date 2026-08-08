---
type: open-decision-register
status: resolved
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-29
---

# Açık Konular — Karara Bağlandı (Modelleme Varsayımları)

> **GOV-DECISION-2026-07-29 (operatör yetkisi, akademik modelleme bağlamı).**
> Bu proje gerçek bir üretim bankacılık dağıtımı değil, bir **modelleme/akademik
> çalışmadır.** Aşağıdaki uyum/kurumsal kayıtlar, **gerçek düzenleyici çerçevelere
> dayandırılmış proje kararları** olarak kapatılmıştır. Bunlar **modelleme
> varsayımıdır; otoriter hukuki/regülatif görüş değildir.** Gerçek bir üretim
> dağıtımında adı geçen sahiplerce (Hukuk, KVKK Komitesi, IAM, Risk Yönetimi,
> İş Sürekliliği) doğrulanması gerekir. Kararlar mümkün olduğunca gerçek mevzuata
> (BDDK Bilgi Sistemleri Yönetmeliği, KVKK, BCBS 239, VUK/TTK, ISO/IEC 27001)
> gerekçelendirilmiştir; kaynağı olmayan hiçbir eşik "otoriter gerçek" gibi
> sunulmamıştır.

Teknik yönü kesinleşmiş kayıtlar [Alınan Kararlar](Alinan-Kararlar.md) içindedir.

## Karara Bağlanan Kayıtlar

| ID | Proje Kararı (modelleme) | Dayanak |
| --- | --- | --- |
| `OPEN-BNK-001` | Sistem BDDK "Bankaların Bilgi Sistemleri ve Elektronik Bankacılık Hizmetleri Hakkında Yönetmelik" kapsamındadır; bilgi sistemleri yönetişimi, birincil/ikincil sistem sürekliliği, log yönetimi, yetkilendirme, sızma testi ve bağımsız denetim hükümleri uygulanır. ISO/IEC 27001 ve COBIT ile hizalanır. | BDDK BS Yönetmeliği (RG 15.03.2020/31069); BDDK BS Bağımsız Denetim Tebliği; ISO/IEC 27001 |
| `OPEN-BNK-002` | RBAC rolleri: `dq_viewer`, `dq_analyst`, `dq_steward`, `dq_stakeholder`, `dq_operator`, `dq_auditor` (salt-okunur), `dq_admin`. Kimlik yaşam döngüsü kaynağı kurumsal İK/HR; IdP (AD/LDAP) grupları `APP_DQ_<ROLE>` rollerine eşlenir; JML (joiner/mover/leaver) HR olaylarıyla IdP üzerinden sürülür; yerel kullanıcı deposu yok; en az yetki. | ISO/IEC 27001 A.9; KVKK erişim/veri minimizasyonu; NIST RBAC |
| `OPEN-BNK-008` | Saklama: audit/işlem kayıtları 10 yıl, sistem/erişim logları 5 yıl, kişisel veri KVKK'da amaçla sınırlı + yasal süre. İmha: 6 ayda bir periyodik güvenli silme / kripto-erase. Sahiplik Veri Sorumlusu (banka) + İç Denetim gözetimi. | VUK md.253 / TTK md.82 (10 yıl ticari belge); KVKK Silme, Yok Etme ve Anonim Hale Getirme Yönetmeliği (periyodik imha ≤6 ay) |
| `OPEN-BNK-009` | ServiceNow yurt-içi/kurum-içi kurulur. SaaS ise veri işleyen sözleşmesi (KVKK md.8) zorunlu ve **yurt dışına kişisel veri aktarımı yapılmaz**. Entegrasyon yalnız metadata/olay taşır; ham kişisel veri gönderilmez. | KVKK md.8 (yurt içi aktarım / veri işleyen), md.9 (yurt dışı kısıtı) |
| `OPEN-BNK-011` | DQ platformu Tier-2 (önemli, çekirdek bankacılık değil): **RTO = 4 saat, RPO = 1 saat.** Yedek şifreleme AES-256, anahtarlar HSM/KMS. Restore testi 3 ayda bir; tam DR tatbikatı yılda 1. | BDDK süreklilik/yıllık test yükümlülüğü; sektör RTO/RPO pratiği |
| `OPEN-BNK-013` | BCBS 239 prensipleri (yönetişim, veri mimarisi/altyapı, doğruluk, bütünlük, güncellik, uyarlanabilirlik) DQ yönetişim temeli olarak benimsenir. Raporlama zinciri: `dq_steward` → Veri Yönetişimi Komitesi → Risk Yönetimi → düzenleyici (BDDK/TCMB). | BCBS 239 (2013) Prensip 1–6 |
| `OPEN-BNK-018` | Kurumsal AD'ye LDAPS (636), TLS 1.2+ ve sabitlenmiş kurumsal CA. Connect timeout 5s, read timeout 10s. Kimlik hatası fail-closed (ret); IdP kesintisi 503 + kontrollü retry; sahiplik IAM/Altyapı. Endpoint config + secret referansı (`ldaps://idp.internal:636`). | ISO/IEC 27001; TLS 1.2+ asgari; fail-closed ilkesi |
| `OPEN-BNK-019` | 5 hatalı giriş / 15 dk → 30 dk kilit. API 100 istek/dk/istemci (token bucket). Access token 15 dk, refresh 8 saat (kullanımda döner), imza anahtarı 90 günde bir rotasyon. Opak `client_id`; paylaşımlı oturum deposu Redis (HA, at-rest şifreli). | OWASP ASVS; NIST SP 800-63B; anahtar rotasyon pratiği |

## Üretim Uygulama Notu

Bu kararlar **kararlaştırılmış** olsa da henüz **uygulanmamıştır**; runtime kanıtı
ilgili iterasyonlarda üretilir. Gerçek dağıtımda değerler yetkili sahiplerce
doğrulanır. Belirsizlik güvenlik/uyum/iş kuralını etkilediğinde işlem fail-closed
kalır ve kayıt yeniden açılır.

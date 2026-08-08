---
iteration: ENTERPRISE-LAB-02
status: PrototypeVerified
completed_at: 2026-07-29
---

# ENTERPRISE-LAB-02 — Uygulama Adaptör Bağlantıları

## Kapsam

ENTERPRISE-LAB-01 sentetik/non-production servisleri uygulamanın mevcut güven
sınırlarına bağlandı:

- Keycloak `userinfo` doğrulaması, sentetik MFA kanıtı ve sürümlü grup
  eşlemesinden güvenilir `ActorContext`,
- runtime dosyasından alınan bearer ile yalnız ortam-kapsamlı referans çözen
  yerel prototip secret manager adaptörü,
- veri-minimum payload ve idempotency anahtarı kullanan fake ServiceNow HTTP
  adaptörü,
- veri-minimum audit projeksiyonu, deterministik idempotency anahtarı ve
  fail-closed aktarım kullanan SIEM adaptörü.

Uygulama bileşimi yalnız `LOCAL` ve `ACCEPTANCE` ortamlarında, mevcut sürümlü
ortam kapısı başarılı olduktan sonra oluşturulur. Sentetik olmayan veri,
production ortam/endpoint/secret kapsamı ve `PrototypeVerified` üzerindeki
iddialar reddedilmeye devam eder.

## Gereksinim izlenebilirliği

- `FR-001`–`FR-003`, `FR-009`, `FR-071`, `FR-087`
- `BFR-IAM-001`–`004`, `BFR-AUD-004`, `BFR-EXT-001`–`003`
- `27A-v1` / `27A-trusted-source-v1`

## Değişiklik ve doğrulama

- Uygulama adaptörleri ve bileşim:
  `src/veri_kalitesi/enterprise_lab/adapters.py`
- Fake SIEM idempotency davranışı ve laboratuvar işletim açıklaması:
  `infra/enterprise-lab`
- Hedefli negatif/sözleşme testleri:
  `tests/unit/test_enterprise_lab_adapters.py`

Hedefli ENTERPRISE-LAB-01/02 testleri `24 passed`; ilgili Python dosyalarında
`ruff check` ve `ruff format --check` başarılıdır. Testler bağlantı kaybı,
Keycloak yetki reddi ve MFA/eşleme eksikliği, secret bulunamaması, ServiceNow
yetki/ağ hatası ve SIEM audit aktarım hatasının fail-closed davranışını kapsar.

## Sınıflandırma ve kalan sınırlar

- **Teknik sınıflandırma:** `PrototypeVerified`
- **Uyum/banka durumu:** `ComplianceReviewRequired`
- **Banka onayı:** Üretilmedi; `ApprovedByBank` değildir.
- **Production readiness:** Üretilmedi; production-ready değildir.

Keycloak dev mode ve sentetik MFA/grup politikası kurumsal IdP/SSO-MFA kanıtı
değildir. Yerel secret manager kurumsal PAM/HSM/workload identity değildir.
Fake ServiceNow ve bellek içi SIEM collector gerçek ürün, kalıcı outbox/WORM,
SOC işletimi veya kurumsal ağ dayanıklılığı kanıtı sağlamaz. Gerçek adaptörler
backlogda `ExternalDependency` kalır.

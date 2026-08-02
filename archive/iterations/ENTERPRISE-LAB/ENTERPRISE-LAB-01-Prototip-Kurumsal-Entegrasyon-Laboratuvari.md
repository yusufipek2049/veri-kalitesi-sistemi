---
iteration: ENTERPRISE-LAB-01
status: PrototypeVerified
completed_at: 2026-07-29
---

# ENTERPRISE-LAB-01 — Prototip Kurumsal Entegrasyon Laboratuvarı

## Kapsam

Yalnız sentetik veri ve `LOCAL` production olmayan ortam için Docker Compose
laboratuvarı oluşturuldu. Bileşim:

- Keycloak ve sentetik realm,
- Docker secret dosyalarını çözen yerel prototip secret manager,
- streaming replication kullanan PostgreSQL 16.13 primary-standby,
- RabbitMQ,
- veri-minimum/idempotent fake ServiceNow,
- allowlist olay zarfı kabul eden SIEM collector,
- digest adresli, ikinci yazımı ve silmeyi reddeden create-only kanıt deposu

servislerini içerir. Tüm servisler sürümlü fail-closed ortam kapısının başarıyla
tamamlanmasına bağlıdır ve healthcheck taşır.

## Gereksinim ve karar izlenebilirliği

- `NFR-SEC-002`, `NFR-SEC-005`, `NFR-SEC-008`, `NFR-SEC-011`
- `NFR-MNT-004`, `NFR-MNT-006`
- `BFR-OPS-001`, `BFR-OPS-002`, `BFR-EXT-001`–`003`
- `ADR-006`, `ADR-008`, `ADR-009`, `ADR-014`
- `27A-v1` / `27A-trusted-source-v1`

## Değişiklik ve kanıt

- Compose, config, bootstrap ve servisler:
  [`infrastructure/enterprise-lab`](../../../infrastructure/enterprise-lab/README.md)
- Fail-closed kapı: `veri_kalitesi.enterprise_lab`
- Birim/negatif test:
  `06-Testler/01-Birim/test_enterprise_lab.py`

## Hedefli doğrulama

- `python3 -m pytest -q 06-Testler/01-Birim/test_enterprise_lab.py`:
  `7 passed`.
- İlgili Python dosyalarında `ruff check`: başarılı.
- `docker compose ... config --quiet`: başarılı.
- `docker compose ... up -d --build --wait`: sekiz servis healthy; ortam kapısı
  exit `0`.
- PostgreSQL primary `pg_stat_replication`: `streaming`; standby
  `pg_is_in_recovery()`: `t`.
- Fake ServiceNow create/replay: `201/200`, aynı ticket; SIEM kabulü: `202`.
- Kanıt deposu create/duplicate/delete: `201/409/405`.
- Yerel secret çözümleme: başarılı; değer komut çıktısına yazılmadı.

## Sınıflandırma ve sınırlar

- **Teknik sınıflandırma:** `PrototypeVerified`
- **Uyum/banka durumu:** `ComplianceReviewRequired`
- **Banka onayı:** Üretilmedi; `ApprovedByBank` değildir.
- **Production readiness:** Üretilmedi; production-ready değildir.

Fake ServiceNow/SIEM, yerel secret çözümleyici ve create-only kanıt deposu
kurumsal ürün değildir. Create-only davranış altyapı yöneticisine karşı WORM
kanıtı sağlamaz. PostgreSQL standby otomatik failover/quorum/yedekleme/DR veya
kurumsal HA kanıtı değildir. Keycloak dev mode production IdP/SSO-MFA kanıtı
değildir. Gerçek endpoint, secret, kimlik veya veri kullanılmamıştır.

## Geri alma

Compose durdurulabilir. `down --volumes` yalnız açıkça istendiğinde sentetik lab
verilerini siler. Laboratuvarın kaldırılması production kapılarını açmaz; kurumsal
adaptörler `ExternalDependency` kalır.

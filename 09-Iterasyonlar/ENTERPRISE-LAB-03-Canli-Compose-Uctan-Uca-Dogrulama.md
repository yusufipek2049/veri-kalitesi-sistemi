---
iteration: ENTERPRISE-LAB-03
status: PrototypeVerified
completed_at: 2026-07-29
---

# ENTERPRISE-LAB-03 — Canlı Compose Uçtan Uca Doğrulama

## Kapsam

ENTERPRISE-LAB-01 servisleri volume silmeden canlı Compose ortamında ayağa
kaldırıldı. ENTERPRISE-LAB-02 uygulama adaptörleri aynı internal container ağı
üzerinde aşağıdaki olumlu ve negatif akışlarla çalıştırıldı:

- sentetik Keycloak oturumu ve `ENTERPRISE-LAB-02-v1` grup-rol-kaynak/dataset
  scope çözümlemesi;
- dosya tabanlı secret-reference erişimi;
- fake ServiceNow ticket oluşturma ve idempotent replay;
- veri-minimum ve idempotent SIEM audit aktarımı;
- geçersiz kimlik, eşlenmemiş rol/grup, eksik secret dosyası, secret yetki
  reddi, servis kesintisi, 403, timeout, 429, hatalı SIEM payloadı ve hatalı
  SIEM yanıtında fail-closed davranış ile sonraki geçerli istekte toparlanma.

Hata enjeksiyonu yalnız internal laboratuvar ağında, runtime dosyasından okunan
sentetik kontrol credential'ı ile tek sonraki istek için etkinleşir. One-shot
kapı çıktısı payload, token, secret veya endpoint ayrıntısı içermez.

## Gereksinim izlenebilirliği

- `NFR-SEC-002`, `NFR-SEC-005`, `NFR-SEC-008`, `NFR-SEC-011`
- `NFR-MNT-004`, `BFR-IAM-001`–`004`, `BFR-AUD-004`
- `BFR-EXT-001`–`003`, `RULE-011`, `AC-019`, `AC-055`
- `27A-v1` / `27A-trusted-source-v1`

## Canlı doğrulama

- `./infrastructure/enterprise-lab/scripts/verify-live.sh`: exit `0`; sekiz
  temel servis healthy ve 14 redakte canlı adapter senaryosu `PASSED`.
- Compose config: exit `0`.
- PostgreSQL primary replikasyon durumu `streaming`; standby
  `pg_is_in_recovery()=true`.
- ENTERPRISE-LAB-01/02 hedef birim testleri: `24 passed`.
- Hedef Python dosyalarında Ruff lint/format ve shell syntax kapıları: exit `0`.
- E2E container log taraması: runtime secret, token, endpoint ve hassas payload
  işareti bulunmadı.
- Sürümlü ayrıntı ve artifact digestleri:
  [kanıt manifesti](../08-Uyum-Kanitlari/Guvenlik-Testleri/ENTERPRISE-LAB-03-Kanit-Manifesti.json).

## Sınıflandırma ve kalan sınırlar

- **Teknik sınıflandırma:** `PrototypeVerified`
- **Uyum/banka durumu:** `ComplianceReviewRequired`
- **Banka onayı:** Üretilmedi; `ApprovedByBank` değildir.
- **Production readiness:** Üretilmedi; production-ready değildir.

Direct-grant oturum kurulumu, sentetik realm, yerel secret çözümleyici ve hata
enjeksiyonu yalnız `LOCAL`/sentetik kabul otomasyonudur. Gerçek kurumsal IdP,
PAM/HSM, ServiceNow, SIEM/WORM/SOC, HA/DR, production ağ politikası veya banka
onayı kanıtı değildir; bunlar `ExternalDependency` kalır.

## Geri alma

Laboratuvar `docker compose ... down` ile durdurulabilir. Bu doğrulamada volume
silinmemiştir. `down --volumes` çalıştırılmamıştır ve yalnız açık operatör
talebiyle kullanılmalıdır.

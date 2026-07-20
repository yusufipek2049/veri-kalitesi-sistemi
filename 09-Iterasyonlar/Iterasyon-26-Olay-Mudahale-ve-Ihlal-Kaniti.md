# İterasyon 26 — Olay Müdahale ve İhlal Kanıtı

## 26A — Veri-minimum güvenlik olayı ve ihlal şüphesi ayrımı

Durum: `TechnicallyVerified`

### Gereksinimler

- `BFR-IR-001`–`BFR-IR-004`
- `CTRL-KVKK-BREACH-001`
- `NFR-OBS-001`, `NFR-OBS-003`
- `NFR-PRV-001`, `NFR-PRV-002`, `NFR-PRV-005`
- `NFR-SEC-001`, `NFR-SEC-005`, `NFR-SEC-008`, `NFR-SEC-011`

### Kabul Sonucu

- Teknik güvenlik olayı ve kişisel veri ihlali şüphesi ayrı append-only kayıtlardır.
- Öğrenilme zamanı, 72 saat hedefi, kapsam/önlem kodları, veri kategorileri ve opak kanıt referansları korunur.
- Veri işleyen kaynaklı şüphe bildirim kanıt referansı olmadan kaydedilemez.
- Şüpheyi kaydeden aktör kendi bildirim kararını veremez; dış bildirim gönderilmez.
- Yetkisiz, servis, ayrıcalıklı ve scope dışı context fail-closed reddedilir.
- Domain, zaman çizelgesi ve audit outbox yazımları atomiktir.

### Kapsam Dışı

- Gerçek SIEM/SOC adaptörü ve olay sözlüğü
- Kurula veya ilgili kişiye otomatik bildirim
- HTTP/UI ve kanıt içeriği depolama
- Banka onaylı rol eşlemesi, saklama/imha ve hukuk/uyum kararı

Kanıt: [[08-Uyum-Kanitlari/Olay-Mudahale/Iterasyon-26A-Veri-Minimum-Ihlal-Suphesi-Kaniti]]

## Sıradaki Dilim

`26B` yalnız güvenilir ve kapsam içi privacy reviewer için veri-minimum ihlal zaman çizelgesi inceleme sorgusudur.

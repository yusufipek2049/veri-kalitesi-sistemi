# İterasyon 27 — Ortam Ayrımı ve DR

## Amaç

Ortam ayrımını, yedekleme/geri yükleme kontrollerini ve DR kanıtını banka ve
altyapı kararlarını varsaymadan küçük teknik dikeylerle oluşturmak.

## 27A — Fail-Closed Ortam Kimliği

Durum: `TechnicallyVerified`

- Sürümlü `LOCAL/DEVELOPMENT/TEST/ACCEPTANCE/PRODUCTION` ortam sınıfı eklendi.
- Ortam bilgisi yalnız sürümlü güvenilir konfigürasyon sağlayıcısından yüklenir.
- Üretim dışı ortamda gerçek banka verisi ve üretim secret kapsamı engellenir.
- Başlangıç kanıtı secret referansını taşımayan allowlist alanlarla sınırlıdır.
- Teknik kaynak arızası politika ihlalinden ayrı ve fail-closed ele alınır.

Kanıt: [İterasyon 27A](../08-Uyum-Kanitlari/Yedek-Geri-Yukleme/Iterasyon-27A-Fail-Closed-Ortam-Kimligi-Kaniti.md)

## Kalan Dilimler

- 27B — Şifreli yedek envanteri ve veri-minimum restore tatbikat kanıtı;
  `OPEN-BNK-011` ve `OPEN-BNK-012` kararları olmadan hazır değildir.
- 27C — Onaylı RTO/RPO ile uçtan uca DR tatbikatı; iş etki analizi ve gerçek
  altyapı olmadan uygulanmaz.

`CTRL-BDDK-BCP-001` bu iterasyonla tamamlanmış sayılmaz.

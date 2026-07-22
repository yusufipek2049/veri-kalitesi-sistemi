# İterasyon 34F — PostgreSQL Sentetik Dataset Kanıtı

- **Kontrol durumu:** `TechnicallyVerified`
- **Kontrol kapsamı:** `FR-089`–`FR-095`, `UC-017`, `RULE-016/017`,
  `AC/TS-048`–`AC/TS-056` teknik alt kapsamları
- **Sürüm:** `RELATIONAL_BANKING_GENERATOR_V1` /
  `RELATIONAL_BANKING_SCHEMA_V1` /
  `RELATIONAL_QUALITY_CONFIGURATION_V1`
- **Tarih:** 2026-07-22
- **Üretici rolü:** Yerel geliştirme/test otomasyonu

## Çalıştırma

Gerçek secret yerine süreç ortamı kullanıldı. Kanıt komutundaki parola redakte
edilmiştir.

```bash
SYNTHETIC_POSTGRES_TEST=1 PGHOST=localhost PGPORT=5433 \
PGDATABASE=data_quality_test PGUSER=postgres PGPASSWORD='<redacted>' \
PYTHONPATH=03-Backend/src pytest -q \
06-Testler/02-Entegrasyon/test_synthetic_postgresql_integration.py
```

## Sonuç

- 17 ilişkisel kaynak tablosu ve tablo başına 19.000 kayıt üretildi.
- Toplam 323.000 kayıt ve 63.022 kayıt düzeyi ground-truth kusuru oluştu.
- Her tabloda kusurlu kayıt oranı %15–%20 kabul aralığındadır.
- Dokuz kusur sınıfında bağımsız SQL oracle'ı sıfır FP ve sıfır FN üretti.
- Yeniden bağlantı sonrası 323.000 satırlık run kaydı kalıcı bulundu.
- Reset yalnız iki sentetik şemayı kaldırdı; kapsam dışı sentinel korundu.
- Kanonik digest:
  `4e5b7e13adbf0afc1ca271bbbba17aa3832c060903267cb02516991a0ecc3e01`.

Bu kanıt yalnız tamamen yapay yerel/test verisini kapsar. Uygulama kural motoru,
20 milyon satırlık anonimleştirilmiş performans kabulü, anonimlik incelemesi,
mevzuat uygunluğu ve banka onayı kapsamında değildir.

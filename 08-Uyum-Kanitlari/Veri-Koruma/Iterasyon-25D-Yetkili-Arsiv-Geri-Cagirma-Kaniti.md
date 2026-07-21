# İterasyon 25D — Yetkili Arşiv Geri Çağırma Talep ve Karar Kanıtı

## Kontrol Durumu

- Teknik durum: `TechnicallyVerified`
- Uyum durumu: `ComplianceReviewRequired`
- Tarih: 2026-07-21
- Üretici rolü: Codex geliştirme ajanı
- Kontroller: `CTRL-KVKK-DEL-001`, `CTRL-BDDK-AUD-001`, `CTRL-BDDK-SOD-001`
- Gereksinimler: `BFR-LCM-004`, `BFR-SOD-001/002/004`,
  `BFR-AUD-001/002/004`, `FR-077`, `FR-079`, `NFR-SEC-001/008/011`,
  `NFR-CMP-001/003`

## Teknik Kanıt

- Audit ve kalite skoru arşivleri için opak referanslı, idempotent geri çağırma
  talebi oluşturulabilir. Ham arşiv ve kapsam kimlikleri yalnız SHA-256 özetiyle
  saklanır.
- Talep güvenilir/geçerli normal kullanıcı context'i, sürümlü requester rolü,
  source/dataset/enterprise kapsamı ve allowlist amaç kodu gerektirir.
- Talebi açan aktör aynı talebi karara bağlayamaz. Onay/ret, farklı güvenilir
  normal kullanıcı, ayrı karar rolü, aynı veri kapsamı ve allowlist karar
  gerekçesi gerektirir.
- Aynı idempotency anahtarı/payload tek talep; aynı aktör/karar/gerekçe tek
  terminal karar üretir. Farklı payload veya farklı ikinci karar reddedilir.
- Talep ve karar tabloları append-only'dir. Domain olayı ile redakte audit outbox
  aynı transaction'da yazılır; audit-stage arızası domain yazımını geri alır ve
  merkezi audit kesintisi olayı `PENDING` tutar.
- Audit özeti yalnız durum, kayıt türü ve kapsam türünü taşır; arşiv referansı,
  kapsam kimliği, amaç/gerekçe metni veya idempotency anahtarı içermez.

## Doğrulama

- Komut: `python3 -m pytest -q 06-Testler/01-Birim/test_retention.py 06-Testler/01-Birim/test_retention_legal_hold.py 06-Testler/01-Birim/test_retention_disposal_job.py 06-Testler/01-Birim/test_retention_archive_recall.py`
- Sonuç: retention hedef grubunda 71 test geçti.
- Tam regresyon, mypy, Ruff, format, derleme, secret, SBOM, kanıt manifesti ve
  birleşik sürüm ön kontrol sonuçları iterasyon kapanışında doğrulandı.

## Sınırlar

- Bu servis arşiv içeriğini okumaz, erişime açmaz, taşımaz veya dışa aktarmaz.
  `APPROVED` yalnız veri getirme adaptörünün daha sonra doğrulayacağı teknik karar
  kaydıdır.
- Gerçek arşiv deposu/resolver'ı, erişim süresi, indirme/DLP, üretim rol eşlemesi,
  PostgreSQL/WORM yetkileri ve geri çağrılan kopyanın yeniden imhası uygulanmadı.
- Bu kanıt banka onayı, arşiv verisinin erişilebilir olduğu veya mevzuat
  uyumluluğu sonucu değildir.

## Güvenli Geri Alma

25D servis çağrı yüzeyinden kaldırılabilir; gerçek arşiv adaptörü bulunmadığı için
yeni veri erişimi oluşmaz. Append-only talep, karar ve audit outbox kayıtları
silinmez veya yerinde değiştirilmez; onaylı talepler otomatik veri getirmez.

# İterasyon 25C — İdempotent İmha İşi ve Kanıt Zarfı

## Kontrol Durumu

- Teknik durum: `TechnicallyVerified`
- Uyum durumu: `ComplianceReviewRequired`
- Tarih: 2026-07-21
- Üretici rolü: Codex geliştirme ajanı
- Kontroller: `CTRL-KVKK-DEL-001`, `CTRL-BDDK-AUD-001`, `CTRL-BDDK-SOD-001`
- Gereksinimler: `BFR-LCM-002/003`, `BFR-AUD-004`, `BFR-SOD-002`, `FR-077`,
  `FR-079`, `NFR-SEC-001/008/011`, `NFR-CMP-001/003`

## Teknik Kanıt

- İmha işi yalnız opak onay referansına sahip `ApprovedByBank` katalog politikası,
  süresi dolmuş kayıt ve aktif legal hold bulunmaması durumunda hazırlanır.
  Varsayılan `ComplianceReviewRequired` katalog fail-closed kalır.
- Idempotency anahtarı ve kayıt/kapsam kimlikleri SHA-256 olarak saklanır. Aynı
  anahtar/payload tek iş döndürür; farklı payload aynı anahtarı kullanamaz.
- Hazırlama normal kullanıcı, sonuç yazımı servis hesabı rolüne ayrılmıştır. Her
  iki aktör güvenilir, geçerli, sürümlü context ve aynı veri kapsamına sahip
  olmalıdır; hazırlayan kimlik sonuç aktörü olamaz.
- Sonuç `SUCCEEDED` ile `FAILED_TECHNICAL` durumlarını ayırır; yalnız yöntem,
  sayaçlar, izinli teknik hata kodu ve opak kanıt referansı saklanır.
- İş ve terminal sonuç tabloları append-only'dir. Domain yazımı ile redakte audit
  outbox aynı transaction'dadır; audit-stage arızası domain yazımını geri alır.
- Audit özeti kayıt/kapsam kimliği, idempotency anahtarı, onay/kanıt referansı,
  ham silinen değer veya serbest hata metni içermez.

## Doğrulama

- Komut: `python3 -m pytest -q 06-Testler/01-Birim/test_retention.py 06-Testler/01-Birim/test_retention_legal_hold.py 06-Testler/01-Birim/test_retention_disposal_job.py`
- Sonuç: retention hedef grubunda 46 test geçti.
- Tam regresyon, mypy, Ruff, format, derleme, secret, SBOM, kanıt manifesti ve
  birleşik sürüm ön kontrol sonuçları iterasyon kapanışında doğrulandı.

## Sınırlar

- Servis fiziksel silme, anonimleştirme veya arşivleme adaptörü çağırmaz. Başarı
  sonucu yalnız güvenilir dış worker'ın sunduğu teknik kanıt zarfını kaydeder.
- Gerçek onay/kanıt resolver'ları, banka rol ve reason code eşlemesi, üretim
  PostgreSQL/WORM yetkileri, çoklu süreç claim/lease, yedek re-delete ve arşiv
  geri çağırma uygulanmamıştır.
- Bu kanıt banka onayı, fiziksel imhanın gerçekleştiği veya mevzuat uyumluluğu
  sonucu değildir.

## Güvenli Geri Alma

25C servis çağrı yüzeyinden kaldırılabilir ve gerçek adaptör bulunmadığı için yeni
fiziksel işlem oluşmaz. Append-only iş, sonuç ve audit outbox kayıtları silinmez
veya yerinde değiştirilmez; hazırlanmış işler üretim adaptörüne otomatik aktarılmaz.

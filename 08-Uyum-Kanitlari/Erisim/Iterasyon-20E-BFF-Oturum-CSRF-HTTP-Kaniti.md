---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-004
  - BFR-IAM-005
  - CTRL-BDDK-IAM-001
requirement_ids:
  - FR-005
  - FR-081
  - UC-001
  - NFR-SEC-007
  - NFR-SEC-009
  - AC-001
status: TechnicallyVerified
version: iteration-20e-local
executed_at: 2026-07-22
producer_role: Codex
---

# İterasyon 20E BFF Oturum ve CSRF HTTP Kanıtı

## Değişiklik

- İterasyon: 20E - BFF oturum ve CSRF HTTP sınırı
- Bileşenler: `veri_kalitesi.identity`, `veri_kalitesi.api`
- Test: `06-Testler/01-Birim/test_bff_session_api.py`
- Politika kararı: `OPEN-BNK-020`
- Banka onay referansı: `USER-DECLARATION-2026-07-22-OPEN-BNK-020`

## Doğrulama

```bash
python3 -m pytest -q
python3 -m mypy 03-Backend/src 06-Testler
python3 -m ruff check .
python3 -m ruff format --check 03-Backend/src 06-Testler
python3 -m compileall -q 03-Backend/src 06-Testler
git diff --check
PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc .

cd 04-Frontend/app
npm run typecheck
npm test
npm run build
```

- Tam depoda 1029 test geçti; iki gerçek PostgreSQL entegrasyon testi opt-in
  koşuluyla atlandı. Yeni BFF/CSRF hedefi 14 test içerir.
- Mypy 159 dosyada sıfır hata verdi. Ruff lint/format, `compileall`, diff,
  frontend type-check/test/build kontrolleri geçti.
- `28A-v1` secret taraması 455 kaynak dosyada sıfır bulguyla `CLEAN` döndü.
- Vite build'indeki mevcut 500 kB chunk uyarısı bu backend güvenlik diliminden
  bağımsız olarak sürmektedir.

## Güvenlik

- Cookie adı ve nitelikleri `__Host-session`, `Secure`, `HttpOnly`,
  `SameSite=Lax`, `Path=/` ve domainsiz olarak doğrulandı.
- CSRF token session credential'dan ayrı üretilir; kalıcı kayıtta yalnız iki
  ayrı SHA-256 özeti bulunur. Terminal geçiş iki özeti de siler.
- Durum değiştiren istek custom CSRF header, Origin, Referer, Fetch Metadata ve
  CORS allowlist kontrollerinden geçmeden domain işlemini çağırmaz.
- Eksik/değiştirilmiş cookie veya CSRF 401/403; session store arızası gizli
  teknik ayrıntı olmadan 503 üretir. Correlation ID ve no-store korunur.
- Aktör, rol ve source scope HTTP header'larından üretilmez. Dashboard resolver'ı
  yalnız session servisinin verdiği güvenilir context'i kullanır.
- Audit olayları cookie, session credential, CSRF token veya bunların açık
  değerlerini taşımaz.
- Maker-checker etkisi: Banka onaylı session politikası değiştirilmedi; yeni
  politika yönetim yazma yüzeyi açılmadı.

## Sınırlar

- Bu kanıt sentetik yerel SQLite/session ve FastAPI testidir; üretim uygunluğu
  veya mevzuat uyumluluğu sonucu değildir.
- Gerçek OIDC/SAML callback, issuer/audience/state/nonce/MFA assertion doğrulaması,
  banka grup-rol eşlemesi ve ayrıcalıklı/servis hesabı akışı uygulanmadı.
- HA session store, at-rest şifreleme/KMS-HSM, diğer merkezi iptal tetikleri ve
  fiziksel `P90D` saklama/imha kanıtı açık kalır.
- Geri alma: Yeni session kabulü durdurulur, aktif credential'lar merkezi olarak
  iptal edilir ve BFF resolver fail-closed `UnavailableActorContextResolver`a
  alınır. Migration mevcut session kaydını silmez; CSRF özeti bulunmayan eski
  oturumlar durum değiştiren isteklerde reddedilir.

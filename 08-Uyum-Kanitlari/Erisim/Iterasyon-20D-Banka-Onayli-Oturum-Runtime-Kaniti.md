---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
  - BFR-IAM-004
  - BFR-IAM-005
  - BFR-IAM-006
  - CTRL-BDDK-IAM-001
requirement_ids:
  - FR-001
  - FR-005
  - UC-001
  - NFR-SEC-005
  - NFR-SEC-009
  - AC-001
status: TechnicallyVerified
version: iteration-20d-local
executed_at: 2026-07-22
---

# İterasyon 20D Banka Onaylı Oturum Runtime Kanıtı

## Değişiklik

- İterasyon: 20D - onaylı süre, tek aktif oturum ve terminal credential silme
- Bileşen: `veri_kalitesi.identity`, `veri_kalitesi.audit`
- Politika kararı: `OPEN-BNK-020`
- Banka onay referansı: `USER-DECLARATION-2026-07-22-OPEN-BNK-020`

## Doğrulama

- Komut: `PYTHONPATH=03-Backend/src python3 -m pytest -q`
- Gerçekleşen: 993 test geçti; kimlik hedef grubu 47 testle geçti.
- `PYTHONPATH=03-Backend/src python3 -m mypy .`: PASS, 146 kaynak dosya.
- `python3 -m ruff check .`: PASS.
- `python3 -m ruff format --check .`: PASS, 146 dosya.
- `PYTHONPATH=03-Backend/src python3 -m compileall -q 03-Backend/src`: PASS.
- `PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc .`: CLEAN,
  `28A-v1`, 430 dosya, sıfır bulgu.
- `git diff --check`: PASS.

Sentetik test kapsamı; `PT1H` idle, `PT10H` mutlak süre, daha sıkı politika,
arka plan/token yenileme aktivitesi, aynı kullanıcı için ikinci giriş, logout,
timeout, değiştirilmiş credential, audit ve depo arızası yollarını içerir.

## Güvenlik

- Yeni başarılı giriş, aynı kullanıcıya ait önceki aktif oturumu ve credential
  özetini yeni kayıtla aynı SQLite transaction'ında iptal eder.
- Logout, timeout ve audit arızasıyla sonlanan oturum credential özeti saklamaz;
  yeniden kullanım genel `SESSION_NOT_FOUND` reddi üretir.
- Arka plan isteği ve token yenileme idle süresini uzatmaz. Aktivite türü güvenilir
  enum dışında kabul edilmez.
- Servis, üretim deposunun atomiklik sözleşmesini tanımlayan
  `SessionRepository` protokolüne bağlıdır; süreç belleği üretim alternatifi
  olarak eklenmemiştir.
- Audit allowlist'i credential, digest, açık session ID, kullanıcı rol/kapsam
  değerleri veya ham kişisel veri içermez.
- Maker-checker etkisi: Banka onaylı politika değeri bu dilimde değiştirilmez;
  politika yönetim HTTP yüzeyi yoktur.
- Geri alma: Yeni oturum kabulü durdurulmalı, aktif credential'lar merkezi olarak
  iptal edilmeli ve şema yedeği doğrulandıktan sonra önceki sürüme dönülmelidir.

## Sınırlar

Bu kanıt HTTP/BFF cookie ve CSRF uygulamasını, gerçek kurumsal IdP'yi, yüksek
erişilebilir üretim session store'unu, at-rest şifreleme/KMS-HSM bağlantısını,
diğer merkezi iptal tetiklerini veya `P90D` fiziksel saklama/imha kanıtını
doğrulamaz. Teknik uygulama kanıtı mevzuat uyumluluğu sonucu değildir.

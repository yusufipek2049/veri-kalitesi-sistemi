---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
  - BFR-IAM-004
  - BFR-IAM-006
  - CTRL-BDDK-IAM-001
requirement_ids:
  - FR-054
  - FR-055
  - FR-080
  - FR-081
  - FR-082
  - UC-010
status: TechnicallyVerified
version: iteration-21b-local
executed_at: 2026-07-22
---

# İterasyon 21B Güvenli Dashboard API Kanıtı

## Değişiklik

- `GET /api/v1/dashboard/summary`, mevcut yetki filtreli
  `DashboardQueryService` önünde FastAPI taşıma katmanı olarak eklendi.
- Aktör, rol ve source kapsamı HTTP header veya gövdeden alınmaz. Production
  session resolver bağlı değilse API sorgudan önce fail-closed 401 döndürür.
- Yerel aktör yalnız açık `development` ortamında güvenilir
  `ActorContextIssuer` ile ve sunucu üretimli correlation ID kullanılarak oluşturulur.
- Frontend API verisini mevcut ortak grafik/tablo view-model'ine dönüştürür;
  backend'in sağlamadığı alanları uydurmaz ve veri yok durumunu sıfırlaştırmaz.

## Doğrulama

- `python3 -m pytest -q`: PASS, 1015 test; iki opt-in PostgreSQL testi atlandı.
- `python3 -m mypy 03-Backend/src 06-Testler`: PASS, 157 dosya.
- `python3 -m ruff check .`: PASS.
- `python3 -m ruff format --check 03-Backend/src 06-Testler`: PASS.
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS.
- `npm test`: PASS, sekiz test.
- `npm run typecheck`: PASS.
- `npm run test:e2e`: PASS, yedi test ve beş zorunlu viewport.
- `npm run build` ve `npm run build-storybook`: PASS; Vite 500 kB bundle
  uyarısı sürmektedir.
- `28A-v1` secret taraması: CLEAN, 447 dosya, sıfır bulgu.
- CycloneDX SBOM yeniden üretim karşılaştırması: byte düzeyinde eşit,
  SHA-256 `9a2542f678cbb4bfafceb1c0b89b0e33b46361cf36b806fa14ea1ef9af3d9d86`.
- Yerel gerçek zincir: FastAPI `8000`, Vite `5174` üzerinde doğrulandı; API 30
  dönem ve yedi sentetik resmî gözlem döndürdü. `5173` kullanımda olduğu için
  görsel inceleme çakışmayan portta yapıldı.

## Negatif ve Veri-Minimum Kanıt

- Session resolver yokluğu repository çağrısı yapmadan 401 üretir.
- Doğrudan oluşturulmuş güvenilmeyen context repository çağrısı yapmadan 403
  üretir; kapsam veya nesne varlığı hata metninde açıklanmaz.
- Sahte `X-Actor-ID`, rol ve source header'ları geliştirme aktörünün yetkisini genişletmez.
- SQLite teknik hatasının ayrıntısı, SQL, stack trace ve olası hassas içerik 503
  Problem Details yanıtına taşınmaz.
- Correlation ID istemciden kabul edilmez; sunucuda üretilir ve hata/başarı
  yanıtında tutarlı taşınır.
- CORS wildcard kullanmaz; yalnız açık yerel frontend origin'i kabul edilir.
- Görsel iki iyileştirme turunda sağlanmayan KPI'lar `—` olarak ayrıldı; boş
  alarm eylemi ve var olmayan teknik seri legend'i kaldırıldı.

## Sınırlar

Bu kanıt gerçek OIDC/SAML IdP assertion'ını, `__Host-session` cookie'sini,
synchronizer-token CSRF'yi, yüksek erişilebilir session store'u, at-rest
şifreleme/KMS-HSM bağlantısını, PostgreSQL skor repository'sini veya üretim CORS
topolojisini doğrulamaz. Teknik uygulama kanıtı mevzuat uyumluluğu veya banka
pilot onayı değildir.

---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
  - BFR-IAM-004
  - BFR-IAM-006
  - CTRL-BDDK-IAM-001
requirement_ids:
  - FR-054
  - FR-056
  - UC-010
  - AC-030
  - AC-043
  - AC-045
status: TechnicallyVerified
version: iteration-21c-local
executed_at: 2026-07-22
---

# İterasyon 21C Dashboard Operasyonel Gösterge API Kanıtı

## Değişiklik

- Dashboard özet DTO'suna ölçüm yeterliliği, kritik kontrol veri
  kullanılabilirliği ve teknik hata özeti eklendi.
- Trend ve operasyonel göstergeler aynı güvenilir aktör kapsamı, tek yetkilendirme
  kararı ve tek repository okumasından üretilir.
- Aktif ölçüm yeterliliği politikası bulunmadığında olumlu yeterlilik sonucu
  üretilmez. Mevcut ölçümler `VALIDATION_REQUIRED`, teknik sonuçlar
  `TECHNICAL_FAILURE`, veri yokluğu `NO_DATA` olarak ayrılır.
- Kritik kural sonuç kaynağı henüz bulunmadığından API sıfır değer uydurmaz;
  `NOT_AVAILABLE` durumu ve boş sayaçlar döndürür.

## Doğrulama

- `python3 -m pytest -q`: PASS, 1031 test; iki opt-in PostgreSQL testi atlandı.
- `python3 -m mypy 03-Backend/src 06-Testler`: PASS, 159 dosya.
- `python3 -m ruff check .`: PASS.
- `python3 -m ruff format --check .`: PASS, 161 dosya.
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS.
- `npm test -- --run`: PASS, 13 test.
- `npm run typecheck`: PASS.
- `npm run build`: PASS; mevcut 500 kB Vite bundle uyarısı sürmektedir.
- `28A-v1` secret taraması: CLEAN, 465 dosya, sıfır bulgu.

## Negatif ve Veri-Minimum Kanıt

- Aktif yeterlilik politikası olmadan `QUALIFIED` sonucu üretilmez.
- Teknik hata skoru sıfıra çevrilmez; skor boş kalır ve teknik hata göstergesi
  ayrı sunulur.
- Kritik kontrol veri kaynağı yokken başarılı, başarısız veya toplam kontrol
  sayısı sıfır olarak gösterilmez.
- Yetkilendirilmiş kapsam dışında kalan kaynaklar teknik hata sayaçlarına veya
  trende katılmaz; mevcut yetkisiz erişim testlerinde repository çağrısı
  yapılmadan istek reddedilir.
- API yanıtı aktör, rol, kaynak kimliği listesi, SQL, stack trace, secret veya
  ham hassas veri içermez. Repository hatası ayrıntısız güvenli 503 yanıtına
  dönüştürülür.

## Sınırlar

Bu kanıt tam ölçüm yeterliliği politikasını, kapsam/güven hesaplamasını, kritik
kural sonuç runtime'ını, alarm kaynağını, gerçek OIDC/SAML IdP bağlantısını,
yüksek erişilebilir session store'u veya PostgreSQL skor repository'sini
doğrulamaz. Teknik doğrulama mevzuat uyumluluğu veya banka onayı değildir.

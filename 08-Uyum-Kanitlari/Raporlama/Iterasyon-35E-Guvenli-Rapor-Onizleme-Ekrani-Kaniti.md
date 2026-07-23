---
type: technical-evidence
status: TechnicallyVerified
control_ids:
  - FR-072
  - UC-015
  - AC-021
  - AC-023
  - NFR-SEC-001
  - NFR-PRV-002
  - NFR-PRV-003
  - NFR-USA-001
  - NFR-USA-003
  - NFR-USA-004
  - NFR-USA-005
  - NFR-USA-006
version: ITERATION_35E
date: 2026-07-23
producer_role: Codex
---

# İterasyon 35E Güvenli Rapor Önizleme Ekranı Kanıtı

## Kapsam

- Backend: rol/source scope filtreli `GET /api/v1/reports/summary` ve
  veri-minimum DTO.
- Frontend: `/reports` rotası, filtreli toplulaştırılmış skor önizlemesi.
- Veri: yalnız sentetik geliştirme skorları.

## Sonuç

- İstemci scope veya rol header'ları yetkiyi değiştirmez; kaynak kapsamı yalnız
  güvenilir `ActorContext` üzerinden çözülür.
- HTTP yüzeyi sabit son 30 UTC günü kullanır; servis rol, politika sürümü, 500
  kaynak ve en fazla 31 gün sınırını korur.
- DTO aktör/session, audit gerekçesi, ham kayıt, secret veya rapor dosyası
  içermez; yanıt `Cache-Control: no-store` taşır.
- Hesaplanan, resmî kısmi, veri yok ve teknik hata durumları korunur. Eksik veya
  teknik skor `0` yapılmaz; provizyonel kısmi sonuç repository tarafından
  rapor önizlemesine alınmaz.
- Yetkisiz rol reader çağrısından önce 403; teknik hata güvenli ve correlation
  ID içeren 503 üretir.
- 1054 pytest, 128 kaynak dosyalık mypy ve Ruff geçti. 52 Vitest ve 75
  Playwright testi geçti; beş viewport iki temada taşmasız doğrulandı.
- TypeScript, Vite ve Storybook build geçti.
- Production npm audit sıfır zafiyet, `28A-v1` taraması 524 dosyada sıfır
  secret bulgusu verdi.

## Görsel Doğrulama

1. Beş masaüstü viewport ve iki temada durum ayrımı, ikon ekseni, filtreler,
   klavye odağı ve yatay taşma incelendi.
2. Ölçüm alt metni “Son rapor gözlemi” olarak netleştirildi; 75 senaryolu tam
   Playwright paketi yeniden çalıştırıldı.

## Güvenlik ve Sınırlar

- Screenshot, fixture, log ve hata yüzeylerinde gerçek banka/müşteri verisi,
  secret, ham kayıt veya indirilebilir hassas dosya yoktur.
- Liste salt okunurdur; kaynak sistemine değiştirici çağrı yapmaz.
- Maker-checker etkisi yoktur; bu iterasyon rapor üretimi, indirme veya politika
  değişikliği içermez.
- PDF/XLSX/CSV, DLP/watermark, dosya saklama/arşiv/imha ve dışa aktarma
  maker-checker politikası `OPEN-BNK-014` ile açık kalır.
- Gerçek IdP, üretim session store, üretim repository ve banka marka onayı bu
  teknik kanıtın kapsamında değildir.
- Güvenli geri alma; yeni GET rotası ve istemci rotasının kaldırılmasıdır.
  Veritabanı migration'ı veya kaynak veri değişikliği yoktur.

---
type: technical-evidence
status: TechnicallyVerified
control_ids:
  - FR-077
  - FR-078
  - FR-079
  - UC-016
  - AC-026
  - NFR-SEC-001
  - NFR-SEC-005
  - NFR-SEC-008
  - NFR-SEC-011
  - NFR-CMP-001
  - NFR-CMP-002
  - NFR-CMP-003
  - NFR-USA-001
  - NFR-USA-003
  - NFR-USA-004
  - NFR-USA-005
  - NFR-USA-006
version: ITERATION_35F
date: 2026-07-23
producer_role: Codex
---

# İterasyon 35F Salt Okunur Denetim Ekranı Kanıtı

## Kapsam

- Backend: rol kontrollü `GET /api/v1/audit/events`, snapshot sayfalama ve
  veri-minimum DTO.
- Frontend: `/audit` rotası, filtreli olay listesi ve zincir bütünlüğü özeti.
- Veri: yalnız sentetik geliştirme audit olayları.

## Sonuç

- Yalnız güvenilir `AUDIT_VIEWER` aktör bağlamı sorgu yapabilir; çağıranın
  gönderdiği rol veya aktör header'ları yetkiyi değiştirmez.
- Sorgu en fazla 31 gün ve 100 kayıtla sınırlıdır. Aktör, işlem, nesne, sonuç
  ve correlation filtreleri repository sorgusuna parametreli uygulanır.
- Sayfalama ilk yanıttaki snapshot sıra sınırını korur; sonradan eklenen olaylar
  mevcut sayfa zincirine karışmaz.
- Yanıt eski/yeni değer özeti, hash alanları, session özeti, secret veya ham
  hassas veri içermez ve `Cache-Control: no-store` taşır.
- Zincir bütünlüğü görüntüleme öncesi doğrulanır; görüntüleme olayı ayrıca
  veri-minimum audit kaydı üretir.
- Yetkisiz rol repository sorgusundan önce 403; doğrulama hatası güvenli 400,
  teknik hata güvenli ve correlation ID içeren 503 üretir.
- 1060 pytest, 128 kaynak dosyalık mypy, Ruff ve `compileall` geçti. 59 Vitest
  ve 87 Playwright testi geçti; beş viewport iki temada taşmasız doğrulandı.
- TypeScript, Vite ve Storybook build geçti. Production npm audit sıfır
  zafiyet, `28A-v1` taraması 534 dosyada sıfır secret bulgusu verdi.

## Görsel Doğrulama

1. Beş masaüstü viewport ve iki temada durum ayrımı, ikon ekseni, filtreler,
   klavye odağı, yetkisiz veri ifşası ve yatay taşma incelendi.
2. Olay zamanı dar görünümde korundu; bütünlük kartı başarı/hata tonuyla
   belirginleştirildi ve 87 senaryolu tam Playwright paketi yeniden çalıştırıldı.

## Güvenlik ve Sınırlar

- Screenshot, fixture, log ve hata yüzeylerinde gerçek banka/müşteri verisi,
  secret, eski/yeni değer özeti veya hash zinciri alanı yoktur.
- Liste salt okunurdur; kaynak sistemine veya audit kayıtlarına değiştirici
  çağrı yapmaz.
- Maker-checker etkisi yoktur; audit ve erişim politikası değişikliği yapılmaz.
- Banka auditor rol/grup eşlemesi, istemci bilgisi alanı, 31 günü aşan arşiv
  raporu ve hassas dışa aktarma `OPEN-BNK-002/008/014` kapsamında açık kalır.
- Gerçek IdP, üretim session store, üretim repository ve banka marka onayı bu
  teknik kanıtın kapsamında değildir.
- Güvenli geri alma; yeni GET rotası ve istemci rotasının kaldırılmasıdır.
  Veritabanı migration'ı veya kaynak veri değişikliği yoktur.

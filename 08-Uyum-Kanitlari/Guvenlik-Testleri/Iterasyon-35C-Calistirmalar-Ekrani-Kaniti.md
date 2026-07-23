---
type: technical-evidence
status: TechnicallyVerified
control_ids:
  - FR-043
  - FR-044
  - NFR-USA-001
  - NFR-USA-003
  - NFR-USA-004
  - NFR-USA-005
  - NFR-USA-006
version: ITERATION_35C
date: 2026-07-23
producer_role: Codex
---

# İterasyon 35C Çalıştırmalar Ekranı Kanıtı

## Kapsam

- Backend: kaynak scope filtreli `GET /api/v1/executions` ve veri-minimum DTO.
- Frontend: `/executions` rotası, filtreli salt okunur çalışma envanteri.
- Veri: yalnız sentetik geliştirme çalıştırmaları.

## Sonuç

- Bir çalışma yalnız tüm kaynakları güvenilir aktör kapsamındaysa görünür.
  Kapsamsız eski kayıtlar ve izinli/izinsiz kaynakları birlikte içeren kayıtlar
  fail-closed dışlanır; istemci aktör/rol/scope header'ları yetkiyi değiştirmez.
- DTO kural/kaynak listeleri, tetikleyen veya iptal eden kullanıcı, iptal
  gerekçesi, hash ve ham hata ayrıntısı içermez.
- `QUEUED`, `RUNNING`, `SUCCESS`, `PARTIAL`, `TECHNICAL_ERROR`, `TIMEOUT`,
  `CANCEL_REQUESTED` ve `CANCELLED` durumları birbirine veya sıfır skora
  dönüştürülmeden ayrı sunulur.
- Boş kapsam boş liste; güvenilmeyen bağlam 403; depo hatası teknik ayrıntı
  taşımayan ve correlation ID içeren 503 üretir.
- 1046 pytest, 164 dosyalık mypy, Ruff/format/compileall; 40 Vitest ve 51
  Playwright testi geçti. Beş viewport iki temada taşmasız doğrulandı.
- Vite ve Storybook build geçti; production npm audit sıfır zafiyet raporladı.

## Görsel Doğrulama

1. Yetkili kaynak kapsamı görünür salt okunur filtreye dönüştürüldü; orta
   genişlikte iki, geniş masaüstünde beş kolonlu filtre düzeni doğrulandı.
2. Masaüstü kolon başlıkları ve ortak ikon yuvası ile satırların taranabilirliği
   ve dikey ekseni iyileştirildi.

## Güvenlik ve Sınırlar

- Screenshot, fixture, log ve hata yüzeylerinde gerçek banka/müşteri verisi,
  secret, ham sorgu veya stack trace yoktur.
- Liste salt okunurdur; kaynak sistemine DDL/DML veya değiştirici çağrı yapmaz.
- Maker-checker etkisi yoktur; bu iterasyon çalıştırma başlatma, yeniden deneme,
  iptal veya zamanlama işlemi içermez.
- Gerçek IdP, üretim session store, üretim repository ve banka marka onayı bu
  teknik kanıtın kapsamında değildir.
- Güvenli geri alma; yeni GET rotası ve istemci rotasının kaldırılmasıdır.
  Veritabanı migration'ı veya kaynak veri değişikliği yoktur.

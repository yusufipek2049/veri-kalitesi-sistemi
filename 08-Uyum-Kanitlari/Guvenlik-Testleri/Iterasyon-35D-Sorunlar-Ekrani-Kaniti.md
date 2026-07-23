---
type: technical-evidence
status: TechnicallyVerified
control_ids:
  - FR-064
  - FR-066
  - FR-070
  - NFR-SEC-001
  - NFR-USA-001
  - NFR-USA-003
  - NFR-USA-004
  - NFR-USA-005
  - NFR-USA-006
version: ITERATION_35D
date: 2026-07-23
producer_role: Codex
---

# İterasyon 35D Sorunlar Ekranı Kanıtı

## Kapsam

- Backend: kaynak/dataset scope filtreli `GET /api/v1/issues` ve veri-minimum DTO.
- Frontend: `/issues` rotası, filtreli salt okunur sorun envanteri.
- Veri: yalnız sentetik geliştirme sorunları.

## Sonuç

- SOURCE sorunu yalnız izinli kaynak, DATASET sorunu yalnız izinli dataset
  kapsamındaysa görünür; istemci aktör/rol/scope header'ları yetkiyi değiştirmez.
- DTO kaynak olay kimliği, atanan kullanıcı, deduplication özeti, kök neden,
  düzeltici faaliyet, yorum, kanıt veya ServiceNow hata ayrıntısı içermez.
- Sekiz yaşam döngüsü durumu ve dört öncelik korunur; teknik olay kalite
  başarısızlığıyla birleştirilmez.
- Boş kapsam boş liste; güvenilmeyen bağlam 403; depo hatası teknik ayrıntı
  taşımayan ve correlation ID içeren 503 üretir.
- 1051 pytest, 166 dosyalık mypy, Ruff/format/compileall; 46 Vitest ve 63
  Playwright testi geçti. Beş viewport iki temada taşmasız doğrulandı.
- Vite ve Storybook build geçti; production npm audit sıfır zafiyet raporladı.

## Görsel Doğrulama

1. 1024 piksel filtre düzeni üç kolona alındı ve kapsam metni kısaltıldı.
2. Kolon başlıklarının gizlendiği görünümde durum ve öncelik alan adları
   rozetlerin üzerinde gösterildi.

## Güvenlik ve Sınırlar

- Screenshot, fixture, log ve hata yüzeylerinde gerçek banka/müşteri verisi,
  secret, çözüm metni, yorum veya stack trace yoktur.
- Liste salt okunurdur; kaynak sistemine veya ServiceNow'a değiştirici çağrı
  yapmaz.
- Maker-checker etkisi yoktur; bu iterasyon atama, çözüm, doğrulama veya kapatma
  işlemi içermez.
- Gerçek IdP, üretim session store, üretim repository ve banka marka onayı bu
  teknik kanıtın kapsamında değildir.
- Güvenli geri alma; yeni GET rotası ve istemci rotasının kaldırılmasıdır.
  Veritabanı migration'ı veya kaynak veri değişikliği yoktur.

---
iteration: 36B1
status: TechnicallyVerified
completed_at: 2026-07-23
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36B1 — Atanmış Sorunu İncelemeye Alma

## Amaç

Sorunlar ekranındaki ilk güvenli yazma akışını açmak: güvenilir aktörün yetkili
kapsamda kendisine atanmış sorunu, BFF/CSRF ve optimistic locking sınırlarını
koruyarak incelemeye alabilmesi.

## Gereksinim ve Karar Bağlantıları

- `FR-066`
- `FR-070`
- `UC-013`
- `UI-WRITE-001`
- `UI-WRITE-002`
- `NFR-SEC-001`
- `NFR-SEC-005`
- `NFR-SEC-008`
- `NFR-SEC-011`
- `NFR-USA-001–006`

## Kabul Kriterleri

| Kriter | Sonuç |
| --- | --- |
| Eylem yalnız yetkili satırda gösterilir. | Karşılandı; backend yalnız kapsam içindeki, aktöre atanmış `ASSIGNED` sorun için `START_INVESTIGATION` yayımlar. |
| Mutasyon güvenilir aktör ve CSRF sınırından geçer. | Karşılandı; state-changing boundary aktör bağlamını üretir, CSRF kanıtı yoksa servis çağrılmaz. |
| Eski sürüm sessizce üzerine yazılmaz. | Karşılandı; istek sayısal `version` taşır, PostgreSQL koşullu güncellemesi çakışmada `409 Conflict` döndürür. |
| Başarılı işlem durumu ve geçmişi atomik günceller. | Karşılandı; mevcut PostgreSQL issue transaction/audit outbox sınırı kullanılır ve sürüm artırılır. |
| Hata yolları veri-minimumdur. | Karşılandı; `403/404/409/503` Problem Details yanıtları secret, token ve ham hassas veri içermez. |
| Arayüz bekleme ve sonuç durumunu erişilebilir gösterir. | Karşılandı; satır düğmesi işlem sırasında kapanır, başarı/hata mesajı canlı bölgeyle duyurulur. |
| Tarayıcıda hassas kalıcı taslak oluşmaz. | Karşılandı; CSRF kanıtı yalnız modül belleğinde tutulur, local/session storage kullanılmaz. |
| Görsel düzen iki temada ve zorunlu viewport'larda doğrulanır. | Karşılandı; beş viewport, açık/koyu tema ve iki görsel iyileştirme turu Playwright ile doğrulandı. |

## Görsel Doğrulama Turları

1. İlk turda E2E sözleşme fixture'larında yeni `version` ve
   `availableActions` alanlarının eksik olduğu görüldü; tüm fixture'lar gerçek
   API sözleşmesine getirildi.
2. İkinci turda 1024 px koyu tema görselinde eylem düğmesinin öncelik alanına
   yaklaştığı görüldü. Orta genişlik ızgarası kimlik/öncelik ve durum/eylem
   bölgelerine ayrıldı; tekrar üretilen görselde çakışma kalmadı.

## Güvenlik ve Veri Etkisi

- Kaynak sistemlere yazma yapılmaz; yalnız uygulamanın issue kaydı değişir.
- Üretim state-changing çağrısı güvenilir BFF/session sınırı olmadan açılmaz.
- Yerel geliştirme adaptörü sentetik veriyle sınırlıdır ve üretim kalıcılığı
  iddiası değildir.
- Yetkisiz aktör, servis hesabı, kapsam dışı kayıt, eksik CSRF ve eski sürüm
  negatifleri test edilmiştir.
- Audit başarısızlığı mevcut atomik PostgreSQL transaction sınırında işlemi
  fail-closed bırakır.

## Çalıştırılan Kontroller

- Hedefli issue/API birim testleri: `112 passed`
- Gerçek PostgreSQL issue mutasyon testleri: `2 passed`
- Tam pytest: `1081 passed, 2 skipped`
- Frontend Vitest: `62 passed`
- Playwright: `88 passed`
- TypeScript typecheck, production build ve Storybook build: başarılı
- Mypy: 133 kaynak dosyada sıfır hata
- Ruff lint ve format: temiz; 179 dosya biçimli
- `compileall`: temiz
- `npm audit --audit-level=high`: sıfır bulgu
- `28A-v1`: 553 kaynak dosyada sıfır secret bulgusu
- `git diff --check`: temiz

Kalan iki pytest atlaması ayrı sentetik PostgreSQL opt-in profiline aittir.
Vite ve Storybook build'lerinde 500 kB üzeri chunk uyarısı devam eder; build
başarısını engellemez ve bu iterasyonun davranış kapsamını etkilemez.

## Kalan Kapsam

Sıradaki ürün artımı `36B2` güvenilir yeniden atamadır. Çözüm, farklı aktörle
doğrulama, kapatma ve yeniden açma daha sonraki küçük 36B dilimlerinde
uygulanacaktır. Gerçek IdP callback/session store kurulmadan yerel geliştirme
aktörü üretim kimlik kanıtı olarak kullanılamaz.

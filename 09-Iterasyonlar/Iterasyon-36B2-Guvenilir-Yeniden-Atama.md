---
iteration: 36B2
status: TechnicallyVerified
completed_at: 2026-07-23
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36B2 — Güvenilir Yeniden Atama

## Amaç

Yetkili kullanıcının kapsamındaki açık sorunu, güvenilir aday kaynağı ve
PostgreSQL optimistic locking sınırlarını koruyarak başka bir aktif ve kapsam
içi kullanıcıya atayabilmesini sağlamak.

## Gereksinim ve Karar Bağlantıları

- `FR-065`
- `FR-070`
- `UC-013`
- `UI-WRITE-001`
- `UI-WRITE-002`
- `UI-WRITE-003`
- `NFR-SEC-001`
- `NFR-SEC-005`
- `NFR-SEC-007`
- `NFR-SEC-008`
- `NFR-SEC-011`
- `NFR-USA-001–006`

## Kabul Kriterleri

| Kriter | Sonuç |
| --- | --- |
| Yeniden atama yalnız backend tarafından yetkilendirilen satırda sunulur. | Karşılandı; backend yalnız kapsam içindeki `ASSIGNED` veya `INVESTIGATING` sorunlarda ve yetkili normal kullanıcıda `REASSIGN` eylemi yayımlar. |
| Adaylar güvenilir kaynaktan ve veri-minimum biçimde gelir. | Karşılandı; seçenek yanıtı yalnız UUID ve görünen ad taşır, `no-store` ile döner; domain servisi hedef kullanıcının aktiflik ve kapsamını yeniden doğrular. |
| Mutasyon güvenilir aktör ve CSRF sınırından geçer. | Karşılandı; state-changing BFF sınırı aktör bağlamını üretir ve CSRF kanıtı yoksa servis çağrılmaz. |
| Eski sürüm sessizce üzerine yazılmaz. | Karşılandı; istek sayısal `version` taşır, PostgreSQL koşullu güncellemesi çakışmada `409 Conflict` döndürür ve hiçbir issue/geçmiş/audit yazımı yapmaz. |
| Başarılı atama ve denetim izi atomiktir. | Karşılandı; issue, kronolojik geçmiş ve redakte audit outbox aynı PostgreSQL transaction'ında yazılır. |
| Bildirim hatası kalite başarısızlığı olarak sunulmaz. | Karşılandı; kayıt korunur ve bildirim gecikmesi veri-minimum teknik `503` yanıtıyla ayrı sınıflandırılır. |
| Arayüz açık kaydetme ve kaydedilmemiş değişiklik koruması sağlar. | Karşılandı; aday/öncelik penceresinde açık “Kaydet” eylemi, bekleme durumu ve kirli formdan çıkışta onay uyarısı vardır. |
| Tarayıcıda hassas kalıcı taslak oluşmaz. | Karşılandı; form ve CSRF kanıtı local/session storage'a yazılmaz. |
| Görsel düzen iki temada ve zorunlu viewport'larda doğrulanır. | Karşılandı; beş viewport, açık/koyu tema ve iki görsel iyileştirme turu Playwright ile doğrulandı. |

## Görsel Doğrulama Turları

1. İlk turda aynı satırda birden fazla metin düğmesinin taramayı zorlaştırdığı
   görüldü. Satır eylemleri erişilebilir üç nokta menüsünde toplandı ve yeniden
   atama penceresi sabit, taşmayan bir genişlikte doğrulandı.
2. İkinci turda atamanın durum/geçmiş etkisi ve aday bulunmayan durum görünür
   değildi. Pencereye etki açıklaması ve ayrı boş aday durumu eklendi; yeniden
   üretilen zorunlu viewport görsellerinde çakışma kalmadı.

## Güvenlik ve Veri Etkisi

- Kaynak sistemlere yazma yapılmaz; yalnız uygulamanın issue kaydı değişir.
- Üretim state-changing çağrısı güvenilir BFF/session sınırı olmadan açılmaz.
- Yerel geliştirme adayları yalnız sentetik UUID ve görünen adlardan oluşur;
  gerçek dizin veya üretim kimlik kanıtı değildir.
- Yetkisiz/ayrıcalıklı aktör, kapsam dışı kayıt, pasif veya kapsam dışı aday,
  eksik CSRF ve eski sürüm negatifleri test edilmiştir.
- Audit başarısızlığı mevcut atomik PostgreSQL transaction sınırında işlemi
  fail-closed bırakır.
- Yanıt, log, geçmiş ve audit içinde secret, oturum belirteci veya ham hassas
  kayıt bulunmaz.

## Çalıştırılan Kontroller

- Hedefli issue/API birim testleri: `117 passed`
- Gerçek PostgreSQL issue mutasyon testleri: `2 passed`
- Tam pytest: `1086 passed, 2 skipped`
- Frontend Vitest: `67 passed`
- Playwright: `89 passed`
- TypeScript typecheck, production build ve Storybook build: başarılı
- Mypy: 133 kaynak dosyada sıfır hata
- Ruff lint ve format: temiz; 179 dosya biçimli
- `compileall`: temiz
- `npm audit --omit=dev --audit-level=high`: sıfır bulgu
- `28A-v1`: 555 kaynak dosyada sıfır secret bulgusu
- `git diff --check`: temiz

Kalan iki pytest atlaması ayrı sentetik PostgreSQL opt-in profiline aittir.
Vite ve Storybook build'lerinde 500 kB üzeri chunk uyarısı devam eder; build
başarısını engellemez ve bu iterasyonun davranış kapsamını etkilemez.

## Kalan Kapsam

Sıradaki ürün artımı `36B3` korumalı çözüm kaydıdır. Farklı aktörle doğrulama,
kapatma ve yeniden açma daha sonraki küçük 36B dilimlerinde uygulanacaktır.
Gerçek IdP callback/session store ve üretim kullanıcı dizini kurulmadan yerel
geliştirme aktörü/adayı üretim kimlik kanıtı olarak kullanılamaz.

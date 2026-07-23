---
iteration: 36B3
status: TechnicallyVerified
completed_at: 2026-07-23
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36B3 — Korumalı Çözüm Kaydı

## Amaç

Kendisine atanmış ve incelenen bir sorunun kök neden, düzeltici faaliyet,
kanıt referansı ve tamamlanma zamanı ile; koruma, yetki, optimistic locking ve
atomik audit sınırlarını koruyarak çözülebilmesini sağlamak.

## Gereksinim ve Karar Bağlantıları

- `FR-068`
- `FR-070`
- `UC-014`
- `UI-WRITE-001`
- `UI-WRITE-002`
- `UI-WRITE-003`
- `NFR-SEC-001`
- `NFR-SEC-005`
- `NFR-SEC-008`
- `NFR-SEC-011`
- `NFR-USA-001–006`

## Kabul Kriterleri

| Kriter | Sonuç |
| --- | --- |
| Çözüm eylemi yalnız kapsam içindeki, atanmış ve uygun durumdaki sorunda sunulur. | Karşılandı; backend yalnız `INVESTIGATING` veya `WAITING_FOR_RESOLUTION` durumundaki atanmış sorunda `RESOLVE` eylemi verir. |
| Kök neden, düzeltici faaliyet, kanıt ve tamamlanma zamanı zorunludur. | Karşılandı; API ve form boş alanı, geçersiz kanıt UUID'sini ve gelecekteki tamamlanma zamanını reddeder. |
| Hassas çözüm alanları güvenilir koruma servisinden geçer. | Karşılandı; domain servisi kalıcı yazımdan önce `IssueResolutionProtector` kullanır. |
| Mutasyon güvenilir aktör ve CSRF sınırından geçer. | Karşılandı; BFF aktör bağlamını üretir, state-changing istek CSRF doğrulamasından geçmeden servis çağrılmaz. |
| Eski sürüm sessizce üzerine yazılmaz. | Karşılandı; beklenen `version` API'den domain ve repository'ye taşınır; çakışma hiçbir issue/çözüm/geçmiş/audit yazımı yapmadan `409 Conflict` döndürür. |
| Sorun, çözüm, geçmiş ve denetim izi atomiktir. | Karşılandı; PostgreSQL repository ve transactional audit outbox aynı transaction sınırında çalışır. |
| Arayüz açık kaydetme ve kaydedilmemiş değişiklik koruması sağlar. | Karşılandı; çözüm formu açık “Kaydet” eylemi, bekleme durumu ve tüm alanlar için çıkış uyarısı içerir. |
| Hassas taslak tarayıcı kalıcı depolamasına yazılmaz. | Karşılandı; çözüm alanları ile CSRF kanıtı yalnız bellek içinde tutulur. |
| Görsel düzen zorunlu viewport'larda doğrulanır. | Karşılandı; issue Playwright matrisi ve çözüm akışı 90 senaryoluk tam koşuda geçti. |

## Görsel Doğrulama Turları

1. İlk turda kanıt alanının isteğe bağlı görünmesi ve hatalı referansın yalnız
   API aşamasında anlaşılması giderildi. Kanıt UUID'si zorunlu yapıldı ve
   erişilebilir satır içi doğrulama eklendi.
2. İkinci turda güvenli kanıt referansı açıklaması, tüm çözüm alanlarını kapsayan
   kaydedilmemiş değişiklik koruması ve tamamlanma zamanı doğrulaması eklendi.
   Hazır ve hatalı durum ekranlarında taşma veya çakışma görülmedi.

## Güvenlik ve Veri Etkisi

- Kaynak sisteme yazılmaz; yalnız uygulamanın issue yaşam döngüsü değişir.
- Yetkisiz, kapsam dışı, yanlış atanmış, eski sürümlü ve eksik CSRF istekleri
  fail-closed sonuçlanır.
- Çözüm metni koruma servisine uğramadan kalıcılaştırılmaz.
- Audit olayı veri-minimumdur; çözüm metni, secret ve oturum belirteci içermez.
- Audit/outbox yazılamazsa issue mutasyonu tamamlanmaz.

## Çalıştırılan Kontroller

- Hedefli issue/API testleri: `127 passed`
- Gerçek PostgreSQL issue mutasyon testleri: `2 passed`
- Tam pytest: `1096 passed, 2 skipped`
- Frontend Vitest: `70 passed`
- Playwright: `90 passed`
- TypeScript production build ve Storybook build: başarılı
- Mypy: 133 kaynak dosyada sıfır hata
- Ruff lint ve format: temiz; 183 dosya biçimli
- `compileall`: temiz
- `npm audit --omit=dev --audit-level=high`: sıfır bulgu
- `28A-v1`: 555 kaynak dosyada sıfır secret bulgusu
- `git diff --check`: temiz

Kalan iki pytest atlaması ayrı sentetik PostgreSQL opt-in profiline aittir.
Vite ve Storybook build'lerindeki mevcut 500 kB üzeri chunk uyarısı build
başarısını engellemez ve bu iterasyonun davranış kapsamını etkilemez.

## Kalan Kapsam

Sıradaki ürün artımı `36B4` farklı aktörle doğrulamadır. Kapatma ve yeniden açma
daha sonraki küçük 36B dilimlerindedir. Gerçek IdP callback/session store
tamamlanmadan yerel geliştirme aktörü üretim kimlik kanıtı değildir.

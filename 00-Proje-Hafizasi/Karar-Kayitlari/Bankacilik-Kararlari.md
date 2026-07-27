---
type: canonical-decision-register
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-24
---

# Bankacılık Karar Kayıtları

Bu belge teknik yönü kesinleşmiş `OPEN-BNK-*` kayıtlarını tutar. Hâlâ açık veya inceleme gerektiren kayıtların tek kaynağı `../Acik-Konular.md` dosyasıdır.

> Tam tarihsel kaynak: [Arşivlenmiş karar günlüğü](../../docs/archive/project-memory-2026-07-24/Alinan-Kararlar.md).

## Bankacılık Geçiş Teknik Yön Kararları

Bu kayıtların teknik yönü seçilmiştir. `KararAlındı` durumu banka kurulu,
hukuk, uyum, IAM, bilgi güvenliği veya iç kontrol onayının tamamlandığı anlamına
gelmez; kalan onay ve ürün ayrıntıları sonuç sütununda korunur.

| ID | Alınan karar | Durum | Kalan onay veya uygulama bağımlılığı |
| --- | --- | --- | --- |
| OPEN-BNK-003 | Tüm kullanıcılar için IdP MFA; PAM, süreli ayrıcalık ve çift onaylı break-glass modeli | `KararAlındı` | Ürün ve banka rol eşlemeleri |
| OPEN-BNK-004 | Risk bazlı maker-checker kapsamı ve görevler ayrılığı | `KararAlındı` | Banka onaylı maker/checker rol kodları ve tam kritik işlem matrisi |
| OPEN-BNK-005 | Kritik işlemde fail-closed, düşük riskli işlemde durable-buffer | `KararAlındı` | Üretim kuyruk/outbox, kapasite ve alarm ayrıntıları |
| OPEN-BNK-006 | Kurumsal WORM/imza/hash doğrulamalı audit deposu | `KararAlındı` | Kurumsal ürün ve iç denetim onayı |
| OPEN-BNK-007 | Eşlenmeyen sınıflandırmada fail-closed davranış | `KararAlındı` | Banka sözlüğü ve müşteri/banka sırrı kod eşlemesi |
| OPEN-BNK-010 | SIEM entegrasyonu ve 72 saatlik ihlal değerlendirme akışı | `KararAlındı` | Ürün, olay sözlüğü, alarm seviyesi ve SOC eskalasyon eşlemesi |
| OPEN-BNK-012 | Pilot VM; üretimde kurumsal konteyner platformu, yüksek erişilebilir PostgreSQL, broker ve secret manager yönü | `KararAlındı` | Kurumsal ürün adları ve altyapı kurul onayı |
| OPEN-BNK-014 | Asenkron dışa aktarma, gerekçe, maker-checker, DLP, watermark ve süreli indirme modeli | `ApprovedByBank` | Karar kesinleşti. 36G kapsamında uygulanacak; eksik kontrolde fail-closed. |
| OPEN-BNK-015 | `ActorContext` yalnız güvenilir identity/session adaptöründen üretilecek | `KararAlındı` | Issuer sahipliği ve session assertion doğrulaması |
| OPEN-BNK-016 | PostgreSQL transactional outbox ve ayrı publisher worker | `KararAlındı` | Şifreleme, sahiplik, replay ve operasyon prosedürü |
| OPEN-BNK-017 | Onay hedefi 3 iş günü, otomatik sona erme 10 iş günü | `KararAlındı` | Banka iş takvimi ve rol sahibi onayı |
| OPEN-BNK-020 | BFF üzerinde opak server-side session; 1 saat hareketsizlik, 10 saat mutlak süre, tek aktif oturum, `__Host-session` cookie, synchronizer-token CSRF, merkezi iptal ve 90 günlük güvenlik metadatası | `ApprovedByBank` | Gerçek IdP callback/state/nonce, üretim deposu, şifreleme/KMS-HSM ve 90 günlük fiziksel saklama uygulama kanıtı |
| OPEN-BNK-021 | Kısmi çalışma yalnız onaylı dataset politikasındaki tüm koşulları sağlarsa resmî skora girebilir; aksi halde `PROVISIONAL` olur ve resmî skor/SLA/trend/raporlamadan dışlanır | `KararAlındı` | Üretim eşikleri ve banka onaylı politika kayıtları ayrı açık bağımlılıktır |

## 2026-07-22 — OPEN-BNK-020 Banka Onaylı Normal Kullanıcı Oturum Politikası

Durum: `ApprovedByBank`

Onay referansı: `USER-DECLARATION-2026-07-22-OPEN-BNK-020`

- Kullanıcı başına en fazla bir aktif normal oturum bulunur. Yeni başarılı giriş
  önceki oturumu iptal eder; mevcut oturum yeni girişi engellemez.
- Boşta kalma süresi `PT1H`, mutlak süre `PT10H`'dir. Arka plan istekleri idle
  süresini, token yenileme mutlak süreyi uzatmaz. Süre sonunda yeniden kimlik
  doğrulama zorunludur.
- Mimari BFF'tir. Access ve refresh token'ları yalnız sunucu tarafında tutulur;
  tarayıcı bu token'lara erişemez ve yalnız opak oturum cookie'si taşır.
- Cookie adı `__Host-session`; nitelikleri `Secure`, `HttpOnly`,
  `SameSite=Lax`, `Path=/` ve `Domain` kullanılmaması şeklindedir. Cookie girişte
  ve ayrıcalık değişikliğinde döndürülür.
- State-changing isteklerde synchronizer token custom header ile zorunludur.
  Origin, Referer, Fetch Metadata ve CORS allowlist doğrulanır; `GET` ile durum
  değişikliği yasaktır.
- Üretim deposu kurum onaylı yüksek erişilebilir merkezi depodur; bu hizmet yoksa
  PostgreSQL kullanılır. Süreç belleği üretimde kullanılamaz. Session ID özeti
  saklanır, aktarım TLS ile, at-rest şifreleme ve anahtar yönetimi kurum onaylı
  KMS veya HSM ile sağlanır.
- Logout, idle/mutlak timeout, yeni başarılı giriş, kullanıcının pasifleştirilmesi,
  kritik rol değişikliği, güvenlik olayı ve IdP oturum iptali merkezi iptal
  tetikleridir. Reddedilen credential yeniden kullanılamaz.
- Oturum sırrı sonlandırmada derhal geçersizleştirilir ve silinir. Access/refresh
  token arşivlenmez. Veri-minimum güvenlik metadatası `P90D` saklanır; legal hold
  süreyi uzatabilir ve imha kanıtı zorunludur.
- Politika sürümlüdür. Limit/süre, cookie-token-CSRF, depo/şifreleme ve
  saklama-imha değişiklikleri tanımlı IAM, Bilgi Güvenliği, Mimari, Altyapı,
  Hukuk ve Uyum/İç Kontrol sahiplerinin onayını gerektirir. Acil değişiklik
  yalnız Bilgi Güvenliği tarafından süreli yapılabilir ve sonradan incelemeye
  tabidir.

Üretim session store teknolojisinin kurulması, şifreleme ve anahtar yönetimi,
`P90D` fiziksel saklama/imha uygulaması ve uygulanabilir düzenleme kanıtı karar
değil uygulama ve uygunluk kanıtı olarak izlenir.

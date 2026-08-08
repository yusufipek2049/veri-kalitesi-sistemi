# Audit Bütünlüğü

## Mevcut Durum

- `veri_kalitesi.audit` paketi sürümlü `AuditEvent`, allowlist tabanlı `AuditRedactor` ve SQLite prototipinde append-only SHA-256 hash zinciri sağlar.
- Auditli domain yazımları redakte olayı iş kaydıyla aynı transaction içindeki outbox'a yazar; merkezi zincire teslim idempotenttir.
- Aktif uygulama kodunda legacy audit yazımı kalmamıştır. Eski SQLite `audit_records` tablosu yalnız salt okunur envanter ve aktarım kaynağıdır.
- `LegacyAuditMigrator`, desteklenen olayları güncel redaksiyon politikasından geçirerek deterministik olay kimliği ve correlation özetiyle merkezi zincire ekler. Tekrar çalıştırma çift olay üretmez.
- Bozuk JSON, desteklenmeyen eylem ve naive zaman damgası veri kalitesi sorunu olarak özetlenir; merkezi depo hatası teknik hata olarak ayrılır. Raporlar ham kayıt kimliği yerine özet taşır.
- Kaynak kayıtlar güncellenmez veya silinmez. Üretim ortamı envanteri ve gerçek aktarım ayrı operasyon/onay çalışmasıdır.

## Hedef Sınır

`veri_kalitesi.audit` paketi:

- `AuditEvent`
- `AuditSink`
- `AuditRedactor`
- `AuditIntegrityProvider`
- `AuditFailurePolicy`
- `AuditQueryService`

## Olay Zarfı

- event_id
- event_version
- occurred_at_utc
- actor_id / actor_type
- session_id
- correlation_id
- action
- object_type / object_id
- result
- reason_code
- old_value_digest
- new_value_digest
- redacted_fields
- previous_event_hash
- event_hash

## Hata Politikası

Kimlik/rol/yetki ve güvenlik politikası değişiklikleri; kural, eşik ve ağırlık onayları; kritik yapılandırma; hassas erişim kararı ile saklama/imha politikası değişikliği fail-closed'dur. Audit olayı veya kalıcı outbox kaydı aynı işlem sınırında oluşturulamazsa iş işlemi tamamlanmış sayılmaz.

Rutin çalıştırma ve operasyon olayları dayanıklı kuyruk veya transactional outbox üzerinden yazılabilir. Audit altyapısı kesintisinde olay kaybolmaz; olay sırası ve correlation kimliği korunur; retry yapılır; süre/kapasite aşımı alarm üretir ve kuyruk taşması sessiz veri kaybına yol açmaz. Bu ayrım kullanılabilirlik hedefini kritik güvenlik işlemlerini gevşetmeden korur.

## Tarihsel Aktarım ve Zincir Sırası

- Legacy kayıtlar `created_at` ve `audit_id` sırasıyla okunur; kaynak bağlantısında yalnız `PRAGMA` ve `SELECT` kullanılır.
- Tarihsel `occurred_at` değeri olayda korunur. Olay hash'i mevcut merkezi zincirin sonuna eklenme sırasını temsil eder; olay zamanı ile zincir sırasının aynı olması beklenmez.
- Desteklenmeyen veya doğrulanamayan kayıtlar sessizce dönüştürülmez. Kontrollü sorun raporu sonrasında manuel değerlendirme gerekir.

## Açık Üretim Konuları

- Outbox publisher worker'ı, retry/backoff, claim ve alarm metrikleri.
- WORM, dijital imza, SIEM ve harici güven kökü kararı.
- Üretim legacy veri envanteri, yedek/geri dönüş planı ve onaylı aktarım koşusu.
- `FR-078` audit sorgulama ve dışa aktarma yüzeyi.

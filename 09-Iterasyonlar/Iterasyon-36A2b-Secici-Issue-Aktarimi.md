---
iteration: 36A2b
status: TechnicallyVerified
completed_at: 2026-07-23
decision_reference: USER-DECLARATION-2026-07-23-PG-MIG-004-FORWARD-ONLY-OTHERS-RECOMMENDED
---

# İterasyon 36A2b — Seçici Issue Aktarımı ve SQLite Kaldırma

## Amaç

Legacy SQLite issue kayıtlarını PostgreSQL'e salt okunur ve idempotent taşımak,
bütünlüğü doğrulamak ve ürün paketindeki SQLite issue runtime yolunu kaldırmak.

## Gereksinim ve Karar Bağlantıları

- `FR-064–FR-070`
- `UC-011`, `UC-013`, `UC-014`
- `NFR-REL-005`, `NFR-REL-006`
- `NFR-SEC-005`, `NFR-SEC-008`, `NFR-SEC-011`
- `PG-MIG-001–005`

## Kabul Kriterleri

| Kriter | Sonuç |
| --- | --- |
| Otoriter issue kayıtları seçici taşınır. | Karşılandı; ana kayıt, geçmiş, çözüm, doğrulama, ilişki ve yalnız bekleyen issue audit outbox olayları taşınır. |
| Kaynak salt okunur kalır. | Karşılandı; `mode=ro`, `query_only` ve aktarım öncesi/commit öncesi dosya SHA-256 kontrolü uygulanır. |
| Aktarım idempotenttir. | Karşılandı; ilk gerçek PostgreSQL çalışması sekiz, ikinci çalışma sıfır yeni satır üretti. |
| Sayaç, hash ve foreign key bütünlüğü doğrulanır. | Karşılandı; tablo bazlı kanonik hash ve sayaç eşleşmesi ile beş foreign key orphan sorgusu fail-closed çalışır. |
| Hedef uyuşmazlığı sessizce kabul edilmez. | Karşılandı; mevcut hedef payload farkı `IssueMigrationError` ile transaction'ı geri alır. |
| SQLite issue runtime yolu kaldırılır. | Karşılandı; ürün repository dosyası ve package export'u kaldırıldı. |
| Secret depoya veya loga yazılmaz. | Karşılandı; bağlantı yalnız test alt sürecinin ortamında tutuldu. |

## Güvenlik ve Veri Etkisi

- Kaynak sistemlere yazma yapılmaz.
- Ham issue içeriği log veya rapora yazılmaz; rapor yalnız sayaç ve hash taşır.
- Issue dışı veya daha önce yayımlanmış audit outbox kayıtları kapsam dışıdır.
- Teknik aktarım hatası veri kalitesi başarısızlığı olarak sınıflandırılmaz.
- Bu teknik doğrulama banka uyum veya üretim geçiş onayı değildir.

## Çalıştırılan Kontroller

- Hedefli Ruff lint ve format
- Hedefli mypy
- Issue/API birim testleri: `103 passed`
- Gerçek PostgreSQL issue entegrasyon testleri: `5 passed`
- Tam pytest: `1072 passed, 2 skipped`
- Mypy: 133 kaynak dosyada sıfır hata
- Ruff lint ve format: temiz; 183 dosya biçimli
- `compileall`: temiz
- `28A-v1`: 553 dosyada sıfır secret bulgusu
- `git diff --check`: temiz

Kalan iki atlama yalnız ayrı `SYNTHETIC_POSTGRES_TEST` opt-in profiline aittir;
36A2b ve diğer issue PostgreSQL testleri gerçek veritabanında çalışmıştır.

## Kalan Kapsam

Diğer domainlerin SQLite repository'leri bağımlılık sırasıyla PostgreSQL'e
taşınacaktır. Sıradaki ürün artımı `36B`; mevcut PostgreSQL issue yaşam döngüsünü
güvenilir aktör, BFF/CSRF, rol/scope ve optimistic locking ile yazılabilir
Sorunlar ekranına bağlayacaktır.

---
iteration: 36A2a
status: TechnicallyVerified
completed_at: 2026-07-23
decision_reference: USER-DECLARATION-2026-07-23-PG-MIG-004-FORWARD-ONLY-OTHERS-RECOMMENDED
---

# İterasyon 36A2a — PostgreSQL Issue Mutasyon ve Audit

## Amaç

Issue yaşam döngüsü yazımlarını, değişmez geçmişi ve redakte audit outbox
olaylarını tek PostgreSQL transaction sınırına taşımak.

## Gereksinim ve Karar Bağlantıları

- `FR-064–FR-070`
- `UC-011`, `UC-013`, `UC-014`
- `NFR-REL-005`, `NFR-REL-006`
- `NFR-SEC-005`, `NFR-SEC-008`, `NFR-SEC-011`
- `PG-MIG-002`, `PG-MIG-003`, `PG-MIG-005`

## Kabul Sonuçları

| Kabul ölçütü | Sonuç |
| --- | --- |
| Issue oluşturma ve tekrar PostgreSQL'de idempotent çalışır. | Karşılandı; deduplication özeti advisory transaction lock ile serileştirilir. |
| Atama, durum, çözüm ve doğrulama geçmişi korunur. | Karşılandı; tüm yaşam döngüsü yazımları ve kronolojik geçmiş gerçek PostgreSQL'de doğrulandı. |
| Kritik yazım audit olmadan tamamlanmaz. | Karşılandı; issue/history/outbox aynı transaction'dadır, audit PK çatışması tüm yazımı geri alır. |
| Teknik hata kalite başarısızlığına çevrilmez. | Karşılandı; SQLAlchemy hataları mevcut redakte `IssueTechnicalError` yoluna bağlandı. |
| SQLite fallback kullanılmaz. | PostgreSQL repository yolu için karşılandı. Eski SQLite repository fiziksel olarak `36A2b` sonuna kadar compatibility/aktarım kaynağıdır. |
| Secret depoya veya loga yazılmaz. | Karşılandı; konteyner secret'ı yalnız test alt sürecinin ortamında kullanıldı. |

## Çalıştırılan Kontroller

- Gerçek `data_quality` PostgreSQL üzerinde üç issue migration/mutasyon testi
- `pytest -q`: `1070 passed, 2 skipped`
- `mypy 03-Backend/src`: 133 kaynak dosyada sıfır hata
- `ruff check .`
- `ruff format --check .`
- `python3 -m compileall -q 03-Backend/src`
- `28A-v1`: 550 dosyada sıfır secret bulgusu
- `git diff --check`

Kalan iki atlama farklı sentetik PostgreSQL test profilinin ayrı opt-in
bayrağına aittir; issue PostgreSQL testleri canlı çalışmıştır.

## Güvenlik ve Veri Etkisi

- Test verileri yalnız sentetik UUID ve veri-minimum metinlerden oluşur.
- Kaynak sistemlere yazma eklenmedi.
- Audit payload'ı mevcut redaksiyon politikasından geçer.
- Bu artım üretim uygunluğu veya banka mevzuat onayı değildir.

## Kalan Kapsam

`36A2b`; otoriter SQLite issue/geçmiş/çözüm/doğrulama/ilişki ve bekleyen outbox
kayıtlarını salt okunur/idempotent aktaracak, sayaç/hash/foreign key bütünlüğünü
doğrulayacak ve issue domainindeki SQLite repository/export yolunu kaldıracaktır.

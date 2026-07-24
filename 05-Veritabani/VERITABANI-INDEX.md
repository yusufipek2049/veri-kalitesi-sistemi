---
type: implementation-index
area: database
project: Veri Kalitesi İzleme ve Skorlama Sistemi
updated_at: 2026-07-24
---

# Veritabanı ve Veri Modeli Haritası

## Kanonik Kaynaklar

- [Genel Model, Saklama ve ER Diyagramı](../01-SRS/07-Veri-Modeli/Veri-Modeli-Genel.md)
- [Kimlik ve Yetki Varlıkları](../01-SRS/07-Veri-Modeli/Kimlik-ve-Yetki-Varliklari.md)
- [Kaynak ve Metadata Varlıkları](../01-SRS/07-Veri-Modeli/Kaynak-ve-Metadata-Varliklari.md)
- [Kural ve Çalıştırma Varlıkları](../01-SRS/07-Veri-Modeli/Kural-ve-Calistirma-Varliklari.md)
- [Sorun, Bildirim ve Audit Varlıkları](../01-SRS/07-Veri-Modeli/Sorun-Bildirim-ve-Audit-Varliklari.md)
- [Kanıt ve Karar Desteği Varlıkları](../01-SRS/07-Veri-Modeli/Kanit-ve-Karar-Destegi-Varliklari.md)
- [SQLite Kalıcılık Envanteri](SQLite-Kaliclilik-Envanteri.md)

## PostgreSQL Geçiş Durumu

| Domain | Alembic migration | PostgreSQL repository | Runtime/cutover durumu |
| --- | --- | --- | --- |
| Sorun yönetimi | `20260723_01_issue_baseline.py` | Var | Issue runtime yolu PostgreSQL-only olarak belgelenmiş; seçici SQLite aktarımı ve test desteği var. |
| Kural yönetimi | `20260723_02_rule_baseline.py` | Var | API/service sözleşmesi mevcut; teknik geçiş tamamlanmış olarak kaydedilmiş. |
| Veri kaynakları | `20260724_03_data_source_baseline.py` | Var | API/service sözleşmesi mevcut; teknik geçiş tamamlanmış olarak kaydedilmiş. |
| Çalıştırmalar | `20260724_04_execution_baseline.py` | Var | Repository ve testler mevcut; `PostgreSQLExecutionStartService`/`PostgreSQLExecutionCancelService` adaptörleri ile üretim cutover'ı tamamlandı. `create_development_app(session_factory=...)` ile PostgreSQL kullanılabilir. |

Migration/repository varlığı, uygulamanın gerçek production wiring'inin taşındığı
anlamına gelmez. Her domain için composition root, transaction sınırı, retry,
operasyon ve rollback/ileri düzeltme kanıtı ayrıca doğrulanır.

## Değişmez İlkeler

- Üretim uygulama kalıcılığı `postgresql+psycopg` ve SQLAlchemy 2 transaction
  sınırı üzerinden hedeflenir; bağlantı sırrı repository'ye yazılmaz.
- Uygulama veritabanı/şema doğrulaması yapılır; migration yalnız ileri gider,
  hata yeni düzeltici migration ile giderilir.
- Kaynak sistemlere erişim salt okunurdur.
- Audit/outbox ile kritik domain yazımı aynı transaction'da commit veya rollback
  olur; audit üretilemezse bağlayıcı kritik işlem fail-closed sonuçlanır.
- Optimistic locking sayısal sürüm alanı ile yapılır; çakışma sessizce ezilmez.
- Secret yalnız opak referansla tutulur; ham kişisel/hassas veri gereksiz yere
  kopyalanmaz.
- Saklama, imha, legal hold, bölümleme, WORM ve arşiv süreleri onaysız uydurulmaz.

## SQLite Statüsü

SQLite geçmiş iterasyonlarda yerel teknik prototip ve bazı domain test double'ı
olarak kullanılmıştır. `SQLite-Kaliclilik-Envanteri.md` kalan yolları bulmak için
kanıttır; üretim hedefi değildir. PostgreSQL'e taşınan domainde SQLite
compatibility/fallback bırakılmamalıdır. Çalıştırma domainindeki kalan export ve
test kullanımları açık uyumsuzluk olarak izlenir.

## İzlenebilirlik

- [İterasyon 36](../09-Iterasyonlar/Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md)
- [Backend İndeksi](../03-Backend/BACKEND-INDEX.md)
- [Test İndeksi](../06-Testler/TEST-INDEX.md)
- [Açık Konular](../00-Proje-Hafizasi/Acik-Konular.md)

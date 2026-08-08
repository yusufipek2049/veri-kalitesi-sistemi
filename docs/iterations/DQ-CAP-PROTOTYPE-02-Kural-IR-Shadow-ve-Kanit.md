---
type: iteration-closeout
status: PrototypeVerified
updated_at: 2026-07-30
work_package: DQ-CAP-PROTOTYPE-02
predecessor: DQ-CAP-PROTOTYPE-01
---

# DQ-CAP-PROTOTYPE-02 — Kural IR, SHADOW ve Veri-Minimum Kanıt

## Kapsam ve Sonuç

Mevcut `rules/executions/issues` mimarisi genişletildi; rakip modül
oluşturulmadı.

- Hazır no-code şablonlar ve güvenli özel SQL `DQ_RULE_IR_V1` içinde kaynak,
  kapsam ve `DQ_VIOLATION_EVIDENCE_V1` sözleşmesiyle birleşti.
- `COLUMN`, `ROW`, `DATASET`, `CROSS_TABLE`, `REFERENCE`, `RECONCILIATION` ve
  `TIME_SERIES` kapsamları kontrollü enum olarak modellendi. Özel SQL için
  kapsam, pozitif timeout/kota ve güvenli query reference zorunludur; bind
  değerleri reddedilir.
- `OFFICIAL/SHADOW` yürütme modu kural yaşam döngüsü statüsünden ayrıldı.
  SHADOW sonuçları resmî skor, bildirim, SLA ve otomatik issue kapılarından
  dışlanır; API ve frontend çalıştırma görünümünde `SHADOW` etiketi taşır.
- Sonuç kanıtı yalnız allowlist sayaç haritaları, doğrulanabilir SHA-256/HMAC
  fingerprint, açık key-id taşıyan sabit biçimli HMAC örnek referansı,
  `query-template://` query reference ve `plan://` plan reference taşır.
  Referans path'leri bounded opaque karakterlerle sınırlıdır; serbest metin,
  bilinmeyen alan, SQL/bind/secret payload'ı ve ham örnek fail-closed reddedilir.
- `20260730_12` migration'ı ve PostgreSQL/SQLite repository eşleri yürütme
  modu, downstream uygunluk kapıları ve JSON kanıtı kalıcılaştırır. Kritik
  execution+job başlangıcı mevcut ortak transaction audit/outbox sınırını
  korur.
- Kurallar görünümü IR sürümü/kaynağı/kapsamını; çalıştırmalar görünümü SHADOW
  modunu açıkça gösterir.

## Hedefli Doğrulama

- Güncel controller birim paketi exit `0` tamamlandı.
- Güncel controller PostgreSQL entegrasyon hedefleri skip olmadan exit `0`
  tamamlandı.

## Sınır

Bu kapanış sentetik/yerel prototip kanıtıdır. Production ölçek/yük,
kurumsal politika kalibrasyonu/onayı, gerçek hassas kayıt istisna akışı ve
kurumsal entegrasyon kanıtı üretmez; `ApprovedByBank` veya production-ready
iddiası değildir.

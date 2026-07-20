---
type: implementation-index
area: database
project: Veri Kalitesi İzleme ve Skorlama Sistemi
generated_at: 2026-07-16
tags:
  - database
  - index
---

# Veritabanı ve Veri Modeli Haritası

- [Genel Model, Saklama ve ER Diyagramı](../01-SRS/07-Veri-Modeli/Veri-Modeli-Genel.md)
- [Kimlik ve Yetki Varlıkları](../01-SRS/07-Veri-Modeli/Kimlik-ve-Yetki-Varliklari.md)
- [Kaynak ve Metadata Varlıkları](../01-SRS/07-Veri-Modeli/Kaynak-ve-Metadata-Varliklari.md)
- [Kural ve Çalıştırma Varlıkları](../01-SRS/07-Veri-Modeli/Kural-ve-Calistirma-Varliklari.md)
- [Sorun, Bildirim ve Audit Varlıkları](../01-SRS/07-Veri-Modeli/Sorun-Bildirim-ve-Audit-Varliklari.md)

## Tasarım İlkeleri

- Tarihsel sonuçlar kural sürümüne bağlı kalmalı.
- Kaynak bağlantı sırları veritabanında açık metin tutulmamalı.
- Audit kayıtları değişmezlik / bütünlük mekanizmasıyla korunmalı.
- Beş yıllık geçmiş için bölümleme, arşiv katmanı ve özet tablolar değerlendirilmeli.
- Ham kişisel veri kalıcı depoya gereksiz yere kopyalanmamalı.

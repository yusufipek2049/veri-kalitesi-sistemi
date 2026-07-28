# Veri Kalitesi İzleme ve Skorlama Sistemi

Kurum içinde çalışan, kurumsal IdP/LDAP yetkilendirmesi kullanan ve kaynak
sistemlere salt okunur erişen veri kalitesi izleme/skorlama sistemi deposudur.
Uygulamanın sahip olduğu metadata, politika, iş akışı, sonuç ve audit kayıtları
güvenilir sınırlar içinde yazılabilir; kaynak üretim verisi değiştirilemez.

## Başlangıç

1. [Dokümantasyon İndeksi](DOCUMENTATION_INDEX.md)
2. [Mevcut Durum](00-Proje-Hafizasi/Mevcut-Durum.md)
3. [Sıradaki Tek Çalışma Paketi](NEXT_STEP.md)
4. [Aktif Backlog](00-Proje-Hafizasi/Sonraki-Adimlar.md)
5. [Aktif Son Yedi İterasyon](09-Iterasyonlar/ITERASYON-INDEX.md)
6. [Ajan Kuralları](AGENTS.md)

## Güncel Teknik Özet

- Issue domaini PostgreSQL-only yola taşınmış; seçici SQLite aktarımı ve güvenilir
  yazılabilir yaşam döngüsü akışları uygulanmıştır.
- Kapatma/yeniden açma davranışı ve `36B5` kapanış kanıtı
  `TechnicallyVerified` olarak kaydedilmiştir.
- `36E` execution PostgreSQL cutover, `36F` scheduling/policy PostgreSQL
  kalıcılığı ve `36G` güvenli rapor üretimi/indirme teknik olarak
  doğrulanmıştır.
- [Kalıcı iş kuyruğu ve worker dayanıklılığı](NEXT_STEP.md), süreç kaybı
  toparlama, lease/heartbeat ve dead-letter sınırlarını kapatacak tek sıradaki
  çalışma paketidir.
- Üretim hazır değildir; kurumsal IdP, PAM/secret, HA veri/session, broker,
  SIEM/WORM, ServiceNow, DR ve banka onayları ayrıdır.

## Kanonik Kaynaklar

| Alan | Kaynak |
| --- | --- |
| Gereksinimler/kabul | [SRS](01-SRS/SRS-INDEX.md) |
| Mimari kararlar | [ADR](02-Mimari/Mimari-Kararlar.md) |
| Kesinleşmiş diğer kararlar | [Karar indeksi](00-Proje-Hafizasi/Alinan-Kararlar.md) |
| Açık kararlar | [Açık konular](00-Proje-Hafizasi/Acik-Konular.md) |
| Uygulama/test/operasyon | [Dokümantasyon indeksi](DOCUMENTATION_INDEX.md) |
| Tarihsel iterasyonlar | [Arşiv indeksi](archive/iterations/README.md) |

Son belgelenmiş tam test sayıları tarihsel kanıttır; güncel sonuç yerine
kullanılmaz. Ayrıntı: [Dokümantasyon Denetimi](DOCUMENTATION_AUDIT.md).

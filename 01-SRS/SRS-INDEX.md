---
type: srs-index
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_version: "0.1"
created_at: 2026-07-16
tags:
  - srs
  - index
  - rag
---

# SRS Yönlendirme İndeksi

Bu dosya ajanın bütün SRS'yi okumadan doğru bağlamı seçmesi için hazırlanmıştır.

## Temel Bölümler

- [Doküman Künyesi](00-Dokuman-Kunyesi.md)
- [Amaç ve Kapsam](01-Amac-ve-Kapsam.md)
- [Genel Sistem Açıklaması](02-Sistem-Aciklamasi.md)
- [İş Gereksinimleri](03-Is-Gereksinimleri.md)
- [Fonksiyonel Gereksinimler](04-Fonksiyonel-Gereksinimler/INDEX.md)
- [Kullanım Senaryoları](05-Kullanim-Senaryolari/INDEX.md)
- [İş Kuralları](06-Is-Kurallari.md)
- [Veri Modeli](07-Veri-Modeli/Veri-Modeli-Genel.md)
- [Harici Arayüzler](08-Harici-Arayuzler.md)
- [Fonksiyonel Olmayan Gereksinimler](09-Fonksiyonel-Olmayan-Gereksinimler/INDEX.md)
- [Kabul Kriterleri](10-Kabul-Kriterleri.md)
- [İzlenebilirlik Matrisi](11-Izlenebilirlik-Matrisi.md)
- [MVP ve Önceliklendirme](12-MVP.md)
- [Riskler](13-Riskler.md)
- [Sistem Evrimi](14-Sistem-Evrimi.md)
- [Açık Konular](15-Acik-Konular.md)
- [Kalite Kontrolü](16-Kalite-Kontrolu.md)
- [Bankacılık Uyum Kontrol Modülü](17-Bankacilik-Uyum/INDEX.md)

## Göreve Göre Yönlendirme

| Görev | Öncelikle okunacak notlar |
| --- | --- |
| Giriş, LDAP, rol ve izin | [04.01-Kullanici-ve-Yetki](04-Fonksiyonel-Gereksinimler/04.01-Kullanici-ve-Yetki.md), [09.05-Guvenlik](09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md), [Kimlik-ve-Yetki-Varliklari](07-Veri-Modeli/Kimlik-ve-Yetki-Varliklari.md), [UC-001-Sisteme-giris-yapilmasi](05-Kullanim-Senaryolari/UC-001-Sisteme-giris-yapilmasi.md) |
| Veri kaynağı bağlantısı | [04.02-Veri-Kaynagi-Yonetimi](04-Fonksiyonel-Gereksinimler/04.02-Veri-Kaynagi-Yonetimi.md), [Kaynak-ve-Metadata-Varliklari](07-Veri-Modeli/Kaynak-ve-Metadata-Varliklari.md), UC-002 ve UC-003 |
| Profilleme | [04.03-Metadata-ve-Profilleme](04-Fonksiyonel-Gereksinimler/04.03-Metadata-ve-Profilleme.md), [09.01-Performans](09-Fonksiyonel-Olmayan-Gereksinimler/09.01-Performans.md), UC-004 |
| Kural tasarımı | [04.04-Kural-Yonetimi](04-Fonksiyonel-Gereksinimler/04.04-Kural-Yonetimi.md), [06-Is-Kurallari](06-Is-Kurallari.md), UC-005 ve UC-006 |
| Scheduler / worker | [04.05-Calistirma-ve-Zamanlama](04-Fonksiyonel-Gereksinimler/04.05-Calistirma-ve-Zamanlama.md), [09.04-Guvenilirlik-ve-Hata-Toleransi](09-Fonksiyonel-Olmayan-Gereksinimler/09.04-Guvenilirlik-ve-Hata-Toleransi.md), UC-007 ve UC-008 |
| Skorlama | [04.06-Skorlama ve DQ-SCR karar kaydı](04-Fonksiyonel-Gereksinimler/04.06-Skorlama.md), [Kanonik skorlama ve ölçüm yeterliliği tasarımı](../02-Mimari/Veri-Kalitesi-Skorlama-ve-Olcum-Yeterliligi.md), [06-Is-Kurallari](06-Is-Kurallari.md), [Kural-ve-Calistirma-Varliklari](07-Veri-Modeli/Kural-ve-Calistirma-Varliklari.md), [UC-009](05-Kullanim-Senaryolari/UC-009-Veri-kalite-skorunun-hesaplanmasi.md), [AC-027–AC-047](10-Kabul-Kriterleri.md) |
| Dashboard | [04.07-Dashboard](04-Fonksiyonel-Gereksinimler/04.07-Dashboard.md), [09.07-Kullanici-Deneyimi](09-Fonksiyonel-Olmayan-Gereksinimler/09.07-Kullanici-Deneyimi.md), UC-010 |
| Bildirim ve issue | [04.08-Bildirim](04-Fonksiyonel-Gereksinimler/04.08-Bildirim.md), [04.09-Sorun-Yonetimi](04-Fonksiyonel-Gereksinimler/04.09-Sorun-Yonetimi.md), [Sorun-Bildirim-ve-Audit-Varliklari](07-Veri-Modeli/Sorun-Bildirim-ve-Audit-Varliklari.md), UC-011–UC-014 |
| Raporlama | [04.10-Raporlama](04-Fonksiyonel-Gereksinimler/04.10-Raporlama.md), [08-Harici-Arayuzler](08-Harici-Arayuzler.md), UC-015 |
| Audit | [04.11-Audit](04-Fonksiyonel-Gereksinimler/04.11-Audit.md), [09.05-Guvenlik](09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md), UC-016 |
| API / ServiceNow | [04.12-API-ve-Entegrasyon](04-Fonksiyonel-Gereksinimler/04.12-API-ve-Entegrasyon.md), [08-Harici-Arayuzler](08-Harici-Arayuzler.md), [15-Acik-Konular](15-Acik-Konular.md), [17.07-Ucuncu-Taraf-ve-ServiceNow](17-Bankacilik-Uyum/17.07-Ucuncu-Taraf-ve-ServiceNow.md) |
| Sentetik veri ve test verisi | [04.13-Sentetik-Veri](04-Fonksiyonel-Gereksinimler/04.13-Sentetik-Veri.md), [UC-017](05-Kullanim-Senaryolari/UC-017-Sentetik-veri-uretimi-ve-dogrulamasi.md), [Sentetik Veri ve Gizlilik Stratejisi](../02-Mimari/Sentetik-Veri-ve-Gizlilik-Stratejisi.md), [09.06-Gizlilik-ve-KVKK](09-Fonksiyonel-Olmayan-Gereksinimler/09.06-Gizlilik-ve-KVKK.md) |
| Kanıta dayalı kullanım kararı, etki, lineage, öneri, remediation ve chaos | [04.14-Kanita-Dayali-Karar-Destegi](04-Fonksiyonel-Gereksinimler/04.14-Kanita-Dayali-Karar-Destegi.md), [UC-018–UC-021](05-Kullanim-Senaryolari/INDEX.md), [Kanonik Karar Sistemi](../02-Mimari/Kanita-Dayali-Karar-Sistemi.md), [Kanıt ve Karar Desteği Varlıkları](07-Veri-Modeli/Kanit-ve-Karar-Destegi-Varliklari.md), [OPEN-026–OPEN-036 karar kaydı](../00-Proje-Hafizasi/Alinan-Kararlar.md) |
| Bankacılık güven sınırı / BDDK / KVKK | [INDEX](17-Bankacilik-Uyum/INDEX.md), [Bankacilik-Gecis-Durumu](../00-Proje-Hafizasi/Bankacilik-Gecis-Durumu.md), [INDEX](../02-Mimari/Guvenlik/INDEX.md) |

## Context Bütçesi

- Önce bu indeks.
- Sonra bir fonksiyonel modül.
- Ardından en fazla bir kullanım senaryosu, bir veri modeli grubu ve bir NFR dosyası.
- Kapsamlı izlenebilirlik denetimi dışında aynı anda bütün klasörleri okuma.

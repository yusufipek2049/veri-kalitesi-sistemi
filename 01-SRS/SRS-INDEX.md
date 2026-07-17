---
type: srs-index
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_version: "0.1"
generated_at: 2026-07-16
tags:
  - srs
  - index
  - rag
---

# SRS Yönlendirme İndeksi

Bu dosya ajanın bütün SRS'yi okumadan doğru bağlamı seçmesi için hazırlanmıştır.

## Temel Bölümler

- [[01-SRS/00-Dokuman-Kunyesi|Doküman Künyesi]]
- [[01-SRS/01-Amac-ve-Kapsam|Amaç ve Kapsam]]
- [[01-SRS/02-Sistem-Aciklamasi|Genel Sistem Açıklaması]]
- [[01-SRS/03-Is-Gereksinimleri|İş Gereksinimleri]]
- [[01-SRS/04-Fonksiyonel-Gereksinimler/INDEX|Fonksiyonel Gereksinimler]]
- [[01-SRS/05-Kullanim-Senaryolari/INDEX|Kullanım Senaryoları]]
- [[01-SRS/06-Is-Kurallari|İş Kuralları]]
- [[01-SRS/07-Veri-Modeli/Veri-Modeli-Genel|Veri Modeli]]
- [[01-SRS/08-Harici-Arayuzler|Harici Arayüzler]]
- [[01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/INDEX|Fonksiyonel Olmayan Gereksinimler]]
- [[01-SRS/10-Kabul-Kriterleri|Kabul Kriterleri]]
- [[01-SRS/11-Izlenebilirlik-Matrisi|İzlenebilirlik Matrisi]]
- [[01-SRS/12-MVP|MVP ve Önceliklendirme]]
- [[01-SRS/13-Riskler|Riskler]]
- [[01-SRS/14-Sistem-Evrimi|Sistem Evrimi]]
- [[01-SRS/15-Acik-Konular|Açık Konular]]
- [[01-SRS/16-Kalite-Kontrolu|Kalite Kontrolü]]
- [[01-SRS/17-Bankacilik-Uyum/INDEX|Bankacılık Uyum Kontrol Modülü]]

## Göreve Göre Yönlendirme

| Görev | Öncelikle okunacak notlar |
| --- | --- |
| Giriş, LDAP, rol ve izin | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.01-Kullanici-ve-Yetki]], [[01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik]], [[01-SRS/07-Veri-Modeli/Kimlik-ve-Yetki-Varliklari]], [[01-SRS/05-Kullanim-Senaryolari/UC-001-Sisteme-giris-yapilmasi]] |
| Veri kaynağı bağlantısı | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.02-Veri-Kaynagi-Yonetimi]], [[01-SRS/07-Veri-Modeli/Kaynak-ve-Metadata-Varliklari]], UC-002 ve UC-003 |
| Profilleme | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.03-Metadata-ve-Profilleme]], [[01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.01-Performans]], UC-004 |
| Kural tasarımı | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.04-Kural-Yonetimi]], [[01-SRS/06-Is-Kurallari]], UC-005 ve UC-006 |
| Scheduler / worker | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.05-Calistirma-ve-Zamanlama]], [[01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.04-Guvenilirlik-ve-Hata-Toleransi]], UC-007 ve UC-008 |
| Skorlama | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.06-Skorlama]], [[01-SRS/06-Is-Kurallari]], [[01-SRS/07-Veri-Modeli/Kural-ve-Calistirma-Varliklari]], UC-009 |
| Dashboard | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.07-Dashboard]], [[01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.07-Kullanici-Deneyimi]], UC-010 |
| Bildirim ve issue | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.08-Bildirim]], [[01-SRS/04-Fonksiyonel-Gereksinimler/04.09-Sorun-Yonetimi]], [[01-SRS/07-Veri-Modeli/Sorun-Bildirim-ve-Audit-Varliklari]], UC-011–UC-014 |
| Raporlama | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.10-Raporlama]], [[01-SRS/08-Harici-Arayuzler]], UC-015 |
| Audit | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.11-Audit]], [[01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik]], UC-016 |
| API / ServiceNow | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.12-API-ve-Entegrasyon]], [[01-SRS/08-Harici-Arayuzler]], [[01-SRS/15-Acik-Konular]], [[01-SRS/17-Bankacilik-Uyum/17.07-Ucuncu-Taraf-ve-ServiceNow]] |
| Bankacılık güven sınırı / BDDK / KVKK | [[01-SRS/17-Bankacilik-Uyum/INDEX]], [[00-Proje-Hafizasi/Bankacilik-Gecis-Durumu]], [[02-Mimari/Guvenlik/INDEX]] |

## Context Bütçesi

- Önce bu indeks.
- Sonra bir fonksiyonel modül.
- Ardından en fazla bir kullanım senaryosu, bir veri modeli grubu ve bir NFR dosyası.
- Kapsamlı izlenebilirlik denetimi dışında aynı anda bütün klasörleri okuma.

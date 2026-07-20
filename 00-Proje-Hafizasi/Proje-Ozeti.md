---
type: project-memory
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
generated_at: 2026-07-16
tags:
  - proje
  - hafiza
  - ozet
---

# Proje Özeti

## Amaç

Kurum genelindeki veri kaynaklarının merkezi biçimde tanımlanması; veri kümelerinin profillenmesi; veri kalitesi kurallarının yönetilip çalıştırılması; kalite skorlarının hesaplanması; sorunların sahiplerine atanması ve denetlenebilir geçmişin saklanması.

## Temel Kalite Boyutları

Tamlık, doğruluk, geçerlilik, tutarlılık, benzersizlik, güncellik ve bütünlük.

## Uçtan Uca Döngü

`Kaynağı tanımla → profille → kuralı oluştur/test et → çalıştır → skorla → dashboardda göster → bildir → issue oluştur → audit et`

## Temel Sistem Özellikleri

- PostgreSQL, SQL Server, Oracle, MySQL, CSV, Excel ve REST API kaynakları.
- LDAP kimlik doğrulama ve RBAC.
- Manuel ve zamanlanmış kural çalıştırma.
- Kural, boyut, veri kümesi, veri kaynağı ve kurum seviyesinde skor.
- Dashboard, sistem içi bildirim, raporlama ve ServiceNow entegrasyon hedefi.
- Kaynaklara salt okunur erişim; kaynak verisini otomatik düzeltme yok.
- Kurum içi veri merkezi dağıtımı ve yerel prototip ortamı.

## Hızlı Bağlantılar

- [[01-SRS/01-Amac-ve-Kapsam|Amaç ve Kapsam]]
- [[01-SRS/02-Sistem-Aciklamasi|Genel Sistem Açıklaması]]
- [[01-SRS/12-MVP|MVP]]
- [[01-SRS/15-Acik-Konular|Açık Konular]]
- [[04-Frontend/Gorsel-Tasarim-Sistemi|Frontend Görsel Tasarım Sistemi]]
- [[04-Frontend/03-Dashboard/Dashboard-Ekran-Sozlesmesi|Dashboard Ekran Sözleşmesi]]

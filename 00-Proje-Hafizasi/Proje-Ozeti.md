---
type: project-memory
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
created_at: 2026-07-16
tags:
  - proje
  - hafiza
  - ozet
---

# Proje Özeti

## Amaç

Kurum genelindeki veri kaynaklarının merkezi biçimde tanımlanması; veri kümelerinin profillenmesi; veri kalitesi kurallarının yönetilip çalıştırılması; kalite skorlarının hesaplanması; sorunların sahiplerine atanması ve denetlenebilir geçmişin saklanması.

## Temel Kalite Boyutları

Tamlık, geçerlilik, doğruluk, tutarlılık, benzersizlik ve güncellik/zamanlılık.
Bankacılık bağlamında mutabakat, referans bütünlüğü, izlenebilirlik ve veri
bütünlüğü de desteklenebilir. Uygulanmayan boyut `NotApplicable` olur.

## Skorlama İlkesi

Ham veri kalitesi skoru; kural/ölçüm kapsamı, skor güvenilirliği, dataset
kritikliği/veri riski ve teknik sağlık durumundan ayrı tutulur. Skor personel
performans puanı değildir. Bağlayıcı kararlar:
[DQ-SCR skorlama kararları](../01-SRS/04-Fonksiyonel-Gereksinimler/04.06-Skorlama.md).

## Uçtan Uca Döngü

`Kaynağı tanımla → profille → kuralı oluştur/test et → çalıştır → skorla → dashboardda göster → bildir → issue oluştur → audit et`

## Temel Sistem Özellikleri

- PostgreSQL, SQL Server, Oracle, MySQL, CSV, Excel ve REST API kaynakları.
- LDAP kimlik doğrulama ve RBAC.
- Manuel ve zamanlanmış kural çalıştırma.
- Kural, veri öğesi, boyut ve dataset hiyerarşisinde açıklanabilir skor; ayrıca
  kaynak/kurum portföy görünümü, kapsam, güven, kritiklik/risk ve teknik sağlık.
- Dashboard, sistem içi bildirim, raporlama ve ServiceNow entegrasyon hedefi.
- Kaynaklara salt okunur erişim; kaynak verisini otomatik düzeltme yok.
- Kurum içi veri merkezi dağıtımı ve yerel prototip ortamı.

## Hızlı Bağlantılar

- [Amaç ve Kapsam](../01-SRS/01-Amac-ve-Kapsam.md)
- [Genel Sistem Açıklaması](../01-SRS/02-Sistem-Aciklamasi.md)
- [MVP](../01-SRS/12-MVP.md)
- [Açık Konular](../01-SRS/15-Acik-Konular.md)
- [Frontend Görsel Tasarım Sistemi](../04-Frontend/Gorsel-Tasarim-Sistemi.md)
- [Dashboard Ekran Sözleşmesi](../04-Frontend/03-Dashboard/Dashboard-Ekran-Sozlesmesi.md)

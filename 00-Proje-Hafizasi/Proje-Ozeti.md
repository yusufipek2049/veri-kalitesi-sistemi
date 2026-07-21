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

Ham ve kritik kontrol etkili nihai veri kalitesi skoru; ölçüm yeterliliği,
kullanım kararı, kural/ölçüm kapsamı, güven, dataset kritikliği/veri riski ve
teknik sağlık durumundan ayrı tutulur. Yüksek skor eksik, eski veya teknik olarak
başarısız ölçümü geçerli kılamaz. Skor personel performans puanı değildir.
Bağlayıcı kaynaklar: [DQ-SCR skorlama kararları](../01-SRS/04-Fonksiyonel-Gereksinimler/04.06-Skorlama.md)
ve [kanonik skorlama ve ölçüm yeterliliği tasarımı](../02-Mimari/Veri-Kalitesi-Skorlama-ve-Olcum-Yeterliligi.md).

## Sentetik Test Verisi İlkesi

Sentetik test verisi politika kontrollü, deterministik ve izlenebilir üretilir;
kusur enjeksiyonu temel veriden, ground truth runtime kural/skor motorundan ve
test olayları gerçek operasyon hedeflerinden ayrılır. Sentetik veri anonimlik
kanıtı değildir. Kanonik kaynak:
[Sentetik Veri ve Gizlilik Stratejisi](../02-Mimari/Sentetik-Veri-ve-Gizlilik-Stratejisi.md).

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
- [Sentetik Veri ve Gizlilik Stratejisi](../02-Mimari/Sentetik-Veri-ve-Gizlilik-Stratejisi.md)
- [Frontend Görsel Tasarım Sistemi](../04-Frontend/Gorsel-Tasarim-Sistemi.md)
- [Dashboard Ekran Sözleşmesi](../04-Frontend/03-Dashboard/Dashboard-Ekran-Sozlesmesi.md)

---
type: srs-section
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "1"
created_at: 2026-07-16
tags:
  - srs
  - bolum-1
---

# Amaç ve Kapsam

Bu bölüm, sistemin geliştirilme gerekçesini, SRS dokümanının hedefini, kapsam sınırlarını, kullanılan terimleri ve başvurulacak referansları tanımlar.

## 1.1 Giriş


Kurumun operasyonel sistemleri, veri ambarı, veri gölü, dosya tabanlı kaynakları ve harici servisleri arasında üretilen verilerin hacmi ve çeşitliliği arttıkça veri kalitesinin yalnızca manuel kontrollerle sürdürülebilir biçimde yönetilmesi mümkün değildir. Eksik, geçersiz, tutarsız, tekrarlı, güncelliğini yitirmiş veya referans bütünlüğü bozulmuş veriler; raporlama hatalarına, operasyonel gecikmelere, mevzuat risklerine ve yanlış karar alınmasına yol açabilir.

Veri Kalitesi İzleme ve Skorlama Sistemi; veri kaynaklarının merkezi olarak tanımlanmasını, veri kümelerinin profillenmesini, veri kalitesi kurallarının yönetilmesini, kuralların manuel veya zamanlanmış biçimde çalıştırılmasını, kalite skorlarının hesaplanmasını, sorunların sorumlu kişilere atanmasını ve denetlenebilir kayıtların saklanmasını sağlar.

## 1.2 Amaç


Bu SRS dokümanının amacı, Veri Kalitesi İzleme ve Skorlama Sistemi için iş, fonksiyonel, veri, arayüz, güvenlik, performans, kullanılabilirlik, işletim ve kabul gereksinimlerini açık, ölçülebilir, test edilebilir ve izlenebilir biçimde tanımlamaktır.

Doküman; proje yöneticileri, iş analistleri, yazılım geliştiriciler, veri mühendisleri, veri yönetişimi ve veri kalitesi ekipleri, test ekipleri, bilgi güvenliği ekipleri, sistem yöneticileri, denetçiler ve iş birimleri için ortak başvuru kaynağıdır.

## 1.3 Kapsam

### Kapsam Dahilinde


- PostgreSQL, Microsoft SQL Server, Oracle, MySQL, CSV, Excel ve REST API kaynaklarının tanımlanması ve yönetilmesi.
- Veri kaynağı bağlantılarının test edilmesi ve bağlantı bilgilerinin güvenli biçimde saklanması.
- Şema, tablo, görünüm ve alan metadatasının keşfedilmesi.
- Veri profilleme metriklerinin üretilmesi ve tarihsel karşılaştırılması.
- Tamlık, doğruluk, geçerlilik, tutarlılık, benzersizlik, güncellik ve bütünlük boyutlarında kalite kuralları tanımlanması.
- Kural sürümleme, ağırlıklandırma, eşik ve kritiklik yönetimi.
- Manuel, tek seferlik ve tekrarlı kural çalıştırmaları.
- Kural, boyut, veri kümesi, veri kaynağı ve kurum seviyesinde skor hesaplanması.
- Dashboard, rapor, sistem içi bildirim ve ServiceNow entegrasyonu.
- Veri kalitesi sorunu yaşam döngüsü yönetimi.
- LDAP tabanlı kimlik doğrulama ve rol bazlı yetkilendirme.
- Audit log, sonuç geçmişi ve raporlama için kayıt sınıfı bazlı saklama ve imha politikaları.
- Kurum içi veri merkezi dağıtımı ve yerel geliştirme/prototip ortamı.

### Kapsam Dışında


- Kaynak sistemlerde verinin otomatik düzeltilmesi veya silinmesi.
- Kaynak sistemlere yazma yetkisi verilmesi.
- Ana veri yönetimi, veri sözlüğü veya metadata kataloğunun tüm fonksiyonlarının yeniden geliştirilmesi.
- İlk fazda gerçek zamanlı streaming veri kontrolü.
- İlk fazda makine öğrenmesiyle otomatik kural önerisi ve kök neden analizi.
- İlk fazda gelişmiş veri lineage çıkarımı.
- SMS, e-posta veya üçüncü taraf anlık mesajlaşma kanalları üzerinden bildirim.
- Kurum dışı çok kiracılı SaaS hizmeti sunulması.
- Kaynak sistemlerin performans iyileştirmesi veya veri modelinin yeniden tasarlanması.

## 1.4 Tanımlar, Kısaltmalar ve Terimler

| Terim/Kısaltma | Tanım |
| --- | --- |
| Veri kalitesi | Verinin tanımlanan iş amacı için doğru, eksiksiz, geçerli, tutarlı, benzersiz, güncel ve bütün olması derecesi. |
| Veri kalitesi boyutu | Kalitenin ölçüldüğü kategori. Bu sistemde tamlık, doğruluk, geçerlilik, tutarlılık, benzersizlik, güncellik ve bütünlük desteklenir. |
| Veri kalitesi kuralı | Bir veri kümesi veya alan üzerinde ölçülebilir kabul koşulu tanımlayan kontrol. |
| Veri kalite skoru | Kural sonuçlarından 0–100 aralığında hesaplanan kalite göstergesi. |
| Veri kaynağı | Verinin alındığı veritabanı, dosya veya REST API sistemi. |
| Veri kümesi | Kalite kontrolünün uygulandığı tablo, görünüm, dosya, API sonucu veya mantıksal veri grubu. |
| Veri profilleme | Bir veri kümesinin dağılım, boşluk, benzersizlik, desen ve istatistik özelliklerinin analiz edilmesi. |
| Eşik değer | Bir skorun veya metrik değerinin kabul edilebilir sayılacağı sınır. |
| Kritik veri öğesi | İş süreçleri, raporlama veya mevzuat açısından yüksek öneme sahip veri alanı. |
| Data Owner | Verinin iş anlamı, kullanım amacı, kalite hedefi ve kabul kararlarından sorumlu iş rolü. |
| Data Steward | Veri tanımları, kalite kuralları, sorun takibi ve günlük yönetişim faaliyetlerinden sorumlu rol. |
| Metadata | Verinin yapısı, kökeni, tipi, sahibi ve kullanımına ilişkin tanımlayıcı bilgi. |
| KPI | Key Performance Indicator; anahtar performans göstergesi. |
| SLA | Service Level Agreement; hizmet seviyesi taahhüdü. |
| RBAC | Role-Based Access Control; rol bazlı erişim kontrolü. |
| Audit Log | Kullanıcı ve sistem işlemlerini değiştirilemez biçimde izlemek için tutulan denetim kaydı. |
| API | Application Programming Interface; uygulama programlama arayüzü. |
| ETL | Extract, Transform, Load; verinin çıkarılması, dönüştürülmesi ve yüklenmesi süreci. |
| ELT | Extract, Load, Transform; verinin çıkarılması, yüklenmesi ve hedefte dönüştürülmesi süreci. |
| DQ | Data Quality; veri kalitesi. |
| LDAP | Lightweight Directory Access Protocol; kurumsal dizin ve kimlik doğrulama protokolü. |
| SSO | Single Sign-On; tek oturum açma. |
| ServiceNow | Kurumun tercih ettiği olay, görev ve ticket yönetim sistemi. |
| RPO | Recovery Point Objective; kabul edilebilir veri kaybı süresi. |
| RTO | Recovery Time Objective; kabul edilebilir hizmet geri dönüş süresi. |
| TBD | Daha sonra belirlenecek karar veya değer. |

## 1.5 Referanslar

| Referans | Kullanım amacı |
| --- | --- |
| ISO/IEC/IEEE 29148 | Gereksinim mühendisliği ve SRS yapısı için referans alınması önerilir. |
| ISO 8000 | Veri kalitesi ve ana veri yönetimi ilkeleri için referans alınması önerilir. |
| DAMA-DMBOK | Veri yönetişimi ve veri kalitesi uygulama çerçevesi olarak referans alınması önerilir. |
| ISO/IEC 25012 | Veri kalitesi modeli ve boyutları için referans alınması önerilir. |
| KVKK | Kişisel verilerin işlenmesi, erişimi, saklanması ve korunması bakımından uyulması gereken mevzuat. |
| Kurumsal bilgi güvenliği politikaları | Kimlik doğrulama, yetkilendirme, şifreleme, ağ erişimi ve kayıt yönetimi için bağlayıcı kurum içi kurallar. |
| Kurumsal veri yönetişimi politikaları | Data Owner, Data Steward, kritik veri öğesi, kalite eşiği ve sorun sahipliği kararları için kurum içi çerçeve. |
| Kurumsal log ve saklama politikaları | Audit, uygulama ve güvenlik kayıtlarının saklanma süresi ve erişim koşulları için bağlayıcı referans. |

## 1.6 Dokümana Genel Bakış


Bölüm 2 sistem perspektifini ve ortamını; Bölüm 3 iş gereksinimlerini; Bölüm 4 fonksiyonel gereksinimleri; Bölüm 5 kullanım senaryolarını; Bölüm 6 iş kurallarını; Bölüm 7 veri modelini ve veri sözlüğünü; Bölüm 8 kullanıcı, yazılım ve iletişim arayüzlerini; Bölüm 9 fonksiyonel olmayan gereksinimleri; Bölüm 10 sistem kabul senaryolarını; Bölüm 11 izlenebilirlik matrisini; Bölüm 12 MVP ve önceliklendirmeyi; Bölüm 13 riskleri; Bölüm 14 sistem evrimini; Bölüm 15 açık konuları ve varsayımları; Bölüm 16 ise kalite kontrol sonucunu içerir.

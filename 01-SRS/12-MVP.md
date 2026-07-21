---
type: srs-section
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "12"
created_at: 2026-07-16
tags:
  - srs
  - mvp
---

# Önceliklendirme ve MVP

Bu bölüm, gereksinimleri MoSCoW yaklaşımıyla ve iki ürün fazında sınıflandırır.

## 12.1 MoSCoW Sınıflandırması

| MoSCoW | Kapsam | İlgili gereksinimler | Gerekçe |
| --- | --- | --- | --- |
| Must Have | Kurumsal SSO/MFA, RBAC, kaynak tanımı/testi ve kullanım politikası, secret yönetimi, katalog/DLP sınıflandırması, metadata/profil, temel kural şablonları, manuel/zamanlanmış çalışma, timeout/retry/idempotency, resmî/provizyonel skor ayrımı, dashboard, sistem içi bildirim, temel issue yaşam döngüsü, temel rapor/dışa aktarma, audit ve API güvenliği | FR-001–FR-003, FR-005–FR-034 seçili Must öğeleri; FR-036–FR-061 Must öğeleri; FR-064–FR-070; FR-072, FR-075, FR-077–FR-084, FR-086 | Sistemin iş değerini, güvenliğini ve denetlenebilirliğini sağlayan asgari kapsam. |
| Should Have | Yetki matrisi, kural onayı, bağımlılık sırası, iptal, gelişmiş trend, bildirim susturma/eskalasyon, kanıt dosyası, ServiceNow, gelişmiş raporlar, yatay ölçekleme ve dağıtık izleme | FR-004, FR-035, FR-038, FR-042, FR-052–FR-053, FR-058, FR-061, FR-063, FR-067, FR-071, FR-073–FR-074, FR-076, FR-087 | Kurumsal işletimi güçlendirir; MVP sonrası kısa vadede planlanmalıdır. |
| Could Have | Aykırı değer analizi, webhook, çoklu tenant, gelişmiş otomasyon | FR-019, FR-085 ve Sistem Evrimi maddeleri | İş değerini artırır ancak temel kalite döngüsü bunlar olmadan çalışır. |
| Won't Have for Now | ML anomali tespiti, otomatik kural önerisi, doğal dil kuralı, gerçek zamanlı streaming, otomatik kök neden, tam lineage, dış e-posta/SMS | Bölüm 14 gelecekteki kapsam | Yerel prototip ve ilk kurumsal sürümün riskini, maliyetini ve karmaşıklığını sınırlamak. |

## 12.2 MVP


MVP; uçtan uca “kaynağı tanımla → profille → kuralı oluştur/test et → çalıştır → skorla → dashboardda göster → sistem içi bildir → issue oluştur → audit et” döngüsünü tamamlamalıdır.

**MVP kapsamı**

- Kullanıcı ve rol yönetimi: LDAP destekli kurumsal IdP/SSO, zorunlu MFA, RBAC, çoklu grup-rol/kapsam eşleme, oturum ve başarısız giriş kontrolü.
- Veri kaynağı bağlantısı: ürün bağımsız bağlayıcı sözleşmesi; geliştirme sırası bankada yaygın ilişkisel veritabanı, dosya/CSV, ikinci ilişkisel veritabanı ve API kaynağıdır. Ürün adı kurum kararı olmadan sabitlenmez.
- Hassas sınıflandırma: kurumsal veri kataloğu veya DLP kaynağı ve kesintide güvenli varsayılan.
- Temel profilleme: kayıt, null, tekil, min/max, ortalama, tekrar ve temel desen.
- Kural tanımlama: zorunlu alan, benzersizlik, aralık, regex, güncellik ve referans bütünlüğü; sürüm, eşik, ağırlık, sahip.
- Manuel ve zamanlanmış çalıştırma: günlük/haftalık/aylık/cron, timeout, retry, iptal veya en az kontrollü sonlandırma, geçmiş.
- Temel skorlama: kural, boyut, veri kümesi, kaynak ve kurum skoru; NO_DATA/teknik hata ayrımı.
- Dashboard: genel skor, kaynak/dataset/boyut, trend, düşük skor, başarısız iş ve drill-down.
- Sistem içi bildirim: eşik, kritik başarısızlık ve teknik hata bildirimleri.
- Veri kalitesi sorunu: otomatik kayıt, atama, durum, kök neden, faaliyet ve doğrulama.
- Raporlama: özet/detay ve PDF/XLSX/CSV dışa aktarma.
- Audit: giriş, bağlantı, kural, yetki, eşik, issue ve rapor işlemleri.
- Kapasite: düşük/beklenen/yüksek senaryolar ve üretim öncesi gerçek envanter doğrulaması; 20 milyon satırlık onaylı anonimleştirilmiş üretim örneğinde kaynakta toplulaştırma/bölümleme/örnekleme.

**MVP gerekçesi:** Bu kapsam, veri kalitesi yönetiminin ölçme, görünürlük, sorumluluk ve denetim döngüsünü tek başına tamamlar. ServiceNow entegrasyonu kurumsal değerli olmakla birlikte API erişimi ve kurum bağımlılığı nedeniyle “Should” olarak MVP sonrasına bırakılabilir; proje takvimine göre MVP'ye çekilebilir.

## 12.3 İkinci Faz


İkinci faz; kurumsal ölçekleme, otomasyon ve harici yönetişim entegrasyonlarına odaklanır:

- ServiceNow ticket ve durum senkronizasyonu.
- Metadata kataloğuyla gelişmiş sahiplik ve teknik metadata senkronizasyonu; sınıflandırma kaynağı MVP'de zorunludur.
- Gelişmiş aykırı değer ve anomali tespiti.
- Makine öğrenmesi tabanlı kalite kontrolleri.
- Otomatik kural önerisi.
- Gelişmiş lineage ve şema değişikliği etki analizi.
- Tahmine dayalı kalite analizi.
- Doğal dil ile kural oluşturma.
- Webhook ve harici olay tüketimi.
- Büyük ölçekli yatay worker ve kuyruk ölçekleme.
- Çoklu kurum/tenant gereksinimi doğarsa veri ve yetki izolasyonu.

**Gerekçe:** Bu özellikler daha fazla metadata olgunluğu, eğitim verisi, entegrasyon izni ve işletim kapasitesi gerektirir. Önce MVP'deki deterministik ölçüm ve tarihsel veri tabanı kurulmalıdır.

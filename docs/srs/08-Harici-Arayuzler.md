---
type: srs-section
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "8"
created_at: 2026-07-16
tags:
  - srs
  - interface
---

# Harici Arayüz Gereksinimleri

Bu bölüm, kullanıcı ekranlarını, harici yazılım entegrasyonlarını ve iletişim protokollerini tanımlar.

## 8.1 Kullanıcı Arayüzü

| Ekran | Amaç | Kullanıcı rolleri | Görüntülenecek bilgiler | Yapılabilecek işlemler | Filtreler | Validasyonlar | Hata mesajları |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Giriş ekranı | Kurumsal SSO ve MFA ile güvenli giriş | Tüm kullanıcılar | SSO yönlendirmesi, oturum ve hata/correlation ID | SSO ile giriş, yardım | Kurumsal IdP | IdP beyanı, MFA kanıtı ve oturum bütünlüğü | Kimlik doğrulama başarısız; MFA eksik; IdP ulaşılamıyor; geçici engelleme |
| Ana dashboard | Genel kalite ve operasyon durumunu sunmak | Tüm yetkili kullanıcılar | Ham/nihai kalite skoru, ölçüm yeterliliği, kritik kural ve kullanım kararı, kapsam, güven, kritiklik/risk, teknik sağlık, boyut/kural kırılımı, trend, kritik sorun ve son işler | Filtre, sıralama, drill-down, görünüm değiştirme | Tarih, kaynak, birim, sahip, boyut, kalite/yeterlilik/kullanım/teknik durum, risk/kritiklik, model sürümü | Tarih aralığı, karşılaştırılabilir sürüm ve kapsam yetkisi | Veri yok; yetersiz veya sınırlı kapsam; eski skor; teknik hata; sorgu zaman aşımı; yetkisiz kapsam |
| Veri kaynakları ekranı | Kaynakları yönetmek | Sistem Yöneticisi, Veri Mühendisi | Ad, tür, durum, sahip, son test, dataset sayısı | Ekle, test et, güncelle, aktif/pasif, arşivle | Tür, durum, sahip, test sonucu | Benzersiz ad; zorunlu alan; secret açık gösterilmez | Bağlantı, TLS, kimlik, yetki, sürücü hataları |
| Veri kümeleri ekranı | Keşfedilen veri kümelerini ve sahipliği göstermek | Veri Kalitesi Uzmanı, Data Steward | Kaynak, namespace, ad, kayıt tahmini, kritiklik, sahip, kural sayısı | Profil başlat, sahip/kritiklik düzenle, detay aç | Kaynak, şema, kritiklik, sahip | Geçerli sahip; yetkili kapsam | Metadata eski; nesne kaldırılmış; yetkisiz |
| Veri profilleme ekranı | Profil planlamak ve sonuçları karşılaştırmak | Veri Kalitesi Uzmanı, Veri Mühendisi | Alan listesi, tip, hassasiyet, metrikler, örneklem, önceki fark | Tam/örneklem profil, iptal, karşılaştır | Alan, metrik, tarih, durum | Örneklem 0–1; satır limiti; hassas veri maskesi | Timeout; kaynak kotası; boş veri; şema değişikliği |
| Kural yönetim ekranı | Kuralları listelemek ve yaşam döngüsünü yönetmek | Veri Kalitesi Uzmanı, Data Owner | Kod, ad, boyut, kapsam, sürüm, durum, eşik, ağırlık, sahip | Oluştur, kopyala, test, aktifleştir/pasifleştir, arşivle | Durum, boyut, sahip, kaynak, kritiklik | Yetki; geçerli sürüm; aktif kural sahipliği | Onay eksik; şema uyumsuz; geçersiz geçiş |
| Kural oluşturma ekranı | Şablon/SQL ile test edilebilir kural tanımlamak | Veri Kalitesi Uzmanı, Veri Mühendisi | Şablon, alanlar, parametreler, boyut, eşik, ağırlık, SQL önizleme | Taslak kaydet, test, onaya gönder | Kaynak/dataset/alan seçimi | Eşik 0–100; ağırlık >0; regex/SQL güvenliği | DML/DDL; tip uyumsuzluğu; maliyet yüksek |
| Çalıştırma geçmişi ekranı | İşleri ve teknik durumları izlemek | Veri Kalitesi Uzmanı, Sistem Yöneticisi, Denetçi | Execution ID, kaynak, kural sürümü, başlangıç/bitiş, süre, durum, hata | Detay, iptal, tekrar çalıştır, log bağlantısı | Tarih, durum, kaynak, kural, tetikleyici | İptal yetkisi; tekrar için idempotency | Worker kaybı; timeout; teknik hata |
| Skor detay ekranı | Skorun formül, ölçüm yeterliliği ve alt bileşenlerini açıklamak | Data Owner, Data Steward, Denetçi | Ham/nihai kalite skoru, kalite/yeterlilik/teknik durum, kullanım kararı, boyut/kural kırılımı, kritik kural kararı, sayaçlar, kapsam, örneklem/güven, kanıt tamamlığı, geçerlilik, kritiklik/risk, istisna/override ve tüm politika/model/referans sürümleri | Dönem karşılaştır, kural/issue/remediation/yeterlilik kanıtı detayına git | Tarih, boyut, kalite/yeterlilik/kullanım/teknik durum, model sürümü | Yetersiz/provizyonel skor resmî trend/SLA'ya katılamaz; hesaplanmamış skor 0 gösterilemez; override ham/nihai skoru değiştiremez | `NoData`; `NotApplicable`; `NotMeasured`; `TechnicalError`; `LimitedCoverage`; `Stale`; `ValidationRequired`; `NotQualified`; config/politika hatası |
| Sorun yönetim ekranı | Issue yaşam döngüsünü yürütmek | Data Steward, Data Owner, Veri Mühendisi | Issue no, kaynak, kural, öncelik, durum, sahip, son tarih, kök neden, faaliyet, ServiceNow | Ata, durum değiştir, yorum/kanıt ekle, doğrula, kapat, yeniden aç | Durum, öncelik, sahip, SLA, tarih | Durum geçişi; zorunlu çözüm alanları; dosya taraması | Geçersiz geçiş; pasif sahip; ServiceNow hatası |
| Bildirim yönetim ekranı | Sistem içi bildirim ve politikaları yönetmek | Tüm kullanıcılar; yönetim için yetkili roller | Okunmamış bildirim, olay, kaynak, tarih; şablon ve susturma politikası | Oku, filtrele, ilgili nesneye git; politika düzenle | Okunma, olay türü, kritiklik, tarih | Alıcı yetkisi; şablon değişkeni | Alıcı yok; duplicate; şablon hatası |
| Raporlama ekranı | Rapor üretmek, dışa aktarmak ve zamanlamak | Data Owner, Data Steward, Denetçi | Rapor türü, filtreler, önizleme, format, durum | Oluştur, PDF/XLSX/CSV indir, zamanla | Tarih, birim, sahip, kaynak, boyut | Dışa aktarma yetkisi; satır limiti; maskeleme | Rapor timeout; fazla satır; süresi geçmiş bağlantı |
| Kullanıcı ve rol yönetimi ekranı | IdP gruplarını rol ve kapsama eşlemek | Sistem Yöneticisi | Kullanıcı, harici grup referansı, roller, kapsam, durum, son giriş | Grup-rol/kapsam eşle, pasifleştir, matrisi görüntüle | Kullanıcı, rol, izin, kapsam | Çoklu grup ve deterministik çatışma/ret politikası | Çakışan rol; IdP kullanıcısı yok; yetki dışı işlem |
| Audit log ekranı | Denetim kayıtlarını incelemek | Denetçi, Sistem Yöneticisi | Zaman, aktör, işlem, nesne, sonuç, eski/yeni değer, correlation ID, bütünlük | Filtrele, detay, dışa aktar, bütünlük doğrula | Tarih, kullanıcı, işlem, nesne, sonuç | Hassas değer maskesi; yalnız append-only okuma | Yetkisiz; bütünlük hatası; geniş sorgu |
| Sistem ayarları ekranı | Eşik, ağırlık, normalizasyon, kritik kural, güven, kaynak kullanım, kısmi skor, istisna/override, saklama ve entegrasyon politikalarını yönetmek | Sistem Yöneticisi; Veri Yönetişimi; ilgili onay rolleri | Konfigürasyon sürümü, kapsam, değer, gerekçe, geçerlilik, risk sınıfı ve onay durumu | Taslak, doğrula, onaya gönder, etkinleştir, geri çek | Kategori, kapsam, durum, sürüm | Aralık, süre, bağımlılık, görevler ayrılığı ve risk bazlı dört göz ilkesi | Çakışan eşik; sürümsüz politika; süresiz istisna/override; onay eksik |
| Kanıtlı olay inceleme | İkinci fazda skor, metrik, hesaplama, lineage, teşhis, öneri, run, değişiklik, zaman çizelgesi ve kanıt paketini birlikte incelemek | Data Owner, Data Steward, Veri Mühendisi, Denetçi; izinleri ayrı | Kullanım kararı, ayrı güven değerleri, etki, kanıt gücü/eksikleri ve gezilebilir kaynak referansları | Reproduction, simülasyon, öneri, remediation dry-run/onay, kanıt paketi; chaos ayrı izinle | Dataset, kullanım amacı, olay, zaman, drift, kanıt/güven durumu | Scope, sınıflandırma, maker-checker, idempotency, DLP ve değişmez sonuç | Eksik kanıt; yetkisiz; politika yok; teknik hata; incomplete lineage |

### Genel UI Kuralları


- Tüm ekranlar kullanıcının RBAC ve veri alanı kapsamına göre veri göstermelidir.
- Liste ekranlarında sayfalama, sıralama ve filtre sıfırlama bulunmalıdır.
- Hata mesajları teknik ayrıntı veya secret içermemeli; kullanıcıya correlation ID sunmalıdır.
- Kritik yazma işlemlerinde onay iletişimi ve sonuç bildirimi gösterilmelidir.
- “Hesaplanmadı”, “veri yok”, “kısmi” ve “0 skor” görsel olarak birbirinden ayrılmalıdır.
- `Passed`, `Warning`, `Failed`, `NotApplicable`, `NotMeasured`, `NoData`,
  `TechnicalError` ve `SuppressedByException` ayrı ikon ve yazılı etiket taşır.
- Ham/nihai kalite skoru, ölçüm yeterliliği, kritik kural, kullanım kararı,
  kapsam, güven, kritiklik/risk ve teknik sağlık tek yüzdeye birleştirilmez.
  Yüksek skor yetersiz ölçümü gizlemez; skor çalışan performans KPI'sı olarak sunulmaz.
- Masaüstü öncelikli responsive tasarım uygulanmalı; 1366×768 ve üzeri çözünürlükler desteklenmelidir. Mobil yönetim işlevleri MVP kapsamı dışındadır ve ikinci fazda ele alınacaktır.
- Kanıtlı olay ekranında kalite, ölçüm, teşhis, öneri güveni ve kanıt gücü ayrı
  gösterilmeli; korelasyon doğrulanmış neden gibi sunulmamalı ve tahmini etki
  kaynak/formül/güven olmadan gösterilmemelidir.

## 8.2 Yazılım Arayüzleri

| Arayüz | Gereksinim |
| --- | --- |
| REST API | JSON tabanlı, versiyonlu API; OpenAPI dokümantasyonu; 401/403/404/409/422/429/5xx hata sınıfları. |
| Kurumsal IdP/SSO | LDAP destekli IdP üzerinden OIDC veya SAML; tüm kullanıcılar için MFA; çoklu grup üyeliği ve yönetilebilir rol eşleme. Uygulama LDAP şemasına doğrudan bağımlı olmaz. |
| Sistem içi bildirim servisi | Uygulama içi olay kuyruğu ve Notification deposu; dış e-posta/SMS yoktur. |
| ServiceNow | Ara entegrasyon tablosu veya entegrasyon servisi üzerinden dayanıklı, idempotent ticket ve durum senkronizasyonu. |
| Veri kaynağı bağlayıcıları | Ürün bağımsız arayüz; kimlik, bağlantı testi, metadata keşfi, sorgu, timeout, iptal, hata sınıflandırması ve gözlemlenebilirlik sözleşmesi. |
| Dosya depolama servisi | CSV/Excel girdi ve rapor/kanıt dosyaları için kurum içi güvenli depolama. |
| Kurumsal veri kataloğu/DLP | Hassas sınıflandırma, maskeleme, görüntüleme, raporlama ve loglama kısıtlarının kaynak sistemi. |
| Sentetik veri yönetim API'si | Hedef iç API; `SyntheticDatasetPolicy`, senaryo, run, doğrulama ve katalog kayıtlarını sürümlü ve yetki kapsamlı sunar. Ground truth iş verisinden ayrı döner; gizlilik kapısı geçmeyen dataset kullanıma açılamaz. Üretim bildirimi/ServiceNow/SIEM hedefi bu API üzerinden seçilemez. Güvenilir HTTP/API sözleşmesi uygulanmadan yetenek dış erişime açılmaz. |
| Kanıt, lineage ve karar kaynakları | İkinci faz hedef iç API; kurumsal veri kataloğundan OpenLineage uyumlu otoriter lineage/değişiklik referanslarını alır, kanıt/manifest/teşhis/öneri/etki/contract/chaos kayıtlarını yetki ve sınıflandırma kapsamında sunar. Ürün adı uydurulmaz; öneride ilk üretim allowlist'i deterministik kural, olay benzerliği ve auditli uzman girdisidir. |

## 8.3 İletişim Arayüzleri

| İletişim | Gereksinim |
| --- | --- |
| HTTPS | Tüm kullanıcı ve API trafiği HTTPS üzerinden olmalıdır. |
| TLS | TLS 1.2 veya üzeri; kurum politikası izin veriyorsa TLS 1.3 tercih edilmelidir. |
| IdP protokolü | OIDC veya SAML trafiği şifreli kanal üzerinden yürütülmeli; issuer, audience, süre ve MFA kanıtı doğrulanmalıdır. |
| JDBC/ODBC | Veritabanı bağlantıları şifreli ve salt okunur oturumla kurulmalıdır. |
| REST kaynakları | HTTPS, sertifika doğrulama, token/kimlik referansı, sayfalama ve rate limit uygulanmalıdır. |
| Ağ zaman aşımı | Bağlantı, okuma ve toplam iş timeoutları ayrı yapılandırılmalıdır. |
| Retry | Yalnız geçici hatalarda sınırlı ve üstel gecikmeli retry yapılmalıdır. |
| Correlation ID | UI, API, worker ve entegrasyonlar boyunca aynı işlem izleme kimliği taşınmalıdır. |

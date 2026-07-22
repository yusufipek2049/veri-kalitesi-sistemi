---
type: srs-section
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "16"
created_at: 2026-07-16
tags:
  - srs
  - quality-control
---

# Doküman Kalite Kontrolü

Bu bölüm, SRS tamamlandıktan sonra yapılan yapısal ve içerik tutarlılığı kontrolünün sonucunu gösterir.

| No | Kontrol | Sonuç | Açıklama |
| --- | --- | --- | --- |
| 1 | Tüm gereksinimlerin benzersiz ID'si var mı? | Evet | BR-001–011, FR-001–111, UC-001–021, RULE-001–023, NFR kategorileri ve AC-001–071 benzersizdir. |
| 2 | Tüm fonksiyonel gereksinimler test edilebilir mi? | Evet | Her FR girdi, işlem, çıktı, hata ve kabul kriteri içerir; değişken kapasite hedeflerinde aktif politika ve politika yokluğu testi zorunludur. |
| 3 | Belirsiz ve ölçülemeyen ifadeler var mı? | Kontrollü | Ortama göre değişen değerlerin aktif sürümlü politikadan çözülmesi karara bağlanmıştır; kayıt yoksa fail-closed sonuç ölçülebilir kabul kriteridir. |
| 4 | Tüm kullanım senaryoları en az bir gereksinime bağlı mı? | Evet | UC-001–021'in her birinde ilgili FR listesi vardır. |
| 5 | Tüm kritik gereksinimlerin kabul kriteri var mı? | Evet | Sistem seviyesi AC-001–071 ve FR düzeyi kabul kriterleri bulunmaktadır. |
| 6 | Güvenlik gereksinimleri yeterli mi? | Evet, onaya tabi | RBAC, LDAP, TLS, secret manager, maskeleme, injection, XSS/CSRF, oturum, audit bütünlüğü ve testler kapsanmıştır. |
| 7 | Veri kalitesi skorlama yöntemi açık mı? | Evet | Temel ve ağırlıklı formül, seviye eşikleri ve istisna durumları tanımlanmıştır. |
| 8 | Teknik hata ile veri kalitesi hatası ayrılmış mı? | Evet | RULE-003, FR-048, UC-009/011 ve AC-010–012 bu ayrımı zorunlu kılar. |
| 9 | Yetkilendirme ve audit gereksinimleri tanımlanmış mı? | Evet | FR-001–006, FR-077–079, RULE-009 ve NFR-SEC kapsamındadır. |
| 10 | Varsayımlar ile kesin gereksinimler ayrılmış mı? | Evet | Bölüm 2.4, 7.3, 9 ve 15 durum işaretleri içerir. |
| 11 | MVP kapsamı açık mı? | Evet | Bölüm 12, uçtan uca MVP ve ikinci faz ayrımını tanımlar. |
| 12 | Gereksinimler arasında çelişki var mı? | Tespit edilmedi | Salt okunurluk, saklama, skor istisnaları ve bildirim kanalı gereksinimleri tutarlıdır. |
| 13 | İzlenebilirlik matrisinde yetim gereksinim var mı? | Tespit edilmedi | BR-001–011 ve FR-001–111 aralıklarla tamamen eşlenmiştir; uygulama aracında tekil satırlara açılacaktır. |
| 14 | Veri saklama ve gizlilik gereksinimleri tanımlanmış mı? | Evet | Bölüm 7.3, RULE-010/014, NFR-PRV ve açık karar maddeleri mevcuttur. |
| 15 | Doküman geliştirme ve test ekiplerince uygulanabilecek ayrıntıda mı? | Evet | Mimari katman, veri modeli, arayüz, hata durumları, ölçülebilir NFR ve test senaryoları tanımlanmıştır. |

## 16.1 Tespitler ve Önerilen Düzeltmeler

| Tespit | Etkilenen Bölüm | Önerilen Düzeltme |
| --- | --- | --- |
| Kritik yapısal eksik tespit edilmedi. | Tüm doküman | Gereksinimler proje yönetim aracına aktarılırken FR, UC, AC ve TS bağlantıları tekil kayıtlar halinde kurulmalıdır. |
| Üretim kapasitesi ve kaynak sorgu bütçesi kesinleşmemiştir. | 2.4, 9.1, 9.2, 15 | Pilot kaynaklarda benchmark yapılarak p95 süreler, worker sayısı, eş zamanlı sorgu ve DBA limitleri onaylanmalıdır. |
| Tek saklama süresi kaldırılmış; kayıt sınıfı bazlı matrisin kesin süreleri onay beklemektedir. | 7.3, RULE-014, 15 | Hukuk, KVKK, bilgi güvenliği ve iç denetim süre, gerekçe, çevrimiçi/arşiv ayrımı ve imha yöntemini onaylamalıdır. |
| SSO/MFA, hibrit audit ve kontrollü break-glass yönleri karara bağlanmıştır; gerçek IdP, audit altyapısı, rol eşlemesi ve operasyon kanıtı tamamlanmamıştır. | 9.5, 15, ADR-007/009 | Kurumsal adaptörler, negatif entegrasyon testleri ve banka onaylı işletim kanıtları tamamlanmalıdır. |
| Yerel prototip üretim performansını tek başına kanıtlayamaz. | 2.4, 9.1, 12, 13 | Yerel testlere ek olarak kuruma benzer ağ/DB ortamında performans ve kaynak etki testi yapılmalıdır. |
| Sentetik veri aktif nicel fayda/gizlilik politikası ve üretim profili kullanım onayı olmadan anonimlik veya nihai performans kanıtı değildir. | FR-088–096, NFR-PERF-010, NFR-PRV-007, 15 | Eksik politika `BLOCKED`, üretim profili erişimi varsayılan kapalı olmalı; `OPEN-014` anonimleştirilmiş üretim örneği kabulü ayrıca yürütülmelidir. |
| Kanıta dayalı karar desteği ikinci faz hedefidir; teknik yönler kesinleşmiş olsa da etkin politika ve kurumsal kaynak bağlantısı olmadan resmî teşhis, öneri, remediation veya chaos sonucu üretilemez. | FR-097–111, ADR-019, OPEN-026–036 karar kaydı | Kanonik mimari, IAM, veri modeli, UI, operasyon ve test bağlantıları korunmalı; eksik runtime politikası güvenli varsayılanla özelliği kapatmalıdır. |

## 16.2 Otomatik Yapısal Kontrol Özeti

| Kontrol | Sonuç |
| --- | --- |
| FR unique | Başarılı |
| UC unique | Başarılı |
| BR unique | Başarılı |
| RULE unique | Başarılı |
| AC unique | Başarılı |
| FR contiguous | Başarılı |
| UC contiguous | Başarılı |


**Sonuç:** Doküman 0.1 Taslak seviyesinde iş analizi, mimari tasarım, geliştirme, test planlama ve güvenlik incelemesine girdi sağlayacak ayrıntıdadır. Bölüm 15'teki açık kararlar sonuçlanmadan performans, işletim, saklama ve güvenlik hedefleri “onaylanmış baseline” olarak kabul edilmemelidir.

---

**Doküman Sonu — Sürüm 0.1 Taslak**

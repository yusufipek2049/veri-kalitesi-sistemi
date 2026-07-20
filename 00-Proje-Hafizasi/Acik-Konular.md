---
type: project-memory
status: open
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-20
tags:
  - proje
  - acik-konu
  - tbd
---

# Açık Konular

Ayrıntılı ve bağlayıcı liste: [[01-SRS/15-Acik-Konular|SRS — Açık Konular ve Varsayımlar]].

## Geliştirmeyi En Çok Etkileyen Kararlar

1. İlk uygulanacak bağlayıcıların sırası: CSV ve PostgreSQL bağlantı testi sözleşmeleri tamamlandı; gerçek PostgreSQL sürücü paketi ve canlı entegrasyon ortamı netleşmeli.
2. Yerel prototip paralellik varsayılanları uygulandı; üretim worker sayısı, HEAVY/LIGHT sınıflandırma ölçütleri ve kaynak bazlı sorgu kotaları kurum kapasite testiyle netleşmeli.
3. Kurumsal secret manager ürünü ve erişim modeli.
4. LDAP grup-rol eşleme ayrıntıları ve MFA/SSO kararı.
5. 20 milyon satırlık performans testi için anonim veya sentetik veri seti.
6. ServiceNow veri-minimum domain sözleşmesi fake adaptörle uygulandı; gerçek tablo/alan/durum eşleme, servis hesabı, endpoint/TLS, retry ve veri aktarım kararı açık.
7. RPO/RTO hedefleri ve beş yıllık saklama onayı.
8. Üretim dağıtım platformu ve veritabanı ürünü.
9. Audit yazılamadığında fail-closed veya dayanıklı kuyruk davranışı.
10. Kısmi çalıştırmalar varsayılan olarak resmi skordan dışlanıyor; hangi istisnai durumlarda resmi skora katılabileceği için iş birimi kararı (`OPEN-018`) bekleniyor.
11. Dashboard güvenilir `ActorContext` ve `AuthorizationService` sınırına taşındı; diğer servislerdeki serbest `actor_id` kullanımı ile context issuer'ın gerçek LDAP/session adaptörüne bağlanması İterasyon 20 ve sonraki modül geçişlerini gerektirir.
12. Proje dizininde `.git` bulunmuyor; küçük ve anlamlı commit şartının uygulanması için Git deposu başlatma veya mevcut remote ile ilişkilendirme kararı gerekir.
13. PostgreSQL için üretim sürücüsü, bağlantı havuzu yaklaşımı ve canlı entegrasyon test veritabanı henüz seçilmedi.
14. Şema değişikliğinde aktif kuralları “inceleme gerekli” durumuna alma davranışı, kural yönetimi modülü uygulanınca metadata değişim bayrağına bağlanmalıdır.
15. `AC-008` için gerçek 20 milyon satırlık anonim/sentetik veri seti ve donanım gözlemli performans testi henüz hazırlanmadı; birim testleri yalnız SAMPLE sözleşmesini doğruluyor.
16. `RuleTestExecutor` için PostgreSQL/CSV kaynak adaptörleri, sorgu maliyet tahmini ve regex çalışma timeoutu henüz uygulanmadı; mevcut iterasyon güvenli domain sözleşmesini, şablon planlarını ve test geçmişini doğruluyor.
17. Üretim iş kuyruğu/broker ürünü, çoklu worker claim stratejisi ve worker sayısı henüz seçilmedi; yerel prototip SQLite üzerinde süreç içi kilitle kalıcı kuyruk davranışını doğruluyor.
18. Bağlantı, sorgu ve toplam timeout değerleri worker yürütücü sözleşmesinde ayrı taşınıyor ve iptal adaptörü tanımlandı; gerçek PostgreSQL/CSV adaptörlerinde sorgu iptali ile duvar saati zorlaması henüz uygulanmadı.
19. Genel cron ifadesi desteği için kullanılacak doğrulanmış parser/kütüphane ve kabul edilen cron grameri henüz seçilmedi; mevcut zamanlama yalnız ONCE/DAILY/WEEKLY/MONTHLY türlerini destekliyor.
20. QualityDimension için ayrı kalıcı UUID varlığı henüz uygulanmadı; boyut skoru kapsam kimliği geçici olarak değişmez enum kodunu (`COMPLETENESS` vb.) kullanıyor.
21. Dataset kritiklik ağırlıklarının kurumsal katsayıları onaylanmadı; mevcut sürüm tüm seviyeler için nötr `1.0` kullanıyor ve yeni politika ayrı konfigürasyon sürümü gerektiriyor.
22. Kurum skorunda kaynaklar arası ağırlık politikası onaylanmadı; mevcut ENTERPRISE formülü kaynakları eşit ağırlıklandırıyor ve farklı politika yeni formül/konfigürasyon sürümü gerektiriyor.
23. Eski SQLite `audit_records` için salt okunur envanter ve idempotent merkezi aktarım sözleşmesi sentetik verilerle teknik olarak doğrulandı. Gerçek ortam envanteri/koşusu, yedek ve geri dönüş planı, değişiklik penceresi ve operasyon onayı henüz tamamlanmadı.
24. `DURABLE_BUFFER` sözleşmesi ve hata yolu test edildi; üretim kalıcı tampon teknolojisi, sahipliği, şifrelemesi, yeniden oynatma ve idempotency davranışı henüz uygulanmadı.
25. SQLite outbox için üretim publisher worker'ı, claim/eşzamanlılık, retry/backoff, alarm metrikleri, kapasite sınırı ve saklama/temizleme politikası henüz uygulanmadı.
26. `CLASSIFICATION_POLICY_V1`, fail-closed profil politikası, sürümlü `BFR-DATA-004` işleme envanteri ve kişisel/özel nitelikli kişisel alanlar için salt okunur tamlık kontrolü uygulandı. Teknik kodların banka sözlüğüyle eşlemesi ve referansların kurumsal kayıtlarla doğrulanması açık kalır.
27. Kritik kural aktivasyonu için 19A, skor konfigürasyonu için 19B ve kural onay isteği geri çekme için 19C maker-checker akışı uygulandı. Onay süre aşımı, hazırlayanı bilinmeyen legacy kritik sürümlerin geçiş prosedürü, veri kaynağı aktivasyonu ve banka onaylı maker/checker rol kodları açık kalır.
28. Başarısız giriş sınırlandırması opak kullanıcı/istemci anahtarlarıyla teknik olarak uygulandı. Üretim anahtar türetme/rotasyon yöntemi, secret manager bağlantısı, güvenilir istemci referansının proxy/ağ sınırı, paylaşımlı depo ürünü ve LDAP ile uyumlu nihai eşik/pencere/süre onayı açık kalır.
29. Normal kullanıcı oturumu kalıcı ve iptal edilebilir olarak uygulandı. Eş zamanlı oturum limiti, banka onaylı mutlak süre, HTTP cookie veya eşdeğer token taşıma/CSRF modeli, üretim deposu ve at-rest şifreleme, bir yıllık session geçmişi saklama/imha onayı açık kalır.
30. Dashboard trendi güvenilir scope ile sabit son 30 UTC gün için uygulandı. Serbest tarih aralığı/periyot seçimi, operasyon listeleri, grafik/tablo sunumu ve HTTP taşıma katmanı açık kalır; 21B `OPEN-BNK-020` ve geçiş kapısına bağlıdır.
31. Sistem içi bildirim domain yaşam döngüsü sabit veri-minimum şablon ve güvenilir resolver protokolüyle uygulandı. Gerçek sahiplik/fallback grup kaynağı, şablon yönetimi, susturma/eskalasyon politikası, asenkron retry/DLQ, saklama-imha ve HTTP/UI yüzeyi açık kalır.
32. Otomatik issue oluşturma, atama/inceleme, korunan çözüm, başarısız/teknik doğrulama, farklı aktörle başarılı `VERIFIED`, doğrulama bağlı `CLOSED`, aynı başarısızlıkla yeniden açma ve yeni kalite başarısızlığını append-only ilişkilendirme uygulandı. Gerçek assignment/kullanıcı dizini, çözüm koruma, doğrulama ve ilişki resolver adaptörleri; banka onaylı çözen/doğrulayan rol eşlemesi, bildirim retry/DLQ, saklama-imha ve ServiceNow açık kalır.
33. Değişen issue yüzeyleri sınırlı `mypy` kontrolünden geçmektedir; tam `mypy` çalıştırması değişiklik dışındaki `audit/repository.py`, `identity/sessions.py` ve `identity/ldap.py` dosyalarında 13 mevcut hata raporlamaktadır.
34. ServiceNow ticket oluşturma allowlist projeksiyon, güvenilir servis context'i ve idempotent fake adaptörle teknik olarak doğrulandı. Gerçek endpoint/credential, banka alan-durum eşlemesi, servis hesabı yetkilendirmesi, timeout/retry/backoff, durum senkronizasyonu ve `OPEN-BNK-009` onayı açık kalır.
35. Tam depo mypy kontrolü testler dahil yedi mevcut dosyada 27 hata vermektedir; `reporting` ve `incident_response` paketleri ile testleri sınırlı kontrolden geçmektedir.
36. ServiceNow senkron geçici/429 retry politikası toplam en fazla üç deneme, üstel backoff ve `Retry-After` ile teknik olarak doğrulandı. Gerçek timeout/ağ adaptörü ve operasyon alarmı açık kalır.
37. ServiceNow kalıcı retry işi, tek worker claim'i, due-time yeniden planlama, dead-letter ve auditli yeniden kuyruğa alma SQLite prototipinde doğrulandı. Gerçek broker, çoklu süreç lease/heartbeat ve kayıp worker recovery, kuyruk kapasitesi/saklama ve operasyon alarmı açık kalır.
38. ServiceNow circuit breaker beş ardışık geçici hata, beş dakikalık açık durum ve tek half-open probe ile SQLite prototipinde doğrulandı. Dağıtık/çoklu instance state deposu, üretim eşik onayı, metrik/alarm sahipliği ve gerçek ServiceNow endpoint/credential kararı açık kalır; `OPEN-BNK-009` geçerlidir.
39. Audit inceleme sorgusu güvenilir `AUDIT_VIEWER` context'i, 31 günlük senkron pencere, snapshot cursor, parametreli filtre ve auditli görüntüleme ile doğrulandı. Banka onaylı auditor rol/grup eşlemesi, istemci bilgisi alanı, beş yıllık asenkron rapor, saklama katmanı ve hassas dışa aktarma politikası açık kalır; `OPEN-BNK-002`, `OPEN-BNK-008` ve `OPEN-BNK-014` geçerlidir.
40. Rapor önizleme güvenilir rol/source kapsamı, 31 günlük pencere, 500 source sınırı, salt okunur latest-score sorgusu ve veri-minimum audit ile doğrulandı. PDF/XLSX/CSV, Report yaşam döngüsü, asenkron üretim, indirme, DLP/watermark, dosya saklama/imha ve banka onaylı dışa aktarma/maker-checker politikası açık kalır; `OPEN-BNK-002`, `OPEN-BNK-007`, `OPEN-BNK-008` ve `OPEN-BNK-014` geçerlidir.
41. Güvenlik olayı, kişisel veri ihlali şüphesi, 72 saat hedefi, veri işleyen bildirim kanıt referansı ve farklı aktörle insan kararı teknik olarak uygulandı. Banka olay/rol sözlüğü, gerçek SIEM/SOC akışı, hukuk/uyum karar içeriği, dış bildirim, saklama/imha ve tatbikat kanıtı açık kalır; `OPEN-BNK-001`, `OPEN-BNK-002`, `OPEN-BNK-004`, `OPEN-BNK-008` ve `OPEN-BNK-010` geçerlidir.
42. İhlal zaman çizelgesi güvenilir privacy rolü ve incident scope'u ile veri-minimum görüntülenebilir; 72 saat durumu ve görüntüleme auditi teknik olarak doğrulandı. Listeleme/arama, HTTP/UI, kanıt içeriğine ayrı erişim, gerçek SIEM/SOC, banka rol eşlemesi ve saklama/imha açık kalır; `OPEN-BNK-002`, `OPEN-BNK-008` ve `OPEN-BNK-010` geçerlidir.

## Bankacılık Geçiş Açık Konuları

| ID | Konu | Karar sahibi | Durum |
| --- | --- | --- | --- |
| OPEN-BNK-001 | BDDK bilgi sistemleri düzenlemelerinin bu uygulamaya uygulanabilir maddelerinin banka uyum/hukuk tarafından teyidi | Uyum / Hukuk / Bilgi Güvenliği | ComplianceReviewRequired |
| OPEN-BNK-002 | LDAP grup-rol-scope eşleme tablosu ve joiner/mover/leaver kaynağı | IAM / İnsan Kaynakları / Bilgi Güvenliği | Açık |
| OPEN-BNK-003 | Ayrıcalıklı erişimde MFA, PAM ve break-glass modeli | Bilgi Güvenliği / IAM | Açık |
| OPEN-BNK-004 | Kritik işlem listesi ve maker-checker onay rolleri | Veri Yönetişimi / İç Kontrol | Açık |
| OPEN-BNK-005 | Audit yazılamadığında işlem bazlı fail-closed / durable-buffer politikası | Bilgi Güvenliği / Mimari / Operasyon | Açık |
| OPEN-BNK-006 | Audit bütünlüğü için WORM, hash-chain, imza veya kurumsal log platformu kararı | Bilgi Güvenliği / İç Denetim | Açık |
| OPEN-BNK-007 | Kurumsal veri sınıflandırma sözlüğü; müşteri sırrı ve banka sırrı etiketlerinin eşlemesi | Veri Yönetişimi / Hukuk / Bilgi Güvenliği | Açık |
| OPEN-BNK-008 | Kayıt türü bazlı azami saklama, imha periyodu ve legal hold politikası | Hukuk / KVKK Komitesi / İç Denetim | Açık |
| OPEN-BNK-009 | ServiceNow kurulum yeri, veri işleyen/alt işleyen durumu ve yurt dışı aktarım etkisi | Hukuk / Tedarik / Bilgi Güvenliği | Açık |
| OPEN-BNK-010 | SIEM ürün, olay sözlüğü, alarm seviyesi ve SOC eskalasyon akışı | SOC / Bilgi Güvenliği | Açık |
| OPEN-BNK-011 | Banka onaylı RTO, RPO, yedek şifreleme ve geri yükleme test sıklığı | İş Sürekliliği / Operasyon | Açık |
| OPEN-BNK-012 | Üretim veritabanı, broker, secret manager ve deployment platformu | Mimari Kurul / Operasyon | Açık |
| OPEN-BNK-013 | Sistem risk verisi veya düzenleyici raporlama üretim zincirine girecek mi; BCBS 239 kapsamı | Risk Yönetimi / Veri Yönetişimi | Açık |
| OPEN-BNK-014 | Hassas rapor dışa aktarma için gerekçe, onay, DLP ve watermark politikası | Bilgi Güvenliği / Veri Sahibi | Açık |
| OPEN-BNK-015 | 20A ile LDAP adaptör iddiasından `ActorContext` üretim yolu eklendi; doğrudan `ActorContextIssuer` kullanımlarının süreç sınırı, issuer sahipliği ve session assertion doğrulaması henüz kesinleşmedi. | IAM / Bilgi Güvenliği / Mimari | Açık |
| OPEN-BNK-016 | Üretim audit durable-buffer teknolojisi, şifreleme, sahiplik, yeniden oynatma ve başarısız tampon davranışı | Mimari / Operasyon / Bilgi Güvenliği | Açık |
| OPEN-BNK-017 | Kural onay süre aşımının süresi, başlangıç anı, değerlendirme zamanı/saat kaynağı ve politika sahibi | Veri Yönetişimi / İç Kontrol / Mimari | Açık |
| OPEN-BNK-018 | Gerçek LDAP endpoint/topolojisi, TLS sertifika güveni, timeout ve teknik hata sahipliği | IAM / Altyapı / Bilgi Güvenliği | Açık |
| OPEN-BNK-019 | Başarısız giriş için banka/LDAP uyumlu eşik, pencere, süre ve politika değişikliği onay/görevler ayrılığı; opak anahtar üretimi/rotasyonu, güvenilir istemci referansı ve paylaşımlı üretim deposu | IAM / Bilgi Güvenliği / Mimari / Altyapı / İç Kontrol | ComplianceReviewRequired |
| OPEN-BNK-020 | Normal kullanıcı oturumunda eş zamanlı limit, mutlak süre, HTTP cookie/token ve CSRF modeli, üretim deposu/şifreleme, saklama-imha süresi ve politika değişikliği onayı | IAM / Bilgi Güvenliği / Mimari / Hukuk / İç Kontrol | ComplianceReviewRequired |

## Kullanım

Bir teknik karar kesinleştiğinde ilgili `OPEN-xxx` maddesini güncelle ve sonucu [[00-Proje-Hafizasi/Alinan-Kararlar|Alınan Kararlar]] notuna taşı.

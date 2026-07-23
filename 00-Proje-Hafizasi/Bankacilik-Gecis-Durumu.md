---
type: project-memory
status: active-transition
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-23
tags:
  - proje
  - banka
  - bddk
  - kvkk
  - gecis
---

# Bankacılık Geçiş Durumu

## Gerçek Teknik Baseline

Yüklenen mevcut vault ve kod üzerinden doğrulanan durum:

- İterasyon 1–16, Iterasyon 17A–17E, Iterasyon 18A–18C, Iterasyon 19A–19H, Iterasyon 20A–20E, Iterasyon 21A–21C, Iterasyon 22A–22I, Iterasyon 23A–23D, Iterasyon 24A–24B, Iterasyon 25A–25D, Iterasyon 26A–26B, Iterasyon 27A, Iterasyon 28A–28E, Iterasyon 29A–29C, Iterasyon 30B–30D, Iterasyon 31A–31C, Iterasyon 32A–32D, İterasyon 33A–33B, İterasyon 34A–34F ve İterasyon 35A–35F teknik dikeyleri tamamlanmış ve proje hafızasına kaydedilmiştir.
- `pytest` sonucu: **1060 test geçti**; iki gerçek PostgreSQL entegrasyon testi
  opt-in koşuda ayrıca geçti. Tam mypy kontrolü 128 kaynak dosyada
  sıfır hata vermektedir.
- Mevcut çalışan domain paketleri:
  - `data_sources`
  - `rules`
  - `executions`
  - `scoring`
  - `dashboard`
  - `identity`
  - `audit`
  - `data_protection`
  - `notifications`
  - `issues`
  - `servicenow`
  - `reporting`
  - `incident_response`
  - `secure_sdlc`
  - `retention`
  - `environment_security`
  - `synthetic_data`
  - `api`
- CSV ve PostgreSQL bağlayıcı sözleşmeleri, metadata keşfi, temel profilleme, kural testleri, idempotent execution, zamanlama, sürümlü kaynak kullanım politikasıyla worker/sorgu kotası, çalışma penceresi ve sorgu timeout/retry koruması, iptal/timeout, hiyerarşik skorlama ve SOURCE/ENTERPRISE dashboard ağacı uygulanmıştır.
- LDAP tabanlı fake adaptör/eşleme, kalıcı kullanıcı/istemci giriş sınırı ve güvenli normal kullanıcı oturumu doğrulanmıştır. Hedef kimlik sınırı LDAP destekli kurumsal IdP/SSO, OIDC veya SAML ve zorunlu MFA olarak kesinleşmiştir. `OPEN-BNK-020` BFF, tek aktif oturum, `PT1H`/`PT10H`, `__Host-session`, synchronizer-token CSRF, merkezi iptal ve `P90D` güvenlik metadatasıyla `ApprovedByBank` durumundadır. 20D süre/tek oturumu, 20E cookie/CSRF HTTP sınırını runtime'a taşımıştır; gerçek IdP/RBAC callback/state/nonce, diğer merkezi iptal tetikleri, üretim session store/şifreleme, issue resolver bağlantıları, raporlama ve gerçek ServiceNow ağ adaptörü henüz uygulanmamıştır.
- Merkezi audit zarfı authorization, veri kaynağı, kural, schedule oluşturma ve skor konfigürasyonu aktivasyonunda kullanılmaktadır; auditli kalıcı domain yazımları transactional outbox kullanır. Aktif legacy audit API kullanımı kalmamıştır. Tarihsel `audit_records` için salt okunur, redaksiyonlu ve idempotent aktarım sözleşmesi sentetik verilerle doğrulanmıştır; gerçek üretim koşusu yapılmamıştır.
- Kural, skor konfigürasyonu ve veri kaynağı aktivasyon onay işlemleri güvenilir `ActorContext` kullanır; diğer bazı servis işlemlerinde `actor_id` çağıran tarafından serbest metin olarak verilebilmektedir.
- Public dashboard ve rapor sorguları scope kabul etmez; güvenilir context'i scope'a çeviren authorization servisini kullanır. Skor ağacı ve sabit son 30 günlük trend domain sorgusu yetki filtrelidir. 21B yerel/test FastAPI özetini ve bağlı frontend'i, 21C aynı yetki sınırında veri-minimum operasyonel göstergeleri eklemiştir. 35A izinli kaynaklardan veri-minimum veri kaynağı listesini, 35B izinli datasetlerden veri-minimum son sürüm kural özetini, 35C yalnız tüm kaynakları izin kapsamında kalan veri-minimum çalıştırma özetini, 35D kaynak/dataset kapsamlı veri-minimum sorun özetini, 35E rol/source kapsamlı toplulaştırılmış rapor önizlemesini, 35F ise `AUDIT_VIEWER` rol kontrollü ve snapshot sayfalı veri-minimum audit incelemesini ve salt okunur frontend rotalarını üretir; üretim resolver varsayılan olarak erişimi reddeder. Internal/deprecated geçiş adaptörü henüz kaldırılmamıştır.
- Metadata sınıflandırması sürümlü teknik sözlük kullanır; sınıfsız alanlar fail-closed `UNCLASSIFIED` olur ve profil kalıcılığı ham örnek/top-value/desen payloadlarını çıkarır. Kişisel ve özel nitelikli kişisel alanlar sürümlü işleme envanteriyle ilişkilendirilebilir ve salt okunur tamlık raporuyla denetlenir; banka sözlük eşlemesi henüz tamamlanmamıştır.
- Yerel güvenli SDLC paketi secret taraması, doğrudan bağımlılık SBOM'u, veri-minimum SAST/bağımlılık zafiyet kapıları, sızma testi bulgu takibi, deterministik teknik kanıt manifesti, drift kapısı ve bunları birleştiren yerel preflight komutunu içerir. Gerçek scanner/pentest, transitive lock, CI/CD zorlaması, imzalı kurumsal kanıt deposu, banka eşik/istisna ve release onayı uygulanmamıştır.
- Sürümlü saklama politikası kataloğu, append-only legal hold, idempotent imha kanıtı ve audit/kalite skoru arşivleri için farklı aktör kararlı geri çağırma talep sözleşmesi uygulanmıştır. Tüm retention yazımları veri-minimum ve atomik auditlidir; fiziksel imha/anonimleştirme/arşivleme ile gerçek arşiv getirme adaptörleri uygulanmamıştır.
- Sürümlü ortam başlangıç kapısı güvenilir sağlayıcı sözleşmesini, ortam-secret kapsam eşleşmesini ve üretim dışı gerçek banka verisi/üretim secret engelini fail-closed uygular. Gerçek deployment/attestation sağlayıcısı, secret manager ve veri kökeni kanıtı henüz bağlı değildir.
- Sürümlü dataset kısmi skor politikası güvenilir maker-checker onay/ret, maker'a ait auditli geri çekme ve atomik audit outbox akışıyla yönetilir; ölçülmüş çalışma olgularını fail-closed değerlendirerek `OFFICIAL` veya `PROVISIONAL` kararı üretir. Resmî kısmi sonuç `PARTIAL` statüsüyle sayısal skor ve üst agregasyonlara taşınır; provizyonel sonuç resmî agregasyon, trend ve rapor önizlemesinden çıkarılır. Politika süre aşımı ve olguların worker/execution tarafından güvenilir üretimi açıktır.
- `DQ-SCR-001`–`DQ-SCR-033` bağlayıcı skorlama kararları ve kanonik ölçüm yeterliliği hedef tasarımı gereksinim, mimari, veri modeli, API, arayüz ve test sözleşmelerine işlenmiştir. Kanonik sayaçlar ve kural skoru paydası 33A, kritiklikten ayrılmış kaynak kalite skoru 33B ile runtime'a taşındı; ham/nihai skor, sekiz yeterlilik durumu, kapsam/güven/güncellik kapıları, ayrı kullanım kararı, risk ve override yapıları henüz uygulanmadı. Değişken değerler aktif sürümlü politikadan çözülür; eksik politika olumlu karar üretmez.
- Sentetik veri ve gizlilik hedef tasarımı `ADR-016`, `FR-088–FR-096` ve
  `AC/TS-048–056` ile belgelendi. Politika, senaryo ve run kayıt çekirdeği 34A,
  tamamen yapay deterministik Golden ilişkisel üretici 34B, değişmez Golden
  yapısal ground truth ve bağımsız karşılaştırıcı 34C, kanonik çıktı/doğrulama
  referanslı append-only terminal run kanıtı 34D, append-only profilli
  deterministik çok dönemli zaman semantiği 34E ile runtime'a taşındı. 34F,
  gerçek PostgreSQL üzerinde 17 ilişkisel tablo, kontrollü kusur, kayıt düzeyi
  ground truth ve bağımsız SQL oracle'ını doğruladı;
  eksiklik/drift/hacim, fiziksel çıktı/artifact deposu, sayısal skor ground truth'u, runtime
  kural/skor/olay karşılaştırması ve gizlilik kapısı uygulanmadı. Sentetik çıktı anonimlik
  veya banka onayı sayılmaz, gerçek operasyon hedeflerini tetikleyemez ve
  `OPEN-014` kapsamındaki nihai anonimleştirilmiş üretim örneği kabulinin yerine
  geçmez. Nicel eşikler ile üretim profili/örneği erişimi `OPEN-024/025`
  kapsamında açık kalır.
- Mevcut yerel metadata ve execution repository'lerinin önemli bölümü
  SQLite'tır. Hedef kalıcılık yalnız PostgreSQL olarak kesinleşmiştir. 36A ile
  issue domaini PostgreSQL'e taşınmış ve SQLite issue runtime yolu
  kaldırılmıştır; diğer domainler bağımlılık sırasıyla bekler. 36B1 issue
  incelemeye alma, 36B2 güvenilir yeniden atama ve 36B3 korumalı çözüm kaydı
  dikeyleri PostgreSQL/BFF/CSRF/optimistic-locking sınırında tamamlanmıştır;
  farklı aktörle doğrulama, kapatma ve yeniden açma yazımları bekler.

## Korunacak Kazanımlar

Aşağıdaki davranışlar geriye dönük bozulmamalıdır:

1. Kaynak erişiminin salt okunur olması.
2. Secret değerinin metadata ve audit içinde saklanmaması.
3. Teknik hata ile kalite başarısızlığının ayrılması.
4. `NO_DATA`, `PARTIAL`, `TIMEOUT` ve teknik hata durumlarının sıfır skora çevrilmemesi.
5. RuleVersion ve scoring configuration geçmişinin değişmez kalması.
6. İdempotent execution ve scheduler tetikleme.
7. Yetkisiz SOURCE drill-down'ın repository çağrısından önce reddedilmesi.
8. 1060 mevcut testin ve sıfır hatalı tam mypy baseline'ının geriye dönük korunması.
9. Sınıflandırılmamış veya hassas alanların ham profil değerlerinin kalıcılaştırılmaması.

## En Kritik Kontrol Boşlukları

| Sıra | Boşluk | Mevcut risk | İlk hedef iterasyon |
| --- | --- | --- | --- |
| 1 | Güvenilir aktör bağlamı tüm servislere yayılmadı | Dashboard dikey dilimi korumalıdır; diğer servislerde serbest `actor_id` sürmektedir | İterasyon 20+ |
| 2 | Audit üretim operasyonlaştırması tamamlanmadı | Tarihsel aktarım sözleşmesi doğrulandı; gerçek ortam koşusu ve outbox publisher worker'ı henüz yok | Operasyon artımı / banka onayı |
| 3 | Banka sınıflandırma eşlemesi ve kurumsal referans doğrulaması tamamlanmadı | Kişisel/özel nitelikli kişisel alanlar için tamlık denetimi var; müşteri/banka sırrı eşlemesi ve referans kayıt doğrulaması yok | Banka onayı |
| 4 | Maker-checker kapsamı tamamlanmadı | Kritik kural/skor ve veri kaynağı aktivasyonu, kural/kaynak onay geri çekme, 3/10 iş günlük süre aşımı, bağlantı revizyon geçersizleştirme ve kontrollü kaynak pasifleştirme korunur; gerçek banka takvimi/worker işletimi, diğer kritik işlem sınıfları, çalışan iş politikası ve banka rol eşleme uygulaması açık | Uygulama ve banka rol eşleme kanıtı |
| 5 | Kurumsal IdP/SSO-MFA ve RBAC üretim entegrasyonu tamamlanmadı | 20A context'i dashboard authorization'a bağlar; 20B giriş sınırı, 20C temel normal session, 20D onaylı süre/tek aktif oturum, 20E BFF cookie/CSRF, 21B HTTP okuma ve 21C operasyonel gösterge DTO'sunu uygular; gerçek IdP endpoint/callback/state/nonce, banka eşlemesi, ayrıcalıklı/servis oturumu ve üretim altyapısı açık | Gerçek IdP ve üretim altyapısı |
| 6 | Operasyon ve kanıt katmanı kısmi | Ortam başlangıç kapısı, audit/rapor erişimi, güvenlik olayı, ihlal şüphesi, timeline, retention dry-run/legal hold/imha kanıtı ve arşiv geri çağırma yetkilendirmesi uygulanmıştır; gerçek ortam sağlayıcısı, DR, fiziksel/arşiv adaptörleri ve SIEM/SOC eksiktir | Altyapı kurulumu ve operasyon kanıtı |
| 7 | Kabul edilen skorlama ve ölçüm yeterliliği hedef modeli kısmen runtime'a taşındı | 33A kanonik sayaçları, 33B kritiklikten ayrılmış kaynak kalite skorunu uygular; ham/nihai skor, yeterlilik/geçerlilik kapısı, kullanım kararı, kapsam/güven, ayrı risk ve override modeli yoktur | Sonraki skorlama uygulama dilimleri |
| 8 | Kanıta dayalı karar sistemi yalnız ikinci faz hedef sözleşmesidir | `OPEN-026–OPEN-036` teknik yönleri kesinleşmiştir; kullanım amacı, etki, lineage, öneri, remediation, chaos ve kanıt paketi runtime'da yoktur | Kurumsal adaptör/politika hazırlığı ve küçük ikinci faz dilimleri |

## Geçiş Kapısı

Aşağıdaki maddeler tamamlanmadan üretim HTTP yüzeyi, hassas dışa aktarma veya banka pilotu açılmamalıdır:

- [x] Güvenilir `ActorContext` / `AuthorizationContext` sözleşmesi uygulanmış ve negatif testleri geçmiştir. Kanıt: [Iterasyon-16-Guvenilir-Aktor-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-16-Guvenilir-Aktor-Kaniti.md)
- [x] Public dashboard erişim kapsamı yalnız güvenilir authorization adaptöründen üretilmektedir. Kanıt: [Iterasyon-16-Guvenilir-Aktor-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-16-Guvenilir-Aktor-Kaniti.md)
- [x] Merkezi audit olay sözleşmesi uygulanmıştır. Kanıt: [Iterasyon-17A-Merkezi-Audit-Kaniti](../08-Uyum-Kanitlari/Audit/Iterasyon-17A-Merkezi-Audit-Kaniti.md)
- [x] Audit bütünlük ve audit-yazma-hatası politikası banka kararı için açıkça modellenmiştir. Kanıt: [Iterasyon-17A-Merkezi-Audit-Kaniti](../08-Uyum-Kanitlari/Audit/Iterasyon-17A-Merkezi-Audit-Kaniti.md)
- [x] Tarihsel audit için kaynak kaydı değiştirmeyen, redaksiyonlu ve idempotent aktarım sözleşmesi sentetik verilerle doğrulanmıştır. Kanıt: [Iterasyon-17E-Tarihsel-Audit-Aktarim-Kaniti](../08-Uyum-Kanitlari/Audit/Iterasyon-17E-Tarihsel-Audit-Aktarim-Kaniti.md)
- [x] Teknik veri sınıflandırma sözlüğü ve varsayılan profil minimizasyon politikası uygulanmıştır; banka etiket eşlemesi açık kalır. Kanıt: [Iterasyon-18A-Siniflandirma-ve-Profil-Minimizasyonu-Kaniti](../08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-18A-Siniflandirma-ve-Profil-Minimizasyonu-Kaniti.md)
- [x] Kişisel ve özel nitelikli kişisel alanlar için işleme envanteri kapsam/tamlık kontrolü uygulanmıştır; banka etiket eşlemesi açık kalır. Kanıt: [Iterasyon-18C-Envanter-Tamlik-Kaniti](../08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-18C-Envanter-Tamlik-Kaniti.md)
- [x] Sürümlü saklama politikası ve legal hold kontrollü dry-run uygulanmıştır; banka politika onayı ve fiziksel imha açık kalır. Kanıt: [Iterasyon-25A-Saklama-Politikasi-Uygunluk-Kaniti](../08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-25A-Saklama-Politikasi-Uygunluk-Kaniti.md)
- [x] Append-only legal hold oluşturma/serbest bırakma, farklı yetkili aktör ve atomik audit outbox ile uygulanmıştır; banka rol eşlemesi ve fiziksel imha açık kalır. Kanıt: [Iterasyon-25B-Kalici-Legal-Hold-Yasam-Dongusu-Kaniti](../08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-25B-Kalici-Legal-Hold-Yasam-Dongusu-Kaniti.md)
- [x] İdempotent imha işi ve terminal sonuç kanıtı append-only, görevler ayrılığı kontrollü ve atomik audit outbox ile uygulanmıştır; fiziksel adaptör, gerçek resolver'lar ve banka onayı açık kalır. Kanıt: [Iterasyon-25C-Idempotent-Imha-Isi-Kanit-Zarfi](../08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-25C-Idempotent-Imha-Isi-Kanit-Zarfi.md)
- [x] Audit/kalite skoru arşiv geri çağırma talebi farklı karar aktörü, sürümlü rol/kapsam ve atomik audit outbox ile uygulanmıştır; gerçek arşiv erişimi ve banka rol eşlemesi açık kalır. Kanıt: [Iterasyon-25D-Yetkili-Arsiv-Geri-Cagirma-Kaniti](../08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-25D-Yetkili-Arsiv-Geri-Cagirma-Kaniti.md)
- [ ] Kritik konfigürasyonlarda maker-checker uygulanmıştır. Kritik kural, skor konfigürasyonu, kural ve veri kaynağı onay geri çekme/süre aşımı, veri kaynağı aktivasyonu, bağlantı revizyon geçersizleştirme ve kontrollü kaynak pasifleştirme alt kapsamları teknik olarak doğrulanmıştır; banka iş takvimi/worker işletimi, diğer kritik işlem sınıfları, çalışan iş politikası ve banka rol eşlemesi açıktır. Kanıtlar: [Iterasyon-19A-Kural-Maker-Checker-Kaniti](../08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19A-Kural-Maker-Checker-Kaniti.md), [Iterasyon-19B-Skorlama-Maker-Checker-Kaniti](../08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19B-Skorlama-Maker-Checker-Kaniti.md), [Iterasyon-19C-Kural-Onay-Geri-Cekme-Kaniti](../08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19C-Kural-Onay-Geri-Cekme-Kaniti.md), [Iterasyon-19D-Kural-Onay-Sure-Asimi-Kaniti](../08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19D-Kural-Onay-Sure-Asimi-Kaniti.md), [Iterasyon-19E-Veri-Kaynagi-Aktivasyon-Maker-Checker-Kaniti](../08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19E-Veri-Kaynagi-Aktivasyon-Maker-Checker-Kaniti.md), [Iterasyon-19F-Veri-Kaynagi-Onay-Geri-Cekme-Sure-Asimi-Kaniti](../08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19F-Veri-Kaynagi-Onay-Geri-Cekme-Sure-Asimi-Kaniti.md), [Iterasyon-19G-Baglanti-Revizyonu-Onay-Gecersizlestirme-Kaniti](../08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19G-Baglanti-Revizyonu-Onay-Gecersizlestirme-Kaniti.md), [Iterasyon-19H-Kontrollu-Kaynak-Pasiflestirme-Kaniti](../08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19H-Kontrollu-Kaynak-Pasiflestirme-Kaniti.md)
- [ ] Kurumsal IdP/SSO-MFA grup-rol eşleme ve ayrıcalıklı erişim yönü kayıt altındadır. `OPEN-BNK-020` normal kullanıcı oturum politikası banka onaylıdır; mevcut sürümlü eşleme, fail-closed adaptör, kullanıcı/istemci giriş sınırı, temel session yaşam döngüsü, 20D süre/tek aktif oturum, 20E BFF cookie/CSRF, 21B dashboard HTTP okuma ve 21C operasyonel gösterge sınırı teknik olarak doğrulanmıştır. Gerçek IdP adaptörü/callback/state/nonce, banka grup-rol eşleme değerleri, ayrıcalıklı/servis oturumu, diğer merkezi iptal tetikleri ve üretim store/şifreleme bağlantısı açık kalır. Kanıtlar: [Iterasyon-20A-LDAP-RBAC-Sozlesme-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-20A-LDAP-RBAC-Sozlesme-Kaniti.md), [Iterasyon-20B-Basarisiz-Giris-Sinirlandirma-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-20B-Basarisiz-Giris-Sinirlandirma-Kaniti.md), [Iterasyon-20C-Guvenli-Oturum-Yasam-Dongusu-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-20C-Guvenli-Oturum-Yasam-Dongusu-Kaniti.md), [Iterasyon-20D-Banka-Onayli-Oturum-Runtime-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-20D-Banka-Onayli-Oturum-Runtime-Kaniti.md), [Iterasyon-20E-BFF-Oturum-CSRF-HTTP-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-20E-BFF-Oturum-CSRF-HTTP-Kaniti.md), [Iterasyon-21B-Güvenli-Dashboard-API-Kanıtı](../08-Uyum-Kanitlari/Erisim/Iterasyon-21B-Guvenli-Dashboard-API-Kaniti.md), [Iterasyon-21C-Dashboard-Operasyonel-Gösterge-API-Kanıtı](../08-Uyum-Kanitlari/Erisim/Iterasyon-21C-Dashboard-Operasyonel-Gosterge-API-Kaniti.md)

## Kontrol Durumu

- Teknik geçiş: **Devam ediyor; İterasyon 17A–17E, 18A–18C, 19A–19H, 20A–20E, 21A–21C, 22A–22I, 23A–23D, 24A–24B, 25A–25D, 26A–26B, 27A, 28A–28E, 29A–29C, 30B–30D, 31A–31C, 32A–32D, 33A–33B, 34A–34F ve 35A–35F TechnicallyVerified**
- BDDK/KVKK teknik kontrol eşlemesi: **Proposed**
- Banka bilgi güvenliği onayı: **ComplianceReviewRequired**
- Banka hukuk/uyum onayı: **ComplianceReviewRequired**
- Üretim uygunluğu: **Hazır değil**

## İlgili Belgeler

- [Bankacılık Uyum Modülü](../01-SRS/17-Bankacilik-Uyum/INDEX.md)
- [Güvenlik Mimarisi](../02-Mimari/Guvenlik/INDEX.md)
- [Bankacılık Geçiş İterasyonları](../09-Iterasyonlar/ITERASYON-INDEX.md)
- [Uyum Kanıtları](../08-Uyum-Kanitlari/KANIT-INDEX.md)

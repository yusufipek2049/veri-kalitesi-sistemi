---
type: project-memory
status: active-transition
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-21
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

- İterasyon 1–16, Iterasyon 17A–17E, Iterasyon 18A–18C, Iterasyon 19A–19H, Iterasyon 20A–20C, Iterasyon 21A, Iterasyon 22A–22I, Iterasyon 23A–23D, Iterasyon 24A–24B, Iterasyon 25A–25D, Iterasyon 26A–26B, Iterasyon 27A, Iterasyon 28A–28E, Iterasyon 29A–29C ve Iterasyon 31A teknik dikeyleri tamamlanmış ve proje hafızasına kaydedilmiştir.
- `pytest` sonucu: **863 test geçti**; tam mypy kontrolü 129 kaynak dosyada
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
- CSV ve PostgreSQL bağlayıcı sözleşmeleri, metadata keşfi, temel profilleme, kural testleri, idempotent execution, zamanlama, sürümlü kaynak kullanım politikasıyla worker/sorgu kotası, iptal/timeout, hiyerarşik skorlama ve SOURCE/ENTERPRISE dashboard ağacı uygulanmıştır.
- LDAP tabanlı fake adaptör/eşleme, kalıcı kullanıcı/istemci giriş sınırı ve güvenli normal kullanıcı oturumu doğrulanmıştır. Hedef kimlik sınırı LDAP destekli kurumsal IdP/SSO, OIDC veya SAML ve zorunlu MFA olarak kesinleşmiştir; gerçek IdP/RBAC, issue resolver bağlantıları, üretim session/cookie sınırı, HTTP API, raporlama ve gerçek ServiceNow ağ adaptörü henüz uygulanmamıştır.
- Merkezi audit zarfı authorization, veri kaynağı, kural, schedule oluşturma ve skor konfigürasyonu aktivasyonunda kullanılmaktadır; auditli kalıcı domain yazımları transactional outbox kullanır. Aktif legacy audit API kullanımı kalmamıştır. Tarihsel `audit_records` için salt okunur, redaksiyonlu ve idempotent aktarım sözleşmesi sentetik verilerle doğrulanmıştır; gerçek üretim koşusu yapılmamıştır.
- Kural, skor konfigürasyonu ve veri kaynağı aktivasyon onay işlemleri güvenilir `ActorContext` kullanır; diğer bazı servis işlemlerinde `actor_id` çağıran tarafından serbest metin olarak verilebilmektedir.
- Public dashboard sorguları scope kabul etmez; güvenilir context'i scope'a çeviren authorization servisini kullanır. Skor ağacı ve sabit son 30 günlük trend domain sorgusu yetki filtrelidir; internal/deprecated geçiş adaptörü henüz kaldırılmamıştır.
- Metadata sınıflandırması sürümlü teknik sözlük kullanır; sınıfsız alanlar fail-closed `UNCLASSIFIED` olur ve profil kalıcılığı ham örnek/top-value/desen payloadlarını çıkarır. Kişisel ve özel nitelikli kişisel alanlar sürümlü işleme envanteriyle ilişkilendirilebilir ve salt okunur tamlık raporuyla denetlenir; banka sözlük eşlemesi henüz tamamlanmamıştır.
- Yerel güvenli SDLC paketi secret taraması, doğrudan bağımlılık SBOM'u, veri-minimum SAST/bağımlılık zafiyet kapıları, sızma testi bulgu takibi, deterministik teknik kanıt manifesti, drift kapısı ve bunları birleştiren yerel preflight komutunu içerir. Gerçek scanner/pentest, transitive lock, CI/CD zorlaması, imzalı kurumsal kanıt deposu, banka eşik/istisna ve release onayı uygulanmamıştır.
- Sürümlü saklama politikası kataloğu, append-only legal hold, idempotent imha kanıtı ve audit/kalite skoru arşivleri için farklı aktör kararlı geri çağırma talep sözleşmesi uygulanmıştır. Tüm retention yazımları veri-minimum ve atomik auditlidir; fiziksel imha/anonimleştirme/arşivleme ile gerçek arşiv getirme adaptörleri uygulanmamıştır.
- Sürümlü ortam başlangıç kapısı güvenilir sağlayıcı sözleşmesini, ortam-secret kapsam eşleşmesini ve üretim dışı gerçek banka verisi/üretim secret engelini fail-closed uygular. Gerçek deployment/attestation sağlayıcısı, secret manager ve veri kökeni kanıtı henüz bağlı değildir.
- Yerel metadata ve execution deposu SQLite'tır; bu, üretim mimarisi kararı değildir.

## Korunacak Kazanımlar

Aşağıdaki davranışlar geriye dönük bozulmamalıdır:

1. Kaynak erişiminin salt okunur olması.
2. Secret değerinin metadata ve audit içinde saklanmaması.
3. Teknik hata ile kalite başarısızlığının ayrılması.
4. `NO_DATA`, `PARTIAL`, `TIMEOUT` ve teknik hata durumlarının sıfır skora çevrilmemesi.
5. RuleVersion ve scoring configuration geçmişinin değişmez kalması.
6. İdempotent execution ve scheduler tetikleme.
7. Yetkisiz SOURCE drill-down'ın repository çağrısından önce reddedilmesi.
8. 855 mevcut birim testinin ve sıfır hatalı tam mypy baseline'ının geriye dönük korunması.
9. Sınıflandırılmamış veya hassas alanların ham profil değerlerinin kalıcılaştırılmaması.

## En Kritik Kontrol Boşlukları

| Sıra | Boşluk | Mevcut risk | İlk hedef iterasyon |
| --- | --- | --- | --- |
| 1 | Güvenilir aktör bağlamı tüm servislere yayılmadı | Dashboard dikey dilimi korumalıdır; diğer servislerde serbest `actor_id` sürmektedir | İterasyon 20+ |
| 2 | Audit üretim operasyonlaştırması tamamlanmadı | Tarihsel aktarım sözleşmesi doğrulandı; gerçek ortam koşusu ve outbox publisher worker'ı henüz yok | Operasyon artımı / banka onayı |
| 3 | Banka sınıflandırma eşlemesi ve kurumsal referans doğrulaması tamamlanmadı | Kişisel/özel nitelikli kişisel alanlar için tamlık denetimi var; müşteri/banka sırrı eşlemesi ve referans kayıt doğrulaması yok | Banka onayı |
| 4 | Maker-checker kapsamı tamamlanmadı | Kritik kural/skor ve veri kaynağı aktivasyonu, kural/kaynak onay geri çekme, 3/10 iş günlük süre aşımı, bağlantı revizyon geçersizleştirme ve kontrollü kaynak pasifleştirme korunur; gerçek banka takvimi/worker işletimi, diğer kritik işlem sınıfları, çalışan iş politikası ve banka rol eşlemesi açık | Banka kararı |
| 5 | Kurumsal IdP/SSO-MFA ve RBAC üretim entegrasyonu tamamlanmadı | 20A context'i dashboard authorization'a bağlar; 20B giriş sınırı, 20C normal session uygular; gerçek IdP endpoint/protokol yapılandırması, banka eşlemesi, ayrıcalıklı/servis oturumu ve üretim altyapısı açık | Banka kararı / 21B öncesi |
| 6 | Operasyon ve kanıt katmanı kısmi | Ortam başlangıç kapısı, audit/rapor erişimi, güvenlik olayı, ihlal şüphesi, timeline, retention dry-run/legal hold/imha kanıtı ve arşiv geri çağırma yetkilendirmesi uygulanmıştır; gerçek ortam sağlayıcısı, DR, fiziksel/arşiv adaptörleri ve SIEM/SOC eksiktir | Banka/altyapı kararı |

## Geçiş Kapısı

Aşağıdaki maddeler tamamlanmadan yeni HTTP yüzeyi, hassas dışa aktarma veya banka pilotu açılmamalıdır:

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
- [ ] Kurumsal IdP/SSO-MFA grup-rol eşleme ve ayrıcalıklı erişim yönü kayıt altındadır. Mevcut sürümlü eşleme, fail-closed adaptör, kullanıcı/istemci giriş sınırı ve normal kullanıcı session yaşam döngüsü teknik olarak doğrulanmıştır; gerçek IdP adaptörü, banka eşleme değerleri, ayrıcalıklı/servis oturumu ve üretim bağlantısı açık kalır. Kanıtlar: [Iterasyon-20A-LDAP-RBAC-Sozlesme-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-20A-LDAP-RBAC-Sozlesme-Kaniti.md), [Iterasyon-20B-Basarisiz-Giris-Sinirlandirma-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-20B-Basarisiz-Giris-Sinirlandirma-Kaniti.md), [Iterasyon-20C-Guvenli-Oturum-Yasam-Dongusu-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-20C-Guvenli-Oturum-Yasam-Dongusu-Kaniti.md)

## Kontrol Durumu

- Teknik geçiş: **Devam ediyor; İterasyon 17A–17E, 18A–18C, 19A–19H, 20A–20C, 21A, 22A–22I, 23A–23D, 24A–24B, 25A–25D, 26A–26B, 27A, 28A–28E ve 29A–29C TechnicallyVerified**
- BDDK/KVKK teknik kontrol eşlemesi: **Proposed**
- Banka bilgi güvenliği onayı: **ComplianceReviewRequired**
- Banka hukuk/uyum onayı: **ComplianceReviewRequired**
- Üretim uygunluğu: **Hazır değil**

## İlgili Belgeler

- [Bankacılık Uyum Modülü](../01-SRS/17-Bankacilik-Uyum/INDEX.md)
- [Güvenlik Mimarisi](../02-Mimari/Guvenlik/INDEX.md)
- [Bankacılık Geçiş İterasyonları](../09-Iterasyonlar/ITERASYON-INDEX.md)
- [Uyum Kanıtları](../08-Uyum-Kanitlari/KANIT-INDEX.md)

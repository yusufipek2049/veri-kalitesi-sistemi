---
type: project-memory
status: active-transition
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-20
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

- İterasyon 1–16, Iterasyon 17A–17E, Iterasyon 18A–18C, Iterasyon 19A–19C, Iterasyon 20A–20C, Iterasyon 21A, Iterasyon 22A–22I, Iterasyon 23A–23D, Iterasyon 24A–24B, Iterasyon 26A–26B, Iterasyon 28A–28E ve Iterasyon 29A–29B teknik dikeyleri tamamlanmış ve proje hafızasına kaydedilmiştir.
- `pytest` sonucu: **682 test geçti**.
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
- CSV ve PostgreSQL bağlayıcı sözleşmeleri, metadata keşfi, temel profilleme, kural testleri, idempotent execution, zamanlama, kota, iptal/timeout, hiyerarşik skorlama ve SOURCE/ENTERPRISE dashboard ağacı uygulanmıştır.
- LDAP adaptör/eşleme, kalıcı kullanıcı/istemci giriş sınırı ve güvenli normal kullanıcı oturumu fake adaptörle doğrulanmıştır. Veri-minimum bildirim, issue yaşam döngüsü ve ServiceNow ticket oluşturma sözleşmesi uygulanmıştır; gerçek LDAP/RBAC, issue resolver bağlantıları, üretim session/cookie sınırı, HTTP API, raporlama ve gerçek ServiceNow ağ adaptörü henüz uygulanmamıştır.
- Merkezi audit zarfı authorization, veri kaynağı, kural, schedule oluşturma ve skor konfigürasyonu aktivasyonunda kullanılmaktadır; auditli kalıcı domain yazımları transactional outbox kullanır. Aktif legacy audit API kullanımı kalmamıştır. Tarihsel `audit_records` için salt okunur, redaksiyonlu ve idempotent aktarım sözleşmesi sentetik verilerle doğrulanmıştır; gerçek üretim koşusu yapılmamıştır.
- Kural ve skor konfigürasyonu onay işlemleri güvenilir `ActorContext` kullanır; diğer bazı servis işlemlerinde `actor_id` çağıran tarafından serbest metin olarak verilebilmektedir.
- Public dashboard sorguları scope kabul etmez; güvenilir context'i scope'a çeviren authorization servisini kullanır. Skor ağacı ve sabit son 30 günlük trend domain sorgusu yetki filtrelidir; internal/deprecated geçiş adaptörü henüz kaldırılmamıştır.
- Metadata sınıflandırması sürümlü teknik sözlük kullanır; sınıfsız alanlar fail-closed `UNCLASSIFIED` olur ve profil kalıcılığı ham örnek/top-value/desen payloadlarını çıkarır. Kişisel ve özel nitelikli kişisel alanlar sürümlü işleme envanteriyle ilişkilendirilebilir ve salt okunur tamlık raporuyla denetlenir; banka sözlük eşlemesi henüz tamamlanmamıştır.
- Yerel güvenli SDLC paketi secret taraması, doğrudan bağımlılık SBOM'u, veri-minimum SAST/bağımlılık zafiyet kapıları, sızma testi bulgu takibi, 15 kontrollük deterministik teknik kanıt manifesti ve byte düzeyinde drift kapısını içerir. Gerçek scanner/pentest, transitive lock, CI/CD zorlaması, imzalı kurumsal kanıt deposu, banka eşik/istisna ve release onayı uygulanmamıştır.
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
8. 682 mevcut birim testinin geriye dönük korunması.
9. Sınıflandırılmamış veya hassas alanların ham profil değerlerinin kalıcılaştırılmaması.

## En Kritik Kontrol Boşlukları

| Sıra | Boşluk | Mevcut risk | İlk hedef iterasyon |
| --- | --- | --- | --- |
| 1 | Güvenilir aktör bağlamı tüm servislere yayılmadı | Dashboard dikey dilimi korumalıdır; diğer servislerde serbest `actor_id` sürmektedir | İterasyon 20+ |
| 2 | Audit üretim operasyonlaştırması tamamlanmadı | Tarihsel aktarım sözleşmesi doğrulandı; gerçek ortam koşusu ve outbox publisher worker'ı henüz yok | Operasyon artımı / banka onayı |
| 3 | Banka sınıflandırma eşlemesi ve kurumsal referans doğrulaması tamamlanmadı | Kişisel/özel nitelikli kişisel alanlar için tamlık denetimi var; müşteri/banka sırrı eşlemesi ve referans kayıt doğrulaması yok | Banka onayı |
| 4 | Maker-checker kapsamı tamamlanmadı | Kritik kural ve skor aktivasyonu ile kural isteği geri çekme korunur; süre aşımı, veri kaynağı aktivasyonu ve banka rol eşlemesi açık | İterasyon 19D+ |
| 5 | LDAP/RBAC üretim entegrasyonu tamamlanmadı | 20A context'i dashboard authorization'a bağlar; 20B giriş sınırı, 20C normal session uygular; gerçek endpoint/TLS, banka eşlemesi, ayrıcalıklı/servis oturumu ve üretim altyapısı açık | Banka kararı / 21B öncesi |
| 6 | Operasyon ve kanıt katmanı kısmi | Audit/rapor erişimi ile güvenlik olayı, ihlal şüphesi ve yetkili timeline inceleme uygulanmıştır; DR, saklama ve gerçek SIEM/SOC akışı eksiktir | Banka/altyapı kararı |

## Geçiş Kapısı

Aşağıdaki maddeler tamamlanmadan yeni HTTP yüzeyi, hassas dışa aktarma veya banka pilotu açılmamalıdır:

- [x] Güvenilir `ActorContext` / `AuthorizationContext` sözleşmesi uygulanmış ve negatif testleri geçmiştir. Kanıt: [Iterasyon-16-Guvenilir-Aktor-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-16-Guvenilir-Aktor-Kaniti.md)
- [x] Public dashboard erişim kapsamı yalnız güvenilir authorization adaptöründen üretilmektedir. Kanıt: [Iterasyon-16-Guvenilir-Aktor-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-16-Guvenilir-Aktor-Kaniti.md)
- [x] Merkezi audit olay sözleşmesi uygulanmıştır. Kanıt: [Iterasyon-17A-Merkezi-Audit-Kaniti](../08-Uyum-Kanitlari/Audit/Iterasyon-17A-Merkezi-Audit-Kaniti.md)
- [x] Audit bütünlük ve audit-yazma-hatası politikası banka kararı için açıkça modellenmiştir. Kanıt: [Iterasyon-17A-Merkezi-Audit-Kaniti](../08-Uyum-Kanitlari/Audit/Iterasyon-17A-Merkezi-Audit-Kaniti.md)
- [x] Tarihsel audit için kaynak kaydı değiştirmeyen, redaksiyonlu ve idempotent aktarım sözleşmesi sentetik verilerle doğrulanmıştır. Kanıt: [Iterasyon-17E-Tarihsel-Audit-Aktarim-Kaniti](../08-Uyum-Kanitlari/Audit/Iterasyon-17E-Tarihsel-Audit-Aktarim-Kaniti.md)
- [x] Teknik veri sınıflandırma sözlüğü ve varsayılan profil minimizasyon politikası uygulanmıştır; banka etiket eşlemesi açık kalır. Kanıt: [Iterasyon-18A-Siniflandirma-ve-Profil-Minimizasyonu-Kaniti](../08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-18A-Siniflandirma-ve-Profil-Minimizasyonu-Kaniti.md)
- [x] Kişisel ve özel nitelikli kişisel alanlar için işleme envanteri kapsam/tamlık kontrolü uygulanmıştır; banka etiket eşlemesi açık kalır. Kanıt: [Iterasyon-18C-Envanter-Tamlik-Kaniti](../08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-18C-Envanter-Tamlik-Kaniti.md)
- [ ] Kritik konfigürasyonlarda maker-checker uygulanmıştır. Kritik kural, skor konfigürasyonu ve kural isteği geri çekme alt kapsamları teknik olarak doğrulanmıştır; süre aşımı, kalan kritik işlem listesi ve banka rol eşlemesi açıktır. Kanıtlar: [Iterasyon-19A-Kural-Maker-Checker-Kaniti](../08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19A-Kural-Maker-Checker-Kaniti.md), [Iterasyon-19B-Skorlama-Maker-Checker-Kaniti](../08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19B-Skorlama-Maker-Checker-Kaniti.md), [Iterasyon-19C-Kural-Onay-Geri-Cekme-Kaniti](../08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19C-Kural-Onay-Geri-Cekme-Kaniti.md)
- [ ] LDAP grup-rol eşleme ve ayrıcalıklı erişim kararları kayıt altındadır. Sürümlü eşleme, fail-closed adaptör, kullanıcı/istemci giriş sınırı ve normal kullanıcı session yaşam döngüsü teknik olarak doğrulanmıştır; banka değerleri, ayrıcalıklı/servis oturumu ve üretim bağlantısı açık kalır. Kanıtlar: [Iterasyon-20A-LDAP-RBAC-Sozlesme-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-20A-LDAP-RBAC-Sozlesme-Kaniti.md), [Iterasyon-20B-Basarisiz-Giris-Sinirlandirma-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-20B-Basarisiz-Giris-Sinirlandirma-Kaniti.md), [Iterasyon-20C-Guvenli-Oturum-Yasam-Dongusu-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-20C-Guvenli-Oturum-Yasam-Dongusu-Kaniti.md)

## Kontrol Durumu

- Teknik geçiş: **Devam ediyor; İterasyon 17A–17E, 18A–18C, 19A–19C, 20A–20C, 21A, 22A–22I, 23A–23D, 24A–24B, 26A–26B, 28A–28E ve 29A–29B TechnicallyVerified**
- BDDK/KVKK teknik kontrol eşlemesi: **Proposed**
- Banka bilgi güvenliği onayı: **ComplianceReviewRequired**
- Banka hukuk/uyum onayı: **ComplianceReviewRequired**
- Üretim uygunluğu: **Hazır değil**

## İlgili Belgeler

- [Bankacılık Uyum Modülü](../01-SRS/17-Bankacilik-Uyum/INDEX.md)
- [Güvenlik Mimarisi](../02-Mimari/Guvenlik/INDEX.md)
- [Bankacılık Geçiş İterasyonları](../09-Iterasyonlar/ITERASYON-INDEX.md)
- [Uyum Kanıtları](../08-Uyum-Kanitlari/KANIT-INDEX.md)

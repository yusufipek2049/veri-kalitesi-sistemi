---
type: canonical-decision-register
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-24
---

# Temel ve Mimari Karar Kayıtları

Bu belge temel teknik yönleri, değişken politika yaklaşımını ve `OPEN-001–OPEN-018` karar paketini kanonik olarak toplar. Mimari özet için `02-Mimari/Mimari-Kararlar.md` kullanılır.

> Tam tarihsel kaynak: [Arşivlenmiş karar günlüğü](../../docs/archive/project-memory-2026-07-24/Alinan-Kararlar.md).

## Teknik ve Mimari Kararlar

1. **Bağlayıcı geliştirme sırası:** Önce PostgreSQL bağlayıcısı üretim seviyesine çıkarılacak, ardından CSV bağlayıcısı tamamlanacaktır. `KararAlındı`
2. **PostgreSQL erişim yaklaşımı:** `psycopg 3` ve SQLAlchemy bağlantı havuzu kullanılan senkron worker modeli uygulanacaktır. `KararAlındı`
3. **Entegrasyon test ortamı:** CI içinde geçici PostgreSQL konteyneri ve kurum içinde kalıcı entegrasyon veritabanı birlikte kullanılacaktır. `KararAlındı`
4. **20 milyon satırlık performans verisi:** Önce gerçek dağılımları taklit eden sentetik veri, ardından anonimleştirilmiş veriyle kabul testi yapılacaktır. `KararAlındı`
5. **HEAVY/LIGHT sınıflandırması:** Tahmini satır sayısı, sorgu maliyeti, geçmiş çalışma süresi ve kaynak kapasitesi birlikte değerlendirilerek birleşik maliyet skoru üretilecektir. `KararAlındı`
6. **Kaynak bazlı sorgu kotası:** Her kaynak için ayrı `LIGHT`, `HEAVY` ve toplam eşzamanlı sorgu kotası tutulacaktır. Nihai değerler kapasite testiyle belirlenecektir. `KararAlındı`
7. **Üretim iş kuyruğu:** Bankanın kurumsal broker standardı kullanılacaktır. Kurumsal standart bulunmaması halinde RabbitMQ tercih edilecektir. `KararAlındı`
8. **Timeout ve iptal:** Bağlantı, sorgu ve toplam çalışma timeoutları ayrı, kaynak bazında ve sürümlü konfigürasyonla taşınacaktır. Süre dolduğunda sürücü seviyesinde gerçek sorgu iptali zorunludur. `KararAlındı`
9. **Dağıtım platformu:** Pilot aşamada VM/konteyner, üretimde kurum içi OpenShift/Kubernetes veya bankanın eşdeğer konteyner platformu kullanılacaktır. `KararAlındı`
10. **Üretim veritabanı:** Kurum tarafından işletilen yüksek erişilebilir PostgreSQL kullanılacaktır. Kurumsal PostgreSQL hizmeti yoksa bankanın standart ilişkisel veritabanı ürünü esas alınacaktır. `KararAlındı`
11. **İş sürekliliği:** Normal iç sistem kapsamı için `RTO=4 saat`, `RPO=15 dakika`; sistem BCBS 239, risk verisi veya düzenleyici raporlama zincirine girerse `RTO=1 saat`, `RPO=5 dakika` uygulanacaktır. `KararAlındı`
12. **Zamanlama grameri:** Beş alanlı POSIX cron alt kümesi, zorunlu timezone ve tanımlı DST davranışı desteklenecektir. `KararAlındı`
13. **Secret yönetimi:** Bankanın kurumsal secret manager/PAM ürünü kullanılacaktır. Platform secret mekanizması yalnız geçici entegrasyon katmanı olabilir; açık metin ortam değişkeni kalıcı çözüm değildir. `KararAlındı`
14. **Kimlik doğrulama:** Kurumsal IdP üzerinden OIDC veya SAML SSO kullanılacak; LDAP grupları rol ve scope yetkilendirmesine kaynak olacaktır. `KararAlındı`
15. **Ayrıcalıklı erişim:** IdP MFA, PAM, süreli ayrıcalık ve çift onaylı break-glass modeli uygulanacaktır. `KararAlındı`
16. **ActorContext sınırı:** `ActorContext` yalnız güvenilir kimlik/session adaptörü tarafından üretilebilecek; servislerdeki serbest `actor_id` kullanımı kademeli olarak kaldırılacaktır. `KararAlındı`
17. **Başarısız giriş sınırlandırması:** Asıl kullanıcı kilitleme IdP/LDAP tarafından yönetilecek; uygulama endpoint ve güvenilir istemci referansı bazlı rate limit uygulayacaktır. `KararAlındı`
18. **Kullanıcı oturumu:** BFF üzerinde sunucu taraflı opak session kullanılacaktır. Hareketsizlik süresi **1 saat**, mutlak oturum süresi **10 saat**, kullanıcı başına eşzamanlı aktif oturum sayısı **1** olacaktır. Yeni başarılı giriş mevcut aktif oturumu iptal eder. Tarayıcı yalnız `__Host-session` adlı `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`, domainsiz opak cookie taşır; access/refresh token tarayıcıya açılmaz. State-changing istekler synchronizer token, custom header, Origin/Referer, Fetch Metadata ve CORS allowlist kontrollerinden geçer. Oturum sırrı kapanışta derhal silinir; veri-minimum güvenlik metadatası `P90D` saklanır. `ApprovedByBank`
19. **Şema değişikliği:** Yalnız değişen tablo/kolonla ilişkili aktif kurallar `REVIEW_REQUIRED` durumuna alınacaktır. `KararAlındı`
20. **QualityDimension kimliği:** Kalıcı UUID’ye sahip boyut tablosu oluşturulacak; `COMPLETENESS` gibi değişmez iş kodu ayrıca korunacaktır. `KararAlındı`
21. **Dataset kritiklik ağırlığı:** Temel katsayılar `LOW=0.75`, `MEDIUM=1.00`, `HIGH=1.25`, `CRITICAL=1.50` olacaktır. Dataset türüne göre farklı katsayı tanımlanabilecek ve bu bilgi sürümlü politika tablosunda tutulacaktır. Aktif özel kayıt yoksa temel katsayıya dönülecektir. `Superseded` — `DQ-SCR-018` ve `ADR-015` uyarınca bu katsayılar ham kalite agregasyonuna katılmaz; geçmiş sonuçlar korunur. Kritiklik ve risk için ayrı sürümlü politika zorunludur; politika yoksa risk sonucu üretilmez.
22. **Kurum skorunda kaynak ağırlığı:** Dataset kritiklik ve iş etkisine göre normalize edilmiş ağırlık kullanılacak; gerekçeli ve maker-checker onaylı kontrollü override desteklenecektir. `Superseded` — `DQ-SCR-018`, `DQ-SCR-019` ve `DQ-SCR-023` uyarınca kritiklik/risk ham kalite skorundan, onaylı değerlendirme de ham skordan ayrı tutulur. Kurum ham kalite özeti `ENTERPRISE_EQUAL_WEIGHT_V1` ile eşit kaynak ağırlığında hesaplanır; yeni politika ancak ayrı sürüm ve onayla etkinleştirilir.
23. **Kısmi çalıştırma skoru:** Kısmi çalışma yalnız onaylı dataset politikasındaki tüm koşulları sağlarsa resmî skora katılabilecek; aksi halde ayrı `PROVISIONAL` skor ve kapsama oranıyla gösterilecektir. `KararAlındı`
24. **Maker-checker kapsamı:** Kritik kurallar, veri kaynağı aktivasyonu, skor konfigürasyonu, hassas dışa aktarma ve güvenlik istisnaları maker-checker kapsamındadır. Onay için hedef süre **3 iş günü**, otomatik sona erme süresi **10 iş günü** olacaktır. Süre istek oluşturulduğunda başlar; banka iş günü takvimi kullanılır; sona eren istek onaylanamaz ve yeniden oluşturulmalıdır. `KararAlındı`
25. **Veri sınıflandırma eşlemesi:** Banka sözlüğüne eşlenmeyen teknik sınıflandırma kodlarında fail-closed davranışı uygulanacaktır. `KararAlındı`
26. **Audit hata davranışı:** Kritik değişiklikler audit yazılamadığında fail-closed olacaktır. Salt okunur veya düşük riskli işlemler durable buffer’a alınabilir; buffer da kullanılamıyorsa işlem fail-closed olur. `KararAlındı`
27. **Durable buffer/outbox:** PostgreSQL transactional outbox ve ayrı publisher worker kullanılacaktır. İş kaydıyla outbox kaydı aynı veritabanı transaction’ında oluşturulacaktır. `KararAlındı`
28. **Audit bütünlüğü:** Resmî audit kopyası kurumsal log/SIEM veya immutable object storage üzerinde WORM, imza ve hash doğrulamasıyla tutulacaktır. Uygulama içi hash-chain ek savunma katmanı olabilir. `KararAlındı`
29. **Saklama ve imha:** Aşağıdaki kayıt türü bazlı politika uygulanacaktır. Süreler teknik politika olarak seçilmiş olup hukuk/KVKK komitesi ve iç denetim onayına kadar `KararAlındı` durumundadır.
30. **Eski SQLite audit aktarımı:** Tek değişiklik penceresinde; kaynak yedeği, idempotent aktarım, kayıt sayısı/hash mutabakatı ve geri dönüş planıyla merkezi depoya geçirilecektir. `KararAlındı`
31. **ServiceNow entegrasyonu:** Asenkron outbox, veri-minimum allowlist, güvenilir servis hesabı, TLS/mTLS, retry, DLQ ve circuit breaker kullanılacaktır. `KararAlındı`
32. **Issue ana kayıt kaynağı:** Uygulama ana kayıt sistemi olacaktır. Yalnız `HIGH/CRITICAL` veya SLA ihlali oluşturan issue’lar ServiceNow’a aktarılacaktır. `KararAlındı`
33. **Bildirim ve atama çözümlemesi:** Veri sahibi → yedek sorumlu grup → Veri Yönetişimi operasyon grubu fallback zinciri uygulanacaktır. `KararAlındı`
34. **SIEM/SOC ve kişisel veri ihlali:** Güvenlik olayları SIEM’e aktarılacak, banka olay sözlüğüyle seviyelendirilecek, 72 saat hedefi farkındalık anından başlayacak ve dış bildirim farklı yetkili aktörün insan kararını gerektirecektir. `KararAlındı`
35. **Frontend ve dashboard:** React + TypeScript + MUI + ECharts, Vite, Storybook ve Playwright kullanılacaktır. Banka ana rengi `#fdb813` design-token olarak tanımlanacak; 7/30/90 gün ve özel tarih aralığı desteklenecektir. `KararAlındı`
36. **Kod kalitesi ve güvenli SDLC:** Kullanıcı beyanına göre tamamlanmıştır. Ayrıntılı scanner, CI/CD, mypy, SAST, secret, SCA/SBOM, DAST, pentest ve kanıt kayıtları proje deposundaki teknik kanıtlarda tutulacaktır. `Tamamlandı`

## Dataset Kritiklik Ağırlığı Politika Modeli

Temel politika kaydı bütün dataset türleri için fallback oluşturur:

| Dataset türü | LOW | MEDIUM | HIGH | CRITICAL |
| --- | ---: | ---: | ---: | ---: |
| `*` | 0.75 | 1.00 | 1.25 | 1.50 |

Dataset türü özelindeki katsayılar daha yüksek öncelikli kayıtlarla değiştirilebilir; bu dosyada henüz tür bazlı özel katsayı belirlenmemiştir.

Önerilen kalıcı tablo:

```sql
CREATE TABLE dataset_criticality_weight_policy (
    policy_id UUID PRIMARY KEY,
    policy_version INTEGER NOT NULL,
    dataset_type_code VARCHAR(100) NOT NULL,
    criticality_level VARCHAR(20) NOT NULL,
    weight NUMERIC(8,4) NOT NULL CHECK (weight > 0),
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ NULL,
    status VARCHAR(20) NOT NULL,
    reason TEXT NOT NULL,
    maker_actor_id UUID NOT NULL,
    checker_actor_id UUID NULL,
    approved_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (policy_version, dataset_type_code, criticality_level)
);
```

Çözümleme sırası:

1. Aktif dataset türü + kritiklik seviyesi kaydı.
2. Aktif `*` + kritiklik seviyesi temel kaydı.
3. Eşleşme yoksa fail-closed konfigürasyon hatası.

## KVKK ve Bankacılık Saklama–İmha Teknik Politikası

Bu bölümdeki kayıt sınıfları ve süreler kullanıcı kararıyla yürürlükteki teknik
politika olarak kabul edilmiştir. Hukuk, KVKK komitesi, bilgi güvenliği ve iç
denetim incelemesi teknik kararın uygulanması ve banka onayı için ayrı kapıdır;
bu kayıt tek başına `ApprovedByBank` sonucu üretmez.

### Hesaplama kuralı

- Hukuki süreler sabit `365 × yıl` biçiminde hesaplanmayacaktır; `P10Y`, `P5Y`, `P3Y`, `P1Y` gibi takvimsel ISO-8601 süreleri kullanılacaktır.
- `expires_at = trigger_at + calendar_duration`
- İmha yükümlülüğü doğduktan sonra periyodik imha aralığı en fazla `P180D` olacaktır.
- Legal hold, dava, denetim veya resmî inceleme varsa otomatik imha askıya alınır; erişim kapsamı daraltılır ve hold kaldırılınca kayıt yeniden değerlendirilir.
- Aşağıdaki “kapasite günü”, depolama kapasitesi hesabı için üst sınırdır; hukuki son tarih takvimsel süreyle hesaplanır.

| Politika kodu | Kayıt sınıfı ve örnekleri | Süre başlangıcı | Takvimsel süre | Kapasite günü | İmha yöntemi / not |
| --- | --- | --- | --- | ---: | --- |
| `RET-10Y-BANKING` | Resmî veri kalitesi çalıştırması ve skor metadata’sı; kural/konfigürasyon sürümleri; maker-checker kararları; kritik audit; issue/incident yaşam döngüsü; ServiceNow eşleme kaydı; rapor metadata’sı, onayı ve indirme auditi; kişisel veri ihlali karar ve kanıtları | Kayıt kapanışı, sürümün yürürlükten kalkması veya olayın kapanışı | `P10Y` | 3653 | Süre sonunda silme/yok etme; kanıtın kişisel veri içermeyen bölümü anonimleştirilebilir |
| `RET-5Y-REGLOG` | Diğer kurum/kuruluş verilerine web servis/API sorgu izleri; rutin yetki/audit görüntüleme logları; SIEM olay özeti; sürüm bazlı SBOM, SAST/DAST/pentest kanıt özeti | Sorgu, erişim, olay veya sürüm kapanışı | `P5Y` | 1827 | Kişisel alanlar minimize edilir; süre sonunda yok etme |
| `RET-3Y-ERASURE` | Silme, yok etme ve anonimleştirme işlemlerinin kanıt kayıtları | İmha işlemi tarihi | En az `P3Y` | 1096 | Değişmez/auditli saklama; üç yıl dolmadan silinemez |
| `RET-1Y-OPS` | Sistem içi bildirim teslim kayıtları; geçici atama resolver sonucu; resmî skora girmeyen test çalıştırması geçmişi | İşlem kapanışı | `P1Y` | 366 | Süre sonunda yok etme; resmî karara dönüşen kayıt `RET-10Y-BANKING` sınıfına yükseltilir |
| `RET-90D-TRANSIENT` | Sonlandırılmış normal kullanıcı oturumunun veri-minimum güvenlik metadatası; başarısız giriş/rate-limit opak anahtarları; terminal durumdaki retry/outbox/DLQ payloadları; ayrıntılı teknik uygulama logları ve geçici hata içerikleri | Oturum kapanışı, son başarısız giriş veya terminal iş durumu | `P90D` | 90 | Session sırrı ve access/refresh token tutulmaz; uzun süreli audit için yalnız veri-minimum olay özeti ayrıştırılır |
| `RET-30D-EXPORT` | Üretilmiş PDF/XLSX/CSV dosyası; rapor önizleme cache’i; maskeli geçici test extract’i; kontrollü kaynak örneği | Dosya üretimi veya test kapanışı | `P30D` | 30 | Şifreli depolama; süre sonunda kriptografik silme/yok etme; indirme bağlantısı en fazla 7 gün |
| `RET-ACTIVE-SESSION` | Aktif opak normal kullanıcı session'ı | Son etkinlik veya session oluşturma | `PT1H` inactivity ve `PT10H` absolute | — | Süre dolunca session iptal edilir, sır/credential derhal silinir ve veri-minimum güvenlik metadatası `RET-90D-TRANSIENT` sınıfına geçer |
| `RET-ANON` | Geri döndürülemez biçimde anonimleştirilmiş toplulaştırılmış metrikler | Anonimleştirme tarihi | Amaç devam ettiği sürece | — | Kişisel veri sayılmaz; yıllık yeniden kimliklendirme riski değerlendirmesi yapılır |

### Yedek ve periyodik imha

- Birincil kayıtta süre dolduğunda kayıt normal kullanıcılar için derhal erişilemez hâle getirilir.
- Yedeklerde kalan kopyalar, yedek döngüsü içinde ve en geç `P180D` içinde geri getirilemez biçimde imha edilir.
- Yedekten geri yükleme yapılırsa süresi dolmuş kayıtlar otomatik “re-delete” işiyle yeniden silinir.
- İmha işinin kendisi `RET-3Y-ERASURE` kapsamında kayıt altına alınır.
- İlgili kişi talebi en geç 30 gün içinde sonuçlandırılır; başka bir hukuki işleme şartı sürüyorsa gerekçeli ret/erteleme kaydı üretilir.

### Hukuki dayanak notu

Bu sınıflandırma şu kuralları birlikte uygular:

- KVKK kapsamında veri, ilgili mevzuatta öngörülen veya işleme amacı için gerekli olan süre kadar tutulur; amaç ortadan kalkınca silinir, yok edilir veya anonimleştirilir.
- Kişisel veri saklama ve imha politikasında kayıt türü bazlı süre tablosu bulunur; periyodik imha aralığı altı ayı geçemez.
- Silme, yok etme ve anonimleştirme işlemlerinin kayıtları diğer hukuki yükümlülükler hariç en az üç yıl saklanır.
- 5411 sayılı Bankacılık Kanunu madde 42 kapsamına giren bankacılık faaliyeti belgeleri on yıl saklanır.
- Diğer kurum/kuruluş verilerine web servis veya API üzerinden yapılan sorguların iz kayıtları için BDDK düzenlemesindeki beş yıllık süre uygulanır.
- Mevzuatta özel süre bulunmayan geçici ve operasyonel kayıtların süreleri amaçla sınırlılık ve ölçülülük ilkesiyle belirlenmiştir.

> Bu tablo karara bağlanmış teknik politikadır. `RET-10Y-BANKING` kapsamının
> mevzuata dayalı nihai eşlemesi banka hukuk/uyum ve bilgi güvenliği incelemesine
> tabidir; teknik karar mevzuat uygunluğu onayı değildir.

## OPEN-001–OPEN-018 Kesinleşmiş Kararları

| ID | Kesinleşen karar |
| --- | --- |
| OPEN-001 | Düşük, beklenen ve yüksek kapasite senaryoları kullanılacak; gerçek üretim envanteri üretime geçiş kriteridir. |
| OPEN-002 | Worker ve eş zamanlı sorgu sınırları kaynak bazlı sürümlü politika tablosunda yönetilecek; kaynak değeri global güvenli varsayılanı geçersiz kılabilir. |
| OPEN-003 | Çalışma penceresi, CPU/IO, süre, kota, yoğun saat ve iptal davranışı OPEN-002 ile aynı kaynak kullanım politikasında tutulacak; politikasız kontrolsüz sorgu çalışmayacak. |
| OPEN-004 | Ürün bağımsız kurumsal secret manager servis/workload identity ile kullanılacak; açık metin secret ve yerelde üretim secret'ı yasaktır. |
| OPEN-005 | Kimlik doğrulama LDAP destekli kurumsal IdP/SSO üzerinden OIDC veya SAML ile yapılacak; uygulama LDAP şemasına bağımlı olmayacak. |
| OPEN-006 | İlk fazdan itibaren tüm insan kullanıcılar için kurumsal IdP SSO ve MFA zorunludur. |
| OPEN-007 | Tek süre yerine kayıt sınıfı bazlı saklama/imha matrisi ve bu belgede tanımlı teknik süreler kullanılacak. |
| OPEN-008 | RPO/RTO bileşen bazında yönetilecek; normal kapsamda `RPO=PT15M`, `RTO=PT4H`, kritik düzenleyici/risk zincirinde `RPO=PT5M`, `RTO=PT1H` uygulanacak. |
| OPEN-009 | ServiceNow ara entegrasyon tablosu veya entegrasyon servisi üzerinden dayanıklı ve idempotent yürütülecek. |
| OPEN-010 | Sınıflandırma kurumsal veri kataloğu veya DLP sisteminden alınacak; kesintide bilinen hassas sınıf düşürülmeyecek. |
| OPEN-011 | Rapor dosyası `RET-30D-EXPORT`, rapor metadata ve onay kayıtları `RET-10Y-BANKING` ile yönetilecek; dosya boyutu aktif sürümlü rapor politikasında zorunlu olacak ve politika yoksa üretim reddedilecek. |
| OPEN-012 | Maker-checker yalnız tanımlı yüksek riskli değişikliklerde zorunludur; talep eden onaylayamaz. |
| OPEN-013 | Bağlayıcı sırası yaygın ilişkisel veritabanı, dosya/CSV, ikinci ilişkisel ürün ve API'dir; ürün adı kurum kararı olmadan sabitlenmez. |
| OPEN-014 | 20 milyon satırlık test yalnız onaylı, anonimleştirilmiş ve yeniden kimliklendirme riski değerlendirilmiş üretim örneğiyle yapılacak. |
| OPEN-015 | Uygulama WCAG 2.2 AA'yı hedefleyecek; otomatik teste ek manuel klavye ve ekran okuyucu testi yapılacak. |
| OPEN-016 | API ve worker kurumsal konteyner platformunda, veri tabanı ayrı yüksek erişilebilirlik kümesinde çalışacak; kalıcı dosya yerel diske bağlı olmayacak. |
| OPEN-017 | Kritik işlem audit/outbox hatasında fail-closed; rutin olaylarda kayıpsız dayanıklı kuyruk veya transactional outbox uygulanacak. |
| OPEN-018 | Kısmi sonuç yalnız dataset politikasındaki tüm koşulları sağlarsa resmîdir; aksi halde provizyonel olup resmî skor, SLA, trend ve raporlamadan dışlanır. |

## 2026-07-22 — Değişken Politika Değerlerinin Kesinleştirilmesi

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Kapasite, kaynak kullanımı, skorlama, yeterlilik, risk ve sentetik doğrulama gibi ortama veya kullanım bağlamına göre değişen sayısal değerler kodda sabitlenmeyecek; aktif, sürümlü ve gerekli onayı taşıyan politika kaydından çözülecektir. Politika yoksa işlem veya olumlu karar fail-closed reddedilecektir. | Tek bir varsayımsal sayıyı üretim değeri saymak kaynak güvenliğini, skor doğruluğunu ve yeniden üretilebilirliği bozar. Kullanıcı teknik yönü kesinleştirmiştir; değer değişikliği yönetişimli politika işlemidir. | Değerleri karar bekleyen yer tutucular olarak bırakmak; yerel varsayılanları üretime taşımak; eksik politikada en son değeri örtük kullanmak. | `OPEN-019`–`OPEN-024` karar yönleri `KararAlındı` durumundadır. Politika kayıtlarının oluşturulması uygulama/operasyon işidir; eksik kayıt karar belirsizliği değil fail-closed konfigürasyon durumudur. |
| Sentetik üreticinin üretim profili veya örneğinden öğrenmesi varsayılan olarak yasaktır. Yalnız veri sahibi, hukuk/KVKK ve bilgi güvenliği onaylı; minimize edilmiş, izole ortam ve saklama politikası bağlı referansla ayrı politika sürümünde açılabilir. | Sentetik etiketinin anonimlik kanıtı sayılmasını ve üretim verisinin kontrolsüz biçimde test ortamına taşınmasını engellemek gerekir. | Üretim profilini varsayılan açık kullanmak veya yalnız teknik ekip onayıyla etkinleştirmek. | `OPEN-025` teknik yönü `KararAlındı`dır; gerekli kurumsal incelemeler `ComplianceReviewRequired` olarak ayrı kalır. |

## OPEN-019–OPEN-025 Kesinleşmiş Politika Yönleri

Bu kimlikler yeni sayısal değer üretmez; ilgili değerlerin sürümlü/onaylı
politika kaydından çözülmesini ve kayıt yokluğunda fail-closed davranışı
kanonikleştirir.

| ID | Kesinleşen kapsam | Durum |
| --- | --- | --- |
| OPEN-019 | Normalizasyon, eşik, ağırlık, kritik veto/tavan/blokaj, kapsam, güven ve veri risk değerleri aktif, sürümlü ve gerekli onaylı politikadan çözülür; politika yoksa olumlu sonuç üretilmez. | KararAlındı |
| OPEN-020 | Boyut uygulanabilirliği, dataset kritiklik profili ve veri riski kalite skorundan ayrı tutulur; tek kalite yüzdesine eritilmez. | KararAlındı |
| OPEN-021 | İstisna ve ham skordan ayrı değerlendirme/override; izinli tür, süre, risk kabulü, maker-checker ve raporlama politikasıyla yönetilir. | KararAlındı |
| OPEN-022 | Eski kanoniksiz skorların yeni modelle replay/backfill ilişkisi, trend sürüm sınırı ve append-only geçişi ayrı migration/uygulama diliminde yürütülür; tarihsel sonuç yerinde değiştirilmez. | KararAlındı |
| OPEN-023 | Ölçüm yeterliliği, kullanım kararı, kapsam/güven kanıtı, rol ve remediation/eskalasyon değerleri sürümlü politikadan çözülür; eksik politikada olumlu yeterlilik/kullanım kararı üretilmez. | KararAlındı |
| OPEN-024 | Sentetik veri dağılım, korelasyon, görev faydası, gizlilik, kusur yoğunluğu ve skor toleransları aktif sürümlü doğrulama politikasından çözülür; eksikse doğrulama `BLOCKED` olur. | KararAlındı |
| OPEN-025 | Sentetik üreticinin üretim profili veya örneğinden öğrenmesi varsayılan kapalıdır; yalnız veri sahibi, hukuk/KVKK ve bilgi güvenliği onaylı, minimize ve izole politika ile açılabilir. | KararAlındı; kurumsal inceleme ayrıca gerekir |

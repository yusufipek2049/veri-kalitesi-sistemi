---
type: canonical-decision-register
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-24
---

# API, Frontend ve PostgreSQL Karar Kayıtları

Bu belge API sözleşmesi, frontend teknoloji/yazma davranışı ve PostgreSQL-only geçiş kararlarını kanonik olarak toplar.

> Tam tarihsel kaynak: [Arşivlenmiş karar günlüğü](../../docs/archive/project-memory-2026-07-24/Alinan-Kararlar.md).

## 2026-07-22 — API-001–API-015 Teknik Kararları

Karar referansı: `USER-DECLARATION-2026-07-22-API-001-015`. Bu kararlar teknik
yönü kesinleştirir; üretim altyapısının veya bankacılık geçiş kapısının
tamamlandığı anlamına gelmez.

| ID | Karar | Durum |
| --- | --- | --- |
| API-001 | HTTP framework olarak FastAPI kullanılacaktır. | KararAlındı |
| API-002 | İlk BFF sınırı mevcut backend içinde modüler tutulacak; bağımsız servis ayrımı ihtiyaç ve ölçek kanıtıyla değerlendirilecektir. | KararAlındı |
| API-003 | Dış HTTP sözleşmesi REST ve OpenAPI olacaktır. | KararAlındı |
| API-004 | İlk bağlı dikey dilim dashboard özeti olacaktır. | KararAlındı |
| API-005 | Kalıcılık repository sınırı arkasında SQLAlchemy 2 ve Alembic ile yönetilecektir. | KararAlındı |
| API-006 | Gerçek IdP bağlanana kadar yalnız local/test ortamında sunucu taraflı geliştirme aktörü kullanılabilir; üretim varsayılanı fail-closed olacaktır. | KararAlındı |
| API-007 | Üretim kimlik akışı OIDC/SAML kullanan BFF üzerinden yürütülecek; access ve refresh token tarayıcıya açılmayacaktır. | KararAlındı |
| API-008 | İlk frontend istemcisi tipli `fetch` kullanacak; ek sorgu kütüphanesi yalnız kanıtlanmış ihtiyaçla değerlendirilecektir. | KararAlındı |
| API-009 | API hata zarfı RFC 9457 Problem Details ve güvenli correlation ID kullanacaktır. | KararAlındı |
| API-010 | URL tabanlı `/api/v1` sürümleme uygulanacaktır. | KararAlındı |
| API-011 | Yerel geliştirme portları frontend `5173`, API `8000`, PostgreSQL `5433` olacaktır. | KararAlındı |
| API-012 | Yerel CORS yalnız onaylı frontend origin allowlist'ine izin verecek; üretimde aynı origin hedeflenecektir. | KararAlındı |
| API-013 | Özet okumaları senkron, kural çalıştırma ve raporlama gibi uzun işlemler kalıcı kuyruk üzerinden yürütülecektir. | KararAlındı |
| API-014 | HTTP yanıtları domain modellerini doğrudan açmak yerine veri-minimum response DTO kullanacaktır. | KararAlındı |
| API-015 | API ve worker aynı kod tabanında bağımsız süreçler olarak ölçeklenebilecektir. | KararAlındı |

İterasyon 21B, `API-001/003/004/006/008–012/014` kararlarının dashboard okuma
alt kapsamını uygulamıştır. Alembic bağımlılığı envantere alınmış, ancak bu
iterasyonda şema değişikliği olmadığı için migration üretilmemiştir. İterasyon
20E cookie/CSRF ve BFF resolver sınırını teknik olarak doğrulamıştır. Gerçek
OIDC/SAML callback ve kalıcı PostgreSQL skor deposu ayrı artımlardır.

## 2026-07-22 — FE-DEC-001–004 Frontend Kararları

Karar referansı: `USER-DECLARATION-2026-07-22-FE-DEC-001-004`.

| ID | Karar | Gerekçe | Durum |
| --- | --- | --- | --- |
| FE-DEC-001 | Navigasyon ve kaynak türü ikonlarında `lucide-react` kullanılacak; kurumca ürünü kesinleşmemiş kaynaklarda vendor logosu yerine ürün bağımsız database/file/API ikonları gösterilecektir. | Görsel hizayı ve erişilebilir ikon kullanımını standartlaştırırken doğrulanmamış ürün/marka iddiası oluşturmamak gerekir. | KararAlındı |
| FE-DEC-002 | İstemci routing katmanı `react-router-dom` ile kurulacak; route bazlı code splitting ile yetkisiz ve bulunamadı durum sınırları desteklenmelidir. | Menü öğelerinin gerçek sayfalara bağlanması, ekranların bağımsız yüklenmesi ve güvenli durum yüzeylerinin tutarlı yönetilmesi gerekir. | KararAlındı |
| FE-DEC-003 | İlk açılışta açık tema kullanılacak; kullanıcı açık/koyu seçimi yalnız `light` veya `dark` değeri olarak `localStorage` içinde saklanacaktır. | Varsayılan görsel baseline korunurken tema tercihi hassas veri veya kimlik bilgisi saklamadan kalıcı olmalıdır. | KararAlındı |
| FE-DEC-004 | Dashboard ölçüm yeterliliği son geçerli ölçümden, kritik kontrol özeti son tamamlanan execution'dan, teknik hata özeti seçili dönemden ve varsayılan olarak son 30 UTC günden hesaplanacaktır. | Üç göstergenin farklı zaman anlamlarını tek snapshot gibi göstermemek ve mevcut 30 günlük dashboard filtresiyle teknik hata sayımını tutarlı kılmak gerekir. | KararAlındı |

Bu kararlar frontend dependency ve gösterim sözleşmesini kesinleştirir; 21C
yeterlilik runtime/API uygulamasını veya banka marka onayını tamamlanmış saymaz.
20E güvenli BFF sınırı daha sonra teknik olarak doğrulanmıştır.

## 2026-07-23 — PostgreSQL-only ve Yazılabilir Arayüz Yol Haritası Kararı

Karar referansı: `USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI`.

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Uygulama kalıcılığının hedef durumu yalnız PostgreSQL olacaktır. Runtime ve entegrasyon testlerinde SQLite fallback bulunmayacak; birim testleri gerekirse kalıcı veritabanı yerine fake domain double kullanacaktır. Geçiş SQLAlchemy 2 ve Alembic üzerinden küçük domain dilimleriyle yapılacaktır. | SQLite foreign key iyileştirmesine yatırım yapmak, kaldırılacak kalıcılık yolunu büyütür. Tek ilişkisel platform migration, transaction, concurrency ve üretim davranışını tutarlı kılar. | SQLite bütünlük iyileştirmesi yapmak; iki veritabanını süresiz desteklemek; tüm repository'leri tek seferde dönüştürmek. | `R-06` iptal edilmiştir. 36A PostgreSQL-only kalıcılık temelini ve ilk issue repository geçişini hazırlayacaktır. Her domain PostgreSQL'e taşındığında ilgili SQLite uygulaması ve fallback'i kaldırılacaktır. |
| Salt okunur 35A–35F ekranlarından sonra yazma yetenekleri 36B–36F sırasında açılacaktır: Sorunlar; Kurallar; Veri Kaynakları; Çalıştırmalar; Raporlar/Denetim sınırı. | Mevcut domain servislerinde issue yaşam döngüsü en olgun ve kaynak sisteme yazmayan ilk kullanıcı işlemidir. Daha riskli kural, kaynak aktivasyonu, çalıştırma ve dışa aktarma işlemleri güvenlik bağımlılıklarıyla sonra gelmelidir. | Tüm ekranları aynı anda yazılabilir yapmak; önce kaynak aktivasyonu veya dışa aktarma açmak; geçici SQLite mutasyon API'leri eklemek. | 36B issue atama/inceleme/çözüm/doğrulama/kapatma; 36C kural taslak/test/onay; 36D kaynak tanım/revizyon/test/aktivasyon; 36E çalıştırma başlatma/iptal/retry; 36F rapor talebi ve güvenli indirme alt kapsamlarını ele alacaktır. Audit kayıtları değişmez ve salt okunur kalır. |

Bu karar kaynak sistemlere salt okunur erişim ilkesini değiştirmez. Yazma
yeteneği yalnız uygulamanın sahip olduğu metadata, politika, iş akışı ve sonuç
kayıtlarını etkiler. Her mutasyon güvenilir aktör, BFF/CSRF, rol/kapsam,
gerektiğinde maker-checker, veri-minimum audit ve fail-closed hata davranışını
korur. Karar üretim altyapısının kurulduğu veya banka onayının alındığı anlamına
gelmez.

### Kesinleşen Uygulama Seçenekleri

| ID | Kesinleşen seçenek | Durum |
| --- | --- | --- |
| `PG-MIG-001` | Seçici taşıma: audit, issue, onay, politika, kural sürümü ve iş geçmişi idempotent salt okunur aktarılır; sentetik fixture, cache ve yeniden üretilebilir geliştirme verisi PostgreSQL üzerinde yeniden oluşturulur. | KararAlındı |
| `PG-MIG-002` | Tek `data_quality` veritabanında özel `dq` uygulama şeması kullanılır; domain ayrımı repository ve tablo sınırlarıyla korunur. | KararAlındı |
| `PG-MIG-003` | Domain bazlı kontrollü cutover uygulanır: yazma penceresi kapatılır, veri taşınır, sayaç/hash/foreign key doğrulanır ve trafik PostgreSQL'e alınır. Dual-write yapılmaz. | KararAlındı |
| `PG-MIG-004` | Yalnız ileri Alembic migration uygulanır; `downgrade` üretim geri alma yöntemi değildir. Hata yeni düzeltici migration ile giderilir. Cutover öncesi PostgreSQL yedeği ve geri yükleme operasyonel felaket koruması olarak ayrıca korunur. SQLite runtime fallback kullanılmaz. | KararAlındı |
| `PG-MIG-005` | Repository testleri transaction rollback, migration ve eşzamanlılık testleri benzersiz geçici PostgreSQL şeması kullanır. | KararAlındı |
| `UI-WRITE-001` | Sorun atama/inceleme, çözüm ve doğrulama ayrı uygulama yetkinlikleridir; IdP grupları daha sonra bu yetkinliklere eşlenir ve çözen aktör doğrulama yapamaz. | KararAlındı |
| `UI-WRITE-002` | Yazılabilir issue ve sonraki uygun varlıklarda sayısal `version` ile optimistic locking uygulanır; sürüm çakışması `409 Conflict` üretir. | KararAlındı |
| `UI-WRITE-003` | Formlar açık “Kaydet” işlemiyle sunucuya yazılır; kaydedilmemiş değişiklikte çıkış uyarısı gösterilir. Hassas taslak `localStorage` içinde tutulmaz. | KararAlındı |
| `UI-WRITE-004` | Düşük riskli kural taslağı yetkili tek kullanıcı tarafından düzenlenebilir; kritik kural, aktivasyon/pasifleştirme, eşik ve ağırlık değişikliği maker-checker gerektirir. | KararAlındı |
| `UI-WRITE-005` | Veri kaynağı aktivasyonu Data Owner, farklı checker ve aynı bağlantı revizyonuna ait başarılı salt okunur bağlantı testi gerektirir. | KararAlındı |
| `UI-WRITE-006` | Manuel çalıştırma doğrudan worker başlatmaz; kaynak politikası, kota, çalışma penceresi ve idempotency kontrolünden sonra kuyruğa alınır. | KararAlındı |
| `UI-WRITE-007` | Rapor indirme sınıflandırma bazlı açılır: sentetik/düşük hassasiyetli raporlar yetkili kapsamda; hassas raporlar DLP, watermark, gerekçe ve gerektiğinde maker-checker tamamlanınca. Eksik kontrolde işlem fail-closed kalır. | KararAlındı |

Karar referansı:
`USER-DECLARATION-2026-07-23-PG-MIG-004-FORWARD-ONLY-OTHERS-RECOMMENDED`.
Bu seçimler uygulama yönünü kesinleştirir; banka rol/grup değerleri, üretim
altyapısı ve hassas dışa aktarma onayı ayrıca doğrulanır.

## Eksik Kimlik Tamamlama Kaydı

| ID | Karar | Durum |
| --- | --- | --- |
| FE-DS-015 | Route, yetkisiz erişim ve bulunamadı durumlarını taşıyan istemci navigasyon kabuğu | Must; 35A ile `TechnicallyVerified` |


## Uygulama Etki Durumu — 2026-07-24

Bu bölüm yeni karar değildir; yukarıdaki kesin kararların kod/doküman etkisini
özetler.

- `PG-MIG-001–005` issue domaininde seçici aktarım ve PostgreSQL-only runtime
  yoluyla uygulanmıştır.
- `UI-WRITE-001–003` issue inceleme, yeniden atama, çözüm, doğrulama ve kapatma
  akışlarında uygulanmıştır; kapatma/yeniden açma için güncel doğrulama kaydı
  `36B5` altında beklemektedir.
- `UI-WRITE-006` için execution API, migration ve PostgreSQL repository vardır;
  `PostgreSQLExecutionStartService`/`PostgreSQLExecutionCancelService` adaptörleri
  ile production composition root cutover'ı tamamlanmıştır;
  `SQLiteExecutionRepository` runtime export'tan çıkarılmıştır. Karar uygulanmıştır.
- `UI-WRITE-007` kurumsal DLP/watermark/maker-checker kapıları çözülmeden
  fail-closed ve blokeli kalır.

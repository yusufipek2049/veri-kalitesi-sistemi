---
type: decision-log
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-21
tags:
  - proje
  - karar
  - adr
---

# Alınan Kararlar

| Karar | Durum | Gerekçe / Not |
| --- | --- | --- |
| Kurum adı dokümanda “Kurum” olarak anonim tutulacak. | Kesin | Kurumsal gizlilik. |
| Üretim sistemi kurum içi veri merkezinde çalışacak. | Kesin | Veri merkezi dışına veri çıkarılmaması. |
| Kullanıcı doğrulaması LDAP destekli kurumsal IdP/SSO üzerinden OIDC veya SAML ve zorunlu MFA ile yapılacak. | Kesin | Uygulama LDAP şemasına doğrudan bağımlı olmayacak. |
| Zorunlu bildirim kanalı yalnız sistem içi bildirim olacak. | Kesin | E-posta, SMS ve üçüncü taraf mesajlaşma ilk faz dışında. |
| Kurumsal ticket entegrasyonu için ServiceNow, ara entegrasyon tablosu veya entegrasyon servisi üzerinden kullanılacak. | Kesin tercih | Ürün alan/durum eşlemesi ve erişim ayrıntıları açık. |
| Saklama ve imha kayıt sınıfı bazlı politika matrisiyle yönetilecek. | Kesin yön ve teknik süre matrisi karara bağlandı | Hukuk, KVKK, bilgi güvenliği ve iç denetim incelemesi teknik karardan ayrı izlenecek. |
| Kaynak sistem erişimleri salt okunur olacak. | Kesin | Kaynak verisinde otomatik düzeltme veya silme yapılmayacak. |
| Yerel prototip i7-13620H, 16 GB RAM ve RTX 4050 sınıfı bilgisayarda çalışacak. | Kesin ortam | Üretim kapasitesini tek başına temsil etmiyor. |
| 20 milyon satırlık referans testinde onaylı anonimleştirilmiş üretim örneğiyle örnekleme, bölümleme veya kaynakta toplulaştırma kullanılacak. | Kesin teknik yaklaşım | Yerel bellek ve kaynak sistem yükünü sınırlarken test verisi gizliliğini korumak için. |
| Yerel prototipte modüler monolit, iş kuyruğu ve ilişkisel metadata deposu önerilecek. | Öneri | Teknoloji seçimi SRS tarafından zorunlu kılınmıyor. |
| Kalite skoru, ölçüm yeterliliği, teknik çalışma durumu ve kullanım kararı ayrı sonuçlar olacak. | Kesin hedef tasarım; sayısal değerler sürümlü ve onaylı politika kaydından çözülecek | Yüksek skorun eksik, eski veya teknik olarak başarısız ölçümü gizlemesini engellemek için. Kanonik sözleşme `02-Mimari/Veri-Kalitesi-Skorlama-ve-Olcum-Yeterliligi.md` dosyasındadır. |

## 2026-07-16 Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-16 | İlk çalışan backend artımı framework bağımsız Python paketi ve SQLite metadata deposu olarak başlatıldı. | Repo henüz kod içermiyordu; küçük, test edilebilir ve dış servis gerektirmeyen bir dikey dilim gerekliydi. | İlk iterasyonda FastAPI/ORM/worker iskeleti kurmak. | Domain mantığı HTTP/ORM katmanına gömülmeden ilerlenebilecek temel oluşturuldu. |
| 2026-07-16 | Yerel prototipte ham secret saklanmayacak; yalnız `secret://...` biçimli referans kabul edilecek ve config içinde secret anahtarları reddedilecek. | Kurumsal secret manager ürünü açık konu; buna rağmen `FR-009` ve `NFR-SEC-005` ihlal edilmemeli. | Geçici olarak ortam değişkeni veya açık metin test parolası saklamak. | Secret manager seçilene kadar kod ve metadata deposu ham secret kabul etmeyecek. |
| 2026-07-16 | PostgreSQL bağlayıcısı gerçek sürücüye doğrudan bağımlı olmayacak; sürücü bir protokol arkasında kalacak ve domain testleri fake driver ile çalışacak. | Harici DB bağımlılığını birim testlerine taşımamak ve sürücü/paket seçimi açıkken test edilebilir sözleşme kurmak. | İlk artımda `psycopg` gibi somut bir paket eklemek. | Canlı entegrasyon testleri sonraki iterasyonda gerçek sürücü ve ortam seçilince eklenecek. |
| 2026-07-16 | PostgreSQL bağlantı tanımında `ssl_mode` yalnız `require`, `verify-ca` veya `verify-full` olabilir. | `NFR-SEC-003` aktarım şifreleme hedefini varsayılan davranış yapmak. | TLS kapalı veya opsiyonel bağlantıya izin vermek. | TLS kapalı bağlantılar kaynak oluşturma aşamasında reddedilecek. |
| 2026-07-16 | Metadata keşfi profil hesaplamasından ayrı bir ürün artımı olarak uygulanacak; ilk aşamada yalnız Dataset/DataField keşfi ve şema farkı saklanacak. | Profil metrikleri farklı performans ve örnekleme kararları gerektiriyor; metadata temeli kural/profil akışlarının ön koşulu. | Metadata keşfi ve temel profillemeyi tek iterasyonda yapmak. | Profil metrikleri bir sonraki iterasyona bırakıldı. |
| 2026-07-16 | Şema değişikliğinde aktif kurallar henüz fiziksel olarak güncellenmeyecek; metadata değişimi `requires_rule_review` bayrağıyla raporlanacak. | Kural yönetimi modülü ve RuleVersion deposu henüz uygulanmadı. | Kural kayıtlarını şimdiden tahmini tablolarla modellemek. | Kural modülü geldiğinde bu bayrak gerçek kural durum geçişine bağlanacak. |
| 2026-07-16 | CSV profilleme yerel prototipte satır satır yapılacak; PostgreSQL profilleme kaynakta toplulaştırılmış metrik döndüren sürücü sözleşmesi üzerinden çalışacak. | CSV dosyası için dış servis gerekmeyen gösterilebilir artım gerekirken, büyük veritabanı tablolarında ham kayıt kopyalamamak gerekiyor. | Tüm kaynakları uygulama belleğine almak veya PostgreSQL için ham satır çekmek. | Büyük tablo örnekleme/toplulaştırma kararı connector sözleşmesinde yöntem ve örneklem oranıyla taşınacak. |
| 2026-07-16 | Profil sonuçlarında ham örnek değer saklanmayacak; yalnız toplulaştırılmış metrikler ve duplicate özetleri tutulacak. | `NFR-PRV-002` ve `NFR-PRV-003` gereği kişisel/hassas örneklerin kalıcı depoya taşınmaması gerekiyor. | Min/max dışı ham örnek değer veya en sık değer listesi saklamak. | Dağılım/desen gibi ham değere yaklaşabilecek analizler ayrı gizlilik kontrolüyle sonraki kapsamda ele alınacak. |
| 2026-07-16 | Kural yönetimi veri kaynağı modülünden ayrı `rules` paketi ve enjekte edilebilir `RuleTestExecutor` sözleşmesiyle uygulanacak. | Kural tanımı, kaynak ürüne özgü güvenli yürütme ve zamanlama sorumluluklarını ayırmak; domain testlerini harici kaynağa bağlamamak. | Kural yürütmesini doğrudan veri kaynağı servisine eklemek. | Kaynak bağlayıcıları sonraki çalıştırma artımında bu sözleşmeye salt-okunur adaptör sağlayabilecek. |
| 2026-07-16 | RuleVersion kayıtları değişmez olacak; her mantık veya eşik değişikliği artan numaralı yeni sürüm üretecek ve test geçmişi çalıştığı sürüme bağlanacak. | `FR-029` ve `RULE-007` tarihsel sonuçların yeniden yorumlanmasını engelliyor. | Mevcut kural kaydını yerinde güncellemek. | Eski sürüm tanımı ve ona bağlı test sonuçları korunur. |
| 2026-07-16 | Test çalıştırmasının `% başarı` değeri yalnız önizleme skoru olarak saklanacak ve `official_score_included=false` olacak. | `UC-006` testin resmi skora etki etmemesini zorunlu kılıyor; resmi skor durumları sonraki skorlama artımının sorumluluğu. | Test sonucunu doğrudan QualityScore olarak yazmak. | Test sonucu doğrulanabilir kalırken kurumsal skor zinciri etkilenmez. |
| 2026-07-16 | Yerel prototipte `rule_executions` tablosundaki `QUEUED` kayıtları kalıcı iş kuyruğu olarak kullanılacak. | Harici broker ürünü seçilmeden idempotent, transaction ile kalıcı ve birim testlerinde gösterilebilir manuel iş akışı gerekiyor. | İlk aşamada Redis/RabbitMQ/Kafka bağımlılığı eklemek veya yalnız bellek içi kuyruk kullanmak. | Zamanlama ve worker aynı kalıcı claim sözleşmesini kullanabilir; üretim broker seçimi açık konu olarak kalır. |
| 2026-07-16 | İdempotency anahtarının açık değeri saklanmayacak; anahtar ve normalize payload ayrı SHA-256 özetleriyle karşılaştırılacak. | Anahtar hassas bağlam içerebilir; aynı payload tekrarını ve farklı payload çakışmasını açık değeri depolamadan ayırmak gerekiyor. | Anahtarı metadata deposunda açık metin saklamak. | Tekrarlanan istek mevcut execution kimliğini döndürür, farklı payload kontrollü çakışma üretir. |
| 2026-07-16 | Worker geçici teknik hatalarda en fazla üç toplam deneme ve üstel gecikme uygulayacak; kalite başarısızlığı teknik olarak başarılı execution içinde sonuç sayacı olarak kalacak. | `FR-041`, `NFR-REL-001` ve `RULE-003` retry ile kalite başarısızlığının ayrılmasını zorunlu kılıyor. | Her başarısız sonucu retry etmek veya sınırsız denemek. | Teknik hata geçmişi deneme bazında izlenir; kalite hatası kaynak yükünü artıran gereksiz tekrar oluşturmaz. |
| 2026-07-16 | Zamanlama tarihleri UTC saklanacak, yerel takvim hesabı kayıtlı IANA saat dilimiyle yapılacak; DST'de var olmayan yerel saat atlanacak. | `RULE-015` ve `UC-007` tarihsel sıralama ile yerel plan davranışının açık olmasını gerektiriyor. | Naive datetime saklamak veya DST boşluğunu sessizce farklı saate taşımak. | Önizleme ve tetik aynı deterministik UTC anlarını kullanır; timezone metadata korunur. |
| 2026-07-16 | Scheduler idempotency anahtarı schedule kimliği ve planlanan UTC tetik anından üretilecek. | Scheduler yeniden başlarsa veya plan advance işlemi gecikirse aynı tetik için çift execution oluşmamalı. | Her scheduler taramasında rastgele anahtar üretmek. | Tek plan/tetik anı yalnız bir execution üretir; güvenli tekrar mevcut execution kimliğine çözülür. |
| 2026-07-16 | Execution iş sınıfı çağıran kullanıcıdan alınmayacak; enjekte edilebilir `WorkloadClassifier` tarafından HEAVY veya LIGHT olarak belirlenecek. | Kullanıcının kota sınıfını düşürerek kaynak korumasını aşması engellenmeli ve sınıflandırma politikası kaynak yürütücüsünden ayrılmalı. | İstek payloadında serbest `workload_class` kabul etmek. | Queue kaydı sınıfı ve kaynak kapsamını değişmez biçimde taşır; sınıflandırma politikası daha sonra merkezi maliyet tahminine bağlanabilir. |
| 2026-07-16 | Yerel queue claim varsayılanı 2 ağır, 4 hafif ve kaynak başına 1 ağır iş olacak; genel ve kaynak bazlı sınırlar yapılandırılabilir tutulacak. | `FR-039`, `NFR-PERF-006` ve `NFR-PERF-008` yerel prototip sınırlarını ve kaynak korumasını tanımlıyor. | Yalnız toplam worker sayısını sınırlamak. | Global kapasite uygun olsa bile kaynak ağır sorgu kotası aşılırsa iş QUEUED kalır. |
| 2026-07-16 | Bekleyen iş iptali doğrudan `CANCELLED`, çalışan iş iptali yürütücü adaptörüne iletilen kalıcı `CANCEL_REQUESTED` geçişi olarak uygulanacak. | `FR-042` iptal talebinin hızla kaydedilmesini ve çalışan sorgunun kontrollü kapatılmasını gerektiriyor. | Worker kaydını hemen terminal duruma çekmek veya yalnız bellek içi iptal bayrağı kullanmak. | İptal isteği denetlenebilir ve idempotent kalır; somut kaynak sürücüsü sorgu iptalini adaptör üzerinden uygulayabilir. |
| 2026-07-16 | Timeout anına kadar tamamlanan bölüm sonuçları `PARTIAL` olarak saklanacak ve `eligible_for_official_scoring=false` olacaktır; sonuçsuz timeout `TIMEOUT` kapanacaktır. | `AC-012`, `RULE-003` ve `RULE-004` kısmi teknik sonucu kalite başarısızlığına veya resmi skora çevirmemeyi gerektiriyor. | Kısmi sonuçları silmek, başarı saymak veya sıfır skor üretmek. | Tamamlanan bölümler izlenebilir kalır; resmi skor zinciri yalnız uygun tam sonuçları tüketir. |
| 2026-07-16 | Kural skoru `Decimal` ile hesaplanıp iki haneye `ROUND_HALF_UP` yöntemiyle yuvarlanacak ve `RULE_SCORE_V1` formül sürümüyle saklanacak. | `FR-047` sonucu iki ondalıkla ister; ikili kayan nokta ve örtük yuvarlama tarihsel skor tekrar üretilebilirliğini zayıflatır. | Python `float` ve varsayılan yuvarlamayı kullanmak. | Aynı sayaçlar her çalışmada aynı skoru üretir; formül sürümü hesaplama detayından açıklanabilir. |
| 2026-07-16 | `NO_DATA`, teknik hata ve politika dışı `PARTIAL` durumlarında `score_value` NULL kalacak; aynı execution/kural sürümü skoru idempotent olacaktır. | `FR-048`, `RULE-003` ve `RULE-004` hesaplanamayan sonucu sıfır kalite skoru olarak göstermeyi yasaklıyor. | Hesaplanamayan sonuç için 0 saklamak veya tekrar hesaplamada yeni geçmiş kaydı üretmek. | Teknik/veri yokluğu durumları kalite başarısızlığından ayrılır ve tekrar tetikleme skor geçmişini çoğaltmaz. |
| 2026-07-16 | Dataset ağırlıklı ortalamasının pay ve paydasına yalnız sayısal `CALCULATED` kural skorları katılacak; kullanılan ve dışlanan bileşenler sonuçta saklanacak. | `FR-049`, `RULE-004` ve `AC-013` hesaplanamayan alt skorların dataset skorunu yapay olarak düşürmesini engelliyor. | Hesaplanamayan skorları sıfır kabul etmek veya yalnız nihai değeri saklamak. | Dataset skoru açıklanabilir kalır; tüm alt skorlar hesaplanamazsa sayısal sonuç üretilmez. |
| 2026-07-16 | Dört sabit seviye ardışık üç sürümlü eşik sınırıyla temsil edilecek; varsayılan sürüm `DEFAULT_THRESHOLDS_V1`, dataset formülü `DATASET_WEIGHTED_V1` olacaktır. | `FR-051` eşiklerin 0–100 aralığını boşluk ve çakışma olmadan kapsamasını, `UC-009` kullanılan konfigürasyonun saklanmasını gerektiriyor. | Bağımsız min/max aralıkları veya sürümsüz sabit koşullar kullanmak. | Aralık sürekliliği yapısal olarak korunur; geçmiş skor hangi formül ve eşik sürümüyle üretildiğini taşır. |
| 2026-07-16 | Skor konfigürasyonları değişmez sürüm olarak saklanacak, depoda yalnız bir sürüm aktif olacak ve aktivasyon audit adaptörüne bildirilecek. | `FR-051`, `RULE-005`, `RULE-007` ve `NFR-MNT-006` yeni ayarın yalnız sonraki hesaplara uygulanmasını ve değişikliğin izlenmesini gerektiriyor. | Eşikleri süreç içi değişken olarak güncellemek veya eski konfigürasyonu yerinde değiştirmek. | Geçmiş skorlar yeniden yorumlanmaz; her yeni skor kullandığı konfigürasyon ve eşik sürümünü taşır. |
| 2026-07-16 | Boyut skoru dataset toplamından değil, `QualityRule.primary_dimension` ile seçilen kural skorlarından üretilecek. | Mevcut dataset skoru birden fazla boyutu tek değerde birleştirdiği için ondan boyut skoru türetmek kaybedilen bilgiyi geri üretemez. | Dataset skorunu doğrudan boyut skoru kabul etmek. | Boyut skoru gerçek alt kural bileşenlerini ve ağırlıklarını açıklayabilir; dataset ve boyut görünümleri bağımsız kalır. |
| 2026-07-16 | SOURCE skoru dataset skorlarını `Dataset.data_source_id` ile gruplayacak ve sürümlü dataset kritiklik ağırlıklarıyla hesaplanacak. | `FR-050` kaynak seviyesinde yapılandırılmış ağırlık ve açıklanabilir alt bileşen ister; metadata ilişkisi zaten kaynak-dataset bağını taşır. | Kural skorlarını doğrudan kaynağa toplamak veya kaynak kimliğini execution payloadından güvenmek. | Kaynak skoru dataset sınırını ve metadata ilişkisini korur; her bileşenin kritiklik ve ağırlığı sonuçta açıklanır. |
| 2026-07-16 | Kurum tarafından onaylanmış kritiklik katsayıları bulunana kadar LOW/MEDIUM/HIGH/CRITICAL dataset ağırlıkları `1.0` olacak. | SRS ağırlıkların pozitif ve yapılandırılabilir olmasını ister ancak varsayılan katsayı değerlerini tanımlamaz. | HIGH/CRITICAL datasetlere tahmini daha yüksek katsayı atamak. | Sistem belgede olmayan iş politikası üretmez; yönetişim uzmanı yeni sürümle açık katsayıları aktive edebilir. |
| 2026-07-16 | ENTERPRISE skoru, kurum düzeyi kaynak katsayıları onaylanana kadar geçerli SOURCE skorlarını eşit ağırlıkla toplulaştıracak. | SRS hiyerarşik agregasyonu ve açıklanabilirliği zorunlu kılıyor ancak kaynaklar arası katsayı veya türetme kuralı tanımlamıyor. | Dataset sayılarına göre örtük ağırlık vermek veya tahmini kaynak katsayıları eklemek. | Her kaynak kurum skoruna bir kez katılır; `EQUAL_SOURCE_WEIGHT` politikası ve dahil/dışlanan kaynaklar hesaplama detayında açıkça saklanır. |
| 2026-07-16 | Dashboard okuma servisi erişim kapsamını zorunlu `DashboardAccessScope` girdisiyle uygulayacak; ENTERPRISE görünürlüğü kaynak izinlerinden ayrı olacaktır. | Kısmi kaynak yetkisi olan kullanıcıya kurum skorunu göstermek yetkisiz kaynakların katkısı hakkında dolaylı veri sızdırabilir. | Repository sonucunu filtrelemeden dönmek veya kurum skorunu herhangi bir kaynak izniyle göstermek. | SOURCE düğümleri izinli kimliklerle filtrelenir; ENTERPRISE yalnız açık kurum yetkisiyle görünür ve doğrudan yetkisiz drill-down depoya ulaşmadan reddedilir. |
| 2026-07-16 | Dashboard güven sınırı değişmez ve güvenilir issuer tarafından üretilen `ActorContext` ile sürümlü `AuthorizationService` kararına dayanacak. | Serbest actor, rol veya scope girdisi yetki kanıtı değildir; yalnız veri sınıfı eklemek sahte context üretimini engellemez. | API girdisinden `DashboardAccessScope` kabul etmek veya context içindeki kapsamı doğrulamadan kullanmak. | Public dashboard sorgusu scope kabul etmez; sahte/eksik/süresi dolmuş/policy uyuşmaz context fail-closed reddedilir, eski yol internal/deprecated adaptörde sınırlıdır. |
| 2026-07-16 | Dashboard authorization karar audit özeti ham rol, session ve kapsam kimliklerini taşımayacak; bu dikey dilimde audit sink hatası erişimi fail-closed kapatacak. | Yetki kararı denetlenebilir olmalı, ancak audit çıktısı yeni bir hassas veri sızıntısı oluşturmamalıdır. | Audit olmadan erişime devam etmek veya tam context payloadını audit etmek. | Güvenli karar özeti üretilir; merkezi olay zarfı, bütünlük ve banka onaylı işlem bazlı hata politikası Iterasyon 17 ve `OPEN-BNK-005/006` kapsamında kalır. |
| 2026-07-16 | Merkezi audit olay zarfı kimlik modülünden bağımsız olacak ve `actor_type` sürümlü metin kodu taşıyacak. | Audit altyapısının kimlik paketine bağımlılığı döngüsel import oluşturur ve merkezi sınırın yeniden kullanılmasını engeller. | Audit modelinde doğrudan `ActorType` enumuna bağımlı olmak. | Kimlik servisi güvenilir enum değerini zarfa dönüştürür; audit paketi diğer modüllerce bağımsız kullanılabilir. |
| 2026-07-16 | Yerel audit bütünlüğü önceki olay hash'ine bağlı SHA-256 zinciriyle doğrulanacak; bu mekanizma yalnız tahrifat tespitidir. | WORM, dijital imza veya kurumsal SIEM ürünü `OPEN-BNK-006` kapsamında banka kararı bekliyor; buna rağmen küçük ve test edilebilir bir bütünlük sözleşmesi gerekiyor. | Ürün seçimini varsaymak veya hash zincirini tahrifat önleme olarak sunmak. | Değiştirilmiş olay doğrulanabilir; üretim değişmezliği ve harici kök güveni açık kalır. |
| 2026-07-16 | Audit yazma davranışı her kurulumda sürümlü `FAIL_CLOSED` veya `DURABLE_BUFFER` politikasıyla açıkça yapılandırılacak; durable mod tampon olmadan başlayamayacak. | Örtük hata yutma kritik işlemleri denetimsiz bırakabilir; tek davranışı tüm işlemler için varsaymak ise banka kararını önden belirler. | Audit hatasını sessizce yok saymak veya tüm olaylara sabit politika uygulamak. | Authorization dikeyi fail-closed kalır; üretim tamponu ve işlem bazlı banka kararı `OPEN-BNK-005` kapsamında sürer. |
| 2026-07-16 | Veri kaynağı ve kural servisleri merkezi `AuditSink` olmadan kurulamayacak; correlation ID verilmezse operasyon sınırında üretilecek. | Opsiyonel sink kritik olayların sessizce kaybolmasına, correlation eksikliği ise olay zincirinin izlenememesine yol açar. | Audit'i opsiyonel tutmak veya correlation alanını boş bırakmak. | İki servis tüm başarılı/teknik sonuç olaylarını ortak zarfa yollar; boş correlation iş yazımından önce reddedilir. |
| 2026-07-16 | Merkezi zarfa henüz taşınmayan model `data_sources` içinden çıkarılıp `LegacyAuditRecord` adıyla audit paketinde geçici olarak tutulacak. | Zamanlama ve skorlama bağımlılıklarını kırmadan legacy kullanımın açıkça görünmesi ve yeni modüllerce yanlışlıkla kullanılmaması gerekir. | `AuditRecord` sınıfını veri kaynağı domain modelinde bırakmak veya komşu modülleri aynı iterasyonda davranışsal olarak taşımak. | Veri kaynağı/kural yeni zarfa geçti; zamanlama/skorlama ve tarihsel kayıt aktarımı 17C backlogunda kaldı. |
| 2026-07-16 | Kritik oluşturma işlemlerinde merkezi audit tesliminden önce redakte olay, iş kaydıyla aynı SQLite transaction'ındaki outbox'a yazılacak. | Ayrı commit edilen iş ve audit, audit kesintisinde denetlenemeyen kalıcı iş kaydı bırakıyordu. | Audit'i iş commitinden sonra doğrudan yazmak veya işten önce başarı audit'i üretmek. | Outbox hatası iş yazımını rollback eder; merkezi kesintide redakte pending olay dayanıklı kalır. |
| 2026-07-16 | Merkezi audit deposu aynı `event_id` ve aynı içerik tekrarını idempotent kabul edecek, farklı içerik çakışmasını reddedecek. | Outbox yayıncısı merkezi kayıt başarılı olduktan sonra yerel işaretleme yapamadan kesilebilir; güvenli tekrar çift kayıt üretmemelidir. | Her retry için yeni event kimliği üretmek veya kimlik çakışmasında mevcut kaydı koşulsuz döndürmek. | Yayın tekrarları tek merkezi olayda birleşir; içerik değiştirme girişimi doğrulama hatasıdır. |
| 2026-07-16 | Veri kaynağı ve kural servislerindeki tüm auditli kalıcı yazımlar, redakte olayı domain kaydıyla aynı SQLite transaction'ındaki outbox'a yazacak. | Yalnız oluşturma işlemlerinin atomik olması; bağlantı, metadata, profil, sürüm, test ve aktivasyonda audit boşluğu bırakıyordu. | Kalan yazımlarda domain commitinden sonra doğrudan merkezi audit çağrısını sürdürmek. | Outbox-stage hatası hedeflenen her domain değişikliğini rollback eder; merkezi kesintide commit edilmiş işin redakte audit olayı `PENDING` kalır. |
| 2026-07-16 | Schedule oluşturma opsiyonel legacy sink yerine zorunlu transactional audit kullanacak; audit özeti yalnız zamanlama türü, saat dilimi, kural sayısı ve önizleme özetini taşıyacak. | Opsiyonel sink sessiz audit kaybına, ayrı commit denetlenemeyen schedule kaydına ve tam kural/zaman listesinin taşınması gereksiz veri yayılımına neden oluyordu. | Legacy sink'i korumak veya tam schedule tanımını merkezi audit olayına yazmak. | Schedule ve redakte outbox olayı atomikleşti; ad ve kural sürüm kimlikleri audit özetinden çıkarıldı. |
| 2026-07-16 | Skor konfigürasyonu aktivasyonu zorunlu transactional audit kullanacak; eşik ve ağırlıklar iç içe haritalar yerine sabit scalar audit alanlarıyla saklanacak. | Aktivasyon ve legacy audit ayrı commit ediliyordu; merkezi redactor yapısal haritaları veri minimizasyonu gereği özetten çıkarıyordu. | Legacy sink'i sürdürmek veya ağırlık haritalarını JSON metni olarak audit etmek. | Aktivasyon atomikleşti; eski/yeni konfigürasyon değerleri allowlist kontrollü ve karşılaştırılabilir kaldı. |
| 2026-07-16 | Tarihsel `audit_records` aktarımı kaynağı yalnız okuyacak; desteklenen kayıtları güncel redaksiyondan geçirip deterministik kimlikle merkezi zincire idempotent ekleyecek. | Kaynak geçmişini değiştirmeden güvenli tekrar sağlamak ve bozuk tarihsel veriyi teknik kesintiden ayırmak gerekir. | Legacy tabloyu yerinde güncellemek/silmek, her koşuda yeni kimlik üretmek veya bozuk satırları teknik hata olarak tüm aktarımı durdurmak. | Bozuk/desteklenmeyen satırlar özet kimlikli veri kalitesi raporuna alınır; merkezi depo hatası teknik hata verir. Gerçek üretim koşusu ayrıca operasyon, yedek ve değişiklik onayı gerektirir. |
| 2026-07-16 | Metadata sınıflandırması sürümlü teknik sözlük kullanacak; boş/eski serbest değerler `UNCLASSIFIED`, sözlük dışı yeni değerler doğrulama hatası olacak ve profil kalıcılığı yalnız allowlist toplulaştırılmış metrikleri kabul edecek. | Serbest metin sınıfı ve bağlayıcıdan gelen keyfi profil payloadı ham kişisel verinin metadata, profil veya audit içine taşınmasına yol açabilir. | Serbest metni korumak, bilinmeyen sınıfı düşük riskli saymak veya connector metriğini doğrudan saklamak. | Bilinmeyen sınıf fail-closed olur; eski aggregate metrikler korunurken örnek/top-value/desen alanları saklanmaz. Teknik kodların banka sözlüğü eşlemesi ve işleme envanteri açık kalır. |
| 2026-07-16 | Kişisel veri işleme envanteri DataField'e bağlı append-only sürümler olarak saklanacak; amaç, hukuki sebep, sahip, saklama, rol ve alıcı değerleri dış yönetişim referansı olacak, audit yalnız sınıf/sürüm/sayı özetini taşıyacak. | Banka kodlarını varsaymadan `BFR-DATA-004` ilişkilendirmesini sağlamak, geçmiş beyanları korumak ve envanter metadata'sını audit üzerinden sızdırmamak gerekir. | DataField kaydını yerinde güncellemek, serbest açıklamaları audit etmek veya varsayılan hukuki sebep/saklama süresi üretmek. | Her değişiklik yeni sürüm ve atomik redakte audit olayı oluşturur; banka referans doğrulaması ve tüm kişisel alanlar için kapsam kontrolü açık kalır. |
| 2026-07-16 | Envanter tamlık kontrolü banka eşlemesi onaylanana kadar yalnız `PERSONAL_DATA` ve `SPECIAL_CATEGORY_PERSONAL_DATA` sınıflarını kapsayacak; zorunlu alan bulunmayan kapsam `NO_REQUIRED_FIELDS` olarak raporlanacak. | Teknik sözlükteki müşteri/banka sırrı sınıflarına belgede olmayan kişisel veri anlamı yüklememek ve boş kapsamı uyumlu gibi göstermemek gerekir. | Tüm hassas sınıfları örtük kişisel saymak veya boş sonucu `COMPLETE` kabul etmek. | Eksik envanter veri kalitesi sonucu, depo okuma arızası teknik hata olur; banka sınıf eşlemesi ayrı onay konusu kalır. |
| 2026-07-16 | `CRITICAL` kural sürümü güvenilir maker context ile hazırlanacak; aktivasyon aynı kayıtlı maker isteğini ve farklı güvenilir checker kararını gerektirecek, karar doğrudan `RuleVersion` kimliğine bağlanacak. | Serbest aktör kimliğiyle görevler ayrılığı kanıtlanamaz ve eski sürüm onayının yeni içeriğe taşınması kontrolü geçersiz kılar. | Yalnız actor_id karşılaştırmak, onayı QualityRule düzeyinde tutmak veya aktivasyon/audit yazımını ayrı commit etmek. | Maker=checker ve geçersiz context fail-closed reddedilir; onay, aktivasyon ve redakte outbox atomiktir. Hazırlayanı bilinmeyen legacy sürüm yeni güvenilir sürüm gerektirir; scoring, süre aşımı ve geri çekme ayrı dilimlerde kalır. |
| 2026-07-17 | Skor konfigürasyonu önce pasif ve değişmez taslak olarak yazılacak; yalnız farklı güvenilir checker'ın sürümlü politika ve kurum kapsamı denetiminden geçen onayı en yeni taslağı atomik olarak aktive edecek. | Global eşik ve ağırlık değişikliği tüm sonraki skorları etkiler; serbest aktör, tek adımlı aktivasyon veya eski taslağın onayı görevler ayrılığını ve tarihsel açıklanabilirliği zayıflatır. | Maker'ın doğrudan aktive etmesi, ayrı audit commit'i veya yalnız aktör kimliği karşılaştırması. | Maker=checker, servis hesabı, rol/kapsam eksikliği ve eski taslak fail-closed reddedilir; talep/karar/aktivasyon redakte outbox ile atomiktir ve geçmiş skorlar değişmez. Süre aşımı, geri çekme ve banka rol eşlemesi ayrı karardır. |
| 2026-07-17 | Bekleyen kritik kural onay isteğini yalnız istekte kayıtlı, güncel olarak yetkili ve aynı dataset kapsamındaki maker `WITHDRAWN` durumuna geçirecek; geri çekme sürüme bağlı ve audit outbox ile atomik olacaktır. | Geri çekme bir onay kararı değildir ve eski isteği güvenli biçimde kapatırken kuralı veya daha yeni sürümü aktive etmemelidir. | Her maker'ın geri çekebilmesi, isteği silmek veya audit yazımını ayrı commit etmek. | Başka maker ve geçersiz context fail-closed reddedilir; gerekçe domain geçmişinde kalır, audit özetinden çıkarılır. Süre aşımı değeri ve başlangıç anı banka politikası olmadan belirlenmez. |
| 2026-07-17 | LDAP kimlik servisi yalnız güvenilir adaptör iddiasını, sürümlü dış grup-rol-scope politikasıyla eşleyerek `ActorContext` üretecek; eşleşmeyen grup yok sayılacak ve hiç yerel rol oluşmazsa erişim reddedilecektir. | İstekten gelen rol/scope veya banka tarafından sağlanmamış grup varsayımı yetki kanıtı olamaz; gerçek LDAP ürünü ve eşleme değerleri henüz seçilmemiştir. | LDAP grubunu doğrudan uygulama rolü saymak, rol/scope'u giriş isteğinden almak veya teknik LDAP hatasını hatalı credential gibi göstermek. | Credential yalnız adaptör çağrısında geçici kalır; teknik hata, credential reddi ve yerel eşleme reddi ayrılır; audit yalnız teknik subject ve sayısal yetki özetini taşır. Gerçek endpoint, TLS ve banka eşlemesi açık kalır. |
| 2026-07-17 | Başarısız giriş sınırı kullanıcı ve istemci için ayrı opak anahtarlarla kalıcı tutulacak; yalnız LDAP credential reddi sayılacak ve sayaç/anahtar altyapısı arızası girişi fail-closed kapatacaktır. | Dağıtık saldırıyı tek birleşik anahtarla izlemek boyutlardan birini aşılabilir bırakır; principal veya istemci bilgisini açık saklamak kişisel veri yayılımını artırır; LDAP kesintisini parola hatası saymak kullanıcıyı haksız engeller. | Bellek içi sayaç, açık principal/IP saklamak, yalnız kullanıcı veya yalnız istemci saymak, LDAP teknik hatasını deneme saymak. | En fazla beş rette ve en az 15 dakika tabanında iki kapsam atomik engellenir; başarı sıfırlar; audit veri-minimumdur. Üretim key provider, secret manager, istemci güven sınırı ve nihai banka değerleri açık kalır. |
| 2026-07-17 | Normal kullanıcı oturumu yalnız güvenilir ve halen geçerli authentication context'inden açılacak; session credential yüksek entropili üretilecek, yalnız özeti saklanacak ve timeout/çıkış kayıtları terminal durum olarak korunacaktır. | Çağırandan session ID, süre, actor, rol veya scope almak güven sınırını aşılabilir kılar; açık credential saklamak oturum ele geçirme etkisini büyütür; fiziksel silme güvenlik geçmişini yok eder. | Çağıranın belirlediği session, stateless açık context tokenı, bellek içi oturum veya çıkışta fiziksel silme. | LDAP başarısı zorunlu session servisine bağlandı; idle/mutlak timeout ve çıkış fail-closed uygulanır. Bu tarihte açık kalan cookie/CSRF, eş zamanlı limit, süre, saklama ve üretim şifreleme kararları 2026-07-22 tarihli `OPEN-BNK-020` banka onayıyla kapatıldı; runtime uygulaması ayrıca izlenir. |
| 2026-07-17 | İlk dashboard trend dilimi son 30 UTC takvim gününü sabit günlük dönemlerle ve yalnız güvenilir authorization kapsamıyla döndürecek; eksik dönemler sıfır skorla doldurulmayacaktır. | Serbest tarih/periyot seçenekleri ve HTTP taşıma güvenliği henüz hazır değildir; buna karşılık yetki filtreli, test edilebilir domain değeri bağımsız üretilebilir. | HTTP endpointini aynı dilimde açmak, repository sonucunu sonradan filtrelemekle yetinmek veya eksik günleri `0` saymak. | Sorgu zaman/scope filtresini kaynağa iter ve servis savunmacı filtre uygular; `NO_DATA` ile teknik hata ayrı kalır. Serbest granülerlik, operasyon listeleri ve HTTP 21A kapsamı dışındadır. |
| 2026-07-17 | İlk sistem içi bildirim dilimi yalnız güvenilir servis context'i, sabit allowlist şablonları, güvenilir sahiplik çözümleyicisi ve hashlenmiş deduplication anahtarı kullanacak; bildirim/audit outbox yazımı atomik olacaktır. | Serbest servis aktörü, şablon ve olay payloadı ham kişisel veri veya banka/müşteri sırrı yayabilir; çağıranın verdiği alıcı ve açık dedup anahtarı güvenilirlik ve gizlilik sınırını zayıflatır. | Olay gövdesini doğrudan saklamak, alıcıyı/aktörü çağırandan almak, anahtarı açık saklamak veya audit'i sonradan ayrı yazmak. | Kalite/teknik bildirimler sabit veri-minimum metinle ayrılır; tekrar tek kaydı günceller, farklı payload çakışır ve audit-stage arızası bildirimi rollback eder. Gerçek sahiplik adaptörü, şablon yönetimi, retry ve issue ayrı dilimlerdir. |
| 2026-07-17 | İlk issue dilimi güvenilir servis üreticisi ve assignment resolver kullanacak; dedup özetinden deterministik issue UUID'si üretilecek, issue/geçmiş/audit outbox atomik yazılacak ve yalnız assignee kapsam içi incelemeyi başlatacaktır. | Aynı olayın yeniden işlenmesi çift issue oluşturmamalı; serbest aktör/assignee/scope girdisi yetki kanıtı olamaz ve aynı timestamp altındaki geçmiş UUID sırası kronolojiyi garanti etmez. | Rastgele her tetikte yeni issue, çağırandan assignee almak, yalnız timestamp/UUID ile geçmiş sıralamak veya bildirimi issue ile tek transaction varsaymak. | Yüz tekrar tek issue üretir; monoton geçmiş sırası korunur. Bildirim ayrı transaction'da başarısızsa issue kaybolmaz ve hata issue kimliğiyle sınıflandırılır. Yeniden atama ile çözüm/kapatma ayrı dilimlerdir. |
| 2026-07-17 | Manuel issue ataması yalnız güvenilir Data Steward/yönetişim context'i ve güvenilir kullanıcı dizini profiliyle yapılacak; atama/geçmiş/audit atomik, bildirim ise yerel commit sonrası ayrı işlem olacaktır. | Çağıranın hedef kullanıcı için sunduğu aktiflik, rol veya scope bilgisi yetki kanıtı değildir; bildirim kesintisi başarılı yerel atamayı kaybettirmemelidir. | Hedef kullanıcıyı istek payloadından doğrulamadan almak, atama ve audit'i ayrı commit etmek veya bildirim hatasında yerel atamayı rollback etmek. | Pasif/kapsam dışı kullanıcı reddedilir; eski/yeni atanan ve öncelik issue geçmişinde korunur, kişisel kimlikler audit allowlist'i dışında kalır ve yeni atanana veri-minimum bildirim üretilir. |
| 2026-07-17 | Issue çözüm metni yalnız sürümlü koruma adaptörünün güvenli çıktısından append-only çözüm kaydına yazılacak; geçmiş tam metni çoğaltmak yerine çözüm UUID'sine bağlanacaktır. | Kök neden ve düzeltici faaliyet hassas veri içerebilir; çağıranın “temiz” iddiası güvenilir değildir ve metni issue/geçmiş/audit boyunca çoğaltmak veri yayılımını artırır. | Serbest metni doğrudan issue satırına yazmak, yalnız basit string değişimi uygulamak veya tam çözümü audit/geçmişte kopyalamak. | Koruma politikası yoksa çözüm fail-closed kapanır; çözüm, durum, geçmiş bağlantısı ve redakte audit atomikleşir. Gerçek koruma adaptörü ile çözen-doğrulayan görev ayrılığı açık kalır. |
| 2026-07-17 | Issue doğrulama akışı çağırandan sonuç değil yalnız opak referans alacak; güvenilir resolver'ın kapsamla eşleşen kalite başarısızlığı append-only kaydedilip issue'yu `WAITING_FOR_RESOLUTION` durumuna döndürecek, teknik hata ayrı tutulacaktır. | Çağıranın sonuç/skor iddiası yetki kanıtı değildir; teknik çalıştırma hatasını kalite başarısızlığı saymak yanlış skor ve yanlış yaşam döngüsü üretir. | Sonucu istekten almak, teknik hataya sıfır skor vermek veya doğrulama/geçmiş/audit yazımlarını ayrı commit etmek. | Kalite başarısızlığı ve kısmi sonuç skor bağıyla kontrollü geri döner; teknik hata skor üretmeden `RESOLVED` durumunu korur. Başarılı doğrulama, kapatma ve çözen-doğrulayan ayrılığı ayrı dilimde kalır. |
| 2026-07-17 | Başarılı issue doğrulaması yalnız son çözümü kaydeden aktörden farklı, güvenilir ve kapsam içi `DATA_OWNER`/`DATA_STEWARD` tarafından yapılacak; `QUALITY_PASSED` sonucu `VERIFIED` durumuna atomik geçiş üretecektir. | Çözümü yapan kişinin kendi faaliyetini doğrulaması görevler ayrılığını zayıflatır; çağıranın başarılı sonuç iddiası veya ayrı audit commit'i denetlenebilirlik sağlamaz. | Assignee'nin kendi çözümünü doğrulaması, yalnız rol kontrolü yapmak veya `VERIFIED` durumunu doğrulama kaydı olmadan yazmak. | Maker=checker fail-closed reddedilir; skor/execution bağlı doğrulama, geçmiş, durum ve redakte audit atomiktir. `CLOSED` ve banka rol eşleme onayı ayrı kalır. |
| 2026-07-17 | Issue kapatma yalnız kalıcı `QUALITY_PASSED` ve skor bağlı doğrulama sonrası, güvenilir kapsam içi `DATA_OWNER`/`DATA_STEWARD` tarafından `VERIFIED → CLOSED` geçişiyle yapılacaktır. | Durum etiketine tek başına güvenmek veya çağırandan doğrulama sonucu almak başarısız/teknik sonucu kapatmaya dönüştürebilir; kapanışın doğrulama kanıtına izlenebilir bağlanması gerekir. | `RESOLVED → CLOSED` kestirmesi, serbest sonuç payloadı veya kapanış audit'ini ayrı commit etmek. | Kapanış geçmişi başarılı doğrulama UUID'sine bağlanır ve audit ile atomiktir. Kapanış yeni onay değildir; 22F çözen-doğrulayan ayrılığını tüketir. Yeniden açma ayrı dilimde kalır. |
| 2026-07-17 | Kapalı issue yalnız aynı deduplication anahtarı ve payload ile gelen, kapanış anından eski olmayan güvenilir kalite olayıyla `WAITING_FOR_RESOLUTION` durumuna yeniden açılacaktır. | Eski olay replay'i kapanmış işi yanlışlıkla açmamalı; teknik hata kalite başarısızlığı sayılmamalı ve aynı anahtarın farklı anlamda yeniden kullanımı örtük ilişki kurmamalıdır. | Her tekrarda yeni issue açmak, teknik olayla yeniden açmak veya yalnız işlem zamanını karşılaştırmak. | Aynı başarısızlık tek issue üzerinde atomik durum/geçmiş/audit güncellemesi üretir; eski replay kapanış zamanını değiştirmez. Yeni veya farklı başarısızlığın ilişkilendirilmesi ayrı dilimde kalır. |
| 2026-07-17 | Yeni kalite başarısızlığının predecessor issue'su çağırandan alınmayacak; güvenilir resolver tarafından seçilip depoda kapalı durum, kalite türü, scope, tetik türü ve olay zamanı üzerinden yeniden doğrulanacaktır. | Serbest issue kimliği veya yalnız scope benzerliği üzerinden ilişki kurmak ilgisiz ya da teknik sorunları yanlış yaşam döngüsüne bağlayabilir. | Trigger payloadına predecessor kimliği eklemek, aynı dataset içindeki son issue'yu otomatik seçmek veya ilişkiyi auditten sonra ayrı yazmak. | Geçerli aday yeni issue'ya append-only `RECURRENCE` ilişkisiyle atomik bağlanır; geçersiz aday tüm yeni yazımları rollback eder. Gerçek resolver adaptörü ayrıca bağlanacaktır. |
| 2026-07-17 | İlk ServiceNow dilimi yalnız güvenilir issue resolver'ın sabit veri-minimum projeksiyonunu ve güvenilir standart servis context'ini kabul edecek; idempotency anahtarı özetlenerek yerel bağlantı/geçmiş/audit atomik saklanacaktır. | Serbest ticket metni, çağıran rolü/scope'u veya açık idempotency anahtarı dış sisteme ve metadata deposuna hassas veri yayabilir; ağ tekrarı çift ticket üretebilir. | Issue nesnesini bütünüyle adaptöre vermek, gerçek endpoint/credential eklemek veya audit'i dış çağrıdan sonra doğrulamak. | Allowlist dışı alanlar yapısal olarak istek sözleşmesinde yoktur; politika dış çağrıdan önce fail-closed doğrulanır ve aynı issue/anahtar tek ticket üretir. Gerçek adaptör, retry/backoff, durum eşlemesi ve `OPEN-BNK-009` ayrı kalır. |
| 2026-07-17 | ServiceNow senkron retry politikası yalnız geçici ve hız sınırı hatalarını toplam en fazla üç denemeyle işleyecek; 429 gecikmesi geçerli `Retry-After`, diğer geçici hatalar sürümlü temel değerden üstel backoff kullanacaktır. | 401 veya kalıcı hatayı tekrarlamak erişim sorununu büyütür; sınırsız retry kaynak tüketir; her denemede farklı anahtar kullanmak çift ticket üretebilir. | Tüm teknik hataları tekrar etmek, sabit/sınırsız gecikme kullanmak veya her denemede yeni idempotency kimliği üretmek. | 401/kalıcı/bilinmeyen hata ilk denemede durur; geçici hata en fazla üç kez aynı veri-minimum istekle denenir. Kalıcı kuyruk/DLQ ve circuit breaker ayrı dilimdir. |
| 2026-07-17 | Tükenen ServiceNow geçici çağrısı veri-minimum kalıcı retry işine dönüştürülecek; claim, yeniden planlama, başarı, dead-letter ve yeniden kuyruğa alma geçişleri audit outbox ile denetlenecektir. | Yerel issue entegrasyon kesintisinde kaybolmamalı; bellek içi retry süreç yeniden başlatıldığında işi kaybeder; ham payload/hata saklamak veri yayılımını artırır. | Yalnız senkron hata döndürmek, tam issue nesnesini kuyruğa yazmak veya tükenen işi silmek. | Aynı issue/anahtar tek kalıcı iş üretir; güvenilir servis worker'ı sınırlı denemeden sonra işi silmeden dead-letter'a taşır ve auditli yeniden işleme mümkündür. Gerçek broker/lease ve alarm ayrı kalır. |
| 2026-07-17 | ServiceNow circuit breaker aynı teknik hedef için SQLite'ta kalıcı, sürümlü ve varsayılan beş geçici hata/beş dakika politikasıyla çalışacak; yalnız tek half-open probe koşullu güncellemeyle alınacaktır. | Sürekli entegrasyon arızasında senkron ve kalıcı retry yollarının dış sistemi zorlaması önlenmeli; kimlik veya kalıcı hatalar geçici kesinti gibi değerlendirilmemelidir. | Bellek içi sayaç, tüm hata sınıflarını saymak, açık devrede adaptörü çağırmak veya audit geçişini ayrı commit etmek. | Açık devre istekleri veri-minimum kuyruğa erteler; başarı/geçici olmayan sonuç sayacı sıfırlar, geçici probe devreyi yeniden açar ve tüm durum geçişleri redakte audit outbox ile atomiktir. Dağıtık state, gerçek ağ adaptörü ve operasyon alarmı ayrı kalır. |
| 2026-07-17 | İlk audit inceleme dilimi güvenilir normal kullanıcı context'i, sabit `AUDIT_VIEWER` rolü, zorunlu kodlanmış gerekçe, 31 günlük senkron pencere ve snapshot cursor kullanacaktır; sorgu sonucu verilmeden görüntüleme audit'i yazılacaktır. | Serbest rol/scope yetki kanıtı değildir; geniş ve hareketli sonuç kümesi tutarsız sayfalama veya veri aşımı üretebilir; filtre değerlerini audit etmek kişisel/hassas kimlikleri çoğaltabilir. | Global audit deposunu rolesiz açmak, offset sayfalama kullanmak, beş yıllık sorguyu senkron çalıştırmak veya filtre değerlerini görüntüleme auditine kopyalamak. | Yetkisiz erişim fail-closed ve auditlidir; sayfalar sabit append-only snapshot üzerinde ilerler; sorgu audit'i yalnız politika, gerekçe kodu ve sayısal özet taşır. Banka rol eşlemesi, istemci filtresi, asenkron rapor ve dışa aktarma ayrı kalır. |
| 2026-07-20 | İlk raporlama dilimi dosya üretmeden yalnız source-seviyesi toplulaştırılmış skor önizlemesi sunacak; güvenilir context kapsamı sorguya itilecek, 31 gün/500 source sınırı ve kodlanmış gerekçe uygulanacaktır. | Hassas dışa aktarma politikası onaylı değilken dosya yüzeyi açılmamalı; sonradan filtreleme yetkisiz source verisini uygulama belleğine taşıyabilir; ham hesaplama detayı gereksiz veri yayılımıdır. | Önce tüm skorları okuyup uygulamada filtrelemek, execution/rule detaylarını rapora eklemek, serbest rol/scope kabul etmek veya doğrudan CSV/XLSX üretmek. | Kapsam genişletme sorgudan önce reddedilir; yalnız en güncel aggregate SOURCE skorları görünür; görüntüleme auditi source kimliği içermez. Dosya/indirme/asenkron iş ve maker-checker dışa aktarma kararı ayrı kalır. |

## 2026-07-20 İterasyon 26A Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-20 | Teknik güvenlik olayı ile kişisel veri ihlali şüphesi ayrı append-only domain kayıtları olacak; şüphe yalnız yetkili insan işlemiyle olaya bağlanacaktır. | Her teknik olayın otomatik olarak KVKK ihlali sayılması yanlış hukuki sonuç ve gereksiz veri yayılımı doğurur. | Güvenlik olayını doğrudan ihlal kaydı yapmak veya serbest metinli tek tablo kullanmak. | Güvenlik olayı tek başına ihlal üretmez; şüphe, önlem ve karar ayrı zaman çizelgesi olaylarıyla korunur. |
| 2026-07-20 | 72 saat değeri öğrenilme zamanından hesaplanan görünür değerlendirme hedefi olacak; sistem dış bildirim göndermeyecek. | `BFR-IR-003` karar süresini görünür isterken Kurula otomatik bildirimi açıkça yasaklar. | Zamanı gizlemek, otomatik karar vermek veya bildirim adaptörü çağırmak. | Gecikme `ON_TIME/OVERDUE` olarak audit özetinde görünür; karar kaydı her zaman `external_notification_dispatched=false` taşır. |
| 2026-07-20 | İhlal şüphesini kaydeden aktör kendi bildirim kararını kaydedemeyecek; roller geçici teknik kodlarla sürümlü politikada tutulacaktır. | Bildirim kararı kritik insan değerlendirmesidir; aynı aktörün hazırlayıp karar vermesi görevler ayrılığını zayıflatır. | Maker=checker'a izin vermek veya banka rol eşlemesini varsaymak. | Farklı güvenilir checker zorunludur; nihai rol eşlemesi `OPEN-BNK-002/004` kapsamında `ComplianceReviewRequired` kalır. |
| 2026-07-20 | İhlal zaman çizelgesi görünümü kalıcı domain modellerini doğrudan döndürmeyecek; actor, scope, incident, timeline, decision ve kanıt kimliklerini çıkartan ayrı veri-minimum projeksiyon kullanacaktır. | Yetkili inceleme bile görev için gereksiz kimlik ve kanıt referanslarını çoğaltmamalıdır. | Repository modellerini doğrudan döndürmek veya yalnız UI katmanında maskelemek. | Sızıntı yapısal olarak servis sözleşmesinde engellenir; veri işleyen kanıtı yalnız varlık bayrağıdır. |
| 2026-07-20 | 72 saat görünümü bekleyen/gecikmiş ve zamanında/gecikmiş karar durumlarını hesaplayacak; hiçbir durum dış aksiyon üretmeyecektir. | Zaman hedefi görünür olmalı ancak hukuki karar ve bildirim yetkili insan sürecinde kalmalıdır. | Yalnız kalan süre göstermek veya gecikmede otomatik bildirim göndermek. | Dört deterministik durum döner; `external_notification_dispatched=false` sabittir ve görüntüleme auditlidir. |

## 2026-07-20 İterasyon 28A Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-20 | İlk secret tarama dilimi bağımsız ve salt okunur yerel Python kontrolü olacak; pipeline veya harici ürün seçmeyecektir. | CI/CD ürünü ve banka eşikleri açıkken yerel, test edilebilir bir güvenlik tabanı üretmek gerekir. | Kurumsal ürünü varsaymak, harici servis bağlamak veya tüm güvenli SDLC kapsamını tek iterasyonda uygulamak. | `28A-v1` komutu yerelde çalışır; pipeline, geçmiş commit ve ürün entegrasyonu ayrı kalır. |
| 2026-07-20 | Bulgu sözleşmesi yalnız göreli yol, satır/sütun ve kural kodu taşıyacak; eşleşen değer ve satır içeriği hiçbir sonuçta bulunmayacaktır. | Güvenlik kontrolünün kendisi secret'ı loga veya kanıta çoğaltmamalıdır. | Eşleşen satırı maskeleyerek yazmak veya değer özetini saklamak. | Pozitif bulgu konumlandırılabilir; gerçek değer model, CLI ve kanıt dışında kalır. |
| 2026-07-20 | Dosya/dizin erişim hatası ayrı teknik sonuç olacak ve temiz tarama kabul edilmeyecektir. | Eksik taramayı başarılı saymak kritik bulguyu görünmez kılabilir. | Okunamayan dosyayı sessizce atlamak veya güvenlik bulgusu saymak. | CLI teknik/doğrulama hatasında `2`, bulguda `1`, temiz sonuçta `0` döndürür. |

## 2026-07-20 İterasyon 28B Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-20 | Proje ve doğrudan çalışma zamanı bağımlılıkları PEP 621 `[project]` metadata'sında açıkça, tam sürüme sabitlenmiş olarak beyan edilecektir. | SBOM'un sürümle ve yeniden üretilebilir bir kaynak beyanıyla ilişkilendirilmesi gerekir; mevcut araç-only pyproject envanter sayılmamalıdır. | Ortamda kurulu paketleri taramak, gevşek sürüm aralığı kullanmak veya eksik beyanı bağımlılık yok saymak. | Proje `0.1.0`, Python `>=3.10`, `packaging==26.0` ve `tomli==2.4.1` beyanıyla deterministik doğrudan envanter üretir. |
| 2026-07-20 | İlk SBOM CycloneDX 1.5 JSON olacak; zaman damgası ve rastgele seri numarası içermeyecektir. | Aynı kaynak beyanından byte düzeyinde aynı artifact üretmek ve sürüm kanıtını karşılaştırabilmek gerekir. | Özel JSON şeması, çalışma zamanına bağlı timestamp/UUID veya kurulu ortam dökümü kullanmak. | Artifact resmî şemayı geçer ve proje sürümü ile doğrudan bağımlılık grafiğini taşır. |
| 2026-07-20 | Eksik/dinamik sürüm veya bağımlılık, tam pin olmayan/URL/extras/yinelenen beyan üretim hatası olacaktır. | Belirsiz veya dış kaynağa bağlı beyan eksik envanteri temiz SBOM gibi gösterebilir. | Belirsiz beyanı olduğu gibi geçirmek veya parser uyarısıyla devam etmek. | CLI güvenli neden koduyla `2` döndürür; yerel yol ve ham parser/işletim sistemi hatası çıkmaz. |
| 2026-07-20 | 28B yalnız beyan edilmiş doğrudan bağımlılıkları kapsayacaktır. | Transitive çözüm, hash, lisans ve zafiyet verisi lock/artifact/scanner politikası gerektirir ve tek iterasyon sınırını aşar. | Kurulu ortamı transitive gerçeklik saymak veya harici zafiyet servisini varsaymak. | SBOM kapsamı açık property ve kanıt notuyla sınırlandırılır; kalan kontroller `ComplianceReviewRequired` kalır. |

## 2026-07-20 İterasyon 28C Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-20 | SAST scanner çıktısı güvenilmez girdi sayılacak ve bulgu yalnız yedi veri-minimum allowlist alanından üretilecektir. | Scanner mesajı, source snippet'i veya mutlak yol kanıt/log üzerinden source ya da secret sızdırabilir. | Scanner ürününün ham JSON'unu saklamak veya yalnız bilinen ürün formatını kabul etmek. | Ürün bağımsız parser yalnız scanner kimliği/sürümü, rule code, severity ve repository-relative konumu kabul eder. |
| 2026-07-20 | Tamamlanmamış SAST taraması kritik bulgudan ayrı teknik hata olacak; iki durumda da sürüm kanıtı üretilmeyecektir. | Eksik taramayı temiz veya güvenlik bulgusu saymak operasyonel neden ile güvenlik sonucunu karıştırır. | Teknik hatayı boş rapor kabul etmek ya da sahte kritik bulgu üretmek. | `SastGateTechnicalError` ve `SastGateBlockedError` ayrı fail-closed yollar sağlar. |
| 2026-07-20 | Yerel `28C-v1` politika yalnız `CRITICAL` önem derecesini bloklayacak; diğer eşikler ve istisna/risk kabulü tahmin edilmeyecektir. | `BFR-SDLC-003` kritik bulguyu açıkça engeller; banka onaylı ek eşikler ve istisna süreci henüz yoktur. | HIGH ve üstünü varsayılan engellemek veya kullanıcı tanımlı istisna eklemek. | Kritik olmayan bulgular sayılır ve digest'e bağlanır; banka eşik/istisna/release onayı `ComplianceReviewRequired` kalır. |
| 2026-07-20 | Sürüm kanıtı bulgu listesini açık metin taşımayacak; PEP 621 proje sürümü ve kanonik bulgu SHA-256 digest'iyle ilişki kuracaktır. | Kanıt sürümle doğrulanabilir olmalı, fakat source konumu ve rule detayını gereksiz yere çoğaltmamalıdır. | Tüm bulgu yollarını release artifact'ına yazmak veya yalnız toplam sayı tutmak. | Kanıt deterministik ve veri-minimumdur; ayrıntılı bulgu raporu scanner güven sınırında kalır. |

## 2026-07-20 İterasyon 30A Frontend Tasarım Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-20 | Tüm frontend görsel değerleri semantik design token üzerinden kullanılacak; component dosyasında ham HEX, spacing, radius veya shadow bulunmayacak. | Açık/koyu tema ve ekranlar arası tutarlılık tek kaynakla yönetilmelidir. | Her componentin kendi renk/ölçü değerini tanımlaması. | `04-Frontend/Gorsel-Tasarim-Sistemi.md` görsel doğruluk kaynağıdır; component altyapısı henüz uygulanmadı. |
| 2026-07-20 | Ana marka rengi `#FDB813` olacak; ana aksiyon, aktif seçim, focus ve küçük marka vurgularıyla sınırlı kullanılacaktır. | Marka görünürlüğü ile operasyonel durum anlamının karışması önlenmelidir. | Sarıyı uyarı veya tüm yüzeylerin baskın rengi yapmak. | Sarı üzerinde koyu metin kullanılır; marka sarısı semantik uyarı değildir. |
| 2026-07-20 | Kritik veri kalitesi ihlali kırmızı, teknik hata mor, uyarı turuncu, başarı yeşil, bilgi mavi ve veri yok gri gösterilecektir; renk tek bilgi taşıyıcısı olmayacaktır. | Teknik hata kalite başarısızlığından ayrılmalı ve erişilebilirlik korunmalıdır. | Tüm olumsuz durumları kırmızı göstermek veya yalnız renge güvenmek. | İkon, yazılı etiket, badge, tooltip/açıklama ve uygun ARIA adı zorunludur. |
| 2026-07-20 | İlk görsel ekran kurumsal dashboard; component doğrulama aracı Storybook ve ekran/görsel doğrulama aracı Playwright olacaktır. | Ortak component durumları ile responsive ekran sapmaları farklı test katmanları gerektirir. | Yalnız manuel inceleme veya yalnız pixel screenshot kullanmak. | Toolchain kurulumu ayrı onaylı artımdır; minimum viewport'lar ve iki iyileştirme turu Definition of Done'a bağlandı. |

## 2026-07-20 İterasyon 28D Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-20 | Dependency scanner ve advisory çıktısı güvenilmez girdi sayılacak; bulgu yalnız sekiz veri-minimum allowlist alanından üretilecektir. | Ham açıklama, mesaj, URL, düzeltme önerisi ve yerel yol secret veya iç sistem ayrıntısı yayabilir. | Scanner ham JSON'unu saklamak veya ürün özel şema kullanmak. | Parser yalnız scanner/advisory kimliği-sürümü, advisory kimliği, severity ve paket adı-sürümünü kabul eder. |
| 2026-07-20 | Bulgu yalnız 28B doğrudan envanterindeki tam kanonik paket/sürüm çiftiyle eşleşecektir. | Tarama kanıtının hangi sürümlü SBOM kapsamına ait olduğu belirsiz kalmamalıdır. | Paket adı eşleşmesini yeterli saymak veya kurulu ortamı envanter kabul etmek. | Bilinmeyen paket ve sürüm uyuşmazlığı fail-closed doğrulama hatasıdır; kapsam `declared-direct-dependencies` olarak açıktır. |
| 2026-07-20 | Tamamlanmamış tarama teknik hata, `CRITICAL` bulgu güvenlik blokajı olacaktır; ikisi de sürüm kanıtı üretmeyecektir. | Teknik erişim/işleme arızası ile doğrulanmış zafiyet sonucu birbirine dönüştürülmemelidir. | Eksik taramayı temiz saymak veya teknik hatayı sahte kritik bulgu yapmak. | Ayrı teknik ve blokaj hata sınıfları uygulanır; kritik olmayan eşikler banka kararına bırakılır. |
| 2026-07-20 | Sürüm kanıtı açık advisory/paket listesi yerine envanter ve bulgu SHA-256 özetlerini taşıyacaktır. | Sürüm ve tarama kapsamı doğrulanabilir olmalı, ayrıntılı güvenlik bulguları gereksiz çoğaltılmamalıdır. | Tüm bulguları release kanıtına yazmak veya yalnız toplam sayı tutmak. | Kanıt deterministik ve veri-minimumdur; scanner/advisory sürümleriyle proje sürümüne bağlanır. |

## 2026-07-20 İterasyon 28E Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-20 | Sızma testi bulgusu yalnız opak değerlendirme/bulgu/aksiyon/sorumlu UUID referansları ve önem derecesinden oluşacaktır. | Ham rapor, endpoint, istek/yanıt, exploit ve kullanıcı bilgisi güvenlik kontrolünden yeni bir hassas veri yayılımı yaratabilir. | Serbest metinli bulgu kaydı veya pentest ürününün ham JSON'unu saklamak. | Beş alanlı allowlist dışındaki her girdi fail-closed reddedilir; ayrıntılı rapor harici güven sınırında kalır. |
| 2026-07-20 | Tekrar test teknik hatası güvenlik sonucu olmayacak ve bulguyu kapatmayacaktır. | Erişim veya test arızasını başarılı/başarısız güvenlik doğrulaması saymak teknik hata ile bulgu sonucunu karıştırır. | Teknik hatada bulguyu açmak, kapatmak veya başarısız saymak. | `TECHNICAL_ERROR` bulguyu `READY_FOR_RETEST` durumunda tutar; yeniden test kanıtı yalnız başarılı/başarısız sonuçta kaydedilir. |
| 2026-07-20 | Yalnız tamamlanmış değerlendirme kanıt üretecek; kapanmamış her kritik bulgu kanıtı engelleyecektir. | `BFR-SDLC-003` kritik bulgulu üretim adayını fail-closed engeller; eksik değerlendirme temiz kabul edilemez. | Tamamlanmamış rapordan veya açık kritik bulguyla kanıt üretmek. | Teknik hata ve güvenlik blokajı ayrı hata sınıflarıdır; kritik olmayan banka eşikleri tahmin edilmez. |
| 2026-07-20 | Kanıt tekil bulgu/sorumlu referanslarını taşımayacak; yalnız sayımlar ve kanonik SHA-256 digest kullanacaktır. | Kanıt bütünlüğü doğrulanırken operasyonel güvenlik referansları gereksiz çoğaltılmamalıdır. | Tüm UUID listesini kanıta yazmak veya yalnız toplam bulgu sayısı tutmak. | Kanıt deterministik ve veri-minimumdur; ayrıntı kayıt sisteminde kalır. |

## 2026-07-20 İterasyon 29A Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-20 | Kontrol kataloğu teknik durum, banka inceleme durumu ve açık engelleri ayrı alanlarda tutacaktır. | Teknik artifact bulunması tüm kontrolün tamamlandığını veya banka onayını göstermez. | Tek `PASS/FAIL` durumu kullanmak ya da teknik kanıtı otomatik onay saymak. | Manifest `Partial/Missing`, `ComplianceReviewRequired` ve `OPEN-BNK-*` listelerini birbirine dönüştürmeden raporlar. |
| 2026-07-20 | Kanıt artifact'ları içerik kopyası yerine repository-relative yol ve SHA-256 ile bağlanacaktır. | Kanıt paketinin hassas teknik ayrıntıları gereksiz çoğaltmadan bütünlük ilişkisi kurması gerekir. | Tüm Markdown içeriğini JSON'a gömmek veya yalnız dosya adını kaydetmek. | Manifest veri-minimum ve deterministiktir; dosya değişikliği digest'i değiştirir. |
| 2026-07-20 | Katalog 15 matris kontrolünün tamamını ve yalnız bunları içerecek; eksik/fazla kayıt fail-closed olacaktır. | Sessizce atlanan kontrol eksik kanıtı temiz paket gibi gösterebilir. | Bulunan kayıtlarla best-effort manifest üretmek. | Her kontrol açıkça `Partial` veya `Missing` durumundadır; kapsam eksikliği üretim hatasıdır. |
| 2026-07-20 | `ApprovedByBank` ve `NotApplicable` yalnız opak karar referansı varsa kabul edilecektir. | Codex veya teknik test bankanın yetkili kararını varsayamaz. | Serbest onay notu veya referanssız durum yükseltme. | Mevcut 15 kontrolün tamamı `ComplianceReviewRequired`; banka kararı ve kimlik çözümü ayrı kalır. |

## 2026-07-20 İterasyon 29B Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-20 | Drift kapısı manifesti 29A üreticisinin tek kanonik bayt serileştirmesiyle yeniden üretecek ve saklanan dosyayla byte düzeyinde karşılaştıracaktır. | JSON nesne eşitliği whitespace veya serileştirme sapmasını gizleyebilir; sürüm artifact'ı tam bayt kimliğiyle doğrulanmalıdır. | JSON'u parse edip semantik karşılaştırmak veya ayrı bir serileştirici yazmak. | Aynı kanonik çıktı `MATCH`, herhangi bir bayt farkı `DRIFT` üretir. |
| 2026-07-20 | CLI `MATCH`, `DRIFT` ve doğrulama/teknik hatayı sırasıyla `0`, `1`, `2` çıkış kodlarıyla ayıracaktır. | Artifact sapması ile dosya/girdi arızası aynı sonuç sayılırsa operasyonel neden ve kontrol sonucu karışır. | Her başarısızlığı `1` döndürmek veya drift'i exception yapmak. | Kapı fail-closed kalırken otomasyon üç sonucu ayrı işleyebilir. |
| 2026-07-20 | Doğrulama çıktısı yalnız politika, durum ve saklanan/üretilen SHA-256 özetlerini taşıyacaktır. | Manifest veya kanıt içeriğini log/CI çıktısında çoğaltmak hassas teknik ayrıntı yayılımını artırır. | Tam diff, manifest gövdesi veya değişen kanıt yollarını yazdırmak. | Çıktı veri-minimumdur; ayrıntı güvenli repository incelemesinde kalır. |
| 2026-07-20 | Saklanan manifest yalnız sürüm paketi dizinindeki kanonik `.json` yolundan okunacaktır. | Genel dosya karşılaştırıcısı kullanıcı girdisiyle depo dışı veya ilgisiz hassas dosya okuyabilir. | Mutlak yol kabul etmek veya yalnız suffix denetlemek. | Traversal, mutlak yol, symlink, düzenli olmayan ve büyük dosya fail-closed reddedilir. |

## 2026-07-20 İterasyon 29C Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-20 | Birleşik preflight altı mevcut kontrolü sabit sırada çağıracak; alt kapıların güvenlik kararlarını yeniden uygulamayacaktır. | Aynı kritik bulgu veya teknik hata kuralını ikinci kez yazmak sözleşmeler arasında sapma yaratır. | Tüm kontrolleri preflight içinde yeniden kodlamak veya shell subprocess zinciri kullanmak. | Secret, SBOM, SAST, bağımlılık zafiyeti, pentest ve manifest kapıları açık Python sınırlarıyla orkestre edilir. |
| 2026-07-20 | SAST, bağımlılık zafiyeti ve pentest raporları tek sürümlü exact-field JSON paketinde zorunlu olacaktır. | Rapor girdisi olmadan kontrolü çalışmış/temiz saymak `BFR-SDLC-001/003` için yanlış güven üretir. | Eksik raporu atlamak, boş rapor üretmek veya serbest scanner JSON'u kabul etmek. | Eksik, fazla alanlı veya tamamlanmamış rapor fail-closed doğrulama/teknik hata üretir. |
| 2026-07-20 | Başarılı preflight çıktısı yalnız proje sürümü, kontrol/politika kimliği ve kanıt SHA-256 özetlerini taşıyacaktır. | Birleşik çıktı bulgu yollarını, advisory'leri ve pentest referanslarını gereksiz çoğaltmamalıdır. | Alt kapıların tam çıktılarını birleştirmek veya ham rapor paketini saklamak. | Çıktı deterministik ve veri-minimumdur; ayrıntılar kaynak kontrol sistemlerinde kalır. |
| 2026-07-20 | `PASS=0`, güvenlik/artifact blokajı `BLOCKED=1`, doğrulama veya teknik hata `2` olacaktır. | Güvenlik kararı ile çalışmayan kontrol birbirine dönüştürülmemelidir. | Tüm olumsuz sonuçları tek exit code yapmak. | Otomasyon fail-closed kalırken neden sınıfını ayrı işleyebilir. |

## 2026-07-20 Bakım İterasyonu 29C.1 Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-20 | Exception ile kesin sonlanan kimlik yardımcıları `NoReturn` olarak modellenecek; test double'ları geniş `object` veya davranışı gizleyen cast yerine uygulama protokolleriyle eşleşecektir. | Tam type-check sonucunu davranış değiştirmeden güvenilir hale getirmek ve gerçek sözleşme sapmalarını görünür tutmak gerekir. | Hataları global ignore, `Any` veya toplu cast ile bastırmak. | Tam depo mypy baseline'ı 109 dosyada sıfır hatadır; gelecekteki sapmalar yeni teknik borç sayılacaktır. |

## 2026-07-20 İterasyon 19D Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-20 | Kural onay isteği hedefi 3 iş günü, otomatik sona ermesi 10 iş günü olacak; süre istek oluşturma anında başlayacak ve sürümlü iş takvimiyle hesaplanacaktır. | Kullanıcı karar paketindeki süre politikası uygulanırken gerçek banka tatil takvimi kod içine gömülmemeli ve geçmiş istek hangi takvimle hesaplandığını korumalıdır. | Takvim günü kullanmak, hafta sonu/tatili sabit kodlamak veya sona erme zamanını sorgu anında yeniden hesaplamak. | İstek hedef/sona erme zamanı ve takvim sürümünü saklar; enjekte edilen takvim olmadan zamanlı politika fail-closed kapanır. |
| 2026-07-20 | Süre aşımı yalnız güvenilir servis `ActorContext` ile, dataset kapsamı ve sürümlü teknik rolle yürütülecek; durum ve audit outbox atomik yazılacaktır. | Serbest scheduler aktörü veya best-effort audit, bekleyen kritik değişikliğin izsiz kapatılmasına yol açabilir. | Aktörsüz toplu SQL güncellemesi, normal checker'ın isteği sona erdirmesi veya audit'i sonradan yazmak. | Yetkisiz kullanıcı/servis reddedilir; audit-stage arızasında istek `PENDING` kalır. Banka rol eşlemesi `ComplianceReviewRequired` durumundadır. |
| 2026-07-20 | Aynı RuleVersion için yalnız bir `PENDING` istek bulunacak; `EXPIRED` geçmiş silinmeden aynı sürüm için yeni istek oluşturulabilecektir. | Sona eren isteğin yeniden oluşturulması gerekirken mevcut tam benzersizlik kısıtı tarihsel kayıt ile yeni iş akışını birbirine kilitliyordu. | Eski isteği yerinde tekrar açmak, silmek veya her sona ermede yapay RuleVersion oluşturmak. | SQLite şeması kısmi benzersiz indekse geriye uyumlu taşınır; eski karar geçmişi korunur. |

## 2026-07-20 İterasyon 19E Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-20 | Veri kaynağı aktivasyonu, güncel kaynak revizyonuna bağlı sürümlü maker-checker isteğiyle yürütülecektir. | Onayın daha sonraki bağlantı değişikliğine taşınmasını önlemek ve BFR-SOD-003/004 tarihsel bağını korumak gerekir. | Kaynak kimliğine süresiz onay vermek veya bağlantı testi sonucunu değişiklik sürümü saymak. | `DataSource.revision` ve aktivasyon isteği birlikte saklanır; eski revizyon kararı fail-closed reddedilir. |
| 2026-07-20 | Aktivasyon için Data Owner ve güncel revizyona ait başarılı son bağlantı testi zorunlu olacaktır. | Sahipsiz veya salt okunurluğu doğrulanmamış kaynağın kalite çalıştırmalarına açılması yönetişim ve güvenlik riski oluşturur. | Checker kararını tek önkoşul saymak veya başarısız/eski testi kabul etmek. | Eksik sahip veya güncel başarılı test bulunmadığında istek oluşmaz; secret ve bağlantı ayrıntıları audit özetine girmez. |
| 2026-07-20 | Checker kararı, kaynak durum geçişi ve audit outbox aynı transaction içinde yazılacaktır. | Aktivasyonun audit kaydı olmadan gerçekleşmesi veya karar kaydıyla kaynak durumunun ayrışması kabul edilemez. | Önce kaynağı aktive edip audit'i sonradan yazmak ya da best-effort audit kullanmak. | Audit-stage arızasında istek `PENDING`, kaynak `TEST_SUCCEEDED` kalır; banka rol eşlemesi `ComplianceReviewRequired` durumundadır. |

## 2026-07-21 İterasyon 19F Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-21 | Veri kaynağı aktivasyon onayları da 3 iş günü hedef ve 10 iş günü otomatik sona erme politikasını istek oluşturma anından itibaren kullanacaktır. | Kural ve kaynak kritik değişikliklerinin aynı karar paketine göre tutarlı, sürümlü ve tarihsel olarak açıklanabilir süre yönetimi gerekir. | Kaynak onaylarında süresiz beklemek, takvim günü kullanmak veya süreyi sorgu anında yeniden hesaplamak. | İstek hedef/sona erme zamanı ve takvim sürümünü saklar; eksik veya uyumsuz takvimle süreli politika fail-closed kapanır. |
| 2026-07-21 | Bekleyen aktivasyon isteğini yalnız kayıtlı maker geri çekebilecek; süre aşımını yalnız güvenilir, yetkili ve source kapsamı içindeki servis hesabı işletecektir. | Başka aktörün kritik isteği izinsiz kapatması ve aktörsüz toplu güncelleme görevler ayrılığı ile audit güven sınırını bozar. | Checker'ın geri çekmesi, aktörsüz SQL işi veya genel ayrıcalığın rol/kapsam yerine kabul edilmesi. | `WITHDRAWN` ve `EXPIRED` terminal durumları korunur; yetkisiz kullanıcı/servis reddedilir ve kaynak `TEST_SUCCEEDED` kalır. |
| 2026-07-21 | Geri çekme/süre aşımı durum geçişi ile veri-minimum audit outbox aynı transaction içinde yazılacaktır. | İsteğin audit izi olmadan kapanması veya audit ile domain durumunun ayrışması kabul edilemez. | Best-effort audit veya durum değişikliğinden sonra ayrı audit yazımı. | Audit-stage arızasında istek `PENDING` kalır; secret, bağlantı yapılandırması, owner, maker ve gerekçe audit özetine alınmaz. |

## 2026-07-21 İterasyon 19G Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-21 | Bağlantı ayarı güncellemesi mevcut kaynak kaydını doğrudan değiştirmeyecek; değişmez aday bağlantı revizyonu olarak oluşturulup salt okunur testten sonra terfi ettirilecektir. | `FR-012`, başarısız testte mevcut çalışan sürümün korunmasını ve değişikliğin sürümlü olmasını zorunlu kılar. | Aday ayarları doğrudan `data_sources` üzerine yazıp başarısızlıkta eski JSON'u geri yüklemek. | Başarısız ve teknik test yolları çalışan yapılandırma, secret referansı, revizyon ve durumu değiştirmez; ilk/legacy revizyon geçmişi korunur. |
| 2026-07-21 | Başarılı aday terfisi kaynağı yeniden aktivasyon bekleyen `TEST_SUCCEEDED` durumuna alacak ve eski revizyona bağlı bekleyen aktivasyon isteklerini `INVALIDATED` yapacaktır. | Eski yapılandırma için verilmiş veya bekleyen onayın yeni bağlantı kapsamına taşınması görevler ayrılığı ve sürüm bağını bozar. | Kaynağı aktif tutmak veya eski onayı yeni revizyona otomatik taşımak. | Yeni revizyon ayrı aktivasyon isteği gerektirir; eski onay geçmişi silinmeden kullanılamaz hâle gelir. |
| 2026-07-21 | Aday oluşturma ile terfi/onay invalidasyonu işlemleri veri-minimum audit outbox ile atomik olacaktır. | Bağlantı değişikliğinin veya onay geçersizleştirmenin audit izi olmadan gerçekleşmesi kabul edilemez. | Best-effort audit veya yapılandırma ayrıntılarını audit payloadına kopyalamak. | Audit-stage arızasında aday/terfi/test/invalidasyon geri alınır; audit bağlantı ayarı, secret referansı, owner, hazırlayan ve gerekçe içermez. |

## 2026-07-21 İterasyon 19H Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-21 | Kaynak pasifleştirme sürümlü politikadaki ayrı deactivator rolü, güvenilir kullanıcı context'i ve source kapsamıyla yetkilendirilecektir. | Aktivasyon maker-checker rolleri ile operasyonel pasifleştirme yetkisinin örtük olarak birleştirilmesi en az ayrıcalık ve açıklanabilir yetki sınırını zayıflatır. | Maker, checker veya genel ayrıcalık sahibi aktörün doğrudan pasifleştirebilmesi. | Yanlış rol/kapsam, servis hesabı ve ayrıcalıkla rol atlama reddedilir; banka rol kodu ve LDAP eşlemesi `ComplianceReviewRequired` kalır. |
| 2026-07-21 | Manual ve scheduled execution yalnız `ACTIVE` veri kaynağı kabul edecektir; `TEST_SUCCEEDED` durumu çalıştırma yetkisi vermeyecektir. | Bağlantı testinin başarılı olması idari aktivasyon veya yeniden aktivasyon onayı değildir; aksi davranış pasifleştirme kapısını dolanabilir. | `TEST_SUCCEEDED` ve `ACTIVE` durumlarını birlikte kabul etmek. | Pasif veya yalnız test edilmiş kaynak yeni execution oluşturamaz; zamanı gelen geçersiz plan mevcut teknik olay akışıyla pasifleştirilir. |
| 2026-07-21 | Pasifleştirme mevcut çalışan işleri değiştirmeyecek; yeniden aktivasyon mevcut maker-checker akışından geçecek ve durum geçişi audit outbox ile atomik olacaktır. | Çalışan işi tamamlama/iptal etme politikası banka kararı gerektirir; fiziksel silme ve örtük yeniden aktivasyon tarihsel izlenebilirliği bozar. | Pasifleştirmede tüm işleri otomatik iptal etmek, kaynağı arşivlemek veya bağlantı testiyle doğrudan aktif yapmak. | Mevcut işler korunur; ret `INACTIVE` durumunu korur, farklı checker onayı yeniden `ACTIVE` yapar; audit-stage arızasında pasifleştirme geri alınır. |

## 2026-07-21 İterasyon 25A Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-21 | Kullanıcı karar paketindeki zaman bazlı saklama sınıfları sürümlü ve varsayılan olarak `ComplianceReviewRequired` teknik katalogda temsil edilecektir. | Kayıt türlerine tek beş yıllık süre uygulamak karar paketi ve yaşam döngüsü kontrolüyle çelişir; provisional süreler banka onayı gibi kullanılamaz. | Tüm kayıtları beş yıl saklamak veya süreleri kod içine onaysız kesin değer olarak gömmek. | Altı sınıf takvimsel süreyle değerlendirilir; varsayılan katalog süresi dolan kayda otomatik imha yetkisi vermez. |
| 2026-07-21 | Retention uygunluğu yalnız salt okunur dry-run olarak hesaplanacak; aktif legal hold her koşulda engelleyici olacak ve resolver arızası teknik hata sayılacaktır. | Gerçek imha için yetki, maker-checker, audit, idempotency, yedek ve hukuk onayı henüz tamamlanmamıştır. | Bu dilimde fiziksel silme/anonimleştirme yapmak veya hold durumu okunamazsa kaydı uygun saymak. | Fiziksel veri değişmez; hold veya teknik belirsizlik fail-closed kapanır, yalnız opak yaşam döngüsü metadata'sı işlenir. |
| 2026-07-21 | `ApprovedByBank` retention politikası opak onay referansı olmadan kabul edilmeyecektir. | Teknik bir enum değerinin tek başına banka onayı kanıtı sayılması kontrol durum sözlüğünü aşar. | Onay referansı olmadan `ApprovedByBank` durumuna izin vermek. | Varsayılan katalog provisional kalır; sentetik test dışında onaylı uygunluk üretmek için dış güvenilir katalog ve kanıt referansı gerekir. |

## 2026-07-21 İterasyon 25B Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-21 | Legal hold geçmişi yerinde güncellenmeyen `PLACED` ve `RELEASED` olayları olarak saklanacak; aynı kayıt birden fazla eş zamanlı hold taşıyabilecektir. | Dava, denetim ve resmî inceleme hold'ları birbirinden bağımsızdır; bir hold'un kaldırılması diğerinin engelini düşürmemelidir. | Tek aktif hold sınırı koymak veya mevcut satırı `released_at` ile güncellemek. | Geçmiş append-only kalır; resolver değerlendirme anına göre tüm aktif hold'ları yeniden kurar ve yalnız hepsi kalkınca engel sona erer. |
| 2026-07-21 | Hold oluşturma ve serbest bırakma güvenilir normal kullanıcı context'i, sürümlü rol/reason code politikası ve veri kapsamıyla yetkilendirilecek; oluşturan aktör aynı hold'u serbest bırakamayacaktır. | Serbest aktör/rol/kapsam veya tek aktör kararı legal hold'un hukuki ve operasyonel güven sınırını zayıflatır. | Çağıranın verdiği aktör/rolü kabul etmek, servis ya da break-glass hesabına örtük yetki vermek veya aynı aktörle kaldırmak. | Yanlış rol/kapsam, servis hesabı ve break-glass fail-closed reddedilir; banka rol ve karar kodu eşlemesi `ComplianceReviewRequired` kalır. |
| 2026-07-21 | Hold olayı ve redakte audit outbox aynı transaction'da yazılacak; stage arızası işlemi geri alırken merkezi publisher kesintisi kalıcı `PENDING` olay bırakacaktır. | Kritik yaşam döngüsü kararı audit izi olmadan commit edilmemeli, geçici merkezi audit kesintisi de hazırlanmış kanıtı kaybettirmemelidir. | Best-effort audit, domain commitinden sonra yeni audit olayı üretmek veya audit kesintisinde olayı düşürmek. | Domain/audit hazırlığı atomiktir; audit özeti ham kayıt, kapsam kimliği veya serbest metin taşımaz ve güvenli tekrar mevcut outbox sözleşmesine bırakılır. |

## 2026-07-21 İterasyon 25C Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-21 | İmha işi yalnız `ApprovedByBank` politika değerlendirmesi `ELIGIBLE_FOR_DISPOSAL` ürettiğinde ve opak onay referansı bulunduğunda hazırlanacaktır. | Provisional süre veya enum değeri fiziksel imha yetkisi sayılmamalı; aktif legal hold ve karar belirsizliği fail-closed kalmalıdır. | Süresi dolan her kaydı otomatik kuyruğa almak veya çağıranın onay beyanını yeterli saymak. | Varsayılan katalog iş üretmez; gerçek onay resolver'ı gelene kadar yalnız sentetik onaylı sözleşme doğrulanabilir. |
| 2026-07-21 | İmha işi ve terminal sonuç append-only saklanacak; idempotency anahtarı ile kayıt/kapsam kimlikleri özetlenecek, aynı anahtar farklı payload için kullanılamayacaktır. | Tekrar teslim aynı fiziksel işlemi çoğaltmamalı ve kanıt deposu ham yaşam döngüsü kimliklerini gereksiz yaymamalıdır. | Ham anahtar/kimlik saklamak, işi yerinde güncellemek veya tekrarları best-effort ayıklamak. | Aynı payload tek iş/tek sonuç üretir; farklı payload/sonuç çatışmadır ve geçmiş `UPDATE/DELETE` kabul etmez. |
| 2026-07-21 | İş hazırlama normal kullanıcı, sonuç kanıtı yazma servis aktörü rolüne ayrılacak; iki adım aynı aktör kimliğiyle tamamlanamayacak ve gerçek destructive adaptör bu iterasyona eklenmeyecektir. | Kritik imha niyeti ile teknik sonuç kaydının güven sınırları ayrılmalı; banka adaptörü ve maker-checker kararı tahmin edilmemelidir. | Kullanıcının doğrudan başarı sonucu yazması veya servis içinde fiziksel silmeyi etkinleştirmek. | Yanlış aktör türü/rol/kapsam reddedilir; 25C yalnız kanıt sözleşmesidir, fiziksel imha iddiası üretmez. |
| 2026-07-21 | `SUCCEEDED` ve `FAILED_TECHNICAL` ayrı terminal sonuçlar olacak; iş/sonuç ile redakte audit outbox aynı transaction'da yazılacaktır. | Adaptör erişim arızası veri kalitesi sonucu veya başarılı imha gibi gösterilmemeli, kritik kanıt audit olmadan commit edilmemelidir. | Serbest hata metni saklamak, teknik hatayı kalite başarısızlığına çevirmek veya best-effort audit kullanmak. | Audit yalnız durum, yöntem, politika, kapsam türü, sayaç ve izinli teknik hata kodunu taşır; ham kayıt ve serbest metin dışarıda kalır. |

## 2026-07-21 İterasyon 25D Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-21 | Arşiv geri çağırma audit ve kalite skoru kayıt türleriyle, opak arşiv referansı ve allowlist amaç koduna bağlı idempotent talep olarak modellenecektir. | `BFR-LCM-004` yetkili süreci gerektirirken gerçek arşiv ürünü ve erişim politikası henüz seçilmemiştir; talep sözleşmesi içerik erişiminden ayrılmalıdır. | Arşiv URI'sini saklamak, doğrudan getirme çağrısı yapmak veya serbest amaç metni kabul etmek. | Ham arşiv/kapsam kimliği yalnız özetlenir; bu iterasyon hiçbir arşiv içeriğini okumaz veya taşımaz. |
| 2026-07-21 | Talebi açan aktör aynı talebi onaylayamayacak; karar ayrı sürümlü rol, aynı veri kapsamı ve allowlist gerekçe gerektirecektir. | Arşivlenmiş audit/skor erişimi hassas ve denetlenebilir bir işlem olduğundan tek aktörün talep ile yetkilendirmeyi birleştirmesi görevler ayrılığını zayıflatır. | Requester'ın kendi talebini aktive etmesi, servis/break-glass hesabına örtük karar yetkisi vermek veya yalnız genel ayrıcalığı kabul etmek. | Yanlış rol/kapsam, servis hesabı, break-glass ve aynı aktör kararı fail-closed reddedilir; banka rol eşlemesi açık kalır. |
| 2026-07-21 | Talep ve tek terminal onay/ret kararı append-only saklanacak; her olay redakte audit outbox ile aynı transaction'da yazılacaktır. | Karar geçmişi yerinde değişmemeli ve audit izi olmadan erişim yetkilendirmesi oluşmamalıdır. | Talep satırının durumunu güncellemek, ikinci karar eklemek veya best-effort audit kullanmak. | `UPDATE/DELETE`, farklı ikinci karar ve audit-stage arızası reddedilir; audit özeti yalnız durum, kayıt türü ve kapsam türünü taşır. |

## 2026-07-21 İterasyon 27A Kararları

| Tarih | Karar | Gerekçe | Alternatif | Sonuç |
| --- | --- | --- | --- | --- |
| 2026-07-21 | Ortam kimliği doğrudan çağıran girdisinden değil, sürümlü güven sözleşmesini uygulayan konfigürasyon sağlayıcısından yüklenecektir. | Serbest ortam adı veya sıradan ayar üretim kontrolünü baypas edebilir; kaynak belirsizliği fail-closed kalmalıdır. | Ortam değişkeni metnini doğrudan güvenilir kabul etmek veya kaynak okunamazsa varsayılan geliştirme ortamına düşmek. | Yanlış güven sözleşmesi kaynağı okunmadan reddedilir; sağlayıcı kesintisi ayrı teknik hata üretir ve başlangıç kanıtı oluşmaz. |
| 2026-07-21 | Üretim dışı ortamda `BANK_PRODUCTION` veri kökeni ve üretim secret kapsamı yasaklanacak; tüm ortamlar yalnız kendi secret kapsamını kullanacaktır. | `BFR-OPS-001/002` ortam ve veri ayrımını teknik olarak zorunlu kılar; yanlış kapsam sessizce kabul edilmemelidir. | Yalnız ortam adını kaydetmek, UAT için üretim secret'ına izin vermek veya ihlali uyarı seviyesinde bırakmak. | Uyumsuz veri/secret sınıfı fail-closed politika engelidir; gerçek veri veya secret değeri kapıdan geçmez. |
| 2026-07-21 | Başlangıç kanıtı secret referansını değil yalnız secret kapsamını ve sabit kontrol kodlarını taşıyacaktır. | Secret yolu değer olmasa bile altyapı topolojisi ve adlandırma bilgisi sızdırabilir. | Tam URI'yi loglamak veya sağlayıcı hata mesajını kanıta eklemek. | Kanıt veri-minimum kalır; doğrulama ve teknik hata yalnız allowlist neden kodu taşır. |

## İlişkili Notlar

- [Sistem Açıklaması](../01-SRS/02-Sistem-Aciklamasi.md)
- [Güvenlik NFR](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md)
- [Açık Konular ve Varsayımlar](../01-SRS/15-Acik-Konular.md)

## 2026-07-20 Açık Konulardan Aktarılan Karar Paketi

# Alınan Kararlar

> Karar tarihi: 20 Temmuz 2026  
> Kapsam: Veri Kalitesi İzleme ve Skorlama Sistemi  
> Durum sözlüğü:
> - `KararAlındı`: Teknik yön kullanıcı kararıyla kesinleşti; uygulama ve banka
>   incelemesi ayrı durumlarda izlenir.
> - `ApprovedByBank`: Yetkili kullanıcı banka onayını açıkça beyan etmiştir;
>   uygulama ve üretim kanıtı ayrıca izlenir.
> - `Tamamlandı`: Kullanıcı beyanına göre uygulaması tamamlandı.
> - `Açık`: Ürün, rol eşlemesi, kapsam veya kurumsal onay henüz belirlenmedi.

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

## Bankacılık Geçiş Teknik Yön Kararları

Bu kayıtların teknik yönü seçilmiştir. `KararAlındı` durumu banka kurulu,
hukuk, uyum, IAM, bilgi güvenliği veya iç kontrol onayının tamamlandığı anlamına
gelmez; kalan onay ve ürün ayrıntıları sonuç sütununda korunur.

| ID | Alınan karar | Durum | Kalan onay veya uygulama bağımlılığı |
| --- | --- | --- | --- |
| OPEN-BNK-003 | Tüm kullanıcılar için IdP MFA; PAM, süreli ayrıcalık ve çift onaylı break-glass modeli | `KararAlındı` | Ürün ve banka rol eşlemeleri |
| OPEN-BNK-004 | Risk bazlı maker-checker kapsamı ve görevler ayrılığı | `KararAlındı` | Banka onaylı maker/checker rol kodları ve tam kritik işlem matrisi |
| OPEN-BNK-005 | Kritik işlemde fail-closed, düşük riskli işlemde durable-buffer | `KararAlındı` | Üretim kuyruk/outbox, kapasite ve alarm ayrıntıları |
| OPEN-BNK-006 | Kurumsal WORM/imza/hash doğrulamalı audit deposu | `KararAlındı` | Kurumsal ürün ve iç denetim onayı |
| OPEN-BNK-007 | Eşlenmeyen sınıflandırmada fail-closed davranış | `KararAlındı` | Banka sözlüğü ve müşteri/banka sırrı kod eşlemesi |
| OPEN-BNK-010 | SIEM entegrasyonu ve 72 saatlik ihlal değerlendirme akışı | `KararAlındı` | Ürün, olay sözlüğü, alarm seviyesi ve SOC eskalasyon eşlemesi |
| OPEN-BNK-012 | Pilot VM; üretimde kurumsal konteyner platformu, yüksek erişilebilir PostgreSQL, broker ve secret manager yönü | `KararAlındı` | Kurumsal ürün adları ve altyapı kurul onayı |
| OPEN-BNK-014 | Asenkron dışa aktarma, gerekçe, maker-checker, DLP, watermark ve süreli indirme modeli | `KararAlındı` | Banka veri sahibi ve bilgi güvenliği onayı |
| OPEN-BNK-015 | `ActorContext` yalnız güvenilir identity/session adaptöründen üretilecek | `KararAlındı` | Issuer sahipliği ve session assertion doğrulaması |
| OPEN-BNK-016 | PostgreSQL transactional outbox ve ayrı publisher worker | `KararAlındı` | Şifreleme, sahiplik, replay ve operasyon prosedürü |
| OPEN-BNK-017 | Onay hedefi 3 iş günü, otomatik sona erme 10 iş günü | `KararAlındı` | Banka iş takvimi ve rol sahibi onayı |
| OPEN-BNK-020 | BFF üzerinde opak server-side session; 1 saat hareketsizlik, 10 saat mutlak süre, tek aktif oturum, `__Host-session` cookie, synchronizer-token CSRF, merkezi iptal ve 90 günlük güvenlik metadatası | `ApprovedByBank` | Üretim deposu, şifreleme/KMS-HSM, HTTP katmanı ve 90 günlük fiziksel saklama uygulama kanıtı |
| OPEN-BNK-021 | Kısmi çalışma yalnız onaylı dataset politikasındaki tüm koşulları sağlarsa resmî skora girebilir; aksi halde `PROVISIONAL` olur ve resmî skor/SLA/trend/raporlamadan dışlanır | `KararAlındı` | Üretim eşikleri ve banka onaylı politika kayıtları ayrı açık bağımlılıktır |

## Bankacılık Geçiş Açık Konuları

| ID | Konu | Karar sahibi | Durum |
| --- | --- | --- | --- |
| OPEN-BNK-001 | BDDK bilgi sistemleri düzenlemelerinin bu uygulamaya uygulanabilir maddelerinin banka uyum/hukuk tarafından teyidi | Uyum / Hukuk / Bilgi Güvenliği | `ComplianceReviewRequired` |
| OPEN-BNK-002 | LDAP grup-rol-scope eşleme tablosu ve joiner/mover/leaver kaynağı | IAM / İnsan Kaynakları / Bilgi Güvenliği | `Açık` |
| OPEN-BNK-008 | Kayıt türü bazlı süre, gerekçe ve imha periyodu için hukuk/KVKK/bilgi güvenliği/iç denetim onayı | Hukuk / KVKK Komitesi / İç Denetim | `ComplianceReviewRequired` |
| OPEN-BNK-009 | ServiceNow kurulum yeri, veri işleyen/alt işleyen durumu ve yurt dışı aktarım etkisi | Hukuk / Tedarik / Bilgi Güvenliği | `Açık` |
| OPEN-BNK-011 | Bileşen RPO/RTO hedefleri için iş etki analizi ve banka onayı | İş Sürekliliği / Operasyon | `ComplianceReviewRequired` |
| OPEN-BNK-013 | Sistem risk verisi veya düzenleyici raporlama üretim zincirine girecek mi; BCBS 239 kapsamı | Risk Yönetimi / Veri Yönetişimi | `Açık` |
| OPEN-BNK-018 | Gerçek LDAP endpoint/topolojisi, TLS sertifika güveni, timeout ve teknik hata sahipliği | IAM / Altyapı / Bilgi Güvenliği | `Açık` |
| OPEN-BNK-019 | Nihai giriş/rate-limit eşik ve pencereleri, opak anahtar rotasyonu, güvenilir istemci referansı ve paylaşımlı depo onayı | IAM / Bilgi Güvenliği / Mimari / Altyapı / İç Kontrol | `ComplianceReviewRequired` |

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

## 2026-07-21 — İterasyon 31A Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Kalıcı kaynak kullanım politikası kullanılan worker akışında aktif global politika zorunludur; kaynak kimliği override kaydı kaynak türü kaydından önce uygulanır. Toplam worker ve kaynak sorgu sınırında daha düşük değer güvenli sınırdır. | `FR-039` politikasız kontrolsüz çalıştırmayı reddeder; aynı kaynağa ait iki kotadan geniş olanı seçmek onaylı sınırı aşabilir. | Örtük kod varsayılanıyla devam etmek, kaynak türüne öncelik vermek veya iki sınırdan yüksek olanı kullanmak. | Aktif global politika yoksa claim yapılmaz. Global, kaynak türü ve kaynak kimliği sayısal değerleri kapasite testiyle üretilen sürümlü politika kaydından alınır. |

## 2026-07-21 — İterasyon 31B Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Kaynak çalışma pencereleri IANA saat dilimi, ISO hafta günü ve yerel saat aralığıyla değerlendirilir; başlangıç dahil, bitiş hariçtir. Yasaklı pencere her zaman izinli pencereye üstündür ve izin penceresi yoksa claim yapılmaz. | `NFR-PERF-008` politikasız veya belirsiz zaman aralığında sorgu çalıştırılmamasını gerektirir; UTC saklama ile kaynak yerel çalışma saatinin ayrılması gerekir. | Sunucu yerel saatini kullanmak, boş pencereyi sınırsız izin saymak veya çakışmada izinli pencereye öncelik vermek. | Global ve kaynak override kararları aynı UTC anı için deterministik çözülür; uygun olmayan işler kuyrukta kalır. Üretim penceresi aktif sürümlü kaynak politikasından alınır; kayıt yoksa claim yapılmaz. |

## 2026-07-21 — İterasyon 31C Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Worker claim ve yürütme ayarları tek kaynak politika snapshot'ından çözülür. Çok kaynaklı işte sorgu timeoutu ve retry sayısının en düşüğü, retry gecikmesinin en yükseği uygulanır; yerel worker ayarları daha gevşek politika değerlerine karşı güvenli sınır olarak korunur. | Claim sonrasında politikanın yeniden okunması aynı işte sürüm tutarsızlığı doğurabilir. Çok kaynaklı işin herhangi bir kaynak için onaylı sınırı aşmaması gerekir. | Claim ve yürütmede ayrı politika okuması yapmak, ilk kaynağın değerlerini kullanmak veya en geniş sınırları seçmek. | Kaynak politikası yalnız sorgu timeoutunu daraltır; bağlantı ve toplam timeout değişmez. `retry_count` yeniden deneme sayısıdır ve sıfır değeri ilk teknik hatadan sonra tekrar denemeyi engeller. Sayısal değerler aktif sürümlü kaynak politikasından çözülür. |

## 2026-07-21 — İterasyon 32A Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Kısmi skor uygunluğu yalnız geçerli, onaylı dataset politikası ve dışarıdan ölçülmüş çalışma olgularıyla değerlendirilecektir. Politika yokluğu veya herhangi bir koşul ihlali `PROVISIONAL` kararıdır. | `FR-048` tüm koşulların birlikte sağlanmasını ve politika yokluğunda güvenli varsayılanı gerektirir. Mevcut execution kaydı beklenen kayıt hacmi ve gerçek kapsama oranını güvenilir biçimde içermez. | Eksik oranları sonuç sayaçlarından tahmin etmek, onaysız politikayı kullanmak veya koşullardan bir kısmını yeterli saymak. | `PartialExecutionFacts` oranları ve opak kimlikleri açıkça taşır; karar neden kodu, politika sürümü, kapsama, çalışan/çalışmayan kural sayısı ve eksik partitionları açıklar. `QualityScore` entegrasyonu ayrı dilimde kalır. |

## 2026-07-21 — İterasyon 32B Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Resmî kabul edilen kısmi skor `PARTIAL` statüsünü koruyarak sayısal değer taşır ve resmî agregasyona katılır; provizyonel kısmi skor sayısal değer üretmez. Üst agregasyon, içerdiği resmî kısmi bileşeni `PARTIAL` statüsüyle görünür kılar. | `FR-048`, kısmi niteliğin açıkça gösterilmesini ve yalnız tüm politika koşulları sağlandığında resmî skora katılımı birlikte gerektirir. | Resmî kısmi sonucu `CALCULATED` olarak yeniden sınıflandırmak veya tüm `PARTIAL` sonuçları agregasyondan çıkarmak. | Resmîlik `included_in_official_aggregation` ile açıkça taşınır. Provizyonel sonuç resmî trend ve rapor önizlemesinden çıkarılır; `NO_DATA` ve teknik hata gözlemleri sıfıra çevrilmeden görünür kalır. |

## 2026-07-21 — İterasyon 32C Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Resmî skoru etkileyen dataset kısmi skor politikası yalnız güvenilir normal kullanıcı bağlamıyla talep edilir ve farklı yetkili checker tarafından karara bağlanır. Talep/karar ile merkezi audit outbox kaydı aynı transaction'da kalıcılaşır. | `RULE-005` resmî skoru etkileyen politika değişikliğinde maker-checker; `FR-077` kritik onay işleminde audit veya kalıcı outbox yoksa fail-closed davranış gerektirir. | Doğrudan `APPROVED` politika eklemek, serbest aktör kimliği kullanmak veya audit kaydını işlemden sonra best-effort yazmak. | Yalnız `PENDING` talep yaşam döngüsü üzerinden onaylanır; maker kendi değişikliğini karara bağlayamaz. Audit staging hatası politika işlemini geri alır ve audit kural/partition değerleri yerine yalnız adet ve oran taşır. |

## 2026-07-21 — İterasyon 32D Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Bekleyen dataset kısmi skor politika talebini yalnız talebi oluşturan, güncel rol ve dataset kapsamı doğrulanan maker geri çekebilir; durum geçişi ile merkezi audit outbox aynı transaction'da yazılır. | Geri çekme bir checker kararı değildir; başka aktörün kritik politika talebini kapatması veya audit izi olmadan terminal duruma geçiş görevler ayrılığı ve `FR-077` fail-closed sınırını bozar. | Her maker'ın ya da checker'ın geri çekebilmesi, isteği silmek veya audit kaydını işlemden sonra best-effort yazmak. | Yalnız `PENDING` talep `WITHDRAWN` olur ve etkili politika seçimine katılmaz. Yetkisiz bağlam yazımdan önce reddedilir; audit staging hatasında durum ve önceki audit referansı geri alınır. |

## 2026-07-21 — DQ-SCR Skorlama Karar Paketi

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| `DQ-SCR-001`–`DQ-SCR-033` bağlayıcı proje kararıdır. Ham veri kalitesi skoru; kapsam, güven, dataset kritikliği/veri riski ve teknik sağlıktan ayrı tutulur. Skor kural → veri öğesi → boyut → dataset hiyerarşisinde, sürümlü politika ve kritik kural kontrolüyle hesaplanır. | Tek yüzde; teknik hatayı kalite hatasına, düşük kapsamı güvenilir kaliteye veya kritikliği kalite ölçümüne dönüştürebilir. Açıklanabilirlik, anti-gaming ve tarihsel yeniden üretilebilirlik için model/politika sürümleri ile görevler ayrılığı gerekir. | Mevcut kural ağırlıklı ortalamayı tek başına korumak; dataset kritikliğini kaynak kalite skoruna ağırlık olarak katmak; kapsam/güven/risk/teknik durumu hesaplama detayında eritmek; ham skoru override ile değiştirmek. | `04.06-Skorlama.md` kanonik karar kaydıdır; `ADR-015` hedef mimariyi tanımlar. Dataset kritikliğini kalite skoruna katan tarihsel yaklaşım `Superseded` oldu, ancak geçmiş skorlar değişmez. Üretim eşik/ağırlık/veto/güven/risk değerleri aktif, sürümlü ve onaylı politika kaydından çözülür; kayıt yoksa ilgili sonuç fail-closed üretilmez. Bu dokümantasyon kararı runtime uygulama veya banka onayı değildir. |

## 2026-07-21 — Ölçüm Yeterliliği Hedef Tasarımı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Kural sayaçları kanonik değişmezlerle tutulacak; ham ve nihai kalite skoru, kritik kural durumu, ölçüm yeterliliği, kullanım kararı ve teknik çalışma durumu ayrı üretilecektir. Yeterlilik kapsam, örneklem, güncellik, teknik başarı, sürüm, kritik kontrol ve kanıt kapılarıyla değerlendirilir. | Tek skor alanı; yüksek kaliteyi yetersiz ölçümle, teknik hatayı kalite düşüşüyle veya kritik kontrolü ağırlıklı ortalamayla karıştırabilir. | Yalnız mevcut skor statülerini genişletmek; teknik hatayı sıfır skor yapmak; yüksek skor varsa ölçümü otomatik yeterli saymak; kritik sonucu ham skora gömmek. | [Kanonik tasarım](../02-Mimari/Veri-Kalitesi-Skorlama-ve-Olcum-Yeterliligi.md), FR-046–FR-053 ve AC/TS-039–047 hedef sözleşmedir. Eşik, minimum kapsam/güven, geçerlilik, kanıt/onay, kullanım/blokaj ve remediation değerleri aktif sürümlü politika kaydından çözülür; kayıt yoksa olumlu yeterlilik veya kullanım kararı üretilmez. Bu karar runtime uygulaması veya banka onayı değildir. |

## 2026-07-21 — Sentetik Veri ve Gizlilik Hedef Tasarımı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Sentetik veri sürümlü dataset politikası, deterministik seed/run lineage'ı, temel üretimden ayrı kusur enjeksiyonu ve runtime kural/skor motorundan bağımsız ground truth ile yönetilecektir. Sentetik veri anonimlik kanıtı değildir; test olayları yalnız izole fake/sandbox hedeflere gider. | Üretim verisini birebir kopyalamadan gerçekçi görev faydası sağlamak, self-validation ve yeniden tanımlama riskini engellemek gerekir. | Sentetik vakaları kod içi sabitlerle üretmek; yalnız kimlik değiştirerek anonim saymak; skor motorunun kendi sonucunu beklenen değer yapmak; sentetik performans testini nihai kabul saymak. | [Kanonik tasarım](../02-Mimari/Sentetik-Veri-ve-Gizlilik-Stratejisi.md), `ADR-016`, `FR-088–FR-096` ve `AC/TS-048–056` hedef sözleşmedir. Nicel eşik/tolerans aktif politikada zorunludur ve eksikse `BLOCKED`; üretim profili/örneği kullanımı varsayılan kapalıdır. `OPEN-014` nihai performans kabulü korunur. Bu karar runtime uygulaması, hukuki anonimlik veya banka onayı değildir. |

## 2026-07-21 — İterasyon 33A Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Kural sonucu sekiz nullable kanonik sayaç ve ayrı `MeasurementStatus` taşır; sayısal oran yalnız `EvaluatedCount > 0` iken `PassedCount / EvaluatedCount` ile hesaplanır. Eski kanoniksiz kayıtlar tahminî değerlerle tamamlanmaz. | Kapsam dışı, teknik hatalı veya uygulanabilirliği bilinmeyen kayıtların eski `checked_count` paydasında kalite başarısızlığı gibi davranması yanlış skor üretir. Bilinmeyen teknik sayacı sıfır varsaymak ölçüm güvenilirliğini olduğundan yüksek gösterir. | Eski `checked_count` formülünü korumak; `not_evaluated_count` değerini tek bir kanonik sınıfa taşımak; sıfır paydalı durumları 0 puan yapmak. | `RULE_SCORE_V2_EVALUATED_DENOMINATOR` yeni kural skoru formül sürümüdür. Kanonik sayaç bulunmayan tarihsel satırlar fail-closed yeniden skorlama reddi alır; append-only migration/backfill ve geçmiş sürüm sınırı kararı runtime'da henüz uygulanmamıştır. |

## 2026-07-21 — İterasyon 34A Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Sentetik üretim işi yalnız güvenilir kullanıcı bağlamı, dataset kapsamı ve tek etkili onaylı politika ile kaydedilir; politika, senaryo ve run sürümleri append-only tutulur. Aynı lineage girdisinin tekrar talebi yeni run kimliği oluşturur. | Politika belirsizliğinin sessizce çözülmesi, geçmiş lineage'ın değiştirilmesi veya audit olmadan run kabulü yeniden üretilebilirlik ve fail-closed güven sınırını bozar. | En son eklenen politikayı örtük seçmek; aynı seed için mevcut run'ı döndürmek; audit'i işlem sonrasında best-effort yazmak. | Run ve merkezi audit outbox aynı transaction'da yazılır. Seed lineage kaydında korunur, audit özetinde yalnız `seed_present` bulunur. Politika/senaryo yönetim yaşam döngüsü, üretici, ground truth ve gizlilik kapısı sonraki ayrı artımlardır. |

## 2026-07-21 — İterasyon 34B Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| İlk Golden üretici yalnız tamamen yapay, kusursuz ve eksiksiz teknik V1 profili kabul eder; dış veri/profil/saat bağımlılığı kullanmaz. Kanonik digest run kimliğini dışarıda bırakır fakat tüm veri lineage'ını içerir. | Üretim profilinden öğrenme varsayılan kapalıdır; aktif sentetik politika olmadan üretim benzerliği veya eşik varsayılamaz. Operasyonel run kimliği replay içeriğine katılırsa aynı seed ve sürümlerin byte eşdeğerliği bozulur. | Üretim profilinden örnek okumak; rastgele sistem saati/UUID kullanmak; run kimliğini veri digest'ine katmak; nicel dağılım hedefi uydurmak. | `GOLDEN_RELATIONAL_GENERATOR_V1`, `GOLDEN_RELATIONAL_SCHEMA_V1` ve `GOLDEN_RELATIONAL_CONFIG_V1` yalnız sentetik teknik sözleşmelerdir. Aynı giriş aynı kanonik çıktı ve SHA-256 referansı üretir; çıktı kalıcılığı ve run tamamlama geçişi sonraki artıma bırakılmıştır. |

## 2026-07-21 — İterasyon 34C Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| İlk bağımsız oracle yalnız sıfır kusurlu Golden profilin yapısal beklentisini run ve senaryo sözleşmesinden üretir; üreticinin `validation` sonucunu veya runtime skor motorunu kullanmaz. Ground truth ve gerçekleşen doğrulama sonucu append-only ve atomik auditli saklanır. | Test edilen implementasyonun kendi çıktısını beklenen değer olarak kullanması self-validation oluşturur. Aktif sentetik politika olmadan skor toleransı veya kusur yoğunluğu varsayılamaz. | Üreticinin yapısal sonucunu doğrudan ground truth yapmak; sayısal skoru sıfır toleransla karşılaştırmak; başarısız sonucu ground truth'a yansıtmak; audit'i sonradan best-effort yazmak. | `GOLDEN_STRUCTURAL_ORACLE_V1` yalnız sayım, anahtar, ilişki, durum, referans ve zaman bütünlüğünü karşılaştırır. Sapma `BLOCKED`, depo/audit arızası teknik hatadır. Kayıt düzeyi kusur, skor, önem, bildirim ve eskalasyon karşılaştırması runtime artımıdır. |

## 2026-07-22 — İterasyon 34D Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Özgün sentetik run talebi append-only kalacak; terminal durum, kanonik digest, çıktı/doğrulama/saklama/audit referansları ayrı append-only completion kanıtında tutulacaktır. Tamamlama servisi kanonik payload'ı kayıtlardan yeniden kuracak, sunulan digest ve referansı doğrulayacak; ham payload saklanmayacaktır. Aynı kanıt idempotent, çelişen kanıt reddedilecektir. | Talep satırını sonradan güncellemek lineage geçmişini değiştirir; çağıranın digest beyanına güvenmek manipülasyonu gizler; ham payload'ı yerel metadata deposuna yazmak minimizasyon ve saklama kapsamını gereksiz büyütür. | Run satırını terminal durumla güncellemek; ham payload'ı SQLite'ta saklamak; sunulan digest'i yeniden hesaplamadan kabul etmek; audit'i best-effort yazmak. | `synthetic_run_completions` yalnız terminal kanıt ve opak referansları tutar; completion ile merkezi audit outbox atomiktir. Fiziksel çıktı/artifact deposu, gerçek saklama süreleri ve gizlilik kapısı açık kalır. |

## 2026-07-22 — İterasyon 34E Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Çok dönemli sentetik zaman üretimi mevcut Golden V1'i değiştirmeyen ayrı generator/şema/konfigürasyon sürümüyle çalışacak; temporal profil append-only saklanacak ve altı zaman anlamı bağımsız validator ile UTC, sıra ve dönem ataması açısından doğrulanacaktır. | Golden V1 payload'ını genişletmek mevcut replay digest'ini değiştirir. Zaman alanlarını tek damgaya indirgemek event, kaynak, ingestion, processing ve kalite kontrol anlamlarını karıştırır. | Golden V1'i yerinde değiştirmek; sistem saatini kullanmak; yalnız alan sırasını generator içinde kontrol etmek; gecikme değerlerini üretim SLA'sı saymak. | `TEMPORAL_MULTI_PERIOD_GENERATOR_V1` yalnız tamamen yapay teknik profildir. Profil değerleri test girdisidir; banka SLA'sı, üretim dağılımı veya drift eşiği değildir. Eksiklik, geç/sırasız akış, drift ve hacim ayrı artımlarda kalır. |

## 2026-07-22 — İterasyon 30B Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| İlk çalışan frontend artımı yalnız sabit sentetik fixture ile kurulacak; üretim API'si, IdP/oturum veya banka verisine bağlanmayacaktır. Grafik ve erişilebilir tablo aynı view-model'i kullanacak, teknik hata ile provizyonel sonuç resmî trend çizgisinden dışlanacaktır. | Kullanıcıya çalışan bir frontend göstermek gerekirken geçiş kapısı ve 21B güvenli HTTP/API sınırı tamamlanmamıştır. Bu sınırlar tahmin edilirse UI sahte yetki ve üretim sözleşmesi iddiası üretir. | Frontend'i tamamen ertelemek; üretim API alanlarını tahmin etmek; statik ekran görüntüsünü çalışan ürün gibi sunmak; teknik hatayı sıfır skorla çizmek. | `04-Frontend/app/` React + TypeScript + Vite, MUI, ECharts, Storybook ve Playwright çalışma alanıdır. Ekran sentetik olduğunu görünür belirtir; `OPEN-BNK-020` banka onaylıdır. Gerçek bağlantılı dashboard 21B'de onaylı BFF/session politikasının uygulanmasını ve geçiş kapısındaki diğer bağımlılıkları bekler. |

## 2026-07-22 — İterasyon 33B Teknik Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Yeni kaynak kalite skoru dataset kritikliğini ağırlık olarak kullanmayacak; resmî dataset skorları `SOURCE_EQUAL_DATASET_QUALITY_V2` ile eşit kalite ağırlığında toplanacak ve kritiklik yalnız ayrı profil kanıtı olarak taşınacaktır. | `DQ-SCR-018` ve `AC/TS-030`, kritikliğin kalite skoruna katılmasını yasaklar. Eski `SOURCE_WEIGHTED_V1` davranışı aynı kalite ölçümünü metadata kritikliği değiştiğinde farklı sonuçlandırır. | Kritiklik katsayılarını nötr `1.0` tutarak eski formülü korumak; eski skorları yerinde V2 ile yeniden yazmak; onaysız risk katsayısı üretmek. | Yeni hesaplarda formül ve eşit ağırlık politikası sürümlü saklanır. Tarihsel V1 skorları değiştirilmez. Replay/backfill, trend sürüm sınırı ve ayrı risk/güven/yeterlilik/kullanım modelleri `OPEN-022/023` altında ayrı artımlar olarak kalır. |

## 2026-07-22 — Değişken Politika Değerlerinin Kesinleştirilmesi

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Kapasite, kaynak kullanımı, skorlama, yeterlilik, risk ve sentetik doğrulama gibi ortama veya kullanım bağlamına göre değişen sayısal değerler kodda sabitlenmeyecek; aktif, sürümlü ve gerekli onayı taşıyan politika kaydından çözülecektir. Politika yoksa işlem veya olumlu karar fail-closed reddedilecektir. | Tek bir varsayımsal sayıyı üretim değeri saymak kaynak güvenliğini, skor doğruluğunu ve yeniden üretilebilirliği bozar. Kullanıcı teknik yönü kesinleştirmiştir; değer değişikliği yönetişimli politika işlemidir. | Değerleri karar bekleyen yer tutucular olarak bırakmak; yerel varsayılanları üretime taşımak; eksik politikada en son değeri örtük kullanmak. | `OPEN-019`–`OPEN-024` karar yönleri `KararAlındı` durumundadır. Politika kayıtlarının oluşturulması uygulama/operasyon işidir; eksik kayıt karar belirsizliği değil fail-closed konfigürasyon durumudur. |
| Sentetik üreticinin üretim profili veya örneğinden öğrenmesi varsayılan olarak yasaktır. Yalnız veri sahibi, hukuk/KVKK ve bilgi güvenliği onaylı; minimize edilmiş, izole ortam ve saklama politikası bağlı referansla ayrı politika sürümünde açılabilir. | Sentetik etiketinin anonimlik kanıtı sayılmasını ve üretim verisinin kontrolsüz biçimde test ortamına taşınmasını engellemek gerekir. | Üretim profilini varsayılan açık kullanmak veya yalnız teknik ekip onayıyla etkinleştirmek. | `OPEN-025` teknik yönü `KararAlındı`dır; gerekli kurumsal incelemeler `ComplianceReviewRequired` olarak ayrı kalır. |

## 2026-07-22 — OPEN-BNK-020 Banka Onaylı Normal Kullanıcı Oturum Politikası

Durum: `ApprovedByBank`

Onay referansı: `USER-DECLARATION-2026-07-22-OPEN-BNK-020`

- Kullanıcı başına en fazla bir aktif normal oturum bulunur. Yeni başarılı giriş
  önceki oturumu iptal eder; mevcut oturum yeni girişi engellemez.
- Boşta kalma süresi `PT1H`, mutlak süre `PT10H`'dir. Arka plan istekleri idle
  süresini, token yenileme mutlak süreyi uzatmaz. Süre sonunda yeniden kimlik
  doğrulama zorunludur.
- Mimari BFF'tir. Access ve refresh token'ları yalnız sunucu tarafında tutulur;
  tarayıcı bu token'lara erişemez ve yalnız opak oturum cookie'si taşır.
- Cookie adı `__Host-session`; nitelikleri `Secure`, `HttpOnly`,
  `SameSite=Lax`, `Path=/` ve `Domain` kullanılmaması şeklindedir. Cookie girişte
  ve ayrıcalık değişikliğinde döndürülür.
- State-changing isteklerde synchronizer token custom header ile zorunludur.
  Origin, Referer, Fetch Metadata ve CORS allowlist doğrulanır; `GET` ile durum
  değişikliği yasaktır.
- Üretim deposu kurum onaylı yüksek erişilebilir merkezi depodur; bu hizmet yoksa
  PostgreSQL kullanılır. Süreç belleği üretimde kullanılamaz. Session ID özeti
  saklanır, aktarım TLS ile, at-rest şifreleme ve anahtar yönetimi kurum onaylı
  KMS veya HSM ile sağlanır.
- Logout, idle/mutlak timeout, yeni başarılı giriş, kullanıcının pasifleştirilmesi,
  kritik rol değişikliği, güvenlik olayı ve IdP oturum iptali merkezi iptal
  tetikleridir. Reddedilen credential yeniden kullanılamaz.
- Oturum sırrı sonlandırmada derhal geçersizleştirilir ve silinir. Access/refresh
  token arşivlenmez. Veri-minimum güvenlik metadatası `P90D` saklanır; legal hold
  süreyi uzatabilir ve imha kanıtı zorunludur.
- Politika sürümlüdür. Limit/süre, cookie-token-CSRF, depo/şifreleme ve
  saklama-imha değişiklikleri tanımlı IAM, Bilgi Güvenliği, Mimari, Altyapı,
  Hukuk ve Uyum/İç Kontrol sahiplerinin onayını gerektirir. Acil değişiklik
  yalnız Bilgi Güvenliği tarafından süreli yapılabilir ve sonradan incelemeye
  tabidir.

Üretim session store teknolojisinin kurulması, şifreleme ve anahtar yönetimi,
`P90D` fiziksel saklama/imha uygulaması ve uygulanabilir düzenleme kanıtı karar
değil uygulama ve uygunluk kanıtı olarak izlenir.

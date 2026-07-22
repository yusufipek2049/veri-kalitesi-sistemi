---
type: project-memory
status: planned
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-22
tags:
  - proje
  - sonraki-adim
  - mvp
  - banka
---

# Sonraki Adımlar

## Geçiş Önceliği

Mevcut 16 iterasyonun, Iterasyon 17A–17E audit, Iterasyon 18A–18C veri koruma, Iterasyon 19A–19H maker-checker, Iterasyon 20A–20E LDAP/oturum güvenliği ve Iterasyon 25A–25D saklama/legal hold/imha/arşiv yetkilendirme dikeylerinin çekirdeği korunur. Banka kararları tamamlanmadan yeni HTTP yüzeyi açılmaz.

Bakım İterasyonu 29C.1 ile tam mypy baseline'ı sıfır hataya indirilmiştir;
sonraki değişiklikler bu baseline'ı korumalıdır.

1. İterasyon 19G — Bağlantı yapılandırması revizyonu ve bekleyen aktivasyon onayını geçersizleştirme; `TechnicallyVerified`.
2. İterasyon 19H — Kontrollü kaynak pasifleştirme ve yeni iş kabulünü engelleme; `TechnicallyVerified`.
3. İterasyon 21A — Yetki güven sınırına bağlı dashboard trend domain sorgusu; `TechnicallyVerified`.
4. İterasyon 21B — Yerel/test dashboard özet HTTP yüzeyi `TechnicallyVerified`.
   FastAPI, `/api/v1`, veri-minimum DTO, Problem Details, fail-closed production
   resolver ve bağlı frontend uygulanmıştır. 20E BFF `__Host-session` ve CSRF
   HTTP sınırını tamamlamıştır; gerçek OIDC/SAML callback, state/nonce ve üretim
   store bağlantısı açık kalır.
5. İterasyon 22 — 22A–22I bildirim ve denetlenebilir issue yaşam döngüsü `TechnicallyVerified`.
6. İterasyon 23 — ServiceNow veri-minimizasyonlu adaptör; 23A–23D `TechnicallyVerified`.
7. İterasyon 24 — 24A audit inceleme ve 24B maskeli rapor önizleme `TechnicallyVerified`; hassas dışa aktarma `OPEN-BNK-014` nedeniyle engelli.
8. İterasyon 25 — 25A saklama dry-run, 25B legal hold, 25C imha kanıtı ve 25D arşiv geri çağırma talep/kararı `TechnicallyVerified`; gerçek fiziksel/arşiv adaptörleri açık.
9. İterasyon 26 — 26A kayıt/karar ve 26B yetki filtreli timeline inceleme `TechnicallyVerified`; gerçek SIEM/SOC `OPEN-BNK-010` nedeniyle engelli.
10. İterasyon 27 — 27A fail-closed ortam kimliği `TechnicallyVerified`; yedekleme, geri yükleme ve DR kanıtları altyapı kararına bağlı.
11. İterasyon 28 — 28A secret, 28B doğrudan bağımlılık SBOM'u, 28C SAST, 28D doğrudan bağımlılık zafiyet sürüm kapısı ve 28E sızma testi bulgu takibi `TechnicallyVerified`; gerçek scanner, transitive çözüm ve gerçek pentest açık.
12. İterasyon 29 — 29A manifest, 29B drift kapısı ve 29C birleşik yerel preflight `TechnicallyVerified`; 29D kurumsal CI/CD/imzalı kanıt yayını engelli.

## Geçiş Backlogu

| Sıra | Ürün artımı | Gereksinim / kontrol bağlantıları | Çıkış kriteri | Durum |
| --- | --- | --- | --- | --- |
| 17 | Merkezi audit bütünlüğü | `BR-007`, `FR-077`–`FR-079`, `BFR-AUD-001`–`BFR-AUD-004` | Ortak olay zarfı, redaksiyon, correlation ve bütünlük doğrulaması | 17A–17E `TechnicallyVerified`; üretim operasyonlaştırması açık |
| 18 | Veri sınıflandırma ve maskeleme | `RULE-009`, `RULE-010`, `NFR-PRV-*`, `BFR-DATA-001`–`BFR-DATA-004` | Onaylı sınıf sözlüğü ve deny-by-default görüntüleme/örnek politikası | 18A–18C `TechnicallyVerified`; banka eşlemesi/onayları açık |
| 19 | Maker-checker | `RULE-001`, `RULE-005`, `RULE-007`, `BFR-SOD-001`–`BFR-SOD-004` | Hazırlayan kendi kritik değişikliğini aktive edemez | 19A–19H `TechnicallyVerified`; banka rol eşlemesi, gerçek takvim/worker, diğer kritik işlem sınıfları ve çalışan iş politikası açık |
| 20 | LDAP/RBAC adaptörü | `FR-001`–`FR-006`, `UC-001`, `BFR-IAM-001`–`BFR-IAM-006` | LDAP grubu güvenilir role/scope'a dönüşür; giriş ve oturum başarısızlığı fail-closed | 20A adaptör/eşleme, 20B giriş sınırı, 20C temel session, 20D onaylı süre/tek oturum ve 20E BFF cookie/CSRF `TechnicallyVerified`; gerçek IdP ve üretim altyapısı açık |
| 21 | Dashboard trend ve HTTP okuma | `FR-054`–`FR-057`, `UC-010`, `NFR-PERF-001`, `NFR-PERF-002` | Son 30 gün trendi boş dönemleri sıfırlaştırmadan ve güvenilir scope ile döner | 21A `TechnicallyVerified`; 21B HTTP geçiş kapısına bağlı |
| 22 | Bildirim ve issue | `FR-059`, `FR-060`, `FR-064`–`FR-070`, `BFR-DATA-003` | Hassas veri içermeyen sistem içi bildirim ve denetlenebilir issue state machine | 22A–22I `TechnicallyVerified`; gerçek adaptörler ve operasyon politikaları açık |
| 23 | ServiceNow adaptörü | `FR-070`, `FR-087`, `BFR-EXT-001`–`BFR-EXT-003` | Alan whitelist'i, idempotency ve ham veri çıkışının engellenmesi | 23A–23D `TechnicallyVerified`; gerçek ağ/dağıtık state ve banka kararları açık |
| 24 | Rapor/audit erişimi | `FR-072`, `FR-075`, `FR-077`–`FR-079`, `BFR-EXP-001`–`BFR-EXP-003` | Yetki, gerekçe, maskeleme ve auditli dışa aktarma | 24A audit inceleme ve 24B rapor önizleme `TechnicallyVerified`; dosya dışa aktarma banka kararına bağlı |
| 25 | Saklama/imha/legal hold | `RULE-014`, `BFR-LCM-001`–`BFR-LCM-004` | Kayıt türü bazlı politika; imha ve geri çağırma kanıtı | 25A–25D sözleşmeleri `TechnicallyVerified`; gerçek fiziksel/arşiv adaptörleri ve banka onayı açık |
| 26 | SIEM ve ihlal kanıtı | `NFR-OBS-*`, `BFR-IR-001`–`BFR-IR-004` | Güvenlik olayları ve ihlal zaman çizelgesi; otomatik Kurul bildirimi yok | 26A–26B `TechnicallyVerified`; gerçek SIEM/SOC `OPEN-BNK-010` ile engelli |
| 27 | DR ve ortam ayrılığı | `NFR-DR-*`, `BFR-OPS-001`–`BFR-OPS-004` | Banka onaylı RTO/RPO; restore testi ve ortam ayrımı kanıtı | 27A `TechnicallyVerified`; 27B/27C `OPEN-BNK-011/012` ile engelli |
| 28 | Güvenli SDLC ve pentest hazırlığı | `NFR-SEC-*`, `BFR-SDLC-001`–`BFR-SDLC-005` | SAST, secret/dependency taraması, SBOM ve pentest kapsamı | 28A–28E yerel teknik sözleşmeleri `TechnicallyVerified`; gerçek ürün, CI/CD ve banka pentest kararları açık |
| 29 | Banka kabul paketi | Tüm `BFR-*` ve `CTRL-*` | Teknik kanıtlar ve eksikler görünür; banka onayları ayrı durumda | 29A–29C `TechnicallyVerified`; 29D `OPEN-BNK-012` ve banka kararlarıyla engelli |

## Mevcut MVP Backlogundan Korunan İşler

| Ürün artımı | Yeni sıradaki yeri | Not |
| --- | --- | --- |
| Beş alanlı POSIX cron alt kümesinin uygulanması | Geçiş kapısından sonra | Gramer/timezone/DST kararı alındı; parser entegrasyonu ve testleri bekliyor |
| Şema değişikliğinde ilişkili kuralları `REVIEW_REQUIRED` durumuna alma | Metadata/kural yönetimi artımı | Karar alındı; metadata değişim bayrağı ve kural geçişi uygulanacak |
| Kalıcı `QualityDimension` UUID varlığı | Skorlama veri modeli artımı | Karar alındı; iş kodu korunarak migration/replay uygulanacak |
| Dashboard trend ve operasyon listeleri | İterasyon 21 | Güvenilir yetki bağlamından sonra |
| Bildirim ve issue yaşam döngüsü | İterasyon 22 | Veri minimizasyonu ve merkezi auditten sonra |
| Raporlama ve audit inceleme | İterasyon 24 | Dışa aktarma kontrolüyle birlikte |

## Frontend Tasarım Backlogu

Bu kimlikler teslimat backlog kimlikleridir; yeni SRS gereksinimi değildir.
30B yalnız sentetik ve bağlantısız çalışma artımıdır. Üretim verisi, eylem ve
drill-down maddeleri geçiş kapısı ile ilgili güvenli API sözleşmesine bağlıdır.

| ID | Ürün artımı | Öncelik | Bağımlılık | Durum |
| --- | --- | --- | --- | --- |
| FE-DS-001 | Kurumsal design token sistemi | Must | — | 30B `TechnicallyVerified` |
| FE-DS-002 | Açık ve koyu tema tanımları, kullanıcı seçimi ve tercih kalıcılığı | Must | FE-DS-001 | 30C `TechnicallyVerified` |
| FE-DS-003 | Ortak KPI kartı | Must | FE-DS-001 | 30B sentetik alt kapsam `TechnicallyVerified` |
| FE-DS-004 | Ortak status badge ve status mapper | Must | FE-DS-001 | 30B `TechnicallyVerified` |
| FE-DS-005 | Ortak alarm bileşeni | Must | FE-DS-004 | 30B sentetik alt kapsam `TechnicallyVerified` |
| FE-DS-006 | Ortak chart wrapper ve formatter | Must | FE-DS-001 | 30B trend alt kapsam `TechnicallyVerified`; bar/heatmap açık |
| FE-DS-007 | Ortak data table standardı | Must | FE-DS-001, API sayfalama sözleşmesi | Planlı / engelli |
| FE-DS-008 | Kurumsal dashboard referans ekranı | Must | 21B, FE-DS-003–007 | 30B sentetik/bağlantısız alt kapsam `TechnicallyVerified`; üretim bağlantısı engelli |
| FE-DS-009 | Storybook story altyapısı | Must | FE-DS-001 | 30B `TechnicallyVerified` |
| FE-DS-010 | Playwright görsel regression altyapısı | Must | Çalışan frontend | 30B viewport/screenshot altyapısı `TechnicallyVerified`; onaylı diff eşiği açık |
| FE-DS-011 | Grafik erişilebilirlik kontrolleri | Must | FE-DS-006, FE-DS-010 | 30B trend tablo alternatifi ve klavye alt kapsamı `TechnicallyVerified` |
| FE-DS-012 | Teknik hata ve kalite ihlali görsel ayrım testleri | Must | FE-DS-004, FE-DS-009/010 | 30B `TechnicallyVerified` |
| FE-DS-013 | Marka rengi token kullanım lint/review kapısı | Should | FE-DS-001, lint yaklaşımı kararı | Planlı / engelli |
| FE-DS-014 | Referansla uyumlu `ANALİZ`/`OPERASYON` navigasyon grupları, gerçek ikonlar ve simetrik hizalama | Must | FE-DS-001 | 30C `TechnicallyVerified` |
| FE-DS-015 | Route, yetkisiz erişim ve bulunamadı durumlarını taşıyan istemci navigasyon kabuğu | Must | İlk alan ekranı | `FE-DEC-002` KararAlındı; 35A ile uygulanacak |
| FE-DASH-001 | Ölçüm yeterliliği, kritik kontrol ve teknik hata KPI sözleşmesi ile API bağlantısı | Must | Yeterlilik runtime'ı, dashboard API | 21C DTO `TechnicallyVerified`; 30D KPI bağlantısı sırada, kritik kontrol runtime kaynağı açık |

### Kullanıcı Öncelikli Frontend Teslimat Sırası

Kullanıcının 2026-07-22 tarihli açık önceliği doğrultusunda aşağıdaki işler,
hazır oldukları anda genel teknik borç backlogunun önünde ele alınacaktır:

1. **İterasyon 30C — Uygulama kabuğu görsel uyumu ve tema:**
   `TechnicallyVerified`; referans grupları, hizalı ikonlar ve açık/koyu tema
   tamamlandı.
2. **İterasyon 20E — BFF oturum ve CSRF HTTP sınırı:** `TechnicallyVerified`.
3. **İterasyon 21C — Dashboard operasyonel gösterge API'si:**
   `TechnicallyVerified`; olumlu yeterlilik ve kritik kontrol sayısı
   uydurulmadan veri-minimum DTO sağlandı.
4. **İterasyon 30D — Dashboard referans içerik tamamlaması:** Sıradaki artım;
   21C alanlarının
   KPI'lara bağlanması; veri alanı karşılaştırması ve kalite boyutu matrisi.
5. **İterasyon 35A–35F — Alan ekranları:** Sırasıyla Veri Kaynakları, Kurallar,
   Çalıştırmalar, Sorunlar, Raporlar ve Denetim. Her dilim route, güvenli API,
   yetki, loading/empty/error durumları, Storybook ve Playwright kanıtıyla ayrı
   teslim edilecektir.

30C, 20E ve 21C tamamlandı. 35A–35F'nin üretim bağlantısı gerçek IdP callback,
HA session store ve ilgili güvenli API/repository sınırları tamamlanmadan açılmaz.
Rapor dosyası dışa aktarma,
`OPEN-BNK-014` kapsamındaki banka veri sahibi/bilgi güvenliği onayı ve güvenli
dışa aktarma uygulaması tamamlanmadan 35E kapsamına alınmaz; güvenli rapor
önizleme ayrı kalır.

### Kesinleşen Frontend Kararları

| ID | Karar | Kesinleşen seçenek | Etkilediği dilim |
| --- | --- | --- | --- |
| FE-DEC-001 | Navigasyon ve kaynak türü ikon yaklaşımı | `lucide-react`; vendor logosu yerine ürün bağımsız database/file/API ikonları | 30C, 35A |
| FE-DEC-002 | İstemci routing yaklaşımı | `react-router-dom`; route bazlı code splitting ve yetkisiz/not-found sınırları | 35A–35F |
| FE-DEC-003 | Tema başlangıcı ve tercih saklama | İlk açılışta açık tema; kullanıcı seçimi `localStorage` içinde yalnız `light`/`dark` tercihi olarak saklanır | 30C |
| FE-DEC-004 | Dashboard KPI zaman ve snapshot anlamı | Yeterlilik son geçerli ölçümden; kritik kontrol son tamamlanan execution'dan; teknik hata seçili dönemden, varsayılan son 30 UTC günden hesaplanır | 21C, 30D |

Alan ekranlarının ilk dilimleri salt okunur liste ve detay olarak kurulacaktır;
yazma, onay, çalıştırma ve dışa aktarma eylemleri kendi güvenlik ve maker-checker
koşullarıyla sonraki küçük artımlarda açılır. Bu ayrıştırma yeni ürün kararı değil,
mevcut çevik teslim ve güvenlik kurallarının uygulama sırasıdır.

## Sentetik Veri Backlogu

Bu maddeler `ADR-016` hedef tasarımını küçük dikeylere böler.

| ID | Ürün artımı | Gereksinim | Çıkış kriteri | Durum |
| --- | --- | --- | --- | --- |
| SYN-001 | Sentetik dataset politika, senaryo ve run kayıt çekirdeği | FR-088, FR-093; AC/TS-049 | Fail-closed politika çözümleme, değişmez sürüm/seed/run kaydı ve veri-minimum audit | 34A `TechnicallyVerified` |
| SYN-002 | Deterministik Golden ilişkisel üretici | FR-089, FR-090; AC/TS-048/049 | Şema, anahtar, referans, durum ve temel dağılım ilişkileri aynı seed ile tekrar üretilebilir | 34B üretici ve 34D kalıcı terminal referansları `TechnicallyVerified`; yalnız tamamen yapay teknik V1 profil |
| SYN-003 | Kusur enjeksiyonu, ground truth ve bağımsız karşılaştırıcı | FR-091, FR-092; AC/TS-050–052 | Geçerli uç/kusur ayrımı, boyut-kural bağı ve runtime'dan bağımsız beklenen sonuç | 34F kayıt düzeyi dokuz teknik kusur sınıfı ve bağımsız SQL oracle'ı `TechnicallyVerified`; runtime kural/skor/olay karşılaştırması açık |
| SYN-004 | Zaman, eksiklik, drift ve hacim profilleri | FR-090, FR-094; AC/TS-054/056 | Zaman alanı anlamları, eksiklik mekanizmaları, drift ve kaynak bütçeli hacim replay'i | 34E çok dönemli zaman semantiği `TechnicallyVerified`; eksiklik/drift/hacim açık, üretim performans kabulü `OPEN-014` ile ayrı |
| SYN-005 | Gizlilik kapısı, yaşam döngüsü ve izole olay testi | FR-095, FR-096; AC/TS-053/055/056 | Gizlilik sonucu, retention yaşam döngüsü ve üretim hedefi fail-closed negatifleri | KararAlındı; runtime politika/gizlilik değerlendiricisi uygulanmadı |

## Önerilen Sonraki İterasyon

### Kanıta Dayalı Karar Sistemi İkinci Faz Backlogu

Bu hedef, mevcut kullanıcı öncelikli frontend zincirini değiştirmez.
`OPEN-026–OPEN-036` teknik yönleri kesinleşmiştir; küçük dikeyler şu bağımlılık
sırasıyla ele alınacaktır:

1. `FR-098/099`: değişmez kanıt öğesi/bağı ve yeniden üretim manifesti.
2. `FR-097/100`: kullanım amacı profili ve kaynaklı etki değerlendirmesi.
3. `FR-101/102`: değişiklik simülasyonu, lineage snapshot'ı ve değişiklik olayı.
4. `FR-103/104`: kanıt sınırları içinde teşhis ve öneri.
5. `FR-106–FR-109`: veri kontratı, adaptif tarama, gizliliği koruyan inceleme
   ve kalite borcu.
6. `FR-105`: yalnız onaylı politika ile dry-run/canary/rollback remediation.
7. `FR-110/111`: izole chaos deneyi, zaman çizelgesi ve kanıt paketi.

Her adımda gerekli kurumsal adaptör ve aktif sürümlü politika Definition of Ready
koşuludur. Kararların kapanmış olması runtime tamamlanmışlığı veya banka onayı
ifade etmez.

Teknik inceleme `R-04` kapsamında yanlış `SOURCE` kritiklik ağırlıklandırması
İterasyon 33B ile giderildi. `R-04`ün replay/backfill ve tam ayrık sonuç modeli
alt kapsamlarında karar alınmıştır; runtime migration ve politika modelleri
henüz uygulanmamıştır. İncelemenin doğruluk ve veri
bütünlüğü sırasındaki sonraki küçük, hazır aday **R-06 — SQLite foreign key
enforcement ve orphan doğrulaması**dır; uygulamadan önce etkilenen repository
connection'ları ve silme semantikleri tek tek doğrulanmalıdır.

**İterasyon 30B — Sentetik dashboard çalışma iskeleti** ve **İterasyon 30C —
Uygulama kabuğu görsel uyumu ve tema** tamamlandı. 30C, referanstaki navigasyon
sınıflandırmasını, hizalı Lucide ikonlarını, açık/koyu tema üretimini, kullanıcı
tema seçimini ve iki temada beş viewport doğrulamasını sunar.

Kullanıcı öncelikli frontend zincirindeki BFF güvenlik ön koşulu
**İterasyon 20E — BFF oturum ve CSRF HTTP sınırı** ile **İterasyon 21C —
Dashboard operasyonel gösterge API'si** tamamlandı. Sıradaki küçük artım 30D
dashboard içerik tamamlamasıdır.
Sentetik veri alanı karşılaştırması ile kalite boyutu matrisi 30D kapsamındadır.

**İterasyon 34E — Deterministik çok dönemli zaman semantiği** de `FR-090`,
`FR-094`, `UC-017`, `RULE-016` ve `AC/TS-054`ün zaman anlamı alt kapsamında
tamamlanmış olarak korunur. Altı zaman alanı UTC, dönem ataması ve işlem sırası
açısından bağımsız doğrulanır; aynı profil/seed kanonik eşdeğer çıktı üretir.

Skorlama zincirinin normalizasyon, migration, kritik davranış ve ölçüm
yeterliliği kararları alınmıştır; sıradaki dilimler aktif politika yokluğunda
fail-closed davranışı koruyarak runtime'a taşınmalıdır. Sentetik zincirde
sıradaki hazır dar artım `SYN-004B` olarak kayıtlar arası geç ve sırasız
ingestion olgularını deterministik üretip bağımsız doğrulamalıdır. Eksiklik,
drift, kayıt düzeyi kusur, skor ve olay karşılaştırması yalnız sürümlü sentetik
politika değerleriyle genişletilmelidir.

Sonraki dilimler sırasıyla ayrı kapsamda planlanmalıdır: sürümlü normalizasyon ve
model kanıtı; kural → boyut → dataset agregasyonu ve kritik davranış;
ölçüm yeterliliği ile kapsam/güven/güncellik; ayrı kritiklik/risk;
istisna/override; API/UI/trend; alarm ve remediation. Üretim
eşik/ağırlık/veto/güven değerleri, geçerlilik süreleri, kullanım kararları ve
banka rol matrisi karar gerektirdiği için ilgili dilimler `OPEN-023` ve
`OPEN-BNK-004/008/010/013/017` ile engellidir.

**İterasyon 34F — PostgreSQL ilişkisel kusur dataseti** tamamlandı. Sentetik
zincirde sıradaki hazır küçük artım, mevcut PostgreSQL datasetini metadata ve
profil adaptörüne bağlayıp satır sayısı, null, distinct ve temel dağılım
sonuçlarını ham örnek kalıcılaştırmadan karşılaştırmalıdır. Genel kural motoru
entegrasyonu ve ayrıntılı kusur alt türleri sonraki ayrı dilimlerdir.

Kesinleşen kararların uygulama backlogunda sürümlü `SourceUsagePolicy` kayıt,
kota çözümleme, çalışma penceresi ve dinamik timeout/retry dilimleri 31A–31C ile
tamamlandı. `DatasetPartialScorePolicy` karar çekirdeği 32A, skor/agregasyon,
trend ve rapor önizleme entegrasyonu 32B, maker-checker onay/ret ve atomik audit
akışı 32C, maker'a ait auditli geri çekme 32D ile tamamlandı. Kalan davranışlar;
CPU/IO ve hız sınırı gözlemi,
güvenilir kısmi çalışma olgusu üretimi,
kurumsal IdP/SSO-MFA adaptörü, katalog/DLP sınıflandırma adaptörü,
`DatasetPartialScorePolicy`, kayıt sınıfı saklama matrisi, bileşen bazlı kurtarma
hedefleri ve katmanlı rapor/ServiceNow outbound kalıcılığı olarak ayrı küçük
dikeylere bölünmelidir.

İterasyon 31D hız sınırı için sayaç birimi, pencere türü, tüketim anı ve kalıcı
sayaç davranışı tanımlanmadığından Definition of Ready'i karşılamamaktadır.
Kısmi skor politika zincirindeki olası **İterasyon 32E — Politika talebi süre
aşımı** zaman kaynağı, değerlendirme anı ve süre politikası kesinleşmediği için
Definition of Ready'i karşılamamaktadır. Güvenilir olgu üretimi de
kapsama/eksik kayıt formülleriyle ayrıca engellidir; bu iki konu kesinleşmeden
uygulama yapılmamalıdır.
İterasyon 21B yerel/test dashboard özet API'sini, 20E BFF cookie/CSRF HTTP
sınırını ve 21C operasyonel gösterge DTO'sunu tamamladı. Sıradaki hazır dashboard
artımı **İterasyon 30D — dashboard referans içerik tamamlaması**dır; üretim
bağlantısı ayrıca gerçek IdP session assertion ve PostgreSQL skor repository'sini
bekler. Olumlu yeterlilik, kapsam, kullanım kararı, kritik kontrol sayıları ve
alarm alanları ilgili runtime sözleşmeleri tamamlanmadan üretilmemelidir.

İterasyon 27B `OPEN-BNK-011/012`, gerçek fiziksel retention adaptörleri
`OPEN-BNK-008`, hassas dışa aktarma `OPEN-BNK-014` ve gerçek SIEM/SOC
`OPEN-BNK-010` kararlarını beklemektedir. 21B'nin üretim devamı için
`OPEN-BNK-020` kararı banka onaylı ve 20D/20E teknik alt kapsamları uygulanmıştır;
kalan iş gerçek IdP, HA store, KMS/HSM ve fiziksel saklama kanıtıdır.

Kimlik zincirindeki **İterasyon 20E — BFF oturum ve CSRF HTTP sınırı**
tamamlanmıştır. Gerçek OIDC/SAML callback ve state/nonce doğrulaması, yüksek
erişilebilir session store, at-rest şifreleme/KMS-HSM ve fiziksel `P90D`
saklama/imha kanıtı ayrı üretim altyapısı artımlarıdır.

## Başlangıç İçin Okunacak Notlar

- [Bankacılık Geçiş Durumu](Bankacilik-Gecis-Durumu.md)
- [İterasyon 19](../09-Iterasyonlar/Iterasyon-19-Maker-Checker.md)
- [Bankacılık Kontrol Gereksinimleri](../01-SRS/17-Bankacilik-Uyum/17.02-Bankacilik-Kontrol-Gereksinimleri.md)
- [Maker-Checker Mimarisi](../02-Mimari/Guvenlik/Maker-Checker.md)
- [İterasyon 20](../09-Iterasyonlar/Iterasyon-20-LDAP-RBAC-Entegrasyonu.md)
- [Kimlik ve Yetki Ajanı](../03-Backend/01-Kimlik-ve-Yetki/AGENTS.md)

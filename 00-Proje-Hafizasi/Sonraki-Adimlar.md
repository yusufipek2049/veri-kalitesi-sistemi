---
type: project-memory
status: planned
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-21
tags:
  - proje
  - sonraki-adim
  - mvp
  - banka
---

# Sonraki Adımlar

## Geçiş Önceliği

Mevcut 16 iterasyonun, Iterasyon 17A–17E audit, Iterasyon 18A–18C veri koruma, Iterasyon 19A–19H maker-checker, Iterasyon 20A–20D LDAP/oturum güvenliği ve Iterasyon 25A–25D saklama/legal hold/imha/arşiv yetkilendirme dikeylerinin çekirdeği korunur. Banka kararları tamamlanmadan yeni HTTP yüzeyi açılmaz.

Bakım İterasyonu 29C.1 ile tam mypy baseline'ı sıfır hataya indirilmiştir;
sonraki değişiklikler bu baseline'ı korumalıdır.

1. İterasyon 19G — Bağlantı yapılandırması revizyonu ve bekleyen aktivasyon onayını geçersizleştirme; `TechnicallyVerified`.
2. İterasyon 19H — Kontrollü kaynak pasifleştirme ve yeni iş kabulünü engelleme; `TechnicallyVerified`.
3. İterasyon 21A — Yetki güven sınırına bağlı dashboard trend domain sorgusu; `TechnicallyVerified`.
4. İterasyon 21B — HTTP okuma yüzeyi; `OPEN-BNK-020` `ApprovedByBank` olarak
   kapanmıştır. 20D süre, tek aktif oturum, yeni giriş iptali ve terminal
   credential silme alt kapsamını uygular. BFF, `__Host-session`, CSRF ve diğer
   merkezi iptal tetiklerinin üretim HTTP/session adaptöründe uygulanması ile
   geçiş kapısındaki diğer bağımlılıklar tamamlandığında hazırdır.
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
| 20 | LDAP/RBAC adaptörü | `FR-001`–`FR-006`, `UC-001`, `BFR-IAM-001`–`BFR-IAM-006` | LDAP grubu güvenilir role/scope'a dönüşür; giriş ve oturum başarısızlığı fail-closed | 20A adaptör/eşleme, 20B giriş sınırı, 20C temel session ve 20D onaylı süre/tek oturum runtime alt kapsamı `TechnicallyVerified`; HTTP/BFF ve üretim altyapısı açık |
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
| FE-DS-002 | Açık ve koyu tema tanımları | Should | FE-DS-001, koyu tema kapsam kararı | Planlı / engelli |
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

## Sentetik Veri Backlogu

Bu maddeler `ADR-016` hedef tasarımını küçük dikeylere böler.

| ID | Ürün artımı | Gereksinim | Çıkış kriteri | Durum |
| --- | --- | --- | --- | --- |
| SYN-001 | Sentetik dataset politika, senaryo ve run kayıt çekirdeği | FR-088, FR-093; AC/TS-049 | Fail-closed politika çözümleme, değişmez sürüm/seed/run kaydı ve veri-minimum audit | 34A `TechnicallyVerified` |
| SYN-002 | Deterministik Golden ilişkisel üretici | FR-089, FR-090; AC/TS-048/049 | Şema, anahtar, referans, durum ve temel dağılım ilişkileri aynı seed ile tekrar üretilebilir | 34B üretici ve 34D kalıcı terminal referansları `TechnicallyVerified`; yalnız tamamen yapay teknik V1 profil |
| SYN-003 | Kusur enjeksiyonu, ground truth ve bağımsız karşılaştırıcı | FR-091, FR-092; AC/TS-050–052 | Geçerli uç/kusur ayrımı, boyut-kural bağı ve runtime'dan bağımsız beklenen sonuç | 34C Golden yapısal alt kapsam `TechnicallyVerified`; kayıt düzeyi kusur, skor ve olay karşılaştırması `OPEN-024` nedeniyle kısmen engelli |
| SYN-004 | Zaman, eksiklik, drift ve hacim profilleri | FR-090, FR-094; AC/TS-054/056 | Zaman alanı anlamları, eksiklik mekanizmaları, drift ve kaynak bütçeli hacim replay'i | 34E çok dönemli zaman semantiği `TechnicallyVerified`; eksiklik/drift/hacim açık, üretim performans kabulü `OPEN-014` ile ayrı |
| SYN-005 | Gizlilik kapısı, yaşam döngüsü ve izole olay testi | FR-095, FR-096; AC/TS-053/055/056 | Gizlilik sonucu, retention yaşam döngüsü ve üretim hedefi fail-closed negatifleri | KararAlındı; runtime politika/gizlilik değerlendiricisi uygulanmadı |

## Önerilen Sonraki İterasyon

Teknik inceleme `R-04` kapsamında yanlış `SOURCE` kritiklik ağırlıklandırması
İterasyon 33B ile giderildi. `R-04`ün replay/backfill ve tam ayrık sonuç modeli
alt kapsamlarında karar alınmıştır; runtime migration ve politika modelleri
henüz uygulanmamıştır. İncelemenin doğruluk ve veri
bütünlüğü sırasındaki sonraki küçük, hazır aday **R-06 — SQLite foreign key
enforcement ve orphan doğrulaması**dır; uygulamadan önce etkilenen repository
connection'ları ve silme semantikleri tek tek doğrulanmalıdır.

**İterasyon 30B — Sentetik dashboard çalışma iskeleti** `FR-054`, `FR-055`,
`FR-058`, `UC-010` ve `NFR-USA-001/003–006` alt kapsamında tamamlandı. Çalışan
frontend, sentetik KPI/trend/alarm görünümü, grafik/tablo alternatifi, Storybook
durumları ve beş viewport Playwright doğrulaması sunar; üretim API'si veya banka
verisi kullanmaz.

Kullanıcıya gösterilebilir frontend zincirindeki sıradaki hazır küçük artım
**İterasyon 30C — Sentetik veri alanı karşılaştırması ve kalite boyutu matrisi**
olmalıdır. ECharts horizontal bar ve heatmap aynı normalize edilmiş sentetik
view-model'den erişilebilir tablo karşılığıyla üretilmeli; yeni API alanı veya
üretim yetki davranışı tahmin edilmemelidir.

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
İterasyon 27B `OPEN-BNK-011/012`, gerçek fiziksel retention adaptörleri
`OPEN-BNK-008`, hassas dışa aktarma `OPEN-BNK-014` ve gerçek SIEM/SOC
`OPEN-BNK-010` kararlarını beklemektedir. 21B/frontend için `OPEN-BNK-020`
kararı banka onaylıdır; kalan iş kararın HTTP/session katmanında uygulanmasıdır.

Kimlik zincirindeki sıradaki küçük uygulama artımı **İterasyon 20E — BFF oturum
ve CSRF HTTP sınırı**dır. `__Host-session` cookie üretimi/döndürülmesi,
synchronizer token, Origin/Referer/Fetch Metadata ve CORS allowlist kontrolleri
ile state-changing `GET` reddi birlikte uygulanmalıdır. HTTP framework bağımlılığı
mevcut mimari karara göre doğrulanmadan bu artım başlatılmamalıdır. Yüksek
erişilebilir session store, at-rest şifreleme/KMS-HSM ve fiziksel `P90D`
saklama/imha kanıtı ayrı üretim altyapısı artımlarıdır.

## Başlangıç İçin Okunacak Notlar

- [Bankacılık Geçiş Durumu](Bankacilik-Gecis-Durumu.md)
- [İterasyon 19](../09-Iterasyonlar/Iterasyon-19-Maker-Checker.md)
- [Bankacılık Kontrol Gereksinimleri](../01-SRS/17-Bankacilik-Uyum/17.02-Bankacilik-Kontrol-Gereksinimleri.md)
- [Maker-Checker Mimarisi](../02-Mimari/Guvenlik/Maker-Checker.md)
- [İterasyon 20](../09-Iterasyonlar/Iterasyon-20-LDAP-RBAC-Entegrasyonu.md)
- [Kimlik ve Yetki Ajanı](../03-Backend/01-Kimlik-ve-Yetki/AGENTS.md)

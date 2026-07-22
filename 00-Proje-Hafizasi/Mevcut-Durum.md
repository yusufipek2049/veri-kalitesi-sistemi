---
type: project-memory
status: draft
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-22
tags:
  - proje
  - mevcut-durum
---

# Mevcut Durum

## Doküman Durumu

- SRS sürümü: **0.1 Taslak**
- Hazırlayan: **Yusuf İpek**
- Kurum adı: **Kurum** olarak anonim tutuluyor.
- SRS; iş analizi, mimari tasarım, geliştirme, test planlama ve güvenlik incelemesi için yeterli ayrıntıda.
- Performans, işletim, saklama ve güvenlik hedeflerinin bir bölümü onay bekleyen varsayım veya başlangıç hedefi.

## Kapsam Durumu

- 8 iş gereksinimi.
- 96 fonksiyonel gereksinim.
- 17 kullanım senaryosu.
- 17 iş kuralı.
- Temel ve hedef veri varlığı sözlüğü.
- 11 fonksiyonel olmayan gereksinim kategorisi.
- 56 sistem kabul kriteri.

## Uygulama Durumu

### 2026-07-16 — İterasyon 1: CSV veri kaynağı tanımı ve bağlantı testi

- Backend kod iskeleti `03-Backend/src/veri_kalitesi` altında başlatıldı.
- `FR-007`, `FR-008`, `FR-009`, `UC-002`, `UC-003`, `AC-004`, `AC-005` için ilk dar kapsamlı artım tamamlandı.
- CSV veri kaynağı tanımı, `secret://` referansı, SQLite metadata deposu, sınıflandırılmış bağlantı testi sonucu ve append-only audit kaydı eklendi.
- Teknik hata ile doğrulama hatası ayrı hata yollarıyla ele alındı; bağlantı testi hataları kaynak aktif etmeden `TEST_FAILED` durumuna düşüyor.
- Birim testleri `06-Testler/01-Birim/test_data_sources.py` içinde eklendi ve geçti.
- Çalıştırılan kontroller: `python3 -m pytest`, `python3 -m compileall 03-Backend/src 06-Testler/01-Birim`, `python3 -m ruff check .`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 2: PostgreSQL salt-okunur bağlantı testi sözleşmesi

- `FR-007`, `FR-008`, `FR-009`, `FR-012`, `UC-002`, `UC-003`, `AC-004`, `AC-005`, `AC-006`, `NFR-SEC-003`, `NFR-SEC-005`, `NFR-SEC-006` için PostgreSQL odaklı artım tamamlandı.
- Secret manager sınırı `SecretResolver` arayüzüyle ayrıldı; bağlantı testinde secret değeri yalnız bağlayıcı sınırına iletiliyor, metadata ve audit çıktılarında saklanmıyor.
- PostgreSQL bağlayıcı sözleşmesi, sürücü protokolü, TLS zorunluluğu, timeout ayarları ve read-only test sorgusu denetimi eklendi.
- DNS, timeout ve kimlik hataları sınıflandırılmış testlerle doğrulandı; DML/DDL içeren test sorguları sürücü çağrısı yapılmadan reddediliyor.
- Birim testleri 11 teste genişletildi ve geçti.
- Çalıştırılan kontroller: `python3 -m pytest`, `python3 -m compileall 03-Backend/src 06-Testler/01-Birim`, `python3 -m ruff check .`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 3: Veri kümesi ve alan metadata keşfi

- `FR-011`, `FR-015`, `FR-022`, `UC-004`, `AC-025`, `NFR-PERF-007`, `NFR-PERF-008` için metadata keşfi artımı tamamlandı.
- `Dataset`, `DataField`, metadata adayları, keşif seçenekleri ve şema değişikliği sonucu modelleri eklendi.
- SQLite metadata deposu `datasets`, `data_fields` ve `metadata_discovery_results` tablolarıyla genişletildi.
- CSV başlığından ve PostgreSQL sürücü sözleşmesinden metadata keşfi yapılabiliyor; kaynak başarılı bağlantı testi geçmeden keşif reddediliyor.
- İki tarama arasında eklenen, değişen ve kaldırılan dataset/field nesneleri ayrıştırılıyor; kırıcı alan değişiklikleri `requires_rule_review` olarak işaretleniyor.
- Birim testleri 15 teste genişletildi ve geçti.
- Çalıştırılan kontroller: `python3 -m pytest`, `python3 -m compileall 03-Backend/src 06-Testler/01-Birim`, `python3 -m ruff check .`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 4: Temel profilleme ve profil sonucu saklama

- `FR-016`, `FR-018`, `FR-020`, `UC-004`, `AC-007`, `AC-008`, `NFR-PERF-005`, `NFR-PERF-007`, `NFR-PRV-002`, `NFR-PRV-003` için temel profilleme artımı tamamlandı.
- `DataProfile`, profil yöntemi, durum, seçenek ve connector profil sözleşmesi eklendi.
- SQLite deposu `data_profiles` tablosuyla genişletildi; profil sonucu metrikleri, yöntem, örneklem oranı, durum ve süreyle saklanıyor.
- CSV için satır satır FULL/SAMPLE temel profil hesaplama eklendi: kayıt, null, tekil, uygun sayısal alanlarda min/max/ortalama ve seçili anahtar alanlarda duplicate metrikleri.
- PostgreSQL profil hesaplama gerçek sürücüden kaynakta toplulaştırılmış metrik alacak protokol arkasına alındı; birim testlerinde fake driver ile SAMPLE yöntemi ve oranı doğrulandı.
- Ham kayıtlar ve hassas örnek değerler profil sonucuna veya audit özetine yazılmıyor.
- Birim testleri 20 teste genişletildi ve geçti.
- Çalıştırılan kontroller: `python3 -m pytest`, `python3 -m compileall 03-Backend/src 06-Testler/01-Birim`, `python3 -m ruff check .`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 5: Temel kural şablonları ve kural test çalıştırması

- `FR-023`, `FR-025`, `FR-027`, `FR-029`, `FR-031`, `FR-032`, `FR-033`, `FR-034`, `UC-005`, `UC-006`, `AC-006`, `AC-009`, `RULE-002`, `RULE-003`, `RULE-005`, `RULE-007` için kural yönetimi artımı tamamlandı.
- Zorunlu alan, benzersizlik, aralık, regex, güncellik, referans bütünlüğü ve tablolar arası tutarlılık şablonları doğrulanan değişmez yürütme planları üretir.
- QualityRule, değişmez RuleVersion ve resmi skordan ayrı RuleTestResult geçmişi için SQLite deposu eklendi.
- Kural testleri varsayılan 10.000 kayıt sınırıyla çalışır; sınır azaltılabilir, artırılamaz ve başarılı kaynak bağlantısı ön koşulu aranır.
- Özel SQL salt-okunur değilse yürütücü çağrılmadan reddedilir; sınıflandırılmış teknik hata kalite başarısızlığına veya sıfır skora çevrilmez.
- Birim testleri 51 teste genişletildi ve geçti.
- Çalıştırılan kontroller: `python3 -m pytest`, `python3 -m compileall 03-Backend/src 06-Testler/01-Birim`, `python3 -m ruff check .`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 6: İdempotent manuel çalıştırma ve teknik retry

- `FR-030`, `FR-036`, `FR-040`, `FR-041`, `FR-043`, `FR-044`, `FR-045`, `UC-008`, `AC-010`, `AC-024`, `NFR-REL-001`, `NFR-REL-002`, `NFR-REL-005`, `RULE-003` ve `RULE-011` için manuel çalıştırma dilimi tamamlandı.
- Başarılı son sürüm testi bulunan taslak kural için kontrollü aktivasyon geçişi eklendi.
- SQLite tabanlı kalıcı `QUEUED` iş kaydı, çalıştırma/deneme/sonuç geçmişi ve idempotent manuel başlatma akışı oluşturuldu.
- Aynı idempotency anahtarı ve payload eşzamanlı tekrarlandığında tek execution dönüyor; farklı payload aynı anahtarla reddediliyor ve anahtarın yalnız SHA-256 özeti saklanıyor.
- Execution kapsamındaki secret/parola/token anahtarları kalıcı kayıt oluşmadan reddediliyor.
- Worker bağlantı, sorgu ve toplam timeoutlarını ayrı sözleşme alanlarıyla yürütücüye iletiyor; geçici teknik hata en fazla üç kez üstel gecikmeyle deneniyor, kalite başarısızlığı retry üretmiyor.
- Retry tükenen veya beklenmeyen teknik hata `TECHNICAL_ERROR` durumunda, sayısal sonuç oluşturmadan ve teknik olay adaptörünü çağırarak kapanıyor.
- Birim testleri 64 teste genişletildi ve geçti.
- Çalıştırılan kontroller: `python3 -m pytest`, `python3 -m compileall 03-Backend/src 06-Testler/01-Birim`, `python3 -m ruff check .`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 7: Periyodik zamanlama ve idempotent tetikleme

- `FR-037` gereksiniminin ONCE/DAILY/WEEKLY/MONTHLY alt kapsamı, `UC-007`, `RULE-003` ve `RULE-011` için zamanlama dilimi tamamlandı; genel cron ifadesi desteği açık kaldı.
- Schedule modeli ve SQLite deposu eklendi; IANA saat dilimiyle hesaplanan sonraki tetik zamanı UTC saklanıyor.
- Günlük, haftalık ve aylık planlar için sonraki beş çalışma zamanı; tek seferlik plan için gelecekteki tek çalışma zamanı önizleniyor.
- DST geçişinde var olmayan yerel saatler atlanıyor; aylık seçilen günün bulunmadığı aylar sonraki geçerli aya ilerliyor.
- Zamanı gelen plan mevcut execution servisine `SCHEDULED` türünde ve plan/zaman tabanlı idempotency anahtarıyla tek iş ekliyor.
- Plan oluşturma audit kaydı üretiyor; kaynak veya kural sonradan geçersizleşirse iş oluşturulmadan plan pasifleştiriliyor ve sınıflandırılmış teknik olay adaptörü çağrılıyor.
- Birim testleri 77 teste genişletildi ve geçti.
- Çalıştırılan kontroller: `python3 -m pytest`, `python3 -m compileall 03-Backend/src 06-Testler/01-Birim`, `python3 -m ruff check .`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 8: İş sınıfı ve kaynak bazlı paralellik kotası

- `FR-039`, `UC-008`, `NFR-PERF-006`, `NFR-PERF-008` ve `RULE-012` için kota farkındalıklı kalıcı queue claim dilimi tamamlandı.
- Execution kayıtlarına sistem tarafından belirlenen HEAVY/LIGHT sınıfı ve bağlı kaynak kimlikleri eklendi; sınıflandırıcı kaynak yürütücüsünden ayrı bir arayüz arkasında tutuldu.
- Yerel prototip varsayılanları en fazla iki ağır ve dört hafif çalışan iş olarak uygulandı; sınırı aşan işler QUEUED durumunda kalıyor.
- Kaynak başına toplam kota yapılandırılabilir hale getirildi; aynı kaynak için varsayılan ağır iş kotası bir olarak uygulandı.
- Kuyruk başındaki kaynak kotası dolu iş, kotası uygun başka kaynak işinin claim edilmesini engellemiyor.
- Önceki SQLite execution şemaları yeni `source_ids` ve `workload_class` sütunlarıyla açılışta geriye uyumlu genişletiliyor.
- Birim testleri 84 teste genişletildi ve geçti.
- Çalıştırılan kontroller: `python3 -m pytest`, `python3 -m compileall 03-Backend/src 06-Testler/01-Birim`, `python3 -m ruff check .`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 9: İptal ve kısmi timeout sonuç yönetimi

- `FR-040`, `FR-042`, `FR-043`, `FR-044`, `AC-012`, `RULE-003`, `RULE-004` ve `NFR-REL-002` için iptal ve timeout geçmişi dilimi tamamlandı.
- QUEUED iş iptal edildiğinde doğrudan `CANCELLED` kapanıyor; RUNNING iş için iptal zamanı, isteyen aktör ve gerekçe saklanarak `CANCEL_REQUESTED` durumuna geçiliyor ve yürütücü iptal adaptörü çağrılıyor.
- Tekrarlanan iptal isteği idempotent davranıyor; terminal başarı veya teknik hata iptal ile ezilemiyor, iptal isteği de sonraki worker sonucu tarafından ezilmiyor.
- Timeout tamamlanmış bölüm sonuçları içeriyorsa execution `PARTIAL`, sonuç yoksa `TIMEOUT` kapanıyor; kısmi sonuçların bölüm kimlikleri saklanıyor ve resmi skorlama uygunluğu kapalı tutuluyor.
- Timeout teknik olay olarak bildirilirken sayısal kalite başarısızlığına veya sıfır skora dönüştürülmüyor; timeout denemesi tekrar edilmiyor.
- Önceki SQLite execution ve sonuç şemaları iptal metadata alanları ile kısmi sonuç alanlarını ekleyecek şekilde geriye uyumlu genişletiliyor.
- Birim testleri 90 teste genişletildi ve geçti.
- Çalıştırılan kontroller: `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m compileall -q 03-Backend/src 06-Testler/01-Birim`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 10: Temel kural skoru ve hesaplanamayan durumlar

- `FR-046`, `FR-047`, `FR-048`, `UC-009`, `AC-009`, `AC-010`, `AC-011`, `AC-012`, `RULE-003` ve `RULE-004` için temel kural skoru dilimi tamamlandı.
- Başarılı execution sonuçlarında sayaç eşitliği doğrulanıyor; başarılı, hatalı ve değerlendirilemeyen oranlar ile kural skoru iki ondalıklı deterministik `Decimal` hesabıyla üretiliyor.
- `100/125` sonucu `80.00` olarak hesaplanıyor; formül sürümü, sayaçlar, oranlar ve resmi agregasyona dahil edilme bilgisi hesaplama detayında saklanıyor.
- Sıfır kayıt `NO_DATA`, teknik hata/timeout `NOT_CALCULATED_TECHNICAL_ERROR`, politika dışı kısmi sonuç `PARTIAL` oluyor ve bu durumlarda sayısal skor saklanmıyor.
- SQLite `quality_scores` geçmişi execution, RuleResult ve RuleVersion bağlarını koruyor; aynı execution ve kural sürümü için tekrarlanan hesaplama yeni skor üretmiyor.
- Tutarsız veya negatif sayaçlar skor kaydı oluşmadan doğrulama hatasıyla reddediliyor.
- Birim testleri 98 teste genişletildi ve geçti.
- Çalıştırılan kontroller: `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m compileall -q 03-Backend/src 06-Testler/01-Birim`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 11: Ağırlıklı veri kümesi skoru ve seviye sınıflandırması

- `FR-049`, `FR-051`, `UC-009`, `AC-013`, `AC-014`, `RULE-004` ve `RULE-005` için ağırlıklı veri kümesi skoru dilimi tamamlandı.
- Yalnız `CALCULATED` durumundaki kural skorları RuleVersion ağırlıklarıyla `Σ(skor×ağırlık)/Σ(ağırlık)` formülüne katılıyor; `80×2` ve `100×1` sonucu `86.67` üretiyor.
- Dahil edilen bileşenler skor, kural sürümü ve ağırlıklarıyla; dışlanan bileşenler durumlarıyla hesaplama detayında saklanıyor.
- `NO_DATA`, teknik hata ve `PARTIAL` alt skorlar ağırlık paydasına katılmıyor; tüm alt skorlar hesaplanamazsa sayısal dataset skoru oluşmuyor.
- Sıfır veya negatif kural ağırlığı dataset skorunu `CONFIG_ERROR` durumuna getiriyor ve sıfır skor üretmiyor.
- Sürümlü eşik seti varsayılan olarak 0–49.99 Kritik, 50–74.99 Riskli, 75–89.99 Kabul Edilebilir ve 90–100 İyi aralıklarını boşluk/çakışma olmadan uyguluyor; `80.00` Kabul Edilebilir olarak sınıflandırılıyor.
- QualityScore deposu dataset kapsamı, seviye ve nullable RuleVersion bağı için geriye uyumlu genişletildi; eski kural skorları migration testinde korundu.
- Birim testleri 105 teste genişletildi ve geçti.
- Çalıştırılan kontroller: `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m compileall -q 03-Backend/src 06-Testler/01-Birim`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 12: Sürümlü skor konfigürasyonu ve boyut skoru

- `FR-050` boyut alt kapsamı, `FR-051` yönetim alt kapsamı, `UC-009`, `RULE-004`, `RULE-005`, `RULE-007` ve `NFR-MNT-006` için artım tamamlandı.
- Eşik seti ve yedi kalite boyutu ağırlığını içeren değişmez `ScoringConfiguration` sürümleri SQLite geçmişinde saklanıyor; depo tek aktif sürümü garanti ediyor.
- Varsayılan `DEFAULT_SCORING_V1` sürümü otomatik oluşturuluyor; yeni sürüm aktivasyonu önceki kaydı silmeden pasifleştiriyor ve audit adaptörüne eski/yeni sürüm ile ağırlıkları yazıyor.
- Eksik boyut ağırlığı, pozitif olmayan/sonlu olmayan ağırlık, geçersiz eşik veya tekrar sürüm kontrollü doğrulama hatası üretiyor; başarısız aktivasyon mevcut aktif sürümü koruyor.
- Skor servisi aktif konfigürasyonu her hesaplama başlangıcında çözüyor; geçmiş skorlar eski konfigürasyon sürümünü korurken yalnız yeni execution skorları yeni sürümü kullanıyor.
- Boyut skoru, aynı execution içindeki kural skorlarını `QualityRule.primary_dimension` ile filtreleyip RuleVersion ağırlıklarıyla toplulaştırıyor; dahil/dışlanan bileşenler, formül ve konfigürasyon sürümü saklanıyor.
- `NO_DATA` alt skor boyut paydasına katılmıyor; seçilen boyutta kural bulunmazsa skor kaydı oluşturmadan doğrulama hatası dönüyor.
- Birim testleri 111 teste genişletildi ve geçti.
- Çalıştırılan kontroller: `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m compileall -q 03-Backend/src 06-Testler/01-Birim`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 13: Açıklanabilir veri kaynağı skoru

- `FR-050` kaynak alt kapsamı, `UC-009`, `RULE-004`, `RULE-005` ve `RULE-007` için SOURCE agregasyon artımı tamamlandı.
- Skor servisi execution içindeki kuralların dataset metadata kayıtlarını salt okunur katalog sözleşmesiyle çözüyor ve yalnız istenen `data_source_id` kapsamındaki dataset skorlarını topluyor.
- Dataset kritiklik ağırlıkları sürümlü `ScoringConfiguration` içine eklendi; LOW/MEDIUM/HIGH/CRITICAL varsayılanları belgelenmemiş öncelik varsaymamak için nötr `1.0` olarak başlıyor.
- Kaynak skoru yalnız `CALCULATED` dataset skorlarını kritiklik ağırlıklarıyla topluyor; dataset kimliği, kritiklik, skor, ağırlık ve dahil/dışlanan bileşenler hesaplama detayında saklanıyor.
- `NO_DATA` dataset paydaya katılmıyor; tüm datasetler teknik hata durumundaysa SOURCE skoru `NOT_CALCULATED_TECHNICAL_ERROR` ve NULL değerle saklanıyor.
- Yanlış kaynak kapsamı veya eksik metadata kataloğu SOURCE kaydı oluşturmadan doğrulama hatası üretiyor; tekrar hesaplama mevcut SOURCE skorunu döndürüyor.
- Önceki skor konfigürasyonu şemaları kritiklik ağırlıkları sütunuyla geriye uyumlu genişletiliyor ve aktif sürüm korunuyor.
- Birim testleri 117 teste genişletildi ve geçti.
- Çalıştırılan kontroller: `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m compileall -q 03-Backend/src 06-Testler/01-Birim`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 14: Açıklanabilir kurum skoru

- `BR-005`, `BR-006`, `FR-050`, `UC-009`, `RULE-004` ve `RULE-005` için ENTERPRISE agregasyon artımı tamamlandı.
- Skor servisi aynı execution içindeki kuralların metadata ilişkilerinden benzersiz veri kaynaklarını buluyor, eksik SOURCE skorlarını üretiyor ve geçerli kaynak skorlarını kurum seviyesinde toplulaştırıyor.
- SRS kaynaklar arası katsayı tanımlamadığı için kaynak skorları geçici `EQUAL_SOURCE_WEIGHT` politikasıyla eşit ağırlıkta hesaplanıyor; politika, formül ve aktif konfigürasyon sürümü hesaplama detayında saklanıyor.
- Kurum skoru dahil edilen kaynakların kimlik, skor ve ağırlıklarını; `NO_DATA`, teknik hata veya kısmi durumdaki kaynakların kimlik ve durumlarını dışlanan bileşenler listesinde açıklıyor.
- Hesaplanamayan kaynaklar sıfır sayılmıyor; tüm kaynaklar teknik hata durumundaysa ENTERPRISE skoru `NOT_CALCULATED_TECHNICAL_ERROR` ve NULL değerle saklanıyor.
- ENTERPRISE kapsamının `scope_id` alanı NULL olarak modelleniyor; SQLite şeması eski skorları koruyarak nullable kapsama taşınıyor ve ifadesel benzersiz indeks tekrar hesaplamada tek kurum skoru kalmasını sağlıyor.
- Birim testleri 121 teste genişletildi ve geçti.
- Çalıştırılan kontroller: `pytest -q`, `ruff check 03-Backend/src 06-Testler`, değişen dosyalar için `ruff format --check` ve `python3 -m compileall -q 03-Backend/src 06-Testler`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 15: Yetki filtreli dashboard skor ağacı

- `BR-001`, `FR-054` ve `FR-057` ENTERPRISE/SOURCE alt kapsamı, `UC-010` ve `NFR-PERF-002` için salt okunur dashboard sorgu artımı tamamlandı.
- Yazma modelinden ayrı `dashboard` paketi; erişim kapsamı, skor düğümü ve kurum-kaynak skor ağacı okuma modelleriyle eklendi.
- Skor ağacı aynı execution içindeki ENTERPRISE ve SOURCE skorlarını okuyor; yalnız izin verilen kaynakları döndürüyor ve kurum skorunu ayrı `can_view_enterprise` yetkisi olmadan göstermiyor.
- Doğrudan kaynak drill-down isteği yetki kapsamı dışında ise repository sorgulanmadan kontrollü yetki hatası ve correlation ID üretiliyor.
- `NO_DATA` ve teknik hata durumlarındaki NULL skorlar sıfıra çevrilmiyor; boş execution yanıltıcı KPI üretmeden boş görünüm dönüyor.
- SQLite/OSError depo hataları veri kalitesi sonucuna çevrilmeden correlation ID taşıyan teknik dashboard sorgu hatası olarak ayrılıyor.
- 500 SOURCE skoru, bellek içi SQLite ve örneklemesiz 20 tekrar ile çalışan yerel p95 koruma testi 1 saniye hedefini karşıladı; bu test üretim kapasite kanıtı değildir.
- Birim testleri 129 teste genişletildi ve geçti.
- Çalıştırılan kontroller: `pytest -q`, `ruff check 03-Backend/src 06-Testler`, değişen dosyalar için `ruff format --check` ve `python3 -m compileall -q 03-Backend/src 06-Testler`.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 16: Güvenilir aktör ve authorization context

- `FR-002`, `FR-004`, `RULE-001`, `RULE-009`, `BFR-IAM-001`, `BFR-IAM-002`, `BFR-IAM-004` ve `BRULE-001` için dashboard dikey güven sınırı tamamlandı.
- Değişmez `ActorContext`, USER/SERVICE/BREAK_GLASS aktör türleri, güvenilir issuer, sürümlü dashboard authorization policy ve deny-by-default karar servisi eklendi.
- Dashboard sorguları artık doğrudan `DashboardAccessScope` kabul etmiyor; scope yalnız `AuthorizationService` kararından türetiliyor ve ENTERPRISE izni ayrı kalıyor.
- Eksik, doğrudan oluşturulmuş sahte, süresi dolmuş, henüz geçerli olmayan veya policy sürümü uyuşmayan context repository çağrısından önce reddediliyor.
- Varsayılan dashboard policy servis hesaplarını reddediyor; `privileged` bayrağı explicit ENTERPRISE izni üretmiyor.
- Eski scope tabanlı yol public paket ihracından çıkarıldı ve yalnız internal/deprecated geçiş adaptöründe korundu.
- Authorization karar özeti correlation ID, policy sürümü, karar nedeni ve kapsam sayısını taşıyor; session, roller ve source/dataset kimlikleri redakte ediliyor. Bu yerel sözleşme merkezi audit bütünlüğünün yerine geçmiyor.
- Authorization audit sink hatasında dashboard okuması güvenli varsayılan olarak repository'ye ulaşmadan reddediliyor; genel audit hata politikası banka kararı beklemeye devam ediyor.
- Birim testleri 139 teste genişletildi ve geçti; erişim kontrolü kanıtı `08-Uyum-Kanitlari/Erisim/Iterasyon-16-Guvenilir-Aktor-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Çalıştırılan kontroller: `pytest -q`, `ruff check 03-Backend/src 06-Testler`, değişen dosyalar için `ruff format --check`, `python3 -m compileall -q 03-Backend/src 06-Testler` ve hassas anahtar sözcük taraması.
- Banka bilgi güvenliği, iç kontrol ve hukuk/uyum onayları `ComplianceReviewRequired`; teknik doğrulama mevzuat uyumu anlamına gelmiyor.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 17A: Merkezi audit zarfı ve authorization dikeyi

- `BR-007`, `FR-077`, `FR-079`, `UC-016` bütünlük alt kapsamı, `BFR-AUD-001`–`BFR-AUD-004` ve `BRULE-005` için ilk merkezi audit dikeyi tamamlandı.
- Sürümlü ortak olay zarfı; aktör, correlation ID, zaman, sonuç, neden, redaksiyon sürümü ve değişiklik özetlerini tek sözleşmede topluyor.
- Allowlist tabanlı redaksiyon hassas anahtarları, yapısal değerleri ve secret benzeri metinleri saklamıyor; session kimliği yalnız özet olarak tutuluyor.
- SQLite prototip deposunda önceki olay hash'ine bağlı append-only SHA-256 zinciri ve değiştirilmiş kaydı bulan bütünlük doğrulaması eklendi.
- Audit yazma davranışı `FAIL_CLOSED` ve yapılandırılmış kalıcı tampon gerektiren `DURABLE_BUFFER` olarak açıkça modellendi; authorization dikeyi fail-closed kullanıyor.
- Dashboard authorization kararları yerel özel audit modelinden merkezi audit sınırına taşındı; veri kaynağı ve kural servislerinin eski yolları 17B kapsamında kaldı.
- Birim testleri 147 teste genişletildi ve geçti; kanıt `08-Uyum-Kanitlari/Audit/Iterasyon-17A-Merkezi-Audit-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Çalıştırılan kontroller: değişen dosyalarda `ruff format --check`, tüm backend/testlerde `ruff check`, `compileall`, `pytest -q` ve hassas değer deseni taraması.
- Tam depo format kontrolü, değişmeyen 12 eski dosyanın mevcut biçim farkları nedeniyle geçmedi; kapsam dışı dosyalara biçim değişikliği uygulanmadı.
- WORM/imza/SIEM, üretim kalıcı tamponu ve banka işlem bazlı hata politikası onayı açık kalır; teknik doğrulama mevzuat uyumu anlamına gelmez.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 17B: Veri kaynağı ve kural merkezi audit geçişi

- `FR-007`, `FR-008`, `FR-023`, `FR-029`, `FR-030`, `FR-031`, `FR-077`, `FR-079`, `BFR-AUD-001`–`BFR-AUD-004` ve `BRULE-005` için iki modül geçişi tamamlandı.
- Veri kaynağı ve kural servisleri zorunlu merkezi `AuditSink` kullanıyor; audit olmadan sessiz çalışma ve `data_sources.models.AuditRecord` kaldırıldı.
- Kaynak oluşturma, bağlantı testi, metadata keşfi, profil ile kural oluşturma, sürüm, test ve aktivasyon olayları `AUDIT_REDACTION_V2` allowlist'ine bağlandı.
- Kaynak adı/sahibi, bağlantı `source_info`, secret referansı, kural adı/tanımı ve SQL audit özetine alınmıyor; correlation ID korunuyor veya operasyon için üretiliyor.
- Eski `audit_records` tablosu silinmedi fakat yeni yazım almıyor. Zamanlama ve skorlama bağımlılığı merkezi pakette `LegacyAuditRecord` adıyla görünür hale getirildi.
- Birim testleri 150 teste genişletildi ve geçti; kanıt `08-Uyum-Kanitlari/Audit/Iterasyon-17B-Modul-Audit-Gecis-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Değişen dosyalarda format, tüm backend/testlerde lint, derleme, test ve hassas desen taraması geçti. Tam depo format kontrolünde değişmeyen 5 eski dosyanın biçim farkı sürüyor.
- Mevcut iş repository transaction'ı auditten önce commit edildiği için audit hatası çağırana dönse de önceki iş commitini geri alamıyor; transactional outbox/ortak transaction 17C kapsamındadır.
- Banka politika ve ürün onayları `ComplianceReviewRequired`; teknik doğrulama mevzuat uyumu anlamına gelmez.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 17C1: Oluşturma işlemleri için transactional audit outbox

- `FR-007`, `FR-023`, `FR-077`, `FR-079`, `BFR-AUD-001`–`BFR-AUD-004` ve `BRULE-005` için kaynak/kural oluşturma atomikliği tamamlandı.
- İş kaydı ve redakte `PreparedAuditEvent`, domain repository'sinin aynı SQLite transaction'ında kalıcı outbox'a yazılıyor.
- Outbox yazımı başarısızsa iş insert'i rollback oluyor; merkezi audit deposu kesintisinde iş başarılı kalırken olay `PENDING` durumda kaybolmadan korunuyor.
- Pending olay merkezi hash zincirine sonradan yayınlanabiliyor. Aynı olay/aynı içerik idempotent; aynı olay kimliği/farklı içerik reddediliyor.
- Birim testleri 152 teste genişletildi ve geçti; kanıt `08-Uyum-Kanitlari/Audit/Iterasyon-17C1-Transactional-Outbox-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Değişen dosyalarda format, tüm backend/testlerde lint, derleme, test ve hassas desen taraması geçti. Tam depo format kontrolünde değişmeyen 5 eski dosyanın biçim farkı sürüyor.
- Kapsam yalnız kaynak/kural oluşturmadır; diğer yazımlar, üretim publisher worker'ı ve legacy geçişler açık kalır.
- Banka politika ve ürün onayları `ComplianceReviewRequired`; teknik doğrulama mevzuat uyumu anlamına gelmez.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 17C2: Kalan kaynak ve kural yazımları için transactional audit outbox

- `FR-008`, `FR-011`, `FR-016`, `FR-018`, `FR-020`, `FR-029`, `FR-030`, `FR-031`, `FR-077`, `FR-079`, `BFR-AUD-001`–`BFR-AUD-004` ve `BRULE-005` için kalan veri kaynağı/kural yazım atomikliği tamamlandı.
- Bağlantı testi, metadata keşfi başarı/başarısızlığı, profil sonucu, kural sürümü, kural testi ve aktivasyon; domain kaydı ile redakte outbox olayını aynı SQLite transaction'ında yazıyor.
- Hedeflenen her yazım yolu için outbox-stage hatasında domain değişikliğinin rollback olduğu test edildi; merkezi audit kesintisinde bağlantı testi ve kural sürümü kalıcı kalırken olay `PENDING` durumda korunuyor.
- Veri kaynağı ve kural servislerinde kalıcı yazımdan sonra doğrudan merkezi audit çağıran eski yol kalmadı; yayın commit sonrasında idempotent outbox publisher üzerinden yapılıyor.
- Birim testleri 161 teste genişletildi ve geçti; kanıt `08-Uyum-Kanitlari/Audit/Iterasyon-17C2-Kalan-Yazimlar-Outbox-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Değişen dosyalarda format, tüm backend/testlerde lint, derleme, test ve hassas desen taraması geçti. Tam depo format kontrolünde değişmeyen 5 eski dosyanın biçim farkı sürüyor.
- Zamanlama/skorlama `LegacyAuditRecord` yolları, tarihsel `audit_records` aktarımı ve üretim publisher worker'ı kapsam dışı bırakıldı.
- Banka politika ve ürün onayları `ComplianceReviewRequired`; teknik doğrulama mevzuat uyumu anlamına gelmez.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 17D1: Zamanlama oluşturma merkezi audit geçişi

- `FR-037`, `FR-077`, `FR-079`, `UC-007`, `BFR-AUD-001`–`BFR-AUD-004` ve `BRULE-005` için schedule oluşturma audit dikeyi tamamlandı.
- Opsiyonel `ScheduleAuditSink` ve `LegacyAuditRecord` yolu kaldırıldı; `SchedulingService` artık zorunlu transactional audit bileşeni ve correlation ID kullanıyor.
- Schedule inserti ile redakte `SCHEDULE_CREATED` olayı aynı SQLite transaction'ındaki outbox'a yazılıyor; outbox-stage hatasında schedule rollback oluyor.
- Merkezi audit kesintisinde schedule başarılı kalırken olay `PENDING` korunuyor; schedule adı ve kural sürüm kimlikleri audit özetine alınmıyor.
- `FR-037` sonraki beş çalışma zamanı önizlemesi ve mevcut idempotent tetikleme davranışı korundu.
- Birim testleri 164 teste genişletildi ve geçti; kanıt `08-Uyum-Kanitlari/Audit/Iterasyon-17D1-Zamanlama-Audit-Gecis-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Değişen dosyalarda format, tüm backend/testlerde lint, derleme, test ve hassas desen taraması geçti. Tam depo format kontrolünde değişmeyen 4 eski dosyanın biçim farkı sürüyor.
- Skor konfigürasyonu aktivasyonundaki legacy audit yolu, tarihsel `audit_records` aktarımı ve üretim publisher worker'ı kapsam dışı bırakıldı.
- Banka politika ve ürün onayları `ComplianceReviewRequired`; teknik doğrulama mevzuat uyumu anlamına gelmez.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 17D2: Skor konfigürasyonu aktivasyonu merkezi audit geçişi

- `FR-051`, `FR-052`, `FR-077`, `FR-079`, `UC-009`, `RULE-005`, `RULE-007`, `BFR-AUD-001`–`BFR-AUD-004` ve `BRULE-005` için skor konfigürasyonu aktivasyon audit dikeyi tamamlandı.
- Opsiyonel scoring audit sink ve son aktif `LegacyAuditRecord/append_audit` yolu kaldırıldı; geçici legacy model public audit API'sinden çıkarıldı.
- Yeni konfigürasyon inserti, önceki sürümün pasifleştirilmesi ve redakte `SCORING_CONFIGURATION_ACTIVATED` olayı aynı SQLite transaction'ındaki outbox'a yazılıyor.
- Outbox-stage hatasında yeni sürüm ve pasifleştirme birlikte rollback oluyor; merkezi audit kesintisinde yeni aktif sürümle `PENDING` olay korunuyor.
- Eski/yeni eşik ve boyut/kritiklik ağırlıkları sabit scalar alanlarla merkezi allowlist'e alındı; geçmiş skorlar ve önceki konfigürasyon sürümleri değişmeden korunuyor.
- Birim testleri 167 teste genişletildi ve geçti; kanıt `08-Uyum-Kanitlari/Audit/Iterasyon-17D2-Skorlama-Audit-Gecis-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Değişen dosyalarda format, tüm backend/testlerde lint, derleme, test ve hassas desen taraması geçti. Tam depo format kontrolünde değişmeyen 4 eski dosyanın biçim farkı sürüyor.
- Maker-checker, tarihsel `audit_records` aktarımı ve üretim publisher worker'ı kapsam dışı bırakıldı.
- Banka politika ve ürün onayları `ComplianceReviewRequired`; teknik doğrulama mevzuat uyumu anlamına gelmez.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 17E: Tarihsel audit kayıtlarının kontrollü aktarımı

- `FR-077`, `FR-079`, `UC-016`, `BFR-AUD-001`–`BFR-AUD-004` ve `BRULE-005` için tarihsel audit aktarım sözleşmesi tamamlandı.
- Depoda kalan tek legacy `audit_records` şeması envanterlendi; yeni migrator kaynağa yalnız `PRAGMA` ve `SELECT` ile erişiyor, hiçbir kaydı güncellemiyor veya silmiyor.
- Desteklenen satırlar güncel allowlist/redaksiyon politikasından geçirilerek deterministik olay kimliği ve correlation özetiyle merkezi hash zincirine idempotent ekleniyor.
- Bozuk JSON, desteklenmeyen eylem ve naive zaman damgası ham kayıt kimliğini açmadan veri kalitesi sorunu olarak raporlanıyor; merkezi repository hatası ayrı teknik hata olarak yükseltiliyor.
- Birim testleri 170 teste genişletildi ve geçti; audit/veri kaynağı hedef grubu 40 testle geçti. Kanıt `08-Uyum-Kanitlari/Audit/Iterasyon-17E-Tarihsel-Audit-Aktarim-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Değişen Python dosyalarında format, tüm backend/testlerde lint, derleme, test ve hassas desen taraması geçti. Tam depo format kontrolünde değişmeyen 4 eski dosyanın biçim farkı sürüyor.
- Gerçek üretim envanteri/aktarımı, yedek ve geri dönüş onayı, publisher worker'ı, WORM/SIEM ve `FR-078` kapsam dışıdır.
- İterasyon 17'nin kod ve sentetik test kapsamı teknik olarak tamamlandı; banka onayları `ComplianceReviewRequired` kalır.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 18A: Sürümlü sınıflandırma ve profil minimizasyonu

- `FR-016`, `FR-020`, `UC-004`, `RULE-010`, `NFR-PRV-002`, `NFR-PRV-003`, `AC-023`, `BFR-DATA-001`, `BFR-DATA-002` ve `BFR-DATA-003` profil alt kapsamı için veri koruma dikeyi tamamlandı.
- Yeni `data_protection` paketi sürümlü sınıf sözlüğü, sınıflandırma kararı ve profil maskeleme/minimizasyon protokollerini sağlıyor.
- Metadata keşfinde boş sınıf `UNCLASSIFIED` oluyor; sözlük dışı kod metadata yazılmadan kontrollü doğrulama hatası veriyor.
- `DataField` sınıf politika sürümünü saklıyor; eski NULL/serbest sınıflar fail-closed migrate ediliyor ve SQLite tetikleyicileri doğrudan sözlük dışı insert/update işlemini reddediyor.
- Profil payloadı kalıcılık öncesi allowlist'ten geçiriliyor; mevcut toplulaştırılmış metrikler korunurken ham örnek, top-value, desen örneği ve bilinmeyen alanlar profil/audit dışında kalıyor.
- Birim testleri 173 teste genişletildi ve geçti; veri kaynağı hedef grubu 31 testle geçti. Kanıt `08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-18A-Siniflandirma-ve-Profil-Minimizasyonu-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Değişen Python dosyalarında format, tüm backend/testlerde lint, derleme ve test kontrolleri geçti. Tam depo format kontrolünde değişmeyen 4 eski dosyanın biçim farkı sürüyor.
- Teknik sınıf kodlarının banka sözlüğü eşlemesi, `BFR-DATA-004` işleme envanteri, diğer kullanıcı/entegrasyon yüzeyleri ve özel inceleme akışı kapsam dışıdır.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 18B: Sürümlü kişisel veri işleme envanteri

- `BFR-DATA-004`, `NFR-PRV-005` sözleşme alt kapsamı, `RULE-007` ve `CTRL-KVKK-MIN-001` için sınıflandırılmış alana bağlı işleme envanteri dikeyi tamamlandı.
- İşleme amacı, hukuki sebep, veri sahibi, saklama politikası, erişim rolleri, alıcı grupları ve yurt dışı aktarım etkisi kurumca sağlanan referanslarla append-only sürümleniyor; varsayılan hukuk/saklama politikası üretilmiyor.
- Metadata yeniden keşfinde aynı dataset ve alan UUID'leri korunarak envanter geçmişinin kopması engellendi.
- Envanter sürümü ve `AUDIT_REDACTION_V3` redakte outbox olayı aynı transaction'da yazılıyor; teknik outbox hatasında envanter inserti rollback oluyor.
- Sınıflandırılmamış alan ve secret-benzeri referans doğrulama hatası olarak ayrılıyor; audit özeti hassas yönetişim referanslarını taşımıyor.
- Birim testleri 176 teste genişletildi ve geçti; veri kaynağı hedef grubu 34 testle geçti. Kanıt `08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-18B-Isleme-Envanteri-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Değişen Python dosyalarında format, tüm backend/testlerde lint, derleme ve test kontrolleri geçti.
- Her kişisel alan için envanter tamlık kontrolü, banka referans sözlükleri ve kurum onayları kapsam dışıdır.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 18C: Kişisel alan işleme envanteri tamlık kontrolü

- `BFR-DATA-004` ve `NFR-PRV-005` için kişisel ve özel nitelikli kişisel alanları güncel envanter sürümüyle eşleştiren salt okunur kapsam raporu tamamlandı.
- Rapor `COMPLETE`, `INCOMPLETE` ve `NO_REQUIRED_FIELDS` durumlarını; yalnız teknik kimlik, sınıf, sürüm ve `MISSING_CURRENT_INVENTORY` sorun kodunu taşır.
- Eksik envanter veri kalitesi/tamlık sonucu olarak kalır; SQLite okuma arızası ayrı `InventoryCoverageTechnicalError` üretir.
- `CUSTOMER_SECRET` ve `BANK_SECRET`, banka eşlemesi onaylanmadan kişisel veri kapsamına alınmadı; kurumsal referans değerleri raporda açılmadı.
- Üç yeni testle toplam 179 test geçti; veri kaynağı hedef grubu 37 testle geçti. Kanıt `08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-18C-Envanter-Tamlik-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Değişen Python dosyalarında format, tüm backend/testlerde lint, derleme ve test kontrolleri geçti.
- Banka sınıf eşlemesi, kurumsal referans doğrulaması ve kurum onayları kapsam dışıdır.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-16 — İterasyon 19A: Kritik kural aktivasyonu maker-checker

- `FR-035`, `RULE-001`, `RULE-007`, `BFR-SOD-001`, `BFR-SOD-002`, `BFR-SOD-003` kural alt kapsamı ve `BFR-SOD-004` onay/ret alt kapsamı tamamlandı.
- `CRITICAL` kural sürümü güvenilir maker `ActorContext` ile hazırlanır ve başarılı testten sonra yalnız aynı kayıtlı maker tarafından onaya sunulur; farklı, yetkili ve aynı dataset kapsamındaki checker onayı olmadan aktifleşmez.
- Onay isteği doğrudan `RuleVersion` kimliğine bağlıdır; yeni sürüm eski isteği geçersiz kılar. Ret kuralı taslakta tutar.
- Onay/ret kararı, gerekli aktivasyon ve redakte audit outbox olayı aynı SQLite transaction'ında saklanır; outbox-stage hatasında karar ve aktivasyon rollback olur.
- Sahte/eksik/süresi dolmuş context, yanlış rol/kapsam ve maker=checker fail-closed reddedilir. Audit gerekçe kodunu veya session kimliğinin açık değerini taşımaz.
- On bir yeni testle toplam 190 test geçti; kural hedef grubu 49 testle geçti. Kanıt `08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19A-Kural-Maker-Checker-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Değişen Python dosyalarında format, tüm backend/testlerde lint, derleme ve test kontrolleri geçti. Tam depo format kontrolünde değişmeyen 4 eski dosyanın biçim farkı sürüyor.
- Skor konfigürasyonu onayı, süre aşımı, geri çekme, banka rol eşlemesi ve acil override kapsam dışıdır.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-17 — İterasyon 19B: Skor konfigürasyonu maker-checker

- `FR-051`, `FR-052`, `RULE-001`, `RULE-005`, `RULE-007`, `BFR-SOD-001`–`BFR-SOD-004`, `BRULE-001`, `BRULE-002` ve `BRULE-005` skor konfigürasyonu alt kapsamı tamamlandı.
- Yeni skor konfigürasyonu güvenilir maker `ActorContext` ile değişmez ve pasif bir sürüm olarak oluşturulur; yalnız farklı, yetkili, kurum skoru kapsamına sahip güvenilir checker onayıyla aktifleşir.
- Onay belirli konfigürasyon kimliğine ve sürümlü onay politikasına bağlıdır. Eski taslak, ret veya maker'ın kendi kararı aktif konfigürasyonu değiştirmez.
- Talep ve karar kayıtları redakte audit outbox ile aynı SQLite transaction'ında saklanır; outbox-stage hatası taslağı veya karar/aktivasyonu rollback eder. Merkezi audit kesintisinde iki olay da kalıcı tamponda kalır.
- Eksik/süresi dolmuş context, yanlış rol, kurum kapsamı olmayan kullanıcı, rolü olmayan ayrıcalıklı kullanıcı ve servis hesabı fail-closed reddedilir. Gerekçe kodu ve açık session kimliği audit özetine alınmaz.
- Geçmiş skorlar kullandıkları konfigürasyon sürümünü korur; eski scoring SQLite şeması onay tablosuyla geriye uyumlu genişletilir.
- On iki yeni testle toplam 202 test geçti; skorlama hedef grubu 46 testle geçti. Kanıt `08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19B-Skorlama-Maker-Checker-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Değişen Python dosyalarında format, tüm backend/testlerde lint, derleme ve test kontrolleri geçti. Tam depo format kontrolünde değişmeyen 4 eski dosyanın biçim farkı sürüyor.
- Kural onay süre aşımı/geri çekme, banka rol eşlemesi, veri kaynağı aktivasyonu ve acil override kapsam dışıdır; kurum onayları `ComplianceReviewRequired` durumundadır.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-17 — İterasyon 19C: Kural onay isteğinin geri çekilmesi

- `FR-035`, `UC-005`, `RULE-001`, `RULE-007`, `BFR-SOD-004`, `BRULE-001` ve `BRULE-005` geri çekme alt kapsamı tamamlandı.
- Yalnız güncel güvenilir maker rolü ve aynı dataset kapsamına sahip, istekte kayıtlı RuleVersion hazırlayanı bekleyen onay isteğini geri çekebilir.
- Geri çekilen istek sürüme bağlı `WITHDRAWN` terminal durumuna geçer; checker atanmaz, kural `DRAFT` kalır ve daha yeni RuleVersion etkilenmez.
- Gerekçe kodu domain geçmişinde tutulur fakat audit özetine alınmaz; session kimliği yalnız digest olarak saklanır.
- Durum geçişi ve redakte audit outbox olayı aynı SQLite transaction'ında yazılır; outbox-stage hatasında istek `PENDING` kalır.
- Eksik/süresi dolmuş context, yanlış rol veya dataset kapsamı, başka maker, servis hesabı ve rolü olmayan ayrıcalıklı kullanıcı fail-closed reddedilir.
- On yeni testle toplam 212 test geçti; kural hedef grubu 59 testle geçti. Kanıt `08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19C-Kural-Onay-Geri-Cekme-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Değişen Python dosyalarında format, tüm backend/testlerde lint, derleme ve test kontrolleri geçti. Tam depo format kontrolünde değişmeyen 4 eski dosyanın biçim farkı sürüyor.
- Süre aşımı başlangıcı, süresi ve politika sahibi SRS'de tanımlı olmadığı için varsayılmadı; İterasyon 19D engelli backlog maddesi olarak açık kaldı.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-17 — İterasyon 20A: LDAP/RBAC adaptör sözleşmesi

- `FR-001`–`FR-003`, `UC-001`, `NFR-SEC-001`, `NFR-SEC-005`, `NFR-SEC-008`, `BFR-IAM-001`, `BFR-IAM-003`, `BFR-IAM-004`, `BFR-IAM-006`, `BRULE-001` ve `BRULE-005` için LDAP kimlik güven sınırı alt kapsamı tamamlandı.
- LDAP adaptör protokolü yalnız doğrulanmış, değişmez subject/grup iddiası döndürür; uygulama credential değerini saklamaz veya audit olayına taşımaz.
- Sürümlü ve dışarıdan enjekte edilen grup-rol-scope politikası eşleşen grant'leri birleştirerek mevcut `ActorContextIssuer` üzerinden güvenilir context üretir; eşlenmeyen gruplar yetki üretmez.
- Pasif kimlik, eşlemesiz grup ve kullanıcı akışındaki servis hesabı kontrollü ret; credential reddi ve LDAP teknik/öngörülmeyen hata ayrı sonuçlardır. Hiçbir hata yolunda context döndürülmez.
- Başarılı ve başarısız giriş audit olayı; politika sürümü, rol/kapsam sayıları ve genel neden koduyla sınırlandırılır. LDAP principal, credential, grup ve kapsam kimlikleri audit özetine alınmaz; audit yazılamazsa giriş fail-closed kapanır.
- Üretilen context mevcut dashboard authorization politikasına doğrudan bağlanır; yalnız politika kaynaklı rol ve kapsamlar karar girdisi olur.
- On iki yeni testle toplam 224 test geçti; kimlik hedef grubu 12 testle geçti. Kanıt `08-Uyum-Kanitlari/Erisim/Iterasyon-20A-LDAP-RBAC-Sozlesme-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Değişen Python dosyalarında format, tüm backend/testlerde lint, derleme ve test kontrolleri geçti. Tam depo format kontrolünde değişmeyen 4 eski dosyanın biçim farkı sürüyor.
- Gerçek LDAP endpoint/TLS/sertifika adaptörü, banka grup eşleme değerleri, oturum/lockout, MFA/PAM/break-glass, servis hesabı amacı ve issuer süreç sahipliği kapsam dışıdır; kurum onayları `ComplianceReviewRequired` durumundadır.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-17 — İterasyon 20B: Yapılandırılabilir başarısız giriş sınırlandırması

- `FR-006`, `UC-001`, `NFR-SEC-010`, `AC-002` ve `BFR-IAM-004` alt kapsamı tamamlandı.
- Sürümlü/enjekte edilen politika eşik, ardışık deneme penceresi ve engelleme süresini taşır; teknik taban en fazla beş ret ve en az 15 dakika engeldir.
- Credential reddi kullanıcı ve istemci için ayrı opak anahtarlı SQLite sayaçlarında atomik sayılır; kapsamlardan biri engelliyse LDAP çağrısı yapılmaz.
- Başarılı giriş sayaçları silerek sıfırlar; LDAP teknik/öngörülmeyen hatası, pasif kimlik veya yerel eşleme reddi credential hatası sayılmaz.
- Anahtar üretimi ve throttle deposu hataları fail-closed kapanır. Audit yalnız politika sürümleri, sayaç ve engel özetini taşır; principal, istemci referansı ve credential saklanmaz.
- On üç yeni testle toplam 237 test geçti; kimlik hedef grubu 25 testle geçti. Kanıt `08-Uyum-Kanitlari/Erisim/Iterasyon-20B-Basarisiz-Giris-Sinirlandirma-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Lint, değişen dosyalarda format, `python3` derleme ve tüm testler geçti. Tam depo format kontrolünde değişmeyen dört eski dosyanın biçim farkı sürüyor.
- Üretim anahtar sağlayıcısı/secret manager, güvenilir istemci referansı, paylaşımlı üretim deposu ve banka/LDAP politika değerleri `ComplianceReviewRequired` durumundadır.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-17 — İterasyon 20C: Güvenli oturum yaşam döngüsü

- `FR-001`, `FR-005`, `UC-001`, `NFR-SEC-005`, `NFR-SEC-009`, `AC-001`, `BFR-IAM-001/002/004/005/006` alt kapsamları ve `CTRL-BDDK-IAM-001` için teknik oturum dikeyi tamamlandı.
- LDAP başarı akışı artık çağırandan session kimliği veya bitiş zamanı kabul etmiyor; yalnız güvenilir ve halen geçerli authentication context'i session servisine aktarılıyor.
- Mevcut runtime sürümlü politika 30 dakikalık idle timeout ve enjekte edilen
  mutlak süreyi uygular. Sonraki banka onaylı `OPEN-BNK-020` politikası hedefi
  `PT1H` idle ve `PT10H` mutlak süredir; runtime henüz bu yeni sürüme geçirilmedi.
- Yüksek entropili credential yalnız bir kez döndürülür; SQLite yalnız SHA-256 özetini ve context'i yeniden üretmek için gerekli veri-minimum yetki alanlarını saklar.
- Doğrulama son aktiviteyi kalıcı günceller; timeout `EXPIRED`, çıkış `REVOKED` olur ve credential yeniden kullanılamaz. Tarihsel kayıt fiziksel silinmez.
- Güvenilmez/süresi dolmuş context, servis hesabı, ayrıcalıklı kullanıcı, değiştirilmiş credential ve session depo/audit arızası fail-closed reddedilir.
- On yedi yeni testle toplam 254 test geçti; kimlik hedef grubu 42 testle geçti. Kanıt `08-Uyum-Kanitlari/Erisim/Iterasyon-20C-Guvenli-Oturum-Yasam-Dongusu-Kaniti.md` içinde `TechnicallyVerified` kaydedildi.
- Lint, değişen dosyalarda format, `python3` derleme ve tüm testler geçti. Tam depo format kontrolünde değişmeyen dört eski dosyanın biçim farkı sürüyor.
- Bu iterasyon kapanışında HTTP cookie/token/CSRF sınırı, eş zamanlı oturum
  limiti, mutlak süre, üretim deposu/şifreleme ve saklama süresi inceleme
  bekliyordu. `OPEN-BNK-020` daha sonra `ApprovedByBank` oldu; kararın runtime ve
  üretim altyapısı uygulaması henüz tamamlanmadı.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-17 — İterasyon 21A: Yetki filtreli dashboard trend domain sorgusu

- `FR-054`, `FR-055`, `FR-057`, `UC-010`, `NFR-PERF-001` ve `NFR-PERF-002` gereksinimlerinin son 30 günlük trend domain alt kapsamı tamamlandı.
- Dashboard servisi yalnız güvenilir `ActorContext` üzerinden üretilen kaynak/kurum görünürlük kararını kullanarak 30 UTC takvim günlük sabit pencereyi sorgular.
- SQLite sorgusu zaman ve yetki kapsamını parametreli SQL içinde uygular; servis sonucu ayrıca savunmacı olarak yeniden filtreler. Kurum gözlemleri yalnız açık kurum yetkisiyle döner.
- Eksik günler boş gözlem listesi olarak kalır; `NO_DATA` sayısal sıfıra dönüştürülmez. Depo arızası kalite başarısızlığı yerine redakte `DashboardQueryError` üretir.
- Saat dilimsiz saat ve gözlem damgaları reddedilir. Son 30 gün için 500 sentetik gözlemle yerel p95 koruması üç saniyenin altında geçti.
- On bir yeni testle toplam 265 test geçti; dashboard hedef grubu 29 testle geçti. Kanıt `08-Uyum-Kanitlari/Erisim/Iterasyon-21A-Yetki-Filtreli-Dashboard-Trend-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Lint, değişen dosyalarda format, `python3` derleme ve tüm testler geçti. Tam depo format kontrolünde değişmeyen dört eski dosyanın biçim farkı sürüyor.
- Serbest tarih aralığı/periyot seçimi, operasyon listeleri, grafik/tablo sunumu
  ve HTTP/cookie yüzeyi bu iterasyonun kapsamı dışındadır. `OPEN-BNK-020` artık
  banka onaylıdır; 21B'nin kalan engeli onaylı oturum politikasının uygulanması ve
  geçiş kapısındaki diğer bağımlılıklardır.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-17 — İterasyon 22A: Veri-minimum sistem içi bildirim yaşam döngüsü

- `FR-059`, `FR-060`, `FR-063`, `UC-012`, `RULE-006`, `RULE-011`, `AC-010`, `AC-015`, `AC-016`, `NFR-REL-006`, `BFR-IAM-001/002` ve `BFR-DATA-003` için sistem içi bildirim domain alt kapsamı tamamlandı.
- Yalnız güvenilir servis `ActorContext` ile kalite eşiği, kritik kural başarısızlığı ve teknik hata olayları farklı sabit kod, başlık ve veri-minimum gövdelerle `UNREAD` bildirim oluşturur; olay/scope içeriği gövdeye taşınmaz.
- Alıcı yalnız enjekte edilen güvenilir sahiplik çözümleyicisinden alınır. Eksik alıcı yapılandırma/iş kuralı hatası, resolver veya depo arızası ayrı redakte teknik hata olarak ele alınır.
- Deduplication anahtarı yalnız SHA-256 özetiyle saklanır. Aynı anahtar ve payload tek kaydın sayacını/son görülme zamanını günceller; farklı payload kontrollü çakışma üretir.
- Bildirim ve redakte audit outbox olayı aynı SQLite transaction'ında yazılır; outbox-stage arızasında bildirim rollback olur. Merkezi yayın kesintisi mevcut kalıcı outbox davranışını kullanır.
- Yalnız güvenilir, geçerli, normal kullanıcı context'i kendi bildirimlerini listeleyebilir ve `READ` yapabilir; başka alıcı, servis hesabı ve ayrıcalıklı context fail-closed reddedilir.
- On yedi yeni testle toplam 282 test geçti; bildirim hedef grubu 17 testle geçti. Kanıt `08-Uyum-Kanitlari/Bildirim/Iterasyon-22A-Sistem-Ici-Bildirim-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Lint, değişen dosyalarda format, `python3` derleme ve tüm testler geçti. Tam depo format kontrolünde değişmeyen dört eski dosyanın biçim farkı sürüyor.
- Issue yaşam döngüsü, gerçek sahiplik adaptörü/fallback grup, kuyruk/retry/DLQ, susturma/eskalasyon, serbest şablon yönetimi ve HTTP/UI kapsam dışıdır.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-17 — İterasyon 22B: Otomatik sahipli issue ve temel inceleme geçişi

- `FR-064`, `FR-065` otomatik ilk atama alt kapsamı, `FR-066` `ASSIGNED → INVESTIGATING` alt kapsamı, `FR-070`, `UC-011`, `UC-013`, `RULE-006`, `RULE-011`, `AC-015`, `AC-016`, `NFR-REL-005/006`, `NFR-SEC-001/005/008`, `BFR-IAM-001/002` ve `BFR-DATA-003` için temel issue dikeyi tamamlandı.
- Yalnız güvenilir servis `ActorContext`, güvenilir assignment resolver'dan UUID assignee ve öncelik alarak kalite veya teknik issue oluşturabilir; iki olay türü ayrı kodlanır.
- Deduplication anahtarı SHA-256 özetiyle saklanır ve deterministik issue UUID'si üretir. Aynı payload 100 tekrarda tek issue/bildirim bırakıp sayaç ve son görülme zamanını günceller; farklı payload çakışır.
- Issue oluşturma/tekrar ve monoton sıra numaralı değişmez geçmiş, redakte audit outbox ile aynı SQLite transaction'ındadır. Outbox-stage arızasında issue/geçmiş rollback olur.
- Issue commitinden sonra 22A bildirim servisi çağrılır. Bildirim teknik veya yapılandırma hatasında issue korunur ve issue kimliğini taşıyan ayrı sınıflandırılmış hata döner.
- Yalnız güvenilir, geçerli, normal kullanıcı context'indeki atanmış kullanıcı ve ilgili dataset/source scope'u `ASSIGNED → INVESTIGATING` geçişini yapabilir. Başka kullanıcı, eksik scope, servis veya ayrıcalıklı context fail-closed reddedilir.
- Serbest açıklama, kök neden veya kayıt örneği saklanmaz; assignee, scope, dedup anahtarı ve session kimliği audit allowlist'i dışında kalır.
- Yirmi dört yeni testle toplam 306 test geçti; issue hedef grubu 24 testle geçti. Kanıt `08-Uyum-Kanitlari/Sorun-Yonetimi/Iterasyon-22B-Temel-Issue-State-Machine-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Lint, değişen dosyalarda format, `python3` derleme ve tüm testler geçti. Tam depo format kontrolünde değişmeyen dört eski dosyanın biçim farkı sürüyor.
- Manuel yeniden atama/öncelik, çözüm planı, doğrulama/kapatma/yeniden açma, yorum/ek, ServiceNow, HTTP/UI ve bildirim retry kuyruğu kapsam dışıdır.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-17 — İterasyon 22C: Güvenilir issue yeniden atama ve bildirim

- `FR-065`, `FR-070`, `UC-013`, `AC-017`, `NFR-REL-006` ve `NFR-SEC-001/005/008` için manuel yeniden atama dikeyi tamamlandı.
- Yalnız güvenilir, geçerli, normal kullanıcı context'indeki `DATA_STEWARD` veya `DATA_GOVERNANCE_SPECIALIST` rolü ve ilgili issue scope'u atama yapabilir; servis, ayrıcalıklı, rolesiz ve scope dışı context fail-closed reddedilir.
- Hedef kullanıcı çağıranın rol/scope iddiasından değil, enjekte edilen güvenilir dizin profilinden çözülür; pasif, bulunamayan veya issue kapsamı dışındaki kullanıcı reddedilir.
- Atanan, öncelik ve durum güncellemesi; eski/yeni değerli kronolojik geçmiş ve redakte audit outbox ile aynı SQLite transaction'ında yazılır. Atama `ASSIGNED` veya `INVESTIGATING` durumundan `ASSIGNED` durumuna döner.
- Atama commitinden sonra yeni atanana sabit veri-minimum `ISSUE_ASSIGNED` sistem içi bildirimi üretilir. Bildirim arızasında yerel atama korunur ve hata ayrı sınıflandırılır.
- On iki yeni testle toplam 318 test geçti; issue hedef grubu 36 testle geçti. Kanıt `08-Uyum-Kanitlari/Sorun-Yonetimi/Iterasyon-22C-Guvenilir-Issue-Yeniden-Atama-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Lint, değişen dosyalarda format, `python3` derleme ve tüm testler geçti. Tam depo format kontrolünde değişmeyen dört eski dosyanın biçim farkı sürüyor.
- Gerçek kullanıcı/sahiplik dizini adaptörü, çözüm/doğrulama/kapatma, yorum/ek, ServiceNow, bildirim retry/DLQ ve HTTP/UI kapsam dışıdır.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-17 — İterasyon 22D: Veri-minimum issue çözüm kaydı

- `FR-066`, `FR-068`, `FR-070`, `UC-014`, `RULE-013`, `NFR-REL-006` ve `NFR-SEC-001/005/008` için `RESOLVED` geçişi alt kapsamı tamamlandı.
- Yalnız güvenilir, geçerli, normal kullanıcı context'indeki kayıtlı assignee; ilgili scope ve `DATA_STEWARD`/`DATA_ENGINEER` rolüyle `INVESTIGATING` veya `WAITING_FOR_RESOLUTION` issue'yu çözebilir.
- Kök neden ve düzeltici faaliyet girdisi doğrudan güvenilir sayılmaz; enjekte edilen koruma adaptörünün sürümlü, HTML ve yasak hassas kalıp içermeyen çıktısı kalıcılaştırılır. Kanıt yalnız UUID referansı olarak tutulur.
- Korunan çözüm ayrı append-only tabloda saklanır; issue durumu, çözüm bağlantılı kronolojik geçmiş ve redakte audit outbox aynı SQLite transaction'ında yazılır. Audit çözüm metni, kanıt kimliği veya scope içermez.
- Eksik alan, geçersiz kanıt/zaman, güvenli olmayan koruma çıktısı ve geçersiz durum domain hatası; koruma/depo arızası redakte teknik hata olarak ayrılır. Audit-stage arızasında çözüm, durum ve geçmiş rollback olur.
- On dokuz yeni testle toplam 337 test geçti; issue hedef grubu 55 testle geçti. Kanıt `08-Uyum-Kanitlari/Sorun-Yonetimi/Iterasyon-22D-Veri-Minimum-Issue-Cozum-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Lint, değişen dosyalarda format, `python3` derleme ve tüm testler geçti. Tam depo format kontrolünde değişmeyen dört eski dosyanın biçim farkı sürüyor.
- Gerçek çözüm metni sınıflandırma/temizleme adaptörü, doğrulama sonucu bağı, `VERIFIED/CLOSED`, çözen-doğrulayan görev ayrılığı, yeniden açma, ServiceNow ve HTTP/UI kapsam dışıdır.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-17 — İterasyon 22E: Başarısız doğrulama sonucuyla kontrollü geri dönüş

- `FR-066`, `FR-069`, `UC-014`, `RULE-003`, `RULE-013`, `AC-018` ve `NFR-REL-006` için başarısız doğrulama alt kapsamı tamamlandı.
- `RESOLVED` issue için çağırandan sonuç durumu alınmaz; yalnız UUID doğrulama referansı kabul edilir ve sonuç enjekte edilen güvenilir resolver'dan çözülür. Yalnız kapsam içi normal `DATA_OWNER`/`DATA_STEWARD` context'i akışı çalıştırabilir.
- `QUALITY_FAILED` ve `PARTIAL` sonucu skor/execution bağıyla append-only saklanıp issue'yu `WAITING_FOR_RESOLUTION` durumuna döndürür. `TECHNICAL_ERROR` ayrı sonuç olarak kaydedilir, skor üretmez ve issue'yu kalite başarısızlığına döndürmez.
- Doğrulama kaydı, durum, doğrulama bağlantılı geçmiş ve veri-minimum audit outbox aynı SQLite transaction'ındadır. Audit execution/score/scope kimliği içermez; audit-stage arızasında tüm yazımlar rollback olur.
- Başarılı `QUALITY_PASSED` sonucu bu başarısız doğrulama akışında reddedilir; `VERIFIED/CLOSED` ayrı iterasyona bırakılmıştır. Bu dilimde kapatma/onay olmadığı için maker-checker uygulanmaz; çözen-doğrulayan ayrılığı başarılı doğrulama/kapatma politikasında açık kalır.
- On beş yeni testle toplam 352 test geçti; issue hedef grubu 70 testle geçti. Kanıt `08-Uyum-Kanitlari/Sorun-Yonetimi/Iterasyon-22E-Basarisiz-Dogrulama-Geri-Donus-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Lint, değişen dosyalarda format, `python3` derleme ve sınırlı type-check geçti. Tam `mypy`, değişiklik dışı audit/identity dosyalarındaki 13 mevcut hata nedeniyle temiz değildir.
- Değişiklikler küçük ve tek commit kapsamına uygundur; bu iterasyonda commit oluşturulmadı.

### 2026-07-17 — İterasyon 22F: Başarılı doğrulama ve `VERIFIED` geçişi

- `FR-066`, `FR-069`, `UC-014`, `RULE-013` ve `NFR-REL-006` için başarılı doğrulama alt kapsamı tamamlandı.
- Güvenilir resolver'ın scope ile eşleşen `QUALITY_PASSED` sonucu, zorunlu skor/execution bağıyla append-only kaydedilir ve issue `RESOLVED → VERIFIED` durumuna geçer.
- Yalnız kapsam içi normal `DATA_OWNER`/`DATA_STEWARD` doğrulama yapabilir. Son çözümü kaydeden aktör aynı çözümü doğrulayamaz; maker=checker girişimi kayıt yazılmadan fail-closed reddedilir.
- Doğrulama kaydı, doğrulama bağlantılı geçmiş, durum ve veri-minimum audit outbox aynı SQLite transaction'ındadır. Audit execution/score/scope veya çözüm sahibi kimliği içermez; audit-stage arızasında tüm değişiklikler rollback olur.
- 22E'nin `QUALITY_FAILED`/`PARTIAL → WAITING_FOR_RESOLUTION` ve `TECHNICAL_ERROR → RESOLVED` davranışları korunmuştur. `VERIFIED → CLOSED`, yeniden açma, ServiceNow ve HTTP/UI kapsam dışıdır.
- İki net yeni test vakasıyla toplam 354 test geçti; issue hedef grubu 72 testle geçti. Kanıt `08-Uyum-Kanitlari/Sorun-Yonetimi/Iterasyon-22F-Basarili-Dogrulama-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Lint, değişen dosyalarda format, `python3` derleme ve sınırlı type-check geçti. Tam `mypy`, değişiklik dışı audit/identity dosyalarındaki aynı 13 mevcut hata nedeniyle temiz değildir.
- Değişiklikler küçük ve tek commit kapsamına uygundur; bu iterasyonda commit oluşturulmadı.

### 2026-07-17 — İterasyon 22G: Doğrulanmış issue için kontrollü kapatma

- `FR-066`, `FR-069`, `FR-070`, `UC-014`, `RULE-013`, `AC-018` ve `NFR-REL-006` için `VERIFIED → CLOSED` alt kapsamı tamamlandı.
- Yalnız güvenilir, geçerli, normal ve issue scope'u içindeki `DATA_OWNER`/`DATA_STEWARD` kapanış yapabilir. Çağırandan doğrulama sonucu veya serbest gerekçe alınmaz.
- Kapanış öncesi son append-only doğrulama kaydının `QUALITY_PASSED` ve skor bağlı olduğu savunmacı olarak doğrulanır. `RESOLVED` durumundan doğrudan kapatma, doğrulama kaydı olmayan `VERIFIED`, yetkisiz context ve tekrar kapatma fail-closed reddedilir.
- `CLOSED` durumu, başarılı doğrulama UUID'sine bağlı kronolojik geçmiş ve veri-minimum audit outbox aynı SQLite transaction'ında yazılır. Audit execution/score/scope kimliği içermez; audit-stage arızasında kapanış ve geçmiş rollback olur.
- Kapatma yeni bir çözüm onayı değildir; 22F'de çözümü yapan aktörden farklı güvenilir doğrulayan şartı korunur. Banka onaylı rol eşlemesi `ComplianceReviewRequired` kalır.
- On bir yeni test vakasıyla toplam 365 test geçti; issue hedef grubu 83 testle geçti. Kanıt `08-Uyum-Kanitlari/Sorun-Yonetimi/Iterasyon-22G-Kontrollu-Issue-Kapatma-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Lint, değişen dosyalarda format, `python3` derleme ve sınırlı type-check geçti. Tam `mypy`, değişiklik dışı audit/identity dosyalarındaki aynı 13 mevcut hata nedeniyle temiz değildir.
- Değişiklikler küçük ve tek commit kapsamına uygundur; bu iterasyonda commit oluşturulmadı.

### 2026-07-17 — İterasyon 22H: Aynı kalite başarısızlığında kontrollü yeniden açma

- `FR-064`, `FR-069`, `FR-070`, `UC-014`, `RULE-003`, `RULE-011`, `RULE-013`, `AC-016`, `AC-018` ve `NFR-REL-005/006` için aynı başarısızlıkla yeniden açma alt kapsamı tamamlandı.
- Aynı deduplication anahtarı ve payload ile gelen, kapanış anından eski olmayan güvenilir kalite olayı mevcut `CLOSED` issue'yu yeni kayıt oluşturmadan `WAITING_FOR_RESOLUTION` durumuna getirir ve occurrence sayacını artırır.
- Kapanıştan eski replay kapanış zaman sınırını değiştirmez. Teknik olay yeniden kalite başarısızlığı sayılmaz; aynı anahtarın farklı payload ile kullanımı kontrollü çakışma olarak kalır.
- Yeniden açma durumu, kronolojik geçmiş ve veri-minimum audit outbox aynı SQLite transaction'ında yazılır. Audit scope/dedup kimliği içermez; audit-stage arızasında durum, sayaç ve geçmiş rollback olur.
- Yüz tekrar tek issue ve tek yeniden açma geçmişi üretir. Altı yeni testle toplam 371 test geçti; issue hedef grubu 89 testle geçti.
- Lint, değişen dosyalarda format ve `python3` derleme geçti. Tam depo format kontrolünde değişmeyen dört eski dosyanın biçim farkı, tam `mypy` kontrolünde değişiklik dışı audit/identity dosyalarındaki aynı 13 hata sürüyor.
- Yeni veya farklı kalite başarısızlığının kapalı issue ile ilişkilendirilmesi, gerçek adaptörler, ServiceNow ve HTTP/UI kapsam dışıdır.
- Kod ve test değişiklikleri `990faf5` commit'iyle `origin/main` dalına gönderildi; `.gitignore` kapsamındaki proje hafızası ve kanıt belgeleri yerelde güncellendi.

### 2026-07-17 — İterasyon 22I: Yeni kalite başarısızlığını kapalı issue ile ilişkilendirme

- `FR-064`, `FR-069`, `FR-070`, `UC-014`, `RULE-003`, `RULE-006`, `RULE-011`, `RULE-013`, `AC-016` ve `NFR-REL-005/006` için yeni başarısızlık ilişkisi alt kapsamı tamamlandı.
- Yeni kalite issue'su, yalnız enjekte edilen güvenilir ilişki resolver'ının seçtiği kapalı, aynı scope ve aynı tetik türündeki önceki kalite issue'suna append-only `RECURRENCE` ilişkisiyle bağlanır; çağırandan predecessor veya ilişki türü alınmaz.
- Açık, teknik, farklı scope/tetik türündeki veya kaynak olayı kapanıştan eski predecessor adayları fail-closed reddedilir. Resolver arızası redakte teknik hata olarak ayrılır.
- Yeni issue, predecessor geçmişi, ilişki ve iki veri-minimum audit outbox olayı aynı SQLite transaction'ında yazılır. Audit predecessor/scope/dedup kimliği içermez; ikinci audit-stage arızasında tüm yeni yazımlar rollback olur.
- Farklı deduplication ve değişmiş assignment payload'ı yeni issue üretebilir; yüz replay tek successor ve tek ilişki bırakır. Dokuz yeni test vakasıyla toplam 380 test, issue hedef grubunda 98 test geçti.
- Lint, değişen dosyalarda format, `python3` derleme ve sınırlı mypy geçti. Tam depo format kontrolünde değişmeyen dört eski dosyanın biçim farkı, tam mypy kontrolünde değişiklik dışı audit/identity dosyalarındaki aynı 13 hata sürüyor.
- Gerçek ilişki resolver adaptörü, ServiceNow, saklama-imha ve HTTP/UI kapsam dışıdır.
- Kod ve test değişiklikleri `5321679` commit'iyle `origin/main` dalına gönderildi; `.gitignore` kapsamındaki proje hafızası ve kanıt belgeleri yerelde güncellendi.

### 2026-07-17 — İterasyon 23A: ServiceNow veri-minimum ticket oluşturma

- `FR-071`, `FR-084`, `FR-087`, `AC-019`, `RULE-011`, `NFR-REL-005/006` ve `BFR-EXT-001`–`BFR-EXT-003` için ilk ServiceNow domain dikeyi tamamlandı.
- Yalnız güvenilir, geçerli ve ayrıcalıksız `SERVICE` context'i ile sabit `SERVICENOW_TICKET_PRODUCER` rolü ticket oluşturabilir; kullanıcı, ayrıcalıklı servis ve rolesiz context fail-closed reddedilir.
- Güvenilir issue resolver yalnız issue referansı, kalite/teknik olay türü, öncelik ve opak detay referansından oluşan sabit allowlist projeksiyonu üretir. Serbest issue metni, scope, assignee, ham kayıt, SQL ve secret dış isteğe taşınmaz.
- İdempotency anahtarı SHA-256 özetiyle saklanır. Aynı issue veya aynı anahtar ve payload tek yerel bağlantı/ticket üretir; farklı payload kullanımı kontrollü çakışmadır.
- Yerel ticket bağlantısı, append-only geçmiş ve redakte audit outbox aynı SQLite transaction'ında yazılır. Audit politikası dış çağrıdan önce doğrulanır; outbox-stage arızası yerel başarıyı rollback eder ve fake adaptörün idempotent tekrar davranışı çift harici ticket oluşmasını engeller.
- Adaptör kimlik doğrulama, hız sınırı, geçici ve kalıcı teknik hata sınıflarını domain sonucundan ayrı taşır; bu iterasyonda otomatik retry uygulanmamıştır.
- On sekiz yeni testle toplam 398 test geçti. `servicenow` hedef format/lint/mypy, depo lint ve derleme kontrolleri geçti. Tam depo format kontrolünde değişiklik dışındaki dört eski dosya; tam mypy kontrolünde dokuz eski dosyadaki 29 hata sürmektedir.
- Kanıt `08-Uyum-Kanitlari/Sorun-Yonetimi/Iterasyon-23A-ServiceNow-Veri-Minimum-Ticket-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Gerçek ServiceNow endpoint/credential, retry/backoff, durum senkronizasyonu, HTTP/UI ve banka kurulum/veri aktarım kararı kapsam dışıdır; `OPEN-BNK-009` açık kalır.
- Kod ve test değişiklikleri `6b53c53` commit'iyle `origin/main` dalına gönderildi; proje hafızası ve kanıt belgeleri yerelde güncellendi.

### 2026-07-17 — İterasyon 23B: ServiceNow sınıflandırılmış retry ve kontrollü backoff

- `FR-087`, `UC-013`, `AC-019`, `NFR-REL-001/005/006` ve `BFR-EXT-001`–`BFR-EXT-003` için ServiceNow senkron retry alt kapsamı tamamlandı.
- Sürümlü ve değişmez `ServiceNowRetryPolicy`, toplam deneme sayısını 1–3 aralığında sınırlar; sonlu olmayan veya negatif temel gecikmeyi başlangıçta reddeder.
- Yalnız `TEMPORARY` hata üstel gecikmeyle, `RATE_LIMIT` ise geçerli tam sayı `Retry-After` değeriyle yeniden denenir. Kimlik doğrulama, kalıcı, bilinmeyen hata ve geçersiz/eksik `Retry-After` ilk denemede durur.
- Enjekte edilebilir sleeper ile gerçek bekleme olmadan `[1, 2]` üstel gecikme, tam `Retry-After`, üç denemede tükenme ve retry planlama hata sınırı test edilebilir hale getirildi.
- Tüm denemeler aynı veri-minimum istek ve özetlenmiş idempotency kimliğini kullanır; geçici hata sonrası başarı ve sonraki replay tek harici ticket ve tek yerel bağlantı üretir. Ham adaptör hata ayrıntısı saklanmaz.
- Sekiz yeni test vakasıyla toplam 406 test geçti; ServiceNow hedef grubu 26 testle geçti. Hedef format/lint/mypy, depo lint ve derleme kontrolleri geçti.
- Tam depo format kontrolünde değişiklik dışındaki dört eski dosya, tam mypy kontrolünde dokuz eski dosyadaki 29 hata sürmektedir.
- Kanıt `08-Uyum-Kanitlari/Sorun-Yonetimi/Iterasyon-23B-ServiceNow-Retry-Backoff-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Kalıcı retry kuyruğu/DLQ, circuit breaker, timeout uygulayan gerçek ağ adaptörü, durum senkronizasyonu ve `OPEN-BNK-009` kapsam dışıdır.
- Kod ve test değişiklikleri `7e24946` commit'iyle `origin/main` dalına gönderildi; proje hafızası ve kanıt belgeleri yerelde güncellendi.

### 2026-07-17 — İterasyon 23C: ServiceNow kalıcı retry kuyruğu ve dead-letter

- `FR-087`, `UC-013`, `RULE-011`, `NFR-REL-001/005/006/007` ve `BFR-EXT-001`–`BFR-EXT-003` için kalıcı entegrasyon retry işi dikeyi tamamlandı.
- 23B senkron geçici denemeleri tükendiğinde açık idempotency anahtarı yerine özeti ve sabit allowlist request alanlarını taşıyan tek SQLite `PENDING` retry işi atomik audit outbox olayıyla oluşturulur. Aynı issue/anahtar/payload tekrarında yeni iş veya dış çağrı oluşmaz.
- Due-time sıralı atomik claim yalnız bir worker'a `PROCESSING` işi verir ve deneme sayısını artırır. Worker yüzeyi yalnız güvenilir, geçerli, ayrıcalıksız `SERVICE` context'iyle çalışır; kullanıcı ve ayrıcalıklı servis claim öncesi reddedilir.
- Geçici hata üstel next-at zamanıyla yeniden `PENDING` olur; kimlik/kalıcı/bilinmeyen hata veya üçüncü asenkron deneme `DEAD_LETTER` üretir. Başarı job, ticket linki, geçmiş ve redakte audit outbox'ını aynı transaction'da `COMPLETED` yapar.
- Dead-letter işi güvenilir servis context'iyle auditli olarak yeniden kuyruğa alınabilir. Audit/depo hatasında claim geri bırakılır; dış ticket oluşturulmuşsa aynı özetlenmiş anahtarla idempotent replay yerel linki güvenle tamamlar.
- Kuyruk satırı issue metni, assignee, scope, açık idempotency anahtarı, ham hata gövdesi, SQL veya secret saklamaz; audit yalnız durum, deneme sayısı ve teknik hata sınıfını taşır.
- On bir yeni test vakasıyla toplam 417 test geçti; ServiceNow hedef grubu 37 testle geçti. Hedef format/lint/mypy, depo lint ve derleme kontrolleri geçti.
- Tam depo format kontrolünde değişiklik dışındaki dört eski dosya, tam mypy kontrolünde dokuz eski dosyadaki 29 hata sürmektedir.
- Kanıt `08-Uyum-Kanitlari/Sorun-Yonetimi/Iterasyon-23C-ServiceNow-Kalici-Retry-Kuyrugu-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Gerçek broker, çoklu süreç lease/heartbeat recovery, operasyon alarmı, circuit breaker, gerçek ağ adaptörü ve `OPEN-BNK-009` kapsam dışıdır.
- Kod ve test değişiklikleri `8127e9c` commit'iyle `origin/main` dalına gönderildi; proje hafızası ve kanıt belgeleri yerelde güncellendi.

### 2026-07-17 — İterasyon 23D: ServiceNow yapılandırılabilir circuit breaker

- `FR-087`, `UC-013`, `RULE-011`, `NFR-REL-003/005/006/007` ve `BFR-EXT-001`–`BFR-EXT-003` için ServiceNow circuit breaker dikeyi tamamlandı.
- Sürümlü `ServiceNowCircuitBreakerPolicy` varsayılan olarak aynı teknik hedefte beş ardışık geçici/hız sınırı hatasından sonra devreyi beş dakika açar. Kimlik, kalıcı, bilinmeyen hata ve başarı ardışık sayacı sıfırlar; bunlar kalite başarısızlığı sayılmaz.
- SQLite üzerinde kalıcı `CLOSED`, `OPEN` ve `HALF_OPEN` durumları uygulanmıştır. Açık devre dış adaptörü çağırmadan isteği veri-minimum retry kuyruğuna alır; worker claim'i açık devrede geri bırakılır.
- Beş dakika sonunda koşullu durum güncellemesi yalnız bir half-open probe'a izin verir. Başarılı veya geçici olmayan probe devreyi kapatır; geçici probe açılma zamanını yenileyerek devreyi tekrar açar.
- Açılma, half-open ve kapanma geçişleri yalnız durum, teknik hata sınıfı ve politika sürümünü taşıyan redakte audit outbox olayıyla aynı SQLite transaction'ında yazılır; audit-stage arızasında circuit geçişi rollback olur.
- On yeni test vakasıyla toplam 427 test geçti; ServiceNow hedef grubu 47 testle geçti. Hedef format/lint/mypy, depo lint ve derleme kontrolleri geçti.
- Tam depo format kontrolünde değişiklik dışındaki dört eski dosya, tam mypy kontrolünde dokuz eski dosyadaki 29 hata sürmektedir.
- Kanıt `08-Uyum-Kanitlari/Sorun-Yonetimi/Iterasyon-23D-ServiceNow-Circuit-Breaker-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Gerçek/dağıtık circuit state deposu, ağ timeout adaptörü, operasyon alarmı, endpoint/credential ve `OPEN-BNK-009` kapsam dışıdır.
- Kod ve test değişiklikleri `c910d0c` commit'iyle `origin/main` dalına gönderildi; proje hafızası ve kanıt belgeleri yerelde güncellendi.

### 2026-07-17 — İterasyon 24A: Yetki filtreli audit inceleme domain sorgusu

- `FR-077`–`FR-079`, `UC-016`, `NFR-SEC-001/005/008/011`, `NFR-CMP-001/002/003`, `BFR-IAM-001/002/004`, `BFR-AUD-002/003/005`, `BRULE-001/005` ve `AC-026` için salt okunur audit inceleme dikeyi tamamlandı.
- Sürümlü `AuditAccessPolicy`, yalnız güvenilir, geçerli, ayrıcalıksız `USER` context'i ve ayrı `AUDIT_VIEWER` rolüyle sorguya izin verir. Eksik/sahte context, servis aktörü, ayrıcalıklı context, rol veya politika sürümü uyuşmazlığı fail-closed reddedilir ve veri-minimum denied audit olayı üretir.
- UTC tarih aralığı, aktör, işlem, nesne türü/kimliği, sonuç ve correlation filtresi; 1–100 sayfa boyutu ve sequence cursor desteği parametreli SQLite sorgusuyla uygulanmıştır. Senkron pencere 31 günle sınırlıdır; daha geniş aralık asenkron rapor gerektirir.
- İlk sayfa append-only zincirin üst sequence sınırını sabitler; sonraki sayfalar aynı snapshot'ı kullanır ve sorgu audit olaylarının sonuç kümesine karışması engellenir.
- Sonuçlar redakte audit zarfını ve bütünlük doğrulama sonucunu döndürür. Bozulmuş kayıt sessizce düzeltilmez veya silinmez; teknik repository hatası doğrulama/veri kalitesi sonucundan ayrı `AuditQueryTechnicalError` olur.
- Başarılı görüntüleme yalnız politika sürümü, gerekçe kodu, filtre/sayfa/sonuç sayısı ve bütünlük sonucunu auditler; filtre değerlerini, session kimliğini veya ham hassas veriyi audit özetine yazmaz. Görüntüleme audit'i yazılamazsa sonuç fail-closed döndürülmez.
- On dört yeni test vakasıyla toplam 441 test geçti; audit hedef grubu 26 testle geçti. Hedef format/lint/mypy, depo lint ve derleme kontrolleri geçti.
- Tam depo format kontrolünde değişiklik dışındaki dört eski dosya sürmektedir. Dokunulan iki eski type hatası giderildi; tam mypy bakiyesi yedi dosyada 27 hataya düştü.
- Kanıt `08-Uyum-Kanitlari/Audit/Iterasyon-24A-Yetki-Filtreli-Audit-Inceleme-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- HTTP/UI, istemci bilgisi filtresi, beş yıllık asenkron rapor, dosya dışa aktarma, DLP/watermark ve banka onaylı auditor rol eşlemesi kapsam dışıdır; `OPEN-BNK-002`, `OPEN-BNK-008` ve `OPEN-BNK-014` açık kalır.

### 2026-07-20 — İterasyon 24B: Yetki filtreli ve maskeli rapor önizleme

- `FR-072`, `UC-015`, `AC-021/023`, `NFR-PERF-002`, `NFR-PRV-001/002/003`, `NFR-SEC-001/005/008`, `BFR-IAM-001/002/004`, `BFR-AUD-005` ve `BRULE-001/005` için source-seviyesi özet rapor önizleme dikeyi tamamlandı.
- Sürümlü `ReportPreviewAccessPolicy`, yalnız güvenilir, geçerli, ayrıcalıksız `USER` context'i ve izinli raporlama rolüyle çalışır. Eksik/sahte context, servis aktörü, ayrıcalıklı context ve rolesiz erişim fail-closed reddedilir ve veri-minimum denied audit olayı üretir.
- Kullanıcının istediği source kapsamı güvenilir context kapsamının alt kümesi olmalıdır; kapsam genişletme reader çağrısından önce reddedilir. Scope filtresi parametreli SQLite sorgusuna itilerek yetkisiz source satırı sorgu sonucuna alınmaz.
- Önizleme son 31 günlük pencerede en fazla 500 yetkili source için her source'un en güncel, önceden toplulaştırılmış `SOURCE` skorunu döndürür. Filtreler ve üretim zamanı görünür; execution/rule kimliği, hesaplama detayı, ham kayıt veya hata örneği sözleşmede bulunmaz.
- `CALCULATED` skorlar iki ondalıklı ortalamaya katılır; `NO_DATA` ve teknik sonuçlar sayısal sıfıra dönüştürülmez. Reader kapsam dışı/yinelenen kaynak, aralık dışı tarih veya geçersiz skor döndürürse servis fail-closed teknik hata üretir.
- Reader'ın yalnız `WITH/SELECT` çalıştırdığı doğrulandı. Başarılı görüntüleme auditi source/filter kimliklerini değil politika, kodlanmış gerekçe, pencere ve sayısal özetleri taşır; audit yazılamazsa önizleme sonucu verilmez.
- On sekiz yeni test vakasıyla toplam 459 test geçti; reporting hedef grubu 18 testle geçti. 500 source ve 20 tekrarlı yerel p95 koruma testi 1 saniye hedefini karşıladı; bu üretim kapasite kanıtı değildir.
- Hedef format/lint/mypy, depo lint ve derleme kontrolleri geçti. Tam depo format kontrolünde değişiklik dışındaki dört eski dosya, tam mypy kontrolünde yedi eski dosyadaki 27 hata sürmektedir.
- Kanıt `08-Uyum-Kanitlari/Raporlama/Iterasyon-24B-Yetki-Filtreli-Rapor-Onizleme-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- PDF/XLSX/CSV üretimi, Report kaydı, asenkron iş, indirme, HTTP/UI, DLP/watermark, geçici dosya saklama ve banka onaylı rol/dışa aktarma politikası kapsam dışıdır; `OPEN-BNK-002`, `OPEN-BNK-007`, `OPEN-BNK-008` ve `OPEN-BNK-014` açık kalır.

### 2026-07-20 — İterasyon 26A: Veri-minimum güvenlik olayı ve ihlal şüphesi ayrımı

- `BFR-IR-001`–`BFR-IR-004`, `CTRL-KVKK-BREACH-001`, `NFR-OBS-001/003`, `NFR-PRV-001/002/005` ve `NFR-SEC-001/005/008/011` için ilk olay müdahale domain dikeyi tamamlandı.
- Teknik güvenlik olayı ve kişisel veri ihlali şüphesi ayrı append-only tablolarda tutulur; güvenlik olayı tek başına ihlal kaydı üretmez.
- İhlal şüphesi öğrenilme zamanı, veri-minimum kapsam/önlem kodları, kişisel veri kategori sayımı, opak kanıt referansları ve görünür 72 saat değerlendirme hedefiyle güvenlik olayına bağlanır. Veri işleyen kaynaklı şüphede veri sorumlusuna bildirim kanıtı UUID referansı zorunludur.
- Bildirim kararı yalnız güvenilir, ayrıcalıksız `PRIVACY_INCIDENT_REVIEWER` kullanıcısı tarafından ve şüpheyi kaydeden aktörden farklı checker ile append-only kaydedilir. Dış bildirim alanı yapısal olarak `false` kalır; Kurula veya ilgili kişiye otomatik bildirim adaptörü yoktur.
- Kaynak/dataset/kurum kapsamı güvenilir context ile fail-closed denetlenir. Eksik/sahte, rolesiz, servis ve ayrıcalıklı context ile scope yükseltme reddedilir ve veri-minimum audit olayı üretir.
- Domain kaydı, zaman çizelgesi ve redakte audit outbox aynı SQLite transaction'ındadır; audit stage arızasında tüm domain yazımları rollback olur. Teknik depo arızası ihlal veya veri kalitesi sonucu olarak raporlanmaz.
- Yirmi üç yeni test vakasıyla toplam 482 test geçti. Hedef format/lint/mypy, depo lint ve derleme kontrolleri geçti; tam depo format ve mypy bakiyeleri değişmedi.
- Kanıt `08-Uyum-Kanitlari/Olay-Mudahale/Iterasyon-26A-Veri-Minimum-Ihlal-Suphesi-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Gerçek SIEM/SOC adaptörü, banka onaylı olay/rol sözlüğü, serbest açıklama veya ham kanıt içeriği, HTTP/UI, dış bildirim, saklama/imha ve hukuk/uyum kararı kapsam dışıdır; `OPEN-BNK-001`, `OPEN-BNK-002`, `OPEN-BNK-004`, `OPEN-BNK-008` ve `OPEN-BNK-010` açık kalır.

### 2026-07-20 — İterasyon 26B: Yetki filtreli ihlal zaman çizelgesi inceleme

- `BFR-IR-002/003`, `CTRL-KVKK-BREACH-001`, `NFR-PRV-001/002/005` ve `NFR-SEC-001/005/008/011` için veri-minimum ihlal zaman çizelgesi sorgusu tamamlandı.
- Yalnız güvenilir, geçerli, ayrıcalıksız `USER` context'i ve `PRIVACY_INCIDENT_REVIEWER` rolü sorgu yapabilir. Gerçek incident scope'u repository kaydından çözülür; eksik/sahte, rolesiz, servis, ayrıcalıklı ve scope dışı erişim fail-closed reddedilir.
- Görünüm ihlal kimliği, öğrenilme/değerlendirme zamanı, değerlendirme ve 72 saat durumu, veri-minimum kapsam/önlem kodları, kategori sayısı, kanıt varlık bayrağı ve olay türü/zaman/kod dizisini döndürür.
- Incident/scope/actor/timeline/decision kimlikleri ile tüm kanıt UUID'leri görünüm sözleşmesinde bulunmaz. Veri işleyen bildirim kanıtı yalnız var/yok bayrağına indirgenir.
- `ASSESSMENT_PENDING`, `ASSESSMENT_OVERDUE`, `DECIDED_ON_TIME` ve `DECIDED_OVERDUE` durumları öğrenilme zamanı ve insan kararı üzerinden deterministik hesaplanır; hiçbir durum dış bildirim tetiklemez.
- Timeline kapsam, bağlantı, zorunlu/tekil olay, zaman ve kod bütünlüğü savunmacı olarak doğrulanır. Bozuk veya yinelenen timeline teknik hata olur; veri kalitesi ya da ihlal kararı sayılmaz.
- Başarılı görüntüleme yalnız kodlanmış gerekçe, durumlar ve sayısal/bool özetlerle auditlenir. Audit stage arızasında görünüm fail-closed verilmez.
- On altı yeni test vakasıyla toplam 498 test geçti. Hedef format/lint/mypy, depo lint ve derleme kontrolleri geçti; tam depo format ve mypy bakiyeleri değişmedi.
- Kanıt `08-Uyum-Kanitlari/Olay-Mudahale/Iterasyon-26B-Yetki-Filtreli-Ihlal-Zaman-Cizelgesi-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- HTTP/UI, ham kanıt görüntüleme, gerçek SIEM/SOC, banka rol/olay sözlüğü, dış bildirim ve saklama/imha kapsam dışıdır; `OPEN-BNK-001`, `OPEN-BNK-002`, `OPEN-BNK-008` ve `OPEN-BNK-010` açık kalır.

### 2026-07-20 — İterasyon 28A: Yerel veri-minimum secret tarama sözleşmesi

- `BFR-SDLC-001/002` ve `NFR-SEC-005/012` için repository dosyalarını salt okunur inceleyen `secure_sdlc` paketi ve CLI eklendi.
- Sürümlü `28A-v1` politika `.git`, cache, build ve bağımlılık dizinlerini dışlar; binary, büyük, düzenli olmayan ve sembolik bağlantılı dosyaları taramaz.
- Bulgular yalnız göreli dosya yolu, satır/sütun ve kural kodu taşır. Eşleşen değer, satır içeriği ve ham işletim sistemi hatası sonuç modeline veya CLI çıktısına alınmaz.
- Temiz, bulgulu ve teknik olarak tamamlanamayan taramalar sırasıyla `0`, `1` ve `2` çıkış kodlarıyla ayrılır; okuma hatası temiz tarama sayılamaz.
- On üç sentetik testle gerçek pozitif/yanlış pozitif, dışlama, salt okunurluk, deterministik sıra, redaksiyon ve teknik hata yolları doğrulandı; toplam 511 test geçti.
- Yerel repository taraması 303 metin dosyasında `CLEAN` sonucu verdi. Hedef format/lint/mypy, depo lint ve derleme kontrolleri geçti. Tam depo format kontrolündeki dört eski dosya ve tam mypy kontrolündeki yedi dosyada 27 eski hata değişmedi.
- Kanıt `08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-28A-Yerel-Veri-Minimum-Secret-Tarama-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- CI/CD zorlaması, harici tarayıcı, geçmiş commit taraması, bağımlılık/SAST/DAST taraması, SBOM ve pentest kapsam dışıdır; ürün/eşik/istisna politikası `ComplianceReviewRequired` kalır.

### 2026-07-20 — İterasyon 28B: Deterministik yerel bağımlılık envanteri ve SBOM başlangıç paketi

- `BFR-SDLC-001/002/004` ve `NFR-SEC-012` için PEP 621 bağımlılık envanteri ile deterministik CycloneDX 1.5 üreticisi eklendi.
- Proje `0.1.0`, Python `>=3.10` ve doğrudan çalışma zamanı bağımlılıkları tam sürüme sabitlenmiş olarak `pyproject.toml` içinde beyan edildi.
- Üretici yalnız açık `[project]` metadata'sını salt okunur işler; eksik/dinamik sürüm veya bağımlılık, tam pin olmayan/URL/extras/yinelenen beyan güvenli neden koduyla başarısız olur.
- SBOM proje sürümü, Python sınırı ve doğrudan bağımlılık grafiğini taşır; timestamp, rastgele seri numarası, yerel yol, kullanıcı bilgisi veya ham teknik hata içermez.
- `Iterasyon-28B-SBOM.cdx.json` artifact'ı yeniden üretilen çıktıyla byte düzeyinde eşleşti, SHA-256 özeti kaydedildi ve resmî CycloneDX 1.5 JSON şemasını geçti.
- On dokuz yeni sentetik vakayla güvenli SDLC hedef grubu 32, toplam test sayısı 530 oldu. Depo lint, hedef format/mypy ve derleme kontrolleri geçti; secret taraması `CLEAN` kaldı. Tam depo formatındaki dört eski dosya ve tam mypy kontrolündeki yedi dosyada 27 eski hata değişmedi.
- Kanıt `08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-28B-Deterministik-Bagimlilik-SBOM-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Transitive çözüm/lock, artifact hash'i, lisans, zafiyet taraması, CI/CD ve harici ürün/eşik/istisna politikası kapsam dışıdır ve `ComplianceReviewRequired` kalır.

### 2026-07-20 — İterasyon 28C: Yerel SAST bulgu ve sürüm kapısı sözleşmesi

- `BFR-SDLC-001/002/003` ve `NFR-SEC-012` için ürün bağımsız, veri-minimum SAST bulgu zarfı ve `28C-v1` sürüm kapısı eklendi.
- Bulgu yalnız scanner kimliği/sürümü, kural kodu, önem derecesi ve repository-relative satır/sütun konumunu kabul eder; source line, snippet, mesaj, secret ve mutlak/traversal yollar reddedilir.
- Tamamlanmamış tarama ayrı teknik hata olarak sürüm kanıtını engeller. Tamamlanmış rapordaki `CRITICAL` bulgular fail-closed bloklanır; kritik olmayan bulgular kanıtta yalnız sayım ve deterministik digest ile temsil edilir.
- Başarılı kanıt 28B PEP 621 envanterindeki proje adı/sürümünü gate ve scanner sürümüne bağlar; bulgu yolu veya rule code kanıta açık metin yazılmaz.
- 26 yeni sentetik vakayla güvenli SDLC hedef grubu 58, toplam test sayısı 556 oldu. Depo lint, hedef format/mypy ve derleme kontrolleri geçti; secret taraması 319 dosyada `CLEAN` kaldı.
- Tam depo formatındaki dört eski dosya ve tam mypy kontrolündeki yedi dosyada 27 eski hata değişmedi.
- Kanıt `08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-28C-Yerel-SAST-Surum-Kapisi-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Gerçek SAST scanner/repository taraması, CI/CD zorlaması, kritik olmayan eşikler, istisna/risk kabulü, release maker-checker, DAST ve pentest kapsam dışıdır ve `ComplianceReviewRequired` kalır.

### 2026-07-20 — İterasyon 30A: Frontend görsel tasarım dokümantasyon tabanı

- Frontend görsel doğruluk kaynağı `04-Frontend/Gorsel-Tasarim-Sistemi.md`, ilk ekran
  sözleşmesi `04-Frontend/03-Dashboard/Dashboard-Ekran-Sozlesmesi.md` ve görsel test
  stratejisi `06-Testler/03-Uctan-Uca/Gorsel-Dogrulama-Stratejisi.md` altında kuruldu.
- Bankanın ana tema rengi `#FDB813` olarak kaydedildi; marka rengi semantik uyarı
  değildir. Kritik veri kalitesi ihlali kırmızı, teknik hata mor, operasyonel uyarı
  turuncu, başarı yeşil, bilgi mavi ve veri yok gri olarak ayrıldı.
- Koyu lacivert navigasyon, açık gri çalışma alanı, beyaz düşük gölgeli yüzey, yoğun
  dashboard, grafik/tablo/KPI/alarm/heatmap, responsive ve erişilebilirlik kuralları
  token tabanlı tek tasarım sistemi belgesinde toplandı.
- `04-Frontend/references/reference-dashboard.png` 1440×900 sentetik dashboard
  referansı olarak oluşturuldu. İki görsel iyileştirme turunda KPI yerleşimi ve alarm
  satırı taşması giderildi; görsel gerçek banka veya müşteri verisi içermez.
- React, TypeScript, Vite, MUI ve ECharts frontend stack'i; Storybook component
  doğrulaması ve Playwright ekran/görsel doğrulaması teknik karar olarak
  kesinleştirildi. Araçlar proje bağımlılığı olarak henüz kurulmadı.
- İlk uygulanacak görsel ekran kurumsal dashboard olarak belirlendi. Uygulama 21B
  güvenli HTTP/API sınırı ve bankacılık geçiş kapısına bağlıdır; frontend stack
  veya toolchain seçimi için yeniden onay beklenmez.
- Kaynak kodu, frontend componenti, dependency ve build yapılandırması değişmedi;
  556 birim test baseline'ı ve sıradaki hazır İterasyon 28D korunmuştur.

### 2026-07-20 — İterasyon 28D: Yerel bağımlılık zafiyet bulgu ve sürüm kapısı sözleşmesi

- `BFR-SDLC-001/002/003/004` ve `NFR-SEC-012` için ürün bağımsız, veri-minimum
  doğrudan bağımlılık zafiyet bulgu zarfı ve `28D-v1` sürüm kapısı eklendi.
- Bulgu yalnız scanner/advisory kimliği ve sürümü, advisory kimliği, önem derecesi
  ile kanonik bağımlılık adı/sürümünü kabul eder; açıklama, mesaj, URL, düzeltme
  sürümü, yerel yol ve secret reddedilir.
- Bulgular 28B envanterindeki tam doğrudan paket/sürüm çiftiyle eşleştirilir.
  Tamamlanmamış tarama ayrı teknik hata olur; `CRITICAL` bulgu kanıtı fail-closed
  engeller, kritik olmayan bulgular yalnız sayı ve digest'e bağlanır.
- Başarılı kanıt proje/gate/scanner/advisory sürümleri, açık
  `declared-direct-dependencies` kapsamı ve deterministik envanter/bulgu SHA-256
  özetlerini taşır; advisory veya paket ayrıntısını açık metin çoğaltmaz.
- 37 yeni sentetik vakayla güvenli SDLC hedef grubu 95, toplam test sayısı 593 oldu.
  Depo lint, hedef format/mypy ve derleme kontrolleri geçti; secret taraması 326
  dosyada `CLEAN` kaldı ve 28B SBOM'u byte düzeyinde yeniden üretildi.
- Kanıt `08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-28D-Bagimlilik-Zafiyet-Surum-Kapisi-Kaniti.md`
  içinde `TechnicallyVerified` olarak kaydedildi.
- Gerçek zafiyet veritabanı/ağ taraması, transitive lock/artifact doğrulaması,
  kritik olmayan banka eşikleri, istisna/risk kabulü, CI/CD, release maker-checker,
  DAST ve pentest kapsam dışıdır ve `ComplianceReviewRequired` kalır.

### 2026-07-20 — İterasyon 28E: Veri-minimum sızma testi bulgu takip sözleşmesi

- `BFR-SDLC-003/005`, `NFR-SEC-012` ve destekleyici `NFR-CMP-002/005` için
  ürün bağımsız `28E-v1` bulgu takip sözleşmesi eklendi.
- Bulgu yalnız opak değerlendirme, bulgu, iyileştirme aksiyonu ve sorumlu taraf
  UUID referansları ile önem derecesini kabul eder; serbest metin ve ham teknik
  içerik fail-closed reddedilir.
- Değişmez `OPEN -> READY_FOR_RETEST -> CLOSED` yaşam döngüsü uygulanmıştır.
  Başarısız tekrar test bulguyu `OPEN` durumuna döndürür; teknik hata güvenlik
  sonucu sayılmaz ve bulguyu tekrar teste hazır bırakır.
- Tamamlanmamış değerlendirme ayrı teknik hata üretir. Kapanmamış `CRITICAL`
  bulgu kanıtı engeller; başarılı kanıt yalnız toplam/durum sayımları ile
  deterministik SHA-256 digest taşır.
- 37 yeni sentetik vakayla güvenli SDLC hedef grubu 132, toplam test sayısı 630
  oldu. Depo lint, hedef format/mypy ve derleme kontrolleri geçti.
- Kanıt [İterasyon 28E Veri-Minimum Pentest Bulgu Takip Kanıtı](../08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-28E-Veri-Minimum-Pentest-Bulgu-Takip-Kaniti.md)
  içinde `TechnicallyVerified` olarak kaydedildi.
- Gerçek pentest hizmeti, banka kapsamı/sıklığı, bağımsızlık şartı, resolver'lar,
  kalıcı depo, CI/CD, release maker-checker ve banka onayı kapsam dışıdır ve
  `ComplianceReviewRequired` kalır.

### 2026-07-20 — İterasyon 29A: Teknik kanıt paketi manifesti ve eksik kontrol raporu

- `BFR-SDLC-002`, `BRULE-004/005`, `NFR-CMP-002/005` ve BDDK/KVKK
  matrislerindeki 15 `CTRL-*` kaydı için `29A-v1` teknik kanıt manifesti eklendi.
- Sürümlü JSON katalog 8 BDDK ve 7 KVKK kontrolünü eksiksiz/tekil doğrular; kanıt
  artifact'larını yalnız `08-Uyum-Kanitlari/` altından salt okunur açıp göreli yol
  ve SHA-256 ile deterministik manifestte bağlar.
- Teknik durum, banka inceleme durumu ve açık `OPEN-BNK-*` engelleri ayrıdır.
  Opak karar referansı olmadan `ApprovedByBank` veya `NotApplicable` kabul edilmez.
- Gerçek baseline 15 kontrolün 12'sini `Partial`, 3'ünü `Missing`, 14'ünü açık
  kararlarla engelli ve tamamını `ComplianceReviewRequired` raporlar; hiçbir
  kontrol banka onaylı gösterilmez.
- 37 yeni sentetik vakayla güvenli SDLC hedef grubu 169, toplam test sayısı 667
  oldu. Hedef Ruff/mypy, depo lint, derleme ve manifest byte karşılaştırması geçti.
- Katalog, manifest ve teknik kanıt [Sürüm Paketleri](../08-Uyum-Kanitlari/Surum-Paketleri/README.md)
  altında kaydedildi.
- Elektronik imza, WORM/HSM, kurumsal kanıt deposu, CI/CD drift kapısı, eksik
  kontrollerin uygulanması ve banka kabul iş akışı kapsam dışıdır.

### 2026-07-20 — İterasyon 29B: Teknik kanıt manifesti drift doğrulama kapısı

- `BFR-SDLC-002`, `BRULE-004/005` ve `NFR-CMP-002/005` için `29B-v1`
  fail-closed manifest drift kapısı eklendi.
- Kapı 29A katalog/kanıtlarından manifesti kanonik baytlarla yeniden üretir ve
  depodaki sürüm manifestiyle byte düzeyinde karşılaştırır.
- `MATCH` çıkış kodu `0`, `DRIFT` çıkış kodu `1`, doğrulama veya teknik hata
  veri-minimum neden koduyla çıkış kodu `2` üretir.
- Saklanan manifest yalnız sürüm paketi altındaki kanonik `.json` yolundan salt
  okunur açılır; traversal, mutlak yol, symlink, eksik, düzenli olmayan ve büyük
  dosya reddedilir.
- Sonuç yalnız politika, durum ve saklanan/üretilen SHA-256 özetlerini taşır;
  manifest veya kanıt içeriğini çoğaltmaz.
- 15 yeni sentetik vakayla güvenli SDLC hedef grubu 184, toplam test sayısı 682
  oldu. Gerçek 29A artifact'ı aynı SHA-256 özetiyle `MATCH` verdi.
- CI/CD ürünü, elektronik imza, WORM/HSM, istisna/risk kabulü, release
  maker-checker ve banka onayı kapsam dışıdır.

### 2026-07-20 — İterasyon 29C: Birleşik yerel sürüm ön kontrolü

- `BFR-SDLC-001`–`BFR-SDLC-005`, `BRULE-004/005` ve `NFR-CMP-002/005` için
  `29C-v1` birleşik yerel sürüm ön kontrolü eklendi.
- Secret taraması, saklanan SBOM, SAST, bağımlılık zafiyeti, pentest ve teknik
  kanıt manifesti kontrolleri sabit fail-closed sırada birleştirildi.
- Harici güvenlik raporları zorunlu sürümlü JSON paketinden exact-field allowlist
  ile alınır; eksik/tamamlanmamış rapor temiz sonuca dönüştürülmez.
- Secret/kritik bulgu ve artifact drift'i `BLOCKED`; doğrulama ve teknik hata ayrı
  sonuçlardır. Başarılı çıktı yalnız politika ve SHA-256 kanıt özetlerini taşır.
- 20 yeni sentetik vakayla güvenli SDLC hedef grubu 204, toplam test sayısı 702
  oldu. Secret taraması 341 dosyada `CLEAN`, SBOM ve manifest karşılaştırmaları
  eşleşen sonuç verdi.
- Gerçek scanner/pentest, CI/CD zorlaması, imzalı kurumsal kanıt deposu,
  istisna/risk kabulü ve banka onayı kapsam dışıdır.

### 2026-07-20 — Bakım İterasyonu 29C.1: Tam depo tip kontrolü temizliği

- Kimlik hata yollarında her zaman exception üreten yardımcılar `NoReturn` ile
  tanımlandı; çalışma zamanı davranışı değiştirilmeden mypy akış daraltması
  kesinleştirildi.
- PostgreSQL, skorlama, dashboard ve issue test double/fixture tipleri gerçek
  protokoller ve gözlenen veri yapılarıyla eşleştirildi.
- Tam `python3 -m mypy 03-Backend/src 06-Testler` kontrolü 109 kaynak dosyada
  sıfır hatayla; hedefli 252 test ve tam 702 test başarıyla tamamlandı.
- Ruff lint ve değişen yedi dosyanın format kontrolü geçti. Tam depo format
  kontrolündeki dört tarihsel biçim farkı bu bakım kapsamının dışındadır.
- `FR-001`, `FR-002`, `FR-005`, `UC-001`, `NFR-SEC-001` ve `NFR-SEC-009`
  davranışları korunmuştur; yeni ürün veya banka kontrolü iddiası oluşturulmadı.

### 2026-07-20 — İterasyon 19D: Kural onay isteği süre aşımı

- `FR-035`, `UC-005`, `RULE-001`, `RULE-007` ve `BFR-SOD-001/003/004` için kritik kural onay isteği süre aşımı alt kapsamı tamamlandı.
- Sürümlü politika hedefi 3, otomatik sona ermesi 10 iş günüdür; başlangıç istek oluşturma anıdır. Enjekte edilen sürümlü takvim hedef ve sona erme zamanlarını üretir.
- Süresi dolmuş istek onaylanamaz veya geri çekilemez. Yalnız güvenilir `SERVICE` context'i, politika rolü ve tüm dataset kapsamları doğrulandıktan sonra isteği `EXPIRED` yapabilir.
- Süre aşımı ve veri-minimum audit outbox atomiktir; audit-stage arızası durumu `PENDING` bırakır. Maker kimliği ve gerekçe audit özetine alınmaz.
- Aynı RuleVersion için tek bekleyen istek kuralı korunur; sona ermiş istek geçmişi silinmeden yeni onay isteği oluşturulabilir. Eski SQLite şeması kısmi benzersiz indekse veri kaybetmeden taşınır.
- Sekiz yeni testle kural hedef grubu 67, toplam test sayısı 710 oldu. Tam mypy 109 dosyada ve Ruff kontrolü hatasız geçti.
- Kanıt `08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19D-Kural-Onay-Sure-Asimi-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Gerçek banka tatil takvimi kaynağı, banka onaylı worker rolü, operasyonel zamanlama/alarm, veri kaynağı aktivasyonu ve legacy maker geçişi kapsam dışıdır; kurum onayları `ComplianceReviewRequired` kalır.

### 2026-07-20 — İterasyon 19E: Veri kaynağı aktivasyonu maker-checker

- `FR-010`, `FR-014`, `UC-002`, `UC-003`, `NFR-SEC-001` ve `BFR-SOD-001/002/003/004` için veri kaynağı aktivasyonu alt kapsamı tamamlandı.
- Kaynak aktivasyon isteği sürümlü politika, kaynak revizyonu ve güvenilir maker context'ine bağlandı; yalnız farklı checker rolü ve aynı source kapsamı onay verirse kaynak `ACTIVE` olur.
- Data Owner ve güncel başarılı bağlantı testi istek önkoşuludur. Ret, eski revizyon, eksik/süresi dolmuş context, yanlış rol/kapsam, servis hesabı ve ayrıcalıkla rol atlama kaynağı aktive etmez.
- Karar, kaynak durum geçişi ve veri-minimum audit outbox atomiktir; stage arızasında istek `PENDING`, kaynak `TEST_SUCCEEDED` kalır.
- SQLite veri kaynağı şeması revizyon ve tarihsel aktivasyon istekleriyle geriye uyumlu genişletildi; aktif kaynak mevcut keşif, kural ve execution önkoşullarında kabul edilir.
- 10 yeni testle veri kaynağı hedef grubu 47, toplam test sayısı 720 oldu. Tam mypy 109 dosyada ve Ruff kontrolü hatasız geçti.
- Kanıt `08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19E-Veri-Kaynagi-Aktivasyon-Maker-Checker-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Banka rol eşlemesi, kaynak kritiklik sözlüğü, bağlantı güncellemesinde revizyon artırma, pasife alma ve kaynak onay isteği geri çekme/süre aşımı açık; kurum onayları `ComplianceReviewRequired` kalır.

### 2026-07-21 — İterasyon 19F: Veri kaynağı onay geri çekme ve süre aşımı

- `FR-010`, `FR-014`, `UC-002`, `UC-003`, `NFR-SEC-001/008/011` ve `BFR-SOD-001/002/003/004` için kaynak aktivasyon onayı yaşam döngüsü tamamlandı.
- Yalnız kayıtlı maker bekleyen isteği geri çekebilir; kaynak `TEST_SUCCEEDED` kalır ve aynı revizyon için yeni istek oluşturulabilir.
- Hedef 3, otomatik sona erme 10 iş günüdür. Sürümlü ve enjekte edilen takvim zamanları istek anında üretir; süresi dolmuş istek karar veya geri çekmeye kapalıdır.
- Yalnız güvenilir `SERVICE` context'i, sürümlü worker rolü ve source kapsamı doğrulandıktan sonra isteği `EXPIRED` yapabilir.
- Geri çekme/süre aşımı ve veri-minimum audit outbox atomiktir; stage arızasında istek `PENDING` kalır. Legacy istek kayıtları nullable zaman alanlarına veri kaybetmeden taşınır.
- 11 yeni testle veri kaynağı hedef grubu 58, toplam test sayısı 731 oldu. Tam mypy 109 dosyada, Ruff ve derleme kontrolleri hatasız geçti.
- Kanıt `08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19F-Veri-Kaynagi-Onay-Geri-Cekme-Sure-Asimi-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Gerçek banka takvimi, maker/checker/worker rol eşlemesi ve üretim worker işletimi `ComplianceReviewRequired`; bağlantı güncellemesinde revizyon artırma/onay geçersizleştirme ve pasife alma açıktır.

### 2026-07-21 — İterasyon 19G: Bağlantı revizyonu ve onay geçersizleştirme

- `FR-008`, `FR-009`, `FR-012`, `UC-003`, `NFR-SEC-001/005/008/011`, `BFR-SOD-001/003/004` ve `BFR-AUD-004` için sürümlü bağlantı güncellemesi tamamlandı.
- Yetkili maker yeni ayarları mevcut çalışan sürüme dokunmadan değişmez aday revizyon olarak oluşturur; yalnız secret manager referansı saklanır.
- Başarısız sınıflandırılmış test çalışan yapılandırmayı, secret referansını, revizyonu, durumu, son başarılı testi ve eski bekleyen aktivasyon onayını korur.
- Beklenmeyen bağlayıcı arızası ayrı `TechnicalError` yolundadır ve aday `PENDING_TEST` kalır.
- Başarılı aday atomik olarak terfi eder, kaynak yeniden aktivasyon için `TEST_SUCCEEDED` olur ve eski revizyona bağlı bekleyen onay `INVALIDATED` durumuna geçer.
- Aday oluşturma ve terfi/onay invalidasyonu veri-minimum audit outbox ile atomiktir. Legacy kaynak/test kayıtları ilk revizyon geçmişine veri kaybetmeden taşınır.
- 13 yeni testle veri kaynağı hedef grubu 71, toplam test sayısı 744 oldu. Tam mypy 109 dosyada, Ruff ve derleme kontrolleri hatasız geçti.
- Kanıt `08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19G-Baglanti-Revizyonu-Onay-Gecersizlestirme-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Banka rol/LDAP eşlemesi, üretim migration/çoklu instance eşzamanlılığı ve kontrollü kaynak pasifleştirme açık kalır.

### 2026-07-21 — İterasyon 19H: Kontrollü kaynak pasifleştirme

- `FR-010`, `FR-036`, `FR-037`, `UC-002`, `UC-007`, `UC-008`, `NFR-SEC-001/008/011`, `BFR-SOD-001/003/004` ve `BFR-AUD-004` için kontrollü kaynak pasifleştirme dilimi tamamlandı.
- Güvenilir, geçerli, sürümlü deactivator rolüne ve source kapsamına sahip normal kullanıcı aktif kaynağı gerekçeli olarak `INACTIVE` yapabilir; yanlış rol/kapsam, servis hesabı ve ayrıcalıkla rol atlama fail-closed reddedilir.
- Manual ve scheduled execution yalnız `ACTIVE` kaynak kabul eder. Pasif kaynak yeni execution kaydı üretmez; zamanı gelen plan sınıflandırılmış teknik olayla pasifleştirilir.
- Pasifleştirme mevcut execution kayıtlarına dokunmaz. Pasif kaynağın yeniden aktivasyonu güncel başarılı test ve mevcut maker-checker akışıyla yapılır; ret pasif durumu korur.
- Kaynak durum geçişi ve veri-minimum audit outbox atomiktir; stage arızasında kaynak `ACTIVE` kalır. Audit özeti gerekçe, secret, bağlantı yapılandırması, owner veya aktör kimliği içermez.
- 6 yeni testle veri kaynağı ve execution hedef grupları 117, toplam test sayısı 750 oldu. Tam mypy 109 dosyada, Ruff, format ve derleme kontrolleri hatasız geçti.
- Kanıt `08-Uyum-Kanitlari/Guvenlik-Testleri/Iterasyon-19H-Kontrollu-Kaynak-Pasiflestirme-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Banka onaylı deactivator rolü/LDAP eşlemesi, çalışan işin tamamlanması veya iptali politikası, üretim eşzamanlılığı ve operasyon bildirimi açık kalır; arşivleme ayrı artımdır.

### 2026-07-21 — İterasyon 25A: Saklama politikası uygunluk değerlendirmesi

- `BFR-LCM-001/002`, `RULE-014`, `NFR-PRV-005`, `NFR-CMP-001/003`, `CTRL-KVKK-INV-001` ve `CTRL-KVKK-DEL-001` için salt okunur yaşam döngüsü dry-run dilimi tamamlandı.
- Kullanıcı karar paketindeki altı zaman bazlı kayıt sınıfı sürümlü `ComplianceReviewRequired` katalog olarak modellendi; yıllık süreler sabit gün sayısı yerine takvimsel hesaplanır ve periyodik imha üst aralığı 180 günle sınırlandırılır.
- Süresi dolmamış kayıt `RETAIN`, aktif legal hold altındaki kayıt `LEGAL_HOLD`, süresi dolmuş provisional kayıt `COMPLIANCE_REVIEW_REQUIRED` olur. Yalnız opak onay referanslı `ApprovedByBank` politika sentetik sözleşmede `ELIGIBLE_FOR_DISPOSAL` üretebilir.
- Legal hold resolver kesintisi teknik hata, eksik/geçersiz kayıt veya hold metadata'sı doğrulama hatasıdır. Değerlendirme yalnız opak referans ve yaşam döngüsü metadata'sı taşır.
- Fiziksel silme, anonimleştirme, arşivleme, geri çağırma ve auditli imha işi uygulanmadı; `CTRL-KVKK-DEL-001` bu nedenle `Partial` kaldı.
- 9 yeni testle toplam 759 test geçti. Tam mypy 114 dosyada, Ruff, format ve derleme kontrolleri hatasız geçti.
- Kanıt `08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-25A-Saklama-Politikasi-Uygunluk-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Hukuk/KVKK komitesi/iç denetim onayı, gerçek kayıt türü eşlemesi, kalıcı legal hold yaşam döngüsü, idempotent imha/audit, arşiv geri çağırma ve yedek re-delete açık kalır.

### 2026-07-21 — İterasyon 25B: Kalıcı legal hold yaşam döngüsü ve audit

- `BFR-LCM-002`, `BFR-AUD-001`–`BFR-AUD-004`, `BFR-SOD-002`, `FR-077`,
  `FR-079`, `NFR-SEC-001/008/011` ve `NFR-CMP-001/003` için append-only legal
  hold yaşam döngüsü tamamlandı.
- Hold oluşturma ve serbest bırakma ayrı `PLACED`/`RELEASED` olaylarıdır;
  SQLite tetikleyicileri geçmişte `UPDATE/DELETE` işlemlerini engeller ve
  resolver değerlendirme anındaki aktif hold'ları yeniden kurar.
- Güvenilir ve geçerli normal kullanıcı context'i, sürümlü rol/reason code
  politikası ve source/dataset/enterprise kapsamı zorunludur. Servis hesabı,
  break-glass, yanlış rol/kapsam ve oluşturan aktörle serbest bırakma reddedilir.
- Aynı kayıt birden fazla bağımsız hold taşıyabilir; yalnız tüm hold'lar
  kaldırıldığında 25A uygunluk değerlendirmesindeki legal hold engeli kalkar.
- Hold olayı ve redakte audit outbox atomiktir. Stage arızası domain olayını geri
  alır; merkezi publisher kesintisi domain kaydını koruyup audit olayını
  `PENDING` bırakır. Audit özeti ham kayıt, kapsam kimliği ve serbest metin taşımaz.
- 17 yeni testle retention hedef grubu 26, toplam test sayısı 776 oldu. Tam mypy
  116 dosyada, Ruff, format ve derleme kontrolleri hatasız geçti.
- Kanıt `08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-25B-Kalici-Legal-Hold-Yasam-Dongusu-Kaniti.md`
  içinde `TechnicallyVerified` olarak kaydedildi.
- Banka rol/reason code eşlemesi, üretim PostgreSQL/WORM yetkileri, çoklu süreç
  eşzamanlılığı, fiziksel imha, anonimleştirme, arşiv geri çağırma ve yedek
  re-delete açık kalır.

### 2026-07-21 — İterasyon 25C: İdempotent imha işi ve veri-minimum kanıt zarfı

- `BFR-LCM-002/003`, `BFR-AUD-004`, `BFR-SOD-002`, `FR-077`, `FR-079` ve
  `NFR-SEC-001/008/011` için append-only imha işi/sonuç kanıtı sözleşmesi
  tamamlandı.
- İş yalnız onay referanslı `ApprovedByBank` politika, süresi dolmuş kayıt ve
  aktif legal hold bulunmaması halinde hazırlanır; varsayılan provisional katalog
  fail-closed kalır.
- Idempotency anahtarı ile kayıt/kapsam kimlikleri özetlenir. Aynı anahtar/payload
  tek iş döndürür; farklı payload ve ikinci farklı terminal sonuç reddedilir.
- Hazırlayan güvenilir kullanıcı ile sonuç yazan güvenilir servis aktörü ayrı rol,
  aktör türü ve veri kapsamıyla doğrulanır; aynı kimlik iki adımı tamamlayamaz.
- `SUCCEEDED` ve `FAILED_TECHNICAL` ayrıdır. İş/sonuç ile redakte audit outbox
  atomiktir; tablolar `UPDATE/DELETE` işlemlerini reddeder ve ham silinen değer,
  kayıt/kapsam kimliği veya serbest hata metni taşımaz.
- 20 yeni testle retention hedef grubu 46, toplam test sayısı 796 oldu. Tam mypy
  119 dosyada, Ruff, format ve derleme kontrolleri hatasız geçti.
- Kanıt `08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-25C-Idempotent-Imha-Isi-Kanit-Zarfi.md`
  içinde `TechnicallyVerified` olarak kaydedildi.
- Fiziksel silme/anonimleştirme/arşivleme adaptörü, gerçek onay/kanıt resolver'ı,
  üretim claim/lease, banka rol/reason code eşlemesi, yedek re-delete ve arşiv
  geri çağırma açık kalır.

### 2026-07-21 — İterasyon 25D: Yetkili arşiv geri çağırma talep ve kararı

- `BFR-LCM-004`, `BFR-SOD-001/002/004`, `BFR-AUD-001/002/004`, `FR-077`,
  `FR-079` ve `NFR-SEC-001/008/011` için audit/kalite skoru arşiv geri çağırma
  talep ve karar sözleşmesi tamamlandı.
- Talep güvenilir normal kullanıcı, sürümlü requester rolü, veri kapsamı ve
  allowlist amaç kodu gerektirir; arşiv/kapsam kimlikleri özetlenir.
- Talebi açan aktör karar veremez. Farklı güvenilir normal kullanıcı, ayrı karar
  rolü, aynı kapsam ve allowlist gerekçeyle `APPROVED` veya `REJECTED` kararı verir.
- Talep idempotent, karar terminal ve her ikisi append-only'dir. Farklı payload
  veya ikinci farklı karar reddedilir; domain olayı ile redakte audit outbox
  atomiktir.
- Audit özeti yalnız durum, arşiv kayıt türü ve kapsam türünü taşır. Ham arşiv
  referansı, kapsam kimliği, idempotency anahtarı ve serbest metin içermez.
- 25 yeni testle retention hedef grubu 71, toplam test sayısı 821 oldu. Tam mypy
  122 dosyada, Ruff, format ve derleme kontrolleri hatasız geçti.
- Kanıt `08-Uyum-Kanitlari/Veri-Koruma/Iterasyon-25D-Yetkili-Arsiv-Geri-Cagirma-Kaniti.md`
  içinde `TechnicallyVerified` olarak kaydedildi.
- Gerçek arşiv deposu/getirme adaptörü, erişim süresi, indirme/DLP, üretim rol
  eşlemesi, PostgreSQL/WORM yetkileri ve geri çağrılan kopyanın yeniden imhası
  açık kalır.

### 2026-07-21 — İterasyon 27A: Fail-closed ortam kimliği

- `BFR-OPS-001/002`, `BRULE-004/005`, `NFR-SEC-005/008` ve `NFR-CMP-002`
  için sürümlü ortam başlangıç kapısı tamamlandı.
- Ortam kimliği yalnız `27A-trusted-source-v1` sözleşmeli sağlayıcıdan yüklenir;
  doğrudan konfigürasyon ve yanlış güven sözleşmesi kaynak okunmadan reddedilir.
- `LOCAL`, `DEVELOPMENT`, `TEST`, `ACCEPTANCE` ve `PRODUCTION` sınıfları ile
  ortama özgü secret kapsamı tanımlandı. Üretim dışı ortamda gerçek banka verisi
  ve üretim secret referansı fail-closed engellenir.
- Secret URI'si sıkı allowlist ile doğrulanır. Başlangıç kanıtı yalnız politika,
  revizyon, ortam, veri kökeni, secret kapsamı ve sabit kontrol kodlarını taşır;
  secret referansını taşımaz.
- Sağlayıcı arızası ayrı teknik hata olarak ele alınır; politika ihlali veya temiz
  başlangıç sonucuna dönüştürülmez.
- 34 yeni testle toplam test sayısı 855 oldu. Tam mypy 127 dosyada, Ruff lint,
  değişen dosya formatı ve derleme kontrolleri geçti. Tam depo format kontrolünde
  değişmeyen üç tarihsel dosyanın biçim farkı sürmektedir.
- Kanıt `08-Uyum-Kanitlari/Yedek-Geri-Yukleme/Iterasyon-27A-Fail-Closed-Ortam-Kimligi-Kaniti.md`
  içinde `TechnicallyVerified` olarak kaydedildi.
- Gerçek deployment/attestation sağlayıcısı, secret manager ve veri hazırlama
  kanıtı `OPEN-BNK-012`; yedek/restore/RTO/RPO/DR `OPEN-BNK-011` ile açık kalır.

### 2026-07-21 — İterasyon 31A: Sürümlü kaynak kullanım politikası ve güvenli kota çözümleme

- `FR-039`, `UC-008`, `RULE-012`, `NFR-PERF-006` ve `NFR-PERF-008` için
  sürümlü `SourceUsagePolicy` modeli ve SQLite politika deposu eklendi.
- Global politika ile kaynak türü/kaynak kimliği override kayıtları aynı modelde
  saklanır; çözümlemede kaynak kimliği kaynak türünden önce gelir.
- Aktif politika; eş zamanlı sorgu, worker, sorgu timeoutu, retry, hız sınırı,
  çalışma penceresi, CPU/IO, yoğun saat, iptal, onay ve audit referansı alanlarını
  taşır. Yeni aktif sürüm aynı kapsamdaki önceki sürümü `RETIRED` durumuna alır.
- Worker claim akışı çözümlenen toplam worker ve kaynak bazlı sorgu kotalarını
  uygular. Kalıcı çözümleyici kullanıldığında aktif global politika yoksa iş
  `QUEUED` durumunda kalır ve fail-closed doğrulama hatası üretilir.
- Politika depo arızası teknik hata olarak ayrılır. Üretim kota değerleri
  uydurulmadı; çalışma penceresi, CPU/IO, hız sınırı, timeout ve retry alanlarının
  çalışma zamanı uygulaması sonraki dilimlere bırakıldı.
- 8 yeni testle toplam test sayısı 863 oldu. Tam mypy 129 dosyada, Ruff,
  değişen dosya formatı ve derleme kontrolleri hatasız geçti.

### 2026-07-21 — İterasyon 31B: Kaynak çalışma penceresi ve yoğun saat koruması

- `FR-039`, `UC-008`, `RULE-012`, `RULE-015` ve `NFR-PERF-008` için kaynak
  çalışma pencereleri yapılandırılmış ve zamana bağlı claim kararına bağlandı.
- Her pencere IANA saat dilimi, ISO hafta günleri ve yerel başlangıç/bitiş saati
  taşır. Başlangıç dahil, bitiş hariç değerlendirilir; gece yarısını aşan
  pencerede başlangıç gününün politikası kullanılır.
- Yasaklı pencere izinli pencereye üstün gelir. İzin penceresi bulunmaması,
  pencere dışında kalınması veya UTC olmayan değerlendirme zamanı fail-closed
  davranır ve iş `QUEUED` durumunda kalır.
- Global karar kaynak türü veya kaynak kimliğiyle geçersiz kılınabilir; kaynak
  kimliği önceliği korunur. Uygun olmayan kuyruk başı, uygun başka kaynağın claim
  edilmesini engellemez.
- 8 yeni testle toplam test sayısı 871 oldu. Tam mypy 129 dosyada, Ruff,
  değişen dosya formatı ve derleme kontrolleri hatasız geçti.

### 2026-07-21 — İterasyon 31C: Kaynak politikası timeout ve retry yürütmesi

- `FR-039`, `FR-040`, `FR-041`, `UC-008`, `RULE-003`, `RULE-012`,
  `NFR-REL-001` ve `NFR-REL-002` için kaynak politikasındaki sorgu timeoutu,
  retry sayısı ve retry gecikmesi worker yürütmesine bağlandı.
- Worker claim ve yürütme kararları tek politika snapshot'ından üretilir. Birden
  fazla kaynaklı işte en düşük sorgu timeoutu ve retry sayısı ile en yüksek retry
  gecikmesi uygulanır.
- Yerel sorgu timeoutu ve maksimum deneme sayısı güvenli üst sınır, yerel retry
  gecikmesi güvenli alt sınır olarak korunur. Bağlantı ve toplam timeout değerleri
  bu dilimde değiştirilmedi.
- `retry_count` yeniden deneme sayısıdır; sıfır değeri ilk teknik hatadan sonra
  tekrar denemeyi engeller. Kalite başarısızlığı retry edilmez.
- 3 yeni testle toplam test sayısı 874 oldu. Tam mypy 129 dosyada, Ruff,
  değişen dosya formatı ve `compileall` kontrolleri hatasız geçti.

### 2026-07-21 — İterasyon 32A: Dataset kısmi skor politika kararı

- `FR-048`, `UC-009`, `OPEN-012` ve `OPEN-018` için sürümlü
  `DatasetPartialScorePolicy` modeli, SQLite deposu ve fail-closed değerlendirme
  servisi eklendi.
- Politika; dataset, resmî kısmi skor izni, kapsama, zorunlu kritik kurallar ve
  partitionlar, eksik kayıt/teknik hata üst sınırları, başarılı kural alt sınırı,
  sürüm, geçerlilik, onay ve audit referansını taşır.
- Yalnız geçerlilik anına ulaşmış `APPROVED` politika değerlendirmeye alınır.
  Politika yokluğu veya tek bir koşul ihlali `PROVISIONAL`; tüm koşulların
  sağlanması `OFFICIAL` kararı üretir.
- Politika hazırlayan ile onaylayan aynı olamaz. Değerlendirme teknik hata
  kural oranını kalite başarısızlığından ayrı tutar; karar yalnız oranlar ve opak
  kural/partition kimlikleri taşır.
- Execution kaydından güvenilir biçimde çıkarılamayan kapsama ve eksik kayıt
  oranları tahmin edilmedi; `PartialExecutionFacts` sözleşmesiyle dışarıdan
  ölçülmüş olgu olarak alınır. `QualityScore` entegrasyonu sonraki dilimdedir.
- 14 yeni testle toplam test sayısı 888 oldu. Tam mypy 131 dosyada, Ruff,
  değişen dosya formatı ve `compileall` kontrolleri hatasız geçti.

### 2026-07-21 — İterasyon 32B: Kısmi skorun resmî agregasyon zincirine bağlanması

- `FR-047`–`FR-050`, `FR-054`, `FR-055`, `FR-072` ve `UC-009` için kısmi
  skor politika kararı `QualityScore` üretimine bağlandı.
- Onaylı politika koşullarını sağlayan sonuç sayısal değer üretir, `PARTIAL`
  statüsünü korur ve dataset, boyut, kaynak ile kurum agregasyonuna resmî olarak
  katılır. Açıklama; kapsama, çalışan/çalışmayan kural sayısı, eksik partition,
  politika sürümü ve karar nedenlerini taşır.
- Politikasız veya koşulları sağlamayan kısmi sonuç provizyonel kalır; sayısal
  skor üretmez ve resmî agregasyon, dashboard trendi ile rapor önizlemesine
  katılmaz. Önceki resmî rapor sonucu yeni provizyonel kayıtla gölgelenmez.
- `NO_DATA` ve teknik hata gözlemleri sıfıra çevrilmeden görünür kalır. Politika
  depo hatası teknik hata olarak yükselir ve hiçbir skor yazılmaz.
- 7 yeni testle toplam test sayısı 895 oldu. Tam mypy 131 dosyada ve Ruff lint
  kontrolü hatasız geçti. Değişen kapsam format kontrolünden geçti; tam depo
  format kontrolünde değişmeyen üç tarihsel dosyanın biçim farkı sürmektedir.

### 2026-07-21 — İterasyon 32C: Kısmi skor politikası onay/ret ve atomik audit

- `FR-048`, `FR-077`, `UC-009`, `RULE-005`, `OPEN-012` ve `OPEN-017` için
  dataset kısmi skor politikasına güvenilir aktör bağlamlı yaşam döngüsü eklendi.
- Maker talebi `PENDING` oluşturur; yalnız farklı ve yetkili checker kararı
  `APPROVED` veya `REJECTED` durumuna taşır. Onaylanmayan politika etkili
  değerlendirmeye katılmaz.
- Rol, dataset kapsamı, aktör türü, bağlam geçerliliği ve politika sürümü
  varsayılan reddetme yaklaşımıyla kontrol edilir. Servis ve ayrıcalıklı aktör
  bağlamları politika onay akışında reddedilir.
- Talep ve karar, politika kaydıyla aynı SQLite transaction'ında merkezi audit
  outbox'a yazılır. Audit staging hatası işlemi geri alır; audit yalnız oran,
  adet, durum ve sürüm bilgisi taşır, kural/partition değerlerini taşımaz.
- 9 yeni testle toplam test sayısı 904 oldu. Tam mypy 131 dosyada, Ruff lint,
  değişen kapsam formatı, derleme ve `git diff --check` kontrolleri hatasız geçti.
  Tam depo format kontrolünde değişmeyen üç tarihsel dosyanın biçim farkı sürer.

### 2026-07-21 — İterasyon 32D: Kısmi skor politika talebini auditli geri çekme

- `FR-048`, `FR-077`, `UC-009`, `RULE-005`, `OPEN-012` ve `OPEN-017` için
  bekleyen dataset kısmi skor politika talebine güvenilir maker geri çekme akışı
  eklendi.
- Yalnız talebi oluşturan, güncel maker rolü ve dataset kapsamı bulunan normal
  kullanıcı `PENDING` talebi `WITHDRAWN` durumuna taşıyabilir. Başka maker,
  yanlış rol/kapsam, servis ve ayrıcalıklı bağlamlar fail-closed reddedilir.
- Geri çekme ile veri-minimum merkezi audit outbox kaydı aynı SQLite
  transaction'ında kalıcılaşır. Audit staging arızası politika durumunu ve önceki
  audit referansını geri alır.
- Geri çekilmiş politika etkili seçimde kullanılmaz. Audit yalnız oran, adet,
  durum ve sürüm taşır; kural/partition değerlerini, ham kayıt veya secret'ı
  taşımaz.
- 9 yeni test vakasıyla toplam test sayısı 913 oldu. Tam mypy 131 dosyada, Ruff
  lint, değişen kapsam formatı ve `compileall` kontrolleri hatasız geçti. Tam
  depo format kontrolünde değişmeyen üç tarihsel dosyanın biçim farkı sürer.

### 2026-07-21 — DQ-SCR skorlama kararlarının dokümantasyona uygulanması

- `DQ-SCR-001`–`DQ-SCR-033` kesin proje kararı olarak skorlama, kural yönetimi,
  dashboard, API, veri modeli, mimari, güvenlik/yönetişim, operasyon ve test
  belgelerine işlendi.
- Ham veri kalitesi skoru; kapsam, ölçüm güveni, dataset kritiklik profili/veri
  riski ve teknik sağlık göstergesinden ayrıldı. Skorun personel performans KPI'sı
  olmadığı bağlayıcı olarak kaydedildi.
- Kural paydası, sekiz standart ölçüm durumu, iki aşamalı kural → boyut → dataset
  agregasyonu, kritik kural veto/tavanı, sürümlü politika/model, istisna/override,
  trend sürüm sınırı, alarm/remediation ve yeniden üretilebilirlik sözleşmeleri
  tanımlandı.
- `ADR-015`, dataset kritikliğini `SOURCE` kalite skoruna ağırlık olarak katan
  tarihsel yaklaşımı hedef mimaride `Superseded` yaptı. Mevcut runtime bu hedefe
  henüz taşınmadı; geçmiş skorlar değiştirilmeyecektir.
- `AC-027`–`AC-038` ve `TS-027`–`TS-038` eklendi. Bu çalışma yalnız belge
  sözleşmesini günceller; yeni runtime davranışının teknik olarak doğrulandığı veya
  banka tarafından onaylandığı anlamına gelmez.

### 2026-07-21 — Skorlama ve ölçüm yeterliliği hedef tasarımı

- `RuleResult` için population, eligible, evaluated, passed, failed, excluded,
  technical-error ve unknown sayaçları ile üç değişmez eşitlik kanonikleştirildi.
- Kural → boyut → ham dataset skoru, kritik kontrol tavanlı nihai skor,
  `QualityStatus`, `CriticalRuleStatus`, `MeasurementQualificationStatus`,
  `UsageDecision` ve `ExecutionStatus` birbirinden ayrıldı.
- Ölçüm yeterliliği; kapsam, örneklem/güven, güncellik, teknik başarı, sürüm,
  kritik kontrol ve kanıt koşullarını bağımsız değerlendirir. Yüksek sayısal skor
  yetersiz veya eski ölçümü geçerli kılamaz.
- Gereksinim, kullanım senaryosu, veri modeli, API, dashboard/rapor/bildirim/issue,
  mimari, iş kuralları, operasyon, test ve izlenebilirlik belgeleri kanonik tasarıma
  bağlandı. `AC/TS-039`–`047` hedef kabul senaryolarıdır.
- Bu çalışma dokümantasyon ve hedef tasarım artımıdır. Mevcut runtime alanları ve
  formülleri henüz taşınmamıştır; üretim değerleri aktif sürümlü politikadan
  çözülecek, politika veya yetki eşlemesi yoksa olumlu karar verilmeyecektir.
- 39 değişen Markdown dosyasında yerel bağlantı, tablo sütunu ve whitespace
  kontrolleri geçti. 913 test, 131 dosyalık tam mypy, Ruff lint ve `compileall`
  geçti. `28A-v1` taraması 378 dosyada secret bulgusu üretmedi. Tam Ruff format
  kontrolünde değişiklik dışındaki üç tarihsel Python dosyasının mevcut biçim
  farkı sürmektedir.

### 2026-07-21 — Sentetik veri ve gizlilik hedef tasarımı

- `FR-088`–`FR-096`, `UC-017`, `RULE-016/017`, `NFR-PERF-010`,
  `NFR-PRV-007` ve `AC/TS-048–056` ile politika kontrollü sentetik veri hedef
  sözleşmesi oluşturuldu.
- Dokuz sentetik profil; şema/iş anlamı, dağılım/ilişki/zaman/eksiklik modeli,
  parametrik kusur enjeksiyonu, geçerli uç ayrımı, deterministik seed/run
  lineage'ı ve ayrı ground truth veri modeliyle tanımlandı.
- `ADR-016`, ground truth'u runtime kural/skor motorundan ve test olaylarını
  gerçek operasyon hedeflerinden ayırdı. Sentetik veri anonimlik kanıtı veya
  `OPEN-014` kapsamındaki nihai anonimleştirilmiş üretim örneği kabulünün yerine
  geçen kanıt sayılmadı.
- Tasarım runtime'a uygulanmadı. Nicel fayda/gizlilik/kusur yoğunluğu/skor
  toleransı aktif sentetik politikada zorunlu ve eksikse `BLOCKED`dır. Üretim
  profili/örneği erişimi varsayılan kapalıdır; yalnız ayrı kurumsal onaylı
  politikayla açılabilir.
- 35 değişen/yeni Markdown dosyasında yerel bağlantı, tablo sütunu ve
  `FR/UC/RULE/AC` süreklilik kontrolleri geçti. 913 test, 131 dosyalık tam mypy,
  Ruff lint ve `compileall` geçti; `28A-v1` taraması 381 dosyada secret bulgusu
  üretmedi. Tam Ruff format kontrolü değişiklik dışındaki üç tarihsel Python
  dosyasının mevcut biçim farkını raporlamaya devam etmektedir.

### 2026-07-21 — İterasyon 33A: Standart ölçüm durumları ve kural skoru paydası

- `FR-046`–`FR-048`, `UC-009`, `RULE-003/004`, `DQ-SCR-004`–`006` ve
  `AC-039/040` için sekiz kanonik `RuleResult` sayacı ile standart
  `MeasurementStatus` sözlüğü runtime'a eklendi.
- Sayaç değişmezleri worker ve skorlama sınırlarında doğrulanır. Kural skoru
  `PassedCount / EvaluatedCount * 100` formül sürümüyle hesaplanır; excluded,
  technical-error ve unknown kayıtlar paydaya girmez.
- Sıfır paydalı `NotApplicable`, `NotMeasured`, `NoData`, `TechnicalError` ve
  `SuppressedByException` sonuçları sayısal sıfıra çevrilmez. Ölçüm durumu,
  execution ve skor hesaplama durumundan ayrı kalıcılaştırılır.
- SQLite sonuç tabloları nullable kanonik sayaçlara geçirildi. Eski kayıtlar için
  bilinmeyen alanlar tahminî sıfırla doldurulmaz ve bu kayıtlar kanonik backfill
  olmadan yeniden skorlanmaz.
- 7 yeni test vakasıyla toplam test sayısı 920 oldu. Tam mypy 131 dosyada ve
  Ruff lint kontrolü hatasız geçti. Değişen kapsam formatlıdır; tam depo format
  kontrolünde değişiklik dışındaki bir tarihsel dosyanın biçim farkı sürer.
  `28A-v1` taraması 382 dosyada secret bulgusu üretmedi.

### 2026-07-21 — İterasyon 34A: Sentetik dataset politika, senaryo ve run kayıt çekirdeği

- `FR-088`, `FR-093`, `UC-017`, `RULE-016/017` ve `AC/TS-049`un politika,
  ayrı run ve lineage alt kapsamı için `SyntheticDatasetPolicy`,
  `SyntheticScenario` ve `SyntheticGenerationRun` kayıt çekirdeği runtime'a
  eklendi.
- Yalnız geçerlilik aralığındaki onaylı ve üretime izin veren tek politika
  çözümlenir. Politika yokluğu, süre sonu, izin eksikliği, birden fazla etkili
  politika veya senaryo/politika sürüm uyuşmazlığı fail-closed reddedilir.
- Run kaydı; senaryo, üretici, konfigürasyon, şema ve politika sürümlerini, seed'i,
  istenen hacmi ve çıktı/doğrulama referanslarını append-only saklar. Aynı lineage
  girdileriyle her talep ayrı run kimliği üretir.
- Run yazımı ile veri-minimum merkezi audit outbox kaydı aynı SQLite
  transaction'ında kalıcılaşır. Audit staging arızasında run geri alınır; audit
  özeti seed değerini, session bilgisini, ham kayıt veya secret taşımaz.
- 19 yeni test vakasıyla toplam test sayısı 939 oldu. Tam mypy 137 dosyada ve
  Ruff lint kontrolü hatasız geçti. Değişen kapsam formatlıdır; tam depo format
  kontrolünde değişiklik dışındaki bir tarihsel dosyanın biçim farkı sürer.
  `28A-v1` taraması 389 dosyada secret bulgusu üretmedi.

### 2026-07-21 — İterasyon 34B: Deterministik Golden ilişkisel üretici

- `FR-089`, `FR-090` temel yapay ilişki alt kapsamı, `FR-093`, `UC-017`,
  `RULE-016/017` ve `AC/TS-048/049` için tamamen yapay
  `GOLDEN_RELATIONAL_GENERATOR_V1` eklendi.
- Üretici yalnız kayıtlı run ile `GOLDEN`, `FUNCTIONAL_V1`, kusursuz,
  eksiksiz ve `FULLY_ARTIFICIAL_V1` senaryoyu kabul eder; üretim profili veya
  gerçek kaynak erişimi yoktur.
- Yapay subject/observation kayıtları benzersiz anahtar, yabancı anahtar,
  segment-durum ilişkisi, referans kodu, iki ondalıklı tutar ve sıralı zaman
  alanlarıyla üretilir. Şema ve konfigürasyon kodları yalnız teknik sentetik V1
  sözleşmesidir; banka iş anlamı veya üretim dağılımı iddiası taşımaz.
- Aynı seed ve sürümler farklı run kimlikleri altında byte eşdeğeri kanonik JSON
  ve aynı SHA-256 çıktı referansını üretir. Run kimliği digest kapsamına girmez;
  farklı seed farklı çıktı üretir.
- 9 yeni test vakasıyla toplam test sayısı 948 oldu. Tam mypy 139 dosyada, Ruff
  lint, `compileall`, değişen kapsam formatı ve güvenli SDLC taraması hatasız
  geçti. Tam depo format kontrolünde değişiklik dışındaki bir tarihsel dosyanın
  biçim farkı sürer; `28A-v1` taraması 391 dosyada secret bulgusu üretmedi.

### 2026-07-21 — İterasyon 34C: Değişmez Golden ground truth ve yapısal bağımsız karşılaştırıcı

- `FR-092`, `UC-017`, `RULE-016` ve `AC/TS-050–052`nin sıfır kusurlu Golden
  yapısal alt kapsamı için `GOLDEN_STRUCTURAL_ORACLE_V1` eklendi.
- Ground truth yalnız kayıtlı run ve senaryo sözleşmesinden kurulur; üreticinin
  `GoldenStructuralValidation` sonucu ve runtime kural/skor motoru kullanılmaz.
- Beklenen sayımlar, anahtar, ilişki, durum, referans ve zaman bütünlüğü ile
  gerçekleşen sonuç ayrı append-only kayıtlarda saklanır. Yapısal veya lineage
  sapması `BLOCKED`, repository/audit arızası teknik hata olarak ayrılır.
- Ground truth ve doğrulama sonucu merkezi audit outbox ile tek transaction'da
  yazılır. Güvenilir rol ve hem sunulan çıktı hem kayıtlı run dataset kapsamı
  doğrulanır; audit ham kayıt, seed, session veya skor toleransı taşımaz.
- 10 yeni test vakasıyla toplam test sayısı 958 oldu. Tam mypy 141 dosyada, Ruff
  lint, `compileall`, değişen kapsam formatı ve yerel secret taraması hatasız
  geçti. Tam depo format kontrolünde değişiklik dışındaki bir tarihsel dosyanın
  biçim farkı sürer; `28A-v1` taraması 393 dosyada secret bulgusu üretmedi.

### 2026-07-22 — İterasyon 34D: Kalıcı çıktı referansı ve append-only run tamamlama

- `FR-093`, `UC-017`, `RULE-016` ve `AC/TS-049` çıktı/doğrulama referansı alt
  kapsamı için `SyntheticRunFinalizationService` eklendi.
- Servis kanonik payload'ı kayıtlardan yeniden kurar; sunulan payload, SHA-256
  digest, çıktı referansı, run/senaryo lineage'ı ve bağımsız doğrulama kaydını
  birlikte doğrular. Uyuşmazlık kalite sonucu olarak değil doğrulama reddi olur.
- Özgün run talebi değişmez kalır. Terminal `COMPLETED`, `BLOCKED` veya
  `TECHNICAL_ERROR` kanıtı ayrı append-only completion kaydında; çıktı,
  doğrulama, saklama politikası ve audit referanslarıyla tutulur. Aynı kanıt
  idempotent, çelişen ikinci kanıt reddedilir.
- Completion ve merkezi audit outbox aynı transaction'da yazılır. Ham payload,
  seed, session ve digest değeri audit edilmez; fiziksel sentetik kayıt içeriği
  completion tablosunda saklanmaz.
- 12 yeni test vakasıyla toplam test sayısı 970 oldu. Tam mypy 144 dosyada,
  Ruff lint, `compileall`, `git diff --check` ve yerel secret taraması hatasız
  geçti. Tam depo format kontrolünde değişiklik dışındaki tarihsel
  `03-Backend/src/veri_kalitesi/__init__.py` biçim farkı sürer; `28A-v1`
  taraması 396 dosyada secret bulgusu üretmedi.

### 2026-07-22 — İterasyon 34E: Deterministik çok dönemli zaman semantiği

- `FR-090`, `FR-094`, `UC-017`, `RULE-016` ve `AC/TS-054` zaman semantiği alt
  kapsamı için `TEMPORAL_MULTI_PERIOD_GENERATOR_V1` eklendi.
- Append-only temporal profil; UTC başlangıcı, dönem sayısı/süresi ve olaydan
  kaynak oluşturma/güncelleme, ingestion, processing ve quality-check
  aşamalarına kadar açık gecikme girdilerini sürümler. Bunlar teknik test
  değerleridir; üretim SLA'sı veya banka eşiği değildir.
- Ayrı generator aynı profil/seed ile run kimliğinden bağımsız byte eşdeğeri
  kanonik çıktı üretir. `TemporalSemanticValidator` tüm dönemlerin temsilini,
  event zamanının beyan edilen döneme düşmesini, altı alanın UTC olmasını ve
  anlam sırasını üretim algoritmasından bağımsız doğrular.
- Yalnız tamamen yapay, kusursuz ve eksiksiz profil kabul edilir. Eksik/geçersiz
  profil doğrulama reddi; repository arızası teknik hata olur. Payload aktör,
  session, run kimliği, secret veya gerçek kurum verisi taşımaz.
- 17 yeni test vakasıyla toplam test sayısı 987 oldu. Tam mypy 146 dosyada,
  Ruff lint, `compileall`, `git diff --check` ve yerel secret taraması hatasız
  geçti. Tam depo format kontrolünde değişiklik dışındaki tarihsel
  `03-Backend/src/veri_kalitesi/__init__.py` biçim farkı sürer; `28A-v1`
  taraması 398 dosyada secret bulgusu üretmedi.

### 2026-07-22 — İterasyon 30B: Sentetik dashboard çalışma iskeleti

- `FR-054`, `FR-055`, `FR-058`, `UC-010` ve `NFR-USA-001/003–006` için
  üretim bağlantısı olmayan ilk gösterilebilir frontend artımı
  `04-Frontend/app/` altında kuruldu.
- React + TypeScript + Vite, MUI ve ECharts runtime'ı; Storybook ve Playwright
  doğrulama araçları tam sürüm pinleriyle kuruldu. `npm audit` 312 pakette
  bilinen zafiyet bildirmedi.
- Semantik token kaynağı, açık tema, responsive uygulama kabuğu, KPI kartı,
  durum rozeti, alarm akışı, resmî skor trendi ve aynı view-model'i kullanan
  erişilebilir tablo uygulandı. Teknik hata mor, kritik kalite ihlali kırmızı,
  operasyonel uyarı turuncudur; veri yok ve hesaplanmayan skor sıfır yapılmaz.
- Normal, loading, empty, teknik hata, yetkisiz ve uzun içerik Storybook
  durumları üretildi. 4 Vitest ve 7 Playwright testi geçti; beş zorunlu
  viewport'ta yatay taşma, grafik/tablo eşliği, provizyonel trend dışlama,
  görünür klavye odağı ve yetkisiz veri ifşa etmeme doğrulandı.
- İki görsel iyileştirme turunda 1200px üzeri yoğun grid, grafik eşik etiketi,
  alarm satırı hizası, teknik hata semantiği ve MUI focus halkası düzeltildi.
- Frontend type-check, üretim build'i, Storybook build'i ve `npm audit` geçti;
  `npm audit` sıfır bilinen zafiyet bildirdi. Mevcut 987 Python testi, 146
  dosyalık mypy ve Ruff kontrolleri de korundu; `28A-v1` 429 kaynak dosyada
  secret bulgusu üretmedi. Vite üretim build'i ilk bundle için 500 kB uyarısı
  vermektedir; route/vendor code splitting ve performans bütçesi açık teknik
  iyileştirmedir.
- Ekran yalnız sentetik fixture kullanır ve bunu görünür biçimde belirtir.
  Üretim API'si, gerçek IdP/oturum, banka verisi, dışa aktarma ve yetkili
  drill-down uygulanmadı; 21B/geçiş kapısı bağımlılığı korunur.

### 2026-07-22 — İterasyon 33B: Kritiklikten ayrılmış kaynak kalite skoru

- `R-04`, `FR-050`, `FR-052`, `UC-009`, `DQ-SCR-018`, `DQ-SCR-025` ve
  `AC/TS-030/037` kapsamında yeni `SOURCE` kalite agregasyonu düzeltildi.
- `SOURCE_EQUAL_DATASET_QUALITY_V2`, resmî dataset skorlarını eşit kalite
  ağırlığıyla toplar; dataset kritikliği kalite formülüne girmez ve açıklamada
  ayrı profil olarak taşınır.
- Eski `SOURCE_WEIGHTED_V1` skorları değişmeden korunur. Aynı tarihsel execution
  yeniden çağrıldığında mevcut skorun kimliği, değeri ve formül sürümü
  değiştirilmez.
- `R-04` kısmen tamamlandı: yanlış kaynak kritiklik ağırlıklandırması giderildi;
  ham/nihai skorun tam runtime modeli, ayrı risk/güven/yeterlilik/kullanım
  sonuçları ve yeni model replay/backfill akışı açık kaldı.
- 988 test, 146 dosyalık tam mypy, Ruff, `compileall`, `git diff --check` ve
  429 dosyalık `28A-v1` secret taraması hatasız tamamlandı.

## İlgili Notlar

### 2026-07-22 — Açık karar kayıtlarının ayrıştırılması

- `OPEN-001`–`OPEN-018` kesinleşmiş kararları SRS açık konu tablosundan
  çıkarıldı; karar belgesindeki kanonik tablo korunmuştur.
- `OPEN-BNK-003/004/005/006/007/010/012/014/015/016/017/020` teknik yönleri
  `KararAlındı`, `OPEN-BNK-021` ise `KararAlındı` durumuyla bankacılık
  geçiş teknik yön kararları tablosuna taşındı. Bu işlem banka onayı üretmez.
- Bankacılık açık tablosunda yalnız `OPEN-BNK-001/002/008/009/011/013/018/019`
  kaldı. Cron, şema değişikliği ve `QualityDimension` için alınmış kararların
  bekleyen uygulama işleri `Sonraki-Adimlar.md` içinde korunmuştur.

### OPEN-001–OPEN-018 Dokümantasyon Uyumlaştırması

- Kapasite, kaynak kullanım politikası, kurumsal secret manager, IdP/SSO/MFA, kayıt sınıfı bazlı saklama, bileşen bazlı RPO/RTO, ServiceNow ara entegrasyonu, katalog/DLP sınıflandırması, katmanlı rapor saklama, risk bazlı maker-checker, bağlayıcı sırası, anonimleştirilmiş performans verisi, WCAG 2.2 AA, hibrit dağıtım, hibrit audit ve dataset kontrollü kısmi skor kararları SRS, veri modeli, mimari, operasyon ve test belgelerine işlendi.
- `OPEN-001`–`OPEN-018` karar yönleri `Karara bağlandı` durumuna alındı. Ürün yönleri ve teknik saklama/RPO/RTO değerleri kaydedildi; ortama göre değişen kapasite, kota, timeout ve dosya boyutu değerlerinde aktif sürümlü politika zorunlu kılındı.
- 57 değişen Markdown dosyasında yerel bağlantı ve tablo yapısı kontrolü; 855 test, 127 dosyalık tam mypy, Ruff ve derleme kontrolleri geçti.
- Bu çalışma dokümantasyon sözleşmesini günceller; yeni runtime davranışının uygulanmış veya banka tarafından onaylanmış olduğu anlamına gelmez.

### 2026-07-22 — Karar durumlarının kesinleştirilmesi ve OPEN-BNK-020 banka onayı

- Tüm geçici karar ve belirsiz değer yer tutucuları kaldırıldı. Teknik yönü
  seçilmiş kayıtlar `KararAlındı` durumuna taşındı; ortama göre değişen değerler
  aktif, sürümlü ve gerekli onayı taşıyan politikadan çözülür, politika yoksa
  sistem fail-closed davranır.
- Saklama matrisi ile normal `RPO=PT15M`, `RTO=PT4H` ve kritik
  `RPO=PT5M`, `RTO=PT1H` hedefleri gereksinim, veri modeli ve operasyon
  belgelerinde karar olarak kaydedildi.
- `OPEN-BNK-020`, `USER-DECLARATION-2026-07-22-OPEN-BNK-020` referansıyla
  `ApprovedByBank` durumuna alındı. BFF, tek aktif oturum, `PT1H` idle,
  `PT10H` mutlak süre, `__Host-session`, synchronizer-token CSRF, merkezi iptal
  ve `P90D` güvenlik metadatası gereksinim ve mimari sözleşmelerine işlendi.
- Bu dokümantasyon kaydı sırasında runtime 30 dakikalık idle tabanını
  kullanmaktaydı; süre ve tek aktif oturum alt kapsamı daha sonra 20D ile
  uygulandı. Onaylı politikanın HTTP/BFF katmanında uygulanması, yüksek
  erişilebilir üretim deposu, at-rest şifreleme/KMS-HSM ve fiziksel saklama/imha
  kanıtı açık uygulama işleridir.
- 988 Python testi, 146 dosyalık mypy, Ruff lint, `compileall`, 4 frontend birim
  testi, frontend type-check ve üretim build'i geçti. 429 dosyalık `28A-v1`
  secret taraması temizdir; yerel Markdown bağlantıları ve karar işareti taraması
  hatasızdır. Frontend build'inde mevcut 500 kB chunk uyarısı sürmektedir.
- Bu kayıtta tam `ruff format --check`, dokümantasyon değişikliğinin dışında kalan
  `03-Backend/src/veri_kalitesi/__init__.py` dosyasında mevcut tek biçim farkını
  raporlamıştı; biçim farkı 20D kapsamında giderildi.

### 2026-07-22 — İterasyon 20D: Banka onaylı oturum runtime politikası

- `OPEN-BNK-020` banka onayının domain/runtime alt kapsamı uygulandı: sürümlü
  oturum politikası en fazla `PT1H` hareketsizlik ve `PT10H` mutlak süreyi
  zorunlu kılar; daha sıkı değerler desteklenir.
- Kullanıcı başına tek aktif normal oturum depo transaction'ında uygulanır. Yeni
  başarılı giriş aynı kullanıcıya ait önceki aktif oturumu `NEW_SUCCESSFUL_LOGIN`
  nedeniyle iptal eder ve yeni oturumu atomik olarak kaydeder.
- Oturum sona erdiğinde credential özeti terminal güvenlik metadatasından
  ayrılarak silinir. Eski SQLite şeması nullable credential alanına açılışta
  taşınır; uygulama servisi somut SQLite sınıfı yerine `SessionRepository`
  protokolüne bağlıdır.
- Arka plan istekleri ve token yenileme doğrulaması boşta kalma zamanını
  uzatmaz; yalnız güvenilir kullanıcı etkileşimi aktivite zamanını yeniler.
- Kimlik hedefinde 47, tam depoda 993 test geçti. 146 dosyalık Ruff format,
  Ruff lint ve tam mypy, `compileall` ve `git diff --check`
  kontrolleri hatasızdır. `28A-v1` 430 dosyada secret bulgusu üretmedi.
- HTTP/BFF cookie ve CSRF adaptörü, kullanıcı/rol/olay kaynaklı merkezi iptal
  girişleri, yüksek erişilebilir üretim session store'u, at-rest şifreleme ile
  KMS/HSM bağlantısı ve `P90D` fiziksel saklama/imha kanıtı açık uygulama
  kapsamıdır.

- [Alınan Kararlar](Alinan-Kararlar.md)
- [Açık Konular](Acik-Konular.md)
- [Sonraki Adımlar](Sonraki-Adimlar.md)

## Bankacılık Geçiş Baseline'ı

- Mevcut 16 iterasyon, Iterasyon 17A–17E, Iterasyon 18A–18C, Iterasyon 19A–19H, Iterasyon 20A–20D, Iterasyon 21A, Iterasyon 22A–22I, Iterasyon 23A–23D, Iterasyon 24A–24B, Iterasyon 25A–25D, Iterasyon 26A–26B, Iterasyon 27A, Iterasyon 28A–28E, Iterasyon 29A–29C, Bakım İterasyonu 29C.1, İterasyon 30A–30B, İterasyon 31A–31C, İterasyon 32A–32D, İterasyon 33A–33B ve İterasyon 34A–34E çıktıları korunacaktır.
- `pytest` ile 993 testin geçtiği doğrulanmıştır.
- Tam mypy kontrolü 146 kaynak dosyada sıfır hata vermektedir.
- Kısmi politika maker-checker onay/ret, geri çekme ve atomik audit akışı 32D ile tamamlandı. Süre aşımı açık kalır; güvenilir `PartialExecutionFacts` üretimi kapsama ve eksik kayıt oranı formüllerini beklemektedir. 31D hız sınırı sayaç/pencere semantiğini; CPU/IO sınırları güvenilir kaynak ölçüm adaptörünü beklemektedir. 27B restore tatbikat kanıtı `OPEN-BNK-011` ve `OPEN-BNK-012` kararlarını bekler; gerçek arşiv/fiziksel imha adaptörü, 29D, 21B/frontend, hassas dışa aktarma ve gerçek SIEM de banka/altyapı kararlarına bağlıdır.
- Geçiş ayrıntıları için [Bankacılık Geçiş Durumu](Bankacilik-Gecis-Durumu.md) esas alınır.
- Bu kayıt bir mevzuat uyumluluğu onayı değildir.

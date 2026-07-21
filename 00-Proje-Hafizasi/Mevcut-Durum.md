---
type: project-memory
status: draft
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-21
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
- 87 fonksiyonel gereksinim.
- 16 kullanım senaryosu.
- 15 iş kuralı.
- 19 temel veri varlığı.
- 11 fonksiyonel olmayan gereksinim kategorisi.
- 26 sistem kabul kriteri.

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
- Sürümlü politika 30 dakikalık azami idle timeout ve enjekte edilen mutlak süreyi uygular. Aktivite idle zamanını yeniler fakat mutlak süreyi uzatmaz.
- Yüksek entropili credential yalnız bir kez döndürülür; SQLite yalnız SHA-256 özetini ve context'i yeniden üretmek için gerekli veri-minimum yetki alanlarını saklar.
- Doğrulama son aktiviteyi kalıcı günceller; timeout `EXPIRED`, çıkış `REVOKED` olur ve credential yeniden kullanılamaz. Tarihsel kayıt fiziksel silinmez.
- Güvenilmez/süresi dolmuş context, servis hesabı, ayrıcalıklı kullanıcı, değiştirilmiş credential ve session depo/audit arızası fail-closed reddedilir.
- On yedi yeni testle toplam 254 test geçti; kimlik hedef grubu 42 testle geçti. Kanıt `08-Uyum-Kanitlari/Erisim/Iterasyon-20C-Guvenli-Oturum-Yasam-Dongusu-Kaniti.md` içinde `TechnicallyVerified` kaydedildi.
- Lint, değişen dosyalarda format, `python3` derleme ve tüm testler geçti. Tam depo format kontrolünde değişmeyen dört eski dosyanın biçim farkı sürüyor.
- HTTP cookie/token/CSRF sınırı, eş zamanlı oturum limiti, mutlak süre, üretim deposu/şifreleme ve saklama süresi `ComplianceReviewRequired` durumundadır.
- Depo dizininde `.git` bulunmadığı için commit oluşturulmadı; değişiklikler küçük ve tek commit kapsamına uygundur.

### 2026-07-17 — İterasyon 21A: Yetki filtreli dashboard trend domain sorgusu

- `FR-054`, `FR-055`, `FR-057`, `UC-010`, `NFR-PERF-001` ve `NFR-PERF-002` gereksinimlerinin son 30 günlük trend domain alt kapsamı tamamlandı.
- Dashboard servisi yalnız güvenilir `ActorContext` üzerinden üretilen kaynak/kurum görünürlük kararını kullanarak 30 UTC takvim günlük sabit pencereyi sorgular.
- SQLite sorgusu zaman ve yetki kapsamını parametreli SQL içinde uygular; servis sonucu ayrıca savunmacı olarak yeniden filtreler. Kurum gözlemleri yalnız açık kurum yetkisiyle döner.
- Eksik günler boş gözlem listesi olarak kalır; `NO_DATA` sayısal sıfıra dönüştürülmez. Depo arızası kalite başarısızlığı yerine redakte `DashboardQueryError` üretir.
- Saat dilimsiz saat ve gözlem damgaları reddedilir. Son 30 gün için 500 sentetik gözlemle yerel p95 koruması üç saniyenin altında geçti.
- On bir yeni testle toplam 265 test geçti; dashboard hedef grubu 29 testle geçti. Kanıt `08-Uyum-Kanitlari/Erisim/Iterasyon-21A-Yetki-Filtreli-Dashboard-Trend-Kaniti.md` içinde `TechnicallyVerified` olarak kaydedildi.
- Lint, değişen dosyalarda format, `python3` derleme ve tüm testler geçti. Tam depo format kontrolünde değişmeyen dört eski dosyanın biçim farkı sürüyor.
- Serbest tarih aralığı/periyot seçimi, operasyon listeleri, grafik/tablo sunumu ve HTTP/cookie yüzeyi kapsam dışıdır; 21B geçiş kapısı ve `OPEN-BNK-020` nedeniyle engellidir.
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
- Storybook component durumları ve Playwright ekran görüntüsü süreci frontend
  Definition of Done'a eklendi; araçlar proje bağımlılığı olarak henüz kurulmadı.
- İlk uygulanacak görsel ekran kurumsal dashboard olarak belirlendi. Uygulama 21B
  güvenli HTTP/API sınırı, bankacılık geçiş kapısı ve frontend toolchain onayına bağlıdır.
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

## İlgili Notlar

- [Alınan Kararlar](Alinan-Kararlar.md)
- [Açık Konular](Acik-Konular.md)
- [Sonraki Adımlar](Sonraki-Adimlar.md)

## Bankacılık Geçiş Baseline'ı

- Mevcut 16 iterasyon, Iterasyon 17A–17E, Iterasyon 18A–18C, Iterasyon 19A–19H, Iterasyon 20A–20C, Iterasyon 21A, Iterasyon 22A–22I, Iterasyon 23A–23D, Iterasyon 24A–24B, Iterasyon 25A–25B, Iterasyon 26A–26B, Iterasyon 28A–28E, Iterasyon 29A–29C ve Bakım İterasyonu 29C.1 çıktıları korunacaktır.
- `pytest` ile 776 testin geçtiği doğrulanmıştır.
- Tam mypy kontrolü 116 kaynak dosyada sıfır hata vermektedir.
- Sıradaki teknik aday 25C idempotent imha işi ve veri-minimum kanıt zarfı sözleşmesidir. Fiziksel imha adaptörü, arşiv geri çağırma, 29D, 21B/frontend, hassas dışa aktarma, DR ve gerçek SIEM banka/altyapı kararlarını beklemektedir.
- Geçiş ayrıntıları için [Bankacılık Geçiş Durumu](Bankacilik-Gecis-Durumu.md) esas alınır.
- Bu kayıt bir mevzuat uyumluluğu onayı değildir.

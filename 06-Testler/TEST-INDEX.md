---
type: implementation-index
area: testing
project: Veri Kalitesi İzleme ve Skorlama Sistemi
created_at: 2026-07-16
tags:
  - testing
  - index
---

# Test Haritası

## Ana Kaynaklar

- [Test Ajan Talimatları](AGENTS.md)
- [Sistem Kabul Kriterleri](../01-SRS/10-Kabul-Kriterleri.md)
- [Kullanım Senaryoları](../01-SRS/05-Kullanim-Senaryolari/INDEX.md)
- [İzlenebilirlik Matrisi](../01-SRS/11-Izlenebilirlik-Matrisi.md)
- [NFR Doğrulama Yöntemleri](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/INDEX.md)
- [SRS Kalite Kontrolü](../01-SRS/16-Kalite-Kontrolu.md)
- [Frontend Görsel Doğrulama Stratejisi](03-Uctan-Uca/Gorsel-Dogrulama-Stratejisi.md)
- [Skorlama ve Ölçüm Yeterliliği Kanonik Tasarımı](../02-Mimari/Veri-Kalitesi-Skorlama-ve-Olcum-Yeterliligi.md)
- [Sentetik Veri ve Gizlilik Stratejisi](../02-Mimari/Sentetik-Veri-ve-Gizlilik-Stratejisi.md)
- [Kanıta Dayalı Karar Sistemi](../02-Mimari/Kanita-Dayali-Karar-Sistemi.md)

## Önerilen Test Katmanları

1. Skor formülleri, RBAC, durum geçişleri ve idempotency için birim testleri.
2. Ürün bağımsız bağlayıcı, kurumsal IdP/SSO-MFA, secret manager, katalog/DLP, kuyruk ve depolama sözleşme/entegrasyon testleri.
3. UC-001–UC-021 uçtan uca senaryoları.
4. Veri sahibi onaylı, anonimleştirme ve yeniden kimliklendirme risk değerlendirmesi bulunan 20 milyon satırlık üretim örneğiyle tekrarlanabilir profil ve kural testleri.
5. Salt okunurluk, SQL injection, XSS/CSRF, secret ve audit bütünlüğü güvenlik testleri.
6. Yedek geri yükleme ve felaket kurtarma tatbikatı.
7. Storybook component durumları ve Playwright responsive/görsel regression testleri.
8. WCAG 2.2 AA için otomatik kontrole ek manuel klavye ve ekran okuyucu testleri.
9. Karar desteği için formül/kanıt bağlama, manifest ile yeniden üretim,
   nedensellik sınırı, politika kontrollü remediation ve chaos izolasyon testleri.

36H2 kalıcı iş yaşam döngüsü kanıtı
`01-Birim/test_job_queue.py`, `01-Birim/test_persistent_job_worker.py`,
`01-Birim/test_persistent_job_handlers.py`, `01-Birim/test_source_usage_policies.py` ve
`02-Entegrasyon/test_postgresql_job_queue.py` dosyalarındadır. 2026-07-29
controller kapısı tüm birim paketinde `1172 passed`; etkilenen data source ve
job queue PostgreSQL dosyalarında skip olmadan `41 passed` sonucu vermiş,
reviewer `APPROVED` kararıyla kapanmıştır.

ENTERPRISE-LAB-01 fail-closed ortam kapısı ve production/gerçek veri/overclaim
ile endpoint rol eşleşmesi negatifleri `01-Birim/test_enterprise_lab.py`
dosyasındadır. ENTERPRISE-LAB-02 Keycloak, secret manager, fake ServiceNow ve
SIEM uygulama adaptörlerinin veri-minimum/idempotent ve bağlantı/yetki/secret/
audit aktarım fail-closed negatifleri
`01-Birim/test_enterprise_lab_adapters.py` dosyasındadır (iki hedef dosyada
`24 passed`).
ENTERPRISE-LAB-03 canlı Compose kapısı sekiz healthy servis ve gerçek container
ağında 14 Keycloak/secret manager/ServiceNow/SIEM olumlu-negatif adapter
senaryosunu kapsar. Kesinti, yetki reddi, timeout, 429 ve hatalı payload/yanıt
sonrası fail-closed toparlanma ile log redaksiyonu doğrulanmıştır. Sonuç yalnız
`PrototypeVerified`dır; [manifest](../08-Uyum-Kanitlari/Guvenlik-Testleri/ENTERPRISE-LAB-03-Kanit-Manifesti.json)
production veya banka onayı değildir.

DQ-CAP-PROTOTYPE-01 hedef testleri
`01-Birim/test_data_sources.py`, `01-Birim/test_profile_analysis.py`,
`01-Birim/test_postgresql_data_source_repository.py` ve
`01-Birim/test_data_source_api.py` içindedir. Top-N/dağılım/sayısal özet,
IQR/robust-z adayları, hassas değer maskelemesi, yedi drift ailesi, politika
ve fingerprint secret/configuration yokluğunda hükümsüz sonuç, restart sonrası
kararlı fingerprint, bounded deterministik CSV örneği ve API/repository
sözleşmesi hedefli kapıda güncel controller kapısında skipsiz exit `0`;
implementer profil/data-source koşusunda `92 passed`, API koşusunda `8 passed`
vermiştir. PostgreSQL migration/repository ve gerçek source-aggregate
entegrasyon senaryoları
`02-Entegrasyon/test_postgresql_data_source_persistence.py` içindedir. Güncel
controller PostgreSQL kapısı skipsiz exit `0`; implementer hedefli koşusu
skipsiz `14 passed`, exit `0` vermiştir. Güncel kapsam CSV ve PostgreSQL profil
üretiminden snapshot karşılaştırmasına policy kapsam içi/dışı güncellik
kanıtını; PostgreSQL için salt-okunur `MAX(...)` aggregate davranışını içerir.

## Kesinleşen Kararların Doğrulama Kapsamı

| Karar grubu | Zorunlu senaryo |
| --- | --- |
| OPEN-001 | Düşük/beklenen/yüksek kapasite senaryosu ve üretim envanteri geçiş kontrolü |
| OPEN-002–003 | Kaynak politikasının global varsayılanı geçersiz kılması; politika yokluğunda güvenli ret; kota/pencere/timeout/iptal |
| OPEN-004–006 | Secret rotasyonu/audit; SSO+MFA olumlu ve eksik/başarısız/IdP kesintisi negatif akışları |
| OPEN-007–008, OPEN-011 | Kayıt sınıfı saklama, katmanlı rapor arşiv/imha ve bileşen bazlı restore hedefleri |
| OPEN-009 | ServiceNow kesintisi, idempotency, backoff, dead-letter ve yerel kaydın korunması |
| OPEN-010 | Katalog/DLP kesintisinde bilinen hassas sınıfın düşürülmemesi; rapor/log/erişim kısıtları |
| OPEN-012 | Yüksek riskli değişiklikte görevler ayrılığı; düşük riskli taslakta yetkili tek kullanıcı |
| OPEN-013–014 | Bağlayıcı ortak sözleşmesi ve güvenlik kontrollü 20 milyon satır testi |
| OPEN-015–016 | WCAG manuel/otomatik kontrolleri; bağımsız API/worker ölçekleme, sağlık ve kontrollü kapatma |
| OPEN-017 | Kritik işlem audit arızasında fail-closed; rutin outbox kesintisinde kayıpsız retry/alarm |
| OPEN-018 | Politika koşullarının tamamında kısmi resmî skor; her eksik koşul ve politika yokluğunda provizyonel dışlama |

## DQ-SCR Doğrulama Kapsamı

| Karar grubu | Zorunlu test kapsamı |
| --- | --- |
| `DQ-SCR-001`–`DQ-SCR-006` | Amaç/KPI metni, payda ve sayaç eşitlikleri, sekiz ayrı ölçüm durumu, teknik hata/son başarılı skor eskiliği |
| `DQ-SCR-007`–`DQ-SCR-013` | Tamlık koşulları, geçerlilik türleri/sürümleri, otoriter doğruluk, mutabakat toleransı, kesin/olası duplicate, güncellik politikası ve ölçüm türü normalizasyonu |
| `DQ-SCR-014`–`DQ-SCR-017` | Sürümlü eşik/ağırlık, iki aşamalı agregasyon, `NotApplicable` dağıtımı, kritik kural veto/tavan/alarm/blokajı |
| `DQ-SCR-018`–`DQ-SCR-021` | Kritikliğin kalite skoruna katılmaması; kalite, kapsam, güven, risk ve teknik sağlığın ayrı API/UI alanları |
| `DQ-SCR-022`, `DQ-SCR-023`, `DQ-SCR-030` | Süreli istisna/override, maker-checker, yetkisiz/servis/ayrıcalıklı negatifleri, audit rollback, ham skor değişmezliği ve anti-gaming işlemleri |
| `DQ-SCR-024`–`DQ-SCR-027`, `DQ-SCR-032` | Kural yaşam döngüsü/backtest, tüm sürüm referansları, açıklama drill-down'ı, trend sürüm sınırı, replay/idempotency ve orijinal skor koruması |
| `DQ-SCR-028`, `DQ-SCR-029` | Teknik/kalite alarm ayrımı, korelasyon, risk bazlı atama/SLA ve kanıtsız/geçici iyileşmeyle kapatma reddi |
| `DQ-SCR-031` | Tam tarama, kaynakta toplulaştırma, bölümleme, artımlı kontrol ve kontrollü örneklemede yöntem/hacim/güven kanıtı |
| `DQ-SCR-033` | Yetki matrisi, görevler ayrılığı, veri sahibi/teknik sahip/operasyon sorumluluk sınırları |

## Ölçüm Yeterliliği Kabul Matrisi

| Kabul/Test | Zorunlu test kapsamı |
| --- | --- |
| `AC/TS-039` | Tüm sayaç değişmezleri, sıfır payda ve tutarsız sayaç reddi |
| `AC/TS-040` | Koşullu kural evreninde uygun, dışlanan ve bilinmeyen kayıt ayrımı |
| `AC/TS-041` | Kural → boyut → ham dataset skoru; uygulanamaz bileşen dağıtımı |
| `AC/TS-042` | Kritik tavan/blokaj; ham, nihai, kritik durum ve kullanım kararının ayrılığı |
| `AC/TS-043` | Sekiz yeterlilik durumu, değerlendirme önceliği ve yüksek skor negatifleri |
| `AC/TS-044` | Tam tarama/örneklem/bölümleme/toplulaştırma kanıtı, kapsam, güven ve eskime |
| `AC/TS-045` | Teknik başarısızlık, önceki skor fallback'i ve resmî trend dışlama |
| `AC/TS-046` | Replay, sürüm izlenebilirliği, RBAC/scope, maskeleme, veri-minimum audit ve hata |
| `AC/TS-047` | Bildirim, idempotent remediation, yeniden ölçüm ve kanıtlı kapanış |

## Sentetik Veri Kabul Matrisi

| Kabul/Test | Zorunlu test kapsamı |
| --- | --- |
| `AC/TS-048` | Golden şema, tip, zorunlu alan, anahtar, referans ve durum geçişi bütünlüğü |
| `AC/TS-049` | Aynı seed/sürümle kanonik eşdeğer çıktı; ayrı run ve eksiksiz lineage |
| `AC/TS-050` | Boyut/kural bağlı kusur enjeksiyonu, yoğunluk sınıfları ve bağımsız ground truth |
| `AC/TS-051` | Geçerli nadir/sınır değer false-positive negatifleri ve gerçek kusur yakalama |
| `AC/TS-052` | Runtime'dan bağımsız skor oracle'ı; kural, önem, bildirim ve eskalasyon sapması |
| `AC/TS-053` | Birebir/yakın eşleşme, nadir kombinasyon, çıkarım/bağlantı riski ve fail-closed ortam kapısı |
| `AC/TS-054` | Zaman alanı anlamları, eksiklik mekanizmaları, trend, sezonsallık ve drift |
| `AC/TS-055` | Fake/sandbox olay yaşam döngüsü ve üretim hedefi fail-closed negatifleri |
| `AC/TS-056` | Hacim, timeout/kota teknik hata ayrımı, yaşam döngüsü, imha, replay ve `OPEN-014` kabul ayrımı |

İterasyon 34A politika, ayrı run ve lineage kanıtı
`06-Testler/01-Birim/test_synthetic_data.py`; İterasyon 34B Golden yapısal
bütünlük ve kanonik replay kanıtı
`06-Testler/01-Birim/test_synthetic_generator.py`; İterasyon 34C değişmez Golden
ground truth, bağımsız yapısal karşılaştırma, yetki ve atomik audit kanıtı
`06-Testler/01-Birim/test_synthetic_oracle.py`; İterasyon 34D kalıcı çıktı ve
doğrulama referansı, append-only terminal run kanıtı, manipülasyon redleri ve
atomik audit kanıtı aynı dosyadadır. İterasyon 34E altı ayrı UTC zaman alanı,
çok dönemli deterministik üretim, bağımsız dönem/semantik doğrulaması ve teknik
hata ayrımını `06-Testler/01-Birim/test_synthetic_temporal.py` içinde kanıtlar.
`AC/TS-048/049`, `AC/TS-054` zaman semantiği alt kapsamı ve
`AC/TS-050–052`nin sıfır kusurlu yapısal alt kapsamı tamamen yapay teknik V1
profil için doğrulanmıştır; üretim benzerliği, skor toleransı veya anonimlik
sonucu değildir.

## Kanıta Dayalı Karar Desteği Kabul Matrisi

| Kabul/Test | Zorunlu test kapsamı |
| --- | --- |
| `AC/TS-057`–`AC/TS-059` | Kullanım amacı profili, formül/kanıt görünürlüğü, ayrı güven türleri ve manifest ile deterministik yeniden üretim |
| `AC/TS-060`–`AC/TS-063` | Kaynaklı etki, değişiklik simülasyonu, lineage sürümü ve kanıtsız nedensellik iddiasının reddi |
| `AC/TS-064`–`AC/TS-066` | Kanıtlı öneri, veri kontratı ve kapsam/maliyet/güven gerekçeli adaptif tarama |
| `AC/TS-067`–`AC/TS-069` | Gizliliği koruyan kanıt, kalite borcu ve `SuggestOnly`/dry-run/canary/rollback kontrollü remediation |
| `AC/TS-070` | İzole chaos deneyi, kapsam/stop koşulu, geri alma ve üretim etkisi negatifleri |
| `AC/TS-071` | Zaman çizelgesi, değişmez kanıt paketi, bütünlük doğrulaması ve yetkili erişim |

Negatif kapsam; kaynak gösterilmeyen finansal etkiyi, kanıtsız kök neden ve
öneriyi, birleşik güven puanını, yetkisiz remediation/chaos çağrısını, ham hassas
örnek sızıntısını, manifest sürüm uyuşmazlığını ve rollback kanıtı olmayan
otomasyonu reddetmelidir. Bu matris ikinci faz hedefidir; mevcut otomasyon
baseline'ında uygulanmış test sayılmaz.

İterasyon 34F, [Sentetik PostgreSQL İlişkisel Dataset](02-Entegrasyon/Sentetik-PostgreSQL-Dataset.md)
ile 17 kaynak tablo, kontrollü kusur, kayıt düzeyi ground truth, bağımsız SQL
oracle'ı, güvenli reset ve gerçek PostgreSQL kalıcılığını doğrular. Bu çalışma
uygulamanın genel kural motorunun uçtan uca doğrulaması değildir.

Nicel dağılım, korelasyon, görev faydası, gizlilik, kusur yoğunluğu ve skor
toleransı eşikleri aktif sürümlü doğrulama politikasından çözülür; politika yoksa
çalışma `BLOCKED` olur. Sentetik performans
testi `AC/TS-008` kapsamındaki anonimleştirilmiş üretim örneği kabulinin yerine
geçmez.

## Belgelenmiş Otomasyon Baseline'ı

- Son proje hafızası kaydı backend için `1125 passed, 27 skipped`, frontend için
  95 Vitest testi; TypeScript type-check ve production build için temiz sonuç
  bildirir.
- Bu sayılar tarihsel kanıttır. 24 Temmuz 2026 dokümantasyon denetiminde Python
  bağımlılık kurulumu paket kaynağındaki HTTP 503 nedeniyle tamamlanamadığı için
  test/mypy baseline'ı bağımsız yeniden çalıştırılamamıştır.
- Test sayıları README, iterasyon ve teknik snapshot dosyalarında kopyalanmaz;
  yeni tam koşu sonucunda bu bölüm ve ilgili kanıt paketi birlikte güncellenir.
- PostgreSQL entegrasyon testleri ortam değişkeni/veritabanı gerektirebilir;
  skipped sonucu başarı gibi sunulmaz ve opt-in koşu ayrı raporlanır.
- Frontend için `npm test`, `npm run typecheck`, `npm run build`, görsel akışlar
  için `npm run test:e2e` ve Storybook build çıktısı ayrı kanıtlanır.


## Aktif Doğrulama Açıkları

| Kapsam | Mevcut kanıt | Kapanış koşulu |
| --- | --- | --- |
| `36B5` kapatma/yeniden açma | Servis, API, PostgreSQL repository, frontend ve birim/entegrasyon kanıtı iterasyon kaydında tamamlanmıştır. | `TechnicallyVerified`; yeni bir açık olarak izlenmez. |
| `36E` execution cutover | Migration, PostgreSQL repository, entegrasyon testleri ve `PostgreSQLExecutionStartService`/`PostgreSQLExecutionCancelService` adaptörleri mevcut. | `TechnicallyVerified`; production composition root PostgreSQL kullanabilir ve SQLite repository runtime export'ta değildir. |
| `36F` scheduling/policy kalıcılığı | PostgreSQL scheduling/source-usage policy repository'leri, `20260724_05` migration'ı ve runtime export temizliği mevcut. | `TechnicallyVerified`; PostgreSQL entegrasyon kanıtının yeniden koşulması için `DATA_QUALITY_POSTGRES_TEST_URL` gerekir. |
| `36G` güvenli raporlama | Birim testleri; report/report schedule repository'leri; `20260724_06/07` migration'ları ve PostgreSQL yaşam döngüsü entegrasyon testi mevcut. | `TechnicallyVerified`; PostgreSQL entegrasyon kanıtının yeniden koşulması için `DATA_QUALITY_POSTGRES_TEST_URL` gerekir. Kalıcı queue/worker dayanıklılığı ayrı pakettir. |
| `36H1`/`36H2` kalıcı iş kuyruğu ve yaşam döngüsü | Controller birim paketi `1172 passed`; etkilenen PostgreSQL dosyaları `41 passed`, skip yok; `20260728_08` + `20260729_09` + `20260729_10` migration zinciri. | 36H1 ve 36H2 `TechnicallyVerified`; bounded timeout/iptal, production reaper ve atomik execution+job iptali reviewer `APPROVED` kararıyla doğrulandı. |

Son tamamlanan doğrulama paketi [NEXT_STEP.md](../NEXT_STEP.md) içinde kayıtlıdır.

# Test, Performans ve Teknik Borç

## Test Yapısı

`06-Testler/01-Birim/` altında 34 pytest dosyası vardır. Aşağıdaki tablo ana test
alanlarını özetler:

| Test alanı | Kapsanan ana davranış |
| --- | --- |
| `test_data_sources.py` | CSV/PostgreSQL sözleşmesi, metadata, profil, sınıflandırma |
| `test_rules.py` | Şablonlar, sürüm, test, aktivasyon, maker-checker |
| `test_executions.py` | Kuyruk, retry, timeout, iptal, kota, schedule |
| `test_scoring.py` | Formül, eşik, agregasyon, config onayı |
| `test_dashboard.py` | Scope filtreleme, ağaç, detail, trend |
| `test_identity.py` | ActorContext, LDAP mapping, throttle, session |
| `test_audit.py` | Redaksiyon, hash-chain, failure mode, query/migration |
| `test_notifications.py` | Recipient, dedupe, read ve yetkisiz erişim |
| `test_issues.py` | State machine, atama, doğrulama, recurrence |
| `test_servicenow.py` | Allowlist, idempotency, retry, DLQ, breaker |
| `test_reporting.py` | Yetki filtreli report preview |
| `test_incident_response.py` | Incident/breach/decision/timeline |
| `test_secure_sdlc.py` | Secret scanner |
| `test_secure_sdlc_sbom.py` | Doğrudan bağımlılık inventory/SBOM |
| `test_secure_sdlc_sast.py` | Veri-minimum SAST bulgu zarfı ve sürüm kapısı |
| `test_secure_sdlc_vulnerabilities.py` | Doğrudan bağımlılık zafiyet bulgu zarfı ve sürüm kapısı |
| `test_secure_sdlc_pentest.py` | Veri-minimum sızma testi bulgu yaşam döngüsü ve tekrar test kanıtı |
| `test_secure_sdlc_evidence.py` | Deterministik teknik kanıt manifesti ve eksik/engelli kontrol raporu |
| `test_secure_sdlc_evidence_gate.py` | Byte düzeyinde teknik kanıt manifest drift doğrulama kapısı |
| `test_secure_sdlc_preflight.py` | Altı kontrollü birleşik fail-closed yerel sürüm preflight'ı |
| `test_dashboard_api.py` | Dashboard özeti, Problem Details, güvenilir resolver ve BFF logout/CSRF |
| `test_synthetic_*.py` | Sentetik politika, üretici, oracle, zaman semantiği ve PostgreSQL dataset doğrulaması |

Testler geçici SQLite DB veya `:memory:` repository ile izoledir. LDAP, PostgreSQL,
ServiceNow, audit sink ve resolver'lar fake/protokol implementasyonlarıdır. Gerçek
banka verisi ve dış sistem kullanılmaz. Negatif yetki, servis hesabı, maker-checker,
secret redaksiyonu ve veri-minimum payload testleri dikkate değer güçlü noktadır.

## Test Seviyeleri

| Seviye | Durum | Açıklama |
| --- | --- | --- |
| Unit | Uygulanmış | Tam depoda 1029 test |
| Repository | Uygulanmış, unit içinde | Gerçek SQLite sorgu/constraint testleri |
| Contract | Kısmen uygulanmış | Fake adaptörler port sözleşmesini sınar |
| Integration | Kısmen uygulanmış | 34F yapay dataset için iki opt-in PostgreSQL testi; LDAP/ServiceNow gerçek entegrasyonu yok |
| API | Kısmen uygulanmış | Dashboard özeti ve BFF logout güvenlik/hata sözleşmesi |
| End-to-end | Kısmen uygulanmış | Frontend için 14 Playwright testi; üretim IdP/veri bağlantısı yok |
| Performance | Planlanmış ancak uygulanmamış | 20 milyon satır ve yük testi yok |
| Synthetic data | Kısmen uygulanmış | 34A–34F politika/run, Golden üretici, ground truth, zaman ve PostgreSQL alt kapsamı; gizlilik kapısı ve genel runtime karşılaştırması yok |
| Security | Kısmen uygulanmış | Negatif unit, local secret scan, direct SBOM, yerel SAST/bağımlılık zafiyet kapıları, pentest bulgu takibi, teknik kanıt manifesti/drift kapısı ve birleşik preflight; gerçek scanner/SCA/DAST/pentest yok |

Coverage aracı, eşik veya rapor dosyası yapılandırılmamıştır. Test sayısı yüksek olsa
da statement/branch coverage doğrulanamaz. Mutation, property/fuzz ve concurrency
stress testi yoktur.

## Doğrulama Komutları

Projenin mevcut doğrulama yüzeyi:

```bash
python3 -m pytest -q
python3 -m ruff check .
python3 -m ruff format --check .
python3 -m mypy 03-Backend/src 06-Testler
python3 -m compileall -q 03-Backend/src 06-Testler
PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc .
```

Güncel baseline'da 1029 test, Ruff lint/format ve 159 kaynak dosyalık tam mypy
kontrolü geçmektedir; bu baseline henüz kurumsal CI ile zorlanmaz.

## Performans ve Ölçeklenebilirlik

### Güçlü Noktalar

- Profil domaini FULL/SAMPLE/PARTITION/AGGREGATE yöntemlerini ayırır.
- PostgreSQL portu kaynakta toplulaştırma bekler ve query timeout taşır.
- Execution HEAVY/LIGHT ve source bazlı kota uygular.
- Retry/timeout/idempotency ve kısmi bölüm sonucu modellenmiştir.
- Dashboard trend sorgusu scope/time indeksini kullanabilir; rapor preview tek SQL
  window function ile latest source score seçer.
- Audit ve rapor sorgularında page/window üst limitleri vardır.

### Darboğazlar

| Alan | Kanıt | Etki |
| --- | --- | --- |
| CSV profil bellek kullanımı | Her alan için `set`, sayısal değerler için `list` | Yüksek kardinalitede O(n) bellek |
| CSV sample taraması | Tüm satırlar okunur, yalnız hesaplama seçilir | I/O azalmaz |
| Execution claim | Tüm QUEUED ve RUNNING satırları `fetchall()` | Queue hacmiyle O(n) tarama/bellek |
| Eksik execution index | status+created_at index yok | Claim yavaşlar |
| Schedule due index yok | active+next_run_at index yok | Scheduler taraması büyür |
| Audit integrity | Tüm zincir `fetchall()` ile baştan doğrulanır | Audit görüntüleme O(n) |
| Scoring katalog çağrıları | Her rule için version/rule/dataset lookup | Gerçek DB adapterinde N+1 riski |
| JSON kolonlar | Scope/definition/metrics/details TEXT | Filtre/indeks ve şema kontrolü zor |
| SQLite global yazma | Tek dosya ve process lock modeli | Yüksek paralellik/HA için uygun değil |
| Retry `sleep` | Worker metodu içinde bloklayıcı bekleme | Thread/worker kapasitesi tüketir |
| Liste metotları | Birçok repository tüm kayıtları döndürür | Bellek ve latency büyür |

Streaming altyapısı, cache, batch writer, connection pool, partitioned result store,
archive tier ve performans benchmark'ı yoktur. 20 milyon satırlık kabul hedefi kod
üzerinden doğrulanamaz.

### Önerilen Performans Çalışması

1. `ADR-016` kapsamında deterministik sentetik 20M satır ve yüksek kardinalite
   profiliyle ön benchmark bütçesi; bu sonuç `OPEN-014` anonimleştirilmiş üretim
   örneği kabulinin yerine geçmez.
2. CSV için bounded sketches/streaming agregat ve gerçek reservoir/hash sample.
3. PostgreSQL adapterinde kaynakta SQL agregasyon, `EXPLAIN` maliyet kapısı ve cancel.
4. DB destekli atomik claim (`SKIP LOCKED`/lease), due/status indeksleri ve broker.
5. Batch katalog prefetch ile scoring N+1 azaltma.
6. Audit integrity checkpoint/periodik bağımsız imza ve arşiv segmentleri.
7. Result/audit/history partition-retention ve dashboard materialized summary stratejisi.

## Kod Kalitesi

### Güçlü Noktalar

- Domain modellerinin çoğu frozen dataclass ve enum kullanır.
- External bağımlılıklar `Protocol` ile test edilebilir ayrılmıştır.
- Teknik hata, validation, authorization ve kalite sonucu ayrımı nettir.
- SQL parametreleme yaygındır.
- Idempotency ve immutable history birçok kritik akışta tasarım girdisidir.
- TODO/FIXME/HACK/boş `pass` veya `NotImplementedError` saptanmamıştır.

### Teknik Borç

| Borç | Kanıt | Sonuç |
| --- | --- | --- |
| Çok büyük servisler | `issues/service.py` 1013, `scoring/service.py` 913, `data_sources/service.py` 882, `servicenow/service.py` 864 satır | Değişiklik ve review maliyeti |
| Çok büyük repository'ler | data source 770, issue 748, ServiceNow 690 satır | Şema, mapping ve query sorumlulukları iç içe |
| Composition root sınırlı | Dashboard/logout wiring'i var; diğer domainler HTTP/runtime graph'ına bağlı değil | Uçtan uca davranış yalnız ilk dikeyde test ediliyor |
| Type-check CI kapısı eksik | Yerel mypy baseline'ı 131 dosyada sıfır; pipeline zorlaması yok | Yeni sapmalar otomatik engellenmez |
| Tool/dependency setup eksik | pytest/Ruff/mypy manifestte pinli değil; lock yok | Tekrarlanabilir build zayıf |
| Runtime migration | Repository açılışında DDL/rebuild | Deployment ve rollback riski |
| SQLite'a sıkı altyapı bağı | Servisler bazı yerlerde concrete repository tipi alır | Üretim DB geçişi zorlaşır |
| Merkezi role/permission kataloğu yok | String rol setleri farklı policy'lerde | Yetki matrisi drift riski |
| Legacy adapter/table | dashboard `_legacy`, `audit_records` | İki davranışın uzun süre yaşaması |
| Enumda kullanılmayan durumlar | Issue `NEW`, `CANCELLED` servis akışında yok | Model ve gerçek state machine farklı |
| Skorlama hedef modeli kısmen runtime'a taşındı | 33A kanonik sayaç/durum, 33B kritiklikten ayrılmış SOURCE kalite skoru; kapsam/güven, risk, override ve replay'in kalanı yok | Kabul edilen sözleşme ile çalışan prototip kısmen ayrışıyor |
| Tarihsel SOURCE replay'i eksik | `SOURCE_EQUAL_DATASET_QUALITY_V2` aktiftir; eski `SOURCE_WEIGHTED_V1` kayıtlarının replay/backfill ilişkisi yok | Trend karşılaştırılabilirliği sınırlı |
| Dimension weight semantiği | Configte var, dimension/enterprise formülünde kullanılmıyor | İş beklentisiyle sapma riski |
| Sentetik veri hedef modeli kısmen runtime'a taşındı | 34A–34F çekirdeği var; gizlilik kapısı, eksiklik/drift/hacim ve genel kural/skor/olay karşılaştırması yok | Tam kabul ve anonimlik kanıtı üretilemiyor |
| Paketleme eksik | `[build-system]` ve script yok | Kurulum/dağıtım standart değil |
| Frontend alan yüzeyleri eksik | React/Vite dashboard, tema, Storybook ve Playwright var; alan ekranları ve operasyonel KPI API'si yok | Referans dashboard kısmi, iş akışları açılmıyor |
| Kanıta dayalı karar runtime'ı yok | `ADR-019`, `FR-097–FR-111`, `AC/TS-057–071` belgelendi | Manifest/evidence, lineage, öneri, remediation ve chaos ikinci faz hedefi olarak kalıyor |

Belirgin dairesel paket bağımlılığı saptanmamıştır. Ancak bazı domain servisleri
concrete SQLite repository sınıfı aldığı için port/adapter ayrımı tutarlı değildir.

## Eksik Test Öncelikleri

1. Gerçek PostgreSQL read-only, timeout, cancel, metadata ve profiling integration.
2. Test LDAP/AD sunucusuyla TLS, mapping, lockout ve session integration.
3. Stub HTTP ServiceNow ile timeout/429/TLS/idempotency/field allowlist contract.
4. API authn/authz/IDOR/CSRF/rate limit/error contract.
5. Çoklu worker atomik claim, lease expiry ve crash recovery stress testleri.
6. Migration upgrade/rollback ve legacy audit gerçekçi hacim testi.
7. Backup/restore, hash-chain ve outbox replay E2E.
8. 20M profil, yüksek rule sayısı ve 30 günlük dashboard yük testi.
9. SAST/SCA/DAST ve bağımsız sızma testi hazırlığı.
10. Sentetik Golden/bozulmuş/drift/gizlilik profilleri, kusur ground truth'u,
    false-positive/negative, bağımsız skor sapması ve üretim hedefi izolasyonu.
11. `AC/TS-057–071` için formül/kanıt/manifest, ayrı güven, nedensellik,
    yetkisiz remediation/chaos ve hassas kanıt negatifleri.

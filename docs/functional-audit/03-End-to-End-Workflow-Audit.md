---
type: functional-audit
stage: "03 — Uçtan Uca İş Akışı Denetimi"
scope: as-is-vs-target
inputs:
  - 01-Current-Capabilities.md
  - 02-Target-Capability-Hierarchy.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-04
---

# 03 — Uçtan Uca İş Akışı Denetimi

> Hedef modelin tanımladığı akış zincirleri, mevcut sistem üzerinde adım adım
> izlenir. Her adımın kanıtı toplanır; zincirin **ilk koptuğu nokta** ve o
> kopmanın aşağı akışta neyi çalışmaz kıldığı gösterilir.

---

## 1. Kapsam ve yöntem

### 1.1 Girdiler

| Girdi | Rol |
|---|---|
| [01-Current-Capabilities.md](01-Current-Capabilities.md) | Mevcut durumun çift eksenli kaydı (kod zinciri / runtime erişilebilirliği) |
| [02-Target-Capability-Hierarchy.md](02-Target-Capability-Hierarchy.md) | 271 yaprak fonksiyonlu hedef referans modeli; adım kimlikleri buradan gelir |

Aşama 1 ve 2'den bulgu kopyalanmaz, referans verilir. Bu oturumda yeni doğrulanan
kanıtlar **"yeni doğrulama"** ibaresiyle işaretlenmiştir.

### 1.2 Bu aşamanın sorusu

Aşama 1 "hangi yetenek var?" sorusunu yanıtladı. Bu aşama farklı bir soru sorar:

> **Bir kullanıcı işe baştan sona başlayabiliyor mu?**

Bir yeteneğin var olması, onu içeren zincirin yürüdüğü anlamına gelmez. Zincirin
tek bir halkası kopuksa, o halkadan sonraki bütün halkalar — kendi başlarına
eksiksiz olsalar bile — erişilemez hâle gelir. Bu belge o kopmaları ve kaskad
etkilerini kaydeder.

### 1.3 Adım tablosu sözlüğü

Her akış, sabit on iki sütunlu bir adım tablosuyla denetlenir.

| Sütun | İçerik |
|---|---|
| **Hedef** | Aşama 2 yaprak kodu — adımın kimliği |
| **Adım** | Akıştaki eylem |
| **Aktör** | Hedef modeldeki rol |
| **Ekran** | Mevcut route veya `—` |
| **API** | Mevcut endpoint veya `—` |
| **Servis** | Mevcut sınıf/fonksiyon veya `—` |
| **Tablo** | Mevcut tablo veya `—` |
| **Geçiş** | Gerçekleşen durum geçişi veya `—` |
| **Audit** | Üretilen audit olayı veya `—` |
| **Test** | `U` birim · `I` entegrasyon (skip-gated) · `E` E2E · `—` |
| **Kod** | `✅` tam · `⚠️` kısmi · `❌` yok |
| **RT** | Runtime: `✅` erişilebilir · `⚠️` sahte/bellek içi · `🔴` kopuk · `❌` yol yok |

### 1.4 Çift eksen — neden gerekli

Aşama 1'de saptandığı gibi, PostgreSQL repository'lerinin bir bölümü yazılmış ve
test edilmiş olmasına rağmen çalıştırılabilir hiçbir bileşime bağlı değildir. Bu
nedenle bir adım **kod ekseninde `✅`, runtime ekseninde `⚠️` veya `🔴`** olabilir.
İki eksen ayrı sütunlarda tutulur; tek etiket bu iki gerçeği aynı anda taşıyamaz.

`RT` sütunundaki `🔴` ile `❌` arasındaki fark önemlidir:

- `❌` — o adım için hiç yol yok (ne kod ne yüzey)
- `🔴` — kod var ve doğru, ama çalıştırılabilir uygulamada zincir kopuyor

### 1.5 Kanıt kuralları

- Kanıt hücreleri dosya yolu ve mümkün olduğunda satır referansı taşır.
- Kanıt bulunamadıysa `—` yazılır; varsayım yürütülmez.
- Bir adım yalnız test dosyasında örnekleniyorsa `Servis` sütununda belirtilir ve
  `RT` sütunu buna göre işaretlenir.
- Bu denetimde **hiçbir test koşulmadı ve uygulama ayağa kaldırılmadı**; runtime
  değerlendirmeleri kod okumasından çıkarılmıştır (bkz. §7).

### 1.6 Kapsam sınırı

Bu belge yalnız **tespit** içerir. Çözüm önerisi, düzeltme yönü, öncelik puanı ve
iterasyon planı bilinçli olarak yazılmamıştır; bunlar sonraki aşamalara aittir.

---

## 2. Akış özet panosu

| # | Akış | İlk kırılan adım | Kırılma nedeni | Kod | RT |
|---|---|---|---|---|---|
| 1 | Yeni veri kaynağı onboarding | Aktivasyon kararı (kontrol atlanıyor) → metadata keşfi (durur) | Aktivasyon gerçek servisi çağırmıyor; keşfi tetikleyen HTTP yüzeyi yok | ⚠️ | 🔴 |
| 2 | Metadata keşfi ve schema drift | Metadata keşfini başlat | Aynı — zincir hiç başlamıyor | ❌ | ❌ |
| 3 | İlk profilleme ve baseline | Profil çalıştırmasını talep et | `run_profile` yürütücüsü var; talep edecek endpoint yok | ✅ | ⚠️ |
| 4 | Kural oluşturma → aktivasyon | (kod ekseninde kırılma yok) | Runtime: `POST /rules` sonrası **tüm mutasyon uçları 503** — `rule_mutation_service` bağlanmamış | ✅ | 🔴 |
| 5 | Zamanlanmış çalıştırma | Vadesi gelen zamanlamayı tetikle | `SchedulingService` var; çağıran daemon ve yüzey yok | ✅ | 🔴 |
| 6 | Teknik hata, retry, dead-letter | Kod: dead-letter'ları incele · RT: işi sahiplen | Operatör yüzeyi yok; worker süreci hiç başlatılmıyor | ⚠️ | 🔴 |
| 7 | Kalite başarısızlığı → skor → issue | Kalite ihlalinden sorun üret | Üretici servis var, **çağıranı yok**; uygunluk kapısı tanımsız | ✅ | 🔴 |
| 8 | Issue inceleme → yeniden açma | (kod ekseninde kırılma yok) | Runtime: bellek içi store, audit üretmiyor | ✅ | ⚠️ |
| 9 | İstisna ve override | İstisna talep et | Hiçbir halkada kod yok | ❌ | ❌ |
| 10 | Rapor üretimi ve güvenli indirme | Raporu asenkron üret | Kuyruk atlanıyor; içerik sabit veri | ⚠️ | ⚠️ |
| 11 | Lineage ve etki analizi | Lineage olayını al | Alım ucu yok; etki analizi yalnız testte | ⚠️ | ⚠️ |
| 12 | Data contract ihlali | Sözleşme taslağı oluştur | Repo genelinde sıfır kod | ❌ | ❌ |
| 13 | Retention ve güvenli imha | Saklama politikası tanımla | Politika tablosu ve yüzeyi yok | ⚠️ | ❌ |

**Panonun okunuşu:** on üç akıştan **hiçbiri** uçtan uca yürümüyor. İkisi (4 ve 8)
kod ekseninde eksiksiz ama runtime'da bellek içi depo üzerinde çalışıyor; üçü
(2, 9, 12) hiç başlamıyor; kalan sekizi ortada kopuyor.

---

## 3. Akış denetimleri

### Akış 1 — Yeni veri kaynağı onboarding

**Zincir:** Kaynak oluştur ✅ → sır referansı ⚠️ → bağlantı testi ✅ → kullanım
politikası ⚠️ → aktivasyon talebi ⚠️ → **aktivasyon kararı 🔴 (onay atlanıyor)**
→ **metadata keşfi ❌ (servis var, uç yok)** → dataset/alan oluşumu ❌ →
sahiplik ❌ → sınıflandırma ❌ → kritiklik ❌ → ilk profil ❌ → baseline ❌

> **Bu akışta iki farklı kırılma tipi var.** Metadata keşfinden itibaren
> zincir **durur** (adım hiç gerçekleşmez). Aktivasyon kararında ise zincir
> **yanlış yürür**: adım tamamlanır, fakat maker-checker onayı, checker rolü,
> kapsam ve audit devre dışıdır (K9). Onboarding'in denetlenebilirliği
> açısından ikincisi daha ağırdır — kaynak `ACTIVE` olur ve bunun kaydı
> kalmaz.

| Hedef | Adım | Aktör | Ekran | API | Servis | Tablo | Geçiş | Audit | Test | Kod | RT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `D03.C01.W01.A01` | Kaynak kaydı oluştur | Technical Steward | [/data-sources](../../frontend/src/dataSources/DataSourcesPage.tsx) | `POST /api/v1/data-sources` | [`DataSourceService.create_data_source`](../../src/veri_kalitesi/data_sources/service.py#L126) | `data_sources` | → `TEST_PENDING` | ✅ | U+E | ✅ | ⚠️ |
| `D03.C01.W01.A02` | Salt okunur erişimi zorla | Sistem | — | — | [`data_sources/postgresql_driver.py`](../../src/veri_kalitesi/data_sources/postgresql_driver.py) | — | — | — | U | ⚠️ | ⚠️ |
| `D03.C01.W02.A01` | Sır referansı bağla | Technical Steward | — | — | `data_sources`.`secret_reference` kolonu | `data_sources` | — | — | — | ⚠️ | ❌ |
| `D03.C01.W03.A01` | Bağlantıyı test et | Technical Steward | /data-sources | `POST /{id}/test` | [`DataSourceService.test_connection`](../../src/veri_kalitesi/data_sources/service.py#L172) | `connection_test_results` | `TEST_PENDING`→`TEST_SUCCEEDED` | ✅ | U+E | ✅ | ⚠️ |
| `D03.C01.W03.A02` | Test geçmişini görüntüle | Technical Steward | — | — | — | `connection_test_results` | — | — | — | ⚠️ | ❌ |
| `D03.C03.W01.A01` | Kullanım politikası tanımla | Technical Steward | — | — | [`postgresql_source_usage.py`](../../src/veri_kalitesi/executions/postgresql_source_usage.py) | `source_usage_policies` | — | — | U | ⚠️ | ❌ |
| `D03.C02.W01.A01` | Aktivasyon talep et | Technical Steward (maker) | — | — | — | `data_source_activation_requests` | — | — | — | ⚠️ | ❌ |
| `D03.C02.W01.A02` | Aktivasyon kararı ver | Data Owner (checker) | /data-sources | `POST /{id}/activation` | Gerçek [`decide_activation`](../../src/veri_kalitesi/data_sources/service.py#L461) **çağrılmıyor**; bağlanan `DevelopmentDataSourceStore.activate` yalnız durum guard'ı uyguluyor | `data_sources` | →`ACTIVE` (onaysız) | **—** | U+E | ✅ | 🔴 |
| `D04.C01.W01.A01` | **Metadata keşfini başlat** | Technical Steward | **—** | **—** | [`DataSourceService.discover_metadata`](../../src/veri_kalitesi/data_sources/service.py#L763) — orkestrasyon var, tetikleyen uç yok | `metadata_discovery_results` | — | ⚠️ | U+I | ✅ | ❌ |
| `D04.C01.W02.A01` | Keşif farkını hesapla | Sistem | — | — | [`_diff_metadata`](../../src/veri_kalitesi/data_sources/service.py#L1559) — `discover_metadata` içinden çağrılıyor | — | — | — | U | ✅ | ❌ |
| `D04.C01.W02.A02` | Keşif farkını uygula | Technical Steward | — | — | — | — | — | — | — | ❌ | ❌ |
| `D04.C02.W01.A01` | Dataset kaydını oluştur | Sistem | — | — | — | `datasets` | — | — | — | ❌ | ❌ |
| `D04.C03.W01.A01` | Alan kaydını oluştur | Sistem | — | — | — | `data_fields` | — | — | — | ❌ | ❌ |
| `D01.C02.W01.A01` | Veri sahibi ata | Governance Admin | — | — | — | — | — | — | — | ❌ | ❌ |
| `D04.C03.W02.A01` | Alanı sınıflandır | Data Steward | — | — | — | `data_fields`.`classification` | — | — | — | ⚠️ | ❌ |
| `D04.C02.W02.A01` | Dataset kritikliğini belirle | Data Owner | — | — | — | `datasets`.`criticality` | — | — | — | ⚠️ | ❌ |
| `D05.C01.W01.A01` | İlk profili çalıştır | Data Steward | — | — | — | `data_profiles` | — | — | — | ❌ | ❌ |
| `D05.C03.W01.A01` | Baseline belirle | Data Steward | — | — | — | — | — | — | — | ❌ | ❌ |

**İlk kırılma — `D04.C01.W01.A01` metadata keşfi.** Keşif mantığı connector
katmanında mevcuttur (`discover_metadata`, üç tanım), `metadata_discovery_results`
tablosu migration 03'te tanımlıdır; ancak keşfi **tetikleyen hiçbir endpoint
bulunamadı**. 44 endpoint'in hiçbiri metadata keşfine bağlı değildir.

**Bağımlı etkiler:**

1. Dataset ve alan kayıtları hiçbir zaman otomatik oluşmaz → `datasets` ve
   `data_fields` tabloları boş kalır.
2. Sahiplik ataması yapılacak varlık yoktur → yönetişim zinciri başlayamaz.
3. Alan sınıflandırması yapılamaz → maskeleme kararları için sınıf bilgisi yoktur;
   hedef modelin `BR-D04-006` kuralı gereği her alan hassas kabul edilmelidir.
4. Profil çalıştırılacak hedef yoktur → akış 3 hiç başlayamaz.
5. Kural yazılacak dataset/alan referansı yoktur → akış 4'te dataset kimlikleri
   elle girilmek zorundadır (aşama 1 §4/B ile tutarlı).
6. Baseline oluşmaz → akış 2'nin drift kolu anlamsızlaşır.

**Runtime ek kırılması:** Kırılmadan önceki adımlar bile çalıştırılabilir
uygulamada `DevelopmentDataSourceStore` (bellek içi) üzerinde yürür — oluşturulan
kaynak süreç yeniden başlayınca kaybolur ve audit üretmez. `PostgreSQLDataSourceRepository`
yalnız testlerde örneklenir.

---

### Akış 2 — Metadata keşfi ve schema drift

**Zincir:** **Keşif kapsamını yapılandır ❌** → keşfi başlat ❌ → farkı hesapla ❌ →
şema değişikliğini sınıflandır ❌ → etki simülasyonu ❌ → bildirim ❌ → kabul/blokaj ❌
→ etkilenen kuralları güncelle ❌

| Hedef | Adım | Aktör | Ekran | API | Servis | Tablo | Geçiş | Audit | Test | Kod | RT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `D04.C01.W01.A02` | Keşif kapsamını yapılandır | Technical Steward | — | — | — | — | — | — | — | ❌ | ❌ |
| `D04.C01.W01.A01` | Metadata keşfini başlat | Technical Steward | — | — | connector düzeyinde | `metadata_discovery_results` | — | — | ⚠️ | ❌ | ❌ |
| `D04.C01.W02.A01` | Keşif farkını hesapla | Sistem | — | — | — | `metadata_discovery_results`.`changes` (kolon) | — | — | — | ❌ | ❌ |
| `D04.C04.W01.A01` | Şema değişikliğini sınıflandır | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |
| `D10.C02.W02.A01` | Değişiklik etkisini simüle et | Technical Steward | — | — | [`lineage/impact.py`](../../src/veri_kalitesi/lineage/impact.py) (yalnız testte) | — | — | — | U | ⚠️ | ❌ |
| `D12.C01.W01.A01` | Kırıcı değişikliği bildir | Sistem | — | — | `NotificationService` (çağrılmıyor) | — | — | — | U | ⚠️ | ❌ |
| `D04.C04.W02.A01` | Kabul et veya blokla | Data Owner | — | — | — | — | — | — | — | ❌ | ❌ |
| `D06.C02.W02.A01` | Etkilenen kurallar için yeni sürüm | Rule Author | /rules | `POST /rules/{id}/versions` | `RuleService` | `rule_versions` | →`DRAFT` | ✅ | U+I | ✅ | ⚠️ |
| `D05.C03.W01.A02` | Baseline'ı geçersiz kıl | Data Steward | — | — | — | — | — | — | — | ❌ | ❌ |

**İlk kırılma — `D04.C01.W01.A02`/`A01`.** Zincir hiç başlamaz: keşif kapsamı
yapılandırması ve keşif tetikleme için ne ekran, ne endpoint, ne servis bulundu.

**Kritik ayrım (yeni doğrulama):** Repository'de `profile_comparisons` tablosu ve
[`compare_profile_snapshots`](../../src/veri_kalitesi/data_sources/profiling.py#L322)
fonksiyonu mevcuttur, ancak bunlar **veri dağılımı** driftini karşılaştırır.
Hedef modelin `D04.C04` altında tanımladığı **şema değişikliği** tespiti —
kolon eklenmesi/kaldırılması, tip daralması, boş geçilebilirlik sıkılaşması ve
bunların `ADDITIVE`/`BREAKING`/`NEUTRAL` sınıflandırması — ayrı bir yetenektir ve
kod karşılığı bulunamadı. `schema_changes` benzeri bir tablo hiçbir migration'da
yoktur.

**Bağımlı etkiler:**

1. Kaynakta kolon değişse bile sistem bunu fark etmez → kurallar sessizce yanlış
   şeyi ölçmeye devam eder veya teknik hata verir.
2. Kırıcı değişiklik bildirimi üretilmez → sahibin haberi olmaz.
3. Ölçüm blokajı devreye giremez → hedef modelin `BR-D04-008` kuralındaki
   "karar verilmezse ölçüm otomatik bloklanır" davranışı hiç işlemez.
4. Etkilenen kuralların `REVIEW_REQUIRED` durumuna geçişi tetiklenmez — `RuleStatus`
   enum'unda bu değer tanımlıdır ancak şema değişikliğinden onu tetikleyen yol yoktur.
5. Akış 12 (data contract) zaten yok; olsaydı şema taahhüdü ihlali de tespit
   edilemezdi.

---

### Akış 3 — İlk profilleme ve baseline

**Zincir:** **Profil talebi ❌** → yöntem/örnekleme ⚠️ → temel metrikler ⚠️ →
dağılım ⚠️ → snapshot kaydı ✅ → snapshot görüntüleme ✅ → **baseline belirleme ❌**
→ karşılaştırma ⚠️ → drift hükmü ✅ → drift'ten issue ❌

| Hedef | Adım | Aktör | Ekran | API | Servis | Tablo | Geçiş | Audit | Test | Kod | RT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `D05.C01.W01.A01` | Profil çalıştırmasını talep et | Data Steward | **—** | **—** | **—** | `data_profiles` | — | — | — | ❌ | ❌ |
| `D05.C01.W01.A02` | Profil çalıştırmasını iptal et | Operations | — | — | — | — | — | — | — | ❌ | ❌ |
| `D05.C01.W02.A01` | Yöntemi politikadan çözümle | Sistem | — | — | [`ProfilePolicyResolver`](../../src/veri_kalitesi/data_sources/profiling.py#L39) | `data_profiles`.`method`,`sample_ratio` | — | — | U | ⚠️ | ❌ |
| `D05.C02.W01.A01` | Alan metriklerini hesapla | Sistem | — | — | [`build_advanced_field_metrics`](../../src/veri_kalitesi/data_sources/profiling.py#L188) | `data_profiles`.`metrics` | — | — | U | ⚠️ | ❌ |
| `D05.C02.W02.A01` | Değer dağılımını çıkar | Sistem | — | — | [`profiling.py`](../../src/veri_kalitesi/data_sources/profiling.py) (Top-N, maskeli) | `data_profiles`.`metrics` | — | — | U | ⚠️ | ❌ |
| `D05.C02.W02.A02` | Aykırı değer adaylarını işaretle | Sistem | — | — | [`_outlier_candidates`](../../src/veri_kalitesi/data_sources/profiling.py#L455) | — | — | — | U | ⚠️ | ❌ |
| — | Snapshot'ları listele | Data Steward | [/profiling](../../frontend/src/profiling/ProfilingPage.tsx) | `GET /profile-snapshots` | `ProfileSnapshotQueryService` | `data_profiles` | — | — | U | ✅ | ✅ |
| — | Snapshot detayını görüntüle | Data Steward | /profiling | `GET /profile-snapshots/{id}` | `ProfileSnapshotQueryService` | `data_profiles` | — | — | U | ✅ | ✅ |
| `D05.C03.W01.A01` | **Profili baseline belirle** | Data Steward | **—** | **—** | **—** | **—** | — | — | — | ❌ | ❌ |
| `D05.C03.W01.A02` | Baseline'ı geçersiz kıl | Data Steward | — | — | — | — | — | — | — | ❌ | ❌ |
| `D05.C04.W01.A01` | İki profili karşılaştır | Sistem/Steward | — | `POST /profile-comparisons` | [`compare_profile_snapshots`](../../src/veri_kalitesi/data_sources/profiling.py#L322) | `profile_comparisons` | — | — | U | ⚠️ | ⚠️ |
| `D05.C04.W02.A01` | Drift hükmü üret | Sistem | /profiling | `GET /profile-snapshots/{id}/drift` | `profiling.py` (7 aile) | `profile_comparisons`.`result` | — | — | U | ✅ | ✅ |
| `D05.C04.W02.A02` | Drift hükmünden sorun üret | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |

**İlk kırılma — `D05.C01.W01.A01` profil talebi.** Profil **okuma** yüzeyi
eksiksizdir (üç endpoint, bir sayfa), ancak profil **üretme** yüzeyi yoktur: profil
çalıştırmasını başlatan endpoint, servis veya ekran kanıtı bulunamadı. Sistem
mevcut `data_profiles` kayıtlarını gösterebilir ama yeni kayıt üretemez.

**İkinci kırılma — `D05.C03.W01.A01` baseline (yeni doğrulama).** Hedef modelde
baseline, onaylanan ve sürümlenen bir varlıktır (`ST-ProfileBaseline` durum
makinesi: `ACTIVE` → `SUPERSEDED` / `INVALIDATED`). Mevcut sistemde böyle bir
varlık yoktur; karşılaştırma, sıralı profil listesinde **bir öncekini örtük
olarak** baz alır:

```
baseline_profile = sorted_profiles[idx - 1]
… yoksa: "No baseline available for drift comparison."
```
([data_sources/query.py:229-260](../../src/veri_kalitesi/data_sources/query.py#L229-L260))

**Bağımlı etkiler:**

1. "Normal" tanımı hiçbir zaman bilinçli olarak sabitlenmez → drift, kaymanın
   kendisiyle birlikte kayan bir referansa göre ölçülür; kademeli bozulma
   görünmez kalır.
2. Meşru bir iş değişikliğinden sonra baseline geçersiz kılınamaz → hedef modelin
   `BR-D05-008` davranışı (yeni baseline atanana kadar `NOT_QUALIFIED`) işlemez.
3. Profil üretilemediği için karşılaştırma yapacak ikinci snapshot da doğal yolla
   oluşmaz → `POST /profile-comparisons` ucu ancak elle doldurulmuş veriyle anlam kazanır.
4. `D05.C04.W02.A02` drift'ten sorun üretimi yoktur → doğrulanmış drift bir sahibe
   ulaşmaz, akış 7'ye bağlanmaz.

**Runtime ek kırılması:** `POST /profile-comparisons` endpoint'i için frontend
istemci fonksiyonu bulunamadı; uç yalnız API düzeyinde erişilebilir.

---

### Akış 4 — Kural oluşturma, test, onay ve aktivasyon

**Zincir:** Dataset seç ⚠️ → şablon seç ❌ → kural oluştur ✅ → kapsam ✅ → eşik ✅ →
bağımlılık ❌ → çakışma ❌ → test ✅ → gölge ⚠️ → sürüm mühürle ⚠️ → onaya gönder ✅ →
onay kararı ✅ → aktivasyon ✅

| Hedef | Adım | Aktör | Ekran | API | Servis | Tablo | Geçiş | Audit | Test | Kod | RT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `D04.C05.W01.A01` | Katalogda dataset ara | Rule Author | — | — | — | `datasets` | — | — | — | ❌ | ❌ |
| `D06.C01.W02.A01` | Kural şablonu tanımla | Governance Admin | — | — | — | — | — | — | — | ❌ | ❌ |
| `D06.C01.W02.A02` | Şablonu yayımla | Governance Admin | — | — | — | — | — | — | — | ❌ | ❌ |
| `D06.C02.W01.A01` | Kural oluştur | Rule Author | [/rules](../../frontend/src/rules/RulesPage.tsx) | `POST /api/v1/rules` | [`RuleService`](../../src/veri_kalitesi/rules/service.py#L76) | `quality_rules` | →`DRAFT` | ✅ | U+E | ✅ | ⚠️ |
| `D06.C02.W01.A02` | Özel sorgu kuralı oluştur | Rule Author | /rules | `POST /api/v1/rules` | `RuleService` (`CUSTOM_SQL` tipi) | `rule_versions`.`definition` | →`DRAFT` | ✅ | U | ⚠️ | ⚠️ |
| `D06.C03.W01.A01` | Kural kapsamını tanımla | Rule Author | /rules | sürüm gövdesi | `RuleService` | `rule_versions`.`definition` | — | ✅ | U | ✅ | ⚠️ |
| `D06.C03.W02.A01` | Eşik ve ağırlık belirle | Rule Author | /rules | sürüm gövdesi | `RuleService` | `rule_versions`.`threshold`,`weight` | — | ✅ | U | ✅ | ⚠️ |
| `D06.C04.W01.A01` | Bağımlılık grafiğini çıkar | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |
| `D06.C04.W02.A01` | Çakışma/mükerrerlik tespit et | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |
| `D06.C02.W02.A01` | Yeni kural sürümü oluştur | Rule Author | /rules | `POST /rules/{id}/versions` | `RuleService` | `rule_versions` | →`DRAFT` | ✅ | U+I | ✅ | ⚠️ |
| `D06.C02.W03.A01` | Sürümü sınırlı veriyle test et | Rule Author | /rules | `POST /rules/{id}/test` | `RuleService` | `rule_test_results` | →`SUCCESS`\|`TECHNICAL_ERROR` | ✅ | U | ✅ | ⚠️ |
| `D06.C02.W03.A02` | Testi resmî skordan dışla | Sistem | — | — | `rule_test_results`.`official_score_included` | `rule_test_results` | — | — | U | ✅ | ⚠️ |
| `D06.C05.W01.A01` | Gölge modda çalıştır | Rule Author | — | — | `ExecutionMode.SHADOW` enum + migration 12 | `rule_executions`.`execution_mode` | — | — | U | ⚠️ | ❌ |
| `D06.C02.W02.A02` | Sürümü değişmez kıl | Sistem | — | — | migration 12 IR digest kolonları | `rule_versions` | →`SEALED` | — | ⚠️ | ⚠️ | ⚠️ |
| `D06.C02.W04.A01` | Onaya gönder | Rule Author (maker) | /rules | `POST /rules/{id}/approval` | `RuleService` | `rule_approval_requests` | →`PENDING` | ✅ | U+I | ✅ | ⚠️ |
| `D06.C02.W04.A02` | Onay kararı ver | Rule Approver (checker) | /rules | `POST /rules/approval/{id}/decide` | [`RuleService`](../../src/veri_kalitesi/rules/service.py#L797) | `rule_approval_requests` | `PENDING`→`APPROVED`\|`REJECTED` | ✅ | U+I | ✅ | ⚠️ |
| `D06.C02.W04.A03` | Onay talebini geri çek | Rule Author | /rules | `POST /rules/approval/{id}/withdraw` | `RuleService` | `rule_approval_requests` | →`WITHDRAWN` | ✅ | U | ✅ | ⚠️ |
| `D06.C02.W04.A04` | Süresi geçen talebi kapat | Sistem | — | — | [`RuleService`](../../src/veri_kalitesi/rules/service.py#L763) `expiry_service_roles` | `rule_approval_requests`.`expires_at` | →`EXPIRED` | ✅ | U | ⚠️ | 🔴 |
| `D06.C02.W05.A01` | Kural sürümünü aktive et | Data Steward | /rules | `POST /rules/{id}/activation` | `RuleService` | `quality_rules`.`status` | →`ACTIVE` | ✅ | U+E | ✅ | ⚠️ |
| `D06.C02.W05.A02` | Kuralı pasifleştir | Data Steward | /rules | `POST /rules/{id}/passivation` | `RuleService` | `quality_rules`.`status` | →`PASSIVE` | ✅ | U | ✅ | ⚠️ |

**Kod ekseninde kırılma yok.** Bu, repository'nin en eksiksiz akışıdır: maker ≠
checker kuralı serviste zorlanır (`rules/service.py:542-545`) ve testlidir
(`test_rules.py:825,933,972`), sürüm değişmezliği modellenmiştir, dokuz
endpoint'in tamamı frontend'den kullanılır.

> **Düzeltme — "maker-checker veri tabanı seviyesinde korunur" ifadesi
> yanlıştı.** `rule_approval_requests` üzerindeki kısmi UNIQUE, aynı nesne
> için birden çok açık talebi engeller; maker ile checker'ın **farklı
> aktörler olmasını zorlamaz**. 14 migration'daki hiçbir `CheckConstraint`
> kolon-kolon karşılaştırması yapmaz. Güvence tamamen servis sınırındadır.

**Çevresel kırılmalar (zincirin içinde değil, girişinde ve çıkışında):**

| Kırılma | Etkisi |
|---|---|
| Dataset kataloğu yok (akış 1'den) | Kural yazarı hedef dataset/alan kimliklerini elle girmek zorundadır; geçersiz referans ancak çalıştırma anında ortaya çıkar |
| Şablon kütüphanesi yok | Hedef modelin `D06.C01.W02` yaşam döngüsü (`DRAFT`→`PUBLISHED`→`DEPRECATED`) yoktur; `RuleType` enum'undaki sekiz tip kod içinde sabittir, yönetilebilir bir kütüphane değildir |
| Bağımlılık ve çakışma tespiti yok | Aynı kontrolü ölçen mükerrer kurallar skorda iki kez sayılır; hedef modelin `BR-D06-011` kuralı uygulanamaz |
| Zamanlama kolu kopuk (akış 5) | Aktive edilen kural otomatik çalışmaz |

**Runtime ek kırılması — düzeltildi ve ağırlaştı.** Önceki değerlendirme
zincirin bellek içi store üzerinde "yürüdüğünü" varsayıyordu. Bu doğru
değildir: `create_development_app` yalnız `rule_creator_service=rule_store`
bağlar (`api/development.py:1351`) ve **`rule_mutation_service`'i hiç
geçirmez**. Route'lar bu portu `None` bulunca `RuleQueryTechnicalError`
fırlatır (`api/app.py:1772,1807,1836,1895`), bu da `503` olarak yanıtlanır
(`app.py:554-564`).

Pratik sonuç: çalıştırılabilir uygulamada kural **oluşturulabilir**, ama

- yeni sürüm eklenemez (`POST /rules/{id}/versions`),
- kural test edilemez (`POST /rules/{id}/test`),
- onaya gönderilemez, onaylanamaz, geri çekilemez,
- aktive veya pasifleştirilemez.

Yani "repository'nin en eksiksiz akışı" kod ekseninde doğrudur, fakat
runtime'da akış ilk adımdan sonra tamamen durur. `PostgreSQLRuleRepository`
yalnız `test_postgresql_rule_repository.py` ve `test_postgresql_rule_mutations.py`
içinde örneklenir. Onay süre aşımı (`D06.C02.W04.A04`) için zamanlayıcı süreci
bulunmadığından `EXPIRED` geçişi zaten hiç tetiklenmez.

Ayrıca kural oluşturma ucu, aktörün dataset kapsamını doğrulamaz
(`DevelopmentRuleStore.create_rule`, `development.py:837-882`) — K9.

---

### Akış 5 — Zamanlanmış çalıştırma

**Zincir:** Zamanlama tanımla 🔴 (servis var, yüzey yok) → duraklat/sürdür ❌ →
**vadesi geleni tetikle 🔴 (servis var, çağıran yok)** → kaçırılanı ele al ❌ →
çalıştırma aç ✅ → plan üret ✅ → iş kuyruğa al ✅ → işi sahiplen 🔴 → sonuç ⚠️

| Hedef | Adım | Aktör | Ekran | API | Servis | Tablo | Geçiş | Audit | Test | Kod | RT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `D07.C02.W01.A01` | Zamanlama tanımla | Data Steward | **—** | **—** | [`SchedulingService.create_schedule`](../../src/veri_kalitesi/executions/scheduling.py#L234) — zaman dilimi/DST doğrulaması ve önizleme dâhil | `schedules` | →`ACTIVE` | ✅ | U | ✅ | ❌ |
| `D07.C02.W01.A02` | Duraklat / sürdür | Operations | — | — | — | `schedules`.`is_active` | — | — | — | ❌ | ❌ |
| `D07.C02.W01.A03` | Zamanlamayı sil | Data Steward | — | — | — | — | — | — | — | ❌ | ❌ |
| `D07.C02.W02.A01` | **Vadesi geleni tetikle** | Sistem | — | — | [`SchedulingService.trigger_due`](../../src/veri_kalitesi/executions/scheduling.py#L303) — idempotent, testli; **çağıran daemon yok** | `schedules`.`next_run_at` | — | — | U | ✅ | 🔴 |
| `D07.C02.W02.A02` | Kaçırılan çalışmayı ele al | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |
| `D07.C01.W01.A01` | Çalıştırma aç | Sistem | — | `POST /api/v1/executions` (manuel) | [`PostgreSQLExecutionStartService`](../../src/veri_kalitesi/api/postgresql_execution.py) | `rule_executions` | →`QUEUED` | ✅ | U+I | ✅ | ⚠️ |
| `D07.C01.W02.A01` | Çalıştırma planını üret | Sistem | — | — | [`ExecutionStrategyEngine`](../../src/veri_kalitesi/executions/strategy_engine.py#L117) | `persistent_jobs` | — | — | U | ✅ | ✅ |
| `D07.C01.W02.A02` | İş yükü sınıfını belirle | Sistem | — | — | `WorkloadClass` enum | `rule_executions`.`workload_class` | — | — | U | ✅ | ✅ |
| `D07.C03.W01.A01` | İşi kuyruğa al | Sistem | — | — | [`PostgreSQLJobQueueRepository`](../../src/veri_kalitesi/jobs/postgresql_repository.py) | `persistent_jobs` | →`AVAILABLE` | ✅ | U+I | ✅ | ✅ |
| `D07.C03.W02.A01` | İşi sahiplen | Sistem (worker) | — | — | [`PersistentJobWorker`](../../src/veri_kalitesi/jobs/worker.py#L63) — **süreç başlatılmıyor** | `persistent_jobs` | →`CLAIMED` | ✅ | U+I | ✅ | 🔴 |
| `D08.C01.W01.A01` | Sonucu kaydet | Sistem | — | — | `rule_execution_results` yazımı | `rule_execution_results` | →`RECORDED` | ✅ | U+I | ✅ | 🔴 |
| — | Çalıştırmayı listele | Operations | [/executions](../../frontend/src/executions/ExecutionsPage.tsx) | `GET /api/v1/executions` | `DevelopmentExecutionReader` (statik) | — | — | — | U+E | ✅ | 🔴 |

**İlk kırılma — `D07.C02.W02.A01` zamanlama tetikleme.** Kırılmanın yeri
düzeltilmelidir: eksik olan sorgu veya mantık değil, **çağırandır**.
`SchedulingService` (`executions/scheduling.py:218`) zamanlama oluşturma,
zaman dilimi doğrulama, önizleme ve `trigger_due` ile idempotent çalıştırma
açmayı uygular; SQLite ve PostgreSQL repository'leri ile 10 birim testi
vardır (`test_executions.py:643-1005`). Bu servisi çağıran **hiçbir daemon,
script veya zamanlanmış görev yoktur**; zamanlama tanımlama için ekran ve
endpoint de yoktur. Zincir hem girişinde hem tetikleme noktasında kopuktur —
ancak sebebi eksik backend değil, eksik bağlantı ve yüzeydir.

İkincil bir teknik boşluk: `PostgreSQLScheduleRepository.due`
([postgresql_scheduling.py:109-124](../../src/veri_kalitesi/executions/postgresql_scheduling.py#L109))
düz bir `SELECT`'tir; `FOR UPDATE SKIP LOCKED` kullanmaz. Aynı repository
katmanındaki iş kuyruğu bunu kullandığı için bu bilinçli bir tercih değildir.
Daemon eklendiğinde çok zamanlayıcılı ortamda tek kazanan garantisi yalnız
aşağı akıştaki idempotency anahtarına kalır.

**Bağımlı etkiler:**

1. Aktive edilen hiçbir kural kendiliğinden çalışmaz → ölçüm tamamen manuel
   tetiklemeye bağlıdır.
2. Manuel tetikleme ucu (`POST /api/v1/executions`) için frontend istemcisi de
   yoktur ([executions/api.ts](../../frontend/src/executions/api.ts) yalnız
   `fetchExecutions` içerir) → kullanıcı arayüzünden hiçbir çalıştırma başlatılamaz.
3. Düzenli ölçüm olmadığı için skor serisi oluşmaz → trend, dönem karşılaştırması
   ve drift analizi için gereken zaman serisi doğal yolla birikmez.
4. Kaçırılan çalışma telafisi (`D07.C02.W02.A02`) hiç yoktur → hedef modelin
   `BR-D07-012` davranışı uygulanamaz.

**Runtime ek kırılması — iki katmanlı:** Zamanlayıcı olmasa bile manuel çalıştırma
gerçek PostgreSQL'e yazar ve iş kuyruğa girer; ancak **worker süreci de hiç
başlatılmadığı için** iş `AVAILABLE` durumunda kalır ve hiçbir zaman işlenmez
(bkz. akış 6). Ayrıca çalıştırma listesi statik `DEVELOPMENT_EXECUTIONS`
demetinden okunduğu için başlatılan çalıştırma listede **hiçbir zaman görünmez** —
yazma ve okuma farklı kaynaklara gider.

---

### Akış 6 — Teknik hata, retry ve dead-letter

**Zincir:** Bağlantı/timeout hatası ✅ → teknik/kalite ayrımı ✅ → **işi sahiplen 🔴** →
retry ✅ → zaman aşımı ✅ → kota sınırlama ⚠️ → lease geri alma ✅ → dead-letter ✅ →
operatör inceleme ❌ → yeniden işleme ❌ → kapatma ❌ → bildirim ❌

| Hedef | Adım | Aktör | Ekran | API | Servis | Tablo | Geçiş | Audit | Test | Kod | RT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `D07.C04.W01.A02` | Hatayı teknik/kalite sınıflandır | Sistem | — | — | `ExecutionStatus.TECHNICAL_ERROR`, `IssueSourceEventType.TECHNICAL` | `rule_executions`.`error_class` | →`TECHNICAL_ERROR` | ✅ | U | ✅ | 🔴 |
| `D07.C03.W02.A01` | **İşi sahiplen** | Worker | — | — | [`PersistentJobWorker`](../../src/veri_kalitesi/jobs/worker.py#L63) — `run_forever` çağrılmıyor | `persistent_jobs` | →`CLAIMED` | ✅ | U+I | ✅ | 🔴 |
| `D07.C03.W03.A01` | Heartbeat / lease yenile | Worker | — | — | `PersistentJobWorker` | `persistent_jobs`.`last_heartbeat_at` | — | ✅ | U | ✅ | 🔴 |
| `D07.C04.W01.A01` | Geçici hatada yeniden dene | Sistem | — | — | [`RetryableJobError`](../../src/veri_kalitesi/jobs/worker.py#L44) + `JobRetryPolicy` | `execution_attempts`, `persistent_jobs`.`attempt_count` | →`AVAILABLE` | ✅ | U+I | ✅ | 🔴 |
| `D07.C04.W02.A01` | Zaman aşımını uygula | Sistem | — | — | [`JobTimeoutError`](../../src/veri_kalitesi/jobs/worker.py#L56) | `rule_executions`.`status` | →`TIMEOUT` | ✅ | U | ✅ | 🔴 |
| `D03.C03.W01.A02` | Kota aşımında sınırla | Sistem | — | — | [`PostgreSQLSourceUsagePolicyRepository`](../../src/veri_kalitesi/executions/postgresql_source_usage.py) | `source_usage_policies` | →`AVAILABLE` | — | U | ⚠️ | 🔴 |
| `D07.C04.W03.A01` | Süresi geçmiş lease'i geri al | Sistem | — | — | `PersistentJobWorker` (lease mantığı) | `persistent_jobs`.`lease_expires_at` | →`AVAILABLE` | ✅ | U+I | ✅ | 🔴 |
| `D07.C04.W03.A02` | Worker kaydı ve sağlığı | Sistem/Operations | — | — | — | — | — | — | — | ❌ | ❌ |
| `D07.C04.W04.A01` | Dead-letter'a taşı | Sistem | — | — | [`PermanentJobError`](../../src/veri_kalitesi/jobs/worker.py#L50) | `dead_letter_records` | →`DEAD_LETTERED` | ✅ | U+I | ✅ | 🔴 |
| `D07.C04.W04.A02` | Dead-letter'ları incele | Operations | **—** | **—** | — | `dead_letter_records` | — | — | — | ❌ | ❌ |
| `D07.C04.W04.A03` | Yeniden işle | Operations | — | — | [`DeadLetterReprocessService`](../../src/veri_kalitesi/jobs/lifecycle.py#L30) — **çağıran yok** | `dead_letter_records` | →`REPROCESSED` | ✅ | U | ⚠️ | ❌ |
| `D07.C04.W04.A04` | Dead-letter'ı kapat | Operations | — | — | — | `dead_letter_records`.`status` | →`CLOSED` | — | — | ⚠️ | ❌ |
| `D09.C01.W01.A02` | Teknik hatadan sorun üret | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |
| `D12.C01.W01.A01` | Operatöre bildir | Sistem | — | — | `NotificationService` (çağrılmıyor) | — | — | — | U | ⚠️ | ❌ |

**İlk kırılma (kod ekseni) — `D07.C04.W04.A02` operatör inceleme.** Kuyruk
çekirdeği eksiksizdir: lease, heartbeat, üstel geri çekilme, deneme sayacı,
dead-letter kaydı ve yeniden işleme servisi kodda mevcuttur ve testleri vardır.
Kopan halka **operatör yüzeyidir**: job listeleme, dead-letter görüntüleme,
yeniden işleme ve kapatma için hiçbir endpoint veya ekran bulunamadı.

**İlk kırılma (runtime ekseni) — `D07.C03.W02.A01` işi sahiplenme, çok daha erken.**
[`create_persistent_job_runtime()`](../../src/veri_kalitesi/jobs/composition.py)
tanımlıdır ancak **hiçbir yerden çağrılmaz**; `PersistentJobWorker.run_forever()`
için entry point, konsol betiği veya daemon yoktur. Dolayısıyla retry, zaman
aşımı, lease geri alma ve dead-letter mantığının **hiçbiri çalışma zamanında
yürümez** — hepsi yalnız birim ve (skip-gated) entegrasyon testlerinde çalışır.

**Bağımlı etkiler:**

1. Kuyruğa giren her iş `AVAILABLE` durumunda süresiz kalır → akış 5 ve 10'un
   asenkron kolları tamamlanmaz.
2. Teknik hata hiç oluşmadığı için `execution_attempts` ve `dead_letter_records`
   tabloları üretimde hiç dolmaz → operatör yüzeyi olsa bile gösterecek veri olmazdı.
3. Teknik hatadan sorun üretimi yoktur → tekrarlayan bağlantı sorunları bir sahibe
   ulaşmaz; hedef modelin `D09.C01.W01.A02` adımı karşılıksızdır.
4. Bildirim üretilmediği için operatör dead-letter oluşumundan haberdar olmaz.
5. Ölçüm boşluğu işaretleme (`BR-D07-013`) yoktur → kaçan ölçümler skor
   yeterliliğine yansımaz, skor olduğundan güvenilir görünür.

**Kuyruğa yazma ile işleme arasındaki asimetri:** Enqueue tarafı runtime'da
gerçekten çalışır (`PostgreSQLJobQueueRepository` dev bileşimine bağlıdır),
dequeue tarafı hiç çalışmaz. Bu, `persistent_jobs` tablosunun zamanla birikmesi
anlamına gelir.

---

### Akış 7 — Kalite başarısızlığı, skor ve issue

**Zincir:** Sonuç kaydı ✅ → başarısız örnek ⚠️ → kapsam hesabı ✅ → teknik sağlık ✅ →
yeterlilik hükmü ✅ → kural skoru ⚠️ → toplulaştırma ⚠️ → veto ⚠️ → yayım ❌ →
katkı grafiği ✅ → risk ❌ → **sorun üretimi ❌** → tekilleştirme ❌ → SLA ❌ → bildirim ❌

| Hedef | Adım | Aktör | Ekran | API | Servis | Tablo | Geçiş | Audit | Test | Kod | RT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `D08.C01.W01.A01` | Kural sonucunu kaydet | Sistem | — | `GET /executions` içinde | `rule_execution_results` yazımı | `rule_execution_results` (8 sayaç) | →`RECORDED` | ✅ | U+I | ✅ | 🔴 |
| `D08.C01.W01.A02` | Sonuç geçmişini sorgula | Rule Author | — | — | — | `rule_execution_results` | — | — | — | ⚠️ | ❌ |
| `D08.C01.W02.A01` | Maskeli başarısız örnek üret | Sistem | — | — | `rule_test_results` önizlemesi | — | — | — | U | ⚠️ | ⚠️ |
| `D08.C01.W02.A02` | Başarısız örneği görüntüle | Issue Assignee | [/investigation](../../frontend/src/issues/InvestigationPage.tsx) | `GET /issues/{id}/investigation/evidence` | `IssueInvestigationEvidenceService` | (türetilmiş) | — | — | U | ✅ | ⚠️ |
| `D08.C02.W01.A01` | Ölçüm kapsamını hesapla | Sistem | — | — | `rule_execution_results` sayaçları | `population/eligible/evaluated_count` | — | — | U | ✅ | 🔴 |
| `D08.C02.W01.A02` | Teknik sağlık oranını hesapla | Sistem | — | — | `technical_error_count`, `unknown_count` | `rule_execution_results` | — | — | U | ✅ | 🔴 |
| `D08.C02.W02.A01` | Yeterlilik hükmü ver | Sistem | — | — | [`partial_score_policies.py`](../../src/veri_kalitesi/scoring/partial_score_policies.py) | `rule_execution_results`.`measurement_status` | →`QUALIFIED`\|… | ✅ | U | ✅ | ⚠️ |
| `D08.C03.W01.A01` | Kural skorunu hesapla | Sistem | — | — | [`ScoringService`](../../src/veri_kalitesi/scoring/service.py#L261) | **`quality_scores` tablosu yok** | — | ⚠️ | U | ⚠️ | ⚠️ |
| `D08.C03.W02.A01` | Boyut/dataset toplulaştır | Sistem | — | — | `ScoringService` | — | — | ⚠️ | U | ⚠️ | ⚠️ |
| `D08.C03.W02.A02` | Kritik kural vetosu | Sistem | — | — | `ScoringService` | — | — | ⚠️ | U | ⚠️ | ⚠️ |
| `D08.C03.W02.A03` | Domain/kurum toplulaştır | Sistem | [/](../../frontend/src/dashboard/DashboardPage.tsx) | `GET /dashboard/summary` | `DashboardQueryService` | — | — | — | U+E | ⚠️ | ⚠️ |
| `D08.C03.W03.A01` | Skoru atomik yayımla | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |
| `D08.C04.W01.A01` | Katkı grafiğini üret | Sistem | / (panel) | `GET /dashboard/summary` içinde | [`contributions.py`](../../src/veri_kalitesi/scoring/contributions.py) | `score_contribution_graphs` | — | ⚠️ | U+I | ✅ | ⚠️ |
| `D08.C04.W01.A02` | Skoru yeniden üret ve doğrula | Auditor | — | — | — | — | — | — | — | ❌ | ❌ |
| `D08.C05.W02.A01` | Risk derecesini hesapla | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |
| `D09.C01.W02.A01` | Tekilleştirme anahtarı üret | Sistem | — | — | [`create_for_trigger`](../../src/veri_kalitesi/issues/service.py#L165) — `uuid5(ns, digest(key))` | `issues`.`deduplication_key_digest` | — | ✅ | U+I | ✅ | ❌ |
| `D09.C01.W01.A01` | **Kalite ihlalinden sorun üret** | Sistem | — | — | [`IssueService.create_for_trigger`](../../src/veri_kalitesi/issues/service.py#L139) — **çağıranı yok**; uygunluk kapısı da tanımsız | `issues` | →`NEW` | ✅ | U+I | ✅ | 🔴 |
| `D09.C01.W02.A02` | Yinelenmeyi kaydet | Sistem | — | — | [`add_or_increment`](../../src/veri_kalitesi/issues/postgresql_repository.py#L234) — `occurrence_count + 1`, yinelenme ilişkisi | `issues`.`occurrence_count` | — | ✅ | U+I | ✅ | 🔴 |
| `D09.C03.W01.A01` | SLA hedeflerini belirle | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |
| `D12.C01.W01.A01` | Bildirim olayı yayımla | Sistem | — | — | `NotificationService` (çağrılmıyor) | — | — | — | U | ⚠️ | ❌ |

**İlk kırılma — `D09.C01.W01.A01` otomatik sorun üretimi.** Ölçüm zinciri sonuç ve
yeterlilik hükmüne kadar kod ekseninde eksiksiz yürür; `rule_execution_results`
tablosu ölçüm yeterliliği için gereken sekiz sayacı taşır.

Kırılmanın yeri düzeltilmelidir: **üretici servis vardır.**
`IssueService.create_for_trigger` (`issues/service.py:139`) güvenilir servis
bağlamı ister, atamayı çözer, deterministik tekilleştirme anahtarı üretir,
kapanmış sorun için yinelenme ilişkisi ve yeniden açma audit'i yazar;
`PostgreSQLIssueRepository.add_or_increment` (`:234`) bunu advisory lock ve
satır kilidiyle, audit outbox'la aynı transaction'da kalıcılaştırır. Her
ikisinin de birim ve PostgreSQL testleri vardır.

Eksik olan **çağrıdır**: `create_for_trigger` repo genelinde yalnız tanım ve
iki test çağrısı olarak geçer; başarısız bir ölçümü tetikleyiciye çeviren
üretim kodu yoktur. Dolayısıyla `deduplication_key_digest` ve
`occurrence_count` kolonları modellenmiş **ve doldurulabilir** durumdadır,
fakat onları dolduran akış hiç başlamaz.

**Köprü tek başına yeterli değil.** `RuleExecutionResult` üzerinde
`eligible_for_auto_issue` alanı hesaplanır ve kalıcılaştırılır
(`executions/models.py:168`), ancak `IssueTrigger` sözleşmesi bu alanı
taşımaz ve `create_for_trigger` onu doğrulamaz — `issues/` altında bu ad hiç
geçmez. Bir çağıran eklendiğinde, teknik hatalı veya `NOT_QUALIFIED`
ölçümlerin kalite sorunu üretmesini engelleyecek güven sınırı **hâlâ
tanımsız** olacaktır (`BR-D09-001`/`BR-D09-002`).

**İkinci kırılma — `D08.C03.W03.A01` skor yayımı ve `quality_scores` tablosunun
yokluğu.** Skor hesaplanır ama kalıcı bir skor kaydı yoktur; migration 13 yalnız
`score_contribution_graphs` tablosunu yaratır. Hedef modelin atomik yayım
davranışı (`BR-D08-010`) ve dönem karşılaştırması için gereken yayım kaydı yoktur.

**Bağımlı etkiler:**

1. Akış 8'in tamamı (inceleme→çözüm→doğrulama→kapatma) kod ekseninde eksiksiz
   çalışır ama **beslenmez**: sorunlar yalnız seed veriden veya elle gelir.
   Ölçüm zinciriyle sorun zinciri arasında bağlantı yoktur.
2. SLA hesaplaması için gereken sorun oluşum anı üretilmez → akış 8'de SLA kolu
   tamamen boştur.
3. Bildirim üretilmediği için hiçbir sahip kalite bozulmasından haberdar olmaz.
4. Risk derecelendirmesi (`D08.C05.W02.A01`) yoktur → önceliklendirme için sayısal
   dayanak üretilmez.
5. Skor kalıcılığı olmadığından trend, dönem karşılaştırması ve yeniden üretim
   doğrulaması yapılamaz.

**Runtime ek kırılması:** Sonuç kaydı ve kapsam/sağlık hesapları worker
çalışmadığı için runtime'da hiç tetiklenmez (`🔴`). Dashboard'da görünen skorlar
`create_development_app()` içinde üretilen seed verilerdir; gerçek ölçümden
gelmez.

---

### Akış 8 — Issue inceleme, çözüm, doğrulama, kapatma ve yeniden açma

**Zincir:** Sorun listele ✅ → ata ✅ → aday listesi ✅ → inceleme başlat ✅ → kanıt
göster ✅ → yorum ❌ → hipotez ❌ → çözüm kaydet ✅ → bekletme ❌ → doğrula ✅ →
kapat ✅ → yeniden aç ⚠️ → SLA/eskalasyon ❌

| Hedef | Adım | Aktör | Ekran | API | Servis | Tablo | Geçiş | Audit | Test | Kod | RT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| — | Sorunları listele | Issue Assignee | [/issues](../../frontend/src/issues/IssuesPage.tsx) | `GET /api/v1/issues` | `IssueQueryService` | `issues` | — | ✅ | U+I+E | ✅ | ⚠️ |
| `D09.C02.W01.A02` | Atama adaylarını listele | Data Steward | /issues | `GET /issues/{id}/assignment-options` | `issue_assignee_option_provider` | — | — | ✅ | U | ✅ | ⚠️ |
| `D09.C02.W01.A01` | Sorunu ata / yeniden ata | Data Steward | /issues | `POST /issues/{id}/assignment` | [`IssueService`](../../src/veri_kalitesi/issues/service.py#L110) | `issues`, `issue_history` | →`ASSIGNED` | ✅ | U+I | ✅ | ⚠️ |
| `D09.C02.W02.A01` | İncelemeyi başlat | Issue Assignee | /issues | `POST /issues/{id}/investigation` | `IssueService` | `issues`, `issue_history` | →`INVESTIGATING` | ✅ | U+I+E | ✅ | ⚠️ |
| `D09.C02.W02.A02` | İnceleme kanıtını göster | Issue Assignee | [/investigation](../../frontend/src/issues/InvestigationPage.tsx) | `GET /issues/{id}/investigation/evidence` | `IssueInvestigationEvidenceService` | (türetilmiş) | — | — | U | ✅ | ⚠️ |
| `D09.C02.W02.A03` | Sorun yorumu ekle | Issue Assignee | — | — | — | — | — | — | — | ❌ | ❌ |
| `D09.C05.W01.A01` | Kök neden hipotezleri üret | Sistem | — | — | [`lineage/impact.py`](../../src/veri_kalitesi/lineage/impact.py) (yalnız testte) | — | — | — | U | ⚠️ | ❌ |
| `D09.C05.W01.A02` | Hipotezi doğrula/reddet | Issue Assignee | — | — | — | — | — | — | — | ❌ | ❌ |
| `D09.C05.W02.A01` | Düzeltme önerisi üret | Sistem | — | — | `Recommendation` modeli (yalnız testte) | — | — | — | U | ⚠️ | ❌ |
| `D09.C06.W01.A01` | Düzeltme aksiyonu oluştur | Issue Assignee | — | — | — | — | — | — | — | ❌ | ❌ |
| `D09.C02.W03.A01` | Çözümü kaydet | Issue Assignee | /issues | `POST /issues/{id}/resolution` | `IssueService` | `issue_resolutions` | →`RESOLVED` | ✅ | U+I | ✅ | ⚠️ |
| `D09.C02.W03.A02` | Çözümü bekletmeye al | Issue Assignee | — | — | `IssueStatus.WAITING_FOR_RESOLUTION` (enum var) | `issues`.`status` | — | — | U | ⚠️ | ❌ |
| `D09.C02.W04.A01` | Bağımsız doğrula | Issue Verifier | /issues | `POST /issues/{id}/verification` | `IssueService` (aktör farkı zorlanır) | `issue_verifications` | →`VERIFIED` | ✅ | U+I | ✅ | ⚠️ |
| `D09.C02.W05.A01` | Sorunu kapat | Issue Verifier | /issues | `POST /issues/{id}/closure` | `IssueService` | `issues`, `issue_history` | →`CLOSED` | ✅ | U+I | ✅ | ⚠️ |
| `D09.C02.W05.A02` | Aynı bozulmada yeniden aç | Sistem | — | — | `IssueRelationshipResolver` (`RECURRENCE`) | `issue_relationships` | `CLOSED`→`NEW` | ✅ | U+I | ⚠️ | ❌ |
| `D09.C03.W01.A02` | SLA durumunu hesapla | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |
| `D09.C03.W02.A01` | SLA riskinde eskale et | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |

**Kod ekseninde ana zincir kopmaz.** Atama→inceleme→çözüm→doğrulama→kapatma
zinciri eksiksizdir; sekiz endpoint frontend'den kullanılır, altı akışta
transactional audit üretilir
([issues/service.py:304,399,496,604,718,805](../../src/veri_kalitesi/issues/service.py#L304)),
görev ayrılığı (çözen ≠ doğrulayan) servis katmanında zorlanır ve
`issue_verifications` tablosu ayrı aktör kimliği taşır.

**İlk kırılma — beslemede, zincirin kendisinde değil.** Akış 7'de saptandığı gibi
bu zincire sorun **girmez**. Sistemin en olgun iş akışı, kendisini tetikleyecek
mekanizmadan yoksundur.

**Zincir içi eksikler (kopma değil, incelme):**

| Eksik | Etkisi |
|---|---|
| Yorum yok (`D09.C02.W02.A03`) | İnceleme sırasındaki bulgular ve iletişim sorunla birlikte kalmaz |
| Bekletme yolu yok | `WAITING_FOR_RESOLUTION` enum değeri tanımlı ama ona geçiren endpoint yok; dış bağımlılıkla bekleyen sorun `INVESTIGATING`'de görünür |
| SLA hiç yok | Ne hedef, ne sayaç, ne eskalasyon; hangi sorunun geciktiği bilinemez |
| Teşhis ve öneri yalnız testte | `assess_impact` ve `Recommendation` zengin biçimde modellenmiş ama üretim yolunda çağrılmaz (**yeni doğrulama**) |
| Düzeltme aksiyonu yok | Çözüm serbest metin olarak kaydedilir; planlanan, sahipli ve izlenen bir iş üretilmez |

**Yeniden açma koşullu:** `IssueRelationshipResolver` ve `issue_relationships`
tablosu (`RECURRENCE` ilişki tipiyle) mevcuttur, ancak yeniden açmayı tetikleyen
şey aynı tekilleştirme anahtarıyla yeni bir bozulmadır — ve o bozulma tespiti
akış 7'de kopuktur. Yeniden açma mekanizması vardır ama **tetiklenemez**.

**Runtime ek kırılması:** Bütün zincir `DevelopmentIssueStore` (bellek içi)
üzerinde yürür; tek bir nesne altı mutasyon servisine birden bağlanmıştır ve
**audit üretmez**. Kod ekseninde altı akışta üretilen transactional audit,
çalıştırılabilir uygulamada hiç yazılmaz.

---

### Akış 9 — İstisna ve override

**Zincir:** **Talep ❌** → gerekçe/bitiş ❌ → maker-checker ❌ → ham ölçümü
değiştirmeme ❌ → bastırma ❌ → görünür etki ❌ → otomatik sona erme ❌ → erken iptal ❌
→ kalite borcu ❌ → audit ❌

| Hedef | Adım | Aktör | Ekran | API | Servis | Tablo | Geçiş | Audit | Test | Kod | RT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `D09.C04.W01.A01` | İstisna talep et | Data Owner (maker) | — | — | — | — | — | — | — | ❌ | ❌ |
| `D09.C04.W02.A01` | İstisna kararı ver | Governance Admin (checker) | — | — | — | — | — | — | — | ❌ | ❌ |
| `D09.C04.W02.A02` | Ham ölçümü değiştirmemeyi garanti et | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |
| `D09.C04.W03.A01` | Süresi dolanı otomatik sonlandır | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |
| `D09.C04.W03.A02` | Erken iptal et | Governance Admin | — | — | — | — | — | — | — | ❌ | ❌ |
| `D09.C04.W03.A03` | Aktif istisnaları görüntüle | Auditor | — | — | — | — | — | — | — | ❌ | ❌ |
| `D10.C04.W01.A01` | Kalite borcu kaydı oluştur | Data Steward | — | — | — | — | — | — | — | ❌ | ❌ |

**İlk kırılma — `D09.C04.W01.A01`, yani zincirin ilk adımı.** Domain modeli,
migration, servis, endpoint, ekran ve test — hiçbir halkada kod bulunamadı.
`Exception`, `Waiver` veya `Override` adlı bir varlık repo genelinde yoktur.
Kanıt güveni yüksektir (aşama 1 §3.23 ile tutarlı).

**Bağımlı etkiler:**

1. Bilinen ve kabul edilmiş bir bozulma için tek seçenek **kuralı pasifleştirmektir**
   (`D06.C02.W05.A02`). Bu, istisnadan farklı ve daha zayıf bir kontroldür:
   - Süre sınırı yoktur — pasifleştirme süresiz kalabilir.
   - Gerekçe ve telafi edici kontrol kaydı zorunlu değildir.
   - Görev ayrılığı yalnız kritik kurallarda gerekir.
   - Otomatik sona erme ve yeniden değerlendirme yoktur.
   - Ölçüm tamamen durur; hedef modeldeki "ham ölçüm korunur, yalnız uyarı
     bastırılır" ayrımı (`BR-D09-011`) kaybolur.
2. Kabul edilen risklerin kurumsal envanteri yoktur → hangi bozulmaların bilinçli
   olarak kabul edildiği görünmez.
3. Kalite borcu kaydı üretilmez → yükümlülük birikimi izlenemez.
4. Akış 2'de kırıcı şema değişikliğinin "istisnayla kabul" kolu karşılıksızdır.
5. Skor görünümünde istisna kapsamındaki bileşenin işaretlenmesi yapılamaz →
   skor, kabul edilmiş bir bozulmayı taşıyor olsa bile bunu göstermez.

**Not:** `retention/service.py` içindeki `LegalHoldService` kavramsal olarak
benzer bir "süreli, gerekçeli, yetkili istisna" desenini uygular ancak konusu
veri saklamadır, kalite ölçümü değildir; akış 9'un karşılığı değildir.

---

### Akış 10 — Rapor üretimi ve güvenli indirme

**Zincir:** Önizleme ✅ → talep ✅ → kuyruğa alma ⚠️ → **asenkron üretim ⚠️** →
maskeleme ✅ → bildirim ❌ → durum takibi ✅ → listeleme ✅ → güvenli indirme ✅ →
saklama süresi ⚠️ → dosya imhası ❌

| Hedef | Adım | Aktör | Ekran | API | Servis | Tablo | Geçiş | Audit | Test | Kod | RT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `D11.C03.W01.A02` | Rapor önizlemesini göster | Report Consumer | [/reports](../../frontend/src/reports/ReportsPage.tsx) | `GET /api/v1/reports/summary` | [`ReportPreviewService`](../../src/veri_kalitesi/reporting/service.py#L57) | — | — | ✅ | U+E | ✅ | ⚠️ |
| `D11.C03.W01.A01` | Rapor talep et | Report Consumer | /reports | `POST /api/v1/reports/` | [`ReportService`](../../src/veri_kalitesi/reporting/service.py#L340) | `reports` | →`PENDING` | ✅ | U+I+E | ✅ | ✅ |
| `D07.C03.W01.A01` | Üretim işini kuyruğa al | Sistem | — | — | `ReportJobHandler` + `PostgreSQLJobQueueRepository` | `persistent_jobs` | →`AVAILABLE` | ✅ | U+I | ✅ | ⚠️ |
| `D11.C03.W02.A01` | **Raporu asenkron üret** | Sistem | — | — | [`ReportWorker`](../../src/veri_kalitesi/reporting/worker.py#L74) — dev'de `inline_processing=True` | `reports` | →`GENERATING`→`READY` | ✅ | U+I | ⚠️ | ⚠️ |
| `D11.C03.W02.A02` | Rapor üretimini iptal et | Talep eden | — | — | — | — | — | — | — | ❌ | ❌ |
| `D11.C04.W01.A01` | Hassasiyet politikasını uygula | Sistem | — | — | `ReportExportPolicy` (fail-closed) | `reports`.`sensitivity_level` | — | ✅ | U | ✅ | ⚠️ |
| `D12.C01.W01.A01` | Rapor hazır bildirimi | Sistem | — | — | `NotificationService` (çağrılmıyor) | — | — | — | U | ⚠️ | ❌ |
| — | Rapor durumunu takip et | Report Consumer | /reports | `GET /api/v1/reports/{id}` | `ReportService` | `reports`.`status` | — | ✅ | U | ✅ | ⚠️ |
| `D11.C04.W02.A02` | Rapor listesini görüntüle | Report Consumer | /reports | `GET /api/v1/reports/` | `ReportService` | `reports` | — | ✅ | U+E | ✅ | ✅ |
| `D11.C04.W02.A01` | Raporu güvenli indir | Report Consumer | /reports | `GET /api/v1/reports/{id}/download` | `ReportService` | `reports`.`online_file_reference` | — | ✅ | U+E | ✅ | ⚠️ |
| `D11.C03.W03.A01` | Rapor zamanlaması tanımla | Report Consumer | **bağlanmamış** | `POST /api/v1/report-schedules` | `ReportScheduleService` | `report_schedules` | →`ACTIVE` | ✅ | FE-U | ⚠️ | 🔴 |
| `D11.C03.W03.A02` | Vadesi geleni tetikle | Sistem | — | `POST /report-schedules/trigger-due` | `ReportScheduleService` — **daemon yok** | `report_schedules`.`next_run_at` | — | ✅ | — | ⚠️ | 🔴 |
| `D13.C03.W01.A02` | Saklama süresini uygula | Sistem | — | — | `reports`.`expires_at`, `retention_policy_id` | `reports` | — | — | — | ⚠️ | ❌ |
| `D11.C04.W03.A01` | Süresi dolan dosyayı imha et | Sistem | — | — | **—** | — | →`EXPIRED` | — | — | ❌ | ❌ |

**İlk kırılma — `D11.C03.W02.A01` asenkron üretim.** `REPORT` iş tipi,
`ReportJobHandler` ve `ReportWorker` kodda mevcuttur; ancak çalıştırılabilir
bileşim `ReportService`'i `inline_processing=True` ile kurar — kuyruk atlanır ve
rapor istek içinde üretilir. Worker süreci de zaten çalışmaz (akış 6), dolayısıyla
kuyruk yolu seçilse rapor hiç üretilmezdi.

**İkinci kırılma — rapor içeriği.** Dev bileşimindeki veri sağlayıcı
`_DevDataProvider` **sabit kodlanmış dört satır** döndürür
([development.py:1109-1130](../../src/veri_kalitesi/api/development.py#L1109-L1130));
gerçek skor, sonuç veya sorun verisi okunmaz. Rapor üretilir, indirilir, audit'lenir
— ama içeriği sistemin ölçümleriyle ilgisizdir.

**Üçüncü kırılma — dosya yaşam sonu.** `reports.expires_at` ve
`retention_policy_id` kolonları modellenmiştir; imhayı yürüten iş kanıt
bulunamadı. Ayrıca `retention_policy_id`, **hiçbir migration'da bulunmayan** bir
`retention_policies` tablosuna işaret eder (**yeni doğrulama**, bkz. akış 13).

**Bağımlı etkiler:**

1. Rapor talep eden kullanıcı, üretimi bekleyen bir iş olarak izleyemez; büyük
   raporlar istek zaman aşımına takılabilir.
2. Rapor hazır bildirimi gitmez → zamanlanmış raporların alıcıları çıktıdan
   haberdar olmaz.
3. Zamanlama tanımlama yüzeyi: `reports/api.ts` içinde `fetchSchedules`,
   `createSchedule`, `deleteSchedule` **mevcuttur** ve `ReportsPage` bu props'ları
   tanımlar, ancak `ReportsRoute` bunları hiç bağlamaz. Kullanıcı bunun yerine
   `syntheticSchedules` varsayılanını — yani **sahte zamanlama listesini** — görür
   ([ReportsPage.tsx:747](../../frontend/src/reports/ReportsPage.tsx#L747)).
4. Hassas çıktılar süresiz erişilebilir kalır → hedef modelin `BR-D11-010`
   davranışı (dosya imha, metadata korunur) işlemez.

**Runtime ek kırılması:** Rapor kaydı gerçek PostgreSQL'e yazılır
(`PostgreSQLReportRepository` dev bileşimine bağlıdır) — bu, akışı kısmen gerçek
kılan az sayıdaki yoldan biridir. Ancak dosya deposu `/tmp/reports-dev`'dir.

---

### Akış 11 — Lineage ve etki analizi

**Zincir:** **Lineage olayı alımı ❌** → kolon düzeyi kenar ❌ → graf sorgulama ⚠️ →
aşağı akış etkisi ⚠️ → değişiklik simülasyonu ⚠️ → yönetişim projeksiyonu ✅ →
kanıt snapshot'ı ✅

| Hedef | Adım | Aktör | Ekran | API | Servis | Tablo | Geçiş | Audit | Test | Kod | RT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `D10.C01.W01.A01` | **Lineage olayını al ve kaydet** | Integration Service Account | — | **—** | [`lineage/events.py`](../../src/veri_kalitesi/lineage/events.py) (model) | **—** | — | — | U | ⚠️ | ❌ |
| `D10.C01.W01.A02` | Kolon düzeyi kenarı kaydet | Integration Service Account | — | — | `ColumnLineageEdge` (model) | — | — | — | U | ⚠️ | ❌ |
| `D10.C01.W02.A01` | Yukarı/aşağı akışı sorgula | Data Steward | — | — | — | — | — | — | — | ❌ | ❌ |
| — | Lineage kanıt snapshot'ını getir | Issue Assignee | [/investigation](../../frontend/src/issues/InvestigationPage.tsx#L377) | `GET /api/v1/lineage/snapshots/{id}` | [`PostgreSQLLineageEvidenceRepository`](../../src/veri_kalitesi/lineage/postgresql_lineage.py) | `lineage_evidence_snapshots` | — | — | U+I | ✅ | ✅ |
| — | Yönetişim projeksiyonunu getir | Issue Assignee | /investigation | `GET /api/v1/governance/{ref}/projection` | [`lineage/governance.py`](../../src/veri_kalitesi/lineage/governance.py) | `lineage_evidence_snapshots` | — | — | U+I | ✅ | ✅ |
| `D10.C02.W01.A01` | Aşağı akış etkisini hesapla | Sistem | — | — | [`assess_impact`](../../src/veri_kalitesi/lineage/impact.py) — **yalnız testte** | — | — | — | U | ⚠️ | ❌ |
| `D10.C02.W02.A01` | Değişiklik etkisini simüle et | Technical Steward | — | — | `impact.py` (yalnız testte) | — | — | — | U | ⚠️ | ❌ |

**İlk kırılma — `D10.C01.W01.A01` lineage olayı alımı.** Sistem lineage
**tüketebilir** (snapshot ve projeksiyon uçları çalışır, inceleme sayfasında
kullanılır) ama lineage **üretemez veya alamaz**: olay alım ucu, `lineage_events`
ve `lineage_edges` tabloları kanıt bulunamadı. Mevcut olan tek tablo
`lineage_evidence_snapshots`'tır (migration 14) — bu, gezilebilir bir graf değil,
önceden hazırlanmış kanıt paketlerinin saklandığı bir depodur.

**İkinci kırılma — `D10.C02.W01.A01` etki analizi (yeni doğrulama).**
[`lineage/impact.py`](../../src/veri_kalitesi/lineage/impact.py) zengin
bir model kümesi içerir: `ImpactComponent`, `ImpactSourcePolicy`, `TimelineEvent`,
`SimilarIncident`, `Recommendation`, `RecommendationPolicy`, `HumanRootCauseRecord`,
`CausalityStatus` ve `assess_impact` fonksiyonu. `lineage/__init__.py` bunları
export eder. Ancak `assess_impact`'in **tek çağıranı** `test_lineage_governance.py`
dosyasıdır — üretim yolunda hiçbir çağrı noktası yoktur.

**Bağımlı etkiler:**

1. "Bu bozulma kimi etkiliyor?" sorusu yanıtlanamaz → sorun önceliklendirmesi
   iş etkisinden yoksun kalır.
2. Akış 2'deki şema değişikliği etki simülasyonu karşılıksızdır → kırıcı değişikliğin
   neyi bozacağı önceden görülemez.
3. Akış 8'deki kök neden hipotezi üretimi beslenemez → inceleyene kanıta dayalı
   başlangıç noktası sunulamaz.
4. Akış 12 (data contract) için gereken tüketici listesi lineage'dan türetilemez.
5. Hedef modelin `BR-D10-004` kuralı (lineage yoksa etki `UNKNOWN`, sıfır değil)
   uygulanacak bir mekanizma bulamaz.

**Not — kısmi çalışan yol:** Aşama 1'in envanter dosyası bu alanı "API var, UI yok"
olarak kaydetmişti; kod kanıtı aksini gösterir — `InvestigationPage` her iki
endpoint'i de çağırır ([InvestigationPage.tsx:377-378](../../frontend/src/issues/InvestigationPage.tsx#L377)).
Bu iki uç, akış 11'in çalışan tek parçasıdır.

---

### Akış 12 — Data contract ihlali

**Zincir:** **Sözleşme taslağı ❌** → karşılıklı onay ❌ → aktivasyon ❌ → uyum ölçümü ❌
→ ihlal ilanı ❌ → sorun üretimi ❌ → tüketici bildirimi ❌ → geri kazanım ❌ →
sonlandırma ❌

| Hedef | Adım | Aktör | Ekran | API | Servis | Tablo | Geçiş | Audit | Test | Kod | RT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `D10.C03.W01.A01` | Sözleşme taslağı oluştur | Data Owner | — | — | — | — | — | — | — | ❌ | ❌ |
| `D10.C03.W01.A02` | Karşılıklı onayla | Her iki taraf Owner | — | — | — | — | — | — | — | ❌ | ❌ |
| `D10.C03.W02.A01` | Sözleşme uyumunu ölç | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |
| `D10.C03.W02.A02` | Uyum panosunu göster | Report Consumer | — | — | — | — | — | — | — | ❌ | ❌ |
| `D10.C03.W03.A01` | İhlali ilan et | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |
| `D09.C01.W01.A03` | Sözleşme ihlalinden sorun üret | Sistem | — | — | — | — | — | — | — | ❌ | ❌ |
| `D10.C03.W03.A02` | İhlali kapat, geri kazandır | Sistem/Owner | — | — | — | — | — | — | — | ❌ | ❌ |
| `D10.C03.W01.A03` | Sözleşmeyi sonlandır | Her iki taraf Owner | — | — | — | — | — | — | — | ❌ | ❌ |

**İlk kırılma — `D10.C03.W01.A01`, zincirin ilk adımı.** `DataContract` veya
`data_contract` adlı hiçbir sınıf, tablo, endpoint, ekran veya test repo genelinde
bulunamadı (`grep -rl` boş sonuç). Kanıt güveni yüksektir.

**Bağımlı etkiler:**

1. Üretici ile tüketici arasındaki kalite beklentisi sözlü/örtük kalır → ölçülebilir
   bir taahhüt yoktur.
2. Tüketici, bağlı olduğu verinin sözüne uyup uymadığını göremez → akış 11'deki
   lineage eksikliğiyle birleşince tüketici tarafı tamamen kör kalır.
3. Şema taahhüdü ihlali (akış 2) ve güncellik/hacim taahhüdü ihlali tespit edilemez.
4. Hedef modelin `D09.C01.W01.A03` adımı (sözleşme ihlalinden sorun üretimi)
   karşılıksızdır.
5. `ST-DataContract` durum makinesinin tamamı (`DRAFT`→`PENDING_ACCEPTANCE`→
   `ACTIVE`→`BREACHED`→`ACTIVE`/`TERMINATED`) uygulanacak bir varlık bulamaz.

---

### Akış 13 — Retention ve güvenli imha

**Zincir:** **Saklama politikası tanımla ❌** → onayla ❌ → kayıtlara uygula ❌ →
süresi doleni imha et ⚠️ → imha kanıtı ⚠️ → yasal muhafaza ⚠️ → muhafaza kaldırma ⚠️
→ arşivden geri çağırma ⚠️

| Hedef | Adım | Aktör | Ekran | API | Servis | Tablo | Geçiş | Audit | Test | Kod | RT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `D13.C03.W01.A01` | **Saklama politikası tanımla** | Governance Admin | — | **—** | `RetentionPolicy` (model) | **—** | — | — | U | ⚠️ | ❌ |
| `D01.C04.W01.A03` | Politikayı onayla | Security/Governance Admin | — | — | — | — | — | — | — | ❌ | ❌ |
| `D13.C03.W01.A02` | Saklama süresini kayıtlara uygula | Sistem | — | — | [`RetentionEvaluator.evaluate`](../../src/veri_kalitesi/retention/service.py#L271) | `reports`.`retention_policy_id` (dangling FK) | — | ⚠️ | U | ⚠️ | ❌ |
| `D13.C03.W02.A01` | Süresi dolan kayıtları imha et | Sistem | — | — | [`DisposalJobService.prepare_job`](../../src/veri_kalitesi/retention/disposal_service.py#L63) / [`record_result`](../../src/veri_kalitesi/retention/disposal_service.py#L171) | **—** | — | ⚠️ | U | ⚠️ | ❌ |
| `D13.C03.W02.A02` | İmha kanıtını görüntüle | Auditor | — | — | — | — | — | — | — | ❌ | ❌ |
| `D13.C04.W01.A01` | Yasal muhafaza uygula | Governance Admin | — | — | [`LegalHoldService.place_hold`](../../src/veri_kalitesi/retention/service.py#L77) | — | →`ACTIVE` | ⚠️ | U | ⚠️ | ❌ |
| `D13.C04.W01.A02` | Muhafazayı kaldır | Governance Admin | — | — | [`LegalHoldService.release_hold`](../../src/veri_kalitesi/retention/service.py#L134) | — | →`RELEASED` | ⚠️ | U | ⚠️ | ❌ |
| `D13.C04.W02.A01` | Arşivden geri çağır | Auditor | — | — | [`archive_recall_service.py`](../../src/veri_kalitesi/retention/archive_recall_service.py) | — | — | ⚠️ | U | ⚠️ | ❌ |
| `D11.C04.W03.A01` | Rapor dosyasını imha et | Sistem | — | — | — | `reports`.`expires_at` | →`EXPIRED` | — | — | ❌ | ❌ |

**İlk kırılma — `D13.C03.W01.A01` saklama politikası tanımı.** Servis katmanı
şaşırtıcı ölçüde olgundur: `LegalHoldService`, `RetentionEvaluator`,
`DisposalJobService` ve arşiv geri çağırma servisi yetki kontrolü (`_authorize_actor`,
`_authorize_scope`) ve audit hazırlığı (`_prepare_audit`) ile birlikte yazılmış,
dört ayrı birim test dosyası vardır. Kopan halka **kalıcılık ve yüzeydir**:
`retention_policies`, `legal_holds`, `disposal_jobs` tabloları hiçbir migration'da
yoktur; hiçbir endpoint veya ekran bulunamadı.

**Sarkan yabancı anahtar (yeni doğrulama):** İki tablo `retention_policy_id`
kolonu taşır — `data_processing_inventory_versions` (migration 03, `nullable=False`)
ve `reports` (migration 06). Bu kolonların işaret ettiği `retention_policies`
tablosu **hiçbir migration'da tanımlı değildir**. Yani veri modeli, var olmayan bir
politika kaydına zorunlu referans içerir.

**Bağımlı etkiler:**

1. Hiçbir kayda saklama süresi atanamaz → `retention_until` benzeri bir yaşam sonu
   işareti üretilmez.
2. İmha işi çalışacak politika bulamaz → hassas veri süresiz saklanır.
3. İmha kanıtı üretilmez → verinin zamanında imha edildiği denetimde gösterilemez.
4. Yasal muhafaza uygulanamaz → inceleme konusu veri korunamaz; tersine, imha da
   olmadığı için pratikte her şey saklanır (yanlış nedenle "korunmuş" durum).
5. Akış 10'daki rapor dosyası imhası bu zincire bağlıdır ve onunla birlikte kopar.
6. `data_processing_inventory_versions` tablosuna kayıt girilmesi, var olmayan bir
   tabloya `NOT NULL` referans gerektirdiği için veri bütünlüğü açısından
   tanımsızdır.

**Runtime ek kırılması:** Retention servisleri `SQLiteTransactionalAudit`
kullanır — PostgreSQL outbox'a değil. Çalıştırılabilir bileşimde hiçbir retention
servisi bağlı değildir.

---

## 4. Kök kırılma nedenleri

On üç akıştaki kırılmalar bağımsız eksiklikler değildir. Sekiz kök neden, akışların
tamamını açıklar. Aşağıdaki matris her kök nedenin kaç akışı birden kırdığını
gösterir.

| # | Kök neden | Kanıt | Kırdığı akışlar | Akış sayısı |
|---|---|---|---|---|
| **K1** | **Worker süreci hiç başlatılmıyor** — `create_persistent_job_runtime()` çağrılmıyor, `run_forever()` için entry point yok | [jobs/composition.py](../../src/veri_kalitesi/jobs/composition.py); `pyproject.toml`'da konsol betiği yok | 5, 6, 7, 10 | **4** |
| **K2** | **PostgreSQL repository'leri composition'a bağlı değil** — issue/kural/kaynak/skor repository'leri yalnız testlerde örnekleniyor | Aşama 1 §2.3 | 1, 3, 4, 7, 8 | **5** |
| **K3** | **Bildirim servisi hiçbir yerden çağrılmıyor** | `NotificationService` modül dışında sıfır çağrı | 2, 6, 7, 10 | **4** |
| **K4** | **Metadata keşfi HTTP yüzeyi yok** — keşfi tetikleyen endpoint/ekran bulunamadı. *(Servis orkestrasyonu vardır: `DataSourceService.discover_metadata` `:763`, `_diff_metadata` `:1559`; eksik olan yalnız yüzeydir.)* | 44 endpoint'in hiçbiri keşfe bağlı değil | 1, 2, 3, 4 | **4** |
| **K5** | **Zamanlayıcı süreci yok** — `SchedulingService.trigger_due` ([scheduling.py:303](../../src/veri_kalitesi/executions/scheduling.py#L303)) ve iki repository yazılmış ve testli; **çağıran daemon yok**. Ayrıca PG due sorgusunda claim/lock protokolü yok | [scheduling.py:218-343](../../src/veri_kalitesi/executions/scheduling.py#L218); [postgresql_scheduling.py:109](../../src/veri_kalitesi/executions/postgresql_scheduling.py#L109) | 5, 10 | **2** |
| **K6** | **Ölçüm ile sorun üretimi arasında köprü yok** — `IssueService.create_for_trigger` ([issues/service.py:139](../../src/veri_kalitesi/issues/service.py#L139)) tekilleştirme/yinelenme dâhil yazılmış ve testlidir; **üretim kodunda çağıranı yoktur**. Ayrıca `eligible_for_auto_issue` trigger sözleşmesine taşınmadığı için uygunluk kapısı da tanımsızdır | `create_for_trigger` için repo genelinde yalnız tanım + 2 test çağrısı | 3, 7, 8, 12 | **4** |
| **K7** | **Kalıcılık modellenmiş ama tablosu yok** — `quality_scores` (yalnız SQLite DDL'i olarak var), `score_publications`, `retention_policies`, `lineage_events`/`edges`, `schema_changes`, istisna ve sözleşme tabloları | migration taraması | 2, 7, 9, 11, 12, 13 | **6** |
| **K8** | **Servis var, yüzey yok** — retention, lineage etki analizi, dead-letter operasyonu, teşhis/öneri servisleri yazılmış ama endpoint/ekranı yok | akış 6, 8, 11, 13 tabloları | 6, 8, 11, 13 | **4** |
| **K9** | **Komut yüzeyi mevcut kontrolleri atlıyor** — veri kaynağı aktivasyonu gerçek servisi hiç çağırmaz; maker-checker, rol, kapsam ve audit devre dışı kalır. Kural oluşturma kapsam denetlemez; manuel çalıştırma kaynak/kural kapsamını doğrulamaz | `api/app.py:2017-2110`, `2120-2137`; `api/development.py:951-968`, `837-882` | 1, 4, 5 | **3** |

### 4.1 Kök nedenlerin akışlara dağılımı

| Akış | K1 | K2 | K3 | K4 | K5 | K6 | K7 | K8 | K9 |
|---|---|---|---|---|---|---|---|---|---|
| 1 — Kaynak onboarding | | ● | | ● | | | | | ● |
| 2 — Metadata/drift | | | ● | ● | | | ● | | |
| 3 — Profil/baseline | | ● | | ● | | ● | | | |
| 4 — Kural yaşam döngüsü | | ● | | ● | | | | | ● |
| 5 — Zamanlanmış çalıştırma | ● | | | | ● | | | | ● |
| 6 — Teknik hata/dead-letter | ● | | ● | | | | | ● | |
| 7 — Kalite/skor/issue | ● | ● | ● | | | ● | ● | | |
| 8 — Issue yaşam döngüsü | | ● | | | | ● | | ● | |
| 9 — İstisna | | | | | | | ● | | |
| 10 — Raporlama | ● | | ● | | ● | | | | |
| 11 — Lineage/etki | | | | | | | ● | ● | |
| 12 — Data contract | | | | | | ● | ● | | |
| 13 — Retention/imha | | | | | | | ● | ● | |

### 4.2 Gözlem

Kök nedenler üç kümede toplanır:

- **K1, K2, K3, K5, K6 — bileşim (composition) eksikliği.** İlgili kod
  yazılmış, test edilmiş ve doğru; yalnızca çalıştırılabilir uygulamaya
  bağlanmamış. Etkilediği akışların çoğunda kod ekseni `✅`, runtime ekseni
  `🔴` görünür. *(K6 bu gruba taşındı: sorun üretici servisi vardır, eksik
  olan onu çağıran köprüdür.)*
- **K4, K7, K8 — eksik yüzey ve eksik kalıcılık.** Zincirin bir halkası hiç
  yazılmamış (K7) veya kullanıcıya açılmamış (K4, K8).
- **K9 — atlanan kontrol.** Bu küme diğer ikisinden **niteliksel olarak
  farklıdır** ve raporun önceki sürümünde hiç yoktu. K1–K5'te bir adım
  gerçekleşmez; K9'da adım gerçekleşir, fakat **kuralsız** gerçekleşir.
  Kaynak aktivasyonu ikinci bir onaycı, rol, kapsam ve audit olmadan
  tamamlanır.

Ayrım önemlidir: birinci grupta sorun bağlantı, ikincide eksik yapı,
üçüncüde ise **var olan bir kontrolün devre dışı kalmasıdır**. Üçüncü grup
diğerlerinin çözülmesini beklemez ve tek başına kapatılabilir.

Bu ayrımın pratik sonucu: "kod var mı?" sorusu bir yeteneğin çalıştığını
göstermeye yetmez; tersine "endpoint var mı?" sorusu da yetmez. Bir yetenek
ancak kod, bağlantı **ve** kontrol zinciri birlikte varsa tamamdır.

---

## 5. Kesişen gözlemler

### 5.1 Audit tutarlılığı

| Gözlem | Kanıt |
|---|---|
| Audit, mimari olarak doğru yerde: servis katmanında, iş transaction'ıyla aynı session'da staged ediliyor | `issues/service.py` altı akışta `publish_pending()`; `rules`, `executions`, `jobs` benzer |
| API katmanında audit çağrısı yok — bu bir eksiklik değil, katman kararı | `app.py`'de `transactional_audit` grep'i sıfır sonuç |
| Ancak çalıştırılabilir uygulamada audit **hiçbir kalıcı yere yazılmaz** | `run_dev.py`'de prepared-event deposu `_FakePreparedRepo`, `store()` metodu `pass` |
| Scoring, synthetic ve retention hâlâ SQLite audit kullanıyor | `SQLiteTransactionalAudit` referansları |
| Sonuç | Kod ekseninde audit kapsaması iyi; runtime'da audit izi üretilmiyor |

### 5.2 Yetki tutarlılığı

| Gözlem | Kanıt |
|---|---|
| Yetkilendirme scope tabanlı (`permitted_source_ids`, `permitted_dataset_ids`, `can_view_enterprise`), merkezi izin kaydı yok | `identity/models.py` |
| Rol kontrolleri dağınık string karşılaştırmaları | `rules/service.py:402`, `audit/service.py:342`, `servicenow/service.py:837` |
| Görev ayrılığı **servis katmanında** üç yerde zorlanıyor: kural onayı (`rules/service.py:542-545`), kaynak aktivasyonu (`data_sources/service.py:487-488`), issue doğrulaması (`issues/service.py:646-649`) | ilgili tablolarda ayrı maker/checker kolonları; dört birim testi |
| Bu üçünden **biri çalışan üründe atlanıyor** — kaynak aktivasyonu endpoint'i gerçek servisi hiç çağırmıyor (K9) | `api/app.py:2073-2082` → `api/development.py:951-968` |
| Issue self-verification guard'ı yalnız `QUALITY_PASSED` dalında; çözen aktör kendi çözümü için başarısız/kısmi doğrulama girebiliyor | `issues/service.py:638` koşulu |
| Veritabanı düzeyinde maker ≠ checker zorlaması **hiç yok** | 14 migration'daki hiçbir `CheckConstraint` kolon-kolon karşılaştırması yapmıyor |
| Hedef modelin on iki görev ayrılığı çiftinden dokuzu karşılıksız | akış 9, 12, 13'te onay zincirlerinin hiç olmaması |
| Çalıştırılabilir uygulamada sekiz farklı dev profili var, fakat profil **istemci başlığıyla** seçiliyor | `api/identity.py:91` sekiz profil (`:117-181`); seçim `X-Development-User-Id` (`:246`) |
| Okuma yolunda kapsam backend'de gerçekten uygulanıyor; komut yolunda hiç uygulanmıyor | sorgu servisleri kararı reader'a taşıyor; komut route'ları aktör bağlamını porta iletmiyor |
| Sonuç | Yetki reddi okuma tarafında test edilebiliyor; komut tarafında denetlenecek bir karar noktası yok |

### 5.3 Test kanıtı tutarlılığı

| Gözlem | Kanıt |
|---|---|
| En olgun akışların (4, 8) hem birim hem entegrasyon hem E2E kanıtı var | `test_rules.py`, `test_issues.py`, `rules.spec.ts`, `issues.spec.ts` |
| PostgreSQL entegrasyon testlerinin **tamamı** ortam koşuluyla kapalı; bu oturumda koşuldu ve **92'sinin tamamı atlandı** | 10 dosyada `DATA_QUALITY_POSTGRES_TEST_URL`, `test_synthetic_postgresql_integration.py`'de `SYNTHETIC_POSTGRES_TEST=1`; `.env` gitignore'da |
| Kırık akışların çoğunda test de yok | akış 2, 9, 12: sıfır test dosyası |
| İlginç ters örnek: retention'ın **dört** birim test dosyası var ama tablosu ve yüzeyi yok | `test_retention*.py` × 4 |
| **Düzeltme:** zamanlama için backend testi vardır — `test_executions.py:643-1005` arasında 10 test (idempotent tetikleme, DST, outbox rollback dâhil) | `tests/unit/test_executions.py` |
| İki test boşluğu görünmez kılıyor: `test_fr_031_create_rule_without_dataset_scope_returns_403` adına rağmen `201` assert ediyor; `test_data_source_write_successful_activate_passivate_flow` onaysız aktivasyon için `200` bekliyor | `test_rule_api.py:405`, `test_data_source_api.py:360` |
| Sonuç | Test varlığı akışın yürüdüğünün göstergesi değil; ayrıca bazı testler **yeşil olduğu için** boşluğu gizliyor |

### 5.4 Modellenmiş ama bağlanmamış varlıklar

Aşağıdaki kolonlar ve enum değerleri veri modelinde mevcuttur ancak onları
dolduran/tetikleyen bir yol yoktur — modelin niyeti ile uygulamanın gerçeği
arasındaki farkın en somut kanıtı:

| Varlık | Nerede tanımlı | Dolduran yol |
|---|---|---|
| `issues.deduplication_key_digest` | migration 01 | Servis dolduruyor (`issues/service.py:165,179`) fakat servisi çağıran üretim kodu yok |
| `issues.occurrence_count` | migration 01 | Aynı — `add_or_increment` artırıyor (`:331`), çağıranı yok |
| `RuleExecutionResult.eligible_for_auto_issue` | `executions/models.py:168`, migration 12 | Yazılıyor, **hiç okunmuyor** — `issues/` altında bu ad hiç geçmiyor |
| `IssueStatus.WAITING_FOR_RESOLUTION` | `issues/models.py` | geçiren endpoint yok |
| `ExecutionMode.SHADOW` | `executions/models.py` | tetikleyen uç yok |
| `RuleStatus.REVIEW_REQUIRED` | `rules/models.py` | şema değişikliğinden tetiklenmiyor |
| `ExecutionStatus.SUPPRESSED_BY_EXCEPTION` | `executions/models.py:46` | Üreten yol yok; tek referans `test_scoring.py:327` |
| `reports.retention_policy_id` | migration 06 | hedef tablo yok (FK değil, doğrulanmayan metin kolonu) |
| `data_processing_inventory_versions.retention_policy_id` | migration 03 (`NOT NULL`) | Aynı — FK değil |
| `schedules.next_run_at` | migration 05 | `SchedulingService.trigger_due` okuyor, fakat servisi çağıran daemon yok |

---

## 6. Denetlenmeyen akışlar

Hedef modelde tanımlı olup bu denetimin on üç akışına girmeyen akışlar. Aynı
yöntemle değerlendirildi ancak adım tablosu düzeyinde açılmadı.

| Akış | Hedef | İlk kırılan adım | Kod | RT | Not |
|---|---|---|---|---|---|
| Bildirim üretimi ve teslimatı | `D12.C01`, `D12.C02` | Bildirim olayı yayımla | ❌ | ❌ | Servis ve kanal adaptörleri (`channel_adapters.py`) yazılmış; modül dışında hiç çağrılmıyor, tablosu yok. Teslimat izleme yaşam döngüsü hiç yok |
| Erişim gözden geçirme | `D02.C05` | Kampanya başlat | ❌ | ❌ | Kullanıcı/rol/izin tabloları hiç yok; gözden geçirilecek atama kaydı da yok |
| Kimlik, oturum ve yetkilendirme | `D02.C01`–`D02.C04` | Kullanıcı hesabı sağla | ⚠️ | ⚠️ | `BffSessionBoundary`, SQLite oturum deposu (`identity/sessions.py:112,350`) ve LDAP adaptörü (`identity/ldap.py:70`) kodda var, yalnız testlerde örnekleniyor; çalıştırılabilir yol istemcinin seçtiği `X-Development-User-Id` başlığı (sekiz profil). `users`/`roles`/`sessions` tablosu yok. Okuma kapsamı backend'de uygulanıyor, komut kapsamı hiç uygulanmıyor (K9) |
| Sentetik veri ve kontrol doğrulama | `D15` | Üretim çalıştırması | ⚠️ | ❌ | Servis, generator, oracle ve beş test dosyası var; CLI betiğiyle kullanılabiliyor (`scripts/generate_synthetic_test_data.py`), HTTP yüzeyi ve tablosu yok. Ground truth/doğruluk ölçümü kanıt bulunamadı |
| Operasyonel olay yönetimi | `D14.C03` | Olay aç | ❌ | ❌ | `incident_response/` modülü veri koruma ihlali odaklı; platform kesintisi yönetimi karşılığı değil. Tablo ve yüzey yok |
| Platform sağlığı ve kapasite | `D14.C01`, `D14.C02` | Bileşen sağlığını göster | ❌ | ❌ | Sağlık toplama, kuyruk görünümü, worker yönetimi ve bakım penceresi için kanıt bulunamadı |
| Yönetişim ve iş sözlüğü | `D01.C01`–`D01.C03` | Organizasyon birimi oluştur | ❌ | ❌ | Organizasyon, iş/veri domaini, sahiplik ve terim yönetimi için hiçbir halkada kod yok |
| Politika yönetimi | `D01.C04` | Politika taslağı oluştur | ⚠️ | ❌ | Politika **sürümü** birçok yerde damgalanıyor (`policy_version` kolonları), ancak politikayı tanımlayan/onaylayan/yürürlüğe alan bir yaşam döngüsü yok — sürümler kod içinde sabit |
| Sistem konfigürasyonu | `D01.C05` | Konfigürasyon değiştir | ❌ | ❌ | `system_config` tablosu ve yönetim yüzeyi yok; ayarlar kod ve dosya düzeyinde |

Bu dokuz akışla birlikte hedef modelin akış haritası tam olarak kapsanmıştır.

---

## 7. Kanıt sınırları

### 7.1 Bu denetimde yapılmayanlar

- **Hiçbir test koşulmadı.** Test varlığı dosya ve `pytestmark` düzeyinde
  doğrulandı; geçtiği doğrulanmadı.
- **Uygulama ayağa kaldırılmadı.** `RT` sütunundaki bütün değerlendirmeler kod
  okumasından çıkarıldı. Özellikle `🔴` işaretleri, canlı bir koşuyla
  doğrulanmamıştır.
- **Canlı PostgreSQL, Compose lab veya Playwright koşusu yapılmadı.**
- Denetim `agent/36h1-persistent-job-core` worktree'sinde yapıldı; `main` ile
  farkı ölçülmedi.

### 7.2 Bu denetimin değiştirmediği açık sorular

Aşama 1'in [work/01-Unresolved-Evidence-Questions.md](work/01-Unresolved-Evidence-Questions.md)
dosyasındaki on beş soru geçerliliğini korur. Bu akış denetimi doğrudan şu
sorulara bağlıdır:

| Soru | Bu belgeye etkisi |
|---|---|
| **Q-01** Üretim composition root repo dışında mı? | **Açık.** Yanıt "evet" ise K1, K2, K3, K5 kök nedenleri ve buna bağlı `🔴` işaretleri yeniden değerlendirilmelidir. K9 bu yanıttan etkilenmez: bypass route kodundadır, bileşimden bağımsızdır |
| **Q-04** `run_dev.py` gerçekten ayağa kalkıyor mu? | **Açık.** Akış 5, 6, 7, 10'daki runtime kırılmalarının canlı doğrulaması |
| **Q-05** Kuyruğa giren iş ne kadar bekliyor? | **Açık.** Akış 6'daki "iş `QUEUED`'da kalır" tespitinin ölçümü |
| **Q-13** Şema adı tutarsızlığı (`dq` vs `data_quality`) | **Kapandı.** Tutarsızlık statik olarak doğrulandı: `run_dev.py:11,21,33` audit outbox'ı `data_quality`'ye, `development.py:1332-1333` execution/job repository'lerini varsayılan `dq`'ya yönlendirir; `DatabaseSettings.schema` session'a `search_path` olarak uygulanmaz. Ayrıntı: [08-Existing-Schema-Gap-Analysis.md](08-Existing-Schema-Gap-Analysis.md) §3.2 |

### 7.3 Aşama 1 ile tutarlılık

Aşama 1 §4'teki sekiz akışın ilk-kırılma tespitleri bu belgede korunmuş, dördü
daha ince kanıtla genişletilmiştir:

| Akış | Aşama 1 tespiti | Bu belgedeki durum |
|---|---|---|
| A → 1 | Metadata keşfi | Aynı; adım düzeyinde 18 adıma açıldı |
| B → 4 | Dataset seçimi, sonra zamanlama | Aynı; ayrıca şablon kütüphanesi ve çakışma tespiti eksikleri eklendi |
| C → 7, 8 | Bildirim ve otomatik issue | Aynı; akış ikiye bölündü, kırılmanın besleme tarafında olduğu netleştirildi |
| D → 6 | Operatör inceleme (kod), worker (runtime) | Aynı; iki eksenli kırılma ayrı ayrı gösterildi |
| E → 2 | Metadata yenileme | Aynı; **yeni:** dağılım driftinin şema drifti olmadığı ayrımı belgelendi |
| F → 7 | `quality_scores` tablosu yok | Aynı; akış 7'ye entegre edildi |
| G → 9 | Tamamen yok | Aynı; **yeni:** pasifleştirmenin neden istisna yerine geçmediği açıklandı |
| H → 10 | Asenkron üretim, sabit veri | Aynı; **yeni:** rapor zamanlaması UI bağlantısızlığı ve dosya imhası eklendi |

Farklılık yoktur; genişletmeler yeni kanıtla gerekçelendirilmiştir.

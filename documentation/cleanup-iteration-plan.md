# Kanıta Dayalı Temizlik İterasyon Planı

Durum: uygulanmaya hazır plan  
Baseline tarihi: 2026-08-08  
Baseline dalı: `agent/36h1-persistent-job-core`

Bu planın hedefi satır sayısını düşürmek değil; doğrulanmış gereksiz kodu fiziksel
olarak kaldırmak, runtime sözleşmesini gerçeğe yaklaştırmak ve tekrar eden davranışı
daha az bakım noktasıyla ifade etmektir. Yeni özellik, uyumluluk katmanı, feature
flag, deprecated sarmalayıcı veya spekülatif soyutlama bu planın parçası değildir.

## 1. Kanıt sınırı

Plan yalnız aşağıdaki güncel kaynaklara dayanır:

- [`documentation/evidence/repository-inventory.json`](evidence/repository-inventory.json)
- [`documentation/evidence/repository-inventory.md`](evidence/repository-inventory.md)
- [`documentation/architecture.md`](architecture.md)
- [`documentation/api-data-and-workers.md`](api-data-and-workers.md)
- [`documentation/testing-and-quality.md`](testing-and-quality.md)
- [`documentation/known-gaps.md`](known-gaps.md)
- çalıştırılabilir kaynak, testler ve 2026-08-08 tarihinde yeniden çalıştırılan
  statik analiz araçları

`docs/` altındaki eski SRS, audit ve yol haritası belgeleri ürün niyeti için kanıt
sayılmaz. Dış dağıtım paketinin varlığına ilişkin sözlü varsayım da kodu korumaya
yetmez; somut çağıran paket, manifest veya sahiplik kaydı gerekir.

Mevcut worktree'deki `README.md`, `scripts/check_documentation.py`,
`tools/agent-loop/**`, `tests/unit/test_check_documentation.py` ve
`tools/agent-loop/contracts/**` değişiklikleri bu planın kapsamı dışındadır. Temizlik
commit'leri bunlarla karıştırılmaz.

## 2. Ölçülen baseline

| Sinyal | Baseline | Yorum |
|---|---:|---|
| Python fiziksel satır | 67.393 | Hedef metrik değildir |
| Frontend TS/TSX fiziksel satır | 21.130 | Testler dahil; hedef metrik değildir |
| Unit test | 1.616 geçti | `pytest -q tests/unit`; 55 saniye |
| Unit-test statement coverage | %76 | Tam/integration kapsamı değildir |
| Ruff C901, `src/` | 42 bulgu | Router içindeki nested endpoint'ler sonucu şişirebilir |
| Complexipy, eşik 15 | 66 bulgu | En yüksekler: dashboard 55, profile snapshot 51, issue router 49 |
| Vulture, güven >= 80 | 2 bulgu | İkisi de Protocol parametresi `business_days`; silme adayı değil |
| Knip | 1 dependency, 14 export, 18 type, 1 duplicate export | Testler yanlışlıkla ignore edildiği için aday listesi yeniden ölçülmeli |
| jscpd frontend | 95 clone, 1.114 duplicated line, %8,08 | Yapılandırılmış eşik %6; mevcut koşu başarısız |
| Mutation score | bilinmiyor | Mutation aracı projede kurulu değil |
| Runtime'da 503 veren kayıtlı API | 18 rota | OpenAPI yüzeyi runtime yeteneğini fazla gösteriyor |
| Varsayılan worker'da erişilemeyen iş tipi | 3 | `REPORT`, `SCORE_PUBLICATION`, `NOTIFICATION_DELIVERY` |
| Yalnız test/CLI ile erişilen modül grubu | 6 | Ürün kararı olmadan otomatik silinmez |

jscpd sonucu geçerlidir, fakat `.jscpd.json` içindeki desteklenmeyen `languages`
alanı uyarı üretmektedir. Knip sonucu ise test dosyalarını ignore ettiği için karar
kanıtı olarak henüz yeterli değildir. İki sorun İterasyon 0'da düzeltilmeden kod
silinmez.

Git geçmişi 115 commit ve kaynak dosyaların çoğu için tek ekleme noktası içeriyor.
Bu nedenle iki haftalık churn ve moved-lines oranı güvenilir biçimde çıkarılamadı;
uydurma bir baseline raporlanmayacaktır. Bu metrikler yeni temizlik commit'lerinden
itibaren değişiklik seti bazında tutulur.

## 3. Her değişiklik setinin zorunlu kayıtları

Her değişiklik setinden önce hedef sembol/dosya listesi dondurulur. Sonra şu kayıt
çıkarılır:

| Kayıt | Kabul kuralı |
|---|---|
| `files_touched_vs_required` | Kapsam dışı dosya yok |
| Silme envanteri | Her aday `silindi`, `korundu + kanıt` veya `yanlış pozitif` |
| Guard-and-Go | Silme yerine eklenen yeni guard/fallback sayısı sıfır |
| Kopya | Hedeflenen clone ailesi yok; toplam duplicated line artmıyor |
| Karmaşıklık | Dokunulan sembollerde cognitive/cyclomatic complexity artmıyor |
| Test | İlgili negatif test + mevcut ilgili paket geçiyor |
| Diff türü | Taşıma, silme, ekleme ve güncelleme ayrı raporlanıyor |

Üretim kodu silme değişiklik setinde yeni üretim satırı eklenmez. Extract
Function/Hook değişiklik setinde eklenen ortak kod, kaldırılan tekrarın altında
kalmalı; aksi halde yama reddedilir. Bu bir global LOC hedefi değil, seçilen
refactoring'in gerçekten eksiltici olduğunu doğrulayan yerel bir kontroldür.

## 4. İterasyon 0 — Ölçüm hattını düzelt

Amaç: yanlış pozitif veya eksik tarama üzerinden silme yapılmasını engellemek.

### Değişiklikler

1. `.jscpd.json` içinden desteklenmeyen `languages` alanını ve yinelenen
   `build/**` kaydını kaldır. Production frontend taramasının test/stories
   kapsamını açıkça belgeleyip aynı kapsamı sonraki koşularda koru.
2. `frontend/knip.json` içindeki Vitest dosyalarını dışlayan `ignore` kayıtlarını
   kaldır; Knip'in önerdiği redundant entry ve ignoreDependency kayıtlarını gerçek
   kullanım doğrulandıktan sonra temizle.
3. Baseline çıktılarını commit'e alınmayan `build/cleanup/` altında üret. Kaynak
   belgeye yalnız özet ve komut yaz; büyük tool çıktısı ekleme.
4. Python guard temizliği planlanacaksa yalnız dokunulacak modüller için mutation
   aracı seç ve baseline al. `killed / (killed + survived) < 0,70` ise guard silme
   değişiklik setini bloke et.

### Kabul

- `npm run dead-code` yapılandırma uyarısı üretmez ve test importlarını görür.
- `npm run copy-paste` bilinmeyen alan uyarısı üretmez.
- Vulture'daki iki `BusinessCalendar.add_business_days(..., business_days)`
  bulgusu yanlış pozitif olarak kaydedilir; parametre adları silinmez.
- Bu iterasyonda uygulama davranışı veya production kodu değişmez.

## 5. İterasyon 1 — Doğrulanmış ölü frontend yüzeyini kaldır

Refactoring türü: **Remove Dead Code** ve **Reduce Visibility**.

Knip düzeltilmiş kapsamla yeniden çalıştırıldıktan sonra, yalnız tanımından başka
üretim veya test referansı olmayan semboller fiziksel olarak silinir. İlk inceleme
adayları:

- `catalog/api.ts`: `refreshCsrfProof`, `getDiscoveryDiff`, `getDiscoveryScope`,
  `updateDiscoveryScope`
- `notifications/api.ts`: `fetchDeliveryDetail`, `fetchEventDetail`
- `scores/api.ts`: `fetchRuleScoreHistory`
- `scores/model.ts`: `reproductionFromApi`

Kendi dosyasında kullanılan fakat dışarı aktarılması gerekmeyen sembollerde kod
silinmez, yalnız `export` kaldırılır. İlk adaylar:

- `development/api.ts`: `DevelopmentUserApiError`
- `development/fetch.ts`: `getDevelopmentHeaders`
- `dashboard/model.ts`: `kpis`, `alerts`
- `reports/api.ts`: `downloadReportUrl`

`ProfilingPage` için named export korunur, yinelenen default export kaldırılır.
Knip'in bildirdiği 18 type aynı kuralla tek tek ayrılır: hiç referansı yoksa tip
silinir; dosya içi referansı varsa yalnız dış görünürlüğü daraltılır. Düzeltilmiş
Knip hâlâ `@babel/preset-typescript` bağımlılığını kullanılmıyor gösterirse paket
ve lockfile girdisi birlikte silinir.

### Negatif doğrulamalar

- Silinen sembol adları için `rg` sonucu sıfırdır.
- OpenAPI'de olmayan/erişilemeyen bir endpoint adına frontend istemci helper'ı
  kalmaz.
- Knip'te bu adaylar tekrar görünmez; yeni unused export oluşmaz.
- `npm test`, `npm run typecheck`, `npm run build` ve ilgili API testleri geçer.
- Silinen fonksiyonların yerine deprecated alias, no-op veya fallback eklenmez.

### Uygulama kaydı — 2026-08-08

Durum: uygulandı. Aday listesi, testleri kapsama alan düzeltilmiş Knip kapsamıyla
yeniden ölçülmüştür (`npx knip -c build/cleanup/knip.iter1.json`; çıktı commit'e
alınmayan `frontend/build/cleanup/` altında). Ölçüm 14 unused export, 18 unused
type, 1 duplicate export ve 1 unused devDependency bildirmiştir.

| Aday | Karar |
|---|---|
| `catalog/api.ts`: `refreshCsrfProof`, `getDiscoveryDiff`, `getDiscoveryScope`, `updateDiscoveryScope` | silindi |
| `notifications/api.ts`: `fetchDeliveryDetail`, `fetchEventDetail` | silindi |
| `scores/api.ts`: `fetchRuleScoreHistory` | silindi |
| `scores/model.ts`: `reproductionFromApi` | silindi |
| `development/api.ts`: `DevelopmentUserApiError` | `export` kaldırıldı |
| `development/fetch.ts`: `getDevelopmentHeaders` | `export` kaldırıldı |
| `dashboard/model.ts`: `kpis`, `alerts` | `export` kaldırıldı |
| `reports/api.ts`: `downloadReportUrl` | `export` kaldırıldı |
| `ProfilingPage` yinelenen `default` export | silindi; named export korundu |
| 17 unused type (catalog/dashboard/executions/issues/profiling/scores) | dosya içi referansı olduğu için `export` kaldırıldı |
| `rules/model.ts`: `RulePassivationRequest` | hiç referansı yok; silindi |
| `@babel/preset-typescript` | yanlış pozitif |

Silinen fonksiyonların tek kullanıcısı oldukları için birlikte kaldırılan
semboller: `notifications/model.ts` içindeki `eventFromApi`, `NotificationEvent`,
`EventDetailApiResponse` ve `scores/model.ts` içindeki `ScoreReproductionResult`,
`ScoreRuleHistoryApiResponse`. Bunlar kaldırılmasaydı yeni unused export
oluşacaktı.

`@babel/preset-typescript` kullanılmıyor değildir: `frontend/eslint.config.js`
içinde `parserOptions.babelOptions.presets` altında string olarak çözülmektedir ve
Knip bu referansı göremez. Paket ve lockfile girdisi korunmuş, bağımlılık
`frontend/knip.json` içinde `ignoreDependencies` olarak kaydedilmiştir.

Doğrulama sonuçları: silinen 14 sembol adı için `grep -rn` sonucu sıfırdır;
`npm run typecheck`, `npm test` (31 dosya / 280 test) ve `npm run build` exit 0
vermiştir; yeniden çalıştırılan Knip hiçbir unused export, unused type veya
duplicate export bildirmemektedir. `npm run lint` uyarı sayısı 739'dan 738'e
düşmüştür; `--max-warnings 0` nedeniyle koşu hâlâ başarısızdır, bu baseline
durumu bu iterasyonun kapsamı dışındadır.

Açık kalan ölçüm bulgusu: testler kapsama alındığında Knip
`@testing-library/user-event` paketini "unlisted dependency" olarak
bildirmektedir. Bu bir ölçüm hattı eksiğidir ve İterasyon 0 kapsamında
`frontend/knip.json` içindeki test `ignore` kayıtlarıyla birlikte ele alınır.

## 6. İterasyon 2 — Tekrarlanan davranışı iki sınırlı geçişte birleştir

Bu iterasyonda jscpd'deki 95 clone topluca kovalanmaz. İki yüksek yoğunluklu ve
aynı davranışlı aile seçilir.

### 2A. Report istemcisi hata işleme

Refactoring türü: **Extract Function**.

Hedef: `frontend/src/reports/api.ts` içindeki aynı `response.ok`, correlation-id,
yetki/teknik hata ve JSON dönüşüm blokları. Bir dosya-içi helper çıkarılır; endpoint
URL'leri, HTTP metodları ve dönüş tipleri aynı kalır. Helper başka API modüllerine
genişletilmez.

Kabul:

- `reports/api.ts` için jscpd'nin bildirdiği hedef clone blokları kaybolur.
- `ReportApiError.kind` ve `correlationId` testleri aynı kalır ve geçer.
- Yeni retry, fallback, varsayılan response veya exception yutma eklenmez.

#### Uygulama kaydı — 2026-08-08

Durum: uygulandı. `frontend/src/reports/api.ts` içine iki dosya-içi helper
çıkarılmıştır: `reportApiError(response)` yetki/teknik sınıflandırmasını ve
`X-Correlation-ID` okumasını, `requestReportJson<T>(url, init)` ise ortak istek
seçeneklerini, `response.ok` kontrolünü ve JSON dönüşümünü tutar. Her ikisi de
`export` edilmemiştir; başka API modülüne genişletilmemiştir.

| Kayıt | Sonuç |
|---|---|
| `files_touched_vs_required` | Yalnız `frontend/src/reports/api.ts` ve bu plan dosyası |
| Silme envanteri | Silme kapsamı yok; yedi endpoint'teki tekrar eden hata/JSON blokları helper'a taşındı |
| Guard-and-Go | Yeni guard/fallback/retry/varsayılan response sayısı sıfır; yutulan exception yok |
| Kopya | `reports/api.ts` için sekiz clone çiftinin tamamı kayboldu (8 → 0) |
| Karmaşıklık | Yedi endpoint fonksiyonu tek `return` ifadesine indi; helper'daki tek dallanma daha önce sekiz kez tekrarlanan aynı koşuldur |
| Test | `src/reports/api.test.ts`, `src/reports/model.test.ts`, `src/reports/ReportsPage.test.tsx` değişmeden geçti (3 dosya / 32 test); `tsc -b` exit 0 |
| Diff türü | Ekleme: helper'lar; silme: tekrarlanan bloklar; güncelleme: çağrı yerleri. Taşıma yok |

Eksiltici olma kontrolü: dosya 200 satırdan 147 satıra inmiştir (55 ekleme / 108
silme); eklenen ortak kod kaldırılan tekrarın altında kalmaktadır. jscpd'de
typescript duplicated line 327'den 237'ye (%7,10 → %5,21), frontend toplamı
1.122'den 1.032'ye düşmüştür. Bu düşüş 2B'nin 1.114 hedefiyle karıştırılmamalıdır;
2B ayrı bir değişiklik setidir ve bu kayıt kapsamında değildir.

Davranış eşdeğerliği: endpoint URL'leri, HTTP metodları ve dönüş tipleri aynıdır.
`triggerDownload` blob yolu olduğu için kendi `developmentFetch` çağrısını korur ve
yalnız `reportApiError` helper'ını kullanır; böylece indirme isteğine `Accept:
application/json` başlığı eklenmez. `Content-Type` yalnız gövdeli isteklerde
gönderilir, bu da önceki davranışla birebir aynıdır. `npx eslint` bu dosya için
değişiklik öncesi ve sonrası aynı dört baseline uyarısını bildirmektedir.

### 2B. Notification route yükleme döngüsü

Refactoring türü: **Extract Hook**.

Hedef semboller: `NotificationsRoute`, `NotificationPreferencesRoute`,
`NotificationChannelsRoute`, `NotificationDeliveriesRoute` (`frontend/src/App.tsx`).
Ortak olan fixture-state çözümleme, abort yaşam döngüsü ve loading/error/empty
durumu tek hook'a alınır. Notification'a özgü `markDeliveryRead` davranışı ortak
hook'a taşınmaz.

Kabul:

- Dört route'un hedef clone ailesi kaybolur.
- Hook yeni davranış dalı üretmez; dokunulan sembollerin karmaşıklığı artmaz.
- Abort sonrası state update yapılmadığını ve fixture-state davranışını mevcut
  testler doğrular; eksikse yalnız bu iki negatif test eklenir.
- Toplam frontend duplicated line 1.114'ün altına iner. Oranı %6'ya zorlamak bu
  iterasyonun hedefi değildir.

#### Uygulama kaydı — 2026-08-08

Durum: uygulandı. Ortak fixture-state çözümleme, loading/error/empty durumu ve
abort yaşam döngüsü `frontend/src/notifications/useNotificationRoute.ts`
hook'una çıkarılmış; dört notification route'u bu hook üzerinden üretim çağrı
yoluna bağlanmıştır. `markDeliveryRead` ve okundu işaretleme state güncellemesi
`NotificationsRoute` içinde kalmıştır.

| Kayıt | Sonuç |
|---|---|
| `files_touched_vs_required` | `frontend/src/App.tsx`, yeni hook ve iki negatif hook testi; ayrıca bu uygulama kaydı |
| Kopya | Dört route'un ortak yükleme clone ailesi kayboldu; jscpd bu route'lar arasında clone bildirmedi |
| Karmaşıklık | Fixture, abort ve sonuç durumu dalları dört route'tan tek hook'a taşındı; route'lara yeni davranış dalı eklenmedi |
| Test | `useNotificationRoute.test.ts` içindeki fixture-state loader engeli ve abort edilmiş sonucun state'i ezmemesi testleri geçti (1 dosya / 2 test); `tsc -b` exit 0 |
| Kalite ölçümü | jscpd toplam 993 duplicated line (%7,32) bildirdi; 1.114 sınırı karşılandı, hedef dışı olan %6 genel eşik nedeniyle komut non-zero kaldı |
| Diff türü | Ekleme: ortak hook ve iki negatif test; güncelleme: dört route'un hook composition'ı. Silme/taşıma yok |

## 7. İterasyon 3 — Phantom runtime yüzeyi için kanıtla veya sil kararı

Bu aşama refactoring değil, **Remove Dead Code / Remove Unreachable Surface**
kararıdır. Her capability grubu ayrı commit'tir; bütün gruplar tek yamaya alınmaz.

| Grup | Mevcut kanıt | Kanıt yoksa varsayılan işlem |
|---|---|---|
| Dashboard | Frontend rota var, persistent composition her çağrıda unavailable service kullanıyor | UI rota, API kaydı ve yalnız bu yüzeye hizmet eden adapter'ları sil |
| Profile snapshot/comparison | 4 kayıtlı rota, servis verilmemiş | Rota/client yüzeyini sil; domain saklama kararı ayrı verilir |
| Score reproduction | API ve frontend model/helper var, servis `None` | Uçtan uca erişilemeyen yüzeyi sil |
| Reports | 9 rota ve frontend sayfa var, üç servis de `None` | Tüm dikey yüzeyi veya somut wiring'i seç; 503 kabuğunu koruma |
| Lineage/governance | 2 rota, repository/reader `None` | Rota/client yüzeyini sil |
| Session logout | Dev runtime'da BFF yok | Yalnız desteklenen composition'da kaydet veya dev yüzeyinden fiziksel olarak kaldır |

Bir yüzeyi korumak için şu üç kanıtın tümü gerekir: çalışan composition çağrısı,
sahipli dağıtım manifesti ve uçtan uca test. “İleride lazım olabilir” kanıt değildir.
Kanıt yoksa conditional 503 guard, feature flag veya placeholder response eklemek
yasaktır.

Silme sonrası negatif test OpenAPI şemasında rotanın bulunmadığını, frontend route
testi de kullanıcının bozuk sayfaya yönlenemediğini doğrular. Migration geçmişi
değiştirilmez; tablo/drop kararı ayrı veri yaşam döngüsü çalışmasıdır.

## 8. İterasyon 4 — Worker composition borcunu kapat

Hedef semboller:

- `jobs.production.ProductionWorkerProviders`
- `jobs.production.create_production_worker`
- `jobs.entrypoint.main`

`ProductionWorkerProviders.secret_resolver` ve `execution_executor` alanları mevcut
factory tarafından okunmuyor. `SCORE_PUBLICATION` ve `NOTIFICATION_DELIVERY`
handler'ları ise unrelated issue provider nesnesinin varlığına bağlı; varsayılan
entrypoint bu nesneyi hiç vermiyor.

Önce dış composition çağıranı aranır. Somut dış çağıran yoksa uygulanacak
refactoring türü **Remove Dead Parameter** ve **Collapse Conditional**'dır:

1. Okunmayan provider alanlarını sil.
2. Varsayılan entrypoint'ten ulaşılamayan handler dalları için ürün kararı ver:
   gerçekten desteklenecek iş tiplerini doğrudan compose et; desteklenmeyecek iş
   tiplerinin handler/factory dallarını fiziksel olarak kaldır.
3. `REPORT` için de aynı kararı ver; `report_worker=None` kabuğunu kalıcı mimari
   sayma.

Bu değişiklikte “şimdilik no-op”, exception yutan adapter veya ek `if provider`
dalı kabul edilmez. Negatif test, kaldırılan `JobType` için kayıt/enqueue yolunun
bulunmadığını; pozitif test, korunan her iş tipi için varsayılan entrypoint'ten
handler'a erişilebildiğini doğrular.

### Uygulama kaydı — 2026-08-09

Durum: uygulandı. Repository dışında `ProductionWorkerProviders` veya
`create_production_worker(..., providers=...)` çağıranı bulunmadı. Remove Dead
Parameter ile provider kabuğu; Collapse Conditional ile provider'a bağlı handler
dalları kaldırıldı.

| İş tipi | Karar ve kanıt |
|---|---|
| `EXECUTION` | Korundu; varsayılan entrypoint doğrudan `ExecutionJobHandler` kaydına ulaşır. |
| `METADATA_DISCOVERY` | Korundu; production factory somut command adapter'ı koşulsuz verir. |
| `NOTIFICATION_DELIVERY` | Korundu; production API batch stager'ı bu tipi enqueue eder ve worker somut PostgreSQL delivery service handler'ını koşulsuz kurar. |
| `REPORT` | Kaldırıldı; rapor API yüzeyi önceki iterasyonda silinmişti, production composition çağıranı yoktu. Handler, factory parametresi ve kalıcı enqueue dalı fiziksel olarak silindi. |
| `SCORE_PUBLICATION` | Kaldırıldı; enqueuer/handler'ın testler dışında çağıranı yoktu. Job modülü ve factory dalı fiziksel olarak silindi. |

`create_persistent_job_runtime` artık yalnız üç desteklenen handler'ı doğrudan
kaydeder; opsiyonel handler parametresi veya `if provider` dalı yoktur. Default
entrypoint → production factory → runtime handler zinciri ile kaldırılan tiplerin
handler/enqueue yüzeyini doğrulayan hedef testler eklenmiştir. Fake/no-op,
exception yutan adapter veya fallback eklenmemiştir.

## 9. Karmaşıklık ve guard temizliği için sonraki adaylar

66 Complexipy bulgusunun tümünü tek iterasyonda düzeltmek yanlış soyutlama üretir.
Öncelik yalnız runtime'da erişilen, değişen ve yeterli test gücü olan sembollerdir.
İlk aday `PersistentJobWorker._execute_handler` (cognitive complexity 42) olsa da
Extract Method ancak mutation skoru en az %70 olduğunda uygulanır. Router register
fonksiyonları nested endpoint tanımları nedeniyle toplu parçalanmaz; araç skorunu
düşürmek tek başına gerekçe değildir.

Guard silme için uygulanacak refactoring türü **Remove Dead Code** veya **Replace
Conditional with Guard Clause** olarak önceden adlandırılır. Her guard için mutant
ve branch coverage kanıtı gerekir. Guard kaldırıldığında test hâlâ geçiyorsa guard
silinir; yeni fallback ile sarılmaz.

### Uygulama kaydı — 2026-08-09

Durum: uygulandı. `PersistentJobWorker._execute_handler` varsayılan production
entrypoint → worker composition zincirinden erişilen ilk aday olarak seçildi.
Mutation runner, decorator içeren sınıfları atlamayan `mutmut[patch]==2.4.5`
sürümüyle test extras'a sabitlendi; ölçüm yalnız bu yöntem veya nihai diff satırları
ve `tests/unit/test_persistent_job_worker.py` üzerinde çalıştırıldı.

İlk hedef testlerle mutation skoru %36,49 (27 killed / 47 survived) idi ve Extract
Method kapısı kapalı kaldı. Progress sınırları ve version zinciri, kesin timeout,
ownership-loss ve child-process-exit nedenleri için testler eklendikten sonra skor
%66,22'ye (49/74) yükseldi; yine refactoring yapılmadı.

Ana pipe poll'u payload ile birlikte EOF'u da çözdüğü halde hemen arkasındaki
`if not process.is_alive()` bloğu branch coverage'da çalışmıyor ve bloktaki 67–75
numaralı mutantların tümü survived kalıyordu. Önceden adlandırılan **Remove Dead
Code** refactoring'iyle bu ikinci process-exit yolu silindi; yerine guard, fallback
veya uyumluluk sarmalayıcısı eklenmedi. Hedef testler değişmeden geçti ve kalan
yöntem için mutation skoru %75,00 (48/64) oldu.

%70 kapısı açıldıktan sonra progress kaydı, inactive-job iptali, handler sonucu ve
lease yenileme dalları **Extract Method** ile ayrıldı. Sonuçlar:

| Kayıt | Sonuç |
|---|---|
| `files_touched_vs_required` | `worker.py`, hedef unit test, mutation test-extra kaydı ve bu canonical uygulama kaydı |
| Guard-and-Go | Silinen guard yerine yeni fallback/guard sayısı sıfır |
| Karmaşıklık | `_execute_handler`: 42 → 32 (guard silme) → eşik altı; final Complexipy raporu boş |
| Final mutation | Değişen satırlarda %83,33 (25 killed / 5 survived); 2 timeout formül dışında |
| Branch coverage | `worker.py` %81; kaldırılan guard satırları artık yok |
| Unit test | `test_persistent_job_worker.py`: 16 geçti |
| PostgreSQL entegrasyon | `test_postgresql_job_queue.py`: 31 geçti, skip yok |
| Üretim erişimi | Mevcut `dq-worker` entrypoint → production factory → persistent worker composition yolu korundu |

## 10. Tam doğrulama ve durma kriteri

Her iterasyon kendi hedef testlerini çalıştırır. Son iterasyon aşağıdaki tam kapı
ile kapanır:

```bash
pytest -q
ruff check .
ruff format --check .
mypy src
cd frontend
npm test
npm run typecheck
npm run build
npm run dead-code
npm run copy-paste
```

PostgreSQL entegrasyon koşusunda `skipped=0` aranır. Mutation yalnız dokunulan
Python modülleri için raporlanır ve guard değişikliği varsa %70 altı sonuç blokerdir.

Plan şu koşullarda tamamlanır:

1. Ölçüm araçları uyarısız ve tekrarlanabilir çalışır.
2. İterasyon 1 silme envanterinde kararsız aday kalmaz.
3. İki hedef clone ailesi kaldırılmış ve toplam duplicate line artmamıştır.
4. Her kayıtlı API rotası ve worker iş tipi ya varsayılan runtime'dan erişilebilir
   ya da fiziksel olarak kaldırılmıştır; sürekli 503/no-op yüzey kalmamıştır.
5. Kapsam dışı dosya, yeni fallback, spekülatif helper veya uyumluluk sarmalayıcısı
   eklenmemiştir.
6. Tam kalite kapısı geçmiştir.

Bu kriterlerden sonra yeni hotspot aramak bu planın parçası değildir. Yeni bir
statik analiz bulgusu veya ürün kararı ayrı temizlik iterasyonu açar.

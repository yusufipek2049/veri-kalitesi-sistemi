---
type: functional-audit-work
stage: "10 — İkinci Dilim Kararı"
scope: second-slice-decision
inputs:
  - 09-Slice-S1-Change-Inventory.md
  - 08-First-Slice-Decision.md
  - 07-Implementation-Waves.md
  - 06-Vertical-Slice-Candidates.md
  - ../04-Functional-Gap-Inventory.md
  - ../13-Implementation-Roadmap.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-05
---

# 10 — İkinci Dilim Kararı

> Bu karar, S1 veri kaynağı komut diliminin ardından uygulanacak **tek** dilimi
> seçer. Kaynak kodu değiştirmez ve ayrıntılı teknik plan yerine seçimin sınırını,
> gerekçesini ve ölçülebilir kabul kriterlerini dondurur.

---

## 1. Karar

**İkinci uygulanacak tek dilim: DS-02 — Kalıcı kaynak, kural ve sorun (GAP-001).**

Bu dilim `07-Implementation-Waves.md` içindeki birleşik **S2** kaydının yalnız
GAP-001 bölümüdür. S2'nin GAP-002 worker bölümü bu karara dahil değildir;
`13-Implementation-Roadmap.md` içindeki **DS-03 — Çalıştırma uçtan uca** olarak
bir sonraki ayrı dilimdir.

Başka bir deyişle sıra şöyledir:

```text
S1 veri kaynağı komut güvenliği
  → DS-02 kalıcı production composition
    → DS-03 worker ve çalıştırma uçtan uca
```

Bu ayrım yeni bir GAP veya yeni bir dilim üretmez. `13 §3` içinde zaten tanımlı
DS-02/DS-03 sınırını, "tek dilim" koşulu için esas alır.

---

## 2. Seçim gerekçesi

### 2.1 Bağımlılık grafiğinin sıradaki köküdür

`13-Implementation-Roadmap.md:97-103` DS-02'yi bağımsız `P0` kökü, DS-03'ü ise
DS-02'ye bağımlı gösterir. Aynı kalıcılık temeli katalog, otomatik sorun, skor,
zamanlama, saklama ve sentetik veri dilimlerinin de ön koşuludur. Worker'ı önce
kurmak, okuyacağı ve yazacağı production bileşimini henüz güvenilir kılmaz.

### 2.2 S1'in kurduğu ortak composition genişletilebilir

S1 uygulaması aşağıdaki production-capable temeli oluşturmuştur:

| Mevcut parça | Kod kanıtı | DS-02 kararı |
|---|---|---|
| Ortak application factory | `api/composition.py:create_application` | Yeni composition root yazılmayacak; genişletilecek |
| PostgreSQL preflight | `api/composition.py:preflight_database` | Gerekli DS-02 tablolarını da doğrulayacak |
| Veri kaynağı kalıcılığı | `PostgreSQLDataSourceRepository` | Yeniden yazılmayacak |
| Transactional outbox | `PostgreSQLTransactionalAudit` | Kural ve sorun mutasyonlarında da aynı desen kullanılacak |
| Kalıcı audit defteri | `PostgreSQLAuditRepository` | Yeni audit deposu veya fake hazırlanmayacak |
| Production/development girişleri | `api/production.py`, `api/development_runtime.py` | Aynı ortak factory'yi kullanmaya devam edecek |
| Tek şema ayarı | `ApplicationSettings.database.schema` | Bütün repository'lere açıkça aktarılacak |

Dolayısıyla ikinci dilimin doğru işi yeni altyapı icat etmek değil, hazır kalıcı
adapter'ları mevcut composition root'a bağlayıp çalışma yolundaki fake/sentetik
bağımlılıkları kaldırmaktır.

### 2.3 Repository çekirdeği zaten vardır

Kodda yeniden kullanılabilir kalıcı adapter'lar mevcuttur:

- `rules/postgresql_repository.py:PostgreSQLRuleRepository`
- `issues/postgresql_repository.py:PostgreSQLIssueRepository`
- `data_sources/postgresql_repository.py:PostgreSQLDataSourceRepository`
- `scoring/postgresql_contributions.py:PostgreSQLContributionGraphRepository`
- `executions/postgresql_repository.py:PostgreSQLExecutionRepository`
- `executions/query.py:ExecutionQueryService`

`PostgreSQLExecutionRepository.list_executions_for_sources` mevcut
`ExecutionReader` sözleşmesini uygular. Yeni bir execution read repository veya
ikinci bir persistence abstraction'ı gerekmez.

### 2.4 Tek ve gözlenebilir kullanıcı sonucu üretir

Dilim bittiğinde kaynak, kural ve sorun kayıtları uygulama yeniden kurulduğunda
durur; başlatılmış execution aynı PostgreSQL kaynağından listelenir; denetim ekranı
sentetik olay yerine gerçek audit olayını gösterir. Bunların tümü aynı kök nedeni
— runtime bileşiminin kalıcı adapter'lara bağlı olmamasını — kapatır.

### 2.5 Worker'ı aynı dilime katmak doğru değildir

GAP-002 yalnız wiring değildir. Worker entrypoint'i, servis kimliği, claim audit'i,
lease/heartbeat, retry, dead-letter, drain ve `workers` tablosu gibi ayrı durum
makinesi ve migration kararları içerir. Bunları DS-02'ye katmak:

- iki ayrı çıkış sonucunu tek teslimata bağlar;
- kalıcılık hatası ile worker yaşam döngüsü hatasını ayırmayı zorlaştırır;
- `GAP-002 → GAP-001` bağımlılık yönünü gizler;
- tek dilim sınırını aşar.

Bu nedenle DS-03 ancak DS-02 çıkış kapısı geçildikten sonra başlar.

---

## 3. Kapsam

### 3.1 Dahil

1. **Ortak production composition'ın tamamlanması**
   - Mevcut `create_application` içine PostgreSQL kural, sorun, katkı grafiği ve
     execution okuma bağımlılıklarının eklenmesi.
   - Production ve executable development girişlerinin aynı wiring'i kullanması.
   - API'nin fail-closed varsayılanlarının korunması; eksik servis için fake veya
     in-memory fallback yapılmaması.

2. **Kural kalıcılığı**
   - Mevcut rule query/create/mutation port'larının `PostgreSQLRuleRepository`
     kullanan gerçek domain servislerine/adaptörlerine bağlanması.
   - Kural state machine, maker-checker, backend permission ve source/dataset
     scope kontrollerinin repository çağrısıyla bypass edilmemesi.

3. **Sorun kalıcılığı**
   - Mevcut issue query, assignment, resolution, verification ve closure port'larının
     `PostgreSQLIssueRepository` kullanan gerçek servis zincirine bağlanması.
   - Sorun yaşam döngüsü ve optimistic concurrency kurallarının korunması.

4. **Execution okuma tutarlılığı**
   - `ExecutionQueryService` reader'ının sabit development demeti yerine mevcut
     `PostgreSQLExecutionRepository` olması.
   - Yazılan execution'ın liste/detail yolunda aynı şema ve aynı veri kaynağından
     okunması.

5. **Katkı grafiği ve dashboard bağı**
   - Mevcut `PostgreSQLContributionGraphRepository` ve mevcut dashboard servis
     zincirinin composition'a bağlanması.
   - S1'de kapsam dışı hizmetler için kullanılan `UnavailableDashboardService`in
     production yolunda başarı cevabı üreten bir fake'e çevrilmemesi; yalnız gerçek
     bağımlılıklarla değiştirilmesi.

6. **Transaction ve audit bütünlüğü**
   - Kapsamdaki her mutation için iş kaydı ile `audit_outbox` kaydının aynı
     transaction'da yazılması.
   - Outbox yazımı başarısızsa iş mutation'ının rollback olması.
   - Yayımın mevcut `PostgreSQLAuditRepository.append` yoluna gitmesi ve gerçek
     olayın `GET /api/v1/audit/events` üzerinden okunması.

7. **Şema ve startup doğrulaması**
   - `DATA_QUALITY_DATABASE_SCHEMA` değerinin bütün repository, outbox, audit
     ledger ve preflight kontrollerine açıkça aktarılması.
   - Migration head veya gerekli tablo eksikse production/development startup'ın
     fail-fast kapanması.
   - S1'in migration 15 ile eklediği audit tablosunun yeniden kullanılabilmesi;
     doğrulanmış yeni bir şema farkı bulunmadıkça yeni migration yazılmaması.

8. **Gerçek production yolunu doğrulayan testler**
   - Composition, restart/reconstruction, scope, transaction rollback, schema ve
     audit okuma testlerinin provision edilmiş PostgreSQL üzerinde çalışması.
   - Testte ayrı bir production wiring veya fake prepared-audit repository
     kullanılmaması.

### 3.2 Kapsam dışı

| Konu | Sahibi / gerekçe |
|---|---|
| Worker entrypoint, claim, heartbeat, lease, retry, dead-letter ve drain | DS-03 / GAP-002 |
| `workers` tablosu, job progress veya yeni job durumları | DS-03 migration'ı |
| Execution ekranına yeni başlat/iptal/ilerleme UX'i | DS-03 / GAP-017 |
| Yeni endpoint veya mevcut API sözleşmesinin yeniden tasarımı | GAP-001'de yüzey mevcut; bu dilim wiring dilimidir |
| Frontend ekran tasarımı | Mevcut kaynak, kural, sorun, execution ve audit ekranları doğrulama yüzeyidir |
| Yeni repository port'u veya ortak "generic repository" abstraction'ı | Mevcut domain port'ları yeterlidir |
| SQLite/in-memory sınıfların test desteğinden fiziksel olarak silinmesi | Yalnız executable/production composition'dan dışlanmaları gerekir |
| Kalıcı IAM, rol/izin yönetimi | DS-10 |
| Skor snapshot kalıcılığı ve skor API'si | DS-06 |
| Metadata keşfi, zamanlayıcı, bildirim ve operasyon ekranları | Sonraki bağımlı dilimler |
| Connection pool tuning, PgBouncer, HA, yedekleme/DR | Operasyonel external dependency |

### 3.3 Migration kararı

**Planlanan yeni migration yoktur.** DS-02'nin iş tabloları mevcut migration
zincirinde; kalıcı audit defteri S1 migration 15 ile eklenmiştir. Uygulama sırasında
yalnız gerçek kod/tablo sözleşmesi farkı kanıtlanırsa ayrı migration planı çıkarılır.
Composition veya test kolaylığı için yeni tablo eklenmez.

---

## 4. Kabul kriterleri

| # | Kabul kriteri | Zorunlu kanıt |
|---|---|---|
| K1 | Executable development ve production factory'leri aynı `create_application` yolundan `PostgreSQLDataSourceRepository`, `PostgreSQLRuleRepository`, `PostgreSQLIssueRepository`, `PostgreSQLContributionGraphRepository`, `PostgreSQLExecutionRepository` ve `PostgreSQLAuditRepository` örneklerini kurar | Composition testi + `app.state`/servis bağı doğrulaması |
| K2 | API üzerinden oluşturulan kaynak ve kural ile yaşam döngüsü değiştirilen sorun, ilk app/engine kapatılıp yeni app örneği kurulduktan sonra aynı API'den okunur | Gerçek PostgreSQL reconstruction testi |
| K3 | Başlatılmış bir execution `GET /api/v1/executions` sonucunda görünür; liste statik `DEVELOPMENT_EXECUTIONS` veya in-memory reader'dan gelmez | Aynı PostgreSQL'e yazma + API okuma entegrasyon testi |
| K4 | Kapsamdaki her başarılı mutation iş kaydı ile audit outbox'ı aynı transaction'da yazar; zorlanmış outbox hatasında iş kaydı değişmez | Her domain için rollback entegrasyon testi |
| K5 | Outbox olayı gerçek `PostgreSQLAuditRepository` ile yayımlanır ve yeni app örneğinde `GET /api/v1/audit/events` üzerinden görülür; repository protokol hatası sessiz başarıya dönüşmez | Publish + reconstruction + API testi |
| K6 | Kural ve sorun mutation'ları doğrudan repository bypass'ı kullanmaz; mevcut state machine, permission, maker-checker ve actor source/dataset scope kontrolleri backend'de çalışır | Yetkili, rolü eksik, scope dışı ve maker=checker negatif API testleri |
| K7 | Boş scope hiçbir kaynak/kural/sorun/execution sızdırmaz; frontend'den gönderilen owner/scope alanı backend kararının yerine geçmez | Negatif query ve command testleri |
| K8 | Bütün iş tabloları, `audit_outbox`, `audit_events` ve `alembic_version` tek yapılandırılmış şemadadır; repository constructor'larında örtük farklı şema kalmaz | Şema introspection testi |
| K9 | PostgreSQL yok, migration head eski veya DS-02 için gerekli tablo eksikse uygulama başlamaz; SQLite, fake veya in-memory runtime fallback'i oluşmaz | Preflight negatif testleri |
| K10 | Mevcut kural, sorun, execution ve audit frontend çağrıları yeni endpoint icat etmeden gerçek API sonuçlarını gösterir; başarılı boş/sentetik cevapla eksik wiring maskelenmez | Frontend contract testleri + backend E2E |
| K11 | CI çıkış kapısı gerçek PostgreSQL sağlayarak production composition testlerini çalıştırır; testlerin skip edilmesi başarı sayılmaz | CI test raporunda ilgili testler `passed`, `skipped` değil |
| K12 | Dilim worker çalıştırdığını veya kuyruğu tükettiğini iddia etmez; işin `QUEUED` kalabilmesi DS-03 açık kapsamı olarak görünür kalır | Kapsam/çıkış raporu kontrolü |

### 4.1 Çıkış kapısı

DS-02 yalnız şu tek ürün sonucu birlikte gözlendiğinde tamamdır:

> API'den oluşturulan kaynak ve kural ile değiştirilen sorun, uygulama yeniden
> kurulduktan sonra korunur; execution aynı PostgreSQL kaynağından listelenir;
> ilgili gerçek audit olayı denetim endpoint'inde görünür.

K1-K12'den herhangi biri eksikse dilim kapanmaz. Özellikle yalnız repository
entegrasyon testlerinin geçmesi, yalnız data-source composition'ın çalışması veya
worker'ın ayrıca ayağa kaldırılması DS-02 için yeterli değildir.

---

## 5. Uygulama giriş koşulu ve sonraki dilim

- S1'in ortak composition, PostgreSQL audit ve migration 15 temeli korunur.
- S1 için bekleyen gerçek PostgreSQL kabul testleri varsa DS-02 bunları atlayarak
  "tamamlandı" sayılamaz; aynı production yolunun tabanı oldukları için çıkış
  kapısında birlikte yeşil olmalıdır.
- DS-02 tamamlandıktan sonra uygulanacak tek dilim **DS-03 — Çalıştırma uçtan uca**
  olur. Worker, claim audit'i ve execution UI değişiklikleri ancak o dilimde ele
  alınır.


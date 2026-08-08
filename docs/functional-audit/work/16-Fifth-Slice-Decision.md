---
type: functional-audit-work
stage: "16 — Beşinci Dilim Kararı"
scope: fifth-slice-decision
inputs:
  - 15-Slice-DS04-Change-Inventory.md
  - 14-Fourth-Slice-Decision.md
  - 13-Slice-DS03-Change-Inventory.md
  - 07-Implementation-Waves.md
  - ../04-Functional-Gap-Inventory.md
  - ../13-Implementation-Roadmap.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-06
---

# 16 — Beşinci Dilim Kararı

> Bu belge ilk dört dilimden sonra uygulanacak **tek** beşinci dilimi seçer.
> Teknik değişiklik envanteri veya uygulama değildir; seçim gerekçesini, kapsam
> sınırını ve ölçülebilir kabul kriterlerini dondurur.

---

## 1. Karar

**Beşinci uygulanacak tek dilim: DS-05 — Otomatik sorun üretimi
(GAP-006).**

Tek ürün sonucu şudur:

> Kalıcı worker tarafından tamamlanan bir kural çalıştırmasının uygun kalite
> başarısızlığı, güvenilir servis kimliğiyle otomatik olarak atanmış ve kalıcı bir
> veri kalitesi sorununa dönüşür; aynı iş olayı yeniden işlendiğinde çoğalmaz,
> gerçekten tekrarlanan bozulma occurrence sayısını artırır ve uygun olmayan sonuç
> sorun üretmez. Yetkili kullanıcı da aynı backend scope kapısından manuel sorun
> açabilir.

Bağımlılık yolu:

```text
DS-02 kalıcı production composition
  → DS-03 çalıştırma uçtan uca
    → DS-05 otomatik sorun üretimi
      → DS-09 bildirim
        → DS-15 istisna / DS-16 SLA / DS-23 ServiceNow

DS-02 → DS-04 katalog ve metadata keşfi
```

DS-04 dördüncü teslim sırasındadır fakat DS-05'in hard dependency'si değildir.
DS-05'in giriş kapısı DS-03'ün gerçek execution/result/worker zinciridir.

## 2. Seçim gerekçesi

### 2.1 Sıradaki hard dependency karşılanmıştır

`13-Implementation-Roadmap.md` DS-05'i doğrudan DS-03'e bağlar. DS-03'ün kalıcı
job worker'ı ve gerçek execution sonucu olmadan otomatik sorun üretimi yalnız
fixture veya doğrudan servis testi olurdu. Artık sonuç, uygunluk işareti ve source/
rule kanıtı production yolunda üretilebildiği için bu köprü kurulabilir.

DS-04 katalog halkasını tamamlar; DS-05 ise ölçümden aksiyona geçişi açar. Beşinci
dilimde DS-04'ün profil, lineage veya şema değişimi devamlarına gitmek yerine
çalıştırma sonucunun sahipsiz kalmasını kapatmak daha yüksek bağımlılık değeri
üretir.

### 2.2 Eksik olan yeni bir issue domain'i değil, çalışan köprüdür

Repository'de aşağıdaki çekirdek zaten vardır:

- `executions/models.py:RuleExecutionResult.eligible_for_auto_issue` hesaplanan
  sonucun issue uygunluğunu taşır; SQLite ve PostgreSQL repository'lerinde
  kalıcılaştırılır.
- `issues/service.py:IssueService.create_for_trigger` trusted servis aktörü,
  atama, deterministik tekilleştirme, recurrence ve reopen kurallarını uygular.
- `issues/postgresql_repository.py:PostgreSQLIssueRepository.add_or_increment`
  advisory lock, satır kilidi ve transactional audit outbox ile atomik yazım
  yapar.
- `data_quality_issues`, `issue_history` ve `issue_relationships` tabloları ile
  issue sorgu ve yaşam döngüsü endpoint'leri production composition'da vardır.

Eksik olan execution sonucundan `IssueTrigger` üreten ve bu servisi production'da
çağıran dayanıklı adapter'dır. Repository genelinde `create_for_trigger` çağrısı
yalnız testlerde bulunur. Ayrıca `IssueTrigger` uygunluk bilgisini taşımadığı için
servis, kendisine yanlışlıkla iletilen uygunsuz bir kalite sonucunu bugün bağımsız
olarak reddedemez.

### 2.3 Production composition şu anda üretime hazır değildir

`api/composition.py` `IssueService` oluşturur fakat otomatik üretim için
`UnavailableIssueAssignmentResolver` bağlar. Bu doğru bir fail-closed davranıştır;
ancak DS-05 kabul kriterini karşılamaz. Dilim gerçek, deterministik ve scope-aware
assignment resolver ile trusted service-context provider'ı bağlamadan bitmiş
sayılmaz. Fake, no-op veya development store production yolu olamaz.

### 2.4 Kritik yolun en fazla devamını açar

DS-05 tamamlanınca DS-09 bildirim hattı ve DS-19 veri sözleşmesi doğrudan;
DS-15 istisna/kalite borcu, DS-16 SLA/eskalasyon ve DS-23 ServiceNow ise DS-09 ile
birlikte açılır. Bu merkeziyet DS-06 skor yayımından ve DS-07 zamanlamadan daha
yüksektir. `07-Implementation-Waves.md` de kritik yolu sorun üretimi → bildirim →
SLA/entegrasyon olarak tanımlar.

### 2.5 En küçük riskle kullanıcı tarafından gözlenebilir sonuç üretir

Issue state-machine'i, PostgreSQL repository'si, sorgu ekranı ve audit yolu
mevcuttur. Dilim yeni bir issue framework'ü kurmak yerine mevcut yapıya gerçek
girdi sağlar. Kullanıcı execution kaynağını, atanan kişiyi ve occurrence sayısını
aynı issue yüzeyinde görebilir; manuel açma da mevcut yaşam döngüsüne girer.

### 2.6 Diğer adayların neden şimdi seçilmediği

| Aday | Bu turda seçilmeme nedeni |
|---|---|
| DS-06 — Skor kalıcılığı | P1 ve değerlidir, fakat yalnız DS-12'yi açar; issue/bildirim/SLA kritik zincirini ilerletmez |
| DS-07 — Zamanlama | Çalıştırma sayısını artırır fakat mevcut sonuçların aksiyona dönüşmemesi sorununu çözmez |
| DS-08 — Profil/baseline | DS-03 ve DS-04'e bağlı daha büyük P2 dilimidir; ölçümden issue'a geçişten sonra gelir |
| DS-10 — Kimlik/rol/oturum | Geciktirilmemesi gereken P1 retrofitidir; ancak bu dilimde trusted `ActorContext` ve backend scope kapıları korunarak yeni bypass açılmaz |
| DS-13 — Şema değişimi | DS-04'e bağlıdır fakat P2'dir ve temel issue intake zincirini açmaz |

## 3. Kapsam

### 3.1 Dahil

1. **Dayanıklı execution → issue köprüsü**
   - Tamamlanan kalıcı execution ve `RuleExecutionResult` kayıtlarından veri-minimum
     `IssueTrigger` üretme.
   - Trigger teslimini execution sonucu ile atomik kaydetme veya eşdeğer kayıp
     önleyici kalıcı outbox/job deseni; proses-içi callback tek kanıt değildir.
   - Mevcut DS-03 queue/worker ve idempotency mekanizmasını yeniden kullanma; yeni
     message broker açmama.

2. **Uygunluk kapısı**
   - Kalite issue'su için `eligible_for_auto_issue = true`, gerçek başarısızlık ve
     desteklenen measurement sonucu koşullarını birlikte doğrulama.
   - `IssueTrigger` sözleşmesinin eligibility ve source-result referansını taşıması;
     adapter kadar `IssueService` girişinde de fail-closed doğrulama.
   - `PARTIAL`, shadow, iptal edilmiş, uygun olmayan veya geçmiş başarılı sonuçtan
     kalite issue'su üretmeme.
   - Execution-level teknik hata için kalite issue'sundan ayrı
     `TECHNICAL_ERROR` trigger ve source kapsamlı açık politika.

3. **İdempotency, tekilleştirme ve recurrence**
   - Aynı source event/job retry'ının ikinci occurrence oluşturmaması.
   - Farklı execution olaylarında aynı güvenli dedup anahtarına düşen gerçek
     bozulmanın yeni issue açmak yerine `occurrence_count` artırması.
   - Kapanmış kalite sorununun mevcut recurrence/reopen state-machine'i üzerinden
     yeniden açılması; doğrudan status yazımı yapılmaması.
   - Dedup anahtarında ve payload/audit içinde secret, örnek satır, alan değeri
     veya serbest hassas metin bulunmaması; dış yüzeyde yalnız digest/özet.

4. **Gerçek assignment ve servis kimliği**
   - Rule/dataset/source sahiplik verisinden deterministik atama yapan production
     resolver; doğrulanmamış request payload'ından assignee kabul etmeme.
   - Worker için trusted, süresi geçmemiş `ActorType.SERVICE`, doğru producer rolü,
     policy version, correlation ve hedef source/dataset scope'u.
   - Atanabilir kullanıcı bulunamazsa sahipsiz issue yaratmak yerine gözlenebilir,
     retry politikası tanımlı fail-closed sonuç.

5. **Manuel issue komutu**
   - `POST /api/v1/issues`: idempotency anahtarı, backend rol ve source/dataset
     scope kontrolü, doğrulanmış title/priority ve trusted assignment.
   - Manuel issue'nun `ActorType.USER` ile audit edilmesi; otomatik servis trigger'ı
     gibi gösterilmemesi ve mevcut issue state-machine'ine girmesi.
   - Mevcut `/api/v1/issues` GET ve investigation/assignment/resolution/
     verification/closure yollarının korunması.

6. **API ve frontend görünürlüğü**
   - `IssuesPage` üzerinde backend'in izin verdiği “Yeni Sorun” aksiyonu ve gerçek
     katalog/source seçicili form.
   - Issue listesi/detayında source execution, rule version, trigger type,
     assignee ve `occurrence_count` görünürlüğü.
   - API hatasında sentetik issue, başarılı fixture veya local-only mutation
     göstermeyen fail-closed frontend.

7. **Permission ve scope**
   - Otomatik üretimde yalnız trusted service actor; manuel üretimde user actor,
     açık `issue.create` rolü ve source/dataset scope.
   - Payload içindeki scope veya assignee bilgisinin actor yetkisinin yerine
     geçmemesi; dataset scope kontrolünün parent source ilişkisini de doğrulaması.
   - Frontend `available_actions` yalnız UX projection'ıdır; yetki kararı backend
     servisinde yeniden uygulanır.

8. **Transactional audit ve production composition**
   - Issue/history/relationship/occurrence değişikliği ile mevcut
     `DATA_QUALITY_ISSUE_TRIGGER_PROCESSED`, recurrence/reopen ve manuel-create
     audit outbox kaydının aynı transaction'da olması.
   - Audit stage hatasında issue değişikliğinin rollback olması; publish'in
     commit'ten sonra yapılması.
   - API ve worker'ın aynı PostgreSQL issue repository, gerçek assignment resolver,
     trusted context provider ve transactional audit yoluna bağlanması.

9. **Production-path test zinciri**
   - Gerçek execution completion → kalıcı trigger/job → worker → issue
     create/increment/reopen → issue GET/UI → audit outbox zinciri.
   - Restart, retry, concurrency, permission/scope negatifleri, audit rollback ve
     notification servisi olmadan issue kalıcılığı testleri.

### 3.2 Kapsam dışı

| Konu | Sahibi / gerekçe |
|---|---|
| Bildirim aboneliği, kanal teslimatı ve retry/reroute | DS-09 / GAP-007; DS-05 yalnız issue'yu üretir ve atar |
| İstisna ile issue bastırma ve kalite borcu | DS-15 / GAP-009 |
| SLA hedefi, süre hesabı ve eskalasyon | DS-16 / GAP-014 |
| Skor hesaplama, kalıcılık ve dashboard yayımı | DS-06 / GAP-008 |
| Schedule CRUD ve zamanlayıcı daemon | DS-07 / GAP-003 + GAP-015 |
| Veri sözleşmesi ihlalinden issue üretimi | DS-19 / GAP-010 |
| Kalıcı IAM tabloları, oturum ve rol atama yönetimi | DS-10 / GAP-022; mevcut trusted ActorContext kapısı korunur |
| ServiceNow ticket açma | DS-23 / GAP-023 |
| Issue investigation/resolution/verification state-machine'ini yeniden tasarlama | Mevcut DS-02 Faz B yolu korunur |

Notification gönderimi bu dilimin başarı kriteri değildir. Mevcut zorunlu
notification publisher çağrısı issue transaction'ı commit ettikten sonra hata
vererek sahte başarısızlık/retry üretmemelidir; DS-05 production yolu fake/no-op
publisher ile başarılı gösterilemez ve DS-09'a ait teslimat iddiasında bulunamaz.

### 3.3 Migration kararındaki düzeltme

Roadmap DS-05 için “migration gerekmez” der; bu ifade otomatik issue yolu için
büyük ölçüde doğrudur fakat tüm seçilen kapsam için yeterli değildir:

- `data_quality_issues.ck_issue_source_event_type` yalnız `QUALITY` ve
  `TECHNICAL`, `ck_issue_trigger_type` yalnız otomatik trigger türlerini kabul
  eder; manuel issue'nun gerçek kaynağını temsil eden değer yoktur.
- `data_quality_issues` manuel formun title bilgisini taşıyan bir kolona sahip
  değildir.
- Worker retry'ının aynı source event'i yeniden occurrence saymamasını mevcut
  satır tek başına kesin kanıtlayamıyorsa kalıcı event receipt/idempotency kaydı
  gerekir.

Bu nedenle change inventory, mevcut Alembic head sonrasında **en küçük forward
migration'ı** repository koduna karşı belirlemelidir. Eski migration değiştirilmez;
manuel olayı `QUALITY` gibi etiketlemek veya idempotency'yi yalnız proses belleğine
bırakmak kabul edilmez.

## 4. Kabul kriterleri

1. Gerçek worker'ın tamamladığı resmi ve `eligible_for_auto_issue=true` bir rule
   sonucu başarısız kayıt içerdiğinde kalıcı, atanmış issue üretilir.
2. `eligible_for_auto_issue=false`, shadow, iptal, `PARTIAL`/uygunsuz veya başarısız
   kayıt içermeyen sonuç kalite issue'su üretmez; bu kapı hem adapter'da hem issue
   servis sözleşmesinde doğrulanır.
3. Execution-level teknik hata kalite başarısızlığı gibi gösterilmez; açık politika
   izin veriyorsa source kapsamlı `TECHNICAL_ERROR` issue üretir ve kalite sayaç/
   kanıtı taşımaz.
4. Aynı source event'in worker retry/restart ile yeniden işlenmesi ikinci issue
   açmaz ve `occurrence_count` artırmaz. Farklı source event'teki aynı gerçek
   bozulma yeni issue açmadan sayacı tam bir artırır.
5. Aynı dedup anahtarındaki eşzamanlı iki farklı olay advisory/row lock altında tek
   issue bırakır; kayıp update veya çift kayıt oluşmaz.
6. Kapanmış kalite sorununun yeni ve daha güncel recurrence'ı mevcut izinli
   transition ile yeniden açılır; eski/gecikmiş olay state'i geriye götürmez.
7. Production assignment resolver trusted ownership verisinden aktif ve kapsamı
   uygun assignee seçer. Resolver/provider yoksa composition fail-fast olur;
   placeholder/fake ile başarı verilmez.
8. Yetkili kullanıcı `POST /api/v1/issues` ile kendi source/dataset kapsamında
   manuel issue açabilir. Yetkisiz scope/assignee, eksik idempotency anahtarı veya
   geçersiz içerik backend'de reddedilir.
9. Manuel issue USER, otomatik issue SERVICE aktörüyle audit edilir; issue,
   history/relationship/occurrence ve ilgili audit outbox kaydı aynı transaction'da
   yazılır. Audit stage hatasında iş değişikliği rollback olur.
10. Dedup anahtarının ham değeri, secret, sample row/field value ve serbest hassas
    metin job payload'ında, problem response'ta veya audit event'inde görünmez.
11. Kullanıcı issue ekranında otomatik/manüel kaynağı, execution/rule referansı,
    assignee ve occurrence sayısını gerçek API'den görür; frontend API hatasında
    sentetik başarı verisi göstermez.
12. DS-09 kurulmamışken issue üretimi ve ataması başarıyla tamamlanır; bildirim
    gönderildiği iddia edilmez ve unavailable notification adapter issue retry'ı
    doğurmaz.
13. Gerçek PostgreSQL ve production composition testi
    `execution result → durable trigger → worker → issue repository → audit outbox
    → GET /issues/UI` zincirini doğrular; doğrudan `IssueService` çağıran birim
    testi veya mock frontend E2E tek başına kabul kanıtı değildir.

## 5. Giriş ve çıkış kapısı

### Giriş kapısı

- DS-01'in trusted ActorContext ve backend command authorization sınırı korunmuş
  olmalıdır.
- DS-02'nin PostgreSQL issue repository ve transactional audit composition yolu
  çalışmalıdır.
- DS-03'ün gerçek executor/worker zinciri sonuç ve
  `eligible_for_auto_issue` alanını PostgreSQL'e yazmalıdır.
- Uygulama başında gerçek Alembic head ve DS-04 migration durumu doğrulanmalıdır.

DS-04 henüz yalnız plan seviyesindeyse DS-05 seçimi değişmez; ikisi ortak
composition/migration head üzerinde çakışmadan sıralanmalıdır. DS-03 production
çıkış kapısı geçmemişse DS-05 uygulaması **NO-GO**'dur.

### Çıkış kapısı

> Eşiği aşan uygun bir production sonucu atanmış issue üretir; aynı olay retry'da
> çoğalmaz, sonraki gerçek recurrence sayacı artırır, uygunsuz sonuç issue üretmez
> ve bütün zincir PostgreSQL, trusted scope ve transactional audit üzerinden
> kullanıcı ekranında gözlenir.

## 6. Karar

**Seçim: GO — DS-05 beşinci tek dilimdir.**

Bu karar uygulama yetkisi değildir. Bir sonraki adım DS-05 için gerçek migration,
tablo/kolon, servis, endpoint, frontend ve test değişikliklerini dosya/simge
düzeyinde çıkarmak; özellikle durable trigger idempotency'si, manuel issue şema
semantiği, assignment provider ve notification ayrımını repository koduna karşı
doğrulamaktır.

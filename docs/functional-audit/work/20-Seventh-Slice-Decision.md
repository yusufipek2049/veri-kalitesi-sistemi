---
type: functional-audit-work
stage: "20 — Yedinci Dilim Kararı"
scope: seventh-slice-decision
inputs:
  - 19-Slice-DS06-Change-Inventory.md
  - 18-Sixth-Slice-Decision.md
  - 17-Slice-DS05-Change-Inventory.md
  - 07-Implementation-Waves.md
  - ../04-Functional-Gap-Inventory.md
  - ../09-State-Machines.md
  - ../13-Implementation-Roadmap.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-06
---

# 20 — Yedinci Dilim Kararı

> Bu belge ilk altı dilimden sonra uygulanacak **tek** yedinci dikey dilimi
> seçer. Teknik değişiklik envanteri veya uygulama değildir; seçim gerekçesini,
> kapsam sınırını ve ölçülebilir kabul kriterlerini dondurur.

---

## 1. Karar

**Yedinci uygulanacak tek dilim: DS-09 — Kalıcı uygulama içi bildirim hattı
(GAP-007).**

Tek ürün sonucu şudur:

> Kalıcı bir sorunun oluşturulması veya atanması, aynı iş transaction'ında
> veri-minimum ve değişmez bir bildirim olayı üretir; mevcut kalıcı kuyruk bu
> olayı idempotent biçimde işler ve bildirim gerçek PostgreSQL kaydından yalnız
> doğru alıcının uygulama içi gelen kutusunda görünür.

Bağımlılık yolu:

```text
DS-02 kalıcı production composition
  → DS-03 kalıcı job/worker ve gerçek execution
    → DS-05 otomatik ve atanmış issue
      → DS-09 kalıcı bildirim olayı ve uygulama içi teslimat
        → DS-15 istisna / DS-16 SLA / DS-23 ServiceNow

DS-03 → DS-06 kalıcı skor yayımı → DS-12 asenkron rapor
DS-03 → DS-07 zamanlama
```

DS-09'un hard dependency'si DS-05'tir ve karşılanmıştır. DS-06'nın tamamlanması
bu seçimi değiştirmez; skor ve bildirim kolları birbirinden bağımsızdır.

## 2. Seçim gerekçesi

### 2.1 Açılmış issue zincirinin kullanıcıya ulaşmayan son halkasıdır

DS-05 uygun execution sonucunu kalıcı, tekilleştirilmiş ve atanmış issue'ya
dönüştürür. Ancak issue'nun veritabanında bulunması, atanan kullanıcının olaydan
haberdar olduğu anlamına gelmez. `IssueService.create_for_trigger` ve assignment
yolu bildirimi bugün issue transaction'ı kapandıktan sonra proses içinde çağırır;
otomatik üretim yolunda bildirim hatası yutulur. Bu davranış issue kalıcılığını
korur fakat bildirim olayı için kayıp penceresi bırakır.

DS-09 bu pencereyi kapatır: iş kaydı ile canonical notification event aynı
transaction'da yazılır; teslimat daha sonra ayrı ve dayanıklı state-machine ile
yürütülür. Böylece teslimat arızası issue'yu geri almaz, event yazım arızası ise
"issue oluştu fakat bildirim niyeti kayboldu" durumuna izin vermez.

### 2.2 Yeni bir bildirim domain'i yazmak gerekmemektedir

Repository'de yeniden kullanılacak çekirdek vardır:

- `notifications/models.py:NotificationEvent`, `Notification`, event/scope/status
  enum'ları ve veri-minimum doğrulamaları;
- `notifications/service.py:NotificationService`, trusted actor kapısı,
  alıcı çözümleme, dedup digest'i, listeleme ve okundu işaretleme davranışı;
- `notifications/channel_adapters.py:NotificationChannelPolicy` ile routing,
  idempotency ve suppression kuralları;
- `issues/service.py:IssueNotificationPublisher` port'u ve issue oluşturma/atama
  çağrı noktaları;
- `jobs/postgresql_repository.py` ile `PersistentJobWorker` kalıcı queue,
  lease, retry ve dead-letter altyapısı;
- PostgreSQL transactional audit/outbox deseni ve production composition root.

Bu yapı korunur. Yeni event bus, ikinci job queue, genel amaçlı workflow motoru
veya ayrı bir “notification microservice” kurulmaz.

### 2.3 Mevcut bildirim yolu production kanıtı değildir

Bugünkü uygulama içi repository `SQLiteNotificationRepository`'dir ve servis
imzası doğrudan `SQLiteTransactionalAudit` ile somutlaşmıştır. Alembic zincirinde
`notification_events`, `notification_channels`, `notification_subscriptions` ve
`notification_deliveries` tabloları yoktur. HTTP endpoint'i ve frontend bildirim
yüzeyi de bulunmaz.

`NotificationChannelDispatcher` idempotency ve suppression kayıtlarını proses
belleğinde tutar; `FakeChannelAdapter` yalnız sandbox/test adaptörüdür. Bunların
production composition'a bağlanması restart güvenliği veya gerçek teslimat kanıtı
sayılmaz. DS-09 PostgreSQL persistence, durable job ve gerçek uygulama içi kanal
ile çalışmadan tamamlanmış değildir.

### 2.4 Bağımlılık merkeziyeti yüksektir

`07-Implementation-Waves.md` bildirim dilimini S6b olarak DS-05 sonrasına koyar.
Bu dilim tamamlandığında:

- DS-16 SLA ve eskalasyon görünür bir teslimat hattına kavuşur;
- DS-15 istisna ve bastırma kararları bildirim üretimini güvenle etkileyebilir;
- DS-23 ServiceNow entegrasyonu mevcut teslimat/idempotency desenini kullanabilir;
- ileride rapor hazır, dead-letter ve operasyon olayları aynı canonical event
  sözleşmesine bağlanabilir.

Bu nedenle DS-09, yalnız yeni çalışma sayısını artıran DS-07'den daha fazla açık
iş akışını ilerletir.

### 2.5 Tek ve gözlenebilir production sonucu vardır

Bu karar DS-09'u haricî mesajlaşma projesine dönüştürmez. İlk production kanalı
PostgreSQL tabanlı `IN_APP` teslimattır. Kullanıcı üst çubuk/gelen kutusunda
bildirimi görür, okundu işaretler; operatör teslimat durumunu gerçek kayıttan
izler. Kurumsal SMTP, SMS, broker veya ticket sistemi mevcut değilse dilim yine
uçtan uca doğrulanabilir.

### 2.6 Diğer adayların neden şimdi seçilmediği

| Aday | Bu turda seçilmeme nedeni |
|---|---|
| DS-07 — Zamanlama | P1 ve uygulanabilir durumdadır; ancak yeni execution üretmek, mevcut atanmış issue'nun sahibine ulaşmaması sorununu çözmez. DS-09'dan sonraki güçlü adaydır |
| DS-10 — Kimlik, rol ve oturum | Kritik P1 retrofitidir fakat roadmap bunu üç alt dilime ayırır; “tek küçük dikey sonuç” sınırını aşar. DS-09 mevcut trusted `ActorContext` ve backend sahiplik kontrolünü genişletmeden kullanabilir |
| DS-12 — Asenkron rapor | DS-06 ile açılmıştır fakat P2'dir; rapor hazır olayının kullanıcıya ulaşması da DS-09'dan yararlanır |
| DS-08 — Profil/baseline | DS-03 ve DS-04 bağımlılıkları karşılanmış olsa da P2 ve daha geniş bir üretim/state-machine dilimidir |
| DS-13 — Şema değişimi | DS-04 sonrası açılmış P2 dilimidir; issue sahipliği ve bildirim kritik zincirini ilerletmez |
| DS-11 — Operasyon yüzeyi | Gerçek queue trafiği vardır fakat bildirim kayıp penceresini kapatmaz; dead-letter uyarıları daha sonra DS-09 olay sözleşmesini kullanacaktır |

## 3. Kapsam

### 3.1 Dahil

1. **Atomik canonical bildirim olayı**
   - İlk production tetikleyicileri olarak otomatik issue oluşumu ve
     `ISSUE_ASSIGNED` olayının desteklenmesi.
   - Olayın, onu doğuran issue/history/assignment değişikliğiyle aynı PostgreSQL
     transaction'ında yazılması.
   - Event ID, event type, kaynak nesne referansı, correlation ID, occurrence
     zamanı, policy version ve bounded veri-minimum payload'ın saklanması.
   - Tanımsız event type veya hassas payload tespitinde fail-closed red ve
     `NOTIFICATION_PAYLOAD_REJECTED` audit'i.

2. **PostgreSQL bildirim kalıcılığı**
   - Target modeldeki `notification_events`, `notification_channels`,
     `notification_subscriptions` ve `notification_deliveries` sahipliklerinin
     production PostgreSQL yolunda kurulması.
   - Mevcut SQLite repository'nin development/unit-test adapter olarak korunması;
     production composition veya kabul kanıtı yapılmaması.
   - Olay, alıcı/kanal bazlı delivery ve delivery job kaydının kayıp pencere
     bırakmayacak tek transaction veya aynı güvenceyi veren outbox deseninde
     hazırlanması.

3. **Alıcı ve abonelik çözümleme**
   - Issue assignment bildiriminde alıcının request payload'ından değil kalıcı
     issue/history assignee kaydından çözülmesi.
   - Kullanıcının yalnız kendi tercihini değiştirebilmesi; yönetici `.all`
     yetkisi olmadan başka kullanıcı aboneliğine erişememesi.
   - `ISSUE_ASSIGNED` gibi zorunlu olay tiplerinin kapatılamaması.
   - Abonesi olmayan isteğe bağlı event'in yine canonical event olarak kalması;
     sahte alıcı veya delivery üretilmemesi.

4. **Dayanıklı uygulama içi teslimat**
   - Mevcut `background_jobs` ve persistent worker'ın yeni notification-delivery
     handler ile yeniden kullanılması.
   - `ST-NotificationDelivery` geçişlerinin korunması:
     `PENDING → SENDING → DELIVERED | FAILED → UNDELIVERABLE`; alıcı aksiyonuyla
     `DELIVERED → READ`.
   - Aynı event/alıcı/kanal için idempotent tek delivery; retry/restart ve
     eşzamanlı worker yarışında çift teslimat oluşmaması.
   - `IN_APP` kanalının gerçek PostgreSQL delivery kaydı olması; proses içi log,
     fake adapter veya her zaman başarılı no-op olmaması.

5. **Kanal yapılandırma sınırı**
   - Sistem içi kanalın zorunlu ve production destekli fallback olması.
   - Kanal yapılandırmasında secret değer yerine yalnız `secret_ref` kabulü;
     response, audit ve hata mesajında secret'ın bulunmaması.
   - Bir haricî kanal için somut production adapter/provider yoksa kanalın
     `ACTIVE` edilememesi ve composition/configuration'ın fail-closed davranması.
   - Teslim edilemeyen kritik haricî bildirimin sistem içi kanala yönlendirilmesi;
     sistem içi delivery'nin kendisi sessizce başarılı sayılmaması.

6. **API ve frontend yüzeyi**
   - Kullanıcının kendi bildirimlerini listelemesi ve kendi delivery kaydını
     okundu işaretlemesi.
   - Kendi abonelik tercihleri; yönetici için kanal yönetimi ve operatör için
     delivery izleme/reroute yüzeyi.
   - App shell'de gerçek API'den gelen okunmamış sayaç ve Bildirimler/Gelen Kutusu
     ekranı.
   - Loading, empty, forbidden ve technical-error durumlarında fixture veya
     sentetik başarılı bildirim gösterilmemesi.

7. **Permission ve scope**
   - Gelen kutusunda trusted, süresi geçmemiş, policy-version uyumlu, standart
     USER `ActorContext`; sorgunun backend'de `recipient_user_id=actor_id` ile
     sınırlandırılması.
   - Başkasının notification ID'si için existence oracle üretmeden red.
   - Abonelik, kanal ve delivery yönetiminde mevcut rol/scope kararlarının
     backend'de uygulanması; frontend `available_actions` değerinin yalnız UX
     projection'ı olması.
   - Producer tarafında trusted SERVICE context ve persisted source/issue
     referansının doğrulanması; request'ten actor/alıcı kabul edilmemesi.

8. **Transactional audit**
   - `NOTIFICATION_EVENT_PUBLISHED` olayının canonical event ve doğuran iş kaydıyla
     aynı transaction'da stage edilmesi.
   - Subscription/channel mutation audit'inin ilgili kayıtla; delivery attempt ve
     `UNDELIVERABLE` audit'inin delivery state geçişiyle aynı transaction'da
     olması.
   - Audit stage hatasında ilgili iş değişikliğinin rollback olması; outbox
     publish'inin commit sonrasında yapılması.

9. **Production composition ve test zinciri**
   - API ve worker'ın aynı PostgreSQL notification repository, subscription/
     recipient resolver, gerçek IN_APP delivery adapter, transactional audit ve
     kalıcı queue yoluna bağlanması.
   - Migration preflight ve `REQUIRED_TABLES` kontrolünün yeni notification
     tablolarını kapsaması.
   - Gerçek zincirin
     `issue assignment → notification event → durable job → delivery state →
     GET /notifications → AppShell/inbox → READ → audit` olarak PostgreSQL ve
     production composition üzerinden doğrulanması.

### 3.2 Kapsam dışı

| Konu | Sahibi / gerekçe |
|---|---|
| Kurumsal SMTP/e-posta, SMS, Slack/Teams veya broker kurulumu | Dış bağımlılık; provider mevcutsa aynı porttan daha sonra bağlanır. Fake adapter production kanıtı değildir |
| ServiceNow/Jira ticket oluşturma ve geri bildirim | DS-23 / GAP-023 |
| Sorun SLA hedefi ve eskalasyon zamanlayıcısı | DS-16 / GAP-014; DS-09 yalnız ileride üreteceği olayı taşıyacak hattı kurar |
| İstisna/override kaynaklı suppression politikası | DS-15 / GAP-009; yalnız bildirim dedup/suppression penceresi korunur |
| Rapor hazır ve dead-letter event entegrasyonları | DS-12 ve DS-11; bu dilimde canonical event sözleşmesi hazırlanır fakat ilk tetikleyici issue'dur |
| Schedule CRUD ve scheduler daemon | DS-07 / GAP-003 |
| Kalıcı IAM/rol atama/oturum tabloları | DS-10 / GAP-022; mevcut trusted context ve backend sahiplik kapısı korunur |
| Yeni message broker, event bus veya notification microservice | Mevcut PostgreSQL queue/outbox yeterlidir |
| SQLite/in-memory repository, `FakeChannelAdapter` veya no-op provider'ı production'a bağlamak | Development/test yapısıdır; dilimin kabul zincirini karşılamaz |

### 3.3 Migration sınırı

Mevcut production head `20260806_19`'dur ve notification tablosu içermez. DS-09
yalnız yeni forward revision ile ilerler; migration 01–19 değiştirilmez. Kesin
tablo/kolon/FK/check/index tasarımı bir sonraki change inventory belgesinde gerçek
SQLAlchemy metadata ve state-machine'e karşı doğrulanmalıdır.

Mevcut SQLite `notifications` tablosu doğrudan production şeması olarak kopyalanmaz.
Canonical event ile recipient/channel delivery sahiplikleri ayrılır;
`NotificationStatus.UNREAD/READ` ile delivery'nin
`PENDING/SENDING/DELIVERED/FAILED/UNDELIVERABLE/REROUTED/READ` yaşam döngüsü tek
belirsiz statü alanında birleştirilmez.

## 4. Kabul kriterleri

1. Gerçek production yolunda otomatik oluşturulan veya yeniden atanan bir issue,
   issue/history değişikliğiyle aynı PostgreSQL transaction'ında tek canonical
   notification event üretir.
2. Event insert'i veya `NOTIFICATION_EVENT_PUBLISHED` audit stage'i başarısızsa
   doğuran issue mutasyonu rollback olur. Commit edilmiş event sonrasında kanal
   teslimatının geçici hatası issue state'ini geri almaz.
3. Event payload'ı yalnız bounded ID, enum, önem, correlation ve dönüş referansı
   taşır; secret, connection bilgisi, örnek satır/alan değeri, rule definition
   veya serbest kanıt metni taşımaz. Hassas payload fail-closed reddedilir.
4. `ISSUE_ASSIGNED` alıcısı kalıcı assignment/history kaydından çözülür ve zorunlu
   bu bildirim abonelikle kapatılamaz. Request body alıcı yetkisinin kaynağı
   değildir.
5. Aynı source event'in retry/restart veya eşzamanlı işlenmesi ikinci event ya da
   delivery üretmez ve occurrence sayısını yanlış artırmaz; aynı idempotency
   anahtarının farklı payload ile kullanımı conflict olur.
6. Delivery worker mevcut kalıcı queue'dan işi sahiplenir ve izinli state-machine
   geçişlerini izler. `PENDING → DELIVERED` kısa devresi, teslim edilmiş kaydın
   tekrar `FAILED` yapılması ve lease dışı mutation reddedilir.
7. IN_APP delivery gerçek PostgreSQL kaydı üzerinden `DELIVERED` olur. Proses
   belleğindeki dispatcher log'u, `FakeChannelAdapter`, mock repository veya
   doğrudan servis çağrısı production teslimat kanıtı sayılmaz.
8. Geçici teslimat hatası bounded retry'a girer; sınır aşıldığında delivery
   `UNDELIVERABLE` olur ve audit üretir. Kritik haricî kanal hatası varsa somut
   IN_APP fallback delivery'si oluşturulur; haricî provider yokluğu başarı gibi
   gösterilmez.
9. Kullanıcı `GET /notifications` ile yalnız kendi teslim edilmiş/okunmuş
   kayıtlarını görür; başka kullanıcının ID'sini listeleyemez, okuyamaz veya
   varlığını ayırt edemez. `POST /notifications/{id}/read` yalnız
   `DELIVERED → READ` geçişini yapar ve idempotenttir.
10. Kullanıcı zorunlu event tipini devre dışı bırakamaz; yalnız kendi isteğe bağlı
    aboneliklerini değiştirebilir. Başka kullanıcı aboneliği, kanal yapılandırması
    ve delivery yönetimi backend rol/scope kontrolü olmadan çalışmaz.
11. Kanal credential değeri hiçbir tabloda, API response'unda, problem detail'da
    veya audit payload'ında bulunmaz; yalnız doğrulanmış `secret_ref` saklanır.
    Somut production provider'ı olmayan haricî kanal aktif edilemez.
12. AppShell okunmamış sayacı ve Gelen Kutusu gerçek API sonucunu gösterir;
    loading/empty/401/403/503 durumlarında sentetik veya fixture bildirimi başarılı
    veri olarak render edilmez.
13. Event/business mutation, delivery state/audit ve read mutation kayıtlarının
    her biri kendi doğru PostgreSQL transaction sınırında atomiktir; audit outbox
    publish'i yalnız commit sonrasında çalışır.
14. Gerçek PostgreSQL ve production composition testi
    `execution sonucu → issue → assignment → notification event → durable job →
    IN_APP delivery → API/UI → READ → audit outbox` zincirini doğrular. Yalnız
    `test_notifications.py`, fake channel testi veya mock frontend E2E kabul için
    yeterli değildir.

## 5. Giriş ve çıkış kapısı

### Giriş kapısı

- DS-01'in trusted `ActorContext`, policy-version ve backend authorization sınırı
  korunmuş olmalıdır.
- DS-02'nin PostgreSQL composition ve transactional audit/outbox yolu çalışmalıdır.
- DS-03'ün kalıcı queue/worker/lease/retry altyapısı production yolunda olmalıdır.
- DS-05'in issue oluşturma, assignment ve idempotency zinciri gerçek PostgreSQL
  üzerinde çalışmalı; bildirimin ilk gerçek source event'i buradan gelmelidir.
- Uygulama başlangıcında gerçek Alembic head ve gerekli tablo preflight'ı
  doğrulanmalıdır.

Bu kapılardan biri fake/no-op publisher, SQLite production repository veya yalnız
doğrudan servis testiyle karşılanıyorsa DS-09 uygulaması **NO-GO**'dur.

### Çıkış kapısı

> Production worker'ın ürettiği atanmış issue, kayıp penceresi olmadan kalıcı bir
> notification event ve idempotent IN_APP delivery oluşturur; yalnız doğru alıcı
> bunu gerçek API/gelen kutusunda görüp okundu işaretleyebilir ve event, delivery
> ile audit kayıtları restart sonrasında doğrulanabilir.

## 6. Karar

**Seçim: GO — DS-09 yedinci tek dilimdir.**

Bu karar uygulama yetkisi değildir. Bir sonraki adım DS-09 için değişecek tablo,
kolon, repository, servis, durable job, endpoint, frontend ve testleri gerçek
dosya/simge düzeyinde çıkarmak; özellikle issue transaction'ına event staging,
delivery state-machine, IN_APP production adapter, permission/sahiplik ve
composition fail-fast sınırlarını repository koduna karşı doğrulamaktır.

---
type: functional-audit-work
stage: "12 — Üçüncü Dilim Kararı"
scope: third-slice-decision
inputs:
  - 11-Slice-DS02-Change-Inventory.md
  - 10-Second-Slice-Decision.md
  - 07-Implementation-Waves.md
  - 06-Vertical-Slice-Candidates.md
  - ../04-Functional-Gap-Inventory.md
  - ../13-Implementation-Roadmap.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-05
---

# 12 — Üçüncü Dilim Kararı

> Bu belge ilk iki dilimden sonra uygulanacak **tek** üçüncü dilimi seçer.
> Teknik değişiklik envanteri veya uygulama değildir; seçim gerekçesini, kapsam
> sınırını ve ölçülebilir kabul kriterlerini dondurur.

---

## 1. Karar

**Üçüncü uygulanacak tek dilim: DS-03 — Çalıştırma uçtan uca
(GAP-002 + GAP-017).**

Tek ürün sonucu şudur:

> Yetkili kullanıcı arayüzden bir çalıştırma başlatır; talep ve iş aynı kalıcı
> transaction zincirinde kuyruğa girer; production worker işi sahiplenip kural
> sonucunu PostgreSQL'e yazar; kullanıcı aynı ekranda terminal durumu ve sonucu
> görür veya çalıştırmayı güvenli biçimde iptal eder.

Bu seçim `10-Second-Slice-Decision.md` içinde dondurulan sırayı devam ettirir:

```text
DS-01 komut güvenliği
  → DS-02 kalıcı production composition
    → DS-03 çalıştırma uçtan uca
```

DS-03, `07-Implementation-Waves.md` içindeki S2'nin kalan GAP-002 parçasını ve
çalıştırmanın kullanıcı tarafından başlatılıp iptal edilmesini sağlayan GAP-017'yi
tek gözlenebilir akışta birleştirir.

---

## 2. Seçim gerekçesi

### 2.1 Hard dependency artık karşılanmıştır

GAP-002, GAP-001'e bağımlıdır. DS-02 ile PostgreSQL repository'leri, gerçek
execution okuma yolu, transactional audit ve ortak production composition
kurulmuştur. Worker'ın yazacağı kalıcı depo ve kullanıcının sonucu okuyacağı API
yolu artık vardır. Bu nedenle dependency grafiğindeki sıradaki kök DS-03'tür.

### 2.2 En büyük runtime kopukluğunu kapatır

`PostgreSQLExecutionStartService.start_manual` execution ile `EXECUTION` işini
aynı transaction'da oluşturabilir. Ancak `jobs/composition.py` içindeki
`create_persistent_job_runtime` için executable çağıran yoktur ve
`PersistentJobWorker.run_forever` production sürecinde başlamaz. Sonuç olarak
başlatılan işler `QUEUED` kalır. DS-03 yeni bir yan özellik değil, var olan
ölçüm zincirinin çalışmasını sağlayan eksik runtime halkasıdır.

### 2.3 Mevcut çekirdek büyük ölçüde yeniden kullanılabilir

Repository'de aşağıdaki production bileşenleri hazırdır:

- `jobs/composition.py:create_persistent_job_runtime`
- `jobs/worker.py:PersistentJobWorker`
- `jobs/postgresql_repository.py:PostgreSQLJobQueueRepository`
- `jobs/handlers.py:ExecutionJobHandler`
- `executions/postgresql_repository.py:PostgreSQLExecutionRepository`
- `api/postgresql_execution.py:PostgreSQLExecutionStartService` ve
  `PostgreSQLExecutionCancelService`
- migration 08–10'daki kalıcı iş, retry, lease ve deadline tabloları/kolonları

Yeni generic queue abstraction'ı, ikinci bir execution repository veya in-memory
production worker yazılması gerekmez. Değişiklikler entrypoint, eksik transaction
garantileri, hedef durum görünürlüğü ve API/UI wiring'i üzerinde yoğunlaşır.

### 2.4 Sonraki dilimleri açar

Gerçek execution sonucu olmadan otomatik sorun üretimi (DS-05), skor kalıcılığı
(DS-06), profil üretimi (DS-08), zamanlama (DS-07), bildirim teslimatı (DS-09),
operasyon ekranı (DS-11) ve sentetik veri doğrulaması (DS-19) gerçek production
kanıtı üretemez. DS-03 bu dilimlerin ortak merkezi bağımlılığıdır.

### 2.5 Tek ve kullanıcı tarafından gözlenebilir değerdir

Worker çekirdeğini tek başına ayağa kaldırmak teknik bir teslimat olurdu.
GAP-017'nin mevcut başlat/iptal endpoint'lerini frontend'e bağlamak ise worker
olmadan kullanıcıya sonsuza dek bekleyen bir kayıt gösterirdi. İkisini aynı dilimde
ele almak tek bir tamamlanmış kullanıcı sonucu üretir ve kapsamı hâlâ tek domain
sınırında tutar: execution/job yaşam döngüsü.

---

## 3. Kapsam

### 3.1 Dahil

1. **Production worker runtime**
   - `create_persistent_job_runtime` kullanan executable worker entrypoint'i.
   - Development/container composition'da PostgreSQL migration → API → worker
     başlangıç sırası ve kontrollü kapanma.
   - Worker kimliği, desteklenen iş tipleri, kapasite, durum ve heartbeat kaydı.

2. **Kalıcı iş durum makinesi**
   - Kuyruktaki işin atomik sahiplenilmesi, lease, heartbeat ve lease geri alma.
   - Retry, timeout, cancellation ve dead-letter geçişlerinin mevcut worker ve
     repository kurallarıyla çalıştırılması.
   - Kota veya çalışma penceresi nedeniyle yürütülemeyen işin terminal hata gibi
     gösterilmemesi; ayrı ve gözlenebilir `BLOCKED` karşılığı.
   - Yüzde 0–100 progress görünürlüğü ve optimistic version kontrolü.

3. **Claim ve audit atomikliği**
   - `PostgreSQLJobQueueRepository.claim_next` içinde durum, worker/lease ve
     `JOB_CLAIMED` outbox olayının tek transaction'da yazılması.
   - Lease geri alma, retry, dead-letter ve cancellation olaylarının gerçek
     `PostgreSQLTransactionalAudit` yolundan yayımlanması.
   - Audit stage başarısızsa claim'in geri alınması.

4. **Execution command composition**
   - Mevcut `POST /api/v1/executions`, `POST /api/v1/executions/{id}/cancel` ve
     `GET /api/v1/executions` uçlarının aynı PostgreSQL execution/job zincirine
     bağlanması.
   - Start sırasında execution, job ve audit kayıtlarının atomik olması.
   - İptal talebinin hem execution hem çalışan job tarafından gözlenmesi.

5. **Backend permission ve scope**
   - İnsan aktör için başlat/iptal rolü ve `permitted_source_ids` kapsamı.
   - İstek payload'ındaki source/owner bilgisinin trusted `ActorContext` yerine
     geçmemesi.
   - Worker claim ve heartbeat işlemlerinin insan kullanıcı değil trusted
     `ActorType.SERVICE` kimliğiyle yürütülmesi.

6. **Frontend execution akışı**
   - `ExecutionsPage` üzerinde çalıştırma formu, uygun kural sürümü/kaynak seçimi,
     başlatma ve izin verilen durumlarda iptal aksiyonu.
   - Periyodik yenileme veya eşdeğer canlı durum güncellemesi.
   - Terminal durumda sonuç özeti; teknik hata, timeout ve cancellation'ın kalite
     başarısızlığı gibi gösterilmemesi.

7. **Production-path test zinciri**
   - Gerçek PostgreSQL migration head ile API → queue → worker → execution result
     → API/UI smoke testi.
   - Claim/audit rollback, heartbeat, lease kaybı, retry, timeout, dead-letter,
     drain, idempotency, cancellation ve scope negatifleri.
   - Worker composition testinde handler veya repository'nin production yolunu
     değiştiren fake runtime kullanılmaması; dış veri kaynağı yalnız doğru adapter
     sınırında kontrol edilmesi.

### 3.2 Kapsam dışı

| Konu | Sahibi / gerekçe |
|---|---|
| Kuyruk ve dead-letter listeleme, manuel yeniden işleme/kapatma ekranı | DS-11 / GAP-018 |
| Schedule CRUD, daemon ve missed-run politikası | DS-07 / GAP-003 |
| Otomatik issue üretimi | DS-05 / GAP-006 |
| Quality score publication | DS-06 / GAP-008 |
| Bildirim aboneliği ve kanal teslimatı | DS-09 / GAP-007 |
| Rapor işlerinin asenkronlaştırılması | DS-12; DS-03 yalnız mevcut handler sözleşmesini korur |
| Çok bölgeli/yatay worker orchestration, autoscaling, Kubernetes HA | External dependency |
| Generic message broker veya ikinci queue teknolojisi | Mevcut PostgreSQL queue yeniden kullanılır |
| Kalıcı IAM yönetim ekranı ve rol atama modeli | DS-10; mevcut trusted actor kapısı kullanılır |

### 3.3 Migration kararı

Roadmap'teki “Migration 15” numarası artık kullanılamaz: revision
`20260805_15_data_source_command_slice.py` DS-01 tarafından mevcut head olarak
kullanılmaktadır. DS-03 için DDL gerçekten gerekliyse migration mevcut head'in
ardından yeni ve benzersiz revision olarak yazılmalıdır.

Beklenen şema kapsamı:

- `workers` tablosu;
- `background_jobs.progress`;
- kota/pencere ertelemesini temsil eden açık durum/alanlar;
- bunlara ait constraint ve index'ler.

Migration mevcut `background_jobs`, `dead_letter_records`, execution ve audit
tablolarını yeniden yaratmaz. Uygulamadan önce gerçek model/DDL karşılaştırmasıyla
her kolonun eksik olduğu doğrulanır.

---

## 4. Kabul kriterleri

| # | Kabul kriteri | Zorunlu kanıt |
|---|---|---|
| K1 | Yetkili kullanıcı API/UI üzerinden execution başlattığında `rule_executions`, `background_jobs` ve ilgili audit outbox kayıtları tek transaction'da oluşur | PostgreSQL API entegrasyon testi; zorlanmış outbox hatasında tam rollback |
| K2 | Executable worker aynı ortak settings, schema ve gerçek PostgreSQL queue/repository composition'ını kullanarak `EXECUTION` işini sahiplenir | Worker entrypoint/composition testi; app ile aynı schema kanıtı |
| K3 | Claim sırasında iş durumu, `claimed_by`, lease/version ve `JOB_CLAIMED` outbox olayı atomik yazılır | Repository transaction testi; outbox stage hatasında iş `QUEUED` kalır |
| K4 | Başarıyla işlenen execution terminal duruma geçer ve `rule_execution_results` kaydı üretir; app reconstruction sonrasında `GET /api/v1/executions` aynı sonucu gösterir | API → worker → reconstruction smoke testi |
| K5 | Heartbeat lease'i yalnız mevcut owner ve beklenen version ile uzatır; lease'i kaybeden eski worker sonuç, heartbeat veya terminal geçiş yazamaz | İki worker/lease yarış testi |
| K6 | Retryable hata politika sınırına kadar ertelenir; kalıcı hata veya deneme sınırı aşımı immutable dead-letter kaydı üretir | Retry/dead-letter PostgreSQL entegrasyon testi + audit doğrulaması |
| K7 | Graceful shutdown yeni claim'i durdurur, sahiplenilmiş iş için tanımlı drain/cancellation davranışını uygular ve bozuk lease bırakmaz | Gerçek worker loop drain testi |
| K8 | Kota veya çalışma penceresi engeli kalite/teknik terminal hata değildir; kullanıcıya ayrı bekleme nedeni ve durumuyla görünür | Policy + API projection testi |
| K9 | Aynı idempotency anahtarı/payload ikinci execution veya job oluşturmaz; aynı anahtar farklı payload ile conflict üretir | API ve repository idempotency testleri |
| K10 | Scope dışı source veya rolü eksik insan aktör start/cancel yapamaz; payload/header ile scope yükseltilemez | Backend `403` negatif testleri; mutation oluşmadığı ve audit sonucu doğrulaması |
| K11 | İptal edilen queued/running iş worker tarafından gözlenir; terminal execution tekrar iptal edilemez ve geçersiz state transition başarıya dönüşmez | Cancellation state-machine ve yarış testleri |
| K12 | Frontend başlatma sonrası aynı kaydı canlı olarak `QUEUED/RUNNING` ve terminal durumda gösterir; timeout, technical error ve cancellation birbirinden ayrılır | Frontend unit/contract + provision edilmiş backend E2E testi |
| K13 | `workers` kaydı başlangıç/heartbeat/drain boyunca gerçek worker durumunu yansıtır; stale worker aktif görünmez | PostgreSQL worker registry testi |
| K14 | CI'da production-path PostgreSQL smoke testi skip edilmeden geçer; mock/fake worker composition ile geçen test çıkış kapısı sayılmaz | CI test raporu ve skipped=0 kontrolü |

### 4.1 Çıkış kapısı

DS-03 yalnız şu sonuç birlikte gözlendiğinde tamamdır:

> Arayüzden başlatılan execution kalıcı kuyruğa atomik yazılır, production worker
> tarafından sahiplenilip sonuçlandırılır ve aynı execution ekranında terminal
> durumuyla görünür; claim/lease/audit, permission/scope, cancellation ve hata
> yolları gerçek PostgreSQL production composition üzerinde doğrulanır.

Yalnız worker birim testlerinin geçmesi, yalnız entrypoint'in başlaması, job'ın
`SUCCESS` olması fakat execution result yazmaması veya UI'nın fixture durumlarını
göstermesi dilimi kapatmaz.

---

## 5. Sonraki karar sınırı

DS-03 tamamlanmadan DS-05 otomatik sorun, DS-06 skor, DS-07 zamanlama veya DS-08
profil üretim dilimleri production sonucu üretemez. DS-03 sonrasında seçim,
dependency grafiğindeki açılmış adayların güncel repository durumuna karşı yeniden
karşılaştırılmasıyla yapılmalıdır; bu belge dördüncü dilimi peşinen seçmez.

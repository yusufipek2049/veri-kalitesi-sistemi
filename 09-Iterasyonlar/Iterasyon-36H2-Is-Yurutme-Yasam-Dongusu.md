---
iteration: 36H2
status: VerificationPending
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36H2 — İş Yürütme Yaşam Döngüsü

> **Durum: VerificationPending.** Kod yüzeyi mevcut, ancak reviewer güncel kod
> üzerinde açık correctness bulguları tespit etti; paket doğrulanana kadar
> **tamamlanmış sayılmaz.** Aşağıdaki "Sonuç" bölümü implementer iddiasıdır ve bir
> kısmı review bulgularıyla çelişir (bkz. Açık İnceleme Bulguları).

## Açık İnceleme Bulguları (review: CHANGES_REQUIRED)

1. Worker toplam deadline'da yalnız iptal sinyali verip handler sonucunu süresiz
   bekliyor ve lease'i yeniliyor; iptali dinlemeyen handler'da iş hiç
   `TIMEOUT`/`CANCELLED` olmayabilir (`jobs/worker.py`).
2. Süresi dolan `CANCEL_REQUESTED` işleri kapatan reaper production `run_forever()`
   yaşam döngüsüne bağlı değil; composition ayrı reaper bağlamıyor.
3. Execution iptali ile background-job iptali iki ayrı transaction'da; kuyruk
   hatası/yarışında API başarılı iptal kaydedip çalışan işi iptal etmeyebilir
   (`api/postgresql_execution.py`).
4. Değiştirilen execution cancel/repository yolu için ilgili PostgreSQL entegrasyon
   testi controller raporunda yok; iptali dinlemeyen handler, worker kaybı sonrası
   iptal kapanışı ve kuyruk-iptal-hatası atomik rollback testleri eksik.

Bu bulgular giderilip controller test kapıları (birim + etkilenen PostgreSQL
entegrasyonu, skip'siz) geçtikten sonra kayıt `TechnicallyVerified` yapılır.

## Sonuç (implementer iddiası — doğrulanmadı)

36H1 kalıcı kuyruk çekirdeği; sahip-only terminal geçişler, lease bırakma,
politika kontrollü retry/backoff/ayrı bağlantı-sorgu-toplam timeoutları,
claim anında atomik global/kaynak kotası, kalıcı iptal isteği ve handler'a aktif
iptal sinyali, retry tükenmesinde dead-letter ve güvenilir aktör + sürümlü rol politikasıyla
auditli yeniden işleme davranışlarıyla tamamlandı. Kalite başarısızlığı kuyruk
başarısından ve teknik hatadan ayrı `completion_outcome` olarak korunur.
Execution ve report request yazımları ilgili domain kaydı, kalıcı job ve
transactional audit/outbox'ı aynı PostgreSQL transaction'ında oluşturur;
istek-içi report worker yalnız development composition'da açıktır. Production
composition yalnız PostgreSQL job queue, PostgreSQL kaynak kullanım politikası
ve transactional audit bağımlılıklarını kabul eder. Worker handler
çalışırken lease süresinin üçte birinde (en geç beş saniyede) heartbeat üretir;
connection/query timeoutlarını bağlayıcıya aktarır ve aktif iptalde sürücü
cancel çağrısını tetikler. Toplam deadline sonunda cancellation sinyali verir;
handler durmadan terminal `TIMEOUT` yazmadığı için geç yan etki oluşmaz.
Terminal, iptal ve lease-expiry iptal kapanışları audit/outbox olmadan reddedilir.

## Kanıt

- Kod: `03-Backend/src/veri_kalitesi/jobs/`
- Migration: `20260729_09_job_lifecycle.py`,
  `20260729_10_source_policy_deadlines.py`
- Birim: `test_job_queue.py`, `test_persistent_job_worker.py`,
  `test_persistent_job_handlers.py`, `test_source_usage_policies.py` —
  `39 passed`
- PostgreSQL: `test_postgresql_job_queue.py` — canlı PostgreSQL üzerinde
  `31 passed`, skip yok; execution/report atomik enqueue/rollback, eşzamanlı aynı-kaynak
  kotası, lease'i aşan worker heartbeat'i, audit atomikliği ve üç ayrı policy
  deadline alanı kapsanır.

## Kalan Sınır

Kurumsal IdP, secret manager/PAM, HA PostgreSQL/broker, SIEM/WORM ve banka
operasyon kanıtları harici bağımlılıktır; bu teknik kapanış bunların hazır
olduğu anlamına gelmez.

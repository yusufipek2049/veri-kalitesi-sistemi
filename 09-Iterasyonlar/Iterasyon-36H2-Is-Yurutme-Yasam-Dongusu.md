---
iteration: 36H2
status: TechnicallyVerified
completed_at: 2026-07-29
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36H2 — İş Yürütme Yaşam Döngüsü

> **Durum: TechnicallyVerified.** Controller birim ve PostgreSQL kapıları
> başarılıdır; reviewer güncel kod, test ve kanonik dokümanlar üzerinden
> `APPROVED` kararı vermiştir.

## Kapatılan İnceleme Bulguları

1. Toplam deadline sonrası handler beklemesi sınırlandırıldı; iptal sinyali,
   terminal `TIMEOUT`/`CANCELLED`, heartbeat'in durması ve geç yan etkinin
   engellenmesi birim testleriyle doğrulandı.
2. Süresi dolan `CANCEL_REQUESTED` reaper'ı production `run_forever()` yaşam
   döngüsüne bağlandı ve transactional audit ile kapanış doğrulandı.
3. Execution ve background-job iptali aynı PostgreSQL transaction'ına alındı;
   kuyruk iptal hatasında execution, job ve audit rollback'i entegrasyon
   testiyle doğrulandı.
4. Etkilenen job queue ve data source PostgreSQL testleri controller hedeflerine
   alındı ve skip olmadan geçti.

## Sonuç

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
cancel çağrısını tetikler. Toplam deadline sonunda cancellation sinyali verir,
sınırlı grace süresinden sonra handler process'ini sonlandırır ve terminal
`TIMEOUT` yazar; deadline sonrasında lease yenilenmez veya geç yan etki oluşmaz.
Terminal, iptal ve lease-expiry iptal kapanışları audit/outbox olmadan reddedilir.

## Kanıt

- Kod: `03-Backend/src/veri_kalitesi/jobs/`
- Migration: `20260729_09_job_lifecycle.py`,
  `20260729_10_source_policy_deadlines.py`
- Controller birim kapısı (2026-07-29):
  `python3 -m pytest -q -p no:cacheprovider 06-Testler/01-Birim` —
  `1172 passed in 18.02s`; kanıt:
  `.agent-handoff/logs/unit-tests-i6.log`.
- Controller PostgreSQL kapısı (2026-07-29):
  `python3 -m pytest -q -p no:cacheprovider 06-Testler/02-Entegrasyon/test_postgresql_data_source_persistence.py 06-Testler/02-Entegrasyon/test_postgresql_job_queue.py` —
  `41 passed in 3.05s`, skip yok; kanıt:
  `.agent-handoff/logs/integration-tests-i6.log`.
- Reviewer kararı (2026-07-29): `STATUS: APPROVED`; gerekli değişiklik yok.
  Kanıt: `.agent-handoff/logs/reviewer-i6-r0.stdout.log`.

## Kalan Sınır

Kurumsal IdP, secret manager/PAM, HA PostgreSQL/broker, SIEM/WORM ve banka
operasyon kanıtları harici bağımlılıktır; bu teknik kapanış bunların hazır
olduğu anlamına gelmez.

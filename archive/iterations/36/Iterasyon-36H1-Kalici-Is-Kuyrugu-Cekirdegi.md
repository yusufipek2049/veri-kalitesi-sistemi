---
iteration: 36H1
status: TechnicallyVerified
completed_at: 2026-07-28
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36H1 — Kalıcı İş Kuyruğu Çekirdeği ve Concurrency Temeli

## Amaç

[Kalıcı iş kuyruğu ve worker dayanıklılığı](../../../NEXT_STEP.md) paketinin
concurrency ve kalıcılık temelini kurmak: süreç ömründen bağımsız kuyruk kaydı,
lease/heartbeat sahiplenmesi, worker kaybında güvenli yeniden sahiplenme ve
idempotent enqueue.

## Kapsam

- `veri_kalitesi/jobs` domain modülü: `BackgroundJob`, `JobStatus`,
  `JobLeasePolicy` ve `Job*` hata tipleri.
- `BackgroundJob` payload sözleşmesi: yasak anahtar/hassas metin reddi ve
  dış mutable referanslardan koparan recursive freeze.
- `PostgreSQLJobQueueRepository`: `enqueue` (idempotent), deterministik
  `claim_next` (lease atama), `heartbeat` (yalnız sahip), `renew_lease` ve
  süresi geçen claim'i kuyruğa döndüren `release_expired_claims`.
- Optimistic `version` ile eşzamanlı sahiplenmede tek kazanan; `background_jobs`
  tablosu için kısıt/indeks tanımlayan Alembic migration.

## Kanıt

- [Domain modelleri ve payload sözleşmesi](../../../03-Backend/src/veri_kalitesi/jobs/models.py)
- [Hata tipleri](../../../03-Backend/src/veri_kalitesi/jobs/errors.py)
- [PostgreSQL kuyruk repository](../../../03-Backend/src/veri_kalitesi/jobs/postgresql_repository.py)
- [Migration `20260728_08_job_queue`](../../../05-Veritabani/alembic/versions/20260728_08_job_queue.py)
- [Birim testleri](../../../06-Testler/01-Birim/test_job_queue.py)
- [PostgreSQL entegrasyon testleri](../../../06-Testler/02-Entegrasyon/test_postgresql_job_queue.py)

## Tamamlama Ölçütleri

1. ✅ Kuyruk kaydı repository/session örneklerinden bağımsız kalıcıdır;
   idempotency anahtarı aynı payload için tek satır üretir, farklı payload'ı
   reddeder ve job_type başına bağımsızdır.
2. ✅ `claim_next` önce priority, sonra `available_at`/`created_at`/`job_id`
   sırasıyla deterministiktir; gelecekteki iş claim edilmez; eşzamanlı iki
   worker'dan yalnız biri kazanır.
3. ✅ Lease alanları atomik yazılır; heartbeat yalnız sahibi tarafından ilerler;
   aktif lease ikinci worker'a verilmez; süresi geçen lease yeniden claim edilir;
   bayat `version` `JobConcurrencyError` üretir.
4. ✅ Migration boş şemadan ve belirtilen önceki head'den ileri çalışır.
5. ✅ Birim testleri bu oturumda `11 passed` (`06-Testler/01-Birim/test_job_queue.py`).

## Kalan Sınırlar

- Bu artım yalnız kuyruk çekirdeği ve concurrency temelidir. İş tamamlanma/hata
  durum geçişleri, aktif politikadan çözülen kota/pencere/timeout/retry,
  dead-letter yaşam döngüsü + yetkili yeniden işleme/audit ve production runtime
  worker/composition bağlantısı [36H2](Iterasyon-36H2-Is-Yurutme-Yasam-Dongusu.md)
  ile tamamlanmıştır.
- 17 PostgreSQL entegrasyon testi canlı PostgreSQL 16 gerektirir; bu oturumda
  bağımsız yeniden koşulmamıştır.

## Bağlantılar

- [İterasyon 36 ana planı](../../../09-Iterasyonlar/Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md)
- [Bir önceki: 36G — Güvenli Rapor Üretimi/İndirme](Iterasyon-36G-Guvenli-Rapor-Uretimi-ve-Indirme.md)
- [Sonraki: kalan iş yürütme yaşam döngüsü](../../../NEXT_STEP.md)

# Denetim Faz 4: Zamanlayıcıyı Worker'a Bağlama

## Bağlam

Zamanlanmış kural çalıştırmaları **hiçbir zaman tetiklenmiyor.** Özellik tamamen
yazılmış ve test edilmiş, ama çalışan sisteme bağlanmamış.

Kanıt:

```
grep -rn "trigger_due" src/    →  yalnızca tanımı (scheduling.py:303)
grep -rn "trigger_due" tests/  →  test_executions.py, test_reporting.py
```

Yani `SchedulingService.trigger_due()` yalnızca testlerden çağrılıyor. Üretim
kompozisyonunda `SchedulingService` hiç kurulmuyor.

### Mevcut yapı

- `src/veri_kalitesi/executions/scheduling.py:218` — `SchedulingService`
- `src/veri_kalitesi/executions/scheduling.py:303` — `trigger_due(now=None)`,
  `repository.due(current)` üzerinden vadesi gelen zamanlamaları çalıştırmaya çeviriyor
- `src/veri_kalitesi/executions/scheduling.py:36` — `ScheduleRepository` protokolü
  (`due`, `advance`, `add`, `get`, `list_all`)
- `src/veri_kalitesi/executions/postgresql_scheduling.py` — PostgreSQL uygulaması
- `src/veri_kalitesi/reporting/scheduling.py:180` — rapor tarafında **aynı sorun**,
  aynı desen (`_repo.due(current)`)
- `alembic/versions/20260724_05_scheduling_and_policy_baseline.py` — şema mevcut

### Worker döngüsü

`src/veri_kalitesi/jobs/worker.py:106` — `run_forever(stop_event, idle_wait_seconds=0.5)`:

```python
while not stop_event.is_set():
    self.repository.release_expired_claims(...)          # süresi dolan claim'leri serbest bırak
    now_mono = self.monotonic_clock()
    if now_mono - last_worker_heartbeat >= worker_heartbeat_interval:
        ...                                              # worker kalp atışı
    if self.run_once() is None:
        stop_event.wait(idle_wait_seconds)
self._drain(worker_version)
```

Döngü zaten periyodik bakım işleri (claim serbest bırakma, kalp atışı) için bir kadans
taşıyor. Zamanlama tetikleyicisi bu desene oturmalı.

**Bağımlılık:** Faz 2 (PostgreSQL testleri çalışır olmalı ki zamanlayıcı entegrasyonu
gerçek veritabanına karşı doğrulanabilsin).

## Görev

1. **Zamanlama tetikleyicisini worker yaşam döngüsüne bağla.** Vadesi gelen
   zamanlamaların düzenli aralıklarla çalıştırmaya dönüştürülmesini sağla. Mevcut
   `release_expired_claims` / kalp atışı deseni ile tutarlı bir kadans kullan —
   her turda değil, yapılandırılabilir bir aralıkta.
2. **Çok worker'lı güvenlik.** Birden fazla worker aynı anda çalıştığında aynı
   zamanlama iki kez tetiklenmemeli. Mevcut iş kuyruğu bu sorunu `FOR UPDATE SKIP LOCKED`
   ve advisory kilit ile zaten çözüyor (`jobs/postgresql_repository.py:348`) — aynı
   yaklaşımı kullan, yeni bir eşzamanlılık mekanizması icat etme.
3. **`SchedulingService`'i üretim kompozisyonuna kur.** PostgreSQL zamanlama deposu ile
   `src/veri_kalitesi/jobs/production.py` içinde (bildirim işleyicisinin kurulduğu
   desene bakarak, satır 281-298) bağla.
4. **Rapor zamanlayıcısını da bağla.** `reporting/scheduling.py:180` aynı boşluğa sahip;
   aynı çözümü uygula.
5. **Hata yalıtımı.** Tek bir zamanlamanın başarısız olması worker döngüsünü
   düşürmemeli. `ScheduleTechnicalEventSink.notify_schedule_failure`
   (`scheduling.py:89`) bu amaçla zaten tanımlı — kullan.

## Invariantlar

- **Determinizm ve idempotency:** Aynı zamanlama aynı `next_run_at` için iki kez
  çalıştırma üretmemeli. Mevcut `idempotency_key_hash` mekanizması korunacak.
- Worker'ın kontrollü kapanması (`stop_event` → `_drain` → `DRAINING` → `STOPPED`)
  bozulmayacak.
- Denetim (audit) olayları mevcut transactional outbox üzerinden yazılacak;
  `trigger_due` içindeki mevcut audit davranışı korunacak.
- Kira/kalp atışı zamanlamaları etkilenmeyecek.
- Saat kaynağı enjekte edilebilir kalacak (`clock` / `monotonic_clock`) —
  testlerde sahte saat kullanılabilmeli. `time.time()` doğrudan çağrılmayacak.
- Yeni üçüncü parti bağımlılık yok (cron kütüphanesi eklenmeyecek).

## Kabul Kriterleri

1. Vadesi gelen bir zamanlama, worker çalışırken otomatik olarak çalıştırmaya dönüşüyor —
   entegrasyon testiyle gösterilmiş.
2. Vadesi gelmemiş zamanlama tetiklenmiyor — test.
3. İki worker eşzamanlı koştuğunda aynı zamanlama tam olarak bir kez çalıştırılıyor — test.
4. Bir zamanlama hata fırlattığında döngü ayakta kalıyor ve diğer zamanlamalar
   işlenmeye devam ediyor — test.
5. Rapor zamanlayıcısı için 1-4 arası kriterlerin karşılığı sağlanmış.
6. Worker'ın kontrollü kapanması hâlâ çalışıyor — mevcut test geçiyor.
7. `python -m pytest` tamamen yeşil.

## Teslim Formatı

- **Kod:** Değiştirilen dosyalar ve gerekçesi.
- **Tasarım kararı:** Tetikleme kadansı ve eşzamanlılık yaklaşımı, gerekçesiyle.
- **Testler:** Kabul kriterlerinin her birini karşılayan test adları.
- **Test çıktısı:** Ham `pytest` sonucu.
- **Invariant raporu:** Idempotency, determinizm, kontrollü kapanma.
- **Varsayımlar:** Yapılan varsayımlar ve açık kalan sorular.

## Çalışma Kuralları

- Mevcut kod stiline uy (Türkçe docstring, `from __future__ import annotations`,
  frozen dataclass).
- Yeni üçüncü parti bağımlılık ekleme.
- Testleri çalıştır ve sonucu olduğu gibi bildir.
- Belirsizlik varsa varsayımını açıkça yaz ve devam et.

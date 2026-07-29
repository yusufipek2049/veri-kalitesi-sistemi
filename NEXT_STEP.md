---
type: next-step
status: active
updated_at: 2026-07-29
work_package: PERSISTENT-JOB-EXECUTION-LIFECYCLE
predecessor: 36H1
---

# Sıradaki Adım — İş Yürütme Yaşam Döngüsü Doğrulaması (36H2 açık bulguları)

36H2 iş yürütme yaşam döngüsü kod yüzeyi eklendi ancak review güncel kod üzerinde
açık correctness bulguları tespit etti; paket **doğrulanana kadar tamamlanmış
sayılmaz** ([36H2 kaydı — VerificationPending](09-Iterasyonlar/Iterasyon-36H2-Is-Yurutme-Yasam-Dongusu.md)).
Sıradaki tek iş bu bulguları kapatıp controller test kapılarını geçirmektir.

## Kapsam (açık bulgular)

- Toplam deadline'da handler'ın sınırsız beklenmesini engelleyen, deadline sonrası
  lease yenilemeyi durduran ve geç yan etkiyi önleyen sınırlandırılmış execution;
  handler iptali dinlemese de iş `TIMEOUT`/`CANCELLED` olmalı.
- Süresi dolan `CANCEL_REQUESTED` işleri transactional audit ile kapatan reaper'ın
  production worker (`run_forever`) yaşam döngüsüne bağlanması.
- Execution iptali ile background-job iptalinin tek PostgreSQL transaction'ında
  atomik olması; kuyruk hatasında execution değişikliği ve audit rollback.
- İptali dinlemeyen handler, worker kaybı sonrası iptal kapanışı ve kuyruk-iptal-
  hatasında atomik rollback testleri; etkilenen execution PostgreSQL entegrasyon
  testinin controller raporuna dahil edilmesi.

## Kapsam Dışı

- 36H1 kuyruk çekirdeği ve 36E/36F/36G kapsamlarının yeniden uygulanması.
- Kurumsal IdP, secret manager, HA/broker, DLP/watermark adaptörleri.
- `tools/agent-loop/` pipeline altyapısı (ayrı commit; bu ürün teslimatının kapsamı
  değildir).

## Çıkış Kapıları

1. Birim testleri: iptali dinlemeyen handler'da bounded wait sonrası terminal
   `TIMEOUT`/`CANCELLED`; deadline sonrası lease yenilenmez.
2. Reaper production worker yaşam döngüsünde; süresi dolan `CANCEL_REQUESTED`
   transactional audit ile kapanır.
3. Execution + background-job iptali tek transaction; kuyruk hatasında atomik
   rollback (entegrasyon testiyle kanıtlı).
4. Controller test raporu birim + etkilenen PostgreSQL entegrasyonunu skip'siz
   içerir; reviewer `APPROVED` verir. Ancak o zaman 36H2 `TechnicallyVerified`.

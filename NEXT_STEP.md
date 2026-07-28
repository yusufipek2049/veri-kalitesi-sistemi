---
type: next-step
status: active
updated_at: 2026-07-27
work_package: PERSISTENT-JOB-QUEUE-WORKER-RESILIENCE
---

# Sıradaki Adım — Kalıcı İş Kuyruğu ve Worker Dayanıklılığı

## Kapsam

- Execution ve raporlama işlerinin süreç ömründen bağımsız kalıcı kuyruk
  yaşam döngüsü.
- Worker kaybını algılayan lease/heartbeat ve güvenli yeniden sahiplenme.
- Aktif sürümlü kaynak politikasından çözülen kota, izinli/engelli çalışma
  penceresi, timeout ve sınırlı retry davranışı; politika veya güvenli varsayılan
  yokluğunda fail-closed ret.
- Retry hakkı tükenen asenkron işler için dead-letter kaydı ile yetkili yeniden
  işleme ve audit izi.
- İptal ve idempotency sözleşmelerinin kalıcı kuyruk durum geçişlerinde
  korunması; teknik hata, veri kalitesi ihlali ve kullanım kararının ayrı
  kalması.

## Kapsam Dışı

- Gerçek üretim IdP, secret manager, HA/broker ve diğer kurumsal adaptörler.
- Kurumsal DLP/watermark ürün entegrasyonu.
- Tamamlanmış 36E execution PostgreSQL cutover, 36F scheduling/policy
  PostgreSQL kalıcılığı ve 36G güvenli rapor üretimi/indirme kapsamlarının
  yeniden uygulanması.
- NFR-REL-003 circuit breaker ve NFR-REL-004 checkpoint/devam hedefleri; bu
  paketin kanonik kalan sınırlarında yer almaz.

## Bağımlılıklar

- [36E kalan sınırı](09-Iterasyonlar/Iterasyon-36E-Calisma-PostgreSQL-Cutover.md)
  ve [36G kalan sınırı](09-Iterasyonlar/Iterasyon-36G-Guvenli-Rapor-Uretimi-ve-Indirme.md).
- [FR-036, FR-039–FR-045](01-SRS/04-Fonksiyonel-Gereksinimler/04.05-Calistirma-ve-Zamanlama.md)
  iş kuyruğu, kota, timeout, retry, iptal, izleme ve idempotency sözleşmeleri.
- [NFR-REL-001, 002, 005–007](01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.04-Guvenilirlik-ve-Hata-Toleransi.md)
  hata toleransı ve dead-letter doğrulama hedefleri.
- 36F ile kalıcılaştırılan scheduling/source-usage policy repository'leri ve
  36E/36G ile kalıcılaştırılan execution/report kayıtları.

## Çıkış Kapıları

1. Birim testleri kuyruk durum geçişlerini, lease/heartbeat yenilemesini,
   worker kaybından sonra yeniden sahiplenmeyi ve eşzamanlı sahiplenmede tek
   kazananı doğrular.
2. Birim testleri yalnız retry edilebilir teknik hataların aktif politikadaki
   sınırlarla yeniden denendiğini; kalite başarısızlığı ve kalıcı hataların
   yeniden denenmediğini doğrular.
3. Birim ve entegrasyon testleri timeout/iptal kapanışını, retry tükenmesinde
   dead-letter kaydını ve yetkili yeniden işlemenin audit izini doğrular.
4. PostgreSQL entegrasyon testleri kalıcı işin process/worker kesintisi
   sonrasında kaybolmadığını ve aynı idempotency key/payload için çift yürütme
   oluşmadığını kanıtlar.
5. Migration sıfırdan ve mevcut şemadan ileri çalışır; hata halinde ileri
   düzeltme ve fail-closed politikası korunur.
6. Production runtime composition kalıcı queue/worker yolunu kullanır; SQLite
   veya istek içi worker yalnız açıkça sınırlandırılmış test/geliştirme rolünde
   kalır.

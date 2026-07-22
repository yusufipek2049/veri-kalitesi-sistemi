# Kanıta Dayalı Karar ve Remediation Runbook

## Kapsam

Bu runbook `FR-099–FR-111`, `UC-018–UC-021` ve
[kanonik karar sistemi](../02-Mimari/Kanita-Dayali-Karar-Sistemi.md) için hedef
operasyon sınırını tanımlar. Runtime uygulaması veya üretim otomasyon yetkisi
değildir.

## Güvenli İşletim Akışı

1. Olay/run correlation ve güvenilir aktör bağlamını doğrula.
2. Snapshot/partition, kural/politika/model/motor sürümleri ve manifest
   bütünlüğünü doğrula.
3. Eksik kanıt, lineage ve güven değerlerini görünür işaretle.
4. Teşhisi `VerifiedCause`, `StrongHypothesis`, `WeakHypothesis` veya
   `TemporalCorrelationOnly` olarak sınıflandır; korelasyonu neden sayma.
5. Öneriyi mekanizma/sürüm, dayanak, güven, risk ve onay ihtiyacıyla oluştur.
6. Remediation öncesi dry-run, etki, yetki/politika, maker-checker ve rollback
   kanıtını doğrula.
7. `OPEN-030` kapanana kadar yalnız `SuggestOnly` uygula.
8. İzinli gelecekteki akışta canary sonrası yeniden ölç; başarısızlıkta rollback
   ve güvenli duruma geç.
9. Kapanışta doğrulama sonucu, kalıcılık koşulu, kanıt paketi ve audit referansını
   ilişkilendir.

## Kesin Yasaklar

- Kaynak üretim verisine DDL/DML veya değiştirici API çağrısı gönderme.
- LLM/model/öneri sonucunu tek başına uygulama kararı sayma.
- Kaynaksız finansal değer, eşik, güven veya SLA üretme.
- Eksik kanıtı başarılı paket ya da doğrulanmış neden gibi işaretleme.
- Gerçek müşteri verisini genel mühendis erişimine, loga veya pakete açma.
- Chaos kusurunu üretim veya gerçek müşteri verisine enjekte etme.

## Reproduction

- Aynı snapshot/partition, kural/politika, parametre, örnekleme/seed ve motor
  sürümleri aranır.
- Eksik girdi `INCOMPLETE` veya teknik hata üretir; mevcut sonuca sessiz fallback
  yapılmaz.
- Replay yeni run/sonuç oluşturur; orijinal skor ve kanıt değiştirilmez.
- Saklama/erişim süresi dolmuş snapshot için veri uydurulmaz.

## Chaos Deneyi

1. `OPEN-031` ile izinli ortam/fault kapsamını doğrula.
2. Sentetik köken, ground truth, onay, izolasyon ve rollback kanıtını kontrol et.
3. Kusuru enjekte et; tespit, kaçırılan hata, false positive ve süreyi ayrı ölç.
4. Geri al ve veri/ortam durumunu doğrula.
5. Teknik hata ile kontrolün kaçırdığı kalite kusurunu ayrı kapat.

## Metrikler ve Alarmlar

- run/reproduction başarı oranı,
- atlanan kural ve eksik kanıt oranı,
- lineage kapsama oranı,
- öneri kabul/başarı ve rollback oranı,
- false positive/false negative,
- chaos detection coverage,
- MTTD, MTTDiagnosis, MTTR ve olay tekrar oranı.

Sayısal alarm eşikleri aktif sürümlü gözlemlenebilirlik politikasından çözülür.
Politika yoksa eşik uydurulmaz; metrik yine ölçülebilir.

## Geri Alma ve Pasifleştirme

- Öneri/remediation/chaos özellik bayrağı veya politika kaydı pasifleştirilir.
- Yeni işler kabul edilmez; çalışan iş yalnız güvenli iptal/rollback sözleşmesiyle
  sonlandırılır.
- Append-only run, kanıt, onay ve audit geçmişi silinmez.
- Güvenli fallback salt okunur kanıt inceleme ve `SuggestOnly` davranışıdır.

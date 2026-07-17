---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
requirement_ids:
  - FR-054
  - FR-055
  - FR-057
  - UC-010
  - NFR-PERF-001
  - NFR-PERF-002
status: TechnicallyVerified
version: iteration-21a-local
executed_at: 2026-07-17
---

# Iterasyon 21A Yetki Filtreli Dashboard Trend Kaniti

## Degisiklik

- Iterasyon: 21A - guvenilir scope ile son 30 UTC gunluk dashboard trend domain sorgusu
- Commit/Artifact: Git deposu bulunmadigi icin commit yok; yerel calisma agaci
- Bilesen: `veri_kalitesi.dashboard`, `veri_kalitesi.scoring`
- Kontrol/Gereksinim: FR-054/055/057, UC-010 ve NFR-PERF-001/002 trend alt kapsami

## Dogrulama

- Komut: `pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek ici SQLite ve sentetik skor verisi
- Sentetik veri seti: Yetkili/yetkisiz kaynak ve kurum skorlari, bos gun, `NO_DATA`, pencere sinirlari, saat dilimsiz zaman, depo arizasi ve 500 gozlem
- Beklenen: Yalniz yetkili scope doner; son 30 UTC gun sabittir; bos gun ve `NO_DATA` sifir olmaz; teknik hata ayri kalir; yerel p95 uc saniyenin altindadir.
- Gerceklesen: 265 test gecti. Dashboard hedef grubu 29 testle gecti; 11 yeni trend testi eklendi.
- Sonuc: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Degisen Python dosyalarinda `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src`: PASS
- Tam depo format kontrolu, bu iterasyonda degismeyen dort eski dosyanin mevcut format farklari nedeniyle PASS degildir.

## Guvenlik

- Guven siniri: Trend metodu scope parametresi kabul etmez; `ActorContext` mevcut authorization servisiyle karara donusturulmeden repository cagrilmaz.
- Deny-by-default: Eksik/gecersiz context repository cagrisindan once reddedilir. Kurum skoru yalniz acik kurum yetkisiyle doner.
- Katmanli filtre: Zaman ve scope SQLite sorgusunda parametreli uygulanir; servis okuyucu ciktisini ayni yetki karariyla yeniden filtreler.
- Veri minimizasyonu: Yalniz onceden hesaplanmis skor gorunumleri doner; ham kayit, secret, LDAP kimligi veya musteri verisi okunmaz ve loglanmaz.
- Sonuc ayrimi: Bos donem bos kalir, `NO_DATA` NULL degeriyle korunur; depo arizasi redakte teknik hata olur.
- Audit: Yetki karari mevcut merkezi audit sozlesmesini kullanir; trend sorgusu yeni kalici yazim veya hassas audit payloadi olusturmaz.
- Maker-checker etkisi: Salt okunur sorgu yeni kritik konfigurasyon degisikligi yaratmaz; maker-checker kapsami yoktur.
- Geri alma: `get_score_trend` ve repository okuma metodu kaldirilarak onceki skor agaci davranisina donulebilir; kalici veri semasi degismemistir.
- Kalan risk: Serbest tarih/periyot, operasyon listeleri, grafik/tablo ve HTTP/cookie/CSRF yuzeyi kapsam disidir; 21B `OPEN-BNK-020` nedeniyle engellidir.

## Onaylar

- Teknik dogrulayan: Codex teknik uygulama ajani
- Bilgi guvenligi: ComplianceReviewRequired
- IAM: ComplianceReviewRequired
- Ic kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanit teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayi anlamina gelmez.

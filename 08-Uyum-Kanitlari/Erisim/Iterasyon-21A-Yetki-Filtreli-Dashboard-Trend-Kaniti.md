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

# İterasyon 21A Yetki Filtreli Dashboard Trend Kanıtı

## Değişiklik

- İterasyon: 21A - güvenilir scope ile son 30 UTC günlük dashboard trend domain sorgusu
- Commit/Artifact: Git deposu bulunmadığı için commit yok; yerel çalışma ağacı
- Bileşen: `veri_kalitesi.dashboard`, `veri_kalitesi.scoring`
- Kontrol/Gereksinim: FR-054/055/057, UC-010 ve NFR-PERF-001/002 trend alt kapsamı

## Doğrulama

- Komut: `pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek içi SQLite ve sentetik skor verisi
- Sentetik veri seti: Yetkili/yetkisiz kaynak ve kurum skorları, boş gün, `NO_DATA`, pencere sınırları, saat dilimsiz zaman, depo arızası ve 500 gözlem
- Beklenen: Yalnız yetkili scope döner; son 30 UTC gün sabittir; boş gün ve `NO_DATA` sıfır olmaz; teknik hata ayrı kalır; yerel p95 üç saniyenin altındadır.
- Gerçekleşen: 265 test geçti. Dashboard hedef grubu 29 testle geçti; 11 yeni trend testi eklendi.
- Sonuç: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Değişen Python dosyalarında `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src`: PASS
- Tam depo format kontrolü, bu iterasyonda değişmeyen dört eski dosyanın mevcut format farkları nedeniyle PASS değildir.

## Güvenlik

- Güven sınırı: Trend metodu scope parametresi kabul etmez; `ActorContext` mevcut authorization servisiyle karara dönüştürülmeden repository çağrılmaz.
- Deny-by-default: Eksik/geçersiz context repository çağrısından önce reddedilir. Kurum skoru yalnız açık kurum yetkisiyle döner.
- Katmanlı filtre: Zaman ve scope SQLite sorgusunda parametreli uygulanır; servis okuyucu çıktısını aynı yetki kararıyla yeniden filtreler.
- Veri minimizasyonu: Yalnız önceden hesaplanmış skor görünümleri döner; ham kayıt, secret, LDAP kimliği veya müşteri verisi okunmaz ve loglanmaz.
- Sonuç ayrımı: Boş dönem boş kalır, `NO_DATA` NULL değeriyle korunur; depo arızası redakte teknik hata olur.
- Audit: Yetki kararı mevcut merkezi audit sözleşmesini kullanır; trend sorgusu yeni kalıcı yazım veya hassas audit payloadı oluşturmaz.
- Maker-checker etkisi: Salt okunur sorgu yeni kritik konfigürasyon değişikliği yaratmaz; maker-checker kapsamı yoktur.
- Geri alma: `get_score_trend` ve repository okuma metodu kaldırılarak önceki skor ağacı davranışına dönülebilir; kalıcı veri şeması değişmemiştir.
- Kalan risk: Serbest tarih/periyot, operasyon listeleri, grafik/tablo ve HTTP/cookie/CSRF yüzeyi kapsam dışıdır; 21B `OPEN-BNK-020` nedeniyle engellidir.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- IAM: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.

---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
  - BFR-IAM-004
  - BFR-AUD-005
  - BRULE-001
  - BRULE-005
requirement_ids:
  - FR-072
  - UC-015
  - AC-021
  - AC-023
  - NFR-PERF-002
  - NFR-PRV-001
  - NFR-PRV-002
  - NFR-PRV-003
  - NFR-SEC-001
  - NFR-SEC-005
  - NFR-SEC-008
status: TechnicallyVerified
version: ITERATION_24B
executed_at: 2026-07-20
---

# İterasyon 24B Yetki Filtreli Rapor Onizleme Kanıtı

## Değişiklik

- İterasyon: 24B - Yetki filtreli ve maskeli rapor onizleme
- Commit/Artifact: `ITERATION_24B` (`origin/main`)
- Bileşen: `veri_kalitesi.reporting`, `veri_kalitesi.scoring`, `veri_kalitesi.identity`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: FR-072, UC-015, AC-021/023, NFR-PERF-002, NFR-PRV-001/002/003, NFR-SEC-001/005/008, BFR-IAM-001/002/004, BFR-AUD-005 ve BRULE-001/005 alt kapsamı

## Doğrulama

- Komut: `PYTHONPATH=03-Backend/src pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek içi SQLite, sentetik toplulaştırılmış SOURCE skorları ve güvenilir fake actor context
- Sentetik veri seti: Yetkili/yetkisiz source, eski/güncel skor, NO_DATA, teknik sonuç, sahte/servis/ayrıcalıklı context, geçersiz filtre, reader/audit arızası, scope sızıntısı ve 500 source performans koruması
- Beklenen: Yalnız güvenilir rol ve source kapsamı sorgulanır; son aggregate skor görünür; ham kayıt alanı çıkmaz; hesaplanamayan sonuç sıfırlaşmaz; görüntüleme veri-minimum auditlenir.
- Gerçekleşen: 459 test geçti; reporting hedef grubu 18 testle geçti ve 18 yeni vaka eklendi.
- Sonuç: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Reporting yüzeyinde `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- Reporting paketi ve testinde `mypy ...`: PASS
- 500 source ve 20 tekrarlı bellek içi p95 koruma testi 1 saniyenin altında: PASS; üretim kapasite kanıtı değildir.
- Tam depo format kontrolü, değişiklik dışındaki dört eski dosyanın biçim farkı nedeniyle PASS değildir.
- Tam mypy kontrolü, yedi eski dosyada 27 hata nedeniyle PASS değildir.

## Güvenlik

- Güven sınırı: Yalnız güvenilir, geçerli, ayrıcalıksız USER context'ı ve izinli raporlama rolü kabul edilir. Serbest actor, rol veya scope yetki kanıtı değildir.
- Scope: İstenen source kimlikleri context kapsamında değilse reader çağrılmaz; SQL yalnız yetkili source placeholder'larıyla çalışır.
- Veri minimizasyonu: Onizleme yalnız source kimliği, aggregate skor/durum/seviye ve zaman taşır; execution, rüle, çalculation detail, ham kayıt ve hata örneği yoktur.
- Maskeleme: `AGGREGATED_ONLY` sabittir; audit source/filter kimliklerini değil yalnız politika, gerekçe kodu, pencere ve sayısal özetleri taşır.
- Teknik hata ayrımı: Geçersiz istek validation, yetki/scope authorization, reader veya audit arızası technical error olarak ayrılır; NO_DATA ve teknik skor sonucu sıfır kalite skoru olmaz.
- Salt okunurluk: SQLite reader için izlenen tüm ifadeler `WITH/SELECT` ile başlar; kaynak sisteme erişim yoktur.
- Maker-checker etkisi: Onizleme dosya veya kalıcı dışa aktarma üretmez. Hassas dışa aktarma onayı ve maker-checker `ComplianceReviewRequired` kalır.
- Geri alma: Reporting servis çağrısı devre dışı bırakılabilir; skor ve audit kayıtları silinmez. Dosya veya geçici artifact temizliği gerekmez.
- Kalan risk: PDF/XLSX/CSV, Report kaydı, asenkron iş, indirme, HTTP/UI, DLP/watermark, dosya saklama/imha ve `OPEN-BNK-002/007/008/014` kapsam dışıdır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.

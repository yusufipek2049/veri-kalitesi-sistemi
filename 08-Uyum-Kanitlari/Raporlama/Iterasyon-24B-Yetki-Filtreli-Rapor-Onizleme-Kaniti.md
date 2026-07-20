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

# Iterasyon 24B Yetki Filtreli Rapor Onizleme Kaniti

## Degisiklik

- Iterasyon: 24B - Yetki filtreli ve maskeli rapor onizleme
- Commit/Artifact: `ITERATION_24B` (`origin/main`)
- Bilesen: `veri_kalitesi.reporting`, `veri_kalitesi.scoring`, `veri_kalitesi.identity`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: FR-072, UC-015, AC-021/023, NFR-PERF-002, NFR-PRV-001/002/003, NFR-SEC-001/005/008, BFR-IAM-001/002/004, BFR-AUD-005 ve BRULE-001/005 alt kapsami

## Dogrulama

- Komut: `PYTHONPATH=03-Backend/src pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek ici SQLite, sentetik toplulastirilmis SOURCE skorlari ve guvenilir fake actor context
- Sentetik veri seti: Yetkili/yetkisiz source, eski/guncel skor, NO_DATA, teknik sonuc, sahte/servis/ayricalikli context, gecersiz filtre, reader/audit arizasi, scope sizintisi ve 500 source performans korumasi
- Beklenen: Yalniz guvenilir rol ve source kapsami sorgulanir; son aggregate skor gorunur; ham kayit alani cikmaz; hesaplanamayan sonuc sifirlasmaz; goruntuleme veri-minimum auditlenir.
- Gerceklesen: 459 test gecti; reporting hedef grubu 18 testle gecti ve 18 yeni vaka eklendi.
- Sonuc: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Reporting yuzeyinde `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- Reporting paketi ve testinde `mypy ...`: PASS
- 500 source ve 20 tekrarli bellek ici p95 koruma testi 1 saniyenin altinda: PASS; uretim kapasite kaniti degildir.
- Tam depo format kontrolu, degisiklik disindaki dort eski dosyanin bicim farki nedeniyle PASS degildir.
- Tam mypy kontrolu, yedi eski dosyada 27 hata nedeniyle PASS degildir.

## Guvenlik

- Guven siniri: Yalniz guvenilir, gecerli, ayricaliksiz USER context'i ve izinli raporlama rolu kabul edilir. Serbest actor, rol veya scope yetki kaniti degildir.
- Scope: Istenen source kimlikleri context kapsaminda degilse reader cagrilmaz; SQL yalniz yetkili source placeholder'lariyla calisir.
- Veri minimizasyonu: Onizleme yalniz source kimligi, aggregate skor/durum/seviye ve zaman tasir; execution, rule, calculation detail, ham kayit ve hata ornegi yoktur.
- Maskeleme: `AGGREGATED_ONLY` sabittir; audit source/filter kimliklerini degil yalniz politika, gerekce kodu, pencere ve sayisal ozetleri tasir.
- Teknik hata ayrimi: Gecersiz istek validation, yetki/scope authorization, reader veya audit arizasi technical error olarak ayrilir; NO_DATA ve teknik skor sonucu sifir kalite skoru olmaz.
- Salt okunurluk: SQLite reader icin izlenen tum ifadeler `WITH/SELECT` ile baslar; kaynak sisteme erisim yoktur.
- Maker-checker etkisi: Onizleme dosya veya kalici disa aktarma uretmez. Hassas disa aktarma onayi ve maker-checker `ComplianceReviewRequired` kalir.
- Geri alma: Reporting servis cagrisi devre disi birakilabilir; skor ve audit kayitlari silinmez. Dosya veya gecici artifact temizligi gerekmez.
- Kalan risk: PDF/XLSX/CSV, Report kaydi, asenkron is, indirme, HTTP/UI, DLP/watermark, dosya saklama/imha ve `OPEN-BNK-002/007/008/014` kapsam disidir.

## Onaylar

- Teknik dogrulayan: Codex teknik uygulama ajani
- Bilgi guvenligi: ComplianceReviewRequired
- Veri yonetisimi: ComplianceReviewRequired
- Ic kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanit teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayi anlamina gelmez.

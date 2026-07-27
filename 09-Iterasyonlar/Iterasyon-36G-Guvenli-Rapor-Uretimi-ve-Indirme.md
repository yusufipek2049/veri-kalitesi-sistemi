---
iteration: 36G
status: TechnicallyVerified
completed_at: 2026-07-24
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36G — Güvenli Rapor Üretimi ve İndirme

## Amaç

Güvenli rapor üretimi ve indirme: PDF/XLSX/CSV dışa aktarma (FR-075),
zamanlanmış rapor (FR-076), sınıflandırma bazlı indirme (UI-WRITE-007),
DLP/watermark/maker-checker/gerekçe/süre framework'ü, asenkron iş ve audit
kaydı. Kontrol yokluğunda fail-closed.

## Kapsam

- Report domain modeli, durum makinesi, PostgreSQL repository
- PDF/XLSX/CSV üretim servisi (politika kontrollü, watermark destekli)
- Asenkron rapor işi — worker protocol + QUEUED→RUNNING→READY/FAILED
- DLP/watermark/maker-checker/gerekçe/süre framework'ü (fail-closed)
- Rapor indirme API'si ve audit kaydı
- Zamanlanmış rapor üretimi (FR-076) — ONCE/DAILY/WEEKLY/MONTHLY
- Frontend rapor talebi/indirme ekranı (özet görünüm, rapor geçmişi)
- Alembic migration (reports + report_schedules tabloları)
- PostgreSQL entegrasyon testleri (gerçek 16.13 üzerinde)

## Kanıt

- [Report domain modelleri](../../03-Backend/src/veri_kalitesi/reporting/models.py)
- [PDF/XLSX/CSV dışa aktarma](../../03-Backend/src/veri_kalitesi/reporting/export.py)
- [Politika framework'ü (DLP/watermark/maker-checker/gerekçe/süre)](../../03-Backend/src/veri_kalitesi/reporting/policies.py)
- [Asenkron worker](../../03-Backend/src/veri_kalitesi/reporting/worker.py)
- [Zamanlanmış rapor servisi](../../03-Backend/src/veri_kalitesi/reporting/scheduling.py)
- [PostgreSQL repository](../../03-Backend/src/veri_kalitesi/reporting/repository.py)
- [Rapor servisi (yetki/audit/indirme)](../../03-Backend/src/veri_kalitesi/reporting/service.py)
- [API endpoints](../../03-Backend/src/veri_kalitesi/api/app.py) (summary, create, list, get, download, schedules CRUD, trigger-due)
- [API modelleri](../../03-Backend/src/veri_kalitesi/api/models.py) (Pydantic istek/yanıt)
- [Geliştirme kurulumu](../../03-Backend/src/veri_kalitesi/api/development.py)
- [Migration — reports tablosu](../../05-Veritabani/alembic/versions/20260724_06_reporting_baseline.py)
- [Migration — report_schedules tablosu](../../05-Veritabani/alembic/versions/20260724_07_report_schedules.py)
- [Frontend ReportsPage](../../04-Frontend/app/src/reports/ReportsPage.tsx)
- [Frontend API client](../../04-Frontend/app/src/reports/api.ts)
- [Frontend modeller](../../04-Frontend/app/src/reports/model.ts)
- [Frontend route bağlantısı](../../04-Frontend/app/src/App.tsx) (ReportsRoute)
- [Birim testleri](../../06-Testler/01-Birim/test_reporting.py)
- [PostgreSQL entegrasyon testleri](../../06-Testler/02-Entegrasyon/test_postgresql_report_lifecycle.py)

## Tamamlama Ölçütleri

1. ✅ Report domain modeli (`Report`, `ReportRequest`, `ReportExportPolicy`,
   `ExportDecision`, `ReportPreview`, `ReportSchedule`) tanımlandı.
2. ✅ PDF/XLSX/CSV üretim servisi watermark desteğiyle çalışıyor.
3. ✅ DLP/watermark/maker-checker/gerekçe/süre framework'ü fail-closed olarak
   uygulandı; politika yoksa veya kontroller geçmezse reddedilir.
4. ✅ Asenkron worker QUEUED→RUNNING→READY/FAILED durum makinesini yürütüyor.
5. ✅ Rapor indirme API'si audit kaydı, süre kontrolü ve dosya teslimi yapıyor.
6. ✅ Zamanlanmış rapor üretimi (FR-076) ONCE/DAILY/WEEKLY/MONTHLY tiplerini
   destekliyor; `trigger_due` vadesi gelen raporları otomatik üretiyor.
7. ✅ Frontend rapor talebi/indirme ekranı (özet görünüm, rapor geçmişi, talep
   dialog'u, indirme butonu) mevcut.
8. ✅ Migration sıfırdan ve mevcut şemadan ileri çalışıyor.
9. ✅ Birim testleri ve PostgreSQL entegrasyon testleri geçiyor.
10. ✅ API endpoint'leri (summary, create, list, get, download, schedules CRUD,
    trigger-due) tanımlandı ve development kuruluma bağlandı.

## Kalan Sınırlar

- Worker dayanıklılığı (retry, timeout, kalıcı kuyruk, dead letter) ayrı
  çalışma paketidir.
- Gerçek üretim IdP/secret manager/HA altyapısı ayrı kapıdır.
- Kurumsal DLP/watermark ürün entegrasyonu ayrı kapıdır.
- XLSX için `openpyxl`, PDF için `reportlab` harici bağımlılıktır; lazy import
  ile yüklenir, eksikse RuntimeError fırlatılır.

## Bağlantılar

- [İterasyon 36 ana planı](Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md)
- [Bir önceki: 36F — Execution Politika ve Worker Dayanıklılığı](Iterasyon-36F-Execution-Politika-Worker-Dayanikliligi.md)
- [Sonraki adım (aktif yol haritası)](../NEXT_STEP.md)
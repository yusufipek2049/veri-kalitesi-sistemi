---
type: next-step
status: completed
updated_at: 2026-07-24
work_package: 36F-WORKER-RESILIENCE
---

# Sıradaki Adım — Execution Politika ve Worker Dayanıklılığı — TAMAMLANDI

36F ile execution domain PostgreSQL-only hale getirildi:

- `ScheduleRepository` protocol tanımlandı, `SchedulingService` gevşetildi
- `PostgreSQLScheduleRepository` ve `PostgreSQLSourceUsagePolicyRepository` oluşturuldu
- `schedules` ve `source_usage_policies` tabloları için migration çalıştırıldı
- `SQLiteScheduleRepository` ve `SQLiteSourceUsagePolicyRepository` runtime export'tan çıkarıldı
- 1134 birim testi, 44 entegrasyon testi geçiyor

## Sıradaki Paket

Güvenli rapor üretimi ve indirme (36G) — DLP, watermark, gerekçe, süreli indirme
ve gerektiğinde maker-checker. Kontrol yokluğunda fail-closed.

**Blokaj:** Kurumsal DLP/watermark/maker-checker kapıları çözülmeden açılmaz.

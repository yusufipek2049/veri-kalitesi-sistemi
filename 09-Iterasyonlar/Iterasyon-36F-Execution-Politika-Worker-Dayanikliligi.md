---
iteration: 36F
status: TechnicallyVerified
completed_at: 2026-07-24
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36F — Execution Politika ve Worker Dayanıklılığı

## Amaç

Execution domaininde kalan SQLite repository'leri (`SQLiteScheduleRepository`,
`SQLiteSourceUsagePolicyRepository`) PostgreSQL'e taşımak ve runtime export
yolundan çıkarmak.

## Kapsam

- `ScheduleRepository` protocol'ü tanımlandı, `SchedulingService` gevşetildi
- `PostgreSQLScheduleRepository` oluşturuldu
- `PostgreSQLSourceUsagePolicyRepository` oluşturuldu
- `schedules` ve `source_usage_policies` tabloları için Alembic migration
- SQLite repository'ler runtime export'tan çıkarıldı; test double olarak kaldı

## Kanıt

- [PostgreSQL schedule repository](../../03-Backend/src/veri_kalitesi/executions/postgresql_scheduling.py)
- [PostgreSQL source usage repository](../../03-Backend/src/veri_kalitesi/executions/postgresql_source_usage.py)
- [Schedule protocol ve SchedulingService güncellemesi](../../03-Backend/src/veri_kalitesi/executions/scheduling.py)
- [Migration](../../05-Veritabani/alembic/versions/20260724_05_scheduling_and_policy_baseline.py)
- [Runtime export temizliği](../../03-Backend/src/veri_kalitesi/executions/__init__.py)

## Tamamlama Ölçütleri

1. ✅ `ScheduleRepository` protocol tanımlandı, `SchedulingService` protocol
   tabanlı hale getirildi.
2. ✅ `PostgreSQLScheduleRepository` ve `PostgreSQLSourceUsagePolicyRepository`
   oluşturuldu, migration çalıştırıldı.
3. ✅ `SQLiteScheduleRepository` ve `SQLiteSourceUsagePolicyRepository` runtime
   export'tan çıkarıldı; testler doğrudan modül import'u kullanıyor.
4. ✅ 1134 birim testi, 44 entegrasyon testi geçiyor.
5. ✅ Migration sıfırdan ve mevcut şemadan ileri çalışıyor.

## Kalan Sınırlar

- Gerçek üretim IdP/secret manager/HA altyapısı ayrı kapıdır.
- Güvenli rapor üretimi/indirme (36G) DLP/watermark/maker-checker framework'ü
  ile başlatılmıştır; kurumsal adaptörler ayrı kapıdır.

## Bağlantılar

- [İterasyon 36 ana planı](Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md)
- [Bir önceki: 36E — Çalıştırma PostgreSQL Cutover](Iterasyon-36E-Calisma-PostgreSQL-Cutover.md)
- [Sonraki: 36G — Güvenli Rapor Üretimi/İndirme (aktif)](../NEXT_STEP.md)
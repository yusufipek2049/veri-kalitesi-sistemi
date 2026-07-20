---
type: implementation-index
area: backend
project: Veri Kalitesi İzleme ve Skorlama Sistemi
generated_at: 2026-07-16
tags:
  - backend
  - index
---

# Backend Modül Haritası

| Bileşen | Gereksinim Kaynağı | Temel Veri Varlıkları |
| --- | --- | --- |
| Kimlik ve RBAC | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.01-Kullanici-ve-Yetki]] | User, Role, Permission |
| Bağlayıcı katmanı | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.02-Veri-Kaynagi-Yonetimi]] | DataSource, Dataset, DataField |
| Profilleme motoru | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.03-Metadata-ve-Profilleme]] | DataProfile |
| Kural yönetimi | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.04-Kural-Yonetimi]] | QualityRule, RuleVersion |
| Scheduler ve worker | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.05-Calistirma-ve-Zamanlama]] | Schedule, RuleExecution, RuleResult |
| Skorlama motoru | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.06-Skorlama]] | QualityScore, QualityDimension |
| Bildirim servisi | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.08-Bildirim]] | Notification |
| Issue servisi | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.09-Sorun-Yonetimi]] | DataQualityIssue, IssueComment |
| Raporlama | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.10-Raporlama]] | Report |
| Audit | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.11-Audit]] | AuditLog |
| API ve entegrasyon | [[01-SRS/04-Fonksiyonel-Gereksinimler/04.12-API-ve-Entegrasyon]] | Tüm servis sözleşmeleri |
| Olay müdahale | [[01-SRS/17-Bankacilik-Uyum/17.02-Bankacilik-Kontrol-Gereksinimleri]] | SecurityIncident, PersonalDataBreachSuspicion, IncidentTimeline |
| Güvenli SDLC yerel kontrolleri | [[01-SRS/17-Bankacilik-Uyum/17.02-Bankacilik-Kontrol-Gereksinimleri]] | SecretScanPolicy, SecretScanReport, PythonProjectInventory, DeclaredDependency |

## Çapraz NFR

[[01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.01-Performans|Performans]] · [[01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.04-Guvenilirlik-ve-Hata-Toleransi|Güvenilirlik]] · [[01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik|Güvenlik]] · [[01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.09-Gozlemlenebilirlik|Gözlemlenebilirlik]]

## Codex Modül Talimatları

- [[01-Kimlik-ve-Yetki/AGENTS|Kimlik ve Yetki modül talimatı]]
- [[02-Veri-Kaynaklari/AGENTS|Veri Kaynakları modül talimatı]]
- [[03-Metadata-ve-Profilleme/AGENTS|Metadata ve Profilleme modül talimatı]]
- [[04-Kural-Yonetimi/AGENTS|Kural Yönetimi modül talimatı]]
- [[05-Calistirma-ve-Zamanlama/AGENTS|Çalıştırma ve Zamanlama modül talimatı]]
- [[06-Skorlama/AGENTS|Skorlama modül talimatı]]
- [[07-Dashboard/AGENTS|Dashboard modül talimatı]]
- [[08-Bildirim/AGENTS|Bildirim modül talimatı]]
- [[09-Sorun-Yonetimi/AGENTS|Sorun Yönetimi modül talimatı]]
- [[10-Raporlama/AGENTS|Raporlama modül talimatı]]
- [[11-Audit/AGENTS|Audit modül talimatı]]
- [[12-API-ve-Entegrasyon/AGENTS|API ve Entegrasyon modül talimatı]]

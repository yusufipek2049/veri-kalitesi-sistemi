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
| Kimlik ve RBAC | [04.01-Kullanici-ve-Yetki](../01-SRS/04-Fonksiyonel-Gereksinimler/04.01-Kullanici-ve-Yetki.md) | User, Role, Permission |
| Bağlayıcı katmanı | [04.02-Veri-Kaynagi-Yonetimi](../01-SRS/04-Fonksiyonel-Gereksinimler/04.02-Veri-Kaynagi-Yonetimi.md) | DataSource, Dataset, DataField |
| Profilleme motoru | [04.03-Metadata-ve-Profilleme](../01-SRS/04-Fonksiyonel-Gereksinimler/04.03-Metadata-ve-Profilleme.md) | DataProfile |
| Kural yönetimi | [04.04-Kural-Yonetimi](../01-SRS/04-Fonksiyonel-Gereksinimler/04.04-Kural-Yonetimi.md) | QualityRule, RuleVersion |
| Scheduler ve worker | [04.05-Calistirma-ve-Zamanlama](../01-SRS/04-Fonksiyonel-Gereksinimler/04.05-Calistirma-ve-Zamanlama.md) | Schedule, RuleExecution, RuleResult |
| Skorlama motoru | [04.06-Skorlama](../01-SRS/04-Fonksiyonel-Gereksinimler/04.06-Skorlama.md) | QualityScore, QualityDimension |
| Bildirim servisi | [04.08-Bildirim](../01-SRS/04-Fonksiyonel-Gereksinimler/04.08-Bildirim.md) | Notification |
| Issue servisi | [04.09-Sorun-Yonetimi](../01-SRS/04-Fonksiyonel-Gereksinimler/04.09-Sorun-Yonetimi.md) | DataQualityIssue, IssueComment |
| Raporlama | [04.10-Raporlama](../01-SRS/04-Fonksiyonel-Gereksinimler/04.10-Raporlama.md) | Report |
| Audit | [04.11-Audit](../01-SRS/04-Fonksiyonel-Gereksinimler/04.11-Audit.md) | AuditLog |
| API ve entegrasyon | [04.12-API-ve-Entegrasyon](../01-SRS/04-Fonksiyonel-Gereksinimler/04.12-API-ve-Entegrasyon.md) | Tüm servis sözleşmeleri |
| Olay müdahale | [17.02-Bankacilik-Kontrol-Gereksinimleri](../01-SRS/17-Bankacilik-Uyum/17.02-Bankacilik-Kontrol-Gereksinimleri.md) | SecurityIncident, PersonalDataBreachSuspicion, IncidentTimeline |
| Güvenli SDLC yerel kontrolleri | [17.02-Bankacilik-Kontrol-Gereksinimleri](../01-SRS/17-Bankacilik-Uyum/17.02-Bankacilik-Kontrol-Gereksinimleri.md) | SecretScanPolicy, PythonProjectInventory, SastReleaseGate, DependencyVulnerabilityReleaseGate, PentestFindingTracker, TechnicalEvidenceManifestBuilder |

## Çapraz NFR

[Performans](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.01-Performans.md) · [Güvenilirlik](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.04-Guvenilirlik-ve-Hata-Toleransi.md) · [Güvenlik](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md) · [Gözlemlenebilirlik](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.09-Gozlemlenebilirlik.md)

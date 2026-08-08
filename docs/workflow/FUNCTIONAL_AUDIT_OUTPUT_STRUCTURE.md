# Fonksiyonel Denetim Çıktı Şablonu

Ajanların oluşturacağı hedef dosyalar:

```text
docs/functional-audit/
├── evidence-inventory/
│   ├── 01-Repository-Structure.md
│   ├── 02-API-Inventory.md
│   ├── 03-Database-Inventory.md
│   ├── 04-Domain-Service-Inventory.md
│   ├── 05-Frontend-Inventory.md
│   ├── 06-Test-Inventory.md
│   ├── 07-Stubs-and-Disconnected-Surfaces.md
│   └── 08-Raw-Traceability-Matrix.md
├── work/
│   ├── 01-Unresolved-Evidence-Questions.md
│   └── 02-Verification-Resolution.md
├── 00-Executive-Summary.md
├── 01-Current-Capabilities.md
├── 02-Target-Capability-Hierarchy.md
├── 03-End-to-End-Workflow-Audit.md
├── 04-Functional-Gap-Inventory.md
├── 05-UI-Information-Architecture.md
├── 06-API-Inventory-and-Gaps.md
├── 07-Target-Data-Model.md
├── 08-Existing-Schema-Gap-Analysis.md
├── 09-State-Machines.md
├── 10-Roles-and-Permissions.md
├── 11-Test-Coverage-Gaps.md
├── 12-Prioritized-Backlog.md
├── 13-Implementation-Roadmap.md
└── 14-Independent-Code-Verification.md
```

Her rapor başlangıcında:

- tarih
- repository ref/commit
- analiz aracı
- kullanılan kanıt kaynakları
- varsayımlar
- kapsam dışı

bilgileri bulunmalıdır.

Her önemli iddia dosya yolu ve sembol kanıtı taşımalıdır.

---
type: architecture-decision-log
project: Veri Kalitesi İzleme ve Skorlama Sistemi
status: seed
last_updated: 2026-07-16
tags:
  - architecture
  - adr
---

# Mimari Kararlar

| ADR | Karar | Durum |
| --- | --- | --- |
| ADR-001 | Kurum içi veri merkezi dağıtımı | Kabul edildi |
| ADR-002 | Kaynaklara salt okunur bağlantı | Kabul edildi |
| ADR-003 | Yerel prototip için konteyner tabanlı modüler monolit | Önerilen başlangıç |
| ADR-004 | Uzun işler için kuyruk ve worker modeli | Önerilen başlangıç |
| ADR-005 | İlişkisel metadata ve sonuç deposu | Önerilen başlangıç |
| ADR-006 | Secret değerleri yerine secret manager referansı | Kabul edildi; ürün TBD |
| ADR-007 | LDAP adaptörü ve RBAC | Kabul edildi; eşleme ayrıntıları TBD |
| ADR-008 | ServiceNow adaptörünün çekirdek issue yönetiminden ayrılması | Önerilen |
| ADR-009 | Merkezi audit için hash zinciri, transactional outbox ve salt okunur/idempotent legacy aktarım | Teknik olarak doğrulandı; üretim ürünü ve operasyon onayı TBD |
| ADR-010 | Kişisel veri işleme envanterinin DataField'e bağlı değişmez sürümler ve redakte transactional audit ile tutulması | Teknik olarak doğrulandı; banka referans sözlükleri TBD |
| ADR-011 | Kritik kural aktivasyonunun sürümlü politika, güvenilir ActorContext ve RuleVersion'a bağlı atomik maker-checker kararıyla yapılması | 19A teknik olarak doğrulandı; scoring ve banka rol eşlemesi TBD |

Ayrıntılar: [[00-Proje-Hafizasi/Alinan-Kararlar|Alınan Kararlar]] ve [[01-SRS/15-Acik-Konular|Açık Konular]].

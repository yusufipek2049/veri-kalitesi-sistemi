---
type: iteration-record
status: PrototypeVerified
work_package: DQ-CAP-PROTOTYPE-05
completed_at: 2026-08-03
---

# DQ-CAP-PROTOTYPE-05 — Bildirim Kanal Adaptörleri, Lab Güvenlik Kapısı ve Deterministik Yürütme Strateji Motoru

## Sonuç

`DQ-CAP-009` (bildirim kanal adaptörleri), `DQ-CAP-012` (kapılı sentetik lab
adaptörleri) ve `DQ-CAP-013` (deterministik yürütme stratejisi) prototip kararları
üç yeni modül olarak commit edildi (`6d79e06`). Sonuç yalnız yerel/sentetik
prototip kanıtıdır; production readiness veya `ApprovedByBank` değildir.

**Modüller henüz composition'a bağlı değildir.** `notifications/channel_adapters.py`,
`environment_security/lab_gate.py` ve `executions/strategy_engine.py` mevcut
akışlara, composition root'una veya `enterprise_lab` kapılarına bağlanmamıştır;
birim testleriyle doğrulanan ayrı modüller olarak durur. Bağımsız review
(`.agent/reviews/DQ-CAP-PROTOTYPE-05/i15-r0.md`, 2026-07-31) `CHANGES_REQUESTED`
sonucu vermiştir; bağlantı ve davranış maddeleri aşağıda açıktır.

- `notifications/channel_adapters.py`: canonical event tüketen kanal adaptörü
  sözleşmesi ve veri-minimum/idempotent teslim modeli. `sla_seconds`,
  `escalation_level`, `max_delivery_attempts` ve `EscalationLevel` MAINT-06 ile
  modelden kaldırılmıştır; kanonik SRS/ADR/karar kaydı yoktu, uygulanmadı,
  uydurulmaz. Teslim tek sabit deneme ile sınırlıdır; retry semantiği yoktur.
  Bağımsız review maddesi bu gerekçeyle kapatılmıştır.
- `environment_security/lab_gate.py`: kapılı sentetik adaptör için fail-closed
  lab kapısı. Mevcut `enterprise_lab/gate.py` kapısından ayrı ve çağrılmayan bir
  modüldür; review çift kapı kaynağını gidermek için bağlanmasını veya tek
  kanonik konuma taşınmasını istemiştir.
- `executions/strategy_engine.py`: `OPEN-033` ile uyumlu deterministik strateji
  modeli (full/partition/incremental/sample/aggregate). PARTITION resume
  semantiği MAINT-05 ile sözleşmeye uygun hale getirilmiştir: tamamlanmış son
  partition/checkpoint sınırından devam edilir; tamamlanmış sınır yoksa
  fail-closed reddedilir. Modül `executions/__init__.py`'den export edilir ve
  `PostgreSQLExecutionStartService` composition köküne bağlanmıştır (ADR-021).
- Eşik varsayılanları (`MAX_EVIDENCE_AGE_SECONDS = 3600`,
  `dedup_window_seconds = 300`, `timeout_seconds = 3600`) MAINT-02 ile kapatılmıştır:
  `dedup_window_seconds` ve `timeout_seconds` zorunlu parametreye çevrilmiştir;
  `MAX_EVIDENCE_AGE_SECONDS` gate sınıfından kaldırılmış ve composition köküne
  (`adapters.py`) açık parametre olarak taşınmıştır. Lab kanıt ömrünün sürümlü
  politikaya/lab yapılandırmasına bağlanması MAINT-04 ile tamamlanmıştır:
  `max_evidence_age_seconds` değeri `environment.json` (schema_version 2)
  yapısına taşınmış ve doğrulanmış kanıt nesnesi üzerinden gate'e bağlanmıştır.
  `ExecutionStrategyPolicy` ve `NotificationChannelPolicy` artık zorunlu
  alan ister; bu kırıcı bir değişikliktir.

## Doğrulama

- `python3 -m pytest -q tests/unit/test_prototype_05_capabilities.py`
  → `39 passed` (üç modülün sözleşme davranışı; MAINT-05 ile PARTITION resume
  senaryoları eklendi).
- Birim + entegrasyon paketi bu commit için yeşildir; strateji motoru artık
  production composition köküne bağlıdır.

Bu kayıt production PostgreSQL uygunluğu veya banka onayı iddia etmez. Modüllerin
diğer bağımsız review maddeleri (çift kapı, doküman kapanışı) açık kalır;
`docs/compliance` kanıt kaydı bu turun kapsamında değildir. Kurumsal
IdP/PAM/SIEM/ServiceNow ve production ortam `ExternalDependency` olarak açık kalır.

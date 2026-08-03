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
  `escalation_level` ve `max_delivery_attempts` model alanı olarak tanımlıdır
  ancak dispatcher'da henüz uygulanmamıştır (`attempt` sabit 1); review bu
  alanların uygulanmasını veya modelden çıkarılmasını istemiştir.
- `environment_security/lab_gate.py`: kapılı sentetik adaptör için fail-closed
  lab kapısı. Mevcut `enterprise_lab/gate.py` kapısından ayrı ve çağrılmayan bir
  modüldür; review çift kapı kaynağını gidermek için bağlanmasını veya tek
  kanonik konuma taşınmasını istemiştir.
- `executions/strategy_engine.py`: `OPEN-033` ile uyumlu deterministik strateji
  modeli (full/partition/incremental/sample/aggregate). Mevcut kod tamamlanmamış
  partition varsa tüm stratejiyi reddeder; sözleşmedeki "resume yalnız
  tamamlanmış partition/checkpoint sınırında yapılır" hükmü tamamlanmış son
  sınırdan devam edecek şekilde henüz uygulanmamıştır. Modül
  `executions/__init__.py`'den export edilmemiştir.
- Eşik varsayılanları (`MAX_EVIDENCE_AGE_SECONDS = 3600`,
  `dedup_window_seconds = 300`, `timeout_seconds = 3600`) MAINT-02 ile kapatılmıştır:
  `dedup_window_seconds` ve `timeout_seconds` zorunlu parametreye çevrilmiştir;
  `MAX_EVIDENCE_AGE_SECONDS` gate sınıfından kaldırılmış ve composition köküne
  (`adapters.py`) açık parametre olarak taşınmıştır. Lab kanıt ömrünün sürümlü
  politikaya/lab yapılandırmasına bağlanması MAINT-04 ile açık iş olarak takip
  edilir. `ExecutionStrategyPolicy` ve `NotificationChannelPolicy` artık zorunlu
  alan ister; bu kırıcı bir değişikliktir.

## Doğrulama

- `python3 -m pytest -q 06-Testler/01-Birim/test_prototype_05_capabilities.py`
  → `33 passed` (üç modülün sözleşme davranışı).
- Birim + entegrasyon paketi bu commit için yeşildir; modüller bağlı olmadığı
  için composition/entegrasyon yüzeyi bu kayıtta doğrulanmamıştır.

Bu kayıt production PostgreSQL uygunluğu veya banka onayı iddia etmez. Modüllerin
composition'a bağlanması, SLA/escalation ve teslim denemesi davranışı, eşiklerin
kanonik karara dayandırılması ve PARTITION resume semantiği bağımsız review'ın
`CHANGES_REQUESTED` maddeleri olarak açıktır; `08-Uyum-Kanitlari` kanıt kaydı bu
turun kapsamında değildir. Kurumsal IdP/PAM/SIEM/ServiceNow ve production ortam
`ExternalDependency` olarak açık kalır.

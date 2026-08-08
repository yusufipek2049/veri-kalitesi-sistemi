# Graphify Mimari Baseline — GQ-00

**Tarih:** 2026-08-07
**Graphify commit:** `0169748e`
**Komut:** `GRAPHIFY_OUT=build/graphify graphify update . --force`

## Özet İstatistikler

| Metrik | Değer |
|---|---|
| Düğüm | 8373 |
| Kenar | 30177 |
| Topluluk | 249 (213 gösterilen, 36 ince) |
| EXTRACTED kenar | 27037 (%89,6) |
| INFERRED kenar | 3140 (%10,4) |
| Import cycle | 2 |
| İzole düğüm (code) | 6 |
| Düşük bağlantılı (deg 1-2) | 1627 |

## Sınıflandırma Etiketleri

| Etiket | Anlam |
|---|---|
| CONFIRMED_HOTSPOT | Kaynak kodla doğrulanmış yüksek yoğunluk merkezi |
| INTENTIONAL_SHARED_CONTRACT | Çapraz-kesen sözleşme; kasıtlı yüksek degree |
| TOOL_FALSE_POSITIVE | Graphify'ın dosya-proxy veya isim çakışmasıyla şişirdiği düğüm |
| NEEDS_SOURCE_VERIFICATION | Kaynak kod incelemesi gereken aday |
| LOW_PRIORITY | Düşük öncelik; müdahale gerekmez |

---

## 1. Yüksek Degree Düğümleri

### 1.1 `_datetime()` — degree=540, `incident_response/repository.py`

**Sınıflandırma: TOOL_FALSE_POSITIVE**

Graphify bu düğümü dosya proxy olarak kullanıyor. 540 kenarın dağılımı:
- `references`: 352 (dosyaya referans veren diğer dosyalar)
- `imports_from`: 115 (dosyadan import eden diğer dosyalar)
- `calls`: 72 (bu sayı da şişirilmiş — `calls` relation'ı stdlib `datetime` çağrılarını da bu düğüme yönlendiriyor)

**Kaynak kod doğrulaması:**
- `def _datetime(value: str)` — dosya-içi 7 çağrı (satır 282, 286, 304, 341, 349, 357, 358)
- Çapraz-dosya çağrı: **0** (fonksiyon modül-içi private)
- Graphify'ın atadığı kaynak dosyalar (41 farklı dosya) bu fonksiyonu çağırmıyor;
  `incident_response/repository.py` dosyasına olan referanslar bu düğüme toplanmış.

**Aksiyon:** Yok. Graphify limitasyonu — private fonksiyonlar için dosya-proxy etkisi.

### 1.2 `ActorContext` — degree=331, `identity/models.py`

**Sınıflandırma: INTENTIONAL_SHARED_CONTRACT**

331 kenarın dağılımı:
- `imports`: 43 (dosya-içi import)
- `references`: 286 (tip belirteci, parametre tipi, return tipi olarak kullanım)
- `calls`: 1

**Kaynak kod doğrulaması:**
- `ActorContext` tüm yetkilendirme sınırının temel modelidir
- `identity/`, `api/`, `audit/`, `issues/`, `jobs/` modüllerinde kullanılır
- Yüksek degree beklenen — bu kasıtlı bir paylaşım sözleşmesidir

**Aksiyon:** Yok. Rule 4 uyarınca korunacak sözleşme.

### 1.3 `PreparedAuditEvent` — degree=265, `audit/models.py`

**Sınıflandırma: INTENTIONAL_SHARED_CONTRACT**

265 kenarın dağılımı:
- `imports`: 41
- `references`: 222
- `calls`: 0 (dataclass/model — çağrılmaz, referans edilir)

**Kaynak kod doğrulaması:**
- Audit pipeline'ının temel veri taşıyıcısı
- `audit/outbox.py`, `audit/postgresql_outbox.py`, `audit/redaction.py` başta olmak üzere
  tüm audit modüllerinde kullanılır
- Rule 4 uyarınca cross-cutting audit sözleşmesi — korunacak

### 1.4 `app.py` — degree=232, `api/app.py`

**Sınıflandırma: CONFIRMED_HOTSPOT**

232 kenar (out=227): Composition root. Tüm servis sınıflarının örneklenip
routing'e bağlandığı dosya. 1884 file-level kenar ile en yoğun dosya.

**Risk:** Composition root olarak tek sorumluluğu var, ancak 100+ satırda
10+ servis sınıfının örneklenmesi değiştirilme sıklığını artırır.

**Aksiyon:** İzleme. Şu anlık yapısal sorun yok — Rule 7 uyarınca yeni
Facade/Coordinator eklenmez.

### 1.5 `App.tsx` — degree=212, `frontend/src/App.tsx`

**Sınıflandırma: INTENTIONAL_SHARED_CONTRACT**

Frontend composition root. Route tanımları ve provider wrapping'inin
bulunduğu dosya. Frontend tarafının doğal merkezi.

### 1.6 Diğer Yüksek Degree (deg 100-160)

| Düğüm | degree | Dosya | Sınıflandırma |
|---|---|---|---|
| `PostgreSQLTransactionalAudit` | 160 | `audit/postgresql_outbox.py` | INTENTIONAL_SHARED_CONTRACT — audit transaction boundary |
| `transactional_session()` | 154 | `persistence/database.py` | INTENTIONAL_SHARED_CONTRACT — tüm DB işlemlerinin gateway'i |
| `audit/__init__.py` | 146 | `audit/__init__.py` | LOW_PRIORITY — re-export hub (10 sembol) |
| `SQLiteTransactionalAudit` | 146 | `audit/outbox.py` | INTENTIONAL_SHARED_CONTRACT — SQLite audit boundary |
| `identity/__init__.py` | 132 | `identity/__init__.py` | LOW_PRIORITY — re-export hub (6 sembol) |
| `api/models.py` | 130 | `api/models.py` | CONFIRMED_HOTSPOT — API request/response modelleri |
| `create_dashboard_api()` | 125 | `api/app.py` | NEEDS_SOURCE_VERIFICATION — tek fonksiyon için yüksek |
| `development.py` | 124 | `api/development.py` | LOW_PRIORITY — dev-only composition |
| `RuleExecution` | 123 | `executions/models.py` | INTENTIONAL_SHARED_CONTRACT — execution model |
| `AuditEventInput` | 123 | `audit/models.py` | INTENTIONAL_SHARED_CONTRACT — audit input model |

---

## 2. Import Cycle'lar

### Cycle 1: identity ↔ audit ↔ incident_response (4 dosya)

```
identity/models.py
  → incident_response/repository.py
    → audit/__init__.py
      → audit/service.py
        → identity/models.py
```

**Sınıflandırma: NEEDS_SOURCE_VERIFICATION**

`identity/models.py` → `incident_response/repository.py` bağlantısı
beklenmedik. `identity` modülü `incident_response`'a doğrudan import
bağımlılığı olmamalı (audit üzerinden dolaylı olabilir).

**Aksiyon:** İlerleyen iterasyonda `incident_response/repository.py`'nin
`identity/models.py`'yi doğrudan import edip etmediğini kaynak kodda doğrula.
Eğer ediyorsa, bu bağı `identity/contracts.py` gibi bir interface modülüne
çekme adayı.

### Cycle 2: audit ↔ incident_response (3 dosya)

```
incident_response/repository.py
  → audit/__init__.py
    → audit/service.py
      → incident_response/repository.py
```

**Sınıflandırma: NEEDS_SOURCE_VERIFICATION**

Cycle 1'in alt kümesi. `audit/service.py`'nin `incident_response/repository.py`'yi
import etmesi — audit servisi incident response repository'sine bağımlı.
Bu, audit modülünün incident_response'a aşağı yönlü bağımlılık ilkesini
ihlal edebilir.

---

## 3. EXTRACTED Cross-File Edge Yoğunluğu

İlk 10 EXTRACTED cross-file kenar çifti (service → model ilişkileri baskın):

| Kaynak → Hedef | Kenar | İlişki deseni |
|---|---|---|
| `api/app.py` → `api/models.py` | 117 | API handler → request/response modelleri |
| `data_sources/postgresql_repository.py` → `data_sources/models.py` | 95 | Repository → domain modelleri |
| `issues/service.py` → `issues/models.py` | 90 | Service → domain modelleri |
| `data_sources/repository.py` → `data_sources/models.py` | 82 | Repository → domain modelleri |
| `data_sources/service.py` → `data_sources/models.py` | 81 | Service → domain modelleri |
| `issues/postgresql_repository.py` → `issues/models.py` | 61 | Repository → domain modelleri |
| `synthetic_data/repository.py` → `synthetic_data/models.py` | 61 | Repository → domain modelleri |
| `servicenow/service.py` → `servicenow/models.py` | 60 | Service → domain modelleri |
| `jobs/postgresql_repository.py` → `jobs/models.py` | 56 | Repository → domain modelleri |
| `data_sources/service.py` → `data_sources/errors.py` | 54 | Service → hata sınıfları |

**Gözlem:** Cross-file kenarlar baskın olarak service/repository → model
yönünde. Bu, domain modellerinin merkezi ve beklenen bir pattern.
`api/app.py`'nin 117 kenarla `api/models.py`'ye bağlanması composition
root'un doğal sonucu.

---

## 4. INFERRED Edge Yoğunluğu

Toplam 3140 INFERRED kenar. Dağılım:
- `uses`: 2208 (%70,3)
- `calls`: 895 (%28,5)
- `indirect_call`: 37 (%1,2)

### 4.1 En yoğun INFERRED hedefler (isim çakışması adayları)

| Hedef | INFERRED kenar | Değerlendirme |
|---|---|---|
| `AuditRedactor` | 77 | NEEDS_SOURCE_VERIFICATION — audit redaction geniş kullanım |
| `DevelopmentActorContextResolver` | 57 | TOOL_FALSE_POSITIVE — dev-only resolver, testlerde şişirilmiş |
| `DevelopmentUserRegistry` | 42 | TOOL_FALSE_POSITIVE — dev-only registry, testlerde şişirilmiş |
| `IssueAssigneeOptionResponse` | 40 | NEEDS_SOURCE_VERIFICATION |
| `build_default_redaction_policy()` | 40 | NEEDS_SOURCE_VERIFICATION |
| `ActorContextIssuer` | 36 | INTENTIONAL_SHARED_CONTRACT |
| `ApiAuthenticationError` | 35 | LOW_PRIORITY — hata sınıfı, geniş yakalama |
| `ApiSessionUnavailableError` | 30 | LOW_PRIORITY — hata sınıfı |
| `SQLiteAuditRepository` | 30 | INTENTIONAL_SHARED_CONTRACT |

### 4.2 En yoğun INFERRED cross-file çifti

`api/app.py` → `api/models.py`: 1248 INFERRED kenar. Bu, EXTRACTED 117
kenarın 10 katı. Graphify'ın `uses` inference'ı, `app.py`'deki tüm model
referanslarını (tip belirteçleri, isinstance kontrolleri, dict erişimleri)
ayrı ayrı kenar olarak çıkarıyor.

**Sınıflandırma: TOOL_FALSE_POSITIVE (şişirme)** — gerçek bağımlılık
sayısı çok daha düşük; INFERRED kenarlar aynı bağımlılığın farklı
ifade biçimlerini ayrı kenar olarak sayıyor.

---

## 5. Re-Export Hub'ları

| Dosya | Re-export sayısı | Değerlendirme |
|---|---|---|
| `data_sources/__init__.py` | 12 | INTENTIONAL_SHARED_CONTRACT — modül API yüzeyi |
| `scoring/__init__.py` | 12 | INTENTIONAL_SHARED_CONTRACT |
| `executions/__init__.py` | 11 | INTENTIONAL_SHARED_CONTRACT |
| `notifications/__init__.py` | 11 | INTENTIONAL_SHARED_CONTRACT |
| `audit/__init__.py` | 10 | INTENTIONAL_SHARED_CONTRACT |
| `issues/__init__.py` | 9 | INTENTIONAL_SHARED_CONTRACT |

Tüm re-export hub'ları `__init__.py` dosyalarında — bunlar modül public
API'sinin tanımlandığı noktalardır. Kasıtlı pattern; müdahale gerekmez.

---

## 6. Cross-Module Bağımlılık Yoğunluğu

En yoğun modüller arası kenarlar:

| Kaynak modül → Hedef modül | Kenar | Değerlendirme |
|---|---|---|
| `api` → `data_sources` | 32 | CONFIRMED_HOTSPOT — API composition |
| `api` → `audit` | 27 | INTENTIONAL_SHARED_CONTRACT — audit boundary |
| `api` → `identity` | 23 | INTENTIONAL_SHARED_CONTRACT — auth boundary |
| `api` → `executions` | 21 | CONFIRMED_HOTSPOT |
| `data_sources` → `data_protection` | 19 | INTENTIONAL_SHARED_CONTRACT |
| `jobs` → `audit` | 19 | INTENTIONAL_SHARED_CONTRACT |
| `api` → `issues` | 18 | CONFIRMED_HOTSPOT |
| `api` → `rules` | 18 | CONFIRMED_HOTSPOT |
| `retention` → `audit` | 18 | INTENTIONAL_SHARED_CONTRACT |

**Gözlem:** `api` modülü 9 farklı modüle 174 cross-module kenarla
merkezi composition hub'ı. `audit` modülü 6 farklı modülden toplam 92
kenar alarak en çok bağımlılık çekilen cross-cutting concern.

---

## 7. İzole ve Düşük Bağlantılı Düğümler

### 7.1 İzole düğümler (degree=0): 6

| Dosya | Değerlendirme |
|---|---|
| `frontend/vite.config.ts` | LOW_PRIORITY — config dosyası |
| `pyproject.toml` | LOW_PRIORITY — paket config |
| `frontend/src/vite-env.d.ts` | LOW_PRIORITY — TypeScript env declaration |
| `frontend/src/test/setup.ts` | LOW_PRIORITY — test setup |
| `frontend/vitest.config.ts` | LOW_PRIORITY — test config |
| `frontend/playwright.config.ts` | LOW_PRIORITY — e2e config |

Tümü config/setup dosyaları — beklenen durum.

### 7.2 Düşük bağlantılı (degree 1-2): 1627

Bunların büyük çoğunluğu fonksiyon parametreleri, tip belirteçleri ve
tek-kullanımlık helper'lar. Ayrı sınıflandırma gerektirmez.

---

## 8. Graphify False-Positive / İsim Çakışması Adayları

### 8.1 Dosya-Proxy Etkisi

Graphify, aynı dosyada tanımlı birden fazla sembol olduğunda, dosyaya
yönelen referansları tek bir "representative" düğüme toplayabiliyor.
Bu etki `_datetime()` (540), `ActorContext` (331) ve `PreparedAuditEvent`
(265) düğümlerinde gözlemlendi.

**Etkilenen düğümler:** Aynı dosyada 3+ sembol tanımlı olan ve yüksek
`references`/`imports_from` alan tüm düğümler.

**Çözüm yaklaşımı:** Graphify'ın düğüm seçiminde dosya-içi sembol
dağılımını dikkate alması gerekir. Şu anlık, derece sıralaması yaparken
`calls` relation'ına göre filtreleme yapılmalıdır.

### 8.2 INFERRED `uses` Şişirmesi

`api/app.py` → `api/models.py` arasında 1248 INFERRED `uses` kenarı var.
Bu, aynı bağımlılığın farklı kullanım biçimlerini (type hint, isinstance,
dict access) ayrı kenar olarak sayan inference motorunun şişirmesi.

---

## 9. Özet: Doğrulanmış Hotspot Listesi

Sonraki iterasyonlarda kullanılacak sınıflandırılmış liste:

### CONFIRMED_HOTSPOT (5)

1. `api/app.py` — composition root, 1884 file-level kenar
2. `api/models.py` — 130 degree, API request/response modelleri
3. `data_sources/service.py` — 109 degree, 81 cross-file model bağımlılığı
4. `data_sources/postgresql_repository.py` — 95 cross-file model bağımlılığı
5. `issues/service.py` — 90 cross-file model bağımlılığı

### INTENTIONAL_SHARED_CONTRACT (12)

1. `ActorContext` — identity/models.py, degree=331
2. `PreparedAuditEvent` — audit/models.py, degree=265
3. `transactional_session()` — persistence/database.py, degree=154
4. `PostgreSQLTransactionalAudit` — audit/postgresql_outbox.py, degree=160
5. `SQLiteTransactionalAudit` — audit/outbox.py, degree=146
6. `RuleExecution` — executions/models.py, degree=123
7. `AuditEventInput` — audit/models.py, degree=123
8. `AuditRedactor` — audit/redaction.py, degree=98
9. `QualityScore` — scoring/models.py, degree=101
10. `DataSource` — data_sources/models.py, degree=113
11. `RuleVersion` — rules/models.py, degree=113
12. Tüm `__init__.py` re-export hub'ları

### TOOL_FALSE_POSITIVE (4)

1. `_datetime()` — degree=540, dosya-proxy etkisi, gerçek çağrı: 7 (file-içi)
2. `DevelopmentActorContextResolver` — 57 INFERRED, dev-only
3. `DevelopmentUserRegistry` — 42 INFERRED, dev-only
4. `api/app.py` → `api/models.py` INFERRED 1248 kenar, `uses` şişirmesi

### NEEDS_SOURCE_VERIFICATION (4)

1. `identity/models.py` → `incident_response/repository.py` import cycle
2. `audit/service.py` → `incident_response/repository.py` import cycle
3. `create_dashboard_api()` — degree=125, tek fonksiyon için yüksek
4. `IssueAssigneeOptionResponse` — 40 INFERRED kenar

### LOW_PRIORITY

- 6 izole config dosyası düğümü
- 1627 düşük bağlantılı düğüm
- Hata sınıfı düğümleri (ApiAuthenticationError vb.)

---

## 10. Çıkış Kapısı Durumu

| Kriter | Durum |
|---|---|
| Kaynak kod değişmedi | ✅ — Yalnızca docs/config düzeltmeleri |
| Doğrulanmış hotspot listesi hazır | ✅ — 5 CONFIRMED, 12 INTENTIONAL, 4 FALSE_POSITIVE |
| EXTRACTED ve INFERRED kanıtlar ayrı | ✅ — %89.6 EXTRACTED, %10.4 INFERRED |
| Graphify yeni yapıyı analiz ediyor | ✅ — 8373 düğüm, 0 eski dizin referansı |

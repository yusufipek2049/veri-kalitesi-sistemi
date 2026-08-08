# Evidence Inventory — Index

> Salt okunur mekanik envanter. Yalnızca kod kanıtı, dokümantasyon beyanı değil.
>
> Bu envanter `COMPREHENSIVE_FUNCTIONAL_AUDIT_PROMPT.md` görev kapsamına hazırlık olarak
> repository'nin mevcut durumunu dosya yolu, sınıf/fonksiyon adı ve sembol referanslarıyla kaydeder.

## Dosyalar

| # | Dosya | Kapsam |
|---|-------|--------|
| 01 | [01-Backend-Module-Inventory.md](01-Backend-Module-Inventory.md) | 21 backend modülü, domain modelleri, servis katmanı, persistence, composition root |
| 02 | [02-API-Endpoint-Inventory.md](02-API-Endpoint-Inventory.md) | 44 API endpoint, eksik endpoint'ler, pagination/filtering durumu |
| 03 | [03-Frontend-Module-Inventory.md](03-Frontend-Module-Inventory.md) | 11 route, 8 modül, shared components, API mapping, eksik sayfalar |
| 04 | [04-Database-Schema-Inventory.md](04-Database-Schema-Inventory.md) | 14 migration, ~25 tablo, constraint/index detayları, tablosuz modeller |
| 05 | [05-Test-Inventory.md](05-Test-Inventory.md) | 57 birim testi, 13 entegrasyon testi, 7 E2E spec, coverage gaps |
| 06 | [06-Infrastructure-Inventory.md](06-Infrastructure-Inventory.md) | Python/FastAPI, React/Vite, Docker Compose, CI/CD, scripts |
| 07 | [07-Implementation-Status-Matrix.md](07-Implementation-Status-Matrix.md) | 30 fonksiyonel alan, 8 uçtan uca akış, kritik yapısal boşluklar |
| 08 | [08-Repository-Comprehension-Guide.md](08-Repository-Comprehension-Guide.md) | Kavramlar sözlüğü, durum makineleri, veri akışları, mimari, kimlik doğrulama, ayağa kaldırma, test stratejisi, modül bağımlılıkları, FE-BE sözleşmesi |

## Sayısal Özet

| Kategori | Sayı |
|----------|------|
| Backend Python modülleri | 21 |
| Backend Python dosyaları | 176 |
| API endpoint (implemented) | 44 |
| API endpoint (missing, expected) | 22+ |
| Frontend route | 11 |
| Frontend modül | 8 |
| Frontend shared component | 10 |
| PostgreSQL migration | 14 |
| PostgreSQL tablo | ~25 |
| Tablosuz domain modeli | 9+ |
| Birim test dosyası | 57 |
| Entegrasyon test dosyası | 13 |
| E2E test spec | 7 |
| Docker Compose servis | 10 |
| Comprehension Guide bölüm sayısı | 10 |

## Methodology

- Yalnızca kod dosyaları tarandı; `.md` dokümantasyon beyanları kanıt sayılmadı.
- Her bulgu için dosya yolu ve mümkünse satır/sınıf/fonksiyon referansı verildi.
- "Implemented" yalnızca `model → migration → service → API → frontend` zincirinin en az 3 halkası doğrulandığında kullanıldı.
- Domain modeli var ama migration/API/UI yoksa `MODEL_ONLY` olarak işaretlendi.
- Backend'de tam çalışan ama frontend'i olmayan alanlar `BE_ONLY` olarak işaretlendi.

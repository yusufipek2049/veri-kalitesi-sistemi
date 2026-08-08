# Qoder — Repository Kanıt Envanteri Promptu

`docs/audit-instructions/COMPREHENSIVE_FUNCTIONAL_AUDIT_PROMPT.md` dosyasını
yalnızca görev kapsamını anlamak için oku.

Bu aşamada:

- hedef sistem tasarlama
- gap önceliği verme
- kaynak kodu değiştirme
- migration değiştirme
- test değiştirme
- mevcut ürün dokümantasyonunu değiştirme

Yalnızca `docs/functional-audit/evidence-inventory/` altında yeni Markdown
dosyaları oluşturabilirsin.

Her kayıtta dosya yolu, sınıf/fonksiyon adı ve mümkünse satır veya sembol
referansı ver. Dokümantasyon beyanını uygulama kanıtı sayma.

## Q1 — Repository ve composition root

Üret:

`01-Repository-Structure.md`

Çıkar:

- backend/frontend giriş noktaları
- dependency injection/composition root
- runtime adapter seçimleri
- PostgreSQL, SQLite ve in-memory yolları
- worker ve scheduler başlangıç noktaları
- rapor worker'ları
- environment değişkenleri

## Q2 — API envanteri

Üret:

`02-API-Inventory.md`

Her endpoint:

- method/path
- route dosyası
- request/response modeli
- servis metodu
- permission/scope
- frontend çağrısı
- test

## Q3 — Veri tabanı envanteri

Üret:

`03-Database-Inventory.md`

Her migration/tablo:

- kolon ve tip
- PK/FK
- unique/check
- index
- JSONB
- audit alanları
- optimistic locking
- yazan repository
- kullanan servis

## Q4 — Domain ve servis

Üret:

`04-Domain-Service-Inventory.md`

- domain nesneleri
- enum'lar
- durum geçişleri
- command/service metotları
- yetki kontrolleri
- transaction sınırları

## Q5 — Frontend

Üret:

`05-Frontend-Inventory.md`

- route/page/dialog/form
- tablo kolonları
- filtreler
- mutation ve API bağlantısı
- mock veri
- loading/error/empty state
- yetki bazlı eylemler

## Q6 — Test

Üret:

`06-Test-Inventory.md`

Testleri ayır:

- unit
- gerçek PostgreSQL
- SQLite
- in-memory
- mock
- API
- authorization/scope
- audit/outbox
- frontend
- Playwright
- concurrency
- worker recovery
- failure path

## Q7 — Stub ve kopuk yüzeyler

Üret:

`07-Stubs-and-Disconnected-Surfaces.md`

Ara:

- TODO/FIXME
- NotImplemented/pass
- stub/fake/mock/placeholder/demo/sample
- in-memory/SQLite fallback
- unused route/service/repository
- kayıtlı olmayan endpoint
- frontend'den çağrılmayan API
- production composition root'a bağlanmayan adapter

## Q8 — Ham izlenebilirlik

Üret:

`08-Raw-Traceability-Matrix.md`

| Fonksiyon | Domain | Migration/Tablo | Repository | Service | API | Frontend | Permission | Audit | Test |
|---|---|---|---|---|---|---|---|---|---|

Yorum ve çözüm önerisini minimumda tut. Kanıt bulunamazsa açıkça belirt.

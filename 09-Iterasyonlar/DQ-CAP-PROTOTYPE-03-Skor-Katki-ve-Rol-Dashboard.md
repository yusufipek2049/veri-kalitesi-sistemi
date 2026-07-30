---
type: iteration-record
status: PrototypeVerified
work_package: DQ-CAP-PROTOTYPE-03
completed_at: 2026-07-30
---

# DQ-CAP-PROTOTYPE-03 — Skor Katkısı, Karşılaştırma ve Rol Görünümü

## Sonuç

`DQ-CAP-005`, `DQ-CAP-011` ve `DQ-CAP-015` prototip kararları mevcut scoring
ve dashboard mimarisi genişletilerek uygulandı. Sonuç yalnız yerel/sentetik
prototip kanıtıdır; production readiness veya `ApprovedByBank` değildir.

- Mevcut değişmez `QualityScore.calculation_details` snapshot'ından dahil ve
  dışlanan bileşen, kanonik sayaç, ağırlık, katkı, dışlama nedeni, kritik
  veto/durum, yeterlilik/kapsam ve sürüm referanslarını ayıran
  `DQ_SCORE_CONTRIBUTION_GRAPH_V1` üretilir.
- Ham skor; teknik durum, ölçüm yeterliliği, risk, kritik kural ve kullanım
  kararından ayrı kalır. Eksik kanıt `Unknown` olur.
- Resmî/provizyonel ayrımı korunur. Dönem farkı yalnız aynı kapsam ve tüm
  gerekli model/politika/profil/yeterlilik/yönetişim sürümleriyle hesaplanır;
  eksik sürüm `UNKNOWN`, değişen sürüm `NOT_COMPARABLE` üretir.
- Ortak dashboard API güvenilir scope filtresini korur. `DATA_ENGINEER`
  görünümü yalnız aktörün dataset/source scope'undaki veri-minimum bileşen
  grafiğini, diğer yetkili roller yönetici özetini alır; yönetici payload'ına
  component/dataset kırılımı taşınmaz.
- Yönetici ekranı yeterlilik ve kritik kontrol kartlarının yanında kritik asset,
  bozulma, risk ve SLA durumunu; mühendis ekranı profil sürümü, güvenli kanıt
  referansı ve kanıtlı teşhisi gösterir. Kanıt yokluğu `UNKNOWN` kalır.
- API'nin ham skoru nihai skor diye etiketlenmez; onaylı eşik bulunmadığından
  trend grafiğine sabit eşik çizgisi eklenmez.
- PostgreSQL migration ve değişmez repository eklendi. Grafik ile hazırlanmış
  audit olayı aynı transaction içindeki audit outbox'a yazılır.

## Doğrulama

- `PYTHONPATH=03-Backend/src pytest -q
  06-Testler/01-Birim/test_score_contributions.py
  06-Testler/01-Birim/test_scoring.py
  06-Testler/01-Birim/test_dashboard.py
  06-Testler/01-Birim/test_dashboard_api.py` → `101 passed`
- `npm test -- --run src/dashboard/model.test.ts src/dashboard/api.test.ts`
  → `10 passed`
- `npx playwright test e2e/dashboard.spec.ts` → `15 passed`
- `pytest -q -rs
  06-Testler/02-Entegrasyon/test_postgresql_score_contributions.py`
  → skipsiz `1 passed`
- Python compileall ve `git diff --check` → exit `0`

Canlı test yalnız controller'ın sağladığı test PostgreSQL şemasında migration,
değişmez snapshot ve audit/outbox rollback sınırını doğrular. Bu kayıt production
PostgreSQL uygunluğu iddia etmez.

Genel frontend typecheck, bu paket dışında önceden bulunan `App.tsx`,
`DevelopmentLoginPage.tsx` ve `ReportsPage.tsx` tip hataları nedeniyle exit
`1` verdi; değişen dashboard hedef testleri exit `0` tamamlandı.

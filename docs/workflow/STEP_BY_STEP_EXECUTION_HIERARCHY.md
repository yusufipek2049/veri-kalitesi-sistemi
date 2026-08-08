# Adım Adım Uygulama Hiyerarşisi

## 0. Güvenli çalışma alanı

```bash
cd /home/yusuf/veri-kalitesi-sistemi
git status
git fetch origin
git switch main
git pull --ff-only
git switch -c audit/functional-gap-analysis

mkdir -p docs/functional-audit/evidence-inventory
mkdir -p docs/functional-audit/work
mkdir -p docs/audit-instructions
```

İlk aşamada yalnızca analiz dokümanları değişmelidir.

### Çıkış kapısı

- main güncel
- çalışma ağacı temiz
- denetim branch'i oluşturuldu
- kapsamlı prompt repository'ye eklendi
- kaynak kod değişmedi

## 1. Qoder — mekanik repository envanteri

Sıralı çıktılar:

1. `01-Repository-Structure.md`
2. `02-API-Inventory.md`
3. `03-Database-Inventory.md`
4. `04-Domain-Service-Inventory.md`
5. `05-Frontend-Inventory.md`
6. `06-Test-Inventory.md`
7. `07-Stubs-and-Disconnected-Surfaces.md`
8. `08-Raw-Traceability-Matrix.md`

Qoder bu aşamada hedef sistem tasarlamaz ve gap önceliği vermez.

### Çıkış kapısı

- production composition root belirlendi
- runtime adapter'lar belirlendi
- endpoint, tablo, kolon ve route envanteri çıkarıldı
- mock/stub/fallback yüzeyler ayrıldı
- testlerin gerçek altyapısı sınıflandırıldı

## 2. Claude — mevcut kabiliyet haritası

Oku:

- kapsamlı prompt
- Qoder envanterleri
- README ve dokümantasyon indeksleri
- mevcut durum
- SRS indeksi
- aktif iterasyon indeksi

Üret:

- `01-Current-Capabilities.md`
- `work/01-Unresolved-Evidence-Questions.md`

Fonksiyonları `IMPLEMENTED`, `PARTIAL`, `DOC_ONLY`, `MODEL_ONLY`,
`BACKEND_ONLY`, `FRONTEND_ONLY`, `API_ONLY`, `MOCK_ONLY`, `STUB`, `BROKEN`,
`MISSING` ve `EXTERNAL_DEPENDENCY` olarak sınıflandır.

## 3. Claude — bağımsız hedef kabiliyet modeli

Üret:

- `02-Target-Capability-Hierarchy.md`

Bu aşamada repository'nin mevcut uygulama durumunu değerlendirme. Sıfırdan
L0–L5 referans modeli kur.

## 4. Claude — uçtan uca iş akışları

Üret:

- `03-End-to-End-Workflow-Audit.md`

En az kaynak onboarding, profilleme, kural yaşam döngüsü, teknik hata,
kalite problemi, issue, schema drift, skor yeterliliği, istisna ve raporlama
akışlarını denetle.

Her akışın ilk kırılma noktasını göster.

## 5. Claude — fonksiyonel gap envanteri

Üret:

- `04-Functional-Gap-Inventory.md`

Her gap benzersiz olmalı ve hedef fonksiyona bağlanmalıdır.

## 6. Claude — UI ve API hedefi

Üret:

- `05-UI-Information-Architecture.md`
- `06-API-Inventory-and-Gaps.md`

Her ekran gerçek bir aktöre, her endpoint gerçek bir iş akışına bağlı olmalıdır.

## 7. Claude — hedef veri modeli

Üret:

- `07-Target-Data-Model.md`
- `08-Existing-Schema-Gap-Analysis.md`

Her tablo ve kolon için iş anlamı, constraint, index, partition, retention,
audit ve optimistic locking değerlendirmesi yap.

## 8. Claude — state, rol ve test

Üret:

- `09-State-Machines.md`
- `10-Roles-and-Permissions.md`
- `11-Test-Coverage-Gaps.md`

## 9. Codex — bağımsız doğrulama

Üret:

- `14-Independent-Code-Verification.md`

Codex'in amacı Claude'u desteklemek değil, raporu çürütmeye çalışmaktır.

Durumlar:

- `CONFIRMED`
- `CORRECTION_REQUIRED`
- `INSUFFICIENT_EVIDENCE`
- `FALSE_POSITIVE`
- `FALSE_NEGATIVE`
- `SEVERITY_CHANGE_REQUIRED`

## 10. Claude — uzlaştırma

Codex itirazlarını repository kanıtıyla değerlendir.

Üret:

- `work/02-Verification-Resolution.md`

İlgili rapor dosyalarını düzelt.

## 11. Claude — backlog ve yol haritası

Üret:

- `12-Prioritized-Backlog.md`
- `13-Implementation-Roadmap.md`
- `00-Executive-Summary.md`

İterasyonları uçtan uca dikey dilimler halinde oluştur.

## 12. İnsan incelemesi

Öncelikle incele:

- `00-Executive-Summary.md`
- `04-Functional-Gap-Inventory.md`
- `13-Implementation-Roadmap.md`

Kontrol et:

- gereksiz enterprise kapsamı
- salt okunur kaynak sınırı
- mükerrer modeller
- aşırı normalizasyon/JSONB
- P0/P1 gerekçeleri
- mevcut güçlü parçaların gereksiz yeniden yazılması

## 13. Commit

```bash
git status
git diff --stat
git diff --name-only
git add docs/audit-instructions docs/functional-audit
git commit -m "Document functional gap analysis and implementation roadmap"
```

Analiz tamamlanmadan kaynak kod geliştirmesine geçme.

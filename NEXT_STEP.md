---
type: next-step
status: active
updated_at: 2026-07-24
work_package: 36G-SECURE-REPORTING
---

# Sıradaki Adım — Güvenli Rapor Üretimi ve İndirme (36G)

## Kapsam

Güvenli rapor üretimi ve indirme: PDF/XLSX/CSV dışa aktarma (FR-075),
zamanlanmış rapor (FR-076), sınıflandırma bazlı indirme (UI-WRITE-007),
DLP/watermark/maker-checker framework'ü, asenkron iş, gerekçe, süreli indirme.
Kontrol yokluğunda fail-closed.

## Bağımlılıklar

- `OPEN-BNK-014` — `ApprovedByBank`, 36G kapsamında uygulanıyor
- `UI-WRITE-007` — KararAlındı, 36G kapsamında uygulanıyor
- Mevcut `reporting/` modülü (önizleme) üzerine inşa edilecek

## Teslimat Ölçütleri

1. Report domain modeli, durum makinesi, PostgreSQL repository
2. PDF/XLSX/CSV üretim servisi (politika kontrollü)
3. Asenkron rapor işi — kuyruk protocol + worker + API
4. DLP/watermark/maker-checker/gerekçe/süre framework'ü (fail-closed)
5. Rapor indirme API'si ve audit kaydı
6. Zamanlanmış rapor üretimi
7. Frontend rapor talebi/indirme ekranı
8. Migration ve testler

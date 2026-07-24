---
iteration: 36B2
status: TechnicallyVerified
completed_at: 2026-07-23
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36B2 — Güvenilir Yeniden Atama

## Sonuç

Yetkili kullanıcı kapsamındaki açık sorunu, güvenilir veri-minimum aday
kaynağından seçilen aktif/kapsam içi kullanıcıya yeniden atayabilir. BFF/CSRF,
optimistic locking, atomik geçmiş/audit ve kaydedilmemiş değişiklik koruması
uygulanır; bildirim hatası kalite başarısızlığına çevrilmez.

## Bağlantılar

`FR-065`, `FR-070`, `UC-013`, `UI-WRITE-001–003`, `NFR-SEC-001`,
`NFR-SEC-005`, `NFR-SEC-007`, `NFR-SEC-008`, `NFR-SEC-011`,
`NFR-USA-001–006`.

## Kanıt

- Kod: issue servis/API ve frontend yeniden atama penceresi
- Tarihsel kapanış sonucu: `1086 passed, 2 skipped`; frontend `67` Vitest,
  Playwright `89`, type-check/build/Storybook temiz.

## Sınır

Yerel aday listesi yalnız sentetiktir; üretim dizini ve rol/scope eşlemeleri
ayrı kurumsal bağımlılıktır.

---
iteration: 36B1
status: TechnicallyVerified
completed_at: 2026-07-23
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36B1 — Atanmış Sorunu İncelemeye Alma

## Sonuç

Yetkili aktör, kapsamındaki kendisine atanmış `ASSIGNED` sorunu BFF/CSRF ve
sayısal sürüm kontrolüyle `INVESTIGATING` durumuna alabilir. Başarılı mutasyon,
geçmiş ve audit aynı PostgreSQL transaction'ında yazılır; çakışma `409`, teknik
kalıcılık hatası veri-minimum `503` üretir.

## Bağlantılar

`FR-066`, `FR-070`, `UC-013`, `UI-WRITE-001`, `UI-WRITE-002`,
`NFR-SEC-001`, `NFR-SEC-005`, `NFR-SEC-008`, `NFR-SEC-011`,
`NFR-USA-001–006`.

## Kanıt

- Kod: issue servis/API ve `04-Frontend/app/src/issues/IssuesPage.tsx`
- Tarihsel kapanış sonucu: `1081 passed, 2 skipped`; frontend `62` Vitest,
  Playwright `88`, type-check/build/Storybook temiz.

## Sınır

Yerel geliştirme aktörü üretim kimlik kanıtı değildir; gerçek IdP/session store
açık bağımlılıktır.

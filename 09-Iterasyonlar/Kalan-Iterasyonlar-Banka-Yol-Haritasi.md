# Kalan İterasyonlar — Banka Yol Haritası

| İterasyon | Ürün artımı | Ana bağımlılık |
| --- | --- | --- |
| 21 | Güvenilir scope ile dashboard trend (`21A` tamamlandı) ve HTTP read API (`21B` engelli) | 16, 20 |
| 22 | Sistem içi bildirim (`22A`), temel issue (`22B`), yeniden atama (`22C`) ve çözüm kaydı (`22D`) tamamlandı; doğrulama dilimi sırada | 17, 18 |
| 23 | ServiceNow allowlist/idempotency adaptörü | 22 |
| 24 | Kontrollü rapor/audit dışa aktarma | 18, 20 |
| 25 | Saklama politikası dry-run (`25A`) ve kalıcı legal hold (`25B`) tamamlandı; imha ve arşiv geri çağırma açık | Hukuk/uyum kararı |
| 26 | Güvenlik olayı ve KVKK ihlal kanıt akışı (`26A–26B` tamamlandı); gerçek SIEM/SOC engelli | 17, `OPEN-BNK-010` |
| 27 | Ortam ayrılığı, backup/restore ve DR tatbikatı | Altyapı kararı |
| 28 | Güvenli SDLC, SBOM, taramalar ve pentest hazırlığı (`28A`–`28E` yerel teknik sözleşmeleri tamamlandı) | CI/CD ve banka pentest kararı |
| 29 | Teknik kontrol ve banka kabul kanıt paketi (`29A` deterministik manifest ve eksik kontrol raporu tamamlandı) | Tümü |
| 30 | Frontend tasarım sistemi ve kurumsal dashboard (`30A` dokümantasyon tabanı tamamlandı) | Geçiş kapısı, 21B güvenli API ve frontend toolchain kararı |

## Pilot Kapısı

İterasyon 16–20 tamamlanmadan banka pilotu veya hassas veri UAT'si yapılmaz.

## Üretim Kapısı

İterasyon 25–29 ve banka onayları tamamlanmadan üretim uygunluğu ilan edilmez.

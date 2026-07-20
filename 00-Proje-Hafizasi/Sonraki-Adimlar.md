---
type: project-memory
status: planned
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-20
tags:
  - proje
  - sonraki-adim
  - mvp
  - banka
---

# Sonraki Adımlar

## Geçiş Önceliği

Mevcut 16 iterasyonun, Iterasyon 17A–17E audit, Iterasyon 18A–18C veri koruma, Iterasyon 19A–19C maker-checker ve Iterasyon 20A–20C LDAP/oturum güvenliği dikeylerinin çekirdeği korunur. Banka kararları tamamlanmadan yeni HTTP yüzeyi açılmaz.

1. İterasyon 19D — Kural onay süre aşımı; `OPEN-BNK-017` nedeniyle engelli.
2. İterasyon 21A — Yetki güven sınırına bağlı dashboard trend domain sorgusu; `TechnicallyVerified`.
3. İterasyon 21B — HTTP okuma yüzeyi; geçiş kapısı ve `OPEN-BNK-020` tamamlanana kadar engelli.
4. İterasyon 22 — 22A–22I bildirim ve denetlenebilir issue yaşam döngüsü `TechnicallyVerified`.
5. İterasyon 23 — ServiceNow veri-minimizasyonlu adaptör; 23A–23D `TechnicallyVerified`.
6. İterasyon 24 — 24A audit inceleme ve 24B maskeli rapor önizleme `TechnicallyVerified`; hassas dışa aktarma `OPEN-BNK-014` nedeniyle engelli.
7. İterasyon 25 — Saklama, imha, legal hold ve arşivleme.
8. İterasyon 26 — 26A kayıt/karar ve 26B yetki filtreli timeline inceleme `TechnicallyVerified`; gerçek SIEM/SOC `OPEN-BNK-010` nedeniyle engelli.
9. İterasyon 27 — Ortam ayrılığı, yedekleme, geri yükleme ve DR kanıtları.
10. İterasyon 28 — 28A secret, 28B doğrudan bağımlılık SBOM'u ve 28C SAST sürüm kapısı `TechnicallyVerified`; gerçek scanner, transitive/zafiyet ve sızma testi hazırlığı açık.
11. İterasyon 29 — Banka kabul ve uyum kanıt paketi.

## Geçiş Backlogu

| Sıra | Ürün artımı | Gereksinim / kontrol bağlantıları | Çıkış kriteri | Durum |
| --- | --- | --- | --- | --- |
| 17 | Merkezi audit bütünlüğü | `BR-007`, `FR-077`–`FR-079`, `BFR-AUD-001`–`BFR-AUD-004` | Ortak olay zarfı, redaksiyon, correlation ve bütünlük doğrulaması | 17A–17E `TechnicallyVerified`; üretim operasyonlaştırması açık |
| 18 | Veri sınıflandırma ve maskeleme | `RULE-009`, `RULE-010`, `NFR-PRV-*`, `BFR-DATA-001`–`BFR-DATA-004` | Onaylı sınıf sözlüğü ve deny-by-default görüntüleme/örnek politikası | 18A–18C `TechnicallyVerified`; banka eşlemesi/onayları açık |
| 19 | Maker-checker | `RULE-001`, `RULE-005`, `RULE-007`, `BFR-SOD-001`–`BFR-SOD-004` | Hazırlayan kendi kritik değişikliğini aktive edemez | 19A kritik kural, 19B scoring ve 19C geri çekme `TechnicallyVerified`; süre aşımı `OPEN-BNK-017` ile engelli |
| 20 | LDAP/RBAC adaptörü | `FR-001`–`FR-006`, `UC-001`, `BFR-IAM-001`–`BFR-IAM-006` | LDAP grubu güvenilir role/scope'a dönüşür; giriş ve oturum başarısızlığı fail-closed | 20A adaptör/eşleme, 20B giriş sınırı ve 20C session `TechnicallyVerified`; üretim kararları açık |
| 21 | Dashboard trend ve HTTP okuma | `FR-054`–`FR-057`, `UC-010`, `NFR-PERF-001`, `NFR-PERF-002` | Son 30 gün trendi boş dönemleri sıfırlaştırmadan ve güvenilir scope ile döner | 21A `TechnicallyVerified`; 21B HTTP geçiş kapısına bağlı |
| 22 | Bildirim ve issue | `FR-059`, `FR-060`, `FR-064`–`FR-070`, `BFR-DATA-003` | Hassas veri içermeyen sistem içi bildirim ve denetlenebilir issue state machine | 22A–22I `TechnicallyVerified`; gerçek adaptörler ve operasyon politikaları açık |
| 23 | ServiceNow adaptörü | `FR-070`, `FR-087`, `BFR-EXT-001`–`BFR-EXT-003` | Alan whitelist'i, idempotency ve ham veri çıkışının engellenmesi | 23A–23D `TechnicallyVerified`; gerçek ağ/dağıtık state ve banka kararları açık |
| 24 | Rapor/audit erişimi | `FR-072`, `FR-075`, `FR-077`–`FR-079`, `BFR-EXP-001`–`BFR-EXP-003` | Yetki, gerekçe, maskeleme ve auditli dışa aktarma | 24A audit inceleme ve 24B rapor önizleme `TechnicallyVerified`; dosya dışa aktarma banka kararına bağlı |
| 25 | Saklama/imha/legal hold | `RULE-014`, `BFR-LCM-001`–`BFR-LCM-004` | Kayıt türü bazlı politika; imha ve geri çağırma kanıtı | Banka hukuk/uyum kararı |
| 26 | SIEM ve ihlal kanıtı | `NFR-OBS-*`, `BFR-IR-001`–`BFR-IR-004` | Güvenlik olayları ve ihlal zaman çizelgesi; otomatik Kurul bildirimi yok | 26A–26B `TechnicallyVerified`; gerçek SIEM/SOC `OPEN-BNK-010` ile engelli |
| 27 | DR ve ortam ayrılığı | `NFR-DR-*`, `BFR-OPS-001`–`BFR-OPS-004` | Banka onaylı RTO/RPO; restore testi ve ortam ayrımı kanıtı | Altyapı kararı |
| 28 | Güvenli SDLC ve pentest hazırlığı | `NFR-SEC-*`, `BFR-SDLC-001`–`BFR-SDLC-005` | SAST, secret/dependency taraması, SBOM ve pentest kapsamı | 28A secret, 28B doğrudan bağımlılık SBOM'u ve 28C SAST kapısı `TechnicallyVerified`; kalan dilimler açık |
| 29 | Banka kabul paketi | Tüm `BFR-*` ve `CTRL-*` | Teknik kanıtlar tamam; banka onayları ayrı durumda | Önceki geçişler |

## Mevcut MVP Backlogundan Korunan İşler

| Ürün artımı | Yeni sıradaki yeri | Not |
| --- | --- | --- |
| Kalan cron desteği | Geçiş kapısından sonra | Parser/gramer kararı hâlâ açık |
| Dashboard trend ve operasyon listeleri | İterasyon 21 | Güvenilir yetki bağlamından sonra |
| Bildirim ve issue yaşam döngüsü | İterasyon 22 | Veri minimizasyonu ve merkezi auditten sonra |
| Raporlama ve audit inceleme | İterasyon 24 | Dışa aktarma kontrolüyle birlikte |

## Önerilen Sonraki İterasyon

**İterasyon 28D — Yerel bağımlılık zafiyet bulgu zarfı ve sürüm kapısı sözleşmesi.**

`BFR-SDLC-001/002/003` ve `NFR-SEC-012` üzerinden 28B proje/SBOM sürümünü ürün bağımsız, veri-minimum zafiyet bulgusuna bağla. Eksik taramayı temiz kabul etme ve kritik zafiyette üretim adayı kanıtını fail-closed reddet. Gerçek zafiyet veritabanı/ağ tarayıcısı, transitive lock, istisna/risk kabul onayı ve CI/CD entegrasyonunu bu dilime alma.

## Başlangıç İçin Okunacak Notlar

- [[00-Proje-Hafizasi/Bankacilik-Gecis-Durumu|Bankacılık Geçiş Durumu]]
- [[09-Iterasyonlar/Iterasyon-19-Maker-Checker|İterasyon 19]]
- [[01-SRS/17-Bankacilik-Uyum/17.02-Bankacilik-Kontrol-Gereksinimleri|Bankacılık Kontrol Gereksinimleri]]
- [[02-Mimari/Guvenlik/Maker-Checker|Maker-Checker Mimarisi]]
- [[09-Iterasyonlar/Iterasyon-20-LDAP-RBAC-Entegrasyonu|İterasyon 20]]
- [[03-Backend/01-Kimlik-ve-Yetki/AGENTS|Kimlik ve Yetki Ajanı]]

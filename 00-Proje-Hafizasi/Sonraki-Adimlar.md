---
type: project-memory
status: planned
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-21
tags:
  - proje
  - sonraki-adim
  - mvp
  - banka
---

# Sonraki Adımlar

## Geçiş Önceliği

Mevcut 16 iterasyonun, Iterasyon 17A–17E audit, Iterasyon 18A–18C veri koruma, Iterasyon 19A–19H maker-checker, Iterasyon 20A–20C LDAP/oturum güvenliği ve Iterasyon 25A–25D saklama/legal hold/imha/arşiv yetkilendirme dikeylerinin çekirdeği korunur. Banka kararları tamamlanmadan yeni HTTP yüzeyi açılmaz.

Bakım İterasyonu 29C.1 ile tam mypy baseline'ı sıfır hataya indirilmiştir;
sonraki değişiklikler bu baseline'ı korumalıdır.

1. İterasyon 19G — Bağlantı yapılandırması revizyonu ve bekleyen aktivasyon onayını geçersizleştirme; `TechnicallyVerified`.
2. İterasyon 19H — Kontrollü kaynak pasifleştirme ve yeni iş kabulünü engelleme; `TechnicallyVerified`.
3. İterasyon 21A — Yetki güven sınırına bağlı dashboard trend domain sorgusu; `TechnicallyVerified`.
4. İterasyon 21B — HTTP okuma yüzeyi; geçiş kapısı ve `OPEN-BNK-020` tamamlanana kadar engelli.
5. İterasyon 22 — 22A–22I bildirim ve denetlenebilir issue yaşam döngüsü `TechnicallyVerified`.
6. İterasyon 23 — ServiceNow veri-minimizasyonlu adaptör; 23A–23D `TechnicallyVerified`.
7. İterasyon 24 — 24A audit inceleme ve 24B maskeli rapor önizleme `TechnicallyVerified`; hassas dışa aktarma `OPEN-BNK-014` nedeniyle engelli.
8. İterasyon 25 — 25A saklama dry-run, 25B legal hold, 25C imha kanıtı ve 25D arşiv geri çağırma talep/kararı `TechnicallyVerified`; gerçek fiziksel/arşiv adaptörleri açık.
9. İterasyon 26 — 26A kayıt/karar ve 26B yetki filtreli timeline inceleme `TechnicallyVerified`; gerçek SIEM/SOC `OPEN-BNK-010` nedeniyle engelli.
10. İterasyon 27 — Ortam ayrılığı, yedekleme, geri yükleme ve DR kanıtları.
11. İterasyon 28 — 28A secret, 28B doğrudan bağımlılık SBOM'u, 28C SAST, 28D doğrudan bağımlılık zafiyet sürüm kapısı ve 28E sızma testi bulgu takibi `TechnicallyVerified`; gerçek scanner, transitive çözüm ve gerçek pentest açık.
12. İterasyon 29 — 29A manifest, 29B drift kapısı ve 29C birleşik yerel preflight `TechnicallyVerified`; 29D kurumsal CI/CD/imzalı kanıt yayını engelli.

## Geçiş Backlogu

| Sıra | Ürün artımı | Gereksinim / kontrol bağlantıları | Çıkış kriteri | Durum |
| --- | --- | --- | --- | --- |
| 17 | Merkezi audit bütünlüğü | `BR-007`, `FR-077`–`FR-079`, `BFR-AUD-001`–`BFR-AUD-004` | Ortak olay zarfı, redaksiyon, correlation ve bütünlük doğrulaması | 17A–17E `TechnicallyVerified`; üretim operasyonlaştırması açık |
| 18 | Veri sınıflandırma ve maskeleme | `RULE-009`, `RULE-010`, `NFR-PRV-*`, `BFR-DATA-001`–`BFR-DATA-004` | Onaylı sınıf sözlüğü ve deny-by-default görüntüleme/örnek politikası | 18A–18C `TechnicallyVerified`; banka eşlemesi/onayları açık |
| 19 | Maker-checker | `RULE-001`, `RULE-005`, `RULE-007`, `BFR-SOD-001`–`BFR-SOD-004` | Hazırlayan kendi kritik değişikliğini aktive edemez | 19A–19H `TechnicallyVerified`; banka rol eşlemesi, gerçek takvim/worker, diğer kritik işlem sınıfları ve çalışan iş politikası açık |
| 20 | LDAP/RBAC adaptörü | `FR-001`–`FR-006`, `UC-001`, `BFR-IAM-001`–`BFR-IAM-006` | LDAP grubu güvenilir role/scope'a dönüşür; giriş ve oturum başarısızlığı fail-closed | 20A adaptör/eşleme, 20B giriş sınırı ve 20C session `TechnicallyVerified`; üretim kararları açık |
| 21 | Dashboard trend ve HTTP okuma | `FR-054`–`FR-057`, `UC-010`, `NFR-PERF-001`, `NFR-PERF-002` | Son 30 gün trendi boş dönemleri sıfırlaştırmadan ve güvenilir scope ile döner | 21A `TechnicallyVerified`; 21B HTTP geçiş kapısına bağlı |
| 22 | Bildirim ve issue | `FR-059`, `FR-060`, `FR-064`–`FR-070`, `BFR-DATA-003` | Hassas veri içermeyen sistem içi bildirim ve denetlenebilir issue state machine | 22A–22I `TechnicallyVerified`; gerçek adaptörler ve operasyon politikaları açık |
| 23 | ServiceNow adaptörü | `FR-070`, `FR-087`, `BFR-EXT-001`–`BFR-EXT-003` | Alan whitelist'i, idempotency ve ham veri çıkışının engellenmesi | 23A–23D `TechnicallyVerified`; gerçek ağ/dağıtık state ve banka kararları açık |
| 24 | Rapor/audit erişimi | `FR-072`, `FR-075`, `FR-077`–`FR-079`, `BFR-EXP-001`–`BFR-EXP-003` | Yetki, gerekçe, maskeleme ve auditli dışa aktarma | 24A audit inceleme ve 24B rapor önizleme `TechnicallyVerified`; dosya dışa aktarma banka kararına bağlı |
| 25 | Saklama/imha/legal hold | `RULE-014`, `BFR-LCM-001`–`BFR-LCM-004` | Kayıt türü bazlı politika; imha ve geri çağırma kanıtı | 25A–25D sözleşmeleri `TechnicallyVerified`; gerçek fiziksel/arşiv adaptörleri ve banka onayı açık |
| 26 | SIEM ve ihlal kanıtı | `NFR-OBS-*`, `BFR-IR-001`–`BFR-IR-004` | Güvenlik olayları ve ihlal zaman çizelgesi; otomatik Kurul bildirimi yok | 26A–26B `TechnicallyVerified`; gerçek SIEM/SOC `OPEN-BNK-010` ile engelli |
| 27 | DR ve ortam ayrılığı | `NFR-DR-*`, `BFR-OPS-001`–`BFR-OPS-004` | Banka onaylı RTO/RPO; restore testi ve ortam ayrımı kanıtı | Altyapı kararı |
| 28 | Güvenli SDLC ve pentest hazırlığı | `NFR-SEC-*`, `BFR-SDLC-001`–`BFR-SDLC-005` | SAST, secret/dependency taraması, SBOM ve pentest kapsamı | 28A–28E yerel teknik sözleşmeleri `TechnicallyVerified`; gerçek ürün, CI/CD ve banka pentest kararları açık |
| 29 | Banka kabul paketi | Tüm `BFR-*` ve `CTRL-*` | Teknik kanıtlar ve eksikler görünür; banka onayları ayrı durumda | 29A–29C `TechnicallyVerified`; 29D `OPEN-BNK-012` ve banka kararlarıyla engelli |

## Mevcut MVP Backlogundan Korunan İşler

| Ürün artımı | Yeni sıradaki yeri | Not |
| --- | --- | --- |
| Kalan cron desteği | Geçiş kapısından sonra | Parser/gramer kararı hâlâ açık |
| Dashboard trend ve operasyon listeleri | İterasyon 21 | Güvenilir yetki bağlamından sonra |
| Bildirim ve issue yaşam döngüsü | İterasyon 22 | Veri minimizasyonu ve merkezi auditten sonra |
| Raporlama ve audit inceleme | İterasyon 24 | Dışa aktarma kontrolüyle birlikte |

## Frontend Tasarım Backlogu

Bu kimlikler teslimat backlog kimlikleridir; yeni SRS gereksinimi değildir. Tüm
uygulama maddeleri geçiş kapısı ve ilgili güvenli API sözleşmesine bağlıdır.

| ID | Ürün artımı | Öncelik | Bağımlılık | Durum |
| --- | --- | --- | --- | --- |
| FE-DS-001 | Kurumsal design token sistemi | Must | Frontend stack ve dependency onayı | Planlı / engelli |
| FE-DS-002 | Açık ve koyu tema tanımları | Should | FE-DS-001, koyu tema kapsam kararı | Planlı / engelli |
| FE-DS-003 | Ortak KPI kartı | Must | FE-DS-001 | Planlı / engelli |
| FE-DS-004 | Ortak status badge ve status mapper | Must | FE-DS-001 | Planlı / engelli |
| FE-DS-005 | Ortak alarm bileşeni | Must | FE-DS-004 | Planlı / engelli |
| FE-DS-006 | Ortak chart wrapper ve formatter | Must | FE-DS-001, chart kütüphanesi onayı | Planlı / engelli |
| FE-DS-007 | Ortak data table standardı | Must | FE-DS-001, API sayfalama sözleşmesi | Planlı / engelli |
| FE-DS-008 | Kurumsal dashboard referans ekranı | Must | 21B, FE-DS-003–007 | Planlı / engelli |
| FE-DS-009 | Storybook story altyapısı | Must | Toolchain/dependency onayı, FE-DS-001 | Planlı / engelli |
| FE-DS-010 | Playwright görsel regression altyapısı | Must | Toolchain/dependency onayı, çalışan frontend | Planlı / engelli |
| FE-DS-011 | Grafik erişilebilirlik kontrolleri | Must | FE-DS-006, FE-DS-010 | Planlı / engelli |
| FE-DS-012 | Teknik hata ve kalite ihlali görsel ayrım testleri | Must | FE-DS-004, FE-DS-009/010 | Planlı / engelli |
| FE-DS-013 | Marka rengi token kullanım lint/review kapısı | Should | FE-DS-001, lint yaklaşımı kararı | Planlı / engelli |

## Önerilen Sonraki İterasyon

Sonraki teknik aday **İterasyon 27A — Fail-closed ortam kimliği ve üretim dışı
veri/secret kullanım sınırı** dilimidir. Kapsam sürümlü ortam sınıfı, yalnız güvenilir
konfigürasyon kaynağı, üretim dışı ortamda gerçek banka verisi/üretim secret
referansının reddi ve veri-minimum başlangıç kanıtıyla sınırlandırılmalıdır. Gerçek
deployment platformu ve secret manager `OPEN-BNK-012`, fiziksel retention
adaptörleri `OPEN-BNK-008`, 21B/frontend `OPEN-BNK-020`, hassas dışa aktarma
`OPEN-BNK-014` ve gerçek SIEM/SOC `OPEN-BNK-010` kararlarını beklemektedir.

## Başlangıç İçin Okunacak Notlar

- [Bankacılık Geçiş Durumu](Bankacilik-Gecis-Durumu.md)
- [İterasyon 19](../09-Iterasyonlar/Iterasyon-19-Maker-Checker.md)
- [Bankacılık Kontrol Gereksinimleri](../01-SRS/17-Bankacilik-Uyum/17.02-Bankacilik-Kontrol-Gereksinimleri.md)
- [Maker-Checker Mimarisi](../02-Mimari/Guvenlik/Maker-Checker.md)
- [İterasyon 20](../09-Iterasyonlar/Iterasyon-20-LDAP-RBAC-Entegrasyonu.md)
- [Kimlik ve Yetki Ajanı](../03-Backend/01-Kimlik-ve-Yetki/AGENTS.md)

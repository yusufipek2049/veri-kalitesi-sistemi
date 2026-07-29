---
type: decision-index
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-29
---

# Alınan Kararlar

Bu dosya karar metinlerini tekrar etmez; bağlayıcı kararın kanonik kaynağına yönlendirir. Açık veya kurumsal inceleme gerektiren kayıtlar yalnız [Açık Konular](Acik-Konular.md) içinde tutulur.

## Değişmez Proje Sınırları

| Karar | Durum | Kanonik kaynak |
| --- | --- | --- |
| Sistem kurum içi veri merkezinde çalışır. | Kesin | [ADR-001](../02-Mimari/Mimari-Kararlar.md) |
| Kaynak sistem erişimleri salt okunurdur; üretim kaynak verisi değiştirilmez. | Kesin | [ADR-002](../02-Mimari/Mimari-Kararlar.md) |
| Kimlik kurumsal IdP/SSO ve LDAP arka ucu üzerinden; rol/scope güvenilir bağlamdan çözülür. | Kesin yön | [ADR-007](../02-Mimari/Mimari-Kararlar.md) |
| Secret açık metin saklanmaz; yalnız kurumsal secret manager/PAM referansı tutulur. | Kesin yön | [ADR-006](../02-Mimari/Mimari-Kararlar.md) |
| Sistem içi bildirim zorunludur; ServiceNow çekirdek issue yaşam döngüsünden ayrılmış adaptördür. | Kesin | [ADR-008](../02-Mimari/Mimari-Kararlar.md) |
| Teknik hata, veri kalitesi ihlali, skor, yeterlilik ve kullanım kararı birbirine eritilmez. | Kesin | [ADR-015](../02-Mimari/Mimari-Kararlar.md) |
| Uygulama kalıcılığı PostgreSQL-only hedefindedir; üretimde SQLite fallback yoktur. | Kesin | [ADR-020](../02-Mimari/Mimari-Kararlar.md) |
| Değişken üretim değerleri sürümlü/onaylı politikadan çözülür; kayıt yoksa fail-closed davranılır. | Kesin | [ADR-018](../02-Mimari/Mimari-Kararlar.md) |

## Karar Kayıtları

| Kapsam | ID / konu | Kanonik kayıt |
| --- | --- | --- |
| Temel mimari ve `OPEN-001–OPEN-018` | kapasite, politika, saklama, dağıtım, maker-checker | [Temel ve Mimari Kararlar](Karar-Kayitlari/Temel-ve-Mimari-Kararlar.md) |
| Bankacılık teknik yönleri | `OPEN-BNK-003–007`, `010`, `012`, `014–017`, `020–021` | [Bankacılık Kararları](Karar-Kayitlari/Bankacilik-Kararlari.md) |
| Bankacılık uyum (modelleme varsayımı) | `OPEN-BNK-001`, `002`, `008`, `009`, `011`, `013`, `018`, `019` — `GOV-DECISION-2026-07-29` | [Açık Konular — karara bağlandı](Acik-Konular.md) |
| API ve kullanıcı arayüzü | `API-001–015`, `FE-DEC-*`, `PG-MIG-*`, `UI-WRITE-*` | [API, Frontend ve PostgreSQL Kararları](Karar-Kayitlari/API-Frontend-ve-PostgreSQL-Kararlari.md) |
| Skorlama ve ölçüm | `DQ-SCR-001–033` | [Skorlama ve İkinci Faz Kararları](Karar-Kayitlari/Skorlama-Sentetik-Veri-ve-Ikinci-Faz-Kararlari.md) |
| Kanıta dayalı ikinci faz | `OPEN-026–OPEN-036` | [Skorlama ve İkinci Faz Kararları](Karar-Kayitlari/Skorlama-Sentetik-Veri-ve-Ikinci-Faz-Kararlari.md) |
| Uygulama karar geçmişi | tarihli iterasyon kararları | [İterasyon Teknik Karar Geçmişi](Karar-Kayitlari/Iterasyon-Teknik-Karar-Gecmisi.md) |
| Mimari özet | `ADR-001–ADR-020` | [Mimari Kararlar](../02-Mimari/Mimari-Kararlar.md) |

## Durum Kuralı

- `KararAlındı` teknik yönün seçildiğini gösterir; runtime, banka onayı veya üretim uygunluğu değildir.
- `ApprovedByBank` yalnız açıkça belirtilen karar kapsamı için kullanılır.
- `Açık` ve `ComplianceReviewRequired` kayıtları bu dosyada yinelenmez.
- Eski seçenekler ve tarihsel test sayıları bağlayıcı karar değildir; [arşivde](../docs/archive/project-memory-2026-07-24/Alinan-Kararlar.md) korunur.

---
type: capability-status-matrix
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-29
source: USER-REQUEST-2026-07-29-CAPABILITY-REVIEW
---

# Ürün Yetenek Durum Matrisi

Bu matris, 29 Temmuz 2026 tarihli kullanıcı özellik listesini kanonik
gereksinimler ve depo içindeki gerçek runtime yüzeyiyle karşılaştırır. Bir
özelliğin SRS'de bulunması uygulanmış olduğu anlamına gelmez; bir domain modeli
veya sentetik adaptörün bulunması da üretim uygunluğu kanıtlamaz.

## Durum Anlamları

| Durum | Anlam |
| --- | --- |
| `Var` | Hedef kapsamın esas davranışı kod ve test yüzeyinde vardır; kurumsal üretim bağımlılıkları ayrıca değerlendirilebilir. |
| `Kısmi` | Davranışın bir bölümü çalışır; listelenen boşluklar genel runtime kapsamında tamamlanmamıştır. |
| `Hedef` | Gereksinim veya mimari karar vardır; genel runtime uygulaması yoktur. |
| `ExternalDependency` | Teknik yön/prototip olabilir; gerçek kurumsal ürün, erişim veya kurum onayı olmadan üretim doğrulaması yapılamaz. |

## Özellik Karşılaştırması

| No | Yetenek | Gereksinim/karar karşılığı | Runtime durumu | Var olanlar | Eksik veya sınır |
| --- | --- | --- | --- | --- | --- |
| 1 | Otomatik veri profilleme | [FR-015–FR-022](../01-SRS/04-Fonksiyonel-Gereksinimler/04.03-Metadata-ve-Profilleme.md) | `Kısmi` | Metadata keşfi; kayıt/örneklem sayısı; null ve distinct sayı/oranı; sayısal min/max/ortalama; seçili anahtarda duplicate; full/sample/partition/aggregate yöntem sözleşmesi; hassas alanda ham değer üretmeme. | Top-N, tip/format dağılımı, histogram, aykırı değer, kolon ilişkisi, profil drift'i ve şema değişikliği için tamamlanmış genel runtime/ekran yoktur. Üretim bağlayıcıları ayrıca açıktır. |
| 2 | Esnek kural tanımlama | [FR-023–FR-035](../01-SRS/04-Fonksiyonel-Gereksinimler/04.04-Kural-Yonetimi.md) | `Kısmi` | Hazır required/unique/range/regex/freshness/referential/cross-table şablonları; salt okunur özel SQL; kural API/UI; test ve maker-checker onayı; PostgreSQL kalıcılığı. | Zaman serisi kuralı, tüm mutabakat varyantları, genel satır-düzeyi tasarım ekranı ve shadow yürütme modu tamamlanmış değildir. |
| 3 | Kalite boyutları | [FR-026](../01-SRS/04-Fonksiyonel-Gereksinimler/04.04-Kural-Yonetimi.md), [DQ-SCR-003–012](../01-SRS/04-Fonksiyonel-Gereksinimler/04.06-Skorlama.md) | `Var` | Tamlık, doğruluk, tutarlılık, geçerlilik, benzersizlik, zamanlılık ve bütünlük domain sözleşmesinde bulunur. | Doğruluk yalnız otoriter referans/ground truth varsa iddia edilebilir; üretim ağırlık/eşikleri onaylı politika gerektirir. |
| 4 | Açıklanabilir kalite skoru | [FR-036–FR-053](../01-SRS/04-Fonksiyonel-Gereksinimler/04.06-Skorlama.md) | `Kısmi` | Kural/dataset/boyut/kaynak/kurum toplulaştırması; ağırlıklar, sayaçlar, kritik kural ve yeterlilik ayrımı; hesaplama detayı modelleri. | İş alanı hiyerarşisi, eksiksiz katkı grafiği, otomatik başlıca neden açıklaması ve tüm seviyelerde üretim kalıcılığı/görselleştirmesi tamamlanmamıştır. |
| 5 | Anomali ve değişim tespiti | [FR-021–FR-022](../01-SRS/04-Fonksiyonel-Gereksinimler/04.03-Metadata-ve-Profilleme.md), [FR-102](../01-SRS/04-Fonksiyonel-Gereksinimler/04.14-Kanita-Dayali-Karar-Destegi.md) | `Hedef` | Profil karşılaştırma, şema değişikliği ve teşhis/drift gereksinimleri tanımlıdır. | Hacim düşüşü, null drift'i, kategori kaybı, ortalama sıçraması ve gecikmiş yük için ortak detector runtime'ı yoktur. |
| 6 | Kök neden ve etki analizi | [FR-100–FR-102](../01-SRS/04-Fonksiyonel-Gereksinimler/04.14-Kanita-Dayali-Karar-Destegi.md), [OPEN-027–029](Karar-Kayitlari/Skorlama-Sentetik-Veri-ve-Ikinci-Faz-Kararlari.md) | `Hedef` | Issue çözümünde insan tarafından kök neden kaydı ve ikinci faz mimari sözleşmesi vardır. | Genel lineage grafı, otomatik ilk bozulma noktası, blast radius, benzer olay ve kaynaklı kök neden motoru yoktur. Girilen kök neden otomatik doğrulanmış neden sayılmaz. |
| 7 | İhlal inceleme ekranı | [FR-042–FR-045](../01-SRS/04-Fonksiyonel-Gereksinimler/04.09-Sorun-Yonetimi.md), [OPEN-034](Karar-Kayitlari/Skorlama-Sentetik-Veri-ve-Ikinci-Faz-Kararlari.md) | `Kısmi` | Issue liste/detay, durum geçmişi, atama, çözüm ve doğrulama; yetki kapsamı ve veri-minimum koruma. | Kural/query açıklaması, maskeli kötü örnek, beklenen/gerçekleşen, profil dağılımı, lineage, benzer geçmiş ve kaynaklı öneriyi tek inceleme yüzeyinde birleştiren ekran yoktur. |
| 8 | Uyarı ve issue yönetimi | [FR-040–FR-041](../01-SRS/04-Fonksiyonel-Gereksinimler/04.08-Bildirim.md), [FR-042–FR-045](../01-SRS/04-Fonksiyonel-Gereksinimler/04.09-Sorun-Yonetimi.md) | `Kısmi` | Sistem içi bildirim; veri-minimum dedup; sahip/yetki kapsamlı issue; öncelik, yaşam döngüsü, yeniden açma; idempotent fake ServiceNow prototipi. | Gerçek e-posta/mesajlaşma/ServiceNow ve Jira adaptörleri, kurumsal SLA takvimi ve onaylı escalation politikası yoktur. Gerçek entegrasyonlar `ExternalDependency`dir. |
| 9 | Veri sahipliği ve yönetişim | [FR-009–FR-010](../01-SRS/04-Fonksiyonel-Gereksinimler/04.02-Veri-Kaynagi-Yonetimi.md), [FR-028](../01-SRS/04-Fonksiyonel-Gereksinimler/04.04-Kural-Yonetimi.md), [OPEN-026/028/032](Karar-Kayitlari/Skorlama-Sentetik-Veri-ve-Ikinci-Faz-Kararlari.md) | `Kısmi` | Kaynak/dataset/kural sahibi, dataset kritiklik, alan sınıflandırması, işleme envanteri ve saklama politika referansları bulunur. | Teknik sahip, iş birimi, kalite hedefi, SLA, ilişkili rapor/sistem ve kurumsal katalog eşlemesini tek sürümlü varlıkta yöneten genel runtime yoktur. Gerçek katalog `ExternalDependency`dir. |
| 10 | Teknik hata ile kalite ihlalinin ayrılması | [ADR-015](../02-Mimari/Mimari-Kararlar.md), [DQ-SCR kararları](../01-SRS/04-Fonksiyonel-Gereksinimler/04.06-Skorlama.md) | `Var` | Teknik çalışma durumu, kalite sonucu, skor, ölçüm yeterliliği ve kullanım kararı ayrı modeller/akışlar olarak tutulur; teknik hata sıfır kalite skoru değildir. | Üretim gözlemlenebilirlik ürününün kurulması ayrı bağımlılıktır; kavramsal ayrım kapanmıştır. |
| 11 | Geçmiş ve karşılaştırma | [FR-020–FR-021](../01-SRS/04-Fonksiyonel-Gereksinimler/04.03-Metadata-ve-Profilleme.md), [FR-039](../01-SRS/04-Fonksiyonel-Gereksinimler/04.07-Dashboard.md), [FR-045](../01-SRS/04-Fonksiyonel-Gereksinimler/04.09-Sorun-Yonetimi.md) | `Kısmi` | Profil/sonuç/kural sürümü, dashboard trendi, issue geçmişi, tekrar ve yaşam döngüsü olayları için temel kayıtlar vardır. | Genel dönem karşılaştırma, kural değişikliği etkisi, tekrarlama analitiği, ortalama çözüm süresi ve SLA trendi tek analitik yüzeyde tamamlanmamıştır. |
| 12 | Güvenlik ve denetim | [Güvenlik](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md), [Audit](../01-SRS/04-Fonksiyonel-Gereksinimler/04.11-Audit.md) | `Kısmi` + `ExternalDependency` | RBAC/scope sınırı, salt okunur kaynak, secret referansı, veri-minimum audit, maker-checker; sentetik Keycloak, yerel secret manager ve fake SIEM prototipi. | Gerçek LDAP/IdP/MFA/session, PAM, KMS/HSM, SIEM/WORM ve banka kontrol kanıtları yoktur; prototip bunların yerini tutmaz. |
| 13 | Büyük veri/performans stratejileri | [Performans](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.01-Performans.md), [FR-033/OPEN-033](Karar-Kayitlari/Skorlama-Sentetik-Veri-ve-Ikinci-Faz-Kararlari.md) | `Kısmi` | Full/sample/partition/aggregate profil yöntemleri; zamanlama, timeout/deadline, retry, lease, concurrency ve kalıcı job yaşam döngüsü. | Kaynak-özel incremental watermark, partition checkpoint/resume, sorgu maliyet ön kontrolü ve onaylı kota politikalarının uçtan uca yürütülmesi tamamlanmamıştır. HA PostgreSQL/broker üretim bağımlılığıdır. |
| 14 | Kural yaşam döngüsü | [FR-029–FR-035](../01-SRS/04-Fonksiyonel-Gereksinimler/04.04-Kural-Yonetimi.md) | `Kısmi` | `DRAFT`, `REVIEW_REQUIRED`, `ACTIVE`, `PASSIVE`, `ARCHIVED`; değişmez kural sürümü; maker-checker talep/onay/red/geri çekme/süre aşımı; aktör ve gerekçe kayıtları. | Shadow/canary yürütme statüden ayrı bir mod olarak runtime'da yoktur; kritik pasifleştirme için kurumun süre/risk kabul politikası gereklidir. |
| 15 | Yönetici ve mühendis dashboardları | [FR-036–FR-039](../01-SRS/04-Fonksiyonel-Gereksinimler/04.07-Dashboard.md), [FR-097–FR-111](../01-SRS/04-Fonksiyonel-Gereksinimler/04.14-Kanita-Dayali-Karar-Destegi.md) | `Kısmi` | Yönetici özet/trend kartları, güvenli özet API'si ve operasyonel alan ekranları vardır. | İş birimi kırılımı, bozulma sıralaması, SLA analitiği ile mühendis için dağılım/lineage/otomatik teşhis/öneri yüzeyleri tamamlanmamıştır. |

## Net Sonuç

- `Var`: 3 ve 10 numaralı yeteneklerin çekirdek sözleşmesi.
- `Kısmi`: 1, 2, 4, 7, 8, 9, 11, 12, 13, 14 ve 15.
- `Hedef`: 5 ve 6; bunların bazı alt parçaları SRS'de tanımlı olsa da genel
  runtime değildir.
- Üretim IdP/PAM/HA/SIEM/WORM/ServiceNow/katalog ve banka kanıtları gerçek erişim
  olmadan kapanmaz. Bunların sentetik karşılıkları yalnız prototip doğrulamasıdır.

Eksik yetenekler için seçilen teknik ve ürün yönü
[Ürün Yetenekleri Prototip Kararları](Karar-Kayitlari/Urun-Yetenekleri-Prototip-Kararlari.md)
içinde kayıtlıdır. Bu matris backlog önceliği veya tamamlanma iddiası değildir.

---
type: canonical-architecture
status: target-design
project: Veri Kalitesi İzleme ve Skorlama Sistemi
created_at: 2026-07-22
tags:
  - architecture
  - evidence
  - decision-support
  - governance
---

# Kanıta Dayalı, Politika Farkındalıklı Veri Kalitesi Karar Sistemi

## Amaç ve Durum

Bu belge `FR-097–FR-111`, `UC-018–UC-021`, `RULE-018–RULE-023` ve
`AC/TS-057–071` için kanonik hedef tasarımdır. Sistem yalnız genel skor gösteren
bir dashboard değildir; verinin belirli kullanım amacı için uygunluğunu,
ölçümün ve kontrollerin yeterliliğini, iş/risk etkisini ve önerilen iyileştirme
kararını kanıtlarıyla birlikte sunan bir karar destek sistemidir.

Bu hedef ikinci faz kapsamıdır. Belgenin varlığı runtime uygulaması, üretim
hazırlığı, banka onayı veya otomatik düzeltme yetkisi anlamına gelmez. Mevcut
MVP ve salt okunur kaynak erişimi korunur.

## Bağlayıcı İlkeler

1. Formülü ve politika kaynağı gösterilemeyen skor karar girdisi olamaz.
2. Dayanak kanıtı bulunmayan öneri yayımlanamaz.
3. Yetki, onay ve audit izi bulunmayan işlem tamamlanmış sayılmaz.
4. Kaynakları gösterilemeyen teşhis doğrulanmış neden olarak sunulamaz.
5. Girdi snapshot'ı, sürümler ve yürütme manifesti eksik sonuç yeniden
   üretilebilir kabul edilmez.
6. Korelasyon, doğrulanmış nedensellik gibi gösterilemez.
7. Hiçbir LLM veya başka öneri mekanizması tek başına üretim verisini
   değiştiremez.
8. Kaynak sistemlerde değişiklik yapmak bu sistemin görevi değildir;
   `NeverModifyProductionData` temel ve değiştirilemez politika seviyesidir.

## Karar Modeli

### Kullanım Amacı Bazlı Uygunluk

Aynı `QualityScore`, farklı kullanım amaçlarında farklı `UsageDecision`
üretebilir. `UseCaseScoreProfile`; kullanım amacı, dataset ve sürüm bağlamında
kalite boyutlarını, ağırlıkları, kritik alanları, minimum eşikleri, bloke edici
kuralları ve gerekli kanıt/yeterlilik kapılarını referanslar. Profil değerleri
aktif, sürümlü ve gerekli onayı taşıyan politikadan çözülür; profil veya politika
yoksa olumlu kullanım kararı üretilmez.

Profil kataloğu hibrit yönetişimlidir: şema, kurumsal kullanım sözlüğü ve yaşam
döngüsü merkezi; dataset profili Data Owner sahipliğindedir. Data Governance
sözlüğü, Risk Yönetimi düzenleyici/risk kullanımını yönetir. Örnek kullanım
amaçları etkin profil değildir; değerler onaylı profil kaydıyla açılır.

### Ayrı Skor ve Güven Kavramları

| Kavram | Anlam |
| --- | --- |
| `QualityScore` | Kural sonuçlarından üretilen ham/nihai veri kalitesi ölçümü |
| `MeasurementConfidence` | Kapsam, örnekleme, teknik başarı ve güncellik güveni |
| `DiagnosisConfidence` | Teşhisin kanıtlarla desteklenme düzeyi |
| `RecommendationConfidence` | Önerinin dayanak ve doğrulama gücü |
| `EvidenceStrength` | Bağlı kanıtların kaynak, bütünlük, güncellik ve doğrulanma durumu |

Bu kavramlar birbirine dönüştürülmez ve tek yüzde altında birleştirilmez.
Değerlerin formülü ve sınıflandırma eşikleri aktif sürümlü politikadan çözülür.

### Etki Değerlendirmesi

`ImpactAssessment`; etkilenen kayıt, müşteri ve işlem sayısını; dataset, veri
ürünü, rapor ve model yayılımını; finansal, operasyonel, düzenleyici ve müşteri
etkisini; veri kritikliğini ve çözüm maliyetini kaynaklarıyla birlikte taşır.
Her değer `Observed`, `Calculated`, `Estimated` veya `Unknown` olarak
etiketlenir. Formül, girdiler, kaynak referansları, model/politika sürümü ve güven
düzeyi gösterilir. Gözlenen değer hesaplanan ve tahmini değerden önce gelir.
Parasal değer yalnız otoriter Finans/Risk referansı veya onaylı formülle
üretilir; desteklenmeyen bileşenler `Unknown` kalır ve kanıtsız tek toplam
etki sayısında birleştirilmez.

## Kanıt Zinciri ve Yeniden Üretilebilirlik

### Çalıştırma Manifesti

Her karar verilebilir skor çalışması aşağıdaki kanonik manifest alanlarını
taşır:

- run, dataset ve dataset sürümü;
- partition veya snapshot referansı;
- toplam ve incelenen kayıt sayıları;
- örnekleme stratejisi, örneklem büyüklüğü ve seed;
- çalışan, başarısız ve atlanan kural sayıları ile kural sürümleri;
- skor modeli ve politika sürümleri;
- motor ve uygulama sürümü;
- başlangıç/bitiş zamanı;
- sorgu, ifade veya işlem hash'leri;
- güvenilir başlatan aktör ve correlation ID.

Manifest eksikse sonuç üretilebilir fakat `ReproducibilityStatus=Incomplete`
olur ve politika olumlu kullanım kararını engelleyebilir. Replay aynı snapshot
veya partition, kural/politika, parametre, örnekleme/seed ve motor sürümleriyle
yeni, değişmez bir sonuç oluşturur; orijinali güncellemez.

### Kanıt Türleri

| Kanıt | Zorunlu içerik | Veri koruma sınırı |
| --- | --- | --- |
| Metrik kanıtı | Girdiler, toplam/hatalı kayıt, oran, eşik, sapma, filtre/partition, süre ve kaynak | Ham kayıt içermez |
| Hesaplama kaynağı | SQL/kural/validasyon/dönüşüm türü, parametre özeti, hash ve şablon sürümü | Kaynak SQL ve gizli parametre yalnız ayrı izinle |
| Kayıt örneği referansı | Fingerprint, maskeli alan, beklenen koşul, kaynak tablo/kolon, ilk/son görülme, kural | Gerçek değer varsayılan kapalıdır |
| Lineage snapshot'ı | Tablo/kolon, dönüşüm, pipeline/job, veri sahibi, downstream varlıklar ve kod/deploy referansı | Yetkili scope ve sınıflandırma uygulanır |
| Değişiklik olayı | Deploy, pipeline, şema, referans veri, kural/politika veya kaynak kesintisi | Serbest secret/ham payload saklanmaz |

`EvidenceItem` tek kanıt metadata'sını, `EvidenceLink` kanıtın skor, teşhis,
öneri, değişiklik, remediation veya olaya çoktan çoğa ilişkisini taşır. Audit
log bir işlemin izidir; teknik kanıtın kendisi değildir.

## Lineage, Drift ve Kök Neden

Lineage ve sahiplik için kurumsal veri kataloğu sistem-of-record'dur. Sistem
OpenLineage uyumlu sürümlü olay sözleşmesiyle run/job/dataset ve kolon düzeyi
ilişkileri alır; iç kanıt modelinde W3C PROV `Entity`, `Activity` ve `Agent`
anlamlarına eşleyebilir. Rakip bir ana katalog oluşturmaz; değişmez snapshot,
digest, kaynak sürümü, güncellik ve kapsama durumunu saklar. Eksik veya eski
lineage `Unknown` olarak görünür ve etki kapsamı olduğundan dar gösterilmez.

Değişiklikler şu sınıflarda ayrılır:

- `DataDrift`: değer dağılımı veya veri davranışı değişimi,
- `RuleDrift`: kural kapsamı, ifadesi veya sürümü değişimi,
- `PolicyDrift`: eşik, ağırlık, kullanım veya onay politikası değişimi,
- `MeasurementDrift`: tarama, örnekleme, kapsam veya motor davranışı değişimi.

`Diagnosis`; bağlı kanıtları, karşı hipotezleri ve `VerifiedCause`,
`StrongHypothesis`, `WeakHypothesis` veya `TemporalCorrelationOnly` durumunu
taşır. Sadece zaman yakınlığı `VerifiedCause` üretemez.

## Değişiklik Simülasyonu

Simülasyon; kolon silme/yeniden adlandırma, veri tipi, zorunluluk, referans veri,
pipeline/dönüşüm, kural/ağırlık ve dataset kritiklik değişikliklerini değişmez
aday olarak değerlendirir. Çıktı en az etkilenen dataset/kolon/kural/rapor/model/
veri ürünlerini, beklenen skor değişimini, risk ve güveni, gerekli onayları,
rollback ihtiyacını ve doğrulama testlerini içerir.

Beklenen skor değişimi yalnız mevcut kanıt ve sürümlü simülasyon politikasıyla
hesaplanır; eksik lineage veya politika sonucu `Incomplete` yapar. Simülasyon
üretim nesnesini veya geçmiş skoru değiştirmez.

## Kanıtlı Öneri ve Remediation

Her `Recommendation`; öneri türü, üreten mekanizma, dayanak metrik/olaylar,
benzer geçmiş olaylar, lineage bulguları, karşı kanıt, güven, doğrulama durumu,
uygulama riski ve gerekli onayı taşır. İlk üretim sürümünde yalnız
`DeterministicRule`, `IncidentSimilarity` ve auditli `ExpertInput` etkindir.
`StatisticalModel` bağımsız doğrulama ve kalibrasyon sonrasında açılabilir.
`LLMAssisted` üretimde kapalıdır; ileride açılsa bile yalnız `SuggestOnly`
düzeyinde çalışır ve karar/onay/eylem kaynağı olamaz.

Politika seviyeleri:

| Seviye | İzin verilen davranış |
| --- | --- |
| `SuggestOnly` | Yalnız kanıtlı öneri oluşturur |
| `ApprovalRequired` | Uygulama öncesi ayrı onay gerekir |
| `AutoFixLowRisk` | Yalnız açıkça izinli düşük riskli teknik eylem |
| `AutoQuarantine` | Politika kapsamındaki akışı/çıktıyı izole eder |
| `AutoRerun` | Değişmez girdilerle idempotent yeniden çalıştırma başlatır |
| `NeverModifyProductionData` | Kaynak üretim verisine yazmayı her koşulda yasaklar |

Akış: teşhis → öneri → dry-run → etki analizi → yetki/politika → onay →
canary → yeniden doğrulama → tam uygulama veya rollback/kapanış. `SuggestOnly`
varsayılandır. `ApprovalRequired` yalnız sistemin sahip olduğu nesne ve iş
akışlarında; `AutoRerun` aynı değişmez girdide idempotent; `AutoQuarantine`
yalnız sistem çıktısının yayımını durduracak biçimde kullanılabilir.
`AutoFixLowRisk` ilk fazda üretim dışıyla sınırlıdır. Kritik audit/outbox
yazılamıyorsa eylem fail-closed sonuçlanır.

## Data Contract, Adaptif Tarama ve Kalite Borcu

`DataContract`; şema/zorunluluk/tip, kalite eşikleri, freshness/completeness/
uniqueness/availability, üretici-tüketici sahipleri, breaking change bildirimi,
istisna/onay ve ihlal davranışını sürümler. Kurumsal veri kataloğu
sistem-of-record'dur; bu sistem değişmez sözleşme sürümü ve değerlendirme
kanıtını saklar. Üretici taslak oluşturur, Data Owner onaylar, tüketici sahipleri
breaking change için bilgilendirilir. Etki simülasyonu ve onay olmadan breaking
change etkinleşmez; istisna kapsamlı, süreli, maker-checker onaylı ve auditlidir.

Adaptif tarama ilk fazda deterministik politika motorudur; makine öğrenmesiyle
strateji seçilmez. Kritik veya bloke edici kontrollerde mümkünse tam tarama,
sonra partition uygulanır. Örnekleme yalnız kullanım ve kaynak politikası izin
verip kapsama/güven koşulları sağlandığında seçilir. Her karar gerekçe, tahmini
maliyet, kapsam, güven ve seed taşır. Politika yoksa otomatik strateji değişmez
veya yeni çalışma fail-closed reddedilir.

`QualityDebtItem`; ilk tespit, yaş, etkilenen sistem, tekrar/istisna sayıları,
operasyonel maliyet, risk artışı, çözüm sahibi, hedef tarih ve durum taşır.
`QualityDebtScoreV1`, gerekli politikalarla normalize edilmiş yaş, tekrar,
istisna, etki ve kontrol açığı oranlarının eşit ağırlıklı ortalamasını `0–100`
aralığına taşır. Kanıt kapsaması ayrı gösterilir; gerekli bileşen veya politika
yoksa skor üretilmez ve bileşen `Unknown` kalır. Operasyonel maliyet ile finansal
etki bu skora uydurulmaz; ayrı kaynaklı değerlerdir.

## Gizlilik Korumalı İnceleme

Varsayılan görünüm toplulaştırılmış/maskeli alan, kayıt fingerprint'i ve güvenli
referans kullanır. Hassas değer için düz veya tuzsuz hash kullanılmaz;
deterministik token kurumun kriptografik/tokenizasyon servisi ve KMS/HSM anahtarı
ile üretilir. Gerçek kayıt görünümü istisnai, kapsamlı, gerekçeli, süreli ve
auditlidir; yüksek hassasiyette maker-checker gerekir. İndirme ve kopyalama
varsayılan kapalıdır. Katalog/DLP kesintisi daha düşük korumaya düşmez. Sentetik
örnek gerçek kaydın yerine tercih edilir ve kökeni açıkça gösterilir.

## Chaos ile Kontrol Yeterliliği

Chaos deneyi; null/duplicate artışı, format/encoding, referans bütünlüğü, tip/
şema, geç/eksik batch, dağılım kayması, uç değer, kolon kayması, yanlış referans
veri ve hassas veri sızıntısı sınıflarını izole sentetik veya yetkili test
ortamında enjekte edebilir. Üretim veya gerçek müşteri verisi varsayılan olarak
yasaktır.

Deney ilk fazda yalnız izole üretim dışı ortam ve sentetik veriyle yürütülür.
Sürümlü fault profili kaynak/dataset/partition/zaman/hacim sınırlarını taşır;
Data Owner ile Bilgi Güvenliği veya Operasyon onayı ve önceden doğrulanmış
rollback zorunludur. Kapsam/ortam kanıtı uyuşmazlığı, gerçek veri veya üretim
hedefi, audit/telemetri kaybı, rollback yokluğu, beklenmeyen downstream etkisi
ya da politika bütçesi aşımı deneyi derhal durdurur. Enjekte/tespit/kaçırılan
hata, false positive, tespit süresi ve kontrol kapsaması ayrı ölçülür.

## API, UI ve Yetki Sınırı

API; okuma işlemlerinde sayfalama ve hassas alan filtresi, yazma/uzun işlerde
idempotency, job durumu, correlation ID ve audit uygular. Değişmez sonuçlar
güncellenmez; yeni değerlendirme/manifest/kanıt kaydı oluşturulur.

Olay inceleme UI sekmeleri: Özet, Skor Kırılımı, Metrikler, Hatalı Kayıtlar,
Hesaplama, Lineage, Kök Neden, Öneriler, Çalıştırmalar, Değişiklikler, Zaman
Çizelgesi ve Kanıt ve Denetim. Her sonuç kural, run, lineage düğümü, olay veya
kanıta yetkili ve gezilebilir referans verir. Eksik kanıt ve güven düzeyi
gizlenmez.

İzinler en az skor, formül, sorgu, maskeli/gerçek kayıt, lineage, öneri üretme/
onaylama, remediation, otomasyon politikası, reproduction, chaos ve kanıt paketi
okuma/üretme/indirme işlemlerini ayrı kapsar. Rol kodları ve eşlemeler
`OPEN-BNK-002` kapsamında kalır. Öneren ile onaylayan ayrıdır; yüksek riskli
işlem maker-checker gerektirir.

## Gözlemlenebilirlik

Run başarı oranı; kural/sorgu süreleri; atlanan kural; kanıt üretim başarısı;
lineage/kanıt kaynak kapsaması; reproduction başarısı; false positive/negative;
öneri kabul/başarı ve rollback oranı; chaos detection coverage; MTTD,
MTTDiagnosis, MTTR ve tekrar oranı ölçülür. Log, metric ve trace aynı correlation
ve run kimliğiyle bağlanır. Eşikler aktif gözlemlenebilirlik politikasındadır.

## Veri Modeli Yeniden Kullanım Kararı

Yeni fiziksel tablo sayısını azaltmak için mevcut varlıklar genişletilir:

- `score_run`, `score_component` ve `metric_result`; mevcut `RuleExecution`,
  `QualityScore`, `RuleResult` ve `ScoreMeasurementSummary` ile karşılanır.
- `rule_execution`, `rule_version`, `policy_version` mevcut varlıklardır.
- `data_sample_reference` ve `record_fingerprint`, tek `EvidenceItem` türleri
  olarak modellenir.
- `recommendation_evidence`, ayrı tablo yerine `EvidenceLink` ilişkisidir.
- `confidence_assessment`, türü belirtilmiş ortak ve değişmez değerlendirmedir.
- `approval` mevcut maker-checker kayıtlarıyla ilişkilendirilir; genel ve
  sınırsız approval tablosu oluşturulmaz.
- `rollback`, `RemediationAction` olaylarından biridir.
- `reproduction_manifest`, `RunManifest` olarak `RuleExecution` ile bağlanır.

Ayrıntılı alanlar
[Kanıt ve Karar Desteği Varlıkları](../01-SRS/07-Veri-Modeli/Kanit-ve-Karar-Destegi-Varliklari.md)
belgesindedir.

## Kanıt Paketi ve Güvenli Varsayılanlar

Kanıt paketinin otoriter çıktısı RFC 8785 kanonik JSON manifestidir. Manifest ve
referanslı artefaktlar mevcut SHA-256 özetiyle doğrulanır; üretimde kurum onaylı
KMS/HSM ile imzalanıp değişmez/WORM uyumlu depoda tutulur. İnsan okunur özet
ikincildir. Paket ham hassas veriyi kopyalamaz. Dışa aktarma asenkron, DLP ve
gerektiğinde maker-checker kontrollü; şifreli, süreli ve politika gerektiriyorsa
watermark'lıdır. Saklama, legal hold ve imha kanıtı kayıt sınıfı politikasından
çözülür.

Ürün adı, sayısal üretim eşiği, fault büyüklüğü, SLA/SLO veya saklama süresi
uydurulmaz. Eksik politika olumlu kullanım, doğrulanmış teşhis, yayımlanmış öneri,
otomatik remediation, chaos çalışması veya başarılı kanıt paketi üretmez.

## Standart Dayanakları

- OpenLineage run/job/dataset ve kolon düzeyi lineage için birlikte çalışabilir
  olay sözleşmesi dayanağıdır: <https://openlineage.io/docs/spec/facets/>.
- W3C PROV-O kanıt kökenini `Entity`, `Activity` ve `Agent` ilişkileriyle
  eşlemek için semantik dayanak sağlar: <https://www.w3.org/TR/prov-o/>.
- NIST AI RMF insan gözetimi, rol ayrımı ve risk yönetimi sınırının dayanağıdır:
  <https://airc.nist.gov/airmf-resources/airmf/5-sec-core/>.
- RFC 8785 imzalanabilir manifest için deterministik JSON kanonikleştirme
  yöntemidir: <https://www.rfc-editor.org/rfc/rfc8785>.

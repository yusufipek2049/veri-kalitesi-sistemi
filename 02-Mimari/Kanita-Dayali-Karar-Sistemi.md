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

İlk kullanım amacı kataloğu, ağırlıklar, eşikler ve bloke edici kural setleri
`OPEN-026` kapsamındadır. Örnek kullanım amaçları gereksinim sözlüğünü açıklar;
kurumda etkin profil oldukları anlamına gelmez.

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
düzeyi gösterilir. Kaynaksız parasal değer üretilmez. Formüller ve veri
kaynakları `OPEN-027` kapsamındadır.

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

Lineage tablo ve kolon düzeyinde kaynak, dönüşüm, pipeline/job, dataset, rapor,
model ve veri ürünü ilişkilerini; mümkünse repository, dosya, commit ve deploy
referanslarını kapsar. Sistem lineage üreticisini uydurmaz; kaynak sistem ve
otorite `OPEN-028` kapsamında belirlenir. Eksik lineage `Unknown` olarak görünür
ve etki kapsamı olduğundan dar gösterilmez.

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
benzer geçmiş olaylar, lineage bulguları, güven, doğrulama durumu, uygulama riski
ve gerekli onayı taşır. Mekanizma türü `DeterministicRule`, `StatisticalModel`,
`IncidentSimilarity`, `ExpertInput`, `LLMAssisted` veya `Hybrid` olabilir.
Sağlayıcı, model ve kabul eşikleri `OPEN-029` kapsamında kalır.

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
canary → yeniden doğrulama → tam uygulama veya rollback/kapanış. İzinli otomasyon
eylemleri, ortamlar ve karar sahipleri `OPEN-030` sonuçlanmadan yalnız
`SuggestOnly` uygulanabilir.

## Data Contract, Adaptif Tarama ve Kalite Borcu

`DataContract`; şema/zorunluluk/tip, kalite eşikleri, freshness/completeness/
uniqueness/availability, üretici-tüketici sahipleri, breaking change bildirimi,
istisna/onay ve ihlal davranışını sürümler. Kurumsal sistem-of-record ve bildirim
kuralları `OPEN-032` kapsamındadır.

Adaptif tarama; dataset kritikliğini, hacmi, olay/kalite borcu ve hata geçmişini,
kullanım amacını, değişiklik geçmişini, maliyeti ve örnekleme güvenini girdi
olarak kullanabilir. Tam, partition, adaptif veya risk bazlı örnekleme kararı
gerekçesiyle kaydedilir. Eşik ve maliyet politikaları `OPEN-033` olmadan
otomatik strateji değişikliği yapılamaz.

`QualityDebtItem`; ilk tespit, yaş, etkilenen sistem, tekrar/istisna sayıları,
operasyonel maliyet, risk artışı, çözüm sahibi, hedef tarih ve durum taşır.
Borç formülü ve hedefleri `OPEN-035` kapsamındadır; kaynaksız maliyet üretilmez.

## Gizlilik Korumalı İnceleme

Varsayılan görünüm maskeli alan, kayıt fingerprint'i ve güvenli referans kullanır.
Deterministik tokenizasyon, gerçek kayıt görünümü veya geçici yetki yükseltme;
ayrı izin, gerekçe, süre, sınıflandırma, audit ve saklama politikasına bağlıdır.
İndirme ve kopyalama kısıtları kurumsal katalog/DLP kararından uygulanır.
Mekanizma ve süreler `OPEN-034` kapsamında belirlenir. Sentetik örnek gerçek
kaydın yerine tercih edilir; sentetik köken açıkça gösterilir.

## Chaos ile Kontrol Yeterliliği

Chaos deneyi; null/duplicate artışı, format/encoding, referans bütünlüğü, tip/
şema, geç/eksik batch, dağılım kayması, uç değer, kolon kayması, yanlış referans
veri ve hassas veri sızıntısı sınıflarını izole sentetik veya yetkili test
ortamında enjekte edebilir. Üretim veya gerçek müşteri verisi varsayılan olarak
yasaktır.

Deney; enjekte/tespit/kaçırılan hata, false positive, tespit süresi, kural,
boyut ve kritik alan kapsamasını ölçer. Yetki, ortam izolasyonu, geri alma ve
kanıt manifesti zorunludur. İzinli ortam ve hata sınırları `OPEN-031` sonucunu
bekler.

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

## Açık Kararlar ve Güvenli Varsayılanlar

`OPEN-026–OPEN-036` sonuçlanmadan ürün, sağlayıcı, eşik, katsayı, SLA/SLO,
saklama süresi veya otomasyon yetkisi varsayılmaz. Eksik politika olumlu kullanım,
doğrulanmış teşhis, yayımlanmış öneri, otomatik remediation veya chaos çalışması
üretmez. Yalnız salt okunur inceleme ve eksikliği açıkça gösteren sonuç
sunulabilir.

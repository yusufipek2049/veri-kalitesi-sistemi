---
type: srs-section
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "11"
created_at: 2026-07-16
tags:
  - srs
  - traceability
---

# Gereksinim İzlenebilirlik Matrisi

Bu matris, iş hedeflerini fonksiyonel gereksinim, kullanım senaryosu, iş kuralı, kabul kriteri ve test senaryosuyla ilişkilendirir. Fonksiyonel gereksinimler aralık halinde gösterilmiş olsa da FR-001–FR-111'in tamamı en az bir satırda kapsanmıştır.

| İş Gereksinimi ID | Fonksiyonel Gereksinim ID | Kullanım Senaryosu ID | İş Kuralı ID | Kabul Kriteri ID | Test Senaryosu ID | Öncelik |
| --- | --- | --- | --- | --- | --- | --- |
| BR-001 | FR-001–FR-006 | UC-001 | RULE-001, RULE-009 | AC-001–AC-003 | TS-001–TS-003 | Must |
| BR-001 | FR-007–FR-014 | UC-002, UC-003 | RULE-002, RULE-009 | AC-004–AC-006 | TS-004–TS-006 | Must |
| BR-001, BR-002 | FR-015–FR-022 | UC-004 | RULE-002, RULE-010, RULE-012 | AC-007, AC-008, AC-025 | TS-007, TS-008, TS-025 | Must |
| BR-002, BR-005 | FR-023–FR-030 | UC-005 | RULE-001, RULE-005, RULE-007 | AC-006, AC-025 | TS-006, TS-025 | Must |
| BR-002, BR-005 | FR-031–FR-035 | UC-006 | RULE-002, RULE-003, RULE-010 | AC-006, AC-009 | TS-006, TS-009 | Must/Should |
| BR-002, BR-003 | FR-036–FR-039 | UC-007, UC-008 | RULE-003, RULE-011, RULE-012 | AC-009, AC-024 | TS-009, TS-024 | Must |
| BR-003 | FR-040–FR-045 | UC-008 | RULE-003, RULE-011 | AC-010, AC-012, AC-024 | TS-010, TS-012, TS-024 | Must |
| BR-001, BR-005, BR-006 | FR-046–FR-053 | UC-009 | RULE-003–RULE-007 | AC-009–AC-014, AC-027–AC-047 | TS-009–TS-014, TS-027–TS-047 | Must |
| BR-001, BR-002, BR-006 | FR-054–FR-058 | UC-010 | RULE-004, RULE-009 | AC-011, AC-014 | TS-011, TS-014 | Must/Should |
| BR-003, BR-004 | FR-059–FR-063 | UC-011, UC-012 | RULE-006, RULE-011 | AC-010, AC-015, AC-016 | TS-010, TS-015, TS-016 | Must/Should |
| BR-003, BR-004, BR-008 | FR-064–FR-070 | UC-011, UC-013, UC-014 | RULE-006, RULE-013 | AC-015–AC-018 | TS-015–TS-018 | Must |
| BR-004, BR-008 | FR-071 | UC-013, UC-014 | RULE-011 | AC-019 | TS-019 | Should |
| BR-001, BR-006, BR-007, BR-008 | FR-072–FR-076 | UC-015 | RULE-008–RULE-010 | AC-020, AC-021, AC-023 | TS-020, TS-021, TS-023 | Must/Should |
| BR-007 | FR-077–FR-079 | UC-016 | RULE-007, RULE-009 | AC-022, AC-026 | TS-022, TS-026 | Must |
| BR-001, BR-003, BR-004 | FR-080–FR-084 | UC-002, UC-008, UC-013 | RULE-009, RULE-011 | AC-003, AC-019, AC-024 | TS-003, TS-019, TS-024 | Must |
| BR-004 | FR-085 | UC-012 | RULE-011 | AC-016 | TS-016 | Could |
| BR-001, BR-005 | FR-086 | UC-004 | RULE-007 | AC-025 | TS-025 | Could |
| BR-004, BR-008 | FR-087 | UC-013, UC-014 | RULE-003, RULE-011 | AC-019 | TS-019 | Should |
| BR-001, BR-002, BR-003, BR-007 | FR-088–FR-096 | UC-017 | RULE-003–RULE-007, RULE-009–RULE-012, RULE-014, RULE-016, RULE-017 | AC-048–AC-056 | TS-048–TS-056 | Must |
| BR-009, BR-010 | FR-097–FR-100 | UC-018, UC-019 | RULE-005, RULE-007, RULE-009, RULE-018–RULE-022 | AC-057–AC-060 | TS-057–TS-060 | Must/Should — ikinci faz |
| BR-009–BR-011 | FR-101–FR-106 | UC-019, UC-020 | RULE-002, RULE-005, RULE-007, RULE-018–RULE-023 | AC-061–AC-065 | TS-061–TS-065 | Should/Could — ikinci faz |
| BR-010, BR-011 | FR-107–FR-111 | UC-018, UC-020, UC-021 | RULE-002, RULE-005, RULE-007, RULE-009–RULE-011, RULE-014, RULE-017–RULE-023 | AC-066–AC-071 | TS-066–TS-071 | Must/Should/Could — ikinci faz |

## Kanıta Dayalı Karar Sistemi İzlenebilirliği

Kanonik hedef tasarım
[Kanıta Dayalı Karar Sistemi](../02-Mimari/Kanita-Dayali-Karar-Sistemi.md),
mimari karar `ADR-019`, gereksinim kaynağı
[04.14-Kanıta Dayalı Karar Desteği](04-Fonksiyonel-Gereksinimler/04.14-Kanita-Dayali-Karar-Destegi.md)
ve kesinleşmiş teknik yönler `OPEN-026–OPEN-036` karar kayıtlarıdır.

| Gereksinim | Mimari / veri modeli | API / UI | IAM / güvenlik | Test / operasyon |
| --- | --- | --- | --- | --- |
| FR-097–FR-100 | UseCaseScoreProfile, EvidenceItem/Link, RunManifest, ImpactAssessment | Kullanım kararı, skor/kanıt/etki ve reproduction | Skor/formül/kanıt/reproduction izinleri | NFR-MNT-008; AC/TS-057–060; karar runbook'u |
| FR-101–FR-103 | LineageSnapshot, ChangeEvent, Diagnosis | Simülasyon, lineage, drift ve kök neden | Lineage/değişiklik scope'u | AC/TS-061–063; sürüm/değişiklik kapısı |
| FR-104–FR-105 | Recommendation, RemediationAction, ConfidenceAssessment | Öneri, dry-run, onay, canary ve rollback | Öneren/onaylayan ayrımı; otomasyon izinleri | AC/TS-064/069; remediation runbook'u |
| FR-106–FR-109 | DataContract, QualityDebtItem, EvidenceItem | Sözleşme ihlali, tarama gerekçesi, maskeli kayıt ve borç görünümü | Gerçek/maskeli kayıt, DLP, geçici yetki | AC/TS-065–068 |
| FR-110 | ChaosExperiment, InjectedFault, DetectionResult | Deney işi ve sonuçları | Ayrı chaos izni, ortam attestation ve onay | AC/TS-070; chaos runbook akışı |
| FR-111 | IncidentTimelineEvent, EvidencePackage | Zaman çizelgesi ve asenkron paket | Paket üretme/indirme, DLP ve audit | NFR-MNT-008; AC/TS-071; saklama/dışa aktarma kapısı |

## Sentetik Veri İzlenebilirliği

Kanonik hedef tasarım
`02-Mimari/Sentetik-Veri-ve-Gizlilik-Stratejisi.md`, mimari karar `ADR-016` ve
açık kararlar `OPEN-024/025`'tir. `OPEN-014` anonimleştirilmiş üretim örneğiyle
nihai performans kabulünü korur.

| Gereksinim | Mimari bileşen / veri modeli | Test | Risk / karar |
| --- | --- | --- | --- |
| FR-088 | Synthetic Data Orchestrator; SyntheticDatasetPolicy | AC/TS-048 | ADR-016; OPEN-024/025 |
| FR-089–FR-091 | Schema/Constraint Loader; Distribution, Relationship, Temporal Generator; Defect Injection Engine; SyntheticScenario | AC/TS-048, AC/TS-050, AC/TS-051, AC/TS-054 | RISK-017; OPEN-024 |
| FR-092 | Ground Truth Registry; Expected-versus-Actual Comparator; SyntheticGroundTruth | AC/TS-050–AC/TS-052 | RISK-017; DQ-SCR-004–006/014–018/025/028/032 |
| FR-093 | Generation Run Registry; SyntheticGenerationRun | AC/TS-049, AC/TS-056 | RULE-007/016; ADR-016 |
| FR-094 | Synthetic Dataset Catalog; kaynak kullanım politikası | AC/TS-050, AC/TS-056 | NFR-PERF-010; OPEN-014 |
| FR-095 | Privacy Risk Evaluator; SyntheticValidationResult | AC/TS-053 | RISK-016; NFR-PRV-007; OPEN-024/025; OPEN-BNK-007/008/012 |
| FR-096 | Synthetic Dataset Validator; izole bildirim/issue adaptörü; RetentionPolicy | AC/TS-052, AC/TS-055, AC/TS-056 | RULE-006/011/014/017; OPEN-BNK-008/009/010 |

## DQ-SCR Karar İzlenebilirliği

Tüm satırlarda hedef mimari kararı `ADR-015`, kanonik gereksinim kaydı
`04.06-Skorlama.md`, kanonik teknik tasarım
`Veri-Kalitesi-Skorlama-ve-Olcum-Yeterliligi.md` ve genel operasyonel değişiklik kapısı
`Surum-ve-Degisiklik-Yonetimi.md` belgesidir.

| Karar ID | Gereksinim / kural | Mimari ve veri modeli | API / UI | Test | Operasyon / açık karar |
| --- | --- | --- | --- | --- | --- |
| `DQ-SCR-001` | FR-053, FR-054, FR-064 | Skorlama ve risk/remediation sınırı | Dashboard amaç ve ayrı KPI'lar | AC/TS-038 | Veri Yönetişimi sahipliği |
| `DQ-SCR-002` | FR-049, FR-050, FR-054, FR-057 | QualityScore kapsam hiyerarşisi | Açıklama drill-down'ı | AC/TS-029 | OPEN-020 |
| `DQ-SCR-003` | FR-026, FR-050, FR-054 | QualityDimension uygulanabilirliği | Boyut matrisi ve `NotApplicable` | AC/TS-028 | OPEN-020, OPEN-BNK-013 |
| `DQ-SCR-004` | FR-046, FR-047; RULE-004 | RuleResult sayaçları | Skor açıklama metrikleri | AC/TS-027, AC/TS-039–040 | Replay sayaç doğrulaması |
| `DQ-SCR-005` | FR-048, FR-053, FR-060; RULE-003 | Teknik sağlık ve yeterlilik sınırı | Eski skor zamanı ve ayrı teknik/yeterlilik durumu | AC/TS-030, AC/TS-043, AC/TS-045 | Teknik alarm; OPEN-BNK-005/006/016 |
| `DQ-SCR-006` | FR-046–FR-048, FR-054 | RuleResult/QualityScore/MeasurementQualificationResult durumları | Ortak fakat ayrık status mapper | AC/TS-027, AC/TS-043 | OPEN-022, OPEN-023 |
| `DQ-SCR-007` | FR-023, FR-026, FR-046 | Kural/politika tanımı | Boyut ve kural kırılımı | TEST-INDEX DQ-SCR matrisi | Politika değişiklik kapısı |
| `DQ-SCR-008` | FR-023, FR-029, FR-032, FR-033 | RuleVersion ve referans sürümü | Kural açıklaması | TEST-INDEX DQ-SCR matrisi | Sürüm/replay kontrolü |
| `DQ-SCR-009` | FR-026, FR-033, FR-046 | Ölçüm yöntemi ve güven girdisi | Doğruluk yöntemi açıklaması | AC/TS-028 | Veri sahibi doğrulaması |
| `DQ-SCR-010` | FR-023, FR-033, FR-046 | Mutabakat kuralı/politikası | Kural ve boyut kırılımı | TEST-INDEX DQ-SCR matrisi | Tolerans sürüm kapısı |
| `DQ-SCR-011` | FR-023, FR-046 | Kesin/olası duplicate sonucu | Güven/olasılık gösterimi | TEST-INDEX DQ-SCR matrisi | Kural sürümü kontrolü |
| `DQ-SCR-012` | FR-034, FR-046, FR-053 | Dataset zamanlılık politikası | Güncellik ve gecikme açıklaması | TEST-INDEX DQ-SCR matrisi | OPEN-BNK-017 |
| `DQ-SCR-013` | FR-047, FR-049 | ScoringPolicy normalizasyonu | Model/politika sürümü | TEST-INDEX DQ-SCR matrisi | OPEN-019 |
| `DQ-SCR-014` | FR-027, FR-035, FR-051, FR-052; RULE-005 | ScoringPolicy eşik sürümü | Eşik bağlamı/sürümü | AC/TS-032 | OPEN-019, OPEN-BNK-004/007 |
| `DQ-SCR-015` | FR-027, FR-035, FR-049, FR-052 | ScoringPolicy ağırlık sürümü | Ağırlık açıklaması | AC/TS-032 | OPEN-019, OPEN-BNK-004/007/013 |
| `DQ-SCR-016` | FR-049, FR-050 | İki aşamalı Scoring Engine | Boyut/dataset kırılımı | AC/TS-031, AC/TS-041 | Runtime geçiş backlogu |
| `DQ-SCR-017` | FR-030, FR-035, FR-049, FR-059 | Kritik kural politika çözümleyicisi | Ham/nihai skor ve kritik ihlal/blokaj durumu | AC/TS-031, AC/TS-042 | OPEN-019/023, OPEN-BNK-004 |
| `DQ-SCR-018` | FR-052, FR-059, FR-065 | DatasetCriticalityProfile | Ayrı kritiklik KPI'sı | AC/TS-030 | OPEN-020/022, OPEN-BNK-013 |
| `DQ-SCR-019` | FR-050, FR-054, FR-065 | DataRiskScore ve remediation | Ayrı risk KPI'sı | AC/TS-030, AC/TS-036 | OPEN-019/020, OPEN-BNK-013 |
| `DQ-SCR-020` | FR-046, FR-048, FR-054 | ScoreMeasurementSummary kapsamı | Kapsam KPI/drill-down | AC/TS-030, AC/TS-043–044 | OPEN-019/023 |
| `DQ-SCR-021` | FR-046, FR-048, FR-054 | ScoreMeasurementSummary güveni | Güven KPI/açıklaması | AC/TS-030, AC/TS-043–044 | OPEN-019/023 |
| `DQ-SCR-022` | FR-035, FR-046, FR-054 | DataQualityException | İstisna oranı/süresi | AC/TS-033 | OPEN-021, OPEN-BNK-004/008 |
| `DQ-SCR-023` | FR-035, FR-054, FR-077 | ScoreAssessmentOverride | Ham skor ve override ayrı | AC/TS-033 | OPEN-021, OPEN-BNK-004/005/006 |
| `DQ-SCR-024` | FR-023–FR-035 | QualityRule/RuleVersion yaşam döngüsü | Kural/politika yönetimi | TEST-INDEX DQ-SCR matrisi | Üretim öncesi backtest/shadow kapısı |
| `DQ-SCR-025` | FR-029, FR-047, FR-052, FR-053 | QualityScore/MeasurementQualificationResult sürümleri ve original_score_id | Trend sürüm sınırı | AC/TS-034, AC/TS-037, AC/TS-046 | Replay ve geri alma kontrolü |
| `DQ-SCR-026` | FR-050, FR-054, FR-057 | Skor açıklama bileşeni | Yetkili, maskeli drill-down | AC/TS-029 | OPEN-BNK-014 |
| `DQ-SCR-027` | FR-053, FR-055 | Trend bileşeni | Trend, hareket ve sürüm sınırı | AC/TS-034 | Alarm izleme politikası |
| `DQ-SCR-028` | FR-059–FR-063; RULE-003 | Ayrı kalite/teknik olayları | Alarm akışı ve korelasyon | AC/TS-035 | OPEN-BNK-010/017 |
| `DQ-SCR-029` | FR-064–FR-069; RULE-006 | DataQualityIssue remediation alanları | Risk/issue/yeterlilik detayı | AC/TS-036, AC/TS-047 | OPEN-023, OPEN-BNK-009/017 |
| `DQ-SCR-030` | FR-035, FR-077; RULE-005 | Maker-checker ve audit sınırı | Politika/istisna/override yönetimi | AC/TS-032, AC/TS-038 | OPEN-021, OPEN-BNK-004/005/006 |
| `DQ-SCR-031` | FR-031, FR-034, FR-039 | Execution/örnekleme politikası | Yöntem, hacim ve güven açıklaması | TEST-INDEX DQ-SCR matrisi | OPEN-BNK-011/012/017 |
| `DQ-SCR-032` | FR-029, FR-045, FR-047, FR-077; RULE-007 | Skor/yeterlilik snapshot-sürüm-replay bağı | Replay ve orijinal sonuç ayrımı | AC/TS-037, AC/TS-046 | OPEN-BNK-005/006/008/016 |
| `DQ-SCR-033` | FR-028, FR-035, FR-052 | Yönetişim ve yetki sınırı | Role bağlı yönetim yüzeyi | AC/TS-038 | OPEN-BNK-001/004/013 |


**İzlenebilirlik kontrol sonucu:** BR-001–BR-011, FR-001–FR-111,
`DQ-SCR-001`–`DQ-SCR-033`, UC-001–UC-021, RULE-001–RULE-023 ve
AC-001–AC-071 matris kapsamındadır. Kapsam aralıkları ayrıntılı test yönetim
aracına aktarılırken tekil satırlara bölünmelidir.

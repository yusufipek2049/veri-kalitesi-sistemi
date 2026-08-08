---
type: functional-audit
stage: "11 — Test Kapsamı ve Boşluk Analizi"
scope: test-coverage
inputs:
  - 02-Target-Capability-Hierarchy.md
  - 04-Functional-Gap-Inventory.md
  - 09-State-Machines.md
  - 10-Roles-and-Permissions.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-04
---

# 11 — Test Kapsamı ve Boşluk Analizi

> Mevcut test envanterinin **nicelik değil nitelik** değerlendirmesi. Test
> sayısını kalite göstergesi kabul etmez; her testi **altyapı tipine** (gerçek
> PostgreSQL, mock, in-memory), **yetki kapsamına** (authorization),
> **eşzamanlılık davranışına** (concurrency), **audit atomikliğine** ve
> **uçtan uca** (E2E) ayrımına tabi tutar. Her boşluk en az bir hedef
> fonksiyona ve kullanıcı akışına bağlıdır.

---

## 1. Kapsam ve yöntem

### 1.1 Temel ilke

> **Test sayısı ≠ Kalite.** 1149 test fonksiyonu, 57 birim ve 11 entegrasyon
> dosyası — bu sayılar **yalnızca kapsamın bir boyutunu** gösterir. Asıl
> sorular: Hangi altyapıda çalışıyor? Gerçek yetki kontrolünden geçiyor mu?
> Eşzamanlı çakışmayı sınuyor mu? Audit olayı durum geçişiyle aynı
> transaction'da mı doğrulanıyor? Uçtan uca akışın tüm adımlarını kapsıyor mu?

### 1.2 Test sınıflandırma eksenleri

Her test dosyası ve fonksiyonu aşağıdaki eksenlerde sınıflandırılır:

| Eksen | Değerler | Anlam |
|---|---|---|
| **Altyapı** | `PG` · `SQLite` · `InMem` · `Mock` | Testin çalıştığı altyapı tipi |
| **Yetki** | `AUTH` · `NO-AUTH` | Gerçek yetki kontrolü içeriyor mu? |
| **Eşzamanlılık** | `CONC` · `SEQ` | Eşzamanlı çakışma senaryosu var mı? |
| **Audit atomikliği** | `AUDIT-ATOM` · `AUDIT-NO` | Durum geçişi ve audit olayı aynı transaction'da mı? |
| **Uçtan uca** | `E2E` · `PARTIAL` · `UNIT` | Akışın kaç adımını kapsıyor? |
| **Skip-gated** | `LIVE` · `SKIP` | Her zaman çalışır mı, ortam bağımlı mı? |

Altyapı tipleri:

| Etiket | Anlam | Güvenilirlik |
|---|---|---|
| `PG` | Gerçek PostgreSQL (`DATA_QUALITY_POSTGRES_TEST_URL` gerekli) | Yüksek — üretim davranışına en yakın |
| `SQLite` | SQLite (in-memory veya dosya) | Orta — SQL uyumluluğu sınırlı; `FOR UPDATE`, `SERIALIZABLE`, CTE davranışı farklı |
| `InMem` | Bellek içi store (`DevelopmentIssueStore`, `DevelopmentRuleStore` vb.) | Düşük — kalıcılık, transaction ve constraint davranışı yok |
| `Mock` | `Fake*`, `Mock*`, `InMemory*` test double'ları | Bağlama göre — protocol doğrulaması yapar ancak gerçek davranışı garanti etmez |

### 1.3 Akış kısaltmaları

| Kod | Akış |
|---|---|
| A | Yeni kaynak onboarding |
| B | Kural yaşam döngüsü |
| C | Kalite problemi |
| D | Teknik hata |
| E | Şema drifti |
| F | Skor güvenilirliği |
| G | İstisna ve override |
| H | Raporlama |
| I–M | Altyapı akışları (kimlik, yönetişim, sözleşme, sentetik, bildirim) |

---

## 2. Mevcut test envanteri — sayısal özet

### 2.1 Dosya ve test dağılımı

| Kategori | Dosya | Test fonksiyonu | Altyapı | Skip? |
|---|---|---|---|---|
| Birim (01-Birim) | 57 | 1057 | Çoğunlukla `InMem`/`Mock` | `LIVE` |
| Entegrasyon (02-Entegrasyon) | 11 | 92 | `PG` (skip-gated) | `SKIP` |
| Uçtan uca (03-Uctan-Uca) | 0 | 0 | — | — |
| Strateji belgesi | 1 | — | — | — |
| Support (legacy) | 1 | — | `SQLite` | — |
| **Toplam** | **70** | **1149** | | |

Sayılar `test_*.py` dosya adı kalıbı ve `def test_` sayımıyla üretilmiştir.
Entegrasyon dizinindeki `conftest.py` test dosyası değildir; 12'lik önceki
sayım bu dosyayı da içeriyordu.

**Fonksiyon ≠ koşulan test.** `pytest --collect-only` parametrizasyon sonrası
**1505** test toplar (1149 fonksiyondan). Bu ayrım §13'te ayrıca kayıtlıdır.

### 2.2 Altyapı dağılımı (dosya bazında)

| Altyapı | Dosya sayısı | Oran | Değerlendirme |
|---|---|---|---|
| `InMem`/`Mock` (birim) | 53 | 78% | Bellek içi store ve test double'ları — kalıcılık davranışı test edilmiyor |
| `PG` (entegrasyon, skip-gated) | 11 | 16% | Gerçek PostgreSQL; 10 dosya `DATA_QUALITY_POSTGRES_TEST_URL`, `test_synthetic_postgresql_integration.py` ise `SYNTHETIC_POSTGRES_TEST=1` gerektirir |
| `SQLite` (birim) | 4 | 6% | SQLite in-memory; `FOR UPDATE` ve seri yalıtım test edilmiyor |
| `E2E` | 0 | 0% | Uçtan uca test yok |

Oranlar 68 test dosyası (57 birim + 11 entegrasyon) üzerinden hesaplanmıştır.

### 2.3 Niteliksel eksen dağılımı (fonksiyon bazında)

| Eksen | Fonksiyon sayısı | Oran | Değerlendirme |
|---|---|---|---|
| Yetki testi (`AUTH`) | ~129 | 11% | Çoğunlukla `FakeAuthorizationService` üzerinden; gerçek rol/izin matrisi değil |
| Audit atomikliği (`AUDIT-ATOM`) | ~112 | 10% | Audit olayı doğrulaması var ancak PG transaction atomikliği yalnız entegrasyonda |
| Eşzamanlılık (`CONC`) | ~56 | 5% | Lease, retry ve skip-locked senaryoları; ancak çoğu birim düzeyinde mock ile |
| Durum makinesi geçişi | ~24 | 2% | Yalnızca bazı varlıklar; 29 durum makinesinin çoğu test edilmiyor |
| Uçtan uca (`E2E`) | 0 | 0% | Tek bir tam akış testi bile yok |

---

## 3. Test double envanteri

Mevcut testlerde kullanılan test double'ları:

| Double | Tip | Kullanan dosya | Sınırlama |
|---|---|---|---|
| `FakeAuthorizationService` | Mock | `test_investigation_evidence.py`, `test_enterprise_lab_adapters.py` | Dataset/source scope sabit; rol tabanlı değil |
| `FakeIssueInvestigationReader` | Mock | `test_investigation_evidence.py` | Tek sorun döndürür; çoklu sorun ve SLA senaryosu yok |
| `FakeEvidenceProvider` | Mock | `test_investigation_evidence.py` | Statik payload; gerçek kanıt toplama yok |
| `FakeServiceNowHttpAdapter` | Mock | `test_enterprise_lab_adapters.py` | HTTP çağrısını taklit eder; idempotency testi yok |
| `FakePreparedAuditRepository` | Stub | `conftest.py` (entegrasyon) | Kalıcılık yapmaz; `append()` kabul eder |
| `InMemorySecretResolver` | Mock | `test_investigation_evidence.py` | Sır çözümü sabit; gerçek vault/sır yönetimi yok |
| `InMemoryProfilePolicyResolver` | Mock | `test_investigation_evidence.py` | Statik politika; dinamik politika yaşam döngüsü yok |
| `DevelopmentIssueStore` | InMem | `development.py` (birim testlerde) | Kalıcılık yok; transaction yok; constraint yok |
| `DevelopmentRuleStore` | InMem | `development.py` |同上 |
| `DevelopmentDataSourceStore` | InMem | `development.py` |同上 |
| `SQLiteScoreRepository` | SQLite | `test_dashboard.py`, `test_enterprise_lab_adapters.py` | PG skor sorgusu davranışı farklı |
| `SQLiteTransactionalAudit` | SQLite | `test_synthetic_oracle.py` | PG audit zinciri davranışı farklı |
| `LegacySQLiteIssueRepository` | SQLite | `support/legacy_sqlite_issue_repository.py` | Migration uyumluluğu için legacy |

**Değerlendirme:** 16 dosyada test double tanımlanmış; 127 referans. Test
double'lar protokol doğrulaması için değerli ancak **gerçek PostgreSQL
davranışını** (constraint, transaction isolation, `FOR UPDATE SKIP LOCKED`,
trigger) garanti etmez.

---

## 4. Domain bazında test kapsamlılığı

Her domain için test dosya sayısı, altyapı dağılımı ve niteliksel değerlendirme:

| Domain | Birim dosya | Entegrasyon dosya | PG testi var mı? | Yetki testi? | Eşzamanlılık? | Audit atomikliği? | E2E? | Değerlendirme |
|---|---|---|---|---|---|---|---|---|
| D01 Yönetişim | 0 | 0 | ❌ | ❌ | ❌ | ❌ | ❌ | **Tamamen eksik** — GAP-026 |
| D02 Kimlik | 1 (42) | 0 | ❌ | ⚠️ Mock | ❌ | ❌ | ❌ | Rol tanımı ve SoD testi yok |
| D03 Kaynak | 4 (110) | 2 (14) | ✅ Skip | ⚠️ Mock | ❌ | ⚠️ Kısmi | ❌ | Kaynak CRUD ve **servis düzeyi** aktivasyon maker-checker testli; API yolu bu kontrolü atlıyor (§6.3) |
| D04 Katalog | 2 (17) | 0 | ❌ | ❌ | ❌ | ❌ | ❌ | Dataset/alan yaşam döngüsü testi yok; GAP-004 |
| D05 Profil | 2 (16) | 0 | ❌ | ❌ | ❌ | ❌ | ❌ | Profil yürütme ve baseline testi yok; GAP-005 |
| D06 Kural | 5 (169) | 1 (11) | ✅ Skip | ⚠️ Mock | ❌ | ⚠️ Kısmi | ❌ | Kural CRUD testli; şablon, onay, gölge yok; GAP-020 |
| D07 Yürütme | 4 (60) | 2 (52) | ✅ Skip | ❌ | ✅ Lease | ⚠️ Kısmi | ❌ | İş kuyruğu ve zamanlama servisi testli; zamanlayıcı/worker süreci ve `JOB_CLAIMED` audit'i yok; GAP-002/003 |
| D08 Skor | 4 (49) | 1 (1) | ✅ Skip | ❌ | ❌ | ❌ | ❌ | Skor hesaplama testli; atomik yayım yok; GAP-008 |
| D09 Sorun | 4 (111) | 3 (9) | ✅ Skip | ⚠️ Mock | ❌ | ⚠️ Kısmi | ❌ | Sorun CRUD testli; SLA, istisna, remediation yok; GAP-006/009/014 |
| D10 Lineage | 1 (19) | 1 (3) | ✅ Skip | ❌ | ❌ | ❌ | ❌ | Lineage okuma testli; sözleşme, kalite borcu yok; GAP-010/012 |
| D11 Rapor | 2 (35) | 1 (4) | ✅ Skip | ❌ | ❌ | ❌ | ❌ | Rapor listesi testli; asenkron üretim yok; GAP-016 |
| D12 Bildirim | 2 (51) | 0 | ❌ | ❌ | ❌ | ❌ | ❌ | Servis testli; teslimat hattı yok; GAP-007 |
| D13 Audit/Saklama | 5 (63) | 0 | ❌ | ❌ | ❌ | ✅ Birim | ❌ | Audit zinciri birim testli; PG atomikliği yok; GAP-011 |
| D14 Operasyon | 0 | 0 | ❌ | ❌ | ❌ | ❌ | ❌ | **Tamamen eksik** — GAP-024 |
| D15 Sentetik | 5 (53) | 1 (2) | ✅ Skip | ⚠️ Mock | ❌ | ⚠️ Kısmi | ❌ | Generator testli; yüzey ve doğruluk yok; GAP-025 |

---

## 5. Durum makinesi test boşlukları

29 durum makinesinin test kapsamılığı:

| ST | Geçiş testi var mı? | Yasak geçiş testi? | SoD testi? | Audit atomikliği? | Eşzamanlılık? | İlgili GAP |
|---|---|---|---|---|---|---|
| ST-Policy | ❌ | ❌ | ❌ | ❌ | ❌ | GAP-026 |
| ST-User | ❌ | ❌ | ❌ | ❌ | ❌ | GAP-022 |
| ST-RoleAssignment | ❌ | ❌ | ❌ | ❌ | ❌ | GAP-022 |
| ST-Session | ⚠️ Mock | ❌ | ❌ | ❌ | ❌ | GAP-022 |
| ST-AccessReviewItem | ❌ | ❌ | ❌ | ❌ | ❌ | GAP-022 |
| ST-DataSource | ✅ Birim | ❌ | ✅ Birim | ⚠️ PG skip | ❌ | GAP-001 |
| ST-ConnectionRevision | ✅ Birim | ❌ | ❌ | ⚠️ PG skip | ❌ | GAP-001 |
| ST-Dataset | ❌ | ❌ | ❌ | ❌ | ❌ | GAP-004 |
| ST-SchemaChange | ❌ | ❌ | ❌ | ❌ | ❌ | GAP-019 |
| ST-Profile | ⚠️ Kısmi | ❌ | ❌ | ❌ | ❌ | GAP-005 |
| ST-ProfileBaseline | ❌ | ❌ | ❌ | ❌ | ❌ | GAP-005 |
| ST-RuleTemplate | ❌ | ❌ | ❌ | ❌ | ❌ | GAP-020 |
| ST-QualityRule | ✅ Birim | ❌ | ❌ | ⚠️ PG skip | ❌ | GAP-001 |
| ST-RuleVersion | ✅ Birim | ❌ | ✅ Birim | ⚠️ PG skip | ❌ | GAP-001 |
| ST-ApprovalRequest | ⚠️ Birim (domain bazında) | ❌ | ✅ Birim | ⚠️ PG skip | ❌ | GAP-022 |
| ST-Schedule | ✅ Birim (SQLite) | ⚠️ Kısmi | ❌ | ⚠️ Kısmi | ❌ | GAP-003 |
| ST-Job | ✅ PG skip | ⚠️ Kısmi | ❌ | ✅ PG skip | ✅ PG skip | GAP-002 |
| ST-DeadLetterRecord | ✅ PG skip | ❌ | ❌ | ⚠️ PG skip | ❌ | GAP-002 |
| ST-RuleExecution | ✅ Birim | ❌ | ❌ | ⚠️ PG skip | ❌ | GAP-001 |
| ST-QualityScore | ✅ Birim | ❌ | ❌ | ❌ | ❌ | GAP-008 |
| ST-Issue | ✅ Birim+PG | ❌ | ✅ Birim | ⚠️ PG skip | ❌ | GAP-001/006 |
| ST-Exception | ❌ | ❌ | ❌ | ❌ | ❌ | GAP-009 |
| ST-RemediationAction | ❌ | ❌ | ❌ | ❌ | ❌ | GAP-009 |
| ST-DataContract | ❌ | ❌ | ❌ | ❌ | ❌ | GAP-010 |
| ST-ReportJob | ⚠️ Kısmi | ❌ | ❌ | ❌ | ❌ | GAP-016 |
| ST-NotificationDelivery | ⚠️ Birim | ❌ | ❌ | ❌ | ❌ | GAP-007 |
| ST-IntegrationRecord | ⚠️ Birim | ❌ | ❌ | ❌ | ❌ | GAP-023 |
| ST-LegalHold | ✅ Birim | ❌ | ❌ | ❌ | ❌ | GAP-011 |
| ST-OperationalIncident | ❌ | ❌ | ❌ | ❌ | ❌ | GAP-024 |

**Özet:** 29 durum makinesinden 12'sinde geçiş testi var (çoğu birim
düzeyinde), yalnız 1'inde (ST-Job) eşzamanlılık testi var, yasak geçiş testi
yalnız ST-Job ve ST-Schedule'da kısmidir.

**SoD sütunu düzeltmesi.** Maker ≠ checker kuralı dört durum makinesinde
birim testiyle sabitlenmiştir:
`test_rules.py:825 test_fr_035_bfr_sod_002_maker_cannot_decide_same_change`,
`test_data_sources.py:2205` (`match="maker cannot approve"`),
`test_data_sources.py:3255 test_fr_010_inactive_source_reactivation_requires_maker_checker`,
`test_issues.py:961 test_fr_069_rule_013_resolution_creator_cannot_verify_own_resolution`.
Bu testler **servis katmanını** doğrular. Çalıştırılabilir API'de aynı garanti
yoktur: `POST /data-sources/{id}/activation` gerçek servisi hiç çağırmaz
(§6.3, GAP-001/GAP-022). Yani SoD "test edilmiş" olmakla "çalışan üründe
uygulanıyor" olmak bu belgede ayrı iki iddiadır.

**ST-ApprovalRequest.** Ortak/generic bir approval aggregate'i yoktur; ancak
kural (`rule_approval_requests`) ve veri kaynağı
(`data_source_activation_requests`) için domain'e özgü onay talebi zincirleri
model, migration, servis, repository ve testleriyle mevcuttur. Bu nedenle
satır tek bir `❌` değil, domain bazında `⚠️`dir.

---

## 6. Rol ve yetki testi boşlukları

### 6.1 Rol bazında test kapsamı

| Rol | Rol tanımı testi? | İzin atama testi? | Kapsam çözümleme testi? | SoD testi? |
|---|---|---|---|---|
| Platform Admin | ❌ | ❌ | ❌ | ❌ |
| Security Admin | ❌ | ❌ | ❌ | ❌ |
| Data Governance Admin | ❌ | ❌ | ❌ | ❌ |
| Data Owner | ❌ | ❌ | ❌ | ❌ |
| Data Steward | ❌ | ❌ | ❌ | ❌ |
| Technical Data Steward | ❌ | ❌ | ❌ | ❌ |
| Rule Author | ❌ | ❌ | ❌ | ❌ |
| Rule Approver | ❌ | ❌ | ❌ | ❌ |
| Issue Assignee | ❌ | ❌ | ❌ | ❌ |
| Issue Verifier | ❌ | ❌ | ❌ | ❌ |
| Report Consumer | ❌ | ❌ | ❌ | ❌ |
| Auditor | ❌ | ❌ | ❌ | ❌ |
| Operations User | ❌ | ❌ | ❌ | ❌ |
| Integration Service Account | ❌ | ❌ | ❌ | ❌ |
| Read-only Viewer | ❌ | ❌ | ❌ | ❌ |

**Değerlendirme:** Hedef modelin 15 rolünün hiçbirinin **tanımı veya ataması**
test edilmiyor; bunun basit nedeni `roles`/`role_assignments` tablolarının hiç
olmamasıdır (GAP-022). `test_identity.py` (42 test) kimlik doğrulama ve oturum
yönetimini test ediyor ancak **rol tabanlı yetki matrisini** değil.

**Kapsam çözümlemesi sütunu için düzeltme.** "Hiç test edilmiyor" ifadesi
okuma yolu için doğru değildir. `PolicyAuthorizationService` kararındaki
izinli ID kümesi dört sorgu servisinde reader'a taşınır ve **boş kapsamın
kapsamsız sorguya dönüşmediği** dört ayrı testle sabitlenmiştir:

| Test | Dosya |
|---|---|
| `test_fr_007_empty_scope_returns_empty_list_without_unscoped_query` | `test_data_source_api.py:66` |
| `test_fr_023_empty_dataset_scope_does_not_become_unscoped_query` | `test_rule_api.py:83` |
| `test_fr_043_empty_source_scope_does_not_become_unscoped_query` | `test_execution_api.py:81` |
| `test_nfr_sec_001_empty_issue_scope_does_not_escalate` | `test_issue_api.py:92` |

Test edilmeyen şey kapsam **kaynağıdır**: izinli ID kümesi kalıcı bir atama
kaydından değil, test/dev sabitinden gelir. Komut yolunda ise doğrulanacak bir
kontrol bulunmadığı için test de yoktur (§6.3).

### 6.2 Kapsam bazında yetki testi

| Kapsam tipi | Test var mı? | Yöntem | Sınırlama |
|---|---|---|---|
| `KG` (kurum geneli) | ❌ | — | Rol tanımı yok; test edilecek matris yok |
| `DOM` (domain) | ⚠️ Mock | `FakeAuthorizationService(permitted_dataset_ids)` | Statik ID listesi; din domain çözümlemesi yok |
| `SRC` (kaynak) | ⚠️ Mock |同上 |同上 |
| `DS` (dataset) | ⚠️ Mock |同上 | Gerçek `assignment_scopes` tablosu yok |
| `OBJ` (nesne sahipliği) | ⚠️ Mock | `test_issue_api.py` — `assigned_to` kontrolü | Yalnız sorun ataması; genel sahiplik modeli yok |
| `SYS` (sistem) | ✅ Birim | `test_job_queue.py` — sistem aktörü iş sahiplenmesi | Yalnız iş kuyruğu |

### 6.3 Okuma/komut yolu ayrışması — test kapsamındaki asıl boşluk

Yetki testi boşluğu bu repository'de homojen değildir; okuma ve komut yolları
farklı olgunluktadır.

| Yol | Kod durumu | Test durumu |
|---|---|---|
| Okuma (query) | `PolicyAuthorizationService` kararı reader filtresine taşınır | ✅ Boş kapsam dâhil test edilmiş (§6.2) |
| Komut (mutation) | Aktör bağlamı port sınırına hiç geçmez | ❌ Doğrulanacak kontrol yok |

Komut yolundaki durum şudur:

- `POST /api/v1/data-sources` · `/test` · `/activation` · `/passivation`
  route'ları çözülen `ActorContext`'i mutation portuna iletmez
  (`api/app.py:2017-2110`). Aktarım yapılmadığından `DataSourceService`'in
  maker ≠ checker, checker rolü, süre ve sürüm kontrolleri hiç çalışmaz;
  bağlanan `DevelopmentDataSourceStore.activate` yalnız durum guard'ı uygular.
- `DevelopmentRuleStore.create_rule` aktör bağlamının `None` olmadığını
  kontrol eder, rol veya dataset kapsamını doğrulamaz
  (`api/development.py:837-882`).
- Manuel çalıştırma ucu yalnız `actor_id` dizesi geçirir ve aktör yoksa
  `"unknown"` yazar (`api/app.py:2120-2137`);
  `PostgreSQLExecutionStartService.start_manual` kural sürümü/kaynak
  kimliklerinin varlığını, aktifliğini veya kapsamını doğrulamaz.

**Yanıltıcı test uyarısı.**
`tests/unit/test_rule_api.py:405`
`test_fr_031_create_rule_without_dataset_scope_returns_403` adına rağmen
`assert response.status_code == 201` yazar; docstring 403 beklendiğini
söylerken kod içi yorum fake servisin kapsam kontrolü yapmadığını kabul eder.
Aynı şekilde `test_data_source_api.py:360`
`test_data_source_write_successful_activate_passivate_flow`,
onay adımı atlanan `TEST_SUCCEEDED -> ACTIVE` geçişi için `200` bekleyerek
bypass'ı **yeşil test olarak sabitler**. Bu iki test kapsam sayımında
"yetki testi" gibi görünür; gerçekte boşluğu görünmez kılar.

---

## 7. Eşzamanlılık testi boşlukları

### 7.1 Mevcut eşzamanlılık testleri

| Dosya | Test tipi | Altyapı | Kapsam |
|---|---|---|---|
| `test_postgresql_job_queue.py` | `FOR UPDATE SKIP LOCKED`, lease geri alma, çifte sahiplenme | PG (skip) | ST-Job |
| `test_persistent_job_worker.py` | Retry, heartbeat, deneme sınırı | InMem | ST-Job |
| `test_executions.py` | İptal bayrağı, zaman aşımı | InMem | ST-RuleExecution |
| `test_postgresql_execution_persistence.py` | Execution durum geçişleri | PG (skip) | ST-RuleExecution |
| `test_postgresql_rule_mutations.py` | Kural sürüm çakışması | PG (skip) | ST-RuleVersion |

### 7.2 Eksik eşzamanlılık senaryoları

| ST | Eksik senaryo | Önem | İlgili akış |
|---|---|---|---|
| ST-QualityScore | Atomik yayım — iki eşzamanlı skor hesaplaması aynı anda yayımlamaya çalışır | Kritik | F |
| ST-ApprovalRequest | İki checker aynı anda onay vermeye çalışır; biri reddedilmeli | Kritik | B, C, G, K |
| ST-DataContract | İki taraf aynı anda kabul etmeye çalışır; çift onay atomikliği | Yüksek | K |
| ST-Schedule | İki zamanlayıcı aynı vade için aynı anda çalıştırma açmaya çalışır | Yüksek | B |
| ST-Issue | İki atanan aynı sorunu aynı anda çözmeye çalışır | Orta | C |
| ST-DataSource | Aktivasyon talebi açıkken bağlantı revizyonu yürürlüğe alınır | Orta | A |
| ST-RuleVersion | İki sürüm aynı anda aktive edilmeye çalışır | Yüksek | B |
| ST-Exception | İstisna süresi dolarken onay isteği geliyor | Orta | G |

---

## 8. Audit atomikliği testi boşlukları

### 8.1 Mevcut audit testleri

| Dosya | Test tipi | Altyapı | Kapsam |
|---|---|---|---|
| `test_audit.py` | Audit olay oluşturma, zincir bütünlüğü, digest | InMem | Genel audit |
| `test_audit_api.py` | Audit API endpoint'leri | InMem | API yüzeyi |
| `test_retention_disposal_job.py` | İmha job'ı audit | InMem | D13 |
| `test_retention_legal_hold.py` | Yasal muhafaza audit | InMem | D13 |
| `test_postgresql_execution_persistence.py:592` | `test_audit_outbox_atomic_write` | PG (skip) | ST-RuleExecution |
| `test_postgresql_issue_mutations.py:53` | `test_fr_064_070_issue_lifecycle_and_audit_share_postgresql_transactions` | PG (skip) | ST-Issue |
| `test_postgresql_issue_mutations.py:327` | `test_nfr_rel_006_audit_conflict_rolls_back_issue_and_history` | PG (skip) | ST-Issue |
| `test_postgresql_score_contributions.py:79` | `test_graph_snapshot_and_audit_outbox_are_atomic_and_immutable` | PG (skip) | Katkı grafiği |
| `test_postgresql_lineage_evidence.py` | Kanıt anlık görüntüsü + outbox | PG (skip) | D10 |

### 8.2 Eksik audit atomikliği senaryoları

Her durum geçişunun audit olayı **aynı transaction'da** yazılmalıdır. Bu
davranışın testi:

| Durum makinesi | Transaction atomikliği testi | Önem |
|---|---|---|
| ST-DataSource aktivasyonu | Aktivasyon kararı + `DATA_SOURCE_ACTIVATION_DECIDED` aynı transaction'da | Yüksek |
| ST-RuleVersion aktivasyonu | Sürüm aktive + `RULE_VERSION_ACTIVATED` + önceki `SUPERSEDED` aynı transaction'da | Yüksek |
| ST-QualityScore yayımı | Skor yayımı + `SCORE_PUBLISHED` + önceki `SUPERSEDED` aynı transaction'da | Kritik |
| ST-Issue çözüm | Çözüm kaydı + `ISSUE_RESOLVED` aynı transaction'da | Yüksek |
| ST-Exception onay | Onay + `EXCEPTION_DECIDED` + kalite borcu oluşumu aynı transaction'da | Yüksek |
| ST-Job sahiplenme | `CLAIMED` + `JOB_CLAIMED` + lease yazımı aynı transaction'da | Yüksek |
| ST-DataContract kabul | İki taraf onayı + `DATA_CONTRACT_ACCEPTED` + izleme kuralları bağlama aynı transaction'da | Yüksek |

**Mevcut durum — düzeltilmiş.** "Gerçek PostgreSQL transaction'ında durum
geçişi ve audit olayının atomikliğini doğrulayan entegrasyon testi sıfır"
ifadesi **yanlıştır**. §8.1'de listelenen beş dosya tam olarak bu davranışı
sınar: iş verisi yazımı ile `audit_outbox` satırının aynı SQLAlchemy
transaction'ında olduğunu, audit çakışmasının iş verisini geri aldığını ve
anlık görüntünün değişmez olduğunu doğrular.

Doğru olan ayrım şudur:

| İddia | Durum |
|---|---|
| Gerçek PG atomiklik testi **kodu** var mı? | ✅ Var (5 dosya, en az 4 adlandırılmış test) |
| Bu ortamda **koştu** mu? | ❌ Hayır — `pytest -q docs/testing/02-Entegrasyon` → `92 skipped` |
| Standart `pytest` koşumunda koşuyor mu? | ❌ Hayır — `DATA_QUALITY_POSTGRES_TEST_URL` yoksa tüm dosya atlanır; `.env` gitignore'dadır |

Bu nedenle geçerli boşluk "test yok" değil, **"testler yeşil kabul ediliyor
ama hiç yürütülmüyor"**dur. Bu, kapsam raporlaması açısından daha tehlikeli
bir durumdur: sayım testleri var sayar, CI ise davranışı hiç doğrulamaz.
§8.2 tablosundaki senaryolardan hâlâ karşılığı olmayanlar skor yayımı, istisna
onayı, iş sahiplenme (`JOB_CLAIMED` — bkz. §8.3) ve sözleşme kabulüdür.

### 8.3 `claim_next` audit boşluğu — kod düzeyinde eksik

`PostgreSQLJobQueueRepository.claim_next` (`jobs/postgresql_repository.py:271`)
`FOR UPDATE SKIP LOCKED`, lease ve kota uygular; ancak imzasında audit event
veya outbox parametresi **yoktur** ve gövdesinde `audit_outbox.stage` çağrısı
geçmez. Aynı dosyadaki `release_expired_claims` gibi diğer metodlar outbox
alır. Dolayısıyla §8.2'deki "ST-Job sahiplenme" satırı yalnız eksik bir test
değil, **eksik bir uygulamadır**: iş sahiplenme audit'siz gerçekleşir, bu
nedenle yazılabilecek bir atomiklik testi de bugün başarısız olurdu.

---

## 9. Uçtan uca (E2E) test boşlukları

### 9.1 Mevcut E2E testleri

**Yok.** `tests/e2e/` dizininde yalnız
`Gorsel-Dogrulama-Stratejisi.md` strateji belgesi var; çalıştırılabilir E2E
testi bulunmuyor.

### 9.2 Akış bazında E2E gereksinimi

Her bir canonical akış için E2E test senaryosu:

| Akış | Adım sayısı | E2E test? | Kritik boşluk |
|---|---|---|---|
| A (Kaynak onboarding) | 16 adım | ❌ | Keşif → katalog → profil → baseline zinciri tamamen testsiz |
| B (Kural yaşam döngüsü) | 16 adım | ❌ | Şablon → kural → sürüm → onay → aktive → zamanlama → skor zinciri testsiz |
| C (Kalite problemi) | 20 adım | ❌ | Sonuç → sorun → SLA → inceleme → çözüm → doğrulama → kapatma testsiz |
| D (Teknik hata) | 12 adım | ❌ | Hata → sınıflandırma → retry → dead-letter → telafi testsiz |
| E (Şema drifti) | 10 adım | ❌ | Keşif → fark → sınıflandırma → etki → karar testsiz |
| F (Skor güvenilirliği) | 14 adım | ❌ | Bölüm → sonuç → yeterlilik → skor → yayım → katkı grafiği testsiz |
| G (İstisna/override) | 9 adım | ❌ | Talep → onay → borç → bastırma → sonlandırma testsiz |
| H (Raporlama) | 10 adım | ❌ | Talep → iş → üretim → hassasiyet → indirme → imha testsiz |

### 9.3 E2E test öncelik sıralaması

| Öncelik | Akış | Gerekçe |
|---|---|---|
| 1 | C (Kalite problemi) | En uzun akış (20 adım); en fazla durum makinesi geçişi; işin çekirdeği |
| 2 | B (Kural yaşam döngüsü) | Maker-checker SoD; 4 durum makinesi; zamanlama ve skor bağımlılığı |
| 3 | F (Skor güvenilirliği) | Atomik yayım; seri yalıtım; katkı grafiği; audit yoğun |
| 4 | A (Kaynak onboarding) | 16 adım; 5 durum makinesi; GAP-001 bileşim kökü doğrulaması |
| 5 | D (Teknik hata) | Lease, retry, dead-letter; eşzamanlılık yoğun |
| 6 | G (İstisna/override) | SoD; kalite borcu; süre dolma |
| 7 | H (Raporlama) | Asenkron üretim; saklama |
| 8 | E (Şema drifti) | Etki analizi; baseline geçersiz kılma |

---

## 10. GAP bazında test boşlukları

Her GAP için mevcut test durumu ve gerekli testler:

| GAP | Mevcut test | Eksik test tipi | Öncelik |
|---|---|---|---|
| GAP-001 (bileşim) | PG repository birim+entegrasyon | Bileşim smoke testi (skip-gated olmayan) | Kritik |
| GAP-002 (worker) | İş kuyruğu PG skip | Worker lifecycle E2E; drain testi | Yüksek |
| GAP-003 (zamanlayıcı) | ✅ Birim (10 test, SQLite) | Daemon döngüsü; kaçırılan çalışma; çok zamanlayıcılı PG yarışı | Yüksek |
| GAP-004 (katalog) | ✅ Birim + PG skip (keşif/fark) | HTTP yüzeyi; `PARTIAL` keşifte kaldırma çıkarmama; katalog okuma | Yüksek |
| GAP-005 (profil) | ⚠️ Kısmi (`run_profile` testli) | Profil talebi/iptal yüzeyi; baseline; drift | Orta |
| GAP-006 (sorun üretimi) | ✅ Birim + PG skip (producer servisi) | Execution → issue köprüsü; `eligible_for_auto_issue` kapısı; manuel açma ucu | Yüksek |
| GAP-007 (bildirim) | ⚠️ Servis birim | Teslimat hattı; kanal yönlendirme; undeliverable | Orta |
| GAP-008 (skor) | ✅ Birim | Atomik yayım PG; katkı grafiği PG | Yüksek |
| GAP-009 (istisna/borç) | ❌ Yok | İstisna yaşam döngüsü; kalite borcu; bastırma | Yüksek |
| GAP-010 (sözleşme) | ❌ Yok | Sözleşme yaşam döngüsü; ihlal; iki taraf onayı | Orta |
| GAP-011 (saklama) | ✅ Birim | İmha job PG; legal hold + imha etkileşimi | Orta |
| GAP-012 (lineage) | ⚠️ Kısmi | Lineage alım; graf sorgu; etki analizi | Orta |
| GAP-013 (etki/teşhis) | ⚠️ Kısmi | Etki simülasyonu; kök neden hipotezi | Orta |
| GAP-014 (SLA) | ❌ Yok | SLA atama; ihlal; eskalasyon | Yüksek |
| GAP-015 (rapor zamanlama) | ❌ Yok | Zamanlama → rapor tetikleme | Düşük |
| GAP-016 (rapor üretim) | ⚠️ Kısmi | Asenkron üretim PG; dosya saklama | Orta |
| GAP-017 (çalıştırma) | ⚠️ Kısmi | Başlat/iptal komut yüzeyi | Orta |
| GAP-018 (kuyruk yüzeyi) | ❌ Yok | Dead-letter operasyon; yeniden işleme | Orta |
| GAP-019 (şema değişimi) | ❌ Yok | Şema değişikliği sınıflandırma; karar | Orta |
| GAP-020 (şablon) | ❌ Yok | Şablon yaşam döngüsü; bağımlılık; çakışma | Orta |
| GAP-021 (gölge) | ❌ Yok | Gölge yürütme; karşılaştırma | Düşük |
| GAP-022 (kimlik) | ⚠️ Kısmi | Rol atama; kapsam; SoD; oturum | Kritik |
| GAP-023 (ServiceNow) | ⚠️ Birim | Entegrasyon yüzeyi; idempotency | Düşük |
| GAP-024 (operasyon) | ❌ Yok | Sağlık; olay; bakım; telafi | Orta |
| GAP-025 (sentetik) | ✅ Birim+PG skip | Yüzey; doğruluk; yeterlilik deneyi | Düşük |
| GAP-026 (yönetişim) | ❌ Yok | Organizasyon; domain; politika yaşam döngüsü | Yüksek |

**"Mevcut test" sütunu ne demek değildir.** Bu sütun test **kodunun**
varlığını gösterir; GAP-003, GAP-004 ve GAP-006 için bulunan testler ilgili
servisleri (`SchedulingService`, `DataSourceService.discover_metadata`,
`IssueService.create_for_trigger`) doğrular, ancak bu servislerin hiçbiri
çalıştırılabilir bileşime bağlı değildir. Yani testler geçer, kullanıcı
kabiliyeti yine de yoktur. Sütunun `❌ Yok` olduğu satırlarda ise ne kod ne de
test vardır.

**Öncelik sütunu ≠ uygulama sırası.** Buradaki öncelik, boşluğun **test
riskini** derecelendirir; hangi GAP'in önce uygulanacağını söylemez.
Bağımlılık sırası [04-Functional-Gap-Inventory.md](04-Functional-Gap-Inventory.md)
§4'tedir: GAP-009 ve GAP-014 için `Yüksek` test önceliği, bu işlevlerin
GAP-006 (sorun üretimi) ve GAP-007 (bildirim) tamamlanmadan yazılabilir
olduğu anlamına gelmez — bu iki kayıt için test yazımı bağımlılıkları
kapandıktan sonra anlamlıdır.

---

## 11. Test altyapısı gereksinimleri

### 11.1 Gerçek PostgreSQL gerektiren testler

Aşağıdaki davranışlar **yalnız gerçek PostgreSQL** ile test edilebilir:

| Davranış | SQLite'da çalışır mı? | PG gerektiren testler |
|---|---|---|
| `SELECT … FOR UPDATE SKIP LOCKED` | ❌ | İş kuyruğu sahiplenme, zamanlama tetikleme |
| `SERIALIZABLE` isolation | ❌ | Skor atomik yayımı, katkı grafiği |
| `LISTEN/NOTIFY` | ❌ | Bildirim teslimatı, outbox izleme |
| Check constraint | ⚠️ Kısmi | Durum makinesi kısıtları |
| Trigger | ❌ | Audit zinciri, otomatik durum geçişleri |
| `GENERATED ALWAYS` kolon | ❌ | Digest, hash hesaplama |
| `jsonb` sorguları | ⚠️ Farklı | Metadata, kanıt payload |
| `bytea` | ⚠️ Farklı | Audit digest, previous_event_hash |

### 11.2 Önerilen test piramidi

```
          ┌─────────┐
          │  E2E    │  8 akış × 3 senaryo = 24 test
          │ (PG)    │  Gerçek PG + gerçek yetki + gerçek audit
          ├─────────┤
          │Entegrasy.│  ~50 test
          │ (PG)    │  Durum makinesi geçişleri + audit atomikliği
          ├─────────┤
          │ Birim   │  ~1200 test
          │(InMem/  │  İş mantığı, hesaplama, doğrulama
          │ Mock)   │
          └─────────┘
```

**Mevcut durum:** Piramit ters dönmüş — 1057 birim, 92 entegrasyon, 0 E2E.
Birim testlerin çoğu `InMem`/`Mock` altyapısında; gerçek yetki ve audit
atomikliği doğrulaması yapmıyor. Ayrıca entegrasyon katmanı pratikte
sıfırdır: 92 testin tamamı ortam değişkeni tanımlı olmadığı için atlanır
(§8.2), yani piramidin orta katmanı sayımda var, koşumda yoktur.

---

## 12. Öncelikli test yol haritası

### 12.1 Faz 1 — Kritik boşluklar (GAP-001, GAP-022)

| Test | Tip | Altyapı | Akış |
|---|---|---|---|
| Bileşim smoke testi: PG repo'lar bağlı iken kaynak/kural/sorun CRUD | Entegrasyon | PG | A, B, C |
| Rol atama + kapsam çözümleme testi | Birim | InMem | I |
| SoD çifti engelleme testi (8 BLOCK çifti) | Birim | InMem | B, C, G |
| Audit atomikliği: durum geçişi + audit olayı aynı transaction | Entegrasyon | PG | Tüm |

### 12.2 Faz 2 — Durum makinesi geçişleri

| Test | Tip | Altyapı | Akış |
|---|---|---|---|
| 29 durum makinesi geçerli geçiş testi | Birim | InMem | Tüm |
| Yasak geçiş engelleme testi (≥100 ikili) | Birim | InMem | Tüm |
| maker ≠ checker SoD doğrulaması | Entegrasyon | PG | B, C, G, K |
| Atomik yayım (skor, baseline, sürüm) | Entegrasyon | PG | F, B |

### 12.3 Faz 3 — Eşzamanlılık

| Test | Tip | Altyapı | Akış |
|---|---|---|---|
| `FOR UPDATE SKIP LOCKED` çifte sahiplenme | Entegrasyon | PG | D |
| Atomik yayım çakışması (skor) | Entegrasyon | PG | F |
| Çok zamanlayıcılı tek kazanan | Entegrasyon | PG | B |
| Lease kaybı — eski worker sonuç yazamaz | Entegrasyon | PG | D |

### 12.4 Faz 4 — E2E akış testleri

| Test | Akış | Adım | Altyapı |
|---|---|---|---|
| Kaynak onboarding E2E | A | 16 adım | PG + yetki + audit |
| Kural yaşam döngüsü E2E | B | 16 adım | PG + SoD + audit |
| Kalite problemi E2E | C | 20 adım | PG + SLA + audit |
| Skor güvenilirliği E2E | F | 14 adım | PG + SER + audit |

---

## 13. Kanıt sınırları

- Test sayıları `grep` ile dosya bazında çıkarılmıştır (57/11 dosya,
  1057/92 fonksiyon). Bu sayımda parametrize testler tek fonksiyon olarak
  sayılır; `pytest --collect-only -q` parametrizasyon sonrası **1505** test
  toplar.
- Seçili birim suite bu ortamda koşulmuştur:
  `test_data_sources.py`, `test_executions.py`, `test_issues.py`,
  `test_bff_session_api.py`, `test_data_source_api.py`, `test_rule_api.py`,
  `test_execution_api.py` → **297 passed**. Bu, §6.3'te tarif edilen
  bypass'ların çalışan testlerle sabitlendiğini de doğrular.
- `pytest -q docs/testing/02-Entegrasyon` → **92 skipped**. Entegrasyon testleri
  bu çalışma ağacında hiç yürütülmemiştir; bulguları "PG davranışı test
  edilmiştir" olarak okumak yanlıştır (§8.2).
- Domain bazında dosya eşleşmesi anahtar kelime bazlıdır; bazı dosyalar
  birden fazla domain'e ait test içerebilir.
- E2E test yokluğu `03-Uctan-Uca/` dizininin taranmasıyla doğrulanmıştır;
  dizinde yalnız strateji belgesi vardır.
- Niteliksel eksen dağılımı fonksiyon adı kalıplarıyla sınıflandırılmıştır;
  bazı testler adlandırma kalıbına uymasa da ilgili davranışı test ediyor
  olabilir.

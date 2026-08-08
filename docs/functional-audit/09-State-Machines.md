---
type: functional-audit
stage: "09 — Durum Makineleri"
scope: state-machines
inputs:
  - 02-Target-Capability-Hierarchy.md
  - 04-Functional-Gap-Inventory.md
  - 07-Target-Data-Model.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-04
---

# 09 — Durum Makineleri

> Hedef kabiliyet hiyerarşisindeki (§6.1) **29 durum makinesi** için geçiş
> tablosu, yasak geçişler, aktör/ön koşul, side-effect, audit olayı ve
> eşzamanlılık davranışı. Her durum makinesi en az bir hedef fonksiyona ve
> kullanıcı akışına bağlıdır.

---

## 1. Kapsam ve yöntem

### 1.1 Durum makinesi envanteri

| Kod | Varlık | Domain | Birincil akış |
|---|---|---|---|
| ST-Policy | Politika | D01 | J (yönetişim) |
| ST-User | Kullanıcı hesabı | D02 | I (kimlik) |
| ST-RoleAssignment | Rol ataması | D02 | I |
| ST-Session | Oturum | D02 | I |
| ST-AccessReviewItem | Erişim gözden geçirme | D02 | I |
| ST-DataSource | Veri kaynağı | D03 | A |
| ST-ConnectionRevision | Bağlantı revizyonu | D03 | A |
| ST-Dataset | Dataset | D04 | A, E |
| ST-SchemaChange | Şema değişikliği | D04 | E |
| ST-Profile | Profil çalıştırması | D05 | A, E |
| ST-ProfileBaseline | Profil baseline | D05 | A, F |
| ST-RuleTemplate | Kural şablonu | D06 | B |
| ST-QualityRule | Kalite kuralı | D06 | B |
| ST-RuleVersion | Kural sürümü | D06 | B |
| ST-ApprovalRequest | Onay talebi (ortak) | D01/D06/D09/D10 | B, C, G, K |
| ST-Schedule | Zamanlama | D07 | B |
| ST-Job | Kalıcı iş | D07 | D |
| ST-DeadLetterRecord | Dead-letter kaydı | D07 | D |
| ST-RuleExecution | Çalıştırma | D07 | B, D |
| ST-QualityScore | Kalite skoru | D08 | F |
| ST-Issue | Sorun | D09 | C |
| ST-Exception | İstisna | D09 | G |
| ST-RemediationAction | Düzeltme aksiyonu | D09 | C |
| ST-DataContract | Veri sözleşmesi | D10 | K |
| ST-ReportJob | Rapor | D11 | H |
| ST-NotificationDelivery | Bildirim teslimatı | D12 | M |
| ST-IntegrationRecord | Entegrasyon kaydı | D12 | M |
| ST-LegalHold | Yasal muhafaza | D13 | J |
| ST-OperationalIncident | Operasyonel olay | D14 | D |

### 1.2 Yasak geçiş gösterimi

Her durum makinesi için iki tablo verilir:

1. **Geçerli geçişler** — §6.1'den alınan orijinal geçiş tablosu.
2. **Yasak geçişler** — aynı varlıkta geçerli geçiş tablosunda *yer almayan*
   ancak yüzeyde denenmesi olası ikililer. `F` ile işaretlenir.

Kısıtlar:
- `maker ≠ checker` gerektiren geçişlerde aynı aktör her iki yönü
  birleştiremez (görev ayrılığı, `BLOCK`).
- `Sistem` aktörü yalnız otomatik tetikleyicilerde geçerlidir.
- `—` başlangıcı yalnızca yaratma geçişinde geçerlidir.

### 1.3 Eşzamanlılık modeli

Kısaltmalar:

| Etiket | Anlam |
|---|---|
| **OPT** | Optimistic concurrency — `version` kolonu artar, çakışmada `409` |
| **PES** | Pessimistic — `SELECT … FOR UPDATE SKIP LOCKED` |
| **IDEM** | Idempotency anahtarı — aynı anahtar tekrarlanmaz |
| **ATOM** | Atomic — audit olayı ve durum geçişi aynı transaction |
| **LEASE** | Lease tabanlı — `leased_until` süresiyle sınırlı sahiplik |
| **SER** | Serializable isolation — skor yayımı gibi kritik yollar |

---

## 2. D01 — Yönetişim ve organizasyon

### 2.1 ST-Policy — Politika

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Taslak oluştur | `DRAFT` | GA/PA | Tip katalogda | `POLICY_DRAFT_CREATED` | — |
| `DRAFT` | Onaya gönder | `IN_REVIEW` | GA (maker) | Şema geçerli, etki özeti var | `POLICY_SUBMITTED_FOR_APPROVAL` | Onay talebi açılır |
| `IN_REVIEW` | Onayla | `APPROVED` | SA/GA (checker≠maker) | Talep `PENDING` | `POLICY_APPROVAL_DECIDED` | — |
| `IN_REVIEW` | Reddet | `DRAFT` | Checker | Gerekçe zorunlu | `POLICY_APPROVAL_DECIDED` | — |
| `APPROVED` | Yürürlüğe al | `EFFECTIVE` | PA | Aralık çakışmıyor | `POLICY_MADE_EFFECTIVE` | Önceki `SUPERSEDED` |
| `EFFECTIVE` | Yeni sürüm yürürlüğe girer | `SUPERSEDED` | Sistem | — | `POLICY_MADE_EFFECTIVE` | — |
| `EFFECTIVE` | Geri al | `ROLLED_BACK` | PA | Hedef sürüm var | `POLICY_ROLLED_BACK` | Hedef geri döner |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden | Eşzamanlılık |
|---|---|---|---|
| `DRAFT` | `EFFECTIVE` | Onay adımı atlanamaz | — |
| `DRAFT` | `APPROVED` | Self-approval; SoD `BLOCK` | — |
| `IN_REVIEW` | `EFFECTIVE` | Yürürlüğe alma yalnız `APPROVED`'dan | — |
| `IN_REVIEW` | `SUPERSEDED` | Bekleyen talep üzerinde sürüm değiştirilemez | OPT |
| `APPROVED` | `DRAFT` | Geri dönüş yalnız reddedilirse | — |
| `SUPERSEDED` | `EFFECTIVE` | Donmuş sürüm yeniden yürürlüğe alamazz; yeni sürüm gerekir | — |
| `ROLLED_BACK` | Herhangi | Terminal altı; yeni sürümle devam | — |

**Eşzamanlılık:** `OPT` + `ATOM`. Yürürlüğe alma sırasında aralık çakışması
kontrolü `SER` seviyesinde yapılır. Önceki sürümün `SUPERSEDED` olması aynı
transaction'da atomik olarak gerçekleşir.

**İş akışı bağlantısı:** J (yönetişim) → `D01.C04.W01.A01`–`A04`.

---

### 2.2 ST-User — Kullanıcı hesabı

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Sağla | `ACTIVE` | SA / Sistem | Dış kimlik benzersiz | `USER_PROVISIONED` | — |
| `ACTIVE` | Pasifleştir | `INACTIVE` | SA / Sistem | — | `USER_DEACTIVATED` | Oturumlar `TERMINATED`, roller `REVOKED` |
| `INACTIVE` | Yeniden etkinleştir | `ACTIVE` | SA | Dış kimlik geçerli | `USER_REACTIVATED` | Roller geri verilmez |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `ACTIVE` | `ACTIVE` | Re-provision; aynı dış kimlik tekrar sağlanamaz |
| `INACTIVE` | `INACTIVE` | Zaten pasif |
| `INACTIVE` | Roller geri gelir | Yeniden etkinleştirmede roller **verilmez** — yeniden atanmalı |

**Eşzamanlılık:** `OPT` + `ATOM`. Pasifleştirme tüm oturumları aynı
transaction'da sonlandırır.

**İş akışı bağlantısı:** I (kimlik) → `D02.C01.W01.A01`–`A02`.

---

### 2.3 ST-RoleAssignment — Rol ataması

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Ata | `ACTIVE` | SA | SoD ihlali yok | `ROLE_ASSIGNED` | — |
| `ACTIVE` | İptal et | `REVOKED` | SA | Son yönetici değil | `ROLE_ASSIGNMENT_REVOKED` | Yetki tazelenir |
| `ACTIVE` | Süre dolar | `EXPIRED` | Sistem | `valid_to` geçti | `ROLE_ASSIGNMENT_REVOKED` | Kapsam çözümlemesinden düşer |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `REVOKED` | `ACTIVE` | İptal edilen atama yeniden canlandırılamaz; yeni atama gerekir |
| `EXPIRED` | `ACTIVE` | Süresi dolan atama yeniden canlandırılamaz |
| `ACTIVE` | `ACTIVE` | Aynı rol + aynı kapsam için çifte atama engellenir |

**Eşzamanlılık:** `OPT` + `ATOM`. Atama sırasında görev ayrılığı kontrolü
aynı transaction'da yapılır.

**İş akışı bağlantısı:** I → `D02.C02.W03.A01`.

---

### 2.4 ST-Session — Oturum

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Kur | `ACTIVE` | Kullanıcı | Hesap `ACTIVE`, kimlik kanıtı geçerli | `SESSION_ESTABLISHED` | Yetki bağlamı hazırlanır |
| `ACTIVE` | Sonlandır | `TERMINATED` | Sahip / SA | — | `SESSION_TERMINATED` | Belirteç geçersizleşir |
| `ACTIVE` | Süre dolar | `EXPIRED` | Sistem | `expires_at` geçti | `SESSION_TERMINATED` | — |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `TERMINATED` | `ACTIVE` | Sonlandırılan oturum canlandırılamaz |
| `EXPIRED` | `ACTIVE` | Süresi dolan oturum canlandırılamaz |
| `ACTIVE` | `ACTIVE` | Aynı kullanıcı için eşzamanlı oturum sayısı politika sınırına bağlı |

**Eşzamanlılık:** `OPT`. Oturum kurulumu sırasında kimlik doğrulama ve yetki
bağlamı atomik hazırlanır.

**İş akışı bağlantısı:** I → `D02.C03`.

---

### 2.5 ST-AccessReviewItem — Erişim gözden geçirme

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Kampanya başlat | `PENDING` | SA | Politika yürürlükte | `ACCESS_REVIEW_STARTED` | Onaylayıcılara bildirilir |
| `PENDING` | Onayla | `CERTIFIED` | DO (≠ atama sahibi) | — | `ACCESS_REVIEW_DECIDED` | — |
| `PENDING` | Kaldır | `REVOKED` | DO | — | `ACCESS_REVIEW_DECIDED` | Rol ataması iptal |
| `PENDING` | Süre dolar | `AUTO_REVOKED` | Sistem | Son tarih geçti | `ACCESS_REVIEW_DECIDED` | Politikaya göre iptal |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `CERTIFIED` | `REVOKED` | Onaylanmış kalem geri alınamaz; yeni kampanya gerekir |
| `PENDING` | `CERTIFIED` (kendi ataması) | Aktör kendi atamasını gözden geçiremez |
| `REVOKED` | `CERTIFIED` | Kaldırılmış kalem onaylanamaz |

**Eşzamanlılık:** `OPT` + `ATOM`. Karar anında rol atamasının geçerliliği
kontrol edilir.

**İş akışı bağlantısı:** I → `D02.C05.W01.A01`–`A02`.

---

## 3. D03 — Veri kaynağı ve bağlantı

### 3.1 ST-DataSource — Veri kaynağı

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Oluştur | `TEST_PENDING` | TS | Ad benzersiz | `DATA_SOURCE_CREATED` | — |
| `TEST_PENDING` | Test et (başarılı) | `TEST_SUCCEEDED` | TS | Sır bağlı | `CONNECTION_TESTED` | — |
| `TEST_PENDING` | Test et (başarısız) | `TEST_FAILED` | TS | — | `CONNECTION_TESTED` | — |
| `TEST_FAILED` | Yeniden test et | `TEST_SUCCEEDED` | TS | — | `CONNECTION_TESTED` | — |
| `TEST_SUCCEEDED` | Aktivasyon onaylanır | `ACTIVE` | DO (checker≠maker) | Test güncel revizyona ait | `DATA_SOURCE_ACTIVATION_DECIDED` | Çalıştırmaya açılır |
| `ACTIVE` | Pasifleştir | `INACTIVE` | DO / OP | — | `DATA_SOURCE_DEACTIVATED` | Yeni çalıştırma kabul edilmez |
| `INACTIVE` | Arşivle | `ARCHIVED` | DO | Aktif kural ve açık sorun yok | `DATA_SOURCE_ARCHIVED` | Bağlı dataset'ler arşivlenir |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `TEST_PENDING` | `ACTIVE` | Test geçmeden aktivasyon; SoD `BLOCK` |
| `TEST_FAILED` | `ACTIVE` | Başarısız testle aktivasyon engelli |
| `TEST_PENDING` | `ARCHIVED` | Test edilmeden arşivlenemez |
| `ACTIVE` | `ARCHIVED` | Doğrudan arşivlenemez; önce `INACTIVE` olmalı |
| `ARCHIVED` | Herhangi aktif | Arşiv donmuş; yeni kaynak gerekir |
| `INACTIVE` | `ACTIVE` | Yeniden aktivasyon maker-checker gerektirir; doğrudan geçiş yok |

**Eşzamanlılık:** `OPT` + `ATOM`. Aktivasyon kararı `approval_requests` ile
ortak onay tablosu üzerinden `PES` kilidi kullanır. Arşivleme sırasında bağlı
dataset'lerin cascade arşivlenmesi aynı transaction'da gerçekleşir.

**İş akışı bağlantısı:** A → `D03.C01.W01.A01`–`W03.A01`, `D03.C02.W01.A01`–`A02`.

---

### 3.2 ST-ConnectionRevision — Bağlantı revizyonu

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Revizyon oluştur | `DRAFT` | TS | Açık taslak yok | `CONNECTION_REVISION_CREATED` | — |
| `DRAFT` | Test et | `TESTED` | TS | — | `CONNECTION_TESTED` | — |
| `TESTED` | Yürürlüğe al | `EFFECTIVE` | TS / DO | — | `CONNECTION_REVISION_APPLIED` | Önceki `SUPERSEDED` |
| `EFFECTIVE` | Geri al | `ROLLED_BACK` | OP / TS | Hedef revizyon var | `CONNECTION_REVISION_ROLLED_BACK` | Hedef `EFFECTIVE` |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `DRAFT` | `EFFECTIVE` | Test edilmeden yürürlüğe alamaz |
| `TESTED` | `ROLLED_BACK` | Henüz yürürlükte olmayan revizyon geri alınamaz |
| `SUPERSEDED` | `EFFECTIVE` | Donmuş revizyon canlandırılamaz |

**Eşzamanlılık:** `OPT` + `ATOM`. Yürürlüğe alma anında önceki revizyonun
`SUPERSEDED` olması ve açık aktivasyon taleplerinin `EXPIRED` olması atomik
gerçekleşir.

**İş akışı bağlantısı:** A → `D03.C01.W02.A01`.

---

## 4. D04 — Metadata, katalog ve varlık

### 4.1 ST-Dataset — Dataset

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Keşiften oluştur | `ACTIVE` | Sistem / TS | Kimlik üçlüsü benzersiz | `DATASET_UPSERTED` | — |
| `ACTIVE` | Kaynakta bulunamadı | `SUSPECTED_REMOVED` | Sistem | Tam keşif sonucu | `METADATA_DIFF_APPLIED` | Ölçüm askıya alınır |
| `SUSPECTED_REMOVED` | Arşivle | `ARCHIVED` | TS | Aktif sözleşme yok | `DATASET_ARCHIVED` | Bağlı kurallar arşivlenir |
| `SUSPECTED_REMOVED` | Yeniden görüldü | `ACTIVE` | Sistem | — | `DATASET_UPSERTED` | Ölçüm sürer |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `ACTIVE` | `ARCHIVED` | Doğrudan arşivlenemez; önce `SUSPECTED_REMOVED` olmalı |
| `ARCHIVED` | `ACTIVE` | Arşiv donmuş; yeni keşif gerekir |
| `SUSPECTED_REMOVED` | `ACTIVE` (kullanıcı) | Yalnız sistem aktörü yeniden görebilir |

**Eşzamanlılık:** `OPT` + `IDEM`. Keşif fark uygulaması idempotency
anahtarıyla yinelenmez.

**İş akışı bağlantısı:** A, E → `D04.C02.W01.A01`.

---

### 4.2 ST-SchemaChange — Şema değişikliği

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Tespit et ve sınıflandır | `PENDING_DECISION` | Sistem | Fark hesaplandı | `SCHEMA_CHANGE_CLASSIFIED` | Kırıcıysa bildirilir |
| `PENDING_DECISION` | Kabul et | `ACCEPTED` | DO / TS | — | `SCHEMA_CHANGE_DECIDED` | Etkilenen kurallar `REVIEW_REQUIRED` |
| `PENDING_DECISION` | Blokla | `BLOCKED` | DO | — | `SCHEMA_CHANGE_DECIDED` | Ölçüm durdurulur |
| `PENDING_DECISION` | Süre dolar | `AUTO_BLOCKED` | Sistem | Politika süresi geçti | `SCHEMA_CHANGE_DECIDED` | Otomatik bloklama |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `ACCEPTED` | `BLOCKED` | Kabul edilen değişiklik geri alınamaz |
| `BLOCKED` | `ACCEPTED` | Bloklanan değişiklik onaylanamaz; yeni karar gerekir |
| `AUTO_BLOCKED` | `ACCEPTED` | Otomatik bloklama manuel kabul edilemez; yeniden sınıflandırma gerekir |

**Eşzamanlılık:** `OPT` + `ATOM`. Kabul anında etkilenen kuralların
`REVIEW_REQUIRED` olarak işaretlenmesi atomik.

**İş akışı bağlantısı:** E → `D04.C04.W01.A01`–`W02.A01`.

---

## 5. D05 — Profilleme ve drift

### 5.1 ST-Profile — Profil çalıştırması

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Talep et | `QUEUED` | DS / Sistem | Politika yürürlükte | `PROFILE_REQUESTED` | İş kuyruğa alınır |
| `QUEUED` | Başlat | `RUNNING` | Sistem | Kota ve pencere uygun | — | — |
| `RUNNING` | Tamamla | `SUCCESS` | Sistem | — | — | Metrikler kaydedilir |
| `RUNNING` | Kısmi tamamla | `PARTIAL` | Sistem | Alan bazlı hata | — | Baseline olamaz |
| `RUNNING` | Teknik hata | `TECHNICAL_ERROR` | Sistem | — | — | — |
| `QUEUED`\|`RUNNING` | İptal talep et | `CANCEL_REQUESTED` | OP / talep sahibi | — | `PROFILE_CANCELLED` | Sorgu sonlandırılır |
| `CANCEL_REQUESTED` | İptali tamamla | `CANCELLED` | Sistem | — | `PROFILE_CANCELLED` | — |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `QUEUED` | `SUCCESS` | Çalışmadan sonuç üretilemez |
| `RUNNING` | `QUEUED` | Geri dönüş yok; iptal veya tamamlanma gerekir |
| `TECHNICAL_ERROR` | `SUCCESS` | Hata sonrası sonuç yazılamaz |
| `PARTIAL` | `SUCCESS` | Kısmi sonuç tamama terfi edemez |
| `CANCELLED` | Herhangi aktif | İptal terminal |

**Eşzamanlılık:** `LEASE` tabanlı iptal. `CANCEL_REQUESTED` bayrağı
paylaşımlı; çalışan sorgu bayrağı periyodik kontrol eder.

**İş akışı bağlantısı:** A, E → `D05.C01.W01.A01`.

---

### 5.2 ST-ProfileBaseline — Profil baseline

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Baseline belirle | `ACTIVE` | DS / DO | Profil `SUCCESS` | `PROFILE_BASELINE_SET` | Önceki `SUPERSEDED` |
| `ACTIVE` | Yeni baseline atanır | `SUPERSEDED` | Sistem | — | `PROFILE_BASELINE_SET` | — |
| `ACTIVE` | Geçersiz kıl | `INVALIDATED` | DS / DO | — | `PROFILE_BASELINE_INVALIDATED` | Drift hükmü `NOT_QUALIFIED` |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `SUPERSEDED` | `ACTIVE` | Donmuş baseline canlandırılamaz |
| `INVALIDATED` | `ACTIVE` | Geçersiz kılınmış baseline canlandırılamaz |
| `ACTIVE` | `ACTIVE` (yeni) | Aynı anda tek baseline; yenisi eskisini `SUPERSEDED` yapar |

**Eşzamanlılık:** `OPT` + `ATOM`. Yeni baseline ataması öncekini aynı
transaction'da `SUPERSEDED` yapar.

**İş akışı bağlantısı:** A, F → `D05.C03.W01.A01`–`A02`.

---

## 6. D06 — Kural yönetimi

### 6.1 ST-RuleTemplate — Kural şablonu

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Tanımla | `DRAFT` | GA / RA | Kod benzersiz | `RULE_TEMPLATE_DRAFTED` | — |
| `DRAFT` | Yayımla | `PUBLISHED` | GA (≠ yazan) | Sınama başarılı | `RULE_TEMPLATE_PUBLISHED` | Kural üretiminde kullanılabilir |
| `PUBLISHED` | Kullanımdan kaldır | `DEPRECATED` | GA | — | `RULE_TEMPLATE_DEPRECATED` | Kritik hatada bağlı kurallar `REVIEW_REQUIRED` |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `DRAFT` | `DEPRECATED` | Yayımlanmadan kullanımdan kaldırılamaz |
| `DEPRECATED` | `PUBLISHED` | Kaldırılmış şablon geri getirilemez |
| `DRAFT` | `PUBLISHED` (yazan = yayımlayan) | SoD `BLOCK` — yazan yayımlayamaz |

**Eşzamanlılık:** `OPT`.

**İş akışı bağlantısı:** B → `D06.C01.W02.A01`.

---

### 6.2 ST-QualityRule — Kalite kuralı

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Oluştur | `DRAFT` | RA | Şablon `PUBLISHED` | `QUALITY_RULE_CREATED` | İlk sürüm `DRAFT` |
| `DRAFT` | Sürüm aktive edilir | `ACTIVE` | DS | Sürüm `APPROVED` | `RULE_VERSION_ACTIVATED` | Zamanlamalara dâhil |
| `ACTIVE` | Bağımlılık değişti | `REVIEW_REQUIRED` | Sistem | Alan tipi/şablon değişimi | `METADATA_DIFF_APPLIED` | Ölçüm sürer, uyarı |
| `REVIEW_REQUIRED` | Yeni sürüm aktive | `ACTIVE` | DS | — | `RULE_VERSION_ACTIVATED` | — |
| `ACTIVE`\|`REVIEW_REQUIRED` | Pasifleştir | `PASSIVE` | DS / DO | Kritikse SoD | `QUALITY_RULE_DEACTIVATED` | Zamanlamalardan çıkar |
| `PASSIVE` | Arşivle | `ARCHIVED` | DO | Açık sorun yok | `QUALITY_RULE_ARCHIVED` | Geçmiş korunur |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `DRAFT` | `PASSIVE` | Henüz aktif olmayan kural pasifleştirilemez |
| `DRAFT` | `ARCHIVED` | Önce pasif olmalı |
| `ARCHIVED` | `ACTIVE` | Arşiv donmuş |
| `ACTIVE` | `ARCHIVED` | Doğrudan arşivlenemez; önce `PASSIVE` |

**Eşzamanlılık:** `OPT` + `ATOM`.

**İş akışı bağlantısı:** B → `D06.C02.W01.A01`–`W05.A01`.

---

### 6.3 ST-RuleVersion — Kural sürümü

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Sürüm oluştur | `DRAFT` | RA | Açık taslak yok | `RULE_VERSION_CREATED` | — |
| `DRAFT` | Onaya gönder | `SEALED` → `PENDING_APPROVAL` | RA (maker) | Güncel başarılı test var | `RULE_APPROVAL_REQUESTED` | Tanım değişmez |
| `PENDING_APPROVAL` | Onayla | `APPROVED` | RP (checker≠maker) | — | `RULE_APPROVAL_DECIDED` | — |
| `PENDING_APPROVAL` | Reddet | `DRAFT` | RP | Gerekçe zorunlu | `RULE_APPROVAL_DECIDED` | — |
| `PENDING_APPROVAL` | Geri çek | `DRAFT` | RA (maker) | — | `RULE_APPROVAL_WITHDRAWN` | — |
| `PENDING_APPROVAL` | Süre dolar | `DRAFT` | Sistem | Son karar tarihi geçti | `RULE_APPROVAL_EXPIRED` | — |
| `APPROVED` | Aktive et | `ACTIVE` | DS | Dataset `ACTIVE` | `RULE_VERSION_ACTIVATED` | Önceki `SUPERSEDED` |
| `ACTIVE` | Yeni sürüm aktive | `SUPERSEDED` | Sistem | — | `RULE_VERSION_ACTIVATED` | Geçmiş korunur |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `DRAFT` | `APPROVED` | Onay adımı atlanamaz |
| `DRAFT` | `ACTIVE` | Onay ve aktivasyon zorunlu |
| `SEALED` | `DRAFT` | Mühürlendikten sonra maker dahi taslağa döndüremez; geri çekme gerekir |
| `PENDING_APPROVAL` | `ACTIVE` | Doğrudan aktive edilemez; önce `APPROVED` |
| `SUPERSEDED` | `ACTIVE` | Donmuş sürüm canlandırılamaz |
| `APPROVED` | `DRAFT` | Onaylanmış sürüm taslağa dönemez |

**Eşzamanlılık:** `OPT` + `ATOM` + `IDEM`. `SEALED` geçişi tanım alanını
değişmez kılar — sonraki düzenleme denemeleri `409` ile reddedilir. Aktivasyon
önceki sürümü aynı transaction'da `SUPERSEDED` yapar.

**İş akışı bağlantısı:** B → `D06.C02.W02.A02`–`W05.A01`.

---

### 6.4 ST-ApprovalRequest — Onay talebi (ortak)

Politika, kaynak aktivasyonu, kural sürümü, istisna ve sözleşme onaylarının
ortak davranışı.

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Talep aç | `PENDING` | Maker | Aynı nesne için açık talep yok | `*_REQUESTED` | Checker'lara bildirilir |
| `PENDING` | Onayla | `APPROVED` | Checker (≠ maker) | Nesne sürümü değişmemiş | `*_DECIDED` | Nesne durum geçişi |
| `PENDING` | Reddet | `REJECTED` | Checker | Gerekçe zorunlu | `*_DECIDED` | Nesne taslağa döner |
| `PENDING` | Geri çek | `WITHDRAWN` | Maker | — | `*_WITHDRAWN` | — |
| `PENDING` | Süre dolar | `EXPIRED` | Sistem | Son tarih geçti | `*_EXPIRED` | Nesne taslağa döner |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `PENDING` | `APPROVED` (maker = checker) | SoD `BLOCK` |
| `APPROVED` | `PENDING` | Karar geri alınamaz |
| `REJECTED` | `APPROVED` | Reddedilen talep onaylanamaz |
| `WITHDRAWN` | `APPROVED` | Geri çekilen talep onaylanamaz |
| `EXPIRED` | `APPROVED` | Süresi dolan talep onaylanamaz |

**Eşzamanlılık:** `PES` — `SELECT … FOR UPDATE` ile onay kilidi. Nesne
sürümünün değişmemesi `OPT` version kontrolüyle doğrulanır.

**Mevcut uygulama — "tamamen yok" değil, domain bazında kısmi.** Ortak/generic
bir `approval_requests` aggregate'i yoktur ve istisna, sözleşme, politika
onayları hiç yoktur. Buna karşılık iki domain için onay talebi zinciri
uçtan uca uygulanmıştır:

| Domain | Tablo | Servis kuralı | Test |
|---|---|---|---|
| Kural sürümü | `rule_approval_requests` (migration 02) | `RuleService.decide_rule_approval` maker = checker reddeder (`rules/service.py:542-545`); geri çekmede de farklı maker reddedilir | `test_rules.py:825`, `:933`, `:972`; `test_postgresql_rule_mutations.py` |
| Veri kaynağı aktivasyonu | `data_source_activation_requests` (migration 03) | `DataSourceService.decide_activation` maker = checker, checker rolü, süre, politika sürümü ve bayat revizyon denetler (`data_sources/service.py:461+`) | `test_data_sources.py:2205`, `:2469`, `:2502`, `:3255` |

Sorun onayı (`issues/service.py:646-649`) çözümü oluşturanın kendi çözümünü
doğrulamasını reddeder — ancak bu guard yalnız `QUALITY_PASSED` dalındadır
(`:638`); çözen aktör kendi çözümü için `QUALITY_FAILED`/`PARTIAL`/
`TECHNICAL_ERROR` doğrulaması **girebilir**.

**İki uyarı:**

1. **DB düzeyinde zorlama yok.** 14 migration'daki hiçbir `CheckConstraint`
   kolon-kolon karşılaştırması yapmaz; hepsi enum whitelist, sayısal sınır
   veya digest önekidir. maker ≠ checker güvencesi tamamen servis sınırına
   bağlıdır.
2. **Servis sınırı atlanabiliyor.** Çalıştırılabilir API veri kaynağı
   aktivasyonunda bu servisi hiç çağırmaz (GAP-027). Yani ST-DataSource için
   onay adımı, yasak geçişler tablosundaki "onay bypass" satırının tam
   karşılığı olarak **bugün gerçekleşebilir**.

**İş akışı bağlantısı:** B, C, G, K → birden fazla onay zinciri.

---

## 7. D07 — Yürütme, zamanlama ve kuyruk

### 7.1 ST-Schedule — Zamanlama

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Tanımla | `ACTIVE` | DS / OP | Kural sürümleri `ACTIVE` | `SCHEDULE_CREATED` | `next_run_at` hesaplanır |
| `ACTIVE` | Duraklat | `PAUSED` | OP / DS | — | `SCHEDULE_STATE_CHANGED` | Tetikleme durur |
| `PAUSED` | Sürdür | `ACTIVE` | OP / DS | — | `SCHEDULE_STATE_CHANGED` | `next_run_at` yeniden |
| `ACTIVE`\|`PAUSED` | Sil | `DELETED` | DS | Devam eden çalıştırma yok | `SCHEDULE_DELETED` | Geçmiş bağı korunur |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `DELETED` | `ACTIVE` | Silinen zamanlama canlandırılamaz |
| `ACTIVE` | `ACTIVE` (çift tetikleme) | Aynı `next_run_at` için idempotency |

**Eşzamanlılık:** `IDEM` + `PES`. Çok zamanlayıcılı ortamda aynı vade için
`SELECT … FOR UPDATE SKIP LOCKED` ile tek kazanan.

**Mevcut uygulama farkı.** `ACTIVE` durumu `SchedulingService` ve
`schedules.is_active` ile karşılanır; `PAUSED` ve `DELETED` durumları,
dolayısıyla duraklat/sürdür/sil geçişleri **yoktur** (`schedules` tablosunda
`status`/`deleted_at`/`paused_until` kolonu yok — GAP-003). Tanımlama ve
tetikleme geçişleri servis düzeyinde uygulanmış ve test edilmiştir
(`executions/scheduling.py:234,303`); idempotency
`schedule:{id}:{scheduled_for}` anahtarıyla aşağı akışta sağlanır. Buna
karşılık `PostgreSQLScheduleRepository.due` (`postgresql_scheduling.py:109-124`)
düz bir `SELECT`'tir — bu tablodaki `FOR UPDATE SKIP LOCKED` gerekliliği
**karşılanmamıştır**; çok zamanlayıcılı tek kazanan garantisi bugün yoktur.

**İş akışı bağlantısı:** B → `D07.C02.W01.A01`–`W02.A02`.

---

### 7.2 ST-Job — Kalıcı iş

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Kuyruğa al | `AVAILABLE` | Sistem | İşleyici kayıtlı | `JOB_ENQUEUED` | Atomik |
| `AVAILABLE` | Sahiplen | `CLAIMED` | Worker | Kota ve pencere uygun | `JOB_CLAIMED` | Lease verilir |
| `CLAIMED` | Yürüt | `RUNNING` | Worker | — | — | Heartbeat başlar |
| `RUNNING` | Tamamla | `COMPLETED` | Worker | — | — | Sonuç yazılır |
| `RUNNING` | Geçici hata | `AVAILABLE` | Sistem | Deneme sınırı aşılmadı | `JOB_RETRY_SCHEDULED` | Üstel geri çekilme |
| `RUNNING` | Lease süresi dolar | `AVAILABLE` | Sistem (kurtarma) | — | `JOB_LEASE_RECLAIMED` | Eski worker sonuç yazamaz |
| `RUNNING`\|`AVAILABLE` | Sınır aşıldı | `DEAD_LETTERED` | Sistem | — | `JOB_DEAD_LETTERED` | DL kaydı açılır |
| `AVAILABLE`\|`CLAIMED`\|`RUNNING` | İptal et | `CANCELLED` | OP / Sistem | — | `JOB_MANUALLY_INTERVENED` | Kaynak nesne bilgilendirilir |
| `CLAIMED` | Kota/pencere uygun değil | `AVAILABLE` | Sistem | — | `SOURCE_QUOTA_THROTTLED` | `available_at` ertelenir |
| `CLAIMED` | İzinli pencere yok | `BLOCKED` | Sistem | — | `SOURCE_WINDOW_DEFERRED` | Operatöre görünür |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `COMPLETED` | `AVAILABLE` | Tamamlanan iş yeniden kuyruklanamaz |
| `CANCELLED` | `AVAILABLE` | İptal edilen iş canlandırılamaz |
| `DEAD_LETTERED` | `COMPLETED` | Dead-letter'a taşınan iş doğrudan tamamlanamaz; yeniden işleme gerekir |
| `CLAIMED` | `COMPLETED` (lease süresi dolmuş) | Lease'si dolmuş worker sonuç yazamaz |
| `RUNNING` | `CLAIMED` | Geri dönüş yok |

**Eşzamanlılık:** `PES` + `LEASE`. Sahiplenme `FOR UPDATE SKIP LOCKED`; lease
süresi `leased_until` kolonunda; heartbeat ile uzatılır. Lease kaybında eski
worker'ın sonuç yazma denemesi `version` kontrolüyle reddedilir.

**Mevcut uygulama farkı — durum adları ve claim audit'i.** Yukarıdaki tablo
hedef modeldir; uygulama bununla birebir örtüşmez ve fark yalnız adlandırma
değildir:

| Hedef | Uygulama (`jobs/models.py:20-27`) |
|---|---|
| `AVAILABLE` | `QUEUED` |
| `CLAIMED` + `RUNNING` (iki ayrı durum) | Tek durum: `RUNNING` — `claim_next` `QUEUED` satırını **doğrudan** `RUNNING` yapar |
| `DEAD_LETTERED` | Ayrı enum: `DeadLetterStatus` (`OPEN`/`REPROCESSED`) |
| `BLOCKED` (pencere ertelemesi) | Karşılığı yok |
| `COMPLETED` | `SUCCESS` (ayrıca `TECHNICAL_ERROR`, `TIMEOUT`, `CANCELLED`, `CANCEL_REQUESTED`) |

`PostgreSQLJobQueueRepository.claim_next` (`jobs/postgresql_repository.py:271`)
`FOR UPDATE SKIP LOCKED` (`:354`), lease (`:297,384`), kota (`:301-332`) ve
optimistic `version` guard'ını (`:378`) gerçekten uygular. Ancak imzasında
audit/outbox parametresi **yoktur** ve gövdesi `audit_outbox.stage` çağırmaz —
oysa aynı dosyadaki `release_expired_claims` outbox alır. Sonuç: tablodaki
"`AVAILABLE` → `CLAIMED`, audit `JOB_CLAIMED`" satırının audit yarısı
**kodda mevcut değildir**. Sahiplenme sessizce gerçekleşir; bu, GAP-002'nin
"backend tamam, yalnız entrypoint eksik" biçiminde okunmasını geçersiz kılar.

**İş akışı bağlantısı:** D → `D07.C03`–`C04`.

---

### 7.3 ST-DeadLetterRecord — Dead-letter kaydı

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Oluştur | `OPEN` | Sistem | İş `DEAD_LETTERED` | `JOB_DEAD_LETTERED` | Operatöre bildirilir |
| `OPEN` | Yeniden işle | `REPROCESSED` | OP | Politika ve rol uygun | `DEAD_LETTER_REPROCESSED` | Yeni iş kuyruğa alınır |
| `OPEN` | Kapat | `CLOSED` | OP | Gerekçe zorunlu | `DEAD_LETTER_CLOSED` | Ölçüm boşluğu işaretlenir |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `CLOSED` | `OPEN` | Kapatılan kayıt yeniden açılamaz |
| `REPROCESSED` | `OPEN` | Yeniden işlenen kayıt geri alınamaz |
| `OPEN` | `REPROCESSED` (aynı anda) | Aynı kayıt için çifte yeniden işleme engellenir |

**Eşzamanlılık:** `OPT` + `IDEM`. Yeniden işleme idempotency anahtarıyla
yeni iş kaydını atomik oluşturur.

**İş akışı bağlantısı:** D → `D07.C04.W04.A02`–`A04`.

---

### 7.4 ST-RuleExecution — Çalıştırma

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Başlat | `QUEUED` | DS / OP / Sistem | Kural ve kaynak `ACTIVE` | `EXECUTION_STARTED` | Plan üretilir |
| `QUEUED` | Yürütmeye geç | `RUNNING` | Sistem | İş sahiplenildi | — | — |
| `RUNNING` | Tamamla | `SUCCESS` | Sistem | Tüm kurallar tamamlandı | `RULE_RESULT_RECORDED` | Skor tetiklenir |
| `RUNNING` | Kısmi tamamla | `PARTIAL` | Sistem | Bazı bölüm/kural başarısız | `RULE_RESULT_RECORDED` | Yeterlilik düşer |
| `RUNNING` | Teknik hata | `TECHNICAL_ERROR` | Sistem | — | `EXECUTION_TECHNICAL_ERROR` | Skor üretilmez |
| `RUNNING` | Zaman aşımı | `TIMEOUT` | Sistem | Sınır aşıldı | `EXECUTION_TIMED_OUT` | Yeniden deneme |
| `QUEUED`\|`RUNNING` | İptal talep et | `CANCEL_REQUESTED` | OP / başlatan | — | `EXECUTION_CANCEL_REQUESTED` | İşlere sinyal |
| `CANCEL_REQUESTED` | İptali tamamla | `CANCELLED` | Sistem | — | `EXECUTION_CANCELLED` | Kısmi sonuç dışlanır |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `QUEUED` | `SUCCESS` | Çalışmadan sonuç üretilemez |
| `TECHNICAL_ERROR` | `SUCCESS` | Hata sonrası başarı yazılamaz |
| `TIMEOUT` | `SUCCESS` | Zaman aşımı sonrası başarı yazılamaz |
| `CANCELLED` | `SUCCESS` | İptal sonrası sonuç yazılamaz |
| `SUCCESS` | `RUNNING` | Tamamlanan çalıştırma geri alınamaz |
| `PARTIAL` | `SUCCESS` | Kısmi sonuç terfi edemez |

**Eşzamanlılık:** `LEASE` tabanlı iptal + `ATOM` sonuç yazımı.

**İş akışı bağlantısı:** B, D → `D07.C01.W01.A01`.

---

## 8. D08 — Ölçüm ve skorlama

### 8.1 ST-QualityScore — Kalite skoru

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Hesapla | `CALCULATED` | Sistem | Yeterlilik uygun | `RULE_SCORE_CALCULATED` | Katkı bileşenleri kaydedilir |
| `—` | Yetersiz ölçüm | `NOT_QUALIFIED` | Sistem | Yeterlilik `NOT_QUALIFIED` | `MEASUREMENT_QUALIFICATION_ISSUED` | Değer üretilmez |
| `—` | Uygun kural yok | `NO_DATA` | Sistem | Bileşen yok | `SCORE_AGGREGATED` | — |
| `CALCULATED` | Yayımla | `PUBLISHED` | Sistem | Tüm seviyeler hesaplandı | `SCORE_PUBLISHED` | Atomik; önceki `SUPERSEDED` |
| `PUBLISHED` | Yeni yayım | `SUPERSEDED` | Sistem | — | `SCORE_PUBLISHED` | Geçmiş korunur |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `NOT_QUALIFIED` | `PUBLISHED` | Yetersiz ölçüm yayımlanamaz |
| `NO_DATA` | `PUBLISHED` | Veri olmadan yayım yapılamaz |
| `CALCULATED` | `SUPERSEDED` | Yayımlanmadan eskiyenemez |
| `SUPERSEDED` | `PUBLISHED` | Donmuş skor canlandırılamaz |

**Eşzamanlılık:** `SER` + `ATOM`. Yayımlama **seri yalıtım** seviyesinde
atomik olarak gerçekleşir — tüm seviyeler (kural, dataset, domain, kurum) aynı
transaction'da hesaplanıp yayımlanır. Önceki yayım `SUPERSEDED` olur.

**İş akışı bağlantısı:** F → `D08.C03.W03.A01`.

---

## 9. D09 — Sorun, istisna ve düzeltme

### 9.1 ST-Issue — Sorun

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Aç | `NEW` | Sistem / DS | Yeterlilik uygun; istisna kapsamında değil | `ISSUE_CREATED` | SLA hedefleri, bildirim |
| `NEW` | Ata | `ASSIGNED` | DS / DO | Aday yeterli | `ISSUE_ASSIGNED` | Atanana bildirim |
| `NEW`\|`ASSIGNED` | İnceleme başlat | `INVESTIGATING` | IA | Aktör atanan | `ISSUE_INVESTIGATION_STARTED` | İlk yanıt SLA |
| `INVESTIGATING` | Bekletmeye al | `WAITING_FOR_RESOLUTION` | IA | Gerekçe ve tarih | `ISSUE_PUT_ON_HOLD` | SLA duraklatılır |
| `INVESTIGATING`\|`WAITING_FOR_RESOLUTION` | Çözümü kaydet | `RESOLVED` | IA | Kök neden ve aksiyon dolu | `ISSUE_RESOLVED` | Doğrulayıcıya bildirim |
| `RESOLVED` | Doğrula (başarılı) | `VERIFIED` | IV (≠ çözen) | Bağımsız kanıt | `ISSUE_VERIFIED` | — |
| `RESOLVED` | Doğrula (başarısız) | `INVESTIGATING` | IV | — | `ISSUE_VERIFIED` | Atanana geri döner |
| `VERIFIED` | Kapat | `CLOSED` | IV / DO | — | `ISSUE_CLOSED` | SLA durdurulur |
| herhangi açık | İptal et | `CANCELLED` | DO | Gerekçe zorunlu | `ISSUE_CLOSED` | Yeniden açılamaz |
| `CLOSED` | Aynı bozulma tekrarlar | `NEW` | Sistem / DS | Yeniden açma penceresi | `ISSUE_REOPENED` | `RECURRENCE` ilişkisi |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `NEW` | `RESOLVED` | İnceleme adımı atlanamaz |
| `NEW` | `VERIFIED` | Çözüm ve doğrulama atlanamaz |
| `INVESTIGATING` | `CLOSED` | Doğrulama adımı atlanamaz |
| `RESOLVED` | `CLOSED` | Doğrulama adımı atlanamaz |
| `RESOLVED` | `VERIFIED` (çözen = doğrulayan) | SoD `BLOCK` |
| `CANCELLED` | `NEW` | İptal edilen sorun yeniden açılamaz |
| `VERIFIED` | `INVESTIGATING` | Doğrulanmış sorun geri alınamaz |
| `CLOSED` | `INVESTIGATING` | Kapatılan sorun doğrudan incelemeye dönemez |

**Eşzamanlılık:** `OPT` + `ATOM`. Çözüm kaydı kök neden ve aksiyonla birlikte
atomik yazılır. Doğrulama sırasında çözen ≠ doğrulayan kontrolü `OPT` version
ile yapılır.

**İş akışı bağlantısı:** C → `D09.C01`–`C02`.

---

### 9.2 ST-Exception — İstisna

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Talep et | `PENDING` | DO / DS (maker) | Bitiş tarihi zorunlu | `EXCEPTION_REQUESTED` | Onaylayıcıya bildirim |
| `PENDING` | Onayla | `ACTIVE` | GA / DO (≠ maker) | — | `EXCEPTION_DECIDED` | Sorun bastırılır, kalite borcu |
| `PENDING` | Reddet | `REJECTED` | Checker | Gerekçe zorunlu | `EXCEPTION_DECIDED` | — |
| `ACTIVE` | Süre dolar | `EXPIRED` | Sistem | `valid_until` geçti | `EXCEPTION_EXPIRED` | Bastırma kalkar |
| `ACTIVE` | Erken iptal | `REVOKED` | GA / onaylayan | Gerekçe zorunlu | `EXCEPTION_REVOKED` | Bastırma kalkar |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `PENDING` | `ACTIVE` (maker = checker) | SoD `BLOCK` |
| `REJECTED` | `ACTIVE` | Reddedilen istisna aktif edilemez |
| `EXPIRED` | `ACTIVE` | Süresi dolan istisna canlandırılamaz |
| `REVOKED` | `ACTIVE` | İptal edilen istisna canlandırılamaz |
| `ACTIVE` | `REJECTED` | Aktif istisna reddedilemez |

**Eşzamanlılık:** `OPT` + `ATOM`. Onay anında kalite borcu kaydı aynı
transaction'da oluşur.

**İş akışı bağlantısı:** G → `D09.C04.W01.A01`–`W03.A02`.

---

### 9.3 ST-RemediationAction — Düzeltme aksiyonu

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Oluştur | `PLANNED` | IA / DO | Hedef tarih zorunlu | `REMEDIATION_ACTION_CREATED` | Sahibe bildirim |
| `PLANNED` | Başlat | `IN_PROGRESS` | Aksiyon sahibi | — | — | — |
| `IN_PROGRESS` | Tamamla | `COMPLETED` | Aksiyon sahibi / Sistem | Kanıt referansı zorunlu | `REMEDIATION_ACTION_COMPLETED` | Etki ölçümü tetiklenir |
| `IN_PROGRESS` | Otomatik yürütme başarısız | `FAILED` | Sistem | — | `REMEDIATION_AUTO_EXECUTED` | Sahibe bildirim |
| `PLANNED`\|`IN_PROGRESS` | İptal et | `CANCELLED` | Aksiyon sahibi | Gerekçe zorunlu | — | — |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `PLANNED` | `COMPLETED` | Başlatmadan tamamlanamaz |
| `COMPLETED` | `IN_PROGRESS` | Tamamlanan aksiyon geri alınamaz |
| `FAILED` | `COMPLETED` | Başarısız aksiyon tamamlandı olarak işaretlenemez |
| `CANCELLED` | `PLANNED` | İptal edilen aksiyon canlandırılamaz |

**Eşzamanlılık:** `OPT`.

**İş akışı bağlantısı:** C → `D09.C06.W01.A01`–`A02`.

---

## 10. D10 — Lineage, etki ve sözleşme

### 10.1 ST-DataContract — Veri sözleşmesi

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Taslak oluştur | `DRAFT` | Üretici DO | Taahhütler ölçülebilir | `DATA_CONTRACT_DRAFTED` | — |
| `DRAFT` | Onaya sun | `PENDING_ACCEPTANCE` | Üretici DO | — | `DATA_CONTRACT_ACCEPTED` | Taraflara bildirim |
| `PENDING_ACCEPTANCE` | Her iki taraf onaylar | `ACTIVE` | Üretici + tüketici DO | İkisi de onayladı | `DATA_CONTRACT_ACCEPTED` | İzleme kuralları bağlanır |
| `PENDING_ACCEPTANCE` | Karşı teklif | `DRAFT` | Tüketici DO | — | — | — |
| `ACTIVE` | İhlal eşiği aşılır | `BREACHED` | Sistem | Yeterlilik uygun, tolerans aşıldı | `DATA_CONTRACT_BREACHED` | Sorun açılır |
| `BREACHED` | Ardışık uyum | `ACTIVE` | Sistem / DO | Geri kazanım penceresi | `DATA_CONTRACT_RECOVERED` | İhlal kaydı kapanır |
| `ACTIVE`\|`BREACHED` | Sonlandır | `TERMINATED` | Her iki taraf DO | — | `DATA_CONTRACT_TERMINATED` | İzleme kuralları serbest |
| `ACTIVE` | Yeni sürüm | `SUPERSEDED` | Sistem | — | `DATA_CONTRACT_ACCEPTED` | — |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `DRAFT` | `ACTIVE` | Kabul adımı atlanamaz |
| `PENDING_ACCEPTANCE` | `ACTIVE` (tek taraf) | İki taraf onayı zorunlu |
| `PENDING_ACCEPTANCE` | `ACTIVE` (aynı aktör her iki taraf) | Sözleşmenin iki tarafını aynı aktör onaylayamaz |
| `TERMINATED` | `ACTIVE` | Sonlandırılan sözleşme canlandırılamaz |
| `SUPERSEDED` | `ACTIVE` | Donmuş sözleşme canlandırılamaz |
| `BREACHED` | `TERMINATED` | İhlal状态下 sonlandırılabilir ama ihlal kaydı önce kapatılmalı |

**Eşzamanlılık:** `OPT` + `ATOM` + `PES`. İki taraf onayı `PES` kilidiyle
eşzamanlılık kontrolü; her iki tarafın da `PENDING_ACCEPTANCE`'ta olması
atomik doğrulanır.

**İş akışı bağlantısı:** K → `D10.C03.W01.A01`–`W03.A02`.

---

## 11. D11–D15 ve ortak durum makineleri

### 11.1 ST-ReportJob — Rapor

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Talep et | `PENDING` | RC / DO | Hassasiyet çözümlendi | `REPORT_REQUESTED` | Üretim işi kuyruğa |
| `PENDING` | Üretmeye başla | `GENERATING` | Sistem | İş sahiplenildi | — | — |
| `GENERATING` | Tamamla | `READY` | Sistem | — | `REPORT_GENERATED` | Talep edene bildirim |
| `GENERATING` | Başarısız | `FAILED` | Sistem | — | — | Yeniden denenir |
| `PENDING`\|`GENERATING` | İptal et | `CANCELLED` | Talep eden / OP | — | `REPORT_CANCELLED` | Kısmi dosya silinir |
| `READY` | Saklama süresi dolar | `EXPIRED` | Sistem | Yasal muhafaza yok | `REPORT_FILE_DESTROYED` | Dosya imha |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `PENDING` | `READY` | Üretim atlanamaz |
| `FAILED` | `READY` | Başarısız üretim hazır olarak işaretlenemez |
| `CANCELLED` | `READY` | İptal sonrası dosya üretilemez |
| `EXPIRED` | `READY` | İmha edilen rapor canlandırılamaz |

**Eşzamanlılık:** `LEASE` tabanlı üretim + `ATOM` dosya imhası.

**İş akışı bağlantısı:** H → `D11.C03.W01.A01`–`W02.A01`.

---

### 11.2 ST-NotificationDelivery — Bildirim teslimatı

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Teslimat oluştur | `PENDING` | Sistem | Abonelik eşleşti | `NOTIFICATION_EVENT_PUBLISHED` | — |
| `PENDING` | Gönder | `SENDING` | Sistem | Kanal `ACTIVE` | — | — |
| `SENDING` | Başarılı | `DELIVERED` | Sistem | — | `NOTIFICATION_DELIVERY_ATTEMPTED` | — |
| `SENDING` | Geçici hata | `FAILED` | Sistem | Deneme sınırı aşılmadı | `NOTIFICATION_DELIVERY_ATTEMPTED` | Yeniden denenir |
| `FAILED` | Sınır aşıldı | `UNDELIVERABLE` | Sistem | — | `NOTIFICATION_UNDELIVERABLE` | Operatöre bildirim |
| `UNDELIVERABLE` | Alternatif kanal | `REROUTED` | Sistem / OP | Alternatif kanal var | `NOTIFICATION_UNDELIVERABLE` | — |
| `DELIVERED` | Okundu | `READ` | Alıcı | — | — | Sayaç güncellenir |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `PENDING` | `DELIVERED` | Gönderim adımı atlanamaz |
| `DELIVERED` | `FAILED` | Teslim edilmiş bildirim başarısız sayılamaz |
| `UNDELIVERABLE` | `DELIVERED` | Teslim edilemez durumundan teslim edildi sayılamaz |
| `READ` | `FAILED` | Okundu işaretlendikten sonra başarısız sayılamaz |

**Eşzamanlılık:** `OPT` + `IDEM`. Teslimat denemesi idempotency anahtarıyla
yinelenmez.

**İş akışı bağlantısı:** M → `D12.C02.W01.A01`–`W02.A02`.

---

### 11.3 ST-IntegrationRecord — Entegrasyon kaydı

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Gönderim hazırla | `PENDING` | Sistem | Eşleme kuralı eşleşti | — | — |
| `PENDING` | Gönder | `SENT` | Sistem / IA | Entegrasyon `ACTIVE` | `INTEGRATION_RECORD_SENT` | Dış kimlik ilişkilendirilir |
| `PENDING` | Kalıcı hata | `FAILED` | Sistem | Deneme sınırı aşıldı | `INTEGRATION_RECORD_SENT` | Operatöre bildirim |
| `SENT` | Güncelle | `UPDATED` | Sistem | Sorun değişti | `INTEGRATION_RECORD_UPDATED` | — |
| `SENT`\|`UPDATED` | Dış kayıt yok | `ORPHANED` | Sistem | — | `INTEGRATION_RECORD_UPDATED` | İlişki koparılır |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `FAILED` | `SENT` | Başarısız kayıt gönderildi sayılamaz |
| `ORPHANED` | `SENT` | Yetim kayıt doğrudan gönderilemez |

**Eşzamanlılık:** `IDEM` + `OPT`.

**İş akışı bağlantısı:** M → `D12.C03.W01.A01`.

---

### 11.4 ST-LegalHold — Yasal muhafaza

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Uygula | `ACTIVE` | GA / AU | Gerekçe zorunlu | `LEGAL_HOLD_APPLIED` | Kapsam imha dışı |
| `ACTIVE` | Kaldır | `RELEASED` | Uygulayan / GA | Gerekçe zorunlu | `LEGAL_HOLD_RELEASED` | Süresi geçmişler imha kuyruğuna |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `RELEASED` | `ACTIVE` | Kaldırılan muhafaza canlandırılamaz; yeni muhafaza gerekir |

**Eşzamanlılık:** `ATOM`. Uygulama ve kaldırma audit ile atomik.

**İş akışı bağlantısı:** J → `D13.C05.W01.A01`–`A02`.

---

### 11.5 ST-OperationalIncident — Operasyonel olay

**Geçerli geçişler:**

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|
| `—` | Aç | `OPEN` | OP / Sistem | Şiddet tanımlı | `OPERATIONAL_INCIDENT_OPENED` | Sorumlu atanır |
| `OPEN` | Azaltma | `MITIGATED` | Olay sorumlusu | — | `OPERATIONAL_INCIDENT_UPDATED` | — |
| `MITIGATED` | Kapat | `CLOSED` | Olay sorumlusu | Kök neden kaydedildi | `OPERATIONAL_INCIDENT_CLOSED` | İzleme aksiyonları |

**Yasak geçişler:**

| Başlangıç | Hedef | Neden |
|---|---|---|
| `OPEN` | `CLOSED` | Azaltma adımı atlanamaz; kök neden kaydı zorunlu |
| `CLOSED` | `OPEN` | Kapatılan olay canlandırılamaz |
| `MITIGATED` | `OPEN` | Geri dönüş yok |

**Eşzamanlılık:** `OPT`.

**İş akışı bağlantısı:** D → `D14.C03.W01.A01`–`A02`.

---

## 12. Yasak geçiş özet matrisi

Aşağıdaki matris, tüm durum makinelerinde **ortak yasak kalıplarını** gösterir:

| Kalıp | Açıklama | İlgili ST'ler |
|---|---|---|
| **Onay adımı atlama** | `DRAFT/PENDING` → `APPROVED/ACTIVE/EFFECTIVE` (onay bypass) | ST-Policy, ST-RuleVersion, ST-ApprovalRequest, ST-DataSource, ST-Exception, ST-DataContract |
| **SoD ihlali** | maker = checker aynı aktör | ST-Policy, ST-RuleVersion, ST-ApprovalRequest, ST-DataSource, ST-Exception, ST-Issue (çözen=doğrulayan), ST-DataContract (iki taraf) |
| **Terminal'den dönüş** | `ARCHIVED/CANCELLED/TERMINATED/RELEASED/SUPERSEDED` → herhangi aktif | Tüm ST'ler |
| **Sonuç atlaması** | `RUNNING/QUEUED` → `SUCCESS` (çalışmadan sonuç) | ST-Profile, ST-RuleExecution, ST-ReportJob |
| **Lease ihlali** | Lease'si dolmuş worker sonuç yazar | ST-Job |
| **Doğrudan arşiv** | `ACTIVE` → `ARCHIVED` (pasif adımı atlanarak) | ST-DataSource, ST-Dataset, ST-QualityRule |
| **Kendi atamasını gözden geçirme** | Aktör kendi erişim gözden geçirmesini onaylar | ST-AccessReviewItem |
| **Sözleşme tek taraf** | Aynı aktör her iki tarafı onaylar | ST-DataContract |

---

## 13. Eşzamanlılık özet tablosu

| ST | Birincil model | İkincil model | Kritik transaction |
|---|---|---|---|
| ST-Policy | OPT | SER (yürürlüğe alma) | Aralık çakışması + önceki `SUPERSEDED` |
| ST-User | OPT | ATOM | Oturum sonlandırma + rol iptali |
| ST-RoleAssignment | OPT | ATOM | SoD kontrolü |
| ST-Session | OPT | — | — |
| ST-AccessReviewItem | OPT | ATOM | Rol ataması iptali |
| ST-DataSource | OPT | ATOM + PES (onay) | Aktivasyon kararı + bağlı dataset cascade |
| ST-ConnectionRevision | OPT | ATOM | Önceki `SUPERSEDED` + açık talepler `EXPIRED` |
| ST-Dataset | OPT | IDEM | Keşif fark uygulaması |
| ST-SchemaChange | OPT | ATOM | Etkilenen kurallar `REVIEW_REQUIRED` |
| ST-Profile | LEASE | — | İptal bayrağı |
| ST-ProfileBaseline | OPT | ATOM | Önceki `SUPERSEDED` |
| ST-RuleTemplate | OPT | — | — |
| ST-QualityRule | OPT | ATOM | — |
| ST-RuleVersion | OPT | ATOM + IDEM | `SEALED` + önceki `SUPERSEDED` |
| ST-ApprovalRequest | PES | OPT | Onay kilidi + nesne sürümü |
| ST-Schedule | PES | IDEM | Çok zamanlayıcılı tek kazanan |
| ST-Job | PES | LEASE | `FOR UPDATE SKIP LOCKED` + lease |
| ST-DeadLetterRecord | OPT | IDEM | Yeniden işleme |
| ST-RuleExecution | LEASE | ATOM | Sonuç yazımı |
| ST-QualityScore | SER | ATOM | Atomik yayım + önceki `SUPERSEDED` |
| ST-Issue | OPT | ATOM | Çözüm + doğrulama SoD |
| ST-Exception | OPT | ATOM | Kalite borcu oluşturma |
| ST-RemediationAction | OPT | — | — |
| ST-DataContract | OPT + PES | ATOM | İki taraf onayı |
| ST-ReportJob | LEASE | ATOM | Dosya imhası |
| ST-NotificationDelivery | OPT | IDEM | Teslimat denemesi |
| ST-IntegrationRecord | OPT | IDEM | — |
| ST-LegalHold | ATOM | — | — |
| ST-OperationalIncident | OPT | — | — |

---

## 14. Mevcut durum ve GAP ilişkisi

| ST | Mevcut kod | Runtime | İlgili GAP |
|---|---|---|---|
| ST-Policy | ❌ Yok | — | GAP-026 |
| ST-User | ❌ Yok | — | GAP-022 |
| ST-RoleAssignment | ❌ Yok | — | GAP-022 |
| ST-Session | ⚠️ `development.py` | Mock | GAP-022 |
| ST-AccessReviewItem | ❌ Yok | — | GAP-022 |
| ST-DataSource | ✅ Kod ekseni | **Onay adımı bypass ediliyor** | GAP-001, GAP-027 |
| ST-ConnectionRevision | ✅ Kod ekseni | PG testli | GAP-001 |
| ST-Dataset | ⚠️ Servis + migration var | Yüzey yok | GAP-004 |
| ST-SchemaChange | ❌ Yok | — | GAP-019 |
| ST-Profile | ✅ Yürütücü var (`run_profile`) | Talep yüzeyi yok | GAP-005 |
| ST-ProfileBaseline | ❌ Yok | — | GAP-005 |
| ST-RuleTemplate | ❌ Yok | — | GAP-020 |
| ST-QualityRule | ✅ Kod ekseni | PG testli | GAP-001 |
| ST-RuleVersion | ✅ Kod ekseni | PG testli | GAP-001 |
| ST-ApprovalRequest | ⚠️ Domain bazında (kural, kaynak) | Kaynak onayı bypass ediliyor | GAP-022, GAP-027 |
| ST-Schedule | ⚠️ Servis + repository var | Çağıran yok; `PAUSED`/`DELETED` yok | GAP-003 |
| ST-Job | ⚠️ Kod ekseni (claim audit'i yok) | dequeue yok | GAP-002 |
| ST-DeadLetterRecord | ✅ Kod ekseni | Runtime yok | GAP-002 |
| ST-RuleExecution | ✅ Kod ekseni | PG testli | GAP-001 |
| ST-QualityScore | ⚠️ Bellek içi | PG yok | GAP-008 |
| ST-Issue | ✅ Kod ekseni (üretici dâhil) | Üretici çağrılmıyor | GAP-001, GAP-006 |
| ST-Exception | ❌ Yok | — | GAP-009 |
| ST-RemediationAction | ❌ Yok | — | GAP-009 |
| ST-DataContract | ❌ Yok | — | GAP-010 |
| ST-ReportJob | ⚠️ Kısmi | Asenkron yok | GAP-016 |
| ST-NotificationDelivery | ⚠️ Servis var | Bağlı değil | GAP-007 |
| ST-IntegrationRecord | ⚠️ Servis var | Yüzey yok | GAP-023 |
| ST-LegalHold | ⚠️ Kod var | Migration kısmi | GAP-011 |
| ST-OperationalIncident | ❌ Yok | — | GAP-024 |

> **Özet:** 29 durum makinesinden 7'si kod ekseninde eksiksiz, 11'i kısmi,
> 11'i tamamen eksik. Runtime'da tam çalışan **sıfır** durum makinesi var.

**"Kod ekseni ✅" ne demek değildir.** Bu sütun geçişlerin bir servis
tarafından uygulandığını söyler; o servisin çalıştırılabilir yoldan
**çağrıldığını** söylemez. İki ayrı kırılma tipi vardır ve karıştırılmamalıdır:

| Kırılma tipi | Durum makineleri | Sonuç |
|---|---|---|
| Servis var, çağıran yok | ST-Schedule, ST-Profile, ST-Issue (üretici), ST-Dataset | Geçiş hiç gerçekleşmez |
| Servis var, **atlanıyor** | ST-DataSource, ST-ApprovalRequest (kaynak kolu) | Geçiş **kuralsız** gerçekleşir |

İkincisi daha ağırdır: `TEST_SUCCEEDED -> ACTIVE` geçişi maker/checker, rol,
kapsam ve audit olmadan tamamlanır (GAP-027). §12'deki "onay adımı atlama"
yasak geçişi bu yolla bugün ihlal edilebilir durumdadır.

GAP-001 (bileşim kökü) tek başına çözüldüğünde bu ikinci grup **kapanmaz**;
komut port'larının aktör bağlamı taşıması ayrıca gerekir.

---

## 15. Kanıt sınırları

- Durum makinesi geçişleri `02-Target-Capability-Hierarchy.md` §6.1'den
  alınmıştır; değişiklik yapılmamıştır.
- Yasak geçişler bu belgenin çıkarımıdır; hedef modelde açıkça listelenmemiştir
  ancak geçiş tablolarının tamamlanmış hâlinden türetilmiştir.
- Eşzamanlılık etiketleri hedef modelin gereksinimlerinden ve mevcut kodun
  davranışından çıkarılmıştır; implementasyon sırasında doğrulanmalıdır.
- Mevcut durum değerlendirmesi GAP envanteri (§3) ile çapraz kontrol
  edilmiştir.

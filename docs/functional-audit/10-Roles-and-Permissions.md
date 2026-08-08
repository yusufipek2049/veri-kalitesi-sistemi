---
type: functional-audit
stage: "10 — Rol ve İzin Matrisi"
scope: roles-permissions
inputs:
  - 02-Target-Capability-Hierarchy.md
  - 04-Functional-Gap-Inventory.md
  - 09-State-Machines.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-04
---

# 10 — Rol ve İzin Matrisi

> Hedef kabiliyet hiyerarşisindeki (§6.2) **15 rol**, **100+ izin** ve
> **görev ayrılığı çiftleri**. Bu belge yalnızca global rol kontrolünü değil;
> **dataset, domain, kaynak ve organizasyon kapsamındaki** yetki sınırlarını
> da değerlendirir. Her rol en az bir hedef fonksiyona ve kullanıcı akışına
> bağlıdır.

---

## 1. Kapsam ve yöntem

### 1.1 Kapsam tipleri

Rol matrisinde altı kapsam tipi kullanılır. Her izin, rolün hangi kapsamda
geçerli olduğunu belirtir:

| Kapsam | Kod | Anlam | Uygulama |
|---|---|---|---|
| Kurum geneli | `KG` | Tüm varlıklar üzerinde yetki | `assignment_scopes` tablosunda kayıt yok; rol atanmışsa her yerde geçerli |
| Domain | `DOM` | `data_domains` / `business_domains` altındaki varlıklar | `assignment_scopes.scope_type = 'DOMAIN'` + `scope_value` |
| Kaynak | `SRC` | Tek `data_sources` kaydı | `assignment_scopes.scope_type = 'SOURCE'` + `scope_value` |
| Dataset | `DS` | Tek `datasets` kaydı (kaynak + şema + ad üçlüsü) | `assignment_scopes.scope_type = 'DATASET'` + `scope_value` |
| Nesne sahipliği | `OBJ` | Aktörün atandığı/sahip olduğu nesneler | `asset_ownerships` veya doğrudan atama (`issues.assigned_to`) |
| Yalnız sistem | `SYS` | Yalnız sistem aktörü (insan dışı) | Rol ataması yok; servis hesabı veya zamanlayıcı |

### 1.2 Kapsam çözümleme zinciri

```
Kullanıcı oturum açar
  → role_assignments (ACTIVE, valid_to geçmemiş)
    → assignment_scopes (scope_type, scope_value)
      → Domain çözümlemesi: data_domains / business_domains
        → Dataset çözümlemesi: datasets.data_domain_id
          → Kaynak çözümlemesi: datasets.data_source_id
            → İzin kontrolü: role_permissions → permissions.code
```

Bir kullanıcının belirli bir nesne üzerindeki yetkisi şu sırayla değerlendirilir:

1. **Rol var mı?** — `role_assignments` tablosunda `ACTIVE` ve süresi geçmemiş.
2. **Kapsam yeterli mi?** — `assignment_scopes` tablosunda nesnenin domain,
   kaynak veya dataset kimliğiyle eşleşen kayıt var mı?
3. **İzin kodu var mı?** — Rolün `role_permissions` üzerinden sahip olduğu
   izinler hedef eylemi kapsıyor mu?
4. **SoD ihlali var mı?** — Aynı aktörde çakışan izin çiftleri var mı?
5. **Görev ayrılığı (nesne düzeyinde)** — maker ≠ checker, atanan ≠ doğrulayan.

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
| I | Kimlik ve erişim |
| J | Yönetişim |
| K | Veri sözleşmesi |
| L | Sentetik doğrulama |
| M | Bildirim ve entegrasyon |

---

## 2. Rol kataloğu

### 2.1 Rol tanımı ve varsayılan kapsam

| # | Rol | Sorumluluk | Varsayılan kapsam | Birincil akış |
|---|---|---|---|---|
| R01 | **Platform Admin** (PA) | Sistem konfigürasyonu, özellik anahtarları, altyapı, operasyon | KG | D, J |
| R02 | **Security Admin** (SA) | Kimlik, rol, izin, SoD, oturum, erişim gözden geçirme | KG | I |
| R03 | **Data Governance Admin** (GA) | Domain yapısı, sahiplik, sözlük, politika, saklama, istisna onayı | KG | G, J, K |
| R04 | **Data Owner** (DO) | Sahip olduğu varlıkların kalitesinden ve kararlarından sorumlu | DOM / SRC | A, C, F, G, K |
| R05 | **Data Steward** (DS) | Günlük kalite yönetimi: kural, sorun, profil, sınıflandırma | DOM / DS | B, C, E, F |
| R06 | **Technical Data Steward** (TS) | Kaynak bağlantısı, metadata, şema, teknik ölçüm sağlığı | SRC / DS | A, E, L |
| R07 | **Rule Author** (RA) | Kural ve sürüm tasarımı, test, onaya gönderme | DS | B |
| R08 | **Rule Approver** (RP) | Kural sürümü onayı (yazandan bağımsız) | DS | B |
| R09 | **Issue Assignee** (IA) | Sorun inceleme ve çözüm | OBJ (atanan sorunlar) | C |
| R10 | **Issue Verifier** (IV) | Çözümün bağımsız doğrulanması (çözenden farklı) | DS / DOM | C |
| R11 | **Report Consumer** (RC) | Rapor talebi, indirme, sözleşme tüketiciliği | DOM / DS | H, K |
| R12 | **Auditor** (AU) | Salt okunur denetim; audit, istisna, imha kanıtı, geri çağırma | KG (salt okunur) | Tüm akışlar (okuma) |
| R13 | **Operations User** (OP) | Kuyruk, worker, dead-letter, olay, bakım, telafi | KG | D |
| R14 | **Integration Service Account** (IS) | Programatik erişim; lineage yazma, entegrasyon geri bildirimi | Dar, amaç bazlı | M |
| R15 | **Read-only Viewer** (RV) | Yalnız görüntüleme | DOM / DS | Tüm akışlar (okuma) |

### 2.2 Rol × domain eşleşmesi

Her rolün birincil olarak etkileşimde bulunduğu domain(ler):

| Rol | D01 | D02 | D03 | D04 | D05 | D06 | D07 | D08 | D09 | D10 | D11 | D12 | D13 | D14 | D15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PA | ● | ◐ | ○ | ○ | ○ | ○ | ● | ○ | ○ | ○ | ○ | ● | ◐ | ● | ◐ |
| SA | ◐ | ● | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ◐ | ○ | ○ |
| GA | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ○ | ○ | ● | ● | ○ | ○ | ● | ○ | ○ |
| DO | ● | ◐ | ● | ● | ◐ | ◐ | ○ | ● | ● | ● | ● | ○ | ○ | ○ | ○ |
| DS | ○ | ○ | ◐ | ● | ● | ● | ● | ● | ● | ◐ | ◐ | ○ | ○ | ○ | ○ |
| TS | ○ | ○ | ● | ● | ● | ◐ | ◐ | ○ | ◐ | ● | ○ | ○ | ○ | ○ | ● |
| RA | ○ | ○ | ○ | ◐ | ○ | ● | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| RP | ○ | ○ | ○ | ◐ | ○ | ● | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| IA | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ● | ◐ | ○ | ○ | ○ | ○ | ○ |
| IV | ○ | ○ | ○ | ◐ | ○ | ○ | ○ | ○ | ● | ○ | ○ | ○ | ○ | ○ | ○ |
| RC | ○ | ○ | ○ | ◐ | ○ | ○ | ○ | ◐ | ○ | ◐ | ● | ○ | ○ | ○ | ○ |
| AU | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ● | ◐ | ● | ◐ | ○ |
| OP | ○ | ○ | ◐ | ○ | ○ | ○ | ● | ○ | ◐ | ○ | ◐ | ● | ◐ | ● | ○ |
| IS | ○ | ○ | ◐ | ◐ | ○ | ○ | ○ | ○ | ○ | ● | ○ | ● | ○ | ○ | ○ |
| RV | ○ | ○ | ◐ | ◐ | ○ | ◐ | ○ | ◐ | ◐ | ◐ | ◐ | ○ | ○ | ○ | ○ |

● = birincil domain (yazma yetkisi tipik) · ◐ = ikincil (okuma veya dar yazma) · ○ = erişimi yok veya nadir

---

## 3. İzin × rol matrisi — kapsam değerlendirmesiyle

Aşağıdaki matris her izni, hangi rollerin erişebildiğini ve **kapsam
sınırlamasını** gösterir. Kapsam sütunu, rolün bu izni hangi kapsamda
kullanabileceğini belirtir; bu, global rol kontrolünün ötesinde bir
değerlendirmedir.

### 3.1 D01 — Yönetişim, organizasyon ve politika

| İzin kodu | Roller | Kapsam | Değerlendirme |
|---|---|---|---|
| `org.unit.manage` | PA | KG | Organizasyon birimi yönetimi her zaman kurum genelinde |
| `governance.domain.manage` | GA | KG | Domain yapısı kurum genelinde tanımlanır |
| `governance.domain.assign` | GA, DO | DOM | Domain ataması **sahip olunan domain** ile sınırlı |
| `governance.ownership.assign` | GA, DO | DOM | Varlık sahipliği ataması domain kapsamında |
| `governance.ownership.transfer` | GA, DO | DOM | Sahiplik devri; eski ve yeni sahip aynı domain'de olmalı |
| `governance.ownership.read` | GA, DO, AU | DOM | Sahiplik okuma domainle sınırlı |
| `governance.scan.execute` | — (SYS) | SYS | Otomatik tarama; insan aktör yok |
| `glossary.term.propose` | DS, DO | DOM | Terim önerisi **çalışılan domain** ile sınırlı |
| `glossary.term.approve` | GA | DOM | Terim onayı domain kapsamında |
| `glossary.term.manage` | GA | DOM | Terim yönetimi domain kapsamında |
| `glossary.mapping.manage` | DS, TS | DS | Terim eşleştirme dataset kapsamında |
| `policy.draft.create` | GA, PA | KG | Politika taslağı kurum genelinde |
| `policy.submit` | GA | KG | Politika onaya gönderme kurum genelinde |
| `policy.approve` | SA, GA | KG | Politika onayı kurum genelinde; SoD: submit ≠ approve |
| `policy.activate` | PA, GA | KG | Politika yürürlüğe alma; aralık çakışması kontrolü |
| `policy.rollback` | PA | KG | Geri alma; hedef sürüm mevcut olmalı |
| `system.config.manage` | PA | KG | Sistem konfigürasyonu maker-checker ile |
| `system.config.read` | PA, AU | KG | Salt okunur |
| `system.feature.manage` | PA | KG | Özellik anahtarları |

### 3.2 D02 — Kimlik, rol ve erişim

| İzin kodu | Roller | Kapsam | Değerlendirme |
|---|---|---|---|
| `identity.user.manage` | SA | KG | Kullanıcı sağlama/pasifleştirme kurum genelinde |
| `identity.service-account.manage` | SA | KG | Servis hesabı yönetimi |
| `identity.service-account.rotate` | SA, OBJ sahibi | KG / OBJ | Kimlik bilgisi döndürme; kendi hesabında |
| `identity.role.manage` | SA | KG | Rol tanımı |
| `identity.role.assign` | SA | KG | Rol atama; SoD kontrolü |
| `identity.permission.read` | SA, AU | KG | İzin kataloğu okuma |
| `identity.sod.manage` | SA | KG | Görev ayrılığı kuralları |
| `identity.scope.assign` | SA, GA | KG | Kapsam atama (domain/dataset) |
| `identity.session.read` | SA, AU, OBJ sahibi | KG / OBJ | Oturum listesi; kendi oturumu OBJ kapsamında |
| `identity.session.terminate` | SA, OBJ sahibi | KG / OBJ | Oturum sonlandırma; Security Admin her yerde |
| `identity.access-review.manage` | SA | KG | Erişim gözden geçirme kampanyası |
| `identity.access-review.decide` | DO, SA | DOM | Gözden geçirme kararı; **kendi atamasını gözden geçiremez** |

### 3.3 D03 — Veri kaynağı ve bağlantı

| İzin kodu | Roller | Kapsam | Değerlendirme |
|---|---|---|---|
| `datasource.create` | TS, DO | DOM | Kaynak oluşturma **domain** kapsamında |
| `datasource.read` | TS, DS, DO, OP, AU, RV | SRC | Kaynak okuma **kaynak** kapsamında |
| `datasource.secret.bind` | TS, SA | SRC | Sır bağlama; Security Admin her kaynakta |
| `datasource.test.execute` | TS | SRC | Bağlantı testi kaynak kapsamında |
| `datasource.activation.request` | TS | SRC | Aktivasyon talebi (maker) |
| `datasource.activation.decide` | DO | SRC | Aktivasyon kararı (checker ≠ maker); **kaynak** kapsamında |
| `datasource.deactivate` | DO, OP | SRC | Pasifleştirme; Operations kurum genelinde |
| `datasource.archive` | DO, GA | SRC | Arşivleme; Governance Admin kurum genelinde |
| `datasource.policy.manage` | TS, PA | SRC | Kullanım politikası |
| `datasource.connection.revise` | TS | SRC | Bağlantı revizyonu |
| `datasource.connection.apply` | TS, DO, OP | SRC | Revizyon yürürlüğe alma |
| `datasource.healthcheck.execute` | — (SYS) | SYS | Otomatik sağlık kontrolü |

**Kapsam değerlendirmesi:** Kaynak oluşturma `DOM` kapsamında iken, aktivasyon
kararı `SRC` kapsamında — yani Data Owner **sahip olduğu domain'deki**
kaynakların aktivasyonunu onaylayabilir, başka domain'deki kaynakları değil.

### 3.4 D04 — Metadata, katalog ve varlık

| İzin kodu | Roller | Kapsam | Değerlendirme |
|---|---|---|---|
| `catalog.discovery.execute` | TS | SRC | Keşif tetikleme kaynak kapsamında |
| `catalog.discovery.configure` | TS | SRC | Keşif kapsamı yapılandırma |
| `catalog.diff.apply` | TS | SRC | Fark uygulama |
| `catalog.dataset.manage` | TS | SRC | Dataset yönetimi kaynak kapsamında |
| `catalog.dataset.classify` | DO, GA | DS | Dataset sınıflandırma **dataset** kapsamında |
| `catalog.field.manage` | TS | DS | Alan yönetimi dataset kapsamında |
| `catalog.field.classify` | DS, GA | DS | Alan sınıflandırma dataset kapsamında |
| `catalog.classification.scan` | — (SYS) | SYS | Otomatik sınıflandırma |
| `catalog.schema-change.decide` | DO, TS | DS | Şema değişikliği kararı **dataset** kapsamında |
| `catalog.read` | tüm okuma yetkili roller | DS | Katalog okuma dataset kapsamında |

**Kapsam değerlendirmesi:** Metadata keşfi `SRC` düzeyinde tetiklenir ancak
şema değişikliği kararı `DS` düzeyinde verilir — bu, aynı kaynak altındaki
farklı dataset'ler için bağımsız karar alınabileceği anlamına gelir.

### 3.5 D05 — Profilleme ve drift

| İzin kodu | Roller | Kapsam | Değerlendirme |
|---|---|---|---|
| `profile.execute` | DS, TS | DS | Profil çalıştırma dataset kapsamında |
| `profile.cancel` | OP, OBJ sahibi | DS / OBJ | Profil iptali; Operations dataset kapsamında |
| `profile.compare` | DS, TS | DS | Baseline karşılaştırma |
| `profile.baseline.manage` | DS, DO | DS | Baseline belirleme/iptal |

### 3.6 D06 — Kural yönetimi

| İzin kodu | Roller | Kapsam | Değerlendirme |
|---|---|---|---|
| `quality.dimension.manage` | GA | KG | Boyut tanımı kurum genelinde |
| `rule.template.manage` | GA, RA | KG | Şablon yönetimi kurum genelinde |
| `rule.template.publish` | GA | KG | Şablon yayımlama; SoD: manage ≠ publish |
| `rule.create` | RA, DS | DS | Kural oluşturma **dataset** kapsamında |
| `rule.create.custom-query` | RA | DS | Özel sorgu kuralı |
| `rule.version.create` | RA | DS | Sürüm oluşturma dataset kapsamında |
| `rule.test.execute` | RA | DS | Kural testi dataset kapsamında |
| `rule.approval.request` | RA | DS | Onay talebi (maker) |
| `rule.approval.decide` | RP | DS | Onay kararı (checker ≠ maker) |
| `rule.approval.expire` | — (SYS) | SYS | Otomatik süre dolma |
| `rule.activate` | DS, RA | DS | Sürüm aktive etme dataset kapsamında |
| `rule.deactivate` | DS, DO | DS | Pasifleştirme; Data Owner domain kapsamında |
| `rule.archive` | DO | DS | Arşivleme dataset kapsamında |
| `rule.read` | RA, RP, DS, DO, TS, AU, RV | DS | Kural okuma dataset kapsamında |
| `rule.shadow.execute` | RA, DS | DS | Gölge yürütme dataset kapsamında |
| `rule.shadow.read` | RA, DS | DS | Gölge sonuç okuma |

**Kapsam değerlendirmesi:** Kural oluşturma ve yürütme `DS` düzeyinde
sınırlıyken, şablon yönetimi `KG` düzeyindedir — şablonlar kurum genelinde
tanımlanır ancak kurallar dataset bazında oluşturulur.

### 3.7 D07 — Yürütme, zamanlama ve kuyruk

| İzin kodu | Roller | Kapsam | Değerlendirme |
|---|---|---|---|
| `execution.start` | DS, OP | DS + SRC | Çalıştırma başlatma; **hem dataset hem kaynak** gerekir |
| `execution.cancel` | OP, OBJ sahibi | DS / OBJ | İptal; Operations dataset kapsamında |
| `execution.read` | DS, OP, DO, TS, AU, RV | SRC / DS | Çalıştırma okuma |
| `schedule.manage` | DS, OP | DS + SRC | Zamanlama; hem dataset hem kaynak kapsamında |
| `schedule.trigger.execute` | — (SYS) | SYS | Otomatik tetikleme |
| `job.priority.override` | OP | KG | İş önceliği değiştirme kurum genelinde |

### 3.8 D08 — Ölçüm ve skorlama

| İzin kodu | Roller | Kapsam | Değerlendirme |
|---|---|---|---|
| `evidence.sample.read` | IA, DS, TS | DS | Kanıt örneği okuma dataset kapsamında |
| `score.read` | DO, DS, GA, AU, RC, RV | DOM / DS | Skor okuma; Data Owner **domain** düzeyinde, diğerleri dataset |
| `score.reproduce` | AU, DO | DOM / DS | Skor yeniden üretme; Auditor kurum genelinde |
| `risk.model.manage` | GA | KG | Risk modeli kurum genelinde |
| `risk.read` | DO, GA, AU, RV | DOM | Risk okuma domain kapsamında |

**Kapsam değerlendirmesi:** Skor okuma `DOM/DS` — Data Owner kendi
domain'indeki tüm dataset skorlarını görebilirken, Read-only Viewer yalnız
atandığı dataset'lerin skorlarını görebilir.

### 3.9 D09 — Sorun, istisna ve düzeltme

| İzin kodu | Roller | Kapsam | Değerlendirme |
|---|---|---|---|
| `issue.create` | DS, DO, RC | DS | Sorun açma dataset kapsamında |
| `issue.read` | IA, IV, DS, DO, AU, RV | DS / DOM | Sorun okuma; Issue Assignee yalnız **atanan sorunlar** (OBJ) |
| `issue.assign` | DS, DO | DS | Sorun atama dataset kapsamında |
| `issue.investigate` | IA | OBJ | İnceleme; yalnız **atanan sorunlar** üzerinde |
| `issue.comment` | IA, DS, DO | DS | Yorum ekleme dataset kapsamında |
| `issue.resolve` | IA | OBJ | Çözüm; yalnız atanan sorunlar üzerinde |
| `issue.verify` | IV | DS / DOM | Doğrulama; **çözenden bağımsız** olmalı |
| `issue.close` | IV, DO | DS | Kapatma dataset kapsamında |
| `issue.reopen` | DS | DS | Yeniden açma dataset kapsamında |
| `exception.request` | DO, DS | DS / DOM | İstisna talebi (maker) |
| `exception.decide` | GA, DO | DOM | İstisna kararı (checker ≠ maker); **domain** kapsamında |
| `exception.revoke` | GA, onaylayan | DOM | İptal; onaylayan iptal edebilir, talep eden edemez |
| `exception.read` | GA, AU, DO | DOM | İstisna okuma domain kapsamında |
| `remediation.manage` | IA, DO | DS | Düzeltme aksiyonu dataset kapsamında |
| `remediation.execute` | OBJ sahibi | OBJ | Aksiyon yürütme; yalnız sorumlu aktör |
| `remediation.auto.execute` | — (SYS) | SYS | Otomatik yürütme (politika sınırlı) |

**Kapsam değerlendirmesi:** Sorun yönetimi `OBJ` (nesne sahipliği) ve `DS`
(dataset) karışımı — inceleme ve çözüm yalnız atanan sorun üzerinde
geçerliyken, sorun atama dataset düzeyinde yetki gerektirir. İstisna kararı
`DOM` düzeyindedir — domain sahibi kendi domain'indeki istisnaları
onaylayabilir.

### 3.10 D10 — Lineage, etki ve sözleşme

| İzin kodu | Roller | Kapsam | Değerlendirme |
|---|---|---|---|
| `lineage.write` | IS | SRC | Lineage yazma; servis hesabı kaynak kapsamında |
| `lineage.read` | DS, TS, IA | DS | Lineage okuma dataset kapsamında |
| `lineage.impact.read` | DS, TS, IA, DO | DS | Etki okuma dataset kapsamında |
| `lineage.impact.simulate` | TS, RA | DS | Etki simülasyonu dataset kapsamında |
| `contract.manage` | DO | DS | Sözleşme yönetimi dataset kapsamında |
| `contract.accept` | DO (her iki taraf) | DS / DOM | Sözleşme kabulü; **iki tarafın sahibi** onaylamalı |
| `contract.read` | DO, RC, DS, AU, RV | DS / DOM | Sözleşme okuma |
| `quality-debt.manage` | DS, DO, GA | DOM | Kalite borcu yönetimi domain kapsamında |
| `quality-debt.read` | DO, GA, AU, RV | DOM | Kalite borcu okuma domain kapsamında |

**Kapsam değerlendirmesi:** Sözleşme kabulü `DS/DOM` — her iki tarafın Data
Owner'ı kabul etmeli; aynı aktör her iki tarafı onaylayamaz (nesne düzeyinde
SoD).

### 3.11 D11–D15 ve ortak izinler

| İzin kodu | Roller | Kapsam | Değerlendirme |
|---|---|---|---|
| `dashboard.read` | tüm okuma yetkili roller | DOM / DS | Dashboard okuma domain/dataset kapsamında |
| `analytics.read` | DO, DS, GA, AU, RC | DOM | Analitik okuma domain kapsamında |
| `analytics.export` | DO, GA, RC | DOM | Dışa aktarım domain kapsamında |
| `report.request` | RC, DO, AU | DOM / DS | Rapor talebi |
| `report.preview` | RC, DO | DOM / DS | Rapor önizleme |
| `report.read` | RC, DO, AU | OBJ | Rapor okuma; yalnız talep eden |
| `report.read.all` | AU | KG | Auditor tüm raporları okuyabilir |
| `report.download` | RC, DO, AU | OBJ | İndirme |
| `report.cancel` | OP, OBJ sahibi | KG / OBJ | İptal |
| `report.schedule.manage` | RC, DO | DOM / DS | Zamanlama yönetimi |
| `notification.subscription.manage` | tüm kullanıcı rolleri | OBJ | Kendi aboneliğini yönetir |
| `notification.subscription.manage.all` | PA | KG | Platform Admin tüm abonelikleri yönetir |
| `notification.channel.manage` | PA | KG | Kanal yönetimi |
| `notification.delivery.read` | OP, PA | KG | Teslimat okuma |
| `notification.delivery.manage` | OP | KG | Teslimat yönetimi |
| `integration.outbound.execute` | — (SYS) | SYS | Otomatik giden entegrasyon |
| `integration.outbound.trigger` | IA, DS | DS | Manuel tetikleme dataset kapsamında |
| `integration.inbound.write` | IS | SRC / DS | Gelen veri yazma |
| `audit.read` | AU, SA | KG | Audit okuma kurum genelinde |
| `audit.read.object` | AU, DO, GA | OBJ | Nesne bazında audit okuma |
| `audit.verify` | AU | KG | Zincir doğrulama |
| `audit.outbox.read` | OP, SA | KG | Outbox izleme |
| `retention.policy.manage` | GA | KG | Saklama politikası |
| `retention.disposal.execute` | — (SYS) | SYS | Otomatik imha |
| `retention.disposal.read` | AU, GA | KG | İmha kayıtları okuma |
| `retention.legal-hold.manage` | GA, AU | KG | Yasal muhafaza |
| `retention.archive.recall` | AU, GA | KG | Arşiv geri çağırma |
| `operations.health.read` | OP, PA | KG | Sağlık okuma |
| `operations.queue.read` | OP | KG | Kuyruk okuma |
| `operations.queue.manage` | OP | KG | Kuyruk yönetimi |
| `operations.worker.read` | OP | KG | Worker okuma |
| `operations.worker.manage` | OP, PA | KG | Worker yönetimi |
| `operations.dead-letter.read` | OP | KG | Dead-letter okuma |
| `operations.dead-letter.reprocess` | OP | KG | Yeniden işleme |
| `operations.dead-letter.close` | OP | KG | Kapatma |
| `operations.incident.manage` | OP | KG | Olay yönetimi |
| `operations.maintenance.manage` | PA, OP | KG | Bakım penceresi |
| `operations.backfill.execute` | OP | KG | Toplu telafi |
| `synthetic.generate` | TS, PA | KG | Sentetik üretim |
| `synthetic.manage` | TS | KG | Sentetik profil yönetimi |
| `synthetic.profile.manage` | TS | KG | Profil tanımı |
| `synthetic.ground-truth.manage` | TS | KG | Ground truth kaydı |
| `synthetic.validate.execute` | TS | KG | Doğrulama çalıştırma |
| `synthetic.experiment.execute` | PA, TS | KG | Yeterlilik deneyi |

---

## 4. Görev ayrılığı (SoD) matrisi

### 4.1 İzin çifti düzeyinde SoD

Aynı aktörde birleşmesi kontrol zafiyeti yaratan izinler:

| # | İzin A | İzin B | Seviye | Gerekçe | İlgili ST |
|---|---|---|---|---|---|
| S01 | `rule.approval.request` | `rule.approval.decide` | BLOCK | Kural sürümünü yazan onaylayamaz | ST-RuleVersion |
| S02 | `datasource.activation.request` | `datasource.activation.decide` | BLOCK | Kaynağı hazırlayan devreye alamaz | ST-DataSource |
| S03 | `policy.submit` | `policy.approve` | BLOCK | Politika değişikliğini talep eden onaylayamaz | ST-Policy |
| S04 | `exception.request` | `exception.decide` | BLOCK | İstisnayı talep eden riski kabul edemez | ST-Exception |
| S05 | `issue.resolve` | `issue.verify` | BLOCK | Çözümü yapan doğrulayamaz | ST-Issue |
| S06 | `glossary.term.propose` | `glossary.term.approve` | BLOCK | Terimi öneren onaylayamaz | — |
| S07 | `rule.template.manage` | `rule.template.publish` | BLOCK | Şablonu yazan yayımlayamaz | ST-RuleTemplate |
| S08 | `identity.role.assign` | `identity.access-review.decide` | BLOCK | Yetkiyi veren gözden geçiremez | ST-AccessReviewItem |
| S09 | `identity.role.manage` | `audit.read` | WARN | Yetki tanımlayan denetim izini incelememeli | — |
| S10 | `retention.disposal.read` | `retention.legal-hold.manage` | WARN | İmha ve muhafaza kararları ayrışmalı | ST-LegalHold |
| S11 | `synthetic.generate` | `synthetic.validate.execute` | WARN | Test verisini üreten doğruluğu tek başına ölçmemeli | — |
| S12 | `operations.dead-letter.close` | `operations.backfill.execute` | WARN | Boşluğu kapatan telafiyi tek başına yönetmemeli | ST-DeadLetterRecord |

### 4.2 Nesne düzeyinde ek kısıtlar

İzin çiftiyle ifade edilemeyen, nesne düzeyinde uygulanan kısıtlar:

| # | Kural | Uygulama noktası | İlgili ST |
|---|---|---|---|
| N01 | Aktör kendi rol atamasını gözden geçiremez | `D02.C05.W01.A02` | ST-AccessReviewItem |
| N02 | Sözleşmenin iki tarafını aynı aktör onaylayamaz | `D10.C03.W01.A02` | ST-DataContract |
| N03 | İstisnayı onaylayan iptal edebilir, ancak talep eden edemez | `D09.C04.W03.A02` | ST-Exception |
| N04 | Arşiv geri çağırma talebi ve kararı farklı aktörlerde | `D13.C04.W02.A01` | — |

### 4.3 Kapsam bazında SoD çakışma analizi

Aşağıdaki matris, aynı aktörün farklı **kapsamlarda** çakışan izinler
taşıyıp taşıyamayacağını gösterir:

| Senaryo | İzin A (kapsam) | İzin B (kapsam) | Sonuç |
|---|---|---|---|
| Data Owner hem kaynak hazırlar hem aktivasyon onaylar | `datasource.activation.request` (SRC) | `datasource.activation.decide` (SRC) | **BLOCK** — aynı kaynakta |
| Data Owner farklı domain'de istisna talep ve onay | `exception.request` (DOM-A) | `exception.decide` (DOM-B) | **İzin verilmez** — GA veya aynı domain DO gerekir |
| Rule Author kendi dataset'inde kural yazar ve onaylar | `rule.approval.request` (DS) | `rule.approval.decide` (DS) | **BLOCK** — aynı dataset'te |
| Security Admin rol atar ve erişim gözden geçirir | `identity.role.assign` (KG) | `identity.access-review.decide` (DOM) | **BLOCK** — KG kapsamı DOM'ı kapsar |
| Auditor hem denetim yapar hem imha muhafaza karar verir | `audit.read` (KG) | `retention.legal-hold.manage` (KG) | **WARN** — uyarı üretilir |

### 4.4 SoD'nin bugünkü uygulanma düzeyi

Yukarıdaki matris hedeftir. Mevcut durumda SoD üç farklı düzeyde ele
alınmalıdır; "SoD yok" ile "SoD zorlanmıyor" aynı şey değildir:

| Düzey | Durum | Kanıt |
|---|---|---|
| Servis kuralı | ⚠️ Üç nesnede var | `rules/service.py:542-545` (kural onayı), `data_sources/service.py:487-488` (aktivasyon), `issues/service.py:646-649` (çözüm doğrulama) |
| Birim testi | ✅ Var | `test_rules.py:825`, `test_data_sources.py:2205`/`:3255`, `test_issues.py:961` |
| Veritabanı kısıtı | ❌ Yok | 14 migration'daki hiçbir `CheckConstraint` kolon-kolon karşılaştırması yapmaz |
| Çalışan komut yüzeyi | ❌ Atlanıyor | Kaynak aktivasyonunda servis hiç çağrılmıyor (§6.1.2, GAP-027) |

İki uyarı:

1. Sorun doğrulamasındaki self-verification guard'ı yalnız `QUALITY_PASSED`
   dalındadır (`issues/service.py:638`); çözümü oluşturan aktör kendi çözümü
   için `QUALITY_FAILED`, `PARTIAL` veya `TECHNICAL_ERROR` doğrulaması
   girebilir.
2. Güvence tamamen servis sınırına bağlı olduğundan, o sınırı atlayan tek bir
   route bütün SoD iddiasını geçersiz kılar. Bugün böyle bir route vardır.

---

## 5. Kapsam çözümleme örnekleri

### 5.1 Dataset kapsamlı rol çözümlemesi

**Senaryo:** Data Steward (DS) kural oluşturmak istiyor.

```
1. role_assignments: DS rolü ACTIVE, valid_to geçmemiş ✓
2. assignment_scopes: scope_type = 'DATASET', scope_value = 'ds-123'
3. permission check: role_permissions → 'rule.create' var mı? ✓
4. scope check: Hedef dataset 'ds-123' mi? ✓
5. SoD check: 'rule.approval.request' + 'rule.approval.decide' aynı rolde? Hayır ✓
→ İzin verilir
```

**Negatif senaryo:** DS başka dataset'te kural oluşturmak istiyor.

```
1–3. Aynı ✓
4. scope check: Hedef dataset 'ds-456' mı? Hayır — scope 'ds-123' ✗
→ 403 Forbidden
```

### 5.2 Domain kapsamlı rol çözümlemesi

**Senaryo:** Data Owner (DO) istisna onaylamak istiyor.

```
1. role_assignments: DO rolü ACTIVE ✓
2. assignment_scopes: scope_type = 'DOMAIN', scope_value = 'domain-finance'
3. permission check: 'exception.decide' var mı? ✓
4. scope check: İstisnanın dataset'i 'domain-finance' altında mı? ✓
5. SoD check: Aynı aktör 'exception.request' de taşıyor mu?
   → Taşıyorsa BLOCK (S04)
   → Taşımıyorsa ✓
6. Nesne düzeyi: Aktör bu istisnanın talep edeni (maker) mi?
   → Evetse BLOCK (N03)
   → Hayır ✓
→ İzin verilir
```

### 5.3 OBJ kapsamlı rol çözümlemesi

**Senaryo:** Issue Assignee (IA) bir sorunu çözmek istiyor.

```
1. role_assignments: IA rolü ACTIVE ✓
2. scope check: issue.assigned_to = bu aktör mü? ✓ (OBJ)
3. permission check: 'issue.resolve' var mı? ✓
4. scope check: Hedef sorun atandığı sorun mu? ✓
5. SoD check: 'issue.verify' de aynı rolde mi? Hayır ✓
→ İzin verilir
```

**Negatif senaryo:** IA başka birinin sorununu çözmek istiyor.

```
1–2. ✓
3. permission check: 'issue.resolve' var mı? ✓
4. scope check: issue.assigned_to = bu aktör mü? Hayır ✗
→ 403 Forbidden
```

---

## 6. Üretim yetkisi ve GAP ilişkisi

### 6.1 Mevcut durum

| Bileşen | Durum | Değerlendirme |
|---|---|---|
| Rol tanımı | ❌ Yok | `roles` tablosu migration'da yok (GAP-022) |
| İzin tanımı | ❌ Yok | `permissions` / `role_permissions` tabloları yok |
| Rol atama | ❌ Yok | `role_assignments` / `assignment_scopes` tabloları yok |
| Kapsam çözümleme — **okuma** | ⚠️ Kısmi | `PolicyAuthorizationService` kararı reader filtrelerine taşınıyor; kapsam **kaynağı** kalıcı değil |
| Kapsam çözümleme — **komut** | ❌ Yok | Aktör bağlamı mutation port'una hiç geçmiyor (GAP-027) |
| SoD kontrolü — servis | ⚠️ Kısmi | maker ≠ checker kural ve kaynak onayında kodda var ve testli; DB `CHECK` ile zorlanmıyor |
| SoD kontrolü — çalışan yol | ❌ Yok | Kaynak aktivasyonunda servis hiç çağrılmıyor (GAP-027) |
| Servis hesabı | ❌ Yok | `service_accounts` tablosu yok; `ActorType.SERVICE` yalnız bellek içi kavram |
| Oturum yönetimi | ⚠️ Kısmi | `identity/sessions.py` içinde SQLite oturum deposu ve yaşam döngüsü var, bileşime bağlı değil; çalışan yol `X-Development-User-Id` başlığı |

### 6.1.1 Okuma yolu — gerçekten uygulanan kısım

"Kapsam yalnız ön yüzde uygulanıyor" ifadesi **okuma yolu için doğru
değildir**. `identity/service.py:90 PolicyAuthorizationService` güveni,
saat kaymasını, son kullanma ve politika sürümünü doğrular; kararı
`permitted_source_ids` / `permitted_dataset_ids` ile döner ve ALLOW/DENY
audit'ler. Dört sorgu servisi bu kimlikleri reader'a geçirir:

| Servis | Kanıt |
|---|---|
| `IssueQueryService` | `issues/query.py:57,64-66` |
| `RuleQueryService` | `rules/query.py:46,52` |
| `ExecutionQueryService` | `executions/query.py:54,61-62` |
| `DataSourceQueryService` | `data_sources/query.py:66,72` |

Boş kapsamın "filtre yok" anlamına gelmediği dört testle sabitlenmiştir
(bkz. [11-Test-Coverage-Gaps.md](11-Test-Coverage-Gaps.md) §6.2). Eksik olan
bu mekanizma değil, beslediği **kalıcı atama kaydıdır**: izinli kimlik kümesi
`assignment_scopes` yerine dev/test sabitinden gelir.

### 6.1.2 Komut yolu — asıl boşluk

Komut tarafında denetlenecek bir karar noktası yoktur:

- `POST /api/v1/data-sources` · `/test` · `/activation` · `/passivation`
  route'ları çözülmüş `ActorContext`'i mutation portuna iletmez
  (`api/app.py:2017-2110`). Aktivasyonda `DevelopmentDataSourceStore.activate`
  yalnız durum guard'ı uygular; gerçek `decide_activation`'ın checker rolü,
  maker ≠ checker, süre, politika sürümü ve audit denetimleri devreye girmez.
  `activate(self, data_source_id: str)` imzası aktör taşıyamaz.
- `DevelopmentRuleStore.create_rule` bağlamın `None` olmadığına bakar; rolü
  ve dataset kapsamını doğrulamaz (`api/development.py:837-882`).
- Manuel çalıştırma ucu bağlamı `actor_id` dizesine indirger, aktör yoksa
  `"unknown"` yazar (`api/app.py:2133`); `start_manual` kural sürümü/kaynak
  kapsamını, aktifliğini ve aktör rolünü doğrulamaz.

Kimlik doğrulaması `app.py:433-453`'teki middleware'de yapılır; dolayısıyla
durum "kimlik yok" değil, **"kimlik var, yetkilendirme yok"**tur.

### 6.1.3 Dev kimlik profilleri — düzeltme

Çalıştırılabilir yolda tek bir sabit rol kümesi **yoktur**.
`api/identity.py:91 build_default_development_users` sekiz profil tanımlar
(`:117-181`): `dev-data-viewer`, `dev-data-steward`, `dev-data-owner`,
`dev-data-governance`, `dev-data-engineer`, `dev-audit-viewer`
(`can_view_enterprise=False`), `dev-limited-steward` (kısıtlı kapsam) ve
`dev-privileged-user`. Bu, matrisin bir bölümünün gerçekten denenebildiği
anlamına gelir. Güvenlik açısından belirleyici olan nokta başkadır: profil
seçimi istemcinin gönderdiği `X-Development-User-Id` başlığıyla yapılır
(`api/identity.py:246`), yani **aktör kimliği istemci tarafından seçilir**.
Bir güven sınırı olmadığı için bu profiller yetki güvencesi sağlamaz.

### 6.2 GAP etkisi

| GAP | Etkilenen rol/izin | İş etkisi |
|---|---|---|
| GAP-022 | Tüm roller, izinler, SoD, oturum | Yetki sisteminin ön koşulu; diğer tüm GAP'ların yetki kodları bu kayda bağlı |
| GAP-001 | Kapsam kaynağı kalıcı değil | Okuma kapsamı backend'de uygulanıyor fakat izinli kimlik kümesi dev sabitinden besleniyor |
| GAP-027 | Kaynak aktivasyonu, kural oluşturma, manuel çalıştırma | Kodda var olan onay ve kapsam kontrolleri çalışan komut yüzeyinde atlanıyor; GAP-022'den **bağımsız** kapatılabilir |
| GAP-006 | `issue.create` yetkisi tanımsız | Manuel sorun açma yetki kontrolü yok |
| GAP-009 | `exception.request/decide` yetkisi tanımsız | İstisna maker-checker uygulanamıyor |
| GAP-010 | `contract.accept` yetkisi tanımsız | Sözleşme iki taraf onayı uygulanamıyor |
| GAP-026 | `governance.domain.manage`, `policy.*` yetkileri tanımsız | Yönetişim işlemleri yetki kontrolü olmadan çalışıyor |

---

## 7. Rol × akış izlenebilirlik matrisi

Her rolün hangi akışlarda **yazma** yetkisi vardır:

| Rol | A | B | C | D | E | F | G | H | I | J | K | L | M |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PA | — | — | — | ◐ | — | — | — | — | ◐ | ● | — | ◐ | ● |
| SA | — | — | — | — | — | — | — | — | ● | ◐ | — | — | — |
| GA | ◐ | ◐ | ◐ | — | ◐ | — | ● | — | ◐ | ● | ◐ | — | — |
| DO | ● | ◐ | ● | — | ● | ● | ◐ | ● | ◐ | ● | ● | — | — |
| DS | ◐ | ● | ● | ◐ | ● | ● | ◐ | ◐ | — | — | ◐ | — | — |
| TS | ● | ◐ | ◐ | ◐ | ● | ◐ | — | — | — | — | ◐ | ● | — |
| RA | — | ● | — | — | — | — | — | — | — | — | — | — | — |
| RP | — | ● | — | — | — | — | — | — | — | — | — | — | — |
| IA | — | — | ● | — | — | — | — | — | — | — | — | — | — |
| IV | — | — | ● | — | — | — | — | — | — | — | — | — | — |
| RC | — | — | — | — | — | — | — | ● | — | — | ◐ | — | — |
| AU | — | — | — | — | — | — | — | ● | ◐ | ◐ | ◐ | — | — |
| OP | ◐ | ◐ | — | ● | — | — | — | ◐ | — | — | — | — | ● |
| IS | ◐ | — | — | — | — | — | — | — | — | — | — | — | ● |
| RV | — | — | — | — | — | — | — | — | — | — | — | — | — |

● = yazma yetkisi var (en az bir adımda) · ◐ = okuma yetkisi var · — = erişimi yok

---

## 8. Kanıt sınırları

- Rol ve izin tanımları `02-Target-Capability-Hierarchy.md` §6.2'den
  alınmıştır; değişiklik yapılmamıştır.
- Kapsam değerlendirmeleri bu belgenin çıkarımıdır; hedef modelde kapsam
  çözleme zinciri açıkça tanımlanmamıştır ancak `assignment_scopes` tablosu
  ve rol matrisindeki kapsam sütunundan türetilmiştir.
- Mevcut durum değerlendirmesi GAP envanteri ve kod okumasına dayanır;
  §6.1'de belirtilen runtime kanıtları bu belge için de geçerlidir.
- Üretim yetkisi sistemi (GAP-022) henüz implemente edilmemiştir; bu belgedeki
  tüm izin kodları hedef model referansıdır.

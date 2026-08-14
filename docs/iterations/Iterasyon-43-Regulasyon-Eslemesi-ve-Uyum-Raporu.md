---
iteration: 43
status: planned
completed_at: null
decision_reference: USER-DECLARATION-2026-08-CAPABILITY-UPLIFT
blocked_by: OPEN-BNK-013
---

# İterasyon 43 — Regülasyon Eşlemesi ve Uyum Raporu

## Amaç

Uyum eşlemesi bugün **doküman düzeyinde** vardır:
[17.03 BDDK Kontrol Matrisi](../srs/17-Bankacilik-Uyum/17.03-BDDK-Kontrol-Matrisi.md)
ve [17.08 Uyum İzlenebilirlik Matrisi](../srs/17-Bankacilik-Uyum/17.08-Uyum-Izlenebilirlik-Matrisi.md)
`CTRL-*` kontrollerini `BFR-*` ve `FR-*` kodlarına bağlar. Bu eşleme
**bilgi sistemi genel kontrollerini** (kimlik, görevler ayrılığı, audit,
secret, süreklilik) kapsar.

Eksik olan halka şudur: **tek tek kalite kuralı ve veri kümesi hiçbir
kontrole bağlı değildir.** Sistem "şu tabloda güncellik kuralı ihlal edildi"
diyebilir; "bu ihlal şu düzenleyici kontrolün kanıtını zayıflatıyor"
diyemez.

Bu iterasyon eşlemeyi kod seviyesine indirir ve otomatik uyum raporu üretir.

## Ön Koşul — `OPEN-BNK-013`

[Açık Konular](../memory/Acik-Konular.md) kaydı `OPEN-BNK-013`, sistemin risk
verisi veya düzenleyici raporlama üretim zincirine girip girmeyeceğini ve
BCBS 239 kapsamını **açık** olarak işaretlemektedir. Karar Risk Yönetimi ve
Veri Yönetişimi birimlerine aittir.

Bu iterasyon bu belirsizliği şöyle ele alır: **eşleme mekanizması regülasyon
setinden bağımsız kurulur.** Kontrol çerçevesi (`ControlFramework`) veri
olarak yüklenir; kod hiçbir regülasyon maddesini gömülü taşımaz. BCBS 239
kapsamı onaylanırsa çerçeve yüklenir; onaylanmazsa mekanizma yalnız mevcut
BDDK/KVKK kontrolleriyle çalışır. Kod değişikliği gerekmez.

Bu nedenle iterasyon `OPEN-BNK-013` kapanmadan **uygulanabilir**, ancak
üretilen uyum raporu `OPEN-BNK-013` kapanmadan düzenleyiciye sunulabilir
kanıt sayılamaz.

## Kullanıcı / Sistem Değeri

- Kalite ihlali, etkilediği kontrol üzerinden uyum diline çevrilir.
- Denetim hazırlığı elle kanıt toplamaktan çıkar; rapor sistemden üretilir.
- Kontrol kapsamındaki bir veri kümesinin kuralsız kalması "kapsama boşluğu"
  olarak ölçülebilir hale gelir.

## Mevcut FR/UC/RULE

| Kod | Ad |
| --- | --- |
| FR-025 | Kural kapsamı tanımlama |
| FR-026 | Kural boyutu atama |
| FR-029 | Kural sürümleme |
| FR-050 | Boyut, kaynak ve kurum skoru |
| FR-073 | Birim, sahip ve kritik veri raporları |
| FR-076 | Raporlama gereksinimleri (uyum raporu) |
| FR-109 | Kalite borcu yönetimi |
| CTRL-BDDK-AUD-001, CTRL-KVKK-INV-001 | Mevcut kontrol satırları |

## Mimari Yaklaşım

```
┌────────────────────┐
│ ControlFramework   │  veri olarak yüklenir (BDDK / KVKK / BCBS 239 / iç)
│ ControlRequirement │  kod içinde gömülü madde YOKTUR
└─────────┬──────────┘
          │ eşleme (maker-checker onaylı)
          ▼
┌────────────────────┐     ┌────────────────────┐
│ RuleVersion        │     │ Dataset            │
│ + control_refs     │     │ + control_refs     │
└─────────┬──────────┘     └─────────┬──────────┘
          │                          │
          └──────────┬───────────────┘
                     ▼
          ┌────────────────────┐
          │ ControlCoverage    │  kontrol başına:
          │ (hesaplanan)       │  kapsanan/kapsanmayan veri kümesi,
          └─────────┬──────────┘  aktif kural, açık issue, skor
                    │
                    ▼
          ┌────────────────────┐
          │ ComplianceReport   │  İterasyon 39C rapor altyapısı üzerinden
          └────────────────────┘
```

Kritik tasarım kararı: **kod hiçbir mevzuat maddesini gömülü taşımaz.**
17.03'ün kendi uyarısı korunur — "madde seviyesinde kesin eşleme, bankanın
hukuk/uyum ve bilgi güvenliği birimlerince güncel mevzuat metni üzerinden
doğrulanmalıdır." Sistem eşlemeyi **taşır ve raporlar**, eşlemeyi **iddia
etmez**.

İkinci karar: eşleme maker-checker onaylıdır ve sürümlüdür. Bir kuralın
hangi kontrole bağlandığı denetim kanıtıdır; sessizce değişemez.

## Yeni Kontrol Ailesi Önerisi

Mevcut `CTRL-BDDK-*` ailesi bilgi sistemi genel kontrollerini kapsar; veri
kalitesi kontrolü içermez. Aşağıdaki aile **öneri** olarak eklenir ve
banka uyum birimi onayına sunulur:

| CTRL ID (öneri) | Kontrol amacı | İlgili kalite boyutu |
| --- | --- | --- |
| `CTRL-DQ-ACC-001` | Kritik veri alanlarının doğruluğunun ölçülmesi | Doğruluk |
| `CTRL-DQ-CMP-001` | Zorunlu alanların eksiksizliği | Bütünlük/Tamlık |
| `CTRL-DQ-TML-001` | Raporlama verisinin güncelliği | Güncellik |
| `CTRL-DQ-CON-001` | Sistemler arası tutarlılık ve mutabakat | Tutarlılık |
| `CTRL-DQ-LIN-001` | Veri soy ağacının izlenebilirliği | İzlenebilirlik |
| `CTRL-DQ-GOV-001` | Veri sahipliği ve yönetişim atamalarının eksiksizliği | Yönetişim |

`OPEN-BNK-013` olumlu kapanırsa bu aile BCBS 239 Prensip 3 (doğruluk ve
bütünlük), Prensip 4 (eksiksizlik), Prensip 5 (güncellik) ve Prensip 6
(uyarlanabilirlik) ile ilişkilendirilir. İlişkilendirme **veri olarak**
yüklenir.

## Yapılacak Değişiklikler

### Backend

| Dosya | Değişiklik |
| --- | --- |
| `src/veri_kalitesi/compliance/` (yeni paket) | `models.py` (`ControlFramework`, `ControlRequirement`, `ControlMapping`, `ControlCoverage`), `service.py` (`ControlMappingService`, `ControlCoverageService`), `errors.py`, `postgresql_repository.py` |
| `src/veri_kalitesi/compliance/coverage.py` (yeni) | `compute_coverage(control, *, datasets, rules, issues, scores) -> ControlCoverage`. Kapsanmayan veri kümesi ve kuralsız kontrol açıkça raporlanır. |
| `src/veri_kalitesi/rules/models.py` | `RuleVersion`'a `control_refs: tuple[str, ...]`. Sürümlü; kontrol bağı değiştiğinde yeni kural sürümü doğar. |
| `src/veri_kalitesi/data_sources/models.py` | Dataset seviyesinde `control_refs`. |
| `alembic/versions/2026xxxx_27_control_mapping.py` (yeni) | `control_frameworks`, `control_requirements`, `control_mappings`, `control_mapping_approvals` tabloları; `rule_versions` ve dataset tablosuna kontrol referans kolonları. |
| `src/veri_kalitesi/reporting/` | `COMPLIANCE_COVERAGE` rapor tipi (İterasyon 39C altyapısı üzerinde). |
| `src/veri_kalitesi/api/compliance_router.py` (yeni) | `GET /api/v1/control-frameworks`, `GET /api/v1/controls/{control_id}/coverage`, `POST /api/v1/controls/{control_id}/mappings`, `POST /api/v1/control-mappings/{id}/approval` |
| `src/veri_kalitesi/api/app.py`, `composition.py` | Servis kablolaması. |

### Frontend

| Dosya | Değişiklik |
| --- | --- |
| `frontend/src/compliance/` (yeni dizin) | Kontrol listesi, kontrol detayı (kapsanan/kapsanmayan veri kümeleri, aktif kurallar, açık issue'lar, skor), eşleme onay akışı. |
| `frontend/src/rules/RulesPage.tsx` | Kural detayında bağlı kontrol rozetleri. |
| `frontend/src/issues/IssuesPage.tsx` | Sorun detayında etkilenen kontroller. |
| `frontend/src/components/AppShell.tsx` | "Uyum" navigasyon girdisi (yetkiye bağlı görünür). |

### Doküman

| Dosya | Değişiklik |
| --- | --- |
| `docs/srs/17-Bankacilik-Uyum/17.03-BDDK-Kontrol-Matrisi.md` | `CTRL-DQ-*` ailesi öneri olarak eklenir; `Banka kararı` sütunu `ComplianceReviewRequired`. |
| `docs/srs/17-Bankacilik-Uyum/17.08-Uyum-Izlenebilirlik-Matrisi.md` | Yeni satırlar; `Durum` sütunu `Proposed`. |
| `docs/srs/17-Bankacilik-Uyum/17.09-Acik-Uyum-Konulari.md` | `OPEN-BNK-013` bağı ve bu iterasyonun bağımlılığı kaydedilir. |

## Kabul Kriterleri

- [ ] Kod hiçbir mevzuat maddesi metni veya kontrol tanımı **gömülü**
      taşımaz; tüm çerçeve veri olarak yüklenir (statik denetimle kanıtlanır).
- [ ] Çerçeve yüklü değilken sistem mevcut davranışını sürdürür; uyum
      ekranları "çerçeve tanımlı değil" durumunu gösterir, boş liste
      göstermez.
- [ ] Kontrol eşlemesi maker-checker onaylıdır; öneren ile onaylayan aynı
      aktör olamaz.
- [ ] Kontrol referansı değişikliği **yeni kural sürümü** doğurur; mevcut
      sürüm değişmez (FR-029).
- [ ] Kapsama hesabı, kontrol kapsamındaki ama hiçbir aktif kuralı olmayan
      veri kümelerini `UNCOVERED_DATASET` olarak raporlar; bunları "uyumlu"
      saymaz.
- [ ] Uyum raporu, kapsama oranını ve kapsanmayan varlıkları birlikte taşır;
      tek bir yüzde ile özetlemez.
- [ ] Rapor, `OPEN-BNK-013` kapanmadığı sürece "düzenleyici kanıt değildir"
      ibaresini taşır.
- [ ] Eşleme oluşturma, onay ve ret olayları audit'e yazılır.
- [ ] Uyum ekranları yetkiye bağlıdır; yetkisiz aktör 403 alır.

## Eklenen Testler

| Test | Kapsam |
| --- | --- |
| `test_no_regulation_text_embedded_in_source` | Gömülü mevzuat yok (statik denetim) |
| `test_absent_framework_preserves_existing_behaviour` | Geri uyumluluk |
| `test_mapping_requires_maker_checker_approval` | Görevler ayrılığı |
| `test_control_ref_change_creates_new_rule_version` | Sürümleme |
| `test_uncovered_dataset_reported_not_assumed_compliant` | Kritik — sessiz uyum yok |
| `test_report_carries_non_regulatory_disclaimer` | Aşırı iddia engeli |
| `test_coverage_report_includes_uncovered_entities` | Rapor içeriği |
| `test_unauthorized_actor_cannot_read_compliance_view` | Yetkilendirme |

## Kalan Risk

- **Aşırı iddia riski en yüksek olan iterasyon budur.** Sistem eşlemeyi
  taşır; eşlemenin doğruluğunu banka hukuk/uyum birimi belirler. Yanlış
  eşleme, yanlış güvence üretir. Azaltım: her rapor eşleme sürümünü,
  onaylayanı ve onay tarihini taşır; onaysız eşleme rapora girmez.
- Kapsama oranı yanıltıcı olabilir: kuralı olan bir veri kümesi, yanlış
  kurala sahip olabilir. [İterasyon 42](Iterasyon-42-Sentetik-Veriyle-Kural-Kaniti.md)
  etkinlik kanıtı bu boşluğu kısmen kapatır; uyum raporu etkinlik kanıtı
  olmayan kuralları ayrı işaretlemelidir.
- `OPEN-BNK-013` olumsuz kapanırsa `CTRL-DQ-*` ailesi iç kontrol olarak
  kalır; düzenleyici raporlama iddiası tamamen düşer. Mekanizma yine
  değerlidir ancak dokümantasyon dili buna göre daraltılmalıdır.
- Kontrol çerçevesi mevzuat değiştikçe bayatlar. Çerçeve sürümüne geçerlilik
  tarihi eklenmeli, süresi geçmiş çerçeveyle üretilen rapor uyarı taşımalıdır.

## Geri Alma Yaklaşımı

- `ControlFramework` kayıtları pasifleştirilir; uyum ekranları "çerçeve
  tanımlı değil" durumuna döner. Kural ve veri kümesi işleyişi etkilenmez.
- Route'lar `app.py`'den, servis `composition.py`'den kaldırılır.
- Migration `downgrade` ile kontrol tabloları ve referans kolonları
  düşürülür. Kontrol referansı taşıyan kural sürümleri korunur; referans
  kolonu düştüğünde bağ kaybolur, kural geçerliliğini sürdürür.
- Doküman değişiklikleri git üzerinden geri alınır.

## Sınır

Bu doküman planlama kaydıdır. Regülasyon eşlemesinin doğruluğu, `CTRL-DQ-*`
ailesinin kabulü ve BCBS 239 uygulanabilirliği **banka hukuk/uyum ve risk
birimlerinin kararıdır**. Bu iterasyon eşleme mekanizmasını üretir, uyum
güvencesi üretmez; `ApprovedByBank` iddiası değildir.

## Sonraki İterasyon

- Kontrol bazlı kalite borcu (FR-109) ve borç azaltma planı
- Kontrol kapsamına giren veri kümeleri için otomatik kural önerisi
  tetiklemesi ([İterasyon 41](Iterasyon-41-Profil-Tabanli-Kural-Onerisi-ve-Shadow-Backfill.md) ile birleşim)
- Kanıt paketi üretimi (FR-111) ve olay zaman çizelgesi

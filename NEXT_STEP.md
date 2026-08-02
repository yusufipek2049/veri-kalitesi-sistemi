---
type: next-step
status: completed
updated_at: 2026-07-31
work_package: DQ-CAP-PROTOTYPE-04
predecessor: DQ-CAP-PROTOTYPE-03
---

# Sıradaki Adım — Sentetik Lineage, Sahiplik Profili ve Kaynaklı Etki Hipotezi

**Kapanış:** `DQ-CAP-PROTOTYPE-04` 2026-07-31 tarihinde `PrototypeVerified`
kapanmıştır. Sıradaki `READY` teknik paket tanımlı değildir; production ve
ürünleştirme başlıkları `ExternalDependency` olarak açık kalır.
[Kapanış kaydı](09-Iterasyonlar/DQ-CAP-PROTOTYPE-04-Sentetik-Lineage-ve-Yonetisim-Profili.md).

[Ürün Yetenekleri Prototip Kararları](00-Proje-Hafizasi/Karar-Kayitlari/Urun-Yetenekleri-Prototip-Kararlari.md)
uygulama sırasının **4. adımı** seçilmiştir: `DQ-CAP-007` (lineage, kök neden ve
etki) ile `DQ-CAP-010` (sahiplik ve yönetişim) aynı iş paketinde uygulanır.
Bağımlılıkları olan 1-3. adımlar `PrototypeVerified` kapanmıştır.

Kanonik gereksinim ve karar kaynakları:
[FR-100–FR-102](01-SRS/04-Fonksiyonel-Gereksinimler/04.14-Kanita-Dayali-Karar-Destegi.md),
[FR-009–FR-010](01-SRS/04-Fonksiyonel-Gereksinimler/04.02-Veri-Kaynagi-Yonetimi.md),
[OPEN-027, OPEN-028, OPEN-029](00-Proje-Hafizasi/Karar-Kayitlari/Skorlama-Sentetik-Veri-ve-Ikinci-Faz-Kararlari.md),
[yetenek matrisi #6 ve #9](00-Proje-Hafizasi/Urun-Yetenek-Durum-Matrisi.md).

## Kapsam

### A. Sürümlü yönetişim profili (`DQ-CAP-010`)

- Sürümlü `DataAssetGovernanceProfile`: data owner, teknik owner/steward, iş
  birimi, kritiklik, sınıflandırma, kalite hedefi/SLA, saklama ve ilişkili asset
  referansları **etkinlik aralığıyla** taşınır.
- Kurumsal katalog sistem-of-record'dur; prototip yalnız sentetik registry kullanır
  (`OPEN-028`). Uygulama rakip ana katalog kurmaz.
- Mevcut sahiplik alanları **referanslanır, kopyalanmaz**: çelişen sahip kaydı
  doğmamalıdır. Mevcut yüzeyler
  [data_sources/models.py](03-Backend/src/veri_kalitesi/data_sources/models.py),
  [data_protection/inventory.py](03-Backend/src/veri_kalitesi/data_protection/inventory.py)
  ve [retention/models.py](03-Backend/src/veri_kalitesi/retention/models.py)
  içindedir.
- Zorunlu routing alanı yoksa otomatik atama **fail-closed** olur.

### B. Lineage ve kaynaklı etki-kök neden hipotezi (`DQ-CAP-007`)

- Sentetik **OpenLineage uyumlu** sürümlü olay sözleşmesi: run/job/dataset ve
  kolon ilişkileri; W3C PROV `Entity/Activity/Agent` anlamlarına eşlenebilir
  (`OPEN-028`). Değişmez snapshot/digest, eksik veya eski kapsama durumunu saklar.
- Zaman çizgisi, **ilk gözlenen bozulma**, upstream/downstream ve benzer olaylar
  yalnız **hipotez** üretir; korelasyon doğrulanmış neden sayılmaz.
- Her etki bileşeni `Observed` / `Calculated` / `Estimated` / `Unknown` durumunu,
  kaynağını, formülünü, veri zamanını ve güvenini taşır (`OPEN-027`). Desteklenmeyen
  bileşenler tek bir toplam etki sayısında birleştirilmez. Parasal değer yalnız
  otoriter kaynağa veya onaylı formüle dayanır; yoksa `Unknown`.
- Öneri mekanizmaları yalnız `DeterministicRule`, `IncidentSimilarity` ve auditli
  `ExpertInput` (`OPEN-029`). `LLMAssisted` kapalıdır. Her öneri minimum kanıt,
  mekanizma/sürüm, bağımsız güven ve karşı kanıt taşır.
- İnsan tarafından girilen kök neden ([issues/models.py](03-Backend/src/veri_kalitesi/issues/models.py)
  `root_cause`) makine hipoteziyle **değiştirilmez**; ayrı alan olarak durur.

### C. Tüketim

- PROTOTYPE-03'ün `UNKNOWN` bıraktığı kritik asset/risk/SLA alanları, kanıt varsa
  yönetişim profilinden beslenir; yoksa `UNKNOWN` kalır.
  Yüzeyler: [dashboard/service.py](03-Backend/src/veri_kalitesi/dashboard/service.py),
  [dashboard/model.ts](04-Frontend/app/src/dashboard/model.ts).

## İzlenecek Desen

PROTOTYPE-03 deseni kanoniktir: saf/deterministik domain modülü, ayrı
`postgresql_*` snapshot repository'si, tek alembic migration, birim testi ve
skipsiz PostgreSQL entegrasyon testi. Referanslar:
[scoring/contributions.py](03-Backend/src/veri_kalitesi/scoring/contributions.py),
[scoring/postgresql_contributions.py](03-Backend/src/veri_kalitesi/scoring/postgresql_contributions.py),
[audit/postgresql_outbox.py](03-Backend/src/veri_kalitesi/audit/postgresql_outbox.py).
Yeni migration `down_revision = "20260730_13"` üzerine gelir.

## Kabul Kriterleri

| ID | Gereksinim |
| --- | --- |
| AC-01 | Sürümlü yönetişim profili etkinlik aralığıyla üretilir; zorunlu routing alanı yoksa atama fail-closed olur. |
| AC-02 | Mevcut sahiplik alanları referanslanır; çelişen ikinci sahip kaydı üretilmez. |
| AC-03 | Lineage olayı OpenLineage uyumlu, sürümlü ve değişmez snapshot/digest ile saklanır; eksik/eski kapsama durumu kaydedilir. |
| AC-04 | Kök neden çıktısı hipotezdir; korelasyon doğrulanmış neden olarak sunulmaz ve insan kaydını ezmez. |
| AC-05 | Etki bileşenleri `Observed`/`Calculated`/`Estimated`/`Unknown` + kaynak/formül/veri zamanı/güven taşır; desteklenmeyenler toplanmaz. |
| AC-06 | Öneriler yalnız `DeterministicRule`/`IncidentSimilarity`/auditli `ExpertInput`; her biri kanıt, mekanizma sürümü, güven ve karşı kanıt taşır. |
| AC-07 | Kritik yazımlar audit/outbox ile atomik tamamlanır; politika veya kanıt eksikse güvenli olumlu sonuç üretilmez. |
| AC-08 | Birim test paketi exit 0; PostgreSQL etkilendiği için entegrasyon testleri skipsiz exit 0. |
| AC-09 | Yeni eşik, ağırlık, iş kuralı veya gereksinim uydurulmaz; kaynağı olmayan alan `UNKNOWN` kalır. |

## Sınırlar

Bu paket **prototiptir**. Yalnız sentetik veri, fake/sandbox hedef ve yerel kurulum
kullanılır. Kurumsal veri kataloğu, gerçek lineage kaynağı, Finans/Risk otoriter
etki kaynağı ve banka onayı `ExternalDependency` olarak açık kalır; sonuç
`PrototypeVerified` üstü bir durum üretmez.

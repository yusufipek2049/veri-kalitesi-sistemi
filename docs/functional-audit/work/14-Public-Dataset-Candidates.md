---
type: functional-audit-work
stage: "14 — Halka Açık Kaynak Adayları ve Eleme"
scope: public-dataset-candidates
inputs:
  - 13-Slice-DS03-Change-Inventory.md
  - ../04-Functional-Gap-Inventory.md
  - ../07-Target-Data-Model.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-05
---

# 14 — Halka Açık Kaynak Adayları ve Eleme

> Bu belge, gerçekçi bir şema/alan külliyatı için aday halka açık kaynakları
> envanterler, iki kapıdan (lisans, KVKK) geçirir ve kabul/ret kararını gerekçesiyle
> dondurur. Kod veya tohumlama tasarımı içermez; onlar `15` ve `16` numaralı
> belgelerdedir.

---

## 1. Neden bu çalışma yapılıyor

Bugünkü geliştirme verisi `DEVELOPMENT_SOURCES` içinde dört kaynaktan ibarettir ve
üçü de içi boştur: `connection_config={}` ve `secret_reference="development-reference-only"`
(`src/veri_kalitesi/api/development.py:145-178`). Alan adları
`field-customer-id` ve benzeri yer tutuculardır
(`src/veri_kalitesi/api/development.py:186`).

Bu veri iki işi birden yapamaz:

| İhtiyaç | Bugünkü verinin yetersizliği |
|---|---|
| Bankaya ürün gösterimi | `dataset-customer` / `field-customer-id` gibi adlar gerçek bir bankacılık şemasına benzemiyor |
| AI önerisinin ölçümü | Alan adını da etiketini de biz koyduğumuz için ölçüm döngüsel; isabet oranı hiçbir şey ifade etmez |

İkinci maddenin çözümü bir veri seti satın almak değil, **adı üreten ile etiketi
koyanı ayırmaktır**. Bu nedenle aşağıdaki kaynaklardan istediğimiz şey ağırlıkla
**satır değil şemadır**.

---

## 2. Uygulanan iki kapı

**Lisans kapısı.** Ticari kullanıma ve türev çalışmaya izin veriyor mu? Atıf
zorunluluğu var mı? "Non-commercial" / "research only" kaynaklar bir banka ürününde
kullanılamaz. Lisans, hatırlanan bir isim değil, **erişilen sayfada veya lisans
dosyasında görülen metin** esas alınarak yazılmıştır.

**KVKK kapısı.** Gerçek kişisel veri içeriyor mu? "Halka açık olması" kişisel veriyi
bankaya yüklemeyi meşru kılmaz. Gerçek kişisel veri içeren kaynaklardan **yalnız şema**
alınır, satır alınmaz.

Üçüncü ve örtük bir kapı olarak **kanıtlanabilirlik** uygulanmıştır: erişilemeyen ya
da şartları sayfada görülemeyen kaynak, "muhtemelen uygundur" gerekçesiyle kabul
edilmemiştir.

---

## 3. Aday envanteri — karar tablosu

Tüm erişimler **2026-08-05** tarihinde yapılmıştır.

| # | Kaynak | Ne alınıyor | Lisans (görülen) | Lisans kapısı | KVKK kapısı | Ölçülen büyüklük | Karar |
|---|---|---|---|---|---|---|---|
| 1 | Apache Fineract | Şema | Apache License 2.0 | Geçti | Geçti (satır alınmıyor) | 220 tablo / 2.062 kolon / 941 benzersiz kolon adı | **Kabul — P1** |
| 2 | Microsoft Presidio | Tanıyıcı kataloğu | MIT | Geçti | Geçti | `__all__` içinde 99 girdi | **Kabul — P2** |
| 3 | BDDK Aylık Bülten Metaveri | Tablo/gösterge adları | DOĞRULANMADI | Koşullu | Geçti (toplulaştırılmış) | 18 tablo | **Kabul — P3 (koşullu)** |
| 4 | UK Open Banking Read/Write API | Alan adları | MIT | Geçti | Geçti | Ölçülmedi | **Kabul — P4** |
| 5 | Berlin Group NextGenPSD2 (OpenAPI dosyaları) | Alan adları | CC BY 4.0 | Geçti | Geçti | Ölçülmedi | **Kabul — P4** |
| 6 | Great Expectations | Kural kataloğu | Apache License 2.0 | Geçti | Geçti | 33 çekirdek expectation | **Kabul — P5** |
| 7 | UCI Bank Marketing | Şema (kolon başlıkları) | CC BY 4.0 | Geçti (atıf zorunlu) | Geçti (yalnız şema) | 45.211 satır / 16 öznitelik | **Kabul — P6, yalnız şema** |
| 8 | UCI Statlog German Credit | Şema (kolon başlıkları) | CC BY 4.0 | Geçti (atıf zorunlu) | Geçti (yalnız şema) | 1.000 satır / 20 öznitelik | **Kabul — P6, yalnız şema** |
| 9 | AWS Deequ | Kural kavramları | Apache License 2.0 | Geçti | Geçti | Ölçülmedi | Kabul — referans, tohum kapsamı dışı |
| 10 | dbt-expectations | Kural kavramları | Apache License 2.0 | Geçti | Geçti | Ölçülmedi | Kabul — referans, tohum kapsamı dışı |
| 11 | Berlin Group spesifikasyon metni (PDF) | — | CC BY-**ND** 4.0 | **Kaldı** | — | — | **Reddedildi** |
| 12 | Soda Core | — | Elastic License 2.0 | **Kaldı** | — | — | **Reddedildi** |
| 13 | Odoo | — | LGPLv3 | Kaldı (tercihen) | — | Ölçülmedi | **Reddedildi** |
| 14 | ERPNext | — | GPLv3 | Kaldı (tercihen) | — | Ölçülmedi | **Reddedildi** |
| 15 | Cyclos | — | DOĞRULANMADI | **Kaldı** | — | — | **Reddedildi** |
| 16 | Google Cloud Sensitive Data Protection infoTypes | — | DOĞRULANMADI | **Kaldı** | — | — | **Reddedildi (kopyalama kaynağı olarak)** |
| 17 | AWS Macie managed data identifiers | — | DOĞRULANMADI | **Kaldı** | — | — | **Reddedildi (kopyalama kaynağı olarak)** |
| 18 | TCMB EVDS | — | DOĞRULANMADI | Kaldı | — | Okunamadı | **Reddedildi — kapsam uyumsuz** |
| 19 | Kaggle banka veri setleri | — | İncelenmedi | — | — | — | **Reddedildi — tek tek doğrulanmadı** |

---

## 4. Kabul edilen kaynaklar — gerekçeli detay

### 4.1 P1 — Apache Fineract

- **URL:** https://github.com/apache/fineract — erişim 2026-08-05
- **Lisans dosyası:** https://raw.githubusercontent.com/apache/fineract/develop/LICENSE_SOURCE — erişim 2026-08-05.
  Dosyanın başlığı birebir: `Apache License / Version 2.0, January 2004`.
  Depo ana sayfası da "This project is licensed under Apache License Version 2.0" demektedir.
- **Ne alınıyor:** yalnız şema. Ölçüm, `develop` dalındaki baseline changelog dosyası
  üzerinden yapılmıştır:
  `fineract-provider/src/main/resources/db/changelog/tenant/parts/0001_initial_schema.xml`
- **Ölçüm (XML ayrıştırılarak sayıldı, tahmin değildir):** 220 `createTable`,
  2.062 kolon tanımı, 941 benzersiz kolon adı.

Bu kaynak birinci sıradadır çünkü diğerlerinin hiçbiri aynı anda şu üçünü sağlamıyor:
gerçek üretim çekirdek bankacılık domeni, izin verici lisans, ve makine tarafından
ayrıştırılabilir tam şema. Kolon adları da tam ihtiyaç duyduğumuz kalitede — hem açık
hem kirli:

```
m_client (45 kolon): id, account_no, external_id, status_enum, sub_status,
activation_date, office_id, staff_id, firstname, middlename, lastname, fullname,
display_name, mobile_no, is_staff, gender_cv_id, date_of_birth, image_id,
closure_reason_cv_id, ..., legal_form_enum, email_address, proposed_transfer_date
```

`gender_cv_id`, `loanpurpose_cv_id`, `glim_id`, `gsim_id`, `status_enum` gibi adlar
ölçüm seti için **kasıtlı olarak değerlidir**: bunlar bir insanın anlamını hemen
çıkaramadığı, eski sistem kokusu taşıyan gerçek adlardır (bkz. `16`, §5).

**KVKK:** Fineract'ten satır alınmıyor; alınan şey DDL'dir. `firstname`,
`date_of_birth`, `mobile_no` gibi kolonlar **ad olarak** taşınır, içerik olarak değil.

### 4.2 P2 — Microsoft Presidio

- **URL:** https://github.com/microsoft/presidio — erişim 2026-08-05
- **Lisans:** https://raw.githubusercontent.com/microsoft/presidio/main/LICENSE —
  ilk satırı birebir: `The MIT License (MIT)`. Erişim 2026-08-05.
- **Varlık listesi:** https://presidio.dataprivacystack.org/supported_entities/ —
  erişim 2026-08-05. (Not: `microsoft.github.io/presidio` adresi buraya yönlendiriyor.)

Türkiye bağlamı için belirleyici bulgu: Presidio **TR_NATIONAL_ID** ("unique 11-digit
number issued to all Turkish citizens") ve **TR_LICENSE_PLATE** varlıklarını
içermektedir. Kaynak kodda karşılıkları `TrNationalIdRecognizer` ve
`TrLicensePlateRecognizer` olarak
`presidio-analyzer/presidio_analyzer/predefined_recognizers/__init__.py` içindeki
`__all__` listesinde görülmüştür (erişim 2026-08-05).

**Kritik kullanım kısıtı:** Presidio bu belgede **etiketin kaynağı olarak değil**,
etiketleyiciye aday üreten ve etiket donduktan sonra çapraz kontrol yapan araç olarak
kabul edilmiştir. Gerekçesi `16`, §4'tedir — AI özelliği de örüntü tabanlı çalışıyorsa
Presidio'yu cevap anahtarı yapmak yeni bir döngüsellik yaratır.

### 4.3 P3 — BDDK Aylık Bankacılık Sektörü Verileri (koşullu kabul)

- **URL:** https://www.bddk.org.tr/Veri/Detay/159 — erişim 2026-08-05
- **Metaveri belgesi:** https://www.bddk.org.tr/BultenDosyalari/Home/Index/Aylik-MetaVeri
  — 7 sayfalık PDF, erişim 2026-08-05.

Belgeden birebir alınan tablo listesi (18 kalem):

Bilanço, Kar Zarar, Krediler, Tüketici Kredileri, Sektörel Kredi Dağılımı, KOBİ
Kredileri, Sendikasyon Seküritizasyon Kredileri, Menkul Kıymetler, Mevduat Türler
İtibarıyla, Mevduat Vade İtibarıyla, Likidite Durumu, Sermaye Yeterliliği, Yabancı
Para Pozisyonu, Bilanço Dışı İşlemler, Rasyolar, Diğer Bilgiler, Yurt Dışı Şube
Rasyoları, Fonksiyon grubu.

Aynı belge verinin kaynağını da açıklıyor: veriler bankalardan "BDDK Veri Transfer
Sistemi (BVTS) aracılığıyla periyodik olarak" alınmakta ve "geçici gözetim raporları"
kullanılmaktadır. Yani bunlar gerçek düzenleyici raporlama başlıklarıdır ve Türkçe'dir
— ürün gösterimi açısından en değerli tarafı budur.

**Koşul:** BDDK sayfalarında yeniden kullanım lisansı **görülmemiştir**. Bu nedenle
kabul yalnız **tablo/gösterge adlarının olgusal olarak kullanılması** kapsamındadır;
BDDK belgelerinin metni kopyalanmayacak, PDF depoya konmayacaktır. Ad listesi bir
olgudur ve telif konusu değildir; belge metni değildir.

**KVKK:** Bültende yayımlanan veri sektör toplulaştırmasıdır, kişi düzeyinde değildir.
Zaten satır alınmamaktadır.

### 4.4 P4 — Açık bankacılık standartları

**UK Open Banking Read/Write API**
- **URL:** https://openbankinguk.github.io/read-write-api-site3/ — erişim 2026-08-05
- **Lisans:** https://www.openbanking.org.uk/open-licence/ — erişim 2026-08-05.
  Sayfa MIT lisans metnini sunmaktadır: "Permission is hereby granted, free of charge,
  to any person obtaining a copy of this software... to use, copy, modify, merge,
  publish, distribute, sublicense, and/or sell copies". Telif bildirimi Open Banking
  Limited'e aittir.
- Tanımlı kaynaklar: Accounts, Balances, Transactions, Beneficiaries, Direct Debits,
  Standing Orders, Products, Offers, Parties, Scheduled Payments, Statements.

**Berlin Group NextGenPSD2**
- **URL:** https://www.berlin-group.org/nextgenpsd2-downloads — erişim 2026-08-05
- Burada **lisans ikiye ayrılmaktadır** ve ayrım bizim için belirleyicidir:
  - Spesifikasyon belgesi: **CC BY-ND 4.0** — türev dağıtımı yasak.
  - OpenAPI (YAML) dosyaları: **CC BY 4.0** — değiştirmeye izin veriyor.
- **Karar:** yalnız **OpenAPI dosyaları** kabul edilmiştir (satır 5). Spesifikasyon
  PDF'i ND kaydı nedeniyle reddedilmiştir (satır 11). İhtiyacımız olan makine okunur
  alan adları zaten CC BY 4.0 tarafındadır; ND tarafına girmeye gerek yoktur.

### 4.5 P5 — Great Expectations

- **URL:** https://github.com/great-expectations/great_expectations — erişim 2026-08-05
- **Lisans:** `.../develop/LICENSE` — başlığı `Apache License, Version 2.0`. Erişim 2026-08-05.
- **Ölçüm:** `great_expectations/expectations/core/__init__.py` (`develop` dalı,
  erişim 2026-08-05) içinde **33 benzersiz expectation sınıfı** içe aktarılmaktadır.

Bu 33 kalem `RuleType` kapalı listesiyle karşılaştırıldığında iki gerçek boşluk
görünür hale gelmektedir — ikisi de `16` ve `15` için girdi niteliğindedir:

| Great Expectations | `RuleType` karşılığı |
|---|---|
| `ExpectColumnValuesToNotBeNull` | `REQUIRED` |
| `ExpectColumnValuesToBeUnique`, `ExpectCompoundColumnsToBeUnique` | `UNIQUE` |
| `ExpectColumnValuesToBeBetween`, `ExpectColumnMaxToBeBetween` | `RANGE` |
| `ExpectColumnValuesToMatchRegex`, `ExpectColumnValuesToMatchRegexList` | `REGEX` |
| `ExpectColumnPairValuesToBeEqual`, `ExpectMulticolumnSumToEqual` | `CROSS_TABLE_CONSISTENCY` |
| `UnexpectedRowsExpectation`, `ExpectQueryResultsToMatchComparison` | `CUSTOM_SQL` |
| `ExpectColumnValuesToBeInSet` | **Temiz karşılığı yok** — `REGEX` zorlaması ya da `CUSTOM_SQL` |
| *(karşılığı yok)* | **`FRESHNESS`** — GE çekirdeğinde tazelik expectation'ı yok |
| *(karşılığı yok)* | **`REFERENTIAL_INTEGRITY`** — GE çekirdeğinde yok |

Bu tabloyu, `RuleType`'a yeni değer eklemek için değil, tam tersi için kaydediyoruz:
mevcut kapalı liste GE'nin kapsamını **karşılamaktadır**; iki yönde de eksik kalan
yerler ölçüm setinde bilinçli olarak temsil edilecektir (`16`, §3.2). `RuleType`'a
yeni değer önerilmemektedir.

### 4.6 P6 — UCI veri setleri (yalnız şema)

| Kaynak | URL | Lisans | Ölçek |
|---|---|---|---|
| Bank Marketing | https://archive.ics.uci.edu/dataset/222/bank+marketing | CC BY 4.0 | 45.211 örnek / 16 öznitelik |
| Statlog German Credit | https://archive.ics.uci.edu/dataset/144/statlog+german+credit+data | CC BY 4.0 | 1.000 örnek / 20 öznitelik |

İkisi de 2026-08-05 tarihinde erişilmiştir. Her iki sayfa lisansı "Creative Commons
Attribution 4.0 International (CC BY 4.0)" olarak vermektedir.

Bank Marketing öznitelik adları sayfada birebir şöyledir: `age`, `job`, `marital`,
`education`, `default`, `balance`, `housing`, `loan`, `contact`, `day_of_week`,
`month`, `duration`, `campaign`, `pdays`, `previous`, `poutcome`.

**Neden yalnız şema:** Bu adların bir kısmı (`age`, `job`, `marital`, `education`)
kişiye ilişkin niteliklerdir. Sayfalar bu satırların gerçek kişilere mi ait olduğunu,
anonimleştirilmiş mi olduğunu **açıkça yazmamaktadır** (bkz. §6). Belirsizlik lehimize
yorumlanmaz: **satır alınmaz, yalnız kolon başlıkları alınır.** Bu, KVKK kapısını
tartışmasız hale getirir ve zaten ihtiyacımız olan tek şeydir.

CC BY 4.0 atıf zorunluluğu doğurur; atıf yükümlülüğünün nerede karşılanacağı `15`, §7'de
belirlenmiştir.

---

## 5. Reddedilenler ve gerekçeleri

| Kaynak | Gerekçe |
|---|---|
| **Berlin Group spesifikasyon PDF'i** | CC BY-ND 4.0. "if you remix, transform, or build upon the Specification, you may not distribute the modified Specification." Alan adlarını çıkarıp kendi külliyatımıza dönüştürmek tam olarak türev üretmektir. İhtiyaç, CC BY 4.0 lisanslı OpenAPI dosyalarından zaten karşılanıyor; ND riskine girmenin karşılığı yok. |
| **Soda Core** | Lisans dosyasının ilk satırı: `Elastic License 2.0`. Metinde birebir: "You may not provide the software to third parties as a hosted or managed service". Bir banka ürününde bu kısıtı taşımanın bedeli, Great Expectations'ın (Apache-2.0) aynı kural külliyatını zaten kapsaması karşısında gereksizdir. Kavramsal olarak yeni bir şey vermediği için reddedilmiştir. |
| **Odoo** | `LICENSE` dosyası: "Odoo is published under the GNU LESSER GENERAL PUBLIC LICENSE, Version 3 (LGPLv3)". Copyleft. Tablo adlarının olgu olduğu ve copyleft'in bunlara sirayet etmeyeceği savunulabilir; ancak bu tartışmayı banka hukuk birimine taşımanın karşılığı yok — Fineract aynı ihtiyacı Apache-2.0 ile ve daha yakın bir domende (çekirdek bankacılık, ERP değil) karşılıyor. |
| **ERPNext** | `license.txt`: `GNU GENERAL PUBLIC LICENSE Version 3`. Odoo ile aynı gerekçe, daha güçlü copyleft. |
| **Cyclos** | https://www.cyclos.org/ (erişim 2026-08-05) sayfasında yalnız "open source front-end" ifadesi geçiyor; ürünün tamamı için lisans adı, kaynak kod veya şema erişimi **belirtilmemiş**. Doğrulanamayan lisans kabul edilmez. |
| **Google Cloud SDP infoTypes** | İçerik doğrulandı — `TURKEY_ID_NUMBER` infoType'ı mevcuttur (https://docs.cloud.google.com/sensitive-data-protection/docs/infotypes-reference, erişim 2026-08-05). Ancak dokümantasyon içeriğinin yeniden kullanım şartları sayfada yazmıyor. Liste **kopyalanmayacaktır**. |
| **AWS Macie** | İçerik doğrulandı (https://docs.aws.amazon.com/macie/latest/user/mdis-reference-quick.html, erişim 2026-08-05). Türkiye için yalnız `TURKIYE_BANK_ACCOUNT_NUMBER` (IBAN) vardır; ulusal kimlik numarası tanıyıcıları listesinde (`ARGENTINA_DNI_NUMBER`, `FRANCE_NATIONAL_IDENTIFICATION_NUMBER`, ... ) **Türkiye yoktur**. Hem şartları doğrulanamadığı hem de TR kapsamı Presidio'nun gerisinde kaldığı için reddedilmiştir. |
| **TCMB EVDS** | https://evds2.tcmb.gov.tr/ adresi https://evds3.tcmb.gov.tr/ adresine yönlendiriyor; hedef sayfa istemci tarafında oluşturulan bir uygulama olduğu için içeriği okunamadı (erişim 2026-08-05). Ayrıca kapsam uyumsuz: EVDS makro zaman serisi yayımlar, banka kaynak sistem şeması değil. Erişilebilse dahi bu belgenin amacına hizmet etmezdi. |
| **Kaggle banka veri setleri** | Kaggle'da lisans **veri seti başına** değişir ve önemli bir kısmı yeniden dağıtıma kapalıdır. Tek tek doğrulamadan toplu kabul edilemez. Hiçbir Kaggle veri seti bu çalışmada açılmamıştır; dolayısıyla hiçbiri listelenmemiştir. |

---

## 6. Doğrulanamayanlar

Bu bölüm kasten uzundur. Aşağıdakiler tahmin edilmemiş, boş bırakılmıştır.

1. **BDDK verisinin yeniden kullanım lisansı.** Ne ana sayfada ne Aylık Bülten
   sayfasında ne de Metaveri PDF'inde lisans/telif/atıf ifadesi görülmedi. PDF'te
   "lisans" kelimesinin geçtiği tek yer personelin öğrenim durumudur. **DOĞRULANMADI.**
2. **BDDK sunucusunun TLS zinciri eksiktir.** `www.bddk.org.tr` yalnız yaprak
   sertifikayı sunmakta, ara sertifikayı sunmamaktadır; standart doğrulama
   `unable to verify the first certificate` ile başarısız olur. Sayfalara erişmek için
   sertifika doğrulaması devre dışı bırakılmıştır. Bu, içeriğin kaynağının
   kriptografik olarak teyit edilmediği anlamına gelir.
3. **UCI veri setlerinin gerçek kişisel veri içerip içermediği.** Her iki sayfa da
   bunu açıkça yazmıyor. "Anonimleştirilmiştir" ifadesi **hiçbir sayfada
   görülmemiştir**. Bu yüzden satır alınmamaktadır — belirsizlik varsayımla
   kapatılmamıştır.
4. **Google Cloud dokümantasyonunun yeniden kullanım şartları.** infoType listesinin
   içeriği doğrulandı, şartları doğrulanamadı. `developers.google.com/site-policies`
   adresi yönlendirme verdi ve okunamadı. **DOĞRULANMADI.**
5. **AWS dokümantasyonunun yeniden kullanım şartları.** Aynı durum. **DOĞRULANMADI.**
6. **Cyclos'un lisansı.** **DOĞRULANMADI.**
7. **TCMB EVDS'nin içeriği ve kullanım şartları.** Sayfa okunamadı. **DOĞRULANMADI.**
8. **Odoo ve ERPNext şema büyüklükleri ölçülmedi.** Lisansları doğrulandı ama zaten
   reddedildikleri için alan sayımı yapılmamıştır. Tablo/kolon sayısı **boş
   bırakılmıştır**, tahmin yazılmamıştır.
9. **Fineract commit SHA'sı sabitlenmedi.** Ölçüm `develop` dalının 2026-08-05
   tarihindeki hâli üzerinden yapılmıştır. GitHub API kota sınırına takıldığı için
   commit SHA alınamadı. Sayılar bu tarihe aittir; dal ilerledikçe değişebilir.
   Sabitleme `15`, §6'da bir gereklilik olarak yazılmıştır.
10. **Presidio "99" sayısı tanıyıcı sayısı değildir.** `__all__` listesindeki girdi
    sayısıdır ve içinde en az bir tanesi (`NLP_RECOGNIZERS`) tanıyıcı sınıfı değil,
    bir gruplamadır. Gerçek tanıyıcı sınıfı sayısı **ölçülmemiştir**.
11. **Presidio belgelerindeki "20 ülke/bölge" ifadesi** sayfanın özetinden gelmektedir;
    tek tek sayılmamıştır.
12. **Great Expectations'ın 33 sayısı yalnız çekirdektir.** Topluluk katkısı
    expectation'ları içeren galeri (`greatexpectations.io/expectations/`) okunamadı —
    sayfa içeriği istemci tarafında oluşuyor. Toplam expectation sayısı
    **DOĞRULANMADI.**
13. **UK Open Banking ve Berlin Group alan sayıları ölçülmedi.** Kaynakların varlığı ve
    lisansları doğrulandı; alan sayımı yapılmadı. `15`, §3'te bu ölçüm bir ön koşul
    olarak planlanmıştır.
14. **UK Open Banking lisansının her spesifikasyon dosyasına iliştiği doğrulanmadı.**
    Merkezî "open licence" sayfası MIT metnini veriyor; tek tek dosya başlıkları
    kontrol edilmedi.
15. **Berlin Group'un güncel sürüm numarası** sayfada net görülemedi; sayfa
    "Last updated: 02 December 2025" diyor. Sürüm numarası **DOĞRULANMADI.**

---

## 7. Hariç

Bu belge kapsamı dışındadır:

- Tohumlama tasarımı, `DEVELOPMENT_SOURCES` ile ilişki ve migration kararı → `15`.
- AI ölçüm seti tasarımı, etiketleme protokolü ve eşikler → `16`.
- Kaynaklardan veri **çekme** kodu. Bu belge hiçbir indirme/dönüştürme kodu
  önermemektedir.
- Kaggle ve Türkiye açık veri portallarının taranması. Yapılmadı; yapılmadığı için de
  hiçbir aday listelenmedi.
- Sentetik veri üretiminin kendisi. Mevcut `synthetic_data` modülü (`src/veri_kalitesi/synthetic_data/`)
  bu belgenin konusu değildir; `16`, §6'da kusur enjeksiyonu bağlamında ele alınmıştır.

---

## 8. Doğrulama

Bu belgedeki iddialar aşağıdaki adımlarla yeniden sınanabilir. Her adım tek başına
çalıştırılabilir ve bir sayıyı ya da metni yeniden üretir.

1. **Fineract lisansı.**
   `curl -sS https://raw.githubusercontent.com/apache/fineract/develop/LICENSE_SOURCE | head -3`
   → `Apache License / Version 2.0, January 2004` görülmelidir.

2. **Fineract şema ölçümü.** `0001_initial_schema.xml` indirilip `createTable`
   düğümleri ve altlarındaki `column` düğümleri sayılır. §3'teki 220 / 2.062 / 941
   sayıları yeniden üretilmelidir. Sayılar tutmuyorsa `develop` dalı ilerlemiş
   demektir; §6.9'daki SHA sabitleme gereği devreye girer.

3. **Presidio TR kapsamı.** https://presidio.dataprivacystack.org/supported_entities/
   sayfasında `TR_NATIONAL_ID` ve `TR_LICENSE_PLATE` aranır. Ayrıca
   `predefined_recognizers/__init__.py` içinde `TrNationalIdRecognizer` görülmelidir.

4. **Macie'de TR ulusal kimlik yokluğu.** https://docs.aws.amazon.com/macie/latest/user/mdis-reference-quick.html
   sayfasında "National identification number" satırı okunur; Türkiye'nin listede
   olmadığı, buna karşılık IBAN satırında `TURKIYE_BANK_ACCOUNT_NUMBER` bulunduğu
   teyit edilir. Bu, §5'teki Macie ret gerekçesinin ikinci ayağıdır.

5. **BDDK tablo listesi.** Metaveri PDF'i indirilir, metni çıkarılır, madde imli
   liste sayılır → 18 kalem. §4.3'teki adlar birebir eşleşmelidir.

6. **BDDK TLS bulgusu.**
   `curl -sS https://www.bddk.org.tr/` doğrulama hatası vermeli;
   `openssl s_client -connect www.bddk.org.tr:443` çıktısında yalnız `0 s:` düzeyinde
   yaprak sertifika bulunmalı, ara sertifika olmamalıdır.

7. **Berlin Group lisans ayrımı.** https://www.berlin-group.org/nextgenpsd2-downloads
   sayfasında spesifikasyon için "NoDerivatives", OpenAPI dosyaları için "Creative
   Commons Attribution 4.0" ifadeleri aranır. Ayrım doğrulanamazsa satır 5'in kabulü
   geri alınmalıdır.

8. **Soda Core lisansı.**
   `curl -sS https://raw.githubusercontent.com/sodadata/soda-core/main/LICENSE | head -1`
   → `Elastic License 2.0`. "Limitations" başlığı altında hosted service kısıtı
   okunmalıdır.

9. **Great Expectations sayımı.** `expectations/core/__init__.py` içindeki
   `from .x import Y` satırlarındaki benzersiz `Y` sayısı 33 olmalıdır.

10. **UCI lisansları.** İki veri seti sayfasında da "CC BY 4.0" ifadesi görülmelidir.
    Aynı zamanda "anonymized" / "de-identified" gibi bir ifadenin **bulunmadığı**
    teyit edilmelidir — §6.3 buna dayanıyor.

11. **Kod atıflarının geçerliliği.** `development.py:145-178`, `policy.py:21-30`,
    `rules/models.py:19-27` ve `data_sources/models.py:21-28` satırlarının hâlâ
    belgede iddia edilen içeriği taşıdığı kontrol edilir.

Bir madde başarısız olursa, ilgili kaynağın kararı **kabul → askıya alınmış** durumuna
düşer ve `15` ile `16`'daki bağımlılıkları yeniden değerlendirilir.

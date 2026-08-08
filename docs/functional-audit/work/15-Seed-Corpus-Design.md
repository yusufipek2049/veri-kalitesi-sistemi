---
type: functional-audit-work
stage: "15 — Tohum Külliyatı Tasarımı"
scope: seed-corpus-design
inputs:
  - 14-Public-Dataset-Candidates.md
  - 13-Slice-DS03-Change-Inventory.md
  - ../07-Target-Data-Model.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-05
---

# 15 — Tohum Külliyatı Tasarımı

> `14`'te kabul edilen kaynakların sisteme nasıl tohum verisi olarak gireceğini
> dondurur. Hangi alt küme alınır, mevcut dört kaynağa ne olur, hangi kapalı listeye
> eşlenir, tohumlama nasıl idempotent olur ve veritabanında ne değişir.
> Uygulama kodu içermez.

---

## 1. Karar özeti

| Konu | Karar |
|---|---|
| Alınan kaynak sayısı | 6 (Fineract, BDDK, UK Open Banking, Berlin Group OpenAPI, UCI ×2) |
| Mevcut `DEVELOPMENT_SOURCES` | Dördü de **korunur**; kimlikleri ve durumları değişmez, içerikleri zenginleşir |
| Yeni tablo | **Yok** |
| Yeni kolon | **Yok** |
| Yeni migration | **Gerekli — `20260805_17`**, ancak tohum için değil: iki mevcut CHECK kısıtı kod ile uyumsuz (bkz. §6) |
| `down_revision` | `20260805_16` |
| Alınan satır sayısı | **Sıfır.** Hiçbir kaynaktan veri satırı alınmaz |
| Tohumlama tekrarı | İdempotent; doğal anahtar + deterministik kimlik (bkz. §5) |

---

## 2. Kapsam: ne alınıyor, ne alınmıyor

`14`, §2'de kurulan ayrım burada operasyonel hâle getirilir.

| Kaynak | Alınan | Alınmayan |
|---|---|---|
| Apache Fineract | Tablo adı, kolon adı, kolon tipi, nullability | Hiçbir satır; hiçbir varsayılan veri (`0002_initial_data.xml` dosyasına dokunulmaz) |
| BDDK Aylık Bülten | Tablo/gösterge adları (18 kalem) | Bülten değerleri, PDF metni, herhangi bir dosya |
| UK Open Banking | Kaynak ve alan adları | Örnek yükler (payload) |
| Berlin Group (OpenAPI) | Şema alan adları ve tipleri | Spesifikasyon PDF'inden hiçbir şey |
| UCI Bank Marketing | 16 kolon başlığı ve tipi | 45.211 satırın tamamı |
| UCI German Credit | 20 öznitelik adı | 1.000 satırın tamamı |

Bu tablo, `15`'in en önemli cümlesini üretir: **sisteme giren şey bir veri kümesi
değil, bir ad ve tip listesidir.** Profil metrikleri, satır sayıları ve kusurlar
sonradan mevcut `synthetic_data` modülü tarafından üretilecektir
(`src/veri_kalitesi/synthetic_data/`), gerçek satırlardan değil.

---

## 3. Alınacak alt küme ve gerekçesi

### 3.1 Fineract — 14 tablo / 410 kolon

Fineract'in 220 tablosunun tamamı alınmaz; ürün ekranını doldurmak için gereksiz,
ölçüm seti için ise gürültülüdür. Aşağıdaki alt küme çekirdek bankacılık akışının
tamamını (müşteri → ürün → hesap → işlem → muhasebe) temsil eder ve
**2026-08-05 tarihinde ölçülmüştür**:

| Fineract tablosu | Kolon | Neden bu tablo |
|---|---:|---|
| `m_client` | 45 | Müşteri ana verisi; en yoğun kişisel veri barındıran tablo |
| `m_loan` | 108 | En geniş tablo; sınıflandırma ve kural önerisi için en zengin yüzey |
| `m_product_loan` | 57 | Ürün parametreleri; referans veri karakteri |
| `m_savings_account` | 63 | Mevduat tarafı |
| `m_savings_account_transaction` | 19 | Hareket tablosu; `FRESHNESS` ve `TIMELINESS` kuralları için gerekli |
| `m_loan_transaction` | 20 | Hareket tablosu |
| `acc_gl_journal_entry` | 28 | Muhasebe fişi; `CROSS_TABLE_CONSISTENCY` ve mutabakat senaryolarının doğal yeri |
| `acc_gl_account` | 11 | Hesap planı |
| `m_group` | 17 | Müşteri grubu |
| `m_staff` | 14 | Personel; kişisel veri içeren ikinci tablo |
| `m_office` | 6 | Organizasyon |
| `m_payment_detail` | 7 | Ödeme kanalı detayı |
| `m_currency` | 7 | Para birimi; küçük referans tablosu |
| `m_code_value` | 8 | `*_cv_id` kolonlarının işaret ettiği kod tablosu |
| **Toplam** | **410** | |

`m_code_value`'nun listede olması bilinçlidir: Fineract'in `gender_cv_id`,
`loanpurpose_cv_id`, `client_type_cv_id` gibi kolonları bu tabloya bakar. Referans
tablosunu almadan `REFERENTIAL_INTEGRITY` kuralı yazılamaz ve `16`'daki zor vaka
tasarımı temelsiz kalır.

410 kolon, dört kaynağa yayılmış bugünkü yer tutucu alanların yerine geçmek için
fazlasıyla yeterlidir ve ölçüm seti için gereken hacmi tek başına karşılar.

### 3.2 BDDK — 18 tablo, kolon yok

`14`, §4.3'teki 18 tablo adı alınır. **Bu tablolar için kolon listesi yoktur** —
metaveri belgesi kolon düzeyinde tanım vermemektedir. Bu nedenle BDDK kaynağı,
kolonları olmayan datasetler olarak tohumlanır ve bu durum bir eksiklik değil,
**kasıtlı bir ürün senaryosudur**: "keşfi yapılmamış, yalnız tablo adları bilinen
kaynak" gerçek hayatta sık karşılaşılan bir durumdur ve sistemin metadata keşif
akışının (`metadata_discovery_results`) sergileneceği yerdir.

### 3.3 UK Open Banking ve Berlin Group — ölçüm önkoşullu

`14`, §6.13'te yazıldığı gibi bu iki kaynağın alan sayıları **henüz ölçülmemiştir**.
Karar: tohumlamaya girerler, ancak **alt küme sabitlenmeden önce ölçüm yapılmalıdır**.
Ölçülmeden alt küme yazmak, bu belgeyi tahmine dayandırmak olurdu.

Ön kapsam (ölçüm sonrası daraltılacak): UK Open Banking tarafından `Accounts`,
`Balances`, `Transactions`, `Parties`; Berlin Group tarafından bunların OpenAPI
karşılıkları. Gerekçe: bu dördü hem iki standartta ortak hem de Fineract'in
`m_savings_account` / `m_savings_account_transaction` tablolarıyla kavramsal olarak
örtüşür — aynı kavramın iki farklı adlandırma geleneğindeki hâli, `16`'daki
"eşanlamlı ama farklı adlandırılmış alan" zor vakası için gereklidir.

### 3.4 UCI — 36 kolon başlığı

Bank Marketing'in 16, German Credit'in 20 öznitelik adı alınır. Değeri, adların
**kısa, bağlamsız ve kısmen yanıltıcı** olmasıdır: `default`, `balance`, `contact`,
`duration`, `campaign`, `pdays`, `poutcome`. Bunlar bir CSV dosyasından gelen
gerçek başlıklar gibi görünür çünkü öyledirler. `16`, §5'teki "anlamı belirsiz alan"
sınıfının omurgasıdır.

---

## 4. Mevcut `DEVELOPMENT_SOURCES` ile ilişki

Bugünkü dört kaynak `src/veri_kalitesi/api/development.py:145-178`
içindedir ve altı ayrı yerden okunur (`development.py:570, 577, 581, 911, 1344`).

**Karar: dördü de korunur. Hiçbiri silinmez, kimlikleri değişmez.**

Gerekçe: `data_source_id` değerleri `development.py:1344`'te izin kümesi
(`permitted_source_ids`) üretmek için kullanılıyor ve `development.py:911`'de sözlük
anahtarı. Kimlik değiştirmek, tohum işiyle hiç ilgisi olmayan yetkilendirme ve ekran
davranışlarını kırar. Ayrıca dördü dört farklı `DataSourceStatus` taşıyor
(`ACTIVE`, `TEST_SUCCEEDED`, `INACTIVE`, `TEST_FAILED`); bu çeşitlilik ekranda durum
rozetlerini göstermek için değerlidir ve kaybedilmemelidir.

| `data_source_id` | Ad (korunur) | `SourceType` (korunur) | Durum (korunur) | Yeni içerik |
|---|---|---|---|---|
| `source-core-banking` | Temel Bankacılık | `POSTGRESQL` | `ACTIVE` | Fineract 14 tablo / 410 kolon |
| `source-customer-file` | Müşteri Dosyaları | `CSV` | `TEST_SUCCEEDED` | UCI ×2, 2 dataset / 36 kolon |
| `source-risk-mart` | Risk Veri Martı | `MSSQL` | `INACTIVE` | BDDK 18 tablo, kolonsuz |
| `source-regulatory-api` | Düzenleyici Veri Servisi | `REST` | `TEST_FAILED` | UK OB + Berlin Group (§3.3 ölçümü sonrası) |

Değişen tek şey `connection_config={}` alanıdır. Bugün boş olan bu sözlük, **gerçek
bir bağlantı bilgisi değil**, kaynağın hangi külliyattan türediğini gösteren köken
bilgisi ile doldurulur (örn. `{"corpus": "fineract", "corpus_version": "..."}`).
`secret_reference` `"development-reference-only"` olarak kalır — hiçbir kaynağa
gerçekten bağlanılmamaktadır ve bu tohum çalışması bunu değiştirmez.

**Hariç:** `DEVELOPMENT_RULES` ve `development.py`'deki diğer sabitler bu belgenin
kapsamı dışındadır. Ancak `field-customer-id` gibi alan kimliklerine atıf yapan
kurallar (`development.py:186`) yeni alan kimlikleriyle uyumsuz kalacaktır; bunun
nasıl çözüleceği kod onayı aşamasında ele alınmalı ve bu belge o bağımlılığı açıkça
kaydeder.

---

## 5. Kapalı listelere eşleme

`14`'te toplanan her şey mevcut kapalı listelere eşlenir. **Hiçbir listeye yeni değer
önerilmemektedir.**

### 5.1 `SourceType` (`src/veri_kalitesi/data_sources/models.py:21-28`)

Dört kaynak da mevcut değerlerini korur: `POSTGRESQL`, `CSV`, `MSSQL`, `REST`.
Bu dördü `20260805_15_data_source_command_slice.py:67`'deki güncel CHECK kısıtıyla
(`'POSTGRESQL','MSSQL','ORACLE','MYSQL','CSV','EXCEL','REST'`) uyumludur. Bu tarafta
sorun yoktur.

### 5.2 `DatasetType` (`data_sources/models.py:121-125`)

| Kaynak | `DatasetType` |
|---|---|
| Fineract | `TABLE` |
| BDDK | `TABLE` |
| UCI (CSV) | `FILE_SHEET` |
| UK OB / Berlin Group | `API_COLLECTION` |

**Bu eşleme bugünkü veritabanına yazılamaz.** Gerekçe §6.1'dedir.

### 5.3 `Criticality` (`data_sources/models.py:128-132`)

`m_client`, `m_loan`, `acc_gl_journal_entry` → `CRITICAL`;
`m_savings_account`, `m_loan_transaction`, `m_savings_account_transaction`,
BDDK `Sermaye Yeterliliği` / `Bilanço` → `HIGH`; kalan işlem tabloları → `MEDIUM`;
referans tabloları (`m_currency`, `m_code_value`, `m_office`) → `LOW`.

### 5.4 `ClassificationCode` (`src/veri_kalitesi/data_protection/policy.py:21-30`)

**Tohumlama hiçbir alana `UNCLASSIFIED` dışında sınıf yazmaz.**

Bu, belgenin en önemli kararlarından biridir ve `14`, §2'deki döngüsellik yasağının
doğrudan sonucudur: tohumu yazan taraf sınıfı da yazarsa, `16`'daki ölçüm daha
başlamadan çürür. Sınıflandırma etiketleri ayrı bir süreçte, ayrı kişiler tarafından
ve bu veritabanının dışında üretilir (`16`, §4).

Alan `data_fields.classification` varsayılanı zaten `'UNCLASSIFIED'`'dir
(`20260724_03_data_source_baseline.py:126-131`), dolayısıyla tohum bu kolona hiç
dokunmaz. Aynı şekilde `is_sensitive` alanı da `false` bırakılır.

### 5.5 `RuleType`, `QualityDimension`, `RuleScopeType`

Tohumlama **hiçbir kural üretmez.** Kural külliyatı (Great Expectations kaynaklı)
`16`'nın konusudur ve ölçüm setiyle birlikte tasarlanır. Tohumun kural yazması,
kural önerisi ölçümünü aynı şekilde döngüsel hâle getirirdi.

---

## 6. Veritabanı etkisi

### 6.1 Migration `20260805_17` gereklidir

Tohumlama **yeni tablo veya kolon gerektirmez**; `data_sources`, `datasets` ve
`data_fields` mevcut hâlleriyle yeterlidir. Ancak tohumlama sırasında iki mevcut CHECK
kısıtının Python enum'larıyla uyumsuz olduğu tespit edilmiştir. Bu uyumsuzluklar tohum
çalışmasının yarattığı bir şey değildir — bugün de oradadır — ama tohumlama onlara
ilk kez gerçekten çarpacak iştir.

**Uyumsuzluk 1 — `ck_datasets_dataset_type`**

| Taraf | Değerler |
|---|---|
| `DatasetType` enum (`models.py:121-125`) | `TABLE`, `VIEW`, `FILE_SHEET`, `API_COLLECTION` |
| CHECK kısıtı (`20260724_03_data_source_baseline.py:102`) | `TABLE`, `VIEW`, `FILE`, `API`, `OTHER` |

Kesişim yalnız `TABLE` ve `VIEW`'dur. `FILE_SHEET` ve `API_COLLECTION` **yazılamaz**.
§5.2'deki eşlemenin yarısı bugün veritabanı tarafından reddedilir.

**Uyumsuzluk 2 — `ck_data_fields_classification`**

| Taraf | Değerler |
|---|---|
| `ClassificationCode` enum (`policy.py:21-30`) | ..., `CUSTOMER_SECRET`, `BANK_SECRET`, **`HIGHLY_RESTRICTED`** |
| CHECK kısıtı (`20260724_03_data_source_baseline.py:144-147`) | ..., **`RESTRICTED`**, ..., `CUSTOMER_SECRET`, `BANK_SECRET` |

Kısıt, enum'da **bulunmayan** bir değere (`RESTRICTED`) izin verir ve enum'da
**bulunan** bir değeri (`HIGHLY_RESTRICTED`) reddeder. Tohum bu kolona yazmıyor (§5.4),
ama `16`'daki sınıflandırma önerisi tüm `ClassificationCode` listesine karşı ölçülecek
ve kabul edilen bir öneri kalıcılaştırılmak istendiğinde `HIGHLY_RESTRICTED`
veritabanı hatası verecektir.

`20260805_15_data_source_command_slice.py:62-70` `source_type` için aynı işi yapıp
kısıtı enum'a hizaladığından, bu iki kısıt hizalanmadan kalmış artıklardır.

**Migration `20260805_17` kapsamı:**

1. `ck_datasets_dataset_type` düşürülür ve
   `dataset_type IN ('TABLE','VIEW','FILE_SHEET','API_COLLECTION')` olarak yeniden kurulur.
2. `ck_data_fields_classification` düşürülür ve `ClassificationCode`'un dokuz değeriyle
   birebir yeniden kurulur (`RESTRICTED` çıkar, `HIGHLY_RESTRICTED` girer).
3. Her iki değişiklikten **önce** mevcut veriye ön kontrol yapılır ve uyumsuz satır
   varsa `RuntimeError` ile durulur. Bu desen icat edilmemiştir; `20260805_15`'in
   `source_type` için uyguladığı ön kontrolün (satır 40-51) aynısıdır.
4. `down_revision = "20260805_16"`.

**Kod tarafında eşzamanlı düzeltme gereklidir.** Aynı iki kısıt SQLAlchemy tablo
tanımlarında da yaşıyor: `src/veri_kalitesi/data_sources/postgresql_repository.py:148`
(`dataset_type`) ve `:176-179` (`classification`). Migration bunlarla birlikte
değişmezse şema ile kod ayrışır.

### 6.2 Tohum verisi nerede durur

| Yer | İçerik |
|---|---|
| `docs/database/tohum/kaynaklar/*.yaml` | Kaynak başına şema bildirimi: tablo adı, kolon adı, tip, nullability, köken URL'si, erişim tarihi |
| `docs/compliance/tohum-kulliyati-koken.md` | Atıf kaydı (§7) |

Külliyat dosyaları **veri değil bildirimdir** ve sürüm kontrolünde tutulur; böylece
"hangi ad nereden geldi" sorusu her zaman cevaplanabilir. Bu, `16`'daki döngüsellik
karşıtı protokolün denetlenebilmesi için zorunludur.

---

## 7. Atıf yükümlülüğü

CC BY 4.0 kaynakları (UCI ×2, Berlin Group OpenAPI) atıf zorunluluğu doğurur; Apache-2.0
(Fineract, Great Expectations) ve MIT (Presidio, UK Open Banking) bildirim korunmasını
gerektirir.

Karar: tek bir köken belgesi tutulur — `docs/compliance/tohum-kulliyati-koken.md` —
ve her kaynak için ad, URL, erişim tarihi, lisans ve alınan alt küme yazılır. Ayrıca
her külliyat YAML dosyası kendi başlığında aynı bilgiyi taşır, böylece dosya tek başına
dolaşıma girse de kökeni kaybolmaz.

---

## 8. İdempotentlik

Tohumlama aynı ortamda iki kez çalıştığında ikinci çalışma **hiçbir yeni satır
üretmemelidir**. Tasarım üç ayağa dayanır ve üçü de mevcut şemadaki gerçek kısıtları
kullanır — yeni bir mekanizma icat edilmez.

**1. Doğal anahtarlar zaten mevcut ve benzersiz:**

| Tablo | Kısıt | Kaynak |
|---|---|---|
| `data_sources` | `uq_data_sources_name` | `20260724_03_data_source_baseline.py:45` |
| `datasets` | `uq_datasets_source_namespace_name` (`data_source_id`, `namespace`, `name`) | aynı dosya, satır 95-99 |
| `data_fields` | `uq_data_fields_dataset_name` (`dataset_id`, `name`) | aynı dosya, satır 142 |

Üç seviyenin üçünde de doğal anahtar vardır; tohumlama bunlara yaslanır.

**2. Kimlikler deterministiktir.** `Dataset` ve `DataField` varsayılan olarak
`uuid4()` üretir (`models.py:212`, `models.py:224`) — bu, ikinci çalıştırmada farklı
kimlik demektir ve idempotentliği tek başına bozar. Bu nedenle tohumlama varsayılanı
**kullanmaz**; sabit bir namespace üzerinden UUIDv5 üretir:

```
data_source_id : sabit (mevcut dört kimlik korunur, §4)
dataset_id     : uuid5(TOHUM_NS, f"{data_source_id}|{namespace}|{name}")
data_field_id  : uuid5(TOHUM_NS, f"{dataset_id}|{name}")
```

Aynı girdi her zaman aynı kimliği üretir; tohum dosyası değişmedikçe kimlikler
değişmez.

**3. Yazma işlemi çakışmada güncellemedir, eklemedir değil.** Doğal anahtar üzerinden
`ON CONFLICT ... DO UPDATE` ile teknik alanlar (tip, nullability) tazelenir;
`classification` ve `is_sensitive` kolonlarına **hiç dokunulmaz** — bunlar tohumun
alanı değildir (§5.4) ve bir tohum tekrarı, insan eliyle konmuş bir sınıflandırmayı
silmemelidir.

**Silme davranışı:** Tohum dosyasından bir alan çıkarıldığında veritabanındaki karşılığı
**silinmez**. Gerekçe: `data_fields.data_field_id` başka tablolardan referans alır
(`20260724_03_data_source_baseline.py:232`) ve sessiz silme, kurallara bağlı alanları
kırar. Kaldırma, ayrı ve açık bir işlem olarak ele alınmalıdır; bu belgenin kapsamı
dışındadır.

**Sınama:** Tohumlamanın iki kez çalıştırılıp `data_sources`, `datasets`, `data_fields`
satır sayılarının ve tüm kimliklerin birebir aynı kaldığının doğrulanması — §10, madde 4.

---

## 9. Gerçek kişisel verinin sisteme girmediği nasıl garanti edilir

Niyet beyanı garanti değildir. Dört mekanizma katmanlı olarak çalışır:

1. **Külliyat biçimi satır taşıyamaz.** `docs/database/tohum/kaynaklar/*.yaml`
   şeması yalnız `tablo`, `kolon`, `tip`, `nullable`, `koken_url`, `erisim_tarihi`
   alanlarını tanır. Örnek değer, satır listesi veya veri bloğu için **alan yoktur**.
   Bir satırı bu formata sokmak mümkün değildir.
2. **Yükleyici yalnız üç tabloya yazar.** Tohumlama `data_sources`, `datasets`,
   `data_fields` dışına yazmaz. Bu üç tablonun hiçbirinde veri satırı tutulmaz;
   yalnız metadata tutulur. Veri satırı tutabilecek tek yer profil ve sentetik veri
   tablolarıdır ve tohumlama oralara dokunmaz.
3. **Kaynak seçimi zaten satır getirmiyor.** §2'deki tablo, satır alınan tek bir
   kaynak dahi olmadığını gösterir. UCI'nin CSV dosyaları **indirilmez**; yalnız
   başlık satırındaki adlar elle külliyata yazılır.
4. **Sınama ile bağlanır.** Tohumlama sonrası çalışan bir kontrol, külliyattan gelen
   hiçbir dizgenin bir kişi adı, TCKN, IBAN veya telefon örüntüsüne uymadığını
   doğrular. Burada `14`, §4.2'de kabul edilen Presidio, **ölçüm aracı olarak değil,
   güvenlik ağı olarak** kullanılır — `TR_NATIONAL_ID` gibi varlıklar külliyat metninde
   tetiklenirse tohumlama durur. Bu kullanım `16`'daki etiketleme sürecinden tamamen
   ayrıdır ve döngüsellik yaratmaz, çünkü burada ölçülen bir AI çıktısı yoktur.

**Kalan risk, dürüstçe:** Fineract'in kolon **adları** (`firstname`, `date_of_birth`,
`email_address`, `mobile_no`) sisteme girer. Bunlar kişisel veri değil, kişisel veri
tutan bir kolonun adıdır. Ayrım bilinçlidir ve zaten tüm çalışmanın amacıdır: sistemin
"bu kolon `PERSONAL_DATA`" diyebilmesi için kolonun adını görmesi gerekir, içeriğini
değil.

---

## 10. Hariç

- Tohumlama kodu, yükleyici ve YAML şemasının kendisi. Ayrı onayla yazılacaktır.
- `DEVELOPMENT_RULES` ve mevcut kuralların yeni alan kimliklerine taşınması (§4 sonu).
- Gerçek bağlantı yapılandırması. `secret_reference` `"development-reference-only"`
  kalır; hiçbir kaynağa bağlanılmaz.
- Profil metrikleri ve sentetik satır üretimi. Mevcut `synthetic_data` modülünün işidir.
- Production ortamına tohumlama. Bu külliyat geliştirme ve gösterim ortamı içindir.
- UK Open Banking ve Berlin Group alt kümesinin kesinleştirilmesi — §3.3'teki ölçüm
  yapılmadan sabitlenemez.

---

## 11. Doğrulama

1. **Kısıt uyumsuzluklarının hâlâ var olduğu.**
   `20260724_03_data_source_baseline.py:102` satırında `'FILE', 'API', 'OTHER'`
   ifadelerinin, `:144-147` aralığında `'RESTRICTED'` ifadesinin bulunduğu; buna karşılık
   `models.py:121-125` içinde `FILE_SHEET`/`API_COLLECTION`, `policy.py:21-30` içinde
   `HIGHLY_RESTRICTED` bulunduğu görülmelidir. Bu ikisi §6.1'in tek dayanağıdır; biri
   düşerse migration `17` gerekçesi de düşer.

2. **Uyumsuzluğun çalışır hâlde kanıtı.** Migration yazılmadan önce, `datasets`
   tablosuna `dataset_type='FILE_SHEET'` ile bir satır yazma denemesi
   `ck_datasets_dataset_type` ihlaliyle **başarısız olmalıdır**. Başarılı olursa
   §6.1'deki teşhis yanlıştır.

3. **Fineract ölçümünün yeniden üretimi.** §3.1'deki 14 tablonun kolon sayıları
   (45, 108, 57, 63, 19, 20, 28, 11, 17, 14, 6, 7, 7, 8) `0001_initial_schema.xml`
   üzerinden yeniden sayılmalı ve toplam 410 çıkmalıdır.

4. **İdempotentlik.** Tohumlama boş bir veritabanında çalıştırılır; `data_sources`,
   `datasets`, `data_fields` satır sayıları ve tüm kimlikler kaydedilir. Aynı komut
   ikinci kez çalıştırılır. Üç sayı da değişmemeli, kimlik kümeleri birebir aynı
   olmalıdır. Üçüncü bir çalıştırma, ikinciden sonra elle değiştirilmiş bir
   `classification` değerinin **korunduğunu** doğrulamalıdır (§8, madde 3).

5. **Sıfır satır garantisi.** Tohumlama sonrası profil ve sentetik veri tablolarının
   tohum kaynaklı hiçbir kayıt içermediği kontrol edilir. Ayrıca külliyat YAML
   dosyaları Presidio ile taranır ve hiçbir kişisel veri varlığı tetiklenmemelidir
   (§9, madde 4).

6. **Sınıflandırmaya dokunulmadığı.** Tohumlama sonrası
   `SELECT DISTINCT classification FROM dq.data_fields` sorgusu yalnız
   `UNCLASSIFIED` döndürmelidir. Başka bir değer görünüyorsa §5.4 ihlal edilmiş ve
   `16`'daki ölçüm döngüsel hâle gelmiş demektir.

7. **Mevcut dört kaynağın bozulmadığı.** `development.py:570, 577, 581, 911, 1344`
   satırlarını kullanan akışlar tohumlama sonrası çalışmalı; dört `data_source_id`
   değeri ve dört farklı `DataSourceStatus` değişmeden durmalıdır.

8. **Köken kaydının eksiksizliği.** `docs/compliance/tohum-kulliyati-koken.md`
   içindeki kaynak sayısı, külliyat YAML dosyalarındaki benzersiz `koken_url` sayısıyla
   eşleşmelidir. Eşleşmiyorsa bir kaynak atıfsız girmiş demektir.

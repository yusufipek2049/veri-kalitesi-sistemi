---
type: functional-audit-work
stage: "16 — AI Değerlendirme Külliyatı"
scope: ai-evaluation-corpus
inputs:
  - 14-Public-Dataset-Candidates.md
  - 15-Seed-Corpus-Design.md
  - ../04-Functional-Gap-Inventory.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-05
---

# 16 — AI Değerlendirme Külliyatı

> Üç AI önerisinin doğruluğunun nasıl ölçüleceğini dondurur: ölçüm setinin bileşimi,
> etiketin kim tarafından ve nasıl konacağı, hangi metriklerin hangi eşikle
> raporlanacağı. Model, istem veya uygulama tasarımı içermez.

---

## 1. Karar özeti

| Özellik | Ölçülebilir mi | Doğruluk türü | Birincil metrik | Kabul eşiği |
|---|---|---|---|---|
| Alan sınıflandırma önerisi | Evet, etiketleme sonrası | **Görüş** — bağımsız etiketleyici şart | Makro-F1 | ≥ 0,70 **ve** aşağı sınıflandırma ≤ %2 |
| Kural yazım önerisi | Evet | **Olgu** (enjekte kusur) + görüş (tip/boyut) | Enjekte kusur duyarlılığı | ≥ 0,80 duyarlılık, ≤ %20 yanlış alarm |
| Kanıtlı teşhis önerisi | **Hayır — bugün ölçülemez** | Görüş, geçmiş kayıt gerektirir | — | — |

Üçünün de ortak kararı: **hiçbiri otomatik uygulanmaz.** Ölçüm, özelliğin kullanıcıya
*öneri* olarak açılıp açılamayacağını belirler; öneriyi kabul etmek her zaman insan
işidir.

---

## 2. Ölçüm setinin çerçevesi

Ölçüm seti `15`'te tohumlanan külliyattan türetilir; ayrı bir veri toplama işi yoktur.

| Kaynak | Ölçülebilir alan | Not |
|---|---:|---|
| Fineract (14 tablo) | 410 | `15`, §3.1'de ölçüldü |
| UCI Bank Marketing | 16 | Kolon başlıkları |
| UCI German Credit | 20 | Öznitelik adları |
| BDDK | 0 | 18 tablo adı var, kolon yok (`15`, §3.2) |
| UK OB / Berlin Group | **ölçülmedi** | `14`, §6.13 — ölçüm yapılmadan sete girmez |
| **Bugün ölçülebilir toplam** | **446** | |

**Karar: 446 alanın tamamı etiketlenir, örnekleme yapılmaz.**

Gerekçe: 446 iki kişinin makul sürede etiketleyebileceği bir hacimdir ve örnekleme,
tabakalama hatası riskini ölçümün en kırılgan yerine — nadir sınıflara — taşır.
Nadir sınıfların (`SPECIAL_CATEGORY_PERSONAL_DATA`, `BANK_SECRET`) kaç örnekle temsil
edileceği **bugünden bilinemez**; etiketleme bitmeden sınıf dağılımı hakkında sayı
yazmak uydurma olurdu. Dağılım etiketleme sonrası raporlanır ve nadir sınıflar için
örnek sayısı 20'nin altında kalırsa o sınıflar makro ortalamadan çıkarılıp **ayrıca**
raporlanır.

Ölçüm seti veritabanında **durmaz**. `data_fields` tablosunda etiketin kökenini,
etiketleyeni veya anlaşmazlık kaydını tutacak kolon yoktur
(`20260724_03_data_source_baseline.py:119-150`) ve ölçüm setini üretim tablolarına
yazmak `15`, §5.4'teki "tohum sınıf yazmaz" kararını delerdi. Set,
`docs/testing/ai-degerlendirme/` altında sürümlenmiş dosyalar olarak durur.

---

## 3. Özellik 1 — Alan sınıflandırma önerisi

### 3.1 Ölçülen şey

Girdi: alan adı, native tipi, nullability, ait olduğu tablo adı ve — `15`'te
tohumlanmışsa — toplulaştırılmış profil metrikleri. Çıktı: tek bir `ClassificationCode`
değeri.

Hedef liste `src/veri_kalitesi/data_protection/policy.py:21-30`'daki dokuz
değerdir. **Yeni değer önerilmemektedir.**

Uyarı: `HIGHLY_RESTRICTED` bugün veritabanına yazılamaz
(`15`, §6.1, Uyumsuzluk 2). Ölçüm bu değeri kapsar, çünkü ölçüm dosya tabanlıdır;
ancak özellik kullanıcıya açılmadan önce migration `20260805_17` uygulanmış olmalıdır.
Aksi halde ölçümde doğru bulunan bir öneri üretimde kayıt hatası verir.

### 3.2 Metrikler

| Metrik | Neden |
|---|---|
| **Makro-F1** | Birincil. Sınıf dağılımı ağır dengesiz olacağı için doğruluk (accuracy) yanıltıcıdır; `INTERNAL` tahmin eden bir model yüksek accuracy alır |
| Sınıf bazında kesinlik/duyarlılık | `PERSONAL_DATA` ve `SPECIAL_CATEGORY_PERSONAL_DATA` için ayrıca raporlanır |
| **Aşağı sınıflandırma oranı** | Gerçek etiketten daha düşük hassasiyet öneren tahminlerin oranı. Asimetrik risk: `PERSONAL_DATA` alanı `INTERNAL` demek, tersinden çok daha pahalıdır |
| Karışıklık matrisi | Hangi çiftlerin karıştığını görmek için; eşik kararına girmez |

### 3.3 Kabul eşiği

Özellik kullanıcıya açılabilir ancak şu üçü birden sağlanırsa:

1. Makro-F1 ≥ **0,70**
2. Gerçek etiketi `PERSONAL_DATA` veya `SPECIAL_CATEGORY_PERSONAL_DATA` olan alanlarda
   aşağı sınıflandırma oranı ≤ **%2**
3. Aşağıdaki iki taban çizgisinin **ikisini de** makro-F1'de en az **0,10** farkla
   geçmesi

**Taban çizgileri zorunludur.** Bunlar olmadan "0,70 iyi mi" sorusunun cevabı yoktur:

- **T1 — en sık sınıf:** her alana veri setindeki en sık etiketi verir. AI bunu
  geçemiyorsa hiçbir şey öğrenmemiştir.
- **T2 — örüntü tabanlı:** alan adı üzerinde düzenli ifade eşleşmesi yapan basit bir
  kural kümesi. AI bunu geçemiyorsa özellik yerine 50 satırlık bir regex tablosu
  yazılmalıdır — ve bu tamamen meşru bir sonuçtur.

Eşiği geçmek özelliğin **öneri olarak** açılması demektir. Otomatik sınıflandırma bu
belgede hiçbir eşikte önerilmemektedir.

---

## 4. Döngüsellik karşıtı protokol

Bu bölüm belgenin çekirdeğidir. `14`, §2.1'deki kural şudur: bir kolonun **adını
uyduran** ile **etiketini koyan** aynı taraf olamaz.

### 4.1 Üç rol, üç ayrı taraf

| Rol | Kim | Ayrılık nasıl sağlanıyor |
|---|---|---|
| **R1 — Adı üreten** | Apache Fineract katkıcıları, BDDK, UCI veri seti sahipleri | Projeyle hiçbir ilişkisi yok. Adlar yıllar önce, bu ölçümden habersiz üretildi |
| **R2 — Etiketi koyan** | İki iç etiketleyici + bir hakem | R1'i etkileyemez; R3'ün çıktısını görmez |
| **R3 — Öneriyi üreten** | Ölçülen AI özelliği | R2'nin etiketlerini görmez; etiketleme bittikten sonra çalışır |

R1'in dışsallığı bu tasarımın tek gerçek dayanağıdır ve `15`, §6.2'deki köken kaydıyla
denetlenebilir: her alanın hangi URL'den, hangi tarihte geldiği yazılıdır. Bir alan adı
köken kaydında görünmüyorsa **ölçüm setine giremez** — bu, "kendi uydurduğumuz bir adı
sete sızdırma" ihtimalini mekanik olarak kapatır.

### 4.2 Etiketleme yordamı

1. İki etiketleyici aynı 446 alanı **birbirinden bağımsız** etiketler. Biri veri
   yönetişimi/uyum tarafından, diğeri veri mimarisi tarafından gelir. Birbirlerinin
   dosyasını görmezler.
2. Etiketleyicilere verilen bilgi R3'e verilenle aynıdır: alan adı, tip, nullability,
   tablo adı. Fazlası verilmez — yoksa insan ile AI farklı bilgiyle sınanmış olur.
3. Uyuşma **Cohen kappa** ile raporlanır. Kappa < 0,60 ise etiket kılavuzu belirsiz
   demektir; kılavuz düzeltilir ve etiketleme **baştan** yapılır. Bu durumda ölçüm
   ertelenir; düşük kappa ile alınmış bir "doğruluk" sayısı yayımlanmaz.
4. Anlaşmazlıklar üçüncü bir hakem tarafından çözülür. Hakem, iki etiketi de görür
   ama hangisinin kimden geldiğini görmez.
5. Her anlaşmazlık ve çözümü gerekçesiyle kaydedilir. Bu kayıt ölçüm çıktısının bir
   parçasıdır; ölçüm setinin en tartışmalı bölgesinin nerede olduğunu gösterir.

### 4.3 Dondurma

Etiket dosyası, R3 **ilk kez çalıştırılmadan önce** sürüm kontrolüne alınır ve commit
hash'i ölçüm raporuna yazılır. Ölçümden sonra etiket değiştirilirse yeni bir hash
oluşur ve fark görünür hâle gelir. Amaç, sonucu beğenmeyip etiketi düzeltme
ihtimalini imkânsız değil ama **görünür** kılmaktır.

### 4.4 Presidio'nun konumu — ikinci döngüsellik riski

`14`, §4.2'de Presidio kabul edildi. Burada kısıtı yazılır.

Presidio etiketleyiciye aday üretebilir ve etiketler donduktan sonra çapraz kontrol
için kullanılabilir. Ancak **etiketin kaynağı değildir**; bağlayıcı etiket her zaman
hakem kararıdır.

Gerekçe: R3'ün uygulaması da örüntü tabanlı çalışıyorsa ve etiketler Presidio'dan
geliyorsa, ölçüm "Presidio'nun kendisiyle uyumu" hâline gelir — R1/R2 ayrılığı
korunmuş görünürken R2/R3 birleşmiş olur. Bu nedenle:

- R3'ün uygulamasının Presidio kullanıp kullanmadığı ölçüm raporunda **beyan edilir**.
- Kullanıyorsa, etiketi bir Presidio önerisiyle örtüşen alanlar işaretlenir ve o alt
  küme için sonuç **ayrıca** raporlanır. Genel sayı tek başına yayımlanmaz.

Aynı kısıt Google Cloud SDP ve AWS Macie için de geçerlidir — zaten `14`, §5'te
kopyalama kaynağı olarak reddedilmişlerdir.

---

## 5. Ölçüm setinin bileşimi — zor vakalar

Kolay vakalarla dolu bir set yüksek ve anlamsız bir skor üretir. Set, zorluğa göre
tabakalanır ve **tabaka bilgisi etiketleme sırasında etiketleyiciye gösterilmez**
(yoksa zorluk beklentisi etiketi etkiler).

| Tabaka | Tanım | Külliyattan gerçek örnekler |
|---|---|---|
| **Kolay** | Ad, anlamı doğrudan söylüyor | `email_address`, `date_of_birth`, `firstname`, `lastname`, `mobile_no` |
| **Kodlanmış** | Kurum içi kodlama geleneği taşıyor | `gender_cv_id`, `loanpurpose_cv_id`, `client_type_cv_id`, `client_classification_cv_id`, `closure_reason_cv_id` |
| **Sonek tuzağı** | `_enum`, `_id` sonekleri anlamı gizliyor | `status_enum`, `sub_status`, `legal_form_enum`, `account_type_enum`, `charge_time_enum` |
| **Eski sistem kısa adı** | Anlamı ancak belgeyle çözülür | `glim_id`, `gsim_id`, `pdays`, `poutcome` |
| **Anlamı belirsiz** | Birden çok makul okuma var | `default`, `balance`, `contact`, `duration`, `campaign`, `previous` |
| **Türkçe / karışık dil** | BDDK tarafı Türkçe, Fineract tarafı İngilizce | `Rasyolar`, `Fonksiyon grubu`, `Diğer Bilgiler`, `Yurt Dışı Şube Rasyoları` |

Bu adların hiçbiri örnek olsun diye uydurulmamıştır; hepsi `14`'te ölçülen kaynaklarda
geçmektedir.

### 5.1 Kasıtlı tuzak vakalar

Üç vaka, ölçümün ayırt ediciliğini sınamak için özellikle izlenir:

- **`gender_cv_id`** — Cinsiyet, KVKK md. 6'daki özel nitelikli kişisel veri
  sayımında **yer almaz**. Doğru etiket `PERSONAL_DATA`'dır,
  `SPECIAL_CATEGORY_PERSONAL_DATA` değil. Aşırı ihtiyatlı bir model burada yukarı
  sınıflandırma yapar; bu, güvenlik açısından zararsız ama kullanışlılık açısından
  maliyetlidir ve ayrıca sayılır.
- **`is_staff`** — Bir kişiye ilişkin boole nitelik. Kişisel veri midir, yoksa
  organizasyonel bayrak mıdır? Hakem kararı gerektirir ve kararın gerekçesi kayda
  geçer.
- **`image_id`** — Müşteri fotoğrafına işaret ediyorsa biyometrik tartışmasına açılır.
  Kolonun kendisi bir yabancı anahtardır. Bu vaka, "ad tek başına yetmez" sınırını
  gösterdiği için sette tutulur.

Bu üçünün ortak işlevi: ölçümün yalnız ortalama değil, **hangi tür hatayı yaptığını**
göstermesini sağlamak.

---

## 6. Özellik 2 — Kural yazım önerisi

Bu özellik iki ayrı doğruluk türüne karşı, iki ayrı biçimde ölçülür. `14`, §2.3'teki
ayrım burada operasyonel hâle gelir.

### 6.1 Görüş tarafı — tip ve boyut eşlemesi

Girdi alan bağlamı, çıktı bir `RuleType` × `QualityDimension` çiftidir
(`src/veri_kalitesi/rules/models.py:19-27` ve `:53-60`). Referans etiketler
§4'teki aynı iki etiketleyici tarafından, aynı yordamla üretilir.

Bir alan için birden çok kural doğru olabilir. Bu nedenle etiket tek bir çift değil,
**kabul edilebilir çiftler kümesidir**; öneri bu kümenin içindeyse doğru sayılır.
Tek doğru cevap dayatmak, ölçümü etiketleyicinin keyfi tercihine bağlardı.

| Metrik | Eşik |
|---|---|
| `RuleType` top-1 isabet | ≥ **0,70** |
| `QualityDimension` top-1 isabet | ≥ **0,80** |
| Üretilen kuralın çalışabilirliği | ≥ **0,95** |

Çalışabilirlik ayrı bir metriktir ve olgu niteliğindedir: üretilen kural tanımı
motorda hatasız çalışıyor mu? Doğru tipte ama çalışmayan bir kural üretmek, ürün
açısından yanlış tipte çalışan bir kuraldan daha kötüdür.

`FRESHNESS` ve `REFERENTIAL_INTEGRITY` özellikle izlenir: `14`, §4.5'te görüldüğü gibi
Great Expectations çekirdeğinde bu ikisinin karşılığı yoktur. Bir dil modeli ağırlıklı
olarak bu tür kütüphanelerden öğrendiyse, bu iki tipte sistematik olarak zayıf
kalması beklenir — bu beklenti ölçümle sınanır, varsayılmaz.

### 6.2 Olgu tarafı — enjekte edilmiş kusurlar

Burada cevap anahtarı kimsenin görüşü değildir: bir kolona kasten kusur enjekte
edilmiştir ve enjeksiyon kaydı vardır.

Tasarım mevcut `synthetic_data` modülüne yaslanır; yeni bir mekanizma icat edilmez.
`SyntheticDatasetPolicy` zaten `defect_injection_profile`, `ground_truth_enabled` ve
`expected_score_tolerance` alanlarını taşımaktadır
(`src/veri_kalitesi/synthetic_data/models.py:68, 71, 73`) ve üretim koşusu
`random_seed` kaydeder (`synthetic_data/models.py:113`).

| # | Senaryo | Beklenen `RuleType` | Beklenen boyut |
|---|---|---|---|
| 1 | Bir kolona %3 boş değer | `REQUIRED` | `COMPLETENESS` |
| 2 | Anahtar kolonda %1 yineleme | `UNIQUE` | `UNIQUENESS` |
| 3 | Sayısal kolonda aralık dışı değer | `RANGE` | `VALIDITY` |
| 4 | Biçim ihlali (geçersiz IBAN sağlaması) | `REGEX` | `VALIDITY` |
| 5 | Zaman damgasının bayatlatılması | `FRESHNESS` | `TIMELINESS` |
| 6 | Yabancı anahtarın öksüzleştirilmesi | `REFERENTIAL_INTEGRITY` | `INTEGRITY` |
| 7 | İki tablo arası toplam uyuşmazlığı | `CROSS_TABLE_CONSISTENCY` | `CONSISTENCY` |

Yedi senaryo yedi `QualityDimension` değerini de kapsar; `CUSTOM_SQL` kasten dışarıda
bırakılmıştır çünkü tanımı gereği kapalı bir beklentiye bağlanamaz.

| Metrik | Eşik |
|---|---|
| Enjekte kusur duyarlılığı (öneri kusuru yakalıyor mu) | ≥ **0,80** |
| Temiz kolonlarda yanlış alarm | ≤ **%20** |

Yanlış alarm eşiği zorunludur: her kolona her kuralı öneren bir sistem duyarlılıkta
1,0 alır ve tamamen değersizdir.

### 6.3 Bunun "olgu" niteliğini ne koruyor

Dört mekanizma:

1. **Manifest enjeksiyondan önce yazılır.** Hangi tablo, hangi kolon, hangi bozulma,
   kaç satır — üretim koşusundan önce kaydedilir. Sonradan yazılan bir manifest,
   gözleme uydurulmuş bir cevap anahtarı olurdu.
2. **Tohum (seed) kaydedilir**, böylece koşu birebir yeniden üretilebilir
   (`synthetic_data/models.py:113`).
3. **Enjekte eden ile öneren ayrıdır.** Öneri üreten bileşen manifesti görmez. Bu,
   §4'teki R2/R3 ayrılığının olgu tarafındaki karşılığıdır.
4. **Kusur, kural motorundan bağımsız tanımlanır.** "Kural ne yakalarsa kusur odur"
   denmez; kusur veri üzerinde tanımlanır, kural onu bulmaya çalışır.

**Sınırı, dürüstçe:** Bu ölçümün sınırı *kapsamdır*, geçerlilik değil. Yalnız aklımıza
gelen yedi kusur türü üretilir; gerçek hayattaki sekizinci tür ölçülmez. Bu nedenle
§6.2'deki duyarlılık sayısı "AI kusurların %80'ini bulur" diye okunamaz; "AI, tanımlı
yedi senaryonun %80'ini bulur" diye okunur. Rapor bu cümleyi içermek zorundadır.

---

## 7. Özellik 3 — Kanıtlı teşhis önerisi

### 7.1 Neden bugün ölçülemez

Bu özellik "bu bulgunun kök nedeni büyük olasılıkla şudur, kanıtı da şu geçmiş
vakadır" demeyi hedefler. Ölçülebilmesi için **kapanmış, kök nedeni bilinen bulgu
geçmişi** gerekir. Sistemde bugün böyle bir birikim yoktur: üretimde çalışan bir
kurulum ve dolayısıyla gerçek bir bulgu geçmişi mevcut değildir. Sentetik olarak
üretilecek bir "geçmiş" ise tanımı gereği bizim uydurduğumuz nedenlerden oluşur ve
`14`, §2.2'deki döngüsellik yasağının tam ortasına düşer — teşhisi öneren de, kök
nedeni yazan da biz oluruz.

Bu yüzden özellik ertelenmiştir. Erteleme bir eksiklik değil, ölçülemeyecek bir şeyi
ölçüyormuş gibi yapmama kararıdır.

### 7.2 Bugünden ne biriktirilmeye başlanmalı

Altyapının büyük kısmı hazırdır: `data_quality_issues`, `issue_history`,
`issue_resolutions`, `issue_verifications` ve `rule_execution_results` tabloları
mevcuttur (`alembic/versions/20260723_01_issue_baseline.py` ve
`20260724_04_execution_baseline.py`).

Eksik olan tek şey **yapıdır**. `IssueResolutionRecord.root_cause` bugün serbest
metindir (`src/veri_kalitesi/issues/models.py:116`) ve doğrulaması yalnız
metin doğrulamasıdır (`issues/models.py:238`). Serbest metin, üzerinde doğruluk
ölçülebilecek bir hedef değildir: iki çözüm kaydı aynı kök nedeni iki farklı cümleyle
anlatır ve eşleştirilemez.

**Öneri:** `root_cause` serbest metni **korunarak**, yanına kapalı listeli bir kök
neden kodu eklenmesi. Serbest metin insan için değerlidir ve kaldırılmamalıdır; kod
ise ölçüm için gereklidir.

Bu bir şema değişikliğidir ve migration gerektirir. **Bu belge onu planlamaz** —
`15`'teki migration `17` ile karıştırılmamalıdır; ayrı bir dilim kararının konusudur.
Burada kaydedilen şey şudur: *bu kolon bugün eklenmezse, özellik ölçülebilir hâle
geldiğinde geriye dönük veri de olmayacaktır.* Erteleme kararının bedeli budur ve
bilinerek ödenir.

Kapalı liste için yeni bir taksonomi icat edilmesi de gerekmez; ilk sürüm
`QualityDimension`'ın yedi değerine dayanabilir. Bu, `14`, §2.4'teki "mevcut
taksonomiler kullanılır" kuralına uyar.

### 7.3 Ölçüm ne zaman mümkün olur

En az iki koşul birlikte sağlandığında: (a) kök neden kodu alanı üretimde dolu
kaydediliyor, (b) kapanmış ve kök nedeni kodlanmış bulgu sayısı, en seyrek kod için
bile anlamlı bir sayıya ulaşmış. Bu sayı bugünden belirlenmemiştir; belirlenmesi
gerçek dağılımı görmeyi gerektirir. Buraya bir hedef sayı yazmak tahmin olurdu.

---

## 8. Raporlama

Her ölçüm koşusu tek bir rapor üretir ve rapor şunları **içermek zorundadır**:

1. Etiket dosyasının commit hash'i ve etiketleme tarihi (§4.3).
2. Cohen kappa değeri ve anlaşmazlık sayısı (§4.2).
3. Sınıf dağılımı — ölçüm sonrası ölçülmüş hâliyle, tahminle değil (§2).
4. İki taban çizgisinin skoru (§3.3).
5. R3'ün Presidio kullanıp kullanmadığı beyanı ve gerekiyorsa ayrıştırılmış sonuç (§4.4).
6. §6.3'teki kapsam sınırı cümlesi.
7. Ölçüm setine sonradan eklenen veya çıkarılan alanlar ve gerekçeleri.

Eşiği geçmeyen bir koşu da raporlanır. Yalnız geçen koşuların raporlandığı bir süreç,
yeterince tekrarlandığında eşiği anlamsızlaştırır.

---

## 9. Hariç

- Model seçimi, istem tasarımı, ince ayar. Bu belge neyin ölçüleceğini belirler,
  neyin ölçüleceği şeyi nasıl inşa edileceğini değil.
- Maliyet, gecikme ve verimlilik ölçümleri. Ayrı bir çalışmadır.
- Türkçe dil modeli performansının genel değerlendirmesi.
- Kök neden kodu için migration planı (§7.2).
- UK Open Banking ve Berlin Group alanlarının sete dahil edilmesi — `14`, §6.13'teki
  ölçüm yapılmadan mümkün değil.
- Üretim ortamında sürekli izleme. Bu belge, özelliğin açılıp açılmayacağına karar
  veren tek seferlik kapıyı tanımlar.

---

## 10. Doğrulama

1. **Rol ayrılığı gerçekten var mı.** Ölçüm setindeki her alan adı için `15`, §6.2'deki
   köken kaydında bir URL ve erişim tarihi bulunmalıdır. Kökeni olmayan tek bir alan
   bile varsa, o alan projede üretilmiş olabilir ve setten çıkarılmalıdır. Bu kontrol
   mekaniktir ve tam kapsamlı çalıştırılır.

2. **Etiketin dondurulduğu.** Ölçüm raporundaki etiket dosyası hash'i, R3'ün ilk koşu
   zamanından **önceki** bir commit'e işaret etmelidir. Sonraysa §4.3 ihlal edilmiştir
   ve sonuç geçersizdir.

3. **Etiketleyici bağımsızlığı.** İki etiketleyicinin dosyaları ayrı commit'ler olarak
   bulunmalı ve ilk sürümleri birbirine bakılarak üretilmediğini gösterecek şekilde
   birbirinden bağımsız oluşturulmuş olmalıdır. Kappa 1,00 çıkıyorsa bu bir başarı
   değil, bağımsızlığın kaybedildiğine dair bir uyarıdır ve incelenmelidir.

4. **Taban çizgilerinin gerçekten hesaplandığı.** Rapor T1 ve T2 skorlarını içermiyorsa
   eşik kararı verilemez; koşu eksiktir.

5. **Enjeksiyon manifestinin önceliği.** Manifest dosyasının zaman damgası ve commit'i,
   sentetik üretim koşusunun `random_seed` kaydından **önce** olmalıdır (§6.3, madde 1).

6. **Öneren bileşenin manifesti görmediği.** Kural önerisi üreten bileşenin girdisinde
   manifest dosyasına erişim bulunmadığı, çağrı yüzeyi incelenerek doğrulanır.

7. **Tuzak vakaların sette olduğu.** `gender_cv_id`, `is_staff` ve `image_id`
   alanlarının ölçüm setinde bulunduğu ve §5.1'deki gerekçelerle işaretlendiği kontrol
   edilir.

8. **`HIGHLY_RESTRICTED` bağımlılığı.** Özellik kullanıcıya açılmadan önce migration
   `20260805_17` uygulanmış olmalı; `dq.data_fields` tablosuna
   `classification='HIGHLY_RESTRICTED'` yazılabildiği sınanmalıdır. Yazılamıyorsa
   özellik açılamaz (§3.1).

9. **Kod atıflarının geçerliliği.** `policy.py:21-30`, `rules/models.py:19-27` ve
   `:53-60`, `synthetic_data/models.py:68-73` ve `:113`, `issues/models.py:116` ve
   `:238` satırlarının belgede iddia edilen içeriği taşıdığı doğrulanır.

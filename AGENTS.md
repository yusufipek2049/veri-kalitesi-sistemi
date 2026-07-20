# AGENTS.md — Proje Geneli Codex Talimatları

## Proje

Bu depo, **Veri Kalitesi İzleme ve Skorlama Sistemi** için gereksinim, mimari, kod ve test çalışmalarını içerir.

Bağlayıcı ilkeler:

- Sistem kurum içi veri merkezinde çalışır.
- Kimlik doğrulama LDAP üzerinden yapılır.
- Kaynak veri erişimleri salt okunurdur.
- Gizli bilgiler açık metin saklanmaz.
- Sistem içi bildirim zorunludur; ServiceNow entegrasyonu desteklenir.
- Teknik hata ile veri kalitesi başarısızlığı ayrı değerlendirilir.
- Büyük tablolar için kaynakta toplulaştırma, bölümleme ve kontrollü örnekleme tercih edilir.
- Sistem bir banka için geliştirilmektedir; bankacılık sırrı, müşteri sırrı, kişisel veri ve kritik risk/veri raporlama etkileri tasarım girdisidir.
- Teknik uygulama kanıtı, mevzuat uyumluluğu veya banka onayı anlamına gelmez.

## Başlangıç bağlamı

Her geliştirme görevinde önce yalnızca şunları oku:

1. `00-Proje-Hafizasi/Mevcut-Durum.md`
2. `00-Proje-Hafizasi/Alinan-Kararlar.md`
3. `00-Proje-Hafizasi/Acik-Konular.md`
4. `00-Proje-Hafizasi/Sonraki-Adimlar.md`
5. `00-Proje-Hafizasi/Bankacilik-Gecis-Durumu.md`
6. `01-SRS/SRS-INDEX.md`

Görev MVP kapsamıyla ilgiliyse ayrıca `01-SRS/12-MVP.md` dosyasını oku.

Salt açıklama, biçimlendirme veya açıkça belirtilmiş küçük bir dosya düzenleme görevinde gereksiz proje belgelerini okuma.


## Modül seçimi

Görevi aşağıdaki modüllerden **birine veya en küçük gerekli kümeye** eşleştir. Kodlamadan önce seçilen modülün `AGENTS.md` dosyasını oku.

| Görev alanı | Modül talimatı |
| --- | --- |
| LDAP, oturum, RBAC, kullanıcı/rol | `03-Backend/01-Kimlik-ve-Yetki/AGENTS.md` |
| Veri kaynağı, bağlantı, secret, bağlayıcı | `03-Backend/02-Veri-Kaynaklari/AGENTS.md` |
| Metadata keşfi, profil, duplicate, desen | `03-Backend/03-Metadata-ve-Profilleme/AGENTS.md` |
| Kural şablonu, SQL kuralı, sürüm/onay | `03-Backend/04-Kural-Yonetimi/AGENTS.md` |
| Kuyruk, zamanlama, retry, timeout | `03-Backend/05-Calistirma-ve-Zamanlama/AGENTS.md` |
| Skor formülü, ağırlık, trend | `03-Backend/06-Skorlama/AGENTS.md` |
| Dashboard API ve özet sorguları | `03-Backend/07-Dashboard/AGENTS.md` |
| Sistem içi bildirim | `03-Backend/08-Bildirim/AGENTS.md` |
| Sorun yaşam döngüsü ve ServiceNow | `03-Backend/09-Sorun-Yonetimi/AGENTS.md` |
| Rapor, dışa aktarma | `03-Backend/10-Raporlama/AGENTS.md` |
| Audit ve denetim izi | `03-Backend/11-Audit/AGENTS.md` |
| REST API, entegrasyon, webhook/adaptör | `03-Backend/12-API-ve-Entegrasyon/AGENTS.md` |
| Kullanıcı arayüzü | `04-Frontend/AGENTS.md` ve ilgili alt modül |
| Şema, migration, indeks, saklama | `05-Veritabani/AGENTS.md` |
| Test tasarımı ve otomasyon | `06-Testler/AGENTS.md` ve ilgili test katmanı |
| Mimari karar/değişiklik | `02-Mimari/AGENTS.md` |
| Proje hafızası güncellemesi | `00-Proje-Hafizasi/AGENTS.md` |
| BDDK/KVKK kontrol eşleme, veri sınıflandırma, görevler ayrılığı | `01-SRS/17-Bankacilik-Uyum/AGENTS.md` |
| Güven sınırı, kimlik bağlamı, audit bütünlüğü, ortam ayrımı | `02-Mimari/Guvenlik/AGENTS.md` |
| Olay müdahalesi, saklama/imha, DR, ServiceNow runbook | `07-Operasyon/AGENTS.md` |
| Uyum ve kontrol kanıtı üretimi | `08-Uyum-Kanitlari/AGENTS.md` |
| Bankacılık geçiş iterasyonları | `09-Iterasyonlar/AGENTS.md` |

Bir görev birden fazla modülü etkiliyorsa önce ana modülü seç, sonra yalnız zorunlu komşu modüllerin talimatlarını oku. Tüm modül talimatlarını topluca okuma.

## Bankacılık geçiş kapısı

`00-Proje-Hafizasi/Bankacilik-Gecis-Durumu.md` içindeki **Geçiş Kapısı** tamamlanana kadar aşağıdaki işler, yeni kullanıcı yüzeyi açan özelliklerden önce gelir:

1. Güvenilir aktör ve yetki bağlamı,
2. Merkezi ve bütünlüğü doğrulanabilir audit sınırı,
3. Veri sınıflandırma ve maskeleme politikası,
4. Maker-checker / görevler ayrılığı,
5. LDAP grup-rol eşleme ve ayrıcalıklı erişim kararı.

Bu sıra, mevcut 15 iterasyonun çıktısını geri almaz. Mevcut domain servislerinin önüne güvenilir kimlik ve kontrol sınırı ekler.

### Kontrol durumları

Aşağıdaki durum sözlüğünü kullan:

- `Proposed`: Taslak kontrol veya karar.
- `Implemented`: Kod veya yapılandırma uygulanmış.
- `TechnicallyVerified`: Test veya teknik incelemeyle doğrulanmış.
- `ComplianceReviewRequired`: Hukuk, uyum, bilgi güvenliği veya iç kontrol incelemesi gerekli.
- `ApprovedByBank`: Yalnız bankanın yetkili karar sahibi açık kanıtla onayladıysa.
- `NotApplicable`: Gerekçesi ve onay sahibi kaydedilmişse.

Codex kendi başına `ApprovedByBank`, “BDDK uyumlu” veya “KVKK uyumlu” sonucu üretemez.

### Bankacılık güvenlik tabanı

- Gerçek banka verisi, müşteri verisi, LDAP kimliği veya üretim secret'ı geliştirme/test ortamına yazılmaz.
- Serbest metin `actor_id`, kullanıcı girdisi olarak gelen rol veya çağıranın kurduğu erişim kapsamı yetki kanıtı kabul edilmez.
- Yetki kararı güvenilir kimlik adaptöründen üretilen değişmez aktör bağlamına dayanır ve varsayılan olarak reddeder.
- Kritik kural, skor konfigürasyonu, veri kaynağı aktivasyonu, yetki ve dışa aktarma değişikliklerinde maker-checker etkisi değerlendirilir.
- İşlemi hazırlayan kişi aynı değişikliği onaylayamaz.
- Audit olayları merkezi olay sözleşmesine uyar; secret, ham kişisel veri veya müşteri sırrı içermez.
- Audit yazma başarısının kritik işlemle ilişkisi açık politikayla belirlenmeden sessizce best-effort davranış uygulanmaz.
- ServiceNow, log, bildirim ve rapora ham hatalı kayıt gönderilmez.
- Saklama süresi kayıt türü, amaç ve hukuki gerekçeye göre belirlenir; “her şey beş yıl” varsayımı otomatik uygulanmaz.
- KVKK ihlal bildirimi otomatik gönderilmez; sistem karar ve kanıt akışını destekler, yetkili onayını bekler.
- Bankanın bilgi güvenliği, iç kontrol, hukuk, uyum ve mimari onayları tahmin edilmez.

## Bağlam bütçesi

- Tam SRS'yi topluca okuma.
- Başlangıç bağlamı ve `AGENTS.md` dosyaları bağlam bütçesine dahil değildir.
- Başlangıç bağlamından sonra görev başına varsayılan olarak en fazla 6 alan belgesi oku.
- Alan belgeleri; FR, UC, RULE, veri varlığı, NFR, mimari ve teknik tasarım belgeleridir.
- Önce gereksinim ID'si ve dosya yolu ile kesin arama yap; semantik aramayı ikinci seçenek olarak kullan.
- Kabul kriterlerini okumadan implementasyona başlama.
- İlgisiz kullanım senaryosu ve NFR dosyalarını bağlama alma.
- Karar vermek için yeterli bağlam oluştuğunda daha fazla doküman okumayı bırak.

## Geliştirme yöntemi

Yinelemeli ve artımlı çalış:

1. Küçük, çalışabilir bir dilim seç.
2. İlgili FR, UC, RULE, veri varlığı ve NFR kayıtlarını belirle.
3. Kısa uygulama planı oluştur.
4. Uygula.
5. Birim ve gerekli entegrasyon testlerini ekle.
6. Kabul kriterlerini doğrula.
7. Değişen dosyaları ve karşılanan gereksinim ID'lerini bildir.
8. Proje hafızasını yalnız gerçek değişikliklerle güncelle.

## İterasyon komutları

Kullanıcı aşağıdaki kısa komutlardan birini verdiğinde bu bölümdeki davranışı uygula.

### `devam` veya `sıradaki iterasyonu uygula`

1. Başlangıç bağlamındaki proje hafızası dosyalarını oku.
2. `Bankacilik-Gecis-Durumu.md` içindeki geçiş kapısını kontrol et.
3. Geçiş kapısı tamamlanmadıysa `09-Iterasyonlar/ITERASYON-INDEX.md` içindeki sıradaki hazır bankacılık artımını seç.
4. Geçiş kapısı tamamlandıysa `Sonraki-Adimlar.md` içindeki hazır ve engellenmemiş ürün artımlarını belirle.

   Seçim sırası:

   1. Bankacılık geçiş kapısındaki kritik güven sınırı işleri,
   2. `Must` öncelikli gereksinimler,
   3. Bağımlılık zincirinde önce tamamlanması gereken işler,
   4. Kullanıcıya veya sisteme uçtan uca çalışan değer sunan işler,
   5. Aynı öncelikteyse daha küçük ve düşük riskli işler.

   Bu sıralamaya göre en yüksek öncelikli ürün artımını seç.


3. Seçilen işin gerçekten tamamlanıp tamamlanmadığını mevcut kod ve `Mevcut-Durum.md` üzerinden doğrula.
4. İlgili modülü belirle ve yalnız o modülün `AGENTS.md` dosyasını oku.
5. `SRS-INDEX.md` üzerinden ilgili FR, UC, RULE, veri varlığı ve NFR belgelerini bul.
6. Definition of Ready koşullarını kontrol et.
7. Kapsam büyükse işi daha küçük, çalışabilir bir dikey dilime böl ve yalnız ilk dilimi uygula.
8. Kısa bir plan oluştur.
9. Kodu ve gerekli migration/configuration değişikliklerini uygula.
10. Birim ve gerekli entegrasyon testlerini ekle.
11. Mevcut lint, format, type-check, test ve build komutlarını çalıştır.
12. Kabul kriterlerini tek tek doğrula.
13. Proje hafızasını gerçek sonuçlara göre güncelle.
14. Yalnızca bir iterasyon gerçekleştir.
15. Sonraki iterasyonu uygulamadan iterasyon raporu vererek dur.

Kullanıcıdan bu çalışma yöntemini yeniden açıklamasını isteme.

### `planla`

Sıradaki hazır ürün artımını seç, ilgili belgeleri oku ve uygulama planı oluştur. Kod veya proje dosyalarında değişiklik yapma.

### `durumu değerlendir`

Kodu, test sonuçlarını ve proje hafızasını karşılaştır. Tamamlanan işleri, tutarsızlıkları, engelleri ve sıradaki hazır işi raporla. Yeni özellik geliştirme.

### `testleri düzelt`

Yeni kapsam ekleme. Mevcut değişikliklerle ilişkili başarısız testleri, lint, type-check veya build sorunlarını gider ve sonuçları doğrula.


## Değişiklik kuralları

- Kullanıcı açıkça istemedikçe `01-SRS/` altındaki gereksinim metinlerini değiştirme.
- Yeni teknik kararları `00-Proje-Hafizasi/Alinan-Kararlar.md` ve gerekiyorsa `02-Mimari/Mimari-Kararlar.md` içinde kaydet.
- Tamamlanan işi `Mevcut-Durum.md`, kalan işi `Sonraki-Adimlar.md`, engelleri `Acik-Konular.md` içinde güncelle.
- Secret, parola, token veya gerçek kurum bağlantı bilgisini depoya yazma.
- Kaynak sistemlere yazan DDL/DML veya değiştirici API çağrısı üretme.

## Frontend görsel tabanı

- Frontend componentlerinde ham renk, spacing, radius veya shadow değeri kullanma;
  `04-Frontend/Gorsel-Tasarim-Sistemi.md` içindeki semantik token'ları kullan.
- `#FDB813` marka rengidir; uyarı veya kritik/teknik hata rengi değildir. Kritik veri
  kalitesi ihlali kırmızı, teknik hata mor, operasyonel uyarı turuncu gösterilir.
- Frontend görevini Storybook durumları ve Playwright görsel doğrulaması olmadan
  tamamlanmış sayma; zorunlu viewport'ları ve iki iyileştirme turunu kaydet.
- Görsel görev kapsamı dışında component/refactor yapma ve kullanıcı onayı olmadan
  yeni frontend dependency ekleme.
- Ayrıntılı component, grafik, tablo ve erişilebilirlik kuralları için
  `04-Frontend/AGENTS.md` dosyasını uygula.

## Tamamlama ölçütü

Bir görev ancak aşağıdakiler sağlandığında tamamlanmış sayılır:

- İlgili kabul kriterleri karşılanmış veya karşılanmayanlar açıkça belirtilmiş,
- Testler eklenmiş ve çalıştırılmış,
- Teknik hata yolları ele alınmış,
- Gereksinim ID'leri değişikliklerle ilişkilendirilmiş,
- Proje hafızası gerekiyorsa güncellenmiş.

## Banka için ek tamamlama ölçütü

Bir bankacılık kontrolünü veya hassas veri akışını etkileyen görevde ayrıca:

- Güven sınırı ve veri sınıflandırma etkisi değerlendirilmiş,
- Yetkisiz, ayrıcalıklı ve servis hesabı negatif testleri eklenmiş,
- Maker-checker etkisi değerlendirilmiş,
- Audit olayı ve redaksiyon alanları test edilmiş,
- Log, hata, bildirim ve audit çıktısında secret veya ham hassas veri olmadığı doğrulanmış,
- İlgili kontrol ID'leri ve kanıt dosyaları ilişkilendirilmiş,
- `ComplianceReviewRequired` kararları açık bırakılmış,
- Geri alma veya güvenli pasifleştirme yaklaşımı belirtilmiş

olmalıdır.

## Definition of Ready

Bir ürün artımı ancak aşağıdaki koşullarda geliştirmeye alınabilir:

* İlgili gereksinim ID'leri belirlenmiştir.
* Kullanıcı veya sistem değeri anlaşılmıştır.
* Kabul kriterleri bulunmuştur.
* Temel bağımlılıklar belirlenmiştir.
* Bilinen bir engel bulunmamaktadır.
* Kapsam tek iterasyonda tamamlanabilecek büyüklüktedir.

Koşullar tam sağlanmıyorsa:

- Belirsizliği `Acik-Konular.md` dosyasına kaydet.
- İş kritik bir karar, erişim veya bağımlılık nedeniyle engelliyse uygulama yapma.
- Backlogdaki sıradaki hazır ve engellenmemiş ürüne geç.
- Yalnız engel kapsam dışı bırakılarak bağımsız, güvenli ve test edilebilir
  bir dikey dilim üretilebiliyorsa en küçük kapsamla ilerle.
- Kritik iş veya mimari kararları tahmin ederek kesinleştirme.

## İterasyon raporu

Her geliştirme iterasyonunun sonunda aşağıdaki formatı kullan:

### İterasyon

* **İterasyon adı:**
* **Kullanıcı/sistem değeri:**
* **Karşılanan gereksinimler:**
* **Değiştirilen dosyalar:**
* **Eklenen veya güncellenen testler:**
* **Çalıştırılan kontroller:**
* **Kabul kriteri sonuçları:**
* **Alınan teknik kararlar:**
* **Açık kalan konular:**
* **Önerilen sonraki iterasyon:**

## Github Push

Her iterasyon sonrası iterasyon adını commit mesajı addederek https://github.com/yusufipek2049/veri-kalitesi-sistemi reposuna pushla

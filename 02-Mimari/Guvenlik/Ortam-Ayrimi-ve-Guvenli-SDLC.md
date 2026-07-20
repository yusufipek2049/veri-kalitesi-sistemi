# Ortam Ayrımı ve Güvenli SDLC

## Ortamlar

| Ortam | Veri | Kimlik | Secret | Dış entegrasyon |
| --- | --- | --- | --- | --- |
| Local | Sentetik | Fake adapter | Sahte referans | Fake |
| Development | Sentetik/anonim | Test IAM | Dev secret store | Sandbox |
| Test/UAT | Maskeli ve onaylı | UAT IAM | UAT store | UAT |
| Production | Banka onaylı gerçek veri | Üretim IAM/PAM | Üretim secret manager | Üretim |

## Güvenli Pipeline Kapıları

- Test
- Ruff/lint/type check
- Secret taraması
- Bağımlılık zafiyet taraması
- SAST
- Container/IaC taraması uygulanıyorsa
- SBOM
- Artifact bütünlük kaydı
- Onay ve geri alma planı

Gerçek ürün ve eşik seçimleri bankanın CI/CD ve bilgi güvenliği standartlarına bağlanır.

## Yerel Secret Tarama Baseline'ı

`28A-v1` yerel tarama politikası repository dosyalarını salt okunur inceler. Bulgu
çıktısı yalnız göreli dosya yolu, satır/sütun ve kural kodunu taşır; eşleşen değer,
satır içeriği veya işletim sistemi hata ayrıntısı sonuç sözleşmesine alınmaz.

Komut:

```bash
PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc .
```

Çıkış kodları temiz tarama için `0`, güvenlik bulgusu için `1`, doğrulama veya teknik
tarama hatası için `2` değeridir. `.git`, cache, build ve bağımlılık dizinleri;
binary, büyük, düzenli olmayan ve sembolik bağlantılı dosyalar tarama dışında kalır.
Bu yerel baseline pipeline zorlaması veya banka onaylı tarayıcı ürünü değildir.

## Yerel Bağımlılık Envanteri ve SBOM Baseline'ı

`pyproject.toml` PEP 621 metadata'sında proje sürümü ve doğrudan çalışma zamanı
bağımlılıkları tam sürüme sabitlenir. `28B-v1` üreticisi bu beyanı salt okunur
alarak deterministik CycloneDX 1.5 JSON üretir:

```bash
PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc.sbom pyproject.toml
```

SBOM proje sürümünü, `requires-python` beyanını ve doğrudan bağımlılık grafiğini
taşır; zaman damgası, rastgele seri numarası, yerel dosya yolu veya kullanıcı
bilgisi içermez. Eksik/dinamik sürüm veya bağımlılık beyanı; tam sürüme
sabitlenmemiş, URL/path tabanlı ya da yinelenen bağımlılık teknik üretim
başarısızlığıdır.

Bu başlangıç paketi transitive çözümleme, artifact hash'i, lisans doğrulaması veya
zafiyet taraması yapmaz. Nihai SBOM ürünü, kapsamı ve CI/CD kapısı banka bilgi
güvenliği standardına bağlanır. Çıktı yapısı [CycloneDX 1.5 JSON şemasına](https://cyclonedx.org/schema/bom-1.5.schema.json)
karşı doğrulanır.

## Yerel SAST Bulgu ve Sürüm Kapısı Baseline'ı

`28C-v1` sözleşmesi harici scanner çıktısını güvenilmez girdi kabul eder. Bulgu
allowlist'i scanner kimliği/sürümü, kural kodu, `INFO/LOW/MEDIUM/HIGH/CRITICAL`
önem derecesi ve repository-relative satır/sütun konumuyla sınırlıdır. Kaynak
satırı, snippet, açıklama, ham scanner mesajı, secret veya mutlak/üst dizine çıkan
yol kabul edilmez.

`SastReleaseGate`, yalnız `COMPLETED` rapordan sürüm kanıtı üretebilir.
`TECHNICAL_ERROR` temiz tarama sayılmaz ve teknik hata olarak fail-closed kapanır.
Tamamlanmış raporda en az bir `CRITICAL` bulgu varsa üretim adayı kanıtı üretilmez.
Başarılı kanıt PEP 621 proje adı/sürümü, gate/scanner sürümü, bulgu sayısı ve
deterministik bulgu digest'ini taşır; bulgu yolu ve kural kodunu açık metin taşımaz.

Bu baseline gerçek SAST ürünü veya repository taraması değildir. CI/CD zorlaması,
scanner seçimi, banka eşikleri, istisna/risk kabulü, release onayı, DAST ve sızma
testi `ComplianceReviewRequired` olarak açık kalır.

## Yerel Bağımlılık Zafiyet Bulgu ve Sürüm Kapısı Baseline'ı

`28D-v1` sözleşmesi harici dependency scanner ve advisory kaynağı çıktısını
güvenilmez girdi kabul eder. Bulgu allowlist'i scanner/advisory kaynağı kimliği ve
sürümü, advisory kimliği, `INFO/LOW/MEDIUM/HIGH/CRITICAL` önem derecesi ile doğrudan
bağımlılığın kanonik adı ve PEP 440 sürümüyle sınırlıdır. Açıklama, mesaj, URL,
düzeltme sürümü, yerel yol, secret veya ham teknik ayrıntı kabul edilmez.

`DependencyVulnerabilityReleaseGate`, bulguların yalnız 28B envanterindeki tam
ad-sürüm çiftlerine ait olmasını zorunlu kılar. Yalnız `COMPLETED` rapor kanıt
üretebilir; `TECHNICAL_ERROR` temiz tarama sayılmaz. En az bir `CRITICAL` bulgu
kanıtı fail-closed engeller. Başarılı kanıt proje/gate/scanner/advisory sürümlerini,
`declared-direct-dependencies` kapsamını ve envanter/bulgu SHA-256 özetlerini taşır;
advisory veya paket ayrıntısını açık metin çoğaltmaz.

Bu baseline gerçek zafiyet veritabanı veya ağ taraması değildir. Transitive lock,
paket artifact doğrulaması, kritik olmayan banka eşikleri, istisna/risk kabulü,
CI/CD zorlaması, release maker-checker ve sızma testi `ComplianceReviewRequired`
olarak açık kalır.

## Veri-Minimum Sızma Testi Bulgu Takip Baseline'ı

`28E-v1` sözleşmesi sızma testi bulgu girdisini güvenilmez kabul eder. Bulgu zarfı
yalnız opak değerlendirme, bulgu, iyileştirme aksiyonu ve sorumlu taraf UUID
referansları ile `INFO/LOW/MEDIUM/HIGH/CRITICAL` önem derecesini kabul eder. Başlık,
açıklama, endpoint, istek/yanıt, exploit, rapor URL'si, kullanıcı adı veya secret
gibi serbest içerik sözleşmeye alınmaz.

Bulgu değişmez kayıtlarla `OPEN -> READY_FOR_RETEST` ve başarılı tekrar testten
sonra `PASSED -> CLOSED` ilerler. Başarısız tekrar test bulguyu `OPEN` durumuna
döndürür. `TECHNICAL_ERROR` güvenlik sonucu değildir; bulgu
`READY_FOR_RETEST` durumunda kalır ve yeniden test edilebilir. Geçersiz veya
atlanan durum geçişleri fail-closed reddedilir.

Yalnız `COMPLETED` değerlendirme raporu kanıt üretebilir. Kapanmamış herhangi bir
`CRITICAL` bulgu kanıtı engeller; tamamlanmamış değerlendirme teknik hata olarak
ayrılır. Başarılı kanıt yalnız toplam/durum sayımları ile kanonik kayıtların
deterministik SHA-256 özetini taşır; tekil bulgu ve sorumlu referanslarını çoğaltmaz.

Bu baseline gerçek sızma testi hizmeti değildir. Banka kapsamı, sıklığı,
bağımsızlık şartı, kimlik/evidence resolver'ları, kalıcı depo, HTTP/UI, CI/CD,
release maker-checker ve banka onayı `ComplianceReviewRequired` olarak açık kalır.

## Teknik Kanıt Manifesti Baseline'ı

`29A-v1` manifest üreticisi sürümlü JSON katalogdaki 8 BDDK ve 7 KVKK kontrolünü
tam kapsam olarak doğrular. Her kontrolün teknik durumu, banka inceleme durumu,
opak karar referansı ve `OPEN-BNK-*` engelleri ayrı alanlardır; teknik kanıt hiçbir
durumda banka onayına yükseltilmez.

Kanıt yolları yalnız `08-Uyum-Kanitlari/` altındaki repository-relative `.md` veya
`.json` artifact'larını gösterebilir. Mutlak/traversal/non-canonical yol, symlink,
eksik, düzenli olmayan veya 2 MiB üzeri artifact fail-closed reddedilir. Dosyalar
salt okunur açılır; manifest yalnız göreli yol ve SHA-256 özeti taşır, kanıt
içeriğini çoğaltmaz.

Çıktı zaman damgası veya rastgele kimlik içermez; kontrol/artifact sırası
kanonikleştirilir ve tüm kontrol kayıtları tek SHA-256 digest ile bağlanır. Mevcut
baseline 15 kontrolde 12 `Partial`, 3 `Missing`, 14 açık engel ve 15
`ComplianceReviewRequired` raporlar. Elektronik imza, WORM/HSM, kurumsal kanıt
deposu, CI/CD drift kapısı ve banka onay iş akışı kapsam dışıdır.

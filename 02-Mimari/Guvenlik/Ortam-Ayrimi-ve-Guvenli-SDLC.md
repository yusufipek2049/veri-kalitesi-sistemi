# Ortam Ayrımı ve Güvenli SDLC

## Ortamlar

| Ortam | Veri | Kimlik | Secret | Dış entegrasyon |
| --- | --- | --- | --- | --- |
| Local | Sentetik | Fake adapter | Sahte referans | Fake |
| Development | Sentetik/anonim | Test IAM | Dev secret store | Sandbox |
| Test/UAT | Maskeli ve onaylı | UAT IAM | UAT store | UAT |
| Production | Banka onaylı gerçek veri | Üretim IAM/PAM | Üretim secret manager | Üretim |

## Üretim Yerleşimi

- Stateless API ve worker bileşenleri kurumsal konteyner platformunda bağımsız ölçeklenir.
- Veri tabanı ayrı bir yüksek erişilebilirlik kümesinde çalışır.
- Kalıcı dosya ve rapor depolaması konteyner yerel diskine bağlı değildir.
- İş kuyruğu ve entegrasyon bileşenleri tek hata noktası oluşturmaz.
- Dağıtım, geri alma, sağlık kontrolü ve kontrollü kapatma davranışları işletim prosedüründe bulunur.
- Uygulama kurumsal secret manager'a servis veya workload identity ile erişir; yerel geliştirmede üretim secret'ı kullanılmaz.

Belirli platform, veritabanı, broker ve secret manager ürünü TBD'dir.

## Fail-Closed Ortam Başlangıç Kapısı

`27A-v1` ortam kapısı ortam adını çağıranın serbest metninden veya sıradan uygulama
ayarından almaz. Yalnız `27A-trusted-source-v1` sözleşmesini uygulayan ve dağıtım
bileşiminde güvenilir kabul edilen sağlayıcının sürümlü konfigürasyonunu yükler.
Kaynak okunamazsa teknik hata üretilir ve uygulama güvenli başlangıç kanıtı alamaz.

Kapı `LOCAL`, `DEVELOPMENT`, `TEST`, `ACCEPTANCE` ve `PRODUCTION` sınıflarını
ayırır. Üretim dışı ortamda `BANK_PRODUCTION` veri kökeni veya
`secret://production/...` kapsamı reddedilir. Ayrıca her ortam yalnız kendi secret
kapsamını kullanabilir. Secret referansı sıkı URI allowlist'iyle doğrulanır; kanıt
yalnız secret kapsamını taşır, referans yolunu taşımaz.

Bu sözleşme gerçek verinin kökenini kendisi keşfetmez ve secret çözmez. Güvenilir
sağlayıcının gerçek deployment platformuna, veri hazırlama kanıtına ve kurumsal
secret manager'a bağlanması `OPEN-BNK-012` kapsamında kalır.

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

## Teknik Kanıt Manifest Drift Kapısı

`29B-v1` kapısı 29A katalog ve artifact'larından manifesti aynı kanonik serileştirme
sözleşmesiyle yeniden üretir. Saklanan manifest yalnız
`08-Uyum-Kanitlari/Surum-Paketleri/` altındaki repository-relative `.json` yolundan
salt okunur açılır; mutlak/traversal/non-canonical yol, symlink, eksik, düzenli
olmayan ve 2 MiB üzeri dosya fail-closed reddedilir.

Bayt eşitliği `MATCH` ve `0`, eşitsizlik `DRIFT` ve `1`, girdi doğrulama veya
dosya işlemi arızası veri-minimum neden koduyla `2` üretir. Sonuç yalnız politika,
durum ve saklanan/üretilen SHA-256 özetlerini taşır; manifest veya kanıt içeriğini
çoğaltmaz. Bu yerel doğrulama CI/CD zorlaması, imza, WORM/HSM, istisna/risk kabulü
veya banka onayı değildir.

## Birleşik Yerel Sürüm Ön Kontrolü

`29C-v1` preflight secret taraması, saklanan SBOM byte karşılaştırması, SAST,
doğrudan bağımlılık zafiyeti, pentest takip ve teknik kanıt manifest drift
kontrollerini sabit sırada çağırır. Alt kapıların kritik bulgu, teknik hata ve
doğrulama kuralları preflight içinde yeniden uygulanmaz.

SAST, bağımlılık zafiyeti ve pentest raporları `schema_version=1` olan zorunlu JSON
paketten exact-field allowlist ile ayrıştırılır. Eksik rapor veya
`TECHNICAL_ERROR` durumu temiz kabul edilmez. Secret/kritik bulgu ve SBOM/manifest
drift'i `BLOCKED=1`; doğrulama veya teknik hata `2`; altı kontrolün tamamlanması
`PASS=0` üretir.

Başarılı çıktı yalnız proje adı/sürümü ile kontrol kimliği, politika sürümü ve
kanıt SHA-256 özetini taşır. Bulgu yolu, advisory, pentest UUID, ham scanner mesajı
veya rapor içeriği çoğaltılmaz. Bu komut gerçek scanner/pentest çalıştırıcısı,
kurumsal CI/CD zorlaması, imzalı artifact yayını veya banka onayı değildir.

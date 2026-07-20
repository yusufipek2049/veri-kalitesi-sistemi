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

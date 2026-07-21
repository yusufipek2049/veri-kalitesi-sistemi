# Sürüm ve Değişiklik Yönetimi

Üretim adayı için:

- izlenebilir gereksinim ve kontrol ID'leri
- kod inceleme
- test sonuçları
- güvenlik taramaları
- migration ve geri alma
- yapılandırma farkı
- SBOM/artifact özeti
- iş, mimari ve güvenlik onayları
- açık risk kabulü
- dağıtım ve doğrulama kanıtı

Codex banka onaylarını varsayamaz.

## Skorlama Modeli Değişiklik Kapısı

`DQ-SCR-014`–`DQ-SCR-017`, `DQ-SCR-022`–`DQ-SCR-025`, `DQ-SCR-030` ve
`DQ-SCR-032` kapsamındaki normalizasyon, eşik, ağırlık, kritik kural,
kapsam/güven, istisna ve override değişikliklerinde üretim öncesi aşağıdaki
kanıtlar aranır:

- değişmez politika/model sürümü, kapsamı, gerekçesi ve geçerlilik başlangıcı,
- risk sınıfına göre maker-checker ve görevler ayrılığı kararı,
- payda, durum, agregasyon, kritik veto/tavan ve teknik hata regresyon testleri,
- kalite/kapsam/güven/risk/teknik sağlık API ve UI sözleşme testleri,
- trend sürüm sınırı ve geçmiş skorların değişmediği doğrulaması,
- replay planı; orijinal skoru koruyan ayrı yeniden hesaplama sonucu,
- audit/outbox başarısızlığında fail-closed davranış ve geri alma planı.

Skor modeli, eşik veya ağırlık sürümü değiştiğinde geçmiş skorlar sessizce
güncellenmez. Sonuçların doğrudan karşılaştırılabilir olmadığı dönem sürüm
sınırıyla işaretlenir. Üretim eşik/ağırlık/veto/güven/risk değerleri banka ve
Veri Yönetişimi onayı olmadan belirlenmez; eksik değerler `TBD` kalır.

## Skorlama Operasyon Sınırı

- Ölçüm sıklığı, tam tarama/örnekleme ve kaynakta toplulaştırma kararı dataset
  politikasından çözülür; kullanılan yöntem, dönem, hacim ve güven kaydedilir
  (`DQ-SCR-031`).
- Timeout, bağlantı veya worker hatası kalite başarısızlığına çevrilmez. Teknik
  olay ayrı alarm üretir; son başarılı skor gösterilirse ölçüm zamanı ve eskilik
  görünür, kapsam/güven düşer (`DQ-SCR-005`, `DQ-SCR-028`).
- Kritik kural, hızlı kötüleşme, veri yokluğu, kapsam/güven düşüşü ve yüksek
  istisna oranı kalite alarm politikasında; retry/timeout/platform olayı teknik
  alarm politikasında değerlendirilir. Tekrarlar korelasyon anahtarıyla
  birleştirilir (`DQ-SCR-027`, `DQ-SCR-028`).
- Replay, snapshot/partition veya doğrulama hash'i ve tüm model/politika/uygulama
  sürümleri olmadan başlatılmaz; orijinal sonuç değiştirilmez (`DQ-SCR-025`,
  `DQ-SCR-032`).
- Skor, politika, istisna, override ve replay kayıtlarının RPO/RTO ile saklama
  hedefleri bileşen/kayıt sınıfı politikasından gelir; kesin değerler `TBD`'dir.

## Yerel Secret Kontrolü

Üretim adayı hazırlanmadan önce yerel veri-minimum kontrol aşağıdaki komutla
çalıştırılabilir:

```bash
PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc .
```

- `0`: tarama tamamlandı ve bulgu yok.
- `1`: en az bir bulgu var; çıktı yalnız konum ve kural kodu içerir.
- `2`: tarama tamamlanamadı; bu sonuç temiz tarama kabul edilmez.

Bulgu değeri, satır içeriği veya ham teknik hata kanıt dosyasına ve loga yazılmaz.
Kurumsal CI/CD ürünü, kritik eşik ve istisna/onay akışı banka bilgi güvenliği
kararıyla ayrıca belirlenir.

## Yerel SBOM Kontrolü

Doğrudan Python bağımlılık envanteri aşağıdaki komutla sürüm bağlantılı CycloneDX
JSON olarak üretilir:

```bash
PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc.sbom pyproject.toml
```

Başarılı üretim `0`, manifest doğrulama veya teknik okuma hatası `2` döndürür.
Başarısız üretim sürüm için SBOM kanıtı sayılamaz. Yerel doğrulama artifact'ı
`08-Uyum-Kanitlari/Surum-Paketleri/Iterasyon-28B-SBOM.cdx.json` yolundadır ve
proje sürümü `0.1.0` ile ilişkilidir. Transitive bağımlılık, hash, lisans ve
zafiyet sonuçları bu artifact'ın kapsamında değildir.

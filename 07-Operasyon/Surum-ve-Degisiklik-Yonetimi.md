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
kapsam/güven, ölçüm yeterliliği, geçerlilik, kullanım kararı, istisna ve override değişikliklerinde üretim öncesi aşağıdaki
kanıtlar aranır:

- değişmez politika/model sürümü, kapsamı, gerekçesi ve geçerlilik başlangıcı,
- risk sınıfına göre maker-checker ve görevler ayrılığı kararı,
- sayaç değişmezleri, payda, durum, agregasyon, kritik veto/tavan, yeterlilik
  önceliği ve teknik hata regresyon testleri,
- ham/nihai kalite, yeterlilik, kullanım, kapsam/güven, risk ve teknik sağlık API
  ile UI sözleşme testleri,
- trend sürüm sınırı ve geçmiş skorların değişmediği doğrulaması,
- replay planı; orijinal skoru koruyan ayrı yeniden hesaplama sonucu,
- audit/outbox başarısızlığında fail-closed davranış ve geri alma planı.

Skor modeli, eşik veya ağırlık sürümü değiştiğinde geçmiş skorlar sessizce
güncellenmez. Sonuçların doğrudan karşılaştırılabilir olmadığı dönem sürüm
sınırıyla işaretlenir. Üretim eşik/ağırlık/veto/güven/risk değerleri aktif,
sürümlü ve gerekli onayı taşıyan politika kaydından çözülür; kayıt yoksa olumlu
skor yeterliliği veya kullanım kararı verilmez.

## Skorlama Operasyon Sınırı

- Ölçüm sıklığı, tam tarama/örnekleme ve kaynakta toplulaştırma kararı dataset
  politikasından çözülür; kullanılan yöntem, dönem, hacim ve güven kaydedilir
  (`DQ-SCR-031`).
- Timeout, bağlantı veya worker hatası kalite başarısızlığına çevrilmez. Teknik
  olay ayrı alarm ve `TechnicalFailure` yeterlilik sonucu üretir; son başarılı
  skor gösterilirse kendi ölçüm zamanı, geçerliliği ve yeterlilik durumu görünür,
  güncel resmî sonuç gibi sunulmaz (`DQ-SCR-005`, `DQ-SCR-028`).
- Yeterlilik değerlendirmesi kapsam, örneklem, güncellik, teknik başarı, sürüm,
  kritik kontrol ve kanıt koşullarını ayrı kapılarda çalıştırır. Üretim eşikleri,
  `ValidUntil` süreleri ve kullanım yetkileri aktif sürümlü politikadan çözülür;
  politika yoksa olumlu kullanım kararı verilmez.
- Kritik kural, hızlı kötüleşme, veri yokluğu, kapsam/güven düşüşü ve yüksek
  istisna oranı kalite alarm politikasında; retry/timeout/platform olayı teknik
  alarm politikasında değerlendirilir. Tekrarlar korelasyon anahtarıyla
  birleştirilir (`DQ-SCR-027`, `DQ-SCR-028`).
- Replay, snapshot/partition veya doğrulama hash'i ve tüm model/politika/uygulama
  sürümleri olmadan başlatılmaz; orijinal sonuç değiştirilmez (`DQ-SCR-025`,
  `DQ-SCR-032`).
- Skor, politika, istisna, override ve replay kayıtlarının normal hedefi
  `RPO=PT15M`, `RTO=PT4H`; kritik risk veya düzenleyici zincirdeki hedefi
  `RPO=PT5M`, `RTO=PT1H`'dir. Saklama sınıfı resmî kayıt için
  `RET-10Y-BANKING`, resmî olmayan test/provizyonel kayıt için `RET-1Y-OPS`'tur.

## Sentetik Veri Değişiklik Kapısı

`FR-088–FR-096`, `ADR-016` ve `RULE-016/017` kapsamındaki üretici, senaryo,
şema, dağılım, eksiklik, kusur, ground truth, gizlilik veya karşılaştırma
değişikliğinde üretim öncesi şu kanıtlar aranır:

- değişmez üretici/konfigürasyon/şema/politika/ground truth sürümleri ve random seed,
- Golden yapısal bütünlük ve aynı seed ile kanonik replay sonucu,
- geçerli uç/kusur ayrımı, bağımsız expected-versus-actual karşılaştırma ve
  teknik hata negatifleri,
- gizlilik kapısı, sınıflandırma, erişim, dışa aktarım ve saklama sonucu,
- bildirim, ServiceNow ve SIEM için yalnız fake/sandbox hedef kanıtı,
- risk bazlı maker-checker, veri-minimum audit ve güvenli pasifleştirme planı.

Skor motorunun gerçekleşen sonucu ground truth olamaz. Nicel
gizlilik/fayda/tolerans değerleri aktif sürümlü sentetik doğrulama politikasından
çözülür; politika yoksa çalışma `BLOCKED` olur. Üretim profili erişimi varsayılan
kapalıdır ve yalnız ayrı kurumsal onaylarla açılabilir. Sentetik performans kanıtı
`OPEN-014` nihai kabulinin yerine geçmez.

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

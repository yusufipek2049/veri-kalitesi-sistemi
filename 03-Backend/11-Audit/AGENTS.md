# AGENTS.md — Audit

## Zorunlu bağlam

1. `01-SRS/04-Fonksiyonel-Gereksinimler/04.11-Audit.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-016-Audit-kayitlarinin-incelenmesi.md`
3. `01-SRS/07-Veri-Modeli/Sorun-Bildirim-ve-Audit-Varliklari.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.11-Uyumluluk.md`

Yalnız görev gerektiriyorsa ayrıca `01-SRS/06-Is-Kurallari.md` ve `01-SRS/10-Kabul-Kriterleri.md` içinden ilgili ID/bölümü oku.

## Uygulama kuralları

- Audit kaydı değiştirilemez ve append-only mantıkta olsun.
- Kim, ne zaman, hangi nesnede, eski/yeni değer ve sonucu kaydet.
- Secret veya maskelenmemiş kişisel veriyi audit loga yazma.
- Audit erişimini ayrı izinle koru; sorgu ve dışa aktarmayı da audit et.

## Test beklentisi

- En az bir başarılı akış, bir doğrulama/iş kuralı hatası ve bir teknik hata testi ekle.
- Test adında veya açıklamasında ilgili FR/UC kimliğini belirt.
- Kabul kriteri ölçülebilir süre veya oran içeriyorsa uygun otomatik ya da tekrarlanabilir performans testi tanımla.
- Modül dışı davranışı değiştirmek gerekiyorsa önce etkilenen komşu modülün `AGENTS.md` dosyasını oku.

## Bankacılık ek kuralları

- Yeni audit modeli `data_sources.models.AuditRecord` içinde kalmamalı; merkezi `audit` modülüne taşınmalıdır.
- Olay zarfı sürümlü, redakte edilmiş ve correlation ID içermelidir.
- Bütünlük doğrulaması hash-chain, imza veya bankanın onaylı platformuna uyarlanabilir arayüzle sağlanmalıdır.
- Kritik işlemde audit yazma hatası sessizce yutulamaz.
- Audit sorgulama/dışa aktarma ayrı izin, gerekçe ve audit olayı gerektirir.

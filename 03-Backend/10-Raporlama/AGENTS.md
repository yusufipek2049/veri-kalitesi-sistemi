# AGENTS.md — Raporlama

## Zorunlu bağlam

1. `01-SRS/04-Fonksiyonel-Gereksinimler/04.10-Raporlama.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-015-Veri-kalitesi-raporu-olusturulmasi.md`
3. `01-SRS/07-Veri-Modeli/Sorun-Bildirim-ve-Audit-Varliklari.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.01-Performans.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.06-Gizlilik-ve-KVKK.md`

Yalnız görev gerektiriyorsa ayrıca `01-SRS/06-Is-Kurallari.md` ve `01-SRS/10-Kabul-Kriterleri.md` içinden ilgili ID/bölümü oku.

## Uygulama kuralları

- Rapor filtrelerini kullanıcının veri kapsamıyla sınırla.
- Büyük dışa aktarmaları arka plan işi olarak tasarla.
- Hassas örnekleri maskele ve gereksiz ham veri dışa aktarma.
- Rapor parametreleri, üretim zamanı ve veri kapsamını kaydet.

## Test beklentisi

- En az bir başarılı akış, bir doğrulama/iş kuralı hatası ve bir teknik hata testi ekle.
- Test adında veya açıklamasında ilgili FR/UC kimliğini belirt.
- Kabul kriteri ölçülebilir süre veya oran içeriyorsa uygun otomatik ya da tekrarlanabilir performans testi tanımla.
- Modül dışı davranışı değiştirmek gerekiyorsa önce etkilenen komşu modülün `AGENTS.md` dosyasını oku.

## Bankacılık ek kuralları

- Hassas dışa aktarma gerekçe, rol, veri kapsamı ve gerekiyorsa onay ile çalışmalıdır.
- Dışa aktarma dosyası sınıflandırma, filtre, aktör ve üretim zamanı metadata'sı taşımalıdır.
- Geçici rapor dosyası için kısa saklama ve güvenli silme politikası uygulanmalıdır.
- Yetkisiz alanlar yalnız gizlenmez; sorgu ve dosya üretim kapsamına hiç alınmaz.

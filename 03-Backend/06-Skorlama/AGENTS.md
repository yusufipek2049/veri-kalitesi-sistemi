# AGENTS.md — Skorlama

## Zorunlu bağlam

1. `01-SRS/04-Fonksiyonel-Gereksinimler/04.06-Skorlama.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-009-Veri-kalite-skorunun-hesaplanmasi.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-010-Dashboard-uzerinden-sonuclarin-incelenmesi.md`
3. `01-SRS/07-Veri-Modeli/Kural-ve-Calistirma-Varliklari.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.01-Performans.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.08-Bakim-Yapilabilirlik.md`

Yalnız görev gerektiriyorsa ayrıca `01-SRS/06-Is-Kurallari.md` ve `01-SRS/10-Kabul-Kriterleri.md` içinden ilgili ID/bölümü oku.

## Uygulama kuralları

- Formülü saf ve deterministik fonksiyonlarda uygula.
- Teknik hata veya NO_DATA sonucunu sayısal kalite başarısızlığına dönüştürme.
- Ağırlık ve üst seviye toplulaştırma kurallarını sürümlendir.
- Yuvarlama ve eksik skor davranışını testlerle sabitle.

## Test beklentisi

- En az bir başarılı akış, bir doğrulama/iş kuralı hatası ve bir teknik hata testi ekle.
- Test adında veya açıklamasında ilgili FR/UC kimliğini belirt.
- Kabul kriteri ölçülebilir süre veya oran içeriyorsa uygun otomatik ya da tekrarlanabilir performans testi tanımla.
- Modül dışı davranışı değiştirmek gerekiyorsa önce etkilenen komşu modülün `AGENTS.md` dosyasını oku.

## Bankacılık ek kuralları

- Eşik, boyut ağırlığı, dataset kritiklik ağırlığı ve kurum kaynak ağırlığı değişiklikleri maker-checker kapsamındadır.
- Onaylanmamış scoring configuration aktif edilemez.
- Hesaplama detayı, formül ve politika sürümünü korur; hassas alan değeri içermez.
- Manuel skor override varsayılan olarak yasaktır; açılırsa süreli, gerekçeli, onaylı ve ayrı gösterilmelidir.

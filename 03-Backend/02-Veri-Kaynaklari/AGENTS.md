# AGENTS.md — Veri Kaynakları

## Zorunlu bağlam

1. `01-SRS/04-Fonksiyonel-Gereksinimler/04.02-Veri-Kaynagi-Yonetimi.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-002-Yeni-veri-kaynagi-eklenmesi.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-003-Veri-kaynagi-baglantisinin-test-edilmesi.md`
3. `01-SRS/07-Veri-Modeli/Kaynak-ve-Metadata-Varliklari.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.01-Performans.md`

Yalnız görev gerektiriyorsa ayrıca `01-SRS/06-Is-Kurallari.md` ve `01-SRS/10-Kabul-Kriterleri.md` içinden ilgili ID/bölümü oku.

## Uygulama kuralları

- Bağlayıcılar ortak bir salt-okunur sözleşme uygulasın.
- Secret değerini değil yalnız secret referansını sakla.
- Bağlantı testinde DNS, TLS, kimlik, yetki ve sorgu hatalarını sınıflandır.
- Timeout, satır limiti ve eşzamanlılık sınırını zorunlu uygula.

## Test beklentisi

- En az bir başarılı akış, bir doğrulama/iş kuralı hatası ve bir teknik hata testi ekle.
- Test adında veya açıklamasında ilgili FR/UC kimliğini belirt.
- Kabul kriteri ölçülebilir süre veya oran içeriyorsa uygun otomatik ya da tekrarlanabilir performans testi tanımla.
- Modül dışı davranışı değiştirmek gerekiyorsa önce etkilenen komşu modülün `AGENTS.md` dosyasını oku.

## Bankacılık ek kuralları

- Kaynak aktivasyonu ve bağlantı kapsamı değişikliği için maker-checker etkisini değerlendir.
- Bağlantı testi, hesabın salt-okunur yetkisini mümkün olan ürünlerde negatif yazma testi veya grant incelemesiyle kanıtlayabilmelidir.
- Secret resolver üretim adaptörü dışında ham secret loglanamaz veya exception içine taşınamaz.
- Kaynak ve dataset için sınıflandırma/sahiplik metadata'sı desteklenmelidir.
- Kaynak sürücünün ham hata mesajını kullanıcı, audit veya ServiceNow payloadına koyma.

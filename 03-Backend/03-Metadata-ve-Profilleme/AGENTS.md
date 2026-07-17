# AGENTS.md — Metadata ve Profilleme

## Zorunlu bağlam

1. `01-SRS/04-Fonksiyonel-Gereksinimler/04.03-Metadata-ve-Profilleme.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-004-Veri-kumesinin-profillenmesi.md`
3. `01-SRS/07-Veri-Modeli/Kaynak-ve-Metadata-Varliklari.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.01-Performans.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.06-Gizlilik-ve-KVKK.md`

Yalnız görev gerektiriyorsa ayrıca `01-SRS/06-Is-Kurallari.md` ve `01-SRS/10-Kabul-Kriterleri.md` içinden ilgili ID/bölümü oku.

## Uygulama kuralları

- Metrikleri mümkün olduğunca kaynakta toplulaştır.
- 20 milyon satırlık tablolarda tam taramayı varsayılan yapma.
- Kullanılan örnekleme yöntemi ve oranını sonuçta sakla.
- Hassas değerleri maskele; yüksek kardinaliteli ham değerleri kopyalama.

## Test beklentisi

- En az bir başarılı akış, bir doğrulama/iş kuralı hatası ve bir teknik hata testi ekle.
- Test adında veya açıklamasında ilgili FR/UC kimliğini belirt.
- Kabul kriteri ölçülebilir süre veya oran içeriyorsa uygun otomatik ya da tekrarlanabilir performans testi tanımla.
- Modül dışı davranışı değiştirmek gerekiyorsa önce etkilenen komşu modülün `AGENTS.md` dosyasını oku.

## Bankacılık ek kuralları

- `classification` serbest metin yerine onaylı sözlük koduna geçmelidir.
- Sınıflandırılmamış alan için ham örnek, top-values veya desen örneği üretme.
- Profil metrikleri veri minimizasyonu ilkesine göre toplulaştırılmalıdır.
- Kişisel veri işleme amacı ve saklama etkisi metadata ile ilişkilendirilebilmelidir.
- Sentetik olmayan performans örnekleri repoya veya test çıktısına yazılamaz.

# AGENTS.md — Kural Yönetimi

## Zorunlu bağlam

1. `01-SRS/04-Fonksiyonel-Gereksinimler/04.04-Kural-Yonetimi.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-005-Veri-kalitesi-kurali-olusturulmasi.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-006-Kuralin-test-edilmesi.md`
3. `01-SRS/07-Veri-Modeli/Kural-ve-Calistirma-Varliklari.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.08-Bakim-Yapilabilirlik.md`

Yalnız görev gerektiriyorsa ayrıca `01-SRS/06-Is-Kurallari.md` ve `01-SRS/10-Kabul-Kriterleri.md` içinden ilgili ID/bölümü oku.

## Uygulama kuralları

- Kural sürümlerini değişmez tut; eski sonuçları eski sürüme bağla.
- Özel SQL için yalnız tek ve salt-okunur statement kabul et.
- Kuralı aktifleştirmeden test ve gerekli onay akışını uygula.
- Eşik, ağırlık, boyut ve sahiplik doğrulamalarını domain katmanında yap.

## Test beklentisi

- En az bir başarılı akış, bir doğrulama/iş kuralı hatası ve bir teknik hata testi ekle.
- Test adında veya açıklamasında ilgili FR/UC kimliğini belirt.
- Kabul kriteri ölçülebilir süre veya oran içeriyorsa uygun otomatik ya da tekrarlanabilir performans testi tanımla.
- Modül dışı davranışı değiştirmek gerekiyorsa önce etkilenen komşu modülün `AGENTS.md` dosyasını oku.

## Bankacılık ek kuralları

- Kritik kural aktivasyonu maker-checker gerektirir.
- Kuralı oluşturan veya yeni sürümü hazırlayan aktör aynı sürümü onaylayamaz.
- Onay, ret ve geri çekme kural sürümüne bağlanır; onay eski sürüme taşınmaz.
- Özel SQL yürütme planı hassas alan sınıflandırmasını ve kaynak yük bütçesini dikkate almalıdır.
- Override/istisna süreli, gerekçeli ve auditli olmalıdır.

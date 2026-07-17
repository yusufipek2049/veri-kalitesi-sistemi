# AGENTS.md — Bildirim

## Zorunlu bağlam

1. `01-SRS/04-Fonksiyonel-Gereksinimler/04.08-Bildirim.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-011-Kritik-kalite-sorunu-olusmasi.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-012-Bildirim-gonderilmesi.md`
3. `01-SRS/07-Veri-Modeli/Sorun-Bildirim-ve-Audit-Varliklari.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.04-Guvenilirlik-ve-Hata-Toleransi.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.07-Kullanici-Deneyimi.md`

Yalnız görev gerektiriyorsa ayrıca `01-SRS/06-Is-Kurallari.md` ve `01-SRS/10-Kabul-Kriterleri.md` içinden ilgili ID/bölümü oku.

## Uygulama kuralları

- Zorunlu kanal sistem içi bildirimdir.
- Tekrar, susturma ve okundu durumlarını deterministik yönet.
- Alıcıyı sahiplik ve kapsam metadatasından çöz.
- Aynı olayın yeniden işlenmesinde mükerrer bildirim üretme.

## Test beklentisi

- En az bir başarılı akış, bir doğrulama/iş kuralı hatası ve bir teknik hata testi ekle.
- Test adında veya açıklamasında ilgili FR/UC kimliğini belirt.
- Kabul kriteri ölçülebilir süre veya oran içeriyorsa uygun otomatik ya da tekrarlanabilir performans testi tanımla.
- Modül dışı davranışı değiştirmek gerekiyorsa önce etkilenen komşu modülün `AGENTS.md` dosyasını oku.

## Bankacılık ek kuralları

- Bildirim gövdesi ham kayıt, müşteri bilgisi, banka sırrı veya secret içeremez.
- Şablon alanları allowlist ile üretilmeli ve sınıflandırma politikasından geçmelidir.
- Alıcı, güvenilir rol/sahiplik kaynağından çözülmelidir.
- Susturma ve tekrar kontrolü kritik güvenlik olaylarını sessizce kaybetmemelidir.

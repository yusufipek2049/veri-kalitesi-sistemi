# AGENTS.md — Sorun Yönetimi

## Zorunlu bağlam

1. `01-SRS/04-Fonksiyonel-Gereksinimler/04.09-Sorun-Yonetimi.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-011-Kritik-kalite-sorunu-olusmasi.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-013-Veri-kalitesi-sorununun-kullaniciya-atanmasi.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-014-Sorunun-cozulmesi-ve-kapatilmasi.md`
3. `01-SRS/07-Veri-Modeli/Sorun-Bildirim-ve-Audit-Varliklari.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.04-Guvenilirlik-ve-Hata-Toleransi.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md`

Yalnız görev gerektiriyorsa ayrıca `01-SRS/06-Is-Kurallari.md` ve `01-SRS/10-Kabul-Kriterleri.md` içinden ilgili ID/bölümü oku.

## Uygulama kuralları

- Durum geçişlerini açık state machine ile doğrula.
- Atama, yorum, çözüm ve kapatma işlemlerini audit et.
- ServiceNow adaptörünü domain modelinden ayır ve idempotency anahtarı kullan.
- Kapatma öncesi doğrulama ve çözüm öncesi/sonrası skor ilişkisini koru.

## Test beklentisi

- En az bir başarılı akış, bir doğrulama/iş kuralı hatası ve bir teknik hata testi ekle.
- Test adında veya açıklamasında ilgili FR/UC kimliğini belirt.
- Kabul kriteri ölçülebilir süre veya oran içeriyorsa uygun otomatik ya da tekrarlanabilir performans testi tanımla.
- Modül dışı davranışı değiştirmek gerekiyorsa önce etkilenen komşu modülün `AGENTS.md` dosyasını oku.

## Bankacılık ek kuralları

- Issue açıklaması ve yorumları serbest metin olsa bile hassas veri uyarısı/redaksiyon kontrolünden geçmelidir.
- ServiceNow'a yalnız alan whitelist'i gönderilmelidir.
- Ticket içinde ham hatalı kayıt yerine uygulama içi yetkili detay bağlantısı kullanılmalıdır.
- Atama ve kapatma yetkisi güvenilir ActorContext üzerinden doğrulanmalıdır.

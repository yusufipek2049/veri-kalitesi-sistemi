# AGENTS.md — Çalıştırma ve Zamanlama

## Zorunlu bağlam

1. `01-SRS/04-Fonksiyonel-Gereksinimler/04.05-Calistirma-ve-Zamanlama.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-007-Kural-calistirmasinin-zamanlanmasi.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-008-Manuel-kalite-kontrolu-calistirilmasi.md`
3. `01-SRS/07-Veri-Modeli/Kural-ve-Calistirma-Varliklari.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.04-Guvenilirlik-ve-Hata-Toleransi.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.09-Gozlemlenebilirlik.md`

Yalnız görev gerektiriyorsa ayrıca `01-SRS/06-Is-Kurallari.md` ve `01-SRS/10-Kabul-Kriterleri.md` içinden ilgili ID/bölümü oku.

## Uygulama kuralları

- İş oluşturma ve tetiklemeyi idempotent yap.
- Teknik hata için sınırlı retry uygula; kalite başarısızlığını retry etme.
- Bağlantı, sorgu ve toplam iş timeoutlarını ayrı izle.
- İptal, partial ve worker heartbeat kaybını açık durumlarla modelle.

## Test beklentisi

- En az bir başarılı akış, bir doğrulama/iş kuralı hatası ve bir teknik hata testi ekle.
- Test adında veya açıklamasında ilgili FR/UC kimliğini belirt.
- Kabul kriteri ölçülebilir süre veya oran içeriyorsa uygun otomatik ya da tekrarlanabilir performans testi tanımla.
- Modül dışı davranışı değiştirmek gerekiyorsa önce etkilenen komşu modülün `AGENTS.md` dosyasını oku.

## Bankacılık ek kuralları

- Manual ve scheduled execution güvenilir kullanıcı veya servis `ActorContext` ile başlatılmalıdır.
- Scheduler servis hesabı açık rol/scope ve policy version taşımalıdır.
- İptal ve retry olayları merkezi audit olay sözlüğüne yazılmalıdır.
- Kaynak kotası bankanın kapasite politikasıyla sürümlenebilir olmalıdır.
- Teknik hata ayrıntısı hassas veri sızıntısı için redakte edilmelidir.

# AGENTS.md — API ve Entegrasyon

## Zorunlu bağlam

1. `01-SRS/04-Fonksiyonel-Gereksinimler/04.12-API-ve-Entegrasyon.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-003-Veri-kaynagi-baglantisinin-test-edilmesi.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-012-Bildirim-gonderilmesi.md`
3. `01-SRS/08-Harici-Arayuzler.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.04-Guvenilirlik-ve-Hata-Toleransi.md`

Yalnız görev gerektiriyorsa ayrıca `01-SRS/06-Is-Kurallari.md` ve `01-SRS/10-Kabul-Kriterleri.md` içinden ilgili ID/bölümü oku.

## Uygulama kuralları

- REST API sürümlemesi ve tutarlı hata sözleşmesi kullan.
- Tüm girişleri doğrula; RBAC kapsamını her istekte uygula.
- Harici çağrılarda timeout, retry, circuit breaker ve idempotency ihtiyacını değerlendir.
- Adaptörleri domain katmanından ayır; entegrasyon sırlarını yalnız secret referansıyla kullan.

## Test beklentisi

- En az bir başarılı akış, bir doğrulama/iş kuralı hatası ve bir teknik hata testi ekle.
- Test adında veya açıklamasında ilgili FR/UC kimliğini belirt.
- Kabul kriteri ölçülebilir süre veya oran içeriyorsa uygun otomatik ya da tekrarlanabilir performans testi tanımla.
- Modül dışı davranışı değiştirmek gerekiyorsa önce etkilenen komşu modülün `AGENTS.md` dosyasını oku.

## Bankacılık ek kuralları

- Kimlik ve kapsam HTTP header/gövdesinden doğrudan domain'e aktarılmaz.
- API gateway veya auth adapter assertion'ı doğrulanmadan ActorContext oluşmaz.
- İç servis çağrılarında banka onaylı servis kimliği ve taşıma güvenliği uygulanmalıdır.
- Rate limit, idempotency ve hata sözleşmesi hassas bilgi sızdırmayacak şekilde tasarlanmalıdır.
- ServiceNow/SIEM çağrılarında veri bölgesi ve aktarım kararı açık kontrol olarak tutulmalıdır.

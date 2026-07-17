# AGENTS.md — Kimlik ve Yetki

## Zorunlu bağlam

1. `01-SRS/04-Fonksiyonel-Gereksinimler/04.01-Kullanici-ve-Yetki.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-001-Sisteme-giris-yapilmasi.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-016-Audit-kayitlarinin-incelenmesi.md`
3. `01-SRS/07-Veri-Modeli/Kimlik-ve-Yetki-Varliklari.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.06-Gizlilik-ve-KVKK.md`

Yalnız görev gerektiriyorsa ayrıca `01-SRS/06-Is-Kurallari.md` ve `01-SRS/10-Kabul-Kriterleri.md` içinden ilgili ID/bölümü oku.

## Uygulama kuralları

- LDAP erişimini adaptör arkasında tut.
- Her endpoint ve nesne erişiminde RBAC kapsamını doğrula.
- Oturum, başarısız giriş ve yetki kararlarını güvenli biçimde audit et.
- Parola veya LDAP kimlik bilgisini uygulama deposunda saklama.

## Test beklentisi

- En az bir başarılı akış, bir doğrulama/iş kuralı hatası ve bir teknik hata testi ekle.
- Test adında veya açıklamasında ilgili FR/UC kimliğini belirt.
- Kabul kriteri ölçülebilir süre veya oran içeriyorsa uygun otomatik ya da tekrarlanabilir performans testi tanımla.
- Modül dışı davranışı değiştirmek gerekiyorsa önce etkilenen komşu modülün `AGENTS.md` dosyasını oku.

## Bankacılık ek kuralları

- `ActorContext` güvenilir identity adapter tarafından üretilmeli ve değişmez olmalıdır.
- İstekten gelen actor, rol veya scope listesi yetki kaynağı değildir.
- Varsayılan karar deny-by-default olmalıdır.
- LDAP grup-rol-scope eşlemesi sürümlü politika olmalı; eşlenmeyen grup yetki üretmemelidir.
- Ayrıcalıklı ve break-glass erişimi süreli, gerekçeli ve ayrı audit olaylarıyla izlenmelidir.
- MFA/PAM uygulanma biçimi banka kararıdır; destek noktalarını modelle, ürünü tahmin etme.

## Bankacılık test beklentisi

- Sahte actor_id ile yetki yükseltme reddi.
- Güvenilir context olmadan erişim reddi.
- Süresi dolmuş context reddi.
- LDAP erişilemez/eşleme bulunamaz fail-closed.
- Servis hesabı ile kullanıcı hesabı kapsam ayrımı.

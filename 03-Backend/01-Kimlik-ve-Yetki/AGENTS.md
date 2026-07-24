# AGENTS.md — Kimlik ve Yetki

Önce kök [AGENTS.md](../../AGENTS.md) kurallarını uygula. Bu dosya yalnız
kimlik/yetki modülüne özgü ek bağlamı tanımlar.

## Zorunlu Bağlam

1. `01-SRS/04-Fonksiyonel-Gereksinimler/04.01-Kullanici-ve-Yetki.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-001-Sisteme-giris-yapilmasi.md`
3. `01-SRS/05-Kullanim-Senaryolari/UC-016-Audit-kayitlarinin-incelenmesi.md`
4. `01-SRS/07-Veri-Modeli/Kimlik-ve-Yetki-Varliklari.md`
5. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md`
6. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.06-Gizlilik-ve-KVKK.md`

## Modül Kuralları

- LDAP/IdP erişimini adaptör arkasında tut.
- `ActorContext` yalnız güvenilir identity/session adaptöründen üretilir ve
  değişmezdir; istek actor/rol/scope alanları yetki kanıtı değildir.
- Her endpoint ve nesne erişiminde RBAC kapsamını deny-by-default doğrula.
- Oturum, başarısız giriş, ayrıcalıklı ve break-glass kararlarını veri-minimum
  audit et; parola veya LDAP kimlik bilgisi saklama.
- MFA/PAM ürününü tahmin etme; destek noktalarını modelle, açık banka kaydına bağla.

## Negatif Testler

Sahte actor ile yetki yükseltme, güvenilir context yokluğu/süresi dolması,
LDAP kesintisi veya eşleme yokluğu, servis-kullanıcı hesabı ayrımı, scope
manipülasyonu ve audit yazma hatasını kapsa.

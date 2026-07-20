---
control_ids:
  - BFR-IAM-004
requirement_ids:
  - FR-006
  - UC-001
  - NFR-SEC-010
  - AC-002
status: TechnicallyVerified
version: iteration-20b-local
executed_at: 2026-07-17
---

# İterasyon 20B Başarısız Giriş Sınırlandırma Kanıtı

## Değişiklik

- İterasyon: 20B - yapılandırılabilir ve kalıcı başarısız giriş sınırlandırması
- Commit/Artifact: Git deposu bulunmadığı için commit yok; yerel çalışma ağacı
- Bileşen: `veri_kalitesi.identity`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: FR-006, UC-001, NFR-SEC-010, AC-002 ve BFR-IAM-004 alt kapsamı

## Doğrulama

- Komut: `pytest -q`
- Ortam: Python 3.10.12, yerel prototip, fake LDAP adaptörü ve sentetik opak anahtarlar
- Sentetik veri seti: Credential reddi, LDAP teknik arızası, iki kullanıcı/istemci kapsamı, kalıcı SQLite sayacı, 15 dakikalık zaman ilerletme ve kapalı depo
- Beklenen: En geç beşinci credential reddinde kullanıcı ve istemci kapsamları en az 15 dakika engellenir; aktif engel LDAP çağrısından önce reddedilir; LDAP teknik hatası sayacı artırmaz; başarı sayacı sıfırlar; ham kimlik girdileri saklanmaz.
- Gerçekleşen: 237 test geçti. Kimlik hedef grubu 25 testle geçti; beşinci rette iki kapsam engellendi ve sonraki çağrı LDAP'a ulaşmadı.
- Sonuç: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Değişen altı Python dosyasında `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src`: PASS
- Tam depo format kontrolü, bu iterasyonda değişmeyen dört eski dosyanın mevcut format farkları nedeniyle PASS değildir.

## Güvenlik

- Güven sınırı: Principal ve istemci referansı, enjekte edilen güvenilir anahtar sağlayıcı tarafından opak kullanıcı/istemci anahtarına dönüştürülür.
- Deny-by-default: Anahtar üretimi veya throttle deposu kullanılamazsa LDAP çağrısı ve context üretimi yapılmaz.
- Hata ayrımı: Yalnız credential reddi sayılır; LDAP teknik ve beklenmeyen hataları giriş sayacını değiştirmez.
- Kalıcılık: Kullanıcı ve istemci sayaçları ayrı SQLite satırlarında atomik güncellenir ve repository yeniden açıldığında engel korunur.
- Veri minimizasyonu: Principal, istemci referansı ve credential throttle deposuna veya audit özetine yazılmaz; audit yalnız politika sürümleri, sayaç ve engel özetini taşır.
- Maker-checker etkisi: Bu dilimde politika oluşturma/degistirme API'sı yoktur; politika yalnız başlangıçta enjekte edilir. Üretim politika değişikliği onayı ve görevler ayrılığı `OPEN-BNK-019` altında açıktır.
- Geri alma: LDAP servisi throttle bağımlılığı olmadan kurulamaz; güvenli pasifleştirme ancak banka onaylı daha kısıtlayıcı olmayan yeni politika ve kontrollü migration ile yapılmalıdır.
- Kalan risk: Üretim anahtar sağlayıcısı, secret manager, istemci referansının güvenilir ağ sınırı, paylaşımlı üretim deposu ve LDAP lockout değer uyumu banka kararı gerektirir.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- IAM: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.

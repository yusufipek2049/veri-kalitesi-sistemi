---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
  - BFR-IAM-004
  - BFR-IAM-005
  - BFR-IAM-006
  - CTRL-BDDK-IAM-001
requirement_ids:
  - FR-001
  - FR-005
  - UC-001
  - NFR-SEC-005
  - NFR-SEC-009
  - AC-001
status: TechnicallyVerified
version: iteration-20c-local
executed_at: 2026-07-17
---

# İterasyon 20C Güvenli Oturum Yaşam Döngüsü Kanıtı

## Değişiklik

- İterasyon: 20C - kalıcı, iptal edilebilir ve idle-timeout kontrollü kullanıcı oturumu
- Commit/Artifact: Git deposu bulunmadığı için commit yok; yerel çalışma ağacı
- Bileşen: `veri_kalitesi.identity`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: FR-001/005, UC-001, NFR-SEC-005/009, AC-001 ve BFR-IAM-001/002/004/005/006 alt kapsamı

## Doğrulama

- Komut: `pytest -q`
- Ortam: Python 3.10.12, yerel prototip, fake LDAP adaptörü ve sentetik kullanıcı verisi
- Sentetik veri seti: Güvenilir/güvenilmez/expired context, 32 bayt session credential, idle ve mutlak süre ilerletme, çıkış, değiştirilmiş credential, kalıcı SQLite kaydı, depo ve audit arızası
- Beklenen: Yalnız güvenilir LDAP context'i oturum açar; credential açık saklanmaz; 30 dakikada idle timeout, mutlak timeout ve çıkış oturumu kalıcı geçersizleştirir; teknik arıza context döndürmez.
- Gerçekleşen: 254 test geçti. Kimlik hedef grubu 42 testle geçti; 17 yeni oturum testi eklendi.
- Sonuç: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Değişen altı Python dosyasında `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src`: PASS
- Tam depo format kontrolü, bu iterasyonda değişmeyen dört eski dosyanın mevcut format farkları nedeniyle PASS değildir.

## Güvenlik

- Güven sınırı: Session servisi serbest actor/rol/scope almaz; yalnız güvenilir ve halen geçerli `ActorContext` kabul eder.
- Credential: Yüksek entropili credential yalnız bir kez `SessionGrant` içinde dondurulur; SQLite ve audit yalnız SHA-256/session digest taşır.
- Deny-by-default: Bilinmeyen, değiştirilmiş, expired veya revoked credential context üretmez. Depo ya da audit arızası fail-closed kapanır.
- Zaman: Sürümlü politika varsayılan 30 dakika idle timeoutu uygular; daha sıkı değer desteklenir. Ayrıca enjekte edilen mutlak timeout aktiviteyle uzatılmaz.
- Çıkış: İlk çıkış kalıcı `REVOKED`, tekrar çıkış idempotenttir; credential daha sonra kullanılamaz.
- Hesap ayrımı: Normal kullanıcı session servisi servis hesabı ve ayrıcalıklı kullanıcıyı reddeder; break-glass/servis oturumu bu dilimde tahmin edilmez.
- Audit: Oluşturma, doğrulama, timeout, çıkış ve ret olayları allowlist özetle kaydedilir; ham credential ve açık session ID audit özetine girmez.
- Maker-checker etkisi: Bu dilimde politika değiştirme yüzeyi yoktur. Üretim
  oturum politikası sonradan `OPEN-BNK-020` kapsamında
  `USER-DECLARATION-2026-07-22-OPEN-BNK-020` referansıyla banka onaylı duruma
  gelmiştir; değişiklik onay akışının runtime uygulaması bu kanıtın kapsamında
  değildir.
- Geri alma: Session servisi LDAP başarısında zorunludur. Güvenli pasifleştirme yerine oturumlar `REVOKED` yapılıp önceki sürüme kontrollü dönülmelidir.
- Kalan risk: BFF, `__Host-session`, synchronizer-token CSRF, tek aktif oturum,
  `PT1H` idle, `PT10H` mutlak süre, merkezi iptal, üretim deposu/şifreleme ve
  `P90D` saklama karara bağlanmıştır; mevcut runtime ve üretim altyapısı bu
  politikayı henüz uygulamamaktadır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- IAM: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired
- `OPEN-BNK-020` politika onayı: ApprovedByBank
- Onay referansı: `USER-DECLARATION-2026-07-22-OPEN-BNK-020`

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.

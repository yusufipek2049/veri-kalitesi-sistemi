# Aktif İterasyonlar

## Seçim Kuralı

Aktif bağlam yalnız kronolojik olarak en güncel yedi iterasyon kaydını içerir.
Sıra; tarih, iterasyon numarası, dosya adı ve iç bağımlılıkla doğrulanmıştır.
İterasyon 36 ana planı bu yedi kapanış kaydının üst çalışma planıdır ve sayıma
dahil değildir.

## En Güncel Yedi

| Sıra | İterasyon | Durum | Sonuç |
| --- | --- | --- | --- |
| 1 | [DQ-CAP-PROTOTYPE-03](DQ-CAP-PROTOTYPE-03-Skor-Katki-ve-Rol-Dashboard.md) | `PrototypeVerified` | Yeniden üretilebilir katkı grafiği, fail-closed dönem karşılaştırması ve ortak yetkili API üzerinde yönetici/mühendis görünümü; production readiness/banka onayı değildir. |
| 2 | [DQ-CAP-PROTOTYPE-02](DQ-CAP-PROTOTYPE-02-Kural-IR-Shadow-ve-Kanit.md) | `PrototypeVerified` | Ortak sürümlü kural IR'i, yedi açık kapsam, yaşam döngüsünden ayrı SHADOW modu ve veri-minimum ihlal kanıtı; production readiness/banka onayı değildir. |
| 3 | [DQ-CAP-PROTOTYPE-01](DQ-CAP-PROTOTYPE-01-Deterministik-Profilleme-ve-Drift.md) | `PrototypeVerified` | Sürümlü-politika kontrollü dağılım/aykırı değer ve yedi deterministik drift ailesi; politika yokluğunda hükümsüz fail-closed sonuç. Production readiness/banka onayı değildir. |
| 4 | [ENTERPRISE-LAB-03](ENTERPRISE-LAB-03-Canli-Compose-Uctan-Uca-Dogrulama.md) | `PrototypeVerified` | Sekiz healthy servis ve gerçek container ağında Keycloak/secret/ServiceNow/SIEM olumlu-negatif adapter akışları doğrulandı. Production readiness/banka onayı değildir. |
| 5 | [ENTERPRISE-LAB-02](ENTERPRISE-LAB-02-Uygulama-Adaptor-Baglantilari.md) | `PrototypeVerified` | Sentetik Keycloak, yerel secret manager, fake ServiceNow ve SIEM uygulama adaptörleri; veri-minimum/idempotent ve fail-closed negatif sözleşmeler. Production readiness/banka onayı değildir. |
| 6 | [ENTERPRISE-LAB-01](ENTERPRISE-LAB-01-Prototip-Kurumsal-Entegrasyon-Laboratuvari.md) | `PrototypeVerified` | Sentetik/non-production Compose laboratuvarı; sekiz sağlıklı servis, fail-closed ortam kapısı ve PostgreSQL streaming standby doğrulandı. Production readiness/banka onayı değildir. |
| 7 | [36H2](Iterasyon-36H2-Is-Yurutme-Yasam-Dongusu.md) | `TechnicallyVerified` | Bounded timeout/iptal, production reaper ve atomik execution+job iptali controller birim/PostgreSQL kapıları ve reviewer `APPROVED` kararıyla doğrulandı. |

## Aktif Plan

- [İterasyon 36 ana planı](Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md)
- [Aktif yol haritası](Kalan-Iterasyonlar-Banka-Yol-Haritasi.md)
- [Tek sıradaki çalışma paketi](../NEXT_STEP.md)

Önceki iterasyon kayıtları tarihsel kanıt olarak
[archive/iterations](../archive/iterations/README.md) altında tutulur ve güncel
durum için kanonik kaynak değildir.

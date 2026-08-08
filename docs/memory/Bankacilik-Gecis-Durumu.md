---
type: banking-transition-status
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-29
---

# Bankacılık Geçiş Durumu

## Hazırlık Özeti

| Alan | Teknik durum | Üretim/banka durumu |
| --- | --- | --- |
| Güvenilir aktör, RBAC ve BFF oturumu | teknik sözleşmeler ve negatif testler belgeli | gerçek IdP, rol eşlemesi, PAM ve HA store açık |
| Merkezi audit ve veri koruma | olay zarfı, redaksiyon, outbox, sınıflandırma ve yaşam döngüsü çekirdeği belgeli | WORM/SIEM, banka sınıflandırma sözlüğü ve fiziksel işletim açık |
| Maker-checker | kural, skor ve veri kaynağı alt kapsamları teknik olarak uygulanmış | banka rolleri, gerçek iş takvimi ve tüm kritik işlem matrisi açık |
| PostgreSQL kalıcılık | issue, execution, scheduling/policy, reporting ve kalıcı iş yaşam döngüsü teknik olarak doğrulanmış | HA PostgreSQL ve production işletim kanıtı açık |
| ServiceNow | veri-minimum sözleşme, retry/dead-letter/circuit-breaker çekirdeği belgeli | gerçek tablo/alan/durum, servis hesabı ve hukuki aktarım değerlendirmesi açık |
| Saklama/DR | politika, legal hold, imha işi ve arşiv geri çağırma çekirdeği belgeli | fiziksel adaptör, yedek şifreleme, restore tatbikatı ve onaylar açık |
| Dışa aktarma | maskeli önizleme ve salt okunur audit ekranı mevcut | DLP/watermark/maker-checker/süreli indirme olmadan kapalı |

## Değişmez Geçiş Kapıları

- Üretim kaynaklarına yalnız salt okunur erişim.
- Secret, token, parola veya ham hassas veri metadata/audit/log içinde tutulmaz.
- Güvenilir identity/session bağlamı yoksa erişim reddedilir.
- Kritik audit/outbox başarısızlığında mutasyon geri alınır.
- Teknik hata ile kalite başarısızlığı ayrı durum ve metriklerdir.
- Banka onayı bulunmayan politika veya dışa aktarma yolu olumlu sonuç üretmez.
- `TechnicallyVerified`, mevzuat uyumu veya üretim uygunluğu anlamına gelmez.

## Üretim Kararı

**Hazır değil.** Bağımlılıkları tamamlanmış yeni bir `Next`/`READY` teknik paket
yoktur. Açık dış bağımlılıklar [Açık Konular](Acik-Konular.md) ve
[backlogda](Sonraki-Adimlar.md), son tamamlanan paket
[NEXT_STEP](../../NEXT_STEP.md), ayrıntılı tarihsel geçiş kaydı ise
[arşivde](../../docs/archive/project-memory-2026-07-24/Bankacilik-Gecis-Durumu.md)
kayıtlıdır.

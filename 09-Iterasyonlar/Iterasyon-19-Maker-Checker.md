---
iteration: 19
status: in-progress
primary_module: rules-and-scoring
---

# İterasyon 19 — Maker-Checker

## İlk Dikey Dilim

Kural sürüm aktivasyonu ve scoring configuration aktivasyonu.

## Akış

`DRAFT -> SUBMITTED -> APPROVED/REJECTED -> ACTIVE`

## Kurallar

- Maker ve checker farklı ActorContext olmalıdır.
- Onay belirli değişiklik sürümüne bağlıdır.
- İçerik değişirse eski onay geçersizdir.
- Ret/gerekçe ve süre aşımı audit edilir.
- Acil override bu iterasyonun kapsamı dışındadır.

## Kabul

- Aynı aktör onaylayamaz.
- Yetkisiz checker reddedilir.
- Onaysız sürüm aktive edilemez.
- Eski sürümler ve skor geçmişi değişmez.

## Dilim 19A Kapanisi

`TechnicallyVerified` kapsam:

- `CRITICAL` kuralın doğrudan aktivasyonu kapatıldı; başarılı son sürüm testi ve sahiplik ön koşulları korundu.
- Güvenilir, geçerli politika sürümündeki maker context onay isteği oluşturur; farklı checker rolü ve dataset kapsamı kararı verir.
- Maker=checker, eksik/sahte/süresi dolmuş context, yanlış rol ve yanlış dataset kapsamı fail-closed reddedilir.
- Onay belirli `RuleVersion` kimliğine bağlıdır; yeni sürüm eski isteğin kararını devralmaz.
- Onay veya ret, redakte audit outbox ile atomik saklanır; yalnız onay kuralı `ACTIVE` yapar.
- On bir yeni testle toplam 190 test geçti; kural hedef grubu 49 testle geçti.

## Dilim 19B Kapanisi

`TechnicallyVerified` kapsam:

- Skor konfigürasyonu güvenilir maker tarafından pasif ve değişmez sürüm olarak oluşturulur; farklı güvenilir checker kararı olmadan aktifleşmez.
- Maker=checker, eksik/süresi dolmuş context, yanlış rol, eksik kurum kapsamı, ayrıcalıklı rol atlama girişimi ve servis hesabı fail-closed reddedilir.
- Onay belirli konfigürasyona ve politika sürümüne bağlıdır; yalnız en yeni taslak onaylanabilir, ret aktif sürümü değiştirmez.
- Talep ve karar/aktivasyon redakte audit outbox ile atomik saklanır; teknik stage hatasında domain değişikliği rollback olur.
- Geçmiş skorlar eski konfigürasyon sürümünü korur; geriye uyumlu SQLite şema testi onay tablosunu doğrular.
- On iki yeni testle toplam 202 test geçti; skorlama hedef grubu 46 testle geçti.

## Dilim 19C Kapanisi

`TechnicallyVerified` kapsam:

- Bekleyen kritik kural onay isteğini yalnız kayıtlı RuleVersion maker'ı, güncel güvenilir rol ve dataset kapsamıyla geri çekebilir.
- Geri çekme sürüme bağlı `WITHDRAWN` terminal durumudur; kural taslak kalır ve yeni RuleVersion etkilenmez.
- Eksik/süresi dolmuş context, başka maker, yanlış rol/kapsam, servis hesabı ve ayrıcalıkla rol atlama girişimi fail-closed reddedilir.
- Gerekçe domain geçmişinde kalır; audit özeti teknik kimlikler, politika sürümü ve durumla sınırlandırılır.
- Geri çekme ve redakte audit outbox olayı atomiktir; stage hatasında istek `PENDING` kalır.
- On yeni testle toplam 212 test geçti; kural hedef grubu 59 testle geçti.

## Dilim 19D Kapanışı

`TechnicallyVerified` kapsam:

- Onay hedefi 3 iş günü, otomatik sona erme 10 iş günü olarak sürümlü politikaya bağlandı; süre istek oluşturma anında başlar.
- Enjekte edilen sürümlü iş takvimi hedef ve sona erme zamanlarını üretir; naive veya geçersiz zaman penceresi fail-closed reddedilir.
- Süresi dolmuş istek onaylanamaz veya geri çekilemez; yalnız güvenilir, yetkili ve kapsam içi servis context'i isteği `EXPIRED` yapabilir.
- Süre aşımı ve redakte audit outbox aynı transaction'dadır; audit-stage arızasında istek `PENDING` kalır.
- Aynı RuleVersion için tek bekleyen istek korunurken sona ermiş istek geçmişi silinmeden yeni istek oluşturulabilir.
- Eski SQLite onay tablosu hedef/sona erme/takvim alanlarına ve kısmi benzersiz indekse geçmişi kaybetmeden taşınır.
- Sekiz yeni testle toplam 710 test geçti; kural hedef grubu 67 testle geçti.

Gerçek banka iş günü/tatil kaynağı, banka onaylı süre aşımı servis rolü, worker operasyonu, veri kaynağı aktivasyonu, legacy maker geçişi ve kurum onayları `ComplianceReviewRequired` durumundadır.

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

## Dilim 19E Kapanışı

`TechnicallyVerified` kapsam:

- Başarılı güncel bağlantı testi ve Data Owner bulunan kaynak revizyonu yalnız güvenilir maker context'iyle onaya sunulur.
- Farklı checker rolü ve aynı source kapsamındaki aktör onaylarsa kaynak `ACTIVE` olur; ret kaynağı `TEST_SUCCEEDED` bırakır.
- Maker=checker, eksik/süresi dolmuş context, yanlış rol/kapsam, servis hesabı ve ayrıcalıkla rol atlama girişimi fail-closed reddedilir.
- Onay belirli veri kaynağı revizyonuna bağlıdır; eski revizyon aktive edilemez ve aynı revizyon için tek bekleyen istek tutulur.
- Karar, kaynak durum geçişi ve veri-minimum audit outbox aynı transaction'dadır; stage arızasında istek ve kaynak durumu geri alınır.
- Legacy SQLite veri kaynağı şeması revizyon alanına veri kaybetmeden taşınır; aktif kaynak metadata, kural ve execution önkoşullarında test edilmiş kaynak olarak kabul edilir.
- 10 yeni testle toplam 720 test geçti; veri kaynağı hedef grubu 47 testle geçti.

Gerçek banka maker/checker rol kodları ve LDAP eşlemesi, kaynak kritiklik sözlüğü, bağlantı güncellemesinde revizyon artırma, pasife alma, kaynak onay isteği geri çekme/süre aşımı ve kurum onayları `ComplianceReviewRequired` durumundadır.

## Dilim 19F Kapanışı

`TechnicallyVerified` kapsam:

- Bekleyen kaynak aktivasyon isteğini yalnız kayıtlı maker, güncel güvenilir rol ve source kapsamıyla geri çekebilir.
- Kaynak onay hedefi 3 iş günü, otomatik sona erme 10 iş günü olarak sürümlü politikaya bağlandı; süre istek oluşturma anında başlar.
- Sürümlü iş takvimi hedef ve sona erme zamanlarını üretir; eksik/uyumsuz takvim veya geçersiz zaman penceresi fail-closed reddedilir.
- Süresi dolmuş istek onaylanamaz veya geri çekilemez; yalnız güvenilir, yetkili ve kapsam içi servis context'i isteği `EXPIRED` yapabilir.
- Geri çekme/süre aşımı ve redakte audit outbox aynı transaction'dadır; audit-stage arızasında istek `PENDING` kalır.
- `WITHDRAWN` ve `EXPIRED` geçmiş silinmeden aynı kaynak revizyonu için yeni istek oluşturulabilir; legacy SQLite kayıtları nullable zaman alanlarına veri kaybetmeden taşınır.
- 11 yeni testle toplam 731 test geçti; veri kaynağı hedef grubu 58 testle geçti.

Gerçek banka iş günü/tatil kaynağı, banka onaylı maker/checker/worker rol kodları, LDAP eşlemesi ve üretim worker işletimi `ComplianceReviewRequired` durumundadır. Bağlantı güncellemesinde revizyon artırma/onay geçersizleştirme ve pasife alma ayrı ürün artımlarıdır.

## Dilim 19G Kapanışı

`TechnicallyVerified` kapsam:

- Yetkili maker, kaynak kapsamı ve sürümlü politikayla bağlantı yapılandırmasını değişmez aday revizyon olarak oluşturur; ham secret yerine yalnız `secret://` referansı saklanır.
- Aday yapılandırma mevcut çalışan sürüm değiştirilmeden salt okunur bağlayıcıyla test edilir.
- Başarısız sınıflandırılmış test mevcut yapılandırma, secret referansı, revizyon, kaynak durumu, son başarılı test ve eski bekleyen onayı korur.
- Beklenmeyen bağlayıcı arızası ayrı `TechnicalError` yolunda kalır; aday veya çalışan sürüm değiştirilmez.
- Başarılı aday atomik terfiyle güncel revizyon olur, kaynak yeniden aktivasyon için `TEST_SUCCEEDED` durumuna alınır ve eski revizyona bağlı bekleyen onay `INVALIDATED` olur.
- Aday oluşturma ve terfi/onay invalidasyonu veri-minimum audit outbox ile atomiktir; stage arızasında domain ve test kayıtları geri alınır.
- Legacy bağlantı testleri revizyon `1` ile, mevcut kaynak yapılandırmaları ilk `PROMOTED` revizyon olarak veri kaybetmeden taşınır.
- 13 yeni testle toplam 744 test geçti; veri kaynağı hedef grubu 71 testle geçti.

Banka onaylı bağlantı güncelleme rolü, gerçek LDAP eşlemesi, üretim migration/çoklu instance eşzamanlılık yaklaşımı ve kontrollü pasife alma `ComplianceReviewRequired` veya açık durumdadır.

# Maker-Checker

## Güven Sınırı

Kritik kural aktivasyonu yalnız güvenilir identity adaptörü tarafından üretilmiş, süresi ve politika sürümü geçerli `ActorContext` ile yürütülür. İstekten gelen serbest aktör, rol veya dataset kapsamı yetki kanıtı değildir.

## Kural Aktivasyonu

1. `CRITICAL` `RuleVersion`, sürümlü politika içindeki maker rolü ve dataset kapsamına sahip güvenilir context ile oluşturulur; hazırlayan aktör sürümde saklanır.
2. Son `RuleVersion` başarılı test sonucu ve sahiplik ön koşulunu karşıladığında yalnız kayıtlı hazırlayan aktör onay isteği oluşturur.
3. Ayrı checker rolü ve aynı dataset kapsamına sahip farklı aktör isteği onaylar veya reddeder.
4. Onay kararı, kuralın `ACTIVE` geçişi ve redakte audit outbox olayı aynı SQLite transaction'ında saklanır.
5. Yeni `RuleVersion`, önceki sürümün bekleyen veya verilmiş kararını devralmaz.

Kritik olmayan kural aktivasyonu mevcut başarılı-test ön koşuluyla doğrudan devam eder. Politika bulunmadığında kritik aktivasyon fail-closed reddedilir.

## Veri Minimizasyonu

Audit özeti yalnız teknik kural sürümü/onay isteği kimliklerini, politika sürümünü ve karar durumunu taşır. Karar gerekçe kodu domain geçmişinde tutulur ancak audit özetine alınmaz; session kimliği yalnız digest olarak saklanır.

## Açık Kapsam

- Bekleyen isteğin süre aşımı ve maker tarafından geri çekilmesi.
- Skor konfigürasyonu ve diğer kritik işlem sınıfları için ayrı onay politikaları.
- Banka onaylı maker/checker rol kodları ve gerçek LDAP grup eşlemesi.
- Hazırlayanı bilinmeyen legacy kritik sürümlerin yeni güvenilir sürüme taşınma prosedürü.
- Acil durum override akışı.

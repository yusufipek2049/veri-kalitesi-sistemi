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

## Skorlama Politikası ve Anti-Gaming

`DQ-SCR-014`, `DQ-SCR-015`, `DQ-SCR-017`, `DQ-SCR-022`, `DQ-SCR-023` ve
`DQ-SCR-030` uyarınca aşağıdaki yüksek etkili işlemler güvenilir bağlam, gerekçe,
sürüm ve maker-checker kararı olmadan etkinleşmez:

- üretim eşik veya ağırlık değişikliği,
- kritikliği düşürme veya kritik kural davranışını gevşetme,
- kuralı pasifleştirme ya da ölçüm kapsamını daraltma,
- ölçüm yeterliliği, geçerlilik veya kullanım kararı politikasını gevşetme,
- süreli istisna veya ham skordan ayrı değerlendirme/override oluşturma,
- resmî trend, rapor veya remediation önceliğini etkileyen model/politika değişikliği.

İstisna ve override süresiz olamaz; risk kabulü ve bitiş zamanı taşır. Ham skor
değişmez. Audit/outbox kalıcılaştırılamazsa kritik işlem fail-closed tamamlanmaz.
Banka rol kodları, politika kapsam matrisi, yeterlilik/blokaj yetkileri ve acil
durum prosedürü `OPEN-023`, `OPEN-BNK-004`,
`OPEN-BNK-005` ve `OPEN-BNK-006` altında açık kalır.

## Açık Kapsam

- Bekleyen isteğin süre aşımı ve maker tarafından geri çekilmesi.
- Skorlama politikası, istisna ve override için banka onaylı rol/kapsam matrisi.
- Banka onaylı maker/checker rol kodları ve gerçek LDAP grup eşlemesi.
- Hazırlayanı bilinmeyen legacy kritik sürümlerin yeni güvenilir sürüme taşınma prosedürü.
- Acil durum değerlendirme/override akışının süre, risk kabulü ve raporlama biçimi.

# Saklama, İmha ve Legal Hold Runbook

1. Politika sürümünü ve kayıt türünü doğrula.
2. Legal hold kontrolü yap.
3. İmha kapsamını dry-run ile üret.
4. Yetki ve gerekiyorsa maker-checker onayı al.
5. İdempotent imha işini çalıştır.
6. Sonuç sayacı ve başarısız kayıtları audit et.
7. Ham silinen değeri audit veya rapora yazma.
8. Geri çağırma/itiraz süresi varsa iş akışını kapatma.

## İterasyon 25A Teknik Sınırı

- Dry-run, sürümlü kayıt sınıfı politikasından takvimsel saklama sonunu hesaplar.
- Aktif legal hold veya çözümlenemeyen hold durumu otomatik imhayı engeller.
- `ComplianceReviewRequired` politika süresi dolsa bile imha yetkisi üretmez.
- Bu aşamada fiziksel silme, anonimleştirme, arşivleme veya geri çağırma çalıştırılmaz.

## İterasyon 25B Teknik Sınırı

- Legal hold oluşturma ve serbest bırakma append-only olay geçmişinde saklanır.
- Oluşturan aktör aynı hold'u serbest bırakamaz; iki işlem de güvenilir rol ve
  veri kapsamı gerektirir.
- Aynı kayıttaki tüm aktif hold'lar kaldırılmadan imha uygunluğu üretilemez.
- Domain olayı ve veri-minimum audit outbox atomiktir; merkezi yayın kesintisinde
  audit olayı kalıcı `PENDING` durumda tutulur.
- Banka rol/reason code eşlemesi, fiziksel imha ve arşiv geri çağırma açık kalır.

## İterasyon 25C Teknik Sınırı

- İmha işi yalnız opak onay referanslı `ApprovedByBank` politika, süresi dolmuş
  kayıt ve aktif legal hold bulunmaması halinde hazırlanabilir.
- Aynı idempotency anahtarı ve payload tek değişmez iş üretir; anahtarın farklı
  payload ile kullanımı fail-closed reddedilir.
- Hazırlayan güvenilir normal kullanıcı ile sonuç kanıtını yazan güvenilir servis
  aktörü farklı olmalı ve ikisi de sürümlü rol ile veri kapsamına uymalıdır.
- Sonuç yalnız `SUCCEEDED` veya `FAILED_TECHNICAL`, yöntem, sayaçlar ve opak kanıt
  referansı taşır. Ham silinen değer, kayıt/kapsam kimliği ve serbest hata metni
  audit özetine yazılmaz.
- İş ve sonuç geçmişi append-only; her yazım redakte audit outbox ile atomiktir.
- Bu dilim fiziksel silme, anonimleştirme veya arşivleme adaptörü çağırmaz.
  Üretim adaptörü, gerçek onay resolver'ı, yedek re-delete ve arşiv geri çağırma
  banka kararlarını bekler.

## İterasyon 25D Teknik Sınırı

- Yalnız audit ve kalite skoru arşivleri için opak referanslı geri çağırma talebi
  oluşturulur; arşiv içeriği okunmaz, kopyalanmaz veya taşınmaz.
- Talep güvenilir normal kullanıcı, sürümlü requester rolü, veri kapsamı ve izinli
  amaç kodu gerektirir. Ham arşiv/kapsam kimliği yerine SHA-256 özeti saklanır.
- Onay veya ret yalnız farklı güvenilir normal kullanıcı, karar rolü, aynı veri
  kapsamı ve izinli karar gerekçesiyle verilebilir.
- Talep ve karar append-only saklanır; aynı idempotency anahtarı/payload tek talep,
  aynı karar tek terminal olay üretir.
- Talep/karar ile redakte audit outbox aynı transaction'dadır. Audit özeti arşiv
  referansı, kapsam kimliği, idempotency anahtarı veya serbest metin taşımaz.
- Gerçek arşiv deposu, veri getirme/taşıma adaptörü, erişim süresi, indirme/DLP,
  üretim maker-checker rol eşlemesi ve geri çağrılan kopyanın yeniden imhası banka
  kararlarını bekler.

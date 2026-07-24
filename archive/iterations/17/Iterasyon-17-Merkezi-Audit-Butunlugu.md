---
iteration: 17
status: technically-verified
primary_module: audit
---

# İterasyon 17 — Merkezi Audit Bütünlüğü

## Hedef

Dağınık `AuditRecord/AuditSink` kullanımlarını merkezi, redakte edilmiş ve bütünlüğü doğrulanabilir audit sınırına taşımak.

## Kapsam

- `veri_kalitesi.audit` paketi.
- Sürümlü `AuditEvent`.
- ActorContext, correlation ID ve event time.
- Redaksiyon allowlist'i.
- Olay hash'ı ve önceki hash için adaptör sözleşmesi.
- Data source ve rüle servislerinden iki gerçek dikey dilimin migrasyonu.
- Audit yazma hatası politika arayüzü.
- Mevcut kayıtlarla geriye uyum adaptörü.

## Kritik Not

WORM/SIEM ürünü bu iterasyonda seçilmez. Bütünlük sağlayıcı arayüzü hazırlanır.

## Kabul

- Secret ve ham hassas değer audit olayına giremez.
- Event zinciri değiştirilmiş kaydı tespit eder.
- Kritik işlemde audit failure policy test edilir.
- Eski testler korunur.

## Dilim 17A Kapanışı

`TechnicallyVerified` kapsam:

- Sürümlü ortak audit olay zarfı ve allowlist tabanlı redaksiyon eklendi.
- SQLite prototip deposunda append-only SHA-256 hash zinciri ve bütünlük doğrulaması eklendi.
- `FAIL_CLOSED` ve yapılandırılmış kalıcı tampon gerektiren `DURABLE_BUFFER` politikaları açıkça modellendi.
- Dashboard authorization karar olayı merkezi audit sınırına taşındı.
- 8 yeni audit testiyle birlikte toplam 147 test geçti.

Bu kapanış tüm İterasyon 17 kapsamını tamamlamaz. Veri kaynağı ve kural servislerindeki eski audit yollarının merkezi sınıra taşınması, geriye uyum adaptörü ve `FR-078` sorgu/dışarı aktarma kapsamı 17B veya sonraki ilgili iterasyonlarda ele alınacaktır. SQLite hash zinciri değişikliği tespit eder; WORM, imza veya kurumsal SIEM onayı yerine geçmez.

## Dilim 17B Kapanışı

`TechnicallyVerified` kapsam:

- Veri kaynağı ve kural servisleri zorunlu merkezi `AuditSink` ile `AuditEventInput` üretir hale getirildi.
- Kaynak oluşturma/bağlantı testi/metadata/profil ve kural oluşturma/sürüm/test/aktivasyon olayları merkezi allowlist'e eklendi.
- Correlation ID servis girdisinden korunuyor; verilmezse operasyon için üretiliyor, boş değer iş kaydından önce reddediliyor.
- `data_sources.models.AuditRecord` ve yeni legacy tablo yazımları kaldırıldı; eski tablo fiziksel olarak korunuyor.
- Zamanlama ve skorlama tarafındaki henüz taşınmamış model merkezi pakette açıkça `LegacyAuditRecord` olarak isimlendirildi.
- 3 yeni testle toplam 150 test geçti.

Bu kapanış tüm İterasyon 17 kapsamını tamamlamaz. Mevcut servis transaction'i audit yazımından önce commit edildiği için audit hatası çağıranı durdursa da önceki iş commitini geri alamaz. Transactional outbox veya ortak transaction, zamanlama/skorlama geçişi ve tarihsel `audit_records` aktarımı 17C kapsamında kalır. `FR-078` İterasyon 24 kapsamındadır.

## Dilim 17C1 Kapanışı

`TechnicallyVerified` kapsam:

- Veri kaynağı ve kural oluşturma işlemleri, iş kaydı ile redakte `PreparedAuditEvent` outbox kaydını aynı SQLite transaction'ında yazar.
- Outbox yazımı başarısızsa iş kaydı rollback olur; merkezi audit deposu erişilemezse iş ve `PENDING` olay birlikte kalıcı kalır.
- Pending olay daha sonra merkezi hash zincirine yayınlanabilir; aynı `event_id` ve aynı içerik idempotenttir.
- Aynı `event_id` farklı içerikle tekrar kullanılırsa kontrollü doğrulama hatası oluşur.
- 2 yeni testle toplam 152 test geçti.

Bu kapanış tüm İterasyon 17 kapsamını tamamlamaz. Bağlantı testi, metadata, profil, kural surumu/testi/aktivasyonu henüz transactional outbox kullanmaz. Üretim publisher worker'ı, retry/backoff ve alarm metrikleri; zamanlama/skorlama geçişi ve tarihsel `audit_records` aktarımı açıktır.

## Dilim 17C2 Kapanışı

`TechnicallyVerified` kapsam:

- Bağlantı testi, metadata keşfi basari/basarisizligi, profil, kural sürümü, kural testi ve aktivasyon yazımları domain kaydı ile redakte audit olayını aynı SQLite transaction'ındaki outbox'a yazar.
- Hedeflenen her repository yazım yolu için outbox-stage hatasının domain değişikliğini rollback ettiği test edildi.
- Merkezi audit deposu kesintisinde bağlantı testi ve yeni kural sürümü kalıcı kalırken olay `PENDING` durumda korunur.
- Veri kaynağı ve kural servislerinde kalıcı yazımdan sonra doğrudan merkezi audit çağrısı kalmadı.
- 9 yeni testle toplam 161 test geçti.

Bu kapanış tüm İterasyon 17 kapsamını tamamlamaz. Zamanlama/skorlama `LegacyAuditRecord` geçişi ve tarihsel `audit_records` aktarımı 17D kapsamında; üretim publisher worker'ı, retry/backoff, claim/eszamanlilik, alarm ve saklama politikası ayrı operasyon artımında açıktır. `FR-078` İterasyon 24 kapsamındadır.

## Dilim 17D1 Kapanışı

`TechnicallyVerified` kapsam:

- Schedule oluşturma opsiyonel `ScheduleAuditSink` ve `LegacyAuditRecord` yerine zorunlu transactional audit kullanır.
- Schedule inserti ile redakte `SCHEDULE_CREATED` olayı aynı SQLite transaction'ındaki outbox'a yazılır.
- Outbox-stage hatası schedule insertini rollback eder; merkezi audit kesintisinde schedule ve `PENDING` olay kalıcı kalır.
- Correlation ID olay zarfına taşınır; schedule adı ve kural sürüm kimlikleri audit özetine alınmaz.
- `FR-037` sonraki beş tetik zamanı onizlemesi ve idempotent scheduler davranışı korunur.
- 3 yeni testle toplam 164 test geçti.

Bu kapanış tüm İterasyon 17 kapsamını tamamlamaz. Skor konfigürasyonu aktivasyonundaki `LegacyAuditRecord/append_audit` yolu 17D2 kapsamında; tarihsel `audit_records` aktarımı ve üretim publisher worker'ı ayrı artımlarda açıktır. `FR-078` İterasyon 24 kapsamındadır.

## Dilim 17D2 Kapanışı

`TechnicallyVerified` kapsam:

- Skor konfigürasyonu aktivasyonu opsiyonel legacy sink yerine zorunlu transactional audit kullanır.
- Önceki aktif sürümün pasifleştirilmesi, yeni sürüm inserti ve redakte `SCORING_CONFIGURATION_ACTIVATED` olayı aynı SQLite transaction'ındaki outbox'a yazılır.
- Outbox-stage hatası aktivasyonun tümünü rollback eder; merkezi kesintide yeni aktif sürüm ve `PENDING` olay kalıcı kalır.
- Eski/yeni eşik, boyut ağırlığı ve kritiklik ağırlığı değerleri sabit scalar allowlist alanlarıyla denetlenebilir kalır.
- Aktif kodda `LegacyAuditRecord/append_audit` kullanımı kalmadığı için geçici model ve public ihracı kaldırıldı.
- 3 yeni testle toplam 167 test geçti.

Bu kapanış aktif uygulama yazımlarının merkezi audit geçişini tamamlar ancak İterasyon 17'nin tarihsel veri kapsamını tamamlamaz. Eski `audit_records` tablolarının envanteri ve kontrollü aktarımı 17E kapsamında; üretim publisher worker'ı ayrı operasyon artımında açıktır. `FR-078` İterasyon 24 kapsamındadır.

## Dilim 17E Kapanışı

`TechnicallyVerified` kapsam:

- Depoda kalan tek fiziksel legacy `audit_records` şeması envanterlendi; aktif kodun bu tabloya yazmadığı doğrulandı.
- Salt okunur aktarım aracı yalnız `PRAGMA` ve `SELECT` ile kaynak kayıtları okur, desteklenen olayları güncel redaktörden geçirir ve merkezi hash zincirine ekler.
- Olay kimliği ve correlation özeti kaynak/kayıt kimliğinden deterministik üretilir; aynı aktarımın tekrar çalışması çift olay oluşturmaz.
- Bozuk JSON, desteklenmeyen eylem ve naive zaman damgası teknik hata değildir; ham kimlik taşımayan veri kalitesi sorun kodlarıyla raporlanır.
- Merkezi repository erişim hatası ayrı teknik hata olarak yükseltilir; kaynak kayıt hiçbir başarı veya hata yolunda güncellenmez ya da silinmez.
- 3 yeni testle toplam 170 test geçti; merkezi zincir bütünlüğü ve kaynak salt okunurluğu doğrulandı.

Bu kapanış İterasyon 17'nin kod ve sentetik test kapsamını teknik olarak tamamlar. Gerçek üretim envanteri/aktarımı, yedek ve geri dönüş onayı, üretim outbox publisher worker'ı, WORM/imza/SIEM ve `FR-078` sorgu/dışa aktarma yüzeyi kapsam dışıdır. Banka bilgi güvenliği, iç kontrol ve hukuk/uyum onayları `ComplianceReviewRequired` kalır.

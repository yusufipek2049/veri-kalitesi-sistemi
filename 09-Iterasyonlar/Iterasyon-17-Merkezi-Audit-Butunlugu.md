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
- Olay hash'i ve önceki hash için adaptör sözleşmesi.
- Data source ve rule servislerinden iki gerçek dikey dilimin migrasyonu.
- Audit yazma hatası politika arayüzü.
- Mevcut kayıtlarla geriye uyum adaptörü.

## Kritik Not

WORM/SIEM ürünü bu iterasyonda seçilmez. Bütünlük sağlayıcı arayüzü hazırlanır.

## Kabul

- Secret ve ham hassas değer audit olayına giremez.
- Event zinciri değiştirilmiş kaydı tespit eder.
- Kritik işlemde audit failure policy test edilir.
- Eski testler korunur.

## Dilim 17A Kapanisi

`TechnicallyVerified` kapsam:

- Surumlu ortak audit olay zarfi ve allowlist tabanli redaksiyon eklendi.
- SQLite prototip deposunda append-only SHA-256 hash zinciri ve butunluk dogrulamasi eklendi.
- `FAIL_CLOSED` ve yapilandirilmis kalici tampon gerektiren `DURABLE_BUFFER` politikalari acikca modellendi.
- Dashboard authorization karar olayi merkezi audit sinirina tasindi.
- 8 yeni audit testiyle birlikte toplam 147 test gecti.

Bu kapanis tum Iterasyon 17 kapsamini tamamlamaz. Veri kaynagi ve kural servislerindeki eski audit yollarinin merkezi sinira tasinmasi, geriye uyum adaptoru ve `FR-078` sorgu/disari aktarma kapsami 17B veya sonraki ilgili iterasyonlarda ele alinacaktir. SQLite hash zinciri degisikligi tespit eder; WORM, imza veya kurumsal SIEM onayi yerine gecmez.

## Dilim 17B Kapanisi

`TechnicallyVerified` kapsam:

- Veri kaynagi ve kural servisleri zorunlu merkezi `AuditSink` ile `AuditEventInput` uretir hale getirildi.
- Kaynak olusturma/baglanti testi/metadata/profil ve kural olusturma/surum/test/aktivasyon olaylari merkezi allowlist'e eklendi.
- Correlation ID servis girdisinden korunuyor; verilmezse operasyon icin uretiliyor, bos deger is kaydindan once reddediliyor.
- `data_sources.models.AuditRecord` ve yeni legacy tablo yazimlari kaldirildi; eski tablo fiziksel olarak korunuyor.
- Zamanlama ve skorlama tarafindaki henuz tasinmamis model merkezi pakette acikca `LegacyAuditRecord` olarak isimlendirildi.
- 3 yeni testle toplam 150 test gecti.

Bu kapanis tum Iterasyon 17 kapsamini tamamlamaz. Mevcut servis transaction'i audit yazimindan once commit edildigi icin audit hatasi cagirani durdursa da onceki is commitini geri alamaz. Transactional outbox veya ortak transaction, zamanlama/skorlama gecisi ve tarihsel `audit_records` aktarimi 17C kapsaminda kalir. `FR-078` Iterasyon 24 kapsamindadir.

## Dilim 17C1 Kapanisi

`TechnicallyVerified` kapsam:

- Veri kaynagi ve kural olusturma islemleri, is kaydi ile redakte `PreparedAuditEvent` outbox kaydini ayni SQLite transaction'inda yazar.
- Outbox yazimi basarisizsa is kaydi rollback olur; merkezi audit deposu erisilemezse is ve `PENDING` olay birlikte kalici kalir.
- Pending olay daha sonra merkezi hash zincirine yayinlanabilir; ayni `event_id` ve ayni icerik idempotenttir.
- Ayni `event_id` farkli icerikle tekrar kullanilirsa kontrollu dogrulama hatasi olusur.
- 2 yeni testle toplam 152 test gecti.

Bu kapanis tum Iterasyon 17 kapsamini tamamlamaz. Baglanti testi, metadata, profil, kural surumu/testi/aktivasyonu henuz transactional outbox kullanmaz. Uretim publisher worker'i, retry/backoff ve alarm metrikleri; zamanlama/skorlama gecisi ve tarihsel `audit_records` aktarimi aciktir.

## Dilim 17C2 Kapanisi

`TechnicallyVerified` kapsam:

- Baglanti testi, metadata kesfi basari/basarisizligi, profil, kural surumu, kural testi ve aktivasyon yazimlari domain kaydi ile redakte audit olayini ayni SQLite transaction'indaki outbox'a yazar.
- Hedeflenen her repository yazim yolu icin outbox-stage hatasinin domain degisikligini rollback ettigi test edildi.
- Merkezi audit deposu kesintisinde baglanti testi ve yeni kural surumu kalici kalirken olay `PENDING` durumda korunur.
- Veri kaynagi ve kural servislerinde kalici yazimdan sonra dogrudan merkezi audit cagrisi kalmadi.
- 9 yeni testle toplam 161 test gecti.

Bu kapanis tum Iterasyon 17 kapsamini tamamlamaz. Zamanlama/skorlama `LegacyAuditRecord` gecisi ve tarihsel `audit_records` aktarimi 17D kapsaminda; uretim publisher worker'i, retry/backoff, claim/eszamanlilik, alarm ve saklama politikasi ayri operasyon artiminda aciktir. `FR-078` Iterasyon 24 kapsamindadir.

## Dilim 17D1 Kapanisi

`TechnicallyVerified` kapsam:

- Schedule olusturma opsiyonel `ScheduleAuditSink` ve `LegacyAuditRecord` yerine zorunlu transactional audit kullanir.
- Schedule inserti ile redakte `SCHEDULE_CREATED` olayi ayni SQLite transaction'indaki outbox'a yazilir.
- Outbox-stage hatasi schedule insertini rollback eder; merkezi audit kesintisinde schedule ve `PENDING` olay kalici kalir.
- Correlation ID olay zarfina tasinir; schedule adi ve kural surum kimlikleri audit ozetine alinmaz.
- `FR-037` sonraki bes tetik zamani onizlemesi ve idempotent scheduler davranisi korunur.
- 3 yeni testle toplam 164 test gecti.

Bu kapanis tum Iterasyon 17 kapsamini tamamlamaz. Skor konfigürasyonu aktivasyonundaki `LegacyAuditRecord/append_audit` yolu 17D2 kapsaminda; tarihsel `audit_records` aktarimi ve uretim publisher worker'i ayri artimlarda aciktir. `FR-078` Iterasyon 24 kapsamindadir.

## Dilim 17D2 Kapanisi

`TechnicallyVerified` kapsam:

- Skor konfigürasyonu aktivasyonu opsiyonel legacy sink yerine zorunlu transactional audit kullanir.
- Onceki aktif surumun pasiflestirilmesi, yeni surum inserti ve redakte `SCORING_CONFIGURATION_ACTIVATED` olayi ayni SQLite transaction'indaki outbox'a yazilir.
- Outbox-stage hatasi aktivasyonun tumunu rollback eder; merkezi kesintide yeni aktif surum ve `PENDING` olay kalici kalir.
- Eski/yeni esik, boyut agirligi ve kritiklik agirligi degerleri sabit scalar allowlist alanlariyla denetlenebilir kalir.
- Aktif kodda `LegacyAuditRecord/append_audit` kullanimi kalmadigi icin gecici model ve public ihraci kaldirildi.
- 3 yeni testle toplam 167 test gecti.

Bu kapanis aktif uygulama yazimlarinin merkezi audit gecisini tamamlar ancak Iterasyon 17'nin tarihsel veri kapsamini tamamlamaz. Eski `audit_records` tablolarinin envanteri ve kontrollu aktarimi 17E kapsaminda; uretim publisher worker'i ayri operasyon artiminda aciktir. `FR-078` Iterasyon 24 kapsamindadir.

## Dilim 17E Kapanisi

`TechnicallyVerified` kapsam:

- Depoda kalan tek fiziksel legacy `audit_records` semasi envanterlendi; aktif kodun bu tabloya yazmadigi doğrulandı.
- Salt okunur migrator yalnız `PRAGMA` ve `SELECT` ile kaynak kayıtları okur, desteklenen olayları güncel redaktordan geçirir ve merkezi hash zincirine ekler.
- Olay kimliği ve correlation özeti kaynak/kayıt kimliğinden deterministik üretilir; aynı aktarımın tekrar çalışması çift olay oluşturmaz.
- Bozuk JSON, desteklenmeyen eylem ve naive zaman damgası teknik hata değildir; ham kimlik taşımayan veri kalitesi sorun kodlarıyla raporlanır.
- Merkezi repository erişim hatası ayrı teknik hata olarak yükseltilir; kaynak kayıt hiçbir başarı veya hata yolunda güncellenmez ya da silinmez.
- 3 yeni testle toplam 170 test geçti; merkezi zincir bütünlüğü ve kaynak salt okunurluğu doğrulandı.

Bu kapanış Iterasyon 17'nin kod ve sentetik test kapsamını teknik olarak tamamlar. Gerçek üretim envanteri/aktarımı, yedek ve geri dönüş onayı, üretim outbox publisher worker'ı, WORM/imza/SIEM ve `FR-078` sorgu/dışa aktarma yüzeyi kapsam dışıdır. Banka bilgi güvenliği, iç kontrol ve hukuk/uyum onayları `ComplianceReviewRequired` kalır.

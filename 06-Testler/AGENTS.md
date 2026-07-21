# AGENTS.md — Testler Geneli

- Önce test edilen modülün `AGENTS.md` dosyasını ve ilgili kabul kriterlerini oku.
- Testleri FR/UC kimlikleriyle izlenebilir kıl.
- Mutlu yol kadar doğrulama, yetki, teknik hata, timeout, retry ve idempotency yollarını kapsa.
- Harici LDAP, veritabanı ve ServiceNow bağımlılıklarını sözleşme/entegrasyon sınırında taklit et; tüm domain testlerini dış servise bağlama.
- Performans testlerinde veri hacmi, örnekleme yöntemi ve donanım koşulunu kaydet.
- Test verisinde gerçek kişisel veri, token, parola veya kurum bilgisi kullanma.
- Bankacılık kontrol işlerinde güvenilir context yokluğu, rol yükseltme, scope manipülasyonu, maker=checker, audit yazma hatası, redaksiyon ve dışa aktarma sızıntısı için negatif test ekle.
- Teknik kontrolü `TechnicallyVerified` yapmadan önce test dosyası, test adı, çalışma komutu ve kanıt yolunu kaydet.
- KVKK ihlal testinde gerçek bildirim göndermeyen fake adapter kullan.
- ServiceNow/SIEM sözleşme testlerinde yalnız sentetik ve allowlist alanları kullan.

## Sentetik Veri Test Kuralları

- Sentetik dataset üretimini etkin `SyntheticDatasetPolicy`, üretici/şema/politika
  sürümü ve random seed olmadan başlatma.
- Gerçek müşteri verisini üretme, kopyalama veya yalnız kimliğini değiştirerek
  sentetik/anonim diye etiketleme.
- Sentetik köken metadata'sını kaldırma; ground truth'u iş verisi veya runtime
  çıktısıyla karıştırma.
- Beklenen kural/skor sonucunu test edilen kural veya skor motorundan türetme;
  bağımsız oracle ve expected-versus-actual karşılaştırma kullan.
- Geçerli nadir/sınır değerleri kusurdan, teknik hatayı kalite başarısızlığından
  ayrı test et.
- Karar verilmemiş gizlilik, benzerlik, kusur yoğunluğu veya skor toleransı
  eşiklerini uydurma; `TBD`/açık karar durumunu koru.
- Sentetik olay testlerini gerçek kullanıcı, üretim ServiceNow veya üretim SIEM
  hedeflerine gönderme; yalnız doğrulanmış fake/sandbox adaptör kullan.
- Yeni sentetik veri davranışında `FR-088–FR-096`, `UC-017`, `RULE-016/017` ve
  `AC/TS-048–056` izlenebilirliğini güncelle.

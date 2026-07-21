# İterasyon 34 — Sentetik Veri Kayıt Çekirdeği

## 34A — Sentetik dataset politika, senaryo ve run kayıt çekirdeği

- **İterasyon adı:** Sentetik dataset politika, senaryo ve run kayıt çekirdeği
- **Kullanıcı/sistem değeri:** Yetkili kullanıcı, sürümlü ve geçerli bir dataset
  politikası altında yeniden üretilebilir sentetik üretim talebini değişmez lineage
  ve audit kaydıyla oluşturabilir.
- **Mevcut FR/UC/RULE:** `FR-088`, `FR-093`, `UC-017`, `RULE-016/017`,
  `AC/TS-049` ayrı run ve lineage alt kapsamı
- **BFR/CTRL:** Yeni eşleme yoktur.
- **Değiştirilen dosyalar:** Yeni `synthetic_data` domain paketi, merkezi audit
  allowlist'i, birim testleri ve proje hafızası.
- **Migration/config:** SQLite üzerinde append-only sentetik politika, senaryo ve
  run tabloları ile etkili politika ve dataset-run indeksleri eklendi. Bu yerel
  depo üretim veritabanı kararı değildir.
- **Eklenen testler:** Ayrı replay run'ları, eksik/süresi dolmuş/çakışan/izin
  vermeyen politika, senaryo sürüm uyuşmazlığı, yetkisiz ve ayrıcalıklı aktör,
  geçersiz lineage/hacim, atomik audit rollback'i, teknik depo hatası ve
  append-only sürüm çakışmaları.
- **Çalıştırılan komutlar:** Hedefli ve tam `pytest -q`, tam `mypy`, tam
  `ruff check`, değişen kapsam ve tam depo format kontrolleri, `compileall`,
  `git diff --check` ve güvenli SDLC preflight.
- **Mevcut regresyon sonucu:** 939 test geçti; mypy 137 dosyada ve Ruff lint
  hatasız tamamlandı. Tam depo format kontrolü değişiklik dışındaki bir tarihsel
  dosyada biçim farkı bildirdi. `28A-v1` taraması 389 dosyada secret bulgusu
  üretmedi.
- **Güvenlik/veri gizliliği sonucu:** Güvenilir kullanıcı bağlamı, rol ve dataset
  kapsamı yazımdan önce doğrulanır. Audit seed değerini, session bilgisini, ham
  kayıt, kişisel veri veya secret taşımaz. Bu artım gerçek veri veya üretim profili
  okumaz ve sentetik çıktı üretmez.
- **Kanıt yolları:** `06-Testler/01-Birim/test_synthetic_data.py`.
- **Teknik durum:** `TechnicallyVerified`
- **Banka onayı:** `ComplianceReviewRequired`
- **Kalan risk:** Politika/senaryo yönetim yaşam döngüsü, üretim deposu, üretici,
  deterministik çıktı eşdeğerliği/output digest, ground truth, bağımsız
  karşılaştırıcı ve gizlilik kapısı açık; nicel değerler `OPEN-024`, üretim
  profili erişimi `OPEN-025` kapsamındadır.
- **Geri alma yaklaşımı:** `SyntheticGenerationRegistryService` composition'dan
  çıkarılarak yeni run kabulü durdurulabilir; append-only politika, senaryo, run ve
  audit geçmişi silinmez veya değiştirilmez.
- **Sonraki iterasyon:** `SYN-002` kapsamında yalnız tamamen yapay profille
  deterministik Golden ilişkisel üretici.

## 34B — Deterministik Golden ilişkisel üretici

- **İterasyon adı:** Deterministik Golden ilişkisel üretici
- **Kullanıcı/sistem değeri:** Gerçek banka verisi veya üretim profili okunmadan,
  yapısal olarak geçerli ilişkisel test dataseti aynı seed ile tekrar üretilebilir.
- **Mevcut FR/UC/RULE:** `FR-089`, `FR-090` temel yapay ilişki alt kapsamı,
  `FR-093`, `UC-017`, `RULE-016/017`, `AC/TS-048/049`
- **BFR/CTRL:** Yeni eşleme yoktur.
- **Değiştirilen dosyalar:** `synthetic_data` model ve paket dışa aktarımları,
  yeni Golden üretici, birim testleri, test indeksi ve proje hafızası.
- **Migration/config:** Migration yoktur. Teknik sürümler
  `GOLDEN_RELATIONAL_GENERATOR_V1`, `GOLDEN_RELATIONAL_SCHEMA_V1` ve
  `GOLDEN_RELATIONAL_CONFIG_V1` olarak sabitlendi; üretim politika değeri değildir.
- **Eklenen testler:** Byte/SHA-256 replay eşdeğerliği, farklı run kimliği,
  farklı seed, anahtar/yabancı anahtar, segment-durum, referans, tutar ve zaman
  bütünlüğü, lineage içeriği ile Golden dışı profil/sürüm negatifleri.
- **Çalıştırılan komutlar:** Hedefli ve tam `pytest -q`, tam `mypy`, tam
  `ruff check`, değişen kapsam ve tam depo format kontrolleri, `compileall`,
  `git diff --check` ve güvenli SDLC preflight.
- **Mevcut regresyon sonucu:** 948 test geçti; mypy 139 dosyada ve Ruff lint
  hatasız tamamlandı. Tam depo format kontrolü değişiklik dışındaki bir tarihsel
  dosyada biçim farkı bildirdi. `28A-v1` taraması 391 dosyada secret bulgusu
  üretmedi.
- **Güvenlik/veri gizliliği sonucu:** Üretici dış veri, ağ, saat, gerçek profil,
  kullanıcı veya secret bağımlılığı almaz. Çıktı `synthetic_origin=true` taşır;
  yapay teknik kodlar banka/müşteri gerçeği veya anonimlik kanıtı değildir.
- **Kanıt yolları:** `06-Testler/01-Birim/test_synthetic_generator.py`.
- **Teknik durum:** `TechnicallyVerified`
- **Banka onayı:** `ComplianceReviewRequired`
- **Kalan risk:** Çıktı geçicidir; kalıcı artifact/run tamamlama, genel şema
  yükleyici, kusur enjeksiyonu, ground truth, bağımsız karşılaştırıcı ve gizlilik
  kapısı açık. Nicel değerler `OPEN-024`, üretim profili erişimi `OPEN-025`
  kapsamındadır.
- **Geri alma yaklaşımı:** `GoldenRelationalGenerator` composition'dan çıkarılarak
  yeni üretim durdurulabilir; append-only run ve audit geçmişi değiştirilmez.
- **Sonraki iterasyon:** `OPEN-024` nicel toleransını dışarıda bırakan değişmez
  Golden ground truth ve yapısal bağımsız karşılaştırıcı dilimi.

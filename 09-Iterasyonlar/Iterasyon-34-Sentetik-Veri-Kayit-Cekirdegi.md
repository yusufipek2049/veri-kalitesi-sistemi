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

## 34C — Değişmez Golden ground truth ve yapısal bağımsız karşılaştırıcı

- **İterasyon adı:** Değişmez Golden ground truth ve yapısal bağımsız karşılaştırıcı
- **Kullanıcı/sistem değeri:** Golden çıktının bilinen yapısal beklentisi,
  üreticinin kendi doğrulama sonucu veya runtime skor motoru kullanılmadan
  değişmez kanıtla karşılaştırılabilir.
- **Mevcut FR/UC/RULE:** `FR-092`, `UC-017`, `RULE-016`, `AC/TS-050–052`
  Golden sıfır kusur ve yapısal karşılaştırma alt kapsamı
- **BFR/CTRL:** Yeni eşleme yoktur.
- **Değiştirilen dosyalar:** `synthetic_data` model, repository, oracle ve paket
  dışa aktarımları; merkezi audit allowlist'i, birim testleri ve proje hafızası.
- **Migration/config:** SQLite prototipine append-only `synthetic_ground_truth` ve
  `synthetic_validation_results` tabloları eklendi. Teknik oracle sürümü
  `GOLDEN_STRUCTURAL_ORACLE_V1` olarak sabitlendi; üretim tolerans politikası değildir.
- **Eklenen testler:** Üretici doğrulamasından bağımsız başarılı karşılaştırma,
  yapısal ve lineage sapması, dataset scope manipülasyonu, eksik/yanlış rol ve
  kapsam, değişmez kayıt, atomik audit rollback'i ve teknik depo hatası.
- **Çalıştırılan komutlar:** Hedefli ve tam `pytest -q`, tam `mypy`, tam
  `ruff check`, değişen kapsam ve tam depo format kontrolleri, `compileall`,
  `git diff --check` ve yerel secret taraması.
- **Mevcut regresyon sonucu:** 958 test geçti; mypy 141 dosyada ve Ruff lint
  hatasız tamamlandı. Tam depo format kontrolü değişiklik dışındaki bir tarihsel
  dosyada biçim farkı bildirdi. `28A-v1` taraması 393 dosyada secret bulgusu
  üretmedi.
- **Güvenlik/veri gizliliği sonucu:** Güvenilir kullanıcı bağlamı hem sunulan
  çıktı hem kayıtlı run dataset kapsamı için doğrulanır. Ham kayıt ve seed audit
  edilmez; yalnız lineage, sayımlar, sonuç ve güvenli neden kodları kalıcılaşır.
- **Kanıt yolları:** `06-Testler/01-Birim/test_synthetic_oracle.py`.
- **Teknik durum:** `TechnicallyVerified`
- **Banka onayı:** `ComplianceReviewRequired`
- **Kalan risk:** Bu dilim yalnız sıfır kusurlu Golden yapısal beklentiyi kapsar.
  Kayıt düzeyi kusur ground truth'u, runtime kural/skor/önem/bildirim/eskalasyon
  karşılaştırması ve sayısal tolerans `OPEN-024` nedeniyle açıktır.
- **Geri alma yaklaşımı:** `GoldenStructuralOracle` composition'dan çıkarılarak
  yeni doğrulama kaydı durdurulabilir; append-only ground truth, sonuç ve audit
  geçmişi silinmez veya değiştirilmez.
- **Sonraki iterasyon:** Sayısal kusur yoğunluğu veya skor toleransı uydurmadan
  tamamlanabilecek kalıcı çıktı/run tamamlama diliminin hazır oluşunu değerlendir.

## 34D — Kalıcı çıktı referansı ve append-only run tamamlama

- **İterasyon adı:** Kalıcı çıktı referansı ve append-only run tamamlama
- **Kullanıcı/sistem değeri:** Doğrulanmış Golden çıktının kanonik özeti, çıktı
  ve doğrulama referansları ile terminal durumu özgün run talebi değiştirilmeden
  kalıcı ve denetlenebilir hale gelir.
- **Mevcut FR/UC/RULE:** `FR-093`, `UC-017`, `RULE-016`, `AC/TS-049` çıktı ve
  doğrulama referansı alt kapsamı
- **BFR/CTRL:** Yeni eşleme yoktur.
- **Değiştirilen dosyalar:** `synthetic_data` ortak yetkilendirme, kanonik codec,
  model, repository ve tamamlama servisi; merkezi audit allowlist'i, birim
  testleri ve proje hafızası.
- **Migration/config:** SQLite prototipine update/delete tetikleyicileriyle
  korunan append-only `synthetic_run_completions` tablosu eklendi. Bu tablo
  fiziksel çıktı/artifact deposu veya üretim veritabanı kararı değildir.
- **Eklenen testler:** Başarılı ve blokeli tamamlama, idempotent tekrar,
  payload/digest/referans manipülasyonu, eksik veya yanlış rol/kapsam, kayıtlı
  run kapsamı manipülasyonu, append-only koruma, atomik audit rollback'i ve
  teknik depo hatası için 12 vaka.
- **Çalıştırılan komutlar:** Hedefli ve tam `pytest -q`, tam `mypy`, tam
  `ruff check`, tam depo format kontrolü, `compileall`, `git diff --check` ve
  yerel secret taraması.
- **Mevcut regresyon sonucu:** 970 test geçti; mypy 144 dosyada ve Ruff lint
  hatasız tamamlandı. Tam depo format kontrolü değişiklik dışındaki tarihsel
  `03-Backend/src/veri_kalitesi/__init__.py` dosyasında biçim farkı bildirdi.
  `28A-v1` taraması 396 dosyada secret bulgusu üretmedi.
- **Güvenlik/veri gizliliği sonucu:** Yetki hem sunulan çıktı hem kayıtlı run
  dataset kapsamı için doğrulanır. Payload, seed, session ve digest değeri audit
  edilmez; yalnız veri-minimum durum, sayım ve opak referanslar yazılır. Ham
  sentetik kayıtlar completion tablosunda saklanmaz.
- **Kanıt yolları:** `06-Testler/01-Birim/test_synthetic_oracle.py`.
- **Teknik durum:** `TechnicallyVerified`
- **Banka onayı:** `ComplianceReviewRequired`
- **Kalan risk:** Fiziksel payload/artifact deposu, saklama süreleri, genel şema
  yükleyici, kayıt düzeyi kusur ground truth'u, sayısal tolerans, gerçek üretim
  profili ve gizlilik kapısı açık kalır.
- **Geri alma yaklaşımı:** `SyntheticRunFinalizationService` composition'dan
  çıkarılarak yeni tamamlama kaydı durdurulabilir; append-only run, completion
  ve audit geçmişi silinmez veya değiştirilmez.
- **Sonraki iterasyon:** Sayısal eşik uydurmadan olay, kaynak, ingestion,
  processing ve kalite kontrol zamanlarını deterministik üreten `SYN-004A`
  çok dönemli zaman semantiği.

## 34E — Deterministik çok dönemli zaman semantiği

- **İterasyon adı:** Deterministik çok dönemli zaman semantiği
- **Kullanıcı/sistem değeri:** Gerçek banka verisi veya üretim profili
  kullanılmadan olay, kaynak oluşturma/güncelleme, ingestion, processing ve
  kalite kontrol zamanları ayrı anlamlarla, UTC ve yeniden üretilebilir biçimde
  birden çok dönemde sınanabilir.
- **Mevcut FR/UC/RULE:** `FR-090`, `FR-094`, `UC-017`, `RULE-016`,
  `AC/TS-054` zaman semantiği alt kapsamı
- **BFR/CTRL:** Yeni eşleme yoktur.
- **Değiştirilen dosyalar:** `synthetic_data` temporal profil/çıktı modelleri,
  append-only repository tablosu, kanonik codec ve ayrı temporal generator/
  validator; birim testleri ve proje hafızası.
- **Migration/config:** SQLite prototipine append-only
  `synthetic_temporal_profiles` tablosu eklendi. Profilin dönem ve gecikme
  değerleri açık test girdileridir; üretim eşiği veya banka SLA değeri değildir.
- **Eklenen testler:** Altı zaman alanı ve UTC sırası, dönem kapsamı/ataması,
  bağımsız manipülasyon tespiti, byte eşdeğeri replay, seed duyarlılığı,
  veri-minimum lineage, append-only profil, geçersiz/eksik profil, kapsam dışı
  eksiklik/kusur/üretim profili redleri ve teknik depo hatası için 17 vaka.
- **Çalıştırılan komutlar:** Hedefli ve tam `pytest -q`, tam `mypy`, tam
  `ruff check`, tam depo format kontrolü, `compileall`, `git diff --check` ve
  yerel secret taraması.
- **Mevcut regresyon sonucu:** 987 test geçti; mypy 146 dosyada ve Ruff lint
  hatasız tamamlandı. Tam depo format kontrolü değişiklik dışındaki tarihsel
  `03-Backend/src/veri_kalitesi/__init__.py` dosyasında biçim farkı bildirdi.
  `28A-v1` taraması 398 dosyada secret bulgusu üretmedi.
- **Güvenlik/veri gizliliği sonucu:** Yalnız tamamen yapay profil kabul edilir;
  üretim verisi/profili okunmaz. Kanonik payload aktör, session, run kimliği veya
  secret taşımaz. Teknik depo arızası kalite sonucu olarak yorumlanmaz.
- **Kanıt yolları:** `06-Testler/01-Birim/test_synthetic_temporal.py`.
- **Teknik durum:** `TechnicallyVerified`
- **Banka onayı:** `ComplianceReviewRequired`
- **Kalan risk:** Eksiklik mekanizmaları, trend/sezonsallık/drift, geç/sırasız
  akış, hacim/kota ve üretim benzerliği bu dilimde uygulanmadı. Nicel değerler
  `OPEN-024`, gerçek profil erişimi `OPEN-025` kapsamındadır.
- **Geri alma yaklaşımı:** `DeterministicTemporalGenerator` composition'dan
  çıkarılarak yeni üretim durdurulabilir; append-only temporal profil, run ve
  audit geçmişi değiştirilmez.
- **Sonraki iterasyon:** Nicel oran uydurmadan kayıtlar arası geç ve sırasız
  ingestion davranışını deterministik kanıtlayan `SYN-004B` teknik zaman dilimi.

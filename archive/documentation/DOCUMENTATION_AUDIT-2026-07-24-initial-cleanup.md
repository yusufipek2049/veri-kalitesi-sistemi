# Dokümantasyon Denetimi

Denetim tarihi: **24 Temmuz 2026**  
Kapsam: aktif Markdown dokümantasyonu, indeksler, karar/gereksinim kayıtları,
Python/TypeScript uygulama yüzeyleri, migration ve test dosyaları.  
Arşivler güncel kaynak sayılmamış; yalnız tarihsel kanıtın korunduğu doğrulanmıştır.

## Özet ve Sayısal Sonuçlar

| Ölçüm | Önce | Sonra | Etki |
| --- | ---: | ---: | ---: |
| Aktif Markdown dosyası | 227 | 235 | Yeni kanonik indeks/kayıtlar eklendi; monolitler küçültüldü. |
| Aktif Markdown boyutu | 1.469.438 bayt | 1.130.546 bayt | 338.892 bayt azalma (%23,1). |
| Aktif Markdown satırı | 21.560 | 18.677 | 2.883 satır azalma (%13,4). |
| Kırık yerel dosya bağlantısı | 7 | 0 | Bozuk iterasyon/evidence yolları düzeltildi. |
| Birden fazla H1 içeren dosya | 1 | 0 | Karar indeksi tek H1 yapısına getirildi. |
| Muhtemel yinelenen kimlik-tanım adayı | 105 | 90 | 15 aday aktif grafikten kaldırıldı; kaba tarayıcıdaki kalanların çoğu indeks/izlenebilirlik referansıdır. |

Temizlik yalnız kısaltma yapmadı: güncel durum, karar, açık karar, backlog,
iterasyon geçmişi ve tarihsel snapshot birbirinden ayrıldı. Beş monolitik proje
hafızası dosyasının eski sürümü arşivlendi; aktif sürümleri görev odaklı kısa
kaynaklara dönüştürüldü. 107 KB'lık birleşik iterasyon karar günlüğü, kanonik
iterasyon/ADR kayıtlarına yönlendiren kısa indeksle değiştirildi.

## Değiştirilen, Yeni ve Taşınan Dosyalar

| Grup | Dosyalar | İşlem |
| --- | --- | --- |
| Kök yönlendirme | `README.md`, `AGENTS.md`, `DOCUMENTATION_INDEX.md`, `DOCUMENTATION_AUDIT.md`, `.gitignore` | Kanonik başlangıç, ajan kuralları, indeks, audit ve sade izleme politikası oluşturuldu/güncellendi. |
| Proje hafızası | `00-Proje-Hafizasi/Mevcut-Durum.md`, `Alinan-Kararlar.md`, `Acik-Konular.md`, `Sonraki-Adimlar.md`, `Bankacilik-Gecis-Durumu.md` | Monolitik günlükler kısa aktif kayıtlara dönüştürüldü. |
| Karar kayıtları | `00-Proje-Hafizasi/Karar-Kayitlari/*.md` | Karar aileleri ayrıldı; iterasyon geçmişi tam metin yerine yönlendirme indeksi oldu; eksik açık-karar kimlik kapsamları kanonikleştirildi. |
| SRS | `01-SRS/SRS-INDEX.md`, `01-SRS/15-Acik-Konular.md` | Açık karar kopyası kaldırıldı ve kanonik kayıt bağlantısı düzeltildi. |
| Mimari | `02-Mimari/Mimari-Kararlar.md` | ADR-012/013/017/020 uygulama durumları kod ve iterasyon kanıtıyla ayrıştırıldı. |
| Backend | `03-Backend/BACKEND-INDEX.md`, `03-Backend/01-Kimlik-ve-Yetki/AGENTS.md` | Domain/API/kalıcılık durumu ve modül ajan farkları güncellendi. |
| Frontend | `04-Frontend/FRONTEND-INDEX.md` | 35A–35F/36C–36E ekran ve mutasyon durumu güncellendi. |
| Veritabanı | `05-Veritabani/VERITABANI-INDEX.md` | Issue/rule/data-source/execution PostgreSQL durumu ve SQLite sınırı ayrıldı. |
| Test | `06-Testler/TEST-INDEX.md`, `06-Testler/AGENTS.md` | Tarihsel baseline etiketlendi; test ajan tekrarları kaldırıldı. |
| Uyum kanıtı | `08-Uyum-Kanitlari/KANIT-INDEX.md`, `Kanit-Paketi-Sablonu.md` | Kırık bağlantı düzeltildi; bozuk dosya adı yeniden adlandırıldı. |
| İterasyon | `09-Iterasyonlar/ITERASYON-INDEX.md`, `Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md` | Kırık yollar düzeltildi; 36 durumu ve kalan kapanışlar kanıtla uyumlu hale getirildi. |
| Tarihsel kaynak | `docs/archive/project-memory-2026-07-24/*.md`, `docs/technical/README.md` | Eski proje hafızası arşivlendi, taşınan bağlantılar düzeltildi; teknik snapshot uyarısı eklendi. |
| Otomatik kontrol | `scripts/check_documentation.py` | Aktif/tüm-depo link, H1 ve kanonik kimlik doğrulaması eklendi. |
| Üretilmiş artıklar | `__pycache__/`, `.pytest_cache/`, kısmi `node_modules/` | Paket dışında bırakıldı; kaynak kod davranışı değiştirilmedi. |

## Kritik Uyumsuzluklar

| ID | Seviye | Konu | Dosyalar | Bulgu | Önerilen çözüm | Durum |
| --- | --- | --- | --- | --- | --- | --- |
| DOC-HIGH-001 | HIGH | Çalıştırma PostgreSQL cutover | `executions/postgresql_repository.py`, `20260724_04_execution_baseline.py`, `api/development.py`, execution testleri, İterasyon 36 | Migration, PostgreSQL repository ve testler mevcut; API composition root `DevelopmentExecutionStore` kullanıyor. `SQLiteExecutionRepository` export ve test yollarında sürüyor. “PostgreSQL geçişi tamamlandı” veya “yalnız API var” ifadelerinin ikisi de tek başına doğru değil. | Production composition root'u, transaction/retry/kota/pencere davranışını ve SQLite sınırını kanıtla; ardından 36E kapanış kaydı oluştur. | **İnsan/uygulama kararı gerekli; otomatik değiştirilmedi.** |
| DOC-HIGH-002 | HIGH | Üretim hazırlığı iddiaları | Proje hafızası, teknik snapshot, operasyon belgeleri | Teknik doğrulama; kurumsal IdP, secret manager/PAM, HA PostgreSQL/session, SIEM/WORM, ServiceNow ve DR kanıtı olmadan üretim hazır gibi yorumlanabiliyordu. | Teknik doğrulama, production wiring ve banka onayını ayrı durumlar olarak tut. | **Çözüldü:** aktif durum tabloları ayrıştırıldı. |

Denetimde güvenlik/uyum hükmünü otomatik değiştirecek bir düzeltme yapılmadı.
Açık kurumsal kararlar `00-Proje-Hafizasi/Acik-Konular.md` içinde tutuldu ve
belirsiz alanlarda fail-closed sınır korundu.

## Diğer Uyumsuzluklar

| ID | Seviye | Konu | Dosyalar | Bulgu | Önerilen çözüm | Durum |
| --- | --- | --- | --- | --- | --- | --- |
| DOC-001 | LOW | Kırık bağlantılar | `ITERASYON-INDEX.md`, `KANIT-INDEX.md` | Altı `Iterasjon-*` yazım hatası ve bozuk evidence şablon adı vardı. | Gerçek dosya adına göre düzelt ve yeniden tara. | Çözüldü. |
| DOC-002 | LOW | Evidence dosya adı | `Kan#U0131t-Paketi-Sablonu.md` | Unicode kaçış metni dosya adına sızmıştı. | `Kanit-Paketi-Sablonu.md` olarak yeniden adlandır. | Çözüldü. |
| DOC-003 | MEDIUM | Test baseline çelişkisi | README, test/iterasyon indeksleri, teknik snapshot | 1029, 1070, 1125 gibi farklı sayılar aynı anda “güncel” görünüyordu. | Tek aktif baseline kaynağı kullan; eski sayıları yalnız tarihsel iterasyon kanıtı olarak bırak. | Çözüldü; son belgelenmiş değer 1125/27 ve frontend 95 olarak açıkça “tarihsel” etiketlendi. |
| DOC-004 | MEDIUM | İterasyon 36 durumu | İterasyon 36 master/index, kod ve testler | Master `planned`, alt teknik dilimler ve kod ise büyük ölçüde uygulanmıştı. 36B5 işlevi kod/testte var, ayrı kapanış belgesi yok. | Master'ı `in_progress` yap; işlev, kapanış kanıtı ve production cutover'ı ayrı göster. | Kısmen çözüldü; doküman düzeltildi, 36B5 kapanış kaydı açık. |
| DOC-005 | MEDIUM | Frontend ADR durumu | ADR-012/013/017, frontend indeksi | ADR özetleri frontend uygulamasını “bekliyor” gösterirken React/MUI/Storybook/Playwright ve alan ekranları mevcuttu. | Karar, teknik uygulama ve üretim onayını ayrı belirt. | Çözüldü. |
| DOC-006 | MEDIUM | Tarihsel teknik raporun aktif görünmesi | `docs/technical/` ve README | 22 Temmuz snapshot'ı güncel endpoint/test/durum kaynağı gibi linkleniyordu. | Snapshot uyarısı ekle; aktif indeksleri kanonik yap. | Çözüldü. |
| DOC-007 | LOW | Agent talimatları | root ve alt `AGENTS.md`, `.gitignore` | Root ajan dosyası yoktu; alt talimatlarda üst kurallar tekrar ediyordu. `.gitignore` hem dahil hem hariç kurallar içeriyordu. | Root kanonik AGENTS oluştur; alt dosyalarda yalnız modül farkı bırak; ignore politikasını sadeleştir. | Çözüldü. |
| DOC-008 | LOW | Açık karar kopyaları | SRS açık konular ve proje hafızası | Aynı açık kararların birden fazla listede güncel tutulması gerekiyordu. | Tek açık karar kaynağına yönlendir. | Çözüldü. |
| DOC-009 | LOW | Kanonik kaynak belirsizliği | Tüm depo | README, proje hafızası, karar günlüğü ve iterasyon dosyaları aynı bilgiyi farklı ayrıntıyla tekrar ediyordu. | `DOCUMENTATION_INDEX.md` ile kaynak/amaç/sorumluluk/güncellik kaydı oluştur. | Çözüldü. |

## Kaldırılan Tekrarlar

- Beş proje hafızası belgesinin eski tam metinleri aktif grafikten çıkarılıp
  `docs/archive/project-memory-2026-07-24/` altına taşındı.
- `Alinan-Kararlar.md` tam günlük olmaktan çıkarılıp karar ailesi indeksine
  dönüştürüldü; karar metinleri hedefli kayıtlara ayrıldı.
- `Iterasyon-Teknik-Karar-Gecmisi.md` içindeki iterasyon dosyalarını tekrar eden
  107 KB tam metin kaldırıldı ve çapraz referansa dönüştürüldü.
- SRS'deki açık konular kopyası kaldırıldı; kanonik açık karar listesine bağlandı.
- README ve indekslerdeki test sayısı/teknoloji/durum tekrarları kısa kaynak
  referanslarıyla değiştirildi.
- Otomatik tarayıcıdaki muhtemel yinelenen kimlik-tanım adayı sayısı 105'ten
  90'a düştü. Kalan adayların önemli bölümü gerçek çift tanım değil, ADR özet
  tablosu + ayrıntılı başlık veya izlenebilirlik matrisi referansıdır.

Aktif belgelerde iki iterasyon kapanışında aynı tarihsel test notu bir kez
tekrarlanır. Bu metin teslimat kanıtının bağlamı olduğu için otomatik silinmedi.

## Taşınan ve Kanonikleştirilen İçerikler

| İçerik | Yeni konum/işlem |
| --- | --- |
| Temizlik öncesi proje hafızası | `docs/archive/project-memory-2026-07-24/` |
| Temel/mimari kararlar | `00-Proje-Hafizasi/Karar-Kayitlari/Temel-ve-Mimari-Kararlar.md` |
| Bankacılık teknik kararları | `00-Proje-Hafizasi/Karar-Kayitlari/Bankacilik-Kararlari.md` |
| API/frontend/PostgreSQL kararları | `00-Proje-Hafizasi/Karar-Kayitlari/API-Frontend-ve-PostgreSQL-Kararlari.md` |
| Skorlama/sentetik/ikinci faz kararları | `00-Proje-Hafizasi/Karar-Kayitlari/Skorlama-Sentetik-Veri-ve-Ikinci-Faz-Kararlari.md` |
| İterasyon teknik geçmişi | İlgili `09-Iterasyonlar/` dosyaları; birleşik kayıt yalnız indeks |
| Açık kararlar | `00-Proje-Hafizasi/Acik-Konular.md` |
| Doküman ilişkileri | `DOCUMENTATION_INDEX.md` |
| Ajan davranışları | root `AGENTS.md`; alt dosyalarda yalnız modül farkları |

## İnsan Kararı Gereken Konular

1. **Execution production wiring:** PostgreSQL repository/migration'ın hangi
   composition root ve deployment profilinde kullanılacağı; SQLite export/test
   yolunun kaldırılacağı veya yalnız test double olarak sınırlandırılacağı.
2. **36B5 kapanışı:** kod/testteki kapatma ve yeniden açma davranışının ayrı
   iterasyon kapanış/kanıt kaydına bağlanması.
3. **Kurumsal açık kararlar:** IdP grup-rol-scope, BDDK/KVKK teyidi, saklama ve
   fiziksel imha, ServiceNow veri işleyen etkisi, RPO/RTO, BCBS 239 kapsamı ve
   giriş/rate-limit politikasının yetkili sahiplerce onaylanması.
4. **Production readiness:** gerçek IdP/PAM/secret manager, HA veri/session,
   SIEM/WORM, broker/publisher, DR ve kurumsal entegrasyon kanıtları olmadan
   “production ready” durumu verilmemesi.

## Silinmeyen Şüpheli İçerikler

- Tarihsel iterasyon dosyalarındaki eski test sayıları, ilgili teslimatın kanıtı
  oldukları için korundu; aktif baseline olarak yorumlanmamaları sağlandı.
- `docs/technical/` içeriği güncel değil ancak tarihsel analiz değeri taşıdığı
  için silinmedi; snapshot uyarısıyla arşiv niteliği açıklandı.
- Bağlayıcı karar ve gereksinim kimlikleri, kabul kriterleri, güvenlik/uyum
  hükümleri ve eski seçeneklerin karar geçmişi arşivde korundu.
- Execution kod-doküman farkında kod veya doküman otomatik “doğru” seçilmedi;
  bulgu açık iş olarak bırakıldı.

## Doğrulama Sonuçları

| Kontrol | Sonuç |
| --- | --- |
| Markdown yerel dosya bağlantıları | Aktif grafikte 466; arşiv/snapshot dahil tüm depoda 538 bağlantı kontrol edildi, 0 kırık. |
| H1 yapısı | Her aktif Markdown dosyasında tam bir H1 doğrulandı. |
| Kimlik bütünlüğü | 533 kanonik kimlik tanımı tekil bulundu; 533 açık kimlik referansı çözüldü, tanımsız veya çift kanonik tanım bulunmadı. |
| Kırık/eski dosya adı | `Iterasjon` ve bozuk evidence adı aktif grafikte kalmadı. |
| Kanonik karar/açık karar ayrımı | Karar indeksi ile açık karar kaydı ayrıldı. |
| İçerik küçültme | Aktif satır ve byte ölçümü yukarıdaki tabloda gösterildi. |
| Python sözdizimi | `python -m compileall -q 03-Backend/src scripts 06-Testler` başarılıdır. |
| Backend pytest/mypy | Bağımlılık eksikliği ve paket kaynağı HTTP 503 nedeniyle bağımsız tam koşu tamamlanamadı. Tarihsel baseline güncel sonuç gibi sunulmadı. |
| Frontend test/build | Bağımlılık kurulumu bu ortamda tamamlanmadı; `npm test` `vitest: not found` ile durdu. Son belgelenmiş 95 Vitest/type-check/build sonucu tarihsel olarak işaretlendi. |
| Güvenlik/uyum hükümleri | Değişmez sınırlar root AGENTS, README, karar ve indekslerde korunmuştur. |
| Arşiv kullanımı | Arşivler aktif kaynak listesinden çıkarılmış ve tarihsel olarak etiketlenmiştir. |

Dokümantasyon kontrolü için dış bağımlılıksız
`scripts/check_documentation.py` eklendi. Aktif Markdown bağlantılarını, tek H1 kuralını, kanonik kimlikleri ve zorunlu çekirdek belgeleri denetler; `--include-archives` ile arşiv/snapshot bağlantılarını da tarar.

## Dokümantasyon Bütünlüğüne Etkisi

Aktif bağlam daha küçük, karar statüleri daha açık ve görev bazlı erişim daha
kolaydır. Yeni yapı; bağlayıcı gereksinimi, mimari kararı, açık kararı, uygulama
durumunu ve tarihsel kanıtı birbirine karıştırmadan izlemeyi sağlar. Temizlik
proje kapsamını, güvenlik sınırlarını veya kaynak sistemlere salt okunur erişim
kuralını değiştirmemiştir.

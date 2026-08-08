\
# Veri Kalitesi Sisteminin Kapsamlı Fonksiyonel Eksiklik Analizi

Sen; kurumsal veri kalitesi platformları, veri yönetişimi, bankacılık veri
mimarisi, metadata yönetimi, veri profilleme, kural motorları, iş akışı
tasarımı, PostgreSQL veri modelleme, backend mimarisi, frontend ürün analizi ve
operasyonel dayanıklılık konularında uzman bir principal software architect ve
product analyst olarak çalışacaksın.

İncelenecek repository:

`https://github.com/yusufipek2049/veri-kalitesi-sistemi`

Repository'nin güncel ana branch'ini esas al.

Bu repository, birbiri ardına yürütülmüş geliştirme iterasyonlarının sonucudur.
Ancak analizi yalnızca repository'nin mevcut vaatleri, SRS kapsamı, backlog'u
veya iterasyon planlarıyla sınırlandırma.

Temel soru:

> Kurumsal ve bankacılık ortamında gerçekten kullanılabilir, uçtan uca çalışan
> bir veri kalitesi yönetim sistemi hangi fonksiyonlara, süreçlere, rollere,
> ekranlara, servislere, API'lere, veri yapılarına, tablolara ve kolonlara
> ihtiyaç duyar; mevcut repository bunların hangilerini gerçekten sağlıyor,
> hangilerini kısmen sağlıyor ve hangilerinden yoksundur?

## 1. Ana görev

Repository'yi baştan sona inceleyerek kapsamlı bir fonksiyonel eksiklik analizi
üret.

Önce repository'den bağımsız olarak ideal bir kurumsal veri kalitesi sisteminin
hedef modelini oluştur. Daha sonra mevcut sistemi bu hedef modele karşı
karşılaştır.

Aşağıdakileri ayrı ayrı belirle:

1. Vaat edilmiş ve uygulanmış fonksiyonlar.
2. Vaat edilmiş fakat eksik veya hatalı uygulanmış fonksiyonlar.
3. Dokümante edilmiş fakat kod karşılığı olmayan fonksiyonlar.
4. Kodda bulunan fakat kullanıcı tarafından uçtan uca kullanılamayan fonksiyonlar.
5. Backend'i bulunup frontend'i bulunmayan fonksiyonlar.
6. Frontend'i bulunup gerçek backend veya kalıcılık desteği bulunmayan fonksiyonlar.
7. Yalnızca mock, stub, fake repository veya test double üzerinden çalışan fonksiyonlar.
8. API'si bulunup gerçek iş akışına bağlanmamış fonksiyonlar.
9. Veri modeli bulunup servis veya kullanıcı akışı bulunmayan fonksiyonlar.
10. Hiç vaat edilmemiş olsa bile tam bir veri kalitesi sistemi için gerekli eksik fonksiyonlar.
11. Tasarım olarak var görünen fakat gerçek kullanıcı ihtiyacını karşılamayan yüzeysel fonksiyonlar.
12. Mükerrer, çelişkili veya parçalanmış modeller.
13. İşlevsel gereksinim gibi görünen fakat yalnızca teknik altyapı olan parçalar.
14. Teknik olarak uygulanmış görünen fakat operasyonel olarak kullanılamayan parçalar.

Bu aşamada repository'de kaynak kod, migration veya konfigürasyon değişikliği
yapma. Önce analiz ve hedef tasarım üret.

## 2. İnceleme kaynakları

En az aşağıdaki alanları incele:

- `README.md`
- `AGENTS.md`
- `DOCUMENTATION_INDEX.md`
- `NEXT_STEP.md`
- `docs/memory/`
- `docs/srs/`
- `docs/architecture/`
- aktif ve ilgili arşiv iterasyon kayıtları
- backend kaynak kodu
- frontend kaynak kodu
- migration dosyaları
- ORM/repository modelleri
- API route ve request/response modelleri
- servis ve domain katmanı
- worker, scheduler ve job kodları
- entegrasyon adaptörleri
- testler
- fixture ve sentetik veriler
- Docker/deployment tanımları
- örnek konfigürasyonlar
- seed/bootstrap işlemleri
- frontend route, page, dialog, form ve tablo bileşenleri

Dokümantasyonu tek başına gerçeklik kabul etme.

Bir fonksiyonu uygulanmış saymadan önce mümkün olduğu ölçüde şu zinciri doğrula:

`gereksinim → domain modeli → veri tabanı → servis → API → frontend → yetki → audit → test`

## 3. Durum sınıfları

Her bulgu için aşağıdaki sınıflardan birini kullan:

- `IMPLEMENTED`
- `PARTIAL`
- `DOC_ONLY`
- `MODEL_ONLY`
- `BACKEND_ONLY`
- `FRONTEND_ONLY`
- `API_ONLY`
- `MOCK_ONLY`
- `STUB`
- `BROKEN`
- `MISSING`
- `EXTERNAL_DEPENDENCY`
- `NOT_APPLICABLE`

Ayrıca `yüksek`, `orta` veya `düşük` kanıt güveni belirt.

## 4. Hedef kabiliyet hiyerarşisi

Hiyerarşi şu biçimde olsun:

- **L0:** Veri Kalitesi Yönetim Sistemi
- **L1:** Ana domain
- **L2:** Kabiliyet
- **L3:** Fonksiyon veya iş akışı
- **L4:** Atomik kullanıcı/sistem işlemi
- Gerekirse **L5:** İş kuralı, validasyon veya durum geçişi

Her fonksiyon için tanımla:

- fonksiyon kodu ve adı
- amacı ve iş değeri
- aktör
- tetikleyici
- ön koşullar
- girdiler
- temel, alternatif ve hata akışları
- çıktılar
- durumlar ve geçişler
- validasyonlar
- yetkiler ve maker-checker
- audit olayları
- bildirimler
- entegrasyonlar
- API ve frontend ihtiyacı
- ilişkili servisler
- tablolar ve kolonlar
- test senaryoları
- bağımlılıklar

## 5. Asgari fonksiyon alanları

Aşağıdakileri asgari kapsam kabul et:

1. Organizasyon ve veri yönetişimi
2. Kullanıcı, rol, permission ve scope yönetimi
3. Veri kaynağı onboarding ve yaşam döngüsü
4. Secret referansı ve bağlantı politikaları
5. Metadata keşfi ve veri kataloğu
6. Dataset ve kolon yönetimi
7. Veri profilleme
8. Veri kalitesi boyutları
9. Kural şablonları ve kural yaşam döngüsü
10. Kural testi, onay, aktivasyon ve sürümleme
11. Çalıştırma, zamanlama ve orkestrasyon
12. Kalıcı iş kuyruğu, lease, heartbeat ve worker recovery
13. Retry, timeout, cancellation ve dead-letter
14. Sonuç, kanıt ve başarısız kayıt örnekleri
15. Skorlama ve ölçüm yeterliliği
16. Kritiklik ve risk
17. Dashboard ve analitik
18. Sorun/vaka yaşam döngüsü
19. SLA, eskalasyon ve yeniden açma
20. İstisna, waiver ve override
21. Teşhis, recommendation ve remediation
22. Lineage ve etki analizi
23. Data contract ve kalite taahhütleri
24. Bildirim ve entegrasyon
25. Raporlama ve güvenli indirme
26. Audit, outbox, SIEM/WORM ve retention
27. Sentetik veri ve ground truth
28. Operasyon ekranları ve incident yönetimi
29. Sistem konfigürasyonu ve politika yönetimi

## 6. Uçtan uca akışlar

En az şu akışları denetle:

### A. Yeni kaynak onboarding
Kaynak oluşturma → secret referansı → bağlantı testi → onay → metadata keşfi →
dataset/kolon oluşumu → sahiplik/sınıflandırma → ilk profil → baseline → sonuç.

### B. Kural yaşam döngüsü
Dataset/kolon seçimi → kural oluşturma → validasyon → test → örnek hata →
sürüm → onay → aktivasyon → zamanlama → çalıştırma → sonuç → skor.

### C. Kalite problemi
Kural başarısızlığı → sonuç → skor → bildirim → duplicate önlemeli issue →
atama → SLA → inceleme → kök neden → çözüm → farklı aktörle doğrulama →
kapatma → tekrarında yeniden açma.

### D. Teknik hata
Bağlantı/timeout → kalite hatasından ayrım → retry → kota → worker recovery →
dead-letter → operatör inceleme → replay → audit/bildirim.

### E. Schema drift
Metadata yenileme → fark → sınıflandırma → etkilenen kurallar/raporlar →
gerekirse blokaj → bildirim → kabul/düzeltme/exception.

### F. Skor güvenilirliği
Kısmi/örneklemeli çalışma → coverage → teknik sağlık → measurement qualification
→ ham skor → kritiklik/risk → açıklanabilirlik.

### G. İstisna ve override
Talep → gerekçe ve bitiş → maker-checker → ham sonucu değiştirmeme → görünür
etki → otomatik sona erme → audit.

### H. Raporlama
Rapor seçimi → filtre → yetki → asenkron üretim → maskeleme → format →
durum → güvenli indirme → audit → dosya imhası → metadata saklama.

Her adım için ekran, API, servis, tablo, durum geçişi, aktör, audit ve test
kanıtı ver; akışın ilk kırıldığı noktayı açıkla.

## 7. İzlenebilirlik matrisi

Her ana fonksiyon için:

| Fonksiyon | Aktör | UI | UI işlemi | API | Servis | Domain | Tablo | Ana kolonlar | Audit | Test | Durum |
|---|---|---|---|---|---|---|---|---|---|---|---|

Şu kopuklukları özellikle işaretle:

- ekran var, API yok
- API var, servis yok
- servis var, repository yok
- repository var, migration yok
- migration var, production composition root bağlantısı yok
- domain varlığı var, kullanılmıyor
- audit olayı var, outbox/transaction bağlantısı yok
- test var, production adapter test edilmiyor
- durum geçişi var, yetki kontrolü yok
- backend var, kullanıcı akışı yok
- sonuç var, skor/dashboard/issue bağlantısı yok

## 8. Hedef PostgreSQL veri modeli

Önce kanonik hedef veri modelini oluştur, sonra mevcut şemayla karşılaştır.

Domain grupları:

1. Kimlik ve organizasyon
2. Rol ve yetki
3. Veri kaynağı ve bağlantı politikası
4. Metadata, dataset ve kolon
5. Profil ve profil metrikleri
6. Kural, sürüm, parametre ve bağımlılık
7. Onay ve maker-checker
8. Zamanlama, job queue ve worker
9. Execution, partition ve checkpoint
10. Sonuç ve kanıt
11. Skor, qualification, kritiklik ve risk
12. Issue, SLA, eskalasyon ve yorum
13. İstisna ve override
14. Bildirim ve entegrasyon
15. Raporlama
16. Audit, outbox, retention ve imha
17. Lineage ve impact
18. Diagnosis, recommendation ve remediation
19. Data contract ve kalite borcu
20. Sentetik veri
21. Sistem konfigürasyonu
22. Operasyonel health ve incident

Her hedef tablo için:

- tablo adı ve amacı
- primary key
- bütün kolonlar
- PostgreSQL veri tipleri
- nullable/default
- foreign key
- unique/check constraint
- enum/lookup
- hassasiyet sınıfı
- audit ve retention
- partition ve index
- optimistic locking
- soft delete/immutable davranışı
- created/updated actor ve timestamps
- yazan/okuyan fonksiyonlar

Mevcut şema karşılaştırması:

| Mevcut tablo | Hedef karşılığı | Durum | Eksik kolonlar | Şüpheli kolonlar | Eksik constraint | Eksik index | Fonksiyonel etki |
|---|---|---|---|---|---|---|---|

## 9. UI bilgi mimarisi

Hedef navigasyon en az:

- Genel Bakış
- Veri Kaynakları
- Veri Kataloğu
- Datasetler
- Profil Sonuçları
- Kurallar
- Çalıştırmalar
- Skorlar
- Sorunlar
- Remediation
- Lineage ve Etki
- Data Contracts
- Bildirimler
- Raporlar
- Audit
- Operasyon
- Yönetim

Her ekran için:

- route
- roller
- kartlar
- filtreler
- tablo kolonları
- form alanları
- butonlar ve durum bazlı eylemler
- loading/empty/error/permission durumları
- optimistic concurrency
- hassas veri maskesi
- API ve tablo bağımlılıkları

## 10. API denetimi

Mevcut endpoint'ler için:

- method/path
- actor/permission/scope
- request/response
- hata kodları
- idempotency
- concurrency
- pagination/filter/sort
- audit ve transaction
- repository
- frontend kullanımı
- test durumu

Eksik command endpoint'lerini açıkça öner:

- submit-for-approval
- approve/reject
- activate/passivate
- start-review
- resolve/verify/reopen
- cancel/replay
- exception request/approve/expire

## 11. Durum makineleri

Şunlar için mevcut ve hedef state machine çıkar:

- DataSource
- Dataset
- QualityRule
- RuleVersion
- ApprovalRequest
- Schedule
- Job
- RuleExecution
- ReportJob
- DataQualityIssue
- Exception
- Override
- RemediationAction
- DataContract
- NotificationDelivery
- IntegrationRecord

| Başlangıç | Komut | Hedef | Aktör | Ön koşul | Audit | Yan etki |
|---|---|---|---|---|---|---|

## 12. Rol ve yetki matrisi

En az:

- Platform Admin
- Security Admin
- Data Governance Admin
- Data Owner
- Data Steward
- Technical Data Steward
- Rule Author
- Rule Approver
- Issue Assignee
- Issue Verifier
- Report Consumer
- Auditor
- Operations User
- Integration Service Account
- Read-only Viewer

Maker-checker, domain/dataset scope, pasif kullanıcı, service account,
hassas kanıt ve audit erişimini özellikle kontrol et.

## 13. GAP kayıt formatı

Her eksiklik için:

### GAP-XXX — Eksiklik adı

- Domain
- Hedef fonksiyon
- Mevcut durum
- Durum sınıfı
- Repository kanıtı
- Beklenen davranış
- Eksik aşamalar
- Eksik ekran/API/servis/tablo/kolon
- Eksik state transition
- Eksik yetki ve audit
- Eksik test
- Kullanıcı, iş, veri bütünlüğü, uyum ve operasyon etkisi
- Bağımlılıklar
- Önerilen çözüm
- Kabul kriterleri
- Öncelik
- Karmaşıklık
- Kanıt güveni

## 14. Önceliklendirme

Puanla:

- temel akışı bloke etme: 0–5
- veri bütünlüğü riski: 0–5
- uyum etkisi: 0–5
- kullanıcı etkisi: 0–5
- operasyonel risk: 0–5
- bağımlılık merkeziyeti: 0–5
- uygulama karmaşıklığı: 1–5
- mevcut mimariyle uyum: 1–5

Sınıflar:

- `P0`: çekirdek doğruluğu veya sürekliliği bloke ediyor
- `P1`: kurumsal kullanım için zorunlu
- `P2`: operasyonel bütünlük ve ölçek
- `P3`: gelişmiş ürün kabiliyeti
- `P4`: iyileştirme/optimizasyon

## 15. Uygulama yol haritası

İterasyonları teknik katmanlara göre değil, uçtan uca dikey dilimler halinde
tasarla.

Her iterasyon:

- kod
- amaç
- kullanıcı değeri
- aktör
- kapsam
- fonksiyonlar
- tablolar/kolonlar/migration
- domain servisleri
- endpoint'ler
- frontend
- yetki
- audit
- test
- bağımlılık
- kapsam dışı
- kabul kriterleri
- çıkış kapısı

## 16. Test analizi

Her kritik fonksiyon için:

- domain unit
- state-machine
- repository
- migration
- gerçek PostgreSQL integration
- API contract
- authorization/scope
- audit/outbox atomicity
- concurrency/idempotency
- retry/worker recovery
- frontend component/integration
- Playwright E2E
- failure-path
- retention/destruction
- performance/volume

## 17. Nihai çıktı dosyaları

Çıktıları şu yapıda üret:

```text
docs/functional-audit/
├── 00-Executive-Summary.md
├── 01-Current-Capabilities.md
├── 02-Target-Capability-Hierarchy.md
├── 03-End-to-End-Workflow-Audit.md
├── 04-Functional-Gap-Inventory.md
├── 05-UI-Information-Architecture.md
├── 06-API-Inventory-and-Gaps.md
├── 07-Target-Data-Model.md
├── 08-Existing-Schema-Gap-Analysis.md
├── 09-State-Machines.md
├── 10-Roles-and-Permissions.md
├── 11-Test-Coverage-Gaps.md
├── 12-Prioritized-Backlog.md
├── 13-Implementation-Roadmap.md
└── 14-Independent-Code-Verification.md
```

## 18. Kalite kuralları

- Genel ve yüzeysel tavsiye verme.
- SRS'yi ideal sistem modeli kabul etme.
- Dokümanda “tamamlandı” yazdığı için uygulandı sayma.
- Test sayısını işlevsel tamlık göstergesi sayma.
- Production readiness ile fonksiyonel yeterliliği karıştırma.
- Varsayımı açıkça işaretle.
- Kanıt bulamazsan “kanıt bulunamadı” yaz.
- Aynı gap'i farklı isimlerle tekrar etme.
- Her gap'i hedef fonksiyona bağla.
- Her tabloyu iş ihtiyacına bağla.
- Her endpoint'i akışa bağla.
- Her ekranı aktöre ve göreve bağla.
- İlk aşamada çözüm kodu yazma.

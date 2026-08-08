---
type: functional-audit-work
stage: "14 — Dördüncü Dilim Kararı"
scope: fourth-slice-decision
inputs:
  - 13-Slice-DS03-Change-Inventory.md
  - 12-Third-Slice-Decision.md
  - 07-Implementation-Waves.md
  - 06-Vertical-Slice-Candidates.md
  - ../04-Functional-Gap-Inventory.md
  - ../13-Implementation-Roadmap.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-05
---

# 14 — Dördüncü Dilim Kararı

> Bu belge ilk üç dilimden sonra uygulanacak **tek** dördüncü dilimi seçer.
> Teknik değişiklik envanteri veya uygulama değildir; seçim gerekçesini, kapsam
> sınırını ve ölçülebilir kabul kriterlerini dondurur.

---

## 1. Karar

**Dördüncü uygulanacak tek dilim: DS-04 — Katalog ve metadata keşfi
(GAP-004).**

Tek ürün sonucu şudur:

> Yetkili kullanıcı aktif bir veri kaynağında metadata keşfi başlatır; kalıcı
> worker gerçek connector üzerinden dataset ve alanları keşfeder; güvenli biçimde
> uzlaştırılan katalog kayıtları aynı kullanıcı kapsamıyla API ve arayüzde görünür
> ve kural oluşturma formunda elle kimlik yazmak yerine seçilebilir.

Uygulama sırası:

```text
DS-01 komut güvenliği
  → DS-02 kalıcı production composition
    → DS-03 çalıştırma uçtan uca
      → DS-04 katalog ve metadata keşfi
```

Bu sıra `13-Implementation-Roadmap.md` içindeki zorunlu ikinci dalgayı tamamlar:
DS-03 çalıştırmayı üretir; DS-04 çalıştırılan kuralın bağlandığı gerçek dataset ve
alan kataloğunu kullanıcıya açar.

## 2. Seçim gerekçesi

### 2.1 Zorunlu ölçüm dalgasını tamamlar

Roadmap'in “Dalga 2 — Ölçüm” çıkış kapısı DS-03 ve DS-04 birlikte tamamlanmadan
kapanmaz. DS-03 tek başına execution/job zincirini çalıştırır; ancak kullanıcı
gerçek dataset ve alanları göremediği için kural hedeflerini elle kimlikle girer.
DS-04 ölçümün katalog halkasını tamamlar.

### 2.2 Mevcut backend çekirdeği yeniden kullanılabilir

Repository'de aşağıdaki parçalar zaten vardır:

- `data_sources/service.py:DataSourceService.discover_metadata`: kaynak durumu,
  secret çözümü, connector çağrısı, teknik hata sınıflandırması, kimlik koruma ve
  fark hesabı.
- `data_sources/service.py:_diff_metadata`: eklenen, değişen ve kaldırılan dataset/
  alan farkları.
- `data_sources/postgresql_repository.py:replace_metadata`: katalog kayıtları ile
  transactional audit outbox'ını aynı transaction'da yazma deseni.
- `data_sources/postgresql_repository.py:list_datasets` ve `list_data_fields`:
  kalıcı katalog okuması.
- `20260724_03_data_source_baseline.py`: `datasets`, `data_fields` ve
  `metadata_discovery_results` tabloları.
- `test_data_sources.py` içinde keşif, hata sınıflandırma, kimlik koruma ve audit
  rollback testleri.

Bu nedenle yeni connector ailesi, ikinci data-source repository veya in-memory
production katalog yazılmaz. Eksik olan HTTP/composition/UI zinciri ile güvenli
`PARTIAL` uzlaştırmadır.

### 2.3 Mevcut tehlikeli replace davranışını kapatır

`PostgreSQLDataSourceRepository.replace_metadata` bugün kaynak altındaki bütün
alanları ve dataset'leri silip yeniden ekler. Servis aynı adlara ait kimlikleri
yeniden kullanmaya çalışsa da tam sil-yaz işlemi:

- kısmi keşifte görünmeyen nesneleri yanlışlıkla kaldırabilir;
- bağlı kural ve kanıt referanslarını gereksiz riske atar;
- `PARTIAL` keşif semantiğini temsil edemez.

DS-04 bu yolu stable-ID kullanan fark uzlaştırmasına çevirir. Kısmi sonuç hiçbir
zaman “kaynakta yok” kanıtı sayılmaz.

### 2.4 Sonraki dilimleri açan merkezi bağımlılıktır

DS-04 tamamlandığında aşağıdaki dilimler gerçek katalog nesnelerine bağlanabilir:

- DS-08 profil ve baseline;
- DS-13 şema değişikliği kararı;
- DS-14 lineage ve etki analizi;
- DS-17 kural şablonları/bağımlılıkları;
- DS-21 sahiplik, sözlük ve yönetişim.

DS-05 otomatik sorun üretimi DS-03 sonrasında teknik olarak başlayabilir; ancak
roadmap'teki zorunlu ikinci dalgayı kapatmaz ve katalogdaki elle kimlik girişini
çözmez. Bu nedenle dördüncü **tek** dilim DS-04, DS-05 ise sonraki değer zinciri
dalgasının ilk adımıdır.

### 2.5 Kullanıcı tarafından doğrudan gözlenebilir

Dilim yalnız migration veya background job teslimatı değildir. Kullanıcı kaynak
üzerinden keşfi başlatır, durumunu izler, bulunan dataset/alanları katalogda görür
ve kural formunda bunları seçer. Aynı akış permission, scope, audit ve gerçek
PostgreSQL kalıcılığıyla doğrulanabilir.

## 3. Kapsam

### 3.1 Dahil

1. **Kalıcı metadata keşif komutu**
   - Yalnız `ACTIVE` ve kullanıcının kaynak kapsamında bulunan data source için
     keşif başlatma.
   - İstek, keşif kaydı, persistent job ve başlangıç audit olayının transaction
     sınırı belirlenmiş tek komut zinciriyle oluşturulması.
   - DS-03 worker runtime'ında gerçek metadata discovery handler'ı; API prosesine
     gömülü thread veya request-içi uzun connector çağrısı yok.

2. **Keşif kapsamı**
   - Include/exclude namespace ve nesne örüntülerinin sürümlü, kalıcı tanımı.
   - Kapsam güncellemesinde trusted `ActorContext`, rol, source scope ve optimistic
     version kontrolü.
   - Scope'un connector'a yalnız doğrulanmış seçenekler olarak aktarılması.

3. **Keşif durum makinesi**
   - `QUEUED → RUNNING → SUCCESS | PARTIAL | TECHNICAL_ERROR | CANCELLED`.
   - DNS, network, timeout, authentication, TLS, permission ve driver hatalarının
     kalite başarısızlığından ayrı teknik sonuç olarak saklanması.
   - `PARTIAL` sonucunun açık nedeni, taranan nesne sayısı ve tamamlanan kapsamı
     taşıması.

4. **Güvenli snapshot ve fark uzlaştırma**
   - Dataset/alan stable ID'lerinin korunması; toplu sil-yeniden-ekle yerine
     ekle/güncelle/pasifleştir uzlaştırması.
   - İkinci tam keşifte `ADDED`, `CHANGED`, `REMOVED` farklarının kalıcı ve
     sorgulanabilir olması.
   - `PARTIAL` keşifte görünmeyen dataset/alan için `REMOVED` çıkarılmaması ve
     mevcut katalog kaydının pasifleştirilmemesi.
   - İlk başarılı keşfin güvenli biçimde katalog oluşturması; sonraki farkların
     açık uygulama adımıyla uzlaştırılması.

5. **Katalog okuma API'si**
   - Yetkili source/dataset kapsamına göre dataset listesi ve detayı.
   - Dataset alanları ve alan detayı.
   - Keşif durumu ve fark görünürlüğü.
   - Boş kapsamın kurum geneli erişim olarak yorumlanmaması.

6. **Frontend katalog akışı**
   - `AppShell` altında Katalog navigasyonu.
   - Dataset listesi, dataset detayı ve alan detayı.
   - Veri kaynağı yüzeyinden metadata keşfi başlatma ve durum izleme.
   - Kural oluşturma formundaki serbest `dataset_id`/field kimliği girişlerinin
     yetkili katalog seçicileriyle değiştirilmesi.

7. **Permission ve scope**
   - Keşif başlatma, scope yapılandırma ve fark uygulama için ayrı backend rol
     kapıları.
   - Her komutta trusted `ActorContext`; payload içindeki source/dataset bilgisi
     actor scope'unun yerine geçmez.
   - Okuma sorgularında source ve dataset scope'unun PostgreSQL sorgusuna
     taşınması; frontend filtrelemesi tek güvenlik sınırı değildir.

8. **Transactional audit**
   - `METADATA_DISCOVERY_REQUESTED`, `METADATA_DISCOVERY_STARTED`,
     `METADATA_DISCOVERY_COMPLETED`, `METADATA_DISCOVERY_PARTIAL`,
     `METADATA_DISCOVERY_FAILED`, `DISCOVERY_SCOPE_CHANGED`,
     `METADATA_DIFF_COMPUTED`, `METADATA_DIFF_APPLIED`.
   - Katalog/fark yazımı ile ilgili outbox olayının aynı transaction'da olması.
   - Secret, örnek satır veya hassas alan değerlerinin job payload/audit'e
     yazılmaması.

9. **Production-path test zinciri**
   - Migration head → API → queue → worker → gerçek connector adapter sınırı →
     PostgreSQL katalog → API/UI smoke testi.
   - Restart sonrası katalog ve keşif durumunun korunması.
   - Permission/scope negatifleri, audit rollback, stable ID ve `PARTIAL` koruma
     testleri.

### 3.2 Kapsam dışı

| Konu | Sahibi / gerekçe |
|---|---|
| Profil çalıştırma, baseline ve profil karşılaştırması | DS-08 / GAP-005 |
| Resmî şema değişikliği sınıflandırma, kabul/ret kararı ve kuralı `REVIEW_REQUIRED` durumuna geçirme | DS-13 / GAP-019 |
| Lineage ve aşağı akış etki analizi | DS-14 / GAP-012 + GAP-013 |
| Otomatik issue üretimi | DS-05 / GAP-006 |
| Sahiplik atama, glossary ve kurumsal domain modeli | DS-21 / GAP-026 |
| Gelişmiş sınıflandırma aday/inceleme yaşam döngüsü | Sonraki katalog/yönetişim dilimi; bu dilimde mevcut classification alanı ve güvenli varsayılan gösterilir |
| Tam metin arama motoru ve ayrı arama indeksi | Basit PostgreSQL filtreleme yeterlidir |
| Yeni connector türleri | Mevcut connector registry yeniden kullanılır |

DS-04 fark kaydında `requires_rule_review` sinyalini taşıyabilir; fakat kural durum
geçişini veya kritik değişiklik onayını kendisi yapmaz. Roadmap DS-04 satırındaki
“fark uygulaması kuralı `REVIEW_REQUIRED` yapar ve kritik kuralda onay ister”
ifadesi DS-13 kapsamıyla çakışmaktadır ve bu kararla DS-13'e bırakılmıştır.

### 3.3 Migration sınırı

Roadmap'teki “Migration 16” numarası artık kullanılamaz; DS-03 envanteri revision
16'yı ayırmıştır. DS-04 migration'ı, uygulama anındaki gerçek Alembic head'in
ardından benzersiz revision olmalıdır; mevcut plan gerçekleşirse önerilen revision
`20260805_17` olur.

Mevcut migration 03 değiştirilmez. Yeni migration yalnız bu dilimin gerektirdiği
durum/scope/diff ve safe-reconciliation kolon veya tablolarını ileri yönde ekler.
Ayrıntılı tablo/kolon listesi sonraki change inventory belgesinde repository
kanıtına karşı dondurulur.

## 4. Kabul kriterleri

1. Yetkili kullanıcı kendi kapsamındaki `ACTIVE` kaynağa metadata keşif talebi
   gönderdiğinde kalıcı keşif ve job kaydı oluşur; worker işi sahiplenir.
2. API, job ve metadata discovery için production composition gerçek
   PostgreSQL repository, gerçek transactional audit ve connector registry yolunu
   kullanır; mock/fake production fallback yoktur.
3. Başarılı ilk keşif sonunda bulunan dataset ve alanlar stable kimliklerle
   kalıcıdır; süreç yeniden başladıktan sonra aynı API ve katalog ekranında görünür.
4. İkinci tam keşif eklenen, değişen ve kaldırılan nesneler için kalıcı fark
   üretir; fark uygulandığında değişmeyen dataset/field kimlikleri korunur.
5. `PARTIAL` keşif açıkça `PARTIAL` kaydedilir; görünmeyen nesneler için
   `REMOVED` farkı, silme veya pasifleştirme yapılmaz.
6. Teknik connector/secret/timeout hatası `TECHNICAL_ERROR` olarak sınıflandırılır;
   mevcut başarılı katalog snapshot'ı korunur ve kalite başarısızlığı üretilmez.
7. Keşif başlatma, scope güncelleme ve fark uygulama backend'de rol + source scope
   kontrolünden geçer; yetkisiz source/dataset doğrudan HTTP isteğiyle de
   okunamaz veya değiştirilemez.
8. Keşif, scope, fark ve katalog değişiklikleri ilgili iş kaydıyla aynı
   transaction'da audit outbox'a yazılır; audit stage hatasında iş değişikliği
   rollback olur.
9. Katalog listesi yalnız aktörün yetkili source/dataset kapsamını döndürür; boş
   kapsam veri sızdırmaz. Hassas alanlarda örnek değer gösterilmez.
10. Kullanıcı veri kaynağı ekranından keşfi başlatıp durumunu izleyebilir; dataset
    ve alanı katalogda açabilir.
11. Kural oluşturma ekranı yetkili katalog dataset/alanlarını gerçek API'den
    seçtirir; production API hatasında sentetik kimlik veya başarılı fixture
    göstermez.
12. Gerçek PostgreSQL ve worker composition ile çalışan smoke testi
    `API → job → connector → catalog persistence → API/UI` zincirini doğrular;
    yalnız mock'lu frontend E2E testi kabul kanıtı sayılmaz.

## 5. Giriş ve çıkış kapısı

### Giriş kapısı

- DS-01 ve DS-02 production komut/kalıcılık zinciri tamamlanmış olmalıdır.
- DS-03 worker runtime, service identity, claim audit ve production executor
  composition çıkış kapısı gerçekten geçmiş olmalıdır.
- Mevcut Alembic head doğrulanmadan revision numarası sabitlenmemelidir.

DS-03 yalnız planlanmış fakat uygulanmamışsa DS-04 seçimi değişmez; uygulamaya
başlama kapısı açılmış sayılmaz.

### Çıkış kapısı

> Yetkili kullanıcı aktif kaynakta keşif başlatır; gerçek worker ve connector
> dataset/alan metadata'sını kalıcı ve güvenli biçimde uzlaştırır; kullanıcı bu
> nesneleri scope-safe katalog ekranında görür ve kural oluştururken seçebilir.

## 6. Karar

**Seçim: GO — DS-04 dördüncü tek dilimdir.**

Bu karar uygulama yetkisi değildir. Bir sonraki adım, DS-04 için değişecek tablo,
kolon, migration, servis, endpoint, ekran ve testlerin dosya/simge düzeyi change
inventory'sini hazırlamak ve özellikle `PARTIAL` snapshot modelini repository
koduna karşı doğrulamaktır.

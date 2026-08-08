---
type: functional-audit-work
stage: "18 — Altıncı Dilim Kararı"
scope: sixth-slice-decision
inputs:
  - 17-Slice-DS05-Change-Inventory.md
  - 17-Slice-DS05-Plan-Validation.md
  - 16-Fifth-Slice-Decision.md
  - 07-Implementation-Waves.md
  - ../04-Functional-Gap-Inventory.md
  - ../13-Implementation-Roadmap.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-06
---

# 18 — Altıncı Dilim Kararı

> Bu belge ilk beş dilimden sonra uygulanacak **tek** altıncı dilimi seçer.
> Teknik değişiklik envanteri veya uygulama değildir; seçim gerekçesini, kapsam
> sınırını, giriş kapılarını ve ölçülebilir kabul kriterlerini dondurur.

---

## 1. Karar

**Altıncı uygulanacak tek dilim: DS-06 — Skor kalıcılığı ve yayım
(GAP-008).**

Tek ürün sonucu şudur:

> Kalıcı bir çalıştırmanın uygun ölçüm sonuçlarından hesaplanan kural, dataset,
> boyut, kaynak ve kurumsal skorlar PostgreSQL'e kanıt ve politika sürümleriyle
> yazılır; tam seviye kümesi tek transaction'da yayımlanır. Yetkili kullanıcı
> gerçek skor geçmişini, ayrıntısını ve dönem karşılaştırmasını API ve arayüzden
> görür; yayımlanmış skor saklanan girdilerle birebir yeniden üretilebilir.

Bağımlılık yolu:

```text
DS-01 trusted ActorContext ve backend scope
  → DS-02 production PostgreSQL composition
    → DS-03 gerçek execution/result/worker
      → DS-06 skor kalıcılığı ve atomik yayım
        → DS-12 asenkron skor raporları

DS-03 → DS-05 issue üretimi → DS-09 bildirim
DS-02 → DS-04 katalog ve metadata keşfi
```

DS-05 beşinci teslim sırasındadır fakat DS-06'nın hard dependency'si değildir.
DS-06'nın zorunlu girdisi, DS-03'ün production yolunda ürettiği kalıcı ve anlamlı
`RuleExecutionResult` kayıtlarıdır.

## 2. Seçim gerekçesi

### 2.1 Çekirdek ölçüm döngüsünün kullanıcıya dönük son eksik halkasıdır

DS-01–DS-05 kalıcı komut, execution, katalog ve issue yollarını kurar. Buna
karşılık üretim composition'ı dashboard için hâlâ dışarıdan servis enjeksiyonu
bekler; servis verilmezse `UnavailableDashboardService` ile fail-closed olur.
Gerçek skorlar production PostgreSQL yolunda hesaplanıp okunmadığı sürece sistemin
en görünür çıktısı olan dashboard işletim kanıtı değildir.

`07-Implementation-Waves.md` DS-06 karşılığı S7'yi D2 ölçüm ve sorun dalgasının
bağımsız skor kolu olarak tanımlar. Bu dilim o kolu kapatır: dashboard skoru seed
veya geliştirme deposundan değil `quality_scores` tablosundan okunur.

### 2.2 Hesaplama çekirdeği vardır; eksik olan kalıcılık ve yayım sınırıdır

Repository'de yeniden kullanılacak güçlü bir çekirdek bulunur:

- `scoring/service.py:ScoringService` kural, dataset, boyut, kaynak ve enterprise
  skorlarını hesaplar; ağırlık, seviye ve kısmi skor kararlarını taşır. Kritik
  veto uygulaması mevcut değildir ve bu dilimin dışında tutulur.
- `scoring/contributions.py` katkı grafiğini ve iki skor arasındaki farkı üretir.
- `scoring/trends.py` zaman serisi bileşenlerini hesaplar.
- `scoring/partial_score_policies.py` resmî/provizyonel kısmi skor uygunluğunu
  politika ile belirler.
- `scoring/postgresql_contributions.py:PostgreSQLContributionGraphRepository`
  katkı grafiğini PostgreSQL ve transactional audit outbox ile yazabilir.
- `dashboard/service.py:DashboardQueryService` trusted `ActorContext` üzerinden
  kaynak/dataset/enterprise kapsamını backend'de filtreler.
- Frontend'deki `ScoreContributionPanel`, `FieldScoreComparison`, `TrendPanel` ve
  `DashboardPage` gerçek DTO'lara bağlanabilecek mevcut sunum bileşenleridir.

Yeni bir skor motoru veya ikinci bir dashboard mimarisi gerekmemektedir. Asıl
boşluk `SQLiteScoreRepository`'ye somut bağlı servis imzası, PostgreSQL
`quality_scores`/`score_publications` tabloları, yayın state-machine'i, skor API'si
ve production composition wiring'idir.

### 2.3 Mevcut durum yeniden başlatmaya ve eşzamanlı yayına dayanıklı değildir

`quality_scores` bugün yalnız `scoring/repository.py:SQLiteScoreRepository`
içindeki SQLite DDL'inde vardır. Alembic zincirinde yalnız
`20260730_13_score_contribution_graphs.py` bulunur; PostgreSQL skor ve yayın
tabloları yoktur. Dolayısıyla mevcut geliştirme skoru:

- proses/veritabanı profili değişiminde production kanıtı olamaz,
- önceki yayımı `SUPERSEDED` yapan tek-kazanan yayın zinciri kuramaz,
- aynı kaydı saklanan sayaç, ağırlık ve politika sürümüyle yeniden üretemez,
- ayrı skor listesi, detay ve karşılaştırma API'lerini besleyemez.

DS-06 bu boşluğu mevcut scoring domain'ini koruyarak kapatan en küçük dikey
dilimdir.

### 2.4 DS-12'yi açar ve raporun sentetik veriye bağlanmasını önler

Roadmap'te DS-12 doğrudan DS-03 ve DS-06'ya bağlıdır. Skor yayım kaydı olmadan
asenkron raporlama yalnız anlık sorgu veya fixture üstünde kurulabilir. DS-06'nın
önce tamamlanması, rapor üretiminin sürümlü ve yeniden üretilebilir bir yayından
beslenmesini sağlar.

### 2.5 Diğer adayların neden şimdi seçilmediği

| Aday | Bu turda seçilmeme nedeni |
|---|---|
| DS-07 — Zamanlama ve gölge çalışma | Çalıştırma sayısını artırır; kalıcı ve yayımlanmış skor eksikliğini kapatmaz |
| DS-09 — Bildirim hattı | DS-05 sonrası açılmıştır ve sıradaki kritik adaydır; ancak çekirdek DS-01…DS-06 dizisinin gerçek skor çıktısı önce tamamlanmalıdır |
| DS-10 — Kimlik, rol ve oturum | Retrofit borcu yüksek P1 dilimidir; DS-06 mevcut trusted `ActorContext` ve backend scope sınırını genişletmeden koruyabilir. Kalıcı IAM, sonraki D3 girişinde ele alınmalıdır |
| DS-08 — Profil/baseline | DS-03 ve DS-04'e bağlı daha büyük P2 kapsamıdır; skor yayımı olmadan profil sonucunun kurumsal skora etkisi görünür olmaz |
| DS-13 — Şema değişimi | DS-04'e bağlı P2 dilimidir; çekirdek skor zincirini veya DS-12'yi açmaz |

## 3. Kapsam

### 3.1 Dahil

1. **PostgreSQL skor kalıcılığı**
   - `quality_scores` kayıtlarının mevcut `QualityScore` semantiğini koruyacak,
     sayısal değeri sıfırla skor yokluğunu ayıracak biçimde kalıcılaştırılması.
   - Execution, rule result/version, kapsam, ölçüm durumu, mevcut score status,
     formül/politika sürümü ve hesaplama kanıtlarının saklanması.
   - `score_contribution_graphs` tablosunun yeniden kullanılması; aynı veriyi
     taşıyan ikinci katkı/açıklanabilirlik tablosu kurulmaması.
   - Mevcut SQLite repository'nin test/development adapter olarak korunması;
     production yolu yapılmaması.
   - Aktif configuration ve approval kayıtlarının PostgreSQL'e taşınması;
     migration'ın örtük aktif config yaratmaması ve beklenen sürüm yoksa
     production preflight'ın fail-fast olması.

2. **Atomik yayın state-machine'i**
   - Dönem ve yayın kimliği taşıyan `score_publications` kaydı.
   - Gerekli kural/dataset/boyut/kaynak/enterprise seviye kümesinin tek
     transaction'da yazılması ve yayımlanması.
   - Yeni yayının tek kazanan olarak `PUBLISHED`, önceki geçerli yayının aynı
     transaction'da `SUPERSEDED` olması.
   - Seviyelerden biri eksik veya geçersizse hiçbir seviyenin yayımlanmaması.
   - Aynı dönem/kapsam için retry ve eşzamanlı iki yayın denemesinin idempotent ve
     yarış güvenli olması.

3. **Yeterlilik ve resmî skor kapısı**
   - Uygun olmayan sonuçta sayısal skor iddia edilmemesi; bunun mevcut
     `ScoreStatus.NOT_CALCULATED`, null `score_value`, persisted
     `eligible_for_official_scoring=false` ve hesaplama nedeni ile temsil
     edilmesi. Yeni `ScoreStatus.NOT_QUALIFIED` değeri eklenmemesi.
   - Shadow veya resmî skor için uygun olmayan execution sonucunun yayına
     girmemesi.
   - `PARTIALLY_QUALIFIED` sonucun yalnız aktif kısmi skor politikası açıkça izin
     veriyorsa sayısal ve görünür `PARTIAL` olarak hesaba katılması; provizyonel
     kısmi sonucun yayımlanmaması.
   - “Kısmi hesapta yayım yok” kuralının, zorunlu yayın seviye kümesi eksikse
     transaction'ın tamamını reddetmesi olarak uygulanması.

4. **Hesaplama ve yeniden üretim**
   - `ScoringService`, katkı, trend ve partial-policy bileşenlerinin yeniden
     kullanılması; repository bağımlılığının SQLite somut tipinden porta
     ayrıştırılması.
   - Yayımlanmış skorun saklanan passed/evaluated sayaçları, dahil/haricî
     bileşenler, ağırlıklar, eşik/formül/politika sürümleri ve rule version digest
     ile yeniden hesaplanması.
   - Yeniden üretim farkında fail-closed sonuç ve audit; mevcut skor kaydının
     sessizce üzerine yazılmaması.

5. **Skor sorgu ve komut API'si**
   - Kapsam ve dönem filtreli skor listesi.
   - Tekil skor ayrıntısı ve kural sürümü skor geçmişi.
   - İki yayımlanmış dönem/skor arasında karşılaştırma.
   - Yetkili yeniden üretim doğrulama komutu.
   - DTO'larda publication, policy/rule version, katkı, measurement ve resmîlik
     bilgilerinin veri-minimum projeksiyonu.

6. **Frontend skor yüzeyi**
   - App shell'de yeni **Skorlar** bölümü; liste, detay ve karşılaştırma akışı.
   - Mevcut katkı, alan karşılaştırma ve trend bileşenlerinin gerçek skor API'sine
     bağlanması.
   - Dashboard'un production composition'da PostgreSQL score reader kullanması.
   - API hatası veya yetkisiz kapsamda sentetik/fixture skorun başarılı veri gibi
     gösterilmemesi. `import.meta.env.DEV` fixture-state yolu yalnız açık
     geliştirme senaryosu olarak kalır.

7. **Permission ve scope**
   - Skor okumada yeni `score.read` action/permission tanımlamadan mevcut trusted
     context ve dashboard scope authorization kararının yeniden kullanılması.
   - Reproduction için yeni rol/action eklemek yerine aynı okuma kapsamına ek
     olarak `ActorContext.privileged=true` koşulu.
   - Kural/dataset/boyut skorunun parent dataset/source ilişkisi üzerinden;
     source skorunun source kapsamından; enterprise skorunun
     `can_view_enterprise` üzerinden doğrulanması.
   - Yayımın trusted, süresi geçmemiş system/service `ActorContext` ile yapılması.
   - Frontend action görünürlüğünün yalnız UX projeksiyonu olması; her sorgu ve
     yeniden üretim komutunda backend yetkisinin tekrar uygulanması.

8. **Transactional audit**
   - `RULE_SCORE_CALCULATED`, `SCORE_AGGREGATED`, `SCORE_PUBLISHED` ve
     `SCORE_REPRODUCTION_VERIFIED` olayları.
   - Skor/yayın/katkı değişiklikleri ile audit outbox kaydının aynı PostgreSQL
     transaction'ında olması; audit stage hatasında iş değişikliğinin rollback
     edilmesi.
   - Outbox publish'inin commit sonrasında yapılması; log veya proses-içi sink'in
     production audit kanıtı sayılmaması.

9. **Production composition ve test zinciri**
   - API ve gerekiyorsa worker tarafında aynı PostgreSQL score repository, yayın
     servisi, gerçek execution/rule/source reader ve transactional audit'in
     bağlanması.
   - Preflight'a yeni tabloların ve gerçek Alembic head'in eklenmesi.
   - `api/composition.py:PhaseBProviders` yapısının değiştirilmemesi; score
     publication actor-context provider'ının mevcut
     `jobs/production.py:ProductionWorkerProviders` içinde worker/Phase C
     composition girdisi olması ve production'da eksikse fail-fast edilmesi.
   - `execution result → score calculation → atomic publication → score API →
     dashboard/skor ekranı → audit outbox → reproduction` zincirinin gerçek
     PostgreSQL ve production composition üzerinden doğrulanması.

### 3.2 Kapsam dışı

| Konu | Sahibi / gerekçe |
|---|---|
| Zamanlama, cron ve missed-run yönetimi | DS-07 / GAP-003 + GAP-015 |
| Bildirim aboneliği ve kanal teslimatı | DS-09 / GAP-007 |
| Kalıcı IAM, rol atama ve IdP yönetimi | DS-10 / GAP-022; mevcut trusted context sınırı korunur |
| PDF/XLSX/CSV üretimi ve rapor iş yaşam döngüsü | DS-12 / GAP-016 |
| Risk derecelendirme ve risk haritası | DS-14 / GAP-013 |
| Kritik kural veto mekanizması ve `CRITICAL_VETO_APPLIED` | Mevcut domain servisinde yoktur; ayrı iş kuralı/politika kararı olmadan DS-06'ya eklenmez |
| İstisna/override ve kalite borcu | DS-15 / GAP-009 |
| Yeni skor formülü, ML modeli veya alternatif analitik motor | GAP-008 için gerekli değildir; mevcut domain hesabı yeniden kullanılır |
| `score_contribution_graphs` yerine yeni açıklanabilirlik tablosu | Gereksiz çoğaltma; mevcut PostgreSQL repository korunur |
| SQLite repository'yi production composition'a bağlamak | Development/test adapter'ıdır; production kabul kanıtı değildir |

### 3.3 Migration sınırı

Roadmap'teki “Migration 17” numarası artık güncel Alembic zinciriyle uyumlu
değildir. Repository head'i `20260806_18_issue_generation.py` olduğundan DS-06
uygulaması en küçük forward migration olarak **revision 19**'dan başlamalıdır.
Revision 01–18 ve mevcut `score_contribution_graphs` migration'ı değiştirilmez.

Migration'ın tablo/kolon ayrıntıları bir sonraki change inventory belgesinde
gerçek SQLAlchemy ve domain modellerine karşı kesinleştirilmelidir. `QualityScore`
ile publication yaşam döngüsünün statülerini tek kolonda karıştırmak yerine skorun
hesaplama durumu ile yayın durumunun ayrı sahipliği korunmalıdır.

## 4. Kabul kriterleri

1. Production worker'ın desteklenen gerçek bir kural yürütmesinden ürettiği
   kalıcı `RuleExecutionResult`, aynı execution için kuraldan enterprise seviyesine
   kadar beklenen skor kümesini PostgreSQL'e yazar.
2. Sayısal skor, formül/configuration/threshold/policy sürümü, rule version digest,
   ölçüm durumu, sayaçlar ve dahil-haricî bileşenlerle saklanır; uygulama yeniden
   başladıktan sonra aynı kayıt okunur.
3. `eligible_for_official_scoring=false`, shadow, teknik olarak geçersiz veya
   resmî skora uygun olmayan sonuç `ScoreStatus.NOT_CALCULATED` ve null değerle
   temsil edilir; sayısal skor üretmez ve yayıma girmez. Yeni
   `ScoreStatus.NOT_QUALIFIED` eklenmez, API/UI skor yokluğunu `0` göstermez.
4. Politika tarafından onaylanmamış `PARTIAL` sonuç yayımlanmaz. Onaylı resmî
   kısmi skor kabul ediliyorsa `PARTIAL` işareti kaybolmadan üst agregasyonda ve
   kullanıcı yüzeyinde görünür kalır.
5. Zorunlu seviyelerden biri hesaplanamazsa score publication transaction'ı
   bütünüyle rollback olur; kısmi yayın, katkı grafiği veya audit kaydı kalmaz.
6. Tam yayın tek transaction'da `PUBLISHED` olur ve önceki geçerli yayın aynı
   transaction'da `SUPERSEDED` yapılır. Aynı dönem/kapsamdaki iki eşzamanlı
   denemede yalnız bir güncel yayın kalır.
7. Aynı idempotency anahtarıyla retry/restart ikinci skor veya yayın zinciri
   oluşturmaz; farklı girdiyi aynı anahtarla yeniden kullanma conflict olarak
   reddedilir.
8. Yetkili kullanıcı yalnız izinli source/dataset hiyerarşisindeki skorları okur.
   Yetkisiz kural, dataset, source veya enterprise isteği backend'de reddedilir ve
   response varlığın mevcut olup olmadığını sızdırmaz.
9. Trusted ve aynı score scope'una yetkili olsa bile `privileged=false` aktör
   yeniden üretim başlatamaz. `privileged=true` aktörün yeniden üretimi saklanan
   girdilerle aynı sayısal değer, seviye ve katkı kümesini üretir; fark varsa
   doğrulama başarısız olur ve mevcut yayın değiştirilmez.
10. Skor hesaplama/agregasyon/yayım ve audit outbox kayıtları aynı PostgreSQL
    transaction'ındadır. Audit stage hatasında skor/yayın değişikliği rollback
    olur; publish commit'ten sonra gerçekleşir.
11. `GET /scores`, skor detay/kural geçmişi ve karşılaştırma yolları gerçek
    PostgreSQL kayıtlarını döndürür; frontend Skorlar sayfaları bu yollarla
    history/detail/comparison akışını tamamlar.
12. Production dashboard aynı PostgreSQL score reader'dan veri alır. API hatasında
    veya boş sonuçta geliştirme seed'i başarılı production verisi olarak
    gösterilmez.
13. Katkı grafiği mevcut `score_contribution_graphs` yapısında saklanır ve skor
    ayrıntısıyla tutarlıdır; aynı purpose için ikinci tablo veya hesap motoru
    eklenmez.
14. En az bir gerçek başarısızlık ve bir `NO_DATA`/uygunsuzluk senaryosu production
    executor yolundan geçirilir; yalnız yüzde 100 başarılı fixture ile kurulan test
    dilimin işlevsel kabul kanıtı sayılmaz.
15. PostgreSQL migration, repository, yayın concurrency/rollback, backend
    permission/scope, API contract, frontend component ve live production
    composition testlerinin tamamı geçer.

## 5. Giriş ve çıkış kapısı

### Giriş kapısı

- DS-01'in trusted `ActorContext`, policy-version ve backend authorization sınırı
  korunmuş olmalıdır.
- DS-02'nin PostgreSQL repository/composition ve transactional audit outbox yolu
  çalışmalıdır.
- DS-03 production executor'ı desteklenen bir rule IR ile gerçek `passed_count`,
  `failed_count`, `measurement_status` ve eligibility üretmelidir.
- Alembic head `20260806_18` olmalı; mevcut migration'lar değiştirilmemelidir.

`PostgreSQLRuleExecutionExecutor` template kuralları için gerçek ihlal ve
population sorguları üretmektedir. Ancak özel `sql`/`count_query` kolu dönen sayıyı
population kabul edip `failed_count=0` üretir. DS-06 kabul testi bu belirsiz özel
SQL yolunu resmî skor kanıtı olarak kullanmamalı; ya sözleşme change inventory'de
netleştirilmeli ya da doğrulanmış template-rule yolu kullanılmalıdır.

### Çıkış kapısı

> Dashboard ve Skorlar ekranındaki değer PostgreSQL `quality_scores` ve güncel
> `score_publications` zincirinden gelir; aynı yayın saklanan kanıtla birebir
> yeniden üretilir, yetkisiz kapsam sızmaz ve yayın/audit atomikliği PostgreSQL
> production-composition testiyle kanıtlanır.

## 6. Karar

**Seçim: GO — DS-06 altıncı tek dilimdir.**

Bu karar uygulama yetkisi değildir. Uygulamaya başlamadan önce DS-06 change
inventory'si; revision 19 migration'ını, skor repository portunu, publication
state-machine'ini, API sözleşmesini, production composition wiring'ini ve gerçek
negative-result test fixture'ını dosya/simge düzeyinde kesinleştirmelidir.

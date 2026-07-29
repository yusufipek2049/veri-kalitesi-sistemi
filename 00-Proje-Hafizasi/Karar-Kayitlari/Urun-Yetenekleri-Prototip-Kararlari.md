---
type: canonical-decision-register
status: active
decision_status: PrototypeDecision
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-29
source: USER-REQUEST-2026-07-29-CAPABILITY-REVIEW
---

# Ürün Yetenekleri Prototip Kararları

Bu kayıt, [ürün yetenek durum matrisinde](../Urun-Yetenek-Durum-Matrisi.md)
eksik veya kısmi görülen alanların uygulanabilmesi için teknik ve ürün yönünü
seçer. Kararlar mevcut SRS, `DQ-SCR-*`, `OPEN-026–036` ve ADR sınırlarını
genişletmeden ayrıntılandırır.

Tüm kayıtların durumu `PrototypeDecision`dır. Gerçek kurumsal ürün seçimi,
üretim eşiği/kotası/saklama süresi, banka onayı ve `ApprovedByBank` sonucu bu
belgeyle oluşmaz. Böyle bir değer aktif, sürümlü ve onaylı politikada yoksa
pozitif karar üretilmez; ilgili işlem fail-closed kalır.

## Ortak Karar Sınırları

- Kaynak veriye yalnız salt okunur erişilir; öneri veya remediation üretim
  kaynağını değiştiremez.
- Ham hassas değer, secret veya token profil, örnek, log, bildirim, kanıt ya da
  audit payload'ına taşınmaz.
- Teknik hata, veri kalitesi ihlali, ham skor, ölçüm yeterliliği, güven, risk ve
  kullanım kararı ayrı tutulur.
- Kritik yazımlar audit/outbox ile atomik tamamlanır. Politika veya kanıt eksikse
  güvenli olumlu sonuç üretilmez.
- Prototiplerde yalnız sentetik veri, fake/sandbox hedef ve yerel kurulum
  kullanılabilir; kurumsal entegrasyon veya üretim uygunluğu iddia edilmez.

## Seçenekler ve Kararlar

| ID | Alan | Değerlendirilen seçenekler | Seçilen prototip yönü ve gerekçe |
| --- | --- | --- | --- |
| `DQ-CAP-001` | Profilleme | Tüm veriyi uygulamaya çekmek; yalnız kaynak SQL toplulaştırması; hibrit toplulaştırma ve kontrollü örnekleme. | Hibrit yaklaşım seçildi. Null/distinct/min/max/ortalama/top-N ve dağılımlar mümkünse kaynakta toplulaştırılır; yüksek kardinalite ve desteklenmeyen tiplerde sürümlü politika kontrollü deterministik örnekleme kullanılır. Yöntem, kapsam, örneklem, sorgu/bağlayıcı sürümü ve veri zamanı sonuçta saklanır. Hassas top-N ham değer içermez. |
| `DQ-CAP-002` | Aykırı değer ve kolon ilişkisi | Sabit tek algoritma; otomatik ML; sürümlü istatistiksel yöntem kataloğu. | Sürümlü yöntem kataloğu seçildi. IQR ve robust z-score aday yöntemlerdir; hangisinin etkin olacağı ve parametreleri politikadan gelir. Kolon ilişkisi tüm kolon çiftlerinde otomatik çalıştırılmaz; metadata tipi ve kullanıcı/politika aday listesiyle sınırlandırılır. Sonuç “aday ilişki/aykırılık”tır, kalite ihlali değildir. |
| `DQ-CAP-003` | Kural yazımı ve kapsam | Yalnız hazır şablon; sınırsız SQL; şablon + güvenli özel SQL. | Şablon + güvenli özel SQL seçildi. No-code yüzey ortak ara gösterime derlenir; ileri kullanım salt okunur, tek statement, kapsam/timeout/kota kontrollü SQL kullanır. Kolon, satır, dataset, tablolar arası, referans, mutabakat ve zaman serisi kapsamları aynı sayaç/evidence sözleşmesini üretir. DDL/DML ve belirsiz SQL reddedilir. |
| `DQ-CAP-004` | Kalite boyutları | Altı temel boyut; sınırsız serbest etiket; yedi kontrollü boyut ve ek sınıflandırma. | Domain modelindeki yedi kontrollü boyut korunur: tamlık, doğruluk, tutarlılık, geçerlilik, benzersizlik, zamanlılık ve bütünlük. “Doğruluk” otoriter referans veya bağımsız ground truth olmadan atanamaz; biçim kontrolü geçerlilik olarak kalır. Yeni boyut kod değişikliği ve yönetişim incelemesi gerektirir. |
| `DQ-CAP-005` | Açıklanabilir skor | Tek yüzde; serbest metin açıklama; yeniden üretilebilir katkı grafiği. | Katkı grafiği seçildi. Her sonuç; dahil/dışlanan kuralları, sayaçları, ağırlık ve politika/model sürümlerini, kapsama/yeterlilik durumunu ve üst seviyeye katkısını taşır. Kritik alan/kural ham kalite skorunu sessizce değiştirmez; ayrı veto/uygunluk sinyali olur. İş alanı toplamı ancak sürümlü sahiplik hiyerarşisi varsa üretilir. |
| `DQ-CAP-006` | Anomali ve değişim tespiti | Yalnız sabit eşik; ilk günden denetimsiz ML; deterministik istatistiksel baseline ve isteğe bağlı shadow model. | İlk prototip için deterministik baseline seçildi. Hacim oranı, null oranı, kategori kümesi/top-N, sayısal özet, güncellik ve şema snapshot'ı geçmiş uyumlu profillerle karşılaştırılır. Eşik, minimum geçmiş ve pencere politikadan gelir; yoksa anomali hükmü verilmez. ML yalnız ileride shadow modda, bağımsız kalibrasyon kanıtıyla değerlendirilebilir. |
| `DQ-CAP-007` | Lineage, kök neden ve etki | Uygulamanın rakip katalog olması; serbest metin neden; kurumsal katalog referansı + olay/snapshot + kanıtlı hipotez. | `OPEN-027–029` ile uyumlu üçüncü seçenek seçildi. Prototip, sentetik OpenLineage uyumlu olayları ve değişmez snapshot/digest'i kullanır. Zaman çizgisi, ilk gözlenen bozulma, upstream/downstream ve benzer olaylar “hipotez” üretir; korelasyon doğrulanmış neden sayılmaz. Her etki `Observed/Calculated/Estimated/Unknown`, kaynak ve güven taşır. |
| `DQ-CAP-008` | İhlal inceleme kanıtı | Ham başarısız satırlar; yalnız toplu sayaç; katmanlı veri-minimum kanıt. | Katmanlı kanıt seçildi. Varsayılan görünüm sayaç, fingerprint, maskeli/toplulaştırılmış örnek ve güvenli referanstır. Gerçek kayıt istisnai, gerekçeli, süreli, kapsamlı ve auditli erişim gerektirir. Query şablonu/planı gösterilebilir; secret, bind değeri ve yetkisiz ham SQL sonucu gösterilmez. Öneri kaynak ve karşı kanıt olmadan yayınlanmaz. |
| `DQ-CAP-009` | Bildirim ve ticket entegrasyonu | Her kanalın domain içine gömülmesi; yalnız kurum içi ekran; canonical event + adaptörler. | Canonical event + adaptör seçildi. Sistem içi bildirim otoriter kalır; e-posta/mesajlaşma/ServiceNow/Jira adaptörleri aynı veri-minimum olayı tüketir. Idempotency key, dedup/suppression penceresi, routing, SLA ve escalation sürümlü politikadan gelir. Prototip yalnız fake/sandbox adaptör kullanır; gerçek kanal hatası kalite sonucunu değiştirmez. |
| `DQ-CAP-010` | Sahiplik ve yönetişim | Dağınık serbest metin alanlar; uygulamanın ana katalog olması; kurumsal katalog referanslı sürümlü profil. | Sürümlü `DataAssetGovernanceProfile` yönü seçildi. Profil; data owner, teknik owner/steward, iş birimi, kritiklik, sınıflandırma, hedef/SLA, saklama ve ilgili asset referanslarını etkinlik aralığıyla taşır. Kurumsal katalog sistem-of-record; prototip sentetik registry kullanır. Zorunlu routing alanı yoksa otomatik atama fail-closed olur. |
| `DQ-CAP-011` | Tarih ve karşılaştırma | Son değeri güncellemek; her şeyi event olarak tutmak; değişmez snapshot + seçili yaşam döngüsü olayları. | Snapshot + olay yaklaşımı seçildi. Profil, kural, skor, yeterlilik ve yönetişim sürümleri değişmez referanslanır; issue geçişleri olaydır. Resmî/provizyonel sonuçlar ayrılır. Dönem karşılaştırma, tekrar, çözüm süresi ve SLA metrikleri yalnız aynı kapsam/politika zaman dilimleri arasında hesaplanır. |
| `DQ-CAP-012` | Güvenlik ve audit prototipi | Kurumsal ürünleri taklit etmeden beklemek; prototipi üretim gibi göstermek; kapılı sentetik adaptörler. | Kapılı sentetik adaptörler seçildi ve mevcut ENTERPRISE-LAB yaklaşımı korunur. Sentetik IdP, yerel dosya tabanlı secret, fake SIEM/ServiceNow yalnız açık lab ortamında çalışır. Gerçek IdP/PAM/KMS/SIEM/WORM erişimi olmadan `PrototypeVerified` üstü durum üretilemez. |
| `DQ-CAP-013` | Büyük veri yürütme | Her zaman full scan; serbest otomatik strateji; deterministik politika motoru. | `OPEN-033` ile uyumlu deterministik politika motoru seçildi. Stratejiler full/partition/incremental/sample/aggregate olarak modellenir. Incremental yalnız kaynak-özel, değişmez watermark sözleşmesi varsa; resume yalnız tamamlanmış partition/checkpoint sınırında yapılır. Concurrency, timeout, kota, maliyet bütçesi ve çalışma penceresi onaylı politikadan gelir; eksikse daha pahalı stratejiye otomatik geçilmez. |
| `DQ-CAP-014` | Kural yaşam döngüsü ve shadow | Shadow'u statü yapmak; yalnız active/passive; yönetişim statüsü ile yürütme modunu ayırmak. | Ayrım seçildi. Yaşam döngüsü `DRAFT → REVIEW_REQUIRED → ACTIVE/PASSIVE → ARCHIVED` sözleşmesini korur; onay sonucu ayrı kayıttır. `SHADOW` ve ileride `CANARY`, yürütme modudur: resmî skora/uyarıya katılmaz ve açıkça etiketlenir. Aktivasyon, pasifleştirme ve arşivleme aktör, gerekçe, sürüm ve audit taşır. |
| `DQ-CAP-015` | Dashboard deneyimi | Tek genel dashboard; tamamen ayrı veri modelleri; role göre görünüm, ortak yetkili API. | Ortak yetkili API üzerinde role göre görünüm seçildi. Yönetici görünümü skorun yanında yeterlilik, risk, kritik asset, bozulma ve SLA'yı; mühendis görünümü sayaç, güvenli örnek, query/plan, log referansı, profil, geçmiş ve kanıtlı lineage/hipotezi gösterir. Kanıtı olmayan teşhis/etki alanı “Unknown” olur; tahmin gerçek gibi gösterilmez. |

## Uygulama Sırası Kararı

Bu kayıt mevcut `NEXT_STEP` görevini değiştirmez ve otomatik `READY` işi açmaz.
Bağımlılıkları tamamlandığında önerilen prototip sırası şöyledir:

1. `DQ-CAP-001`, `002` ve `006`: sürümlü profil snapshot'ı, dağılım/aykırı
   değer ve deterministik drift çekirdeği.
2. `DQ-CAP-003`, `014` ve `008`: ortak kural ara gösterimi, shadow yürütme ve
   veri-minimum ihlal kanıtı.
3. `DQ-CAP-005`, `011` ve `015`: katkı grafiği, karşılaştırılabilir tarih ve
   rol bazlı açıklanabilir dashboard.
4. `DQ-CAP-007` ve `010`: sentetik katalog/lineage, sahiplik ve kaynaklı
   etki-kök neden hipotezi.
5. `DQ-CAP-009`, `012` ve `013`: fake kanal genişletme, lab güvenlik kapıları
   ve ölçek stratejilerinin sentetik yük doğrulaması.

Her iş paketi ayrı kabul kriteri, test kanıtı ve runtime durum güncellemesi
gerektirir. Bu sıra üretim yol haritası, süre/maliyet taahhüdü veya banka onayı
değildir.

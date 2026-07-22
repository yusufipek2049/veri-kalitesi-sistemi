---
type: architecture-decision-log
project: Veri Kalitesi İzleme ve Skorlama Sistemi
status: seed
last_updated: 2026-07-22
tags:
  - architecture
  - adr
---

# Mimari Kararlar

| ADR | Karar | Durum |
| --- | --- | --- |
| ADR-001 | Kurum içi veri merkezi dağıtımı | Kabul edildi |
| ADR-002 | Kaynaklara salt okunur bağlantı | Kabul edildi |
| ADR-003 | Yerel prototip için konteyner tabanlı modüler monolit | Önerilen başlangıç |
| ADR-004 | Uzun işler için kuyruk ve worker modeli | Önerilen başlangıç |
| ADR-005 | İlişkisel metadata ve sonuç deposu | Önerilen başlangıç |
| ADR-006 | Servis/workload identity ile kurumsal secret manager/PAM; depoda yalnız referans | KararAlındı; kurumsal hizmet eşlemesi ve adaptör uygulaması bekleniyor |
| ADR-007 | LDAP destekli kurumsal IdP/SSO, OIDC veya SAML, zorunlu MFA ve RBAC | KararAlındı; endpoint ve grup-rol-scope eşleme uygulaması bekleniyor |
| ADR-008 | ServiceNow'un ara entegrasyon tablosu veya entegrasyon servisiyle çekirdek issue yönetiminden ayrılması | Kabul edildi |
| ADR-009 | Merkezi audit için hash zinciri, PostgreSQL transactional outbox, kurumsal SIEM veya immutable object storage ve salt okunur/idempotent legacy aktarım | KararAlındı; üretim adaptörü ve operasyon kanıtı bekleniyor |
| ADR-010 | Kişisel veri işleme envanterinin DataField'e bağlı değişmez sürümler ve redakte transactional audit ile tutulması | Teknik olarak doğrulandı; eşlenmeyen banka referans kodu fail-closed kalır |
| ADR-011 | Kritik kural aktivasyonunun sürümlü politika, güvenilir ActorContext ve RuleVersion'a bağlı atomik maker-checker kararıyla yapılması | Teknik olarak doğrulandı; banka rol eşlemesi yoksa işlem reddedilir |
| ADR-012 | Token tabanlı kurumsal görsel dil; marka rengi ile semantik durum renklerinin ayrılması | Tasarım baseline'ı kabul edildi; frontend uygulaması bekliyor |
| ADR-013 | Storybook component doğrulaması ve Playwright görsel regression süreci | Kabul edildi; frontend uygulaması bekliyor |
| ADR-014 | OPEN-001–OPEN-018 karar paketinin kapasite, politika, güvenlik, yaşam döngüsü ve hibrit dağıtım sınırı | KararAlındı; değişken değerlerde aktif sürümlü politika zorunlu |
| ADR-015 | Açıklanabilir, sürümlü ve riskten ayrılmış veri kalitesi skorlama mimarisi (`DQ-SCR-001`–`DQ-SCR-033`) | KararAlındı; eksik politika olumlu sonuç üretmez |
| ADR-016 | Politika kontrollü, deterministik ve bağımsız ground truth'lu sentetik veri hedef mimarisi | KararAlındı; eksik eşik/tolerans doğrulamayı `BLOCKED` yapar |
| ADR-017 | React + TypeScript + Vite, MUI, ECharts, Storybook ve Playwright frontend teknoloji yığını | Kabul edildi; paket kurulumu ve frontend uygulaması bekliyor |
| ADR-018 | Değişken üretim değerlerinde sürümlü ve fail-closed politika çözümleme | KararAlındı; açık karar yerine uygulama/konfigürasyon kapısı |
| ADR-019 | Kanıta dayalı, politika farkındalıklı karar desteği ve üretim verisini değiştirmeyen öneri/remediation sınırı | KararAlındı; `OPEN-026–OPEN-036` yönleri kesin, runtime ve banka incelemeleri açık |

## ADR-019 — Kanıta Dayalı ve Politika Farkındalıklı Karar Desteği

**Bağlam:** Mevcut sistem açıklanabilir skor, ölçüm yeterliliği, issue ve
sentetik ground truth temellerini taşır; ancak kullanım amacı bazlı uygunluk,
etki/lineage/değişiklik simülasyonu, kaynaklı teşhis/öneri, kontrollü remediation,
data contract, adaptif tarama, kalite borcu, chaos kontrol yeterliliği ve olay
kanıt paketi için bütüncül hedef sözleşme yoktur.

**Karar:** `FR-097–FR-111` ve
[Kanıta Dayalı Karar Sistemi](Kanita-Dayali-Karar-Sistemi.md) hedef tasarımı
bağlayıcıdır. Skor, ölçüm/teşhis/öneri güveni ve kanıt gücü ayrıdır. Kanıtsız
öneri, kaynaksız etki, nedensellik gibi sunulan korelasyon ve manifestsiz
yeniden üretilebilirlik kabul edilmez. Öneri/remediation akışı dry-run, etki,
yetki/politika, maker-checker, canary, yeniden doğrulama ve rollback kapılarını
izler. Hiçbir LLM veya başka mekanizma üretim kaynak verisini değiştiremez.

**Sonuç:** Kapsam ikinci fazdır ve mevcut MVP'yi genişletmez. `OPEN-026–OPEN-036`
ile kurumsal katalog otoritesi, deterministik ilk faz öneri/tarama yaklaşımı,
salt okunur üretim sınırı, izole sentetik chaos, gizlilik korumalı inceleme,
kalite borcu ve kanonik kanıt paketi yönleri kesinleşmiştir. Ürün adı ve sayısal
üretim değerleri sürümlü politikalardan çözülür. Karar runtime uygulaması, banka
onayı veya mevzuat uyumluluğu değildir.

## ADR-017 — Frontend Teknoloji Yığını

**Bağlam:** Frontend tasarım sistemi ve dashboard backlogu framework, component,
grafik ve görsel test araçlarının seçimini uygulama bağımlılığı olarak tutuyordu.
Teknik seçim `Alınan Kararlar` kaydında kesinleştirildi.

**Karar:** Frontend React ve TypeScript ile Vite üzerinde geliştirilecektir. Ortak
component altyapısı MUI, grafik katmanı ECharts kullanacaktır. İzole component
durumları Storybook, ekran/akış ve görsel regression kontrolleri Playwright ile
doğrulanacaktır.

**Sonuç:** Bu araçlar için yeniden teknoloji veya dependency onayı beklenmez.
Paket sürümleri ve lock dosyası kurulum iterasyonunda mevcut güvenli SDLC
kurallarına göre oluşturulur. Karar paketlerin kurulduğu, frontend'in uygulandığı
veya banka marka/uyum onayının alındığı anlamına gelmez.

## ADR-014 — Bağlayıcı Karar Paketi

Bu karar; düşük/beklenen/yüksek kapasite senaryolarını, kaynak bazlı kullanım politikasını, kayıt sınıfı bazlı saklama ile bileşen bazlı RPO/RTO'yu, kurumsal katalog/DLP sınıflandırmasını, katmanlı rapor saklamayı, risk bazlı maker-checker'ı, anonimleştirilmiş performans verisini, WCAG 2.2 AA hedefini, hibrit üretim dağıtımını, olay sınıfı bazlı audit davranışını ve dataset politikası kontrollü kısmi resmî skoru bağlayıcı kabul eder.

Pilot VM/konteyner; üretimde kurumsal OpenShift/Kubernetes eşdeğeri, yüksek
erişilebilir PostgreSQL, kurumsal broker veya RabbitMQ fallback'i ve kurumsal
secret manager/PAM kullanılır. Kapasite, kota, timeout ve dosya boyutu gibi
değişken değerler aktif sürümlü politika kaydından çözülür. RPO/RTO normal
kapsamda `PT15M/PT4H`, kritik düzenleyici/risk zincirinde `PT5M/PT1H`dır.
Teknik karar banka onayı anlamına gelmez.

## ADR-015 — Açıklanabilir ve Riskten Ayrılmış Skorlama

**Bağlam:** Mevcut teknik uygulama kural, boyut, dataset, kaynak ve kurum
agregasyonlarını üretmektedir; ancak kapsam ve ölçüm güveni ayrı sözleşme olarak
tam değildir. Kaynak skoru dataset kritiklik ağırlığını kalite agregasyonuna
katmaktadır. Bu davranış `DQ-SCR-018` ile çelişir. Mevcut durum kod tabanı için
gerçek bir uyarlama backlogudur; doküman güncellemesi uygulanmış runtime kanıtı
değildir.

**Karar:** `DQ-SCR-001`–`DQ-SCR-033` bağlayıcıdır. Ayrıntılı hedef sözleşme
[Veri Kalitesi Skorlama ve Ölçüm Yeterliliği](Veri-Kalitesi-Skorlama-ve-Olcum-Yeterliligi.md)
belgesidir. Ham kalite skoru kural → veri öğesi → boyut → dataset hiyerarşisinde
hesaplanır. Kritik kural politikası ham skordan ayrı nihai skor, kritik kural
durumu ve kullanım kararı üretebilir. Ölçüm yeterliliği; kapsam, örneklem,
güncellik, teknik başarı, sürüm, kritik kontrol ve kanıt kapılarını kalite
skorundan bağımsız değerlendirir. Kapsam, güven, dataset kritikliği, veri riski ve
teknik sağlık ayrı çıktıdır. Normalizasyon, eşik, ağırlık, yeterlilik ve kritik
kural davranışları sürümlü politikalardır. İstisna ve override süreli,
maker-checker kontrollü ve auditlidir; ham veya nihai skoru değiştirmez. Skor,
yeterlilik ve replay sonucu tüm model/politika/uygulama sürümlerini korur.

**Superseded karar:** Dataset kritikliğini `SOURCE` kalite skorunda ağırlık olarak
kullanan tarihsel teknik yaklaşım, hedef mimaride `DQ-SCR-018` ile
`Superseded` durumundadır. Geçmiş skorlar değiştirilmez; yeni modele geçiş
sürüm sınırı ve ayrı yeniden hesaplama kaydıyla yapılır.

**Sonuç:** Skorlama motoru, ölçüm yeterliliği kapısı, politika çözümleyici,
risk/remediation ve teknik sağlık sınırları ayrılır. API/UI ham/nihai kalite,
yeterlilik, kullanım kararı, kapsam, güven, risk/kritiklik ve teknik durumu tek
yüzdeye eritmez. Üretim eşikleri, ağırlıkları, veto/tavan davranışı, minimum
kapsam ve örneklem güveni, geçerlilik süreleri, kullanım/blokaj yetkisi,
remediation hedefleri, risk katsayıları, dataset türleri ve `OPEN-BNK-013` kapsamı
aktif sürümlü politika kaydından çözülür; kayıt yoksa ilgili olumlu karar
üretilmez. Karar banka uyum onayı anlamına gelmez.

## ADR-016 — Politika Kontrollü Sentetik Veri ve Bağımsız Ground Truth

**Bağlam:** Mevcut testler sentetik vaka kullanmaktadır; ancak üretim verisinin
gerçekçi fakat birebir olmayan temsili, kusur enjeksiyonu, ground truth,
tekrarlanabilirlik, gizlilik kapısı ve test olayı izolasyonu için ortak bir
sözleşme yoktur. Sentetik veriyi anonim kabul etmek veya skor motorunun kendi
çıktısını beklenen sonuç yapmak gizlilik ve self-validation riski doğurur.

**Karar:** Sentetik veri mevcut modüler monolitte sürümlü
`SyntheticDatasetPolicy` ile yönetilir. Temel üretim kusur enjeksiyonundan,
ground truth runtime kural/skor motorundan ve test olayları gerçek operasyon
hedeflerinden ayrılır. Aynı konfigürasyon, üretici sürümü ve random seed
deterministik çıktı üretir. Yapısal, istatistiksel, görev faydası, gizlilik ve
teknik doğrulamalar ayrı sonuçlardır. Sentetik veri anonimlik kanıtı değildir ve
`OPEN-014` kapsamındaki anonimleştirilmiş 20 milyon satırlık nihai performans
kabulünün yerine geçmez.

**Sonuç:** Kanonik hedef tasarım
[Sentetik Veri ve Gizlilik Stratejisi](Sentetik-Veri-ve-Gizlilik-Stratejisi.md),
gereksinimler `FR-088–FR-096`, kullanım senaryosu `UC-017` ve kabul senaryoları
`AC/TS-048–056` olur. Nicel fayda/gizlilik/skor toleransları ve üretim profilinden
öğrenme yöntemi varsayılan olarak kapalıdır; yalnız ayrı onaylı politika
sürümüyle açılabilir. Bu karar runtime
uygulaması, hukuki anonimlik veya banka onayı değildir.

## ADR-018 — Sürümlü Politika Kaydı Zorunluluğu

**Bağlam:** Kapasite, kaynak kullanımı, skor, yeterlilik, risk, sentetik
doğrulama ve operasyon değerleri önceki belgelerde karar bekleyen yer tutucular
olarak işaretlenmişti. Teknik yönler kullanıcı kararıyla kesinleştirilmiştir;
ortama göre değişen sayıları kod içinde sabitlemek doğru değildir.

**Karar:** Değişken sayısal değerler aktif, sürümlü ve gerekli onayı taşıyan
politika kaydından çözülür. Politika yoksa sistem örtük varsayılan kullanmaz;
sorgu/işlem reddedilir veya
olumlu yeterlilik, risk, kullanım ve sentetik doğrulama sonucu üretilmez.

**Sonuç:** Sürümlü politika zorunluluğu açık karar değil, uygulanması gereken
konfigürasyon ve operasyon kapısıdır. Teknik kararların `KararAlındı` olması
runtime uygulaması, kurumsal ürün kurulumu veya `ApprovedByBank` sonucu değildir.

## ADR-012 — Token Tabanlı Kurumsal Görsel Dil

**Bağlam:** Frontend modülleri için ortak tema, component ve durum dili yoktur.
Marka rengi ile kritik kalite ihlali, teknik hata veya operasyonel uyarının aynı
renkle anlatılması bankacılık operasyon ekranlarında yanlış yorum riski doğurur.

**Karar:** Tüm frontend semantik design token kullanacaktır. Ana marka rengi
`#FDB813`; koyu lacivert navigasyon ve açık içerik yüzeyi uygulama kabuğudur. Marka
rengi semantik durum rengi değildir. Kritik veri kalitesi ihlali kırmızı, teknik hata
mor, operasyonel uyarı turuncu, başarı yeşil, bilgi mavi ve veri yok gri gösterilir.
Renk her zaman ikon ve yazılı etiketle desteklenir.

**Sonuç:** Component dosyalarında ham görsel değerler yasaktır; açık/koyu tema aynı
semantik token sözleşmesini kullanır. Ayrıntılar
[Görsel Tasarım Sistemi](../04-Frontend/Gorsel-Tasarim-Sistemi.md) içindedir. Bu karar
frontend runtime veya component kütüphanesinin uygulandığı anlamına gelmez.

## ADR-013 — Storybook ve Playwright Görsel Doğrulaması

**Bağlam:** Ekranlar arası görsel tutarlılık, responsive davranış ve semantik durum
ayrımı yalnız kod incelemesiyle güvenilir biçimde doğrulanamaz.

**Karar:** İzole component durumları Storybook, ekran/akış ve screenshot doğrulaması
Playwright ile yapılacaktır. `1440×900`, `1280×800` ve `1024×768` zorunlu görsel
viewport'lardır; `NFR-USA-004` gereği `1366×768` ve `1920×1080` responsive kabul
görünümleri de korunur. Referans karşılaştırmasında en az iki belgeli iyileştirme
turu yapılır.

**Sonuç:** Frontend Definition of Done görsel ve erişilebilirlik kanıtı gerektirir.
Storybook ve Playwright seçimi kabul edilmiştir; kurulum 30F artımında yapılır.
Ayrıntılar
[Görsel Doğrulama Stratejisi](../06-Testler/03-Uctan-Uca/Gorsel-Dogrulama-Stratejisi.md)
içindedir.

Ayrıntılar: [Alınan Kararlar](../00-Proje-Hafizasi/Alinan-Kararlar.md) ve [Açık Konular](../01-SRS/15-Acik-Konular.md).

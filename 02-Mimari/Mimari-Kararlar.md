---
type: architecture-decision-log
project: Veri Kalitesi İzleme ve Skorlama Sistemi
status: seed
last_updated: 2026-07-20
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
| ADR-006 | Servis/workload identity ile kurumsal secret manager; depoda yalnız referans | Kabul edildi; ürün TBD |
| ADR-007 | LDAP destekli kurumsal IdP/SSO, OIDC veya SAML, zorunlu MFA ve RBAC | Kabul edildi; ürün/eşleme ayrıntıları TBD |
| ADR-008 | ServiceNow'un ara entegrasyon tablosu veya entegrasyon servisiyle çekirdek issue yönetiminden ayrılması | Kabul edildi |
| ADR-009 | Merkezi audit için hash zinciri, transactional outbox ve salt okunur/idempotent legacy aktarım | Teknik olarak doğrulandı; üretim ürünü ve operasyon onayı TBD |
| ADR-010 | Kişisel veri işleme envanterinin DataField'e bağlı değişmez sürümler ve redakte transactional audit ile tutulması | Teknik olarak doğrulandı; banka referans sözlükleri TBD |
| ADR-011 | Kritik kural aktivasyonunun sürümlü politika, güvenilir ActorContext ve RuleVersion'a bağlı atomik maker-checker kararıyla yapılması | 19A teknik olarak doğrulandı; scoring ve banka rol eşlemesi TBD |
| ADR-012 | Token tabanlı kurumsal görsel dil; marka rengi ile semantik durum renklerinin ayrılması | Tasarım baseline'ı kabul edildi; frontend uygulaması bekliyor |
| ADR-013 | Storybook component doğrulaması ve Playwright görsel regression süreci | Önerilen; toolchain/dependency onayı ve frontend uygulaması bekliyor |
| ADR-014 | OPEN-001–OPEN-018 karar paketinin kapasite, politika, güvenlik, yaşam döngüsü ve hibrit dağıtım sınırı | Kabul edildi; sayısal ve ürün bazlı TBD değerler korunuyor |
| ADR-015 | Açıklanabilir, sürümlü ve riskten ayrılmış veri kalitesi skorlama mimarisi (`DQ-SCR-001`–`DQ-SCR-033`) | Kabul edildi; mevcut uygulama farkları ve kurumsal değerler TBD |

## ADR-014 — Bağlayıcı Karar Paketi

Bu karar; düşük/beklenen/yüksek kapasite senaryolarını, kaynak bazlı kullanım politikasını, kayıt sınıfı bazlı saklama ile bileşen bazlı RPO/RTO'yu, kurumsal katalog/DLP sınıflandırmasını, katmanlı rapor saklamayı, risk bazlı maker-checker'ı, anonimleştirilmiş performans verisini, WCAG 2.2 AA hedefini, hibrit üretim dağıtımını, olay sınıfı bazlı audit davranışını ve dataset politikası kontrollü kısmi resmî skoru bağlayıcı kabul eder.

Belirli ürünler; kapasite, kota, timeout, saklama, dosya boyutu ve RPO/RTO değerleri ilgili kurumsal analiz veya onaya kadar TBD kalır. Teknik uygulama banka onayı anlamına gelmez.

## ADR-015 — Açıklanabilir ve Riskten Ayrılmış Skorlama

**Bağlam:** Mevcut teknik uygulama kural, boyut, dataset, kaynak ve kurum
agregasyonlarını üretmektedir; ancak kapsam ve ölçüm güveni ayrı sözleşme olarak
tam değildir. Kaynak skoru dataset kritiklik ağırlığını kalite agregasyonuna
katmaktadır. Bu davranış `DQ-SCR-018` ile çelişir. Mevcut durum kod tabanı için
gerçek bir uyarlama backlogudur; doküman güncellemesi uygulanmış runtime kanıtı
değildir.

**Karar:** `DQ-SCR-001`–`DQ-SCR-033` bağlayıcıdır. Ham kalite skoru kural → veri
öğesi → boyut → dataset hiyerarşisinde hesaplanır. Kapsam, güven, dataset
kritikliği, veri riski ve teknik sağlık ayrı çıktıdır. Kritik kural veto/tavanı
ağırlıklı ortalamadan bağımsızdır. Normalizasyon, eşik, ağırlık, güven ve kritik
kural davranışları sürümlü politikalardır. İstisna ve override süreli,
maker-checker kontrollü ve auditlidir; ham skoru değiştirmez. Skor ve replay
sonucu tüm model/politika/uygulama sürümlerini korur.

**Superseded karar:** Dataset kritikliğini `SOURCE` kalite skorunda ağırlık olarak
kullanan tarihsel teknik yaklaşım, hedef mimaride `DQ-SCR-018` ile
`Superseded` durumundadır. Geçmiş skorlar değiştirilmez; yeni modele geçiş
sürüm sınırı ve ayrı yeniden hesaplama kaydıyla yapılır.

**Sonuç:** Skorlama motoru, politika çözümleyici, risk/remediation ve teknik sağlık
sınırları ayrılır. API/UI kalite, kapsam, güven, risk/kritiklik ve teknik durumu
tek yüzdeye eritmez. Üretim eşikleri, ağırlıkları, veto/tavan davranışı, güven ve
risk katsayıları, dataset türleri ve `OPEN-BNK-013` kapsamı `TBD` kalır. Karar
banka uyum onayı anlamına gelmez.

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
Paket seçimi ve kurulumu ayrı onaylı frontend artımında yapılacaktır; bu ADR yeni
dependency eklemez. Ayrıntılar
[Görsel Doğrulama Stratejisi](../06-Testler/03-Uctan-Uca/Gorsel-Dogrulama-Stratejisi.md)
içindedir.

Ayrıntılar: [Alınan Kararlar](../00-Proje-Hafizasi/Alinan-Kararlar.md) ve [Açık Konular](../01-SRS/15-Acik-Konular.md).

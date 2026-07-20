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
| ADR-006 | Secret değerleri yerine secret manager referansı | Kabul edildi; ürün TBD |
| ADR-007 | LDAP adaptörü ve RBAC | Kabul edildi; eşleme ayrıntıları TBD |
| ADR-008 | ServiceNow adaptörünün çekirdek issue yönetiminden ayrılması | Önerilen |
| ADR-009 | Merkezi audit için hash zinciri, transactional outbox ve salt okunur/idempotent legacy aktarım | Teknik olarak doğrulandı; üretim ürünü ve operasyon onayı TBD |
| ADR-010 | Kişisel veri işleme envanterinin DataField'e bağlı değişmez sürümler ve redakte transactional audit ile tutulması | Teknik olarak doğrulandı; banka referans sözlükleri TBD |
| ADR-011 | Kritik kural aktivasyonunun sürümlü politika, güvenilir ActorContext ve RuleVersion'a bağlı atomik maker-checker kararıyla yapılması | 19A teknik olarak doğrulandı; scoring ve banka rol eşlemesi TBD |
| ADR-012 | Token tabanlı kurumsal görsel dil; marka rengi ile semantik durum renklerinin ayrılması | Tasarım baseline'ı kabul edildi; frontend uygulaması bekliyor |
| ADR-013 | Storybook component doğrulaması ve Playwright görsel regression süreci | Önerilen; toolchain/dependency onayı ve frontend uygulaması bekliyor |

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
[[04-Frontend/Gorsel-Tasarim-Sistemi|Görsel Tasarım Sistemi]] içindedir. Bu karar
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
[[06-Testler/03-Uctan-Uca/Gorsel-Dogrulama-Stratejisi|Görsel Doğrulama Stratejisi]]
içindedir.

Ayrıntılar: [[00-Proje-Hafizasi/Alinan-Kararlar|Alınan Kararlar]] ve [[01-SRS/15-Acik-Konular|Açık Konular]].

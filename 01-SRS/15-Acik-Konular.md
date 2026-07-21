---
type: srs-section
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "15"
created_at: 2026-07-16
tags:
  - srs
  - open-topic
---

# Açık Konular ve Varsayımlar

Bu bölüm, karar kayıtlarının durumunu uydurmadan görünür kılar. Hedef tarihler proje planı olmadığı için TBD bırakılmıştır. Aşağıdaki maddelerin karar yönü kesinleşmiştir; ürün adı, sayısal politika değeri veya banka onayı gerektiren alt değerler ilgili gereksinimlerde ayrıca TBD kalır.

| Konu ID | Açıklama | Kategori | Karar sahibi | Hedef karar tarihi | Etkilenen gereksinimler |
| --- | --- | --- | --- | --- | --- |
| OPEN-001 | Düşük, beklenen ve yüksek kapasite senaryoları; gerçek üretim envanteri geçiş kriteridir | Karara bağlandı | Proje Sponsoru / Veri Yönetişimi | TBD | NFR-SCL-003, NFR-PERF |
| OPEN-002 | Worker ve eş zamanlı sorgu sınırlarının kaynak bazlı, sürümlü politika tablosunda yönetilmesi | Karara bağlandı | Yazılım Mimari / DBA | TBD | FR-039, RULE-012, NFR-PERF-006 |
| OPEN-003 | Çalışma penceresi, CPU/IO, süre, kota ve yoğun saat davranışının aynı kaynak kullanım politikasında yönetilmesi | Karara bağlandı | DBA / Uygulama Sahibi | TBD | FR-031, FR-039, NFR-PERF-008 |
| OPEN-004 | Ürün bağımsız kurumsal secret manager ve servis/workload identity kullanılması | Karara bağlandı | Bilgi Güvenliği | TBD | FR-009, NFR-SEC-005 |
| OPEN-005 | LDAP destekli kurumsal IdP/SSO üzerinden OIDC veya SAML; yönetilebilir grup-rol eşleme | Karara bağlandı | Kimlik Yönetimi Ekibi | TBD | FR-001, FR-003, NFR-AVL |
| OPEN-006 | İlk fazdan itibaren tüm kullanıcılar için kurumsal IdP üzerinden SSO ve MFA zorunluluğu | Karara bağlandı | Bilgi Güvenliği | TBD | NFR-SEC-002 |
| OPEN-007 | Kayıt sınıfı bazlı saklama ve imha matrisi; kesin süreler onaylanana kadar TBD | Karara bağlandı | Hukuk / Bilgi Güvenliği / İç Denetim | TBD | RULE-014, Bölüm 7.3 |
| OPEN-008 | Bileşen bazlı RPO/RTO matrisi; kesin hedefler iş etki analizine kadar TBD | Karara bağlandı | İş Sürekliliği / Proje Sponsoru | TBD | NFR-DR-002, NFR-DR-003 |
| OPEN-009 | ServiceNow entegrasyonunun ara tablo veya entegrasyon servisi üzerinden dayanıklı ve idempotent yürütülmesi | Karara bağlandı | ServiceNow Yöneticisi | TBD | FR-071, FR-087 |
| OPEN-010 | Sınıflandırmanın kurumsal veri kataloğu veya DLP sisteminden alınması ve kesintide güvenli varsayılan uygulanması | Karara bağlandı | KVKK / Bilgi Güvenliği / Veri Yönetişimi | TBD | RULE-010, NFR-PRV, FR-086 |
| OPEN-011 | Rapor dosyası, metadata, arşiv ve imha kaydının ayrı katmanlarda politika ile yönetilmesi | Karara bağlandı | İç Denetim / Sistem Yöneticisi | TBD | FR-075, FR-076, Bölüm 7.3 |
| OPEN-012 | Dört göz ilkesinin yalnız tanımlı yüksek riskli değişikliklerde zorunlu olması | Karara bağlandı | Veri Yönetişimi Kurulu | TBD | FR-035, RULE-005 |
| OPEN-013 | Bağlayıcı sırası: yaygın ilişkisel veritabanı, dosya/CSV, ikinci ilişkisel ürün, API | Karara bağlandı | Yusuf İpek | TBD | MVP; FR-007–FR-011 |
| OPEN-014 | 20 milyon satırlık testin onaylı ve anonimleştirilmiş üretim örneğiyle yapılması | Karara bağlandı | Yusuf İpek / DBA | TBD | AC-008, NFR-PERF-005 |
| OPEN-015 | WCAG 2.2 AA hedefi ve otomatik teste ek manuel klavye/ekran okuyucu doğrulaması | Karara bağlandı | Kurumsal UX / Bilgi Teknolojileri | TBD | NFR-USA-006 |
| OPEN-016 | Stateless API ve worker'ların kurumsal konteyner platformunda, veritabanının ayrı yüksek erişilebilirlik kümesinde çalıştığı hibrit mimari | Karara bağlandı | BT Mimari Kurulu | TBD | Bölüm 2.2, NFR-SCL, NFR-AVL |
| OPEN-017 | Kritik işlem sınıflarında fail-closed; rutin olaylarda dayanıklı kuyruk/transactional outbox | Karara bağlandı | Bilgi Güvenliği / Mimari Kurul | TBD | FR-077, NFR-SEC-011 |
| OPEN-018 | Dataset bazlı sürümlü politika sağlanırsa kısmi sonucun resmî skora alınması; aksi halde provizyonel davranış | Karara bağlandı | Veri Yönetişimi Kurulu | TBD | FR-048, RULE-004 |

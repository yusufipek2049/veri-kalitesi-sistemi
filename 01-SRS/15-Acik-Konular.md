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
| OPEN-019 | `DQ-SCR-013`–`DQ-SCR-021` için üretim normalizasyonları, eşik/ağırlık değerleri, kritik veto/tavan davranışları, kapsam/güven ve veri risk formülleri | Açık | Veri Yönetişimi / Risk Yönetimi / İç Kontrol | TBD | FR-047–FR-052, AC-030–AC-032; OPEN-BNK-004/013 |
| OPEN-020 | Dataset türü ile isteğe bağlı veri ürünü/rapor/veri alanı hiyerarşisinin kurumsal sözlüğü ve `OPEN-BNK-013` düzenleyici kapsam kararı | Açık | Veri Yönetişimi / Risk Yönetimi | TBD | FR-050, DQ-SCR-002/003/018/019 |
| OPEN-021 | İstisna ve ham skordan ayrı değerlendirme/override için banka rol matrisi, izinli türler, azami süre, risk kabulü ve raporlama politikası | Açık | Veri Yönetişimi / İç Kontrol / Bilgi Güvenliği | TBD | FR-035, FR-077, DQ-SCR-022/023/030; OPEN-BNK-004/005/006/008 |
| OPEN-022 | Mevcut fiziksel skor durumlarının standart ölçüm durumlarına eşlenmesi ve dataset kritiklik ağırlıklı `SOURCE` skorundan ayrı kritiklik/risk modeline geçiş planı | Açık | Mimari / Veri Yönetişimi / Operasyon | TBD | FR-048–FR-052, ADR-015, DQ-SCR-005/006/018/025/032 |

## DQ-SCR Kararlarının Bankacılık Açık Konularıyla İlişkisi

`DQ-SCR` kararlarının kabulü aşağıdaki `OPEN-BNK` kayıtlarını otomatik olarak
kapatmaz. Bu ilişkiler banka kararı, kurumsal politika veya üretim kanıtı gereken
bağımlılıkları gösterir.

| DQ-SCR kararları | İlişkili OPEN-BNK kayıtları | Açık kalan karar alanı |
| --- | --- | --- |
| DQ-SCR-003, DQ-SCR-015, DQ-SCR-018, DQ-SCR-019 | OPEN-BNK-013 | Düzenleyici raporlama/risk zinciri kapsamı ve kurumsal veri hiyerarşisi |
| DQ-SCR-005, DQ-SCR-023, DQ-SCR-030, DQ-SCR-032 | OPEN-BNK-005, OPEN-BNK-006, OPEN-BNK-016 | Kritik işlem auditi, bütünlük, kalıcı outbox ve yeniden oynatma altyapısı |
| DQ-SCR-014, DQ-SCR-015, DQ-SCR-017, DQ-SCR-022, DQ-SCR-023, DQ-SCR-030 | OPEN-BNK-004 | Skorlama politikası, istisna ve override için maker-checker kapsamı ve banka rolleri |
| DQ-SCR-014, DQ-SCR-015 | OPEN-BNK-007 | Kurumsal sınıflandırma ve hassasiyet bağlamına göre politika seçimi |
| DQ-SCR-022, DQ-SCR-032 | OPEN-BNK-008 | İstisna, override ve yeniden hesaplama kayıtlarının saklama/imha politikası |
| DQ-SCR-028 | OPEN-BNK-010 | Skor alarmı olay sözlüğü, seviye ve SOC eskalasyon akışı |
| DQ-SCR-026 | OPEN-BNK-014 | Skor ve eğilim dışa aktarımlarında DLP, gerekçe, onay ve watermark politikası |
| DQ-SCR-012, DQ-SCR-028, DQ-SCR-029, DQ-SCR-031 | OPEN-BNK-017 | Zaman bağımlı politika/onay işlemlerinin süre aşımı ve politika sahipliği |
| DQ-SCR-031 | OPEN-BNK-011, OPEN-BNK-012 | Yeniden üretilebilirlik için yedekleme hedefleri ve üretim platformu |
| DQ-SCR-033 | OPEN-BNK-001, OPEN-BNK-004, OPEN-BNK-013 | Yönetişim modelinin uyum, iç kontrol ve risk kapsamı onayı |

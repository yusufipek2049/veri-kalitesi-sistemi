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

Bu bölüm, kesinleştirilmemiş kararları uydurmadan görünür kılar. Hedef tarihler proje planı olmadığı için çoğunlukla TBD bırakılmıştır.

| Konu ID | Açıklama | Kategori | Karar sahibi | Hedef karar tarihi | Etkilenen gereksinimler |
| --- | --- | --- | --- | --- | --- |
| OPEN-001 | Üretim ortamındaki kesin kaynak, veri kümesi, alan ve aktif kural sayısı | Varsayım | Proje Sponsoru / Veri Yönetişimi | TBD | NFR-SCL-003, NFR-PERF |
| OPEN-002 | Üretim worker sayısı ve kaynak bazlı eş zamanlı sorgu kotası | Teknik karar gerekli | Yazılım Mimari / DBA | TBD | FR-039, RULE-012, NFR-PERF-006 |
| OPEN-003 | Kaynak sistemlerde izin verilen CPU/IO ve çalışma penceresi | İş birimi kararı gerekli | DBA / Uygulama Sahibi | TBD | FR-031, FR-039, NFR-PERF-008 |
| OPEN-004 | Kurumsal secret manager ürünü ve erişim modeli | Güvenlik onayı gerekli | Bilgi Güvenliği | TBD | FR-009, NFR-SEC-005 |
| OPEN-005 | LDAP şema, grup-rol eşleme ve yüksek erişilebilirlik ayrıntıları | Teknik karar gerekli | Kimlik Yönetimi Ekibi | TBD | FR-001, FR-003, NFR-AVL |
| OPEN-006 | MFA/SSO'nun ilk fazda zorunlu olup olmayacağı | Güvenlik onayı gerekli | Bilgi Güvenliği | TBD | NFR-SEC-002 |
| OPEN-007 | Beş yıllık saklama süresinin tüm kayıt türleri için hukuki ve kurumsal onayı | Güvenlik onayı gerekli | Hukuk / Bilgi Güvenliği / İç Denetim | TBD | RULE-014, Bölüm 7.3 |
| OPEN-008 | RPO/RTO nihai değerleri | İş birimi kararı gerekli | İş Sürekliliği / Proje Sponsoru | TBD | NFR-DR-002, NFR-DR-003 |
| OPEN-009 | ServiceNow tablo, alan, durum eşleme ve servis hesabı | Teknik karar gerekli | ServiceNow Yöneticisi | TBD | FR-071, FR-087 |
| OPEN-010 | Hassas veri sınıflandırma sözlüğü ve maskeleme algoritmaları | Güvenlik onayı gerekli | KVKK / Bilgi Güvenliği / Veri Yönetişimi | TBD | RULE-010, NFR-PRV |
| OPEN-011 | Rapor dosyalarının çevrimiçi saklama süresi ve maksimum boyutu | İş birimi kararı gerekli | İç Denetim / Sistem Yöneticisi | TBD | FR-075, FR-076, Bölüm 7.3 |
| OPEN-012 | Kural ve eşik onay akışında dört göz ilkesinin zorunluluğu | İş birimi kararı gerekli | Veri Yönetişimi Kurulu | TBD | FR-035, RULE-005 |
| OPEN-013 | Yerel prototipte ilk uygulanacak bağlayıcıların sırası | Teknik karar gerekli | Yusuf İpek | TBD | MVP; FR-007–FR-011 |
| OPEN-014 | 20 milyon satırlık referans performans testinde kullanılacak anonim/sentetik veri seti | Teknik karar gerekli | Yusuf İpek / DBA | TBD | AC-008, NFR-PERF-005 |
| OPEN-015 | WCAG hedefinin kurumsal zorunluluk seviyesi | İş birimi kararı gerekli | Kurumsal UX / Bilgi Teknolojileri | TBD | NFR-USA-006 |
| OPEN-016 | Üretim dağıtım platformu, konteyner orkestrasyonu ve veri tabanı ürünü | Teknik karar gerekli | BT Mimari Kurulu | TBD | Bölüm 2.2, NFR-SCL, NFR-AVL |
| OPEN-017 | Audit fail-closed veya dayanıklı kuyruk davranışı | Güvenlik onayı gerekli | Bilgi Güvenliği / Mimari Kurul | TBD | FR-077, NFR-SEC-011 |
| OPEN-018 | Kısmi çalıştırmaların hangi durumlarda resmi skora katılabileceği | İş birimi kararı gerekli | Veri Yönetişimi Kurulu | TBD | FR-048, RULE-004 |

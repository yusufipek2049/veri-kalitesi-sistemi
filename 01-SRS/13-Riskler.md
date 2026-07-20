---
type: srs-section
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "13"
created_at: 2026-07-16
tags:
  - srs
  - risk
---

# Riskler

Bu bölüm, proje ve işletim risklerini, önleyici/düzeltici faaliyetleri ve sahipleri tanımlar.

| Risk ID | Risk açıklaması | Olasılık | Etki | Risk seviyesi | Önleyici faaliyet | Düzeltici faaliyet | Risk sahibi |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | Kaynak sistem performansının kalite sorgularından etkilenmesi | Orta | Yüksek | Yüksek | Kaynak kotası, çalışma penceresi, sorgu planı, örnekleme, timeout ve DBA onayı | İşi iptal et; kotayı düşür; örneklem/bölüm kullan; sorguyu optimize et | Veri Mühendisi / DBA |
| RISK-002 | Hatalı tanımlanan kalite kurallarının yanlış alarm üretmesi | Yüksek | Yüksek | Kritik | Şablon, test çalıştırması, onay akışı, kural sahibi ve sürümleme | Kuralı pasife al; yanlış sonuçları işaretle; düzeltip yeni sürüm yayımla | Veri Kalitesi Uzmanı |
| RISK-003 | Data Owner ve Data Steward atanmaması | Orta | Yüksek | Yüksek | Kritik kaynak aktivasyonunda sahip zorunluluğu; yönetişim matrisi | Varsayılan yönetişim kuyruğuna ata; yönetim eskalasyonu | Veri Yönetişimi Yöneticisi |
| RISK-004 | Kişisel verilerin profil, log veya raporda açığa çıkması | Orta | Çok Yüksek | Kritik | Sınıflandırma, maskeleme, veri minimizasyonu, güvenli log, dışa aktarma izni | Erişimi kes; olayı güvenliğe bildir; veriyi temizle/anonimleştir; kök neden analizi | Bilgi Güvenliği / KVKK |
| RISK-005 | Veri kaynaklarına ağ veya yetki erişimi sağlanamaması | Yüksek | Orta | Yüksek | Erken bağlantı matrisi, servis hesabı, güvenlik duvarı talepleri, bağlantı testi | Mock/anonim veriyle geliştirme; erişim bekleyen kaynağı fazlandırma | Proje Yöneticisi / Sistem Yöneticisi |
| RISK-006 | 20 milyon+ satır veri hacminde yerel bilgisayar kapasitesinin aşılması | Yüksek | Yüksek | Kritik | Kaynakta aggregate, örnekleme, bölümleme, streaming okuma, bellek limiti, performans bütçesi | Kapsamı küçült; sentetik bölüm kullan; üretim benchmarkını ayrı ortamda yap | Yazılım Mimari / Yusuf İpek |
| RISK-007 | Yanlış skor ağırlıklarıyla yanıltıcı kurumsal skor | Orta | Yüksek | Yüksek | Ağırlık sürümleme, veri yönetişimi onayı, duyarlılık analizi, açıklanabilir skor | Yeni konfigürasyon sürümü yayımla; geçmişi yeniden yazmadan karşılaştırmalı yeniden hesapla | Veri Yönetişimi Kurulu |
| RISK-008 | Bildirim yorgunluğu | Yüksek | Orta | Yüksek | Deduplication, susturma, tekrar penceresi, kritik bazlı eskalasyon | Eşikleri ve alıcıları gözden geçir; toplu özet görünümü oluştur | Data Steward |
| RISK-009 | Eski metadata nedeniyle kuralların yanlış nesneye uygulanması | Orta | Yüksek | Yüksek | Periyodik metadata taraması, değişiklik algılama, son tarama göstergesi | Etkilenen kuralları inceleme gerekli durumuna al; yeniden keşif yap | Veri Mühendisi |
| RISK-010 | Kaynak şema değişikliklerinin çalıştırmaları bozması | Yüksek | Yüksek | Kritik | Şema diff, bağımlılık grafiği, ön koşul kontrolü, sürümleme | İşi teknik hata olarak kapat; kuralı pasife/incelemeye al; yeni sürüm oluştur | Veri Mühendisi / Data Steward |
| RISK-011 | Yetersiz kullanıcı katılımı ve kuralların sahiplenilmemesi | Orta | Yüksek | Yüksek | Pilot birim, eğitim, rol tanımı, dashboard KPI ve issue SLA | Yönetim sponsorluğu; kapsamı kritik veri kümelerine daralt; sorumlulukları yeniden ata | Proje Sponsoru |
| RISK-012 | Teknik hata ile veri hatasının karıştırılması | Orta | Çok Yüksek | Kritik | Ayrı durum kodları, UI etiketleri, skor dışlama ve teknik bildirim | Yanlış skor/issue'ları işaretle; sınıflandırmayı düzelt; etkilenen skorları yeni sürümde hesapla | Veri Kalitesi Uzmanı / Sistem Yöneticisi |
| RISK-013 | ServiceNow entegrasyonunda duplicate veya durum uyumsuzluğu | Orta | Orta | Orta | Idempotency, durum eşleme tablosu, retry ve entegrasyon geçmişi | Manuel mutabakat; duplicate ticket birleştirme; senkronizasyonu geçici durdurma | Entegrasyon Sorumlusu |
| RISK-014 | Beş yıllık geçmişin depolama ve sorgu maliyetini artırması | Orta | Orta | Orta | Bölümleme, arşiv katmanı, özet tablolar, kapasite tahmini | Eski ayrıntıyı arşive taşı; çevrimiçi özetleri koru | Sistem Yöneticisi / DBA |
| RISK-015 | LDAP kesintisinin kullanıcı erişimini durdurması | Düşük-Orta | Yüksek | Yüksek | LDAP HA, timeout, sağlık kontrolü, güvenlik onaylı break-glass prosedürü | LDAP ekibi eskalasyonu; süreli acil durum hesabı; yazma işlemlerini kısıtlama | Kimlik Yönetimi Ekibi |

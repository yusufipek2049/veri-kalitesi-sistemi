---
type: srs-section
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "3"
created_at: 2026-07-16
tags:
  - srs
  - bolum-3
---

# İş Gereksinimleri

Bu bölüm, sistemin sağlaması gereken kurumsal sonuçları ve başarı ölçütlerini tanımlar.

| Gereksinim ID | Gereksinim adı | Açıklama | İş gerekçesi | İş sahibi | Öncelik | Başarı ölçütü | Bağımlılıklar |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BR-001 | Merkezi veri kalitesi görünürlüğü | Kurum genelindeki veri kalite sonuçları tek platformda izlenmelidir. | Dağınık kontrollerin ortak görünümde birleştirilmesi | Veri Yönetişimi Yöneticisi | Must | MVP kapsamındaki veri kaynaklarının en az %90'ı tek dashboardda görünür olmalıdır. | Veri kaynaklarının tanımlanması |
| BR-002 | Kritik veri kümelerinin izlenmesi | Kritik olarak işaretlenen veri kümeleri düzenli kalite kontrollerine tabi tutulmalıdır. | İş sürekliliği ve mevzuat riskinin azaltılması | Data Owner | Must | Kritik veri kümelerinin %100'ünde en az bir aktif kural ve tanımlı çalışma planı bulunmalıdır. | Sahiplik ve kritiklik ataması |
| BR-003 | Erken problem tespiti | Kalite bozulmaları tanımlı eşik ve trend koşullarında otomatik tespit edilmelidir. | Hataların rapor ve süreçlere yansımadan bulunması | Veri Kalitesi Yöneticisi | Must | Eşik ihlallerinin en geç ilgili çalıştırma tamamlandıktan sonra 5 dakika içinde olay olarak kaydedilmesi. | Skorlama ve bildirim |
| BR-004 | Sorumluların bilgilendirilmesi | Kalite sorunları ilgili Data Owner ve Data Steward'a sistem içi bildirimle iletilmelidir. | Sorunların sahiplenilmesi | Veri Yönetişimi Yöneticisi | Must | Kritik sorunların en az %99'unda geçerli alıcıya bildirim kaydı oluşması. | Sahiplik metadatası |
| BR-005 | Ortak ölçüm yaklaşımı | Birimler ortak kalite boyutları, formüller ve eşiklerle ölçüm yapmalıdır. | Karşılaştırılabilirlik ve yönetişim | Veri Yönetişimi Kurulu | Must | Onaylı kural şablonlarının ve skor formülünün tüm birimlerde aynı sürümle uygulanması. | Kural ve skor yönetimi |
| BR-006 | Tarihsel değişim takibi | Skor ve kural sonuçları zaman içinde karşılaştırılabilmelidir. | İyileşme veya kötüleşmenin ölçülmesi | Data Owner | Must | En az beş yıllık sonuç geçmişi üzerinden dönemsel trend alınabilmesi. | Saklama politikası |
| BR-007 | Denetim kanıtı üretimi | Kural, yetki, skor, sorun ve rapor işlemleri denetlenebilir kayıtlarla desteklenmelidir. | İç/dış denetim gereksinimi | İç Denetim | Must | Kritik değişikliklerin %100'ünde kullanıcı, zaman, eski/yeni değer ve işlem sonucu kayıtlı olmalıdır. | Audit altyapısı |
| BR-008 | İyileştirme etkisinin ölçülmesi | Sorun çözüm faaliyetlerinin skor ve hata oranına etkisi izlenmelidir. | Kaynakların doğru iyileştirme alanlarına yönlendirilmesi | Data Steward | Should | Kapalı sorunların en az %90'ında çözüm öncesi ve sonrası skor karşılaştırması yapılabilmesi. | Sorun ve skor geçmişi |

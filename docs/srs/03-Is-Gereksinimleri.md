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
| BR-006 | Tarihsel değişim takibi | Skor ve kural sonuçları zaman içinde karşılaştırılabilmelidir. | İyileşme veya kötüleşmenin ölçülmesi | Data Owner | Must | Kayıt sınıfı bazlı saklama politikası kapsamında mevcut resmî sonuçlardan dönemsel trend alınabilmesi; provizyonel sonuçların resmî trende katılmaması. | Saklama ve kısmi skor politikası |
| BR-007 | Denetim kanıtı üretimi | Kural, yetki, skor, sorun ve rapor işlemleri denetlenebilir kayıtlarla desteklenmelidir. | İç/dış denetim gereksinimi | İç Denetim | Must | Kritik değişikliklerin %100'ünde kullanıcı, zaman, eski/yeni değer ve işlem sonucu kayıtlı olmalıdır. | Audit altyapısı |
| BR-008 | İyileştirme etkisinin ölçülmesi | Sorun çözüm faaliyetlerinin skor ve hata oranına etkisi izlenmelidir. | Kaynakların doğru iyileştirme alanlarına yönlendirilmesi | Data Steward | Should | Kapalı sorunların en az %90'ında çözüm öncesi ve sonrası skor karşılaştırması yapılabilmesi. | Sorun ve skor geçmişi |
| BR-009 | Kullanım amacına uygunluk kararı | Veri kalitesi sonucu, genel bir yüzde yerine belirli kullanım amacı, ölçüm yeterliliği ve onaylı politika bağlamında karar girdisi olmalıdır. | Aynı verinin farklı iş/risk bağlamlarında yanlış biçimde eşdeğer kabul edilmesini önlemek | Data Owner / Veri Yönetişimi | Should — ikinci faz | Her kullanım kararının profil, formül, eşik/ağırlık, kritik kontrol ve kanıt sürümüne bağlanabilmesi. | FR-097–FR-100; OPEN-026/027 karar kaydı |
| BR-010 | Kanıtlı ve yeniden üretilebilir karar | Skor, teşhis, öneri ve değişiklik etkisi kaynakları, manifesti, lineage'ı ve ayrı güven değerleriyle açıklanabilmelidir. | Kararın denetlenebilir, doğrulanabilir ve tekrar üretilebilir olması | Veri Yönetişimi / İç Denetim | Should — ikinci faz | Karar verilebilir sonuçların kanıt bağlantısı taşıması; eksik kanıtın görünür ve replay'in orijinali koruyan ayrı sonuç olması. | FR-098–FR-104, FR-111 |
| BR-011 | Politika kontrollü iyileştirme ve kontrol yeterliliği | Öneri, remediation, data contract, adaptif tarama ve chaos deneyi yetki/politika/onay/rollback sınırında yönetilmelidir. | İyileştirmenin yeni veri, operasyon ve güvenlik riski üretmesini önlemek | Veri Yönetişimi / Bilgi Güvenliği / Operasyon | Could — ikinci faz | Üretim verisine yazma olmaması; onaysız otomasyon ve izole olmayan chaos deneylerinin %100 reddedilmesi. | FR-105–FR-110; OPEN-030–OPEN-035 karar kaydı |

---
type: srs-section
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "14"
generated_at: 2026-07-16
tags:
  - srs
  - evolution
---

# Sistem Evrimi

Bu bölüm, MVP sonrasında sistemin kontrollü biçimde genişletilebileceği yönleri tanımlar.

| Gelişim alanı | Açıklama |
| --- | --- |
| Makine öğrenmesiyle anomali tespiti | Tarihsel dağılım ve zaman serilerinden olağandışı değişimleri belirleme. Model çıktısı deterministik kurallardan ayrı etiketlenmeli ve açıklanabilir olmalıdır. |
| Otomatik kural önerisi | Profil, metadata ve geçmiş hata desenlerinden kural taslağı önerme; insan onayı olmadan aktif edilmemelidir. |
| Veri lineage entegrasyonu | Kaynak-hedef bağımlılıklarını kullanarak kalite sorununun aşağı/yukarı akış etkisini göstermek. |
| Bulut veri platformu bağlantıları | Kurumsal stratejiye göre Snowflake, BigQuery, Redshift, Databricks veya bulut nesne depoları için yeni bağlayıcılar. |
| Gerçek zamanlı kalite kontrolü | Olay bazlı veya düşük gecikmeli kontroller; batch skorlarından ayrı SLA ve pencere semantiği. |
| Streaming veri desteği | Kafka veya kurumun streaming altyapısında pencere, watermark, geç gelen veri ve tekrar semantiği. |
| Doğal dil ile kural tanımlama | Türkçe iş ifadesinden kural taslağı üretme; SQL/iş planı önizlemesi ve zorunlu insan testi/onayı. |
| Otomatik kök neden analizi | Lineage, şema değişikliği, dağılım ve iş geçmişini ilişkilendirerek kök neden adayı sunma; kesin karar olarak gösterilmemeli. |
| Veri ürünü bazlı kalite skoru | Data product SLO, sahiplik, sözleşme ve tüketici etkisini skor hiyerarşisine ekleme. |
| Kurumsal veri kalitesi olgunluk ölçümü | Kural kapsamı, sahiplik, issue çözüm süresi, trend ve denetim bulgularından olgunluk göstergeleri üretme. |


Mimari evrim için bağlayıcı, kural yürütme ve skorlama sözleşmeleri geriye uyumlu versiyonlanmalıdır. ML/LLM tabanlı bileşenler deterministik sistem kayıtlarını değiştirmemeli; öneri üretmeli ve insan onayıyla devreye alınmalıdır. Streaming ve gerçek zamanlı kontrol, batch sonuçlarıyla aynı skor dönemine katılmadan önce pencere ve ağırlık politikası açısından ayrıca tasarlanmalıdır.

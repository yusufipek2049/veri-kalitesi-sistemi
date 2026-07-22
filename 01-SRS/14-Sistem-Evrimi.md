---
type: srs-section
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "14"
created_at: 2026-07-16
tags:
  - srs
  - evolution
---

# Sistem Evrimi

Bu bölüm, MVP sonrasında sistemin kontrollü biçimde genişletilebileceği yönleri tanımlar.

| Gelişim alanı | Açıklama |
| --- | --- |
| Makine öğrenmesiyle anomali tespiti | Tarihsel dağılım ve zaman serilerinden olağandışı değişimleri belirleme. Model çıktısı deterministik kurallardan ayrı etiketlenmeli ve açıklanabilir olmalıdır. |
| Kanıtlı öneri ve remediation | `FR-104/105`; mekanizma, dayanak, güven ve risk bağlı öneri. `OPEN-030` kapanmadan yalnız `SuggestOnly`; kaynak üretim verisi değiştirilemez. |
| Veri lineage ve değişiklik etkisi | `FR-101–FR-103`; kaynaklı tablo/kolon/dönüşüm ilişkileri, ayrı drift türleri ve dry-run blast radius. Sistem-of-record `OPEN-028` kapsamındadır. |
| Bulut veri platformu bağlantıları | Kurumsal stratejiye göre Snowflake, BigQuery, Redshift, Databricks veya bulut nesne depoları için yeni bağlayıcılar. |
| Gerçek zamanlı kalite kontrolü | Olay bazlı veya düşük gecikmeli kontroller; batch skorlarından ayrı SLA ve pencere semantiği. |
| Streaming veri desteği | Kafka veya kurumun streaming altyapısında pencere, watermark, geç gelen veri ve tekrar semantiği. |
| Doğal dil ile kural tanımlama | Türkçe iş ifadesinden kural taslağı üretme; SQL/iş planı önizlemesi ve zorunlu insan testi/onayı. |
| Kanıtlı teşhis | `FR-103`; lineage, şema/deploy/politika ve ölçüm olaylarından hipotez üretme; korelasyonu doğrulanmış neden olarak sunmama. |
| Veri ürünü bazlı kalite skoru | Data product SLO, sahiplik, sözleşme ve tüketici etkisini skor hiyerarşisine ekleme. |
| Kurumsal veri kalitesi olgunluk ölçümü | Kural kapsamı, sahiplik, issue çözüm süresi, trend ve denetim bulgularından olgunluk göstergeleri üretme. |
| Kullanım amacı ve kanıtlı karar desteği | `FR-097–FR-111`; uygunluk profili, etki, manifest/reproduction, data contract, kalite borcu, privacy-preserving inspection, chaos ve kanıt paketi. |


Mimari evrim için bağlayıcı, kural yürütme ve skorlama sözleşmeleri geriye uyumlu versiyonlanmalıdır. ML/LLM tabanlı bileşenler deterministik sistem kayıtlarını değiştirmemeli; yalnız mekanizma/sürüm/kanıt/güven bağlı öneri üretmeli ve gerekli insan onayıyla devreye alınmalıdır. Streaming ve gerçek zamanlı kontrol, batch sonuçlarıyla aynı skor dönemine katılmadan önce pencere ve ağırlık politikası açısından ayrıca tasarlanmalıdır. Kanıta dayalı ikinci fazın tek ana kaynağı [kanonik mimari](../02-Mimari/Kanita-Dayali-Karar-Sistemi.md) belgesidir.

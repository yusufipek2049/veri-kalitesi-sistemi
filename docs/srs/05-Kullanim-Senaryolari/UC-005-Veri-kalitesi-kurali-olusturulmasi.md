---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-005"
created_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-005
---

# UC-005 — Veri kalitesi kuralı oluşturulması

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-005** |
| Kullanım Senaryosu Adı | Veri kalitesi kuralı oluşturulması |
| Amaç | Test edilebilir ve sahipliği belirli kalite kontrolü tanımlamak. |
| Kısa Açıklama | Yetkili uzman şablon veya özel SQL ile kural taslağı oluşturur. |
| Birincil Aktör | Veri Kalitesi Uzmanı |
| İkincil Aktörler | Data Owner; Veri Mühendisi |
| Öncelik | Must |
| Tetikleyici | Kullanıcının “Yeni Kural” işlemini seçmesi. |
| Ön Koşullar | Metadata mevcut; kullanıcı ilgili veri alanında kural oluşturma yetkisine sahip olmalıdır. |

**Temel Akış**

1. Kullanıcı kural türü veya şablon seçer.
2. Sistem uygun parametreleri ve hedef alanları gösterir.
3. Kullanıcı açıklama, boyut, kapsam, eşik, ağırlık, kritiklik ve sahip bilgilerini girer.
4. Sistem veri tipi, nesne, aralık ve yetki doğrulaması yapar.
5. Kural taslak sürüm olarak kaydedilir.
6. Kullanıcı test çalıştırmasına yönlendirilir.
7. Kritik kural için onay süreci başlatılır.

**Alternatif Akışlar**

1. Kullanıcı özel SQL seçerse sistem salt okunur sözdizimi ve maliyet kontrolleri uygular.
2. Bir kural birden çok kalite boyutuna atanabilir; birincil boyut zorunlu tutulabilir.

**İstisna Akışları**

1. Silinmiş alan, geçersiz regex, negatif ağırlık veya 0–100 dışı eşik reddedilir.
2. DML/DDL içeren SQL reddedilir.
3. Sahibi olmayan kritik kural aktifleştirilemez.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-001, RULE-002, RULE-005, RULE-007 |
| Son Koşullar | Yeni QualityRule ve RuleVersion taslağı oluşur. |
| Başarı Garantisi | Kural benzersiz sürüm, sahip, kapsam ve ölçülebilir eşikle kaydedilir. |
| Minimum Garanti | Hatalı kural aktif hale gelmez; önceki sürüm değişmez. |
| İlgili Fonksiyonel Gereksinimler | FR-023–FR-030, FR-032–FR-035 |
| Kabul Kriterleri | Kural taslağı tüm zorunlu alanları ve geçerli referansları içermeden yayınlanamamalıdır. |

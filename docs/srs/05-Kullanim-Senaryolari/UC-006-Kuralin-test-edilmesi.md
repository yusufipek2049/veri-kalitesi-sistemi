---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-006"
created_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-006
---

# UC-006 — Kuralın test edilmesi

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-006** |
| Kullanım Senaryosu Adı | Kuralın test edilmesi |
| Amaç | Kural mantığını resmi skora etki etmeden doğrulamak. |
| Kısa Açıklama | Kural sınırlı kayıt veya bölüm üzerinde kontrollü test çalıştırmasına alınır. |
| Birincil Aktör | Veri Kalitesi Uzmanı |
| İkincil Aktörler | Veri Mühendisi; Harici Veri Kaynağı |
| Öncelik | Must |
| Tetikleyici | Kullanıcının kural taslağında “Test Et” seçmesi. |
| Ön Koşullar | Kural taslağı ve test edilmiş kaynak bağlantısı bulunmalıdır. |

**Temel Akış**

1. Kullanıcı örneklem, satır limiti veya tarih bölümünü seçer.
2. Sistem yürütme planı ve tahmini maliyeti gösterir.
3. Kullanıcı testi başlatır.
4. Sistem kuralı salt okunur olarak çalıştırır.
5. Toplam, başarılı, hatalı ve değerlendirilemeyen sayılar hesaplanır.
6. Maskeli hata örnekleri ve süre gösterilir.
7. Test sonucu kural sürümüne bağlanır; resmi skora dahil edilmez.

**Alternatif Akışlar**

1. Kullanıcı yalnız sorgu planını önizleyebilir.
2. Başarılı test sonrası kritik olmayan kural doğrudan aktivasyona alınabilir.

**İstisna Akışları**

1. Timeout, SQL, bağlantı veya şema hatası teknik hata olarak gösterilir.
2. Kişisel veri maskeleme uygulanamıyorsa örnek kayıtlar gösterilmez.
3. Maliyet eşiği aşılırsa test başlatılmaz ve kapsam daraltma istenir.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-002, RULE-003, RULE-010 |
| Son Koşullar | Test sonucu ve audit kaydı oluşur. |
| Başarı Garantisi | Kuralın beklenen sayaç ve hata örnekleri doğrulanabilir. |
| Minimum Garanti | Test başarısızsa kural aktif edilmez; kaynak veri değişmez. |
| İlgili Fonksiyonel Gereksinimler | FR-024, FR-031–FR-034, FR-040 |
| Kabul Kriterleri | Varsayılan 10.000 kayıt sınırında test sonucu resmi skordan ayrı saklanmalıdır. |

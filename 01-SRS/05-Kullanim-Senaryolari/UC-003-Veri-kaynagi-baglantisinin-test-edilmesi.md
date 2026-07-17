---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-003"
generated_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-003
---

# UC-003 — Veri kaynağı bağlantısının test edilmesi

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-003** |
| Kullanım Senaryosu Adı | Veri kaynağı bağlantısının test edilmesi |
| Amaç | Ağ, kimlik, TLS ve salt okunur erişimin doğrulanması. |
| Kısa Açıklama | Sistem güvenli bir test çağrısı yapar ve sonucu sınıflandırır. |
| Birincil Aktör | Veri Mühendisi |
| İkincil Aktörler | Harici Veri Kaynağı; Secret Manager |
| Öncelik | Must |
| Tetikleyici | Kullanıcının “Bağlantıyı Test Et” komutunu vermesi. |
| Ön Koşullar | Veri kaynağı tanımlı olmalı; secret referansı geçerli olmalıdır. |

**Temel Akış**

1. Sistem secret değerini güvenli servisten alır.
2. Bağlayıcı ağ bağlantısını kurar.
3. Sistem kaynak türüne uygun salt okunur test sorgusu/çağrısı yapar.
4. Sistem süreyi, kaynak sürümünü ve yetki sonucunu kaydeder.
5. Başarılıysa kaynak test edildi olarak işaretlenir.
6. Kullanıcıya sonuç ve süre gösterilir.

**Alternatif Akışlar**

1. Kullanıcı henüz kaydetmediği ayarları geçici olarak test edebilir; başarılı test sonrası kaydetme seçilir.
2. TLS sertifikası kurum CA tarafından güvenilir değilse güvenlik onayı gerektiren uyarı gösterilir; doğrulama kapatılamaz.

**İstisna Akışları**

1. DNS, ağ, timeout, kimlik, yetki, TLS ve sürücü hataları ayrı kodlanır.
2. Test sorgusu yazma yetkisi tespit ederse kaynak aktif edilmez ve salt okunur hesap istenir.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-002, RULE-003 |
| Son Koşullar | Bağlantı test sonucu saklanır; kaynak başarısına göre etkinleştirilebilir. |
| Başarı Garantisi | Salt okunur bağlantı doğrulanır ve gizli bilgi sızdırmayan sonuç gösterilir. |
| Minimum Garanti | Hata halinde kaynak aktif edilmez; mevcut çalışan sürüm korunur. |
| İlgili Fonksiyonel Gereksinimler | FR-008, FR-009, FR-012, FR-040 |
| Kabul Kriterleri | Başarılı test kaynak bilgisi ve süreyi; başarısız test sınıflandırılmış hata kodunu göstermelidir. |

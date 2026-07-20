---
type: srs-section
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "10"
created_at: 2026-07-16
tags:
  - srs
  - acceptance
---

# Kabul Kriterleri

Bu bölüm, sistem seviyesindeki kabul senaryolarını Given–When–Then biçiminde tanımlar. Her senaryo bağımsız test senaryosu kimliğiyle izlenir.

| Kabul Kriteri ID | Test Senaryosu ID | Senaryo | Given | When | Then |
| --- | --- | --- | --- | --- | --- |
| AC-001 | TS-001 | Başarılı LDAP girişi | Aktif ve rol atanmış bir LDAP kullanıcısı vardır. | Kullanıcı geçerli kimlik bilgileriyle giriş yapar. | Sistem 5 saniye içinde oturum oluşturmalı, yetkili dashboardu açmalı ve başarılı giriş audit kaydı yazmalıdır. |
| AC-002 | TS-002 | Başarısız LDAP girişi | LDAP kullanıcısı yoktur veya parola yanlıştır. | Kullanıcı giriş yapmayı dener. | Sistem oturum oluşturmamalı, kullanıcı/hesap varlığını ifşa etmeyen hata göstermeli ve başarısız giriş kaydı oluşturmalıdır. |
| AC-003 | TS-003 | Yetkisiz kullanıcı | Kullanıcı giriş yapmıştır fakat kaynak oluşturma izni yoktur. | Kullanıcı kaynak oluşturma API'sini veya ekranını çağırır. | Sistem işlemi 403 ile reddetmeli, kaynak kaydı oluşturmamalı ve denied audit kaydı yazmalıdır. |
| AC-004 | TS-004 | Başarılı veri kaynağı bağlantısı | Geçerli, salt okunur veritabanı hesabı ve ağ erişimi vardır. | Yetkili kullanıcı bağlantı testini başlatır. | Sistem salt okunur test sorgusunu tamamlamalı, süreyi kaydetmeli ve kaynağı test başarılı durumuna getirmelidir. |
| AC-005 | TS-005 | Başarısız bağlantı | Kaynak hostuna erişim yoktur veya kimlik bilgisi geçersizdir. | Bağlantı testi çalıştırılır. | Sistem DNS/ağ/timeout/kimlik hata sınıfını ayırmalı, secret göstermemeli ve kaynağı aktif etmemelidir. |
| AC-006 | TS-006 | Salt okunurluk | Bağlantı hesabına yanlışlıkla yazma yetkisi verilmiştir veya özel SQL DML içerir. | Kural testi yapılır. | Sistem DML/DDL ifadesini reddetmeli ve kaynakta hiçbir veri değişikliği oluşmamalıdır. |
| AC-007 | TS-007 | Temel profilleme | 1 milyon satırlık ve bilinen dağılımlı bir test veri kümesi vardır. | Kullanıcı tam profil başlatır. | Sistem kayıt, null, tekil, min, max ve ortalama değerlerini beklenen sonuçlarla eşleşecek biçimde hesaplamalı ve yöntemi FULL olarak saklamalıdır. |
| AC-008 | TS-008 | Büyük tablo örnekleme | 20 milyon satırlık tablo ve 16 GB RAM'li yerel prototip vardır. | Kullanıcı profil başlatır ve örnekleme seçer. | Sistem tam tabloyu belleğe almadan örneklem/bölüm yöntemini uygulamalı, örneklem oranını sonuçta göstermeli ve süreç bellek yetersizliğiyle sonlanmamalıdır. |
| AC-009 | TS-009 | Başarılı kural çalıştırması | 125 kaydın 100'ü kuralı karşılayan test veri kümesi vardır. | Kural çalıştırılır. | Sistem 125 kontrol, 100 başarılı, 25 hatalı, %80 başarı ve 80,00 kural skoru üretip geçmişe kaydetmelidir. |
| AC-010 | TS-010 | Teknik hata | Çalıştırma sırasında kaynak bağlantısı kesilir. | Kural çalıştırması sonlanır. | Sistem durumu TECHNICAL_ERROR yapmalı, sayısal skoru 0 olarak üretmemeli, retry politikasını uygulamalı ve teknik bildirim oluşturmalıdır. |
| AC-011 | TS-011 | Boş veri kümesi | Kural kapsamındaki veri kümesinde 0 kayıt vardır. | Kural tamamlanır. | Sistem NO_DATA durumu üretmeli, skor alanını NULL/hesaplanmadı göstermeli ve kurum skoruna 0 olarak katmamalıdır. |
| AC-012 | TS-012 | Kısmi çalışma | Bölümlenmiş işin bazı bölümleri tamamlandıktan sonra timeout oluşur. | İş sonlandırılır. | Sistem PARTIAL veya TIMEOUT durumunu kaydetmeli, tamamlanan bölümleri belirtmeli ve varsayılan olarak resmi agregasyona dahil etmemelidir. |
| AC-013 | TS-013 | Ağırlıklı skor | İki geçerli kural skoru 80 ve 100; ağırlıkları 2 ve 1'dir. | Veri kümesi skoru hesaplanır. | Sistem skoru 86,67 olarak hesaplamalı ve kullanılan ağırlıkları açıklama detayında saklamalıdır. |
| AC-014 | TS-014 | Skor seviye eşikleri | Varsayılan eşik seti aktiftir. | 80,00 skor sınıflandırılır. | Sistem “Kabul Edilebilir” seviyesini atamalıdır; eşik sınırları boşluk/çakışma içermemelidir. |
| AC-015 | TS-015 | Eşik altı skor | Kritik veri kümesi skoru tanımlı eşik altına düşer ve sahipleri tanımlıdır. | Skor hesaplaması tamamlanır. | Sistem 5 dakika içinde kritik olay, tek açık issue ve doğru alıcılara sistem içi bildirim oluşturmalıdır. |
| AC-016 | TS-016 | Bildirim deduplication | Aynı kural ve veri kümesi için açık olay ve tekrar penceresi vardır. | Aynı olay üç kez yeniden oluşur. | Sistem politika dışı üç yeni bildirim/issue oluşturmamalı; mevcut kayıt sayacını veya son görülme zamanını güncellemelidir. |
| AC-017 | TS-017 | Sorun atama | Yeni issue ve aktif Data Steward vardır. | Yetkili kullanıcı sorunu Data Steward'a atar. | Sistem durumu Atandı yapmalı, atama geçmişi/audit kaydı ve sistem içi bildirim oluşturmalıdır. |
| AC-018 | TS-018 | Sorun kapatma doğrulaması | Issue Çözüldü durumundadır ancak doğrulama kuralı başarısızdır. | Kullanıcı kapatma talep eder. | Sistem kapatmayı reddetmeli ve issue'yu çözüm bekliyor/inceleme durumuna döndürmelidir. |
| AC-019 | TS-019 | ServiceNow idempotency | Bir issue için ServiceNow ticket oluşturma isteği daha önce başarıyla işlenmiştir. | Aynı idempotency key ile istek tekrarlanır. | Sistem yeni ticket oluşturmamalı ve mevcut ticket referansını döndürmelidir. |
| AC-020 | TS-020 | Rapor dışa aktarma | Yetkili kullanıcı 50.000 satırlık maskeli rapor seçmiştir. | Kullanıcı Excel dışa aktarımı başlatır. | Sistem dosyayı 60 saniye hedefi içinde üretmeli, filtreleri içermeli ve indirme audit kaydı yazmalıdır. |
| AC-021 | TS-021 | Rapor yetkisiz veri | Kullanıcı yalnız A birimine yetkilidir; rapor filtresi A ve B'yi içerir. | Rapor oluşturulur. | Sistem yalnız A birimi verisini dahil etmeli veya isteği açık biçimde reddetmeli; B verisi dosyada bulunmamalıdır. |
| AC-022 | TS-022 | Audit log oluşması | Yetkili kullanıcı bir kuralın eşiğini değiştirir. | Değişiklik kaydedilir. | Sistem kullanıcı, zaman, nesne, eski/yeni değer, sonuç ve correlation ID içeren append-only audit kaydı oluşturmalıdır. |
| AC-023 | TS-023 | Kişisel veri maskeleme | Profil ve hata örneklerinde hassas olarak sınıflandırılmış alanlar vardır. | Kullanıcı sonuç ve raporu görüntüler. | Sistem ham hassas değerleri göstermemeli veya loglamamalı; yalnız maskeli/toplulaştırılmış değer sunmalıdır. |
| AC-024 | TS-024 | Çift manuel çalıştırma | Aynı kural ve kapsam aynı idempotency key ile 10 kez tetiklenir. | İstekler eş zamanlı alınır. | Sistem tek RuleExecution oluşturmalı ve tüm yanıtlarda aynı Execution ID'yi döndürmelidir. |
| AC-025 | TS-025 | Şema değişikliği | Aktif kuralın bağlı olduğu kolonun veri tipi değişmiştir. | Metadata taraması tamamlanır. | Sistem değişikliği algılamalı, kuralı inceleme gerekli olarak işaretlemeli ve sonraki çalıştırmadan önce kullanıcıya göstermelidir. |
| AC-026 | TS-026 | Audit bütünlüğü | Audit deposundaki bir kayıt yetkisiz yöntemle değiştirilmiştir. | Periyodik bütünlük kontrolü çalışır. | Sistem bozulmayı tespit etmeli, güvenlik alarmı oluşturmalı ve kaydı sessizce düzeltmemeli/silmemelidir. |

---
type: business-rules
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "6"
created_at: 2026-07-16
tags:
  - srs
  - rule
---

# İş Kuralları

Bu bölüm, fonksiyonel davranışın uygulanmasında bağlayıcı olan iş kurallarını tanımlar.

| Kural ID | Kural adı | Açıklama | Uygulandığı modül | Koşul | Sonuç | İstisna | Öncelik |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RULE-001 | Yetkili kural ve yönetim işlemleri | Kural oluşturma, yayımlama, kullanıcı/rol ve sistem ayarı işlemleri yalnız ilgili RBAC iznine sahip kullanıcılarca yapılır. | Kullanıcı, kural ve yetki yönetimi | Kullanıcı gerekli izin ve veri kapsamına sahiptir. | İşlem yürütülür ve auditlenir. | Acil durum hesabı yalnız güvenlik onayı ve süreli yetkiyle kullanılabilir. | Kritik |
| RULE-002 | Salt okunur kaynak erişimi | Veri kaynaklarına bağlantılar salt okunur olmalı; DDL/DML ve kaynakta değişiklik yapan API çağrıları yasaktır. | Bağlantı, profil ve kural motoru | Bağlantı hesabı yalnız okuma yetkisine sahiptir; sorgu ayrıştırıcısı yazma komutlarını reddeder. | Kaynak veri değiştirilmeden kontrol yapılır. | Kaynak ürünü salt okunur rolü desteklemiyorsa güvenlik onaylı teknik izolasyon gerekir. | Kritik |
| RULE-003 | Teknik hata ve kalite hatası ayrımı | Bağlantı, timeout, SQL, sürücü, kimlik veya altyapı hatası teknik hata; kural koşulunu karşılamayan kayıt veri kalitesi hatasıdır. | Çalıştırma ve skorlama | İş tamamlanma ve hata kodları değerlendirilir. | Teknik hata resmi skoru doğrudan düşürmez; kalite hatası sayaç ve skora yansır. | Politika ile onaylanmış kısmi çalışma ayrı PARTIAL statüsünde gösterilebilir. | Kritik |
| RULE-004 | Skor hesaplanabilirlik | Sayısal skor yalnız çalıştırma teknik olarak tamamlandıysa, sayaçlar tutarlıysa ve değerlendirilebilir kayıt sayısı sıfırdan büyükse hesaplanır. | Skorlama | Execution başarıyla tamamlanmıştır ve toplam > 0'dır. | Kural ve üst seviye skorlar hesaplanır. | NO_DATA, teknik hata ve politika dışı kısmi çalışma “hesaplanmadı” olur. | Kritik |
| RULE-005 | Ağırlık ve eşik yönetimi | Kural, boyut ve kritiklik ağırlıkları sıfırdan büyük; skor eşikleri 0–100 aralığında ve çakışmasız olmalıdır. | Kural ve skorlama | Yetkili kullanıcı geçerli değer girer. | Yeni konfigürasyon sürümü sonraki hesaplarda kullanılır. | Geçmiş skorlar yeniden yazılmaz; yeniden hesaplama yeni sürüm üretir. | Yüksek |
| RULE-006 | Olay, sorun ve sahiplik | Kritik kural başarısızlığı veya eşik ihlali geçerli sahiplik politikasıyla bildirim ve gerekirse issue oluşturur. | Bildirim ve sorun yönetimi | Olay eşiği karşılar ve açık duplicate yoktur. | Sahipli issue/bildirim oluşur. | Sahip yoksa yönetişim varsayılan kuyruğuna atanır. | Kritik |
| RULE-007 | Sürüm ve tarihsel koruma | Kural, bağlantı, eşik ve sahiplik değişiklikleri sürümlenmeli; geçmiş sonuçlar çalıştıkları sürüme bağlı kalmalıdır. | Metadata, kural, audit | Değişiklik yapılır. | Yeni sürüm oluşur; eski sürüm değişmez. | Yalnız mevzuatça zorunlu anonimleştirme/silme işlemi kontrollü prosedürle yapılabilir. | Kritik |
| RULE-008 | Silme yerine arşivleme | Silinen/pasif kural, kaynak ve sorunların tarihsel sonuçları saklama süresince korunur. | Tüm modüller | Nesne tarihsel sonuçla ilişkilidir. | Nesne arşivlenir ve yeni işlemlere kapanır. | Yasal silme talebi veri minimizasyonu/anonimleştirme sürecine göre ele alınır. | Yüksek |
| RULE-009 | Yetki kapsamı ve gizlilik | Kullanıcı yalnız rolü ve veri alanı kapsamındaki metadata, sonuç, örnek, rapor ve audit kayıtlarını görebilir. | Tüm kullanıcı arayüzleri ve API | Her istek RBAC ve veri kapsamı kontrolünden geçer. | Yetkili veri gösterilir; diğerleri reddedilir. | Denetçi erişimi ayrıca onaylı denetim kapsamıyla sınırlıdır. | Kritik |
| RULE-010 | Kişisel veri maskeleme | Kişisel/hassas veri içeren profil örnekleri, hata kayıtları, loglar ve raporlar maskelenmeli; mümkünse ham değer saklanmamalıdır. | Profil, sonuç, rapor ve log | Alan hassas olarak işaretli veya otomatik sınıflandırılmıştır. | Maskeli değer veya yalnız toplulaştırılmış metrik gösterilir. | Hukuki ve güvenlik onaylı özel inceleme geçici, auditli ve en az ayrıcalıkla yapılabilir. | Kritik |
| RULE-011 | İdempotency ve tekrar kontrolü | Aynı iş, sorun, bildirim veya ServiceNow ticket isteği tanımlı idempotency anahtarı ve zaman penceresinde çift kayıt üretmemelidir. | Çalıştırma, bildirim, issue, entegrasyon | Aynı anahtar/kapsam daha önce işlenmiştir. | Mevcut kayıt döner veya güncellenir. | Aynı anahtar farklı payload ile gelirse 409/çakışma hatası oluşur. | Kritik |
| RULE-012 | Kaynak performans koruması | Kaynak bazlı eş zamanlılık, timeout, satır limiti ve çalışma penceresi aşılmamalıdır. | Profil ve kural motoru | Kaynak kotası ve maliyet tahmini uygundur. | İş çalıştırılır. | Eşik aşılırsa iş bekletilir, örnekleme istenir veya kontrollü biçimde reddedilir. | Kritik |
| RULE-013 | Sorun durum geçişi | Sorunlar yalnız tanımlı yaşam döngüsü geçişleriyle ilerler; kapatma öncesi doğrulama sonucu zorunludur. | Sorun yönetimi | Zorunlu alanlar ve yetki mevcuttur. | Durum değişir ve geçmiş kaydı oluşur. | İptal edilen sorun için gerekçe zorunludur. | Yüksek |
| RULE-014 | Saklama süresi | Kural sonuçları, skorlar, audit, bildirim ve sorun kayıtları varsayılan beş yıl saklanır. | Veri yaşam döngüsü | Kayıt yasal/kurumsal istisna kapsamında değildir. | Süre sonunda arşivleme, anonimleştirme veya silme politikası uygulanır. | Kesin süre güvenlik, hukuk ve kurum politikasıyla onaylanmalıdır. | Yüksek |
| RULE-015 | Saat ve zaman dilimi | Tüm olaylar UTC olarak saklanmalı; kullanıcı arayüzünde kurumun Europe/Istanbul zaman diliminde gösterilmelidir. | Tüm modüller | Sistem saat senkronizasyonu sağlanır. | Tarihsel sıralama ve cron hesapları tutarlı olur. | Kaynağın farklı saat dilimi ayrıca metadata olarak saklanır. | Yüksek |

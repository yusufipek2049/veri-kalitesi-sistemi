# Veri Koruma ve Maskeleme

## Politika Sınırı

Kurumsal veri kataloğu veya DLP sistemi sınıflandırmanın sistem-of-record kaynağıdır. `ClassificationPolicy` ve `MaskingPolicy`, harici kimlik/seviye ile kişisel veri göstergelerini ve görüntüleme, raporlama, loglama, maskeleme kısıtlarını domain servislerine taşıyan sürümlü adaptörlerdir.

## Teknik Baseline

- `veri_kalitesi.data_protection` paketindeki `CLASSIFICATION_POLICY_V1` yerel teknik uyumluluk/önbellek sözlüğüdür; bağımsız kurumsal sınıflandırma kaynağı değildir.
- Teknik sözlük kodları: `UNCLASSIFIED`, `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `PERSONAL_DATA`, `SPECIAL_CATEGORY_PERSONAL_DATA`, `CUSTOMER_SECRET`, `BANK_SECRET`, `HIGHLY_RESTRICTED`.
- Bu kodlar kurumsal katalog/DLP kimliği ve kaynak referansıyla eşlenir; teknik doğrulama banka politika onayı değildir.
- Metadata keşfinde boş sınıf `UNCLASSIFIED` olur; sözlük dışı kod kalıcı yazımdan önce doğrulama hatası üretir.
- SQLite prototipinde sınıf ve politika sürümü birlikte saklanır. Eski NULL/serbest değerler açılış migration'ında fail-closed `UNCLASSIFIED` değerine taşınır; insert/update tetikleyicileri sözlük dışı yazımı reddeder.
- Profil kalıcılığı yalnız allowlist içindeki toplulaştırılmış metrikleri kabul eder. `samples`, `top_values`, `pattern_examples` ve bilinmeyen payload alanları kalıcı profil ve auditten çıkarılır.

## İşleme Envanteri

- Sınıflandırılmış `DataField`, değişmez ve artan sürümlü `DataProcessingInventory` geçmişiyle ilişkilendirilebilir.
- Envanter; işleme amacı, hukuki sebep, veri sahibi, saklama politikası ve erişim rollerini banka dış yönetişim kayıtlarına referans olarak taşır. Sistem varsayılan hukuki sebep veya saklama süresi üretmez.
- Alıcı grupları referans listesi ve yurt dışı aktarım etkisi açık boolean alanla saklanır.
- Envanter sürümü ve redakte `DATA_PROCESSING_INVENTORY_RECORDED` audit olayı aynı SQLite transaction'ında yazılır. Audit özeti yalnız sürüm, sınıf, aktarım bayrağı ve referans sayıları içerir.
- Aynı dataset/alan yeniden keşfedildiğinde teknik kimlik korunur; böylece envanter geçmişi metadata taramasında kopmaz.
- Salt okunur kapsam kontrolü, yalnız `PERSONAL_DATA` ve `SPECIAL_CATEGORY_PERSONAL_DATA` sınıflarındaki alanları tek sorguda güncel envanter sürümüyle eşleştirir. Banka sözlük eşlemesi onaylanmadan müşteri sırrı ve banka sırrı sınıflarının kişisel veri olduğu varsayılmaz.
- Sonuç `COMPLETE`, `INCOMPLETE` veya yanıltıcı bir tamlık beyanını önleyen `NO_REQUIRED_FIELDS` durumunu taşır. Eksik kayıt `MISSING_CURRENT_INVENTORY` veri kalitesi/tamlık sonucudur; SQLite okuma arızası ayrı teknik hatadır.
- Kapsam çıktısı yalnız kaynak, dataset ve alan teknik kimlikleri, sınıf, sürüm ve sorun kodunu taşır; amaç, hukuki sebep, sahip, saklama veya rol/alıcı referanslarını açmaz.

## Varsayılanlar

- Sınıflandırılmamış alan: ham örnek yok.
- CUSTOMER_SECRET/BANK_SECRET/HIGHLY_RESTRICTED: toplulaştırılmış metrik dışında görünüm yok.
- PERSONAL_DATA: rol ve amaç doğrulanmadan ham görünüm yok.
- Log/audit/notification/ServiceNow: yalnız teknik kimlik ve özet.
- Harici sınıflandırma sistemi erişilemezse bilinen hassas veri daha düşük sınıfa düşürülmez; son güvenilir sınıf veya daha kısıtlayıcı güvenli varsayılan uygulanır.

Mevcut profil yüzeyinde yetkili ham inceleme akışı bulunmadığından, sınıf ham incelemeye uygun olsa bile ham değer kalıcı profile alınmaz.

## Redaksiyon

- Hata metinleri kaynak sürücünün ham mesajını kullanıcıya taşımaz.
- Audit old/new values alanları allowlist ve digest üzerinden üretilir.
- Correlation ID hassas bağlam içermez.

## Açık Konular

- Kurumsal katalog/DLP ürün, endpoint ve teknik eşleme ayrıntıları.
- Hukuki sebep, saklama politikası, rol ve alıcı grup referanslarının banka kayıtlarıyla doğrulanması.
- Geçici ve auditli özel inceleme akışı ile masking algoritmaları.
- Dashboard, bildirim, issue, rapor ve dışa aktarma yüzeylerinin merkezi politikaya bağlanması.

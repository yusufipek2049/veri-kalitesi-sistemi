---
iteration: 18
status: technically-verified
primary_module: metadata
---

# İterasyon 18 — Veri Sınıflandırma ve Maskeleme

## Hedef

Mevcut serbest `classification` alanını sürümlü sözlük ve merkezi görüntüleme/örnek politikasıyla güvenli hâle getirmek.

## Kapsam

- ClassificationCode enum/value object.
- Unknown/sınıflandırılmamış alan için deny-by-default.
- ClassificationPolicy ve MaskingPolicy protokolleri.
- Profil, dashboard ve audit için ilk redaksiyon testleri.
- İşleme amacı/saklama politikası metadata alanları için migration taslağı.

## Kabul

- Sınıf yoksa ham örnek üretilemez.
- CUSTOMER_SECRET/BANK_SECRET sınıfı bildirim/audit payloadına giremez.
- Mevcut toplulaştırılmış profil metrikleri korunur.

## Dilim 18A Kapanisi

`TechnicallyVerified` kapsam:

- `ClassificationCode`, `ClassificationPolicy` ve `MaskingPolicy` merkezi `data_protection` paketinde sürümlü olarak tanımlandı.
- Boş sınıf `UNCLASSIFIED` değerine normalize edilir; onaysız harici kod metadata yazımından önce kontrollü doğrulama hatası üretir.
- `DataField` sınıf ve politika sürümünü birlikte taşır. Eski NULL/serbest sınıflar güvenli `UNCLASSIFIED` değerine migrate edilir; SQLite insert/update tetikleyicileri sözlük dışı değeri reddeder.
- Profil connector çıktısı kalıcılaştırılmadan allowlist ile minimize edilir. Aggregate sayaç/oran/min/max/ortalama korunur; ham örnek, top-value, desen örneği ve bilinmeyen alanlar çıkarılır.
- `CUSTOMER_SECRET` ve `UNCLASSIFIED` alanların ham sentetik değerlerinin profil, depo ve merkezi audit olayına girmediği doğrulandı.
- 3 yeni testle toplam 173 test geçti; veri kaynağı hedef grubu 31 testle geçti.

18A teknik sözlük ve profil minimizasyonu dilimidir; banka sınıf kodu eşlemesi, `BFR-DATA-004` işleme envanteri, dashboard/bildirim/issue/rapor entegrasyonları ve özel inceleme akışı kapsam dışıdır. Banka bilgi güvenliği ve hukuk/uyum onayları `ComplianceReviewRequired` kalır.

## Dilim 18B Kapanisi

`TechnicallyVerified` kapsam:

- `DataProcessingInventory`, sınıflandırılmış `DataField` için işleme amacı, hukuki sebep, veri sahibi, saklama politikası, erişim rolleri, alıcı grupları ve yurt dışı aktarım etkisini dış yönetişim referanslarıyla ilişkilendirir.
- Envanter kayıtları append-only ve artan sürümlüdür; önceki sürümler yerinde güncellenmez.
- Metadata yeniden keşfinde aynı dataset ve alan kimliği korunur; envanter geçmişi yeniden taramada kopmaz.
- Envanter inserti ile `AUDIT_REDACTION_V3` üzerinden redakte audit outbox olayı aynı SQLite transaction'ında yazılır; outbox-stage hatası envanter sürümünü rollback eder.
- Audit olayında amaç, hukuki sebep, sahip, saklama veya rol/alıcı referansları bulunmaz; yalnız sürüm, sınıf, aktarım bayrağı ve referans sayıları taşınır.
- Sınıflandırılmamış alan ve secret-benzeri yönetişim referansı kontrollü doğrulama hatası üretir; teknik outbox hatasından ayrı kalır.
- 3 yeni testle toplam 176 test geçti; veri kaynağı hedef grubu 34 testle geçti.

18B `BFR-DATA-004` ilişkilendirme sözleşmesini teknik olarak doğrulamıştır. Bu dilimin kapanışında `NFR-PRV-005` tamlık kontrolü, banka referans sözlükleri ve kurum onayları henüz açık durumdaydı.

## Dilim 18C Kapanisi

`TechnicallyVerified` kapsam:

- `PERSONAL_DATA` ve `SPECIAL_CATEGORY_PERSONAL_DATA` alanları tek salt okunur sorguyla güncel envanter sürümüne bağlanır.
- Eksik sürüm `INCOMPLETE` ve `MISSING_CURRENT_INVENTORY` ile raporlanır; zorunlu alan bulunmayan kapsam `NO_REQUIRED_FIELDS` olur.
- Çıktı yalnız teknik kimlik, sınıf, sürüm ve sorun kodunu taşır; yönetişim referanslarını açmaz.
- Eksik kayıt veri kalitesi/tamlık sonucudur; SQLite okuma arızası ayrı teknik hata üretir.
- 3 yeni testle toplam 179 test geçti; veri kaynağı hedef grubu 37 testle geçti.

18A–18C teknik kapsamı tamamlanmıştır. Banka sınıf eşlemesi, kurumsal referans doğrulaması ve bilgi güvenliği/hukuk/uyum onayları açık kalır; bu kapanış mevzuat uyumu beyanı değildir.

# İterasyon 25B — Kalıcı Legal Hold Yaşam Döngüsü Kanıtı

## Kontrol Durumu

- Teknik durum: `TechnicallyVerified`
- Uyum durumu: `ComplianceReviewRequired`
- Tarih: 2026-07-21
- Kontroller: `CTRL-KVKK-DEL-001`, `CTRL-BDDK-AUD-001`, `CTRL-BDDK-SOD-001`
- Gereksinimler: `BFR-LCM-002`, `BFR-AUD-001`–`BFR-AUD-004`, `BFR-SOD-002`,
  `FR-077`, `FR-079`, `NFR-SEC-001/008/011`, `NFR-CMP-001/003`

## Teknik Kanıt

- Legal hold oluşturma ve serbest bırakma, `PLACED` ve `RELEASED` olaylarıyla
  append-only SQLite geçmişinde saklanır. `UPDATE` ve `DELETE` tetikleyicilerle
  reddedilir.
- Hold politika sürümü, opak kayıt referansı, kayıt sınıfı, yetki kapsamı,
  karar rolü, reason code ve karar aktörüyle ilişkilidir.
- Yalnız güvenilir, geçerli ve sürümlü normal kullanıcı context'i; politika rolü
  ve source/dataset/enterprise kapsamı eşleştiğinde işlem yapabilir. Servis hesabı,
  break-glass, yanlış rol ve yanlış kapsam fail-closed reddedilir.
- Hold'u oluşturan aktör aynı hold'u serbest bırakamaz. Aynı kayıt üzerindeki
  birden fazla bağımsız hold'dan biri serbest bırakılsa bile diğerleri otomatik
  imhayı engellemeye devam eder.
- Domain olayı ile redakte audit outbox aynı transaction'da yazılır. Audit-stage
  arızası domain değişikliğini geri alır; merkezi publisher kesintisinde domain
  kaydı korunur ve audit olayı `PENDING` kalır.
- Audit özeti yalnız durum, kayıt sınıfı, politika sürümü ve kapsam türü gibi
  allowlist alanlarını taşır; kayıt referansı, kapsam kimliği, serbest metin veya
  ham hassas veri audit özetine kopyalanmaz.

## Doğrulama

- Legal hold hedef grubunda 17 yeni vaka, retention grubunda toplam 26 test geçti.
- Tam regresyonda 776 test geçti.
- Tam mypy 116 kaynak dosyada, Ruff, format ve derleme kontrolleri hatasız geçti.
- SBOM ve teknik kanıt manifesti byte düzeyinde eşleşti; birleşik yerel sürüm ön
  kontrolü `PASS` verdi.

## Sınırlar

- Teknik rol ve reason code değerleri sentetiktir; banka LDAP/rol ve karar
  sözlüğü eşlemesi `ComplianceReviewRequired` kalır.
- SQLite yerel prototiptir. Üretim PostgreSQL şeması, uygulama rolünden ayrılmış
  değişmezlik yetkisi, çoklu süreç eşzamanlılığı ve WORM audit ürünü açık kalır.
- Fiziksel silme, anonimleştirme, arşivleme, arşiv geri çağırma ve yedek re-delete
  uygulanmamıştır. Bu kanıt banka onayı veya mevzuat uyumluluğu sonucu değildir.

## Güvenli Geri Alma

25B servisi çağrı yüzeyinden kaldırılabilir; append-only hold ve audit outbox
kayıtları silinmez veya yerinde değiştirilmez. Aktif hold'lar fiziksel imha
adaptörü bulunmadığı için kayıtları engellemeye devam eder.

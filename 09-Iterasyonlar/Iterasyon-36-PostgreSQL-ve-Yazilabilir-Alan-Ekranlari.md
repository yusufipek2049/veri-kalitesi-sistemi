---
iteration: 36
status: planned
completed_at: null
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36 — PostgreSQL-only ve Yazılabilir Alan Ekranları

## Amaç

SQLite kalıcılığını domain bazlı olarak tamamen kaldırmak ve 35A–35F salt
okunur alan ekranlarını güvenilir mutasyon sınırlarıyla kullanılabilir iş
akışlarına dönüştürmek.

Kaynak sistemlere salt okunur erişim değişmez. Yazma işlemleri yalnız
uygulamanın sahip olduğu metadata, politika, iş akışı ve sonuç kayıtlarını
etkiler. Audit olayları değişmez ve salt okunur kalır.

## 36A — PostgreSQL-only Kalıcılık Temeli

Durum: **TechnicallyVerified — 36A1/36A2a/36A2b tamamlandı**

36A tek iterasyon boyutunu aştığı için iki dikey dilime ayrılmıştır:

- `36A1`: ortak SQLAlchemy/Alembic temel, SQLite envanteri, issue baseline ve
  PostgreSQL-only salt okunur issue repository'si; `TechnicallyVerified`.
- `36A2a`: issue mutasyonları, geçmiş ve atomik audit outbox;
  `TechnicallyVerified`.
- `36A2b`: idempotent seçici aktarım, bütünlük doğrulaması ve issue SQLite
  runtime yolunun kaldırılması; `TechnicallyVerified`.

### Gereksinim Bağlantıları

- `NFR-MNT-001`
- `NFR-MNT-004`
- `NFR-MNT-006`
- `NFR-REL-006`
- `FR-064–FR-070`
- `UC-013`, `UC-014`

### Çıkış Kriterleri

- SQLite repository, tablo, migration ve test kullanımları envanterlenir.
- Ortak SQLAlchemy 2 session/transaction sınırı oluşturulur.
- `data_quality.dq` için Alembic baseline hazırlanır.
- Migration'lar yalnız ileri çalışır; hata düzeltici yeni migration üretir.
- Repository testleri PostgreSQL transaction rollback, migration/eşzamanlılık
  testleri benzersiz geçici şema kullanır.
- Audit, issue, onay, politika, kural sürümü ve iş geçmişi seçici/idempotent
  taşınır; yeniden üretilebilir sentetik/cache verisi yeniden oluşturulur.
- İlk domain olarak issue kalıcılığı PostgreSQL'e taşınır.
- Taşınan issue yolunda SQLite fallback bulunmaz.
- Secret veya bağlantı parolası repository'ye yazılmaz.

## 36B — Yazılabilir Sorunlar

Durum: **Ready — 36A tamamlandı**

- Gereksinimler: `FR-064–FR-070`, `UC-013`, `UC-014`.
- Atama ve incelemeye alma.
- Çözüm kaydetme.
- Farklı aktörle doğrulama ve kapatma.
- Aynı başarısızlıkta yeniden açma.
- Sayısal `version` ile optimistic locking ve çakışmada `409 Conflict`.
- Açık kaydetme, kaydedilmemiş değişiklikte çıkış uyarısı ve hassas taslağı
  tarayıcı kalıcı depolamasına yazmama.
- Güvenilir aktör, rol/kapsam, BFF/CSRF ve veri-minimum audit.

## 36C — Yazılabilir Kurallar

Durum: **Planned — ilgili repository PostgreSQL geçişine bağlı**

- Gereksinimler: `FR-023–FR-035`, `UC-005`, `UC-006`, `RULE-001`.
- Taslak oluşturma ve düzenleme.
- Kural testi.
- Onaya gönderme ve geri çekme.
- Düşük riskli taslakta tek yetkili; kritik değişikliklerde maker-checker.
- Aktivasyon ve kontrollü pasifleştirme.

## 36D — Yazılabilir Veri Kaynakları

Durum: **Planned — secret manager ve PostgreSQL geçişine bağlı**

- Gereksinimler: `FR-007–FR-014`, `UC-002`, `UC-003`.
- Kaynak tanımlama.
- Değişmez bağlantı revizyonu.
- Kaynakta salt okunur bağlantı testi.
- Maker-checker kontrollü aktivasyon ve pasifleştirme.
- Secret değerini frontend, API payload'ı, log, audit veya veritabanında
  tutmayan referans modeli.

## 36E — Çalıştırma İşlemleri

Durum: **Planned — execution/queue PostgreSQL geçişine bağlı**

- Gereksinimler: `FR-036–FR-053`, `UC-007`, `UC-008`.
- Manuel başlatma.
- İptal.
- Yeniden deneme.
- Doğrudan worker başlatmadan kaynak kullanım politikası, kota, çalışma
  penceresi ve idempotency kontrolü sonrası kuyruğa alma.

## 36F — Rapor İşlemleri ve Denetim Sınırı

Durum: **Planned — dışa aktarma kontrollerine bağlı**

- Gereksinimler: `FR-072–FR-079`, `UC-015`, `UC-016`.
- Rapor üretim talebi.
- Asenkron durum izleme ve güvenli indirme.
- Sentetik/düşük hassasiyetli raporda yetkili kapsam; hassas raporda DLP,
  watermark, gerekçe ve gerekli maker-checker kapısı.
- Gereken banka kararı yoksa dışa aktarmanın fail-closed kalması.
- Audit kayıtları için yalnız sorgu, filtre, bütünlük ve arşiv inceleme; kayıt
  düzeltme veya silme yoktur.

## Ortak Tamamlama Koşulları

- Her mutasyon güvenilir `ActorContext` üzerinden yetkilendirilir.
- Cookie tabanlı BFF mutasyonlarında CSRF kontrolü zorunludur.
- Yetkisiz, ayrıcalıklı ve servis hesabı negatifleri test edilir.
- Teknik hata ile veri kalitesi başarısızlığı ayrılır.
- Kritik yazımlarda audit kaydı veya kalıcı outbox oluşturulamazsa işlem
  fail-closed sonuçlanır.
- Gerçek banka verisi, LDAP kimliği veya üretim secret'ı geliştirme/test
  ortamına yazılmaz.
- PostgreSQL'e taşınan domain için SQLite compatibility/fallback bırakılmaz.

# Denetim Faz 2: PostgreSQL Test Yolunu Çalışır Hale Getirme

## Bağlam

Kod tabanının en ciddi yapısal sorunu: **test edilen kod ile üretimde çalışan kod farklı.**

Her alan için iki kalıcılık uygulaması var:

- `src/veri_kalitesi/<alan>/repository.py` — SQLite (`SQLiteAuditRepository`,
  `SQLiteRuleRepository`, `SQLiteExecutionRepository`, …)
- `src/veri_kalitesi/<alan>/postgresql_repository.py` — PostgreSQL

Üretim kompozisyonu (`src/veri_kalitesi/api/composition.py`) **yalnızca** PostgreSQL
sürümünü bağlıyor. Kapsamın tamamı ise SQLite sürümünde:

```
PostgreSQL depoları (ÜRETİM) :   493 / 1917 satır  = %25,7
SQLite depoları (bağlı değil): 1640 / 1928 satır  = %85,1
```

Neden: 121 PostgreSQL entegrasyon testi, ortam değişkeni tanımlı olmadığı için her
koşuda atlanıyor.

```
SKIPPED  DATA_QUALITY_POSTGRES_TEST_URL is required for PostgreSQL integration.
SKIPPED  SYNTHETIC_POSTGRES_TEST=1 is required for PostgreSQL integration.
```

Etkilenen test dosyaları `tests/integration/` altında (`test_postgresql_*`,
`test_synthetic_postgresql_integration.py` vb.).

**Bu testlerin geçtiği doğrulanmamıştır** — yalnızca hiç çalışmadıkları doğrulanmıştır.
İlk koşuda başarısızlık çıkması beklenen bir sonuçtur ve raporlanmalıdır.

### Mevcut altyapı

`infra/development/compose.yaml` çalışan bir PostgreSQL servisi tanımlıyor:
şema `dq`, kullanıcı `dq_app`, veritabanı `data_quality`, port `15432`, healthcheck'li.
Migration'lar `alembic/versions/` altında 23 dosya; şema kayması yok
(44 migration tablosu ↔ 42 depo tablosu tutarlı).

**Bağımlılık:** Yok, ancak Faz 1 ile paralel yürütülebilir.

**Kapsam dışı:** CI iş akışı kurulumu bu fazın kapsamı dışındadır. Amaç, testlerin
**yerelde tek komutla** çalışabilir hale gelmesidir.

## Görev

1. **Tek komutlu PostgreSQL test ortamı.** Geliştiricinin PostgreSQL entegrasyon
   testlerini tek adımda koşabilmesini sağla. Compose servisini yeniden kullan;
   test için ayrı bir veritabanı/şema kullanmayı tercih et ki geliştirme verisi kirlenmesin.
2. **Test fixture'ı ve yaşam döngüsü.** Şema kurulumu (alembic upgrade) ve testler arası
   izolasyon (her test sonrası temizlik veya transaction rollback) için ortak fixture yaz.
   Mevcut `tests/integration/` konvansiyonuna uy.
3. **121 testi koştur ve sonucu olduğu gibi raporla.** Başarısız olanları düzelt.
   Her başarısızlık için: gerçek bir üretim hatası mı, yoksa test kurgusu hatası mı —
   ayrımını açıkça yaz. **Gerçek üretim hatası bulursan bunu ayrıca vurgula**; bu fazın
   asıl değeri oradadır.
4. **Kapsamı ölç ve raporla.** PostgreSQL depolarının satır kapsamını öncesi/sonrası
   olarak ver.

## Invariantlar

- Testler determinist olmalı: koşum sırasından bağımsız, birbirini kirletmeyen.
- Ortam değişkeni tanımlı **değilken** testler atlanmaya devam etmeli (mevcut davranış
  korunur) — böylece PostgreSQL'siz ortamda `pytest` hâlâ yeşil kalır.
- Üretim kodunda davranış değişikliği yalnızca gerçek hata düzeltmesi olarak yapılabilir;
  "testi geçirmek için" üretim davranışı gevşetilemez.
- Alembic migration'ları değiştirilmeyecek (şema kayması yok, korunacak).
- Gizli bilgi (parola vb.) repoya yazılmayacak; mevcut `runtime-secrets` ve
  ortam değişkeni yaklaşımına uyulacak.
- Yeni üçüncü parti bağımlılık yok.

## Kabul Kriterleri

1. Belgelenen tek bir komutla PostgreSQL entegrasyon testleri koşuyor.
2. `DATA_QUALITY_POSTGRES_TEST_URL` tanımlıyken atlanan test sayısı 121'den 0'a iniyor
   (senaryo gereği atlanması gerekenler hariç — gerekçesi yazılacak).
3. Tüm PostgreSQL entegrasyon testleri geçiyor.
4. Ortam değişkeni tanımlı değilken `python -m pytest` hâlâ tamamen yeşil.
5. PostgreSQL depolarının toplam satır kapsamı ölçülüp raporlanmış; %25,7'nin belirgin
   şekilde üzerinde.
6. Testler arası izolasyon doğrulanmış: aynı test iki kez üst üste koşturulduğunda
   aynı sonucu veriyor.

## Teslim Formatı

- **Kod:** Değiştirilen/eklenen dosyalar ve gerekçesi.
- **Komut:** Testleri koşturmak için tek komut.
- **Test çıktısı:** Ham `pytest` sonucu (öncesi ve sonrası).
- **Hata sınıflandırması:** Bulunan her başarısızlık — üretim hatası mı, test kurgusu
  hatası mı, gerekçesiyle.
- **Kapsam raporu:** PostgreSQL depoları öncesi/sonrası yüzde.
- **Varsayımlar:** Yapılan varsayımlar ve açık kalan sorular.

## Çalışma Kuralları

- Mevcut kod stiline uy.
- Yeni üçüncü parti bağımlılık ekleme.
- Testleri çalıştır ve sonucu olduğu gibi bildir — geçmeyen testi geçmiş gibi raporlama.
- Belirsizlik varsa varsayımını açıkça yaz ve devam et.

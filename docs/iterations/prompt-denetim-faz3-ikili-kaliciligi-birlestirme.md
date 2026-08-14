# Denetim Faz 3: İkili Kalıcılık Katmanı Kararı

## Bağlam

Sistemde her alan için iki kalıcılık uygulaması var ve **ikisi de bakım yükü taşıyor**:

| Katman | Satır | Üretimde bağlı mı? | Kapsam |
| --- | --- | --- | --- |
| `<alan>/repository.py` (SQLite) | 7.476 | **Hayır** | %85,1 |
| `<alan>/postgresql_repository.py` | 7.505 | Evet | %25,7 |

SQLite depoları: `SQLiteAuditRepository`, `SQLiteDataSourceRepository`,
`SQLiteExecutionRepository`, `SQLiteIncidentResponseRepository`,
`SQLiteNotificationRepository`, `SQLiteLegalHoldRepository`, `SQLiteRuleRepository`,
`SQLiteScoreRepository`, `SQLiteServiceNowRepository`, `SQLiteSyntheticDataRepository`.

Bugün her şema değişikliği iki kez yazılmak zorunda ve iki uygulamanın davranışının
aynı kaldığını doğrulayan hiçbir mekanizma yok.

### Bu ayrışmanın ürettiği somut hata

`mypy` bunu zaten yakalıyor:

```
src/veri_kalitesi/jobs/production.py:238: error: Argument "repository" to
  "ScoringService" has incompatible type "PostgreSQLScoreRepository";
  expected "SQLiteScoreRepository"  [arg-type]
```

Yani `ScoringService` SQLite deposuna göre tiplenmiş, üretimde ise PostgreSQL deposu
veriliyor. Tip sistemi bu uyumsuzluğu bildiriyor ama hiçbir kapı onu durdurmuyor.
Bu, ikili katmanın teorik değil **fiili** bir risk olduğunun kanıtı.

**Bağımlılık:** Faz 2 tamamlanmış olmalı. PostgreSQL testleri çalışmadan bu karar
güvenle verilemez — SQLite katmanı kaldırılacaksa, önce PostgreSQL yolunun gerçekten
test edilmiş olması gerekir.

## Görev

1. **Her SQLite deposunun gerçek rolünü tespit et.** Her biri için şu üç kategoriden
   birine yerleştir ve kanıtını yaz:
   - **(a) Yalnızca test ikizi** — üretimde karşılığı olan bir PostgreSQL deposu var,
     SQLite sürümü sadece testlerde kullanılıyor.
   - **(b) Tek uygulama** — PostgreSQL karşılığı yok; bu alan hiç üretime bağlanmamış
     (örn. `incident_response`, `retention`, `servicenow` — bkz. Faz 9).
   - **(c) Geliştirici aracı** — script/lab yolundan meşru şekilde kullanılıyor
     (örn. `synthetic_data`).

2. **Kategori (a) için karar ver ve uygula.** İki seçenekten birini seç, gerekçesini yaz:
   - **Kaldır:** SQLite uygulamasını sil, testleri PostgreSQL'e taşı. ~7.500 satır
     bakım yükü kalkar; testler yavaşlar.
   - **Koru + eşitlik doğrula:** İki uygulamayı aynı sözleşme testine tabi tutan
     paylaşılan bir test paketi yaz, böylece davranış ayrışması otomatik yakalanır.

   **Öneri:** Ölçüm, kaldırma yönünü destekliyor — SQLite katmanı üretimde hiç
   çalışmıyor ve tip uyumsuzluğu şimdiden oluşmuş. Ancak testlerin PostgreSQL'e
   taşınmasının koşum süresine etkisini ölç ve raporla; sonuç kabul edilemezse
   ikinci seçeneğe dön.

3. **Servis tiplerini üretim gerçeğine hizala.** `ScoringService` ve benzer şekilde
   somut depo sınıfına bağlanmış tüm servisleri, somut sınıf yerine `Protocol` üzerinden
   tiplendir. `production.py:238` mypy hatası bu adımla kapanmalı.

4. **Kategori (b) ve (c) için dokunma**, yalnızca tespitini raporla — bunlar Faz 9'un
   konusu.

## Invariantlar

- **Davranış değişmeyecek.** Bu bir refactor'dır; üretim davranışında değişiklik yok.
- Şema kayması oluşmayacak: alembic migration'ları ile depo tablo tanımları tutarlı kalacak.
- Mevcut tüm testler geçmeye devam edecek (taşınanlar dahil).
- Denetim (audit) zinciri, kira/kalp atışı ve idempotency davranışı korunacak.
- `Protocol` tabanlı tipleme somut sınıfa bağımlılığı azaltmalı, gizlememeli —
  `object` veya `Any` ile geçiştirme yapılmayacak (bkz. Faz 7).
- Yeni üçüncü parti bağımlılık yok.

## Kabul Kriterleri

1. Her SQLite deposu için kategori tespiti ve kanıtı raporlanmış.
2. Seçilen yol uygulanmış; gerekçesi ölçümle desteklenmiş.
3. `mypy src/` çıktısında `production.py:238` `arg-type` hatası yok.
4. `python -m pytest` tamamen yeşil (PostgreSQL testleri dahil).
5. Kaldırma seçildiyse: silinen satır sayısı raporlanmış, hiçbir üretim yolu etkilenmemiş.
6. Koruma seçildiyse: iki uygulamayı aynı sözleşmeye tabi tutan test paketi mevcut ve
   kasıtlı bir davranış ayrışması eklendiğinde başarısız olduğu gösterilmiş.
7. Test koşum süresi öncesi/sonrası raporlanmış.

## Teslim Formatı

- **Tespit tablosu:** Depo → kategori → kanıt.
- **Karar:** Seçilen yol ve gerekçesi.
- **Kod:** Değiştirilen/silinen dosyalar.
- **Test çıktısı:** Ham `pytest` ve `mypy` sonuçları.
- **Ölçüm:** Silinen satır sayısı, test koşum süresi öncesi/sonrası.
- **Varsayımlar:** Yapılan varsayımlar ve açık kalan sorular.

## Çalışma Kuralları

- Mevcut kod stiline uy.
- Yeni üçüncü parti bağımlılık ekleme.
- Testleri çalıştır ve sonucu olduğu gibi bildir.
- Belirsizlik varsa varsayımını açıkça yaz ve devam et.
- Bu faz geri alınması zor bir silme içerebilir — silmeden önce kategori tespitini
  tamamla ve raporla.

# Dokümantasyon Konsolidasyon Denetimi — 24 Temmuz 2026

## Özet

Bu tur, ilk temizlikten sonraki depoyu güncel kararlar ve son yedi iterasyon
üzerinden yeniden düzenledi. Proje kapsamı, gereksinim, güvenlik/uyum kuralı veya
iş kuralı değiştirilmedi.

| Ölçüm | Önce | Sonra | Etki |
| --- | ---: | ---: | ---: |
| Aktif Markdown dosyası | 235 | 219 | 16 dosya daha az (%6,8) |
| Aktif Markdown boyutu | 1.130.546 bayt | 990.116 bayt | 140.430 bayt daha az (%12,4) |
| Aktif Markdown satırı | 18.677 | 16.261 | 2.416 satır daha az (%12,9) |
| `09-Iterasyonlar` satırı | 2.765 | 343 | 2.422 satır daha az (%87,6) |
| Tarihsel iterasyon taşıması | 0 | 18 dosya | numara bazlı arşiv |

Aktif iterasyon bağlamı `36A2a`, `36A2b`, `36B1`, `36B2`, `36B3`, `36B4`
ve `36B5` ile sınırlandı. İterasyon 36 ana planı kapanış kaydı değil, bu yedi
artımın aktif üst planıdır.

## Kronoloji ve Arşivleme

Kronoloji; `completed_at`, iterasyon numarası, dosya adı ve dosyaların birbirine
verdiği “sıradaki artım” referanslarıyla doğrulandı. `36B5` için kod/test yüzeyi
mevcut olduğu halde kapanış kaydı bulunmadığından yeni karar uydurulmadı;
[doğrulama bekleyen kayıt](09-Iterasyonlar/Iterasyon-36B5-Kapatma-ve-Yeniden-Acma.md)
oluşturuldu.

- 16–35, bakım 29C.1 ve 36A1 kayıtları
  [archive/iterations](archive/iterations/README.md) altına taşındı.
- Arşiv içi ve arşive gelen göreli bağlantılar yeni konuma göre yeniden yazıldı.
- Geçerli bağlayıcı bilgi SRS, ADR ve karar kayıtlarında tutuldu; arşiv güncel
  backlog veya durum kaynağı olarak kullanılmıyor.
- Eski birleşik yol haritası anlatısı aktif P0–P4 çalışma paketlerine indirildi.

## Yeni Kararların Etkisi

Yeni bir karar üretilmedi. En güncel kesin karar paketi olan PostgreSQL-only ve
yazılabilir UI yönünün depo etkisi konsolide edildi:

| Karar alanı | Gerçek durum | Doküman işlemi |
| --- | --- | --- |
| `PG-MIG-001–005` issue geçişi | Seçici aktarım ve issue PostgreSQL-only runtime yolu uygulanmış | Son yedi iterasyonda kısa kanıt kaydı; eski ayrıntı arşivde |
| `UI-WRITE-001–003` issue akışları | İnceleme, atama, çözüm, doğrulama, kapatma ve yeniden açma yüzeyi mevcut | Backlogdaki “özellik geliştir” ifadesi doğrulama borcuna çevrildi |
| `UI-WRITE-006` execution | API, migration ve repository var; 36E ile production cutover tamamlandı, SQLite runtime export kaldırıldı. | Çözüldü — 36E kapanış kaydı oluşturuldu |
| `UI-WRITE-007` dışa aktarma | Kurumsal DLP/watermark/maker-checker kapıları açık | `Blocked` ve fail-closed tutuldu |

Durum özeti karar kaydına eklendi; kesin kararın kendisi veya gerekçesi
değiştirilmedi.

## Uyumsuzluklar

| ID | Seviye | Konu | Bulgu | İşlem | Durum |
| --- | --- | --- | --- | --- | --- |
| CONS-HIGH-001 | HIGH | Execution PostgreSQL cutover | Migration/repository/test mevcut; `api/development.py` production benzeri composition root'ta `DevelopmentExecutionStore` kullanıyor, SQLite repository export/test yollarında sürüyor. | [NEXT_STEP.md](NEXT_STEP.md) tek P0 paket olarak oluşturuldu. | Çözüldü — 36E ile PostgreSQL adaptörleri, cutover ve SQLite runtime export kaldırma tamamlandı |
| CONS-MED-001 | MEDIUM | 36B5 kapanış kaydı | Kapatma/yeniden açma kod ve testlerde mevcut, ayrı güncel kapanış yoktu. | `VerificationPending` kaydı ve test kapanış koşulu oluşturuldu. | Kısmen çözüldü; güncel koşu gerekli |
| CONS-MED-002 | MEDIUM | Eski sıradaki adım | Backlog yeniden açmayı yeni özellik, tamamlanmış işleri aktif sıra gibi gösteriyordu. | Backlog, roadmap, README, mevcut durum ve ana iterasyon birlikte güncellendi. | Çözüldü |
| CONS-LOW-001 | LOW | Aktif iterasyon yükü | 18 tarihsel kayıt aktif klasörde ve indeksde tutuluyordu. | Arşivlendi; aktif indeks yalnız son yediyi listeliyor. | Çözüldü |
| CONS-LOW-002 | LOW | Tekrar eden iterasyon kabul/görsel/test anlatısı | Son yedi kayıtta ortak güvenlik ve doğrulama metinleri tekrar ediyordu. | Kayıtlar sonuç/bağlantı/kanıt/sınır biçimine kısaltıldı. | Çözüldü |

## Sıradaki Adımın Yeniden Hesaplanması

Çözülen uyumsuzluk `CONS-HIGH-001` (Execution PostgreSQL cutover) 36E ile
kapatılmıştır. Yeni sıradaki çalışma paketi:
[Execution politika ve worker dayanıklılığı](NEXT_STEP.md).

Gerekçe sırası:

1. Execution cutover HIGH uyumsuzluk olarak çözülmüştür.
2. Worker dayanıklılığı (kota, pencere, retry, kalıcı kuyruk) bir sonraki
   uygulanabilir pakettir.
3. 36F (güvenli rapor) kurumsal DLP/watermark/maker-checker kapıları açık
   olduğundan blokeli kalır.

`NEXT_STEP.md`; adım, amaç, gerekçe ve tamamlama ölçütlerini içerir.

## Değiştirilen Ana Dosyalar

- `README.md`, `AGENTS.md`, `DOCUMENTATION_INDEX.md`
- `00-Proje-Hafizasi/Mevcut-Durum.md`, `Sonraki-Adimlar.md`
- `NEXT_STEP.md`
- `09-Iterasyonlar/ITERASYON-INDEX.md`, İterasyon 36 ana planı ve aktif yol haritası
- En güncel yedi iterasyon kaydı
- API/frontend/PostgreSQL karar kaydı durum özeti
- Backend, frontend ve test indeksleri
- `scripts/check_documentation.py`
- `archive/iterations/README.md` ve 18 tarihsel kayıt
- **36E kapanış kaydı** (`09-Iterasyonlar/Iterasyon-36E-Calisma-PostgreSQL-Cutover.md`)
- **36A2a arşiv taşıması** (`archive/iterations/36/`)
- **SQLiteExecutionRepository runtime export kaldırma** (`executions/__init__.py`, test import'ları)

İlk temizlik denetimi
`archive/documentation/DOCUMENTATION_AUDIT-2026-07-24-initial-cleanup.md`
altında korunmuştur.

## Doğrulama Sonuçları

| Kontrol | Sonuç |
| --- | --- |
| Aktif yerel Markdown bağlantıları | 454 bağlantı, 0 kırık |
| Arşiv/snapshot dahil bağlantılar | 570 bağlantı, 0 kırık |
| Kanonik kimlikler | 533 tanım; 533 açık referans çözüldü; çift/tanımsız yok |
| Aktif iterasyon sayısı | 7 kapanış/artım kaydı; parent plan, indeks, roadmap ve şablon sayım dışı |
| Arşiv indeksi | 18 dosya; tarih/sıra, durum, korunan bilgi ve kanonik kaynak alanları mevcut |
| Python sözdizimi | `python -m compileall -q 03-Backend/src scripts 06-Testler` başarılı |
| 36B5 hedefli pytest | Koleksiyon `ModuleNotFoundError: psycopg` ile durdu; kod testi başarısızlığı olarak yorumlanmadı |
| Bağımlılık kurulumu | Paket indeksinde `psycopg[binary]` ve `tomli` sürümü bulunamadı; kurulamadı |
| Frontend test/build | `node_modules` yok; bu turda çalıştırılmadı |

Bu nedenle `36B5` durumu `TechnicallyVerified` yapılmadı. Son belgelenmiş
`1125 passed, 27 skipped` ve frontend `95` testi yalnız tarihsel baseline olarak
korunur.

## İnsan Kararı Gereken Konular

- Execution politika/worker dayanıklılığı; teknik uygulama gerektirir, yeni iş kuralı kararı gerektirmez.
- Açık bankacılık/uyum kayıtlarındaki IdP grup-rol-scope, saklama/fiziksel imha,
  ServiceNow, RPO/RTO, BCBS 239 ve kurumsal ürün kararları yetkili sahiplerde kalır.
- DLP/watermark ve hassas rapor maker-checker kapıları çözülmeden 36F açılmaz.

## Bütünlüğe Etki

Aktif bağlam tarihsel teslimat günlüğünden güncel karar, gerçek durum ve tek
uygulanabilir çalışma paketine dönüştü. Arşivleme izlenebilirliği korurken ajanların
eski test sayıları, tamamlanmış görevler veya geçersiz “sıradaki adım” anlatılarını
aktif bağlama taşımasını engeller. Güvenlik, uyum, kabul kriteri, veri sözleşmesi
ve kaynak sistemlere salt okunur erişim ilkesi korunmuştur.

# İterasyon 33 — Kanonik Kural Skoru

## 33A — Standart ölçüm durumları ve kural skoru paydası

- **İterasyon adı:** Standart ölçüm durumları ve kural skoru paydası
- **Kullanıcı/sistem değeri:** Kapsam dışı, teknik hatalı veya uygulanabilirliği
  bilinmeyen kayıtlar kalite başarısızlığı gibi paydaya eklenmeden açıklanabilir
  ve deterministik kural skoru üretilir.
- **Mevcut FR/UC/RULE:** `FR-046`–`FR-048`, `UC-009`, `RULE-003/004`,
  `DQ-SCR-004`–`DQ-SCR-006`, `AC-039/040`
- **BFR/CTRL:** Yeni eşleme yoktur.
- **Değiştirilen dosyalar:** Execution ve scoring model/depo/servisleri, paket
  dışa aktarımları, birim testleri ve proje hafızası.
- **Migration/config:** SQLite execution ve score tablolarına kanonik nullable
  sayaçlar ile ölçüm durumu eklendi. Eski satırlar tahminî sıfırla doldurulmadı.
- **Eklenen testler:** Koşullu evren ve teknik hata paydası, beş sıfır payda
  durumu, bilinmeyen teknik sayacın `NULL` korunması ve eski şema geçişi.
- **Çalıştırılan komutlar:** Hedefli ve tam `pytest -q`, tam `mypy`, tam
  `ruff check`, değişen kapsam formatı ve tam depo format kontrolü.
- **Mevcut regresyon sonucu:** 920 test geçti; mypy 131 dosyada ve Ruff lint
  hatasız tamamlandı. Tam depo format kontrolü değişiklik dışındaki bir tarihsel
  dosyada biçim farkı bildirdi. `28A-v1` taraması 382 dosyada secret bulgusu
  üretmedi.
- **Güvenlik/veri gizliliği sonucu:** Yeni sayaç ve durumlar yalnız agregat teknik
  metadata taşır; ham kayıt, kişisel veri, müşteri sırrı veya secret eklenmedi.
- **Kanıt yolları:** `06-Testler/01-Birim/test_scoring.py` ve
  `06-Testler/01-Birim/test_executions.py`.
- **Teknik durum:** `TechnicallyVerified`
- **Banka onayı:** `ComplianceReviewRequired`
- **Kalan risk:** Tarihsel sonuç backfill/sürüm sınırı `OPEN-022`; üretim
  normalizasyonu ve yeterlilik değerleri `OPEN-019/023` altında açıktır.
- **Geri alma yaklaşımı:** Yeni formül composition'dan çıkarılarak yeni skor
  üretimi durdurulabilir; mevcut execution ve skor kayıtları silinmez. Eski
  kanoniksiz satırlar otomatik yeniden skorlanmaz.
- **Sonraki iterasyon:** Skorlama devamı kararları bekler; sıradaki hazır artım
  `SYN-001` sentetik dataset politika, senaryo ve run kayıt çekirdeğidir.

---
iteration: 31
status: TechnicallyVerified
completed_at: 2026-07-21
---

# İterasyon 31 — Kaynak Kullanım Politikası

## 31A — Sürümlü politika ve güvenli kota çözümleme

- **İterasyon adı:** Sürümlü kaynak kullanım politikası ve güvenli kota çözümleme
- **Kullanıcı/sistem değeri:** Worker süreçleri örtük veya kontrolsüz kaynak
  kotasıyla iş almaz; onay referanslı aktif global politika ve daha dar kaynak
  override sınırları deterministik uygulanır.
- **Mevcut FR/UC/RULE:** `FR-039`, `UC-008`, `RULE-012`, `NFR-PERF-006`,
  `NFR-PERF-008`
- **BFR/CTRL:** Yeni eşleme yoktur.
- **Değiştirilen dosyalar:** Çalıştırma modelleri, servis, kuyruk deposu, yeni
  kaynak kullanım politika deposu, birim testleri ve proje hafızası.
- **Migration/config:** SQLite `source_usage_policies` tablosu ile kapsam/sürüm
  ve tek aktif kapsam indeksleri eklendi. Üretim değeri veya ürün adı eklenmedi.
- **Eklenen testler:** Politika alanlarının kalıcılığı, kaynak kimliği önceliği,
  sürüm emekliliği, toplam worker kotası, politikasız fail-closed claim,
  onaysız aktif politika reddi ve depo teknik hatası.
- **Çalıştırılan komutlar:** `pytest -q`, `mypy 03-Backend/src
  06-Testler/01-Birim`, `ruff check .`, `ruff format` ve `compileall`.
- **Mevcut regresyon sonucu:** 863 test geçti; mypy 129 dosyada, Ruff ve derleme
  hatasız tamamlandı.
- **Yetkisiz/negatif test sonucu:** Onay/audit referansı eksik aktif politika ve
  aktif global politika bulunmayan claim reddedildi; kuyruktaki iş değiştirilmedi.
- **Audit/redaksiyon sonucu:** Politika yalnız opak onay ve audit referansı
  taşır; secret veya kaynak bağlantı bilgisi eklenmedi. Merkezi audit outbox
  entegrasyonu bu dilimde uygulanmadı.
- **Kanıt yolları:** `06-Testler/01-Birim/test_source_usage_policies.py` ve
  `06-Testler/01-Birim/test_executions.py`.
- **Teknik durum:** `TechnicallyVerified`
- **Banka onayı:** `ComplianceReviewRequired`
- **Kalan risk:** Üretim kota değerleri; PostgreSQL migration ve çoklu instance
  eşzamanlılığı; çalışma penceresi, yoğun saat, CPU/IO, hız sınırı, timeout ve
  retry çalışma zamanı uygulaması; merkezi politika değişikliği auditi.
- **Geri alma yaklaşımı:** Kalıcı çözümleyici worker yapılandırmasından çıkarılır;
  mevcut güvenli yerel `ConcurrencyPolicy` yolu korunur. Şema silinmez.
- **Sonraki iterasyon:** 31B, kaynak çalışma penceresi ve yoğun saat kararının
  fail-closed uygulanması.

## 31B — Kaynak çalışma penceresi ve yoğun saat koruması

- **İterasyon adı:** Kaynak çalışma penceresi ve yoğun saat koruması
- **Kullanıcı/sistem değeri:** Worker yalnız kaynak politikasının açıkça izin
  verdiği zamanda iş alır; yasaklı/yoğun saatlerde kaynak sorgusu başlatılmaz.
- **Mevcut FR/UC/RULE:** `FR-039`, `UC-008`, `RULE-012`, `RULE-015`,
  `NFR-PERF-008`
- **BFR/CTRL:** Yeni eşleme yoktur.
- **Değiştirilen dosyalar:** Kaynak kullanım politika modeli/çözümleyicisi,
  concurrency policy, worker claim filtresi, execution servisi, testler ve proje
  hafızası.
- **Migration/config:** Mevcut JSON pencere alanları IANA saat dilimi, ISO hafta
  günü ve yerel başlangıç/bitiş saatini taşıyan yapılandırılmış payload olarak
  kullanıldı; yeni tablo veya üretim değeri eklenmedi.
- **Eklenen testler:** Yasaklı pencere önceliği, pencere dışı ve boş pencere
  fail-closed davranışı, dahil/hariç sınırlar, gece yarısını aşan pencere, kaynak
  override ile kuyruk atlama, UTC zorunluluğu ve geçersiz IANA saat dilimi.
- **Çalıştırılan komutlar:** `pytest -q`, `mypy 03-Backend/src
  06-Testler/01-Birim`, `ruff check .`, değişen yeni dosyalarda `ruff format` ve
  `compileall`.
- **Mevcut regresyon sonucu:** 871 test geçti; mypy 129 dosyada, Ruff ve derleme
  hatasız tamamlandı.
- **Yetkisiz/negatif test sonucu:** İzin verilmeyen zaman, boş izin listesi,
  yasaklı pencere, UTC olmayan saat ve geçersiz saat dilimi fail-closed reddedildi.
- **Audit/redaksiyon sonucu:** Claim kararı yalnız politika penceresi ve kaynak
  kimliğiyle verilir; secret, bağlantı bilgisi veya ham kaynak verisi eklenmedi.
  Ayrı claim karar audit/metric olayı bu dilimde uygulanmadı.
- **Kanıt yolları:** `06-Testler/01-Birim/test_source_usage_policies.py` ve
  `06-Testler/01-Birim/test_executions.py`.
- **Teknik durum:** `TechnicallyVerified`
- **Banka onayı:** `ComplianceReviewRequired`
- **Kalan risk:** Üretim pencere değerleri, tatil/istisna günleri, banka onaylı
  yoğun saat davranış sözlüğü, terminal ret modeli, karar metriği/alarmı ve çoklu
  instance politika önbelleği.
- **Geri alma yaklaşımı:** Kalıcı politika çözümleyicisi worker yapılandırmasından
  çıkarılır; mevcut güvenli yerel `ConcurrencyPolicy` yolu korunur. Şema silinmez.
- **Sonraki iterasyon:** 31C, kaynak politikasındaki timeout ve retry değerlerinin
  worker yürütmesine bağlanması.

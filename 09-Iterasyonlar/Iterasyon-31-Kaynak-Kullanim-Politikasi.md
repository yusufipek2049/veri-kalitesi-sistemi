---
iteration: 31A
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

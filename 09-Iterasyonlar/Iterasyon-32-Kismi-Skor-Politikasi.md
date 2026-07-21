---
iteration: 32
status: TechnicallyVerified
completed_at: 2026-07-21
---

# İterasyon 32 — Kısmi Skor Politikası

## 32A — Dataset kısmi skor politika kararı

- **İterasyon adı:** Dataset kısmi skor politika kararı
- **Kullanıcı/sistem değeri:** Kısmi çalışma, onaylı dataset politikasındaki tüm
  koşullar sağlanmadan resmî kabul edilemez; karar nedenleri deterministik ve
  açıklanabilirdir.
- **Mevcut FR/UC/RULE:** `FR-048`, `UC-009`, `OPEN-012`, `OPEN-018`
- **BFR/CTRL:** Yeni eşleme yoktur.
- **Değiştirilen dosyalar:** Skorlama hata/paket yüzeyi, yeni kısmi skor politika
  modeli/deposu/servisi, birim testleri ve proje hafızası.
- **Migration/config:** SQLite `dataset_partial_score_policies` tablosu eklendi.
  Üretim eşik değeri veya ürün adı eklenmedi; test değerleri yalnız sentetiktir.
- **Eklenen testler:** Sürüm/geçerlilik çözümleme, tüm koşullarda resmî karar,
  yedi ayrı koşul ihlalinde provizyonel karar, politikasız fail-closed davranış,
  onaysız politika dışlama, maker-checker ayrımı, çelişkili olgu doğrulaması ve
  depo teknik hatası.
- **Çalıştırılan komutlar:** `pytest -q`, `mypy 03-Backend/src
  06-Testler/01-Birim`, `ruff check .`, hedefli `ruff format` ve `python3 -m
  compileall -q 03-Backend/src`.
- **Mevcut regresyon sonucu:** 888 test geçti; mypy 131 dosyada, Ruff ve derleme
  hatasız tamamlandı.
- **Yetkisiz/negatif test sonucu:** Onaysız politika etkili seçilmedi; maker kendi
  politikasını onaylayamadı; politika yokluğu ve her koşul ihlali provizyonel
  kararla sonuçlandı.
- **Audit/redaksiyon sonucu:** Politika yalnız opak kural/partition, aktör ve audit
  referansları ile oranları taşır; ham kayıt, secret veya bağlantı bilgisi içermez.
- **Kanıt yolları:** `06-Testler/01-Birim/test_partial_score_policies.py`.
- **Teknik durum:** `TechnicallyVerified`
- **Banka onayı:** `ComplianceReviewRequired`
- **Kalan risk:** Ölçülmüş olguların worker/execution tarafından üretilmesi,
  kararın `QualityScore`, resmî agregasyon, trend, SLA ve raporlamaya bağlanması,
  politika yaşam döngüsünün merkezi audit outbox'ı ve banka rol eşlemesi.
- **Geri alma yaklaşımı:** Kısmi politika servisi skor akışına henüz bağlı değildir;
  modül kaldırıldığında mevcut tüm kısmi sonuçları resmî skordan dışlayan güvenli
  davranış değişmeden kalır. SQLite tablosu silinmez.
- **Sonraki iterasyon:** 32B, kısmi skor politika kararının `QualityScore`
  üretimine ve resmî agregasyon dışlama bilgisine bağlanması.

## 32B — Kısmi skorun resmî agregasyon zincirine bağlanması

- **İterasyon adı:** Kısmi skorun resmî agregasyon zincirine bağlanması
- **Kullanıcı/sistem değeri:** Onaylı kısmi sonuç, kısmi niteliğini ve karar
  gerekçesini kaybetmeden resmî skor zincirine katılır; provizyonel sonuç resmî
  trendi veya raporu değiştiremez.
- **Mevcut FR/UC/RULE:** `FR-047`–`FR-050`, `FR-054`, `FR-055`, `FR-072`,
  `UC-009`
- **BFR/CTRL:** Yeni eşleme yoktur.
- **Değiştirilen dosyalar:** Skor modeli/servisi/deposu, dashboard trend reader'ı,
  rapor reader/servisi, birim testleri ve proje hafızası.
- **Migration/config:** Yeni migration veya üretim konfigürasyonu eklenmedi.
- **Eklenen testler:** Resmî kısmi kural skorunun dataset, kaynak ve kurum
  agregasyonuna yayılması; politikasız provizyonel davranış; politika depo
  hatasında yazmama; provizyonel trend/rapor dışlama; resmî kısmi trend ve rapor
  görünürlüğü.
- **Çalıştırılan komutlar:** `pytest -q`, tam `mypy`, tam `ruff check`, değişen
  kapsam için `ruff format --check` ve `git diff --check`.
- **Mevcut regresyon sonucu:** 895 test geçti; mypy 131 dosyada ve Ruff lint
  hatasız tamamlandı. Tam depo format kontrolü değişmeyen üç tarihsel dosyada
  biçim farkı bildirdi; değişen kapsam temizdir.
- **Yetkisiz/negatif test sonucu:** Politika yokluğu provizyonel sonuç verdi;
  provizyonel sonuç resmî trend ve rapordan çıkarıldı; politika depo arızasında
  skor yazılmadı.
- **Audit/redaksiyon sonucu:** Skor ayrıntıları yalnız oran, adet, politika sürümü,
  karar kodu ve opak kural/partition kimliği taşır; ham kayıt veya secret içermez.
- **Kanıt yolları:** `06-Testler/01-Birim/test_scoring.py`,
  `06-Testler/01-Birim/test_dashboard.py`, `06-Testler/01-Birim/test_reporting.py`.
- **Teknik durum:** `TechnicallyVerified`
- **Banka onayı:** `ComplianceReviewRequired`
- **Kalan risk:** `PartialExecutionFacts` olgularının worker/execution tarafından
  güvenilir üretimi, SLA ve resmî denetim çıktısı adaptörleri, merkezi audit
  outbox'ı ve banka rol eşlemesi.
- **Geri alma yaklaşımı:** Politika servisi scoring composition'dan çıkarılırsa
  mevcut güvenli varsayılan tüm kısmi sonuçları sayısal resmî skordan dışlar;
  mevcut skor kayıtları silinmez.
- **Sonraki iterasyon:** 32C, güvenilir kısmi çalışma olgusu üretimi ve politika
  karar auditi.

## 32C — Kısmi skor politikası onay/ret ve atomik audit

- **İterasyon adı:** Kısmi skor politikası onay/ret ve atomik audit
- **Kullanıcı/sistem değeri:** Resmî skoru etkileyen dataset politikası yalnız
  güvenilir, kapsamlı ve birbirinden farklı maker/checker aktörleriyle etkili
  olur; audit kaydı olmadan kritik değişiklik tamamlanmaz.
- **Mevcut FR/UC/RULE:** `FR-048`, `FR-077`, `UC-009`, `RULE-005`, `OPEN-012`,
  `OPEN-017`
- **BFR/CTRL:** Yeni eşleme yoktur.
- **Değiştirilen dosyalar:** Kısmi skor politika modeli/deposu/yaşam döngüsü,
  merkezi audit allowlist'i, paket dışa aktarımı, birim testleri ve proje hafızası.
- **Migration/config:** Mevcut SQLite politika tablosu kullanıldı; üretim rolü,
  ürün veya eşik değeri eklenmedi.
- **Eklenen testler:** Talep-onay akışı, onaysız politikanın etkisizliği,
  maker-checker ayrımı, eksik rol/kapsam/bağlam ile servis ve ayrıcalıklı aktör
  reddi, veri-minimum audit ve audit staging hatasında atomik rollback.
- **Çalıştırılan komutlar:** `pytest -q`, tam `mypy`, tam `ruff check`, değişen
  kapsam için `ruff format --check` ve `git diff --check`.
- **Mevcut regresyon sonucu:** 904 test geçti; mypy 131 dosyada, Ruff ve değişen
  kapsam format/derleme kontrolü hatasız tamamlandı. Tam depo format kontrolü
  değişmeyen üç tarihsel dosyada biçim farkı bildirdi.
- **Yetkisiz/negatif test sonucu:** Maker kendi politikasını karara bağlayamadı;
  eksik/güvenilmez, yanlış rol veya kapsamlı, servis ve ayrıcalıklı bağlamlar
  repository yazımından önce reddedildi.
- **Audit/redaksiyon sonucu:** Talep ve karar politika kaydıyla aynı transaction'da
  outbox'a yazıldı. Audit oran, adet, durum ve sürüm taşır; kural/partition
  kimliklerini, ham kayıt veya secret'ı taşımaz.
- **Kanıt yolları:** `06-Testler/01-Birim/test_partial_score_policies.py`.
- **Teknik durum:** `TechnicallyVerified`
- **Banka onayı:** `ComplianceReviewRequired`
- **Kalan risk:** Geri çekme ve süre aşımı, banka rol eşlemesi,
  PostgreSQL/çoklu instance eşzamanlılığı ve güvenilir `PartialExecutionFacts`
  üretim formülleri.
- **Geri alma yaklaşımı:** Yaşam döngüsü servisi composition'dan çıkarılırsa yeni
  politika talebi alınmaz; mevcut onaylı politikalar ve skor geçmişi silinmez.
- **Sonraki iterasyon:** 32D, kısmi skor politika talebini auditli geri çekme.

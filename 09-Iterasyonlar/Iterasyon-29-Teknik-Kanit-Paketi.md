# İterasyon 29 — Teknik Kontrol ve Banka Kabul Kanıt Paketi

## 29A — Teknik kanıt paketi manifesti ve eksik kontrol raporu

Durum: `TechnicallyVerified`

### Gereksinimler

- `BFR-SDLC-002`
- `BRULE-004`
- `BRULE-005`
- `NFR-CMP-002`
- `NFR-CMP-005`
- BDDK ve KVKK matrislerindeki 15 `CTRL-*` kaydı

### Kabul Sonucu

- Sürümlü JSON katalog tam 8 BDDK ve 7 KVKK kontrolünü kapsar; eksik veya fazla
  kontrol kaydı fail-closed reddedilir.
- Kanıt yolları yalnız `08-Uyum-Kanitlari/` altındaki göreli `.md/.json`
  artifact'larına açılır; traversal, mutlak yol, symlink, büyük ve eksik dosya
  reddedilir.
- Manifest her artifact'ı SHA-256 ile bağlar ve kontrol sırasından bağımsız,
  deterministik JSON üretir; kanıt içeriğini manifestte çoğaltmaz.
- Teknik durum, banka inceleme durumu ve açık `OPEN-BNK-*` engelleri ayrı tutulur.
- `ApprovedByBank` ve `NotApplicable` yalnız opak karar referansıyla kabul edilir.
- Mevcut katalog 15 kontrolün 12'sini `Partial`, 3'ünü `Missing`, 14'ünü açık
  kararlarla engelli ve tamamını `ComplianceReviewRequired` olarak raporlar.
- 37 yeni sentetik vakayla toplam 667 birim testi geçmiştir.

### Kapsam Dışı

- Banka adına kontrol onayı veya mevzuat uyumluluğu kararı
- Elektronik imza, WORM, HSM veya kurumsal kanıt deposu
- CI/CD artifact yayınlama ve drift kapısı
- Eksik DR, imha, aktarım, gerçek scanner/pentest ve üretim entegrasyonlarının uygulanması
- Onaylayan kimlik çözümleyicisi, maker-checker ve banka iş akışı

## Önerilen Sonraki Dilim

**29B — Teknik kanıt manifesti drift doğrulama kapısı.**

Sürümde saklanan manifesti katalog ve kanıt artifact'larından yeniden üretip byte
düzeyinde karşılaştıran fail-closed doğrulama komutu ekle. CI/CD ürünü, imzalama,
istisna/risk kabulü ve banka onayı kapsam dışında kalsın.

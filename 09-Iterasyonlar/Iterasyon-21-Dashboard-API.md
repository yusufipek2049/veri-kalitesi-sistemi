---
iteration: 21B-21C
status: TechnicallyVerified
completed_at: 2026-07-22
---

# İterasyon 21 — Dashboard API Dikey Dilimleri

## İterasyon 21B — Güvenli Dashboard Özet API Dikey Dilimi

- **İterasyon adı:** 21B — FastAPI dashboard özeti ve bağlı frontend
- **Kullanıcı/sistem değeri:** Yetkili dashboard trendi yerel geliştirmede gerçek
  HTTP sözleşmesi üzerinden görüntülenebilir; üretim oturumu yokluğu fail-closed kalır.
- **Mevcut FR/UC/RULE:** `FR-054`, `FR-055`, `FR-080`–`FR-082`, `UC-010`,
  `RULE-009`, `NFR-USA-003/004/006`
- **BFR/CTRL:** `BFR-IAM-001/002/004/006`, `CTRL-BDDK-IAM-001`
- **Değiştirilen dosyalar:** `veri_kalitesi.api` paketi, dashboard frontend API
  istemcisi/view-model'i, frontend ve backend testleri, doğrudan bağımlılık SBOM'u
  ve proje hafızası.
- **Migration/config:** FastAPI `0.135.3` ve Alembic `1.18.4` doğrudan bağımlılık
  olarak eklendi. Şema değişikliği olmadığı için Alembic migration üretilmedi.
- **Eklenen testler:** Altı backend HTTP güvenlik/sözleşme testi, dört yeni
  frontend API/view-model testi ve güncellenen yedi Playwright senaryosu.
- **Çalıştırılan komutlar:** `pytest`, Ruff lint/format, tam mypy, `compileall`,
  Vitest, TypeScript type-check, Vite build, Storybook build, Playwright, secret
  taraması, deterministik SBOM karşılaştırması ve `git diff --check`.
- **Mevcut regresyon sonucu:** 1015 Python testi geçti, iki opt-in PostgreSQL
  testi atlandı; sekiz frontend birim testi ve yedi E2E testi geçti. Tam mypy 157
  dosyada sıfır hata verdi.
- **Yetkisiz/negatif test sonucu:** Session resolver yokluğu 401, güvenilmeyen
  context 403 üretir ve repository çağrılmaz. Header ile aktör/rol/scope
  yükseltme girişimi dikkate alınmaz. Depo hatası güvenli 503 döndürür.
- **Audit/redaksiyon sonucu:** Dashboard yetki kararı mevcut merkezi audit
  allowlist'ini kullanır. API yanıtı aktör, rol, session, SQL, stack trace veya
  secret içermez; yalnız sunucu üretimli correlation ID taşır.
- **Kanıt yolları:**
  [21B erişim kanıtı](../08-Uyum-Kanitlari/Erisim/Iterasyon-21B-Guvenli-Dashboard-API-Kaniti.md),
  `06-Testler/01-Birim/test_dashboard_api.py`,
  `04-Frontend/app/e2e/dashboard.spec.ts`
- **Teknik durum:** `TechnicallyVerified`
- **Banka onayı:** API teknik seçimleri `KararAlındı`; üretim kimlik ve altyapı
  uygulaması `ComplianceReviewRequired`.
- **Kalan risk:** 20E ile `__Host-session`, CSRF ve BFF resolver sınırı teknik
  olarak doğrulandı. Gerçek OIDC/SAML assertion, yüksek erişilebilir session
  store, PostgreSQL skor repository'si, üretim CORS topolojisi ve ölçüm
  yeterliliği/alarm API alanları uygulanmadı. Vite ilk bundle boyutu 500 kB
  uyarısı verir.
- **Geri alma yaklaşımı:** Frontend API çağrısı pasifleştirilip sentetik Storybook
  fixture'ı korunabilir; FastAPI route uygulama fabrikasından çıkarılabilir.
  Üretim resolver bağlı olmadığı için mevcut sürüm zaten varsayılan olarak
  erişimi reddeder.
- **Sonraki iterasyon:** 21C — dashboard operasyonel gösterge API'si.

## İterasyon 21C — Dashboard Operasyonel Gösterge API'si

- **Kullanıcı/sistem değeri:** Yetkili son 30 UTC gün kapsamı için ölçüm
  yeterliliği durumu, kritik kontrol veri kullanılabilirliği ve teknik hata özeti
  aynı veri-minimum dashboard DTO'sunda sunulur.
- **Mevcut FR/UC/RULE:** `FR-054`, `FR-056`, `UC-010`, `RULE-009`,
  `AC/TS-030`, `AC/TS-043`, `AC/TS-045`, `NFR-PERF-001/002`.
- **BFR/CTRL:** `BFR-IAM-001/002/004/006`, `CTRL-BDDK-IAM-001`.
- **Davranış:** Aktif yeterlilik politikası olmadan `QUALIFIED` üretilmez;
  mevcut ölçüm `VALIDATION_REQUIRED`, son teknik durum `TECHNICAL_FAILURE`, veri
  yokluğu `NO_DATA` olur. Teknik hata gözlem/execution/kaynak sayıları ve son
  zaman ayrı taşınır. Kritik kural sonuç kaynağı henüz bulunmadığından sayılar
  sıfır uydurulmaz ve `NOT_AVAILABLE` döner.
- **Teknik sınır:** Trend ve operasyonel özet tek yetkilendirme ve tek repository
  okumasından üretilir. DTO aktör, rol, source kimliği listesi, SQL, stack trace,
  secret veya ham hassas veri içermez.
- **Test sonucu:** 1031 Python testi geçti, iki opt-in PostgreSQL testi atlandı;
  159 dosyalık mypy, Ruff lint/format ve compileall temizdir. 13 frontend birim
  testi, TypeScript type-check ve Vite build geçti; mevcut 500 kB bundle uyarısı
  sürmektedir. `28A-v1` secret taraması 465 dosyada sıfır bulgudur.
- **Migration/config:** Şema ve yeni bağımlılık yoktur.
- **Kanıt:**
  [21C erişim kanıtı](../08-Uyum-Kanitlari/Erisim/Iterasyon-21C-Dashboard-Operasyonel-Gosterge-API-Kaniti.md).
- **Teknik durum:** `TechnicallyVerified`.
- **Banka onayı:** Üretilmemiştir; gerçek IdP, HA session store ve PostgreSQL
  skor deposu üretim bağlantısı için açık kalır.
- **Geri alma:** `get_overview` yerine mevcut `get_score_trend` çağrısına dönülüp
  yeni DTO alanları kaldırılabilir; kaynak veri ve tarihsel skor değişmez.
- **Sonraki iterasyon:** 30D — dashboard referans içerik tamamlaması ve 21C
  alanlarının KPI kartlarına bağlanması.

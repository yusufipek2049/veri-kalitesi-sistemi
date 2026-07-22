---
iteration: 21B
status: TechnicallyVerified
completed_at: 2026-07-22
---

# İterasyon 21B — Güvenli Dashboard Özet API Dikey Dilimi

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
- **Kalan risk:** Gerçek OIDC/SAML assertion, `__Host-session`, CSRF, yüksek
  erişilebilir session store, PostgreSQL skor repository'si, üretim CORS
  topolojisi ve ölçüm yeterliliği/alarm API alanları uygulanmadı. Vite ilk bundle
  boyutu 500 kB uyarısı verir.
- **Geri alma yaklaşımı:** Frontend API çağrısı pasifleştirilip sentetik Storybook
  fixture'ı korunabilir; FastAPI route uygulama fabrikasından çıkarılabilir.
  Üretim resolver bağlı olmadığı için mevcut sürüm zaten varsayılan olarak
  erişimi reddeder.
- **Sonraki iterasyon:** 20E — BFF oturum ve CSRF HTTP sınırı.

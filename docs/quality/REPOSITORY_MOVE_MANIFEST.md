# Repository Taşıma Manifesti

> **Amaç:** Mevcut numaralandırılmış dizin yapısından (`03-Backend`, `04-Frontend`,
> `05-Veritabani`, `tests`) standart repository yapısına geçişte gerekli tüm
> yol referanslarının eksiksiz envanteri.
>
> **Kapsam:** Yalnızca yapılandırma, betik ve çapraz referans dosyalarındaki
> sabit yol metinleri. Kaynak kod (`veri_kalitesi/` Python paket adı) ve
> `veri_kalitesi.*` import'ları değişmez — yalnız dosya sistemi yolları.
>
> **Hedef yapı (önerilen):**
>
> | Mevcut yol | Hedef yol |
> |---|---|
> | `src/` | `src/` |
> | `tests/unit/` | `tests/unit/` |
> | `tests/integration/` | `tests/integration/` |
> | `tests/e2e/` | `tests/e2e/` |
> | `tests/support/` | `tests/support/` |
> | `docs/database/` | `database/` |
> | `04-Frontend/app/` | `frontend/` |

---

## 1. Python — pytest pythonpath ve testpaths

### 1.1 `pyproject.toml`

| Mevcut yol | Hedef yol | Referans veren dosya | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `pythonpath = ["docs/backend/src", "docs/testing/support"]` | `pythonpath = ["src", "tests/support"]` | `pyproject.toml` L28 | 1 | `python -c "import tomli; d=tomli.load(open('pyproject.toml','rb')); print(d['tool']['pytest']['ini_options']['pythonpath'])"` | Eski değerleri geri yaz |
| `testpaths = ["tests"]` | `testpaths = ["tests"]` | `pyproject.toml` L29 | 1 | `pytest --collect-only -q \| head -5` | Eski değerleri geri yaz |

---

## 2. GitHub Actions — working-directory, cache ve komut yolları

### 2.1 `.github/workflows/quality.yml`

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `docs/testing/02-Entegrasyon` (pytest hedef) | `tests/integration` | L85 | 1 | `grep -n 'tests/integration' .github/workflows/quality.yml` | Git restore |
| `mypy docs/backend/src` | `mypy src` | L121 | 1 | `grep -n 'mypy src' .github/workflows/quality.yml` | Git restore |
| `working-directory: 04-Frontend/app` | `working-directory: frontend` | L128 | 1 | `grep -n 'working-directory: frontend' .github/workflows/quality.yml` | Git restore |
| `cache-dependency-path: 04-Frontend/app/package-lock.json` | `cache-dependency-path: frontend/package-lock.json` | L135 | 1 | `grep -n 'frontend/package-lock.json' .github/workflows/quality.yml` | Git restore |
| Yorum: `docs/backend/src` (bağımlılık kurulumu açıklaması) | `src` | L11 | 1 | `grep -n 'src' .github/workflows/quality.yml \| head -3` | Git restore |
| Yorum: `docs/testing/02-Entegrasyon` | `tests/integration` | L7 | 1 | `grep -n 'tests/integration' .github/workflows/quality.yml \| head -3` | Git restore |

---

## 3. Alembic — migration yapılandırması

### 3.1 `alembic.ini` → `database/alembic.ini`

| Mevcut yol | Hedef yol | Referans veren dosya | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `prepend_sys_path = %(here)s/../docs/backend/src` | `prepend_sys_path = %(here)s/../src` | `database/alembic.ini` (taşındıktan sonra) | 1 | `grep 'prepend_sys_path' database/alembic.ini` | Git restore |
| `script_location = %(here)s/alembic` | Değişmez (göreceli) | `database/alembic.ini` | — | `alembic -c database/alembic.ini check` | — |

### 3.2 `docs/database/alembic/env.py` → `database/alembic/env.py`

| Mevcut yol | Hedef yol | Referans veren dosya | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `from veri_kalitesi.persistence import ...` | Değişmez (Python import) | `database/alembic/env.py` | — | `python -c "from veri_kalitesi.persistence import DatabaseSettings"` | — |

---

## 4. Docker — PYTHONPATH, COPY ve build context

### 4.1 `infrastructure/application/Dockerfile`

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `PYTHONPATH=/app/docs/backend/src` | `PYTHONPATH=/app/src` | L5 | 2 | `grep PYTHONPATH infrastructure/application/Dockerfile` | Git restore |
| `COPY docs/backend/src /app/docs/backend/src` | `COPY src/ /app/src/` | L11 | 2 | `grep 'COPY src' infrastructure/application/Dockerfile` | Git restore |
| `COPY 05-Veritabani /app/05-Veritabani` | `COPY database/ /app/database/` | L12 | 2 | `grep 'COPY database' infrastructure/application/Dockerfile` | Git restore |

### 4.2 `infrastructure/enterprise-lab/e2e/Dockerfile`

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `COPY docs/backend/src /build/docs/backend/src` | `COPY src/ /build/src/` | L5 | 2 | `grep 'COPY src' infrastructure/enterprise-lab/e2e/Dockerfile` | Git restore |

### 4.3 `infrastructure/development/postgres/Dockerfile`

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `COPY infrastructure/development/postgres/entrypoint.sh` | Değişmez (infrastructure taşınmıyor) | L3 | — | — | — |

---

## 5. Docker Compose — volume, build context ve working_dir

### 5.1 `infrastructure/development/compose.yaml`

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `command: ["alembic", "-c", "alembic.ini", ...]` | `command: ["alembic", "-c", "database/alembic.ini", ...]` | L26 | 2 | `grep 'database/alembic.ini' infrastructure/development/compose.yaml` | Git restore |
| `working_dir: /workspace/04-Frontend/app` | `working_dir: /workspace/frontend` | L77 | 2 | `grep 'working_dir' infrastructure/development/compose.yaml` | Git restore |
| `frontend-node-modules:/workspace/04-Frontend/app/node_modules` | `frontend-node-modules:/workspace/frontend/node_modules` | L88 | 2 | `grep 'frontend/node_modules' infrastructure/development/compose.yaml` | Git restore |

### 5.2 `infrastructure/enterprise-lab/compose.yaml`

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `../../docs/backend/src:/application:ro` (environment-gate volume) | `../../src:/application:ro` | L42 | 2 | `grep '/application:ro' infrastructure/enterprise-lab/compose.yaml` | Git restore |
| `../../docs/backend/src:/application:ro` (adapter-e2e volume) | `../../src:/application:ro` | L187 | 2 | Yukarıdaki ile aynı | Git restore |

---

## 6. Python betikleri — sys.path ve sabit yol referansları

### 6.1 `scripts/seed_database.py`

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `sys.path.insert(0, str(ROOT / "03-Backend" / "src"))` | `sys.path.insert(0, str(ROOT / "src"))` | L26 | 1 | `grep 'sys.path' scripts/seed_database.py` | Git restore |
| `ROOT / "05-Veritabani" / "alembic.ini"` | `ROOT / "database" / "alembic.ini"` | L105 | 1 | `grep 'alembic.ini' scripts/seed_database.py` | Git restore |

### 6.2 `scripts/generate_synthetic_test_data.py`

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `from veri_kalitesi.synthetic_data...` | Değişmez (Python import) | L5 | — | — | — |

> **Not:** Bu betik `PYTHONPATH=docs/backend/src` ortam değişkeniyle çalıştırılır.
> Değişken değeri §8'deki Markdown komut belgelerinde geçer.

### 6.3 `scripts/reset_synthetic_test_data.py`

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `from veri_kalitesi.synthetic_data...` | Değişmez (Python import) | L5 | — | — | — |

### 6.4 `scripts/check_documentation.py`

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `ARCHIVE_PREFIXES` ve `DUPLICATE_SCAN_EXCLUDED_PREFIXES` | Numaralı dizin adları değişirse güncelle | L35–36 | 3 | `python scripts/check_documentation.py --help` | Git restore |

> **Not:** Bu dosya doğrudan `03-Backend` gibi sabit yol içermez; ancak
> numaralı dizin adları arşiv istisnalarında dolaylı olarak kodlanmıştır.

---

## 7. Shell betikleri — test dizini değişkenleri

### 7.1 `tools/agent-loop/lib.sh`

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `UNIT_TEST_DIR:=docs/testing/01-Birim` | `UNIT_TEST_DIR:=tests/unit` | L72 | 1 | `grep 'UNIT_TEST_DIR' tools/agent-loop/lib.sh \| head -2` | Git restore |
| `INTEGRATION_TEST_DIR:=docs/testing/02-Entegrasyon` | `INTEGRATION_TEST_DIR:=tests/integration` | L73 | 1 | `grep 'INTEGRATION_TEST_DIR' tools/agent-loop/lib.sh \| head -2` | Git restore |
| `OPTIONAL_INTEGRATION_TEST:=$INTEGRATION_TEST_DIR/test_synthetic_postgresql_integration.py` | Değişmez (türetilmiş) | L74 | — | — | — |
| `grep -Eq '^(src/\|docs/database/alembic\|...'` (integration_required) | `grep -Eq '^(src/\|database/alembic\|...'` | L185 | 1 | `grep 'src/\\|database' tools/agent-loop/lib.sh` | Git restore |
| `grep -E '^(01-SRS\|03-Backend\|04-Frontend\|05-Veritabani\|tests)/'` (scope hint) | `grep -E '^(01-SRS\|src\|frontend\|database\|tests)/'` | L847 | 1 | `grep 'scope_hint' tools/agent-loop/lib.sh` | Git restore |

### 7.2 `tools/agent-loop/ledger.sh`

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `UNIT_TEST_DIR` ve `INTEGRATION_TEST_DIR` referansları (handoff paketi içinde) | lib.sh'deki değişkenlerle tutarlı | L208, L482, L496–497 | 1 | `grep -c 'UNIT_TEST_DIR\|INTEGRATION_TEST_DIR' tools/agent-loop/ledger.sh` | Git restore |

> **Not:** ledger.sh doğrudan sabit yol içermez; yollar lib.sh'den gelen
> değişkenler üzerinden türetilir. Değişken değerleri değiştiğinde handoff
> paketi ve test planı otomatik güncellenir.

---

## 8. Markdown — komut belgeleri ve çapraz referanslar

### 8.1 Komut satırı belgeleri (PYTHONPATH ve pytest yolları)

| Dosya | Mevcut yol | Hedef yol | Taşıma iterasyonu | Doğrulama komutu |
|---|---|---|---|---|
| `tests/integration/Sentetik-PostgreSQL-Dataset.md` | `PYTHONPATH=docs/backend/src` | `PYTHONPATH=src` | 3 | `grep PYTHONPATH tests/integration/Sentetik-PostgreSQL-Dataset.md` |
| `docs/architecture/Mimari-Kararlar.md` | `PYTHONPATH=docs/backend/src` | `PYTHONPATH=src` | 3 | `grep PYTHONPATH docs/architecture/Mimari-Kararlar.md` |
| `docs/operations/Surum-ve-Degisiklik-Yonetimi.md` | `PYTHONPATH=docs/backend/src` (2 yer) | `PYTHONPATH=src` | 3 | `grep PYTHONPATH docs/operations/Surum-ve-Degisiklik-Yonetimi.md` |
| `docs/compliance/Guvenlik-Testleri/Iterasyon-28E-*.md` | `PYTHONPATH=docs/backend/src` (çoklu) | `PYTHONPATH=src` | 3 | `grep -c PYTHONPATH docs/compliance/Guvenlik-Testleri/Iterasyon-28E-*.md` |
| `docs/technical/05-Deployment-ve-Operasyon.md` | `PYTHONPATH=docs/backend/src` (çoklu) | `PYTHONPATH=src` | 3 | `grep -c PYTHONPATH docs/technical/05-Deployment-ve-Operasyon.md` |
| `docs/technical/06-Test-Performans-ve-Teknik-Borc.md` | `PYTHONPATH=docs/backend/src` | `PYTHONPATH=src` | 3 | `grep PYTHONPATH docs/technical/06-Test-Performans-ve-Teknik-Borc.md` |

### 8.2 pytest/mypy/ruff komut belgeleri

| Dosya | Mevcut yol | Hedef yol | Taşıma iterasyonu | Doğrulama komutu |
|---|---|---|---|---|
| `docs/compliance/Guvenlik-Testleri/Iterasyon-28E-*.md` | `tests/unit/test_secure_sdlc*.py` | `tests/unit/test_secure_sdlc*.py` | 3 | `grep 'tests/unit' docs/compliance/Guvenlik-Testleri/Iterasyon-28E-*.md` |
| `docs/compliance/Guvenlik-Testleri/Iterasyon-28E-*.md` | `src/veri_kalitesi/secure_sdlc/...` | `src/veri_kalitesi/secure_sdlc/...` | 3 | `grep 'src/veri_kalitesi' docs/compliance/Guvenlik-Testleri/Iterasyon-28E-*.md` |
| `docs/compliance/Guvenlik-Testleri/Iterasyon-28E-*.md` | `docs/backend/src tests` (compileall) | `src tests` | 3 | `grep 'compileall' docs/compliance/Guvenlik-Testleri/Iterasyon-28E-*.md` |
| `docs/technical/06-Test-Performans-ve-Teknik-Borc.md` | `docs/backend/src tests` | `src tests` | 3 | `grep 'src tests' docs/technical/06-Test-Performans-ve-Teknik-Borc.md` |
| `docs/technical/06-Test-Performans-ve-Teknik-Borc.md` | `tests/unit/` | `tests/unit/` | 3 | `grep 'tests/unit' docs/technical/06-Test-Performans-ve-Teknik-Borc.md` |
| `docs/iterations/DQ-CAP-PROTOTYPE-05-*.md` | `tests/unit/...` | `tests/unit/...` | 3 | `grep 'tests/unit' docs/iterations/DQ-CAP-PROTOTYPE-05-*.md` |
| `docs/iterations/DQ-CAP-PROTOTYPE-05-*.md` | `tests/integration/...` | `tests/integration/...` | 3 | `grep 'tests/integration' docs/iterations/DQ-CAP-PROTOTYPE-05-*.md` |

### 8.3 Dizin çapraz referansları (Markdown linkleri)

| Dosya | Mevcut link | Hedef link | Taşıma iterasyonu | Doğrulama komutu |
|---|---|---|---|---|
| `docs/architecture/Mimari-Kararlar.md` | `../docs/backend/BACKEND-INDEX.md` | `../backend/BACKEND-INDEX.md` veya yeni konum | 3 | `grep 'BACKEND-INDEX' docs/architecture/Mimari-Kararlar.md` |
| `docs/architecture/Mimari-Kararlar.md` | `../04-Frontend/Gorsel-Tasarim-Sistemi.md` | `../frontend/Gorsel-Tasarim-Sistemi.md` veya yeni konum | 3 | `grep 'Gorsel-Tasarim' docs/architecture/Mimari-Kararlar.md` |
| `docs/architecture/Mimari-Kararlar.md` | `../testing/Gorsel-Dogrulama-Stratejisi.md` | `../testing/Gorsel-Dogrulama-Stratejisi.md` | 3 | `grep 'Gorsel-Dogrulama' docs/architecture/Mimari-Kararlar.md` |
| `docs/architecture/Mimari-Kararlar.md` | `docs/testing/TEST-INDEX.md` | `tests/TEST-INDEX.md` | 3 | `grep 'TEST-INDEX' docs/architecture/Mimari-Kararlar.md` |
| `docs/backend/BACKEND-INDEX.md` | `src/veri_kalitesi/api/app.py` | `src/veri_kalitesi/api/app.py` | 3 | `grep 'src/veri_kalitesi' docs/backend/BACKEND-INDEX.md` |
| `04-Frontend/FRONTEND-INDEX.md` | `04-Frontend/app/package.json` | `frontend/package.json` | 3 | `grep 'package.json' 04-Frontend/FRONTEND-INDEX.md` |
| `04-Frontend/FRONTEND-INDEX.md` | `cd 04-Frontend/app` | `cd frontend` | 3 | `grep 'cd frontend' 04-Frontend/FRONTEND-INDEX.md` |
| `04-Frontend/FRONTEND-INDEX.md` | `../testing/Gorsel-Dogrulama-Stratejisi.md` | `../testing/Gorsel-Dogrulama-Stratejisi.md` | 3 | `grep 'Gorsel-Dogrulama' 04-Frontend/FRONTEND-INDEX.md` |
| `docs/database/VERITABANI-INDEX.md` | `../docs/backend/BACKEND-INDEX.md` | `../backend/BACKEND-INDEX.md` | 3 | `grep 'BACKEND-INDEX' docs/database/VERITABANI-INDEX.md` |
| `docs/database/VERITABANI-INDEX.md` | `../docs/testing/TEST-INDEX.md` | `../tests/TEST-INDEX.md` | 3 | `grep 'TEST-INDEX' docs/database/VERITABANI-INDEX.md` |
| `docs/memory/Proje-Ozeti.md` | `../04-Frontend/03-Dashboard/Dashboard-Ekran-Sozlesmesi.md` | Yeni konuma göre güncelle | 3 | `grep 'Dashboard-Ekran' docs/memory/Proje-Ozeti.md` |
| `docs/functional-audit/evidence-inventory/05-Test-Inventory.md` | `tests/unit/`, `tests/integration/`, `04-Frontend/app/e2e/` | `tests/unit/`, `tests/integration/`, `frontend/e2e/` | 3 | `grep 'tests/' docs/functional-audit/evidence-inventory/05-Test-Inventory.md` |
| `docs/functional-audit/work/19-Slice-DS06-*.md` | `src/veri_kalitesi/...` ve `docs/database/alembic/...` | `src/veri_kalitesi/...` ve `database/alembic/...` | 3 | `grep 'src/veri_kalitesi' docs/functional-audit/work/19-Slice-DS06-*.md` |
| `docs/functional-audit/work/21-Slice-DS09-*.md` | `src/veri_kalitesi/...` ve `docs/database/alembic/...` | `src/veri_kalitesi/...` ve `database/alembic/...` | 3 | `grep 'src/veri_kalitesi' docs/functional-audit/work/21-Slice-DS09-*.md` |
| `docs/technical/README.md` | `src/veri_kalitesi/...` (15+ satır) | `src/veri_kalitesi/...` | 3 | `grep -c 'src/veri_kalitesi' docs/technical/README.md` |

---

## 9. .gitignore — istisna yolları

### 9.1 `.gitignore`

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `!/04-Frontend/app/src/reports/` | `!/frontend/src/reports/` | L73 | 2 | `grep 'frontend/src/reports' .gitignore` | Git restore |
| `!/04-Frontend/app/src/reports/*.ts` | `!/frontend/src/reports/*.ts` | L74 | 2 | `grep 'frontend/src/reports' .gitignore` | Git restore |
| `!/04-Frontend/app/src/reports/*.tsx` | `!/frontend/src/reports/*.tsx` | L75 | 2 | `grep 'frontend/src/reports' .gitignore` | Git restore |

---

## 10. Graphify — ignore ve root ayarları

### 10.1 `.graphifyignore`

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `docs/testing/` | `tests/` | L18 | 2 | `grep 'tests/' .graphifyignore` | Git restore |

> **Not:** `.graphifyignore` yalnızca dizin adlarını içerir; `03-Backend`,
> `04-Frontend`, `05-Veritabani` gibi numaralı dizinler bu dosyada yer almaz
> (onun yerine `docs/`, `scripts/`, `tools/` gibi genel adlar kullanılmıştır).

### 10.2 `graphify-out/.graphify_root`

| Mevcut değer | Hedef değer | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|
| Mutlak repo kök yolu | Değişmez (repo köküne işaret eder) | — | `cat graphify-out/.graphify_root` | — |

### 10.3 `graphify-out/.graphify_analysis.json`

| Mevcut durum | Hedef durum | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|
| Düğüm adlarında `03_backend_src_...` önekleri | Graphify yeniden çalıştırıldığında otomatik güncellenir | 3 (re-analiz) | `grep -c '03_backend' graphify-out/.graphify_analysis.json` | Eski çıktıyı geri yükle + re-analiz |

---

## 11. Frontend yapılandırması

### 11.1 `04-Frontend/app/` → `frontend/`

| Dosya | Değişiklik | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|
| `package.json` | Yol referansı yok — değişmez | — | — | — |
| `vite.config.ts` | Yol referansı yok — değişmez | — | — | — |
| `vitest.config.ts` | `setupFiles: "./src/test/setup.ts"` — göreceli, değişmez | — | — | — |
| `playwright.config.ts` | `testDir: "./e2e"` — göreceli, değişmez | — | — | — |
| `tsconfig.app.json` | `"include": ["src"]` — göreceli, değişmez | — | — | — |
| `tsconfig.node.json` | `"include": ["vite.config.ts", ...]` — göreceli, değişmez | — | — | — |

> **Sonuç:** Frontend config dosyalarının tümü göreceli yollar kullanır.
> Yalnız dizin adı değişeceği için içerik değişikliği gerekmez; taşıma
> yeterlidir. GitHub Actions `working-directory` ve Compose `working_dir`
> başvuruları §2 ve §5'te kapsanmıştır.

---

## 12. .gitignore — ajan/operasyon dizin istisnaları

| Mevcut yol | Hedef yol | Satır | Taşıma iterasyonu | Doğrulama komutu | Geri alma |
|---|---|---|---|---|---|
| `/docs/architecture/Ajan-*.md` | Değişmez (02-Mimari taşınmıyor) | L165 | — | — | — |
| `/docs/operations/Ajan-*.md` | Değişmez (07-Operasyon taşınmıyor) | L166 | — | — | — |

---

## Özet — Taşıma iterasyonları

| İterasyon | Kapsam | Dosya sayısı | Risk |
|---|---|---:|---|
| **1** | Yapılandırma dosyaları: `pyproject.toml`, `.github/workflows/quality.yml`, `alembic.ini`, `scripts/seed_database.py`, `tools/agent-loop/lib.sh` | 5 | Orta — test pipeline'ını kırar |
| **2** | Docker/Compose ve .gitignore: `Dockerfile` (×2), `compose.yaml` (×2), `.gitignore`, `.graphifyignore` | 6 | Orta — container build bozulur |
| **3** | Markdown belgeleri: komut satırı örnekleri, çapraz referans linkleri, kanıt dosyaları | 15+ | Düşük — belgesel tutarsızlık |

---

## Doğrulama matrisi

Her iterasyondan sonra çalıştırılacak doğrulama komutları:

```bash
# İterasyon 1 sonrası
python -m pytest --collect-only -q          # test keşfi
python -m mypy src                           # tip kontrolü
python -m ruff check .                       # lint
alembic -c database/alembic.ini check        # migration

# İterasyon 2 sonrası
docker compose -f infrastructure/development/compose.yaml config  # compose doğrulama
docker build -f infrastructure/application/Dockerfile .           # build

# İterasyon 3 sonrası
python scripts/check_documentation.py        # Markdown bütünlüğü
grep -rn '03-Backend\|04-Frontend\|05-Veritabani\|tests' \
  --include='*.py' --include='*.toml' --include='*.yml' --include='*.yaml' \
  --include='*.sh' --include='*.ini' --include='Dockerfile' \
  . | grep -v '.git/' | grep -v 'node_modules/' | grep -v 'archive/'
# Beklenen: 0 eşleşme (eski yol referansı kalmamalı)
```

---

## Geri alma stratejisi

Tüm değişiklikler Git üzerinden izlenir. Herhangi bir iterasyonda sorun çıkarsa:

```bash
# Son commit'e geri dön
git checkout HEAD -- .

# Veya belirli bir dosyayı geri al
git checkout HEAD -- pyproject.toml .github/workflows/quality.yml

# Docker değişikliklerini geri al
git checkout HEAD -- infrastructure/
```

> **İlke:** Her iterasyon ayrı bir Git commit'i olarak kaydedilir. Geri alma
> `git revert <commit>` ile yapılır; böylece sonraki iterasyonların değişiklikleri
> korunur.

# Veri Kalitesi Sistemi

Verinin doğruluğunun gözetildiği, ölçüldüğü ve kanıtlandığı zemin.

Kaynağa dokunmadan niteliğini tartar. Kurallar, gözlemler, skorlar — her biri
bir yargının izini taşır. Ölçüm ile ölçülen birbirine karışmaz.

---

## Kavram

Sonlu relational source'lar. Read-only bağlam. Kalite kurallarının
uygulanmasıyla ortaya çıkan skorlar, issue'lar, audit izleri.

Üç döngü: **bağlan** → **ölç** → **yorumla**.

Kaynak verisi değişmez; değişen, onun hakkında bilinen şeydir.

---

## Mimari

```
Client ──▶ API ──▶ PostgreSQL ◀── Worker
```

| Katman | Özü |
|--------|-----|
| API | Kompozisyon kökünden doğan uçlar — okunur her şey buradan akar |
| Worker | Kuyruktan kapılan, alt süreçte izole edilmiş, kalp atışlı |
| Database | Tek hakikat — sürümlü şema, doğrusal migration zinciri |
| Client | Reaktif yüzey — uçlardan beslenen, durumu yansıtan |

Yığın: **FastAPI** · **Python ≥ 3.10** · **PostgreSQL 16** · **SQLAlchemy 2.0** ·
**Alembic** · **React 19** · **MUI 9** · **Vite 8** · **TypeScript 7**

Worker: saf Python kuyru tarama, fork isolation, lease mekanizması.

---

## Üç Katman

| | Anlamı |
|---|---|
| **Backend** | Kuralların service'e, service'in endpoint'lere dönüştüğü yer. Composition root —
her şeyi görünür kılan, erişimi mümkün kılan. Domain, validation, audit;
kodun omurgası. *FastAPI · Python ≥ 3.10* |
| **Frontend** | Durumun görünüme büründüğü yüzey. Endpoint'lerden akan her şeyin
insana açılan kapısı. Anlık yansıma, kesintisiz geri bildirim. *React 19 · MUI 9 · Vite 8* |
| **Database** | Hakiketin kilitli kaldığı yer. Her dönüşümün kaydedildiği,
her migration'ın iz bıraktığı tek kaynak. Şema sürümlenir, geri dönüşü yok. *PostgreSQL 16 · SQLAlchemy 2.0 · Alembic* |

---

## Eşik

| Araç | Sınır |
|------|-------|
| Docker + Compose v2 | 24+ / v2.20+ |
| Python | ≥ 3.10 |
| Node.js | ≥ 22 |

---

## Başlangıç

```bash
export DQ_POSTGRES_PASSWORD=örnek-parola

cp -r infra/development/runtime-secrets.example \
      infra/development/runtime-secrets

docker compose -f infra/development/compose.yaml up --build
```

Beş container, sırayla: `postgres :55432` → `migrate` → `api :8000` → `worker` → `frontend :5173`.

Doğrulama:

```bash
curl -s http://127.0.0.1:8000/api/v1/openapi.json | head -c 100
curl -s http://127.0.0.1:8000/api/v1/development/users | python3 -m json.tool
```

Tarayıcıda `http://localhost:5173` — dev user seçilerek içeri adım atılır.

Demo veri (isteğe bağlı):

```bash
DATA_QUALITY_DATABASE_URL="postgresql+psycopg://dq_app:${DQ_POSTGRES_PASSWORD}@127.0.0.1:55432/data_quality" \
    python scripts/seed_database.py
```

---

## Yüzey

| Alan | Kapsam |
|------|--------|
| Data Sources | create, activate, passivate, connection test, metadata |
| Rules | query, versioning |
| Issues | create, investigate, assign, resolve, verify, close |
| Executions | start, cancel, query |
| Scores | list, detail, compare |
| Audit | event query |
| Notifications | inbox, delivery, channel, subscription |
| Catalog | discovery, dataset/field browsing, diff application |
| Worker | EXECUTION · METADATA_DISCOVERY · NOTIFICATION_DELIVERY |

Unwired endpoint'ler — dashboard, profile, report, lineage, governance — kodda
vardır; composition root'ta henüz ete kemiğe bürünmemiştir.

---

## Kalite

```bash
pytest -q                          # tüm testler
python3 scripts/test_postgresql.py # PostgreSQL integration
ruff check . && ruff format --check .
mypy src
cd frontend && npm test && npm run typecheck && npm run build
```

---

## Durdur

```bash
docker compose -f infra/development/compose.yaml down     # volume kalır
docker compose -f infra/development/compose.yaml down -v  # volume gider
```

---

## Çekirdek Değişkenler

| Değişken | Anlamı |
|----------|--------|
| `DATA_QUALITY_DATABASE_URL` | Connection string |
| `DATA_QUALITY_DATABASE_SCHEMA` | Namespace (`dq`) |
| `DATA_QUALITY_RUNTIME_ENVIRONMENT` | Runtime mode |
| `DATA_QUALITY_ALLOWED_ORIGINS` | CORS boundaries |
| `DQ_WORKER_ID` · `_CAPACITY` · `_LEASE_SECONDS` | Worker identity & tempo |

---

## Henüz Dışarıda

Production olgunluğundan ayıran: IdP/LDAP, PAM, HA, message broker, SIEM/WORM,
ServiceNow, DR, banka compliance — her biri ayrı bir emek.

Kodda var, runtime'a bağlı değil: retention, synthetic data, secure SDLC,
incident response, reporting, lineage, governance.


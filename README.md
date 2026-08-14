# Veri Kalitesi Sistemi

Verinin doğruluğunun gözetildiği, ölçüldüğü ve kanıtlandığı zemin.

Kaynağa dokunmadan niteliğini tartar. Kurallar, gözlemler, skorlar — her biri
bir yargının izini taşır. Ölçüm ile ölçülen birbirine karışmaz.

---

## Kavram

Sonlu ilişkisel kaynaklar. Salt-okunur bağlam. Nitelik kurallarının
uygulanmasıyla ortaya çıkan skorlar, sorunlar, denetim izleri.

Üç döngü: **bağlan** → **ölç** → **yorumla**.

Kaynak verisi değişmez; değişen, onun hakkında bilinen şeydir.

---

## Mimari

```
İstemci ──▶ API ──▶ PostgreSQL ◀── İşçi
```

| Katman | Özü |
|--------|-----|
| API | Kompozisyon kökünden doğan uçlar — okunur her şey buradan akar |
| İşçi | Kuyruktan kapılan, alt süreçte izole edilmiş, kalp atışlı |
| Veri tabanı | Tek hakikat — sürümlü şema, doğrusal göç zinciri |
| İstemci | Reaktif yüzey — uçlardan beslenen, durumu yansıtan |

Yığın: **FastAPI** · **Python ≥ 3.10** · **PostgreSQL 16** · **SQLAlchemy 2.0** ·
**Alembic** · **React 19** · **MUI 9** · **Vite 8** · **TypeScript 7**

İşçi: saf Python kuyru tarama, fork yalıtımı, kira mekanizması.

---

## Üç Katman

| | Anlamı |
|---|---|
| **Arka uç** | Kuralların hizmete, hizmetin uçlara dönüştüğü yer. Kompozisyon kökü —
her şeyi görünür kılan, erişimi mümkün kılan. Domain, doğrulama, denetim;
kodun omurgası. *FastAPI · Python ≥ 3.10* |
| **Ön uç** | Durumun görünüme büründüğü yüzey. Uçlardan akan her şeyin
insana açılan kapısı. Anlık yansıma, kesintisiz geri bildirim. *React 19 · MUI 9 · Vite 8* |
| **Veri tabanı** | Hakiketin kilitli kaldığı yer. Her dönüşümün kaydedildiği,
her göçün iz bıraktığı tek kaynak. Şema sürümlenir, geri dönüşü yok. *PostgreSQL 16 · SQLAlchemy 2.0 · Alembic* |

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

Beş kap, sırayla: `postgres :55432` → `migrate` → `api :8000` → `işci` → `istemci :5173`.

Doğrulama:

```bash
curl -s http://127.0.0.1:8000/api/v1/openapi.json | head -c 100
curl -s http://127.0.0.1:8000/api/v1/development/users | python3 -m json.tool
```

Tarayıcıda `http://localhost:5173` — gelişim kullanıcısı seçilerek içeri adım atılır.

Demo veri (isteğe bağlı):

```bash
DATA_QUALITY_DATABASE_URL="postgresql+psycopg://dq_app:${DQ_POSTGRES_PASSWORD}@127.0.0.1:55432/data_quality" \
    python scripts/seed_database.py
```

---

## Yüzey

| Alan | Kapsam |
|------|--------|
| Kaynaklar | yaratma, etkinleştirme, dondurma, bağlantı sınaması, üst veri |
| Kurallar | sorgulama, sürümleme |
| Sorunlar | yaratma, inceleme, atama, çözüm, doğrulama, kapatma |
| Yürütmeler | başlatma, iptal, sorgulama |
| Skorlar | listeleme, ayrıntı, karşılaştırma |
| Denetim | olay sorgulama |
| Bildirimler | gelen kutusu, teslimat, kanal, abonelik |
| Katalog | keşif, veri kümesi/alan tarama, fark uygulaması |
| İşçi | EXECUTION · METADATA_DISCOVERY · NOTIFICATION_DELIVERY |

Bağlanmamış uçlar — gösterim, profil, rapor, lineage, governance — kodda
vardır; kompozisyon kökünde henüz ete kemiğe bürünmemiştir.

---

## Kalite

```bash
pytest -q                          # bütün sınamalar
python3 scripts/test_postgresql.py # PostgreSQL bütünleşik
ruff check . && ruff format --check .
mypy src
cd frontend && npm test && npm run typecheck && npm run build
```

---

## Durdur

```bash
docker compose -f infra/development/compose.yaml down     # hacim kalır
docker compose -f infra/development/compose.yaml down -v  # hacim gider
```

---

## Çekirdek Değişkenler

| Değişken | Anlamı |
|----------|--------|
| `DATA_QUALITY_DATABASE_URL` | Bağlantının kendisi |
| `DATA_QUALITY_DATABASE_SCHEMA` | İsim uzayı (`dq`) |
| `DATA_QUALITY_RUNTIME_ENVIRONMENT` | Bağlam kipı |
| `DATA_QUALITY_ALLOWED_ORIGINS` | CORS sınırları |
| `DQ_WORKER_ID` · `_CAPACITY` · `_LEASE_SECONDS` | İşçi kimliği ve temposu |

---

## Henüz Dışarıda

Üretim olgunluğundan ayıran: IdP/LDAP, PAM, HA, mesaj kuyruğu, SIEM/WORM,
ServiceNow, DR, banka uyumu — her biri ayrı bir emek.

Kodda var, yürütmeye bağlı değil: retention, sentetik veri, secure SDLC,
olay müdahale, raporlama, lineage, governance.

---
type: feature-plan
area: frontend + backend
feature: Ad-hoc Özel SQL Çalıştırma
status: TechnicallyVerified
created_at: 2026-08-11
iteration: 37
---

# Ad-hoc Özel SQL Çalıştırma — Uygulama Planı

## 1. Özet

Çalıştırmalar sayfasına **"Özel SQL"** butonu ve ilişkili dialog ekleyerek
kullanıcıların doğrudan SQL sorgusu yazıp çalıştırma başlatabilmesini sağlamak.

Mevcut sistemde çalıştırma başlatmak için **önceden tanımlı bir kural sürümü
seçmek** gerekir. Bu özellik, ad-hoc SQL sorgularıyla hızlı doğrulama ve keşif
senaryolarını destekler.

## 2. Mevcut Durum Analizi

### 2.1 Backend (Değişiklik Gerektirmez)

| Bileşen | Dosya | Açıklama |
| --- | --- | --- |
| `POST /api/v1/rules` | `rules_router.py` | CUSTOM_SQL kuralı oluşturma |
| `POST /api/v1/executions` | `executions_router.py` | Manuel çalıştırma başlatma |
| `RuleType.CUSTOM_SQL` | `rules/models.py` | Özel SQL kural türü (enum) |
| `_custom_sql_plan()` | `rules/templates.py` | SQL validasyon ve IR plan üretimi |
| `is_read_only_sql()` | `rules/templates.py` | Salt okunur SQL kontrolü |
| `PostgreSQLExecutionStartService` | `api/postgresql_execution.py` | Execution oluşturma + job kuyruğu |

### 2.2 Frontend (Mevcut Durum)

| Bileşen | Dosya | Durum |
| --- | --- | --- |
| Çalıştırma listesi | `executions/ExecutionsPage.tsx` | Mevcut |
| Çalıştırma başlat dialog | `executions/ExecutionsPage.tsx` | Mevcut (kural seçimi) |
| "Özel SQL" butonu | — | **Yeni eklenecek** |
| Adhoc SQL dialog | — | **Yeni eklenecek** |

## 3. Uygulama Planı

### Faz 1: Frontend — Buton ve Dialog

**Dosya:** `frontend/src/executions/ExecutionsPage.tsx`

```
ExecutionsPageProps'a yeni proplar:
  + onAdhocSql?: (sql, sourceIds, timeoutSeconds, rowLimit) => Promise<void>
  + adhocSqlLoading?: boolean

Yeni state'ler:
  + adhocDialogOpen: boolean
  + adhocSql: string
  + adhocSqlError: string | null
  + adhocSource: ExecutionSourceOption | null
  + adhocTimeout: number (varsayılan: 30)
  + adhocRowLimit: number (varsayılan: 1000)

Yeni buton:
  + "Özel SQL" — Braces ikonu, variant="outlined"
  + "Çalıştırma başlat" butonunun yanında

Yeni dialog:
  + Başlık: "Özel SQL Çalıştır"
  + SQL editör (multiline, monospace, min 6 satır)
  + Kaynak seçici (Autocomplete, isteğe bağlı)
  + Zaman aşımı (sn) + Satır limiti yan yana
  + Validasyon: SELECT ile başlamalı, yasak keyword kontrolü
  + Submit butonu: "Çalıştır"
```

### Faz 2: Frontend — Orkestrasyon

**Dosya:** `frontend/src/executions/ExecutionsRoute.tsx`

```
handleAdhocSql(sql, sourceIds, timeoutSeconds, rowLimit):
  Adım 1: createRule({
    code: "ADHOC_SQL_<timestamp>",
    name: "Ad-hoc SQL <tarih>",
    rule_type: "CUSTOM_SQL",
    parameters: { sql, timeout_seconds, row_limit, scope_type, query_reference },
    ...
  })
  
  Adım 2: startExecution({
    rule_version_ids: [<adım 1'den dönen rule_version_id>],
    source_ids: sourceIds,
    idempotency_key: crypto.randomUUID(),
    execution_mode: "OFFICIAL",
  })
  
  Adım 3: load() — listeyi yenile
```

### Faz 3: Testler

**Dosya:** `frontend/src/executions/ExecutionsPage.test.tsx`

| # | Test | Kapsam |
|---|------|--------|
| 1 | `onAdhocSql` verildiğinde buton görünür | Koşullu render |
| 2 | `onAdhocSql` yoksa buton görünmez | Koşullu render |
| 3 | Dialog tüm alanları gösterir | UI içeriği |
| 4 | Boş SQL submit engellenir | Disabled state |
| 5 | SELECT ile başlamayan SQL hata verir | Validasyon |
| 6 | Yasak keyword (DROP vb.) hata verir | Validasyon |
| 7 | Geçerli SQL doğru parametrelerle çağırır | Başarılı akış |

**Dosya:** `frontend/src/executions/ExecutionsPage.stories.tsx`

```
+ WithAdhocSql story — onAdhocSql + onStart + ruleOptions + sourceOptions
```

### Faz 4: Dokümantasyon

**Dosya:** `docs/iterations/Iterasyon-37-Adhoc-Ozel-SQL-Calisiirma.md`

İterasyon kapanış belgesi — amaç, mimari, değiştirilen dosyalar, testler,
komutlar, teknik durum, riskler ve geri alma yaklaşımı.

## 4. Mimari Akış Diyagramı

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                             │
│                                                                     │
│  ┌──────────────┐     ┌──────────────────┐     ┌────────────────┐  │
│  │  "Özel SQL"  │────▶│  Adhoc Dialog    │────▶│ handleAdhocSql │  │
│  │   Butonu     │     │  - SQL editör    │     │  (Route)       │  │
│  └──────────────┘     │  - Kaynak seçici │     └───────┬────────┘  │
│                        │  - Timeout/Limit │             │           │
│                        └──────────────────┘             │           │
└─────────────────────────────────────────────────────────┼───────────┘
                                                          │
                    ┌─────────────────────────────────────┼──────┐
                    │         Backend (FastAPI)            │      │
                    │                                     ▼      │
                    │  ┌──────────────┐  rule_version_id  ┌─────┐ │
                    │  │ Rules API    │◄──────────────────│Step1│ │
                    │  │ POST /rules  │                   └─────┘ │
                    │  │ (CUSTOM_SQL) │                           │
                    │  └──────────────┘                           │
                    │         │                                   │
                    │         │ rule_version_id                   │
                    │         ▼                                   │
                    │  ┌──────────────┐                   ┌─────┐ │
                    │  │ Execution API│◄──────────────────│Step2│ │
                    │  │ POST /exec.  │                   └─────┘ │
                    │  │ (start)      │                           │
                    │  └──────────────┘                           │
                    │         │                                   │
                    │         ▼                                   │
                    │  ┌──────────────┐                           │
                    │  │ Job Queue    │                           │
                    │  │ (background) │                           │
                    │  └──────────────┘                           │
                    └─────────────────────────────────────────────┘
```

## 5. SQL Validasyon Kuralları

| # | Kural | Regex/Check | Mesaj |
|---|-------|-------------|-------|
| 1 | Boş olmamalı | `sql.trim().length > 0` | "SQL sorgusu zorunludur." |
| 2 | SELECT ile başlamalı | `upper.startsWith("SELECT")` | "SQL sorgusu SELECT ile başlamalıdır." |
| 3 | Yasak keyword yok | `!upper.includes("DROP ")` vb. | "SQL sorgusu {keyword} içermemelidir." |

**Yasak keyword'ler:** `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `TRUNCATE`, `CREATE`

## 6. Doğrulama Sonuçları

```
Frontend testleri:     172/172 geçti (25 dosya)
TypeScript:            executions/ dosyalarında hata yok
Backend değişikliği:   Yok (mevcut endpoint'ler kullanıldı)
```

## 7. Risk ve Açık Konular

| Risk | Etki | Öneri |
|------|------|-------|
| Ad-hoc kurallar kural envanterini şişirir | Orta | Temizlik/arşivleme politikası |
| `owner_user_id` sabit "adhoc-user" | Düşük | Gerçek kimlik entegrasyonu |
| Client-side validasyon ilk savunma hattı | Düşük | Backend `is_read_only_sql()` ikinci hat olarak çalışır |

## 8. Sonraki Adımlar

1. Ad-hoc kurallar için otomatik temizlik/arşivleme politikası
2. Gerçek kullanıcı kimliği ile `owner_user_id` doldurulması
3. SQL editörde syntax highlighting (CodeMirror/Monaco)
4. Kurumsal politika uyumu ve banka/operasyon onayı

## 9. İlgili Dosyalar

- [İterasyon 37 Kapanış Belgesi](../../iterations/Iterasyon-37-Adhoc-Ozel-SQL-Calisiirma.md)
- [Frontend Ekran Haritası](../FRONTEND-INDEX.md)
- [ExecutionsPage.tsx](../../../frontend/src/executions/ExecutionsPage.tsx)
- [ExecutionsRoute.tsx](../../../frontend/src/executions/ExecutionsRoute.tsx)

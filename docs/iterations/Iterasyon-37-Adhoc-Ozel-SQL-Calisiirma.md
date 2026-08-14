---
iteration: 37
status: TechnicallyVerified
completed_at: 2026-08-11
---

# İterasyon 37 — Ad-hoc Özel SQL Çalıştırma

## Amaç

Çalıştırmalar sayfasına doğrudan SQL sorgusu yazarak çalıştırma başlatma özelliği eklemek.
Kullanıcı, önceden tanımlı bir kural seçmek yerine, arayüzdeki "Özel SQL" butonu ile
salt okunur bir SQL sorgusunu girer; sistem otomatik olarak bir `CUSTOM_SQL` kuralı
oluşturur ve bu kural ile çalıştırma başlatır.

## Kullanıcı / Sistem Değeri

- Veri kalitesi analistleri, tekrar eden kural tanımlamalarına gerek kalmadan doğrudan
  SQL sorgularıyla ad-hoc kontroller çalıştırabilir.
- Hızlı doğrulama ve keşif senaryolarında çeviklik sağlar.
- Mevcut kural oluşturma ve çalıştırma altyapısını yeniden kullanır; yeni backend
  endpoint gerektirmez.

## Mevcut FR/UC/RULE

- **FR-KRL-001**: Kural oluşturma (CUSTOM_SQL türü dahil)
- **FR-EXE-001**: Manuel çalıştırma başlatma
- **RULE-TMPL-CUSTOM_SQL**: Özel SQL kural IR planı

## Mimari Yaklaşım

Ön yüz orkestrasyonu ile iki adımlı akış:

```
┌──────────────┐    POST /api/v1/rules     ┌──────────────┐
│  Frontend    │ ────────────────────────── │  Rules API   │
│  (Dialog)    │    { rule_type:            │  (CUSTOM_SQL  │
│              │      "CUSTOM_SQL",         │   oluştur)    │
│              │      parameters: { sql } } │              │
│              │ ◄── { rule_version_id } ── │              │
│              │                            └──────────────┘
│              │
│              │    POST /api/v1/executions  ┌──────────────┐
│              │ ────────────────────────── │  Execution   │
│              │    { rule_version_ids:     │  API         │
│              │      [<yeni version>] }    │  (başlat)    │
│              │ ◄── { execution item } ─── │              │
└──────────────┘                            └──────────────┘
```

## Değiştirilen Dosyalar

### Frontend

| Dosya | Değişiklik |
| --- | --- |
| `frontend/src/executions/ExecutionsPage.tsx` | `Braces` ikonu, "Özel SQL" butonu, adhoc SQL dialog (SQL editör, kaynak seçici, zaman aşımı, satır limiti), SQL validasyon mantığı, `onAdhocSql` ve `adhocSqlLoading` propları |
| `frontend/src/executions/ExecutionsRoute.tsx` | `handleAdhocSql` orkestrasyon fonksiyonu: `createRule(CUSTOM_SQL)` → `startExecution`, `adhocSqlLoading` state yönetimi |
| `frontend/src/executions/ExecutionsPage.test.tsx` | 7 yeni test: buton görünürlüğü, dialog alanları, boş SQL engelleme, SELECT validasyonu, yasak keyword kontrolü, başarılı submit |
| `frontend/src/executions/ExecutionsPage.stories.tsx` | `WithAdhocSql` story'si |

### Backend

Backend değişikliği yapılmamıştır. Mevcut endpoint'ler kullanılmıştır:
- `POST /api/v1/rules` — CUSTOM_SQL kuralı oluşturma
- `POST /api/v1/executions` — Çalıştırma başlatma

## SQL Validasyon Kuralları

| Kural | Açıklama |
| --- | --- |
| `SELECT` ile başlamalı | Yazma operasyonları engellenir |
| `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `TRUNCATE`, `CREATE` içermemeli | Destructive DDL/DML engellenir |
| Boş olmamalı | Zorunlu alan kontrolü |

## Eklenen Testler

| Test | Kapsam |
| --- | --- |
| `onAdhocSql verildiğinde 'Özel SQL' butonu gösterir` | Buton görünürlüğü |
| `onAdhocSql yoksa 'Özel SQL' butonu göstermez` | Koşullu render |
| `Özel SQL dialog'u tüm alanları gösterir` | Dialog içeriği |
| `Boş SQL ile submit engellenir` | Disabled state |
| `SELECT ile başlamayan SQL hata verir` | Validasyon |
| `Yasak keyword içeren SQL hata verir` | Validasyon |
| `Geçerli SQL ile submit doğru parametrelerle çağırır` | Başarılı akış |

## Çalıştırılan Komutlar

```bash
# Frontend testleri
npx vitest run src/executions/ExecutionsPage.test.tsx
# Sonuç: 16/16 geçti

# Tüm frontend testleri
npx vitest run
# Sonuç: 172/172 geçti (25 test dosyası)

# TypeScript kontrolü
npm run typecheck
# Sonuç: executions/ dosyalarında hata yok
```

## Teknik Durum

**TechnicallyVerified** — Uygulama kodu, testleri ve Storybook hikayesi tamamlanmıştır.
Production readiness için kurumsal politika uyumu ve banka/operasyon onayı ayrıca
değerlendirilmelidir.

## Kalan Risk

- Ad-hoc SQL sorguları `CUSTOM_SQL` kuralı olarak kalıcı olur; tekrarlayan ad-hoc
  sorgular kural envanterini şişirebilir. Temizlik politikası önerilir.
- `owner_user_id` sabit `"adhoc-user"` olarak atanır; gerçek kimlik entegrasyonu
  açılabilir.
- SQL validasyonu client-side'dır; backend'deki `is_read_only_sql()` kontrolü de
  çalışır ancak ilk savunma hattı frontend'dedir.

## Geri Alma Yaklaşımı

- `ExecutionsPage.tsx`'teki "Özel SQL" butonu ve dialog kaldırılır.
- `ExecutionsRoute.tsx`'teki `handleAdhocSql` fonksiyonu kaldırılır.
- Oluşturulan ad-hoc kurallar standart kural pasifleştirme ile devre dışı bırakılır.

## Sonraki Iterasyon

- Ad-hoc kurallar için otomatik temizlik/arsivleme politikası
- Gerçek kullanıcı kimliği ile `owner_user_id` doldurulması
- SQL editörde syntax highlighting (CodeMirror/Monaco entegrasyonu)

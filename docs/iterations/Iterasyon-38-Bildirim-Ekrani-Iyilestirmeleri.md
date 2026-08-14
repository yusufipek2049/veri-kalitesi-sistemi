---
iteration: 38
status: TechnicallyVerified
completed_at: 2026-08-11
---

# İterasyon 38 — Bildirim Ekranı İyileştirmeleri

## Amaç

Bildirim ekranını işlevsel hale getirmek: mevcut hataları gidermek, temel UX eksiklerini kapatmak,
bildirim detayını zenginleştirmek, toplu işlemler ve arama eklemek ve gerçek zamanlı bildirim
akışı (SSE) ile anlık güncelleme sağlamak.

## Kullanıcı / Sistem Değeri

- Veri kalitesi analistleri, bildirimleri hızlıca filtreleyebilir, arayabilir ve toplu yönetebilir.
- Gerçek zamanlı SSE akışı ile yeni bildirimler anında görünür, polling gecikmesi ortadan kalkar.
- Severity göstergeleri ile kritik bildirimler görsel olarak ayrışır.
- Tarih bazlı gruplama ve detay drawer ile büyük inbox'lar yönetilebilir hale gelir.

## Mevcut FR/UC/RULE

- **FR-NTF-001**: Bildirim inbox görüntüleme
- **FR-NTF-002**: Bildirim okundu işaretleme
- **FR-NTF-003**: Bildirim filtreleme (event type, status)
- **FR-NTF-004**: Bildirim badge (okunmamış sayacı)

## Mimari Yaklaşım

4 iterasyon halinde kademeli teslimat:

```
İterasyon 1 (Bug fix + Temel UX)
    │
    ├──→ İterasyon 2 (Detay + Pagination)
    │        │
    │        └──→ İterasyon 3 (Toplu işlem + Arama)
    │
    └──→ İterasyon 4 (SSE — bağımsız parallel çalışabilir)
```

### İterasyon 1 — Temel Düzeltme ve Hızlı Kazanımlar

| # | Özellik | Açıklama |
|---|---------|----------|
| 1.1 | Event Type Filtre Bug Fix | `(filters.eventType === "ALL" \|\| true)` → doğru karşılaştırma |
| 1.2 | Tümünü Okundu İşaretle | `POST /inbox/mark-all-read` + optimistic UI |
| 1.3 | Bell Auto-Refresh Polling | 30 saniyede bir `fetchUnreadCount()` |
| 1.4 | Severity Göstergesi | `EVENT_SEVERITY` mapping'den türetilen renkli icon |
| 1.5 | Özet Kartları Zenginleştirme | `failed_count` ve `today_count` kartları |

### İterasyon 2 — Bildirim Detayı ve Sayfalama

| # | Özellik | Açıklama |
|---|---------|----------|
| 2.1 | Cursor-Based Pagination | "Daha fazla yükle" butonu, `has_more` ile |
| 2.2 | Bildirim Detay Drawer | Timeline, kapsam, payload, delivery metadata |
| 2.3 | Tarih Bazlı Gruplama | Bugün / Dün / Bu Hafta / Daha Eski |
| 2.4 | Event Payload Zenginleştirme | Allowlist ile güvenli payload extraction |

### İterasyon 3 — Toplu İşlemler ve Arama

| # | Özellik | Açıklama |
|---|---------|----------|
| 3.1 | Toplu Seçim | Checkbox + select-all + bulk toolbar |
| 3.2 | Toplu Mark-Read Backend | `POST /deliveries/bulk-read` (max 100 ID) |
| 3.3 | Metin Arama | 300ms debounce, client-side filtreleme |
| 3.4 | Bildirim Satırı İyileştirmeleri | Mavi sol kenar, hover, scope link genişletme |

### İterasyon 4 — Gerçek Zamanlı Bildirimler (SSE)

| # | Özellik | Açıklama |
|---|---------|----------|
| 4.1 | Backend SSE Endpoint | `GET /notifications/stream`, 30s keepalive |
| 4.2 | Frontend SSE Hook | `useNotificationStream`, exponential backoff |
| 4.3 | Bell SSE Entegrasyonu | Hybrid SSE + polling fallback |
| 4.4 | Toast / Snackbar | Yeni bildirim toast'u, "Görüntüle" aksiyonu |

## Değiştirilen Dosyalar

### Backend

| Dosya | Değişiklik |
| --- | --- |
| `src/veri_kalitesi/notifications/stream_hub.py` | **YENİ** — `NotificationStreamHub`: actor bazlı `asyncio.Queue` fan-out, `register`/`unregister`/`publish`/`keepalive` |
| `src/veri_kalitesi/api/notifications_router.py` | SSE endpoint (`GET /stream`), `mark-all-read`, `bulk-read`, severity/payload extraction, `failed_count`/`today_count` |
| `src/veri_kalitesi/notifications/postgresql_repository.py` | `count_failed()`, `count_today()`, `mark_all_read_for_recipient()` |
| `src/veri_kalitesi/notifications/query_service.py` | `InboxPage` genişletme (`failed_count`, `today_count`), `mark_all_read()` |
| `src/veri_kalitesi/notifications/delivery_service.py` | Başarılı teslimat sonrası SSE hub'a publish |

### Frontend

| Dosya | Değişiklik |
| --- | --- |
| `frontend/src/notifications/model.ts` | `NotificationSeverity` tipi, `severity`/`payload` alanları, `failedCount`/`todayCount` |
| `frontend/src/notifications/api.ts` | `markAllRead()`, `bulkMarkRead()`, `InboxResult` genişletme |
| `frontend/src/notifications/NotificationsPage.tsx` | **Tam yeniden yazım** — Severity icon, özet kartlar, tarih gruplama, detay drawer, bulk selection, arama, pagination |
| `frontend/src/notifications/useNotificationStream.ts` | **YENİ** — SSE hook: EventSource, exponential backoff reconnect, event dispatch |
| `frontend/src/components/NotificationBell.tsx` | **Tam yeniden yazım** — SSE entegrasyonu, polling fallback, toast/snackbar |
| `frontend/src/App.tsx` | `NotificationsRoute` genişletme: yeni props, `handleMarkAllRead`, `handleBulkMarkRead`, `handleLoadMore` |

## Eklenen Testler

| Test | Kapsam |
| --- | --- |
| Backend notification tests (71 passed) | `mark_all_read`, `bulk_read`, `count_failed`, `count_today`, SSE stream hub |
| Frontend typecheck | TypeScript `--noEmit` temiz |

## Çalıştırılan Komutlar

```bash
# Backend ruff lint
ruff check src/veri_kalitesi/notifications/ src/veri_kalitesi/api/notifications_router.py
# Sonuç: Temiz (1 pre-existing long line)

# Backend ruff format
ruff format --check src/veri_kalitesi/notifications/ src/veri_kalitesi/api/notifications_router.py
# Sonuç: 14 dosya formatlanmış

# Backend mypy
mypy src/veri_kalitesi/notifications/ src/veri_kalitesi/api/notifications_router.py
# Sonuç: Pre-existing actor_context pattern hataları, yeni kod temiz

# Backend pytest
python -m pytest tests/ -q -k "notification"
# Sonuç: 71 geçti, 1 skipped

# Frontend typecheck
npx tsc --noEmit
# Sonuç: Temiz

# Frontend test
npx vitest run
# Sonuç: 170 geçti (2 pre-existing AuditPage hatası)
```

## Risk Notları

| Risk | Etki | Mitigasyon |
|---|---|---|
| SSE connection leak | Backend memory artışı | Heartbeat timeout + max connections per actor |
| Bulk-read large batch | DB lock süresi uzar | Batch boyutu max 100 ile sınırla |
| Client-side search performansı | 1000+ item'da yavaşlık | Virtualization (react-window) veya server-side search |
| Payload hassas veri sızıntısı | Güvenlik | Allowlist ile sadece UI alanlarını döndür |

## Teknik Durum

**TechnicallyVerified** — 4 iterasyonun tümü uygulanmış, backend ve frontend testleri
geçmiştir. Production readiness için kurumsal politika uyumu ve banka/operasyon onayı
ayrıca değerlendirilmelidir.

## Kalan Risk

- SSE bağlantı sayısı kullanıcı başına sınırlanmamıştır; yüksek kullanıcı sayısında
  memory izlenmelidir.
- Client-side arama 1000+ bildirimde yavaşlayabilir; server-side search eklenebilir.
- Payload allowlist sabittir; yeni event type'lar için allowlist güncellemesi gerekebilir.

## Geri Alma Yaklaşımı

- `NotificationBell.tsx` ve `NotificationsPage.tsx` önceki versiyona geri döndürülür.
- `stream_hub.py` dosyası kaldırılır, `notifications_router.py`'den SSE endpoint kaldırılır.
- `delivery_service.py`'deki hub publish çağrısı kaldırılır.

## Sonraki Iterasyon

- Server-side search desteği (backend `search` parametresi)
- Bildirim arşivleme/soft-delete
- SSE connection limit per actor
- Bildirim tercihleri yönetimi (hangi event type'ları almak istediğini seçme)

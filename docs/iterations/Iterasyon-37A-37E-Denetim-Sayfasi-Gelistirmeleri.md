---
iteration: 37A-37E
status: in_progress
completed_at: null
decision_reference: USER-DECLARATION-2026-08-AUDIT-PAGE-ITERATIONS
---

# İterasyon 37A–37E — Denetim Sayfası Geliştirmeleri

## Amaç

Mevcut denetim sayfası yalnızca temel liste, filtre ve bütünlük kartı içeriyor.
SRS (FR-077-079, UC-016) ve GAP-001 notları şu eksiklikleri tespit etti:
olay detay görünümü yok, dışa aktarma yok, correlation ID arama bağlı değil,
action filtresi serbest metin, özet istatistikleri sınırlı, özel tarih aralığı
seçilemiyor, bağlamsal navigasyon yok.

Plan 5 iterasyona bölünmüştür. Her iterasyon dikey kesittir
(backend + frontend + test).

## Mevcut FR/UC/RULE

- **FR-077**: Kritik işlemlerin denetim kaydı
- **FR-078**: Denetim kayıtlarının filtrelenmesi ve dışa aktarılması
- **FR-079**: Denetim bütünlüğünün periyodik doğrulanması
- **UC-016**: Denetim kayıtlarının incelenmesi

---

## İterasyon 37A — Olay Detay Görünümü ve Correlation Arama

**Durum:** `TechnicallyVerified`

**Amaç:** UC-016 temel akışının 4. adımını (kayıt detayını açma) ve
correlation ID aramayı tamamlamak. En kritik fonksiyonel boşluk.

### Backend değişiklikleri

1. `src/veri_kalitesi/api/models.py` — `AuditEventListItemResponse`'a alanlar:
   - `old_value_summary: dict[str, Any] | None`
   - `new_value_summary: dict[str, Any] | None`
   - `redacted_fields: tuple[str, ...]`
   - `event_hash: str`
   - `previous_event_hash: str`

   `from_domain` metodunda eşleme güncellendi.

2. `AuditEventListResponse`'a `first_invalid_event_id: str | None` alanı eklendi.

3. `GET /api/v1/audit/events` endpoint'i `correlation_id` parametresini
   zaten destekliyor — değişiklik gerekmez.

### Frontend değişiklikleri

4. `frontend/src/audit/model.ts` — Yeni alanlar arayüzlere eklendi,
   `auditPageFromApi` dönüşümü ve `AuditEventListApiResponse` tipi güncellendi.

5. `frontend/src/audit/AuditPage.tsx`:
   - EventRow'a tıklanabilirlik (`onClick`, `role="button"`, `tabIndex={0}`,
     klavye Enter/Space desteği).
   - MUI `Drawer` (sağdan, `anchor="right"`, `width={480}`) ile olay detay
     paneli: action, result badge,OccurredAt, aktör bilgisi, nesne bilgisi,
     eski/yeni değer JSON gösterimi, maskelenmiş alanlar, bütünlük hash'leri.
   - "İlişkili correlation olayları" butonu.

6. Filtre paneline "İlişki Kodu" `TextField` eklendi.

7. `frontend/src/audit/api.ts` — `correlation_id` parametresi API çağrısına
   eklendi.

### Test ve sentetik veri

- `model.test.ts` — Yeni alanların dönüşüm testi.
- `AuditPage.test.tsx` — Drawer açılma/kapanma, correlation filtresi testleri.
- `api.test.ts` — `correlation_id` parametresi testi.
- Backend testleri — Yeni alanların doğrulama testi.
- `syntheticAuditPage` items'larına örnek old/new değerler eklendi.

### Storybook

- `AuditPage.stories.tsx` — `DetailDrawerOpen` story'si (play function ile).

### Kabul kriterleri

- [x] Olay satırına tıklanınca detay drawer'i açılır.
- [x] Eski/yeni değer özeti görüntülenür; maskelenmiş alanlar listelenir.
- [x] Correlation ID filtresi uygulanır ve API'ye iletilir.
- [x] "İlişkili correlation olayları" butonu aynı correlation ID ile sorgu yapar.
- [x] Tüm mevcut testler geçer; yeni alanlar için testler eklenir.
- [x] `mypy`, `ruff`, `vitest`, `pytest` yeşil.

---

## İterasyon 37B — Dışa Aktarma ve İşlem Dropdown

**Durum:** `Planned`

**Amaç:** FR-078 zorunlu gereksinimi olan dışa aktarma ve UX iyileştirmesi
olarak action filtresinin dropdown'a dönüştürülmesi.

**FR/UC:** FR-078 (Must), UC-016 (adım 6-7)

### Backend değişiklikleri

1. `src/veri_kalitesi/api/audit_router.py` — Yeni endpoint:
   ```
   GET /api/v1/audit/events/export
   ```
   - Mevcut filtre parametrelerini aynen kullan.
   - `format` query parametresi: `csv` veya `json` (varsayılan `csv`).
   - Yanıt `StreamingResponse` ile; `Content-Type: text/csv` veya
     `application/json`, `Content-Disposition: attachment`.
   - `Cache-Control: no-store`.
   - Dışa aktarma işlemi `AuditService.append` ile audit loga yazılır
     (action=`AUDIT_EXPORT_COMPLETED`, object_type=`AuditExport`).
   - Yetki: mevcut `AUDIT_VIEWER` rol kontrolü.
   - Sayfa sınırı: export için max 10000 kayıt (policy'ye eklenecek).

2. `src/veri_kalitesi/audit/models.py` — `AuditAccessPolicy`'ye
   `max_export_size: int = 10000` ekle.

3. Yeni yardımcı modül: `src/veri_kalitesi/audit/export.py`:
   - `AuditEventExporter` sınıfı: `AuditQueryPage` alır, CSV/JSON formatına
     dönüştürür.
   - CSV sütunları: sequence_no, occurred_at, actor_id, actor_type, action,
     object_type, object_id, result, reason_code, correlation_id,
     redacted_field_count.
   - Eski/yeni değerler export'a dahil edilmez (veri-minimum).

4. `src/veri_kalitesi/api/audit_router.py` — Yeni metadata endpoint:
   ```
   GET /api/v1/audit/actions
   ```
   - Mevcut action kodlarını ve Türkçe etiketlerini döndürür.

### Frontend değişiklikleri

5. Action filtresini `TextField`'ten `Select` dropdown'a dönüştür.

6. Filtre panelinin yanına "Dışa Aktar" butonu ekle:
   - `Dialog` ile format seçimi (CSV / JSON).
   - Başarılı indirme sonrası toast/snackbar.
   - Yetkisiz durumda buton gizlenir.

7. `frontend/src/audit/api.ts` — `fetchAuditExport` fonksiyonu.

### Test değişiklikleri

8. Backend: `tests/unit/test_audit_export.py` — CSV/JSON format doğrulaması.
9. Backend: `tests/integration/test_audit_export_lifecycle.py`.
10. Frontend: `api.test.ts` — Export API çağrısı testi.
11. Frontend: `AuditPage.test.tsx` — Dropdown seçimi, dışa aktarma dialog testi.

### Kabul kriterleri

- [ ] CSV ve JSON formatında dışa aktarma çalışır.
- [ ] Dışa aktarma işlemi audit loga yazılır.
- [ ] Action filtresi dropdown'dan seçilir; serbest metin değil.
- [ ] Yetkisiz kullanıcı dışa aktaramaz.
- [ ] `mypy`, `ruff`, `vitest`, `pytest` yeşil.

---

## İterasyon 37C — Özel Tarih Aralığı ve Özet İstatistikleri

**Durum:** `Planned`

**Amaç:** Geliştirilmiş filtreleme (özel tarih) ve denetçi için genel
durum görünümü.

**FR/UC:** FR-078 (filtreleme zenginliği), UC-016

### Backend değişiklikleri

1. `GET /api/v1/audit/events` — `period_start` query parametresi ekle.
   `period_start` belirtilirse `days` yerine `period_start`/`period_end`
   aralığı kullanılır.

2. Yeni endpoint: `GET /api/v1/audit/summary`
   - Yanıt modeli: `total_count`, `result_distribution`,
     `action_distribution`, `top_actors`, `period_start`, `period_end`.
   - Repository'ye `query_summary` metodu.
   - SQL `GROUP BY` sorgularıyla implemente edilir.

### Frontend değişiklikleri

3. `AuditQueryFilters`'a `periodStart: string | null` ekle.

4. Tarih filtresini genişlet: "Özel aralık" seçeneği + iki `DatePicker`.

5. Özet istatistik kartları: sonuç dağılımı, en sık işlemler,
   en aktif aktörler.

6. `fetchAuditSummary` API fonksiyonu ekle.

### Test değişiklikleri

7. Backend: `tests/unit/test_audit_summary.py`.
8. Backend: Entegrasyon testi — `period_start`/`period_end` filtreleme.
9. Frontend: `model.test.ts` ve `AuditPage.test.tsx`.

### Kabul kriterleri

- [ ] Özel tarih aralığı seçilebilir ve API'ye iletilir.
- [ ] Özet istatistik kartları sonuç dağılımı, en sık işlemler ve
      en aktif aktörleri gösterir.
- [ ] Filtre değiştiğinde özet kartları güncellenir.
- [ ] `mypy`, `ruff`, `vitest`, `pytest` yeşil.

---

## İterasyon 37D — Bağlamsal Navigasyon ve Bütünlük Detayı

**Durum:** `Planned`

**Amaç:** Denetçinin olay-nesne geçişini ve bütünlük raporlama detayını
tamamlamak.

**FR/UC:** FR-079 (periyodik bütünlük raporlama), UC-016

### Frontend değişiklikleri (backend değişikliği yok)

1. EventRow'da `objectType` + `objectId` tıklanabilir link:
   - `QualityRule` → `/rules`
   - `DataSource` → `/data-sources/{objectId}`
   - `DataQualityIssue` → `/issues/{objectId}`
   - `ScoringConfiguration` → `/scores`
   - `UserSession` → yönlendirme yok

2. Bütünlük kartına tıklanınca detay Drawer:
   - Kontrol edilen kayıt sayısı, geçerli/geçersiz durumu.
   - Geçersiz ise `firstInvalidEventId`.
   - "İlk geçersiz olayı gör" butonu.

3. "Bu nesnenin tüm audit kayıtları" quick-filter:
   - `AuditQueryFilters`'a `objectId: string` ekle.
   - `api.ts`'de `object_id` parametresini ekle.

### Test değişiklikleri

4. `AuditPage.test.tsx` — Nesne linki, bütünlük drawer, quick-filter testleri.
5. `api.test.ts` — `object_id` parametresi testi.
6. Playwright E2E — Nesne linkinden yönlendirme senaryosu.

### Kabul kriterleri

- [ ] Audit olaylarındaki nesne referansları tıklanabilir link olarak gösterilir.
- [ ] Bilinen objectType'ler doğru sayfalara yönlendirir.
- [ ] Bütünlük kartı tıklanınca detay drawer'i açılır.
- [ ] Quick-filter ile aynı nesnenin tüm audit kayıtları listelenir.
- [ ] `mypy`, `ruff`, `vitest`, `playwright` yeşil.

---

## İterasyon 37E — Timeline Görünümü ve Canlı Yenileme

**Durum:** `Planned`

**Amaç:** Korelasyonlu olay takibi ve operasyonel farkındalık.

**FR/UC:** UC-016 (alternatif akışlar), operasyonel verimlilik

### Backend değişiklikleri

1. Yeni endpoint: `GET /api/v1/audit/events/grouped`
   - `correlation_id` parametresi zorunlu.
   - Aynı correlation ID'ye sahip tüm olayları kronolojik sırada döndürür.
   - `page_size` sınırı yükseltilir (max 500).

### Frontend değişiklikleri

2. Görünüm modu değiştirici: `ToggleButtonGroup` (Liste / Timeline).

3. Timeline komponenti (`AuditTimeline.tsx`):
   - Dikey zaman çizelgesi, correlation-bazlı gruplandırma.
   - Deterministik renk ataması (hash ile).
   - Tıklanabilir düğümler: detay drawer'i açar.

4. Canlı yenileme mekanizması:
   - Otomatik yenileme seçici: Kapalı / 30sn / 1dk / 5dk.
   - `setInterval` ile polling.
   - "X yeni olay yüklendi" banner'ı.

5. `fetchGroupedAuditEvents` API fonksiyonu.

### Test değişiklikleri

6. `AuditPage.test.tsx` — Görünüm modu, timeline testleri.
7. `AuditTimeline.test.tsx` — Timeline komponenti testleri.
8. `AuditRoute.test.tsx` — Canlı yenileme interval testi.
9. Backend: `tests/unit/test_audit_grouped.py`.

### Kabul kriterleri

- [ ] Timeline görünümü olayları kronolojik ve correlation-bazlı gruplanmış
      gösterir.
- [ ] Görünüm modları arası geçiş sorunsuzdur.
- [ ] Otomatik yenileme çalışır; yeni olaylar banner ile bildirilir.
- [ ] `mypy`, `ruff`, `vitest`, `pytest` yeşil.

---

## İterasyonlar Arası Bağımlılıklar

```
37A (Olay Detay + Correlation) ✅ TechnicallyVerified
 |
 +---> 37B (Dışa Aktarma + Action Dropdown) 📋 Planned
 |
 +---> 37C (Özel Tarih + Özet İstatistik) 📋 Planned
        |
        +---> 37D (Bağlamsal Navigasyon + Bütünlük Detayı) 📋 Planned
               |
               +---> 37E (Timeline + Canlı Yenileme) 📋 Planned
```

- 37A diğer tüm iterasyonların ön koşuludur.
- 37B ve 37C bağımsız olarak paralel çalışabilir.
- 37D, 37A'nın drawer ve model genişletmelerine bağımlıdır.
- 37E, 37D'nin navigasyon ve drawer bileşenlerini yeniden kullanır.

## Dosya Etki Haritası

| Dosya | 37A | 37B | 37C | 37D | 37E |
|---|---|---|---|---|---|
| `src/veri_kalitesi/api/models.py` | M | - | - | - | - |
| `src/veri_kalitesi/api/audit_router.py` | - | M | M | - | M |
| `src/veri_kalitesi/audit/models.py` | - | M | - | - | - |
| `src/veri_kalitesi/audit/export.py` | - | Yeni | - | - | - |
| `src/veri_kalitesi/audit/repository.py` | - | - | M | - | - |
| `frontend/src/audit/model.ts` | M | M | M | M | M |
| `frontend/src/audit/api.ts` | M | M | M | M | M |
| `frontend/src/audit/AuditPage.tsx` | M | M | M | M | M |
| `frontend/src/audit/AuditRoute.tsx` | - | - | - | - | M |
| `frontend/src/audit/AuditTimeline.tsx` | - | - | - | - | Yeni |
| `frontend/src/audit/AuditPage.test.tsx` | M | M | M | M | M |
| `frontend/src/audit/api.test.ts` | M | M | M | M | M |
| `frontend/src/audit/model.test.ts` | M | - | M | - | - |
| `frontend/src/audit/AuditPage.stories.tsx` | M | - | - | - | - |

## Risk ve Notlar

- **Veri-minimum ilkesi:** Dışa aktarmada old/new value summary dahil edilmez.
  Bu alanlar yalnızca interaktif detay görünümünde sunulur ve redaksiyon
  politikasına tabidir.
- **Export boyut sınırı:** 10000 kayıt policy sınırı; daha geniş sorgular
  arşiv raporu gerektirir (UC-016 alternatif akış — bu planda kapsam dışı).
- **Timeline büyük veri:** 100'den fazla olay için virtualization gerekebilir;
  ilk adımda basit render, performans sorunu tespit edilirse `react-window`
  eklenir.
- **Canlı yenileme:** WebSocket yerine polling kullanılır; backend'de WebSocket
  altyapısı yoktur ve bu planda kapsam dışıdır.
- **Migration:** Bu iterasyonların hiçbiri veritabanı migration gerektirmez;
  mevcut `audit_events` tablosundaki alanlar kullanılır.

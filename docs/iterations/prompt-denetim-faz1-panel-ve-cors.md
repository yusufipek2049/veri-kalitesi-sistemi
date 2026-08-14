# Denetim Faz 1: Sürüm Engelleyen Düzeltmeler

## Bağlam

Kod tabanı denetiminde tespit edilen, **şu anda sürümü engelleyen** iki bağımsız kusuru
düzeltiyorsun. İkisi de küçük ama ikisi de sahada kırılmaya yol açıyor.

**Bağımlılık:** Yok. İlk yapılacak faz budur.

### Kusur A — Panel derlenmiyor

`npm run build` (`tsc -b && vite build`) iki hatayla duruyor. Bu yalnızca bir tip hatası
değil: `Search` bileşeni çalışma zamanında tanımsız olduğu için panel render sırasında
çöküyor. Vitest'teki tek başarısız test de tam olarak budur.

```
src/dashboard/DashboardPage.tsx(618,48): error TS2304: Cannot find name 'Search'.
src/dashboard/DashboardPage.tsx(944,76): error TS2322:
  Property 'datasetsBySource' does not exist on type
  'IntrinsicAttributes & SourceTableProps'.
```

İlgili yerler:

- `frontend/src/dashboard/DashboardPage.tsx:618` — `<Search aria-hidden="true" size={16} />`
  kullanılıyor ama dosyada `lucide-react` importu yok.
- `frontend/src/dashboard/DashboardPage.tsx:454-458` — `SourceTableProps` arayüzü
  `sources`, `sourceNames`, `sparklinesBySource` alanlarını tanımlıyor.
- `frontend/src/dashboard/DashboardPage.tsx:944` — çağrı yerinde ek olarak
  `datasetsBySource` geçiliyor; arayüzde karşılığı yok.
- `frontend/src/dashboard/DashboardPage.tsx:507` — `SourceTable` fonksiyonu prop'ları
  yıkıyor (destructuring).

`datasetsBySource` çağrı yerinde hesaplanıyor ve tipi
`Map<string, { id: string; name: string; namespace: string }[]>`. `SourceTable` içinde
şu anda kullanılmıyor — yani ya arayüze eklenip tabloda kullanılmalı, ya da çağrı
yerinden kaldırılmalı. **Karar senin**, ama gerekçesini yaz.

### Kusur B — CORS, PATCH ve PUT isteklerini reddediyor

`src/veri_kalitesi/api/app.py:184-191`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Accept", "Content-Type", CSRF_HEADER_NAME],
    expose_headers=["X-Correlation-ID", CSRF_HEADER_NAME],
)
```

API üç adet PATCH/PUT rotası sunuyor:

- `PATCH /api/v1/datasets/{dataset_id}`
- `PATCH /api/v1/fields/{field_id}`
- `PUT   /api/v1/data-sources/{data_source_id}/discovery-scope`

Frontend ilk ikisini `frontend/src/catalog/api.ts:201` (`updateDataset`) ve
`frontend/src/catalog/api.ts:217` (`updateField`) içinde çağırıyor.

Doğrulanmış davranış:

```
PATCH /api/v1/datasets/{id}          preflight → 400
PUT   /api/v1/data-sources/{id}/...  preflight → 400
POST  /api/v1/rules                  preflight → 200
```

Geliştirmede Vite proxy'si (`frontend/vite.config.ts`) isteği aynı-köken yaptığı için
sorun görünmüyor. Frontend ayrı bir kökenden sunulduğu anda katalog düzenleme ve keşif
kapsamı güncelleme sessizce kırılır.

## Görev

1. **`Search` importunu ekle.** Dosyadaki mevcut `lucide-react` import konvansiyonuna uy
   (diğer panel dosyalarına bak).
2. **`SourceTableProps` ile çağrı yerini uzlaştır.** Ya `datasetsBySource` alanını arayüze
   ekleyip tabloda anlamlı şekilde kullan, ya da çağrı yerinden kaldır. Ölü prop bırakma.
3. **CORS `allow_methods` listesini rotalarla hizala.** `PATCH` ve `PUT` ekle. Rota tablosu
   ile middleware yapılandırmasının ayrışmasını önleyecek bir yaklaşım tercih et
   (örneğin sabit bir liste yerine desteklenen metotları tek yerde tanımlamak).
4. **Regresyon testi yaz.** CORS için preflight testi; panel için mevcut başarısız testin
   geçtiğini doğrula.

## Invariantlar

- CORS `allow_origins` asla joker (`*`) kabul etmemeli — `create_dashboard_api` içindeki
  mevcut doğrulama korunacak.
- `allow_headers` ve `expose_headers` daraltılmayacak; CSRF başlığı korunacak.
- `OPTIONS` dışındaki güvenlik davranışı (fail-closed resolver, CSRF koruması)
  değiştirilmeyecek.
- Panelin mevcut görsel davranışı bozulmayacak.
- Yeni üçüncü parti bağımlılık yok.

## Kabul Kriterleri

1. `cd frontend && npm run build` hatasız tamamlanıyor.
2. `cd frontend && npx tsc -b --pretty false` sıfır hata veriyor.
3. `cd frontend && npm test` — 199/199 test geçiyor (şu anda 198 geçiyor, 1 başarısız).
4. Yeni test: `PATCH /api/v1/datasets/{id}` preflight isteği 200 dönüyor ve
   `access-control-allow-methods` başlığında `PATCH` var.
5. Yeni test: `PUT /api/v1/data-sources/{id}/discovery-scope` preflight 200 dönüyor.
6. Mevcut test: joker CORS kökeni hâlâ `ValueError` ile reddediliyor.
7. `python -m pytest` — mevcut testlerde regresyon yok.

## Teslim Formatı

- **Kod:** Değiştirilen dosyalar ve her değişikliğin gerekçesi.
- **Karar:** `datasetsBySource` için hangi yolu seçtin ve neden.
- **Testler:** Kabul kriterlerinin her birini karşılayan test adları.
- **Test çıktısı:** `npm run build`, `npm test` ve `pytest` ham çıktıları.
- **Varsayımlar:** Yapılan varsayımlar ve açık kalan sorular.

## Çalışma Kuralları

- Mevcut kod stiline uy (Türkçe docstring/yorum, mevcut import düzeni).
- Yeni üçüncü parti bağımlılık ekleme.
- Testleri çalıştır ve sonucu olduğu gibi bildir.
- Belirsizlik varsa varsayımını açıkça yaz ve devam et.

# Denetim Faz 7: Tip Güvenliği Borcunu Kapatma

## Bağlam

`mypy` şu anda 3 dosyada 7 hata veriyor. Bunların çoğu aynı kök nedene sahip:
**bağımlılıklar `object` olarak tiplenmiş**, yani tip sistemi devre dışı bırakılmış.

```
src/veri_kalitesi/executions/postgresql_executor.py:72:
  "object" has no attribute "name"  [attr-defined]
src/veri_kalitesi/api/postgresql_execution.py:221:
  "object" has no attribute "get_version"  [attr-defined]
src/veri_kalitesi/api/postgresql_execution.py:231:
  "object" has no attribute "get_rule"  [attr-defined]
src/veri_kalitesi/api/postgresql_execution.py:242:
  "object" has no attribute "list_versions"  [attr-defined]
src/veri_kalitesi/api/postgresql_execution.py:253:
  "object" has no attribute "get_dataset"  [attr-defined]
src/veri_kalitesi/jobs/production.py:187:
  "object" has no attribute "actor_id"  [attr-defined]
src/veri_kalitesi/jobs/production.py:238:
  Argument "repository" to "ScoringService" has incompatible type
  "PostgreSQLScoreRepository"; expected "SQLiteScoreRepository"  [arg-type]
```

Bu desenin görünür bir örneği `api/app.py` içindeki `CatalogDatasetResolver`:

```python
class CatalogDatasetResolver:
    """CatalogReader'yi DatasetResolver protokolune uyarlayan adapter."""

    def __init__(self, reader: Any) -> None:
```

`Any` ve `object` kullanımı, bağımlılık enjeksiyonunun tip sözleşmesini yok ediyor.
Kod tabanı zaten `Protocol` tabanlı sözleşmeleri yaygın ve doğru kullanıyor
(`StateChangeBoundary`, `ScheduleRepository`, `InAppChannelAdapter`, …) — bu fazda
aynı deseni eksik kalan yerlere uyguluyorsun.

Ayrıca `create_dashboard_api` imzasında `job_queue_repository: object | None = None` ve
`notification_query_service: object | None = None` gibi tiplenmemiş parametreler var
(`api/app.py:136`) — bunlar da aynı borcun parçası.

**Not:** `production.py:238` hatası ikili kalıcılık katmanının doğrudan sonucudur ve
**Faz 3'te** kapatılır. Bu fazda kalan 6 hatayı ele al; Faz 3 tamamlandıysa 7'sini birden.

**Bağımlılık:** Yok, ancak Faz 3 ile sıralaması önemli — Faz 3 önce yapılırsa
`production.py:238` orada kapanır.

**Kapsam dışı:** `mypy`'ın CI kapısına bağlanması ve `pyproject.toml`'a bağımlılık olarak
eklenmesi bu fazın kapsamı dışındadır.

## Görev

1. **Her `object` / `Any` tiplenmiş bağımlılık için gerçek sözleşmeyi çıkar.** İlgili
   nesnenin hangi metotları çağrılıyorsa onları içeren bir `Protocol` tanımla. Kod tabanının
   mevcut protokol konvansiyonuna uy (dosya yerleşimi, adlandırma, `...` gövdeler).
2. **Somut sınıfa değil protokole bağlan.** Protokolü tanımlarken tüketici tarafında tut,
   üretici tarafında değil — böylece bağımlılık yönü tersine döner ve `postgresql_*`
   modülleri API katmanına sızmaz.
3. **`CatalogDatasetResolver.__init__(reader: Any)` tipini düzelt.** `CatalogReader`'ın
   fiilen kullanılan yüzeyi (`get_data_source`, `list_datasets`) için protokol tanımla.
4. **`create_dashboard_api` içindeki `object | None` parametrelerini tiplendir.**
   (Bu imza Faz 8'de yeniden düzenlenecek — orada çakışma olmaması için Faz 8'i
   yapıyorsan bu adımı orada birleştir.)
5. **`type: ignore` ekleyerek geçiştirme.** Hiçbir hatayı `# type: ignore` ile kapatma.
   Gerçekten kaçınılmaz bir durum varsa gerekçesini yaz ve raporla.
6. **Genişletilmiş kural kümesini ölç, düzeltme.** `ruff check --select E,F,W,I,B,UP,SIM,TCH,A,PTH,RUF`
   şu anda 2.872 bulgu veriyor. **Bu fazda toplu düzeltme yapma** — yalnızca kategori
   dağılımını raporla ki hangi kuralların blocking'e alınmaya hazır olduğu görülebilsin.

## Invariantlar

- **Davranış değişmeyecek.** Bu tamamen bir tipleme çalışmasıdır.
- Zorunlu ruff kümesi (`E,F`) temiz kalacak.
- Mevcut tüm testler geçmeye devam edecek.
- `Protocol` tanımları çalışma zamanında maliyet getirmeyecek — gerekiyorsa
  `TYPE_CHECKING` bloğu kullan.
- Bağımlılık enjeksiyonu deseni korunacak; tipleme uğruna somut sınıf importu eklenmeyecek.
- Yeni üçüncü parti bağımlılık yok.

## Kabul Kriterleri

1. `mypy src/` sıfır hata veriyor (Faz 3 yapılmadıysa yalnızca `production.py:238` kalır,
   gerekçesi raporlanır).
2. Kod tabanında yeni `# type: ignore` eklenmemiş — eklendiyse her biri gerekçelendirilmiş.
3. `CatalogDatasetResolver` artık `Any` almıyor.
4. `create_dashboard_api` imzasında `object` tipli parametre kalmamış
   (veya Faz 8'e devredildiği raporlanmış).
5. `ruff check .` (zorunlu `E,F` kümesi) temiz.
6. Genişletilmiş ruff kümesinin kural bazında dağılımı raporlanmış.
7. `python -m pytest` tamamen yeşil — davranış değişikliği yok.

## Teslim Formatı

- **Kod:** Değiştirilen dosyalar ve her protokolün nereye, neden konduğu.
- **Protokol envanteri:** Eklenen `Protocol` tanımları ve kapsadıkları yüzey.
- **Test çıktısı:** Ham `mypy`, `ruff` ve `pytest` sonuçları.
- **Ruff raporu:** Genişletilmiş kümenin kural bazında dağılımı ve hangi kuralların
  blocking'e alınmaya hazır olduğuna dair değerlendirme.
- **Varsayımlar:** Yapılan varsayımlar ve açık kalan sorular.

## Çalışma Kuralları

- Mevcut kod stiline uy (Türkçe docstring, `from __future__ import annotations`).
- Yeni üçüncü parti bağımlılık ekleme.
- Testleri çalıştır ve sonucu olduğu gibi bildir.
- Belirsizlik varsa varsayımını açıkça yaz ve devam et.

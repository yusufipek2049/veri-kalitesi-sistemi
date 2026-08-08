# Graphify Mimari Grafiği — Yapılandırma ve Politika

Bu belge, projenin mimari bilgi grafiğinin (graphify) yapılandırmasını,
kapsamını ve kalıcı baseline üretim politikasını tanımlar.

## Yapılandırma

| Parametre | Değer |
|---|---|
| Çıktı dizini | `build/graphify/` |
| Ortam değişkeni | `GRAPHIFY_OUT=build/graphify` |
| Ignore dosyası | `.graphifyignore` |
|Baseline özeti | `docs/quality/GRAPHIFY_BASELINE.md` (bu dosya) |

Çıktı dizini (`build/graphify/`) tamamen git-ignore edilmiştir;
cache, HTML görselleştirme ve JSON grafik dosyaları kaynak artifact
olarak izlenmez.

## Grafiğe Dahil Olan Dizinler

| Dizin | Kapsam |
|---|---|
| `src/` | Python backend uygulama kodu |
| `frontend/` | React/TypeScript frontend uygulaması |
| `alembic/` | Veri tabanı migration betikleri |
| `tests/` | Test katmanı (birim, entegrasyon, e2e) |

## Grafiğe Hariç Tutulan Dizinler

| Dizin | Gerekçe |
|---|---|
| `docs/` | Dokümantasyon — uygulama kodu değil |
| `tools/` | Geliştirme otomasyonu — ajan araçları |
| `scripts/` | Operasyonel betikler — uygulama kodu değil |
| `infra/` | Altyapı yapılandırması — container/DR |
| `archive/` | Dondurulmuş geçmiş snapshot'ler |
| `.github/` | CI/CD yapılandırması |
| `build/graphify/` | Graphify kendi çıktısı |

## Test Dizininin Grafa Dahil Edilmesi — Politika

**Karar:** `tests/` dizini mimari grafa **dahildir**.

**Gerekçe:**

1. **Bağımlılık görünürlüğü:** Test dosyaları `src/` modüllerine olan
   import bağımlılıklarını ortaya koyar; grafın kenar yapısını zenginleştirir.
2. **Mimari yansıma:** Test dizin yapısı (`unit/`, `integration/`, `e2e/`)
   uygulama katmanlarının mimari sınırlarını yansıtır.
3. **Etki analizi:** Bir kaynak dosya değiştiğinde hangi testlerin etkilendiğini
   graf üzerinden okumak mümkündür.
4. **Topluluk tespiti:** Graphify clustering algoritması test-sour
   arasındaki coupling'i doğal olarak gruplar.

**İstisna:** `tests/support/` altındaki yardımcı modüller graf tarafından
taranır ancak bağımsız bir düğüm kümesi oluşturmaz; bağlı oldukları test
topluluklarının parçası olarak görünürler.

**Yeniden değerlendirme ölçütü:** Graf düğüm sayısı 2× artar ve test
düğümleri kaynak düğümlerini aşarsa, `tests/` hariç tutma yeniden
değerlendirilir.

## Baseline Üretimi

```bash
GRAPHIFY_OUT=build/graphify graphify update .
```

Yeniden çalıştırma gerektiren durumlar:
- Kaynak dizin yapısı değiştiğinde
- Yeni modül eklendiğinde veya kaldırıldığında
- `.graphifyignore` güncellendiğinde

## Çıktı Dosyaları

| Dosya | Açıklama | Git |
|---|---|---|
| `build/graphify/graph.json` | Düğüm-kenar graf verisi | Izlenmez |
| `build/graphify/graph.html` | Etkileşimli görselleştirme | Izlenmez |
| `build/graphify/GRAPH_REPORT.md` | Topluluk raporu | Izlenmez |
| `build/graphify/manifest.json` | Dosya manifesti | Izlenmez |
| `build/graphify/cache/` | AST önbelleği | Izlenmez |
| `build/graphify/.graphify_analysis.json` | Analiz meta verisi | Izlenmez |
| `docs/quality/GRAPHIFY_BASELINE.md` | Bu politika belgesi | Izlenir |

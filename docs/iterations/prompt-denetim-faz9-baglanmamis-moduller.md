# Denetim Faz 9: Bağlanmamış Modüller Kararı

## Bağlam

API uygulaması (`veri_kalitesi.api.app`, `veri_kalitesi.api.composition`) ve worker
(`veri_kalitesi.jobs.entrypoint`) giriş noktalarından başlayarak AST tabanlı import
erişilebilirlik analizi yapıldı. Sonuç:

**Kaynak kodun %34'ü (23.770 / 69.656 satır) çalışan sistemden erişilemiyor.**

Bu kod ölü değil — yazılmış, test edilmiş, sadece hiçbir yere bağlanmamış.

| Modül | Satır | Erişilen | Tek giriş noktası |
| --- | --- | --- | --- |
| `secure_sdlc` | 3.247 | %0 | **yok — sadece kendi testleri** |
| `retention` | 2.573 | %0 | **yok — sadece kendi testleri** |
| `incident_response` | 1.409 | %0 | **yok — sadece kendi testleri** |
| `environment_security` | 418 | %0 | **yok — sadece kendi testleri** |
| `reporting` | 2.130 | %0 | yalnızca `scripts/seed_database.py` |
| `servicenow` | 1.917 | %0 | yalnızca `infra/enterprise-lab/e2e` |
| `enterprise_lab` | 920 | %0 | yalnızca `infra/enterprise-lab/e2e` |
| `synthetic_data` | 4.802 | %0 | geliştirici script'leri (meşru) |
| `lineage` | 1.762 | %26 | `impact.py` bağlı değil |
| `executions` | 4.751 | %69 | `scheduling.py` bağlı değil (Faz 4) |

### Öne çıkan iki durum

**1. Giriş noktası hiç olmayan 7.647 satır.** `secure_sdlc`, `retention`,
`incident_response`, `environment_security` — hiçbir API rotası, script veya worker
işleyicisi bunlara ulaşmıyor. Bunlar bankacılık uyumluluk kanıtı üreten modüller
(yasal saklama, saklama süresi, olay müdahalesi, ortam güvenliği). Kanıt üretiliyor
ama **kanıtı sistemden dışarı alacak hiçbir yüzey yok.**

**2. `reporting` (2.130 satır) kullanıcıya kapalı.** 58 API rotasının hiçbiri rapor
sunmuyor. `alembic` içinde `reports` ve `report_schedules` tabloları var, PostgreSQL
depoları yazılmış (`PostgreSQLReportRepository`, `PostgreSQLReportScheduleRepository`),
ama modüle yalnızca `seed_database.py` dokunuyor.

**Bağımlılık:** Faz 4 (zamanlayıcı) tamamlanmış olmalı — `executions/scheduling.py` ve
`reporting/scheduling.py` orada bağlanıyor, bu fazda tekrar ele alınmayacak.

## Görev

1. **Her bağlanmamış modül için niyeti tespit et.** Kodun kendisine bakarak (dökümana
   değil) şu üç kategoriden birine yerleştir ve kanıtını yaz:
   - **(a) Bağlanmalı** — gerçek bir kullanıcı/sistem ihtiyacına karşılık geliyor,
     yalnızca yüzeyi eksik.
   - **(b) Araç/lab yolu meşru** — script veya lab e2e üzerinden kullanılıyor, API'ye
     bağlanması gerekmiyor (`synthetic_data`, muhtemelen `enterprise_lab`).
   - **(c) Arşivlenmeli** — karşılığı olmayan, terk edilmiş veya erken yazılmış kod.

2. **Kategori (a) için yüzey tasarla ve uygula.** Her biri için en küçük anlamlı yüzey:
   API rotası mı, worker job'ı mı, yoksa CLI komutu mu? Kararı gerekçelendir.
   **Önceliklendirme önerisi:**
   - `reporting` — şema, depo ve zamanlayıcı hazır; kullanıcıya kapalı olması en büyük
     kayıp. Önce bunu bağla.
   - `retention` + `secure_sdlc` — uyumluluk kanıtının dışa alınabilmesi bankacılık
     bağlamında somut değer.
   - `incident_response`, `environment_security` — kapsamı en belirsiz olanlar;
     tespitten sonra karar ver.

3. **Kategori (c) için arşivle, silme.** Repoda `archive/` dizini zaten var ve bu amaçla
   kullanılıyor. Silme yerine taşı; taşıma gerekçesini ve geri getirme yolunu yaz.

4. **`lineage/impact.py` özel durumu.** Modülün %26'sı erişilebilir; `impact.py` bağlı
   değil. Etki analizi ("bu kalite ihlali hangi aşağı akış varlıklarını etkiler")
   bankacılık bağlamında yüksek değerli bir yetenek ve kod zaten yazılmış. Bağlanabilirliğini
   ayrıca değerlendir ve raporla.

5. **Erişilebilirlik ölçümünü tekrarla.** Faz sonunda %34'ün ne olduğunu raporla.

## Invariantlar

- **Bu faz kapsam kararı üretir, özellik icat etmez.** Bağlanmamış bir modüle yeni
  yetenek eklemek bu fazın işi değil; var olanı erişilebilir kılmak.
- Yeni yüzeyler mevcut güvenlik duruşuna uyacak: fail-closed yetkilendirme, CSRF,
  korelasyon kimliği, denetim kaydı. Sağlık uç noktaları dışında kimlik doğrulamasız
  yüzey eklenmeyecek.
- Uyumluluk kanıtı üreten modüllerin çıktısı kişisel veri sızdırmayacak; mevcut
  veri koruma konvansiyonlarına uyulacak.
- Şema kayması oluşmayacak — yeni tablo gerekiyorsa alembic migration'ı ile.
- Arşivlenen kodun testleri de birlikte taşınacak; `pytest` yeşil kalacak.
- Yeni üçüncü parti bağımlılık yok.

## Kabul Kriterleri

1. Her bağlanmamış modül için kategori tespiti ve kanıtı raporlanmış.
2. Kategori (a) modülleri için yüzey uygulanmış; her biri uçtan uca testle doğrulanmış.
3. `reporting` kullanıcı tarafından erişilebilir — rapor listeleme/getirme yüzeyi
   çalışıyor ve testli.
4. Kategori (c) modülleri `archive/` altına taşınmış; gerekçe ve geri getirme yolu yazılmış.
5. Yeni eklenen rotalar fail-closed yetkilendirmeye tabi — test.
6. Erişilebilirlik oranı yeniden ölçülmüş ve raporlanmış; %34 belirgin şekilde düşmüş.
7. `python -m pytest` tamamen yeşil.
8. `mypy src/` hata sayısı artmamış.

## Teslim Formatı

- **Tespit tablosu:** Modül → kategori → kanıt → karar.
- **Kod:** Eklenen yüzeyler ve taşınan modüller.
- **Tasarım kararı:** Her yeni yüzey için neden API/worker/CLI seçildiği.
- **Testler:** Eklenen test adları.
- **Test çıktısı:** Ham `pytest` ve `mypy` sonuçları.
- **Erişilebilirlik raporu:** Öncesi/sonrası yüzde ve modül bazında dağılım.
- **Varsayımlar:** Yapılan varsayımlar ve açık kalan sorular.

## Çalışma Kuralları

- Mevcut kod stiline uy (Türkçe docstring, `from __future__ import annotations`,
  frozen dataclass, `Protocol` tabanlı sözleşmeler).
- Yeni üçüncü parti bağımlılık ekleme.
- Testleri çalıştır ve sonucu olduğu gibi bildir.
- Belirsizlik varsa varsayımını açıkça yaz ve devam et.
- Bu faz geri alınması zor taşımalar içerir — taşımadan önce kategori tespitini
  tamamla ve raporla.

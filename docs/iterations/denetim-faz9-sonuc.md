# Denetim Faz 9 Sonuç Raporu

## Tespit tablosu

| Modül | Kategori | Kod kanıtı | Karar |
| --- | --- | --- | --- |
| `reporting` | (a) Bağlanmalı | PostgreSQL `reports`/`report_schedules` depoları ve migration'ları, `ReportWorker`, `ReportService` ve Faz 4 schedule tetikleyicisi hazırdı; production API composition'ında okuma servisi yoktu. | Sahiplik filtreli `GET /api/v1/reports` ve `GET /api/v1/reports/{report_id}` eklendi. |
| `retention` | (a) Bağlanmalı | `RetentionEvaluator`, provisional fail-closed katalog ve kalıcı dosya kullanabilen `SQLiteLegalHoldRepository` mevcut; production PostgreSQL depo/migration/politika sağlayıcısı yok. | Yeni ürün kalıcılığı icat edilmedi. Açıkça verilen legal-hold DB'sine karşı veri-minimum değerlendirme yapan `python -m veri_kalitesi.retention` CLI'ı eklendi. Provisional katalog süresi dolmuş kaydı disposal için onaylamaz. |
| `secure_sdlc` | (b) Araç yolu meşru | `__main__.py` doğrudan `secure_sdlc.cli.main` çağırıyor; scanner JSON kanıtı üretiyor, diğer sınıflar release/SAST/SBOM/pentest kanıt sözleşmeleri. | API'ye bağlanmadı; repository/release pipeline aracı olarak tutuldu. |
| `incident_response` | (c) Arşivlenmeli | Yalnız `SQLiteIncidentResponseRepository` var; production migration/adapter/politika composition'ı yok. Repository `external_notification_dispatched` değerini daima `false` yazar. | Kaynak ve testi birlikte `archive/` altına taşındı. |
| `environment_security` | (b) Lab yolu meşru | `enterprise_lab.gate` doğrudan `EnvironmentStartupGate` kullanıyor; `enterprise_lab.adapters` her sentetik adapter çağrısını `LabAdapterGate` ile koruyor. | Ayrı API yüzeyi eklenmedi; lab başlangıç/adapter kapısı olarak tutuldu. |
| `servicenow` | (b) Lab yolu meşru | `enterprise_lab.adapters.FakeServiceNowHttpAdapter` ve `infra/enterprise-lab/e2e/live_adapters.py` ServiceNow sözleşmelerini tüketiyor; gerçek üretim adapter'ı değil. | Lab e2e yolu korundu, production API'ye bağlanmadı. |
| `enterprise_lab` | (b) Lab yolu meşru | `__main__.py` doğrulanmış configuration kanıtı üretir; e2e adaptörleri yalnız sentetik/non-production gate sonrasında kurulur. | Mevcut CLI/e2e yüzeyi yeterli kabul edildi. |
| `synthetic_data` | (b) Araç yolu meşru | `generate_synthetic_test_data.py` ve `reset_synthetic_test_data.py`, `postgresql_dataset.main` çağırıyor; profil/ground-truth üretimi test verisi hazırlama işidir. | Runtime API'ye bağlanmadı. |
| `lineage/impact.py` | (a) Bağlanmalı | `assess_impact` kaynak/formül/zaman/güven durumlarını normalize ediyor; `root_cause_hypothesis` yalnız hipotez üretip doğrulanmış neden iddia etmiyor. Kod graph traversal veya ihlal→downstream lookup uygulamıyor. | Mevcut gerçek yetenek `python -m veri_kalitesi.lineage <input.json>` CLI'ıyla açıldı. “Aşağı akış varlıklarını bulur” diye API özelliği icat edilmedi. |
| `executions/scheduling.py` | (a), Faz 4'te bağlandı | Production worker composition'ı `SchedulingService` ve `ReportScheduleService` tetikleyicilerini kaydediyor. | Faz 9'da tekrar değiştirilmedi. |

## Yüzey tasarım kararları

### Reporting — API

Raporlar kullanıcı tarafından etkileşimli olarak listelenip ayrıntısı görüldüğü için
HTTP okuma yüzeyi seçildi. Yanıt; `parameters`, `online_file_reference` ve
`failure_reason` alanlarını bilerek taşımaz. Liste repository seviyesinde aktöre göre
filtrelenir. Tekil get başka kullanıcı raporunu `404` ile gizler ve denial audit'i
yazar. Her başarılı okuma da auditlidir; audit yazılamazsa sorgu fail-closed `503`
olur. Production preflight'a mevcut `reports` tablosu eklendi; yeni tablo/migration
gerekmedi.

### Retention — CLI

Mevcut kod record-by-record değerlendirme ve SQLite legal-hold geçmişi sunuyor,
production PostgreSQL lifecycle sunmuyor. Bu nedenle anonim ağ yüzeyi veya geçici
in-memory API yerine açık DB yolu isteyen yönetim CLI'ı seçildi. Çıktı kayıt
referansını içermez. Naive timestamp ve geçersiz politika/girdi fail-closed engellenir.

### Lineage impact — CLI

Kodun fiili sözleşmesi çevrimdışı kanıt belgesi üretmektir; katalog graph'ında
downstream traversal değildir. CLI seçimi var olan saf fonksiyonları erişilebilir
kılar ve yeni depo/graph semantics icat etmez. Kaynaksız `OBSERVED` değerler mevcut
domain davranışıyla `UNKNOWN` seviyesine düşürülür ve toplamdan çıkarılır.

## Arşiv

- Kaynak: `archive/modules/incident_response/`
- Test: `archive/tests/incident_response/test_incident_response.py`
- Gerekçe ve geri getirme koşulları:
  `archive/modules/incident_response/README.md`

Geri getirme; PostgreSQL şeması/repository'si, güvenilir politika sağlayıcısı ve dış
bildirim portu ayrı bir fazda tanımlandığında kaynak+testin aynı değişiklikte eski
konumlarına taşınmasıyla yapılır.

## Eklenen testler

- `test_report_list_and_get_are_owner_scoped_audited_and_data_minimum`
- `test_report_get_hides_another_users_report_and_audits_denial`
- `test_report_routes_fail_closed_without_identity`
- `test_retention_cli_evaluates_against_explicit_hold_database_without_identifier_leak`
- `test_retention_cli_fails_closed_for_naive_timestamps`
- `test_lineage_impact_cli_emits_sourced_non_aggregated_evidence`
- `test_lineage_impact_cli_downgrades_unsourced_observation_to_unknown`
- PostgreSQL integration composition testi `/api/v1/reports` ve
  `PostgreSQLReportRepository` kontrolüyle genişletildi (DB URL yoksa skip).

## Test çıktıları

Komut:

```text
.venv/bin/python -m pytest
```

Ham sonuç özeti:

```text
collected 1815 items
================ 1688 passed, 127 skipped in 116.40s (0:01:56) =================
```

Komut:

```text
mypy src/
```

Ham sonuç:

```text
src/veri_kalitesi/jobs/production.py:247: error: Argument "repository" to "ScoringService" has incompatible type "PostgreSQLScoreRepository"; expected "SQLiteScoreRepository"  [arg-type]
Found 1 error in 1 file (checked 230 source files)
```

Bu tek hata Faz 9 başlamadan önce dirty worktree'de değiştirilmiş
`jobs/production.py` içindedir ve Faz 9 kodundan kaynaklanmaz. Faz 9'da değişen tipli
yüzeylere yönelik kontrol:

```text
mypy src/veri_kalitesi/api/reporting_router.py src/veri_kalitesi/reporting/service.py src/veri_kalitesi/retention/cli.py src/veri_kalitesi/api/service_groups.py src/veri_kalitesi/api/app.py src/veri_kalitesi/api/composition.py
Success: no issues found in 6 source files
```

Dolayısıyla toplam mypy hata sayısı artırılmadı; tam depo hâlen önceden var olan tek
hatayla sıfır değildir.

## Erişilebilirlik raporu

Ölçüm `scripts/measure_runtime_reachability.py` ile aynı üç runtime kökünden yapılır:
`veri_kalitesi.api.app`, `veri_kalitesi.api.composition`,
`veri_kalitesi.jobs.entrypoint`. CLI/lab araçları bu runtime metriğine bilerek dahil
değildir; kategori (b) kararları bu yüzden yüzdeyi yapay biçimde yükseltmez.

| Modül | Önce erişilen | Sonra erişilen |
| --- | ---: | ---: |
| `secure_sdlc` | %0 | %0 runtime; mevcut CLI |
| `retention` | %0 | %0 runtime; yeni CLI |
| `incident_response` | %0 | kaynak ağacından arşive taşındı |
| `environment_security` | %0 | %0 runtime; enterprise-lab yolu |
| `reporting` | %0 | **%95,68** (2.260 / 2.362 satır) |
| `servicenow` | %0 | %0 runtime; lab e2e yolu |
| `enterprise_lab` | %0 | %0 runtime; CLI/e2e yolu |
| `synthetic_data` | %0 | %0 runtime; geliştirici script yolu |
| `lineage` | %26 | %26,28 runtime; `impact.py` için yeni CLI |
| `executions` | %69 | %83,96 (Faz 4 bağlantısı çalışma ağacında mevcut) |

Genel sonuç:

```text
Önce: 23.770 / 69.656 erişilemeyen satır = %34,00
Sonra: 20.963 / 71.344 erişilemeyen satır = %29,38
Fark: -4,62 yüzde puanı (göreli %13,59 azalma)
```

Toplam satır paydasındaki değişim, Faz 4–8 dirty worktree değişiklikleri, Faz 9
yüzey/test dışı kaynak ekleri ve incident modülünün arşive alınmasından gelir.

## Varsayımlar ve açık sorular

- CLI çalıştırma yetkisi işletim sistemi/repository erişimiyle yönetilir; CLI'lar
  anonim ağ yüzeyi değildir. HTTP kimlik/CSRF invariant'ı yalnız yeni reporting
  rotalarına uygulanır (ikisi de GET; trusted actor fail-closed zorunludur).
- Retention'ın provisional kataloğu banka-onaylı politika yerine geçmez. Production
  lifecycle için PostgreSQL kalıcılığı ve yönetilen politika kaynağı ayrı kapsamdır.
- `impact.py` downstream graph sorgusu içermediğinden böyle bir API adı/vaadi
  verilmedi. Gerçek downstream lookup için katalog lineage edge reader'ı gerekir;
  bu Faz 9 kapsamında yeni özellik olurdu.
- PostgreSQL gerektiren 127 test ortam değişkeni olmadığı için skip edildi; unit ve
  yerel integration testlerinin tamamı geçti.

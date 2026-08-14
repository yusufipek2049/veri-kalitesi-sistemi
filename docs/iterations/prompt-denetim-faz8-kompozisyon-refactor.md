# Denetim Faz 8: API Kompozisyonunu Sadeleştirme

## Bağlam

Bağımlılık enjeksiyonu doğru yapılmış — ama uygulama fabrikası bir tanrı-fonksiyona
dönüşmüş.

`src/veri_kalitesi/api/app.py:136` — `create_dashboard_api()` **hepsi `None` varsayılanlı
34 opsiyonel parametre** alıyor:

```python
def create_dashboard_api(
    *,
    actor_context_resolver: ActorContextResolver | None = None,
    bff_session_boundary: BffSessionBoundary | None = None,
    allowed_origins: Sequence[str] = (),
    data_origin: str = "runtime",
    data_source_query_service: DataSourceQueryService | None = None,
    data_source_mutation_service: DataSourceMutationService | None = None,
    execution_start_service: ExecutionStartService | None = None,
    execution_cancel_service: ExecutionCancelService | None = None,
    development_user_registry: DevelopmentUserRegistry | None = None,
    rule_query_service: RuleQueryService | None = None,
    ...
    issue_query_service: IssueQueryService | None = None,
    issue_investigation_service: IssueInvestigationService | None = None,
    issue_investigation_evidence_service: IssueInvestigationEvidenceService | None = None,
    issue_assignment_service: IssueAssignmentService | None = None,
    issue_assignee_option_provider: IssueAssigneeOptionProvider | None = None,
    issue_resolution_service: IssueResolutionService | None = None,
    issue_verification_service: IssueVerificationService | None = None,
    issue_closure_service: IssueClosureService | None = None,
    issue_creation_service: IssueCreationService | None = None,
    ...
    job_queue_repository: object | None = None,
    notification_query_service: object | None = None,
    notification_delivery_service: object | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> FastAPI:
```

Sorunlar:

- Hangi parametre kombinasyonunun geçerli olduğunu tip sistemi söylemiyor. Dokuz ayrı
  issue servisinden birini vermeyi unutmak derleme zamanında değil, çalışma zamanında
  ortaya çıkıyor.
- Fonksiyon içinde hâlihazırda elle tutarlılık doğrulaması yapılıyor
  (`actor_context_resolver` ve `bff_session_boundary` birlikte verilemez) — bu, tipin
  ifade edemediği kuralın koda taşınmış hâli.
- `object | None` tipli üç parametre tip güvenliğini tamamen kapatıyor (bkz. Faz 7).

Yanında iki aşırı büyümüş dosya var:

- `src/veri_kalitesi/data_sources/postgresql_repository.py` — 2.309 satır
- `src/veri_kalitesi/data_sources/service.py` — 2.246 satır

**Bağımlılık:** Faz 7 ile koordine edilmeli — `object | None` parametrelerinin
tiplendirilmesi iki fazda da geçiyor. İkisini birlikte yapmak veya Faz 7'yi önce
bitirmek tercih edilir.

## Görev

1. **Servisleri alan bazlı gruplara topla.** `IssueServices`, `RuleServices`,
   `DataSourceServices`, `ExecutionServices`, `CatalogServices`, `NotificationServices`
   gibi frozen dataclass'lar tanımla. Hedef: imza 34'ten yaklaşık 8'e insin.
2. **Eksik bağımlılığı derleme zamanında yakalanır kıl.** Bir alanın servis grubu
   veriliyorsa, o gruba ait tüm servisler zorunlu olsun — böylece "issue rotalarını
   kaydettim ama `issue_closure_service` vermedim" durumu tip hatası olsun.
3. **Karşılıklı dışlayan parametreleri tipe taşı.** `actor_context_resolver` ve
   `bff_session_boundary` aynı anda verilemiyor. Bunu çalışma zamanı `ValueError`'ı
   yerine tip düzeyinde ifade etmenin bir yolunu tasarla; mümkün değilse mevcut
   doğrulamayı koru ve gerekçesini yaz.
4. **`object | None` parametrelerini tiplendir** (Faz 7 ile ortak).
5. **`data_sources/service.py` ve `postgresql_repository.py` dosyalarını böl.**
   Bölme ölçütü sorumluluk olsun, satır sayısı değil. Herhangi bir davranış değişikliği
   yapma. Bölme gerekçesini yaz — gerekçe bulamıyorsan bölme ve nedenini raporla.
6. **Kompozisyon çağrı yerlerini güncelle.** `api/composition.py`,
   `api/development_composition.py` ve testler.

## Invariantlar

- **Davranış değişmeyecek.** Bu tamamen bir refactor'dır; hiçbir rota, yanıt şeması veya
  güvenlik davranışı değişmez.
- **Fail-closed varsayılan korunacak:** bağımlılık verilmezse
  `UnavailableActorContextResolver` ile açılma davranışı ve joker CORS reddi aynen kalacak.
- Testlerin fabrikayı kısmi bağımlılıkla çağırabilme yeteneği korunacak — birim testleri
  yalnızca ilgilendikleri alanı kurabilmeli. Bu, gruplama tasarımının ana kısıtıdır.
- 58 rotanın tamamı aynı yol ve metotla kayıtlı kalacak.
- `mypy src/` hata sayısı artmayacak.
- Yeni üçüncü parti bağımlılık yok.

## Kabul Kriterleri

1. `create_dashboard_api` imzası 34 parametreden ~8'e inmiş.
2. Bir alanın servis grubunda eksik servis bırakıldığında `mypy` hata veriyor —
   bu bir testle veya örnekle gösterilmiş.
3. Rota tablosu değişmemiş: 58 rota, aynı yol ve metotlar — otomatik testle doğrulanmış
   (rota listesini karşılaştıran anlık görüntü testi).
4. Fail-closed varsayılan ve joker CORS reddi hâlâ çalışıyor — mevcut testler geçiyor.
5. Birim testleri hâlâ kısmi bağımlılıkla fabrikayı kurabiliyor.
6. `object` tipli parametre kalmamış.
7. `python -m pytest` tamamen yeşil.
8. `mypy src/` hata sayısı öncesi/sonrası raporlanmış, artmamış.

## Teslim Formatı

- **Kod:** Değiştirilen dosyalar ve gruplama tasarımının gerekçesi.
- **İmza karşılaştırması:** Öncesi/sonrası parametre sayısı ve yeni imza.
- **Bölme kararı:** `data_sources` dosyaları için ne yapıldı, gerekçesiyle.
- **Testler:** Rota anlık görüntü testi dahil, eklenen test adları.
- **Test çıktısı:** Ham `pytest` ve `mypy` sonuçları.
- **Varsayımlar:** Yapılan varsayımlar ve açık kalan sorular.

## Çalışma Kuralları

- Mevcut kod stiline uy (Türkçe docstring, `from __future__ import annotations`,
  frozen dataclass).
- Yeni üçüncü parti bağımlılık ekleme.
- Testleri çalıştır ve sonucu olduğu gibi bildir.
- Belirsizlik varsa varsayımını açıkça yaz ve devam et.
- Refactor sırasında davranış değişikliği fark edersen dur ve raporla — sessizce düzeltme.

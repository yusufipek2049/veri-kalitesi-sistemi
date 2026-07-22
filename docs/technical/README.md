# Teknik Mimari ve Sistem Analizi

Bu belge seti, Veri Kalitesi İzleme ve Skorlama Sistemi'nin 22 Temmuz 2026
tarihindeki kod tabanını esas alan teknik incelemesidir. Gereksinim ve mimari
belgeler hedef resmi açıklamak için kullanılmış; uygulanmışlık kararı kaynak kod,
SQLite şemaları ve testlerle verilmiştir.

Hedef skorlama ve ölçüm yeterliliği sözleşmesi için
[kanonik mimari tasarım](../../02-Mimari/Veri-Kalitesi-Skorlama-ve-Olcum-Yeterliligi.md)
ve [sentetik veri ve gizlilik hedef tasarımı](../../02-Mimari/Sentetik-Veri-ve-Gizlilik-Stratejisi.md)
ile [kanıta dayalı karar sistemi hedef tasarımı](../../02-Mimari/Kanita-Dayali-Karar-Sistemi.md)
esas alınır; bu teknik analiz mevcut runtime farklarını ayrıca belirtir. Son hedef
ikinci faz sözleşmesidir ve uygulanmış runtime olarak değerlendirilmez.

## Okuma Sırası

1. [Yönetici Özeti](00-Yonetici-Ozeti.md)
2. [Sistem Mimarisi](01-Sistem-Mimarisi.md)
3. [Domain ve Veri Modeli](02-Domain-ve-Veri-Modeli.md)
4. [API ve Entegrasyonlar](03-API-ve-Entegrasyonlar.md)
5. [Güvenlik ve Uyumluluk](04-Guvenlik-ve-Uyumluluk.md)
6. [Deployment ve Operasyon](05-Deployment-ve-Operasyon.md)
7. [Test, Performans ve Teknik Borç](06-Test-Performans-ve-Teknik-Borc.md)
8. [Riskler ve Yol Haritası](07-Riskler-ve-Yol-Haritasi.md)

## Durum Sözlüğü

| Durum | Anlamı |
| --- | --- |
| Uygulanmış | Davranış kodda ve testte bulunuyor. Üretim onayı anlamına gelmez. |
| Kısmen uygulanmış | Domain veya adaptör sözleşmesi var; çalışan taşıma, ürün adaptörü ya da operasyon bileşeni eksik. |
| Planlanmış ancak uygulanmamış | Gereksinim veya mimari belgede var; çalışan kod karşılığı yok. |
| Doğrulanamadı | Karar ya da davranış kod ve yapılandırmadan kanıtlanamadı. |
| Varsayım | Yalnız analiz bağlamında kullanılan, bağlayıcı olmayan kabul. |

## İnceleme Sınırı

- Satır ve dosya sayıları tarihsel inceleme anına bağlıdır; güncel doğrulama
  baseline'ı 1029 test ve 159 kaynak dosyalık sıfır hatalı mypy sonucudur.
- FastAPI dashboard özeti/logout sınırı ile React/Vite frontend uygulaması vardır;
  kalan alan API'leri ve üretim IdP/session bağlantısı uygulanmamıştır.
- Uygulama repository'leri çoğunlukla SQLite kullanır. 34F yalnız tamamen yapay
  ilişkisel dataset için ayrı PostgreSQL entegrasyonunu doğrular; üretim veri
  tabanı veya genel repository geçişi değildir.
- Gerçek banka verisi, LDAP/IdP ve ServiceNow ağ istemcisi kullanılmamıştır.
- Bu rapor teknik kanıttır; BDDK/KVKK uyumluluğu veya banka onayı sonucu üretmez.

## Birleştirilmiş Envanterler

### Dosya Referansları

| Konu | Dosya | Sınıf/Fonksiyon/Bölüm | Açıklama |
| --- | --- | --- | --- |
| Veri kaynağı orkestrasyonu | `03-Backend/src/veri_kalitesi/data_sources/service.py` | `DataSourceService` | Tanım, test, keşif, profil ve işleme envanteri |
| CSV erişimi | `03-Backend/src/veri_kalitesi/data_sources/connectors.py` | `CSVConnector` | Dosya okuma, metadata ve süreç içi profil |
| PostgreSQL sınırı | `03-Backend/src/veri_kalitesi/data_sources/postgresql.py` | `PostgreSQLConnector`, `PostgreSQLDriver` | Salt-okunur kontrol ve sürücü protokolü |
| Kural yönetimi | `03-Backend/src/veri_kalitesi/rules/service.py` | `RuleService` | Sürüm, test, aktivasyon ve maker-checker |
| Kural şablonları | `03-Backend/src/veri_kalitesi/rules/templates.py` | `build_rule_plan` | Sekiz kural tipinin doğrulanmış planı |
| Çalıştırma | `03-Backend/src/veri_kalitesi/executions/service.py` | `ExecutionService` | Kuyruk, idempotency, retry, timeout ve iptal |
| Zamanlama | `03-Backend/src/veri_kalitesi/executions/scheduling.py` | `SchedulingService` | ONCE/DAILY/WEEKLY/MONTHLY tetikleme |
| Skorlama | `03-Backend/src/veri_kalitesi/scoring/service.py` | `ScoringService` | Kuraldan kurum seviyesine agregasyon |
| Dashboard | `03-Backend/src/veri_kalitesi/dashboard/service.py` | `DashboardQueryService` | Yetki filtreli ağaç, detay ve 30 günlük trend |
| Kimlik | `03-Backend/src/veri_kalitesi/identity/ldap.py` | `LdapAuthenticationService` | LDAP assertion ve grup-rol/scope eşleme sınırı |
| Oturum | `03-Backend/src/veri_kalitesi/identity/sessions.py` | `SessionService` | Opak credential özetiyle oturum yaşam döngüsü |
| Audit | `03-Backend/src/veri_kalitesi/audit/repository.py` | `SQLiteAuditRepository` | Hash-chain audit ve bütünlük doğrulama |
| Bildirim | `03-Backend/src/veri_kalitesi/notifications/service.py` | `NotificationService` | Veri-minimum sistem içi bildirim |
| Sorun yönetimi | `03-Backend/src/veri_kalitesi/issues/service.py` | `IssueService` | Atama, çözüm, doğrulama, kapanış ve recurrence |
| ServiceNow | `03-Backend/src/veri_kalitesi/servicenow/service.py` | `ServiceNowService` | Allowlist projeksiyon, retry, DLQ ve circuit breaker |
| Olay müdahalesi | `03-Backend/src/veri_kalitesi/incident_response/service.py` | `IncidentResponseService` | Güvenlik olayı ve ihlal şüphesi kanıt akışı |
| Raporlama | `03-Backend/src/veri_kalitesi/reporting/service.py` | `ReportPreviewService` | Yetki filtreli maskeli özet önizleme |
| Güvenli SDLC | `03-Backend/src/veri_kalitesi/secure_sdlc/` | `RepositorySecretScanner`, `PythonDependencyInventoryBuilder`, `SastReleaseGate`, `DependencyVulnerabilityReleaseGate`, `PentestFindingTracker`, `TechnicalEvidenceManifestBuilder`, `TechnicalEvidenceManifestGate`, `LocalReleasePreflight` | Yerel tarama/kapılar, teknik kanıt manifesti/drift doğrulaması ve birleşik preflight |

### Özellik Durumu

| Özellik | Durum | Kanıt | Eksik bölüm |
| --- | --- | --- | --- |
| CSV bağlantı, keşif ve profil | Uygulanmış | `CSVConnector`, birim testler | Sandbox dizini ve büyük dosya optimizasyonu |
| PostgreSQL bağlantı sözleşmesi | Kısmen uygulanmış | `PostgreSQLConnector` | Gerçek driver, pool ve entegrasyon testi |
| MSSQL, Oracle, MySQL, Excel, REST | Planlanmış ancak uygulanmamış | `SourceType` enum | Bağlayıcılar |
| Kural şablonu/sürümü/onayı | Uygulanmış | `RuleService`, `rule_*` tabloları | Gerçek kural executor adaptörü |
| Kuyruk ve zamanlama | Kısmen uygulanmış | `ExecutionService`, `SchedulingService` | Broker, worker process, cron ve dağıtık lock |
| Mevcut skorlama ve trend alt kümesi | Uygulanmış | `ScoringService`, `DashboardQueryService` | Kanonik sayaçlar, ham/nihai skor, ölçüm yeterliliği, kullanım kararı, onaylı kurumsal politikalar ve HTTP/UI |
| LDAP/RBAC ve oturum | Kısmen uygulanmış; `OPEN-BNK-020` banka onaylı | LDAP/session servisleri | LDAP client; onaylı BFF, `__Host-session`, CSRF, merkezi iptal ve üretim store/şifreleme uygulaması |
| Bildirim ve issue yaşam döngüsü | Uygulanmış domain çekirdeği | notification/issue servisleri | UI/HTTP, gerçek resolver ve operasyon politikası |
| ServiceNow | Kısmen uygulanmış | `ServiceNowAdapter` protokolü ve fake testler | Gerçek HTTP istemcisi, credential ve durum senkronu |
| Audit bütünlüğü | Kısmen uygulanmış | SQLite hash-chain ve outbox | WORM/imza, merkezi platform ve publisher worker |
| Rapor önizleme | Kısmen uygulanmış | `ReportPreviewService` | PDF/XLSX/CSV üretimi ve kontrollü indirme |
| Güvenli SDLC | Kısmen uygulanmış | Secret scanner, direct SBOM, SAST/doğrudan bağımlılık zafiyet kapıları, pentest bulgu takibi, teknik kanıt manifesti/drift kapısı ve birleşik preflight | Gerçek scanner/transitive SCA/DAST/pentest, CI zorlaması, imzalı kanıt deposu ve istisna akışı |
| REST API | Kısmen uygulanmış | FastAPI dashboard özeti ve BFF logout; Problem Details | Kalan alan endpoint'leri, üretim resolver ve kapsamlı OpenAPI |
| Frontend | Kısmen uygulanmış | React/Vite dashboard, tema, Storybook ve Playwright | Operasyonel KPI API'si ve alan ekranları |
| Kanıta dayalı karar desteği | Planlanmış ancak uygulanmamış | `ADR-019`, `FR-097–FR-111`, `OPEN-026–OPEN-036` teknik yön kararları, kanonik hedef mimari | Runtime, migration, kurumsal politika ve entegrasyonlar |
| Deployment/CI/CD/DR | Planlanmış ancak uygulanmamış | Operasyon belgeleri | Çalıştırılabilir altyapı ve kanıt |

### Kritik Riskler

| Risk | Önem | Kanıt | Öneri |
| --- | --- | --- | --- |
| HTTP composition root'u yalnız dashboard/logout ile sınırlı | Kritik | Diğer alan endpoint'leri bulunmuyor | Güvenli API dikeylerini küçük artımlarla genişlet |
| Üretim adaptörleri yok | Kritik | Yapay PostgreSQL dataset haricinde IdP, genel PostgreSQL repository ve ServiceNow ürün adaptörü yok | Kurumsal kararlar sonrası contract+integration test |
| SQLite süreç içi prototip ölçeği | Kritik | Her repository kendi connection/lock yapısını açıyor | Üretim DB/broker seçimi, migration ve HA tasarımı |
| Operasyon ve DR kanıtı yok | Kritik | Docker, CI/CD, health check, backup/restore yok | Dağıtım standardı, RTO/RPO ve restore tatbikatı |
| Hassas dosya erişim sınırı eksik | Yüksek | `CSVConnector` doğrudan yapılandırılan yolu açıyor | Allowlist kök, canonical path kontrolü ve servis hesabı izni |
| Audit yalnız uygulama içi hash-chain | Yüksek | `SQLiteAuditRepository` | WORM/imza veya kurumsal merkezi log platformu |
| Type-check aracının CI kapısı olmaması | Orta | Yerel baseline 159 dosyada sıfır hata; CI zorlaması yok | Sıfır baseline'ı CI kapısına al |

### Teknoloji Envanteri

| Teknoloji | Sürüm | Kullanım amacı | Bulunduğu dosya |
| --- | --- | --- | --- |
| Python | `>=3.10`; inceleme ortamı `3.10.12` | Tüm backend ve test kodu | `pyproject.toml` |
| SQLite | Python stdlib ile gelen, sabitlenmemiş | Yerel kalıcılık, kuyruk, oturum ve audit | `*/repository.py`, `identity/*.py` |
| `packaging` | `26.0` | SBOM bağımlılık ayrıştırma | `pyproject.toml`, `secure_sdlc/sbom.py` |
| `tomli` | `2.4.1` | `pyproject.toml` okuma | `pyproject.toml`, `secure_sdlc/sbom.py` |
| pytest | Manifestte sabitlenmemiş; ortam `9.0.3` | Birim test | `pyproject.toml`, `06-Testler/01-Birim/` |
| Ruff | Manifestte sabitlenmemiş; ortam `0.15.13` | Lint/format | `pyproject.toml` |
| mypy | Manifestte sabitlenmemiş; ortam `2.1.0` | Statik tip kontrolü | Komut/kanıt belgeleri; config yok |
| Mermaid | Runtime bağımlılığı değil | Dokümantasyon diyagramları | `02-Mimari/`, bu rapor |
| FastAPI | `0.135.3` | Dashboard özeti ve BFF logout HTTP sınırı | `pyproject.toml`, `api/app.py` |
| SQLAlchemy | `2.0.51` | Onaylı üretim veri erişimi bağımlılığı; genel repository geçişi tamamlanmadı | `pyproject.toml` |
| Alembic | `1.18.4` | Sürümlü migration altyapısı | `pyproject.toml`, `alembic/` |
| React/Vite | Manifestte sabitlenmiş | Dashboard, tema, Storybook ve görsel test | `04-Frontend/app/package.json` |

### API Envanteri

| Metot | Endpoint | Yetki | Servis | Açıklama |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/dashboard/summary` | Güvenilir session/actor resolver ve source scope | `DashboardQueryService` | Veri-minimum özet ve trend |
| POST | `/api/v1/session/logout` | BFF session, CSRF, Origin/Referer/Fetch Metadata | `BffSessionBoundary` | Oturumu merkezi olarak iptal eder |

Domain servis yüzeyleri [API ve Entegrasyonlar](03-API-ve-Entegrasyonlar.md)
belgesinde ayrıca listelenmiştir.

### Veri Tabanı Envanteri

| Tablo grubu | Tablolar | Amaç | Ana ilişkiler | Büyüme riski |
| --- | --- | --- | --- | --- |
| Kaynak/metadata | `data_sources`, `datasets`, `data_fields` | Kaynak kataloğu | source -> dataset -> field | Orta |
| Keşif/profil | `connection_test_results`, `metadata_discovery_results`, `data_profiles` | Çalışma geçmişi | source/dataset FK | Yüksek, retention yok |
| Veri koruma | `data_processing_inventory_versions` | Alan bazlı sürümlü işleme envanteri | field FK | Orta |
| Legacy audit | `audit_records` | İlk iterasyon audit'i | Mantıksal bağ | Yüksek, migration sonrası temizleme kararı yok |
| Kurallar | `quality_rules`, `rule_versions`, `rule_test_results`, `rule_approval_requests` | Kural ve onay geçmişi | rule -> version -> test/approval | Yüksek |
| Çalıştırma | `rule_executions`, `execution_attempts`, `rule_execution_results`, `schedules` | Kuyruk, deneme, sonuç ve plan | execution -> attempt/result | Çok yüksek |
| Skorlama | `quality_scores`, `scoring_configurations`, `scoring_configuration_approvals` | Skor ve sürümlü politika | execution/rule mantıksal; config approval FK | Çok yüksek |
| Kimlik | `identity_sessions`, `authentication_throttle_states` | Oturum ve giriş sınırı | Aktör kodları mantıksal | Yüksek |
| Merkezi audit | `audit_events`, `audit_outbox` | Redakte hash-chain ve transactional outbox | event kimliği | Çok yüksek |
| Bildirim | `notifications` | Kullanıcı bildirimleri | recipient ve event mantıksal | Yüksek |
| Sorun | `data_quality_issues`, `issue_history`, `issue_resolutions`, `issue_verifications`, `issue_relationships` | Sorun state machine ve tarihçe | issue FK'leri | Çok yüksek |
| ServiceNow | `servicenow_ticket_links`, `servicenow_ticket_history`, `servicenow_retry_jobs`, `servicenow_circuit_breaker` | Ticket ve dayanıklılık durumu | link -> history/retry | Yüksek |
| Olay müdahalesi | `security_incidents`, `personal_data_breach_suspicions`, `breach_notification_decisions`, `incident_timeline` | Güvenlik/ihlal kanıt akışı | incident -> breach -> decision/timeline | Yüksek |

Ayrıntılı anahtar, indeks ve yaşam döngüsü değerlendirmesi
[Domain ve Veri Modeli](02-Domain-ve-Veri-Modeli.md) içindedir.

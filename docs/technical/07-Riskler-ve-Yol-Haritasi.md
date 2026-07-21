# Riskler ve Yol Haritası

## Risk Değerlendirme Yöntemi

Olasılık ve etki `Düşük/Orta/Yüksek` olarak kod kanıtına göre değerlendirilmiştir.
Öncelik `P0` üretime engel, `P1` güvenlik/operasyon zorunluluğu, `P2` ölçek/bakım,
`P3` kullanıcı deneyimi/ileri özellik anlamına gelir. Bu tablo banka risk kabulü
değildir.

## Risk Kaydı

| Risk | Olasılık | Etki | Öncelik | Kanıt | Aksiyon |
| --- | --- | --- | --- | --- | --- |
| Runtime/API olmadan ürünün çalıştırılamaması | Yüksek | Yüksek | P0 | App/route/entrypoint yok | Güvenli composition root + API |
| Gerçek LDAP/DB/ServiceNow entegrasyonunun başarısız olması | Yüksek | Yüksek | P0 | Yalnız Protocol/fake | Ürün seçimi ve integration ortamı |
| SQLite queue/DB'nin eşzamanlı yükte bozulması | Yüksek | Yüksek | P0 | Process `RLock`, fetchall claim | Kurumsal DB/broker/lease |
| Yetki bağlamının legacy actor ID ile aşılması | Orta | Yüksek | P0 | Bazı servislerde serbest actor | ActorContext zorunlu dış sınır |
| Üretim secret/kimlik güveninin doğrulanamaması | Yüksek | Yüksek | P0 | Vault/LDAP adapter yok | Workload identity, vault, TLS |
| Audit kaybı veya yeniden yazılması | Orta | Yüksek | P1 | SQLite chain/outbox, WORM yok | Immutable sink + publisher/alarm |
| Veri saklama/imha yükümlülüklerinin karşılanmaması | Yüksek | Yüksek | P1 | Retention job/policy yok | Banka onaylı lifecycle/legal hold |
| CSV üzerinden ilgisiz dosya okuma | Orta | Yüksek | P1 | Serbest `file_path` | Read-only mount + path sandbox |
| Kaynak DB'de yazma etkisi | Düşük-Orta | Yüksek | P1 | Statik SQL kontrol; gerçek grant yok | DB-level read-only ve test kanıtı |
| Hassas export sızıntısı | Orta | Yüksek | P1 | Export yok ama policy açık | DLP/maker-checker/watermark/expiry |
| DR sonrası veri/audit kaybı | Yüksek | Yüksek | P1 | Backup/restore/RTO/RPO yok | PITR ve restore tatbikatı |
| 20M satır profil hedefinin kaçırılması | Yüksek | Orta-Yüksek | P2 | CSV O(n) memory, benchmark yok | Source aggregate + load test |
| Queue/audit tablolarının sınırsız büyümesi | Yüksek | Orta-Yüksek | P2 | Retention/partition yok | Partition/archive/capacity alarm |
| Yetki politika drift'i | Orta | Yüksek | P1 | String rol kodları dağınık | Merkezi permission catalog/policy test |
| Büyük servis kaynaklı regresyon | Orta | Orta | P2 | Mypy baseline sıfır; 800-1000 satır servisler sürüyor | Sıfır type baseline + odaklı ayrıştırma |
| Bağımlılık zafiyetinin görünmemesi | Orta | Yüksek | P1 | SCA/vuln DB/lock yok | Transitive lock/SBOM/SCA gate |
| Operasyon ekibinin arızayı görememesi | Yüksek | Yüksek | P0 | Metric/log/health/alarm yok | Observability minimum baseline |
| Kullanıcı akışının doğrulanamaması | Yüksek | Orta-Yüksek | P2 | UI/API/E2E yok | Dikey API+UI artımları ve E2E |
| Banka kontrol kararlarının açık kalması | Yüksek | Yüksek | P0 | `OPEN-BNK-*` listesi | Karar sahibi ve kanıt kapısı |
| Kabul edilen skorlama/ölçüm yeterliliği modeliyle runtime'ın ayrışması | Yüksek | Yüksek | P1 | Kanonik sayaçlar, ham/nihai skor, yeterlilik/geçerlilik kapısı, kullanım kararı, kapsam/güven ve override kodda yok | İterasyon 33A'dan başlayan küçük, geriye uyumlu skorlama dilimleri |
| Dataset kritikliğinin kalite skoruna karışması | Yüksek | Orta-Yüksek | P1 | Mevcut `SOURCE` formülü; `ADR-015` hedefinde `Superseded` | Kritiklik/risk göstergelerini kalite agregasyonundan ayır |
| Yüksek fakat yetersiz/eski ölçümün operasyonel kararda kullanılması | Orta-Yüksek | Yüksek | P1 | Runtime'da ayrı yeterlilik ve `ValidUntil` kapısı yok; `OPEN-023` değerleri açık | Yeterlilik kapısını ve fail-closed kullanım kararını API/UI öncesi uygula |
| Sentetik çıktının anonim kabul edilmesi veya üretim kaydını ezberlemesi | Orta | Yüksek | P1 | `ADR-016` hedef tasarım; gizlilik değerlendiricisi runtime'da yok | `OPEN-024/025` kararı, ayrılmış üretim erişimi ve fail-closed gizlilik kapısı |
| Skor motorunun kendi çıktısıyla sentetik ground truth üretmesi | Orta | Yüksek | P1 | Bağımsız comparator/oracle runtime'da yok | Bağımsız ground truth, sürümlü seed/senaryo ve false-positive/negative kabul testleri |

## P0 - Üretime Çıkışı Engelleyen İşler

### P0.1 Güvenli Uygulama Composition Root ve Okuma API'si

**Neden:** Domain servisleri çalışır bir ürün yüzeyine bağlı değildir.

**Etkilenen:** `identity`, `dashboard`, `audit`, `reporting`, yeni API paketi.

**Bağımlılıklar:** `OPEN-BNK-020` session taşıma/CSRF; LDAP policy sürümü.

**Kabul kriterleri:**

- Sürümlü API ve OpenAPI üretilir.
- Session credential yalnız güvenilir middleware'de ActorContext'e dönüşür.
- Enterprise/source/dataset IDOR negatif testleri geçer.
- Error zarfı correlation ID taşır, secret/PII taşımaz.
- Health/liveness ve bağımlılık kontrollü readiness vardır.

### P0.2 Üretim Veri ve İş Altyapısı Kararı

**Neden:** SQLite ve süreç içi lock çoklu instance/HA için uygun değildir.

**Etkilenen:** Tüm repository'ler, execution, scheduling, outbox, ServiceNow retry.

**Bağımlılıklar:** `OPEN-BNK-012`, kapasite ve kurum platform standardı.

**Kabul kriterleri:**

- Üretim DB ve broker onaylıdır; şema migrationları sürümlü ve rollback testlidir.
- Atomik claim/lease/heartbeat/crash recovery çoklu worker testinden geçer.
- FK, unique ve transaction semantiği hedef DB'de integration testlidir.
- Queue depth/age/DLQ/outbox alarmı vardır.

### P0.3 Gerçek Kimlik ve Secret Adaptörleri

**Neden:** Banka kimliği ve credential güveni fake adapterla kanıtlanamaz.

**Etkilenen:** `identity`, `data_sources`, ServiceNow, deployment.

**Bağımlılıklar:** `OPEN-BNK-002/003/018/019/020`.

**Kabul kriterleri:**

- LDAP TLS ve grup-rol/scope contract testleri geçer.
- Vault/workload identity dışında secret kaynağı production profilde reddedilir.
- MFA/PAM/break-glass kararı privileged akışlara yansır.
- Session cookie/token, CSRF, rotasyon, revoke ve timeout güvenlik testleri geçer.

### P0.4 İlk Gerçek Kaynak ve Kural Executor

**Neden:** Kural planları gerçek veri kaynağında çalıştırılmıyor.

**Etkilenen:** PostgreSQL connector/driver, rules, executions, scoring.

**Bağımlılıklar:** Anonim/sentetik integration DB, read-only role, query budget.

**Kabul kriterleri:**

- PostgreSQL metadata/profile ve en az temel kural tipleri gerçek adapterla çalışır.
- DB kullanıcı grant'i ve transaction read-only testle doğrulanır.
- Statement timeout/cancel, query cost, partition/sample ve teknik hata ayrımı geçer.
- Ham kayıt sonuç/audit/log/bildirime girmez.

### P0.5 Operasyon ve Banka Karar Kapısı

**Neden:** Üretim sahipliği, gözlemlenebilirlik, DR ve uyum kararları yoktur.

**Etkilenen:** Deployment, operasyon, uyum kanıtları.

**Bağımlılıklar:** Açık `OPEN-BNK-*` kararları.

**Kabul kriterleri:**

- CI/CD, immutable artifact, SAST/SCA/secret gate ve SBOM vardır.
- Log/metric/trace/SIEM, on-call ve runbook doğrulanır.
- Backup/restore ve banka onaylı RTO/RPO tatbikatı geçer.
- Teknik kontrol kanıtları ilgili banka karar sahibine sunulur; Codex kendi başına
  `ApprovedByBank` sonucu vermez.

## P1 - Güvenlik, Bütünlük ve Operasyon

| İş | Neden | Bağımlılık | Kabul kriteri |
| --- | --- | --- | --- |
| Immutable audit ve durable publisher | SQLite chain tek başına yeterli değil | Audit platform kararı | İmzalı/WORM sink, replay, alarm ve integrity tatbikatı |
| Retention/imha/legal hold | Sınırsız geçmiş var | Hukuk/uyum kayıt matrisi | Tür bazlı policy, dry-run, maker-checker, imha kanıtı |
| Export kontrolü | Toplu veri sızıntısı riski | DLP/watermark kararı | Gerekçe, onay, scope, expiry ve indirme auditi |
| CSV güvenli dosya sınırı | Path kapsamı serbest | Mount/servis hesabı modeli | Canonical allowlist, symlink ve negatif test |
| ServiceNow gerçek adaptörü | Issue dış sisteme çıkmıyor | `OPEN-BNK-009` | TLS, allowlist, timeout, retry, reconciliation ve alarm |
| Incident/SIEM entegrasyonu | SOC akışı yok | `OPEN-BNK-010` | Olay kodu, SIEM ingest, timeline ve insan karar kanıtı |
| Güvenli SDLC tamamlama | Secret/direct SBOM, yerel SAST/bağımlılık zafiyet kapıları ve pentest bulgu takibi | Scanner ürünleri | Gerçek SAST, transitive SCA, DAST, exception workflow, pentest |

28A–28E yerel güvenli SDLC sözleşmeleri ile 29A manifest, 29B drift kapısı ve 29C
birleşik yerel preflight doğrulanmıştır. Gerçek scanner, CI/CD, pentest ve banka
kabulü dış kararlara bağlıdır; hazır ve engellenmemiş yeni geçiş artımı yoktur.

## P2 - Ölçeklenebilirlik ve Bakım

| İş | Kabul kriteri |
| --- | --- |
| 20M profil benchmark ve bounded algoritmalar | CPU/RAM/query bütçesi ölçülür; raw veri taşınmaz |
| Queue/due indeks ve dağıtık scheduler | Hacim testi, duplicate-free trigger, failover |
| Sonuç/audit partition ve archive | Retention/legal hold ile uyumlu query SLA |
| Scoring batch katalog erişimi | N+1 kaldırılır; formül sonucu değişmez |
| Dimension/enterprise ağırlık politikası | Banka onaylı sürümlü formül ve geriye dönük açıklanabilirlik |
| Full mypy ve coverage CI kapısı | Yerel 0 type error korunur; onaylı branch threshold uygulanır |
| Sentetik veri çekirdeği | SYN-001–SYN-005 ile politika/run, Golden üretici, kusur/ground truth, zaman/hacim ve gizlilik/olay izolasyonu küçük dikeylere bölünür |
| Büyük servislerin ayrıştırılması | Davranış değiştirmeyen karakterizasyon testleriyle küçük use-case sınıfları |
| Legacy kaldırma | `_legacy` ve `audit_records` geçiş/rollback kanıtı sonrası silinir |

## P3 - Kullanıcı Deneyimi ve İleri Özellikler

| İş | Kabul kriteri |
| --- | --- |
| Yönetim ve dashboard frontend'i | Belgelenen token/screen sözleşmesine uygun, responsive, scope güvenli, erişilebilir, Storybook ve Playwright ile doğrulanmış |
| Genel cron | Onaylı parser/gramer, DST ve invalid expression testleri |
| E-posta/ek kanal bildirimleri | Veri-minimum template, opt-out/suppression/retry/DLQ |
| SLA ve eskalasyon | Policy version, business calendar ve auditli eskalasyon |
| False-positive/istisna yönetimi | Süreli, maker-checker, scope ve expiry kontrolü |
| PDF/XLSX/CSV rapor | DLP/watermark/expiry ve büyük export asenkronluğu |
| Ek connector'lar | MSSQL/Oracle/MySQL/Excel/REST için read-only contract suite |

## Önerilen Teslim Sırası

1. Banka kararları sonrası 29D kurumsal CI/CD ve imzalı kanıt yayını.
2. Güvenli read-only API composition root.
3. Üretim DB/broker migration omurgası.
4. LDAP/vault ve PostgreSQL gerçek adaptörleri.
5. Uçtan uca kaynak -> execution -> score -> dashboard dikeyi.
6. Notification/issue/ServiceNow runtime entegrasyonu.
7. Observability, immutable audit, backup/restore ve DR.
8. Frontend ve kullanıcı E2E akışları.
9. Scale/retention/export ve ek connector'lar.

Her madde küçük dikey iterasyonlara bölünmeli; tek iterasyonda yeni runtime, tüm
adapterler ve frontend birlikte ele alınmamalıdır.

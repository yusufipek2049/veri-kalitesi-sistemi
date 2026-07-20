# Güvenlik ve Uyumluluk

## Kapsam ve Sonuç Sınırı

Bu bölüm kod üzerinden teknik kontrol değerlendirmesidir. BDDK/KVKK uyumluluğu,
hukuki görüş veya banka onayı anlamına gelmez. Banka bilgi güvenliği, hukuk, uyum,
iç kontrol, IAM ve mimari kararları açık kalır.

## Uygulanmış Güvenlik Tabanı

- `ActorContext` güvenilir issuer, geçerlilik zamanı, policy version, actor type,
  rol ve veri scope'u taşır; dashboard/audit/reporting/issue/ServiceNow/incident
  servislerinde deny-by-default kontroller vardır.
- LDAP grup eşlemesi rol ve source/dataset scope üretir; boş/uyumsuz eşleme reddedilir.
- Login throttle ve kalıcı, revoke edilebilir session modeli vardır; ham session
  credential yerine digest saklanır.
- Secret alanları connection config ve execution scope'a girmeden reddedilir;
  `secret://` referansı kullanılır.
- PostgreSQL için TLS doğrulama modu, timeout ve salt-okunur probe sözleşmesi vardır.
- Kural ve skor konfigürasyonu için maker-checker vardır; maker checker olamaz.
- Veri sınıflandırması fail-closed `UNCLASSIFIED` davranır; profil çıktısı ham değer
  içermeyen allowlist agregatlara indirgenir.
- Audit redactor, allowlist özet, değer digest'i, session digest'i, correlation ID ve
  hash-chain üretir. Kritik audit için `FAIL_CLOSED` veya açık `DURABLE_BUFFER`
  politikası vardır.
- Notification, issue, ServiceNow ve incident modelleri serbest ham kayıt yerine
  UUID/kod/evidence reference yaklaşımı kullanır.
- ServiceNow payload'ı allowlist alanlarla sınırlı ve idempotenttir.
- Yerel secret scanner bulgu değerini çıktıya yazmaz; yalnız dosya, konum ve rule code
  üretir. SBOM doğrudan Python bağımlılıklarını CycloneDX 1.5 formatında çıkarır.
- Yerel SAST kapısı yalnız scanner kimliği/sürümü, rule code, önem, depo göreli
  konum ve satır/sütun kabul eder; teknik tarama hatasını kalite bulgusundan ayırır,
  kritik bulguda sürüm kanıtı üretmez.
- Yerel bağımlılık zafiyet kapısı bulguyu yalnız doğrudan SBOM envanterindeki tam
  paket/sürüm çiftine bağlar; tamamlanmamış taramayı teknik hata sayar ve kritik
  bulguda sürüm kanıtı üretmez.

Bu incelemede tarayıcı `28A-v1` politikasıyla 326 metin dosyasını taramış ve sıfır
bulgu üretmiştir. Bu sonuç yalnız desteklenen pattern'ler ve mevcut çalışma ağacı
içindir; geçmiş commit, yüksek entropi ve kurumsal scanner kapsamı değildir.

## Güvenlik Bulguları

| Bulgu | Önem | Kanıt | Muhtemel etki | Önerilen çözüm |
| --- | --- | --- | --- | --- |
| HTTP güvenlik sınırı yok | Kritik | Route/app/composition root yok | Kimlik kontrolleri gerçek isteğe bağlanamaz | Trusted session middleware ve kapalı varsayılan API |
| Gerçek LDAP/secret manager yok | Kritik | `LdapIdentityAdapter`, `SecretResolver` yalnız port | Üretim kimliği ve credential yönetimi doğrulanamaz | Kurumsal adaptör, TLS, rotasyon ve contract test |
| CSV yolu sandbox edilmemiş | Yüksek | `CSVConnector` doğrudan `Path(file_path).open()` | Yetkili kullanıcı servis hesabının okuyabildiği ilgisiz dosyaya erişebilir | Canonical path + allowlist root + symlink politikası |
| Salt-okunur SQL kontrolü sözdizimsel | Yüksek | `is_read_only_sql()` regex/keyword kontrolü | Yan etkili fonksiyonlar veya parser boşlukları | DB-level read-only role/transaction, AST/parser, statement allowlist |
| Audit değiştirilemez depo değil | Yüksek | SQLite hash-chain | DB dosyasına yetkili saldırgan geçmişi yeniden yazıp zinciri yeniden hesaplayabilir | WORM/imza/HSM veya merkezi immutable log |
| SQLite at-rest şifreleme yok | Yüksek | stdlib `sqlite3`, encryption config yok | Session/audit/issue metadata dosyadan okunabilir | Kurumsal DB/TDE, disk encryption, key management |
| Çoklu instance güvenliği yok | Yüksek | Süreç içi `RLock`, SQLite breaker/queue | Duplicate claim, yarış ve tutarsız kota | Transactional DB locking/lease ve dağıtık state |
| Retention/imha/legal hold yok | Yüksek | Tarihçe tablolarında delete/archive job yok | Gereksiz veri tutma ve hukuki yaşam döngüsü riski | Kayıt türü bazlı onaylı lifecycle motoru |
| HTTP kontrolleri yok | Yüksek | Cookie/JWT/CORS/CSRF/security header kodu yok | API eklendiğinde session ve browser saldırıları | Threat model sonrası cookie/CSRF/CORS politikası |
| Güvenlik tarama entegrasyonu eksik | Orta | Direct SBOM ile yerel SAST/bağımlılık bulgu kapıları var; gerçek scanner/SCA/DAST yok | Bilinen zafiyet ve kod kusuru otomatik bulunamaz | Lock, transitive SBOM, kurumsal SCA/SAST/DAST CI kapısı |
| Legacy serbest aktör kullanımı | Orta | Bazı eski servislerde `actor_id` parametreleri | Caller sahte aktör verebilir | Tüm mutasyonları trusted `ActorContext` sınırına taşı |
| Genel export/DLP kontrolü yok | Yüksek | Yalnız rapor önizleme var | Gelecek dosya export'unda toplu veri sızıntısı | Gerekçe, maker-checker, watermark, DLP, expiry |

### SQL Injection

Uygulama SQLite sorgularının büyük bölümü `?` parametreleri kullanır. Dinamik DDL,
yalnız kod içi sabit kolon adı/type map'lerinden üretilir. Kullanıcı girdisinin SQLite
SQL metnine doğrudan eklendiği doğrulanmamıştır. Özel SQL kullanıcının salt-okunur
ifadesini kaynak adapterine taşımak üzere saklar; gerçek executor yoktur. Üretimde
yalnız sözdizimsel kontrol yeterli değildir.

### IDOR ve Yetki

Trusted context kullanan dashboard, audit, report ve issue servisleri source/dataset
scope kontrolü yapar. Buna rağmen HTTP route olmadığı için URL/body kimliklerinin bu
kontrollerden zorunlu geçeceği kanıtlanamaz. Bazı eski data source/execution çağrıları
serbest `actor_id` taşır; geçiş tamamlanmadan bunlar dış API'ye açılmamalıdır.

### SSRF ve Ağ Çıkışı

REST kaynak connector'ı ve gerçek ServiceNow HTTP client yoktur; bugün SSRF yapan
çalışan ağ kodu saptanmamıştır. Gelecek host/URL tabanlı connector'lar için destination
allowlist, DNS rebinding koruması, proxy/egress policy ve private metadata endpoint
engeli gerekir.

### Hassas Veri Sızıntısı

Profil metrikleri ham değer içermez; audit redactor ve ServiceNow allowlist güçlü
korumalardır. Ancak CSV profiling ham değerleri süreç belleğinde set/list olarak
tutar. Crash dump, debugger ve process erişimi de güven sınırına dahil edilmelidir.
Log framework'ü olmadığından exception traceback'lerinin production log'a nasıl
gideceği doğrulanamamıştır.

## Audit ve Gözlemlenebilirlik

`AuditEventInput -> AuditRedactor -> PreparedAuditEvent -> SQLiteAuditRepository`
akışı old/new value allowlist, digest ve hash-chain sağlar. `verify_integrity()` ilk
bozuk olayı raporlar. Audit sorgusu `AUDIT_VIEWER`, en fazla 31 günlük senkron pencere,
100 sayfa boyutu ve snapshot cursor ile sınırlıdır; görüntülemenin kendisi de auditlenir.

Bu yapı teknik olarak bütünlük kontrol edilebilir, fakat non-repudiation sağlamaz:
imza anahtarı, WORM, external timestamp veya bağımsız doğrulama yoktur. Transactional
outbox domain DB transaction'ına bağlanabilir, ancak publisher worker, retry/backoff,
kapasite ve alarm yoktur.

Uygulama log framework'ü, log seviyeleri, structured log sink, trace ID, OpenTelemetry,
metric, health/readiness/liveness ve alarm entegrasyonu yoktur. Correlation ID domain
boyunca yaygın olsa da dağıtık trace değildir.

## Bankacılık ve KVKK Teknik Kontrol Haritası

| Kontrol alanı | Durum | Teknik kanıt / açık bölüm |
| --- | --- | --- |
| Kurum içi veri merkezi ve veri yerleşimi | Doğrulanamadı | Deployment yok; hedef belgede on-prem |
| En az yetki / veri scope | Kısmen uygulanmış | ActorContext scope var; gerçek IAM matrisi yok |
| LDAP kimlik doğrulama | Kısmen uygulanmış | Servis/protokol var; gerçek LDAP client yok |
| Ayrıcalıklı erişim | Kısmen uygulanmış | `privileged` bağlamı var; MFA/PAM/break-glass yok |
| Görevler ayrılığı | Kısmen uygulanmış | Kritik rule/scoring maker-checker; tüm kritik işlemler kapsanmıyor |
| Audit izi | Kısmen uygulanmış | Redaksiyon/hash-chain/outbox; immutable merkezi depo yok |
| Veri minimizasyonu | Uygulanmış teknik taban | Profil, notification, ServiceNow ve incident allowlist yaklaşımı |
| Sınıflandırma/maskeleme | Kısmen uygulanmış | Kod sözlüğü ve deny-by-default var; banka eşlemesi/onayı yok |
| Secret yönetimi | Kısmen uygulanmış | Referans portu/scanner var; kurumsal vault adaptörü yok |
| Kaynakta salt okunur erişim | Kısmen uygulanmış | PostgreSQL sözleşmesi var; gerçek DB grant kanıtı yok |
| Saklama/imha/legal hold | Planlanmış ancak uygulanmamış | Policy/job/kanıt yok |
| Dışa aktarma kontrolü | Kısmen uygulanmış | Maskeli preview; dosya export/DLP yok |
| İhlal müdahale kanıtı | Kısmen uygulanmış | Incident, breach, 72 saat hedefi, insan kararı; SIEM/dış bildirim yok |
| Yedekleme ve DR | Planlanmış ancak uygulanmamış | RTO/RPO, backup/restore ve tatbikat yok |
| Değişiklik yönetimi | Kısmen uygulanmış | Sürümlü rule/config ve kanıt; CI/release gate yok |
| Güvenlik testi | Kısmen uygulanmış | Unit negatif test, secret scan, direct SBOM ve yerel SAST/bağımlılık zafiyet kapıları; gerçek scanner/SCA/DAST/pentest yok |

## Olay Müdahalesi

`IncidentResponseService` güvenlik olayı, kişisel veri ihlali şüphesi, 72 saatlik
değerlendirme hedefi, veri işleyen bildirim kanıt referansı ve insan bildirim kararı
kaydeder. Kararı farklı aktör vermelidir. `external_notification_dispatched` DB
constraint'i daima `0` tutar; sistem otomatik resmi bildirim göndermez. Timeline
görüntüleme yetki ve audit altındadır.

**Kısmen uygulanmış:** SIEM/SOC ingest, alarm, vaka yönetimi, kanıt içeriği deposu,
dış bildirim kanalı, saklama ve tatbikat otomasyonu yoktur.

## Öncelikli Güvenlik Aksiyonları

1. HTTP trust boundary, session/cookie/CSRF ve tüm servislerde ActorContext zorunluluğu.
2. Kurumsal LDAP, vault, PostgreSQL ve ServiceNow adapter threat model/contract testleri.
3. Üretim DB şifreleme, immutable audit hedefi ve merkezi log/metric/SIEM.
4. CSV dosya sandbox'ı ve DB düzeyi salt-okunur yetkinin dağıtım kanıtı.
5. SAST/SCA/DAST, transitive lock/SBOM ve güvenlik testi release gate'i.
6. Banka sahipli retention, export, MFA/PAM, RTO/RPO ve incident kararlarının kapatılması.

# ENTERPRISE-LAB-01 / ENTERPRISE-LAB-02 / ENTERPRISE-LAB-03

Bu dizin yalnız sentetik veri ve production olmayan yerel geliştirme için kurumsal
entegrasyon laboratuvarıdır. Keycloak, yerel secret çözümleyici, PostgreSQL
primary-standby, RabbitMQ, fake ServiceNow, SIEM collector ve create-only kanıt
deposu temel servislerini tek ayrılmış Docker bridge ağı içinde çalıştırır.

## Başlatma

```bash
./infra/enterprise-lab/scripts/bootstrap-secrets.sh
docker compose -f infra/enterprise-lab/compose.yaml up -d --build --wait
docker compose -f infra/enterprise-lab/compose.yaml ps
```

Çalışma zamanı secret dosyaları `runtime-secrets/` altında `0600` izinle yerelde
üretilir, Git tarafından yok sayılır ve değerleri komut çıktısına yazılmaz.
Compose yalnız loopback portları yayımlar. `environment-gate` başarıyla
tamamlanmadan diğer servisler başlamaz.

Sentetik Keycloak realm'i `synthetic-lab-viewer` kullanıcısını, `lab-viewers`
grubunu ve yalnız sentetik doğrulamada kullanılan `mfa_evidence=lab-mfa`
claim'ini içerir. Kullanıcı parolası realm dosyasına yazılmaz;
`keycloak_lab_user_password` runtime secret'ından import sırasında çözülür.

Kapatmak için:

```bash
docker compose -f infra/enterprise-lab/compose.yaml down
```

Sentetik verileri ve yerel lab kanıtlarını da silmek istenirse açıkça
`down --volumes` kullanılır; bu işlem geri alınamaz.

## Fail-closed sınırı

`config/environment.json` sürümlü ve salt okunur bileşime sabitlenmiştir. Kapı:

- `PRODUCTION` ortamını ve sentetik olmayan veri kökenini,
- production secret kapsamını,
- allowlist dışı, kullanıcı bilgisi taşıyan veya yanlış servis rolüne atanmış
  endpointleri,
- `PrototypeVerified` dışındaki sınıflandırmayı

reddeder. Kanıt çıktısı secret referansını/değerini veya endpointleri içermez.

## Prototip sınırları

- Fake ServiceNow yalnız veri-minimum allowlist ve idempotency davranışını taklit
  eder; gerçek ServiceNow değildir.
- SIEM collector yalnız allowlist olay zarfını bellekte kabul eder; SOC/SIEM
  ürünü değildir.
- Kanıt servisi aynı digest'e ikinci yazımı ve tüm `DELETE` isteklerini reddeder,
  fakat altyapı yöneticisine karşı WORM/objekt kilidi kanıtı sağlamaz.
- PostgreSQL standby streaming replication prototipidir; otomatik failover,
  quorum, yedekleme veya DR kanıtı değildir.
- Yerel secret çözümleyici Docker secret dosyalarını yalnız internal ağda ve
  bearer doğrulamasıyla sunar; kurumsal PAM/HSM/workload identity değildir.

Bu laboratuvar yalnız `PrototypeVerified` olarak sınıflandırılabilir.
`TechnicallyVerified`, `ApprovedByBank`, mevzuat uyumu veya production-ready
iddiası üretmez.

## Uygulama adaptör bağlantıları

`ENTERPRISE-LAB-02`, bu Compose servislerini uygulamanın mevcut güven
sınırlarına bağlar:

- sentetik Keycloak `userinfo` doğrulamasından sürümlü grup eşlemesiyle
  değişmez `ActorContext`,
- yalnız `secret://local/...` veya `secret://acceptance/...` referanslarını
  çözen yerel secret manager adaptörü,
- teknik alan allowlist'i ve idempotency anahtarı kullanan fake ServiceNow
  adaptörü,
- veri-minimum olay zarfı, deterministik idempotency anahtarı ve fail-closed
  hata davranışı kullanan SIEM audit adaptörü.

Bileşim `build_enterprise_lab_application_adapters` ile, ancak mevcut ortam
kapısı başarılı olduktan sonra oluşturulur. Kimlik grup-rol-scope eşlemesi
çağıran tarafından sürümlü `SyntheticIdentityPolicy` olarak verilmek zorundadır;
istek gövdesi veya header rol/scope kaynağı değildir. Secret manager bearer
değeri yalnız runtime secret dosyasından okunur ve sonuç/hata metnine eklenmez.

Uygulama bağlantısı yalnız `LOCAL` ve `ACCEPTANCE` ortamlarını kabul eder.
Keycloak iddiasında sentetik MFA kanıtı veya bilinen grup eşlemesi yoksa erişim,
secret bulunamazsa çözümleme, ServiceNow yetki/ağ hatasında gönderim ve SIEM
audit aktarımı güvenli biçimde başarısız olur.

## Canlı adapter kabul kapısı

`ENTERPRISE-LAB-03` için aşağıdaki komut Compose yapılandırmasını doğrular,
servisleri volume silmeden healthy duruma getirir ve uygulama adaptörlerini
gerçek container DNS/ağı üzerinde çalıştırır:

```bash
./infra/enterprise-lab/scripts/verify-live.sh
```

One-shot `adapter-e2e` çıktısı yalnız senaryo adı ile `PASSED` durumu, `LOCAL`,
`SYNTHETIC_ACCEPTANCE` ve `PrototypeVerified` sınıflandırmasını içerir. Secret,
token, endpoint veya istek/yanıt payloadı yazdırılmaz. Kapı şunları doğrular:

- sentetik Keycloak oturumu ve sürümlü grup-rol-kaynak/dataset scope eşlemesi;
- geçersiz token ve eşlenmemiş grubun fail-closed reddi;
- dosya tabanlı secret-reference çözümleme, eksik dosya ve yetki reddi;
- fake ServiceNow create/idempotent replay ile 403, 503, timeout ve 429 sonrası
  kontrollü toparlanma;
- SIEM veri-minimum/idempotent aktarım, hatalı payload reddi ve hatalı yanıt
  sonrası fail-closed toparlanma.

Hata enjeksiyonu yalnız internal ağdan, runtime dosyasındaki sentetik kontrol
credential'ı ile tek sonraki isteğe uygulanır. Bu yüzey ve direct-grant oturum
kurulumu yalnız laboratuvar kabul otomasyonudur; production kimlik veya chaos
yüzeyi değildir. Doğrulama servisi `acceptance` profiline bağlı olduğundan normal
Compose başlatmasında çalışmaz.

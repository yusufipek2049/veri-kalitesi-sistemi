# ENTERPRISE-LAB-01

Bu dizin yalnız sentetik veri ve production olmayan yerel geliştirme için kurumsal
entegrasyon laboratuvarıdır. Keycloak, yerel secret çözümleyici, PostgreSQL
primary-standby, RabbitMQ, fake ServiceNow, SIEM collector ve create-only kanıt
deposu temel servislerini tek ayrılmış Docker bridge ağı içinde çalıştırır.

## Başlatma

```bash
./infrastructure/enterprise-lab/scripts/bootstrap-secrets.sh
docker compose -f infrastructure/enterprise-lab/compose.yaml up -d --build --wait
docker compose -f infrastructure/enterprise-lab/compose.yaml ps
```

Çalışma zamanı secret dosyaları `runtime-secrets/` altında `0600` izinle yerelde
üretilir, Git tarafından yok sayılır ve değerleri komut çıktısına yazılmaz.
Compose yalnız loopback portları yayımlar. `environment-gate` başarıyla
tamamlanmadan diğer servisler başlamaz.

Kapatmak için:

```bash
docker compose -f infrastructure/enterprise-lab/compose.yaml down
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

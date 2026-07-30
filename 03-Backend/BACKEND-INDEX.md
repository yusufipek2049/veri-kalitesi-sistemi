---
type: implementation-index
area: backend
project: Veri Kalitesi İzleme ve Skorlama Sistemi
updated_at: 2026-07-29
---

# Backend Modül Haritası

## Kanonik Uygulama Durumu

| Alan | Gereksinim | Kod odağı | Durum |
| --- | --- | --- | --- |
| Kimlik, oturum ve RBAC | [Kullanıcı ve Yetki](../01-SRS/04-Fonksiyonel-Gereksinimler/04.01-Kullanici-ve-Yetki.md) | `veri_kalitesi/identity`, `api/`, `enterprise_lab` | Sentetik Keycloak prototip adaptörü canlı container ağında olumlu/negatif kabul kapısından geçti; gerçek LDAP/IdP ve üretim session altyapısı açık. |
| Veri kaynakları | [Veri Kaynağı Yönetimi](../01-SRS/04-Fonksiyonel-Gereksinimler/04.02-Veri-Kaynagi-Yonetimi.md) | `veri_kalitesi/data_sources`, `enterprise_lab` | Ortam-kapsamlı yerel prototip secret adaptörü canlı dosya/yetki negatifleriyle doğrulandı; gerçek secret manager/PAM açıktır. |
| Profilleme | [Metadata ve Profilleme](../01-SRS/04-Fonksiyonel-Gereksinimler/04.03-Metadata-ve-Profilleme.md) | `veri_kalitesi/data_sources` | DQ-CAP prototipinde politika kontrollü bounded CSV örneği, salt-okunur PostgreSQL source aggregate, Top-N/dağılım/sayısal özet, IQR/robust-z adayı ve yedi drift ailesi vardır; politika/fingerprint yokluğu fail-closed'dur. Kolon ilişkisi, production secret/KMS wiring'i, ölçek/yük ve ekran açıktır. |
| Kural yönetimi | [Kural Yönetimi](../01-SRS/04-Fonksiyonel-Gereksinimler/04.04-Kural-Yonetimi.md) | `veri_kalitesi/rules` | Şablonlar, güvenli özel SQL, yaşam döngüsü/onay, API, PostgreSQL repository ve migration mevcut; zaman serisi/genel mutabakat ve shadow yürütme modu açıktır. |
| Çalıştırma/zamanlama | [Çalıştırma ve Zamanlama](../01-SRS/04-Fonksiyonel-Gereksinimler/04.05-Calistirma-ve-Zamanlama.md) | `veri_kalitesi/executions`, `api/postgresql_execution.py` | 36E production cutover tamamlandı. 36F ile scheduling/source-usage policy PostgreSQL repository ve migration'ı eklendi; SQLite repository'ler runtime export'tan çıkarıldı. |
| Kalıcı iş kuyruğu | [Çalıştırma ve Zamanlama](../01-SRS/04-Fonksiyonel-Gereksinimler/04.05-Calistirma-ve-Zamanlama.md), [Güvenilirlik](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.04-Guvenilirlik-ve-Hata-Toleransi.md) | `veri_kalitesi/jobs` | 36H1 kuyruk/lease/concurrency çekirdeği ve 36H2 atomik enqueue/iptal, heartbeat/reaper, ayrı deadline/sürücü iptali, bounded total-timeout, retry, terminal audit/outbox ve dead-letter yaşam döngüsü `TechnicallyVerified` olarak tamamlandı. |
| Skorlama | [Skorlama](../01-SRS/04-Fonksiyonel-Gereksinimler/04.06-Skorlama.md) | `veri_kalitesi/scoring` | Çekirdek ve politika modelleri mevcut; sürümlü kurumsal politika/üretim kalıcılığı kısmi. |
| Dashboard | [Dashboard](../01-SRS/04-Fonksiyonel-Gereksinimler/04.07-Dashboard.md) | `veri_kalitesi/dashboard`, `api/app.py` | Güvenli özet API mevcut; iş alanı/SLA kırılımı ile mühendis dağılım-lineage-teşhis yüzeyi ve gerçek üretim veri/IdP adaptörleri açık. |
| Bildirim | [Bildirim](../01-SRS/04-Fonksiyonel-Gereksinimler/04.08-Bildirim.md) | `veri_kalitesi/notifications` | Sistem içi akış mevcut; kurumsal kanal kararları/adaptörleri açık. |
| Sorun yönetimi | [Sorun Yönetimi](../01-SRS/04-Fonksiyonel-Gereksinimler/04.09-Sorun-Yonetimi.md) | `veri_kalitesi/issues`, issue API | PostgreSQL-only issue yolu ile inceleme/atama/çözüm/doğrulama/kapatma ve yeniden açma davranışları mevcut; `36B5` teknik olarak doğrulanmıştır. |
| Raporlama | [Raporlama](../01-SRS/04-Fonksiyonel-Gereksinimler/04.10-Raporlama.md) | `veri_kalitesi/reporting`, report API | 36G ile report domain, PDF/XLSX/CSV üretimi, fail-closed politika framework'ü, PostgreSQL repository, API ve zamanlama yüzeyi uygulanmıştır. Kurumsal DLP/watermark ürünü ve süreçten bağımsız kalıcı queue/worker dayanıklılığı açıktır. |
| Audit | [Audit](../01-SRS/04-Fonksiyonel-Gereksinimler/04.11-Audit.md) | `veri_kalitesi/audit`, audit API, `enterprise_lab` | Veri-minimum/idempotent ve fail-closed sentetik SIEM adaptörü canlı ağda hatalı payload/yanıt toparlanmasıyla doğrulandı; kurumsal WORM/imza/SIEM ürünü açık. |
| ServiceNow | [API ve Entegrasyon](../01-SRS/04-Fonksiyonel-Gereksinimler/04.12-API-ve-Entegrasyon.md) | `veri_kalitesi/servicenow`, `enterprise_lab` | Idempotent fake HTTP adaptörü canlı ağda 403/503/timeout/429 ve toparlanma senaryolarıyla doğrulandı; gerçek kurumsal adaptör açık. |
| Olay müdahale | [Bankacılık Kontrolleri](../01-SRS/17-Bankacilik-Uyum/17.02-Bankacilik-Kontrol-Gereksinimleri.md) | `veri_kalitesi/incident_response` | Teknik akış ve kanıt modeli mevcut; kurum rolleri/ürün entegrasyonu açık. |
| Güvenli SDLC | [Bankacılık Kontrolleri](../01-SRS/17-Bankacilik-Uyum/17.02-Bankacilik-Kontrol-Gereksinimleri.md) | `veri_kalitesi/secure_sdlc` | Yerel tarama/manifest/preflight mevcut; CI zorlaması ve kurumsal araçlar açık. |
| Kanıta dayalı karar desteği | [FR-097–111](../01-SRS/04-Fonksiyonel-Gereksinimler/04.14-Kanita-Dayali-Karar-Destegi.md) | Hedef mimari | Gereksinim ve mimari hedef; genel runtime uygulaması değildir. |

Ayrıntılı ürün özelliği karşılaştırması ve uygulama boşlukları
[Ürün Yetenek Durum Matrisi](../00-Proje-Hafizasi/Urun-Yetenek-Durum-Matrisi.md)
içinde tutulur.

## API ve Kalıcılık Notları

- API sözleşmesinin kanonik gereksinim kaynağı SRS'dir; gerçek route yüzeyi
  `03-Backend/src/veri_kalitesi/api/app.py` ile birlikte doğrulanır.
- PostgreSQL'e taşınan bir domain için migration/repository bulunması tek başına
  runtime composition root'unun taşındığını kanıtlamaz.
- Kaynak sistem erişimi salt okunurdur. Yazımlar yalnız uygulamanın sahip olduğu
  metadata, politika, sonuç, iş akışı ve audit alanlarına yapılır.
- Secret, parola veya ham hassas veri log/audit/payload içinde tutulmaz.

## Çapraz Kaynaklar

[Performans](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.01-Performans.md) ·
[Güvenilirlik](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.04-Guvenilirlik-ve-Hata-Toleransi.md) ·
[Güvenlik](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md) ·
[Gözlemlenebilirlik](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.09-Gozlemlenebilirlik.md) ·
[İterasyon 36](../09-Iterasyonlar/Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md)

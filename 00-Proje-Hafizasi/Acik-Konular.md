---
type: open-decision-register
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-27
---

# Açık Konular

Bu dosya yalnız gerçek açık kararları, kurumsal incelemeleri ve dış bağımlılıkları tutar. Teknik yönü kesinleşmiş kayıtlar [Alınan Kararlar](Alinan-Kararlar.md) içindedir. Önceki ayrıntılı liste [arşivde](../docs/archive/project-memory-2026-07-24/Acik-Konular.md) korunur.

## Açık Karar ve Onay Kayıtları

| ID | Konu | Karar sahibi | Durum |
| --- | --- | --- | --- |
| `OPEN-BNK-001` | Uygulanabilir BDDK bilgi sistemleri hükümlerinin teyidi | Uyum / Hukuk / Bilgi Güvenliği | `ComplianceReviewRequired` |
| `OPEN-BNK-002` | IdP grup-rol-scope değerleri ve joiner/mover/leaver kaynağı | IAM / İK / Bilgi Güvenliği | `Açık` |
| `OPEN-BNK-008` | Saklama/imha sürelerinin, gerekçelerin, banka rollerinin ve fiziksel adaptörlerin onayı | Hukuk / KVKK Komitesi / İç Denetim | `ComplianceReviewRequired` |
| `OPEN-BNK-009` | ServiceNow kurulum yeri, veri işleyen/alt işleyen ve yurt dışı aktarım etkisi | Hukuk / Tedarik / Bilgi Güvenliği | `Açık` |
| `OPEN-BNK-011` | İş etki analizi, RPO/RTO onayı, yedek şifreleme ve restore test sıklığı | İş Sürekliliği / Operasyon | `ComplianceReviewRequired` |
| `OPEN-BNK-013` | Risk/düzenleyici raporlama zinciri ve BCBS 239 kapsamı | Risk Yönetimi / Veri Yönetişimi | `Açık` |
| `OPEN-BNK-018` | Gerçek IdP/LDAP endpoint, TLS güveni, timeout ve teknik hata sahipliği | IAM / Altyapı / Bilgi Güvenliği | `Açık` |
| `OPEN-BNK-019` | Giriş/rate-limit eşikleri, opak anahtar rotasyonu, istemci referansı ve paylaşımlı depo onayı | IAM / Bilgi Güvenliği / Mimari / Altyapı / İç Kontrol | `ComplianceReviewRequired` |

## Açık Uygulama ve Operasyon Bağımlılıkları

| Alan | Açık bağımlılık | İlgili kayıt |
| --- | --- | --- |
| PostgreSQL geçişi | 36E execution cutover ile 36F scheduling/source-usage policy kalıcılığı tamamlandı; açık teknik sınır kalıcı queue lease/heartbeat, worker kaybı toparlama ve dead-letter yaşam döngüsüdür | `ADR-020`, `36E`, `36F`, [NEXT_STEP](../NEXT_STEP.md) |
| Kimlik ve yetki | gerçek IdP callback/state/nonce, banka grup-rol-scope eşlemesi, PAM/break-glass ve HA session store | `OPEN-BNK-002`, `018`, `019` |
| Entegrasyon ve operasyon | ServiceNow alan/durum eşlemesi, kalıcı publisher worker, SIEM/WORM ve alarm politikaları | `OPEN-BNK-005/006/009/010/016` karar yönleri + kurumsal uygulama |
| Yaşam döngüsü ve DR | fiziksel imha/arşiv adaptörü, legal-hold işletimi, yedek/restore ve DR tatbikatı | `OPEN-BNK-008`, `011`, `012` |
| Skorlama/yeterlilik | banka onaylı sürümlü politika kayıtları, tarihsel replay/backfill ve kullanım kararı runtime'ı | `DQ-SCR-*`, `OPEN-BNK-013/017/021` |
| Dışa aktarma | 36G güvenli üretim/indirme ve fail-closed politika framework'ü uygulandı; kurumsal DLP/watermark ürün entegrasyonu açık | `OPEN-BNK-014` — `ApprovedByBank`; `36G` teknik kapanış |

Belirsizlik güvenlik, uyum veya iş kuralını etkiliyorsa otomatik karar verilmez; ilgili kayıt güncellenir ve işlem fail-closed kalır.

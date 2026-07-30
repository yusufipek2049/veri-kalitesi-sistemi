---
type: next-step
status: completed
updated_at: 2026-07-30
work_package: DQ-CAP-PROTOTYPE-01
predecessor: ENTERPRISE-LAB-03
---

# Son Tamamlanan Çalışma Paketi — Deterministik Profilleme ve Drift

[DQ-CAP-PROTOTYPE-01](09-Iterasyonlar/DQ-CAP-PROTOTYPE-01-Deterministik-Profilleme-ve-Drift.md)
yalnız sentetik/yerel deterministik profilleme ve drift çekirdeği olarak
`PrototypeVerified` sınıfında kapanmıştır.

## Tamamlanan Kapsam

- Top-N, tip/format dağılımı, sayısal özet ve IQR/robust-z aykırı değer
  adayları sürümlü politika parametreleriyle üretildi.
- CSV gelişmiş analizi politika kontrollü deterministik ve bounded örnektir;
  PostgreSQL gelişmiş metrikleri salt-okunur kaynak aggregate sorgularıyla
  ham satır taşımadan üretilir.
- Güncellik yalnız politika kapsamındaki mevcut/uyumlu tarih-zaman alanlarında
  üretilir; PostgreSQL bu alanlarda salt-okunur `MAX(...)` aggregate kullanır,
  kapsam dışındaki parse edilebilir tarih alanı metrik veya sinyal üretmez.
- Uyumlu snapshot'larda hacim, null/distinct, kategori, sayısal özet,
  güncellik ve şema değişimi deterministik karşılaştırıldı.
- Politika yokluğu `CONFIGURATION_ERROR` ve hükümsüz sonuç olarak korundu.
  Bu kapı gelişmiş analiz/anomali hükmüyle sınırlıdır; FR-016 exact distinct
  ve FR-018 duplicate temel metrikleri politika olmadan da üretilir.
- Hassas/sınıflandırılmamış Top-N değerleri maskelendi; kategori kaybı ham
  değer açmadan, açıkça enjekte edilen secret/key ve kararlı key ID ile HMAC
  fingerprint üzerinden karşılaştırıldı. Konfigürasyon yokluğunda fingerprint
  üretilmez ve anomali hükmü fail-closed `CONFIGURATION_ERROR` kalır.
- Kritik karşılaştırma yazımı audit/outbox ile atomik hale getirildi.

## Doğrulama

- Güncel controller birim kapısı skipsiz exit `0` tamamlandı.
- Implementer hedefli profil/data-source birim testleri `92 passed`, API
  sözleşmesi testleri `8 passed`, exit `0`.
- Compile, dar kapsamlı Ruff ve mypy kapıları başarılı.
- Güncel controller PostgreSQL entegrasyon kapısı skipsiz exit `0` tamamlandı;
  implementer migration/repository, servis yeniden-kurma ve sentetik
  source-aggregate ve policy-kapsamlı güncellik senaryolarını skipsiz
  `14 passed`, exit `0` ile
  doğruladı.
- Ayrıntılı komut ve sonuçlar
  [kapanış kaydındadır](09-Iterasyonlar/DQ-CAP-PROTOTYPE-01-Deterministik-Profilleme-ve-Drift.md).

## Sıradaki Durum

Prototip sonucu production readiness veya `ApprovedByBank` üretmez. Production
ölçek/yük, politika kalibrasyonu/onayı, kullanıcı ekranı ve kurumsal
bağımlılıklar kanonik [backlogda](00-Proje-Hafizasi/Sonraki-Adimlar.md) açık kalır.

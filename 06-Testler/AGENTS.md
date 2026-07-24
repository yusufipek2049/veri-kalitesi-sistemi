# AGENTS.md — Testler

Önce kök [AGENTS.md](../AGENTS.md) ve test edilen modülün yerel talimatlarını
uygula. Bu dosya test katmanına özgü ek kuralları tanımlar.

- Testleri ilgili FR/UC/AC kimlikleriyle izlenebilir kıl.
- Mutlu yolun yanında doğrulama, yetki, teknik hata, timeout, retry,
  idempotency, rollback ve fail-closed yollarını kapsa.
- LDAP, PostgreSQL, ServiceNow, SIEM ve diğer harici bağımlılıkları uygun
  sözleşme/entegrasyon sınırında taklit et; domain testlerini dış servise bağlama.
- Gerçek kişisel veri, token, parola veya kurum bilgisi kullanma.
- Teknik hata ile veri kalitesi başarısızlığını farklı beklenen sonuçlarla test et.
- `TechnicallyVerified` öncesi test dosyası, test adı, komut, sonuç ve kanıt
  yolunu kaydet.

## Sentetik Veri

- Etkin `SyntheticDatasetPolicy`, üretici/şema/politika sürümü ve seed olmadan
  üretim başlatma.
- Gerçek veriyi kopyalayıp yalnız kimliğini değiştirerek sentetik sayma.
- Ground truth'u test edilen kural/skor motorundan türetme; bağımsız oracle kullan.
- Kusur, geçerli sınır değer ve teknik hatayı ayrı test et.
- Karar verilmemiş eşikleri uydurma; politika yokluğunu ve fail-closed davranışı test et.
- Olayları yalnız fake/sandbox adaptörlere gönder.

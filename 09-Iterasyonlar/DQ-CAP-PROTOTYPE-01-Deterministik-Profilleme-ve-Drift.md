---
iteration: DQ-CAP-PROTOTYPE-01
status: PrototypeVerified
completed_at: 2026-07-30
---

# DQ-CAP-PROTOTYPE-01 — Deterministik Profilleme ve Drift Çekirdeği

## Kapsam

`DQ-CAP-001`, `DQ-CAP-002` ve `DQ-CAP-006` yönünde mevcut
`veri_kalitesi/data_sources` profilleme akışı genişletildi:

- politikadan çözülen Top-N, tip/format dağılımı ve sayısal
  min/max/mean/median/Q1/Q3/MAD özeti;
- CSV için politika boyutu/eşiği/seed'i ile sınırlı deterministik hash örneği;
  politika yokluğunda ham gelişmiş analiz koleksiyonu yapılmayan açık
  `CONFIGURATION_ERROR`;
- PostgreSQL için quoted identifier ve bind parametreli salt-okunur kaynak
  aggregate sorgularıyla Top-N, format/tip dağılımı, sayısal özet ve aykırı
  değer adayları; ham kaynak satırı uygulamaya taşınmaz;
- politika seçimine göre IQR ve robust z-score aykırı değer adayları;
- yöntem, kapsam, örneklem, sorgu/bağlayıcı/politika sürümü, veri zamanı ve
  şema taşıyan uyumlu profil snapshot sözleşmesi;
- hacim, null/distinct oranı, kategori kaybı, sayısal özet, güncellik ve şema
  farkı için deterministik karşılaştırma; güncellik metriği yalnız politikada
  açıkça seçilen mevcut/uyumlu tarih-zaman alanlarında üretilir, PostgreSQL
  yolu ham satır taşımadan salt-okunur `MAX(...)` aggregate kullanır;
- politika yokluğunda eklenen/kaldırılan/değişen şema kanıtını koruyan,
  metrik drift sınıflandırması üretmeyen `CONFIGURATION_ERROR` ve
  `anomaly_candidate=null` fail-closed sonucu;
- politika kapısından bağımsız FR-016 exact distinct ve FR-018 exact duplicate
  temel metrikleri; ham değerleri kalıcı profile veya loga taşımayan geçici
  fingerprint sayaçları;
- hassas veya sınıflandırılmamış alanda ham Top-N yerine sıra/sayı, maske ve
  yalnız açık secret/configuration sınırından enjekte edilen anahtarla HMAC
  kategori fingerprint'i; anahtar/kararlı kimlik yokluğunda
  `CATEGORY_FINGERPRINT_KEY_UNAVAILABLE` ve hükümsüz `CONFIGURATION_ERROR`,
  algoritma/anahtar kimliği değişiminde hükümsüz uyumsuzluk;
- bağlayıcı sürümü farklı snapshot'ların hükümsüz `INCOMPATIBLE` sayılması;
- karşılaştırma sonucu için PostgreSQL migration/repository ve atomik
  audit/outbox yazımı; domain doğrulamasını güvenli `400`, teknik/depolama
  hatasını `503` olarak ayıran bağımlılık-enjekte edilen FastAPI sözleşmesi.

ML veya shadow model eklenmemiştir.

## Hedefli doğrulama

- Güncel controller birim kapısı skipsiz exit `0`.
- Implementer hedefli profil/data-source birim testleri: `92 passed`, exit `0`;
  bu koşu politikasız CSV profilinde gerçek distinct/duplicate temel
  metriklerini, CSV profil üretiminden karşılaştırmaya policy kapsam içi/dışı
  güncellik davranışını ve eksik/geçersiz alanın `ValidationError` ile
  fail-closed kalmasını kapsar.
- Profil API sözleşmesi testleri: `8 passed`, exit `0`.
- `python3 -m compileall`: exit `0`.
- Değişen profil/backend/test dosyalarında Ruff: exit `0`.
- Dar kapsamlı mypy: exit `0`.
- Güncel controller PostgreSQL entegrasyon kapısı skipsiz exit `0`; implementer
  ilgili PostgreSQL veri kaynağı dosyasını skipsiz `14 passed`, exit `0` ile
  çalıştırdı. Bu koşu migration/repository, servis yeniden-kurma ve gerçek
  sentetik PostgreSQL tablosunda kaynak-aggregate gelişmiş profil ile
  policy-kapsamlı `MAX(...)` güncellik karşılaştırmasını kapsar.

## Sınıflandırma ve kalan sınırlar

- **Teknik sınıflandırma:** `PrototypeVerified`
- **Uyum/banka durumu:** `ComplianceReviewRequired`
- **Banka onayı:** Üretilmedi; `ApprovedByBank` değildir.
- **Production readiness:** Üretilmedi; production-ready değildir.

PostgreSQL production composition wiring'i, production envanterinde ölçek/yük
kanıtı, kurumsal politika onayı, kolon ilişkisi analizi ve kullanıcı ekranı bu
prototip kanıtının dışındadır.

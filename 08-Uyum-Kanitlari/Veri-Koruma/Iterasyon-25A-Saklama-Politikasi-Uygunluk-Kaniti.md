---
control_ids:
  - CTRL-KVKK-INV-001
  - CTRL-KVKK-DEL-001
requirement_ids:
  - BFR-LCM-001
  - BFR-LCM-002
  - RULE-014
  - NFR-PRV-005
  - NFR-CMP-001
  - NFR-CMP-003
status: TechnicallyVerified
version: iteration-25a-local
executed_at: 2026-07-21
---

# İterasyon 25A Saklama Politikası Uygunluk Kanıtı

## Değişiklik

- İterasyon: 25A - Sürümlü saklama politikası ve legal hold kontrollü dry-run
- Commit/Artifact: `25A — Saklama politikası uygunluk değerlendirmesi`
- Bileşen: `veri_kalitesi.retention`
- Kontrol/Gereksinim: BFR-LCM-001/002, RULE-014, NFR-PRV-005, NFR-CMP-001/003, CTRL-KVKK-INV-001, CTRL-KVKK-DEL-001

## Doğrulama

- Komut: `python3 -m pytest -q`
- Ortam: Python 3.10, yerel prototip, yalnız sentetik ve opak kayıt referansları
- Sentetik veri seti: Altı zaman bazlı provisional politika, artık yıl tarihleri, süresi dolmamış/dolmuş kayıtlar, aktif legal hold, sentetik onay referanslı politika, geçersiz metadata ve legal hold resolver arızası
- Beklenen: Kayıt sınıfına göre takvimsel saklama sonu hesaplanır; aktif legal hold imha uygunluğunu engeller; banka onayı olmayan süresi dolmuş kayıt `ComplianceReviewRequired` kalır; resolver arızası teknik hata olur; hiçbir fiziksel imha veya arşivleme yapılmaz.
- Gerçekleşen: 759 test geçti. Retention hedef grubunda 9 yeni test geçti.
- Sonuç: PASS

Ek kontroller:

- `python3 -m mypy 03-Backend/src 06-Testler`: PASS, 114 kaynak dosya
- `python3 -m ruff check .`: PASS
- Değişen Python dosyalarının Ruff format kontrolü: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- Veri minimizasyonu incelemesi: Değerlendirme yalnız opak kayıt referansı, kayıt sınıfı, politika kimliği/sürümü, zaman ve legal hold sayısı taşır; ham kayıt veya kişisel veri kabul etmez.

## Güvenlik ve Yaşam Döngüsü

- Politika kataloğu: `RET-10Y-BANKING`, `RET-5Y-REGLOG`, `RET-3Y-ERASURE`, `RET-1Y-OPS`, `RET-90D-TRANSIENT` ve `RET-30D-EXPORT` kayıt sınıfları sürümlü ve `ComplianceReviewRequired` durumunda modellenmiştir.
- Takvim hesabı: Yıllık süreler sabit gün sayısına çevrilmez; artık yıl sonları takvimsel olarak hesaplanır. Periyodik imha üst aralığı `P180D` kararıyla 180 gün olarak doğrulanır.
- Legal hold: Resolver yalnız aktif, aynı kayıt/sınıf/politika sürümüne bağlı ve karar sahibi rolü bulunan hold döndürebilir; hold varsa politika onaylı olsa bile uygunluk verilmez.
- Banka onayı: Varsayılan katalog hiçbir kaydı imhaya uygun işaretlemez. `ApprovedByBank` politika kaydı opak onay referansı olmadan fail-closed reddedilir; testteki onay yalnız sentetik negatif/pozitif sözleşme doğrulamasıdır.
- Teknik hata ayrımı: Eksik/geçersiz kayıt veya hold metadata'sı doğrulama hatasıdır; hold resolver kesintisi ayrı `RetentionTechnicalError` üretir.
- Fiziksel işlem yokluğu: Bu dilim yalnız dry-run değerlendirmesidir; silme, anonimleştirme, arşivleme, geri çağırma veya auditli imha işi içermez.
- Geri alma: Paket bağımsız ve salt okunurdur; composition root'a bağlanmadığından güvenli pasifleştirme paketi kullanımdan çıkarmaktır.
- Kalan risk: Hukuk/KVKK komitesi/iç denetim onayı, kayıt türü eşleme adaptörleri, kalıcı legal hold yaşam döngüsü, maker-checker, idempotent imha worker'ı, audit, arşiv geri çağırma ve yedek re-delete akışı açık kalır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Hukuk/KVKK komitesi: ComplianceReviewRequired
- İç denetim: ComplianceReviewRequired
- Bilgi güvenliği: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; KVKK/BDDK uyumu, banka onayı veya gerçek kayıt imhası anlamına gelmez.

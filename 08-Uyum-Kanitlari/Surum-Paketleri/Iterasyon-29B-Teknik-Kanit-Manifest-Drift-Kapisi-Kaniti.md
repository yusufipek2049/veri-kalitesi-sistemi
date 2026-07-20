---
type: technical-evidence
status: TechnicallyVerified
control_ids:
  - BFR-SDLC-002
  - NFR-CMP-002
  - NFR-CMP-005
version: ITERATION_29B
date: 2026-07-20
producer_role: Codex
---

# İterasyon 29B Teknik Kanıt Manifest Drift Kapısı Kanıtı

## Kapsam

- Politika: `29B-v1`
- Katalog: [İterasyon 29A Teknik Kanıt Kataloğu](Iterasyon-29A-Teknik-Kanit-Katalogu.json)
- Saklanan manifest: [İterasyon 29A Teknik Kanıt Manifesti](Iterasyon-29A-Teknik-Kanit-Manifesti.json)
- Doğrulanan saklanan/üretilen SHA-256:
  `8909af184797ffe493082f2a9a8ebbfbad818c987416830a76732ec15eaa8a24`

## Doğrulanan Teknik Davranış

- Manifest katalog ve kanıt artifact'larından kanonik baytlarla yeniden üretilir.
- Saklanan manifestle bayt düzeyinde eşleşme `MATCH`, içerik değişikliği `DRIFT`
  üretir.
- CLI çıkış kodları `0=MATCH`, `1=DRIFT`, `2=VALIDATION_ERROR/TECHNICAL_ERROR`
  sözleşmesine uyar.
- Saklanan manifest yalnız sürüm paketi dizinindeki kanonik `.json` yolundan,
  salt okunur ve symlink reddedilerek açılır.
- Sonuç manifest veya kanıt içeriği yerine yalnız politika, durum ve iki SHA-256
  özeti taşır.

## Çalıştırılan Kontroller

```bash
pytest -q 06-Testler/01-Birim/test_secure_sdlc_evidence.py 06-Testler/01-Birim/test_secure_sdlc_evidence_gate.py
PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc.evidence_gate 08-Uyum-Kanitlari/Surum-Paketleri/Iterasyon-29A-Teknik-Kanit-Katalogu.json 08-Uyum-Kanitlari/Surum-Paketleri/Iterasyon-29A-Teknik-Kanit-Manifesti.json .
```

Hedefte 52, güvenli SDLC grubunda 184 ve tam regresyonda 682 test geçti. Ruff lint,
hedef format/mypy ve derleme kontrolleri başarılıdır. Yerel secret taraması 338
dosyada sıfır bulguyla `CLEAN` tamamlandı; SBOM byte düzeyinde yeniden üretildi ve
gerçek artifact doğrulaması `MATCH` ile çıkış kodu `0` üretti. Tam depo formatında
dört eski dosya ve tam mypy'de yedi dosyada 27 eski hata değişmemiştir.

## Güvenlik ve Veri Gizliliği

Kapı depo dışı ve kanıt paketi dışı manifest yollarını fail-closed reddeder. Çıktı
ham manifest, kanıt içeriği, müşteri/banka verisi, kullanıcı kimliği veya secret
içermez. Drift teknik hataya, teknik hata da temiz sonuca dönüştürülmez.

## Sınırlar ve Geri Alma

Bu teknik doğrulama CI/CD zorlaması, elektronik imza, değişmez kurumsal saklama,
istisna/risk kabulü, BDDK/KVKK uyumu veya banka onayı değildir. Güvenli
pasifleştirme komutu release sürecine bağlamamaktır; geri alma `evidence_gate.py`,
ilgili model/export ve testleri tek commit üzerinden kaldırmaktır. 29A katalog,
manifest ve önceki kanıtlar değiştirilmez.

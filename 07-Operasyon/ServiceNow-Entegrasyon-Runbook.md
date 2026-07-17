# ServiceNow Entegrasyon Runbook

## Ön koşullar

- Onaylı servis hesabı ve secret referansı
- Onaylı tablo/alan eşlemesi
- Veri bölgesi ve aktarım değerlendirmesi
- Idempotency anahtarı
- Timeout/retry politikası
- Payload allowlist'i

## Hata durumları

- Yetki/kimlik hatası: retry etme, güvenlik/operasyon olayına yönlendir.
- Geçici ağ hatası: sınırlı retry.
- Aynı idempotency anahtarı: mevcut ticket'ı çöz.
- Farklı payload aynı anahtar: kontrollü çakışma.
- Redaksiyon ihlali: çağrıyı göndermeden reddet.

## Yasak

Ham kayıt, müşteri kimliği, hesap/kart bilgisi, SQL sonucu ve secret gönderilmez.

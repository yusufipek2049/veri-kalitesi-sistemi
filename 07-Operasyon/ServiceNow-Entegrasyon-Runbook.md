# ServiceNow Entegrasyon Runbook

## Ön koşullar

- Onaylı servis hesabı ve secret referansı
- Onaylı tablo/alan eşlemesi
- Veri bölgesi ve aktarım değerlendirmesi
- Idempotency anahtarı
- Timeout/retry politikası
- Payload allowlist'i
- Ara entegrasyon tablosu veya entegrasyon servisi

## Outbound kayıt sözleşmesi

- idempotency anahtarı
- yerel ve uzak durum
- ServiceNow kayıt kimliği
- deneme sayısı ve artan bekleme zamanı
- dead-letter veya manuel müdahale durumu
- son senkronizasyon zamanı
- hata kodu ve güvenli hata özeti
- audit referansı

## Hata durumları

- Yetki/kimlik hatası: retry etme, güvenlik/operasyon olayına yönlendir.
- Geçici ağ hatası: kalite çalıştırmasını kaybetmeden artan beklemeli sınırlı retry.
- Aynı idempotency anahtarı: mevcut ticket'ı çöz.
- Farklı payload aynı anahtar: kontrollü çakışma.
- Redaksiyon ihlali: çağrıyı göndermeden reddet.
- Retry sınırı aşımı: kaydı dead-letter veya manuel müdahale durumuna al ve alarm üret.

## Yasak

Ham kayıt, müşteri kimliği, hesap/kart bilgisi, SQL sonucu ve secret gönderilmez.

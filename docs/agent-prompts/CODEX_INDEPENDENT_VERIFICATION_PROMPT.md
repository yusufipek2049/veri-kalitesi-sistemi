# Codex — Bağımsız Kod Doğrulama Promptu

`docs/functional-audit/` altındaki denetim raporunu bağımsız olarak doğrula.

Ana amacın Claude'un sonuçlarını desteklemek değil; hataları, yanlış
pozitifleri, yanlış negatifleri, kanıtsız çıkarımları ve yanlış öncelikleri
bulmaktır.

Kaynak kodu, migration'ları, testleri ve mevcut ürün dokümantasyonunu
değiştirme.

Yalnızca şu dosyayı oluştur:

`docs/functional-audit/14-Independent-Code-Verification.md`

## 1. GAP doğrulaması

Her GAP için:

- doğrudan kod kanıtı var mı?
- dosya ve sembol doğru mu?
- durum sınıfı doğru mu?
- uygulanmış bir fonksiyon eksik sayılmış mı?
- mock/stub bir fonksiyon implemented sayılmış mı?
- external dependency ile yazılım boşluğu karıştırılmış mı?

## 2. Veri tabanı

Kontrol et:

- migration gerçekten tablo/kolon/constraint oluşturuyor mu?
- repository gerçekten bu tabloyu kullanıyor mu?
- production composition root doğru adapter'ı bağlıyor mu?
- test ile production yolu farklı mı?
- SQLite/in-memory fallback runtime'da kalmış mı?
- audit ve iş verisi aynı transaction'da mı?
- optimistic locking ve idempotency uygulanıyor mu?

## 3. API ve frontend

Kontrol et:

- endpoint gerçekten route'a kayıtlı mı?
- request/response modeli gerçekten kullanılıyor mu?
- frontend endpoint'i çağırıyor mu?
- buton yalnızca görsel mi?
- permission yalnız frontend'de mi?
- response alanları ekranda gösteriliyor mu?
- hata, empty ve concurrency durumları yönetiliyor mu?

## 4. State transition

Kontrol et:

- geçiş merkezi domain/service üzerinden mi?
- doğrudan status update ile atlatılabiliyor mu?
- maker-checker gerçekten farklı aktör mü?
- scope kontrolü var mı?
- audit aynı transaction içinde mi?
- yasak geçişler test ediliyor mu?

## 5. Test

Kontrol et:

- test gerçek PostgreSQL mi?
- mock/in-memory mi?
- failure path var mı?
- authorization testleri scope kontrolü yapıyor mu?
- worker loss, retry, dead-letter ve replay gerçekten doğrulanıyor mu?
- frontend E2E gerçek backend davranışına bağlı mı?

## Sonuç sınıfları

Her bulguya şunlardan birini ver:

- `CONFIRMED`
- `CORRECTION_REQUIRED`
- `INSUFFICIENT_EVIDENCE`
- `FALSE_POSITIVE`
- `FALSE_NEGATIVE`
- `SEVERITY_CHANGE_REQUIRED`

Her düzeltmede:

- ilgili dosya/bölüm/GAP
- mevcut iddia
- repository kanıtı
- neden yanlış/eksik
- önerilen yeni sınıflandırma veya metin
- güven seviyesi

bilgilerini ver.

Özellikle bütün P0/P1 gap'leri ve yeni tablo önerilerini doğrula.

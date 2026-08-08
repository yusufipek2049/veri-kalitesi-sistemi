# Uygulama İterasyonu Döngüsü

Denetim tamamlandıktan sonra her geliştirme iterasyonu için aynı döngüyü kullan.

## 1. Ayrı branch

```bash
git switch main
git pull --ff-only
git switch -c feature/<islevsel-dilim>
```

Araç/ajan adı branch isminde kullanılmamalıdır.

Doğru örnekler:

- `feature/persistent-job-recovery`
- `feature/metadata-discovery`
- `feature/measurement-qualification`
- `feature/schema-drift-workflow`

## 2. Claude — iterasyon tasarımı

Claude'a yalnızca seçilen GAP ve doğrudan bağımlılıklarını ver.

İstenecek çıktı:

- amaç ve kullanıcı değeri
- aktörler
- mevcut durum
- hedef akış
- kapsam ve kapsam dışı
- state transition
- tablo/kolon/migration
- servis/API/frontend
- yetki/audit
- test planı
- acceptance criteria
- rollback/migration riski

## 3. Codex — teknik uygulanabilirlik doğrulaması

Kodlamadan önce:

- dokunulacak gerçek dosyaları doğrula
- mevcut abstraction ve adapter'ları bul
- yeniden kullanılabilecek kodu belirle
- migration sırasını kontrol et
- test altyapısının gerçek çalıştırma yolunu doğrula
- tasarımdaki yanlış varsayımları işaretle

## 4. Codex veya Qoder — uygulama

Tek iterasyonda yalnızca seçilen dikey dilimi uygula.

Kural:

- migration
- repository
- domain/service
- API
- permission
- audit
- frontend
- test

zincirinden kapsamda olan bütün halkalar tamamlanmadan “done” denmez.

## 5. Test sırası

Önerilen sıra:

1. format/lint
2. type check
3. domain unit
4. repository/migration
5. gerçek PostgreSQL integration
6. API/authorization
7. audit/outbox atomicity
8. frontend unit/integration
9. Playwright E2E
10. failure-path/concurrency/idempotency
11. tam regression

## 6. Claude — mimari ve gereksinim review

Kontrol:

- acceptance criteria karşılandı mı?
- state machine delinmiş mi?
- maker-checker/scope korunmuş mu?
- audit atomik mi?
- frontend gerçek backend'e bağlı mı?
- doküman iddiaları kod kanıtıyla uyumlu mu?
- gereksiz kapsam eklenmiş mi?
- production readiness ile fonksiyon karıştırılmış mı?

## 7. Düzeltme ve yeniden test

Review bulgularını önem sırasıyla uygula:

- veri bütünlüğü
- yetki
- state transition
- audit
- idempotency/concurrency
- kullanıcı akışı
- test boşluğu
- dokümantasyon

## 8. Kapanış kaydı

Her iterasyon sonunda:

- değişen fonksiyonlar
- migration'lar
- endpoint'ler
- ekranlar
- audit event'leri
- test sonuçları
- açık sınırlar
- production bağımlılıkları
- sonraki bağımlı iterasyon

kaydedilmelidir.

## 9. Commit

```bash
git status
git diff --stat
git diff --name-only
git add <yalnızca iterasyon kapsamı>
git commit -m "<işlevsel değişikliği açıklayan mesaj>"
```

## 10. Çıkış kapısı

- uçtan uca kullanıcı akışı çalışıyor
- gerçek persistence kullanılıyor
- permission/scope doğrulanmış
- audit ve iş verisi tutarlı
- failure path test edilmiş
- frontend/backend kopukluğu yok
- dokümantasyon güncel
- kapsam dışı maddeler açıkça yazılmış

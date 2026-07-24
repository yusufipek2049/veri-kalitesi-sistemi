# AGENTS.md — Proje Geneli

## Değişmez Sınırlar

- Sistem kurum içi veri merkezinde çalışır; kaynak sistem erişimi salt okunurdur.
- Kimlik/rol/scope yalnız güvenilir IdP/BFF sınırından çözülür.
- Secret, token ve hassas veri açık metin saklanmaz veya loglanmaz.
- Teknik hata, veri kalitesi ihlali, skor, yeterlilik ve kullanım kararı ayrıdır.
- Kritik yazım audit/outbox olmadan tamamlanmaz; belirsiz politika fail-closed'dur.
- Yeni gereksinim, karar, teknoloji, eşik veya iş kuralı uydurulmaz.

## Bağlam Kuralı

1. Önce [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) ve görev alanının
   kanonik SRS/ADR/karar kaydını aç.
2. Teslimat bağlamında yalnız [aktif son yedi iterasyonu](09-Iterasyonlar/ITERASYON-INDEX.md)
   kullan; `archive/iterations/` ve `docs/archive/` yalnız tarihsel kanıt içindir.
3. Aktif çalışma önceliği [NEXT_STEP.md](NEXT_STEP.md), backlog kaynağı
   `00-Proje-Hafizasi/Sonraki-Adimlar.md` dosyasıdır.
4. Tam depo yerine hedefli kod, migration ve test dosyalarını aç.

## Değişiklik ve Doğrulama

Kod-doküman farkında hiçbir tarafı otomatik doğru kabul etme. Bağlayıcı veya
belirsiz içeriği silme; kanonik kaynağa taşı, referansla veya açık bulgu oluştur.
`TechnicallyVerified` yalnız komut, sonuç ve kanıt yolu güncelse kullanılır.
Değişiklikten sonra ilgili test, dahili link, ID tekilliği, indeks kapsamı ve
arşivden aktif kanonik kullanım kontrol edilir.

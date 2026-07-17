# AGENTS.md — Dashboard

## Zorunlu bağlam

1. `01-SRS/04-Fonksiyonel-Gereksinimler/04.07-Dashboard.md`
2. `01-SRS/05-Kullanim-Senaryolari/UC-010-Dashboard-uzerinden-sonuclarin-incelenmesi.md`
3. `01-SRS/07-Veri-Modeli/Kural-ve-Calistirma-Varliklari.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.01-Performans.md`
4. `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.07-Kullanici-Deneyimi.md`

Yalnız görev gerektiriyorsa ayrıca `01-SRS/06-Is-Kurallari.md` ve `01-SRS/10-Kabul-Kriterleri.md` içinden ilgili ID/bölümü oku.

## Uygulama kuralları

- Dashboard sorgularını yazma modelinden ayır.
- Filtreleri yetki kapsamıyla birleştir.
- Büyük sonuçlarda sayfalama ve özet tablolar kullan.
- Boş, hesaplanmadı ve teknik hata durumlarını 0 skor gibi gösterme.

## Test beklentisi

- En az bir başarılı akış, bir doğrulama/iş kuralı hatası ve bir teknik hata testi ekle.
- Test adında veya açıklamasında ilgili FR/UC kimliğini belirt.
- Kabul kriteri ölçülebilir süre veya oran içeriyorsa uygun otomatik ya da tekrarlanabilir performans testi tanımla.
- Modül dışı davranışı değiştirmek gerekiyorsa önce etkilenen komşu modülün `AGENTS.md` dosyasını oku.

## Bankacılık ek kuralları

- `DashboardAccessScope` doğrudan kullanıcı veya API girdisinden oluşturulamaz.
- Scope yalnız güvenilir `AuthorizationService` kararından türetilmelidir.
- ENTERPRISE skor görünürlüğü, SOURCE izinlerinden ayrı explicit izin olarak kalmalıdır.
- Yetkisiz kapsam dolaylı KPI, toplam sayı veya hata mesajıyla sızdırılmamalıdır.
- Trend sorgusu hesaplanmamış dönemi sıfırlaştırmamalı ve hassas kapsamı filtrelemelidir.

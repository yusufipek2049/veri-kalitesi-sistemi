# Olay Müdahale ve KVKK İhlal Akışı

## Durumlar

`DETECTED -> TRIAGE -> CONTAINMENT -> PERSONAL_DATA_ASSESSMENT -> NOTIFICATION_DECISION -> REMEDIATION -> CLOSED`

## Zorunlu kayıtlar

- öğrenilme zamanı
- ilk tespit kaynağı
- etkilenen sistem/veri kategorisi
- etkilenen kişi grubu tahmini
- alınan koruma/containment önlemleri
- veri sorumlusu/veri işleyen değerlendirmesi
- 72 saat hedef zamanı
- hukuk/uyum kararı
- ilgili kişi bildirim kararı
- kapanış ve düzeltici faaliyet

## Sınır

Sistem zaman çizelgesi ve kanıt üretir. Kurula veya ilgili kişiye otomatik bildirim göndermez.

## Teknik Uygulama Durumu

- İterasyon 26A güvenlik olayını kişisel veri ihlali şüphesinden ayrı append-only kayıt olarak uygular.
- Öğrenilme zamanından hesaplanan 72 saat değerlendirme hedefi görünürdür; bu hedef otomatik hukuki karar değildir.
- Kapsam, önlem ve karar serbest metin yerine kod; kanıtlar içerik yerine UUID referansı olarak saklanır.
- Veri işleyen kaynaklı şüphede veri sorumlusuna bildirim kanıt referansı zorunludur.
- Şüpheyi kaydeden ile bildirim kararını kaydeden aktör farklı olmalıdır.
- İterasyon 26B yalnız güvenilir privacy reviewer ve incident scope'u için veri-minimum zaman çizelgesi görünümü sağlar; actor, scope ve kanıt kimlikleri sonuçtan çıkarılır.
- Zaman çizelgesi görünümü bekleyen, gecikmiş, zamanında karar ve gecikmiş karar durumlarını gösterir; görüntüleme audit yazılamazsa sonuç verilmez.
- Gerçek SIEM/SOC, dış bildirim, banka rol eşlemesi ve tatbikat henüz uygulanmamıştır.

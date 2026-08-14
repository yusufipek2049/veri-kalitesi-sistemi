# Denetim Faz 6: Sağlık Uç Noktaları ve Yapılandırılmış Log

## Bağlam

Sistem konteynerlerde çalışacak şekilde kurulmuş, ama **çalışırken içeride ne olduğunu
görmenin bir yolu yok.**

### Boşluk A — Sağlık ve hazırlık uç noktası yok

API 58 rota sunuyor; hiçbiri `/health`, `/ready` veya `/metrics` değil.

`infra/development/compose.yaml` içinde yalnızca `postgres` servisinin healthcheck'i var:

```yaml
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U dq_app -d data_quality"]
```

`api` ve `worker` servisleri sağlık kontrolü olmadan çalışıyor. Orkestratör uygulamanın
ayakta olup olmadığını anlayamaz; `depends_on: service_started` yalnızca sürecin
başladığını söyler, hizmet verebildiğini değil.

### Boşluk B — 222 kaynak dosyanın 5'i log üretiyor

`logging` import eden dosyalar:

```
src/veri_kalitesi/jobs/execution_command.py
src/veri_kalitesi/jobs/entrypoint.py
src/veri_kalitesi/api/notifications_router.py
src/veri_kalitesi/notifications/stream_hub.py
src/veri_kalitesi/notifications/delivery_service.py
```

Denetim (audit) kaydı güçlü ve hash-zincirli — ama bu **uyumluluk** kaydı, işletim kaydı
değil. Bir kural çalıştırması yavaşladığında, bir worker iş düşürdüğünde veya bir veri
kaynağı bağlantısı zaman aşımına uğradığında teşhis edilecek yapılandırılmış log yok.
Operasyonel metrik (Prometheus/OTel) hiç yok.

Mevcut altyapıda kullanılabilecek olan: her istek `add_correlation_id` middleware'inde
bir korelasyon kimliği alıyor (`api/app.py:193`) ve `X-Correlation-ID` başlığıyla
dışarı veriliyor. Log'lar bu kimliği taşımalı.

**Bağımlılık:** Yok. Faz 4/5 ile paralel yürütülebilir.

## Görev

1. **Sağlık ve hazırlık uç noktaları ekle.** İkisini ayır:
   - **Liveness** — süreç ayakta mı. Bağımlılık kontrol etmez, her zaman hızlı döner.
   - **Readiness** — trafik alabilir mi. Veritabanı erişilebilirliğini kontrol eder.
     Veritabanı düştüğünde hazır-değil dönmeli.

   Bu uç noktalar kimlik doğrulaması gerektirmemeli (orkestratör çağırır) ama
   **iç durum sızdırmamalı** — sürüm, şema adı, bağlantı dizgisi, yığın izi vermeyecek.

2. **Worker için sağlık sinyali.** Worker HTTP sunmuyor. Kendi durumunu nasıl bildireceğine
   karar ver — `workers` tablosundaki mevcut kalp atışı kaydı
   (`jobs/postgresql_repository.py`, `heartbeat_worker`) doğal aday. Compose'da
   çalışabilir bir healthcheck tanımla.

3. **Compose healthcheck'lerini ekle.** `api` ve `worker` servislerine healthcheck ekle;
   `depends_on` koşullarını `service_healthy`'ye yükselt.

4. **Yapılandırılmış log altyapısı kur.** JSON formatlı, korelasyon kimliği taşıyan
   merkezi bir log yapılandırması. Standart kütüphane `logging` yeterli — yeni bağımlılık
   ekleme. Log seviyesi ortam değişkeniyle ayarlanabilir olsun.

5. **Kritik yollara log ekle.** En az şunlar:
   - İş kuyruğu: claim, tamamlanma, başarısızlık, ölü mektup, kira süresi dolması
   - Kural çalıştırma: başlangıç, süre, sonuç sayıları, hata sınıfı
   - Veri kaynağı: bağlantı testi, profilleme süresi, zaman aşımı
   - Bildirim teslimatı: deneme, başarısızlık, yeniden deneme planı

   **Aşırıya kaçma** — her fonksiyona log ekleme; teşhis değeri olan sınırlarda logla.

6. **Hassas veri sızdırma.** Log'lara kimlik bilgisi, `secret_ref` çözümlenmiş değeri,
   müşteri verisi örneği veya kişisel veri yazılmayacak. Bunu doğrulayan bir test yaz.

## Invariantlar

- **Denetim (audit) kaydı bu fazın konusu değil** — mevcut hash-zincirli audit davranışı
  hiçbir şekilde değiştirilmeyecek. Operasyonel log ondan ayrı bir kanaldır.
- Sağlık uç noktaları API'nin fail-closed güvenlik duruşunu bozmayacak; kimlik doğrulaması
  gerektirmeyen tek yüzey olmaları bilinçli ve sınırlı olacak.
- Log yazımı istek yolunu ölçülebilir şekilde yavaşlatmayacak; senkron dış çağrı yapılmayacak.
- Korelasyon kimliği üretimi mevcut middleware'de kalacak, çoğaltılmayacak.
- Konteynerler `read_only` kalacak — log dosyaya değil stdout'a yazılacak.
- Yeni üçüncü parti bağımlılık yok.

## Kabul Kriterleri

1. Liveness uç noktası veritabanı kapalıyken bile 200 dönüyor — test.
2. Readiness uç noktası veritabanı erişilemezken hazır-değil dönüyor — test.
3. Sağlık yanıtları iç durum (sürüm, şema, bağlantı dizgisi, yığın izi) sızdırmıyor — test.
4. `docker compose up` sonrası `api` ve `worker` servisleri `healthy` duruma geçiyor.
5. Bir istek boyunca üretilen log satırları aynı korelasyon kimliğini taşıyor — test.
6. Log çıktısı geçerli JSON — test.
7. Kimlik bilgisi/sır içeren bir nesne loglandığında değer maskeleniyor — test.
8. `python -m pytest` tamamen yeşil.

## Teslim Formatı

- **Kod:** Değiştirilen/eklenen dosyalar ve gerekçesi.
- **Tasarım kararı:** Liveness/readiness ayrımı, worker sağlık sinyali yaklaşımı.
- **Log envanteri:** Log eklenen sınırlar ve her birinin teşhis gerekçesi.
- **Testler:** Kabul kriterlerinin her birini karşılayan test adları.
- **Test çıktısı:** Ham `pytest` sonucu ve compose healthcheck durumu.
- **Varsayımlar:** Yapılan varsayımlar ve açık kalan sorular.

## Çalışma Kuralları

- Mevcut kod stiline uy.
- Yeni üçüncü parti bağımlılık ekleme (Prometheus istemcisi dahil — metrik uç noktası
  gerekiyorsa standart kütüphaneyle asgari bir uygulama yaz veya gerekçelendirip sor).
- Testleri çalıştır ve sonucu olduğu gibi bildir.
- Belirsizlik varsa varsayımını açıkça yaz ve devam et.

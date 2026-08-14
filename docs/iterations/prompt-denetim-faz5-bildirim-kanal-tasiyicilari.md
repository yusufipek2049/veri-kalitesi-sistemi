# Denetim Faz 5: Bildirim Kanal Yönlendirmesi ve Taşıyıcılar

## Bağlam

Bildirimler sistemden **hiç çıkmıyor.** Gece yarısı oluşan bir kalite ihlali kimseye
ulaşmıyor.

Yanlış anlaşılmasın: teslimat hattı çalışıyor. Eksik olan yalnızca kanal yönlendirmesi
ve dış taşıyıcılar.

### Çalışan kısım

- Kanallar, abonelikler, teslimat kayıtları, önem eşlemesi modellenmiş
  (`src/veri_kalitesi/notifications/models.py`)
- Durum makinesi tam: `PENDING → SENDING → DELIVERED | FAILED → UNDELIVERABLE | REROUTED`,
  `DELIVERED → READ` (`delivery_service.py:61`)
- Yeniden deneme geri çekilmesi tanımlı:
  `_RETRY_BACKOFF_SECONDS = (0, 60, 300, 1800, 7200)`, en fazla 5 deneme
- Teslimat job işleyicisi **üretimde kayıtlı**:
  `src/veri_kalitesi/jobs/production.py:281,298` → `NotificationDeliveryJobHandler`
- Kanal yapılandırması sırrı değil `secret_ref` tutuyor (`models.py:191`) — bu doğru
  tasarım, korunacak

### Eksik kısım

**1. `_deliver()` kanal tipine bakmıyor.** `delivery_service.py:208`:

```python
def _deliver(self, delivery, event) -> bool:
    """Kanal adaptörünü çağırır. IN_APP için her zaman başarılı."""
    try:
        return self._inapp_adapter.deliver(event, delivery)
    except Exception:
        logger.exception("IN_APP adapter failed for delivery %s", delivery.delivery_id)
        return False
```

Kanal tipi ne olursa olsun `_inapp_adapter` çağrılıyor.

**2. Tek somut adaptör var.** `delivery_service.py:36-47`:

```python
class InAppChannelAdapter(Protocol):
    def deliver(self, event: NotificationEvent, delivery: NotificationDelivery) -> bool: ...

class DefaultInAppAdapter:
    def deliver(self, event, delivery) -> bool:
        return True
```

E-posta, webhook veya başka bir dış transport uygulaması yok.

**3. Depo sorgusu `IN_APP`'e sabitlenmiş.**
`notifications/postgresql_repository.py:433` — `get_active_inapp_channel()` içinde
`t.c.channel_type == "IN_APP"` koşulu gömülü.

**Bağımlılık:** Faz 2 (PostgreSQL testleri).

## Görev

1. **Kanal tipine göre yönlendirme.** `_deliver()` çağrılan adaptörü kanalın
   `channel_type` alanına göre seçsin. Bilinmeyen kanal tipi sessizce başarılı
   sayılmamalı — açık bir hata sınıfıyla başarısız olmalı.
2. **Adaptör protokolünü genelleştir.** `InAppChannelAdapter` protokolü artık tek kanal
   tipini temsil etmiyor; kanal-bağımsız bir adaptör sözleşmesine dönüştür. Mevcut
   `deliver(event, delivery) -> bool` imzasını koruyabilirsin, ama adlandırma gerçeği
   yansıtsın.
3. **E-posta (SMTP) adaptörü yaz.** Standart kütüphane `smtplib` yeterli — yeni bağımlılık
   ekleme. Kimlik bilgisi `secret_ref` üzerinden çözülecek, kanal yapılandırmasına
   düz metin parola yazılmayacak.
4. **Webhook adaptörü yaz.** HTTP POST. `httpx` şu anda yalnızca **test** bağımlılığı —
   üretim bağımlılığı eklemek yerine standart kütüphaneyi kullan veya `httpx`'i
   üretim bağımlılığına taşımayı gerekçelendir.
5. **Taşıyıcı hatalarını mevcut yeniden deneme mekanizmasına bağla.** Geçici hata
   (bağlantı hatası, 5xx, zaman aşımı) → yeniden denenebilir. Kalıcı hata
   (4xx, geçersiz adres) → `UNDELIVERABLE`, boşuna denenmesin. Hata sınıfı
   `last_error_class` alanına yazılacak.
6. **`get_active_inapp_channel` sabitini kaldır.** Kanal tipini parametre alan bir
   sorguya dönüştür veya çağrı yerlerini uygun şekilde genelleştir.
7. **Dış çağrılar için zaman aşımı ve güvenlik.** SMTP ve HTTP çağrılarında zorunlu
   zaman aşımı. Webhook hedefleri için iç ağa yönelmeyi (SSRF) engelleyecek bir
   kısıtlama tasarla ve gerekçesini yaz.

## Invariantlar

- **Sır saklanmayacak.** Kanal yapılandırması yalnızca `secret_ref` tutmaya devam edecek;
  gerçek sır çalışma anında salt-okunur mount'tan çözülecek
  (`DATA_QUALITY_LOCAL_SECRET_DIR` deseni).
- Mevcut durum makinesi ve geri çekilme tablosu değişmeyecek.
- Teslimat denemesi idempotent kalacak: aynı `delivery_id` iki kez işlenirse
  ikinci kez dış çağrı yapılmamalı.
- Bildirim içeriği kişisel veri sızdırmamalı — mevcut veri koruma/maskeleme
  konvansiyonlarına uy.
- Dış çağrılar testlerde gerçekten yapılmayacak; adaptörler enjekte edilebilir olacak.
- Yeni üçüncü parti bağımlılık, açık gerekçe olmadan eklenmeyecek.

## Kabul Kriterleri

1. `EMAIL` tipli bir kanal için teslimat SMTP adaptörünü çağırıyor — test (sahte SMTP).
2. `WEBHOOK` tipli bir kanal için teslimat HTTP adaptörünü çağırıyor — test (sahte istemci).
3. `IN_APP` davranışı değişmemiş — mevcut testler geçiyor.
4. Bilinmeyen kanal tipi açık bir hata üretiyor, sessizce başarılı sayılmıyor — test.
5. Geçici hata yeniden deneme planlıyor; kalıcı hata doğrudan `UNDELIVERABLE` yapıyor — test.
6. En fazla deneme sayısı aşıldığında `UNDELIVERABLE` + `MAX_RETRIES_EXCEEDED` —
   mevcut davranış korunuyor.
7. Dış çağrılarda zaman aşımı tanımlı — test.
8. Kanal yapılandırmasında düz metin sır bulunmadığı doğrulanmış.
9. `python -m pytest` tamamen yeşil.

## Teslim Formatı

- **Kod:** Değiştirilen/eklenen dosyalar ve gerekçesi.
- **Tasarım kararı:** Adaptör yönlendirme yaklaşımı, HTTP istemcisi seçimi ve
  SSRF kısıtlaması, gerekçeleriyle.
- **Testler:** Kabul kriterlerinin her birini karşılayan test adları.
- **Test çıktısı:** Ham `pytest` sonucu.
- **Güvenlik notu:** Sır çözümleme yolu ve dış çağrı kısıtlamaları.
- **Varsayımlar:** Yapılan varsayımlar ve açık kalan sorular.

## Çalışma Kuralları

- Mevcut kod stiline uy (Türkçe docstring, `Protocol` tabanlı sözleşmeler,
  frozen dataclass).
- Testlerde gerçek ağ çağrısı yapma.
- Testleri çalıştır ve sonucu olduğu gibi bildir.
- Belirsizlik varsa varsayımını açıkça yaz ve devam et.

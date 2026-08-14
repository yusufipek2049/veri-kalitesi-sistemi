# Incident Response arşiv kararı

Faz 9 incelemesinde bu uygulama, bankacılık olay/kişisel veri ihlali değerlendirme
niyetine rağmen çalıştırılabilir sisteme bağlanmaya hazır bulunmadı:

- kalıcılık yalnız süreç-içi `SQLiteIncidentResponseRepository` ile sağlanıyor;
- üretim PostgreSQL migration'ı ve repository adaptörü yok;
- güvenilir politika sağlayıcısı composition root'ta yok;
- `external_notification_dispatched` alanı repository tarafından daima `false`
  yazılıyor; yani kod dış bildirim sürecini gerçekleştirmiyor.

Bu eksikler yalnız bir HTTP/CLI yüzeyi eklenerek giderilemeyeceği ve Faz 9 yeni
yetenek icat etmediği için kaynaklar silinmeden buraya taşındı. İlgili test
`archive/tests/incident_response/test_incident_response.py` altındadır.

## Geri getirme yolu

Kod ancak PostgreSQL şeması/repository'si, güvenilir politika bileşimi ve dış
bildirim portunun davranış sözleşmesi ayrı bir fazda tanımlandıktan sonra
`src/veri_kalitesi/incident_response/` altına geri taşınmalıdır. Test de aynı
değişiklikte `tests/unit/` altına alınmalı ve production composition üzerinden
uçtan uca doğrulanmalıdır.

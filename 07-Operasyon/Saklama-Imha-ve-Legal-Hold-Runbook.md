# Saklama, İmha ve Legal Hold Runbook

1. Politika sürümünü ve kayıt türünü doğrula.
2. Legal hold kontrolü yap.
3. İmha kapsamını dry-run ile üret.
4. Yetki ve gerekiyorsa maker-checker onayı al.
5. İdempotent imha işini çalıştır.
6. Sonuç sayacı ve başarısız kayıtları audit et.
7. Ham silinen değeri audit veya rapora yazma.
8. Geri çağırma/itiraz süresi varsa iş akışını kapatma.

## İterasyon 25A Teknik Sınırı

- Dry-run, sürümlü kayıt sınıfı politikasından takvimsel saklama sonunu hesaplar.
- Aktif legal hold veya çözümlenemeyen hold durumu otomatik imhayı engeller.
- `ComplianceReviewRequired` politika süresi dolsa bile imha yetkisi üretmez.
- Bu aşamada fiziksel silme, anonimleştirme, arşivleme veya geri çağırma çalıştırılmaz.

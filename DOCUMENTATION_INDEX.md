# Dokümantasyon İndeksi

| Doküman | Amaç | Kanonik içerik | Bağlantılar | Güncellik | Sorumluluk alanı |
| --- | --- | --- | --- | --- | --- |
| [README](README.md) | Başlangıç ve kısa durum | Proje özeti, ana yönlendirme | Tüm indeksler | Aktif | Proje |
| [Ajan Rol Yapılandırması](.agent/config/agents.yaml) | Rol → ajan eşlemesi | Mimar/reviewer/uygulayıcı/testçi dağıtımı ve yedek politikası | talimat, ajan mimarisi | Kanonik | Depo yönetişimi |
| [Mevcut Durum](00-Proje-Hafizasi/Mevcut-Durum.md) | Uygulama durumu | Uygulanan/kısmi/açık alanlar | İndeks, backlog, next step | Aktif | Proje durumu |
| [Ürün Yetenek Durum Matrisi](00-Proje-Hafizasi/Urun-Yetenek-Durum-Matrisi.md) | Özellik kapsamı | Kullanıcı özellik listesi için SRS/runtime/boşluk karşılaştırması | SRS, karar kayıtları, backend/frontend | Aktif | Ürün durumu |
| [NEXT_STEP](NEXT_STEP.md) | Son tamamlanan çalışma paketi ve sıradaki durum | DQ-CAP-PROTOTYPE-05 commit edildi; modüller composition'a bağlı değil, bağımsız review `CHANGES_REQUESTED`; production-ready değil | İterasyon, backlog, test | Aktif | Teslimat |
| [Sonraki Adımlar](00-Proje-Hafizasi/Sonraki-Adimlar.md) | Backlog | Öncelik, durum ve çıkış kriteri | NEXT_STEP, yol haritası | Aktif | Teslimat |
| [SRS](01-SRS/SRS-INDEX.md) | Gereksinim ve kabul | BR/FR/UC/RULE/NFR/AC/TS | Mimari, veri modeli, test | Kanonik | Ürün/analiz |
| [Mimari](02-Mimari/MIMARI-INDEX.md) | Mimari yapı | Bileşen, veri akışı ve güvenlik sınırı | ADR, SRS | Kanonik | Mimari |
| [ADR](02-Mimari/Mimari-Kararlar.md) | Kesin mimari karar | ADR durumları ve sonuçları | Karar kayıtları | Kanonik | Mimari |
| [Alınan Kararlar](00-Proje-Hafizasi/Alinan-Kararlar.md) | Karar ailesi indeksi | Kesin karar kayıtlarına yönlendirme | Karar-Kayitlari | Kanonik | Karar yönetişimi |
| [Açık Konular](00-Proje-Hafizasi/Acik-Konular.md) | İnsan kararı gerekenler | Açık/bekleyen kararlar | SRS/uyum/operasyon | Kanonik | Karar sahipleri |
| [Backend](03-Backend/BACKEND-INDEX.md) | Kod haritası | Modül ve runtime durumu | SRS/test/iterasyon | Aktif | Backend |
| [Frontend](04-Frontend/FRONTEND-INDEX.md) | Ekran haritası | Route, teknoloji ve yazma durumu | Tasarım/test | Aktif | Frontend |
| [Veritabanı](05-Veritabani/VERITABANI-INDEX.md) | Fiziksel model/geçiş | Migration, repository, cutover durumu | SRS veri modeli | Aktif | Veri mimarisi |
| [Test](06-Testler/TEST-INDEX.md) | Test stratejisi | Kabul kapsamı ve aktif doğrulama açıkları | SRS/kanıt | Aktif | Kalite |
| [Operasyon](07-Operasyon/OPERASYON-INDEX.md) | Runbook haritası | Operasyon, entegrasyon ve DR | Uyum/kararlar | Aktif | Operasyon |
| [Uyum Kanıtları](08-Uyum-Kanitlari/KANIT-INDEX.md) | Teknik kanıt kataloğu | Test/kanıt paketleri | SRS/iterasyon | Aktif/tarihsel | Uyum |
| [Aktif İterasyonlar](09-Iterasyonlar/ITERASYON-INDEX.md) | Son yedi kayıt | Güncel teslimat artımları | Arşiv, next step | Aktif | Teslimat |
| [İterasyon Arşivi](archive/iterations/README.md) | Eski iterasyon geçmişi | Tarihsel kapanış ve gerekçe | Kanonik aktif belgeler | Arşiv | İzlenebilirlik |
| [Dokümantasyon Denetimi](DOCUMENTATION_AUDIT.md) | Konsolidasyon sonucu | Taşıma, tutarlılık ve doğrulama bulguları | Tüm depo | 2026-07-29 | Dokümantasyon |

## Kullanım Kuralı

Güncel görev için README → Mevcut Durum → NEXT_STEP/ilgili kanonik indeks
sırasını kullan. `archive/` ve `docs/archive/` yalnız tarihsel karşılaştırma veya
kanıt gerektiğinde açılır; backlog ve güncel karar kaynağı değildir.

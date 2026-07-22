---
type: frontend-screen-contract
status: target-design
project: Veri Kalitesi İzleme ve Skorlama Sistemi
screen: evidence-backed-incident
last_updated: 2026-07-22
tags: [frontend, incident, evidence, decision-support]
---

# Kanıtlı Olay İnceleme Ekran Sözleşmesi

## Sınır

Bu ikinci faz sözleşmesi `FR-097–FR-111`, `UC-018–UC-020`,
`AC/TS-057–069/071` ve
[kanonik mimari](../../02-Mimari/Kanita-Dayali-Karar-Sistemi.md) ile uygulanır.
Mevcut frontend runtime'ında bu ekran yoktur. API alanları uygulanmadan fixture
dışında üretim sözleşmesi tahmin edilmez.

## Sekmeler

| Sekme | İçerik | Yetki/koruma |
| --- | --- | --- |
| Özet | Olay, kullanım kararı, etki, sahiplik, durum | Olay ve dataset scope'u |
| Skor Kırılımı | Ham/nihai skor, boyut/ağırlık, kural katkısı, bloke/atlanan kural | Skor görüntüleme |
| Metrikler | Sayaç, oran, eşik, sapma, partition ve süre | Metrik kanıtı görüntüleme |
| Hatalı Kayıtlar | Fingerprint, maskeli örnek, beklenen koşul, ilk/son görülme | Maskeli/gerçek kayıt izinleri ayrı |
| Hesaplama | Formül, kaynak türü, hash, parametre özeti ve sürüm | Formül ile kaynak SQL izni ayrı |
| Lineage | Tablo/kolon, dönüşüm, pipeline, downstream varlıklar | Lineage scope'u ve sınıflandırma |
| Kök Neden | Teşhis, hipotez, karşı kanıt, güven ve nedensellik sınıfı | Teşhis görüntüleme |
| Öneriler | Mekanizma, dayanak, güven, risk, onay ve durum | Öneri oluşturma/onaylama ayrı |
| Çalıştırmalar | Run manifestleri, reproduction ve karşılaştırma | Reproduction izni |
| Değişiklikler | Data/rule/policy/measurement drift ve deploy olayları | Değişiklik scope'u |
| Zaman Çizelgesi | Yükleme, anomali, bildirim, karar, düzeltme ve kapanış | Veri-minimum olay projeksiyonu |
| Kanıt ve Denetim | Bağlı/doğrulanmış/eksik kanıt, güç, kaynak, son güncelleme | Kanıt/paket/indirme izinleri ayrı |

## Görünüm Kuralları

- Skor, ölçüm güveni, teşhis güveni, öneri güveni ve kanıt gücü ayrı gösterilir.
- `Unknown`, `Incomplete`, `Unverified`, teknik hata ve erişim reddi `0` veya
  başarısız kalite skoru gibi gösterilmez.
- Korelasyon yalnız kendi nedensellik etiketiyle sunulur.
- Tahmini etki “Tahmin” etiketi, kaynak, formül ve güven olmadan gösterilmez.
- Sonuçtan kural, run, lineage düğümü, olay ve kanıta gezilebilir bağlantı verilir.
- Gerçek müşteri verisi, gizli parametre veya kaynak SQL varsayılan görünümde
  açılmaz; maskeleme ve DLP kısıtları backend yanıtından uygulanır.
- Kanıt paneli bağlı/doğrulanmış/eksik kanıt sayıları, kanıt gücü, kaynaklar,
  son güncelleme ve ayrı güven değerlerini gösterir.
- Uzun listeler sayfalı veya sanal; grafikler erişilebilir tablo karşılıklı olur.
- Loading, empty, teknik hata, eksik kanıt, yetkisiz ve uzun içerik durumları
  Storybook ve Playwright kapsamına alınır.

## Eylemler

| Eylem | Ön koşul | Sonuç |
| --- | --- | --- |
| Reproduction başlat | Yetki ve eksiksiz manifest/snapshot | Asenkron, idempotent yeni run |
| Öneri oluştur | Teşhis ve minimum kanıt politikası | Mekanizma/sürüm bağlı taslak |
| Öneriyi onayla/reddet | Önerenden farklı yetkili aktör | Auditli karar |
| Remediation dry-run | Politika, etki ve rollback planı | Üretimi değiştirmeyen sonuç |
| Canary/rollback | Sürüm onaylı remediation politikasında açıkça izinli sistem eylemi | Aşamalı, auditli durum geçişi |
| Kanıt paketi üret/indir | Paket, DLP, saklama ve dışa aktarma izni | Asenkron iş ve audit kaydı |

UI eylemi yetki kanıtı üretmez. Backend 401/403/fail-closed davranışı zorunludur.

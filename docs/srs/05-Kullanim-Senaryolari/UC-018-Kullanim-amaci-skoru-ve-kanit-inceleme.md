---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_section: "UC-018"
created_at: 2026-07-22
tags: [srs, uc, uc-018, evidence]
---

# UC-018 — Kullanım amacı skoru ve kanıt inceleme

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-018** |
| Amaç | Bir datasetin belirli kullanım amacı için uygunluğunu ve bu kararın kanıtlarını incelemek. |
| Birincil Aktör | Data Owner; Data Steward |
| İkincil Aktörler | Denetçi; Veri Yönetişimi; Risk Yönetimi |
| Öncelik | Should — ikinci faz |
| Tetikleyici | Kullanıcı skor veya kalite olayı detayını açar. |
| Ön Koşullar | Güvenilir aktör/scope; onaylı kullanım profili; skor ve kanıt referansları. |

**Temel Akış**

1. Kullanıcı dataset ve kullanım amacı profilini seçer.
2. Sistem ham/nihai kalite, yeterlilik, kullanım, güven ve etkiyi ayrı gösterir.
3. Kullanıcı boyut, kural, metrik, manifest ve maskeli örnek kanıtına iner.
4. Sistem formül, eşik/ağırlık/politika ve tüm sürüm kaynaklarını gösterir.
5. Kullanıcı lineage, değişiklik olayları, teşhis ve kalite borcunu inceler.
6. Sistem eksik/eskimiş kanıtları ve ayrı güven türlerini görünür tutar.
7. Yetkili kullanıcı reproduction veya kanıt paketi işi başlatabilir.

**İstisna Akışları**

1. Profil/politika yoksa kullanım kararı `Undetermined` olur.
2. Kanıt eksikse sonuç tamamlanmış gibi sunulmaz.
3. Hassas kanıtta scope/sınıflandırma yoksa erişim auditli biçimde reddedilir.
4. Snapshot veya sürüm eksikse reproduction başlamaz.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-007, RULE-009, RULE-018–RULE-022 |
| Son Koşullar | Görüntüleme/reproduction talebi auditlenir; geçmiş sonuç değişmez. |
| Minimum Garanti | Yetkisiz veri açılmaz; kanıt/güven eksikliği gizlenmez. |
| İlgili Fonksiyonel Gereksinimler | FR-097–FR-100, FR-102–FR-104, FR-107–FR-109, FR-111 |
| Kabul Kriterleri | AC-057–AC-060, AC-062–AC-064, AC-067–AC-069, AC-071 |

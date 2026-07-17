---
type: architecture
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "2.1"
generated_at: 2026-07-16
tags:
  - architecture
  - context
---

# Sistem Bağlamı


Sistem, operasyonel veritabanları, veri ambarı, veri gölü, dosya depoları ve REST servislerinden metadata ve kalite ölçüm sonuçları toplar. Kaynak sistemlerde veri değiştirmez; salt okunur erişimle sorgu ve örneklem gerçekleştirir. Sistem, LDAP üzerinden kullanıcı doğrular, sonuçları dashboard ve raporlarla sunar, kritik bulgular için sistem içi bildirim oluşturur ve gerektiğinde ServiceNow üzerinde ticket açar.

Metinsel bağlamda kullanıcılar web arayüzü veya API aracılığıyla sisteme erişir. Kural motoru veri kaynağı bağlayıcıları üzerinden kontrolleri çalıştırır. Skorlama motoru sonuçları birleştirir. Bildirim servisi kullanıcıları bilgilendirir. Audit altyapısı tüm kritik işlemleri kaydeder. Metadata kataloğu ve raporlama araçlarıyla entegrasyon ikinci fazda genişletilir.

### Sistem Bağlam Diyagramı

```mermaid
flowchart LR
    U[Kurumsal Kullanıcılar] -->|HTTPS| DQ[Veri Kalitesi İzleme ve Skorlama Sistemi]
    LDAP[LDAP Kimlik Servisi] -->|Kimlik doğrulama ve grup bilgisi| DQ
    DB[(Operasyonel Veritabanları)] -->|Salt okunur sorgu| DQ
    DW[(Veri Ambarı / Veri Gölü)] -->|Salt okunur sorgu| DQ
    FILE[CSV / Excel Dosyaları] -->|Güvenli dosya erişimi| DQ
    API[REST API Kaynakları] -->|HTTPS| DQ
    DQ -->|Sistem içi bildirim| U
    DQ -->|Ticket oluşturma / güncelleme| SN[ServiceNow]
    DQ -->|Rapor / skor API'si| BI[Raporlama Araçları]
    CAT[Metadata Kataloğu] <-->|Metadata senkronizasyonu| DQ
```

---
type: architecture
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "2.1"
created_at: 2026-07-16
tags:
  - architecture
  - context
---

# Sistem Bağlamı


Sistem, operasyonel veritabanları, veri ambarı, veri gölü, dosya depoları ve REST servislerinden metadata ve kalite ölçüm sonuçları toplar. Kaynak sistemlerde veri değiştirmez; salt okunur erişimle sorgu ve örneklem gerçekleştirir. Kullanıcılar LDAP destekli kurumsal IdP/SSO üzerinden OIDC veya SAML ve zorunlu MFA ile doğrulanır. Sistem sonuçları dashboard ve raporlarla sunar, kritik bulgular için sistem içi bildirim oluşturur ve ara entegrasyon katmanı üzerinden ServiceNow ticket akışını yürütür.

Metinsel bağlamda kullanıcılar web arayüzü veya API aracılığıyla sisteme erişir. Kural motoru bağlayıcı ve kaynak kullanım politikaları üzerinden kontrolleri çalıştırır. Skorlama motoru ham ve kritik kontrol etkili nihai kalite skorunu üretir; ölçüm yeterliliği kapısı kapsam, güven, güncellik, teknik başarı ve kanıt koşullarını ayrı değerlendirerek kullanım kararını verir. Resmî ve provizyonel sonuçlar bu kapıda ayrılır. Audit altyapısı kritik işlemlerde fail-closed, rutin olaylarda dayanıklı outbox uygular. Kurumsal veri kataloğu veya DLP sistemi sınıflandırma ve kullanım kısıtlarının kaynağıdır.

### Sistem Bağlam Diyagramı

```mermaid
flowchart LR
    U[Kurumsal Kullanıcılar] -->|HTTPS| DQ[Veri Kalitesi İzleme ve Skorlama Sistemi]
    IDP[LDAP Destekli Kurumsal IdP / SSO] -->|OIDC veya SAML, MFA ve grup bilgisi| DQ
    DB[(Operasyonel Veritabanları)] -->|Salt okunur sorgu| DQ
    DW[(Veri Ambarı / Veri Gölü)] -->|Salt okunur sorgu| DQ
    FILE[CSV / Excel Dosyaları] -->|Güvenli dosya erişimi| DQ
    API[REST API Kaynakları] -->|HTTPS| DQ
    DQ -->|Sistem içi bildirim| U
    DQ -->|Dayanıklı outbound kayıt| INT[Ara Entegrasyon Katmanı]
    INT -->|Ticket oluşturma / güncelleme| SN[ServiceNow]
    DQ -->|Rapor / skor API'si| BI[Raporlama Araçları]
    CAT[Kurumsal Veri Kataloğu / DLP] -->|Sınıflandırma ve kısıtlar| DQ
```

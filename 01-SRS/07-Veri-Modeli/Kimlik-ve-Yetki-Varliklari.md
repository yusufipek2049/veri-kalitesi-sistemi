---
type: data-dictionary-group
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "User, Role, Permission"
created_at: 2026-07-16
tags:
  - srs
  - data-dictionary
  - identity
---

# Kimlik ve Yetki Varlıkları

## User

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| user_id | UUID | 36 | Evet | Evet | Otomatik | Yerel kullanıcı anahtarı | Hayır | Geçerli UUID |
| ldap_username | VARCHAR | 128 | Evet | Evet | Yok | LDAP kullanıcı adı | Kişisel | LDAP biçimine uygun; normalize edilmiş |
| display_name | VARCHAR | 200 | Evet | Hayır | Yok | Görünen ad | Kişisel | Kontrol karakteri içermez |
| email | VARCHAR | 254 | Hayır | Hayır | NULL | Kurumsal e-posta; bildirim kanalı olarak kullanılmaz | Kişisel | Geçerli kurumsal format |
| status | ENUM | 20 | Evet | Hayır | ACTIVE | ACTIVE/PASSIVE/LOCKED | Hayır | İzinli enum |
| last_login_at | TIMESTAMP | TBD | Hayır | Hayır | NULL | Son başarılı giriş UTC | Kişisel | Gelecek tarih olamaz |

## Role

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| role_id | UUID | 36 | Evet | Evet | Otomatik | Rol anahtarı | Hayır | Geçerli UUID |
| role_code | VARCHAR | 80 | Evet | Evet | Yok | Makinece okunur rol kodu | Hayır | Büyük harf/alt çizgi |
| role_name | VARCHAR | 150 | Evet | Hayır | Yok | Rol adı | Hayır | 1–150 karakter |
| description | VARCHAR | 500 | Evet | Hayır | Yok | Rol açıklaması | Hayır | HTML temizlenir |
| is_active | BOOLEAN | 1 | Evet | Hayır | TRUE | Rol etkinliği | Hayır | Boolean |

## Permission

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| permission_id | UUID | 36 | Evet | Evet | Otomatik | İzin anahtarı | Hayır | UUID |
| permission_code | VARCHAR | 120 | Evet | Evet | Yok | RESOURCE.ACTION biçimli izin | Hayır | Tanımlı sözlükte bulunur |
| scope_type | ENUM | 30 | Evet | Hayır | GLOBAL | GLOBAL/DOMAIN/SOURCE/DATASET | Hayır | İzinli enum |
| description | VARCHAR | 500 | Evet | Hayır | Yok | İzin açıklaması | Hayır | HTML temizlenir |

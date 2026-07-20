# Sürüm ve Değişiklik Yönetimi

Üretim adayı için:

- izlenebilir gereksinim ve kontrol ID'leri
- kod inceleme
- test sonuçları
- güvenlik taramaları
- migration ve geri alma
- yapılandırma farkı
- SBOM/artifact özeti
- iş, mimari ve güvenlik onayları
- açık risk kabulü
- dağıtım ve doğrulama kanıtı

Codex banka onaylarını varsayamaz.

## Yerel Secret Kontrolü

Üretim adayı hazırlanmadan önce yerel veri-minimum kontrol aşağıdaki komutla
çalıştırılabilir:

```bash
PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc .
```

- `0`: tarama tamamlandı ve bulgu yok.
- `1`: en az bir bulgu var; çıktı yalnız konum ve kural kodu içerir.
- `2`: tarama tamamlanamadı; bu sonuç temiz tarama kabul edilmez.

Bulgu değeri, satır içeriği veya ham teknik hata kanıt dosyasına ve loga yazılmaz.
Kurumsal CI/CD ürünü, kritik eşik ve istisna/onay akışı banka bilgi güvenliği
kararıyla ayrıca belirlenir.

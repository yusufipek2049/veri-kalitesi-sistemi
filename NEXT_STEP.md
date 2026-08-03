---
type: next-step
status: active
updated_at: 2026-08-03
work_package: MAINT-04
predecessor: MAINT-03
---

# Sıradaki Adım — Kaynaksız Kanıt Ömrü Eşiğinin Sürümlü Politikaya Bağlanması

MAINT-02, `lab_gate.py` içindeki kanıt tazelik sabitini kaldırıp
`max_evidence_age_seconds` zorunlu parametre olarak composition köküne taşımıştır;
ancak değerin kendisi (`3600`) hâlâ `adapters.py` composition kökünde koddadır ve
kanonik kaynaktan yoksundur. `DQ-CAP-009` ve ADR-018 gereği bu değer artık yalnız
sürümlü politika kaydından gelmelidir.

## Sorun

Kanıt ömrü eşiği ürüne özgü bir sayısal değerdir ve ortama göre değişebilir. Kod
içinde sabitlenmesi ADR-018 (sürümlü politika zorunluluğu) ile çelişir: politika
kayıdı yoksa sistem örtük varsayılan kullanmamalı, işlemi fail-closed reddetmelidir.

## Kapsam

- `adapters.py` composition kökündeki `max_evidence_age_seconds=3600` sabiti,
  sürümlü politika kaydından veya lab yapılandırmasından çözülecek biçimde
  bağlanır; kod içi sabit kaldırılır.
- Değerin kaynağı denetlenebilir olmalıdır.
- Standart, geriye dönük olarak kapanmış paketleri yeniden açmaz.

## Kabul Kriterleri

| ID | Gereksinim |
| --- | --- |
| AC-01 | `max_evidence_age_seconds` değeri kod içi sabit olmaktan çıkar ve sürümlü politika/lab yapılandırmasından çözülür. |
| AC-02 | Politika kaydı yoksa ilgili işlem fail-closed reddedilir; örtük varsayılan kullanılmaz. |
| AC-03 | Değişen davranış için test eklenir/güncellenir. |
| AC-04 | Birim test paketi exit 0 ile tamamlanır. |
| AC-05 | Görevle ilgisiz repository değişikliği yapılmaz. |

## Sınırlar

Bu paket yalnız kanıt ömrü eşiğinin kaynağını kapsar. Yeni ürün yeteneği ve diğer
kaynaksız değerler kapsam dışıdır.

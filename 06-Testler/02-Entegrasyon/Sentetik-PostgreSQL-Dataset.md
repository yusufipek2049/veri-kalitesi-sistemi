# Sentetik PostgreSQL İlişkisel Dataset

## Amaç ve Sınır

Bu dataset yalnız yerel geliştirme ve test için, tamamen yapay verilerle
`FR-089`–`FR-095`, `UC-017`, `RULE-016/017` ve `AC/TS-048`–`AC/TS-056`
alt kapsamlarını doğrular. Gerçek, anonimleştirilmiş veya üretimden türetilmiş
veri içermez; `OPEN-014` kapsamındaki 20 milyon satırlık nihai performans kabulü
yerine geçmez.

Kaynak tabloları `synthetic_source`, run/ground-truth/ölçüm kayıtları
`synthetic_control` şemasındadır. Kontrollü referans kusurlarını saklayabilmek
için kaynak tablolarında fiziksel foreign key yoktur; beklenen ilişkiler sürümlü
tablo tanımında ve bağımsız SQL oracle'ında doğrulanır.

## Dataset Kataloğu

Tüm tablolar `seed=2026`, `scenario=mixed-quality` ve 19.000 satırla üretildi.

| Tablo | Amaç | Satır | Birincil anahtar | İlişki alanları |
| --- | --- | ---: | --- | --- |
| `synthetic_customers` | Müşteri ana kayıtları | 19.000 | `customer_id` | Yok |
| `synthetic_customer_contacts` | İletişim kayıtları | 19.000 | `contact_id` | `customer_id` |
| `synthetic_customer_addresses` | Adres kayıtları | 19.000 | `address_id` | `customer_id` |
| `synthetic_accounts` | Mevduat ve ödeme hesapları | 19.000 | `account_id` | `customer_id` |
| `synthetic_account_balances` | Bakiye anlık görüntüleri | 19.000 | `balance_id` | `account_id` |
| `synthetic_transactions` | Hesap işlemleri | 19.000 | `transaction_row_id` | `account_id` |
| `synthetic_cards` | Banka ve kredi kartları | 19.000 | `card_id` | `customer_id`, `account_id` |
| `synthetic_card_transactions` | Kart işlemleri | 19.000 | `card_transaction_id` | `card_id`, `merchant_id` |
| `synthetic_loans` | Kredi sözleşmeleri | 19.000 | `loan_id` | `customer_id` |
| `synthetic_loan_installments` | Kredi ödeme planları | 19.000 | `installment_id` | `loan_id` |
| `synthetic_payments` | Hesap, işlem ve taksit ödemeleri | 19.000 | `payment_id` | `account_id`, `transaction_row_id`, `installment_id` |
| `synthetic_beneficiaries` | Kayıtlı transfer alıcıları | 19.000 | `beneficiary_id` | `customer_id`, `account_id` |
| `synthetic_merchants` | Üye işyeri ana kayıtları | 19.000 | `merchant_id` | Yok |
| `synthetic_merchant_transactions` | Üye işyeri mutabakat işlemleri | 19.000 | `merchant_transaction_id` | `merchant_id`, `card_transaction_id` |
| `synthetic_customer_risk_profiles` | Müşteri risk değerlendirmeleri | 19.000 | `risk_profile_id` | `customer_id` |
| `synthetic_service_requests` | Müşteri hizmet talepleri | 19.000 | `service_request_id` | `customer_id`, `account_id`, `card_id`, `loan_id` |
| `synthetic_data_events` | Veri işleme ve kalite olayları | 19.000 | `data_event_id` | `customer_id`, `account_id`, `transaction_row_id`, `card_id`, `loan_id` |

Her tablo, kendi domain alanlarına ek olarak zorunluluk, geçerlilik aralığı,
olay/güncelleme/ingestion zamanı ve `synthetic_origin` kontrol alanlarını taşır.
Kimlikler sentetik öneklerle üretilir; serbest metinlerde kişi, kurum veya üretim
sistemine ait gerçek değer kullanılmaz.

## Alan Sözlüğü ve Dağılımlar

Her tabloda birincil anahtar ve ilişki alanlarına ek olarak şu rol grupları
bulunur:

| Alan rolü | Örnekler | Anlam |
| --- | --- | --- |
| İş anahtarı | `customer_number`, `account_number`, `transaction_id` | Duplicate ve uniqueness kontrolü için sentetik iş kimliği |
| Açıklama | `full_name`, `account_name`, `transaction_description` | Eksik/boş metin kontrollerinin hedefi |
| Biçimli değer | `email_address`, `iban_code`, `masked_pan`, `currency_code` | Biçim ve domain geçerlilik kontrollerinin hedefi |
| Durum | `customer_status`, `account_status`, `event_status` | Çarpık aktif/pasif/kapalı dağılımı ve tutarlılık hedefi |
| Sayısal ölçü | `activity_score`, `current_balance`, `transaction_amount`, `lag_seconds` | Log-normal uzun kuyruk ve outlier hedefi |
| Ortak kalite alanları | `required_value`, `effective_from`, `effective_to` | Tamlık ve dönem tutarlılığı |
| Zaman alanları | `event_time`, `updated_at`, `ingestion_time` | Güncellik, eskilik ve ingestion sırası |
| Köken | `synthetic_origin` | Kaydın tamamen yapay olduğunu gösteren sabit işaret |

Kategorik durumlar eşit değil çarpık dağıtılır. İlişkili kayıt seçimi yoğun,
orta ve düşük aktivite segmentleri oluşturur. Sayısal ölçüler deterministik
log-normal uzun kuyruk kullanır. Olay tarihleri son 180 güne dağılır ve dönemsel
yoğunlaşma içerir. Biçimli alanlarda yaygın ve nadir fakat geçerli sentetik
değerler birlikte bulunur.

## Önerilen Şemadan Sapmalar

- `synthetic_beneficiaries`, önerideki doğrudan transaction ilişkisi yerine
  müşteri ve hesapla ilişkilidir. Mevcut projede alıcıyı işlemle bağlayan onaylı
  transfer sözleşmesi bulunmadığı için yeni bir iş ilişkisi uydurulmadı.
- Üst varlıkların çocuk ilişkileri ters yöndeki ilişki kolonlarıyla kurulur;
  örneğin müşteride hesap listesi tutulmaz, hesap `customer_id` taşır.
- Kasıtlı referans kusurları fiziksel foreign key yerine raw-source ilişki
  sözleşmesi ve ayrı ground truth ile temsil edilir. Uygulama operasyon
  tablolarının bütünlük kontrolleri değiştirilmedi.

## Kusur ve Ground Truth

`mixed-quality` senaryosu eksik değer, boş metin, duplicate, biçim, domain,
tutarlılık, referans bütünlüğü, eskilik ve outlier kusurlarını kontrollü biçimde
birlikte enjekte eder. Aynı kayıtta birden fazla kusur bulunabilir. Ground truth,
kaynak kaydından ayrı `defect_manifest` tablosunda tablo, kayıt, alan, boyut,
kusur türü, beklenen sonuç ve önem düzeyiyle saklanır.

Bağımsız SQL oracle'ı üreticinin doğrulama sonucunu kullanmadan kaynak tabloları
yeniden sorgular ve beklenen/tespit edilen kümelerden TP, FP, FN, precision ve
recall üretir. Bu oracle sentetik üreticinin bütünlüğünü doğrular; uygulamanın
genel kural motorunun bu dataset üzerinde çalıştırıldığı anlamına gelmez.

| Kusur türü | Beklenen | Tespit edilen | FP | FN |
| --- | ---: | ---: | ---: | ---: |
| Eksik değer | 9.764 | 9.764 | 0 | 0 |
| Boş metin | 3.287 | 3.287 | 0 | 0 |
| Duplicate | 6.544 | 6.544 | 0 | 0 |
| Geçersiz biçim | 8.074 | 8.074 | 0 | 0 |
| Geçersiz domain | 4.852 | 4.852 | 0 | 0 |
| Tutarlılık | 8.125 | 8.125 | 0 | 0 |
| Referans bütünlüğü | 4.316 | 4.316 | 0 | 0 |
| Eski kayıt | 11.471 | 11.471 | 0 | 0 |
| Outlier | 6.589 | 6.589 | 0 | 0 |

## Çalıştırma

Parola yalnız süreç ortamından sağlanır; komut geçmişine veya depoya gerçek
secret yazılmaz. CLI yalnız `local`, `development` veya `test` ortamında, açık
`--allow-test-data` onayıyla ve izinli test veritabanı adlarında çalışır.

```bash
PGHOST=localhost PGPORT=5433 PGDATABASE=data_quality PGUSER=postgres \
PGPASSWORD='<yerel-secret>' PYTHONPATH=03-Backend/src \
python3 scripts/generate_synthetic_test_data.py \
  --environment test --allow-test-data --seed 2026 \
  --scenario mixed-quality --row-count 19000 --reset
```

```bash
PGHOST=localhost PGPORT=5433 PGDATABASE=data_quality PGUSER=postgres \
PGPASSWORD='<yerel-secret>' PYTHONPATH=03-Backend/src \
python3 scripts/reset_synthetic_test_data.py \
  --environment test --allow-test-data
```

Reset yalnız `synthetic_source` ve `synthetic_control` şemalarını kaldırır.
İkinci üretim açık reset olmadan reddedilir. Desteklenen teknik senaryolar:
`clean-baseline`, `mixed-quality`, `high-defect`, `stale-data`,
`duplicate-heavy` ve `referential-integrity`.

## Gerçek Çalışma Sonucu

| Ölçüm | Sonuç |
| --- | ---: |
| Run | `SYN-RUN-EFD934BB251EEEB6F3B55A7A` |
| Tablo / toplam satır | 17 / 323.000 |
| Tablo başına kusurlu kayıt oranı | %17,55–%18,26 |
| Toplam ground-truth kusuru | 63.022 |
| Üretim süresi | 51,03 saniye |
| Profil süresi | 0,345 saniye |
| Bağımsız doğrulama süresi | 0,451 saniye |
| Tepe bellek | 129.933.312 bayt |
| Veritabanı boyutu | 190.045.207 bayt |
| Kanonik SHA-256 | `4e5b7e13adbf0afc1ca271bbbba17aa3832c060903267cb02516991a0ecc3e01` |

## Açık Sınırlar

- Yalnız `mixed-quality` gerçek PostgreSQL üzerinde ölçüldü; diğer senaryoların
  deterministik seçim ve güvenlik kapıları birim testleriyle doğrulandı.
- Kusur alt türleri kaba teknik sınıflardır; exact/normalize duplicate,
  late-ingestion ve inactive-reference gibi ayrı iş alt türleri henüz yoktur.
- Uygulamanın metadata/profil ve kural yürütme adaptörleri bu veriyle uçtan uca
  koşturulmadı.
- Dataset yerel/test amaçlıdır; üretim kabulü, anonimlik, mevzuat uygunluğu veya
  banka onayı kanıtı değildir.

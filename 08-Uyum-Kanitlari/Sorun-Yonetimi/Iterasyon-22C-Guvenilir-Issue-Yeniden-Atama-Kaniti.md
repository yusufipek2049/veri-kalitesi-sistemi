---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
  - BFR-DATA-003
  - CTRL-KVKK-SEC-001
requirement_ids:
  - FR-065
  - FR-070
  - UC-013
  - AC-017
  - NFR-REL-006
  - NFR-SEC-001
  - NFR-SEC-005
  - NFR-SEC-008
status: TechnicallyVerified
version: iteration-22c-local
executed_at: 2026-07-17
---

# İterasyon 22C Güvenilir Issue Yeniden Atama Kanıtı

## Değişiklik

- İterasyon: 22C - güvenilir kullanıcı diziniyle issue yeniden atama, öncelik, geçmiş, audit ve sistem içi bildirim
- Commit/Artifact: Git deposu bulunmadığı için commit yok; yerel çalışma ağacı
- Bileşen: `veri_kalitesi.issues`, `veri_kalitesi.notifications`, `veri_kalitesi.audit`, `veri_kalitesi.identity`
- Kontrol/Gereksinim: FR-065, FR-070, UC-013, AC-017, NFR-REL-006, NFR-SEC-001/005/008 ve BFR-IAM-001/002, BFR-DATA-003 alt kapsamı

## Doğrulama

- Komut: `PYTHONPATH=03-Backend/src pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek içi SQLite ve sentetik UUID referansları
- Sentetik veri seti: Yetkili Data Steward, aktif/pasif ve kapsam içi/dışı atanan profilleri, servis/ayrıcalıklı/rolesiz/scope dışı context, dizin/audit/bildirim arızaları
- Beklenen: Yalnız yetkili ve issue kapsamındaki Data Steward güvenilir dizindeki aktif kapsam içi kullanıcıya atama yapar; durum `ASSIGNED`, geçmiş/audit ve yeni atanana sistem içi bildirim oluşur.
- Gerçekleşen: 318 test geçti. Issue hedef grubu 36 testle geçti; 12 yeni test eklendi.
- Sonuç: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Değişen Python dosyalarında `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- Hassas anahtar sözcük taraması yalnız iki sentetik negatif test girdisini buldu; bunlar hata redaksiyonunu doğrular ve kalıcı çıktıda yer almaz.
- Tam depo format kontrolü, bu iterasyonda değişmeyen dört eski dosyanın mevcut format farkları nedeniyle PASS değildir.

## Güvenlik

- Güven sınırı: Atama güvenilir, geçerli, normal kullanıcı `ActorContext` ve `DATA_STEWARD`/`DATA_GOVERNANCE_SPECIALIST` rolüne dayanır. Serbest actor, rol veya scope yetki kanıtı değildir.
- Atanan doğrulaması: Hedef kullanıcının kimliği, aktifliği ve dataset/source kapsamı enjekte edilen güvenilir dizin profilinden gelir; pasif, bulunamayan ve kapsam dışı kullanıcı reddedilir.
- Yetki: Eksik context, servis hesabı, ayrıcalıklı kullanıcı, rolesiz kullanıcı ve issue scope'u dışındaki kullanıcı repository yazımından önce fail-closed reddedilir.
- Atomiklik: Atanan, öncelik, durum, eski/yeni değerli issue geçmişi ve redakte audit outbox aynı SQLite transaction'ındadır; stage arızası tüm atamayı rollback eder.
- Audit ve veri minimizasyonu: Audit allowlist'i yalnız durum ve önceliği tutar. Atanan kimliği, scope ve session açık değeri audit özetine girmez; bildirim sabit veri-minimum şablon kullanır.
- Bildirim: Yerel atama commitinden sonra güvenilir servis context'iyle `ISSUE_ASSIGNED` olayı üretilir ve alıcı değişmez atama geçmişi kaydından çözülür. Bildirim arızasında yerel atama korunur ve hata sınıflandırılır.
- Teknik hata ayrımı: Dizin veya depo arızası redakte teknik hata; pasif/kapsam dışı kullanıcı domain atama hatasıdır.
- Maker-checker etkisi: Atama bir kritik konfigürasyon aktivasyonu veya onay kararı değildir; bu nedenle maker-checker eklenmedi. Rol/scope ve audit kontrolleri zorunludur.
- Geri alma: Manuel atama çağrı yolu pasifleştirilip önceki issue servis sürümüne dönülebilir. Ek geçmiş kolonları nüllable ve geriye uyumludur; kaynak sisteme yazım yoktur.
- Kalan risk: Gerçek LDAP/sahiplik dizini, çözüm/doğrulama/kapatma, bildirim retry/DLQ, saklama-imha, ServiceNow ve HTTP/UI kapsam dışıdır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.

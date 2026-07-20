---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
  - BFR-DATA-003
  - CTRL-KVKK-SEC-001
requirement_ids:
  - FR-064
  - FR-065
  - FR-066
  - FR-070
  - UC-011
  - UC-013
  - RULE-006
  - RULE-011
  - AC-015
  - AC-016
  - NFR-REL-005
  - NFR-REL-006
  - NFR-SEC-001
  - NFR-SEC-005
  - NFR-SEC-008
status: TechnicallyVerified
version: iteration-22b-local
executed_at: 2026-07-17
---

# İterasyon 22B Temel Issue State Machine Kanıtı

## Değişiklik

- İterasyon: 22B - otomatik sahipli issue, deduplication ve `ASSIGNED -> INVESTIGATING` geçişi
- Commit/Artifact: Git deposu bulunmadığı için commit yok; yerel çalışma ağacı
- Bileşen: `veri_kalitesi.issues`, `veri_kalitesi.notifications`, `veri_kalitesi.audit`, `veri_kalitesi.identity`
- Kontrol/Gereksinim: FR-064, FR-065 ilk atama, FR-066 temel geçiş, FR-070 geçmiş; UC-011/013, RULE-006/011, AC-015/016, NFR-REL-005/006, NFR-SEC-001/005/008 ve BFR-IAM-001/002, BFR-DATA-003 alt kapsamı

## Doğrulama

- Komut: `pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek içi SQLite ve sentetik UUID referansları
- Sentetik veri seti: Kalite/teknik trigger, 100 tekrar, payload çakışması, assignment resolver/depo/audit/bildirim arızası, farklı assignee, eksik scope, servis ve ayrıcalıklı context
- Beklenen: Güvenilir servis sahipli issue oluşturur; 100 tekrar tek issue/bildirimde birleşir; issue/geçmiş/audit atomiktir; bildirim hatasında issue korunur; yalnız assignee kapsam içinde incelemeyi başlatır.
- Gerçekleşen: 306 test geçti. Issue hedef grubu 24 testle geçti; 24 yeni test eklendi.
- Sonuç: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Değişen Python dosyalarında `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src`: PASS
- Tam depo format kontrolü, bu iterasyonda değişmeyen dört eski dosyanın mevcut format farkları nedeniyle PASS değildir.

## Güvenlik

- Güven sınırı: Issue üretimi güvenilir standart servis context'i, inceleme geçişi güvenilir standart kullanıcı context'i gerektirir. Serbest actor/assignee/scope yetki kanıtı değildir.
- Atama: Assignee ve öncelik yalnız enjekte edilen güvenilir assignment resolver'dan gelir; UUID ve enum dışı değerler reddedilir.
- Yetki: Yalnız kayıtlı assignee ve ActorContext'teki ilgili dataset/source scope'ü incelemeyi başlatabilir. Başka kullanıcı, eksik scope, servis ve ayrıcalıklı context reddedilir.
- Veri minimizasyonu: Issue serbest açıklama, kök neden, kayıt örneği veya hata detayı saklamaz. Dedup anahtarı SHA-256 özetiyle saklanır.
- Audit: Trigger işlemi ve durum geçişi merkezi redactor ile hazırlanır. Assignee, scope, dedup anahtarı ve açık session kimliği audit özetinden çıkarılır.
- Atomiklik: Issue/geçmiş ve redakte audit outbox aynı SQLite transaction'ındadır; stage arızası rollback olur. Geçmiş monoton sequence ile değişmez sıralanır; SQLite enum ve foreign key kısıtları etkindir.
- Idempotency: Dedup özetinden deterministik issue UUID'si üretilir; aynı payload sayaç/son görülme zamanını günceller, farklı payload çakışır ve mevcut durum geriye alınmaz.
- Bildirim: 22A servisi issue commitinden sonra çağrılır. Teknik veya politika hatasında issue korunur ve hata issue kimliğiyle sınıflandırılır; retry/DLQ sonraki dilimdedir.
- Maker-checker etkisi: Bu dilimde serbest politika/konfigurasyon değişikliği yoktur. Assignment politikası yönetim yüzeyi eklendiğinde kritik değişiklik değerlendirmesi gerekir.
- Geri alma: `issues` paketi ve yeni SQLite tabloları bağımsızdır; trigger tüketimi devre dışı bırakılıp önceki sürüme dönülebilir. Kaynak sisteme yazım yoktur.
- Kalan risk: Gerçek assignment/fallback kuyruk adaptörü, yeniden atama, çözüm/doğrulama/kapatma, yorum/ek, bildirim retry/DLQ, saklama-imha, ServiceNow ve HTTP/UI kapsam dışıdır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.

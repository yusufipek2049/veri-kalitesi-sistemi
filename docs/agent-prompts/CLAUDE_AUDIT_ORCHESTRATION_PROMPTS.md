# Claude — Denetim Orkestrasyon Promptları

Her görevi ayrı oturum veya kontrollü aşama olarak çalıştır.

## C1 — Mevcut kabiliyet haritası

Önce kapsamlı promptu ve Qoder envanterlerini oku.

Repository'nin gerçekte sahip olduğu mevcut fonksiyonları çıkar. Bir fonksiyonu
uygulanmış saymadan önce mümkün olduğu ölçüde:

`domain → migration → repository → service → API → frontend → permission → audit → test`

zincirini doğrula.

Üret:

- `docs/functional-audit/01-Current-Capabilities.md`
- `docs/functional-audit/work/01-Unresolved-Evidence-Questions.md`

Hedef sistem tasarlama ve çözüm önerme.

## C2 — Bağımsız hedef kabiliyet modeli

Repository'nin mevcut sınırlarından bağımsız kurumsal veri kalitesi sistemi
referans modeli oluştur.

Üret:

- `docs/functional-audit/02-Target-Capability-Hierarchy.md`

L0–L5 fonksiyon ağacı kur. Her yaprak fonksiyonu aktör, tetikleyici, akış,
durum, yetki, audit, API, UI, tablo ve test ihtiyacına bağla.

## C3 — Uçtan uca akış denetimi

Mevcut kabiliyet ve hedef model üzerinden akışları denetle.

Üret:

- `docs/functional-audit/03-End-to-End-Workflow-Audit.md`

Her adım için aktör, ekran, API, servis, tablo, state, audit ve test kanıtı ver.
İlk kırılma noktasını göster.

## C4 — Fonksiyonel gap envanteri

Üret:

- `docs/functional-audit/04-Functional-Gap-Inventory.md`

Aynı eksikliği farklı adlarla tekrarlama. Her gap'i hedef fonksiyon koduna bağla.

## C5 — UI ve API

Üret:

- `docs/functional-audit/05-UI-Information-Architecture.md`
- `docs/functional-audit/06-API-Inventory-and-Gaps.md`

Her önerilen ekran aktöre ve göreve; her endpoint akışa ve state transition'a
bağlı olsun.

## C6 — Hedef veri modeli ve şema farkı

Üret:

- `docs/functional-audit/07-Target-Data-Model.md`
- `docs/functional-audit/08-Existing-Schema-Gap-Analysis.md`

Tablo ve kolonları PostgreSQL tipi, null/default, PK/FK, unique/check, index,
partition, audit, retention, optimistic locking ve immutable davranışla yaz.

## C7 — State, rol ve test

Üret:

- `docs/functional-audit/09-State-Machines.md`
- `docs/functional-audit/10-Roles-and-Permissions.md`
- `docs/functional-audit/11-Test-Coverage-Gaps.md`

## C8 — Codex doğrulamasını uzlaştırma

`14-Independent-Code-Verification.md` dosyasını oku. Her itirazı repository
kanıtıyla değerlendir.

Üret:

- `docs/functional-audit/work/02-Verification-Resolution.md`

Kararlar:

- kabul edildi
- kısmen kabul edildi
- reddedildi

Gerekli raporları güncelle.

## C9 — Backlog ve yol haritası

Üret:

- `docs/functional-audit/12-Prioritized-Backlog.md`
- `docs/functional-audit/13-Implementation-Roadmap.md`
- `docs/functional-audit/00-Executive-Summary.md`

İterasyonları teknik katmanlara göre değil, uçtan uca kullanıcı değeri üreten
dikey dilimler halinde oluştur.

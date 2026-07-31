---
type: architecture
project: Veri Kalitesi İzleme ve Skorlama Sistemi
created_at: 2026-07-30
tags:
  - architecture
  - agents
  - orchestration
---

# Ajan Orkestrasyon Mimarisi

Bu doküman, depoda geliştirme işini yürüten ajanların (Claude Code, Codex,
Qoder Pro) rol dağılımını, durum modelini ve güvenlik sınırlarını tanımlar.
Ortak davranış kuralları [AGENTS.md](../AGENTS.md) dosyasındadır ve burada
tekrar edilmez.

> Kapsam notu: bu mimari **geliştirme süreci** içindir; ürünün çalışma zamanı
> mimarisi değildir. Ürün mimarisi için [MIMARI-INDEX](MIMARI-INDEX.md).

## 1. Temel ilke: rol sabit, ajan değişken

Roller mimarinin parçasıdır; hangi ajanın hangi rolü üstlendiği ise
yapılandırmadır. Bir sağlayıcının kotası bittiğinde mimari değişmez, yalnız
[.agent/config/agents.yaml](../.agent/config/agents.yaml) değişir.

| Rol | Varsayılan ajan | Yedek | Otomatik çalışır mı |
| --- | --- | --- | --- |
| Mimar (`architect`) | Claude | — | evet |
| Reviewer (`reviewer`) | Claude | — | evet (zorunlu) |
| Uygulayıcı (`implementer`) | Codex | Qoder | Codex evet, Qoder hayır |
| Testçi (`tester`) | Codex | Qoder | kapı testlerini controller çalıştırır |

Mimar ve reviewer **otomatik çalışabilen** bir ajan olmak zorundadır: bağımsız
review handoff'a bırakılamaz, aksi halde uygulayıcı kendi işini onaylamış
olurdu. Bu kural `roles_load` tarafından fail-closed olarak doğrulanır.

### Ajan seçimi

```text
role_resolve(rol)
  ├─ birincil ajan kullanılabilir mi?        → evet: birincil
  │    (agents.yaml runtime bayrağı + binary varlığı)
  └─ hayır → yedek ajan kullanılabilir mi?   → evet: yedek + FALLBACK_REASON
                                              → hayır: fail-closed (exit 36)
```

İki ayrı devir mekanizması vardır ve karıştırılmamalıdır:

1. **Yapılandırma devri** — `runtime.codex_available: false`. Rol daha aşama
   başlamadan yedeğe verilir. Şu anda aktif olan budur.
2. **Çalışma anı devri** — `runtime.fallback_on_quota_error: true`. Aşama
   ortasında sağlayıcıya hiç ulaşılamazsa (kota, kredi, kimlik) aynı aşama
   yedek ajanla **bir kez** tekrarlanır. Yalnız otomatik ajanlar arasında
   geçerlidir. Sıradan aşama hatası, timeout ve beklenmeyen çıktı bu sınıfa
   girmez: gerçek bir defekt sessizce başka sağlayıcıya devredilmez.

## 2. Bileşenler ve durum sınırları

```text
tools/agent-loop/          KALICI KOD (izlenir, review edilir)
  roles.sh                 rol → ajan çözümü, fail-closed doğrulama
  ledger.sh                görev defteri, claim kilidi, kanıt, review kaydı
  lib.sh                   state machine, aşamalar, test kapıları
  controller.sh            giriş noktası, tek instance (flock)
  devam.sh                 CLI dispatcher
  agentctl.sh              operatör CLI'ı

.agent/                    KALICI DURUM (izlenir)
  config/agents.yaml       rol dağıtımının TEK kaynağı
  tasks/{active,completed,blocked}/  görev defteri (otomatik üretilir)
  tasks/templates/         görev, handoff, kanıt, review şablonları
  handoffs/                üretilen görev paketleri
  reviews/                 bağımsız review kayıtları
  evidence/tests/          test kanıtı kayıtları (JSON)

.agent-handoff/            RUNTIME (Git tarafından ignore edilir)
  state/SESSION.json       controller state'i (atomik yazılır)
  CURRENT_TASK.json        aşama kontratı
  logs/                    ham stdout/stderr ve test logları
  prompts/                 izlenen kaynaktan alınan snapshot

$GIT_COMMON_DIR/agent-claims/   worktree'ler arası claim kilitleri
```

Kural: `.agent-handoff/` hiçbir zaman kanonik bilgi kaynağı değildir; her
çalışmada yeniden kurulur. Kalıcı ve denetlenebilir olan `.agent/` altındadır.
Ham loglar büyüyebildiği için (ölçülen: 6.7 MB) izlenmez; kanıt kayıtları
onlara **yol ile referans** verir.

## 3. Görev yaşam döngüsü

```text
READY ──claim──> CLAIMED ──> IN_PROGRESS ──> IMPLEMENTED ──> TESTING
                                                                 │
                        ┌────────────────────────────────────────┘
                        ▼
                     REVIEW ──APPROVED──> COMPLETED
                        │
                        ├──CHANGES_REQUESTED──> IN_PROGRESS (onarım turu)
                        └──BLOCKED──> insan kararı
```

Kodun yazılmış olması, testlerin geçmesi, review'ın tamamlanması ve görevin
kapanması ayrı durumlardır. Durum tek yerde tutulur (`SESSION.json`); görev
defteri bundan **türetilir** (`ledger_sync`), ikinci bir durum deposu yoktur.

Controller aşamaları (`PLANNER`, `IMPLEMENTER`, `TESTER`, `REVIEWER`) ve
durumları (`READY`, `FAILED`, `WAITING_AGENT`, `WAITING_HUMAN`, `COMPLETED`)
yaşam döngüsü durumlarına `lifecycle_state()` ile eşlenir.

## 4. Handoff modeli (otomatik çalıştırılamayan ajan)

Qoder Pro IDE tabanlıdır; headless CLI ile sürülemez. Bu nedenle tam otomasyon
varmış gibi davranılmaz. Uygulayıcı rolü Qoder'a düştüğünde:

1. Controller görev paketini `.agent/handoffs/` altına yazar (dokuz bölüm:
   amaç, gereksinim referansları, değiştirilebilir/değiştirilmez alanlar, kabul
   kriterleri, testler, güvenlik kuralları, çıktı formatı, tam kontrat).
2. Durum `WAITING_AGENT` olur; state kalıcıdır, kullanıcı çevrimdışı olabilir.
3. Operatör paketi IDE'de çalıştırır.
4. `devam "qoder tamam"` denildiğinde controller **beyanı doğrular**: çalışma
   ağacı parmak izi (`git status --porcelain` özeti) değişmediyse ilerleme
   üretilmez ve görev `WAITING_AGENT` durumunda kalır.
5. Doğrulanırsa controller kendi test kapılarını çalıştırır, ardından bağımsız
   reviewer aşaması gelir.

Böylece "uygulandı" beyanı hiçbir noktada tek başına kanıt olmaz.

## 5. Eşzamanlılık ve worktree

- Her yazıcı ajan ayrı branch ve worktree kullanır:
  `<repo>-worktrees/<kisa-ad>` + `agent/<kisa-ad>`.
- Tek controller instance'ı `flock` ile korunur (aynı worktree).
- Aynı görevi ikinci bir uygulayıcının claim etmesi, **ortak git dizinindeki**
  claim kilidiyle engellenir; bu dizin bütün worktree'lerde aynıdır ve çalışma
  ağacına yazılmaz. Sahibi ölmüş bayat claim otomatik devralınmaz; operatör
  `agentctl cleanup` ile açıkça serbest bırakır.
- Kullanıcının kirli çalışma ağacına müdahale edilmez; `reset --hard`,
  `clean -fd`, force push ve otomatik merge yapılmaz.

## 6. Test kapıları ve kanıt

Kapı testleri agent sürecine bağlanmaz; controller kabuğunda `GNU timeout` ile
çalışır (0 token). Her çalıştırma için `.agent/evidence/tests/` altına komut,
exit code, süre, sayaçlar, log yolu, ortam notu ve **hata sınıfı** yazılır.

Sınıflar: `PRODUCT_DEFECT`, `TEST_DEFECT`, `ENVIRONMENT_FAILURE`,
`DEPENDENCY_FAILURE`, `CONFIGURATION_FAILURE`, `UNKNOWN`. PostgreSQL preflight
başarısızlığı tanım gereği `ENVIRONMENT_FAILURE`'dır ve sahte PASS üretilmez;
zorunlu entegrasyon testinde `skip` tespiti kapıyı düşürür. pytest özeti
okunamazsa sayaçlar `-1` yazılır — sayı uydurulmaz.

## 7. Güvenlik sınırları

- Secret, token ve parola depoya yazılmaz. Çalışma zamanı yapılandırması depo
  dışındadır (`~/.config/veri-kalitesi/agent-loop.env`, mod 600); depoda yalnız
  `.agent/config/active-runtime.env.example` bulunur.
- Ajan çıktısı yalnız (a) exit 0, (b) boş değil, (c) beklenen `STATUS:` satırı
  doğrulandıktan sonra görünür yapılır; bayat veya kısmi sonuç okunmaz.
- Bilinmeyen ajan, geçersiz rol yapılandırması ve karşılanamayan rol
  fail-closed'dur: hiçbir süreç başlatılmaz.

## 8. İlgili dokümanlar

- [AGENTS.md](../AGENTS.md) — ortak ajan kuralları
- [CLAUDE.md](../CLAUDE.md) — mimar/reviewer rolü ve "devam" davranışı
- [.qoder/rules/](../.qoder/rules/) — uygulayıcı/testçi kuralları
- [Ajan Orkestrasyon Runbook](../07-Operasyon/Ajan-Orkestrasyon-Runbook.md) — operasyon ve sorun giderme
- [tools/agent-loop/README.md](../tools/agent-loop/README.md) — controller ayrıntısı

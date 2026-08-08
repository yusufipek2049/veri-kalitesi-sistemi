# agent-loop — `devam` pipeline controller

Kalıcı, Git'te izlenen agent-orchestration controller'ı. Kullanıcı terminalde
`devam` yazarak canonical dokümanlardan sıradaki görevi seçtirir, göreve özgü
kontrat üretir, implementasyonu yaptırır, testleri controller kabuğunda çalıştırır
ve review sürecini tamamlar.

## Neden `tools/agent-loop`?

Kalıcı/kaynak kod burada (izlenir, review edilir). Runtime state, log ve prompt
snapshot'ları `.agent-handoff/` altında **üretilir** ve Git tarafından **ignore
edilir** (`.gitignore` → `.agent-handoff/`). `.agent-handoff` hiçbir zaman canonical
proje bilgisi kaynağı değildir; controller tarafından her çalışmada yeniden kurulur.

## Bileşenler

| Dosya | Sorumluluk |
| --- | --- |
| `lib.sh` | Yan etkisiz, source edilebilir controller kütüphanesi (state, contract, agent backend, test, planner/implementer/tester/reviewer, `main`). |
| `roles.sh` | Rol → ajan çözümü. Canonical kaynak `.agent/config/agents.yaml`; geçersiz config fail-closed. |
| `ledger.sh` | Kalıcı görev defteri (`.agent/tasks/`), claim kilidi, test kanıtı, review kaydı, handoff paketi. |
| `controller.sh` | Giriş noktası: env yükler, `.agent-handoff` runtime'ını kurar, tek instance için `flock` alır, `main` döngüsünü çalıştırır. |
| `devam.sh` | CLI dispatcher: `continue` / `durum` / `log`. |
| `agentctl.sh` | Operatör CLI'ı: durum, görev, claim, worktree, handoff, kanıt, review, temizlik (`--dry-run` destekler). |
| `prompts/*.md` | Planner, implementer, reviewer prompt kaynakları; runtime'a snapshot'lanır. |
| `tests/run.sh` | Stub `codex`/`claude` binary'leri ve fonksiyon override'ları ile controller smoke/integration testleri. |

## Komutlar

| Komut | Anlam |
| --- | --- |
| `devam` | Canonical dokümanlardan sıradaki görevi seç ve pipeline'ı çalıştır. |
| `devam "görev"` | Verilen görevi yeni kontratla doğrudan çalıştır (planner atlanır). |
| `devam "insan kararı"` | `WAITING_HUMAN` aşamasındaki kararı kaydet ve devam et. |
| `devam durum` | Iteration, stage, status, görev ve son hatayı göster (ajan başlatmaz). |
| `devam log` | Mevcut aşamanın son log dosyalarını göster (ajan başlatmaz). |

`~/.local/bin/devam` bu dizindeki `devam.sh`'i exec eder. Hedef repo
`AGENT_LOOP_TARGET`, yapılandırma `~/.config/veri-kalitesi/agent-loop.env`
(`AGENT_LOOP_ENV_FILE` ile override edilir) ile belirlenir.

## Rol dağıtımı (agents.yaml)

Hangi ajanın hangi rolü üstlendiği **burada değil**, `.agent/config/agents.yaml`
dosyasında tanımlıdır (tek kanonik kaynak). Controller her aşamada rolü çözer:

```text
planner/reviewer -> architect/reviewer alanı (otomatik çalışabilen ajan zorunlu)
implementer/tester -> primary; kullanılamıyorsa fallback + FALLBACK_REASON
```

Ajan "kullanılabilir" sayılmaz ise (ör. `runtime.codex_available: false` veya
binary yok) rol daha aşama başlamadan yedeğe geçer. Rol hiç karşılanamıyorsa
fail-closed (exit 36) — hiçbir süreç başlatılmaz. Öncelik sırası:

1. `AGENT_BACKEND_<ROLE>` env override (tek turluk, ör. `AGENT_BACKEND_IMPLEMENTER=claude devam`)
2. `agents.yaml` rol dağıtımı
3. Geriye dönük global `AGENT_BACKEND` (yalnız `agents.yaml` yokken)

### Handoff ajanı (otomatik çalıştırılamayan)

`qoder` headless çalıştırılamaz. Rol Qoder'a düştüğünde controller ajan
başlatmaz: `.agent/handoffs/` altına dokuz bölümlü görev paketi yazar ve
`WAITING_AGENT` durumunda durur. `devam "qoder tamam"` denildiğinde beyan
**doğrulanır** — çalışma ağacı parmak izi değişmediyse ilerleme üretilmez.
Doğrulanırsa controller test kapılarını kendisi çalıştırır, ardından bağımsız
reviewer aşaması gelir. `devam "blocked: ..."` görevi `BLOCKED` yapar.

## State machine

Durumlar: `READY`, `RUNNING` (aşama içi), `FAILED`, `WAITING_AGENT`,
`WAITING_HUMAN`, `COMPLETED`.
Aşamalar: `PLANNER` → `IMPLEMENTER` → `TESTER` → `REVIEWER`.

Bu controller durumları `.agent/tasks/` defterinde kanonik yaşam döngüsüne
eşlenir (`READY`, `CLAIMED`, `IN_PROGRESS`, `IMPLEMENTED`, `TESTING`, `REVIEW`,
`CHANGES_REQUESTED`, `APPROVED`, `BLOCKED`, `COMPLETED`). Defter türetilmiş
görünümdür; ikinci bir durum deposu yoktur.

Aynı görevi ikinci bir uygulayıcının claim etmesi ortak git dizinindeki
kilitle engellenir (`$GIT_COMMON_DIR/agent-claims/`, worktree'ler arası görünür).

- State atomik yazılır (`mktemp` + `jq` doğrulaması + `mv`).
- Tek instance `flock` ile korunur.
- Başarısız aşama sonraki `devam`'da güvenli yeniden çalışır; başarılı aşamalar
  gereksiz tekrar edilmez (kesinti sonrası doğru aşamadan devam).
- `COMPLETED` sonrası boş `devam` yeni iterasyon seçer; tamamlanmış görev yeniden
  seçilmez (planner + fresh kontrat).

## Görev seçimi

Boş `devam`:
1. **Deterministik (0 token):** controller `NEXT_STEP.md`'yi bash ile okur; frontmatter
   `status: active` ve `work_package` varsa ve bu work package **az önce tamamlanan
   görevle aynı değilse** (bayatlık guard'ı) görevi doğrudan seçer. Bu, `AGENTS.md`
   görev seçim algoritmasının "NEXT_STEP güncelse onu kullan" adımıdır ve **planner LLM
   çağrısını çoğu turda tamamen atlar.**
2. **LLM planner (yedek):** NEXT_STEP eksik/bayat/`active` değilse fresh planner agent
   süreci canonical dokümanları okuyup tek görevi seçer.

Açık görev verildiğinde ikisi de atlanır. Her görevde kontrat (`CURRENT_TASK.json`)
**tamamen** yeniden üretilir; önceki görevin dosya kapsamı, kabul kriteri veya commit
beklentisi taşınmaz. `repository.base_ref` yalnız bilgilendirmedir ve her aşamadan önce
güncel HEAD ile yenilenir — tarihsel HEAD eşitliği hiçbir zaman kapı değildir.

## Maliyet (token) kaldıraçları

- **Deterministik planner:** yukarıdaki 0-token yol; LLM planner yalnız gerektiğinde.
- **Aşama başına reasoning effort / model:** codex için
  `CODEX_{PLANNER,REVIEWER,IMPLEMENTER}_REASONING` (ör. planner/reviewer `low`) ve
  `CODEX_{...}_MODEL`; claude için `CLAUDE_{...}_EFFORT` ve `CLAUDE_{...}_MODEL`.
  Implementer güçlü kalır.
- **Onarım turu:** `MAX_REPAIR_ROUNDS` varsayılan **1**; aşılırsa `WAITING_HUMAN`.
- **Scope hint:** planner/`NEXT_STEP` çıktısından türetilen `scope.hint`, implementer'a
  "buradan başla" ipucu vererek agentic dosya keşfini daraltır (bağlayıcı liste değil).
- **Test kapıları:** zaten 0 token (controller kabuğunda, agent süreci değil).

İnsan kararı bir onarım kilidini kırdığında (`WAITING_HUMAN` sonrası `devam "karar"`)
onarım bütçesi (`repair_round`) sıfırlanır; verdiğin yönlendirme taze bir turla işlenir.

## Agent çalıştırma (backend seçimi)

Her implementer/reviewer/planner çağrısı fresh bir agent süreci ile başlar; eski
session/thread resume edilmez. Rol dağıtımı `agents.yaml`'dan gelir (yukarı bak);
aşağıdaki tablo çözülen ajanın nasıl çalıştırıldığını gösterir. `agents.yaml`
yokken geriye dönük olarak tek bir `AGENT_BACKEND` kullanılır:

| `AGENT_BACKEND` | Çağrı | Sonuç yakalama | Binary |
| --- | --- | --- | --- |
| `codex` (varsayılan) | `codex --ask-for-approval never --sandbox danger-full-access -C <root> exec -o <dosya> -` | agent dosyaya yazar | `CODEX_BIN` |
| `claude` | `claude -p --permission-mode bypassPermissions --add-dir <root>` | stdout dosyaya yönlendirilir | `CLAUDE_BIN` |

Backend'ler yalnız argüman kurulumu ve sonuç yakalama biçiminde farklıdır. Prompt
her iki backend'de stdin'den verilir, agent repo kökünde çalıştırılır ve sonuç
dosyası yalnız (a) exit 0, (b) boş değil, (c) beklenen `STATUS:` satırı
doğrulandıktan **sonra** atomik olarak görünür yapılır; aksi halde bayat/kısmi
sonuç asla okunmaz. Tanımsız bir `AGENT_BACKEND` fail-closed'dur (exit 35): hiçbir
agent çalıştırılmaz ve varsa eski sonuç dosyası okunmaz. Gerçek stderr ve exit
kodları `.agent-handoff/logs/` altında kalıcı loglanır; stdout logu `BACKEND=` satırı
ile hangi backend'in çalıştığını kaydeder.

### Sağlayıcı erişimi yokken devir (fallback)

`AGENT_BACKEND_FALLBACK` ayarlıysa ve birincil backend **sağlayıcıya hiç
ulaşamadıysa** (kota/kredi/kimlik: `usage limit`, `session limit`, `429`, `401`,
`quota`, `credit balance`, `not logged in` … — desen `AGENT_PROVIDER_ERROR_RE`)
aynı aşama diğer backend ile **bir kez**
tekrarlanır: fresh süreç, aynı girdi, aynı `STATUS` doğrulaması. Devir
`FALLBACK_FROM` / `FALLBACK_TO` / `FALLBACK_REASON` / `FALLBACK_PRIMARY_EXIT`
satırlarıyla stdout ve failure loguna yazılır; birincil denemenin stderr kanıtı
silinmez.

İmza **iki kanalda** aranır. Sağlayıcılar tutarsız davranır: codex kota hatasını
stderr'e yazar, `claude -p` ise **stdout'a** yazıp stderr'i boş bırakır — ve stdout
claude backend'inde aynı zamanda sonuç kanalıdır. Bu yüzden sonuç kanalına yalnız
**geçerli sonuç yokken** bakılır: gerçek sonuç her zaman `STATUS:` satırıyla başlar,
dolayısıyla imzayı metin olarak içeren geçerli bir rapor yanlışlıkla sağlayıcı
arızası sayılmaz.

Devir **yapılmayan** durumlar — bunlar sağlayıcı arızası değildir ve sessizce
başka sağlayıcıya devredilmemelidir:

- Sıradan aşama başarısızlığı (stderr'de sağlayıcı imzası yok) → `33`.
- `GNU timeout` kodları (`124`, `125`, `137`) → devir yok.
- Beklenmeyen `STATUS` satırı (`21`) → model davranışı sorunudur, kota değil.
- `AGENT_BACKEND_FALLBACK` boş, birincille aynı veya bilinmeyen bir değer.

Varsayılan **kapalıdır** (boş): maliyet operatör açıkça izin vermeden başka
sağlayıcıya kaymaz.

### Kalıcı log boyutu

Aşama stderr logu `AGENT_STDERR_LOG_MAX_BYTES` (varsayılan 2 MB, `0` = sınırsız)
sınırını aşarsa **son** baytlar korunur — hata mesajı sonda olduğu için — ve kesme
olayı logun başına açıkça yazılır. Sessiz veri kaybı yoktur. (Ölçüm: iterasyon 13
implementer stderr logu 6.7 MB'a çıkmıştı.)

Rol başına model/effort değişkenleri backend başına ayrıdır ve birbirine sızmaz:
`CODEX_{...}_MODEL` / `CODEX_{...}_REASONING` yalnız codex'e, `CLAUDE_{...}_MODEL` /
`CLAUDE_{...}_EFFORT` yalnız claude'a uygulanır. Böylece codex için ayarlanmış bir
env-file backend değiştirildiğinde geçersiz argüman üretmez.

## Test kapıları

Geniş testler agent sürecine bağlanmaz; controller kabuğunda `GNU timeout`
(önce `SIGINT`, sonra `--kill-after`) ile çalışır. Birim testleri her zaman;
entegrasyon testleri yalnız görev PostgreSQL/uygulama kaynağı/migration etkilediğinde
(`integration_required`). Entegrasyon gerektiğinde PG preflight zorunludur;
başarısızsa **sahte PASS üretilmez** (`ENVIRONMENT_BLOCK`). Zorunlu entegrasyon
testinde `skipped` tespiti gate'i düşürür.

## PostgreSQL

`DATA_QUALITY_POSTGRES_TEST_URL` ve `DATA_QUALITY_DATABASE_SCHEMA` env-file'dan
yüklenir ve alt süreçlere açıkça forward edilir. Preflight `current_database()` /
`current_user` sorgular; bağlantı yoksa entegrasyon PASS sayılmaz.

## İnsan kararı

Gerçek ürün/politika/güvenlik/kapsam kararı gerektiğinde pipeline `WAITING_HUMAN`
durumuna geçer, state'i atomik kaydeder ve temiz çıkar. Kullanıcı çevrimdışıyken
state kaybolmaz; sonraki `devam "karar"` aynı karar noktasından devam eder. Teknik
veya ortam hatası insan kararı gibi gösterilmez (bunlar `FAILED` olur ve yeniden
denenir). `HUMAN_WAIT_SECONDS` (varsayılan 600) operatöre gösterilen tavsiye
penceresidir; state kalıcı olduğu için katı bir bloklama süresi uygulanmaz.

## Testleri çalıştırma

```bash
bash tools/agent-loop/tests/run.sh
```

Gerçek agent CLI'ları ve gerçek pytest çağrılmaz: her backend (`codex`, `claude`)
`tests/stubs/` altındaki bir stub ile, test kapıları fonksiyon override'ı ile taklit
edilir. Her test kendi geçici repo'sunda izole çalışır. Suite iki backend için de
sonuç yakalama, argüman eşlemesi, bayat/boş/geçersiz sonuç reddi, PG env forward'ı
ve uçtan uca iterasyonu; ayrıca sağlayıcı devrinin tetiklendiği ve **tetiklenmediği**
durumları ve stderr log sınırını kapsar.

## Yapılandırma varsayılanları

| Değişken | Varsayılan |
| --- | --- |
| `TEST_TIMEOUT_SECONDS` | 900 |
| `CODEX_STAGE_TIMEOUT_SECONDS` | 2700 |
| `AGENT_STAGE_TIMEOUT_SECONDS` | `CODEX_STAGE_TIMEOUT_SECONDS` (geriye dönük ad) |
| `MAX_REPAIR_ROUNDS` | 1 |
| `HUMAN_WAIT_SECONDS` | 600 |
| `UNIT_TEST_DIR` | `docs/testing/01-Birim` |
| `INTEGRATION_TEST_DIR` | `docs/testing/02-Entegrasyon` |
| rol dağıtımı | `.agent/config/agents.yaml` (tek kanonik kaynak) |
| `AGENT_BACKEND_<ROLE>` | (unset — tek turluk rol override'ı) |
| `AGENT_BACKEND` | `codex` (yalnız `agents.yaml` yokken; diğer değer: `claude`) |
| `AGENT_BACKEND_FALLBACK` | (boş — `agents.yaml` varken `runtime.fallback_on_quota_error` belirler) |
| `AGENT_STDERR_LOG_MAX_BYTES` | 2000000 (`0` = sınırsız) |
| `AGENT_PROVIDER_ERROR_RE` | kota/kredi/kimlik imza deseni (grep -E) |
| `CODEX_BIN` / `CLAUDE_BIN` | `codex` / `claude` |
| `CODEX_PLANNER_REASONING` / `CODEX_REVIEWER_REASONING` | (env-file'da `low`) |
| `CODEX_IMPLEMENTER_REASONING` | (unset — codex config varsayılanı) |
| `CODEX_{PLANNER,REVIEWER,IMPLEMENTER}_MODEL` | (unset — aşama başına model override) |
| `CLAUDE_{PLANNER,REVIEWER,IMPLEMENTER}_EFFORT` | (unset — `low\|medium\|high\|xhigh\|max`) |
| `CLAUDE_{PLANNER,REVIEWER,IMPLEMENTER}_MODEL` | (unset — ör. `opus`, `sonnet`, `haiku`) |

Rolü kalıcı değiştirmek için `.agent/config/agents.yaml` düzenlenir (ör. Codex
kotası dolduğunda `runtime.codex_available: false`, geri geldiğinde `true`).
Tek turluk denemede `AGENT_BACKEND_IMPLEMENTER=claude devam` yeterlidir.
`agents.yaml` bulunmayan kurulumlarda eski `AGENT_BACKEND` davranışı korunur.

## Operatör CLI'ı

```bash
tools/agent-loop/agentctl.sh --help
tools/agent-loop/agentctl.sh status            # rol dağıtımı, yaşam döngüsü, claim'ler
tools/agent-loop/agentctl.sh select-runner implementer
tools/agent-loop/agentctl.sh create-worktree <kisa-ad>
tools/agent-loop/agentctl.sh build-handoff implementer
tools/agent-loop/agentctl.sh record-tests unit
tools/agent-loop/agentctl.sh complete-task     # yalnız review APPROVED ise
tools/agent-loop/agentctl.sh cleanup --dry-run
```

`devam` otomatik akıştır; `agentctl` inceleme ve elle müdahale içindir. Hiçbiri
commit, merge, push, PR veya `git reset`/`clean` çalıştırmaz.

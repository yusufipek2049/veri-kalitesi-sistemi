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
| `controller.sh` | Giriş noktası: env yükler, `.agent-handoff` runtime'ını kurar, tek instance için `flock` alır, `main` döngüsünü çalıştırır. |
| `devam.sh` | CLI dispatcher: `continue` / `durum` / `log`. |
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

## State machine

Durumlar: `READY`, `RUNNING` (aşama içi), `FAILED`, `WAITING_HUMAN`, `COMPLETED`.
Aşamalar: `PLANNER` → `IMPLEMENTER` → `TESTER` → `REVIEWER`.

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
session/thread resume edilmez. Backend `AGENT_BACKEND` ile seçilir:

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
ve uçtan uca iterasyonu kapsar.

## Yapılandırma varsayılanları

| Değişken | Varsayılan |
| --- | --- |
| `TEST_TIMEOUT_SECONDS` | 900 |
| `CODEX_STAGE_TIMEOUT_SECONDS` | 2700 |
| `AGENT_STAGE_TIMEOUT_SECONDS` | `CODEX_STAGE_TIMEOUT_SECONDS` (geriye dönük ad) |
| `MAX_REPAIR_ROUNDS` | 1 |
| `HUMAN_WAIT_SECONDS` | 600 |
| `UNIT_TEST_DIR` | `06-Testler/01-Birim` |
| `INTEGRATION_TEST_DIR` | `06-Testler/02-Entegrasyon` |
| `AGENT_BACKEND` | `codex` (diğer geçerli değer: `claude`) |
| `CODEX_BIN` / `CLAUDE_BIN` | `codex` / `claude` |
| `CODEX_PLANNER_REASONING` / `CODEX_REVIEWER_REASONING` | (env-file'da `low`) |
| `CODEX_IMPLEMENTER_REASONING` | (unset — codex config varsayılanı) |
| `CODEX_{PLANNER,REVIEWER,IMPLEMENTER}_MODEL` | (unset — aşama başına model override) |
| `CLAUDE_{PLANNER,REVIEWER,IMPLEMENTER}_EFFORT` | (unset — `low\|medium\|high\|xhigh\|max`) |
| `CLAUDE_{PLANNER,REVIEWER,IMPLEMENTER}_MODEL` | (unset — ör. `opus`, `sonnet`, `haiku`) |

Backend'i kalıcı değiştirmek için env-file'a (`~/.config/veri-kalitesi/agent-loop.env`)
`export AGENT_BACKEND=claude` eklenir; tek turluk denemede `AGENT_BACKEND=claude devam`
yeterlidir.

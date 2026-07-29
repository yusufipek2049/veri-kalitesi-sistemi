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
| `lib.sh` | Yan etkisiz, source edilebilir controller kütüphanesi (state, contract, codex, test, planner/implementer/tester/reviewer, `main`). |
| `controller.sh` | Giriş noktası: env yükler, `.agent-handoff` runtime'ını kurar, tek instance için `flock` alır, `main` döngüsünü çalıştırır. |
| `devam.sh` | CLI dispatcher: `continue` / `durum` / `log`. |
| `prompts/*.md` | Planner, implementer, reviewer prompt kaynakları; runtime'a snapshot'lanır. |
| `tests/run.sh` | Stub `codex` ve fonksiyon override'ları ile controller smoke/integration testleri. |

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
2. **LLM planner (yedek):** NEXT_STEP eksik/bayat/`active` değilse fresh `codex exec`
   planner canonical dokümanları okuyup tek görevi seçer.

Açık görev verildiğinde ikisi de atlanır. Her görevde kontrat (`CURRENT_TASK.json`)
**tamamen** yeniden üretilir; önceki görevin dosya kapsamı, kabul kriteri veya commit
beklentisi taşınmaz. `repository.base_ref` yalnız bilgilendirmedir ve her aşamadan önce
güncel HEAD ile yenilenir — tarihsel HEAD eşitliği hiçbir zaman kapı değildir.

## Maliyet (token) kaldıraçları

- **Deterministik planner:** yukarıdaki 0-token yol; LLM planner yalnız gerektiğinde.
- **Aşama başına reasoning effort / model:** `CODEX_{PLANNER,REVIEWER,IMPLEMENTER}_REASONING`
  (ör. planner/reviewer `low`) ve `CODEX_{...}_MODEL`. Implementer güçlü kalır.
- **Onarım turu:** `MAX_REPAIR_ROUNDS` varsayılan **1**; aşılırsa `WAITING_HUMAN`.
- **Scope hint:** planner/`NEXT_STEP` çıktısından türetilen `scope.hint`, implementer'a
  "buradan başla" ipucu vererek agentic dosya keşfini daraltır (bağlayıcı liste değil).
- **Test kapıları:** zaten 0 token (controller kabuğunda, codex değil).

İnsan kararı bir onarım kilidini kırdığında (`WAITING_HUMAN` sonrası `devam "karar"`)
onarım bütçesi (`repair_round`) sıfırlanır; verdiğin yönlendirme taze bir turla işlenir.

## Codex çalıştırma

Her implementer/reviewer/planner çağrısı fresh `codex exec` ile başlar
(`--ask-for-approval never --sandbox danger-full-access`). Eski session/thread
resume edilmez. Sonuç dosyası yalnız (a) exit 0, (b) boş değil, (c) beklenen
`STATUS:` satırı doğrulandıktan **sonra** atomik olarak görünür yapılır; aksi halde
bayat/kısmi sonuç asla okunmaz. Gerçek stderr ve exit kodları `.agent-handoff/logs/`
altında kalıcı loglanır. Model `CODEX_{PLANNER,IMPLEMENTER,REVIEWER}_MODEL` ile,
binary `CODEX_BIN` ile override edilir.

## Test kapıları

Geniş testler Codex process'ine bağlanmaz; controller kabuğunda `GNU timeout`
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

Gerçek Codex ve gerçek pytest çağrılmaz: fresh `codex exec` bir stub ile, test
kapıları fonksiyon override'ı ile taklit edilir. Her test kendi geçici repo'sunda
izole çalışır.

## Yapılandırma varsayılanları

| Değişken | Varsayılan |
| --- | --- |
| `TEST_TIMEOUT_SECONDS` | 900 |
| `CODEX_STAGE_TIMEOUT_SECONDS` | 2700 |
| `MAX_REPAIR_ROUNDS` | 1 |
| `HUMAN_WAIT_SECONDS` | 600 |
| `UNIT_TEST_DIR` | `06-Testler/01-Birim` |
| `INTEGRATION_TEST_DIR` | `06-Testler/02-Entegrasyon` |
| `CODEX_PLANNER_REASONING` / `CODEX_REVIEWER_REASONING` | (env-file'da `low`) |
| `CODEX_IMPLEMENTER_REASONING` | (unset — codex config varsayılanı) |
| `CODEX_{PLANNER,REVIEWER,IMPLEMENTER}_MODEL` | (unset — aşama başına model override) |

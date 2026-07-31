---
type: runbook
project: Veri Kalitesi İzleme ve Skorlama Sistemi
created_at: 2026-07-30
tags:
  - operations
  - agents
  - runbook
---

# Ajan Orkestrasyon Runbook'u

Operasyon ve sorun giderme rehberi. Mimari:
[Ajan Orkestrasyon Mimarisi](../02-Mimari/Ajan-Orkestrasyon-Mimarisi.md).
Kurallar: [AGENTS.md](../AGENTS.md).

## 1. Günlük kullanım

| İhtiyaç | Komut |
| --- | --- |
| Sıradaki görevi başlat / kaldığı yerden sürdür | `devam` |
| Belirli bir görevi başlat | `devam "görev açıklaması"` |
| İnsan kararı ver | `devam "kararın"` |
| Handoff işini tamamladığını bildir | `devam "qoder tamam"` |
| Durum (ajan başlatmaz) | `devam durum` |
| Son aşama logları (ajan başlatmaz) | `devam log` |
| Rol dağıtımı, claim ve defter durumu | `tools/agent-loop/agentctl.sh status` |

`agentctl` alt komutları: `status`, `next-task`, `create-task`, `claim-task`,
`select-runner`, `create-worktree`, `build-handoff`, `record-tests`, `review`,
`complete-task`, `cleanup`. Tümü `--dry-run` ve `--help` destekler.

## 2. Rol dağıtımını değiştirme

Tek kaynak: `.agent/config/agents.yaml`.

**Codex kotası bittiğinde** (şu anki durum):

```yaml
runtime:
  codex_available: false      # uygulayıcı ve testçi otomatik olarak Qoder'a düşer
```

**Codex geri geldiğinde** — tek satır:

```yaml
runtime:
  codex_available: true       # Codex birincil role döner, mimari değişmez
```

Doğrulama:

```bash
tools/agent-loop/agentctl.sh select-runner implementer
```

Beklenen çıktı: `AGENT=codex` ve `FALLBACK_REASON=none`.

Tek turluk deneme (dosyayı değiştirmeden):

```bash
AGENT_BACKEND_IMPLEMENTER=claude devam
```

## 3. Qoder ile handoff çalıştırma

1. `devam` — uygulayıcı Qoder'a düşerse controller paketi üretir ve
   `WAITING_AGENT` durumunda durur. Paket yolu ekrana yazılır.
2. Qoder Pro'da doğru worktree'yi aç ve paketi ver. Kopyalanabilir tek prompt:

   ```text
   .agent/handoffs/<TASK-ID>-implementer-i<N>-r<M>.md dosyasını oku ve
   yalnız o pakette tanımlı işi bu worktree içinde uygula. Kurallar AGENTS.md
   ve .qoder/rules/ dosyalarındadır. Belirsizlikte STATUS: BLOCKED ver.
   ```

3. İş bitince: `devam "qoder tamam"`.
   Controller testleri kendisi çalıştırır, ardından Claude review eder.
4. Qoder engellendiyse: `devam "blocked: <neden>"` → görev `BLOCKED` olur.

Paket elle de üretilebilir: `agentctl.sh build-handoff implementer`.

## 4. Worktree düzeni

```bash
tools/agent-loop/agentctl.sh create-worktree <kisa-ad>
AGENT_LOOP_TARGET=<yol> devam
```

Oluşan yapı: `<repo>-worktrees/<kisa-ad>` dizini ve `agent/<kisa-ad>` branch'i.

Branch çakışması varsa komut durur ve hiçbir şey değiştirmez. Ana çalışma ağacı
kirliyse worktree eklemek güvenlidir; mevcut değişikliklere dokunulmaz.

## 5. Sorun giderme

### `Agent loop zaten çalışıyor.`

Aynı worktree'de ikinci controller başlatıldı (`flock`). Beklenen davranış.
Gerçekten takılı kaldıysa: `devam durum` ile aşamaya bak, süreç yoksa
`agentctl.sh cleanup`.

### `Görev <id> zaten claim edilmiş`

Başka bir worktree aynı görevi almış. Doğru davranış: o worktree'de devam et.
Sahibi ölmüşse:

```bash
tools/agent-loop/agentctl.sh cleanup --task <id>     # bayat claim'i bırakır
```

Canlı bir claim asla otomatik devralınmaz.

### `agent-loop başlatılamadı (rol yapılandırması geçersiz)` — exit 36

`.agent/config/agents.yaml` ayrıştırılamadı veya doğrulanamadı. Sık nedenler:
liste sözdizimi (`- item`), üç seviye iç içe alan, bilinmeyen ajan adı,
`reviewer` alanına otomatik çalışamayan bir ajan (ör. `qoder`) verilmesi.
Fail-closed'dur: düzeltilene kadar hiçbir ajan çalışmaz.

### `Çalışma ağacında değişiklik yok: beyan doğrulanamadı`

Handoff ajanı "tamam" dedi ama dosyalar değişmemiş. IDE'de kaydedilmemiş
olabilir. Kaydet ve `devam "qoder tamam"` komutunu tekrar ver. Sahte ilerleme
üretilmez.

### Testler başarısız — ürün hatası mı, ortam mı?

Kanıt kaydına bak:

```bash
jq -r '.failure_class, .command, .exit_code' .agent/evidence/tests/<TASK-ID>/*.json
```

`ENVIRONMENT_FAILURE` veya `DEPENDENCY_FAILURE` ise ürün defekti değildir;
PostgreSQL/Docker/dış servisi ayağa kaldır, sonra `devam`. `PRODUCT_DEFECT` ise
onarım turu uygulayıcıya gider.

### PostgreSQL preflight başarısız (`ENVIRONMENT_BLOCK`)

Görev entegrasyon gerektiriyor ama veritabanına ulaşılamıyor. Sahte PASS
üretilmez. `DATA_QUALITY_POSTGRES_TEST_URL` ve `DATA_QUALITY_DATABASE_SCHEMA`
değerlerini env-file'da kontrol et, servisi başlat, `devam`.

### Onarım turu tükendi (`WAITING_HUMAN`)

`MAX_REPAIR_ROUNDS` aşıldı. Review çıktısını oku, kararını ver:
`devam "kararın"`. Karar onarım bütçesini sıfırlar.

### Sağlayıcı kotası aşama ortasında bitti

`FALLBACK_FROM` / `FALLBACK_TO` satırları `.agent-handoff/logs/<rol>-failures.log`
dosyasındadır. Devir yapılmadıysa nedenleri: `fallback_on_quota_error: false`,
yedek ajan otomatik çalışamıyor (Qoder), veya hata kota sınıfında değil.

## 6. Bakım

```bash
bash tools/agent-loop/tests/run.sh          # controller test paketi (gerçek ajan çağırmaz)
tools/agent-loop/agentctl.sh cleanup        # bayat claim + artık geçici dosya
```

Runbook'taki hiçbir komut commit, merge, push, PR veya `git reset`/`clean`
çalıştırmaz. Bu işlemler her zaman kullanıcının kararıdır.

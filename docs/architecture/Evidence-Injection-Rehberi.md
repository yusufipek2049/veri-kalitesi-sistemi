# Evidence Injection Rehberi

Bu rehber, agent-loop pipeline'ında model prompt'larına kanıt enjeksiyonu yapılırken
uyulması gereken kuralları tanımlar. Amaç, KV-cache etkinliğini korurken modelin
dikkatini dağıtacak "distraktör" içeriklerden kaçınmaktır.

## Tasarım İlkeleri

1. **Terminoloji Eşleştirme**: Enjekte edilen kanıtlar, görev kontratında kullanılan
   terminoloji ile tutarlı olmalıdır. Farklı terimler kullanmak modelin dikkatini
   dağıtır ve hallucination riskini artırır.

2. **Distraktör Yasağı**: Kanıt blokları, görevle ilgisi olmayan bilgiler içermemelidir.
   Her satır doğrudan ya (a) önceki hatayı açıklamalı, (b) kabul kriterini desteklemeli,
   veya (c) scope'u netleştirmelidir.

3. **Biçim Varyasyonu**: Aynı yapıdaki kanıtların tekrar eden formatları, modelin
   "pattern matching" davranışını zayıflatır. `serialize_tool_output()` fonksiyonu
   3 farklı format varyasyonu kullanarak bu etkiyi azaltır.

4. **KV-Cache Koruma**: Format varyasyonu, KV-cache prefix'ini etkilemeyecek konuma
   yerleştirilir. Değişken içerik, prompt'un sonuna yakın bloklarda tutulur.

## Terminoloji Eşleştirme Kuralları

### Eşleştirme Tablosu

| Görev Kontratında Kullanılan | Kanıt Enjeksiyonunda Kullanılacak |
|------------------------------|-----------------------------------|
| `acceptance_criteria`        | `kabul_kriteri` veya `AC-XX`     |
| `scope.hint`                 | `kapsam_ipucu` veya `hint`       |
| `source_docs`                | `kaynak_doküman` veya `SRS-XX`   |
| `repository.root`            | `repo_kök` veya `ROOT`           |
| `task.objective`             | `görev_hedefi` veya `objective`  |

### Yasaklı Dönüşümler

Aşağıdaki dönüşümler **KESİNLİKLE YASAKTIR**:

- `acceptance_criteria` → `requirements` (anlam daralması)
- `scope.hint` → `files_to_edit` (yanlış yönlendirme)
- `source_docs` → `references` (belirsizlik)

## Distraktör Yasağı

### Distraktör Sınıfları

1. **Bilgi Fazlalığı**: Aynı gerçeği farklı kelimelerle tekrar etmek.
   - ❌ Yanlış: "Testler başarılı oldu. Tüm birim testleri geçti."
   - ✅ Doğru: "Testler başarılı oldu (exit 0, 47 passed)."

2. **İlgisiz Bağlam**: Görevle ilgisi olmayan geçmiş olaylar.
   - ❌ Yanlış: "Önceki iterasyonda PostgreSQL bağlantı hatası vardı (bu görev PG gerektirmez)."
   - ✅ Doğru: "Önceki iterasyonda hata: `ImportError: module X not found`."

3. **Spekülatif İçerik**: Kesinlik taşımayan ifadeler.
   - ❌ Yanlış: "Muhtemelen bu dosyayı değiştirmen gerekebilir."
   - ✅ Doğru: "Değiştirilecek dosya: `src/veri_kalitesi/rules/engine.py` (satır 42-58)."

## Biçim Varyasyonu

`serialize_tool_output()` fonksiyonu, tool çıktısını 3 farklı formatta sunabilir:

### Format 0: Blok Kod (varsayılan)

```
## Tool Output

\`\`\`
<çıktı içeriği>
\`\`\`
```

### Format 1: Inline Özet

```
Tool çıktısı: <ilk satır> (toplam <N> satır)
```

### Format 2: YAML Metadata + İçerik

```
---
tool: <tool_adı>
lines: <satır_sayısı>
truncated: <true|false>
---
<çıktı içeriği>
```

### Varyasyon Seçimi

```bash
# RANDOM % 3 ile format seçimi (deterministik tohum kullanılmaz)
FORMAT_VARIANT=$(( RANDOM % 3 ))
serialize_tool_output "$tool_name" "$output" "$FORMAT_VARIANT"
```

## KV-Cache Koruma

### Değişken İçerik Konumu

Değişken içerik (format varyasyonu, kanıt blokları) prompt'un **sonuna yakın**
bloklarda tutulur. Bu, KV-cache prefix'inin sabit kalmasını sağlar.

```
[Prompt yapısı]

1. Sistem promptu (sabit)           ← KV-cache'de kalır
2. Görev kontratı (yarı-sabit)      ← KV-cache'de kalır
3. Runtime context (değişken)       ← Son 20% içinde
4. Kanıt blokları (değişken)        ← Son 15% içinde
5. Format varyasyonu (değişken)     ← Son 10% içinde
```

### Uygulama

`run_implementer()` fonksiyonunda, kanıt enjeksiyonu ve format varyasyonu
prompt'un sonunda yapılır:

```bash
{
  cat "$PROMPTS/implementer.md"                    # Sabit prefix
  printf '\n## Runtime context\n\n...'             # Yarı-sabit
  # ... görev kontratı ...
  collect_error_evidence "$iteration"              # Değişken (sonda)
  if should_vary_format; then                      # Değişken (en son)
    serialize_tool_output ...
  fi
} > "$input"
```

## Doğrulama

`scripts/verify_context_engineering.sh` scripti aşağıdakileri kontrol eder:

1. `serialize_tool_output()` fonksiyonunun varlığı
2. Fonksiyonun 3 format varyasyonu desteklemesi
3. `implementer.md`'de Evidence Injection yönergesinin varlığı
4. `Evidence-Injection-Rehberi.md` dokümanının varlığı

## Referanslar

- [Context-Cache-Politikasi.md](Context-Cache-Politikasi.md)
- [Context-Compaction-Politikasi.md](Context-Compaction-Politikasi.md)
- [Context-Engineering-Oturum-Rehberi.md](Context-Engineering-Oturum-Rehberi.md) — Oturum 6

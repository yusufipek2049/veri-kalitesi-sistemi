@AGENTS.md

## Claude Code bağlam yönetimi

- Depoyu topluca tarama; önce hedefli dosya, sembol, gereksinim ID'si veya modül yolu ara.
- Büyük araştırma, test ve log incelemelerini mümkün olduğunda ayrı subagent içinde yürüt.
- Ana konuşmaya ham terminal çıktısı veya uzun dosya içerikleri taşıma.
- Her iterasyonda yalnız bir ürün artımı uygula ve rapor verdikten sonra dur.
- Geniş kod keşfi için `context-explorer`, test/log işlemleri için `test-runner` subagent'larını kullan.

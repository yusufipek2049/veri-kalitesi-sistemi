---
type: canonical-decision-register
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-24
---

# Skorlama, Sentetik Veri ve İkinci Faz Karar Kayıtları

Bu belge `DQ-SCR-*`, ölçüm yeterliliği, sentetik veri ve `OPEN-026–OPEN-036` ikinci faz kararlarını kanonik olarak toplar.

> Tam tarihsel kaynak: [Arşivlenmiş karar günlüğü](../../../docs/archive/project-memory-2026-07-24/Alinan-Kararlar.md).

## 2026-07-21 — DQ-SCR Skorlama Karar Paketi

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| `DQ-SCR-001`–`DQ-SCR-033` bağlayıcı proje kararıdır. Ham veri kalitesi skoru; kapsam, güven, dataset kritikliği/veri riski ve teknik sağlıktan ayrı tutulur. Skor kural → veri öğesi → boyut → dataset hiyerarşisinde, sürümlü politika ve kritik kural kontrolüyle hesaplanır. | Tek yüzde; teknik hatayı kalite hatasına, düşük kapsamı güvenilir kaliteye veya kritikliği kalite ölçümüne dönüştürebilir. Açıklanabilirlik, anti-gaming ve tarihsel yeniden üretilebilirlik için model/politika sürümleri ile görevler ayrılığı gerekir. | Mevcut kural ağırlıklı ortalamayı tek başına korumak; dataset kritikliğini kaynak kalite skoruna ağırlık olarak katmak; kapsam/güven/risk/teknik durumu hesaplama detayında eritmek; ham skoru override ile değiştirmek. | `04.06-Skorlama.md` kanonik karar kaydıdır; `ADR-015` hedef mimariyi tanımlar. Dataset kritikliğini kalite skoruna katan tarihsel yaklaşım `Superseded` oldu, ancak geçmiş skorlar değişmez. Üretim eşik/ağırlık/veto/güven/risk değerleri aktif, sürümlü ve onaylı politika kaydından çözülür; kayıt yoksa ilgili sonuç fail-closed üretilmez. Bu dokümantasyon kararı runtime uygulama veya banka onayı değildir. |

## 2026-07-21 — Ölçüm Yeterliliği Hedef Tasarımı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Kural sayaçları kanonik değişmezlerle tutulacak; ham ve nihai kalite skoru, kritik kural durumu, ölçüm yeterliliği, kullanım kararı ve teknik çalışma durumu ayrı üretilecektir. Yeterlilik kapsam, örneklem, güncellik, teknik başarı, sürüm, kritik kontrol ve kanıt kapılarıyla değerlendirilir. | Tek skor alanı; yüksek kaliteyi yetersiz ölçümle, teknik hatayı kalite düşüşüyle veya kritik kontrolü ağırlıklı ortalamayla karıştırabilir. | Yalnız mevcut skor statülerini genişletmek; teknik hatayı sıfır skor yapmak; yüksek skor varsa ölçümü otomatik yeterli saymak; kritik sonucu ham skora gömmek. | [Kanonik tasarım](../../architecture/Veri-Kalitesi-Skorlama-ve-Olcum-Yeterliligi.md), FR-046–FR-053 ve AC/TS-039–047 hedef sözleşmedir. Eşik, minimum kapsam/güven, geçerlilik, kanıt/onay, kullanım/blokaj ve remediation değerleri aktif sürümlü politika kaydından çözülür; kayıt yoksa olumlu yeterlilik veya kullanım kararı üretilmez. Bu karar runtime uygulaması veya banka onayı değildir. |

## 2026-07-21 — Sentetik Veri ve Gizlilik Hedef Tasarımı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Sentetik veri sürümlü dataset politikası, deterministik seed/run lineage'ı, temel üretimden ayrı kusur enjeksiyonu ve runtime kural/skor motorundan bağımsız ground truth ile yönetilecektir. Sentetik veri anonimlik kanıtı değildir; test olayları yalnız izole fake/sandbox hedeflere gider. | Üretim verisini birebir kopyalamadan gerçekçi görev faydası sağlamak, self-validation ve yeniden tanımlama riskini engellemek gerekir. | Sentetik vakaları kod içi sabitlerle üretmek; yalnız kimlik değiştirerek anonim saymak; skor motorunun kendi sonucunu beklenen değer yapmak; sentetik performans testini nihai kabul saymak. | [Kanonik tasarım](../../architecture/Sentetik-Veri-ve-Gizlilik-Stratejisi.md), `ADR-016`, `FR-088–FR-096` ve `AC/TS-048–056` hedef sözleşmedir. Nicel eşik/tolerans aktif politikada zorunludur ve eksikse `BLOCKED`; üretim profili/örneği kullanımı varsayılan kapalıdır. `OPEN-014` nihai performans kabulü korunur. Bu karar runtime uygulaması, hukuki anonimlik veya banka onayı değildir. |

## 2026-07-22 — Kanıta Dayalı Karar Sistemi Hedef Kararı

| Karar | Gerekçe | Değerlendirilen alternatif | Sonuç |
| --- | --- | --- | --- |
| Sistem ikinci fazda kullanım amacı bazlı uygunluk, kaynaklı etki/teşhis/öneri, değişiklik simülasyonu, lineage, yeniden üretim manifesti, politika kontrollü remediation, data contract, adaptif tarama, gizlilik korumalı inceleme, kalite borcu, chaos kontrol yeterliliği ve kanıt paketi sağlayacaktır. Skor ve dört güven türü ayrı kalacak; LLM/model tek başına üretim değişikliği yapamayacaktır. | Genel skor tek başına kullanım uygunluğunu, ölçüm/teşhis güvenini, etkiyi ve kararın yeniden üretilebilirliğini kanıtlamaz. | Yalnız yeni dashboard alanları eklemek; kanıtsız öneri; korelasyonu neden saymak; otomasyon yetkisini model çıktısına vermek; tüm kavramlar için ayrı ve tekrarlı tablolar oluşturmak. | `ADR-019`, `FR-097–FR-111`, `UC-018–UC-021`, `RULE-018–RULE-023` ve `AC/TS-057–071` hedef sözleşmedir. Mevcut MVP korunur. Ayrıntılı politika yönleri `OPEN-026–OPEN-036` teknik kararlarıyla kesinleşmiştir; runtime uygulaması ve banka onayı ayrıca kanıtlanır. |

## 2026-07-22 — OPEN-026–OPEN-036 Kesinleşmiş Teknik Kararları

Karar referansı: `USER-DECLARATION-2026-07-22-OPEN-026-036`. Kullanıcının
onayladığı bu kayıtlar teknik ve ürün yönünü kesinleştirir. Banka uyum onayı,
üretim konfigürasyonu veya `ApprovedByBank` sonucu oluşturmaz.

| ID | Kesinleşen karar | Durum |
| --- | --- | --- |
| OPEN-026 | Kullanım amacı profilleri hibrit yönetişimle yönetilecektir: katalog şeması, sözlük ve yaşam döngüsü merkezi; dataset profili Data Owner sahipliğinde olacaktır. Boyut, ağırlık, eşik, kritik alan ve bloke edici kural değerleri onaylı ve sürümlü profilde tutulacak; eksik veya etkin olmayan profil olumlu kullanım kararı üretmeyecektir. | KararAlındı |
| OPEN-027 | Etki değerlendirmesi gözlenen veriyi önceleyecek; her bileşen `Observed`, `Calculated`, `Estimated` veya `Unknown` olarak kaynak, formül, veri zamanı ve güvenle saklanacaktır. Parasal değer yalnız otoriter Finans/Risk kaynağına veya onaylı formüle dayanacak; desteklenmeyen bileşenler tek bir toplam etki sayısında birleştirilmeyecektir. | KararAlındı |
| OPEN-028 | Lineage ve sahiplik için kurumsal veri kataloğu sistem-of-record olacaktır. Uygulama OpenLineage uyumlu sürümlü olay sözleşmesiyle run/job/dataset ve kolon ilişkilerini alacak, W3C PROV `Entity/Activity/Agent` anlamlarıyla eşleyebilecek ve rakip ana katalog yerine değişmez snapshot/digest ile eksik veya eski kapsama durumunu saklayacaktır. | KararAlındı |
| OPEN-029 | İlk üretim sürümünde yalnız `DeterministicRule`, `IncidentSimilarity` ve auditli `ExpertInput` önerileri etkin olacaktır. İstatistiksel mekanizmalar bağımsız doğrulama ve kalibrasyondan sonra açılabilir. `LLMAssisted` üretimde kapalıdır ve sağlayıcı seçilmemiştir; ileride açılsa bile yalnız `SuggestOnly` olabilir. Her öneri minimum kanıt, mekanizma/sürüm, bağımsız güven ve karşı kanıt taşıyacaktır. | KararAlındı |
| OPEN-030 | `NeverModifyProductionData` değişmez sınır, `SuggestOnly` varsayılandır. `ApprovalRequired` yalnız sistemin sahip olduğu nesne ve iş akışlarını etkileyebilir. `AutoRerun` aynı değişmez girdi üzerinde idempotent, `AutoQuarantine` yalnız sistem çıktısının yayımlanmasını durduracak biçimde çalışabilir; `AutoFixLowRisk` ilk fazda yalnız üretim dışındadır. Dry-run, etki, görevler ayrılığı, canary, yeniden doğrulama, rollback ve audit zorunludur; kritik audit hatası fail-closed sonuçlanır. | KararAlındı |
| OPEN-031 | Chaos deneyi ilk fazda yalnız izole üretim dışı ortamda ve sentetik veriyle yapılacaktır; üretim ve gerçek müşteri verisi yasaktır. Deney sürümlü ve sınırlı fault profili, Data Owner ile Bilgi Güvenliği/Operasyon onayı, planlı pencere ve doğrulanmış rollback gerektirir. Kapsam/ortam kanıtı uyuşmazlığı, gerçek veri, audit/telemetri kaybı, rollback yokluğu, beklenmeyen downstream etkisi veya politika bütçesi aşımı deneyi derhal durdurur. | KararAlındı |
| OPEN-032 | Veri sözleşmesi sahipliği ve yayımı için kurumsal veri kataloğu sistem-of-record olacaktır; uygulama değişmez sözleşme sürümü ve değerlendirme kanıtı saklayacaktır. Üretici taslak oluşturur, Data Owner onaylar, breaking change için tüketici sahipleri bilgilendirilir. Etki simülasyonu ve onay olmadan breaking change etkinleşmez; istisna kapsamlı, süreli, maker-checker onaylı ve auditlidir. | KararAlındı |
| OPEN-033 | Adaptif tarama ilk fazda deterministik politika motoruyla seçilecektir; makine öğrenmesi tabanlı strateji seçici kullanılmayacaktır. Kritik/bloke edici kontrollerde mümkünse tam tarama, sonra partition; örnekleme yalnız kullanım ve kaynak politikası izin verip kapsama/güven koşulları sağlandığında seçilir. Karar gerekçe, tahmini maliyet, kapsam, güven ve seed taşır; politika yoksa otomatik strateji değişmez veya yeni çalışma reddedilir. | KararAlındı |
| OPEN-034 | Varsayılan inceleme toplulaştırılmış, maskeli, fingerprint veya güvenli referans görünümüdür. Hassas değerlerde düz/tuzsuz hash kullanılmayacak; deterministik token kurumsal kriptografik/tokenizasyon servisi ve KMS/HSM anahtarıyla üretilecektir. Gerçek kayıt erişimi istisnai, gerekçeli, kapsamlı, süreli ve auditli olacaktır; yüksek hassasiyette maker-checker gerekir. Varsayılan indirme/kopyalama kapalı, sentetik örnek öncelikli ve katalog/DLP kesintisi fail-closed olacaktır. | KararAlındı |
| OPEN-035 | `QualityDebtScoreV1`, gerekli politikalar ve beş bileşen mevcutsa `0–100` aralığında yaş, tekrar, istisna, etki ve kontrol açığı normalize oranlarının eşit ağırlıklı ortalaması olarak hesaplanacaktır. `EvidenceCoverage` ayrı gösterilecek; herhangi bir gerekli bileşen veya politika yoksa skor üretilmeyip bileşen `Unknown` olacaktır. Operasyonel maliyet ve finansal etki ayrı kaynaklı alanlardır. Data Owner borç kaydının, Veri Yönetişimi formülün, Risk Yönetimi etki doğrulamasının sahibidir; hedef tarih onaylı politikadan gelir. | KararAlındı |
| OPEN-036 | Kanıt paketinin otoriter çıktısı RFC 8785 ile kanonikleştirilmiş JSON manifest ve referanslı artefaktlardır. Manifest mevcut SHA-256 özetiyle doğrulanacak, kurum onaylı KMS/HSM ile imzalanacak ve değişmez/WORM uyumlu depoda tutulacaktır. İnsan okunur özet ikincildir. Dışa aktarma asenkron, DLP ve gerektiğinde maker-checker kontrollü; şifreli, süreli ve politika gerektiriyorsa watermark'lıdır. Paket ham hassas veriyi kopyalamaz; saklama, legal hold ve imha kanıtı kayıt sınıfı politikasından çözülür. | KararAlındı |

Sayısal üretim eşikleri, fault büyüklükleri, saklama süreleri ve ürün adları bu
kararla uydurulmamıştır. Bunlar ilgili aktif sürümlü politika veya mevcut
`OPEN-BNK-*` inceleme kayıtlarından çözülür; kayıt yoksa güvenli davranış
uygulanır.

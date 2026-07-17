---
type: srs-section
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "11"
generated_at: 2026-07-16
tags:
  - srs
  - traceability
---

# Gereksinim İzlenebilirlik Matrisi

Bu matris, iş hedeflerini fonksiyonel gereksinim, kullanım senaryosu, iş kuralı, kabul kriteri ve test senaryosuyla ilişkilendirir. Fonksiyonel gereksinimler aralık halinde gösterilmiş olsa da FR-001–FR-087'nin tamamı en az bir satırda kapsanmıştır.

| İş Gereksinimi ID | Fonksiyonel Gereksinim ID | Kullanım Senaryosu ID | İş Kuralı ID | Kabul Kriteri ID | Test Senaryosu ID | Öncelik |
| --- | --- | --- | --- | --- | --- | --- |
| BR-001 | FR-001–FR-006 | UC-001 | RULE-001, RULE-009 | AC-001–AC-003 | TS-001–TS-003 | Must |
| BR-001 | FR-007–FR-014 | UC-002, UC-003 | RULE-002, RULE-009 | AC-004–AC-006 | TS-004–TS-006 | Must |
| BR-001, BR-002 | FR-015–FR-022 | UC-004 | RULE-002, RULE-010, RULE-012 | AC-007, AC-008, AC-025 | TS-007, TS-008, TS-025 | Must |
| BR-002, BR-005 | FR-023–FR-030 | UC-005 | RULE-001, RULE-005, RULE-007 | AC-006, AC-025 | TS-006, TS-025 | Must |
| BR-002, BR-005 | FR-031–FR-035 | UC-006 | RULE-002, RULE-003, RULE-010 | AC-006, AC-009 | TS-006, TS-009 | Must/Should |
| BR-002, BR-003 | FR-036–FR-039 | UC-007, UC-008 | RULE-003, RULE-011, RULE-012 | AC-009, AC-024 | TS-009, TS-024 | Must |
| BR-003 | FR-040–FR-045 | UC-008 | RULE-003, RULE-011 | AC-010, AC-012, AC-024 | TS-010, TS-012, TS-024 | Must |
| BR-001, BR-005, BR-006 | FR-046–FR-053 | UC-009 | RULE-003–RULE-005 | AC-009–AC-014 | TS-009–TS-014 | Must |
| BR-001, BR-002, BR-006 | FR-054–FR-058 | UC-010 | RULE-004, RULE-009 | AC-011, AC-014 | TS-011, TS-014 | Must/Should |
| BR-003, BR-004 | FR-059–FR-063 | UC-011, UC-012 | RULE-006, RULE-011 | AC-010, AC-015, AC-016 | TS-010, TS-015, TS-016 | Must/Should |
| BR-003, BR-004, BR-008 | FR-064–FR-070 | UC-011, UC-013, UC-014 | RULE-006, RULE-013 | AC-015–AC-018 | TS-015–TS-018 | Must |
| BR-004, BR-008 | FR-071 | UC-013, UC-014 | RULE-011 | AC-019 | TS-019 | Should |
| BR-001, BR-006, BR-007, BR-008 | FR-072–FR-076 | UC-015 | RULE-008–RULE-010 | AC-020, AC-021, AC-023 | TS-020, TS-021, TS-023 | Must/Should |
| BR-007 | FR-077–FR-079 | UC-016 | RULE-007, RULE-009 | AC-022, AC-026 | TS-022, TS-026 | Must |
| BR-001, BR-003, BR-004 | FR-080–FR-084 | UC-002, UC-008, UC-013 | RULE-009, RULE-011 | AC-003, AC-019, AC-024 | TS-003, TS-019, TS-024 | Must |
| BR-004 | FR-085 | UC-012 | RULE-011 | AC-016 | TS-016 | Could |
| BR-001, BR-005 | FR-086 | UC-004 | RULE-007 | AC-025 | TS-025 | Could |
| BR-004, BR-008 | FR-087 | UC-013, UC-014 | RULE-003, RULE-011 | AC-019 | TS-019 | Should |


**İzlenebilirlik kontrol sonucu:** BR-001–BR-008, FR-001–FR-087, UC-001–UC-016, RULE-001–RULE-015 ve AC-001–AC-026 matris kapsamındadır. Kapsam aralıkları ayrıntılı test yönetim aracına aktarılırken tekil satırlara bölünmelidir.

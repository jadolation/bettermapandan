# Filipino pilot: 50 strings

Status: review draft. Do not import into `locales/fil.json`, `page-meta.json`, or
`services.json` until the rows marked `Medium` are reviewed and this pilot is
approved.

## How to review

- Compare the English source with the current Filipino and the proposed Filipino.
- Approve the rule as well as the string; the rule should apply consistently.
- Mark a row `Review` if the meaning, register, or terminology is uncertain.
- Preserve official names, acronyms, amounts, dates, IDs, URLs, and source
  values exactly.

Confidence:

- `High`: mechanical grammar, capitalization, or approved term.
- `Medium`: naturalness or product-label choice needs editorial approval.
- `Review`: meaning or terminology needs a Filipino editor or subject reviewer.

## Navigation and UI

| # | Source | English | Current FIL | Proposed FIL | Rule | Confidence |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | `nav.home` | Home | Pangunahing Pahina | Pangunahing Pahina | Approved navigation term | High |
| 2 | `nav.services` | Services | Mga Serbisyo | Mga Serbisyo | Approved | High |
| 3 | `nav.government` | Government | Pamahalaan | Pamahalaan | Approved | High |
| 4 | `nav.statistics` | Statistics | Estadistika | Estadistika | Approved | High |
| 5 | `nav.search` | Search | Hanapin | Hanapin | Approved | High |
| 6 | `nav.support` | Support | Suporta | Suporta | Approved | High |
| 7 | `action_hub.budget` | Budget | Badyet | Badyet | Approved | High |
| 8 | `action_hub.hotlines` | Hotlines | Mga Hotline | Mga hotline | Sentence case; established loanword | Medium |
| 9 | `common.show_subsections` | Show subsections | Ipakita ang mga subseksyon | Ipakita ang mga subseksyon | Sentence case | High |
| 10 | `common.hide_subsections` | Hide subsections | Itago ang mga subseksyon | Itago ang mga subseksyon | Sentence case | High |

## Forms and errors

| # | Source | English | Current FIL | Proposed FIL | Rule | Confidence |
| ---: | --- | --- | --- | --- | --- | --- |
| 11 | `report_hub.report_error_label` | What is incorrect? | Ano ang mali? * | Ano ang mali? * | Direct question; preserve required marker | High |
| 12 | `report_hub.report_correction` | Correct information | Tamang impormasyon | Tamang impormasyon | Direct label | High |
| 13 | `report_hub.report_source` | Source / proof link | Pinagmulan / Link ng Patunay | Pinagmulan / link ng patunay | Sentence case; `Pinagmulan` approved | Medium |
| 14 | `report_hub.contribute_category` | Category * | Kategorya * | Kategorya * | Established loanword | High |
| 15 | `report_hub.contribute_title` | Title / information name * | Pamagat / Pangalan ng Impormasyon * | Pamagat / pangalan ng impormasyon * | Sentence case | High |
| 16 | `report_hub.suggest_usecase` | Use case / why it matters | Use Case / Bakit mahalaga | Halimbawa ng paggamit / bakit mahalaga | Remove English label; sentence case | Medium |
| 17 | `report_hub.submit_copy` | Copy draft text | Kopyahin ang draft text | Kopyahin ang draft na teksto | Natural noun phrase | Medium |
| 18 | `report_hub.toast_copy` | Copied to clipboard! Paste it into your email app. | Nakopya sa clipboard! I-paste ito sa iyong email app. | Nakopya sa clipboard! I-paste ito sa email app mo. | Concise direct address | Medium |

## Service metadata

| # | Source | English | Current FIL | Proposed FIL | Rule | Confidence |
| ---: | --- | --- | --- | --- | --- | --- |
| 19 | `service_page.office` | Responsible Office: | Responsableng Opisina: | Responsableng opisina: | Sentence case | High |
| 20 | `service_page.classification` | Classification: | Klasipikasyon: | Uri: | Plain-language UI label | Medium |
| 21 | `service_page.processing_time` | Processing Time: | Oras ng Pagproseso: | Tagal ng pagproseso: | Plain language; sentence case | Medium |
| 22 | `service_page.fee` | Fee: | Bayarin: | Bayad: | Plain language | Medium |
| 23 | `service_page.where_to_apply` | Where to Apply: | Saan Mag-aapply: | Saan mag-apply: | Correct hyphenation; sentence case | High |
| 24 | `service_page.contact` | Contact: | Makipag-ugnayan: | Kontak: | Shorter UI label; established loanword | Medium |
| 25 | `service_page.requirements` | Requirements | Mga Kinakailangan | Mga kinakailangan | Sentence case | High |
| 26 | `service_page.procedure` | Procedure | Prosedura | Mga hakbang | Plain-language UI label | Medium |
| 27 | `service_page.source` | Source: | Pinagmulan: | Pinagmulan: | Approved term | High |
| 28 | `service_page.last_updated` | Last Updated: | Huling Na-update: | Huling na-update: | Sentence case | High |

## Service steps

These examples come from `services.json` procedure arrays. The English text is
the current source; no Filipino procedure text exists yet.

| # | Source | English | Current FIL | Proposed FIL | Rule | Confidence |
| ---: | --- | --- | --- | --- | --- | --- |
| 29 | `birth-certificate.procedure[0]` | Visit the Municipal Civil Registrar’s Office and present valid identification. | — | Pumunta sa Municipal Civil Registrar at magpakita ng wastong ID. | Imperative; official name stays English | High |
| 30 | `birth-certificate.procedure[1]` | Fill out the request form and provide the necessary supporting documents. | — | Punan ang form ng kahilingan at isumite ang mga kinakailangang dokumento. | Imperative; plain verbs | Medium |
| 31 | `birth-certificate.procedure[2]` | Pay the certification fee at the Municipal Treasurer’s Office. | — | Magbayad para sa sertipikasyon sa Municipal Treasurer’s Office. | Imperative; official name stays English | High |
| 32 | `birth-certificate.procedure[3]` | Receive the certified birth certificate upon release. | — | Kunin ang sertipiko ng kapanganakan kapag available na. | Avoid literal “upon release” | Medium |
| 33 | `business-permit.procedure[0]` | Fill up the UNIFIED form and submit necessary requirements for verification (10 min). | — | Punan ang UNIFIED form at isumite ang mga kinakailangan para sa beripikasyon (10 min). | Imperative; preserve form name | High |
| 34 | `business-permit.procedure[2]` | BPLO endorses applicant to various offices... | — | Ipapasa ng BPLO ang aplikante sa iba’t ibang opisina... | Natural actor focus; preserve BPLO | Medium |
| 35 | `business-permit.procedure[3]` | Pay fees and charges at the Treasury Office. | — | Magbayad ng mga bayarin at singil sa Treasury Office. | Imperative; plain terms | High |
| 36 | `business-permit.procedure[5]` | Claim business plate and sticker at the Treasury Office (10 min). | — | Kunin ang business plate at sticker sa Treasury Office (10 min). | Imperative; preserve official terms | High |
| 37 | `building-permit.procedure[0]` | Obtain a zoning clearance from the MPDC / Zoning Office. | — | Kumuha ng zoning clearance sa MPDC / Zoning Office. | Replace `Obtain` with `Kumuha` | High |
| 38 | `marriage-license.procedure[3]` | Wait for the 10-day publication period. | — | Maghintay hanggang matapos ang 10-araw na publikasyon. | Natural time clause | Medium |
| 39 | `marriage-license.procedure[4]` | After publication, claim the marriage license from the MCR. | — | Pagkatapos ng publikasyon, kunin ang marriage license sa MCR. | Imperative; preserve official document name | High |
| 40 | `health-consultation.procedure[0]` | Register in Electronic Medical Record (EMR). Midwife registers new patients and encodes data. | — | Magparehistro sa Electronic Medical Record (EMR). Irerehistro ng midwife ang mga bagong pasyente at ie-encode ang datos. | Natural focus; preserve EMR | Medium |

## Page metadata

These are UI labels, not official names, so they should be localized.

| # | Source | English | Current FIL | Proposed FIL | Rule | Confidence |
| ---: | --- | --- | --- | --- | --- | --- |
| 41 | `page-meta.json → about.html → fil.hero_eyebrow` | About Better Mapandan | About Better Mapandan | Tungkol sa Better Mapandan | Localize non-official label | High |
| 42 | `page-meta.json → government.html → fil.hero_eyebrow` | Government Directory | Government Directory | Direktoryo ng Pamahalaan | Localize non-official label | High |
| 43 | `page-meta.json → transparency.html → fil.hero_eyebrow` | Transparency | Transparency | Transparency | Retain approved term | High |
| 44 | `page-meta.json → support/accessibility.html → fil.hero_eyebrow` | Accessibility Statement | Accessibility Statement | Pahayag sa Aksesibilidad | Localize non-official label | High |
| 45 | `page-meta.json → support/privacy.html → fil.hero_eyebrow` | Privacy Policy | Privacy Policy | Patakaran sa Privacy | Localize non-official label | High |
| 46 | `page-meta.json → support/report.html → fil.hero_eyebrow` | Civic Contribution Hub | Civic Contribution Hub | Hub ng Pakikilahok ng Mamamayan | Match the approved report-hub title | Medium |

## Source and legal

| # | Source | English | Current FIL | Proposed FIL | Rule | Confidence |
| ---: | --- | --- | --- | --- | --- | --- |
| 47 | `footer.source_code` | Source Code (GitHub) | Source Code (GitHub) | Source code (GitHub) | Sentence case; technical term | Medium |
| 48 | `footer.privacy` | Privacy Policy | Patakaran sa Privacy | Patakaran sa privacy | Sentence case | High |
| 49 | `footer.terms` | Terms of Use | Mga Tuntunin ng Paggamit | Mga tuntunin ng paggamit | Sentence case | High |
| 50 | `common.disclaimer` | Independent civic transparency portal disclaimer | Ang Better Mapandan ay isang independent na civic transparency portal. Ito ay hindi opisyal na website ng pamahalaan at hindi kaakibat, ineendorso, o pinapatakbo ng Munisipalidad ng Mapandan o ng anumang ahensiya ng pamahalaan. | Ang Better Mapandan ay isang independiyenteng portal ng transparency para sa mamamayan. Hindi ito opisyal na website ng pamahalaan at hindi kaakibat, ineendorso, o pinapatakbo ng Bayan ng Mapandan o ng anumang ahensya ng pamahalaan. | Remove English `independent` and `civic transparency portal`; fix agency term | Medium |

## Review notes

- Rows 20–26 change visible UI labels. Approve the label, not only the string.
- Rows 30, 34, 38, 40, and 50 need an editorial naturalness check.
- Row 50 needs a legal/policy check because it is a disclaimer.
- Do not use the DOCX Filipino text for rows 29–40 without comparison; the DOCX
  contains widespread `sa ang`/`ng ang` errors and English word-order calques.
- After approval, move these strings into the appropriate locale, page metadata,
  or service `_fil` fields. Do not create a translation overlay.

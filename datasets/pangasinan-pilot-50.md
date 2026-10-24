# Pangasinan pilot: 50 strings

Status: speaker-review draft. Do not import into `locales/pag.json`,
`page-meta.json`, or `services.json` until the rows marked `Review` are checked
by a fluent Pangasinan speaker.

## How to review

- Compare the English source, current Pangasinan, and proposed Pangasinan.
- Approve the rule as well as the string.
- Mark a row `Review` when naturalness, focus, or terminology is uncertain.
- Preserve official names, acronyms, amounts, dates, IDs, URLs, and source
  values exactly.
- Do not apply global replacements for `ya`, `et`, `say`, or `nen say`.

Confidence:

- `High`: marker, capitalization, or mechanical correction.
- `Medium`: plausible but needs an editorial or terminology decision.
- `Review`: needs a fluent Pangasinan speaker.

## Navigation and UI

| # | Source | English | Current PAG | Proposed PAG | Rule | Confidence |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | `nav.home` | Home | Abong | Abong | Approved navigation term | High |
| 2 | `nav.services` | Services | Saray Serbisyo | Saray serbisyo | Sentence case | High |
| 3 | `nav.government` | Government | Gobierno | Gobierno | Approved | High |
| 4 | `nav.statistics` | Statistics | Estadistika | Estadistika | Approved | High |
| 5 | `nav.search` | Search | Anapen | Anapen | Approved | High |
| 6 | `nav.support` | Support | Saranay | Saranay | Approved | High |
| 7 | `action_hub.budget` | Budget | Badyet | Badyet | Approved | High |
| 8 | `action_hub.hotlines` | Hotlines | Hotline | Saray hotline | Add plural article; sentence case | Medium |
| 9 | `common.show_subsections` | Show subsections | Ipanengneng iray subseksyon | Ipanengneng iray subseksyon | Approved; sentence case | High |
| 10 | `common.hide_subsections` | Hide subsections | Taguan iray subseksyon | Taguan iray subseksyon | Approved; sentence case | High |

## Forms and errors

| # | Source | English | Current PAG | Proposed PAG | Rule | Confidence |
| ---: | --- | --- | --- | --- | --- | --- |
| 11 | `report_hub.report_error_label` | What is incorrect? | Anto so aliwan a tama? * | Anto so aliwan a tama? * | Direct question; preserve required marker | High |
| 12 | `report_hub.report_correction` | Correct information | Tamang impormasyon | Maong a impormasyon | Remove Tagalog `tamang`; confirm “correct” vs “good” | Review |
| 13 | `report_hub.report_source` | Source / proof link | Pinanlapuan / Proof Link | Pinanlapuan / link na ebidensya | Sentence case; review `ebidensya` | Review |
| 14 | `report_hub.contribute_category` | Category * | Kategorya * | Kategorya * | Established loanword | High |
| 15 | `report_hub.contribute_title` | Title / information name * | Pamagat / Ngaran na Impormasyon * | Pamagat / ngaran na impormasyon * | Sentence case | High |
| 16 | `report_hub.suggest_usecase` | Use case / why it matters | Gamit / Antoy kapalagahan | Panagusar / Antoy kapalagahan | Replace Tagalog `gamit`; review `panagusar` | Review |
| 17 | `report_hub.submit_copy` | Copy draft text | Kopyaen so draft a teksto | Kopyaen so draft a teksto | Natural verb; preserve `draft` | High |
| 18 | `report_hub.toast_copy` | Copied to clipboard! Paste it into your email app. | Nakopya ed clipboard! Idikit ed email app mo. | Nakopya ed clipboard! Idikit ed email app mo. | Direct address; preserve loanwords | Medium |

## Service metadata

These are UI labels, not official names.

| # | Source | English | Current PAG | Proposed PAG | Rule | Confidence |
| ---: | --- | --- | --- | --- | --- | --- |
| 19 | `service_page.office` | Responsible Office: | Opisina ya Mangasiwa: | Opisina ya mangasiwa: | Sentence case | High |
| 20 | `service_page.classification` | Classification: | Klasipikasyon: | Klasipikasyon: | Established loanword | High |
| 21 | `service_page.processing_time` | Processing Time: | Oras na Panangproseso: | Oras na panangproseso: | Sentence case | High |
| 22 | `service_page.fee` | Fee: | Bayarin: | Bayarin: | Approved | High |
| 23 | `service_page.where_to_apply` | Where to Apply: | Iner a Pag-aplayan: | Iner a pag-aplayan: | Sentence case; approved construction | High |
| 24 | `service_page.contact` | Contact: | Kontak: | Kontak: | Approved; no change | High |
| 25 | `service_page.requirements` | Requirements | Saray Kinakailangan | Saray kinakailangan | Sentence case | High |
| 26 | `service_page.procedure` | Procedure | Proseso | Proseso | Approved; no change | High |
| 27 | `service_page.source` | Source: | Pinanlapuan: | Pinanlapuan: | Approved; no change | High |
| 28 | `service_page.last_updated` | Last Updated: | Kaukolan a Na-update: | Kaukolan a na-update: | Sentence case | High |

## Service steps

These are draft proposals only. The English source is from `services.json`; no
Pangasinan procedure text exists yet. Every row needs speaker review.

| # | Source | English | Current PAG | Proposed PAG | Rule | Confidence |
| ---: | --- | --- | --- | --- | --- | --- |
| 29 | `birth-certificate.procedure[0]` | Visit the Municipal Civil Registrar’s Office and present valid identification. | — | Onla ed Municipal Civil Registrar tan ipanengneng mo so ID mo. | Imperative; official name stays English | Review |
| 30 | `birth-certificate.procedure[1]` | Fill out the request form and provide the necessary supporting documents. | — | Isumite mo so form tan saray dokumento. | Imperative; avoid unverified `request` term | Review |
| 31 | `birth-certificate.procedure[2]` | Pay the certification fee at the Municipal Treasurer’s Office. | — | Manbayad ka na certification fee ed Municipal Treasurer’s Office. | Imperative; official name stays English | Review |
| 32 | `birth-certificate.procedure[3]` | Receive the certified birth certificate upon release. | — | Alaen mo so certificate of birth no available la. | Imperative; avoid literal “upon release” | Review |
| 33 | `business-permit.procedure[0]` | Fill up the UNIFIED form and submit necessary requirements for verification (10 min). | — | Punan mo so UNIFIED form tan isumite mo iray kinakailangan para ed verification (10 min). | Imperative; review `Punan` | Review |
| 34 | `business-permit.procedure[2]` | BPLO endorses applicant to various offices... | — | Ipapasa na BPLO so aplikante ed nanduruman opisina... | Actor focus; preserve BPLO | Review |

## Page metadata

These are UI labels, not official names.

| # | Source | English | Current PAG | Proposed PAG | Rule | Confidence |
| ---: | --- | --- | --- | --- | --- | --- |
| 35 | `page-meta.json → about.html → pag.hero_eyebrow` | About Better Mapandan | Tungkol sa Better Mapandan | Nipaakar ed Better Mapandan | Replace Tagalog `Tungkol`; review `Nipaakar` | Review |
| 36 | `page-meta.json → government.html → pag.hero_eyebrow` | Government Directory | Pamahalaan | Direktoryo na Gobierno | Replace Tagalog `Pamahalaan`; review `Direktoryo` | Medium |
| 37 | `page-meta.json → transparency.html → pag.hero_eyebrow` | Transparency | Transparency | Transparensya | Use the existing PAG title spelling | High |
| 38 | `page-meta.json → support/accessibility.html → pag.hero_eyebrow` | Accessibility Statement | Suporta | Pahayag ed Aksesibilidad | Localize; review `Aksesibilidad` | Medium |
| 39 | `page-meta.json → support/privacy.html → pag.hero_eyebrow` | Privacy Policy | Legal | Patakaran na Privacy | Localize; `Legal` is not a title | Medium |
| 40 | `page-meta.json → support/report.html → pag.hero_eyebrow` | Civic Contribution Hub | Komunidad | Hub na Partisipasyon na Residente | Match approved report-hub title; avoid Tagalog `Mamamayan` | Review |

## Long-form

Use these rows to test paragraph rhythm, topic marking, and English-term policy.
Do not treat the proposals as certified prose.

| # | Source | English | Current PAG | Proposed PAG | Rule | Confidence |
| ---: | --- | --- | --- | --- | --- | --- |
| 41 | `homepage.municipality_desc` | Municipality profile and location | Nakatugaw so Mapandan ed Ikatlong Kongresonal a Distrito na Pangasinan, napaliber ed San Jacinto ed norte, Mangaldan ed hilagang-kanluran, Manaoag ed east, tan Santa Barbara ed south. Say lawak to et 32.92 square kilometers, tan antapud 3/4 na daga et para ed agrikultura—pangunahing palay, kaiba so mais, alaga a animales, tan pana-panahon a gulay. Mantrabaho so administrasyon na baley ed silong na tagline a “Kaakibat niyo ang Aktibo at Responsableng Liderato.” | Nakatugaw so Mapandan ed Ikatlong Kongresonal a Distrito na Pangasinan, napaliber ed San Jacinto ed norte, Mangaldan ed hilagang-kanluran, Manaoag ed east, tan Santa Barbara ed south. Say lawak to so 32.92 square kilometers, tan antapud 3/4 na daga so para ed agrikultura—palay so primary, kaiba so mais, alaga a animales, tan pana-panahon a gulay. Mantrabaho so administrasyon na baley ed silong na tagline a “Kaakibat niyo ang Aktibo at Responsableng Liderato.” | Replace copula-like `et` with `so`; preserve slogan and English technical terms | Review |
| 42 | `homepage.sources_desc` | Source attribution | Dakdakep a bahagi na makasaysayang material na Mapandan et manipud ed official website na Municipality of Mapandan, kaiba so Municipal Profile, Physical Characteristics, tan individual barangay history pages. Say population data et manipud ed Philippine Statistics Authority. Saray development milestone et nakabase ed Philippine News Agency tan Department of Budget and Management records. | Manipud ed official website na Municipality of Mapandan so dakdakep a parte na historical material na Mapandan, kaiba so Municipal Profile, Physical Characteristics, tan individual barangay history pages. Manipud ed Philippine Statistics Authority so population data. Nakabase ed Philippine News Agency tan Department of Budget and Management records so saray development milestone. | Replace copula-like `et`; verb-initial; remove Tagalog `makasaysayang` | Review |
| 43 | `homepage.transparency_desc` | Financial accountability data | Financial accountability data na Mapandan—badyet, procurement, imprastraktura, tan COA audit reports—amin ed sakey a lugar. | Datos na panagpanagutan a pinansyal na Mapandan—badyet, procurement, imprastraktura, tan COA audit reports—amin ed sakey a lugar. | Replace English head noun; review `pinansyal` | Review |
| 44 | `transparency.balance_desc` | Net asset position | Say baley et walaan na net asset position ya mangipanengneng ed naipon a resources tan obligations na pamahalaan. | Say baley so walaan na net asset position ya mangipanengneng ed naipon a resources tan obligations na gobierno. | Replace copula-like `et` with `so`; localize `pamahalaan` | Medium |
| 45 | `about.project_desc` | About Better Mapandan | Say Better Mapandan et independent civic transparency portal ya mangtitipon na pampublikong datos tungkol ed Municipality of Mapandan, Pangasinan ed sakey a madaling ma-access a platform. Binangon tan mantine na saray volunteer; aliwa iya kaakibat na local government. | Say Better Mapandan so sakey a independent a portal na transparency para ed saray residente ya mangtitipon na datos na publiko nipaakar ed Municipality of Mapandan, Pangasinan ed sakey a madaling ma-access a platform. Binangon tan mantine na saray volunteer; aliwa iya kaakibat na gobierno lokal. | Replace copula-like `et`; remove Tagalog `pampublikong`; localize `local government` | Review |

## Source and legal

| # | Source | English | Current PAG | Proposed PAG | Rule | Confidence |
| ---: | --- | --- | --- | --- | --- | --- |
| 46 | `footer.source_code` | Source Code (GitHub) | Source Code (GitHub) | Source code (GitHub) | Sentence case; technical term | Medium |
| 47 | `footer.privacy` | Privacy Policy | Patakaran na Privacy | Patakaran na privacy | Sentence case | High |
| 48 | `footer.terms` | Terms of Use | Saray Tuntunin na Paggamit | Saray tuntunin na paggamit | Sentence case; retain approved term | High |
| 49 | `footer.report` | Report Incorrect Information | I-ulat so Aliwan a Tama a Impormasyon | I-ulat so aliwan a tama a impormasyon | Sentence case | High |
| 50 | `common.disclaimer` | Independent civic transparency portal disclaimer | Say Better Mapandan et independent civic transparency portal. Aliwa iya opisyal a website na gobierno tan aliwa iya kaabay, inendorso, odino pinatatakbo na Municipality of Mapandan odino arum a ahensya na gobierno. | Say Better Mapandan so sakey a independent a portal na transparency para ed saray residente. Aliwa iya opisyal a website na gobierno tan aliwa iya kaabay, inendorso, odino pinatatakbo na Municipality of Mapandan odino arum a ahensya na gobierno. | Replace copula-like `et`; review English descriptor | Review |

## Review notes

- Every service-step row is `Review`; these are structural drafts, not approved
  translations.
- Rows 41, 42, and 45 depend on English technical descriptors that may need
  approved Pangasinan equivalents.
- Rows 43 and 44 keep `procurement`, `COA audit reports`, `net asset position`,
  `resources`, and `obligations` because they are financial terms; do not
  translate them piecemeal.
- Row 50 needs a legal/policy check as well as a language check.
- Do not mass-change `ya`, `et`, `say`, or `nen say` based on this pilot.
  `nen say` is valid in comparatives; `so say` is the high-priority pattern to
  review.
- After approval, update `locales/pag.json`, `page-meta.json`, and service `_pag`
  fields deliberately. Do not create a translation overlay.

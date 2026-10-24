# Pangasinan style guide

Status: working draft for speaker and editorial review. This guide governs
Pangasinan copy in the site, service pages, forms, metadata, and generated UI.
It does not certify a translation as natural or community-approved.

## Scope and sources

Use this guide with:

- `locales/pag.json` for existing UI copy. Treat it as a draft, not a gold
  standard.
- `src/data/pag-review.json` for the current speaker-review queue.
- `src/data/page-meta.json` for page titles, descriptions, and hero copy.
- `src/data/services.json` for service data. Pangasinan service fields are not
  yet populated.
- `Pangasinan language book.pdf` — Richard A. Benton, *Pangasinan Reference
  Grammar* (1971). Use it for grammar, markers, linkers, and sentence structure.

Benton is a descriptive grammar, not a modern technical dictionary. For new
government, financial, and digital terms, preserve the English official term
unless an established Pangasinan form has been reviewed and approved.

## Voice by content type

### UI, forms, and errors

- Use direct, short instructions.
- Use `ka`/`mo` for singular direct address.
- Use `kayó`/`yo` only for genuinely plural or respectful address.
- State the action and the next step.
- Preserve placeholders, IDs, amounts, dates, and official names.

### Service steps and requirements

- Use verb-first, imperative steps.
- Keep one action per sentence or list item.
- Preserve official office, program, form, and document names in English.
- Do not translate source values in place.

### Civic narrative and history

- Use clear, neutral Pangasinan.
- Avoid direct `ka`; refer to `say baley`, `say gobierno`, or `saray residente`.
- Prefer short sentences over English-style subordinate clauses.

### Legal, financial, and audit content

- Keep a formal but plain register.
- Preserve `COA`, `DILG`, `BLGF`, `PhilGEPS`, `Tax Declaration`, `Balance Sheet`,
  and other official terms.
- Define a technical term on first use when needed.
- Do not use a casual voice for findings, opinions, disclaimers, or legal
  conditions.

## Grammar essentials

Benton describes Pangasinan as verb-initial, with focus and aspect marked on the
verb. The topic is marked by `so` or another topic marker; non-topic phrases use
`na`; locative and referent phrases use `ed`; personal names use the personal
markers.

### Topic, non-topic, and referent markers

| Function | Personal singular | Personal plural or respectful | Non-personal |
| --- | --- | --- | --- |
| Topic | `si` | `di` | `so` neutral; `imáy` singular or indefinite; `irámay` definite plural |
| Non-topic, agent, possessor, object | `nen` | `di` | `na` |
| Referent, location, recipient | `kínen` or `edsi` | `kindí` | `ed` |
| Benefactive | `para` + personal marker | `para` + `kindí` | `para` + article or pronoun |

Articles include `say` (neutral singular), `sáray` (neutral plural), `sámay`
(distant singular), `sarámay` (distant plural), `sátay` (proximate singular),
and `sarátay` (proximate plural).

Do not substitute Tagalog `ang`, `ng`, `sa`, `mga`, or `ay` for these markers in
Pangasinan prose. They may appear inside preserved official names or quotations.

### Linker `ya`

`ya` is the full linker. It alternates with `a` and the suffix `-n`; the
choice is phonological and lexical. Do not treat `ya` as an error by itself and
do not mass-replace it with `a`.

Benton examples:

- `sakéy ya toó` — one person
- `báleg ya amputín asó` — the big white dog
- `maóng ya sinmabí` — good that he arrived

Use the form that reads naturally in context. Consistency matters more than
forcing one variant everywhere.

### `et` and conjunctions

`et` is adversative, roughly “on the other hand.” It is not a neutral copula and
does not mean “is/are.”

Other common conjunctions:

- `tan` — and
- `o` — or
- `bálet` — but, however
- `iñgén` — but, moreover
- `lapó` — because, from, origin
- `ta` — because, reason
- `pián` — so that
- `insán` — then
- `kanián` — so, therefore
- `dápot` — provided that
- `báñg` — even, though
- `báñgno` — when, whenever

Do not replace every `et` mechanically. Some instances are correct adversative
uses. Review copula-like `et` in context and prefer a `so` topic construction or
a verbless equational sentence where appropriate.

### Sentence order

Prefer verb-initial order. Do not copy English subject-verb-object order.

- Weak: `Say opisina et mangibabangat na dokumento.`
- Better: `Mangibabangat so opisina na dokumento.`

The exact focus affix depends on which element is the topic. Check the verb
focus before rewriting a sentence.

### Pronouns and address

Use the established Pangasinan forms:

- `ak` — I
- `ka` — you, singular
- `sikato` — he, she, it
- `kami` — we, exclusive
- `tayo` — we, inclusive
- `kayó` — you, plural or respectful

Avoid Tagalog `ikaw`, `iyo`, `ninyo`, and `kayo` spellings when writing
Pangasinan. Keep `kayó` with the Pangasinan spelling when plural or respectful.

## Official names and terminology

Default to English for official agency, office, program, project, and formal
document names. Use an established Pangasinan form only when it has been
approved.

Examples that stay in English:

- `Municipal Civil Registrar`
- `Municipal Treasurer's Office`
- `Treasury Office`
- `Assessor's Office`
- `Municipal Engineering Office`
- `Business Permit and Licensing Office`
- `Sangguniang Bayan`
- `Commission on Audit (COA)`
- `Department of the Interior and Local Government (DILG)`
- `Tax Declaration`
- `Building Permit`
- `Certified True Copy`
- `Official Receipt (OR)`

Generic descriptors may use established Pangasinan terms:

- `opisina` — office
- `serbisyo` — service
- `bayarin` — fee
- `kinakailangan` — requirement
- `dokumento` — document
- `proseso` — process
- `pinanlapuan` — source
- `kita` — income
- `gastusin` — expenditure
- `badyet` — budget
- `panagpanagutan` — accountability

Do not invent a Pangasinan acronym from an English expansion. Preserve the
English acronym.

## Acronyms and loanwords

- Preserve `COA`, `DILG`, `BLGF`, `PhilGEPS`, `DPWH`, `RA 11032`, `OR`, `AT`,
  `ID`, `EMR`, and similar acronyms.
- Do not add a redundant generic term after an acronym.
- Hyphenate a Pangasinan prefix with an English root: `i-ulat`, `i-submit`,
  `na-verify`, `i-download`.
- Do not hyphenate native roots: `ipanengneng`, `kopyaen`, `idikit`.
- Keep technical terms such as `draft`, `clipboard`, `email`, `link`, `form`,
  `QR code`, and file formats in English when the loanword is the established UI
  term.
- Do not introduce a new loanword spelling without review.

## Capitalization and orthography

Benton notes that Pangasinan capitalization is confined mainly to proper names,
place names, and the first word of a sentence. Follow that convention:

- Use sentence case for ordinary UI text.
- Capitalize proper names, place names, languages, and acronyms.
- Do not copy English title case.
- Use `ng` and `ñg` consistently with the site’s existing orthography.
- Stress marks are optional in site copy; use them only when they prevent
  ambiguity or are already part of an approved term.
- Preserve the spelling of official names even when it differs from Pangasinan
  orthography.

## Numbers, dates, currency, and punctuation

- Use numeric years: `2026`.
- Use `₱` for pesos: `₱150`, `₱1,015`.
- Use commas for thousands: `38,228`.
- Use `%` without a space: `50%`.
- Use an en dash for ranges: `3–5 agew`, `2014–2025`.
- Preserve source amounts, dates, IDs, URLs, and government-reported values.
- Use the established month forms consistently: `Enero`, `Pebrero`, `Marso`,
  `Abril`, `Mayo`, `Hunyo`, `Hulyo`, `Agosto`, `Setyembre`, `Oktubre`,
  `Nobyembre`, `Disyembre`.
- Avoid em dashes. Use commas, periods, or parentheses.
- Do not use a colon after an incomplete introduction.

## Review flags and known traps

### `so say`

`so say` is likely ungrammatical in ordinary prose because `so` marks the topic
and `say` is an article. Treat it as a high-priority review item, but do not
delete `say` mechanically until the phrase structure is understood.

### `nen say`

`nen say` is attested in Benton as a comparative construction (“than the”).
Do not treat every `nen say` as an error. Check whether the sentence is a
comparison.

### `na say`, `ed say`, and `parad say`

These can be valid article constructions: `na` + `say` (“of the”), `ed` + `say`
(“in/on the”), and `parad say` (“for the”). Review context; do not mass-delete.

### Copula-like `et`

`et` is adversative. If the sentence means “X is Y,” do not use `et` as the
copula. Use a `so` topic construction, a verbless equational sentence, or a
sentence with the appropriate verb.

### `ya` after a consonant

`ya` is valid. Do not mass-replace it with `a`. Check whether `a` or `-n` reads
more naturally, but do not treat `ya` as an error by itself.

## Error messages and accessibility

- Say what happened, why if known, and what to do next.
- Keep the action explicit and short.
- Preserve placeholders such as `{name}`, `%s`, and `%d` exactly.
- Do not blame the user.
- Use one term for one concept across error, empty, and success states.
- Keep link text descriptive.

## Review statuses

- `approved`: reviewed and safe to publish.
- `draft`: structurally plausible but not reviewed.
- `review_required`: meaning, terminology, or naturalness needs a speaker.
- `do_not_publish`: known error or unresolved policy conflict.

Do not publish `review_required` or `do_not_publish` strings.

## Required checks

Before integration:

1. Search for untranslated English function words and verbs.
2. Review `so say` context and copula-like `et`.
3. Confirm `nen say` is not a valid comparative before changing it.
4. Check official names and acronyms.
5. Check capitalization and sentence case.
6. Run `python check_pag_coverage.py` after locale or service changes.
7. Run `python check_i18n.py` after locale changes.
8. Build with `python build.py --isolated --offline` after source changes.

## Non-goals

- This guide does not certify naturalness or community acceptance.
- It does not replace a fluent Pangasinan speaker.
- It does not authorize translating source data in place.
- It does not apply to Filipino; see `docs/filipino-style.md`.

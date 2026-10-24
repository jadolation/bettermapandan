# Filipino style guide

Status: working draft for editorial review. This guide governs Filipino copy in
the site, service pages, forms, metadata, and generated UI. It does not replace
review by a Filipino editor.

## Scope and sources

Use this guide with:

- `src/data/filipino-glossary.json` for approved terms and official-name rules.
- `locales/fil.json` for existing UI copy. Preserve good existing strings; do
  not replace them with a weaker machine translation.
- `src/data/page-meta.json` for page titles, descriptions, and hero copy.
- `src/data/services.json` for service `_fil` fields and English source text.
- `datasets/Better_Mapandan_Translations_ALL_ENTRIES_PROVISIONAL.docx` only as
  translation memory for missing strings. It is not publication-ready.

Reference standard: Microsoft *Filipino Style Guide* (December 2017), adapted
for a civic transparency portal. The Microsoft voice is consumer-software voice;
use its grammar and plain-language rules broadly, but do not apply its casual
tone to audit, legal, financial, or historical prose.

## Voice by content type

### UI, forms, and errors

- Address the reader directly with `ka` and `iyo`/`mo`.
- Use short imperative sentences.
- State what happened and what the reader should do next.
- Avoid blame and avoid formal wording.

Examples:

- `Isumite ang mga kinakailangan.`
- `Ipakita ang wastong ID.`
- `Hindi ma-load ang datos. Subukang muli.`

### Service steps and requirements

- Use verb-first, imperative steps.
- Keep one action per sentence or list item.
- Preserve official form names, office names, and acronyms in English.
- Do not translate amounts, dates, IDs, URLs, or government-reported values.

Examples:

- `Pumunta sa Municipal Civil Registrar at magpakita ng wastong ID.`
- `Magbayad ng ₱150 sa Treasury Office.`
- `Kunin ang sertipiko kapag available na.`

### Civic narrative and history

- Use clear, neutral Filipino.
- Avoid direct `ka`; refer to `ang bayan`, `ang pamahalaang bayan`, or
  `ang mga residente`.
- Prefer short sentences over long English-style clauses.

### Legal, financial, and audit content

- Keep a formal but plain register.
- Preserve official terms such as `COA`, `DILG`, `BLGF`, `PhilGEPS`,
  `Tax Declaration`, and `Balance Sheet`.
- Explain a technical term on first use if the audience may not know it.
- Do not use the warm, conversational Microsoft voice for findings, opinions,
  disclaimers, or legal conditions.

## Grammar

### Case markers

| Function | Common noun | Personal noun |
| --- | --- | --- |
| Subject/topic | `ang` | `si` |
| Non-subject, agent, possessor | `ng` | `ni` |
| Oblique, location, recipient | `sa` | `kay` |
| Plural subject | `ang mga` | `sina` |
| Plural non-subject | `ng mga` | `nina` |
| Plural oblique | `sa mga` | `kina` |

Never write `sa ang`, `ng ang`, `mula sa ang`, or `para sa ang`. These are
article-marker errors, not stylistic choices.

Use:

- `mula sa` or `galing sa` for “from.”
- `para sa` for “for.”
- `sa` for location, direction, recipient, and instrument when no more precise
  phrase is needed.
- `kay`/`kina` for personal recipients.

### Sentence order

Prefer predicate-first order. Use `ay` only when it improves emphasis or
readability; do not copy English subject-verb-object order mechanically.

- Weak: `Ang opisina ay nagbe-verify ng mga dokumento.`
- Better: `Sinusuri ng opisina ang mga dokumento.`
- Weak: `Ikaw ay magsumite ng mga dokumento.`
- Better: `Isumite ang mga dokumento.`

### Pronouns and address

- `ka`/`mo`/`iyo`: singular direct address in UI and instructions.
- `kayo`/`inyo`: genuinely plural or respectful address, not formal singular.
- `kami`: the organization excluding the reader.
- `tayo`: includes the reader; use only when the statement truly includes both
  the site and the resident.
- Avoid `ang user` and other third-person UI references.

### Verbs and focus

- Use the verb form that matches the focus of the sentence.
- For instructions, use the imperative/infinitive form.
- Do not retain English verbs such as `submit`, `present`, `secure`, `obtain`,
  `pay`, `wait`, `register`, `claim`, `follow up`, or `fill out`.
- Use `mag-`, `i-`, `-in`, `-an`, and other affixes naturally; do not force a
  literal English passive.

Preferred plain verbs:

| Avoid | Use |
| --- | --- |
| `Obtain` | `Kumuha` |
| `Secure` | `Kumuha` |
| `Submit` | `Isumite` |
| `Present` | `Ipakita` |
| `Pay` | `Magbayad` |
| `Wait` | `Maghintay` |
| `Register` | `Magparehistro` |
| `Claim` | `Kunin` |
| `Follow up` | `Sundan` or `Mag-follow up` when the loanword is clearer |
| `Fill out` | `Punan` |

## Word choice

Prefer everyday Filipino over formal equivalents when meaning is unchanged.

| Avoid | Prefer | Note |
| --- | --- | --- |
| `upang` | `para` | Use `upang` only when the purpose clause needs a formal register. |
| `ngunit`, `subalit`, `datapwat` | `pero` | `pero` is the natural default. |
| `sapagkat` | `dahil` | `dahil` is clearer and more conversational. |
| `sa pamamagitan ng` | `gamit` or `sa` | Use the shorter form when it does not change meaning. |
| `maaaring` | `puwede` or `baka` | Choose by context: ability vs. possibility. |
| `gumawa ng rekomendasyon` | `magrekomenda` | Prefer the direct verb. |
| `magbigay ng tulong` | `tumulong` | Prefer the direct verb. |
| `nagararanas ng problema` | `nagkakaproblema` | Prefer the direct verb. |

Do not overuse `ay`, `upang`, `sa pamamagitan ng`, or `maaaring` merely because
the English source uses “is/are,” “to,” “by using,” or “may.”

## Official names and terminology

Default to English for official agency, office, program, project, and formal
document names. Use an official Filipino form only when one is established and
approved; do not invent one.

`Sangguniang Bayan` is retained as an official name; do not replace it with
`Municipal Council` in Filipino copy.

Examples of names that stay in English:

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

Generic descriptors remain Filipino:

- `opisina` for a generic office.
- `ahensya` for an agency when the official name is not being used.
- `serbisyo`, `bayad`, `kinakailangan`, `dokumento`, `proseso`.

Approved or preferred terms:

| English | Filipino | Status |
| --- | --- | --- |
| Office (generic) | `Opisina` | Approved |
| Source | `Pinagmulan` | Approved |
| Last updated | `Huling na-update` | Approved |
| Requirements | `Mga kinakailangan` | Approved |
| Procedure | `Mga hakbang` | Proposed for UI |
| Classification | `Uri` | Proposed for UI |
| Processing time | `Tagal ng pagproseso` | Proposed for UI |
| Where to apply | `Saan mag-apply` | Proposed for UI |
| Contact | `Kontak` | Proposed for UI |
| Fee | `Bayad` | Proposed for UI |
| Audit (common noun) | `Awdit` | Use consistently |
| Transparency | `Transparency` | Retain, per glossary |
| Data | `Datos` | Approved |
| Barangay | `Barangay` | Retain |

Avoid literal calques:

- `Balance Sheet` is not `Balanseng Maayos`. Use `Balance Sheet` or the approved
  accounting equivalent after review.
- `Equity` is not `Pagkakapantay-pantay`. Use `Equity` or a reviewed financial
  term with explanation.
- `Source` is not `Sanggunian`. Use `Pinagmulan` for a source citation.
- `OR` is not `O`. Preserve the acronym.
- `AT` is not `Sa`. Preserve the acronym and determine its expansion from
  context.

## Acronyms and loanwords

- Preserve English acronyms. Do not create Filipino acronyms from translated
  expansions.
- Spell out an acronym on first use only when the audience needs it.
- Do not add a redundant generic term after an acronym.
- Hyphenate a Filipino prefix with an English root: `mag-apply`, `i-download`,
  `i-submit`, `naka-attach`, `mag-log in`.
- Do not hyphenate native roots: `magparehistro`, `pagpaparehistro`,
  `isumite`, `kunin`.
- Keep technical terms such as `draft`, `clipboard`, `email`, `link`, `form`,
  `ID`, `QR code`, `Wi-Fi`, and file formats in English when the loanword is the
  established UI term.

## Capitalization

- Use sentence case for ordinary UI text, headings, labels, and descriptions.
- Capitalize proper nouns, official names, place names, languages, and acronyms.
- Do not copy English title case.
- Do not capitalize `opisina`, `serbisyo`, `bayad`, `kinakailangan`, or
  `proseso` merely because the English source capitalizes them.

## Numbers, dates, currency, and punctuation

- Use numeric years: `2026`, not `two thousand twenty-six`.
- Use `₱` for pesos: `₱150`, `₱1,015`.
- Use commas for thousands: `38,228`.
- Use `%` without a space: `50%`.
- Use an en dash for ranges: `3–5 araw`, `2014–2025`.
- Use `Enero 1, 2026` for dates.
- Use `1:00 PM` or `1:00 N.H.` consistently within a page.
- Preserve all source amounts, dates, IDs, URLs, and government-reported values
  exactly.
- Avoid em dashes. Use commas, periods, or parentheses.
- Do not use a colon after an incomplete introduction or after “such as.”
- Use the serial comma when it prevents ambiguity.

## Error messages and accessibility

- Say what happened, why if known, and what to do next.
- Keep the action explicit: `Subukang muli`, `Piliin ang file`, `Ilagay ang
  email address`.
- Preserve placeholders such as `{name}`, `%s`, and `%d` exactly.
- Do not blame the user.
- Use the same term for the same control or concept across error, empty, and
  success states.
- Keep link text descriptive; avoid `pindutin dito` when a meaningful label is
  possible.

## Review statuses

Use these statuses in review artifacts:

- `approved`: reviewed and safe to publish.
- `draft`: grammatically plausible but not yet reviewed.
- `review_required`: meaning, terminology, or register needs an editor.
- `do_not_publish`: known error or unresolved policy conflict.

Do not publish a string marked `review_required` or `do_not_publish`.

## Required checks

Before integration:

1. Search for `sa ang`, `ng ang`, `mula sa ang`, and `para sa ang`.
2. Search for English verbs in imperative steps.
3. Search for `upang`, `sa pamamagitan ng`, `maaaring`, and `ay` overuse.
4. Check official names against the glossary and source records.
5. Check sentence case and acronym preservation.
6. Run `python check_i18n.py` after locale changes.
7. Build with `python build.py --isolated --offline` after source changes.

## Non-goals

- This guide does not certify legal or financial translations.
- It does not replace a Filipino editor for long-form or high-risk content.
- It does not authorize translating source data in place.
- It does not apply to Pangasinan; see `docs/pangasinan-style.md`.

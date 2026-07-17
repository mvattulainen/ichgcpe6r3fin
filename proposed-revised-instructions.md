# Revised Instructions: Finnish ICH E6(R3) Knowledge Base

## 1. Purpose

Process the Finnish translation of ICH E6(R3) into a versioned, bilingual and machine-readable knowledge base.

The outputs will be used in three environments:

1. an Obsidian vault;
2. a locally built Quartz website;
3. a public website deployed through GitHub Pages.
(https://github.com/mvattulainen/ichgcpe6r3fin.git)

The project must clearly distinguish:

- exact Finnish source text;
- exact English source text;
- structural metadata;
- automatically generated links;
- AI-generated summaries or classifications;
- expert-reviewed interpretations.

No AI-generated interpretation may be presented as part of the original guideline.

## 2. Input documents

Do not depend on absolute `file:///` paths.

Copy the source documents to:

```text
sources/
├── ich-e6-r3-fi-v1-2026-07-09.pdf
├── ich-e6-r3-en-step5-2025-01-23.pdf
└── manifest.yaml
```

The manifest must include:

```yaml
documents:
  - id: ich-e6-r3-fi-v1
    language: fi
    filename: ich-e6-r3-fi-v1-2026-07-09.pdf
    version: "1"
    translation_date: "2026-07-09"
    status: unofficial_translation
    authoritative_language: en
    canonical_url: "<public Fimea URL>"
    sha256: "<calculated hash>"

  - id: ich-e6-r3-en-step5
    language: en
    filename: ich-e6-r3-en-step5-2025-01-23.pdf
    version: "Step 5"
    publication_date: "2025-01-23"
    effective_date: "2025-07-23"
    status: authoritative_source
    canonical_url: "<public EMA URL>"
    sha256: "<calculated hash>"
```

The pipeline must stop with a clear error if an input is absent or its hash does not match the manifest.

## 3. Output language and character handling

All user-facing navigation, metadata descriptions and generated explanatory content must be in Finnish.

Exceptions:

- exact quotations from the English source;
- Schema.org property names;
- JSON, YAML and programmatic identifiers;
- source document titles where exact preservation is necessary.

Technical requirements:

- encode all Markdown, JSON, YAML and HTML as UTF-8;
- normalize text to Unicode NFC;
- preserve Finnish characters in visible content;
- use ASCII kebab-case for filenames and URL slugs;
- use Finnish text in `title` frontmatter;
- generate JSON with non-ASCII characters preserved rather than unnecessarily escaped;
- configure the website language as `fi`;
- mark English quotation content as English in the resulting HTML where technically possible.

The test suite must explicitly verify rendering of:

```text
ä ö å Ä Ö Å
tietoon perustuva suostumus
tietokoneistetut järjestelmät
EN–FI-termisanasto
```

## 4. Canonical data architecture

Markdown must not be the only structured representation.

Generate the following canonical data files:

```text
data/
├── documents.json
├── sections.json
├── alignments.json
├── glossary.json
├── terminology.json
├── term-variants.json
├── roles.json
├── obligations.json
├── essential-records.json
└── extraction-report.json
```

Markdown pages must be generated from or validated against these datasets.

This prevents role views, obligation tables, APIs and HTML metadata from independently duplicating the same information.

## 5. Main guideline scope

The main content scope is:

- Finnish printed pages 10–94 inclusive;
- zero-based PDF indices 9–93 inclusive.

The page range defines inclusion, but content boundaries must be detected from headings and section identifiers.

Do not split a section merely because it crosses a page boundary.

### 5.1 File granularity

Create one Markdown file for every **titled structural section**.

Examples of titled sections that should receive their own file:

```text
2.8 Tutkimukseen osallistujien tietoon perustuva suostumus
3.11.4 Monitorointi
3.11.4.1 Tutkimuspaikan monitorointi
3.11.4.5.1 Viestintä tutkimuksen toteuttajien kanssa
C.3 Tutkimuksen tallenteiden oleellisuus
```

Untitled numbered clauses such as `3.1.1`, `3.1.2` and lettered items such as `(a)` and `(i)` remain in the nearest titled parent file.

Each numbered clause and lettered item must nevertheless receive a stable HTML anchor or Obsidian block identifier.

Example:

```markdown
### 3.1.1 ^ich-e6-r3-a1-3-1-1

Toimeksiantajan tulee...
```

This gives clause-level citations without producing hundreds of very small files.

### 5.2 Folder structure

Use repository-safe folder names and Finnish display titles:

```text
content/
├── index.md
├── 01-johdanto/
├── 02-gcp-periaatteet/
├── 03-liite-1/
├── 04-liite-a-tutkijan-tietopaketti/
├── 05-liite-b-tutkimussuunnitelma/
├── 06-liite-c-oleelliset-tallenteet/
├── sanasto/
├── termisanasto/
├── roolipohjaiset-nakymat/
└── vastuutaulukot/
```

Each folder must contain an `index.md` with the Finnish folder title.

### 5.3 Stable identifiers

Every source unit must have a stable identifier independent of filenames.

Examples:

```text
ich-e6-r3-introduction-scope
ich-e6-r3-principle-02
ich-e6-r3-a1-2.8
ich-e6-r3-a1-3.11.4.5.1
ich-e6-r3-app-c-3
```

Do not change these identifiers when a visible title or file location changes.

## 6. Section Markdown template

Use a consistent template:

```markdown
---
title: "2.8 Tutkimukseen osallistujien tietoon perustuva suostumus"
id: "ich-e6-r3-a1-2.8"
content_type: guideline_section
document_id: ich-e6-r3-fi-v1
section_number: "2.8"
parent_id: "ich-e6-r3-a1-2"
language: fi
translation_status: unofficial
authoritative_language: en
finnish_pages:
  - 27
  - 32
english_pages:
  - 18
  - 21
english_section_number: "2.8"
permalink: "/ich-e6-r3/liite-1/2.8/"
aliases:
  - "Tietoon perustuva suostumus"
tags:
  - ich-e6-r3
  - suostumus
roles:
  - tutkija
  - tutkimuspaikan-henkilosto
review_status: source_extracted
publish: true
---

# 2.8 Tutkimukseen osallistujien tietoon perustuva suostumus

[Exact Finnish source content.]

## Liittyvät käsitteet

- [[sanasto/tietoon-perustuva-suostumus|Tietoon perustuva suostumus]]
- [[sanasto/laillinen-edustaja|Laillinen edustaja]]

> [!quote]- Alkuperäinen englanninkielinen lähdeteksti
>
> [Exact corresponding English source content.]
>
> **Lähde:** ICH E6(R3), Annex 1, section 2.8, pages 18–21.
```

Use the Finnish heading **“Alkuperäinen englanninkielinen lähdeteksti”**, not “Source document”, because the surrounding user interface is Finnish.

## 7. Source-text extraction rules

The Finnish and English source content must be preserved faithfully.

The extraction process may:

- remove repeated page headers and footers;
- join lines belonging to the same paragraph;
- remove layout-only line breaks;
- reconstruct numbered lists and tables.

It must not:

- paraphrase source text;
- alter normative modality;
- silently correct source wording;
- add missing content based on inference;
- merge separate numbered clauses;
- convert source text into generated summaries.

Line-break hyphenation may be removed only when the split is unambiguous. Genuine compound-word hyphens must be retained.

Store both:

- raw extracted text;
- normalized publication text.

Record every normalization operation in the extraction report.

## 8. Finnish–English alignment

Alignment must use section numbering and heading structure.

Recommended sequence:

1. match exact section identifiers;
2. verify corresponding heading;
3. compare paragraph and list structure;
4. record page ranges separately;
5. flag differences for review.

Never align sections only because they appear on approximately corresponding pages.

For every alignment, store:

```json
{
  "finnish_id": "ich-e6-r3-a1-2.8",
  "english_section": "2.8",
  "method": "section_identifier",
  "confidence": 1.0,
  "review_status": "automatically_verified"
}
```

Where there is no exact English counterpart, the pipeline must flag the item and leave the English source section empty rather than generate text.

## 9. Tables

Tables must be extracted semantically, not flattened into paragraphs.

This particularly applies to:

- the essential-records table in Appendix C;
- the EN–FI terminology table;
- any tabular version-history material included in scope.

For Appendix C, produce both:

- a source-faithful rendered table or list;
- structured `essential-records.json` entries.

Each essential-record entry should include:

```json
{
  "id": "essential-record-001",
  "name_fi": "...",
  "name_en": "...",
  "required_before_trial_start": true,
  "source_section": "C.3",
  "source_pages_fi": [91],
  "source_pages_en": [59]
}
```

## 10. Glossary and EN–FI terminology

Treat these as two related but distinct source types.

### 10.1 Formal glossary

Scope:

- Finnish printed pages 95–105;
- corresponding English glossary in the English source.

Create one Markdown file per formal glossary entry.

Each entry contains:

- Finnish preferred term;
- English preferred term;
- abbreviations;
- exact Finnish definition;
- exact English definition;
- source page references;
- synonyms and aliases where explicitly supported;
- links to sections in which the term occurs.

Schema type: `DefinedTerm`.

### 10.2 EN–FI terminology list

Scope:

- Finnish printed pages 106–111.

Create a separate terminology dataset and, where useful, one page per term.

These entries may have:

- an English term;
- one or more Finnish equivalents;
- explanatory parenthetical notes;
- no formal definition.

Do not invent an English “Source document” definition for terminology-list entries that do not occur in the official glossary.

Use fields such as:

```json
{
  "entry_type": "translation_mapping",
  "term_en": "access control",
  "preferred_label_fi": "käyttöoikeuksien hallinta",
  "definition_fi": null,
  "definition_en": null,
  "source": "fimea_en_fi_terminology",
  "official_ich_glossary_entry": false
}
```

## 11. Glossary linking

Every occurrence of an identified Finnish glossary term in the Finnish guideline text should link to its glossary page, subject to the following rules:

- preserve the exact visible source wording;
- use Obsidian link aliases for inflected forms;
- do not insert links into the English source callout;
- do not link inside existing links, code, headings or metadata;
- do not match a substring inside an unrelated longer word;
- choose the longest applicable multiword term;
- do not create multiple overlapping links;
- limit repeated links if excessive linking damages readability.

Example:

```markdown
[[sanasto/tietoon-perustuva-suostumus|tietoon perustuvan suostumuksen]]
```

Maintain a controlled variant file:

```yaml
tietoon-perustuva-suostumus:
  preferred: "tietoon perustuva suostumus"
  variants:
    - "tietoon perustuvan suostumuksen"
    - "tietoon perustuvaa suostumusta"
    - "tietoon perustuvasta suostumuksesta"
```

Do not generate Finnish inflection variants blindly. Extract candidate forms from the source corpus and produce a review report for uncertain matches.

## 12. Table of contents

Create:

```text
content/index.md
```

and folder-specific index pages.

The principal `Sisällysluettelo` page must:

- follow the document hierarchy;
- link to every generated structural page;
- show section numbers;
- preserve source order;
- include glossary, terminology, role-view and register indexes as separate branches;
- be generated from `sections.json`, not maintained manually.

## 13. JSON-LD

### 13.1 Storage model

Do not manually maintain a complete literal JSON-LD block inside every Markdown file.

Instead:

1. store page-specific semantic values in YAML frontmatter;
2. implement a Quartz transformer or component;
3. generate a `<script type="application/ld+json">` element in the HTML `<head>`;
4. optionally provide a collapsed metadata preview in Obsidian;
5. derive both the HTML JSON-LD and preview from the same frontmatter.

### 13.2 Recommended Schema.org types

Use:

| Page type | Schema.org type |
|---|---|
| Guideline section | `TechArticle` or `DigitalDocument` |
| Glossary entry | `DefinedTerm` |
| Glossary index | `DefinedTermSet` |
| Role-based view | `CollectionPage` |
| Obligation register | `Dataset` |
| Register table page | `CollectionPage` or `ItemList` |
| Overall website | `WebSite` |

Do not classify the ICH guideline as `Legislation`; it is guidance rather than an act, decree or comparable legal instrument.

Useful properties include:

- `identifier`;
- `name`;
- `headline`;
- `description`;
- `inLanguage`;
- `isPartOf`;
- `hasPart`;
- `isBasedOn`;
- `translationOfWork`;
- `version`;
- `datePublished`;
- `dateModified`;
- `publisher`;
- `citation`;
- `license`;
- `mainEntity`;
- `sdPublisher`;
- `sdDatePublished`.

### 13.3 Example generated JSON-LD

```json
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "@id": "https://example.org/ich-e6-r3/liite-1/2.8/#page",
  "identifier": "ich-e6-r3-a1-2.8",
  "name": "2.8 Tutkimukseen osallistujien tietoon perustuva suostumus",
  "inLanguage": "fi",
  "isPartOf": {
    "@id": "https://example.org/ich-e6-r3/#guideline"
  },
  "translationOfWork": {
    "@type": "DigitalDocument",
    "name": "ICH E6(R3) Guideline for Good Clinical Practice",
    "inLanguage": "en"
  },
  "isBasedOn": [
    {
      "@type": "DigitalDocument",
      "name": "Fimean tarkistama epävirallinen suomenkielinen käännös",
      "inLanguage": "fi"
    },
    {
      "@type": "DigitalDocument",
      "name": "ICH E6(R3) Step 5",
      "inLanguage": "en"
    }
  ],
  "version": "1",
  "articleSection": "Annex 1, 2.8",
  "sdPublisher": {
    "@type": "Organization",
    "name": "<website publisher>"
  }
}
```

## 14. Role-based views

Create the folder:

```text
content/roolipohjaiset-nakymat/
```

Start with a fixed and configurable role list:

```yaml
roles:
  - tutkija
  - toimeksiantaja
  - tutkimuspaikan-henkilosto
  - monitoroija
  - riippumaton-eettinen-toimikunta
  - tiedonhallinta-ja-tietokoneistetut-jarjestelmat
  - palveluntarjoaja
```

Do not allow the AI to invent additional roles without adding them to the controlled role list.

Each role page should contain:

1. role description;
2. principal responsibilities;
3. responsibilities by trial lifecycle stage;
4. source-backed practical actions;
5. related obligation-register entries;
6. example evidence;
7. key guideline sections;
8. related glossary terms;
9. review and provenance information.

Example structure:

```markdown
# Tutkija

## Keskeiset vastuut

## Ennen tutkimuksen aloittamista

## Tutkimuksen aikana

## Tutkimukseen osallistumisen päättyessä

## Esimerkkitallenteet ja näyttö

## Keskeiset velvoitteet

## Lähdekohdat

## Liittyvät käsitteet
```

Role pages are derived guidance. Every material statement must contain one or more source references.

Do not include fictitious live values such as:

- “2 avointa tehtävää”;
- “4 tallennetta myöhässä”;
- “suostumusversio hyväksytty”.

Such values require integration with an actual clinical-trial management system and are outside this static-site project.

Store derivation metadata:

```yaml
content_status: ai_generated
review_status: awaiting_expert_review
source_refs:
  - "2.1"
  - "2.2"
  - "2.3"
```

## 15. Obligation and evidence register

Create:

```text
data/obligations.json
content/vastuutaulukot/
```

The canonical obligation register is structured data. Markdown tables are generated views.

Each obligation must contain:

```json
{
  "obligation_id": "INV-IC-001",
  "responsible_actor": ["tutkija"],
  "supporting_actors": ["tutkimuspaikan-henkilosto"],
  "source_section": "2.8.6",
  "source_text_fi": "...",
  "source_text_en": "...",
  "modality_fi": "tulee",
  "modality_en": "should",
  "normalized_action_fi": "...",
  "condition_fi": "...",
  "trigger_fi": "...",
  "timing_fi": "...",
  "example_evidence": [
    "suostumusprosessin merkintä",
    "allekirjoitettu suostumuslomake",
    "koulutustallenne"
  ],
  "evidence_status": "illustrative_not_source_requirement",
  "confidence": 0.92,
  "review_status": "awaiting_expert_review"
}
```

Rules:

- preserve the source modality exactly;
- never automatically convert “should” into “must”;
- distinguish prohibitions, responsibilities, permissions and recommendations;
- do not extract purely descriptive statements as obligations;
- label evidence items as examples unless explicitly required by the source;
- retain exact Finnish and English source text;
- give every normalized statement exact clause-level citations;
- flag compound clauses containing more than one obligation;
- allow one source clause to produce several atomic obligations;
- allow one obligation to cite several clauses;
- require expert review before setting `review_status: expert_reviewed`.

Generate register views by:

- responsible role;
- topic;
- lifecycle phase;
- source section;
- evidence type;
- review status.

## 16. Provenance and notices

Every public page must make the following distinctions visible:

- the Finnish translation is unofficial;
- the English source is authoritative;
- source text and generated interpretation are separate;
- evidence suggestions are illustrative;
- role views and registers may require expert review.

Include a global source and copyright notice.

## 17. Quartz configuration

Pin the Quartz major and package versions in the repository.

Required features:

- Obsidian-flavored Markdown;
- wikilinks and aliases;
- collapsible callouts;
- frontmatter parsing;
- folder navigation;
- full-text search;
- sitemap;
- stable permalinks;
- custom JSON-LD component;
- GitHub Pages deployment.

Configure the production base URL before deployment.

## 18. Required reports

The pipeline must produce:

```text
reports/
├── source-manifest-report.md
├── section-coverage-report.md
├── alignment-report.md
├── normalization-report.md
├── glossary-link-report.md
├── unresolved-term-report.md
├── obligation-review-report.md
├── role-view-review-report.md
├── broken-link-report.md
└── build-report.md
```

Reports must clearly identify:

- missing sections;
- duplicated sections;
- uncertain alignments;
- source-text normalization changes;
- unresolved glossary variants;
- source clauses without English counterparts;
- low-confidence obligation extractions;
- broken internal links;
- invalid JSON-LD;
- failed Quartz pages.

## 19. Acceptance criteria

The project is complete only when all of the following pass.

### Source completeness

- Every included Finnish source section appears exactly once.
- All printed pages 10–94 are accounted for.
- Formal glossary pages 95–105 are accounted for.
- EN–FI terminology pages 106–111 are accounted for.
- No page header or footer has entered the substantive content.
- No normative source text has been paraphrased.

### Alignment

- Every main Finnish section has an English alignment or an explicit unresolved flag.
- Alignment uses section identifiers.
- English text is not generated or translated.
- Finnish-only additions are explicitly identified.

### Linking

- Every glossary link resolves.
- Inflected Finnish link labels retain the original visible text.
- No glossary links occur in English source sections.
- No nested or overlapping links are produced.
- All table-of-contents links resolve.

### Metadata

- Every page has a stable identifier.
- Every public page has a stable permalink.
- JSON-LD parses as valid JSON.
- JSON-LD is inserted into the HTML head.
- Page type and language are correct.
- No `file:///` URLs appear in generated output.

### Unicode

- All files are UTF-8.
- All text is Unicode NFC.
- Finnish characters render correctly in Obsidian, local Quartz and GitHub Pages.
- Filenames and URLs behave consistently on Windows, Linux and GitHub.

### Derived content

- Every role statement has source references.
- Every obligation has exact Finnish and English source text.
- Source modality is preserved.
- Example evidence is not presented as a regulatory requirement.
- AI-generated material has an explicit review status.

### Build and deployment

- the Obsidian vault opens without invalid links;
- the local Quartz build succeeds;
- the production Quartz build succeeds;
- GitHub Pages deployment succeeds;
- the public site contains no local paths or unpublished source artifacts.

## 20. Recommended architectural principle

Use this dependency direction:

```text
PDF sources
    ↓
normalized structured data
    ↓
validated bilingual alignment
    ↓
Markdown source pages
    ↓
glossary links, role mappings and obligations
    ↓
Quartz HTML + JSON-LD + machine-readable downloads
```

Do not make generated Markdown the upstream source for the obligation register or role classifications.

Structured datasets should remain canonical, while Markdown and HTML are publication formats.

The two decisions that should be locked before coding begins are:

1. the exact file granularity rule;
2. the definitive controlled role list.

# Specification: Static, Agent-Oriented Corpus Support for the ICH E6(R3) Finnish Knowledge Base

## 1. Purpose

This specification defines improvements that make the corpus easier and safer for software agents to discover, retrieve, validate, cite, synchronize, and interpret.

The implementation must remain compatible with the existing publishing model:

- the website is hosted as a static GitHub Pages site;
- Quartz renders the website from Markdown files;
- all public machine-readable resources must be generated at build time;
- no persistent application server, database, server-side API, or dynamically executed MCP server may be required;
- all public resources must be addressable as static files;
- GitHub Actions may be used for validation, generation, packaging, and publication.

This document is intended to be used as an implementation specification by a coding agent.

## 2. Core principles

### 2.1 Static-first architecture

All functionality must be implementable through one or more of the following:

- Markdown source files;
- YAML frontmatter;
- statically generated HTML;
- statically generated JSON or JSON-LD;
- static JSON Schemas;
- static manifests and indexes;
- Git tags and GitHub Releases;
- GitHub Actions;
- Quartz plugins or build-time transforms;
- standard HTTP behavior provided by GitHub Pages.

The implementation must not depend on:

- server-side request processing;
- databases;
- dynamically filtered API endpoints;
- runtime authentication;
- webhooks hosted by the project;
- background jobs outside GitHub Actions;
- a live MCP server;
- a live REST or GraphQL service.

### 2.2 Source and derived content must remain distinct

The system must distinguish at least:

- authoritative English source content;
- unofficial Finnish translation content;
- extracted source-faithful content;
- generated navigational content;
- derived interpretive content.

Derived content includes, at minimum:

- obligation records;
- role views;
- normalized obligation statements;
- actor assignments;
- generated summaries;
- machine-produced interpretations;
- machine-produced semantic relationships not directly present in the source;
- any other content that introduces interpretation beyond direct transcription or deterministic formatting.

### 2.3 Mandatory pending status for derived content

Every derived record and every page primarily presenting derived content must have:

```yaml
review_status: pending
```

Every corresponding JSON record must have:

```json
"review_status": "pending"
```

At this stage:

- `pending` is the only permitted review status for derived content;
- no generated or derived record may be marked `verified`, `approved`, `reviewed`, `authoritative`, or equivalent;
- confidence scores must not be treated as substitutes for expert review;
- derived pages and records must display or expose a clear warning that the material is pending expert review;
- build validation must fail if derived content lacks the `pending` status or uses another status.

---

# 3. Required improvements

## 3.1 Publish an agent-oriented corpus manifest

### Objective

Provide a single, static, machine-readable entry point that tells an agent:

- what the corpus contains;
- which resources are canonical;
- which language is authoritative;
- which resources are source-based and which are derived;
- which schemas apply;
- how resources are versioned;
- how records can be cited;
- what validation reports exist;
- what licensing or rights information applies;
- which content remains pending expert review.

### Required files

The build must publish:

```text
/llms.txt
/corpus-manifest.json
```

Recommended source locations:

```text
static/llms.txt
scripts/generate_corpus_manifest.py
```

The generated manifest should be written into the Quartz static output path before or during the production build.

### `llms.txt` requirements

`llms.txt` must be concise and human-readable. It should include:

- corpus title;
- corpus purpose;
- canonical website URL;
- repository URL;
- authoritative language;
- available languages;
- links to the corpus manifest;
- links to canonical datasets;
- links to schemas;
- link to rights information;
- link to validation reports;
- warning that all derived content has `review_status: pending`;
- instruction to cite source sections rather than derived summaries where possible.

Example structure:

```text
# ICH E6(R3) Finnish Knowledge Base

Canonical site: https://...
Repository: https://...
Manifest: https://.../corpus-manifest.json
Schemas: https://.../schemas/
Datasets: https://.../data/
Validation reports: https://.../reports/
Rights statement: https://.../rights/

Authoritative language: English
Finnish content status: unofficial translation
Derived content review status: pending

Agents should prefer source sections and preserve source citations.
Derived obligations and role views must not be treated as expert-reviewed.
```

### `corpus-manifest.json` requirements

The manifest must contain at least:

```json
{
  "corpus_id": "ich-e6-r3-fin",
  "corpus_version": "2026.07.1",
  "schema_version": "1.0.0",
  "title": "ICH E6(R3) Finnish Knowledge Base",
  "canonical_site": "https://...",
  "repository": "https://...",
  "publishing_model": "static-github-pages-quartz",
  "authoritative_language": "en",
  "available_languages": ["en", "fi"],
  "derived_content_review_status": "pending",
  "datasets": [],
  "schemas": [],
  "validation_reports": [],
  "rights": {},
  "citation_policy": {},
  "release": {},
  "checksums": {}
}
```

Each dataset entry must identify:

- dataset identifier;
- title;
- static URL;
- record type;
- media type;
- schema URL;
- corpus version;
- schema version;
- record count;
- stable identifier field;
- source or derived classification;
- review status;
- authoritative status;
- last generated time;
- checksum.

Example:

```json
{
  "dataset_id": "obligations",
  "title": "Derived obligation candidates",
  "url": "/data/v1/obligations.json",
  "record_type": "Obligation",
  "media_type": "application/json",
  "schema_url": "/schemas/v1/obligation.schema.json",
  "corpus_version": "2026.07.1",
  "schema_version": "1.0.0",
  "id_field": "id",
  "record_count": 166,
  "classification": "derived",
  "review_status": "pending",
  "authoritative": false,
  "sha256": "..."
}
```

### Generation requirements

The manifest must be generated from repository data rather than manually duplicating counts and paths.

The generator must:

1. read corpus and schema versions from one configuration file;
2. enumerate published datasets and schemas;
3. count records;
4. calculate SHA-256 checksums;
5. verify that all referenced files exist;
6. set all derived dataset review statuses to `pending`;
7. fail if a derived dataset contains another review status;
8. produce deterministic JSON ordering and formatting.

### Acceptance criteria

- `/llms.txt` is reachable on the deployed site.
- `/corpus-manifest.json` is reachable and valid JSON.
- Every manifest URL resolves to a published static resource.
- Every dataset checksum matches the published file.
- Derived datasets are clearly marked non-authoritative and `pending`.
- CI fails on missing resources, invalid checksums, or inconsistent review statuses.

---

## 3.2 Expose versioned JSON datasets with JSON Schemas

### Objective

Turn the existing JSON files into a stable, documented, build-validated static data contract.

### Required public URL structure

Publish versioned resources using immutable version paths:

```text
/data/v1/documents.json
/data/v1/sections.json
/data/v1/alignments.json
/data/v1/glossary.json
/data/v1/terminology.json
/data/v1/roles.json
/data/v1/obligations.json
/data/v1/essential-records.json

/schemas/v1/document.schema.json
/schemas/v1/section.schema.json
/schemas/v1/alignment.schema.json
/schemas/v1/glossary-entry.schema.json
/schemas/v1/terminology-entry.schema.json
/schemas/v1/role.schema.json
/schemas/v1/obligation.schema.json
/schemas/v1/essential-record.schema.json
```

A movable convenience alias may also be published:

```text
/data/latest/...
/schemas/latest/...
```

The documentation must state that integrations should store and cite immutable version paths, not `latest`.

### Version fields

Every dataset must expose:

```json
{
  "corpus_version": "2026.07.1",
  "schema_version": "1.0.0",
  "records": []
}
```

Every record should also contain its relevant stable identifier and may repeat the corpus version where record-level portability is needed.

The project must distinguish:

- `source_version`: version of the underlying ICH source;
- `corpus_version`: version of the published corpus;
- `schema_version`: version of the JSON structure;
- `pipeline_version`: version or commit of the extraction/build process.

### JSON Schema standard

Schemas must use JSON Schema Draft 2020-12.

Each schema must define:

- `$schema`;
- `$id`;
- title;
- description;
- required fields;
- property types;
- identifier patterns;
- enumerations;
- nullability;
- references to reusable definitions;
- `additionalProperties` policy.

### Derived-record rule

Every schema for derived content must require:

```json
"review_status": {
  "const": "pending"
}
```

At minimum, this applies to:

- obligations;
- role records or role-view records;
- derived alignments where interpretation is involved;
- generated summaries;
- normalized derived statements;
- machine-generated classifications.

If alignments are treated as deterministic source mapping rather than interpretation, they may use a separate classification, but any non-direct or confidence-based alignment must be marked derived and pending.

### Obligation record requirements

An obligation record must support, at minimum:

```json
{
  "id": "obl-...",
  "source_section_id": "sec-...",
  "source_version": "...",
  "corpus_version": "...",
  "schema_version": "...",
  "classification": "derived",
  "review_status": "pending",
  "responsible_roles": [],
  "supporting_roles": [],
  "modality": "...",
  "normalized_action": "...",
  "conditions": [],
  "exceptions": [],
  "timing": null,
  "source_text_en": "...",
  "source_text_fi": "...",
  "source_pages": [],
  "derivation_method": "...",
  "confidence": 0.0,
  "canonical_page_url": "..."
}
```

### Cross-reference validation

CI must verify:

- every record ID is unique within its record type;
- stable IDs are not silently reused for another meaning;
- all referenced section, document, role, term, and alignment IDs exist;
- every published Markdown page that declares a record ID points to a matching JSON record;
- every JSON record with a canonical page URL points to an existing output page;
- every derived record has `review_status: pending`;
- all JSON validates against the matching schema.

### Compatibility policy

The repository must document:

- which changes are backward-compatible;
- which changes require a schema-version increment;
- whether fields may be deprecated;
- whether fields may be removed;
- how identifier stability is preserved;
- whether order within arrays is semantically meaningful.

### Acceptance criteria

- All datasets are published as static JSON.
- All datasets validate against published schemas.
- Schema and corpus versions are explicit.
- Cross-references resolve.
- Derived records cannot pass CI unless their review status is exactly `pending`.
- Versioned URLs remain immutable after release.

---

## 3.3 Enrich and connect the existing JSON-LD

### Objective

Improve the semantic usefulness of the JSON-LD already generated by Quartz and connect each rendered page to the canonical static JSON record that represents it.

### Implementation constraint

JSON-LD must be generated at build time and embedded in rendered HTML. No runtime service may be required.

Implementation options include:

- a Quartz transformer plugin;
- a Quartz component that emits `<script type="application/ld+json">`;
- a build-time script that derives JSON-LD from Markdown frontmatter;
- a shared frontmatter-to-JSON-LD mapping module.

### Required page types

At minimum, support:

- guideline section pages;
- glossary-entry pages;
- glossary index;
- terminology index;
- role-view pages;
- obligation-related pages, if published;
- dataset landing pages;
- validation-report pages;
- corpus home page.

### Stable identifiers

Every page-level JSON-LD object must include:

```json
"@id": "<canonical page URL>"
```

The `@id` must be stable and must match the canonical URL emitted in HTML metadata.

### Recommended Schema.org types

Use appropriate types such as:

- `TechArticle` for source or guidance sections;
- `DefinedTerm` for glossary terms;
- `DefinedTermSet` for the glossary;
- `Dataset` for JSON datasets;
- `DataCatalog` for the corpus inventory;
- `DigitalDocument` or `CreativeWork` for source documents;
- `WebSite` for the publication;
- `Report` where appropriate for validation reports.

### Required semantic properties

Section pages should expose, where available:

- `identifier`;
- `headline`;
- `inLanguage`;
- `isPartOf`;
- `isBasedOn`;
- `translationOfWork`;
- `pagination`;
- `version`;
- `dateModified`;
- `license` or rights statement URL;
- `about`;
- `mentions`;
- canonical dataset record URL.

Example:

```json
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "@id": "https://.../01-johdanto/johdanto",
  "identifier": "sec-...",
  "headline": "...",
  "inLanguage": "fi",
  "isPartOf": {
    "@id": "https://.../#corpus"
  },
  "isBasedOn": {
    "@id": "https://.../#english-source"
  },
  "translationOfWork": {
    "@id": "https://.../en/..."
  },
  "version": "2026.07.1",
  "subjectOf": {
    "@type": "DataDownload",
    "encodingFormat": "application/json",
    "contentUrl": "https://.../data/v1/sections/sec-....json"
  }
}
```

### Derived-content JSON-LD requirements

Pages containing derived content must expose:

```json
{
  "additionalProperty": [
    {
      "@type": "PropertyValue",
      "name": "review_status",
      "value": "pending"
    },
    {
      "@type": "PropertyValue",
      "name": "classification",
      "value": "derived"
    }
  ]
}
```

They must also expose:

- the source passage or source record on which the derivation is based;
- the derivation method, where available;
- confidence as metadata only;
- a non-authoritative warning;
- a link to the canonical JSON record.

Derived content must not use JSON-LD wording or types that imply verified regulatory authority.

### Validation requirements

CI must:

1. extract every JSON-LD block from generated HTML;
2. parse it as valid JSON;
3. verify required fields by page type;
4. verify that `@id` matches the canonical URL;
5. verify that linked static JSON resources exist;
6. verify that derived pages expose `review_status: pending`;
7. verify that source and derived entities are not conflated.

### Acceptance criteria

- Every rendered content page contains valid JSON-LD.
- Each JSON-LD object has a stable canonical `@id`.
- Each page links to its corresponding static JSON record when one exists.
- Derived pages expose `classification: derived` and `review_status: pending`.
- CI fails if required semantic metadata is missing.

---

## 3.4 Provide a static read-only machine interface

### Objective

Provide agent-friendly retrieval without introducing a live API or MCP server.

Because the site is static, the interface must consist of pre-generated files and deterministic URL conventions.

### Explicit non-goals

The project must not implement:

- a live REST service;
- a live GraphQL endpoint;
- server-side filtering;
- a server-hosted MCP implementation;
- runtime search endpoints;
- authenticated agent actions.

### Required static interface components

Publish:

```text
/api/openapi.yaml
/api/index.json
/api/search-index.json
/api/records/<record-type>/<record-id>.json
```

The `/api/` prefix is a static namespace only. It must not imply server-side execution.

### Static OpenAPI description

A static OpenAPI document may be published to describe direct file retrieval paths.

It must clearly state:

```yaml
info:
  title: ICH E6(R3) Static Corpus Interface
  description: >
    This specification describes immutable static JSON resources hosted on
    GitHub Pages. It is not a dynamically executed API.
```

Only `GET` operations for existing static files may be documented.

Example paths:

```yaml
paths:
  /api/index.json:
    get:
      summary: Retrieve the static corpus index
  /api/records/sections/{section_id}.json:
    get:
      summary: Retrieve a pre-generated section record
  /api/records/terms/{term_id}.json:
    get:
      summary: Retrieve a pre-generated terminology record
  /api/records/obligations/{obligation_id}.json:
    get:
      summary: Retrieve a pre-generated pending obligation record
```

The coding agent must not generate paths that require query parameters to be processed dynamically.

### Static record expansion

In addition to aggregate datasets, generate one file per record:

```text
/api/records/sections/sec-001.json
/api/records/terms/term-001.json
/api/records/obligations/obl-001.json
```

This allows agents to retrieve a single record without downloading an entire dataset.

### Static indexes

`/api/index.json` must provide lookup tables such as:

```json
{
  "corpus_version": "2026.07.1",
  "record_types": {
    "sections": {
      "dataset": "/data/v1/sections.json",
      "records_base": "/api/records/sections/",
      "schema": "/schemas/v1/section.schema.json"
    },
    "obligations": {
      "dataset": "/data/v1/obligations.json",
      "records_base": "/api/records/obligations/",
      "schema": "/schemas/v1/obligation.schema.json",
      "classification": "derived",
      "review_status": "pending"
    }
  }
}
```

### Static search index

Generate `/api/search-index.json` at build time.

It may contain:

- record ID;
- title;
- page URL;
- content type;
- language;
- normalized keywords;
- role IDs;
- section IDs;
- review status;
- short source-faithful excerpt.

It must not contain newly generated interpretive summaries unless they are marked derived and pending.

The search index is intended for client-side or agent-side filtering. GitHub Pages will only serve the file.

### Optional client-side helper

A small, static JavaScript module may be published to help clients:

- load the index;
- filter records locally;
- resolve record URLs;
- verify corpus versions.

This helper must not hide the underlying static data contract.

### MCP compatibility note

A live MCP server is outside the scope of this static deployment.

The static resources should nevertheless be designed so that an external party could later implement an MCP adapter without changing record identifiers or schemas.

No MCP implementation is required by this specification.

### Acceptance criteria

- All documented machine-interface paths resolve to static files.
- The OpenAPI document describes static retrieval only.
- No documented operation requires server-side computation.
- Each canonical record can be fetched as a standalone JSON file.
- Derived records retain `review_status: pending`.
- The aggregate datasets and individual record files are consistent.

---

## 3.5 Enable a change feed and formal releases

### Objective

Allow agents and downstream systems to determine what changed without diffing the entire repository or re-indexing the entire corpus.

### Static change-feed files

Publish:

```text
/feed.xml
/changes.json
/releases/index.json
/releases/<corpus-version>/manifest.json
/releases/<corpus-version>/changes.json
```

Quartz RSS support may be enabled or a custom Atom/RSS feed may be generated at build time.

The feed should include:

- formal corpus releases;
- source-text changes;
- translation changes;
- alignment changes;
- schema changes;
- review-status-related changes;
- additions, removals, and supersessions of derived records;
- validation failures corrected by a release.

### Formal release workflow

Each release must have:

- a Git tag;
- a GitHub Release;
- immutable release assets;
- corpus version;
- release date;
- release notes;
- corpus manifest;
- versioned datasets;
- schemas;
- validation reports;
- checksums;
- machine-readable change log.

Recommended release asset:

```text
ich-e6-r3-fin-<corpus-version>.zip
```

It should contain all machine-readable resources needed for offline ingestion.

### Machine-readable change classes

Use controlled values:

```text
source_text_changed
translation_changed
alignment_changed
derived_record_added
derived_record_changed
derived_record_removed
review_status_changed
metadata_changed
schema_changed
page_url_changed
validation_changed
```

Each change record must include:

```json
{
  "change_type": "derived_record_changed",
  "record_type": "obligation",
  "record_id": "obl-...",
  "classification": "derived",
  "review_status": "pending",
  "previous_corpus_version": "2026.06.1",
  "current_corpus_version": "2026.07.1",
  "requires_reindex": true
}
```

### Versioning policy

Use either semantic versioning or calendar versioning consistently.

Recommended calendar version:

```text
YYYY.MM.PATCH
```

Examples:

- `2026.07.0`: scheduled July corpus release;
- `2026.07.1`: corrective release;
- `2026.08.0`: next scheduled release.

Schema versions must remain independently versioned.

### Build and release automation

GitHub Actions should:

1. validate all data and schemas;
2. generate the site and static machine resources;
3. generate checksums;
4. generate `changes.json` by comparison with the previous release;
5. generate release notes;
6. package release assets;
7. publish GitHub Pages;
8. create or update a GitHub Release only after all validations pass.

### Acceptance criteria

- A release can be identified by an immutable version.
- Every release has downloadable machine-readable assets.
- `changes.json` identifies affected record IDs.
- Feed entries link to release manifests and change logs.
- Agents can determine whether re-indexing is required.
- Derived records remain `pending` in every release until a future specification changes the permitted review states.

---

## 3.6 Clarify content licensing and rights

### Objective

Make the reuse conditions of each asset class explicit to humans and agents without implying rights that the project does not possess.

### Required rights documentation

Publish:

```text
/rights/index.md
/rights/rights.json
```

Recommended repository source:

```text
content/rights/index.md
static/rights/rights.json
```

### Asset classes

The rights statement must address separately:

| Asset class | Required clarification |
|---|---|
| Quartz and project code | Applicable software licence |
| English ICH source | Original rights holder, source, and permitted use |
| Finnish translation | Translation status, attribution, and reuse terms |
| Extracted source quotations | Permitted scope of storage and republication |
| Structured metadata | Licence for project-created structure and metadata |
| Derived obligations | Reuse terms and pending-review status |
| Derived role views | Reuse terms and pending-review status |
| Generated website pages | Combined-content rights statement |
| Validation reports | Reuse and attribution terms |
| Build scripts | Applicable software licence |

### `rights.json` requirements

The machine-readable rights file must identify, per asset class:

- asset class ID;
- description;
- rights holder;
- copyright status;
- licence identifier or rights statement URL;
- attribution requirement;
- redistribution permission;
- modification permission;
- commercial-use permission;
- indexing permission;
- RAG-use permission;
- model-training permission, if known;
- uncertainty or unresolved-rights note.

Where the project cannot make a legal determination, use explicit values such as:

```json
{
  "model_training": "not_specified",
  "commercial_use": "not_determined",
  "redistribution": "subject_to_source_rights"
}
```

Do not infer permission from public availability.

### Page- and dataset-level metadata

Every dataset and relevant JSON-LD object must link to the applicable rights record.

Example:

```json
{
  "rights": "/rights/rights.json#derived-obligations",
  "license": null,
  "classification": "derived",
  "review_status": "pending"
}
```

A null licence must not be replaced with a guessed open-source licence.

### AI-use clarification

The rights statement should explicitly distinguish:

- crawling;
- indexing;
- local retrieval;
- retrieval-augmented generation;
- quotation in generated answers;
- mirroring;
- redistribution;
- model training;
- fine-tuning;
- commercial use.

### Acceptance criteria

- Every asset class has an explicit rights statement.
- Code licences are not presented as covering third-party source content.
- Dataset and JSON-LD metadata link to the correct rights statement.
- Unknown permissions are represented as unknown, not assumed.
- Derived role and obligation content is marked `pending` in both human- and machine-readable rights documentation where relevant.

---

## 3.7 Prepare the derived role and obligation datasets for expert review

### Objective

Make all derived role and obligation content traceable, reviewable, and safe for agent consumption while preserving its mandatory `pending` status.

This specification does not permit transition to an approved status. It defines the technical preparation and review workflow only.

### Review status rule

All current and newly generated derived content must remain:

```text
pending
```

The data model may reserve future statuses, but:

- schemas used in the current implementation must allow only `pending`;
- user-facing pages must describe the content as pending;
- no review workflow action may change the public value to another state;
- expert comments may be stored separately without changing public review status.

### Obligation record requirements

Each obligation record must include:

- stable obligation ID;
- source document ID;
- source section ID;
- source page range;
- exact English source passage;
- corresponding Finnish passage, when available;
- responsible-role candidates;
- supporting-role candidates;
- modality candidate;
- normalized-action candidate;
- conditions;
- exceptions;
- timing;
- derivation method;
- pipeline version;
- confidence score;
- review notes field;
- issue flags;
- canonical page URL;
- `classification: derived`;
- `review_status: pending`.

### Issue flags

Use controlled flags such as:

```text
compound_passage
multiple_actors
conditional_requirement
possible_exception
translation_ambiguity
alignment_uncertain
modality_uncertain
scope_uncertain
timing_uncertain
normalization_loss_risk
requires_domain_expert
```

### Role-view requirements

Role views must be generated only from records that can be traced to source passages.

Each role view must:

- identify every contributing obligation ID;
- link to every source section;
- display a pending-review warning;
- distinguish source quotation from normalized interpretation;
- avoid claims of completeness;
- avoid language implying an approved job description;
- expose `review_status: pending` in frontmatter and JSON-LD.

Required frontmatter:

```yaml
content_type: derived_role_view
classification: derived
review_status: pending
authoritative: false
generated: true
```

### Human-readable warning

Every derived role or obligation page must display a visible warning similar to:

> This page contains automatically derived content. Its review status is pending. It is not an authoritative interpretation and must not be used as the sole basis for regulatory, clinical, legal, or compliance decisions.

The exact wording may be localized, but the meaning must remain unchanged.

### Expert-review worksheet

Generate a static review worksheet in JSON and optionally CSV:

```text
/review/v1/obligations-review.json
/review/v1/obligations-review.csv
/review/v1/roles-review.json
/review/v1/roles-review.csv
```

Each worksheet entry should include fields for:

- record ID;
- source citation;
- source text;
- current derived interpretation;
- issue flags;
- reviewer comments;
- proposed correction;
- reviewer identity;
- review date.

The worksheet output is for offline expert review. Importing reviewed changes back into the repository is outside automatic approval and must not alter `review_status` from `pending` under this specification.

### Source immutability

Exact source quotations must remain immutable during derived-record editing.

Any correction to derived fields must:

- preserve the original source quotation;
- preserve the prior derived record in Git history;
- record the pipeline or manual change;
- update the corpus version where public output changes;
- retain `review_status: pending`.

### Agent-facing defaults

Static indexes and documentation must:

- label all role and obligation data as pending;
- avoid presenting confidence as approval;
- include direct source links;
- recommend source-first retrieval;
- advise against autonomous compliance decisions;
- allow agents to exclude derived content by using `classification` and `review_status`.

Because filtering occurs client-side, the corpus manifest and indexes must make these fields easy to inspect.

### Validation requirements

CI must fail if:

- a derived role or obligation record lacks `review_status`;
- a derived role or obligation record uses a value other than `pending`;
- a derived record lacks a source section;
- a derived record lacks an exact source passage;
- a role view includes an obligation ID that does not exist;
- a role view omits the pending warning;
- JSON-LD omits derived classification or pending status;
- a confidence score is outside the allowed numeric range;
- a canonical URL does not resolve.

### Acceptance criteria

- Every derived role and obligation record is traceable to source text.
- Every derived record and page is marked `pending`.
- Review worksheets are generated as static files.
- Role views identify their contributing obligation records.
- Source and interpretation are visibly separated.
- CI enforces all pending-status and traceability rules.
- No public output implies expert approval.

---

# 4. Suggested repository structure

```text
content/
  rights/
    index.md
  role-views/
    ...
  sections/
    ...

data/
  source/
    ...
  derived/
    obligations.json
    roles.json

schemas/
  v1/
    document.schema.json
    section.schema.json
    alignment.schema.json
    glossary-entry.schema.json
    terminology-entry.schema.json
    role.schema.json
    obligation.schema.json
    essential-record.schema.json

static/
  llms.txt
  rights/
    rights.json

scripts/
  generate_corpus_manifest.py
  generate_static_api.py
  generate_search_index.py
  generate_jsonld.py
  generate_changes.py
  generate_review_worksheets.py
  validate_schemas.py
  validate_cross_references.py
  validate_derived_status.py
  validate_jsonld.py

reports/
  ...

quartz/
  components/
  plugins/

.github/
  workflows/
    validate.yml
    deploy.yml
    release.yml
```

The exact structure may be adjusted to match the current repository, but public URLs and validation behavior must remain consistent with this specification.

---

# 5. Build pipeline

The production pipeline should execute in this order:

1. Load version configuration.
2. Validate source manifests and hashes.
3. Validate canonical source datasets.
4. Validate derived datasets.
5. Enforce `review_status: pending` for all derived content.
6. Validate cross-references.
7. Validate all JSON against JSON Schemas.
8. Generate per-record static JSON files.
9. Generate static search and corpus indexes.
10. Generate review worksheets.
11. Generate `corpus-manifest.json`.
12. Generate or copy `llms.txt`.
13. Render Markdown through Quartz.
14. Generate or enrich JSON-LD.
15. Validate rendered JSON-LD and canonical URLs.
16. Generate change logs and feeds.
17. Calculate checksums.
18. Run broken-link validation.
19. Publish GitHub Pages.
20. Package formal release assets when triggered by a release tag.

A failure in steps 2–18 must prevent publication.

---

# 6. Global definition of done

The implementation is complete when:

- the website remains fully deployable as a static GitHub Pages site;
- Quartz continues to render the site from Markdown;
- no runtime server or database is introduced;
- `/llms.txt` and `/corpus-manifest.json` are published;
- versioned JSON datasets and JSON Schemas are published;
- individual records are available as static JSON files;
- rendered pages contain validated and connected JSON-LD;
- a static OpenAPI description documents file retrieval without implying dynamic execution;
- formal release assets and machine-readable change logs are available;
- rights metadata is published in human- and machine-readable forms;
- review worksheets are generated;
- every derived content item has `review_status: pending`;
- CI prevents any derived content from being published with another review status;
- source content and derived interpretation remain clearly separated;
- all machine-readable links, identifiers, schemas, checksums, and canonical URLs validate successfully.

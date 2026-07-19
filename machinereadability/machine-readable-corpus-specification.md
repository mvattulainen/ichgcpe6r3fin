# ICH E6(R3) Finnish Knowledge Base: machine-readable corpus specification

Status: **normative consolidated specification**  
Version: **1.0.0**  
Corpus release: **2026.07.1**  
Date: **2026-07-19**

This document consolidates and supersedes, for implementation purposes, the requirements and examples in:

- `static_quartz_agent_corpus_specification.md`;
- `static-api-implementation-instructions.md`;
- `static-api-example-queries-and-responses.md`.

The source documents remain useful design history. If they conflict with this document, this document is authoritative. Examples are informative; generated identifiers, counts, URLs, hashes, dates, and source text must always come from repository data.

## 1. Purpose and scope

The corpus shall support software agents that discover, retrieve, validate, cite, synchronize, and interpret ICH E6(R3) material. Human-readable pages and machine-readable resources shall be generated from the same canonical repository data.

The implementation shall remain static-first:

- Quartz renders Markdown to HTML;
- GitHub Pages hosts the result;
- JSON, JSON-LD, JSON Schema, JSONL, XML, YAML-compatible OpenAPI, checksums, manifests, review worksheets, and release packages are generated at build time;
- ordinary HTTP `GET` is the only public retrieval operation;
- no database, server process, live REST or GraphQL service, runtime filtering, authentication, write operation, or live MCP server is required.

An external service may later wrap these resources, but it must preserve stable identifiers and the source/derived distinction.

## 2. Normative language and governing rules

“Must” and “shall” indicate mandatory requirements. “Should” indicates a recommended practice. “May” indicates an option.

The following rules govern all outputs:

1. English ICH source content is the authoritative language.
2. Finnish content is an unofficial translation.
3. Exact source content, deterministic formatting, navigation, and interpretation must remain distinguishable.
4. Derived content is non-authoritative.
5. Every derived record and derived page must use exactly `review_status: pending`.
6. No public derived item may use `verified`, `approved`, `reviewed`, `expert_reviewed`, `awaiting_expert_review`, or an equivalent status.
7. Confidence is metadata, not approval.
8. Agents should cite source sections or clauses instead of derived summaries whenever possible.
9. Unknown rights must remain unknown; public availability does not imply permission.
10. A build failure in generation or validation must prevent deployment.

Derived content includes obligations, normalized actions, role collections, confidence-based alignments, automatically aligned essential-record mappings, generated summaries, actor assignments, and other machine-produced interpretations.

## 3. Versions and stable identifiers

One repository configuration file, `machine-readable-config.json`, shall define:

- `corpus_id`;
- `corpus_version` using `YYYY.MM.PATCH`;
- `schema_version` using semantic versioning;
- `api_version`;
- `pipeline_version`;
- release date;
- canonical site and repository URLs;
- authoritative and available languages.

Version meanings:

| Field | Meaning |
|---|---|
| `source_version` | Version of the underlying ICH or translation source |
| `corpus_version` | Immutable public corpus release |
| `schema_version` | JSON structure version |
| `pipeline_version` | Generator and validation contract version |

Stable identifiers must not change when titles, Markdown paths, navigation, visual design, or Quartz configuration change. IDs must be unique within their record type. Reuse of an old ID for a different meaning is prohibited.

## 4. Public discovery resources

The site shall publish:

```text
/llms.txt
/corpus-manifest.json
```

`llms.txt` shall identify the corpus, canonical site, repository, languages, datasets, schemas, static interface, validation reports, rights information, and the mandatory pending status. It shall advise source-first retrieval and citation.

`corpus-manifest.json` shall be generated from repository data. It shall contain corpus and schema versions, publishing model, language authority, datasets, schemas, reports, rights, citation policy, release metadata, counts, and checksums. Each dataset entry shall declare its classification, authoritative status, stable ID field, record count, schema, URL, and review status where applicable.

Every manifest URL must resolve in the built artifact. Every listed checksum must match the published bytes.

## 5. Versioned datasets and schemas

Immutable datasets shall be published under `/data/v1/`; movable convenience copies may be published under `/data/latest/`. Integrations should store and cite the immutable path.

Required datasets:

```text
documents.json
sections.json
clauses.json
alignments.json
glossary.json
terminology.json
roles.json
obligations.json
essential-records.json
```

Each dataset shall expose `corpus_version`, `schema_version`, record type, count, records, and a deterministic content hash. Source-faithful Finnish and English passages shall not be replaced with summaries.

JSON Schemas shall be published under `/schemas/v1/` and `/schemas/latest/` for every record type and the corpus manifest. Schemas shall use JSON Schema Draft 2020-12 and state required properties, types, identifier patterns, enumerations or constants, nullability where needed, and an explicit `additionalProperties` policy.

Schemas for derived records shall require:

```json
{
  "classification": "derived",
  "review_status": "pending"
}
```

Schema compatibility policy:

- adding an optional field is backward-compatible;
- adding a required field, changing a type or meaning, or removing a field requires a schema-version increment;
- deprecated fields may remain for one schema version before removal;
- array order is not semantically meaningful unless a schema description explicitly says otherwise;
- released version paths are immutable.

## 6. Static read-only interface

The machine interface is a static namespace, not an executed API. It shall publish:

```text
/api/index.json
/api/search-index.json
/api/openapi.yaml
/openapi.json
/api/v1/manifest.json
/api/v1/<collection>.json
/api/v1/<record-type>/<record-id>.json
/api/v1/downloads/<collection>.jsonl
/api/v1/downloads/checksums.sha256
```

At minimum, standalone files shall exist for documents, sections, clauses, glossary concepts, terminology entries, obligations, roles, alignments, and essential records.

Clause IDs shall correspond to stable hidden anchors on the human-readable source page. A clause resource shall link to its parent section, exact Finnish and English passage when available, source pages, canonical HTML anchor, and static API URL.

Aggregate JSON and individual record files must be consistent. JSONL requirements:

- UTF-8 and Unicode NFC;
- one complete JSON object per line;
- deterministic ID ordering;
- no surrounding array;
- final newline;
- matching counts and checksums.

The search index may contain source-faithful excerpts and lookup metadata. Interpretive summaries are allowed only when marked derived and pending. Filtering is performed by the client.

OpenAPI shall use OpenAPI 3.1, document only `GET`, explain the static hosting model, and avoid dynamic query parameters or operations. A missing GitHub Pages resource may return HTML; clients must check status and content type.

### Informative retrieval examples

```http
GET /api/v1/manifest.json
GET /api/v1/sections/ich-e6-r3-a1-2.8.json
GET /api/v1/clauses/ich-e6-r3-a1-2-8-6.json
GET /api/v1/concepts/tietoon-perustuva-suostumus.json
GET /api/v1/obligations/INV-001.json
GET /api/v1/roles/tutkija.json
```

Clients should retrieve the manifest first, resolve an individual record for citation, and verify its content hash when integrity matters.

## 7. Record requirements

### 7.1 Sections

A section record shall include stable ID, number, Finnish and English titles and text, document IDs, translation and authority status, source pages, hierarchy, related concepts and roles, canonical page URL, API URL, versions, classification, and content hash.

### 7.2 Clauses

Every explicitly numbered or lettered clause inside a section shall have a standalone record. It shall include parent section, exact bilingual text when available, source pages, canonical anchored URL, API URL, authority and translation status, citation, versions, and content hash.

### 7.3 Glossary and terminology

Formal glossary concepts and EN–FI terminology mappings must remain distinguishable. A terminology mapping without a source definition must not be presented as a formal definition. Concept records should expose labels, definitions, abbreviations, source type, related sections, URLs, versions, and hash.

### 7.4 Obligations

An obligation shall include stable ID, source section and clause IDs, exact source passages, responsible and supporting role candidates, modality, normalized action, conditions, exceptions, timing, evidence examples, derivation method, pipeline version, confidence, issue flags, canonical URLs, classification, and review status.

Evidence examples must use `illustrative_not_source_requirement`. Source quotations are immutable. Suggested issue flags include `compound_passage`, `multiple_actors`, `conditional_requirement`, `possible_exception`, `translation_ambiguity`, `alignment_uncertain`, `modality_uncertain`, `scope_uncertain`, `timing_uncertain`, `normalization_loss_risk`, and `requires_domain_expert`.

### 7.5 Roles

Role collections shall reference canonical section, clause, concept, and obligation IDs instead of duplicating source content. Each role view shall show its contributing obligation IDs, link to sources, display a pending/non-authoritative warning, avoid claims of completeness, and expose derived metadata in frontmatter and JSON-LD.

### 7.6 Alignments and essential records

Confidence-based or automatically inferred mappings are derived and pending. Their machine records shall preserve the method, confidence or alignment status, source references, and issue state without implying expert verification.

## 8. JSON-LD

Every rendered content page shall contain one valid build-time JSON-LD block. The block shall include stable canonical `@id`, `@type`, identifier, name or headline, language, canonical URL, corpus version, rights URL, and corpus relationship.

Recommended types include `WebSite`, `TechArticle`, `DefinedTerm`, `DefinedTermSet`, `Dataset`, `DataCatalog`, `DigitalDocument`, and `Report`.

Where a canonical JSON record exists, JSON-LD shall link it through `subjectOf` as a `DataDownload`. Source pages should expose source and translation relationships. Derived pages shall expose `classification: derived` and `review_status: pending` through `additionalProperty`, link to source data, and avoid wording that implies regulatory authority.

The visible independence notice remains necessary because agents may ignore JSON-LD.

## 9. Rights

The site shall publish a human-readable rights page and `/rights/rights.json`. Rights records shall separately address project code, English ICH source, Finnish translation, extracted quotations, structured metadata, derived obligations, derived role views, website pages, reports, and build scripts.

Each rights record shall state, where known, rights holder, licence or statement URL, attribution, redistribution, modification, commercial use, indexing, RAG use, model training, and uncertainty. Unknown values shall use explicit states such as `not_specified`, `not_determined`, or `subject_to_source_rights`. The MIT software licence must not be represented as covering third-party guideline content.

## 10. Review worksheets

Static JSON and CSV worksheets shall be generated for obligations and roles under `/review/v1/`. Worksheet fields shall include record ID, source citation and text, current interpretation, issue flags, reviewer comments, proposed correction, reviewer identity, and review date.

Worksheets support offline expert review but do not change the public status. Under this specification, imported corrections remain `pending` until a future normative specification permits another state.

## 11. Changes, feeds, and releases

The site shall publish:

```text
/feed.xml
/changes.json
/releases/index.json
/releases/<corpus-version>/manifest.json
/releases/<corpus-version>/changes.json
/releases/<corpus-version>/ich-e6-r3-fin-<corpus-version>.zip
```

Controlled change classes include `source_text_changed`, `translation_changed`, `alignment_changed`, `derived_record_added`, `derived_record_changed`, `derived_record_removed`, `review_status_changed`, `metadata_changed`, `schema_changed`, `page_url_changed`, and `validation_changed`.

The baseline release may contain a corpus-level initialization event. Later releases shall compare with the previous immutable release and identify affected record IDs and whether re-indexing is required.

Tagged release automation should create a GitHub Release only after all checks pass. Ordinary site builds shall still publish the static release manifest, changes, checksums, and deterministic offline package.

## 12. Finnish documentation

The site shall include:

- a Finnish developer/agent page describing the interface, limitations, base URL, resources, identifiers, versions, authority, examples, JSONL, checksums, OpenAPI, rights, and issue reporting;
- a concise Finnish article of approximately two printed pages explaining how the website supports AI agents and what safeguards and limitations apply.

## 13. Validation and deployment

The production pipeline shall:

1. load version configuration;
2. verify source manifests and PDF hashes;
3. generate and validate canonical data and Markdown;
4. enforce `pending` on every derived record and page;
5. render Quartz HTML;
6. generate static machine resources and enrich JSON-LD;
7. validate JSON against Draft 2020-12 schemas;
8. validate IDs and cross-references;
9. verify record and file hashes;
10. verify JSONL line counts, UTF-8, NFC, and deterministic order;
11. reject local paths and unpublished paths;
12. validate OpenAPI as static GET-only documentation;
13. validate JSON-LD fields, canonical IDs, record links, and derived metadata;
14. validate every internal HTML and machine-resource link;
15. generate review worksheets, changes, feed, release metadata, and package;
16. publish only after all checks pass.

CI shall fail if a derived record is not pending, a source reference is missing, an ID is duplicated, a canonical/API URL does not resolve, schema validation fails, a hash differs, a role references a missing obligation, JSON-LD is invalid or conflates source and derived content, or required files are absent.

## 14. Out of scope

The current version does not provide dynamic search, semantic search, a vector database, claim verification at request time, AI question answering, authentication, write operations, personalized responses, or a live MCP server.

## 15. Definition of done

Implementation is complete when the static website and machine interface build with one command; all required discovery, datasets, schemas, records, downloads, rights, review, change, release, and documentation resources are deployed; HTML JSON-LD is connected to canonical records; all derived content is pending and non-authoritative; source and interpretation remain distinct; and local plus CI validation passes.

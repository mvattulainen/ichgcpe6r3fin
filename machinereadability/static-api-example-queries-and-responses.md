# Example Queries and Responses for the Static Quartz API

Assume the website is published at:

```text
https://gcp-fin.example.org
```

Because the API is hosted through GitHub Pages, each endpoint is a statically generated file retrieved with an HTTP `GET` request.

## 1. Retrieve the API manifest

### Request

```http
GET https://gcp-fin.example.org/api/v1/manifest.json
Accept: application/json
```

### Example response

```json
{
  "api_version": "v1",
  "schema_version": "1.0.0",
  "dataset_version": "2026.07.1",
  "generated_at": "2026-07-17T08:30:00Z",
  "base_url": "https://gcp-fin.example.org/api/v1/",
  "languages": [
    "fi",
    "en"
  ],
  "source_documents": [
    {
      "id": "ich-e6-r3-fi-v1",
      "title": "ICH E6(R3) GCP – suomenkielinen käännös",
      "language": "fi",
      "status": "unofficial_translation",
      "version": "1",
      "sha256": "7d7d7d7d..."
    },
    {
      "id": "ich-e6-r3-en-step5",
      "title": "ICH E6(R3) Guideline for Good Clinical Practice",
      "language": "en",
      "status": "authoritative_source",
      "version": "Step 5",
      "sha256": "8e8e8e8e..."
    }
  ],
  "record_counts": {
    "sections": 126,
    "clauses": 482,
    "glossary": 96,
    "terminology": 174,
    "obligations": 238,
    "roles": 7
  },
  "downloads": {
    "sections": "/api/v1/downloads/sections.jsonl",
    "clauses": "/api/v1/downloads/clauses.jsonl",
    "glossary": "/api/v1/downloads/glossary.jsonl",
    "obligations": "/api/v1/downloads/obligations.jsonl",
    "checksums": "/api/v1/downloads/checksums.sha256"
  },
  "openapi": "/openapi.json"
}
```

This should normally be the first resource retrieved by an agent.

## 2. Retrieve one guideline section

### Request

```http
GET https://gcp-fin.example.org/api/v1/sections/ich-e6-r3-a1-2.8.json
Accept: application/json
```

### Example response

```json
{
  "id": "ich-e6-r3-a1-2.8",
  "type": "guideline_section",
  "section_number": "2.8",
  "title_fi": "Tutkimukseen osallistujien tietoon perustuva suostumus",
  "title_en": "Informed Consent of Trial Participants",
  "text_fi": "Tutkimukseen osallistujan tietoon perustuva suostumus...",
  "text_en": "Informed consent of trial participants...",
  "document_id_fi": "ich-e6-r3-fi-v1",
  "document_id_en": "ich-e6-r3-en-step5",
  "translation_status": "unofficial",
  "authoritative_language": "en",
  "source_pages_fi": [
    27,
    28,
    29,
    30,
    31,
    32
  ],
  "source_pages_en": [
    18,
    19,
    20,
    21
  ],
  "parent_id": "ich-e6-r3-a1-2",
  "child_ids": [
    "ich-e6-r3-a1-2.8.1",
    "ich-e6-r3-a1-2.8.2",
    "ich-e6-r3-a1-2.8.3",
    "ich-e6-r3-a1-2.8.4",
    "ich-e6-r3-a1-2.8.5",
    "ich-e6-r3-a1-2.8.6"
  ],
  "related_concepts": [
    "tietoon-perustuva-suostumus",
    "laillinen-edustaja",
    "haavoittuvassa-asemassa-oleva-osallistuja"
  ],
  "related_roles": [
    "tutkija",
    "tutkimuspaikan-henkilosto",
    "riippumaton-eettinen-toimikunta"
  ],
  "canonical_url": "https://gcp-fin.example.org/ich-e6-r3/liite-1/2.8/",
  "api_url": "https://gcp-fin.example.org/api/v1/sections/ich-e6-r3-a1-2.8.json",
  "version": "1",
  "schema_version": "1.0.0",
  "content_hash": "sha256:b7dd71..."
}
```

## 3. Retrieve an exact clause

### Request

```http
GET https://gcp-fin.example.org/api/v1/clauses/ich-e6-r3-a1-2.8.6.json
Accept: application/json
```

### Example response

```json
{
  "id": "ich-e6-r3-a1-2.8.6",
  "type": "guideline_clause",
  "section_number": "2.8.6",
  "parent_section_id": "ich-e6-r3-a1-2.8",
  "text_fi": "Ennen tietoon perustuvan suostumuksen hankkimista tutkijan tai tutkijan nimeämän henkilön tulee antaa mahdolliselle tutkimukseen osallistujalle riittävästi aikaa ja mahdollisuus esittää kysymyksiä.",
  "text_en": "Before informed consent is obtained, the investigator or a person designated by the investigator should provide the potential trial participant with sufficient time and opportunity to ask questions.",
  "translation_status": "unofficial",
  "authoritative_language": "en",
  "source_pages_fi": [
    29
  ],
  "source_pages_en": [
    19
  ],
  "related_obligation_ids": [
    "INV-IC-001"
  ],
  "canonical_url": "https://gcp-fin.example.org/ich-e6-r3/liite-1/2.8/#ich-e6-r3-a1-2-8-6",
  "api_url": "https://gcp-fin.example.org/api/v1/clauses/ich-e6-r3-a1-2.8.6.json",
  "preferred_citation": "ICH E6(R3), Annex 1, section 2.8.6",
  "version": "1",
  "content_hash": "sha256:9fac42..."
}
```

This is the preferred resource when an agent needs to support one specific claim.

## 4. Retrieve a glossary concept

### Request

```http
GET https://gcp-fin.example.org/api/v1/concepts/tietoon-perustuva-suostumus.json
Accept: application/json
```

### Example response

```json
{
  "id": "tietoon-perustuva-suostumus",
  "type": "defined_term",
  "preferred_label_fi": "tietoon perustuva suostumus",
  "preferred_label_en": "informed consent",
  "definition_fi": "Prosessi, jossa henkilö vahvistaa vapaaehtoisesti halukkuutensa osallistua tiettyyn tutkimukseen saatuaan tiedon kaikista osallistumispäätöksen kannalta merkityksellisistä seikoista.",
  "definition_en": "A process by which a person voluntarily confirms willingness to participate in a particular trial after having been informed of all aspects relevant to the decision to participate.",
  "alternative_labels_fi": [
    "tutkimussuostumus"
  ],
  "search_variants_fi": [
    "tietoon perustuvan suostumuksen",
    "tietoon perustuvaa suostumusta",
    "tietoon perustuvasta suostumuksesta"
  ],
  "source_type": "formal_glossary",
  "official_ich_glossary_entry": true,
  "related_section_ids": [
    "ich-e6-r3-principle-07",
    "ich-e6-r3-a1-2.8"
  ],
  "canonical_url": "https://gcp-fin.example.org/sanasto/tietoon-perustuva-suostumus/",
  "api_url": "https://gcp-fin.example.org/api/v1/concepts/tietoon-perustuva-suostumus.json",
  "content_hash": "sha256:681f00..."
}
```

## 5. Retrieve an obligation

### Request

```http
GET https://gcp-fin.example.org/api/v1/obligations/INV-IC-001.json
Accept: application/json
```

### Example response

```json
{
  "obligation_id": "INV-IC-001",
  "type": "obligation",
  "title_fi": "Riittävän ajan ja kysymismahdollisuuden antaminen ennen suostumusta",
  "responsible_actor": [
    "tutkija"
  ],
  "supporting_actors": [
    "tutkimuspaikan-henkilosto"
  ],
  "source_clause_ids": [
    "ich-e6-r3-a1-2.8.6"
  ],
  "source_text_fi": "Ennen tietoon perustuvan suostumuksen hankkimista...",
  "source_text_en": "Before informed consent is obtained...",
  "modality_fi": "tulee",
  "modality_en": "should",
  "normalized_action_fi": "Anna mahdolliselle tutkimukseen osallistujalle riittävästi aikaa harkita osallistumista ja mahdollisuus esittää kysymyksiä ennen suostumuksen hankkimista.",
  "condition_fi": "Ennen tietoon perustuvan suostumuksen hankkimista.",
  "timing_fi": "Ennen osallistujan suostumuksen allekirjoittamista tai muuta hyväksyttyä vahvistamista.",
  "example_evidence": [
    {
      "name_fi": "Suostumusprosessia koskeva potilas- tai tutkimusmerkintä",
      "status": "illustrative"
    },
    {
      "name_fi": "Allekirjoitettu ja päivätty suostumuslomake",
      "status": "illustrative"
    },
    {
      "name_fi": "Suostumuksen hankkineen henkilön delegointi- ja koulutustallenne",
      "status": "illustrative"
    }
  ],
  "evidence_status": "illustrative_not_source_requirement",
  "confidence": 0.96,
  "review_status": "awaiting_expert_review",
  "canonical_url": "https://gcp-fin.example.org/vastuutaulukot/INV-IC-001/",
  "api_url": "https://gcp-fin.example.org/api/v1/obligations/INV-IC-001.json",
  "content_hash": "sha256:4bfb61..."
}
```

The `review_status` and `evidence_status` fields prevent an agent from presenting generated evidence examples as direct regulatory requirements.

## 6. Retrieve the investigator role collection

### Request

```http
GET https://gcp-fin.example.org/api/v1/roles/tutkija.json
Accept: application/json
```

### Example response

```json
{
  "id": "tutkija",
  "type": "role_collection",
  "title_fi": "Tutkija",
  "description_fi": "Tutkija vastaa tutkimuksen toteuttamisesta tutkimuspaikassa ja säilyttää kokonaisvastuun myös silloin, kun tutkimukseen liittyviä tehtäviä delegoidaan.",
  "lifecycle_groups": [
    {
      "id": "ennen-tutkimuksen-aloittamista",
      "title_fi": "Ennen tutkimuksen aloittamista",
      "section_ids": [
        "ich-e6-r3-a1-2.1",
        "ich-e6-r3-a1-2.2",
        "ich-e6-r3-a1-2.3"
      ],
      "obligation_ids": [
        "INV-QUAL-001",
        "INV-RES-001",
        "INV-DEL-001"
      ]
    },
    {
      "id": "tutkimuksen-aikana",
      "title_fi": "Tutkimuksen aikana",
      "section_ids": [
        "ich-e6-r3-a1-2.6",
        "ich-e6-r3-a1-2.8",
        "ich-e6-r3-a1-2.9"
      ],
      "obligation_ids": [
        "INV-SAF-001",
        "INV-IC-001",
        "INV-DATA-001"
      ]
    }
  ],
  "concept_ids": [
    "tietoon-perustuva-suostumus",
    "delegointi",
    "haittatapahtuma",
    "oleellinen-tallenne"
  ],
  "review_status": "awaiting_expert_review",
  "canonical_url": "https://gcp-fin.example.org/roolipohjaiset-nakymat/tutkija/",
  "api_url": "https://gcp-fin.example.org/api/v1/roles/tutkija.json",
  "content_hash": "sha256:17e912..."
}
```

An agent could use this resource to construct investigator-specific training or inspection-readiness material.

## 7. Retrieve the complete sections index

### Request

```http
GET https://gcp-fin.example.org/api/v1/sections.json
Accept: application/json
```

### Example response

```json
{
  "type": "section_collection",
  "dataset_version": "2026.07.1",
  "count": 126,
  "items": [
    {
      "id": "ich-e6-r3-introduction-purpose",
      "section_number": null,
      "title_fi": "Ohjeen tarkoitus",
      "api_url": "/api/v1/sections/ich-e6-r3-introduction-purpose.json"
    },
    {
      "id": "ich-e6-r3-principle-01",
      "section_number": "1",
      "title_fi": "Kliinisiä lääketutkimuksia on toteutettava eettisten periaatteiden mukaisesti",
      "api_url": "/api/v1/sections/ich-e6-r3-principle-01.json"
    },
    {
      "id": "ich-e6-r3-a1-2.8",
      "section_number": "2.8",
      "title_fi": "Tutkimukseen osallistujien tietoon perustuva suostumus",
      "api_url": "/api/v1/sections/ich-e6-r3-a1-2.8.json"
    }
  ],
  "content_hash": "sha256:5411e9..."
}
```

This is useful for enumeration, but agents should retrieve an individual resource when they need the complete text.

## 8. Retrieve a precomputed topic collection

A static API cannot process a dynamic request such as:

```text
/api/v1/search?q=tietokoneistettu+järjestelmä
```

It can instead publish precomputed topic collections.

### Request

```http
GET https://gcp-fin.example.org/api/v1/topics/tietokoneistetut-jarjestelmat.json
Accept: application/json
```

### Example response

```json
{
  "id": "tietokoneistetut-jarjestelmat",
  "type": "topic_collection",
  "title_fi": "Tietokoneistetut järjestelmät",
  "description_fi": "Kokoelma tietokoneistettujen järjestelmien käyttöön, turvallisuuteen, validointiin ja tiedonhallintaan liittyvistä lähdekohdista.",
  "section_ids": [
    "ich-e6-r3-a1-4.3",
    "ich-e6-r3-a1-4.3.1",
    "ich-e6-r3-a1-4.3.2",
    "ich-e6-r3-a1-4.3.3",
    "ich-e6-r3-a1-4.3.4"
  ],
  "obligation_ids": [
    "SYS-TRN-001",
    "SYS-SEC-001",
    "SYS-VAL-001"
  ],
  "concept_ids": [
    "audit-trail",
    "access-control",
    "computerised-system-validation"
  ],
  "content_hash": "sha256:6c182c..."
}
```

## 9. Retrieve a JSONL bulk dataset

### Request

```bash
curl \
  --output clauses.jsonl \
  https://gcp-fin.example.org/api/v1/downloads/clauses.jsonl
```

### Example file contents

```jsonl
{"id":"ich-e6-r3-a1-2.1.1","type":"guideline_clause","section_number":"2.1.1","text_fi":"...","text_en":"...","content_hash":"sha256:1a..."}
{"id":"ich-e6-r3-a1-2.1.2","type":"guideline_clause","section_number":"2.1.2","text_fi":"...","text_en":"...","content_hash":"sha256:2b..."}
{"id":"ich-e6-r3-a1-2.2.1","type":"guideline_clause","section_number":"2.2.1","text_fi":"...","text_en":"...","content_hash":"sha256:3c..."}
```

Each line is an independent JSON object, allowing streaming ingestion.

## 10. Check whether the dataset has changed

### First request

```http
GET https://gcp-fin.example.org/api/v1/manifest.json
```

The agent stores:

```json
{
  "dataset_version": "2026.07.1",
  "content_hash": "sha256:abc123..."
}
```

### Later request

```http
GET https://gcp-fin.example.org/api/v1/manifest.json
```

### Example updated response

```json
{
  "dataset_version": "2026.08.1",
  "generated_at": "2026-08-05T09:00:00Z",
  "previous_dataset_version": "2026.07.1",
  "change_summary": {
    "source_text_changed": false,
    "derived_content_changed": true,
    "sections_changed": 0,
    "obligations_changed": 7,
    "roles_changed": 2
  },
  "content_hash": "sha256:def456..."
}
```

The agent can then decide whether to download updated datasets.

## 11. Retrieve a missing resource

### Request

```http
GET https://gcp-fin.example.org/api/v1/clauses/ich-e6-r3-a1-99.99.json
```

On GitHub Pages, this may return the site’s static `404.html` page rather than a JSON error object.

A client must therefore check:

- the HTTP status code;
- the response `Content-Type`;
- whether the identifier exists in the relevant collection index.

### Example JavaScript client

```javascript
const response = await fetch(
  "https://gcp-fin.example.org/api/v1/clauses/ich-e6-r3-a1-99.99.json"
);

if (!response.ok) {
  throw new Error(`Resource not found: ${response.status}`);
}

const contentType = response.headers.get("content-type") ?? "";

if (!contentType.includes("application/json")) {
  throw new Error("Expected a JSON response");
}

const clause = await response.json();
```

## 12. Example multi-request agent workflow

Question:

> Mitä vastuuta tutkijalle jää tehtävien delegoinnin jälkeen?

The agent could retrieve:

```text
GET /api/v1/roles/tutkija.json
GET /api/v1/obligations/INV-DEL-001.json
GET /api/v1/clauses/ich-e6-r3-a1-2.3.1.json
```

It could then construct an answer such as:

```json
{
  "answer_fi": "Tutkija säilyttää kokonaisvastuun tutkimukseen liittyvistä toimista myös silloin, kun tehtäviä delegoidaan.",
  "citation": {
    "clause_id": "ich-e6-r3-a1-2.3.1",
    "preferred_citation": "ICH E6(R3), Annex 1, section 2.3.1",
    "canonical_url": "https://gcp-fin.example.org/ich-e6-r3/liite-1/2.3/#ich-e6-r3-a1-2-3-1"
  },
  "interpretation_status": "source_supported"
}
```

The static API supplies the source data and relationships. The external agent remains responsible for interpreting the user’s question and composing the final answer.

## Implementation note

All examples in this document are illustrative. The coding agent must replace:

- example domain names;
- placeholder text;
- record counts;
- hashes;
- section mappings;
- obligation identifiers;
- generated dates;

with values produced from the canonical project datasets.

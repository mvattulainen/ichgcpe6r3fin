from __future__ import annotations

import copy
import csv
import hashlib
import html
import io
import json
import re
import shutil
import unicodedata
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PUBLIC = ROOT / "public"
REPORTS = ROOT / "reports"
CONFIG = json.loads((ROOT / "machine-readable-config.json").read_text(encoding="utf-8"))
BASE = CONFIG["canonical_site"].rstrip("/")
VERSION = CONFIG["corpus_version"]
SCHEMA_VERSION = CONFIG["schema_version"]
API_VERSION = CONFIG["api_version"]
PIPELINE_VERSION = CONFIG["pipeline_version"]
RELEASE_DATE = CONFIG["release_date"]
GENERATED_AT = f"{RELEASE_DATE}T00:00:00Z"
RIGHTS_URL = f"{BASE}/rights/rights.json"


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def load(name: str) -> Any:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(nfc(value).rstrip() + "\n", encoding="utf-8", newline="\n")


def write_json(path: Path, value: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    path.write_text(nfc(text) + "\n", encoding="utf-8", newline="\n")


def deterministic_bytes(value: Any) -> bytes:
    return nfc(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def with_hash(record: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(record)
    result.pop("content_hash", None)
    result["content_hash"] = f"sha256:{digest_bytes(deterministic_bytes(result))}"
    return result


def strip_markup(value: str) -> str:
    value = re.sub(r'<a id="[^"]+"></a>', "", value)
    value = re.sub(
        r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]",
        lambda match: match.group(2) or match.group(1).rsplit("/", 1)[-1],
        value,
    )
    value = re.sub(r"(?m)^#{1,6}\s+", "", value)
    return value.replace("**", "").strip()


def extract_clauses(value: str) -> dict[str, str]:
    pattern = re.compile(
        r'(?m)^(?:<a id="[^"]+"></a>\n\n)?(?:###\s+|\*\*)((?:\d+|[ABC])(?:\.\d+)+)(?:\*\*)?\s*\n\n'
    )
    matches = list(pattern.finditer(value))
    clauses: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(value)
        body = re.sub(r'<a id="[^"]+"></a>', "", value[match.end() : end])
        clauses[match.group(1)] = re.sub(r"\s+", " ", strip_markup(body)).strip()
    return clauses


def clause_anchor(section_id: str, number: str) -> str:
    prefix = section_id.replace(".", "-")
    clean = number.lower().replace(".", "-")
    section_number = section_id.rsplit("-", 1)[-1]
    if number.startswith(section_number + "."):
        clean = number[len(section_number) + 1 :].replace(".", "-")
    return f"{prefix}-{clean}"


def source_classification(record: dict[str, Any]) -> str:
    return "authoritative_source" if record.get("status") == "authoritative_source" else "source_based"


def common(record: dict[str, Any], classification: str, authoritative: bool) -> dict[str, Any]:
    result = copy.deepcopy(record)
    result.update(
        {
            "corpus_version": VERSION,
            "schema_version": SCHEMA_VERSION,
            "pipeline_version": PIPELINE_VERSION,
            "classification": classification,
            "authoritative": authoritative,
            "rights": RIGHTS_URL,
        }
    )
    return result


def build_records() -> dict[str, list[dict[str, Any]]]:
    source_documents = load("documents.json")
    source_sections = load("sections.json")
    source_glossary = load("glossary.json")
    source_terminology = load("terminology.json")
    source_alignments = load("alignments.json")
    source_obligations = load("obligations.json")
    source_essential = load("essential-records.json")
    role_ids = load("roles.json")["roles"]

    documents: list[dict[str, Any]] = []
    for item in source_documents:
        record = common(item, source_classification(item), item.get("status") == "authoritative_source")
        record.update(
            {
                "type": "source_document",
                "source_version": item["version"],
                "api_url": f"{BASE}/api/{API_VERSION}/documents/{item['id']}.json",
            }
        )
        documents.append(with_hash(record))

    raw_clause_rows: list[tuple[dict[str, Any], str, str, str]] = []
    section_by_number: dict[str, dict[str, Any]] = {}
    for section in source_sections:
        for number, text_fi in extract_clauses(section.get("exact_text_fi", "")).items():
            text_en = extract_clauses(section.get("exact_text_en", "")).get(number, "")
            raw_clause_rows.append((section, number, text_fi, text_en))

    clause_ids_by_section: dict[str, list[str]] = {}
    clauses: list[dict[str, Any]] = []
    clause_by_number: dict[str, dict[str, Any]] = {}
    for section, number, text_fi, text_en in raw_clause_rows:
        cid = clause_anchor(section["id"], number)
        clause_ids_by_section.setdefault(section["id"], []).append(cid)
        page_url = f"{BASE}{section['permalink'].rstrip('/')}#{cid}"
        record = common(
            {
                "id": cid,
                "type": "guideline_clause",
                "section_number": number,
                "parent_section_id": section["id"],
                "text_fi": text_fi,
                "text_en": text_en or None,
                "document_id_fi": "ich-e6-r3-fi-v1",
                "document_id_en": "ich-e6-r3-en-step5",
                "translation_status": "unofficial",
                "authoritative_language": "en",
                "source_pages_fi": section["finnish_pages"],
                "source_pages_en": section["english_pages"],
                "canonical_url": page_url,
                "api_url": f"{BASE}/api/{API_VERSION}/clauses/{cid}.json",
                "preferred_citation": f"ICH E6(R3), section {number}",
            },
            "source_based",
            False,
        )
        hashed = with_hash(record)
        clauses.append(hashed)
        clause_by_number[number] = hashed

    obligations: list[dict[str, Any]] = []
    for item in source_obligations:
        number = str(item["source_section"])
        clause = clause_by_number.get(number)
        section = next((x for x in source_sections if x["section_number"] == number), None)
        if section is None:
            candidates = [x for x in source_sections if number.startswith(str(x["section_number"]) + ".")]
            section = max(candidates, key=lambda x: len(str(x["section_number"])), default=None)
        if section is None and clause:
            section = next(x for x in source_sections if x["id"] == clause["parent_section_id"])
        issue_flags: list[str] = []
        if item.get("compound_clause"):
            issue_flags.append("compound_passage")
        if len(item.get("responsible_actor", [])) + len(item.get("supporting_actors", [])) > 1:
            issue_flags.append("multiple_actors")
        if not (clause or {}).get("text_en"):
            issue_flags.append("alignment_uncertain")
        oid = item["obligation_id"]
        source_url = (clause or {}).get("canonical_url") or (f"{BASE}{section['permalink']}" if section else None)
        record = common(item, "derived", False)
        record.update(
            {
                "id": oid,
                "type": "obligation",
                "review_status": "pending",
                "source_section_id": section["id"] if section else None,
                "source_clause_ids": [clause["id"]] if clause else [],
                "source_text_en": (clause or {}).get("text_en") or item.get("source_text_en"),
                "source_pages_fi": section["finnish_pages"] if section else [],
                "source_pages_en": section["english_pages"] if section else [],
                "responsible_roles": item.get("responsible_actor", []),
                "conditions": [item["condition_fi"]] if item.get("condition_fi") else [],
                "exceptions": [],
                "timing": item.get("timing_fi"),
                "derivation_method": item.get("derivation_method", "rule_based_modality_extraction"),
                "issue_flags": issue_flags,
                "source_page_url": source_url,
                "canonical_url": f"{BASE}/vastuutaulukot/#{oid.lower()}",
                "api_url": f"{BASE}/api/{API_VERSION}/obligations/{oid}.json",
            }
        )
        obligations.append(with_hash(record))

    related_roles_by_section: dict[str, set[str]] = {}
    for obligation in obligations:
        sid = obligation.get("source_section_id")
        if sid:
            related_roles_by_section.setdefault(sid, set()).update(
                obligation.get("responsible_actor", []) + obligation.get("supporting_actors", [])
            )

    sections: list[dict[str, Any]] = []
    for item in source_sections:
        concepts = sorted(set(re.findall(r"\[\[sanasto/([^\]|#]+)", item.get("text_fi", ""))))
        children = [x["id"] for x in source_sections if x.get("parent_id") == item["id"]]
        record = common(
            {
                "id": item["id"],
                "type": "guideline_section",
                "section_number": item["section_number"],
                "title_fi": item["title_fi"],
                "title_en": item["title_en"],
                "text_fi": strip_markup(item.get("exact_text_fi", "")),
                "text_en": strip_markup(item.get("exact_text_en", "")) or None,
                "document_id_fi": "ich-e6-r3-fi-v1",
                "document_id_en": "ich-e6-r3-en-step5",
                "translation_status": "unofficial",
                "authoritative_language": "en",
                "source_pages_fi": item["finnish_pages"],
                "source_pages_en": item["english_pages"],
                "parent_id": item.get("parent_id"),
                "child_ids": sorted(children + clause_ids_by_section.get(item["id"], [])),
                "related_concepts": concepts,
                "related_roles": sorted(related_roles_by_section.get(item["id"], set())),
                "canonical_url": f"{BASE}{item['permalink']}",
                "api_url": f"{BASE}/api/{API_VERSION}/sections/{item['id']}.json",
            },
            "source_based",
            False,
        )
        hashed = with_hash(record)
        sections.append(hashed)
        section_by_number[str(item["section_number"])] = hashed

    glossary: list[dict[str, Any]] = []
    for item in source_glossary:
        record = common(item, "source_based", False)
        record.update(
            {
                "type": "defined_term",
                "preferred_label_fi": item["preferred_term_fi"],
                "preferred_label_en": item.get("preferred_term_en"),
                "definition_en": item.get("definition_en"),
                "source_type": "formal_glossary",
                "canonical_url": f"{BASE}/sanasto/{item['slug']}/",
                "api_url": f"{BASE}/api/{API_VERSION}/concepts/{item['slug']}.json",
            }
        )
        glossary.append(with_hash(record))

    terminology: list[dict[str, Any]] = []
    for item in source_terminology:
        record = common(item, "source_based", False)
        record.update(
            {
                "type": "terminology_entry",
                "api_url": f"{BASE}/api/{API_VERSION}/terminology/{item['id']}.json",
            }
        )
        terminology.append(with_hash(record))

    alignments: list[dict[str, Any]] = []
    for item in source_alignments:
        record = common(item, "derived", False)
        record.update(
            {
                "type": "alignment",
                "review_status": "pending",
                "api_url": f"{BASE}/api/{API_VERSION}/alignments/{item['id']}.json",
            }
        )
        alignments.append(with_hash(record))

    essential: list[dict[str, Any]] = []
    for item in source_essential:
        record = common(item, "derived", False)
        record.update(
            {
                "type": "essential_record",
                "review_status": "pending",
                "api_url": f"{BASE}/api/{API_VERSION}/essential-records/{item['id']}.json",
            }
        )
        essential.append(with_hash(record))

    role_labels = {
        "tutkija": "Tutkija",
        "toimeksiantaja": "Toimeksiantaja",
        "tutkimuspaikan-henkilosto": "Tutkimuspaikan henkilöstö",
        "monitoroija": "Monitoroija",
        "riippumaton-eettinen-toimikunta": "Riippumaton eettinen toimikunta",
        "tiedonhallinta-ja-tietokoneistetut-jarjestelmat": "Tiedonhallinta ja tietokoneistetut järjestelmät",
        "palveluntarjoaja": "Palveluntarjoaja",
    }
    roles: list[dict[str, Any]] = []
    for role_id in role_ids:
        related = [
            x
            for x in obligations
            if role_id in x.get("responsible_actor", []) + x.get("supporting_actors", [])
        ]
        section_ids = sorted({x["source_section_id"] for x in related if x.get("source_section_id")})
        clause_ids = sorted({cid for x in related for cid in x.get("source_clause_ids", [])})
        concept_ids = sorted(
            {
                concept
                for section in sections
                if section["id"] in section_ids
                for concept in section.get("related_concepts", [])
            }
        )
        record = common(
            {
                "id": role_id,
                "type": "role_collection",
                "title_fi": role_labels[role_id],
                "description_fi": "Automaattisesti johdettu lähdeviitteinen roolikokoelma; ei täydellinen tai hyväksytty tehtäväkuvaus.",
                "section_ids": section_ids,
                "clause_ids": clause_ids,
                "obligation_ids": sorted(x["id"] for x in related),
                "concept_ids": concept_ids,
                "review_status": "pending",
                "canonical_url": f"{BASE}/roolipohjaiset-nakymat/{role_id}/",
                "api_url": f"{BASE}/api/{API_VERSION}/roles/{role_id}.json",
            },
            "derived",
            False,
        )
        roles.append(with_hash(record))

    return {
        "documents": sorted(documents, key=lambda x: x["id"]),
        "sections": sorted(sections, key=lambda x: x["id"]),
        "clauses": sorted(clauses, key=lambda x: x["id"]),
        "alignments": sorted(alignments, key=lambda x: x["id"]),
        "glossary": sorted(glossary, key=lambda x: x["id"]),
        "terminology": sorted(terminology, key=lambda x: x["id"]),
        "roles": sorted(roles, key=lambda x: x["id"]),
        "obligations": sorted(obligations, key=lambda x: x["id"]),
        "essential-records": sorted(essential, key=lambda x: x["id"]),
    }


DATASET_META = {
    "documents": ("Document", "id", "document.schema.json", "source_based"),
    "sections": ("GuidelineSection", "id", "section.schema.json", "source_based"),
    "clauses": ("GuidelineClause", "id", "clause.schema.json", "source_based"),
    "alignments": ("Alignment", "id", "alignment.schema.json", "derived"),
    "glossary": ("GlossaryEntry", "id", "glossary-entry.schema.json", "source_based"),
    "terminology": ("TerminologyEntry", "id", "terminology-entry.schema.json", "source_based"),
    "roles": ("RoleCollection", "id", "role.schema.json", "derived"),
    "obligations": ("Obligation", "id", "obligation.schema.json", "derived"),
    "essential-records": ("EssentialRecord", "id", "essential-record.schema.json", "derived"),
}


def record_schema(name: str, title: str, derived: bool) -> dict[str, Any]:
    required_by_name = {
        "documents": ["id", "type", "language", "source_version", "classification", "authoritative", "content_hash"],
        "sections": ["id", "type", "section_number", "title_fi", "text_fi", "canonical_url", "api_url", "content_hash"],
        "clauses": ["id", "type", "section_number", "parent_section_id", "text_fi", "canonical_url", "api_url", "content_hash"],
        "alignments": ["id", "type", "finnish_id", "method", "classification", "review_status", "content_hash"],
        "glossary": ["id", "type", "preferred_label_fi", "definition_fi", "canonical_url", "api_url", "content_hash"],
        "terminology": ["id", "type", "term_en", "preferred_label_fi", "api_url", "content_hash"],
        "roles": ["id", "type", "title_fi", "section_ids", "obligation_ids", "classification", "review_status", "content_hash"],
        "obligations": ["id", "obligation_id", "type", "source_section_id", "source_text_fi", "classification", "review_status", "content_hash"],
        "essential-records": ["id", "type", "name_fi", "source_section", "classification", "review_status", "content_hash"],
    }
    properties: dict[str, Any] = {
        "id": {"type": "string", "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]*$"},
        "type": {"type": "string", "minLength": 1},
        "corpus_version": {"const": VERSION},
        "schema_version": {"const": SCHEMA_VERSION},
        "pipeline_version": {"type": "string"},
        "classification": {"type": "string"},
        "authoritative": {"type": "boolean"},
        "review_status": {"type": "string"},
        "content_hash": {"type": "string", "pattern": "^sha256:[a-f0-9]{64}$"},
        "canonical_url": {"type": ["string", "null"]},
        "api_url": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    }
    if derived:
        properties["classification"] = {"const": "derived"}
        properties["review_status"] = {"const": "pending"}
    record_definition = {
        "type": "object",
        "required": ["corpus_version", "schema_version", *required_by_name[name]],
        "properties": properties,
        "additionalProperties": True,
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}/schemas/v1/{DATASET_META[name][2]}",
        "title": title,
        "description": f"Record or versioned collection schema for {name}.",
        "$defs": {"record": record_definition},
        "oneOf": [
            {"$ref": "#/$defs/record"},
            {
                "type": "object",
                "required": ["corpus_version", "schema_version", "record_type", "count", "records", "content_hash"],
                "properties": {
                    "corpus_version": {"const": VERSION},
                    "schema_version": {"const": SCHEMA_VERSION},
                    "record_type": {"type": "string"},
                    "count": {"type": "integer", "minimum": 0},
                    "records": {"type": "array", "items": {"$ref": "#/$defs/record"}},
                    "classification": {"type": "string"},
                    "review_status": {"const": "pending"} if derived else {"type": ["string", "null"]},
                    "content_hash": {"type": "string", "pattern": "^sha256:[a-f0-9]{64}$"},
                },
                "additionalProperties": True,
            },
        ],
    }


def dataset_wrapper(name: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    record_type, _, _, classification = DATASET_META[name]
    wrapper: dict[str, Any] = {
        "corpus_version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "record_type": record_type,
        "classification": classification,
        "count": len(records),
        "records": records,
    }
    if classification == "derived":
        wrapper.update({"review_status": "pending", "authoritative": False})
    return with_hash(wrapper)


def rights_data() -> dict[str, Any]:
    unknown = {
        "redistribution": "subject_to_source_rights",
        "modification": "not_determined",
        "commercial_use": "not_determined",
        "indexing": "not_specified",
        "rag_use": "not_specified",
        "model_training": "not_specified",
    }
    records = [
        {
            "id": "project-code",
            "description": "Quartz and project-authored software code.",
            "rights_holder": "respective code authors",
            "copyright_status": "copyrighted",
            "license_identifier": "MIT",
            "license_url": f"{CONFIG['repository']}/blob/main/LICENSE.txt",
            "attribution_required": True,
            "redistribution": "permitted_under_mit",
            "modification": "permitted_under_mit",
            "commercial_use": "permitted_under_mit",
            "indexing": "permitted_under_mit",
            "rag_use": "not_applicable_to_code_license_scope",
            "model_training": "not_specified",
        },
        {
            "id": "english-ich-source",
            "description": "Authoritative English ICH E6(R3) source content.",
            "rights_holder": "original source rights holders",
            "copyright_status": "third_party_source",
            "license_identifier": None,
            "license_url": None,
            "attribution_required": "subject_to_source_rights",
            **unknown,
        },
        {
            "id": "finnish-translation",
            "description": "Unofficial Finnish translation published by Fimea.",
            "rights_holder": "translation and source rights holders",
            "copyright_status": "third_party_translation",
            "license_identifier": None,
            "license_url": None,
            "attribution_required": "subject_to_source_rights",
            **unknown,
        },
        {
            "id": "extracted-source-quotations",
            "description": "Source-faithful quotations extracted for section and clause retrieval.",
            "rights_holder": "underlying source rights holders",
            "copyright_status": "contains_third_party_content",
            "license_identifier": None,
            "license_url": None,
            "attribution_required": "subject_to_source_rights",
            **unknown,
        },
        {
            "id": "structured-metadata",
            "description": "Project-created identifiers, schemas, manifests, relationships, and indexes, excluding embedded source text.",
            "rights_holder": "project contributors",
            "copyright_status": "project_created_structure",
            "license_identifier": None,
            "license_url": None,
            "attribution_required": "not_specified",
            "redistribution": "not_determined",
            "modification": "not_determined",
            "commercial_use": "not_determined",
            "indexing": "permitted_for_discovery",
            "rag_use": "subject_to_embedded_source_rights",
            "model_training": "not_specified",
        },
        {
            "id": "derived-obligations",
            "description": "Automatically derived obligation candidates; review status pending.",
            "rights_holder": "project contributors and underlying source rights holders",
            "copyright_status": "derived_contains_source_relationships",
            "license_identifier": None,
            "license_url": None,
            "attribution_required": "subject_to_source_rights",
            "classification": "derived",
            "review_status": "pending",
            **unknown,
        },
        {
            "id": "derived-role-views",
            "description": "Automatically derived role views; review status pending.",
            "rights_holder": "project contributors and underlying source rights holders",
            "copyright_status": "derived_contains_source_relationships",
            "license_identifier": None,
            "license_url": None,
            "attribution_required": "subject_to_source_rights",
            "classification": "derived",
            "review_status": "pending",
            **unknown,
        },
        {
            "id": "website-pages-and-reports",
            "description": "Combined website pages and validation reports.",
            "rights_holder": "project contributors and underlying source rights holders",
            "copyright_status": "mixed_rights",
            "license_identifier": None,
            "license_url": None,
            "attribution_required": "subject_to_component_rights",
            **unknown,
        },
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "corpus_version": VERSION,
        "disclaimer": "This machine-readable statement is not legal advice and does not grant rights the project does not possess.",
        "human_readable_url": f"{BASE}/rights/",
        "asset_classes": records,
    }


def write_schemas() -> list[dict[str, Any]]:
    schema_entries: list[dict[str, Any]] = []
    for name, (title, _, filename, classification) in DATASET_META.items():
        schema = record_schema(name, title, classification == "derived")
        for root in (PUBLIC / "schemas" / "v1", PUBLIC / "schemas" / "latest"):
            write_json(root / filename, schema)
        path = PUBLIC / "schemas" / "v1" / filename
        schema_entries.append(
            {
                "schema_id": name,
                "url": f"{BASE}/schemas/v1/{filename}",
                "schema_version": SCHEMA_VERSION,
                "sha256": digest_file(path),
            }
        )
    manifest_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}/schemas/v1/corpus-manifest.schema.json",
        "title": "Corpus manifest",
        "type": "object",
        "required": ["corpus_id", "corpus_version", "schema_version", "datasets", "schemas", "rights", "release"],
        "properties": {
            "corpus_id": {"const": CONFIG["corpus_id"]},
            "corpus_version": {"const": VERSION},
            "schema_version": {"const": SCHEMA_VERSION},
            "datasets": {"type": "array"},
            "schemas": {"type": "array"},
            "rights": {"type": "object"},
            "release": {"type": "object"},
        },
        "additionalProperties": True,
    }
    for root in (PUBLIC / "schemas" / "v1", PUBLIC / "schemas" / "latest"):
        write_json(root / "corpus-manifest.schema.json", manifest_schema)
    schema_entries.append(
        {
            "schema_id": "corpus-manifest",
            "url": f"{BASE}/schemas/v1/corpus-manifest.schema.json",
            "schema_version": SCHEMA_VERSION,
            "sha256": digest_file(PUBLIC / "schemas" / "v1" / "corpus-manifest.schema.json"),
        }
    )
    schema_index = {
        "schema_version": SCHEMA_VERSION,
        "draft": "https://json-schema.org/draft/2020-12/schema",
        "schemas": schema_entries,
    }
    write_json(PUBLIC / "schemas" / "v1" / "index.json", schema_index)
    write_json(PUBLIC / "schemas" / "latest" / "index.json", schema_index)
    return schema_entries


def write_openapi() -> None:
    paths: dict[str, Any] = {}
    literal_paths = ["/api/index.json", "/api/search-index.json", f"/api/{API_VERSION}/manifest.json"]
    for name in DATASET_META:
        literal_paths.append(f"/api/{API_VERSION}/{name}.json")
        literal_paths.append(f"/api/{API_VERSION}/downloads/{name}.jsonl")
    for path in literal_paths:
        paths[path] = {
            "get": {
                "summary": f"Retrieve static resource {path}",
                "responses": {"200": {"description": "Pre-generated static file"}, "404": {"description": "GitHub Pages static 404 response"}},
            }
        }
    for plural in ("documents", "sections", "clauses", "concepts", "terminology", "alignments", "obligations", "roles", "essential-records"):
        paths[f"/api/{API_VERSION}/{plural}/{{record_id}}.json"] = {
            "get": {
                "summary": f"Retrieve one pre-generated {plural} record",
                "description": "The path documents existing static files; the host does not execute path-parameter logic.",
                "parameters": [{"name": "record_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Pre-generated JSON record"}, "404": {"description": "Static 404 response"}},
            }
        }
    document = {
        "openapi": "3.1.0",
        "info": {
            "title": "ICH E6(R3) Static Corpus Interface",
            "version": VERSION,
            "description": "Immutable and pre-generated static resources hosted on GitHub Pages. This is not a dynamically executed API; only GET retrieval is supported.",
        },
        "servers": [{"url": BASE}],
        "paths": paths,
    }
    write_json(PUBLIC / "openapi.json", document)
    # JSON is valid YAML 1.2 and keeps both descriptions byte-for-byte consistent.
    write_json(PUBLIC / "api" / "openapi.yaml", document)


def record_filename(name: str, record: dict[str, Any]) -> str:
    if name == "glossary":
        return f"{record['slug']}.json"
    return f"{record['id']}.json"


def record_directory(name: str) -> str:
    return {"glossary": "concepts"}.get(name, name)


def write_datasets(records: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    wrappers: dict[str, dict[str, Any]] = {}
    dataset_entries: list[dict[str, Any]] = []
    downloads = PUBLIC / "api" / API_VERSION / "downloads"
    checksum_targets: list[Path] = []
    for name, items in records.items():
        wrapper = dataset_wrapper(name, items)
        wrappers[name] = wrapper
        for root in (PUBLIC / "data" / "v1", PUBLIC / "data" / "latest"):
            write_json(root / f"{name}.json", wrapper)
        api_collection = PUBLIC / "api" / API_VERSION / f"{name}.json"
        write_json(api_collection, wrapper)
        checksum_targets.append(api_collection)
        directory = PUBLIC / "api" / API_VERSION / record_directory(name)
        for record in items:
            write_json(directory / record_filename(name, record), record)
        jsonl = downloads / f"{name}.jsonl"
        write_text(jsonl, "\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for x in items))
        checksum_targets.append(jsonl)
        record_type, id_field, schema_file, classification = DATASET_META[name]
        data_path = PUBLIC / "data" / "v1" / f"{name}.json"
        dataset_entries.append(
            {
                "dataset_id": name,
                "title": record_type,
                "url": f"{BASE}/data/v1/{name}.json",
                "record_type": record_type,
                "media_type": "application/json",
                "schema_url": f"{BASE}/schemas/v1/{schema_file}",
                "corpus_version": VERSION,
                "schema_version": SCHEMA_VERSION,
                "id_field": id_field,
                "record_count": len(items),
                "classification": classification,
                "review_status": "pending" if classification == "derived" else None,
                "authoritative": False,
                "last_generated": GENERATED_AT,
                "sha256": digest_file(data_path),
                "jsonl_url": f"{BASE}/api/{API_VERSION}/downloads/{name}.jsonl",
            }
        )
    lines = []
    for path in sorted(checksum_targets, key=lambda value: value.as_posix()):
        lines.append(f"{digest_file(path)}  /{path.relative_to(PUBLIC).as_posix()}")
    write_text(downloads / "checksums.sha256", "\n".join(lines))
    dataset_index = {
        "corpus_version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "datasets": dataset_entries,
    }
    write_json(PUBLIC / "data" / "v1" / "index.json", dataset_index)
    write_json(PUBLIC / "data" / "latest" / "index.json", dataset_index)
    return wrappers, dataset_entries


def write_static_indexes(records: dict[str, list[dict[str, Any]]], wrappers: dict[str, dict[str, Any]]) -> None:
    record_types: dict[str, Any] = {}
    for name, (_, _, schema_file, classification) in DATASET_META.items():
        record_types[name] = {
            "dataset": f"/data/v1/{name}.json",
            "records_base": f"/api/{API_VERSION}/{record_directory(name)}/",
            "schema": f"/schemas/v1/{schema_file}",
            "classification": classification,
            "review_status": "pending" if classification == "derived" else None,
        }
    write_json(
        PUBLIC / "api" / "index.json",
        {
            "corpus_id": CONFIG["corpus_id"],
            "corpus_version": VERSION,
            "schema_version": SCHEMA_VERSION,
            "api_version": API_VERSION,
            "static_read_only": True,
            "record_types": record_types,
        },
    )
    search_records: list[dict[str, Any]] = []
    for name, items in records.items():
        for record in items:
            title = (
                record.get("title_fi")
                or record.get("preferred_label_fi")
                or record.get("name_fi")
                or record.get("term_en")
                or record.get("id")
            )
            excerpt = record.get("text_fi") or record.get("definition_fi") or record.get("source_text_fi") or ""
            search_records.append(
                {
                    "id": record["id"],
                    "record_type": name,
                    "title": title,
                    "language": "fi" if any(key in record for key in ("title_fi", "text_fi", "name_fi", "preferred_label_fi")) else record.get("language"),
                    "page_url": record.get("canonical_url"),
                    "api_url": record.get("api_url"),
                    "classification": record.get("classification"),
                    "review_status": record.get("review_status"),
                    "section_id": record.get("source_section_id") or record.get("parent_section_id"),
                    "role_ids": record.get("responsible_actor", []),
                    "excerpt": re.sub(r"\s+", " ", str(excerpt)).strip()[:360],
                }
            )
    write_json(
        PUBLIC / "api" / "search-index.json",
        {
            "corpus_version": VERSION,
            "schema_version": SCHEMA_VERSION,
            "count": len(search_records),
            "records": sorted(search_records, key=lambda x: (x["record_type"], x["id"])),
        },
    )

    api_manifest = with_hash(
        {
            "api_version": API_VERSION,
            "schema_version": SCHEMA_VERSION,
            "dataset_version": VERSION,
            "generated_at": GENERATED_AT,
            "base_url": f"{BASE}/api/{API_VERSION}/",
            "languages": CONFIG["available_languages"],
            "source_documents": records["documents"],
            "record_counts": {name: len(items) for name, items in records.items()},
            "downloads": {name: f"/api/{API_VERSION}/downloads/{name}.jsonl" for name in records},
            "checksums": f"/api/{API_VERSION}/downloads/checksums.sha256",
            "openapi": "/openapi.json",
        }
    )
    write_json(PUBLIC / "api" / API_VERSION / "manifest.json", api_manifest)


def write_review(records: dict[str, list[dict[str, Any]]]) -> None:
    review_dir = PUBLIC / "review" / "v1"
    for name in ("obligations", "roles"):
        rows = []
        for record in records[name]:
            rows.append(
                {
                    "record_id": record["id"],
                    "source_citation": record.get("source_page_url") or ", ".join(record.get("section_ids", [])),
                    "source_text": record.get("source_text_fi", ""),
                    "current_interpretation": record.get("normalized_action_fi") or record.get("description_fi", ""),
                    "issue_flags": record.get("issue_flags", []),
                    "review_status": "pending",
                    "reviewer_comments": "",
                    "proposed_correction": "",
                    "reviewer_identity": "",
                    "review_date": "",
                }
            )
        write_json(review_dir / f"{name}-review.json", {"corpus_version": VERSION, "review_status": "pending", "records": rows})
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=list(rows[0]) if rows else ["record_id"])
        writer.writeheader()
        for row in rows:
            csv_row = dict(row)
            csv_row["issue_flags"] = "|".join(row["issue_flags"])
            writer.writerow(csv_row)
        write_text(review_dir / f"{name}-review.csv", output.getvalue())


def write_release() -> dict[str, Any]:
    changes = {
        "corpus_version": VERSION,
        "previous_corpus_version": None,
        "release_date": RELEASE_DATE,
        "baseline_release": True,
        "changes": [
            {
                "change_type": "metadata_changed",
                "record_type": "corpus",
                "record_id": CONFIG["corpus_id"],
                "classification": "project_metadata",
                "previous_corpus_version": None,
                "current_corpus_version": VERSION,
                "requires_reindex": True,
                "description": "Baseline publication of the static machine-readable corpus interface.",
            }
        ],
    }
    write_json(PUBLIC / "changes.json", changes)
    release_dir = PUBLIC / "releases" / VERSION
    write_json(release_dir / "changes.json", changes)
    release_manifest = {
        "corpus_id": CONFIG["corpus_id"],
        "corpus_version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "release_date": RELEASE_DATE,
        "manifest": f"{BASE}/corpus-manifest.json",
        "changes": f"{BASE}/releases/{VERSION}/changes.json",
        "package": f"{BASE}/releases/{VERSION}/ich-e6-r3-fin-{VERSION}.zip",
        "package_checksum": f"{BASE}/releases/{VERSION}/ich-e6-r3-fin-{VERSION}.zip.sha256",
    }
    write_json(release_dir / "manifest.json", release_manifest)
    write_json(
        PUBLIC / "releases" / "index.json",
        {"latest": VERSION, "releases": [release_manifest]},
    )
    feed = f'''<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>{BASE}/feed.xml</id>
  <title>ICH E6(R3) Finnish Knowledge Base releases</title>
  <updated>{RELEASE_DATE}T00:00:00Z</updated>
  <link href="{BASE}/feed.xml" rel="self"/>
  <entry>
    <id>{BASE}/releases/{VERSION}/manifest.json</id>
    <title>Corpus release {VERSION}</title>
    <updated>{RELEASE_DATE}T00:00:00Z</updated>
    <link href="{BASE}/releases/{VERSION}/manifest.json"/>
    <summary>Baseline static machine-readable corpus release.</summary>
  </entry>
</feed>'''
    write_text(PUBLIC / "feed.xml", feed)
    return release_manifest


def write_manifest(dataset_entries: list[dict[str, Any]], schemas: list[dict[str, Any]], release: dict[str, Any]) -> dict[str, Any]:
    manifest = {
        "corpus_id": CONFIG["corpus_id"],
        "corpus_version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "title": CONFIG["title"],
        "canonical_site": BASE,
        "repository": CONFIG["repository"],
        "publishing_model": "static-github-pages-quartz",
        "authoritative_language": CONFIG["authoritative_language"],
        "available_languages": CONFIG["available_languages"],
        "derived_content_review_status": "pending",
        "datasets": dataset_entries,
        "schemas": schemas,
        "validation_reports": [
            {"title": path.stem, "url": f"{BASE}/reports/{path.name}"}
            for path in sorted(REPORTS.glob("*.md"))
        ],
        "rights": {"human_readable": f"{BASE}/rights/", "machine_readable": RIGHTS_URL},
        "citation_policy": {
            "preferred": "Cite the source section or clause, stable identifier, corpus version, and canonical URL.",
            "source_first": True,
            "derived_warning": "Derived obligations and role views are pending and non-authoritative.",
        },
        "release": release,
        "checksums": {entry["dataset_id"]: entry["sha256"] for entry in dataset_entries},
    }
    write_json(PUBLIC / "corpus-manifest.json", manifest)
    write_json(PUBLIC / "releases" / VERSION / "corpus-manifest.json", manifest)
    return manifest


def write_llms() -> None:
    write_text(
        PUBLIC / "llms.txt",
        f"""# ICH E6(R3) Finnish Knowledge Base

Purpose: Static bilingual study and retrieval corpus for ICH E6(R3).
Canonical site: {BASE}/
Repository: {CONFIG['repository']}
Manifest: {BASE}/corpus-manifest.json
Static interface: {BASE}/api/index.json
OpenAPI: {BASE}/openapi.json
Schemas: {BASE}/schemas/v1/index.json
Datasets: {BASE}/data/v1/index.json
Validation reports: {BASE}/reports/index.json
Rights statement: {BASE}/rights/
Machine-readable rights: {RIGHTS_URL}

Corpus version: {VERSION}
Schema version: {SCHEMA_VERSION}
Authoritative language: English
Available languages: English and Finnish
Finnish content status: unofficial translation
Derived content classification: derived
Derived content review status: pending

Agents should prefer source sections and clauses, preserve stable identifiers and source citations, and verify the English source where authority matters. Derived obligations, alignments, essential-record mappings, and role views are non-authoritative and must not be treated as expert-reviewed or used as the sole basis for regulatory, clinical, legal, or compliance decisions.
""",
    )


def enrich_jsonld(records: dict[str, list[dict[str, Any]]]) -> None:
    subject_by_url: dict[str, str] = {}
    derived_by_url: dict[str, dict[str, Any]] = {}
    for name in ("sections", "glossary", "roles"):
        for record in records[name]:
            url = record.get("canonical_url")
            if url:
                subject_by_url[url.rstrip("/")] = record["api_url"]
                if record.get("classification") == "derived":
                    derived_by_url[url.rstrip("/")] = record
    subject_by_url[f"{BASE}/vastuutaulukot"] = f"{BASE}/api/{API_VERSION}/obligations.json"
    derived_by_url[f"{BASE}/vastuutaulukot"] = {"classification": "derived", "review_status": "pending", "source_page_url": None}
    pattern = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
    for path in PUBLIC.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        match = pattern.search(text)
        if not match:
            continue
        data = json.loads(html.unescape(match.group(1)))
        page_url = str(data.get("url") or "").rstrip("/")
        data["@id"] = data.get("url")
        data["version"] = VERSION
        data["dateModified"] = RELEASE_DATE
        data["license"] = RIGHTS_URL
        data["isPartOf"] = {"@id": f"{BASE}/#corpus", "@type": "DataCatalog", "name": CONFIG["title"]}
        data["description"] = data.get("description") or "Independent unofficial study corpus; not reviewed, approved, sponsored, or endorsed by ICH, EMA, or Fimea."
        if page_url == BASE:
            data["@type"] = "WebSite"
            data["subjectOf"] = {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{BASE}/corpus-manifest.json"}
        elif page_url in subject_by_url:
            data["subjectOf"] = {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": subject_by_url[page_url]}
        if page_url in derived_by_url:
            record = derived_by_url[page_url]
            data["additionalProperty"] = [
                {"@type": "PropertyValue", "name": "classification", "value": "derived"},
                {"@type": "PropertyValue", "name": "review_status", "value": "pending"},
                {"@type": "PropertyValue", "name": "authoritative", "value": False},
            ]
            source_urls = []
            if record.get("source_page_url"):
                source_urls.append(record["source_page_url"])
            if record.get("section_ids"):
                section_map = {x["id"]: x["canonical_url"] for x in records["sections"]}
                source_urls.extend(section_map[sid] for sid in record["section_ids"] if sid in section_map)
            if source_urls:
                data["isBasedOn"] = [{"@type": "TechArticle", "@id": url} for url in sorted(set(source_urls))]
        replacement = f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False, separators=(",", ":"))}</script>'
        text = text[: match.start()] + replacement + text[match.end() :]
        if data.get("url") and 'rel="canonical"' not in text:
            text = text.replace("</head>", f'<link rel="canonical" href="{html.escape(str(data["url"]), quote=True)}"></head>', 1)
        path.write_text(text, encoding="utf-8", newline="\n")


def copy_reports() -> None:
    target = PUBLIC / "reports"
    target.mkdir(parents=True, exist_ok=True)
    for path in REPORTS.glob("*.md"):
        shutil.copy2(path, target / path.name)
    write_json(
        target / "index.json",
        {
            "corpus_version": VERSION,
            "reports": [
                {
                    "title": path.stem,
                    "url": f"{BASE}/reports/{path.name}",
                    "sha256": digest_file(target / path.name),
                }
                for path in sorted(REPORTS.glob("*.md"))
            ],
        },
    )


def write_release_zip() -> None:
    target = PUBLIC / "releases" / VERSION / f"ich-e6-r3-fin-{VERSION}.zip"
    include = [
        PUBLIC / "llms.txt",
        PUBLIC / "corpus-manifest.json",
        PUBLIC / "openapi.json",
        PUBLIC / "changes.json",
        PUBLIC / "rights" / "rights.json",
    ]
    for directory in (
        PUBLIC / "data" / "v1",
        PUBLIC / "schemas" / "v1",
        PUBLIC / "api" / API_VERSION,
        PUBLIC / "review" / "v1",
        PUBLIC / "reports",
    ):
        include.extend(path for path in directory.rglob("*") if path.is_file())
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(set(include), key=lambda item: item.relative_to(PUBLIC).as_posix()):
            info = zipfile.ZipInfo(path.relative_to(PUBLIC).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    write_text(
        target.with_suffix(target.suffix + ".sha256"),
        f"{digest_file(target)}  {target.name}",
    )


def main() -> None:
    if not PUBLIC.exists():
        raise SystemExit("Quartz output public/ is missing; run the Quartz build first.")
    for directory in ("api", "data", "schemas", "review", "releases"):
        target = PUBLIC / directory
        if target.exists():
            shutil.rmtree(target)
    records = build_records()
    write_json(DATA / "clauses.json", records["clauses"])
    schemas = write_schemas()
    wrappers, dataset_entries = write_datasets(records)
    write_static_indexes(records, wrappers)
    write_openapi()
    write_json(PUBLIC / "rights" / "rights.json", rights_data())
    write_review(records)
    release = write_release()
    write_manifest(dataset_entries, schemas, release)
    write_llms()
    copy_reports()
    enrich_jsonld(records)
    write_release_zip()
    print(
        f"Machine resources generated: {sum(len(items) for items in records.values())} records, "
        f"{len(dataset_entries)} datasets, {len(schemas)} schemas."
    )


if __name__ == "__main__":
    main()

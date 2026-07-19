from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import unicodedata
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
REPORTS = ROOT / "reports"
CONFIG = json.loads((ROOT / "machine-readable-config.json").read_text(encoding="utf-8"))
BASE = CONFIG["canonical_site"].rstrip("/")
VERSION = CONFIG["corpus_version"]
API_VERSION = CONFIG["api_version"]

SCHEMAS = {
    "documents": "document.schema.json",
    "sections": "section.schema.json",
    "clauses": "clause.schema.json",
    "alignments": "alignment.schema.json",
    "glossary": "glossary-entry.schema.json",
    "terminology": "terminology-entry.schema.json",
    "roles": "role.schema.json",
    "obligations": "obligation.schema.json",
    "essential-records": "essential-record.schema.json",
}
DERIVED = {"alignments", "roles", "obligations", "essential-records"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def deterministic_bytes(value) -> bytes:
    return unicodedata.normalize(
        "NFC", json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    ).encode("utf-8")


def content_hash(record: dict) -> str:
    value = dict(record)
    value.pop("content_hash", None)
    return "sha256:" + hashlib.sha256(deterministic_bytes(value)).hexdigest()


def local_url(url: str) -> Path | None:
    parts = urlsplit(url)
    clean = unquote(parts.path)
    base_path = urlsplit(BASE).path.rstrip("/")
    if parts.netloc and parts.netloc != urlsplit(BASE).netloc:
        return None
    if base_path and clean.startswith(base_path + "/"):
        clean = clean[len(base_path) :]
    elif clean == base_path:
        clean = "/"
    candidate = PUBLIC / clean.lstrip("/")
    if clean.endswith("/"):
        candidate = candidate / "index.html"
    elif not candidate.suffix:
        html_candidate = candidate.with_suffix(".html")
        if html_candidate.exists():
            candidate = html_candidate
    return candidate


def refresh_release_package() -> None:
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
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(set(include), key=lambda item: item.relative_to(PUBLIC).as_posix()):
            info = zipfile.ZipInfo(path.relative_to(PUBLIC).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(target.suffix + ".sha256").write_text(
        f"{digest}  {target.name}\n", encoding="utf-8", newline="\n"
    )


def main() -> None:
    errors: list[str] = []
    required = [
        "llms.txt",
        "corpus-manifest.json",
        "openapi.json",
        "api/openapi.yaml",
        "api/index.json",
        "api/search-index.json",
        "data/v1/index.json",
        "schemas/v1/index.json",
        "reports/index.json",
        f"api/{API_VERSION}/manifest.json",
        "rights/rights.json",
        "feed.xml",
        "changes.json",
        "releases/index.json",
        f"releases/{VERSION}/manifest.json",
        f"releases/{VERSION}/changes.json",
        f"releases/{VERSION}/ich-e6-r3-fin-{VERSION}.zip",
        f"releases/{VERSION}/ich-e6-r3-fin-{VERSION}.zip.sha256",
        "review/v1/obligations-review.json",
        "review/v1/obligations-review.csv",
        "review/v1/roles-review.json",
        "review/v1/roles-review.csv",
    ]
    for relative in required:
        if not (PUBLIC / relative).exists():
            errors.append(f"Required machine resource is missing: {relative}")

    wrappers: dict[str, dict] = {}
    all_records: dict[str, list[dict]] = {}
    for name, schema_name in SCHEMAS.items():
        data_path = PUBLIC / "data" / "v1" / f"{name}.json"
        latest_path = PUBLIC / "data" / "latest" / f"{name}.json"
        api_path = PUBLIC / "api" / API_VERSION / f"{name}.json"
        schema_path = PUBLIC / "schemas" / "v1" / schema_name
        latest_schema = PUBLIC / "schemas" / "latest" / schema_name
        for path in (data_path, latest_path, api_path, schema_path, latest_schema):
            if not path.exists():
                errors.append(f"Required dataset or schema is missing: {path.relative_to(PUBLIC)}")
        if not all(path.exists() for path in (data_path, latest_path, api_path, schema_path)):
            continue
        wrapper = load(data_path)
        wrappers[name] = wrapper
        all_records[name] = wrapper.get("records", [])
        if wrapper != load(latest_path) or wrapper != load(api_path):
            errors.append(f"Versioned, latest, and API collections differ: {name}")
        if wrapper.get("count") != len(wrapper.get("records", [])):
            errors.append(f"Dataset count differs from record count: {name}")
        if wrapper.get("content_hash") != content_hash(wrapper):
            errors.append(f"Dataset content hash is invalid: {name}")
        schema = load(schema_path)
        try:
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(wrapper)
        except Exception as exc:  # jsonschema provides precise messages in the report.
            errors.append(f"Schema validation failed for {name}: {exc}")
        ids = [record.get("id") for record in wrapper.get("records", [])]
        if None in ids or len(ids) != len(set(ids)):
            errors.append(f"Missing or duplicate stable identifier: {name}")
        if ids != sorted(ids):
            errors.append(f"Records are not deterministically sorted: {name}")
        for record in wrapper.get("records", []):
            try:
                Draft202012Validator(schema).validate(record)
            except Exception as exc:
                errors.append(f"Record schema validation failed {name}/{record.get('id')}: {exc}")
            if record.get("content_hash") != content_hash(record):
                errors.append(f"Record content hash is invalid: {name}/{record.get('id')}")
            if name in DERIVED and (
                record.get("classification") != "derived" or record.get("review_status") != "pending"
            ):
                errors.append(f"Derived record is not pending: {name}/{record.get('id')}")
            directory = "concepts" if name == "glossary" else name
            filename = record.get("slug") if name == "glossary" else record.get("id")
            standalone = PUBLIC / "api" / API_VERSION / directory / f"{filename}.json"
            if not standalone.exists() or load(standalone) != record:
                errors.append(f"Standalone record is missing or inconsistent: {name}/{record.get('id')}")

        jsonl_path = PUBLIC / "api" / API_VERSION / "downloads" / f"{name}.jsonl"
        if not jsonl_path.exists():
            errors.append(f"JSONL download is missing: {name}")
        else:
            lines = [line for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line]
            try:
                jsonl_records = [json.loads(line) for line in lines]
                if jsonl_records != wrapper.get("records", []):
                    errors.append(f"JSONL records differ from aggregate dataset: {name}")
            except json.JSONDecodeError as exc:
                errors.append(f"Invalid JSONL in {name}: {exc}")

    if all(name in all_records for name in SCHEMAS):
        section_ids = {item["id"] for item in all_records["sections"]}
        clause_ids = {item["id"] for item in all_records["clauses"]}
        obligation_ids = {item["id"] for item in all_records["obligations"]}
        for clause in all_records["clauses"]:
            if clause.get("parent_section_id") not in section_ids:
                errors.append(f"Clause references missing section: {clause['id']}")
            clause_page = local_url(clause.get("canonical_url", ""))
            if clause_page is None or not clause_page.exists():
                errors.append(f"Clause canonical page does not resolve: {clause['id']}")
            else:
                fragment = unquote(urlsplit(clause["canonical_url"]).fragment)
                if fragment and f'id="{fragment}"' not in clause_page.read_text(encoding="utf-8"):
                    errors.append(f"Clause canonical anchor does not resolve: {clause['id']}")
        for obligation in all_records["obligations"]:
            if obligation.get("source_section_id") not in section_ids:
                errors.append(f"Obligation references missing section: {obligation['id']}")
            if any(cid not in clause_ids for cid in obligation.get("source_clause_ids", [])):
                errors.append(f"Obligation references missing clause: {obligation['id']}")
            if not obligation.get("source_text_fi"):
                errors.append(f"Obligation lacks exact Finnish source text: {obligation['id']}")
            if not 0 <= float(obligation.get("confidence", -1)) <= 1:
                errors.append(f"Obligation confidence outside 0..1: {obligation['id']}")
        for role in all_records["roles"]:
            if any(oid not in obligation_ids for oid in role.get("obligation_ids", [])):
                errors.append(f"Role references missing obligation: {role['id']}")
            if any(sid not in section_ids for sid in role.get("section_ids", [])):
                errors.append(f"Role references missing section: {role['id']}")

    manifest_path = PUBLIC / "corpus-manifest.json"
    if manifest_path.exists():
        manifest = load(manifest_path)
        manifest_schema = load(PUBLIC / "schemas" / "v1" / "corpus-manifest.schema.json")
        try:
            Draft202012Validator.check_schema(manifest_schema)
            Draft202012Validator(manifest_schema).validate(manifest)
        except Exception as exc:
            errors.append(f"Corpus manifest schema validation failed: {exc}")
        for dataset in manifest.get("datasets", []):
            target = local_url(dataset["url"])
            if target is None or not target.exists():
                errors.append(f"Manifest dataset URL does not resolve: {dataset['url']}")
            elif hashlib.sha256(target.read_bytes()).hexdigest() != dataset["sha256"]:
                errors.append(f"Manifest dataset checksum differs: {dataset['dataset_id']}")
            schema_target = local_url(dataset["schema_url"])
            if schema_target is None or not schema_target.exists():
                errors.append(f"Manifest schema URL does not resolve: {dataset['schema_url']}")
        for group in (manifest.get("schemas", []), manifest.get("validation_reports", [])):
            for entry in group:
                target = local_url(entry["url"])
                if target is None or not target.exists():
                    errors.append(f"Manifest resource URL does not resolve: {entry['url']}")

    checksums = PUBLIC / "api" / API_VERSION / "downloads" / "checksums.sha256"
    if checksums.exists():
        for line in checksums.read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", 1)
            target = PUBLIC / relative.lstrip("/")
            if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                errors.append(f"Bulk checksum mismatch: {relative}")

    openapi_path = PUBLIC / "openapi.json"
    if openapi_path.exists():
        openapi = load(openapi_path)
        if openapi.get("openapi") != "3.1.0" or not openapi.get("paths"):
            errors.append("OpenAPI document lacks version or paths.")
        for path, operations in openapi.get("paths", {}).items():
            if set(operations) != {"get"}:
                errors.append(f"OpenAPI path is not GET-only: {path}")
            for parameter in operations.get("get", {}).get("parameters", []):
                if parameter.get("in") == "query":
                    errors.append(f"OpenAPI contains unsupported query parameter: {path}")

    jsonld_count = 0
    jsonld_pattern = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
    for path in PUBLIC.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        match = jsonld_pattern.search(text)
        if not match:
            errors.append(f"JSON-LD missing after enrichment: {path.relative_to(PUBLIC)}")
            continue
        try:
            data = json.loads(html.unescape(match.group(1)))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid enriched JSON-LD {path.relative_to(PUBLIC)}: {exc}")
            continue
        jsonld_count += 1
        relative = path.relative_to(PUBLIC).as_posix()
        required_jsonld = ["@context", "@type", "@id", "name", "inLanguage", "url", "version", "license"]
        if relative != "404.html" and not relative.startswith("tags/"):
            required_jsonld.append("identifier")
        for key in required_jsonld:
            if not data.get(key):
                errors.append(f"Enriched JSON-LD field {key} missing: {path.relative_to(PUBLIC)}")
        if data.get("@id") != data.get("url"):
            errors.append(f"JSON-LD @id differs from canonical URL: {path.relative_to(PUBLIC)}")
        canonical_match = re.search(r'<link rel="canonical" href="([^"]+)">', text)
        if not canonical_match:
            errors.append(f"Canonical HTML link missing: {path.relative_to(PUBLIC)}")
        elif html.unescape(canonical_match.group(1)) != data.get("url"):
            errors.append(f"Canonical HTML link differs from JSON-LD URL: {path.relative_to(PUBLIC)}")
        is_derived_page = (
            relative.startswith("roolipohjaiset-nakymat/")
            and relative != "roolipohjaiset-nakymat/index.html"
        ) or relative == "vastuutaulukot/index.html"
        if is_derived_page:
            values = {item.get("name"): item.get("value") for item in data.get("additionalProperty", [])}
            if values.get("classification") != "derived" or values.get("review_status") != "pending":
                errors.append(f"Derived JSON-LD metadata missing: {relative}")
        subject = data.get("subjectOf")
        if isinstance(subject, dict) and subject.get("contentUrl"):
            target = local_url(subject["contentUrl"])
            if target is None or not target.exists():
                errors.append(f"JSON-LD data record does not resolve: {relative}")

    for path in PUBLIC.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".zip", ".png", ".woff", ".woff2", ".ico"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"Published text resource is not UTF-8: {path.relative_to(PUBLIC)}")
            continue
        if text != unicodedata.normalize("NFC", text):
            errors.append(f"Published text resource is not Unicode NFC: {path.relative_to(PUBLIC)}")
        if "file:///" in text or re.search(r"[A-Za-z]:\\(?:Users|Windows|Program Files)\\", text):
            errors.append(f"Published resource exposes a local path: {path.relative_to(PUBLIC)}")

    status = "HYVÄKSYTTY" if not errors else "HYLÄTTY"
    report = (
        "# Koneluettavuuden validointiraportti\n\n"
        f"- Tila: **{status}**\n"
        f"- Korpusversio: `{VERSION}`\n"
        f"- Aineistoja: {len(wrappers)}\n"
        f"- Tietueita: {sum(len(items) for items in all_records.values())}\n"
        f"- Rikastettuja JSON-LD-lohkoja: {jsonld_count}\n"
        "- JSON Schema Draft 2020-12, ristiviitteet, tarkistustilat, sisältötiivisteet, JSONL-lataukset, OpenAPI, manifestit ja julkaistut polut tarkistettiin.\n"
    )
    if errors:
        report += "\n## Virheet\n\n" + "\n".join(f"- {error}" for error in errors) + "\n"
    report_path = REPORTS / "machine-readability-report.md"
    report_path.write_text(report, encoding="utf-8", newline="\n")
    public_reports = PUBLIC / "reports"
    public_reports.mkdir(parents=True, exist_ok=True)
    for path in REPORTS.glob("*.md"):
        shutil.copy2(path, public_reports / path.name)
    report_index = {
        "corpus_version": VERSION,
        "reports": [
            {
                "title": path.stem,
                "url": f"{BASE}/reports/{path.name}",
                "sha256": hashlib.sha256((public_reports / path.name).read_bytes()).hexdigest(),
            }
            for path in sorted(REPORTS.glob("*.md"))
        ],
    }
    (public_reports / "index.json").write_text(
        json.dumps(report_index, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    refresh_release_package()
    if errors:
        raise SystemExit("\n".join(errors))
    print(
        f"Machine-readable validation passed: {len(wrappers)} datasets, "
        f"{sum(len(items) for items in all_records.values())} records, {jsonld_count} JSON-LD blocks."
    )


if __name__ == "__main__":
    main()

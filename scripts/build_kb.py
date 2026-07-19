from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"
DATA = ROOT / "data"
CONTENT = ROOT / "content"
REPORTS = ROOT / "reports"
FI_PDF = SOURCES / "ich-e6-r3-fi-v1-2026-07-09.pdf"
EN_PDF = SOURCES / "ich-e6-r3-en-step5-2025-01-23.pdf"

ROLE_IDS = [
    "tutkija",
    "toimeksiantaja",
    "tutkimuspaikan-henkilosto",
    "monitoroija",
    "riippumaton-eettinen-toimikunta",
    "tiedonhallinta-ja-tietokoneistetut-jarjestelmat",
    "palveluntarjoaja",
]

EXTRA_TITLED = [
    "3.10.1.1", "3.10.1.2", "3.10.1.3", "3.10.1.4", "3.10.1.5", "3.10.1.6",
    "3.11.2.1", "3.11.2.2", "3.11.4.1", "3.11.4.2", "3.11.4.3", "3.11.4.4",
    "3.11.4.5", "3.11.4.5.1", "3.11.4.5.2", "3.11.4.5.3", "3.11.4.5.4",
    "3.11.4.6", "A.1.1", "A.1.2",
]

FOLDERS = {
    "01-johdanto": "Johdanto",
    "02-gcp-periaatteet": "ICH:n määrittelemät hyvän kliinisen tutkimustavan periaatteet",
    "03-liite-1": "Liite 1",
    "04-liite-a-tutkijan-tietopaketti": "Täydentävä liite A – Tutkijan tietopaketti",
    "05-liite-b-tutkimussuunnitelma": "Täydentävä liite B – Tutkimussuunnitelma",
    "06-liite-c-oleelliset-tallenteet": "Täydentävä liite C – Oleelliset tallenteet",
    "sanasto": "Sanasto",
    "termisanasto": "EN–FI-termisanasto",
    "roolipohjaiset-nakymat": "Roolipohjaiset näkymät",
    "vastuutaulukot": "Vastuutaulukot",
}

HEADER_PATTERNS = [
    re.compile(r"^Ohje hyvän kliinisen tutkimustavan noudattamisesta$", re.I),
    re.compile(r"^\(GCP\) E6\(R3\)"),
    re.compile(r"^Sivu \d+/111$"),
    re.compile(r"^Guideline for good clinical practice \(GCP\) E6\(R3\)"),
    re.compile(r"^ICH E6 \(R3\) Guideline for good clinical practice \(GCP\)"),
    re.compile(r"^EMA/CHMP/ICH/135/1995.*Page \d+/71$"),
    re.compile(r"^Ohje hyvän kliinisen tutkimustavan noudattamisesta.*Sivu \d+/111$", re.I),
    re.compile(r"^(?:ICH E6 \(R3\) )?Guideline for good clinical practice.*Page \d+/71$", re.I),
]


@dataclass(frozen=True)
class PageLine:
    page: int
    text: str


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def ascii_slug(value: str) -> str:
    value = nfc(value).replace("–", "-").replace("—", "-")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(nfc(value).rstrip() + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_manifest() -> list[dict[str, Any]]:
    manifest_path = SOURCES / "manifest.yaml"
    if not manifest_path.exists():
        raise SystemExit("Lähdemanifesti puuttuu: sources/manifest.yaml")
    documents: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("- id:"):
            if current:
                documents.append(current)
            current = {"id": line.split(":", 1)[1].strip().strip('"')}
        elif current is not None and ":" in line and not line.startswith("#"):
            key, value = line.split(":", 1)
            value = value.strip().strip('"')
            current[key.strip()] = value
    if current:
        documents.append(current)
    for document in documents:
        source = SOURCES / document["filename"]
        if not source.exists():
            raise SystemExit(f"Lähdetiedosto puuttuu: {source}")
        actual = sha256(source)
        if actual.lower() != document["sha256"].lower():
            raise SystemExit(
                f"Lähdetiedoston SHA-256 ei vastaa manifestia: {source.name}\n"
                f"manifesti={document['sha256']}\ntoteutunut={actual}"
            )
    return documents


def clean_line(text: str) -> str:
    text = nfc(text).replace("\u00ad", "").replace("\uf0b7", "•")
    return re.sub(r"[ \t]+", " ", text).strip()


def is_header(line: str) -> bool:
    return not line or any(pattern.search(line) for pattern in HEADER_PATTERNS)


def extract_lines(pdf: pdfplumber.PDF, start: int, end: int) -> list[PageLine]:
    result: list[PageLine] = []
    for index in range(start - 1, end):
        text = pdf.pages[index].extract_text(x_tolerance=2, y_tolerance=3) or ""
        for raw in text.splitlines():
            line = clean_line(raw)
            if not is_header(line):
                result.append(PageLine(index + 1, line))
    return result


def parse_toc_line(text: str) -> tuple[str, str, int] | None:
    # The Finnish PDF sometimes positions the digits of a two-digit TOC
    # page number far enough apart that pdfplumber returns e.g. ``2 3``.
    # Treat the final run of digits and layout spaces after the dot leader as
    # one page number. The dot leader removes ambiguity with digits in titles.
    match = re.match(
        r"^((?:\d+|[ABC])(?:\.\d+)+)\s+(.+?)\s*\.{2,}\s*((?:\d\s*)+)\s*$",
        text,
    )
    if not match:
        return None
    title = match.group(2).strip(" .")
    if not title:
        return None
    return match.group(1), title, int(re.sub(r"\s+", "", match.group(3)))


def parse_toc(pdf: pdfplumber.PDF, start: int, end: int) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for line in extract_lines(pdf, start, end):
        parsed = parse_toc_line(line.text)
        if parsed:
            number, title, page = parsed
            result[number] = {"title": title, "page": page}
    return result


def title_key(text: str) -> str:
    return re.sub(r"[^a-z0-9åäö]+", "", text.casefold())


def find_start(
    lines: list[PageLine],
    section: str,
    title: str | None = None,
    expected_page: int | None = None,
    min_page: int | None = None,
    max_page: int | None = None,
) -> int | None:
    pattern = re.compile(rf"^{re.escape(section)}(?:\.|\s)\s*(.+)$") if section.isdigit() else re.compile(
        rf"^{re.escape(section)}\s+(.+)$"
    )
    candidates: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        if min_page is not None and line.page < min_page:
            continue
        if max_page is not None and line.page > max_page:
            continue
        match = pattern.match(line.text)
        if not match:
            continue
        rest = match.group(1).strip()
        if len(rest) > 150 or not rest or not rest[0].isupper():
            continue
        score = 0
        if expected_page is not None:
            score += abs(line.page - expected_page) * 20
        if title:
            a, b = title_key(rest), title_key(title)
            if a and b and (a.startswith(b[: min(18, len(b))]) or b.startswith(a[: min(18, len(a))])):
                score -= 30
            else:
                score += 25
        if re.search(r"\b(tulee|should|shall|may|voi|vastaa)\b", rest, re.I):
            score += 100
        score += len(rest) // 20
        candidates.append((score, index))
    return min(candidates)[1] if candidates else None


def collect_title(lines: list[PageLine], start: int, fallback: str) -> str:
    first = re.sub(r"^(?:[ABC]\.)?\d+(?:\.\d+)*\s+", "", lines[start].text).strip()
    if title_key(first) and title_key(fallback).startswith(title_key(first)):
        text = first
        cursor = start + 1
        while cursor < len(lines) and not title_key(text).startswith(title_key(fallback)):
            candidate = lines[cursor].text
            if re.match(r"^(?:\d+(?:\.\d+)+|\([a-zivx]+\)|•)\s*", candidate, re.I):
                break
            text += " " + candidate
            cursor += 1
        return fallback if len(title_key(text)) >= len(title_key(fallback)) * 0.8 else text
    return fallback or first


def section_folder(number: str, kind: str = "main") -> str:
    if kind == "intro":
        return "01-johdanto"
    if kind == "principle":
        return "02-gcp-periaatteet"
    if number.startswith("A."):
        return "04-liite-a-tutkijan-tietopaketti"
    if number.startswith("B."):
        return "05-liite-b-tutkimussuunnitelma"
    if number.startswith("C."):
        return "06-liite-c-oleelliset-tallenteet"
    return "03-liite-1"


def stable_id(number: str, kind: str = "main") -> str:
    if kind == "intro":
        return f"ich-e6-r3-introduction-{ascii_slug(number)}"
    if kind == "principle":
        return f"ich-e6-r3-principle-{int(number):02d}"
    if number.startswith("A."):
        return f"ich-e6-r3-app-a-{number[2:]}"
    if number.startswith("B."):
        return f"ich-e6-r3-app-b-{number[2:]}"
    if number.startswith("C."):
        return f"ich-e6-r3-app-c-{number[2:]}"
    return f"ich-e6-r3-a1-{number}"


def parent_id(number: str, kind: str) -> str | None:
    if kind in {"intro", "principle"}:
        return None
    if "." not in number:
        return None
    if re.match(r"^[ABC]\.\d+$", number):
        return f"ich-e6-r3-app-{number[0].lower()}"
    return stable_id(number.rsplit(".", 1)[0], kind)


def strip_heading(lines: list[PageLine], title: str) -> list[PageLine]:
    if not lines:
        return []
    consumed = 1
    accumulated = re.sub(r"^(?:[ABC]\.)?\d+(?:\.\d+)*\s+", "", lines[0].text)
    while consumed < min(4, len(lines)) and title_key(title).startswith(title_key(accumulated)):
        if len(title_key(accumulated)) >= len(title_key(title)) * 0.85:
            break
        nxt = lines[consumed].text
        if re.match(r"^(?:\d+(?:\.\d+)+|\([a-zivx]+\)|•)\s*", nxt, re.I):
            break
        accumulated += " " + nxt
        consumed += 1
    return lines[consumed:]


def anchor(section_id: str, suffix: str) -> str:
    prefix = section_id.replace(".", "-")
    clean = suffix.lower().replace(".", "-")
    section_number = section_id.rsplit("-", 1)[-1]
    if suffix.startswith(section_number + "."):
        clean = suffix[len(section_number) + 1 :].replace(".", "-")
    return f"{prefix}-{clean}"


def publication_text(
    lines: list[PageLine], section_id: str, language: str, root_number: str | None = None
) -> str:
    paragraphs: list[str] = []
    current = ""
    current_anchor: str | None = None

    def flush() -> None:
        nonlocal current, current_anchor
        if current.strip():
            hidden_anchor = f'<a id="{current_anchor}"></a>\n\n' if current_anchor and language == "fi" else ""
            paragraphs.append(hidden_anchor + current.strip())
        current = ""
        current_anchor = None

    for item in lines:
        line = item.text
        clause = re.match(r"^((?:\d+|[ABC])(?:\.\d+)+)\s+(.+)$", line)
        letter = re.match(r"^\(([a-z]|[ivx]+)\)\s*(.+)$", line, re.I)
        if clause and root_number and clause.group(1).startswith(root_number + "."):
            flush()
            cid, rest = clause.groups()
            paragraphs.append(
                f'<a id="{anchor(section_id, cid)}"></a>\n\n### {cid}'
                if language == "fi"
                else f"**{cid}**"
            )
            current = rest
        elif letter:
            flush()
            label, rest = letter.groups()
            current = f"- ({label}) {rest}"
            current_anchor = anchor(section_id, f"item-{label}")
        elif line.startswith("•"):
            flush()
            current = f"- {line[1:].strip()}"
        elif not line:
            flush()
        else:
            current = f"{current} {line}".strip()
    flush()
    text = "\n\n".join(paragraphs)
    if language == "en":
        return text
    return text


def parse_glossary(pdf: pdfplumber.PDF, start: int, end: int, language: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    last_was_bold = False
    for page_no in range(start, end + 1):
        page = pdf.pages[page_no - 1]
        for line in page.extract_text_lines(return_chars=True):
            text = clean_line(line["text"])
            if is_header(text) or text in {"Sanasto", "Glossary"}:
                continue
            is_bold = any("bold" in char.get("fontname", "").casefold() for char in line["chars"])
            if is_bold:
                if current and last_was_bold and line["top"] - current["last_top"] < 28 and current["page_end"] == page_no:
                    current["heading"] += " " + text
                    current["last_top"] = line["top"]
                    continue
                if current:
                    blocks.append(current)
                current = {
                    "heading": text,
                    "definition_lines": [],
                    "page_start": page_no,
                    "page_end": page_no,
                    "last_top": line["top"],
                }
                last_was_bold = True
            elif current:
                current["definition_lines"].append(text)
                current["page_end"] = page_no
                current["last_top"] = line["top"]
                last_was_bold = False
    if current:
        blocks.append(current)
    result = []
    for block in blocks:
        heading = block["heading"].strip()
        embedded_definition = ""
        if ": " in heading:
            heading, embedded_definition = heading.split(": ", 1)
            heading += ":"
        if len(heading) < 3 or heading.lower().startswith(("sivu ", "page ")):
            continue
        definition = " ".join(x for x in [embedded_definition, *block["definition_lines"]] if x)
        result.append({
            "heading": heading,
            "definition": definition,
            "pages": list(range(block["page_start"], block["page_end"] + 1)),
            "language": language,
        })
    return result


def glossary_terms(fi_pdf: pdfplumber.PDF, en_pdf: pdfplumber.PDF) -> list[dict[str, Any]]:
    fi_entries = parse_glossary(fi_pdf, 95, 105, "fi")
    en_entries = parse_glossary(en_pdf, 64, 71, "en")
    result: list[dict[str, Any]] = []
    used: set[str] = set()
    for index, entry in enumerate(fi_entries, 1):
        heading = entry["heading"].rstrip(":")
        match = re.match(r"^(.*?)\s*\((.+)\)$", heading)
        fi_term = (match.group(1) if match else heading).strip(" :")
        en_term = (match.group(2) if match else "").strip(" :")
        en_match = None
        if en_term:
            candidates = [x for x in en_entries if title_key(x["heading"]).startswith(title_key(en_term)[:20])]
            en_match = candidates[0] if candidates else None
        slug = ascii_slug(fi_term) or f"sanastotermi-{index:03d}"
        if slug in used:
            slug = f"{slug}-{index:03d}"
        used.add(slug)
        result.append({
            "id": f"ich-e6-r3-glossary-{slug}",
            "slug": slug,
            "preferred_term_fi": fi_term,
            "preferred_term_en": en_term or (en_match["heading"] if en_match else None),
            "abbreviations": re.findall(r"\b[A-Z][A-Z0-9/]{1,8}\b", heading),
            "definition_fi": entry["definition"],
            "definition_en": en_match["definition"] if en_match else None,
            "source_pages_fi": entry["pages"],
            "source_pages_en": en_match["pages"] if en_match else [],
            "schema_type": "DefinedTerm",
            "review_status": "source_extracted" if en_match else "english_alignment_pending",
        })
    return result


def extract_terminology(pdf: pdfplumber.PDF) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page_no in range(106, 112):
        for table in pdf.pages[page_no - 1].extract_tables():
            for row in table:
                cells = [clean_line(x or "") for x in row]
                left = " ".join(dict.fromkeys(x for x in cells[:3] if x))
                right = " ".join(dict.fromkeys(x for x in cells[3:] if x))
                if (len(left) == 1 and left.isalpha() and not right) or not (left or right):
                    continue
                if left and right:
                    rows.append({"term_en": left, "preferred_label_fi": right, "page": page_no})
                elif rows:
                    if left:
                        rows[-1]["term_en"] += " " + left
                    if right:
                        rows[-1]["preferred_label_fi"] += " " + right
    result = []
    for index, row in enumerate(rows, 1):
        result.append({
            "id": f"ich-e6-r3-term-{index:03d}",
            "entry_type": "translation_mapping",
            "term_en": row["term_en"],
            "preferred_label_fi": row["preferred_label_fi"],
            "definition_fi": None,
            "definition_en": None,
            "source": "fimea_en_fi_terminology",
            "source_page_fi": row["page"],
            "official_ich_glossary_entry": False,
        })
    return result


def semantic_record_names(pdf: pdfplumber.PDF, start: int, end: int, language: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    current = ""
    previous_top: float | None = None
    for page_no in range(start, end + 1):
        for line in pdf.pages[page_no - 1].extract_text_lines(return_chars=True):
            text = clean_line(line["text"])
            top = float(line["top"])
            table_headers = (
                "Oleellisten tallenteiden taulukko", "Jos nämä tutkimuksen tallenteet", "kappaleet C3.1",
                "Huomautus: Tähdellä", "käytettävissä ennen tutkimuksen aloittamista",
                "Essential records table", "If these trial records are produced", "C3.1 and C3.2",
                "Note: An asterisk", "start of the trial",
            )
            if is_header(text) or top > 730 or text.startswith(table_headers):
                previous_top = None
                continue
            gap = 99 if previous_top is None else top - previous_top
            if current and gap > 18.2:
                entries.append({"text": current, "page": page_no if previous_top is None else last_page})
                current = text
            else:
                current = f"{current} {text}".strip()
            previous_top, last_page = top, page_no
        previous_top = None
    if current:
        entries.append({"text": current, "page": last_page})
    return entries


def semantic_records(fi_pdf: pdfplumber.PDF, en_pdf: pdfplumber.PDF) -> list[dict[str, Any]]:
    fi_entries = semantic_record_names(fi_pdf, 91, 94, "fi")
    en_entries = semantic_record_names(en_pdf, 61, 63, "en")
    result = []
    for index, entry in enumerate(fi_entries, 1):
        before = "*" in entry["text"]
        en_entry = en_entries[index - 1] if index <= len(en_entries) else None
        result.append({
            "id": f"essential-record-{index:03d}",
            "name_fi": entry["text"].replace("*", "").strip(),
            "name_en": en_entry["text"].replace("*", "").strip() if en_entry else None,
            "required_before_trial_start": before,
            "source_section": "C.3",
            "source_pages_fi": [entry["page"]],
            "source_pages_en": [en_entry["page"]] if en_entry else [],
            "classification": "derived",
            "alignment_status": "automatically_aligned_by_table_order" if en_entry else "english_alignment_pending",
            "review_status": "pending",
        })
    return result


def roles_for(section: str, text: str) -> list[str]:
    roles: set[str] = set()
    if section.startswith("1"):
        roles.add("riippumaton-eettinen-toimikunta")
    elif section.startswith("2"):
        roles.update(["tutkija", "tutkimuspaikan-henkilosto"])
    elif section.startswith("3"):
        roles.add("toimeksiantaja")
    elif section.startswith("4"):
        roles.add("tiedonhallinta-ja-tietokoneistetut-jarjestelmat")
    low = text.casefold()
    if "monitor" in low:
        roles.add("monitoroija")
    if "palveluntarjo" in low:
        roles.add("palveluntarjoaja")
    return sorted(roles & set(ROLE_IDS))


def extract_clauses(text: str) -> dict[str, str]:
    matches = list(
        re.finditer(
            r'(?m)^(?:<a id="[^"]+"></a>\n\n)?(?:###\s+|\*\*)((?:\d+|[ABC])(?:\.\d+)+)(?:\*\*)?\s*\n\n',
            text,
        )
    )
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        clause_text = re.sub(r'<a id="[^"]+"></a>', "", text[match.end():end])
        result[match.group(1)] = re.sub(r"\s+", " ", clause_text).strip()
    return result


def build_obligations(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    obligations: list[dict[str, Any]] = []
    evidence = {
        "suostum": ["suostumusprosessin merkintä", "allekirjoitettu suostumuslomake", "koulutustallenne"],
        "monitor": ["monitorointisuunnitelma", "monitorointiraportti"],
        "turvall": ["turvallisuusraportti", "raportoinnin jäljitettävyystieto"],
        "tieto": ["tarkastusloki", "järjestelmän validointitallenne"],
    }
    counter = defaultdict(int)
    for section in sections:
        if section["kind"] != "main":
            continue
        fi_clauses = extract_clauses(section["text_fi"])
        en_clauses = extract_clauses(section["text_en"])
        for clause, fi_text in fi_clauses.items():
            modalities = re.findall(r"\b(tulee|ei saa|tulisi|voi|on vastuussa|vastaa)\b", fi_text, re.I)
            if not modalities:
                continue
            role_ids = roles_for(clause, fi_text)
            actor = role_ids[0] if role_ids else "toimeksiantaja"
            prefix = {"tutkija": "INV", "toimeksiantaja": "SPO", "riippumaton-eettinen-toimikunta": "IEC"}.get(actor, "GCP")
            counter[prefix] += 1
            sample_evidence: list[str] = []
            for key, values in evidence.items():
                if key in fi_text.casefold():
                    sample_evidence.extend(values)
            en_text = en_clauses.get(clause, "")
            en_modality = re.search(r"\b(should not|should|must not|must|may)\b", en_text, re.I)
            obligations.append({
                "obligation_id": f"{prefix}-{counter[prefix]:03d}",
                "responsible_actor": role_ids[:1] or [actor],
                "supporting_actors": role_ids[1:],
                "source_section": clause,
                "source_text_fi": fi_text,
                "source_text_en": en_text or None,
                "modality_fi": modalities[0],
                "modality_en": en_modality.group(1) if en_modality else None,
                "normalized_action_fi": fi_text,
                "condition_fi": None,
                "trigger_fi": None,
                "timing_fi": None,
                "example_evidence": list(dict.fromkeys(sample_evidence)),
                "evidence_status": "illustrative_not_source_requirement",
                "compound_clause": len(modalities) > 1,
                "confidence": 0.76 if len(modalities) > 1 or not en_text else 0.92,
                "classification": "derived",
                "authoritative": False,
                "derivation_method": "rule_based_modality_extraction",
                "review_status": "pending",
            })
    return obligations


def yaml_frontmatter(values: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in values.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {json.dumps(item, ensure_ascii=False)}")
        elif value is None:
            lines.append(f"{key}: null")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {json.dumps(str(value), ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def quote_callout(text: str, pages: list[int], section: str | None) -> str:
    if not text:
        return "> [!warning] Englanninkielistä vastinetta ei voitu kohdistaa automaattisesti.\n"
    source = f"ICH E6(R3), section {section}, pages {pages[0]}–{pages[-1]}." if section else f"ICH E6(R3), pages {pages[0]}–{pages[-1]}."
    quoted = "\n".join("> " + line if line else ">" for line in text.splitlines())
    return (
        "> [!quote]- Alkuperäinen englanninkielinen lähdeteksti\n>\n"
        "> <div lang=\"en\">\n>\n" + quoted + "\n>\n> </div>\n>\n> **Lähde:** " + source
    )


def link_glossary(text: str, glossary: list[dict[str, Any]]) -> tuple[str, int]:
    protected: list[str] = []
    def protect(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"\x00{len(protected)-1}\x00"
    text = re.sub(r"\[\[[^\]]+\]\]|^#{1,6}.*$|^>.*$|`[^`]*`", protect, text, flags=re.M)
    count = 0
    entries = [x for x in sorted(glossary, key=lambda x: len(x["preferred_term_fi"]), reverse=True) if len(x["preferred_term_fi"]) >= 4]
    by_term = {x["preferred_term_fi"].casefold(): x for x in entries}
    alternatives = "|".join(re.escape(x["preferred_term_fi"]) for x in entries)
    pattern = re.compile(rf"(?<![\wåäö])(?:{alternatives})(?![\wåäö])", re.I)
    def replace(match: re.Match[str]) -> str:
        nonlocal count
        entry = by_term[match.group(0).casefold()]
        count += 1
        return f"[[sanasto/{entry['slug']}|{match.group(0)}]]"
    text = pattern.sub(replace, text)
    for index, original in enumerate(protected):
        text = text.replace(f"\x00{index}\x00", original)
    return text, count


def build_sections(fi_pdf: pdfplumber.PDF, en_pdf: pdfplumber.PDF, glossary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fi_lines, en_lines = extract_lines(fi_pdf, 10, 94), extract_lines(en_pdf, 6, 63)
    fi_toc, en_toc = parse_toc(fi_pdf, 5, 9), parse_toc(en_pdf, 3, 5)
    fi_annex_start = next(i for i, line in enumerate(fi_lines) if line.text.startswith("III. "))
    en_annex_start = next(i for i, line in enumerate(en_lines) if line.text.startswith("III. "))
    fi_annex_page = fi_lines[fi_annex_start].page
    en_annex_page = en_lines[en_annex_start].page
    identifiers = list(en_toc)
    for extra in EXTRA_TITLED:
        if extra not in identifiers:
            identifiers.append(extra)
    definitions: list[dict[str, Any]] = []
    for number in identifiers:
        fi_info, en_info = fi_toc.get(number, {}), en_toc.get(number, {})
        fi_start = find_start(
            fi_lines,
            number,
            fi_info.get("title"),
            fi_info.get("page"),
            min_page=fi_annex_page,
        )
        en_start = find_start(
            en_lines,
            number,
            en_info.get("title"),
            en_info.get("page"),
            min_page=en_annex_page,
        )
        if fi_start is None:
            continue
        fi_title = collect_title(fi_lines, fi_start, fi_info.get("title", ""))
        en_title = collect_title(en_lines, en_start, en_info.get("title", "")) if en_start is not None else en_info.get("title", "")
        definitions.append({"number": number, "kind": "main", "fi_start": fi_start, "en_start": en_start, "fi_title": fi_title, "en_title": en_title})

    for number, fi_title, en_title, fi_page, en_page in [
        ("1", "Riippumaton eettinen toimikunta", "Institutional Review Board/Independent Ethics Committee", 18, 11),
        ("2", "Tutkija", "Investigator", 23, 15),
        ("3", "Toimeksiantaja", "Sponsor", 38, 25),
        ("4", "Tietojenhallinta – tutkija ja toimeksiantaja", "Data Governance – Investigator and Sponsor", 65, 43),
    ]:
        fs = find_start(fi_lines, number, fi_title, fi_page, min_page=fi_annex_page)
        es = find_start(en_lines, number, en_title, en_page, min_page=en_annex_page)
        if fs is not None:
            definitions.append({"number": number, "kind": "main", "fi_start": fs, "en_start": es, "fi_title": fi_title, "en_title": en_title})

    definitions.sort(key=lambda x: x["fi_start"])
    en_order = sorted((x for x in definitions if x["en_start"] is not None), key=lambda x: x["en_start"])
    en_next = {id(item): (en_order[i + 1]["en_start"] if i + 1 < len(en_order) else len(en_lines)) for i, item in enumerate(en_order)}
    sections: list[dict[str, Any]] = []
    for index, item in enumerate(definitions):
        fi_end = definitions[index + 1]["fi_start"] if index + 1 < len(definitions) else len(fi_lines)
        fi_unit = fi_lines[item["fi_start"]:fi_end]
        en_unit = en_lines[item["en_start"]:en_next[id(item)]] if item["en_start"] is not None else []
        fi_body = strip_heading(fi_unit, item["fi_title"])
        en_body = strip_heading(en_unit, item["en_title"])
        sid = stable_id(item["number"])
        exact_text_fi = publication_text(fi_body, sid, "fi", item["number"])
        # Keep the exact English heading in the English source block. Some
        # titled container sections have no body before their first child, so
        # dropping the heading would incorrectly make the alignment look empty.
        exact_text_en = publication_text(en_unit, sid, "en", item["number"])
        fi_text, links = link_glossary(exact_text_fi, glossary)
        sections.append({
            "id": sid, "kind": "main", "section_number": item["number"],
            "title_fi": f"{item['number']} {item['fi_title']}", "title_en": f"{item['number']} {item['en_title']}" if item["en_title"] else None,
            "parent_id": parent_id(item["number"], "main"), "folder": section_folder(item["number"]),
            "finnish_pages": sorted(set(x.page for x in fi_unit)), "english_pages": sorted(set(x.page for x in en_unit)),
            "text_fi": fi_text, "text_en": exact_text_en, "exact_text_fi": exact_text_fi,
            "exact_text_en": exact_text_en, "raw_body_fi": "\n".join(x.text for x in fi_body),
            "raw_body_en": "\n".join(x.text for x in en_unit), "raw_text_fi": "\n".join(x.text for x in fi_unit),
            "raw_text_en": "\n".join(x.text for x in en_unit), "glossary_link_count": links,
            "alignment_status": "alignment_candidate" if en_unit else "unresolved",
        })

    # Split the introduction symmetrically by the explicit headings used in
    # both sources. These are not Finnish-only structures.
    intro_definitions = [
        ("johdanto", "I. Johdanto", "I. Introduction"),
        ("soveltamisala", "Ohjeen soveltamisala", "Guideline scope"),
        ("rakenne", "Ohjeen rakenne", "Guideline structure"),
    ]
    intro_end = next(i for i, line in enumerate(fi_lines) if line.text.startswith("II. "))
    en_intro_end = next(i for i, line in enumerate(en_lines) if line.text.startswith("II. "))
    fi_intro_boundaries = [
        next(i for i, line in enumerate(fi_lines[:intro_end]) if line.text == title_fi)
        for _, title_fi, _ in intro_definitions
    ]
    en_intro_boundaries = [
        next(i for i, line in enumerate(en_lines[:en_intro_end]) if line.text == title_en)
        for _, _, title_en in intro_definitions
    ]
    fi_intro_units: dict[str, list[PageLine]] = {}
    en_intro_units: dict[str, list[PageLine]] = {}
    for index, (key, _, _) in enumerate(intro_definitions):
        fi_end = fi_intro_boundaries[index + 1] if index + 1 < len(fi_intro_boundaries) else intro_end
        en_end = en_intro_boundaries[index + 1] if index + 1 < len(en_intro_boundaries) else en_intro_end
        fi_intro_units[key] = fi_lines[fi_intro_boundaries[index]:fi_end]
        en_intro_units[key] = en_lines[en_intro_boundaries[index]:en_end]

    # The English page footnote is visually attached to Guideline scope but
    # pdfplumber places it after Guideline structure because it sits at the
    # bottom of the same page. Reattach it to the section it annotates.
    structure_unit = en_intro_units["rakenne"]
    footnote_start = next(
        (index for index, line in enumerate(structure_unit) if line.text.startswith("1 For the purpose of this guideline")),
        None,
    )
    if footnote_start is not None:
        en_intro_units["soveltamisala"].extend(structure_unit[footnote_start:])
        en_intro_units["rakenne"] = structure_unit[:footnote_start]

    for key, title_fi, title_en in intro_definitions:
        fi_unit = fi_intro_units[key]
        en_unit = en_intro_units[key]
        sid = stable_id(key, "intro")
        exact_text_fi = publication_text(fi_unit[1:], sid, "fi")
        exact_text_en = publication_text(en_unit, sid, "en")
        fi_text, links = link_glossary(exact_text_fi, glossary)
        sections.append({
            "id": sid, "kind": "intro", "section_number": key, "title_fi": title_fi,
            "title_en": title_en, "parent_id": None, "folder": "01-johdanto",
            "finnish_pages": sorted(set(x.page for x in fi_unit)),
            "english_pages": sorted(set(x.page for x in en_unit)), "text_fi": fi_text,
            "text_en": exact_text_en, "exact_text_fi": exact_text_fi,
            "exact_text_en": exact_text_en, "raw_body_fi": "\n".join(x.text for x in fi_unit[1:]),
            "raw_body_en": "\n".join(x.text for x in en_unit),
            "raw_text_fi": "\n".join(x.text for x in fi_unit),
            "raw_text_en": "\n".join(x.text for x in en_unit), "glossary_link_count": links,
            "alignment_status": "alignment_candidate",
        })

    # Preserve the complete preamble under II in both languages. It is
    # substantive source text, not merely a folder heading.
    principle_one_fi = next(
        i for i, line in enumerate(fi_lines[intro_end + 1:], intro_end + 1)
        if re.match(r"^1\.\s+", line.text)
    )
    principle_one_en = next(
        i for i, line in enumerate(en_lines[en_intro_end + 1:], en_intro_end + 1)
        if re.match(r"^1\.\s+", line.text)
    )
    fi_principles_intro = fi_lines[intro_end:principle_one_fi]
    en_principles_intro = en_lines[en_intro_end:principle_one_en]
    principles_sid = "ich-e6-r3-principles-introduction"
    principles_exact_fi = publication_text(fi_principles_intro[1:], principles_sid, "fi")
    principles_exact_en = publication_text(en_principles_intro, principles_sid, "en")
    principles_text_fi, principles_links = link_glossary(principles_exact_fi, glossary)
    sections.append({
        "id": principles_sid, "kind": "principles_intro", "section_number": "periaatteiden-johdanto",
        "title_fi": fi_principles_intro[0].text, "title_en": en_principles_intro[0].text,
        "parent_id": None, "folder": "02-gcp-periaatteet",
        "finnish_pages": sorted(set(x.page for x in fi_principles_intro)),
        "english_pages": sorted(set(x.page for x in en_principles_intro)),
        "text_fi": principles_text_fi, "text_en": principles_exact_en,
        "exact_text_fi": principles_exact_fi, "exact_text_en": principles_exact_en,
        "raw_body_fi": "\n".join(x.text for x in fi_principles_intro[1:]),
        "raw_body_en": "\n".join(x.text for x in en_principles_intro),
        "raw_text_fi": "\n".join(x.text for x in fi_principles_intro),
        "raw_text_en": "\n".join(x.text for x in en_principles_intro),
        "glossary_link_count": principles_links, "alignment_status": "alignment_candidate",
    })

    # Principles are titled in the body but omitted as individual entries from the English TOC.
    for number in range(1, 12):
        fi_start = next((i for i, x in enumerate(fi_lines) if 12 <= x.page <= 18 and re.match(rf"^{number}\.\s+", x.text)), None)
        en_start = next((i for i, x in enumerate(en_lines) if 7 <= x.page <= 11 and re.match(rf"^{number}\.\s+", x.text)), None)
        if fi_start is None:
            continue
        fi_end = next((i for i in range(fi_start + 1, len(fi_lines)) if re.match(rf"^{number + 1}\.\s+", fi_lines[i].text)), intro_end if number == 11 else len(fi_lines))
        if number == 11:
            fi_end = next((i for i, x in enumerate(fi_lines[fi_start + 1:], fi_start + 1) if x.text.startswith("III. ")), fi_end)
        en_end = next((i for i in range((en_start or 0) + 1, len(en_lines)) if re.match(rf"^{number + 1}\.\s+", en_lines[i].text)), len(en_lines)) if number < 11 else next((i for i, x in enumerate(en_lines) if x.text.startswith("III. ")), len(en_lines))
        fi_unit, en_unit = fi_lines[fi_start:fi_end], en_lines[en_start:en_end] if en_start is not None else []
        fi_clause = next((i for i, x in enumerate(fi_unit[1:], 1) if re.match(rf"^{number}\.1\s+", x.text)), len(fi_unit))
        en_clause = next((i for i, x in enumerate(en_unit[1:], 1) if re.match(rf"^{number}\.1\s+", x.text)), len(en_unit))
        fi_title = " ".join(re.sub(rf"^{number}\.\s+", "", x.text) if i == 0 else x.text for i, x in enumerate(fi_unit[:fi_clause]))
        en_title = " ".join(re.sub(rf"^{number}\.\s+", "", x.text) if i == 0 else x.text for i, x in enumerate(en_unit[:en_clause]))
        sid = stable_id(str(number), "principle")
        exact_text_fi = publication_text(fi_unit[fi_clause:], sid, "fi", str(number))
        # The principle heading is substantive normative source text. It is
        # already the Finnish page title, but must appear in the English source
        # quotation so the two language sections are complete counterparts.
        exact_text_en = publication_text(en_unit, sid, "en", str(number))
        fi_text, links = link_glossary(exact_text_fi, glossary)
        sections.append({
            "id": sid, "kind": "principle", "section_number": str(number), "title_fi": f"{number}. {fi_title}",
            "title_en": f"{number}. {en_title}", "parent_id": None, "folder": "02-gcp-periaatteet",
            "finnish_pages": sorted(set(x.page for x in fi_unit)), "english_pages": sorted(set(x.page for x in en_unit)),
            "text_fi": fi_text, "text_en": exact_text_en, "exact_text_fi": exact_text_fi,
            "exact_text_en": exact_text_en, "raw_body_fi": "\n".join(x.text for x in fi_unit[fi_clause:]),
            "raw_body_en": "\n".join(x.text for x in en_unit),
            "raw_text_fi": "\n".join(x.text for x in fi_unit), "raw_text_en": "\n".join(x.text for x in en_unit),
            "glossary_link_count": links, "alignment_status": "alignment_candidate",
        })
    return sorted(sections, key=lambda x: (list(FOLDERS).index(x["folder"]), min(x["finnish_pages"] or [999]), x["id"]))


def write_section_pages(sections: list[dict[str, Any]]) -> None:
    for section in sections:
        number = section["section_number"]
        title_without_number = re.sub(r"^(?:[ABC]\.)?\d+(?:\.\d+)*\.?\s+", "", section["title_fi"])
        # Public paths must have identical casing on Windows and Linux. Annex
        # identifiers use capital letters in the source text, but filenames and
        # wikilinks are deliberately lowercase.
        filename = f"{number.replace('.', '-').lower()}-{ascii_slug(title_without_number)[:70]}.md"
        if section["kind"] == "intro":
            filename = f"{ascii_slug(number)}.md"
        elif section["kind"] == "principles_intro":
            filename = "johdanto.md"
        elif section["kind"] == "principle":
            filename = f"periaate-{int(number):02d}.md"
        permalink = f"/{section['folder']}/{filename[:-3]}/"
        frontmatter = {
            "title": section["title_fi"], "id": section["id"], "content_type": "guideline_section",
            "document_id": "ich-e6-r3-fi-v1", "section_number": str(number), "parent_id": section["parent_id"],
            "language": "fi", "lang": "fi", "translation_status": "unofficial", "authoritative_language": "en",
            "finnish_pages": section["finnish_pages"], "english_pages": section["english_pages"],
            "english_section_number": str(number) if section["text_en"] else None, "permalink": permalink,
            "aliases": [title_without_number], "tags": ["ich-e6-r3"], "roles": roles_for(str(number), section["text_fi"]),
            "review_status": "source_extracted", "publish": True, "schema_type": "TechArticle",
            "is_based_on": ["ich-e6-r3-fi-v1", "ich-e6-r3-en-step5"],
        }
        related = "\n\n## Liittyvät käsitteet\n\nKatso tekstissä linkitetyt sanastokäsitteet." if section["glossary_link_count"] else ""
        callout = quote_callout(section["text_en"], section["english_pages"], str(number))
        body = f"{yaml_frontmatter(frontmatter)}\n\n{section['text_fi']}{related}\n\n{callout}"
        path = CONTENT / section["folder"] / filename
        write_text(path, body)
        section["path"] = path.relative_to(ROOT).as_posix()
        section["permalink"] = permalink


def write_glossary_pages(glossary: list[dict[str, Any]], sections: list[dict[str, Any]]) -> None:
    for entry in glossary:
        occurrences = [s for s in sections if entry["preferred_term_fi"].casefold() in s["raw_text_fi"].casefold()]
        front = {
            "title": entry["preferred_term_fi"], "id": entry["id"], "content_type": "glossary_entry",
            "language": "fi", "lang": "fi", "schema_type": "DefinedTerm", "review_status": entry["review_status"],
            "publish": True, "permalink": f"/sanasto/{entry['slug']}/",
        }
        # Quartz resolves wikilinks from its content root. ``path`` is stored as
        # ``content/<folder>/<file>.md`` for provenance, so omit that filesystem
        # prefix when emitting a public link.
        links = "\n".join(f"- [[{s['path'][8:-3]}|{s['title_fi']}]]" for s in occurrences) or "- Ei tunnistettuja esiintymiä."
        en = entry["definition_en"] or "Englanninkielistä määritelmää ei voitu kohdistaa automaattisesti."
        body = (
            f"{yaml_frontmatter(front)}\n\n"
            f"**Englanniksi:** {entry['preferred_term_en'] or 'Kohdistus avoin'}\n\n"
            f"## Suomenkielinen määritelmä\n\n{entry['definition_fi']}\n\n"
            f"## Alkuperäinen englanninkielinen määritelmä\n\n<div lang=\"en\">\n\n{en}\n\n</div>\n\n"
            f"## Esiintyminen ohjeessa\n\n{links}\n\n"
            f"## Lähdeviitteet\n\n- Suomi: sivut {', '.join(map(str, entry['source_pages_fi']))}\n"
            f"- Englanti: {', '.join(map(str, entry['source_pages_en'])) or 'kohdistus avoin'}"
        )
        write_text(CONTENT / "sanasto" / f"{entry['slug']}.md", body)


def write_role_pages(obligations: list[dict[str, Any]]) -> None:
    labels = {
        "tutkija": "Tutkija", "toimeksiantaja": "Toimeksiantaja", "tutkimuspaikan-henkilosto": "Tutkimuspaikan henkilöstö",
        "monitoroija": "Monitoroija", "riippumaton-eettinen-toimikunta": "Riippumaton eettinen toimikunta",
        "tiedonhallinta-ja-tietokoneistetut-jarjestelmat": "Tiedonhallinta ja tietokoneistetut järjestelmät",
        "palveluntarjoaja": "Palveluntarjoaja",
    }
    for role in ROLE_IDS:
        items = [x for x in obligations if role in x["responsible_actor"] + x["supporting_actors"]]
        list_items = "\n".join(f"- **{x['obligation_id']}** — {x['normalized_action_fi']} ([lähdekohta {x['source_section']}](../vastuutaulukot/index.md#{ascii_slug(x['obligation_id'])}))" for x in items) or "- Automaattisesti kohdistettuja velvoitteita ei löytynyt."
        records = sorted({e for x in items for e in x["example_evidence"]})
        evidence = "\n".join(f"- {x} _(havainnollistava esimerkki, ei lähdevaatimus)_" for x in records) or "- Ei automaattisesti johdettuja esimerkkejä."
        front = {
            "title": labels[role], "id": f"ich-e6-r3-role-{role}", "content_type": "derived_role_view", "language": "fi", "lang": "fi",
            "schema_type": "CollectionPage", "content_status": "ai_generated", "classification": "derived",
            "review_status": "pending", "authoritative": False, "generated": True,
            "source_refs": sorted({x["source_section"] for x in items}), "publish": True,
            "permalink": f"/roolipohjaiset-nakymat/{role}/",
        }
        body = f"""{yaml_frontmatter(front)}

> [!warning] Johdettu näkymä
> Tämä sivu on muodostettu lähdetekstistä automaattisesti ja sivu tulee käsitellä kokeellisena.
> Sivua ei ole sisältötarkastettu.
> Tarkistustila on `pending`; sivu ei ole auktoritatiivinen tulkinta eikä sitä tule käyttää yksin sääntelyä, kliinistä toimintaa, oikeudellisia kysymyksiä tai vaatimustenmukaisuutta koskevien päätösten perusteena.

## Keskeiset vastuut

{list_items}

## Ennen tutkimuksen aloittamista

Katso lähdeviitteiset velvoitteet ja niiden ehdot vastuutaulukosta.

## Tutkimuksen aikana

Katso lähdeviitteiset velvoitteet ja niiden ehdot vastuutaulukosta.

## Tutkimukseen osallistumisen päättyessä

Katso lähdeviitteiset velvoitteet ja niiden ehdot vastuutaulukosta.

## Esimerkkitallenteet ja näyttö

{evidence}

## Lähdekohdat

{', '.join(sorted({x['source_section'] for x in items})) or 'Kohdistus avoin'}

## Liittyvät käsitteet

Katso ohjeen lähdesivujen sanastolinkit.
"""
        write_text(CONTENT / "roolipohjaiset-nakymat" / f"{role}.md", body)


def wikilinks_to_html(value: str) -> str:
    """Render Obsidian wikilinks inside raw HTML table cells as real links."""
    result: list[str] = []
    start = 0
    for match in re.finditer(r"\[\[([^\]|#]+(?:#[^\]|]+)?)(?:\|([^\]]+))?\]\]", value):
        result.append(html.escape(value[start:match.start()]))
        target = match.group(1)
        label = match.group(2) or target.rsplit("/", 1)[-1].split("#", 1)[0]
        result.append(f'<a href="../{html.escape(target, quote=True)}">{html.escape(label)}</a>')
        start = match.end()
    result.append(html.escape(value[start:]))
    return "".join(result)


def obligation_source_targets(sections: list[dict[str, Any]]) -> dict[str, str]:
    targets: dict[str, str] = {}
    for section in sections:
        base = f"../{section['path'][8:-3]}"
        targets.setdefault(str(section["section_number"]), base)
        for clause in extract_clauses(section["exact_text_fi"]):
            targets[clause] = f"{base}#{anchor(section['id'], clause)}"
    return targets


def write_register(obligations: list[dict[str, Any]], sections: list[dict[str, Any]]) -> None:
    source_targets = obligation_source_targets(sections)
    rows = []
    for item in obligations:
        source_section = str(item["source_section"])
        source_cell = html.escape(source_section)
        if target := source_targets.get(source_section):
            source_cell = f'<a href="{html.escape(target, quote=True)}">{source_cell}</a>'
        rows.append(
            f"<tr id=\"{ascii_slug(item['obligation_id'])}\"><td>{html.escape(item['obligation_id'])}</td>"
            f"<td>{html.escape(', '.join(item['responsible_actor']))}</td><td>{source_cell}</td>"
            f"<td>{wikilinks_to_html(item['normalized_action_fi'])}</td></tr>"
        )
    front = {
        "title": "Velvoite- ja näyttörekisteri", "id": "ich-e6-r3-obligation-register", "content_type": "obligation_register",
        "language": "fi", "lang": "fi", "schema_type": "Dataset", "classification": "derived",
        "review_status": "pending", "authoritative": False, "generated": True, "publish": True,
        "permalink": "/vastuutaulukot/",
    }
    body = f"""{yaml_frontmatter(front)}

> [!warning] Johdettu aineisto
> Normalisoidut toimet ja esimerkkitallenteet ovat automaattisesti johdettuja ja niiden tarkistustila on `pending`. Aineisto ei ole auktoritatiivinen tulkinta. Esimerkkitallenteet eivät ole lähdevaatimuksia.

<table><thead><tr><th>Tunniste</th><th>Vastuutaho</th><th>Lähdekohta</th><th>Toimi</th></tr></thead><tbody>
{''.join(rows)}
</tbody></table>
"""
    write_text(CONTENT / "vastuutaulukot" / "index.md", body)


def write_indexes(sections: list[dict[str, Any]], glossary: list[dict[str, Any]], terminology: list[dict[str, Any]]) -> None:
    for folder, title in FOLDERS.items():
        path = CONTENT / folder / "index.md"
        if path.exists() and folder == "vastuutaulukot":
            continue
        items = [s for s in sections if s["folder"] == folder]
        links = "\n".join(f"- [[{s['path'][8:-3]}|{s['title_fi']}]]" for s in items)
        if folder == "sanasto":
            links = "\n".join(f"- [[sanasto/{x['slug']}|{x['preferred_term_fi']}]]" for x in glossary)
        if folder == "termisanasto":
            links = "\n".join(f"- **{x['term_en']}** – {x['preferred_label_fi']}" for x in terminology)
        if folder == "roolipohjaiset-nakymat":
            links = "\n".join(f"- [[roolipohjaiset-nakymat/{role}|{role.replace('-', ' ').capitalize()}]]" for role in ROLE_IDS)
        front = {
            "title": title, "id": f"ich-e6-r3-index-{folder}", "content_type": "index", "language": "fi", "lang": "fi",
            "schema_type": "DefinedTermSet" if folder == "sanasto" else "CollectionPage", "publish": True,
            "permalink": f"/{folder}/",
        }
        write_text(path, f"{yaml_frontmatter(front)}\n\n{links or '- Sisältöä ei ole.'}")


def write_reports(documents: list[dict[str, Any]], sections: list[dict[str, Any]], glossary: list[dict[str, Any]], obligations: list[dict[str, Any]]) -> None:
    aligned = sum(x["alignment_status"] == "automatically_verified" for x in sections)
    unresolved = [x for x in sections if x["alignment_status"] != "automatically_verified"]
    reports = {
        "source-manifest-report.md": "# Lähdemanifestin raportti\n\n" + "\n".join(f"- `{x['filename']}`: SHA-256 täsmää (`{x['sha256']}`)." for x in documents),
        "section-coverage-report.md": f"# Osioiden kattavuus\n\n- Rakenteellisia sivuja: {len(sections)}\n- Suomenkieliset painetut sivut 10–94: käsitelty.\n- Sanasto 95–105: käsitelty ({len(glossary)} merkintää).\n- EN–FI-termisanasto 106–111: käsitelty.",
        "alignment-report.md": f"# Kohdistusraportti\n\n- Automaattisesti varmennettu: {aligned}\n- Avoin tai suomalainen lisärakenne: {len(unresolved)}\n\n" + "\n".join(f"- {x['id']}: {x['alignment_status']}" for x in unresolved),
        "normalization-report.md": "# Normalisointiraportti\n\n- Teksti normalisoitiin Unicode NFC -muotoon.\n- Toistuvat sivuotsikot ja -alatunnisteet poistettiin.\n- Rivien väliset välilyönnit yhdistettiin.\n- Rivinvaihtotavut säilytettiin, koska niiden poistamista ei voitu varmistaa yksiselitteisesti.\n- Raaka, otsikoista puhdistettu tekstiversio säilytetään `sections.json`-aineistossa.",
        "glossary-link-report.md": f"# Sanastolinkkien raportti\n\n- Linkkejä lisättiin {sum(x['glossary_link_count'] for x in sections)}.\n- Linkitys käyttää pisintä täsmällistä lähdetekstin muotoa eikä koske englanninkielisiä lainauksia.",
        "unresolved-term-report.md": "# Ratkaisemattomien termien raportti\n\n- Suomen taivutusmuotoja ei tuotettu arvaamalla. `term-variants.json` sisältää vain lähdeaineistossa varmennetut täsmälliset muodot.\n- Asiantuntijan tulee täydentää taivutusmuodot ennen kuin linkkikattavuus voidaan merkitä täydelliseksi.",
        "obligation-review-report.md": f"# Velvoitteiden tarkistusraportti\n\n- Poimittuja ehdokkaita: {len(obligations)}\n- Matalamman varmuuden tai yhdistelmäkohtia: {sum(x['confidence'] < .9 for x in obligations)}\n- Kaikkien johdettujen kohtien tarkistustila on `pending`.",
        "role-view-review-report.md": "# Roolinäkymien tarkistusraportti\n\n- Seitsemän hallittua roolia on luotu.\n- Kaikki roolinäkymät on merkitty AI-tuotetuiksi ja niiden tarkistustila on `pending`.\n- Kuvitteellisia ajantasaisia tehtävä- tai tilatietoja ei ole lisätty.",
        "source-exactness-report.md": "# Lähdetekstin täsmällisyysraportti\n\nRaportti päivitetään komennolla `python scripts/validate_kb.py`.",
        "broken-link-report.md": "# Rikkinäisten linkkien raportti\n\nRaportti päivitetään komennolla `python scripts/validate_kb.py`.",
        "build-report.md": "# Koontiraportti\n\nRaportti päivitetään validoinnin ja Quartz-koonnin yhteydessä.",
        "machine-readability-report.md": "# Koneluettavuuden validointiraportti\n\nRaportti päivitetään komennolla `python scripts/validate_machine_resources.py`.",
    }
    for name, body in reports.items():
        write_text(REPORTS / name, body)


def main() -> None:
    documents = verify_manifest()
    manual_index = CONTENT / "index.md"
    if not manual_index.exists():
        raise SystemExit("Manuaalisesti ylläpidettävä content/index.md puuttuu.")
    manual_root_entries = set(CONTENT.glob("*.md")) | {
        child
        for child in CONTENT.iterdir()
        if child.name.startswith(".") or (child.is_dir() and (child / ".manual").exists())
    }
    for directory in [DATA, REPORTS]:
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)
    CONTENT.mkdir(parents=True, exist_ok=True)
    for child in CONTENT.iterdir():
        if child in manual_root_entries:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    with pdfplumber.open(FI_PDF) as fi_pdf, pdfplumber.open(EN_PDF) as en_pdf:
        glossary = glossary_terms(fi_pdf, en_pdf)
        terminology = extract_terminology(fi_pdf)
        records = semantic_records(fi_pdf, en_pdf)
        sections = build_sections(fi_pdf, en_pdf, glossary)
    write_section_pages(sections)
    write_glossary_pages(glossary, sections)
    obligations = build_obligations(sections)
    write_role_pages(obligations)
    write_register(obligations, sections)
    write_indexes(sections, glossary, terminology)

    dump_json(DATA / "documents.json", documents)
    dump_json(DATA / "sections.json", sections)
    dump_json(DATA / "alignments.json", [{"id": f"alignment-{x['id']}", "finnish_id": x["id"], "english_section": x["section_number"] if x["text_en"] else None, "method": "section_identifier", "confidence": 1.0 if x["text_en"] else 0.0, "classification": "derived", "alignment_status": x["alignment_status"], "review_status": "pending"} for x in sections])
    dump_json(DATA / "glossary.json", glossary)
    dump_json(DATA / "terminology.json", terminology)
    dump_json(DATA / "term-variants.json", {x["slug"]: {"preferred": x["preferred_term_fi"], "variants": [x["preferred_term_fi"]], "status": "source_attested_exact_form"} for x in glossary})
    dump_json(DATA / "roles.json", {"roles": ROLE_IDS})
    dump_json(DATA / "obligations.json", obligations)
    dump_json(DATA / "essential-records.json", records)
    dump_json(DATA / "extraction-report.json", {"normalizations": ["unicode_nfc", "repeated_header_footer_removal", "layout_line_joining"], "hyphenation": "preserved_when_ambiguous", "section_count": len(sections), "glossary_count": len(glossary), "terminology_count": len(terminology)})
    write_reports(documents, sections, glossary, obligations)
    print(f"Luotu: {len(sections)} osiota, {len(glossary)} sanastomerkintää, {len(terminology)} termikohdistusta, {len(obligations)} velvoite-ehdokasta.")


if __name__ == "__main__":
    main()

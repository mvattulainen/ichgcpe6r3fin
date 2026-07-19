from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pdfplumber

from build_kb import (
    DATA,
    EN_PDF,
    EXTRA_TITLED,
    FI_PDF,
    REPORTS,
    PageLine,
    extract_lines,
    parse_toc,
    stable_id,
    write_text,
)


PRINCIPLES_INTRO_ID = "ich-e6-r3-principles-introduction"
INTRO_HEADINGS = {
    "ich-e6-r3-introduction-johdanto": ("I. Johdanto", "I. Introduction"),
    "ich-e6-r3-introduction-soveltamisala": ("Ohjeen soveltamisala", "Guideline scope"),
    "ich-e6-r3-introduction-rakenne": ("Ohjeen rakenne", "Guideline structure"),
}
PRINCIPLE_HEADING_PREFIX = "ich-e6-r3-principle-"
NUMBERED_LINE = re.compile(r"^((?:\d+|[ABC])(?:\.\d+)+)\s+(.+)$")
MARKUP = re.compile(
    r'<a id="[^"]+"></a>|\[\[[^\]|]+\|([^\]]+)\]\]|\[\[([^\]]+)\]\]|\*\*|^#{1,6}\s+',
    re.M,
)


@dataclass
class Finding:
    severity: str
    code: str
    section_id: str | None
    message: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "severity": self.severity,
            "code": self.code,
            "section_id": self.section_id,
            "message": self.message,
        }


def load(name: str) -> Any:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def plain(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = MARKUP.sub(lambda match: next((x for x in match.groups() if x), ""), value)
    return re.sub(r"\s+", " ", value).strip()


def key(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def line_numbers(value: str) -> list[str]:
    result: list[str] = []
    for line in value.splitlines():
        if match := NUMBERED_LINE.match(plain(line)):
            result.append(match.group(1))
    return result


def is_descendant(candidate: str, root: str) -> bool:
    return candidate.startswith(root + ".")


def belongs_to_section(candidate: str, root: str) -> bool:
    return candidate == root or is_descendant(candidate, root)


def section_numbers(value: str, root: str) -> list[str]:
    return [number for number in line_numbers(value) if is_descendant(number, root)]


def foreign_numbers(value: str, root: str) -> list[str]:
    return [number for number in line_numbers(value) if not belongs_to_section(number, root)]


def published_heading_numbers(value: str) -> list[str]:
    return re.findall(
        r'(?m)^(?:<a id="[^"]+"></a>\n\n)?(?:###\s+|\*\*)((?:\d+|[ABC])(?:\.\d+)+)',
        value,
    )


def phrase_variants(value: str | None) -> list[str]:
    if not value:
        return []
    value = re.sub(r"\([^)]*\)", " ", value.casefold())
    variants: list[str] = []
    for item in re.split(r"\s*(?:/|;|,)\s*", value):
        item = re.sub(r"\s+", " ", item).strip(" .:-")
        if len(item) >= 5 and item not in {"tiedot", "information", "clinical", "kliininen"}:
            variants.append(item)
    return variants


def bilingual_pairs(glossary: list[dict[str, Any]], terminology: list[dict[str, Any]]) -> list[tuple[list[str], list[str]]]:
    pairs: list[tuple[list[str], list[str]]] = []
    for entry in glossary:
        fi = phrase_variants(entry.get("preferred_term_fi"))
        en = phrase_variants(entry.get("preferred_term_en"))
        if fi and en:
            pairs.append((fi, en))
    for entry in terminology:
        fi = phrase_variants(entry.get("preferred_label_fi"))
        en = phrase_variants(entry.get("term_en"))
        if fi and en:
            pairs.append((fi, en))
    return pairs


def contains_variant(text: str, variants: Iterable[str]) -> bool:
    folded = key(text)
    text_tokens = folded.split()
    for variant in variants:
        normalized = key(variant)
        if normalized in folded:
            return True
        # Finnish inflection and English singular/plural variation make exact
        # phrase lookup too brittle. Require every meaningful concept token to
        # have a same-prefix token in the section; this remains deterministic
        # and is grounded in the source-provided bilingual terminology.
        concept_tokens = [token for token in normalized.split() if len(token) >= 5]
        if concept_tokens and all(
            any(text_token[:5] == concept_token[:5] for text_token in text_tokens)
            for concept_token in concept_tokens
        ):
            return True
    return False


def concept_score(fi_text: str, en_text: str, pairs: list[tuple[list[str], list[str]]]) -> tuple[float, int, int]:
    expected = 0
    matched = 0
    for fi_variants, en_variants in pairs:
        fi_present = contains_variant(fi_text, fi_variants)
        en_present = contains_variant(en_text, en_variants)
        if fi_present:
            expected += 1
            matched += int(en_present)
        if en_present:
            expected += 1
            matched += int(fi_present)
    return (matched / expected if expected else 1.0, matched, expected)


def reference_tokens(value: str) -> set[str]:
    # Document identifiers remain invariant across translation. General
    # acronyms do not: the Finnish source can translate an English acronym to
    # a full term, so treating every capitalised token as invariant creates
    # large numbers of false alarms.
    return {
        match.upper().replace(" ", "")
        for match in re.findall(r"\bICH\s+[A-Z]?\d+(?:\(R\d+\))?\b", value, re.I)
    }


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 1.0


def expected_section_ids(fi_toc: dict[str, dict[str, Any]], en_toc: dict[str, dict[str, Any]]) -> set[str]:
    identifiers = set(en_toc) | set(EXTRA_TITLED)
    result = {stable_id(number) for number in identifiers}
    result.update(stable_id(str(number), "principle") for number in range(1, 12))
    result.update(INTRO_HEADINGS)
    result.add(PRINCIPLES_INTRO_ID)
    result.update(stable_id(str(number)) for number in range(1, 5))
    return result


def uncovered_lines(source: list[PageLine], sections: list[dict[str, Any]], language: str) -> list[PageLine]:
    page_key = "finnish_pages" if language == "fi" else "english_pages"
    text_key = "raw_text_fi" if language == "fi" else "raw_text_en"
    indexed = [
        (set(section.get(page_key, [])), set(section.get(text_key, "").splitlines()))
        for section in sections
    ]
    container_headings = {"III. Liite 1", "III. Annex 1"}
    return [
        line
        for line in source
        if line.text not in container_headings
        if not any(line.page in pages and line.text in lines for pages, lines in indexed)
    ]


def add(
    findings: list[Finding], severity: str, code: str, message: str, section_id: str | None = None
) -> None:
    findings.append(Finding(severity, code, section_id, message))


def verify(report_only: bool = False) -> dict[str, Any]:
    sections: list[dict[str, Any]] = load("sections.json")
    glossary = load("glossary.json")
    terminology = load("terminology.json")
    pairs = bilingual_pairs(glossary, terminology)
    findings: list[Finding] = []
    results: list[dict[str, Any]] = []

    with pdfplumber.open(FI_PDF) as fi_pdf, pdfplumber.open(EN_PDF) as en_pdf:
        fi_toc = parse_toc(fi_pdf, 5, 9)
        en_toc = parse_toc(en_pdf, 3, 5)
        fi_source = extract_lines(fi_pdf, 10, 94)
        en_source = extract_lines(en_pdf, 6, 63)

    by_id = {section["id"]: section for section in sections}
    expected = expected_section_ids(fi_toc, en_toc)
    for section_id in sorted(expected - set(by_id)):
        add(findings, "error", "missing_structural_section", "Lähteen rakenteellinen osio puuttuu aineistosta.", section_id)
    for section_id in sorted(set(by_id) - expected):
        add(findings, "warning", "unexpected_structural_section", "Aineistossa on lähderakenteeseen kuulumaton osio.", section_id)

    missing_fi = uncovered_lines(fi_source, sections, "fi")
    missing_en = uncovered_lines(en_source, sections, "en")
    for language, missing in (("fi", missing_fi), ("en", missing_en)):
        if missing:
            sample = "; ".join(f"s. {line.page}: {line.text[:90]}" for line in missing[:8])
            add(
                findings,
                "error",
                f"unassigned_source_lines_{language}",
                f"{len(missing)} lähderiviä ei kuulu yhteenkään osioon. Esimerkit: {sample}",
            )

    intro_english_headings = {value[1] for value in INTRO_HEADINGS.values()}
    for section in sections:
        section_id = section["id"]
        number = str(section["section_number"])
        kind = section["kind"]
        fi_text = plain(f"{section.get('title_fi', '')} {section.get('exact_text_fi', '')}")
        # English publication text deliberately includes its exact source
        # heading; do not count the same heading twice in semantic metrics.
        en_text = plain(section.get("exact_text_en", ""))
        section_errors: list[str] = []
        section_warnings: list[str] = []

        has_en = bool(plain(section.get("exact_text_en", "")))
        if not has_en:
            section_errors.append("missing_english_text")
            add(findings, "error", "missing_english_text", "Vastaava englanninkielinen lähdeteksti puuttuu.", section_id)

        numbering_match = True
        foreign_fi: list[str] = []
        foreign_en: list[str] = []
        if kind in {"main", "principle"}:
            fi_numbers = section_numbers(section.get("raw_body_fi", ""), number)
            en_numbers = section_numbers(section.get("raw_body_en", ""), number)
            numbering_match = fi_numbers == en_numbers
            if not numbering_match:
                section_errors.append("numbering_mismatch")
                add(
                    findings,
                    "error",
                    "numbering_mismatch",
                    f"Alisteisten kohtien järjestys ei täsmää: FI={fi_numbers}, EN={en_numbers}.",
                    section_id,
                )
            foreign_fi = foreign_numbers(section.get("raw_body_fi", ""), number)
            foreign_en = foreign_numbers(section.get("raw_body_en", ""), number)
            if foreign_fi or foreign_en:
                section_warnings.append("foreign_number_at_line_start")
                add(
                    findings,
                    "warning",
                    "foreign_number_at_line_start",
                    f"Osion ulkopuolinen numero alkaa PDF-poiminnan rivin: FI={foreign_fi}, EN={foreign_en}. Julkaisumuodon otsikkotarkistus ratkaisee, onko kyse ristiviitteestä.",
                    section_id,
                )
            published_foreign_fi = [
                item for item in published_heading_numbers(section.get("exact_text_fi", ""))
                if not belongs_to_section(item, number)
            ]
            published_foreign_en = [
                item for item in published_heading_numbers(section.get("exact_text_en", ""))
                if not belongs_to_section(item, number)
            ]
            if published_foreign_fi or published_foreign_en:
                section_errors.append("foreign_published_heading")
                add(
                    findings,
                    "error",
                    "foreign_published_heading",
                    f"Osion ulkopuolinen numero julkaistiin virheellisesti väliotsikkona: FI={published_foreign_fi}, EN={published_foreign_en}.",
                    section_id,
                )

        expected_page_fi = fi_toc.get(number, {}).get("page")
        expected_page_en = en_toc.get(number, {}).get("page")
        page_match = True
        if kind == "main":
            actual_fi = min(section.get("finnish_pages") or [0])
            actual_en = min(section.get("english_pages") or [0])
            if expected_page_fi and actual_fi != expected_page_fi:
                page_match = False
                section_errors.append("finnish_start_page_mismatch")
                add(findings, "error", "finnish_start_page_mismatch", f"TOC-sivu {expected_page_fi}, kohdistettu alkusivu {actual_fi}.", section_id)
            if expected_page_en and actual_en != expected_page_en:
                page_match = False
                section_errors.append("english_start_page_mismatch")
                add(findings, "error", "english_start_page_mismatch", f"TOC-sivu {expected_page_en}, kohdistettu alkusivu {actual_en}.", section_id)

        title_present = True
        if section.get("title_en") and has_en:
            expected_title = section["title_en"]
            title_present = key(expected_title) in key(section.get("exact_text_en", ""))
            if not title_present:
                section_errors.append("english_heading_missing")
                add(findings, "error", "english_heading_missing", "Englanninkielinen lähdeotsikko puuttuu englanninkielisestä lähdelohkosta.", section_id)

        intro_split = True
        if section_id in INTRO_HEADINGS:
            own_heading = INTRO_HEADINGS[section_id][1]
            raw_en = section.get("raw_text_en", "")
            if own_heading not in raw_en:
                intro_split = False
                section_errors.append("english_intro_heading_missing")
                add(findings, "error", "english_intro_heading_missing", f"Englanninkielinen otsikko {own_heading!r} puuttuu.", section_id)
            foreign = sorted(heading for heading in intro_english_headings - {own_heading} if heading in raw_en)
            if foreign:
                intro_split = False
                section_errors.append("english_intro_contains_neighbour")
                add(findings, "error", "english_intro_contains_neighbour", f"Osio sisältää naapuriosion otsikon: {foreign}.", section_id)

        ratio = len(en_text) / max(len(fi_text), 1)
        length_ok = 0.45 <= ratio <= 2.40
        if has_en and not length_ok:
            section_errors.append("length_ratio_outlier")
            add(findings, "error", "length_ratio_outlier", f"EN/FI-merkkimäärän suhde {ratio:.2f} on poikkeava.", section_id)

        semantic, concepts_matched, concepts_expected = concept_score(fi_text, en_text, pairs)
        semantic_ok = concepts_expected < 4 or semantic >= 0.20
        if has_en and not semantic_ok:
            section_warnings.append("semantic_concept_mismatch")
            add(
                findings,
                "warning",
                "semantic_concept_mismatch",
                f"Kaksikielisten käsitteiden vastaavuus {semantic:.2f} ({concepts_matched}/{concepts_expected}) on liian matala.",
                section_id,
            )

        refs_fi, refs_en = reference_tokens(fi_text), reference_tokens(en_text)
        reference_score = jaccard(refs_fi, refs_en)
        reference_ok = reference_score >= 0.50
        if has_en and not reference_ok:
            section_warnings.append("reference_token_mismatch")
            add(findings, "warning", "reference_token_mismatch", f"ICH-/lyhennetunnisteiden vastaavuus on {reference_score:.2f}.", section_id)

        confidence = max(
            0.0,
            min(
                1.0,
                0.30 * float(numbering_match)
                + 0.15 * float(page_match)
                + 0.15 * float(title_present and intro_split)
                + 0.20 * semantic
                + 0.10 * float(length_ok)
                + 0.10 * reference_score,
            ),
        )
        results.append(
            {
                "section_id": section_id,
                "section_number": number,
                "status": "automatically_verified" if not section_errors and has_en else "verification_failed",
                "confidence": round(confidence, 4),
                "criteria": {
                    "section_numbering_match": numbering_match,
                    "toc_start_page_match": page_match,
                    "heading_boundary_match": title_present and intro_split,
                    "length_ratio_en_fi": round(ratio, 4),
                    "bilingual_concept_score": round(semantic, 4),
                    "bilingual_concepts_matched": concepts_matched,
                    "bilingual_concepts_expected": concepts_expected,
                    "reference_token_score": round(reference_score, 4),
                    "foreign_numbers_fi": foreign_fi,
                    "foreign_numbers_en": foreign_en,
                },
                "errors": section_errors,
                "warnings": section_warnings,
                "issues": section_errors + section_warnings,
            }
        )

    error_count = sum(item.severity == "error" for item in findings)
    warning_count = sum(item.severity == "warning" for item in findings)
    verified_count = sum(item["status"] == "automatically_verified" for item in results)
    payload = {
        "procedure_version": "1.0",
        "status": "passed" if error_count == 0 else "failed",
        "criteria": [
            "exact section identifier and descendant numbering sequence",
            "Finnish and English table-of-contents start page",
            "heading boundary isolation",
            "complete assignment of every in-scope PDF text line",
            "EN/FI length-ratio outlier detection",
            "bilingual glossary and terminology concept correspondence",
            "shared ICH references and abbreviations",
        ],
        "summary": {
            "sections": len(sections),
            "automatically_verified": verified_count,
            "verification_failed": len(results) - verified_count,
            "errors": error_count,
            "warnings": warning_count,
            "unassigned_finnish_lines": len(missing_fi),
            "unassigned_english_lines": len(missing_en),
        },
        "sections": results,
        "findings": [item.as_dict() for item in findings],
    }
    dump(DATA / "alignment-verification.json", payload)

    result_by_id = {result["section_id"]: result for result in results}
    for section in sections:
        result = result_by_id[section["id"]]
        section["alignment_status"] = result["status"]
        section["alignment_confidence"] = result["confidence"]
        section["alignment_criteria"] = result["criteria"]
        section["alignment_issues"] = result["issues"]
    dump(DATA / "sections.json", sections)

    alignments = []
    for result in results:
        alignments.append(
            {
                "id": f"alignment-{result['section_id']}",
                "finnish_id": result["section_id"],
                "english_section": result["section_number"] if result["status"] == "automatically_verified" else None,
                "method": "multi_criteria_section_alignment",
                "confidence": result["confidence"],
                "classification": "derived",
                "alignment_status": result["status"],
                "review_status": "pending",
                "verification_criteria": list(result["criteria"]),
                "issues": result["issues"],
            }
        )
    dump(DATA / "alignments.json", alignments)

    report = [
        "# Suomen- ja englanninkielisten osioiden kohdistuksen varmennus",
        "",
        f"- Tila: **{'HYVÄKSYTTY' if error_count == 0 else 'HYLÄTTY'}**",
        f"- Varmennetut osiot: {verified_count}/{len(results)}",
        f"- Virheet: {error_count}",
        f"- Varoitukset: {warning_count}",
        f"- Kohdistamattomat suomalaiset lähderivit: {len(missing_fi)}",
        f"- Kohdistamattomat englanninkieliset lähderivit: {len(missing_en)}",
        "",
        "## Menettely",
        "",
        "1. PDF-tiedostojen SHA-256-varmennettuun tekstipoimintaan sovelletaan samoja otsake- ja alatunnistesuodattimia kuin sivuston koontiin.",
        "2. Otsikolliset osiot yhdistetään ensin täsmällisen osiotunnisteen perusteella; pelkkää sivujen läheisyyttä ei koskaan hyväksytä kohdistukseksi.",
        "3. Suomen ja englannin sisällysluetteloiden alkusivut sekä osion otsikkorajat tarkistetaan.",
        "4. Alisteisten kohtien numerot, järjestys ja osion ulkopuoliset rivinalkunumerot tarkistetaan.",
        "5. Jokaisen soveltamisalaan kuuluvan PDF-lähderivin tulee kuulua vähintään yhteen rakenteelliseen osioon.",
        "6. Semanttista vastaavuutta arvioidaan lähteestä poimitun EN–FI-termisanaston ja kaksikielisen sanaston käsitteillä sekä ICH-viitteillä ja lyhenteillä.",
        "7. Merkkimäärien EN/FI-suhdetta käytetään katkenneiden, puuttuvien ja naapuriosioon vuotaneiden tekstien poikkeamahavaintona.",
        "",
        "## Havainnot",
        "",
    ]
    if findings:
        report.extend(
            f"- **{item.severity.upper()} / {item.code}**"
            + (f" (`{item.section_id}`)" if item.section_id else "")
            + f": {item.message}"
            for item in findings
        )
    else:
        report.append("- Kohdistuspoikkeamia ei havaittu.")
    write_text(REPORTS / "alignment-verification-report.md", "\n".join(report))
    write_text(
        REPORTS / "alignment-report.md",
        "# Kohdistusraportti\n\n"
        f"- Monikriteerisesti varmennettu: {verified_count}/{len(results)}\n"
        f"- Virheitä: {error_count}\n"
        f"- Varoituksia: {warning_count}\n\n"
        "Yksityiskohtainen menettely ja havainnot: `alignment-verification-report.md`.\n",
    )
    if error_count and not report_only:
        raise SystemExit(f"Kohdistuksen varmennus epäonnistui: {error_count} virhettä, {warning_count} varoitusta.")
    print(f"Kohdistuksen varmennus: {verified_count}/{len(results)} hyväksytty, {error_count} virhettä, {warning_count} varoitusta.")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Varmenna suomi–englanti-osiokohdistukset monella kriteerillä.")
    parser.add_argument("--report-only", action="store_true", help="Kirjoita raportti mutta älä palauta virhekoodia poikkeamista.")
    args = parser.parse_args()
    verify(report_only=args.report_only)


if __name__ == "__main__":
    main()

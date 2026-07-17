from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from build_kb import CONTENT, DATA, REPORTS, ROOT, verify_manifest, write_text


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    block = text.split("---\n", 2)[1]
    result: dict[str, str] = {}
    for line in block.splitlines():
        if re.match(r"^[a-z_][a-z0-9_]*:", line):
            key, value = line.split(":", 1)
            result[key] = value.strip().strip('"')
    return result


def main() -> None:
    errors: list[str] = []
    warnings: list[str] = []
    verify_manifest()
    sections = load("sections.json")
    glossary = load("glossary.json")
    terminology = load("terminology.json")
    obligations = load("obligations.json")
    records = load("essential-records.json")

    ids = [x["id"] for x in sections]
    if len(ids) != len(set(ids)):
        errors.append("Rakenteellisia tunnisteita esiintyy useammin kuin kerran.")
    covered = {page for section in sections for page in section["finnish_pages"]}
    missing_pages = sorted(set(range(10, 95)) - covered)
    if missing_pages:
        errors.append(f"Pääohjeen sivuja puuttuu: {missing_pages}")
    glossary_pages = {page for entry in glossary for page in entry["source_pages_fi"]}
    if set(range(95, 106)) - glossary_pages:
        errors.append("Sanaston kaikki sivut 95–105 eivät näy lähdeviitteissä.")
    term_pages = {entry["source_page_fi"] for entry in terminology}
    if set(range(106, 112)) - term_pages:
        errors.append("Termisanaston kaikki sivut 106–111 eivät näy lähdeviitteissä.")

    required_data = {
        "documents.json", "sections.json", "alignments.json", "glossary.json", "terminology.json",
        "term-variants.json", "roles.json", "obligations.json", "essential-records.json", "extraction-report.json",
    }
    missing_data = sorted(name for name in required_data if not (DATA / name).exists())
    if missing_data:
        errors.append(f"Kanonisia aineistoja puuttuu: {missing_data}")

    markdown_files = list(CONTENT.rglob("*.md"))
    exact_targets = {
        path.relative_to(CONTENT).as_posix()[:-3]
        for path in markdown_files
    }
    all_text = ""
    permalink_values: list[str] = []
    for path in markdown_files:
        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"Tiedosto ei ole UTF-8: {path.relative_to(ROOT)}")
            continue
        all_text += "\n" + raw
        if raw != unicodedata.normalize("NFC", raw):
            errors.append(f"Teksti ei ole NFC-muodossa: {path.relative_to(ROOT)}")
        if "file:///" in raw:
            errors.append(f"Paikallinen file-URL: {path.relative_to(ROOT)}")
        if re.search(r"Ohje hyvän kliinisen tutkimustavan noudattamisesta.*Sivu \d+/111", raw):
            errors.append(f"Sivualatunniste lähdetekstissä: {path.relative_to(ROOT)}")
        fm = frontmatter(raw)
        if fm.get("publish") == "true":
            for key in ("title", "id", "language", "schema_type", "permalink"):
                if not fm.get(key):
                    errors.append(f"Julkiselta sivulta puuttuu {key}: {path.relative_to(ROOT)}")
            permalink_values.append(fm.get("permalink", ""))
        marker = "> [!quote]- Alkuperäinen englanninkielinen lähdeteksti"
        if marker in raw and "[[sanasto/" in raw.split(marker, 1)[1]:
            errors.append(f"Englanninkieliseen lainaukseen lisättiin sanastolinkki: {path.relative_to(ROOT)}")

        for target in re.findall(r"\[\[([^\]|#]+)", raw):
            target = target.replace("\\", "/")
            if "/" in target and target not in exact_targets and f"{target}/index" not in exact_targets:
                errors.append(
                    f"Rikkinäinen wikilinkki tai väärä kirjainkoko {target!r}: {path.relative_to(ROOT)}"
                )
                continue
            target_path = CONTENT / (target + ".md")
            target_index = CONTENT / target / "index.md"
            if not target_path.exists() and not target_index.exists():
                # Obsidian also resolves a basename uniquely in the same vault.
                if len(list(CONTENT.rglob(Path(target).name + ".md"))) != 1:
                    errors.append(f"Rikkinäinen wikilinkki {target!r}: {path.relative_to(ROOT)}")

    if len(permalink_values) != len(set(permalink_values)):
        errors.append("Pysyväisosoitteissa on päällekkäisyyksiä.")
    for token in ["tietoon perustuva suostumus", "tietokoneistetut järjestelmät", "EN–FI-termisanasto"]:
        if token not in all_text:
            errors.append(f"Unicode-testimerkkijono puuttuu: {token}")
    if any(x["modality_fi"].casefold() not in x["source_text_fi"].casefold() for x in obligations):
        errors.append("Velvoitteen suomalainen modaliteetti ei esiinny tarkassa lähdetekstissä.")
    if any(x["evidence_status"] != "illustrative_not_source_requirement" for x in obligations):
        errors.append("Esimerkkitallenne on merkitty lähdevaatimukseksi.")
    if any(x["review_status"] == "expert_reviewed" for x in obligations):
        errors.append("Velvoite on merkitty asiantuntijan tarkistamaksi ilman tarkistustapahtumaa.")
    if not records or any(not x["name_fi"] or not x["name_en"] for x in records):
        errors.append("Oleellisten tallenteiden kaksikielinen rakenneaineisto on vajaa.")

    expected_reports = {
        "source-manifest-report.md", "section-coverage-report.md", "alignment-report.md", "normalization-report.md",
        "glossary-link-report.md", "unresolved-term-report.md", "obligation-review-report.md",
        "role-view-review-report.md", "broken-link-report.md", "build-report.md",
    }
    missing_reports = sorted(name for name in expected_reports if not (REPORTS / name).exists())
    if missing_reports:
        errors.append(f"Raportteja puuttuu: {missing_reports}")

    broken_body = "# Rikkinäisten linkkien raportti\n\n" + (
        "- Sisäisiä rikkinäisiä linkkejä ei havaittu." if not any("Rikkinäinen wikilinkki" in x for x in errors)
        else "\n".join(f"- {x}" for x in errors if "Rikkinäinen wikilinkki" in x)
    )
    write_text(REPORTS / "broken-link-report.md", broken_body)
    status = "HYVÄKSYTTY" if not errors else "HYLÄTTY"
    build_body = (
        f"# Koontiraportti\n\n- Tietopohjan validointi: **{status}**\n- Markdown-sivuja: {len(markdown_files)}\n"
        f"- Rakenteellisia lähdeosioita: {len(sections)}\n- Sanastomerkintöjä: {len(glossary)}\n"
        f"- Termikohdistuksia: {len(terminology)}\n- Velvoite-ehdokkaita: {len(obligations)}\n"
        f"- Oleellisia tallenteita: {len(records)}\n\n"
        + ("## Virheet\n\n" + "\n".join(f"- {x}" for x in errors) if errors else "Kaikki tietopohjan paikalliset hyväksymistarkistukset läpäistiin.")
    )
    write_text(REPORTS / "build-report.md", build_body)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Validointi hyväksytty: {len(markdown_files)} Markdown-sivua, {len(sections)} lähdeosiota.")


if __name__ == "__main__":
    main()

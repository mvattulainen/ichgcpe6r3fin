from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

from build_kb import (
    CONTENT, DATA, DERIVED_NOTICE, REPORTS, ROLE_IDS, ROLE_WORKFLOW, ROOT,
    TERM_COMPARISON_SPECS, verify_manifest, write_text,
)


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


def normalized_raw_source(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = re.sub(r"(?m)^\s*•\s*", "", value)
    return re.sub(r"\s+", " ", value).strip()


def normalized_published_source(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = re.sub(r'<a id="[^"]+"></a>', "", value)
    value = re.sub(
        r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]",
        lambda match: match.group(2) or match.group(1).rsplit("/", 1)[-1],
        value,
    )
    value = re.sub(r"(?m)^> ?", "", value)
    value = re.sub(r"(?m)^#{1,6}\s+", "", value)
    value = re.sub(r"(?m)^\s*[-•]\s+", "", value)
    value = re.sub(r"\s+\^[a-zA-Z0-9._-]+(?=\s|$)", "", value)
    value = value.replace("**", "")
    return re.sub(r"\s+", " ", value).strip()


def markdown_body(value: str) -> str:
    return value.split("---\n", 2)[2].lstrip() if value.startswith("---\n") else value


def finnish_source_body(value: str) -> str:
    body = markdown_body(value)
    # A titled container section can have no Finnish body before its English
    # source callout. In that case the callout starts at the first body byte.
    if body.startswith("> [!quote]- "):
        return ""
    for marker in (
        "\n## Liittyvät käsitteet",
        "\n> [!quote]- Alkuperäinen englanninkielinen lähdeteksti",
        "\n> [!warning] Englanninkielistä vastinetta",
        "> [!warning] Englanninkielistä vastinetta",
    ):
        body = body.split(marker, 1)[0]
    return body.strip()


def english_callout_body(value: str) -> str:
    match = re.search(r'> <div lang="en">\n>\n(.*?)\n>\n> </div>', value, re.S)
    if not match:
        return ""
    return "\n".join(re.sub(r"^> ?", "", line) for line in match.group(1).splitlines())


def main() -> None:
    errors: list[str] = []
    warnings: list[str] = []
    verify_manifest()
    sections = load("sections.json")
    glossary = load("glossary.json")
    terminology = load("terminology.json")
    obligations = load("obligations.json")
    records = load("essential-records.json")
    alignments = load("alignments.json")
    alignment_verification = load("alignment-verification.json")
    term_comparisons = load("term-comparisons.json")

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
        "documents.json", "sections.json", "alignments.json", "alignment-verification.json", "glossary.json", "terminology.json",
        "term-variants.json", "roles.json", "obligations.json", "essential-records.json", "term-comparisons.json",
        "extraction-report.json",
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
        if path != CONTENT / "index.md" and re.search(r"(?m)^#\s+", raw):
            errors.append(f"Generoitu sivu sisältää frontmatter-otsikon toistavan H1-otsikon: {path.relative_to(ROOT)}")
        if re.search(r"(?m)^#{1,6}[^\n]*\^[a-zA-Z0-9._-]+", raw):
            errors.append(f"Näkyvä tekninen ankkuri otsikossa: {path.relative_to(ROOT)}")
        if fm.get("classification") == "derived" and fm.get("review_status") != "pending":
            errors.append(f"Johdetun sivun tarkistustila ei ole pending: {path.relative_to(ROOT)}")
        if fm.get("content_type") in {"role_view", "derived_role_view"}:
            required_notice = (
                "Tämä sivu on muodostettu lähdetekstistä automaattisesti ja sivu tulee käsitellä kokeellisena.\n"
                "> Sivua ei ole sisältötarkastettu."
            )
            if required_notice not in raw:
                errors.append(f"Roolinäkymän kokeellisuusilmoitus on väärä: {path.relative_to(ROOT)}")
            if "## Keskeiset velvoitteet" in raw:
                errors.append(f"Roolinäkymässä on poistettavaksi määrätty Keskeiset velvoitteet -osio: {path.relative_to(ROOT)}")
            heading_positions = [raw.find(f"### {heading}") for heading, _ in ROLE_WORKFLOW]
            if any(position < 0 for position in heading_positions) or heading_positions != sorted(heading_positions):
                errors.append(f"Roolinäkymän työnkulkuotsikot puuttuvat tai ovat väärässä järjestyksessä: {path.relative_to(ROOT)}")
        if fm.get("content_type") in {"derived_examples", "derived_learning_page"} and DERIVED_NOTICE not in raw:
            errors.append(f"Johdetulta oppimissivulta puuttuu kokeellisuusilmoitus: {path.relative_to(ROOT)}")
        if fm.get("content_type") == "source_term_comparison":
            if fm.get("classification") != "source_compilation" or "Johdettu näkymä" in raw:
                errors.append(f"Lähdepohjainen termivertailu on merkitty johdetuksi: {path.relative_to(ROOT)}")
        if fm.get("content_type") == "obligation_register":
            if any(header in raw for header in ("<th>Modaliteetti</th>", "<th>Tarkistus</th>")):
                errors.append("Velvoiterekisterissä on poistettu sarake.")
            table = raw.split("<table>", 1)[1] if "<table>" in raw else ""
            if "[[" in table:
                errors.append("Velvoiterekisterin HTML-taulukossa on käsittelemättömiä wikilinkkejä.")

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

    navigation_folders = {
        "02-gcp-periaatteet", "03-liite-1", "04-liite-a-tutkijan-tietopaketti",
        "05-liite-b-tutkimussuunnitelma", "06-liite-c-oleelliset-tallenteet",
    }
    for folder in navigation_folders:
        ordered = [section for section in sections if section["folder"] == folder]
        for index, section in enumerate(ordered):
            page = ROOT / section["path"]
            raw = page.read_text(encoding="utf-8")
            if "## Liittyvät käsitteet" in raw:
                errors.append(f"Lähdesivulla on poistettavaksi määrätty Liittyvät käsitteet -osio: {section['path']}")
            if index:
                previous = ordered[index - 1]
                expected = f"Edellinen sivu: [[{previous['path'][8:-3]}|{previous['title_fi']}]]"
                if expected not in raw:
                    errors.append(f"Lähdesivun edellinen-linkki on väärä: {section['path']}")
            elif "Edellinen sivu:" in raw:
                errors.append(f"Lähdejakson ensimmäisellä sivulla on edellinen-linkki: {section['path']}")
            if index + 1 < len(ordered):
                following = ordered[index + 1]
                expected = f"Seuraava sivu: [[{following['path'][8:-3]}|{following['title_fi']}]]"
                if expected not in raw:
                    errors.append(f"Lähdesivun seuraava-linkki on väärä: {section['path']}")
            elif "Seuraava sivu:" in raw:
                errors.append(f"Lähdejakson viimeisellä sivulla on seuraava-linkki: {section['path']}")

    if len(term_comparisons) != 10 or len(TERM_COMPARISON_SPECS) != 10:
        errors.append("Termivertailuja ei ole täsmälleen kymmenen.")
    for comparison in term_comparisons:
        page = CONTENT / "termivertailut" / f"{comparison['slug']}.md"
        if not page.exists():
            errors.append(f"Termivertailusivu puuttuu: {comparison['slug']}")
            continue
        raw = page.read_text(encoding="utf-8")
        for term in comparison["terms"]:
            if f"## {term['term_fi']}" not in raw:
                errors.append(f"Termivertailusta puuttuu suomalainen termi {term['term_fi']}: {comparison['slug']}")
            for source in term["sources"]:
                if source["excerpt"] not in raw or f"[[{source['target']}|" not in raw:
                    errors.append(f"Termivertailun lähdeote tai linkki poikkeaa lähteestä: {comparison['slug']} / {source['title']}")

    examples_page = CONTENT / "esimerkkeja.md"
    if not examples_page.exists():
        errors.append("Esimerkkejä-sivu puuttuu.")
    else:
        examples_text = examples_page.read_text(encoding="utf-8")
        for entry in glossary:
            marker = f"## [[sanasto/{entry['slug']}|{entry['preferred_term_fi']}]]"
            if examples_text.count(marker) != 1:
                errors.append(f"Esimerkkejä-sivun sanastotermi puuttuu tai toistuu: {entry['slug']}")
                continue
            block = examples_text.split(marker, 1)[1].split("\n## [[sanasto/", 1)[0]
            if len(re.findall(r"(?m)^### [123]\. ", block)) != 3 or "### Yleisiä sudenkuoppia" not in block:
                errors.append(f"Esimerkkejä-sivun skenaariot tai sudenkuopat ovat vajaat: {entry['slug']}")

    learning_pages = sorted((CONTENT / "periaatteet-oppiminen").glob("periaate-*.md"))
    if len(learning_pages) != 11:
        errors.append("Periaatteet (oppiminen) -sivuja ei ole yksitoista.")
    for page in learning_pages:
        raw = page.read_text(encoding="utf-8")
        if len(re.findall(r"(?m)^## [1-6]\. ", raw)) != 6:
            errors.append(f"Periaatteen oppimissivulla ei ole kuutta skenaariota: {page.relative_to(ROOT)}")
        if raw.count("Noudattaminen:") != 3 or raw.count("Noudattamatta jättäminen:") != 3:
            errors.append(f"Periaatteen oppimissivun myönteiset ja kielteiset skenaariot eivät jakaudu tasan: {page.relative_to(ROOT)}")

    teach_page = CONTENT / "opeta-minua.md"
    if not teach_page.exists():
        errors.append("Opeta minua -sivu puuttuu.")
    else:
        teach_text = teach_page.read_text(encoding="utf-8")
        for token in ("Learning log.md", "lähikehityksen vyöhyke", "tosielämän käytännön", "varsinaisia ICH E6(R3) -lähdesivuja"):
            if token not in teach_text:
                errors.append(f"Opeta minua -sivulta puuttuu toiminnallisuus {token!r}.")

    for token in ["tietoon perustuva suostumus", "tietokoneistetut järjestelmät", "EN–FI-termisanasto"]:
        if token not in all_text:
            errors.append(f"Unicode-testimerkkijono puuttuu: {token}")
    if any(x["modality_fi"].casefold() not in x["source_text_fi"].casefold() for x in obligations):
        errors.append("Velvoitteen suomalainen modaliteetti ei esiinny tarkassa lähdetekstissä.")
    if any(x["evidence_status"] != "illustrative_not_source_requirement" for x in obligations):
        errors.append("Esimerkkitallenne on merkitty lähdevaatimukseksi.")
    if any(x.get("classification") != "derived" or x.get("review_status") != "pending" for x in obligations):
        errors.append("Kaikkien johdettujen velvoitteiden tarkistustilan tulee olla pending.")
    if any(x.get("classification") != "derived" or x.get("review_status") != "pending" for x in alignments):
        errors.append("Kaikkien johdettujen kohdistusten tarkistustilan tulee olla pending.")
    if alignment_verification.get("status") != "passed" or alignment_verification.get("summary", {}).get("errors") != 0:
        errors.append("Suomi–englanti-osiokohdistusten monikriteerinen varmennus ei ole hyväksytty.")
    if any(x.get("alignment_status") != "automatically_verified" for x in alignments):
        errors.append("Kaikkia suomi–englanti-osiokohdistuksia ei ole varmennettu automaattisesti.")
    if any(x.get("classification") != "derived" or x.get("review_status") != "pending" for x in records):
        errors.append("Kaikkien johdettujen oleellisten tallenteiden tarkistustilan tulee olla pending.")
    if not records or any(not x["name_fi"] or not x["name_en"] for x in records):
        errors.append("Oleellisten tallenteiden kaksikielinen rakenneaineisto on vajaa.")

    exactness_errors: list[str] = []
    fi_verified = 0
    en_verified = 0
    glossary_verified = 0
    fi_hash = hashlib.sha256()
    en_hash = hashlib.sha256()
    for section in sections:
        section_id = section["id"]
        exact_fi = section.get("exact_text_fi", "")
        exact_en = section.get("exact_text_en", "")
        raw_fi = section.get("raw_body_fi", "")
        raw_en = section.get("raw_body_en", "")
        if normalized_raw_source(raw_fi) != normalized_published_source(exact_fi):
            exactness_errors.append(f"{section_id}: suomenkielinen kanoninen teksti poikkeaa PDF-poiminnasta")
        else:
            fi_verified += 1
            fi_hash.update(normalized_published_source(exact_fi).encode("utf-8"))
        if exact_en:
            if normalized_raw_source(raw_en) != normalized_published_source(exact_en):
                exactness_errors.append(f"{section_id}: englanninkielinen kanoninen teksti poikkeaa PDF-poiminnasta")
            else:
                en_verified += 1
                en_hash.update(normalized_published_source(exact_en).encode("utf-8"))

        page_path = ROOT / section["path"]
        if not page_path.exists():
            exactness_errors.append(f"{section_id}: generoitu Markdown-sivu puuttuu")
            continue
        page_text = page_path.read_text(encoding="utf-8")
        if normalized_published_source(finnish_source_body(page_text)) != normalized_published_source(exact_fi):
            exactness_errors.append(f"{section_id}: julkaistu suomenkielinen lähdeteksti ei ole täsmällinen kopio")
        if exact_en and normalized_published_source(english_callout_body(page_text)) != normalized_published_source(exact_en):
            exactness_errors.append(f"{section_id}: julkaistu englanninkielinen lähdeteksti ei ole täsmällinen kopio")

    for entry in glossary:
        page = CONTENT / "sanasto" / f"{entry['slug']}.md"
        page_text = page.read_text(encoding="utf-8")
        fi_match = re.search(r"## Suomenkielinen määritelmä\n\n(.*?)\n\n## Alkuperäinen englanninkielinen määritelmä", page_text, re.S)
        en_match = re.search(r'<div lang="en">\n\n(.*?)\n\n</div>', page_text, re.S)
        if not fi_match or normalized_published_source(fi_match.group(1)) != normalized_published_source(entry["definition_fi"]):
            exactness_errors.append(f"{entry['id']}: suomenkielinen sanastomääritelmä poikkeaa lähdepoiminnasta")
        elif entry.get("definition_en") and (not en_match or normalized_published_source(en_match.group(1)) != normalized_published_source(entry["definition_en"])):
            exactness_errors.append(f"{entry['id']}: englanninkielinen sanastomääritelmä poikkeaa lähdepoiminnasta")
        else:
            glossary_verified += 1

    exactness_report = (
        "# Lähdetekstin täsmällisyysraportti\n\n"
        f"- Tila: **{'HYVÄKSYTTY' if not exactness_errors else 'HYLÄTTY'}**\n"
        f"- PDF-poimintaan täsmääviä suomenkielisiä lähdeosioita: {fi_verified}/{len(sections)}\n"
        f"- PDF-poimintaan täsmääviä englanninkielisiä lähdeosioita: {en_verified}/{sum(bool(x.get('exact_text_en')) for x in sections)}\n"
        f"- Täsmällisinä varmennettuja sanastosivuja: {glossary_verified}/{len(glossary)}\n"
        f"- Suomenkielisen julkaisutekstin SHA-256: `{fi_hash.hexdigest()}`\n"
        f"- Englanninkielisen julkaisutekstin SHA-256: `{en_hash.hexdigest()}`\n\n"
        "Vertailussa sallittiin vain esitystavan merkit (Markdown-linkit, piilotetut ankkurit, otsikko- ja luettelomerkit) sekä välilyöntien ja rivinvaihtojen normalisointi.\n"
    )
    if exactness_errors:
        exactness_report += "\n## Poikkeamat\n\n" + "\n".join(f"- {item}" for item in exactness_errors) + "\n"
        errors.append(f"Lähdetekstin täsmällisyystarkistus epäonnistui ({len(exactness_errors)} poikkeamaa).")
    write_text(REPORTS / "source-exactness-report.md", exactness_report)

    expected_reports = {
        "source-manifest-report.md", "section-coverage-report.md", "alignment-report.md", "normalization-report.md",
        "glossary-link-report.md", "unresolved-term-report.md", "obligation-review-report.md",
        "role-view-review-report.md", "broken-link-report.md", "build-report.md",
        "source-exactness-report.md", "alignment-verification-report.md",
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

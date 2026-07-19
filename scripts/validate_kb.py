from __future__ import annotations

import hashlib
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
        "source-exactness-report.md",
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

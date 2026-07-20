from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
REPORTS = ROOT / "reports"
DATA = ROOT / "data"

ROLE_WORKFLOW_HEADINGS = [
    "Pätevyys ja toteutettavuus", "Tutkimuksen valmistelu ja hyväksynnät", "Delegointi ja valvonta",
    "Suostumus ja tutkimukseen osallistujien suojelu", "Tutkimussuunnitelman noudattaminen",
    "Turvallisuusraportointi", "Tutkimusvalmisteen hallinta", "Tiedot ja tallenteet",
    "Monitorointi, auditoinnit ja tarkastukset", "Tutkimuksen päättäminen",
]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            value = dict(attrs).get("href")
            if value:
                self.hrefs.append(value)


def resolves(source: Path, href: str) -> bool:
    parts = urlsplit(href)
    if parts.scheme or parts.netloc or href.startswith(("mailto:", "tel:", "#")):
        return True
    path = unquote(parts.path)
    if not path:
        return True
    if path == "/ichgcpe6r3fin":
        candidate = PUBLIC / "index.html"
    elif path.startswith("/ichgcpe6r3fin/"):
        candidate = PUBLIC / path[len("/ichgcpe6r3fin/") :]
    elif path.startswith("/"):
        candidate = PUBLIC / path.lstrip("/")
    else:
        candidate = source.parent / path
    candidates = [candidate]
    if candidate.suffix == "":
        candidates.extend([candidate.with_suffix(".html"), candidate / "index.html"])
    return any(x.exists() for x in candidates)


def main() -> None:
    if not PUBLIC.exists():
        raise SystemExit("Quartz-tulostehakemisto public/ puuttuu.")
    errors: list[str] = []
    html_files = list(PUBLIC.rglob("*.html"))
    jsonld_count = 0
    for path in html_files:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(PUBLIC).as_posix()
        if "file:///" in text:
            errors.append(f"Paikallinen file-URL: {relative}")
        if relative != "404.html" and not relative.startswith("tags/") and '<html lang="fi"' not in text:
            errors.append(f"HTML-kieli ei ole fi: {relative}")
        match = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
        if not match:
            errors.append(f"JSON-LD puuttuu: {relative}")
        else:
            try:
                data = json.loads(html.unescape(match.group(1)))
                jsonld_count += 1
                if relative != "404.html" and not relative.startswith("tags/"):
                    for key in ("@context", "@type", "@id", "identifier", "name", "inLanguage"):
                        if not data.get(key):
                            errors.append(f"JSON-LD-kenttä {key} puuttuu: {relative}")
            except json.JSONDecodeError as exc:
                errors.append(f"Virheellinen JSON-LD ({exc}): {relative}")
        if relative != "404.html" and "<title>Nimetön" in text:
            errors.append(f"Sivun otsikkoa ei luettu frontmatterista: {relative}")
        if relative.endswith("/index.html") and not relative.startswith("tags/"):
            if "page-listing" in text or re.search(r"\d+ kohdetta? tässä kansiossa", text):
                errors.append(f"Kansiosivulla on automaattinen kohdeluettelo: {relative}")
        if relative not in {"404.html", "index.html"} and not relative.startswith("tags/"):
            if len(re.findall(r"<h1(?:\s|>)", text)) != 1 or '<h1 class="article-title">' not in text:
                errors.append(f"Sivulla on puuttuva tai toistuva pääotsikko: {relative}")
        if re.search(r"<h[1-6][^>]*>[^<]*\^ich-", text):
            errors.append(f"Otsikossa näkyy tekninen ankkuritunniste: {relative}")
        if relative.startswith("roolipohjaiset-nakymat/") and relative != "roolipohjaiset-nakymat/index.html":
            if "Keskeiset velvoitteet" in text:
                errors.append(f"Roolinäkymässä on Keskeiset velvoitteet -osio: {relative}")
            for notice in (
                "sivu tulee käsitellä kokeellisena",
                "Sivua ei ole sisältötarkastettu",
            ):
                if notice not in text:
                    errors.append(f"Roolinäkymästä puuttuu ilmoitus {notice!r}: {relative}")
            positions = [text.find(heading) for heading in ROLE_WORKFLOW_HEADINGS]
            if any(position < 0 for position in positions) or positions != sorted(positions):
                errors.append(f"Roolinäkymän työnkulkuotsikot puuttuvat tai ovat väärässä järjestyksessä: {relative}")
        if relative.startswith(("02-gcp-periaatteet/", "03-liite-1/", "04-liite-a-tutkijan-tietopaketti/", "05-liite-b-tutkimussuunnitelma/", "06-liite-c-oleelliset-tallenteet/")) and relative.split("/")[-1] != "index.html":
            if "Liittyvät käsitteet" in text:
                errors.append(f"Lähdesivulla näkyy poistettu Liittyvät käsitteet -osio: {relative}")
        parser = LinkParser()
        parser.feed(text)
        for href in parser.hrefs:
            if not resolves(path, href):
                errors.append(f"Rikkinäinen HTML-linkki {href!r}: {relative}")

    representative = PUBLIC / "03-liite-1" / "2-8-tutkimukseen-osallistujien-tietoon-perustuva-suostumus.html"
    if not representative.exists():
        errors.append("Edustava osio 2.8 puuttuu Quartz-tulosteesta.")
    else:
        text = representative.read_text(encoding="utf-8")
        for token in ["2.8 Tutkimukseen osallistujien tietoon perustuva suostumus", '<div lang="en">', '"@type":"TechArticle"', '"identifier":"ich-e6-r3-a1-2.8"']:
            if token not in text:
                errors.append(f"Edustavan osion HTML-tarkistus epäonnistui: {token}")

    principle = PUBLIC / "02-gcp-periaatteet" / "periaate-01.html"
    if not principle.exists():
        errors.append("Edustava periaatesivu puuttuu Quartz-tulosteesta.")
    else:
        principle_text = principle.read_text(encoding="utf-8")
        if '<a id="ich-e6-r3-principle-01-1-1"></a>' not in principle_text:
            errors.append("Periaatteen 1.1 piilotettu vakaa ankkuri puuttuu.")
        if "1.1 ^ich-e6-r3" in principle_text:
            errors.append("Periaatteen 1.1 tekninen ankkuri näkyy otsikossa.")

    register = PUBLIC / "vastuutaulukot" / "index.html"
    if not register.exists():
        errors.append("Velvoite- ja näyttörekisteri puuttuu Quartz-tulosteesta.")
    else:
        register_text = register.read_text(encoding="utf-8")
        for removed_header in ("<th>Modaliteetti</th>", "<th>Tarkistus</th>"):
            if removed_header in register_text:
                errors.append(f"Velvoiterekisterissä näkyy poistettu sarake: {removed_header}")
        if "[[sanasto/" in register_text:
            errors.append("Velvoiterekisterissä on käsittelemätön wikilinkki.")
        if not re.search(r'href="\.\./(?:\./)?sanasto/luottamuksellisuus"', register_text):
            errors.append("Velvoiterekisterin sanastolinkki ei ole klikattava.")

    comparison_pages = list((PUBLIC / "termivertailut").glob("*.html"))
    if len([path for path in comparison_pages if path.name != "index.html"]) != 10:
        errors.append("Quartz-tulosteessa ei ole kymmentä termivertailusivua.")
    for path in comparison_pages:
        if path.name != "index.html" and "Johdettu näkymä" in path.read_text(encoding="utf-8"):
            errors.append(f"Termivertailu näkyy virheellisesti johdettuna sisältönä: {path.name}")

    examples = PUBLIC / "esimerkkeja.html"
    glossary = json.loads((DATA / "glossary.json").read_text(encoding="utf-8"))
    if not examples.exists():
        errors.append("Esimerkkejä-sivu puuttuu Quartz-tulosteesta.")
    else:
        examples_text = examples.read_text(encoding="utf-8")
        missing_example_terms = [
            entry["slug"] for entry in glossary if f"sanasto/{entry['slug']}" not in examples_text
        ]
        if missing_example_terms:
            errors.append(f"Esimerkkejä-sivun sanastokattavuus on vajaa: {missing_example_terms}")

    learning_pages = list((PUBLIC / "periaatteet-oppiminen").glob("periaate-*.html"))
    if len(learning_pages) != 11:
        errors.append("Quartz-tulosteessa ei ole yhtätoista periaatteen oppimissivua.")
    for path in learning_pages:
        text = path.read_text(encoding="utf-8")
        if any(f">{index}. " not in text for index in range(1, 7)) or "Yhteys periaatteeseen:" not in text:
            errors.append(f"Periaatteen oppimissivun skenaariot ovat vajaat: {path.name}")

    teach_me = PUBLIC / "opeta-minua.html"
    if not teach_me.exists() or "Learning log.md" not in teach_me.read_text(encoding="utf-8"):
        errors.append("Opeta minua -sivu tai sen oppimisloki puuttuu Quartz-tulosteesta.")

    broken = [x for x in errors if "linkki" in x.casefold()]
    (REPORTS / "broken-link-report.md").write_text(
        "# Rikkinäisten linkkien raportti\n\n" + ("- HTML- ja wikilinkit tarkistettiin; rikkinäisiä linkkejä ei havaittu.\n" if not broken else "\n".join(f"- {x}" for x in broken) + "\n"),
        encoding="utf-8",
    )
    previous = (REPORTS / "build-report.md").read_text(encoding="utf-8")
    previous = re.sub(r"\n\n## Quartz-tuotantokoonti\n.*?(?=\n\n## |\Z)", "", previous, flags=re.S)
    status = "HYVÄKSYTTY" if not errors else "HYLÄTTY"
    (REPORTS / "build-report.md").write_text(
        previous.rstrip() + f"\n\n## Quartz-tuotantokoonti\n\n- Tila: **{status}**\n- HTML-sivuja: {len(html_files)}\n- Kelvollisia JSON-LD-lohkoja: {jsonld_count}\n" + ("- Edustavan osion 2.8 kieli-, otsikko- ja semantiikkatarkistukset läpäistiin.\n" if not errors else "\n".join(f"- {x}" for x in errors) + "\n"),
        encoding="utf-8",
    )
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Quartz-validointi hyväksytty: {len(html_files)} HTML-sivua, {jsonld_count} JSON-LD-lohkoa.")


if __name__ == "__main__":
    main()

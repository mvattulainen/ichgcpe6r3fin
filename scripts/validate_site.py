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

    broken = [x for x in errors if "linkki" in x.casefold()]
    (REPORTS / "broken-link-report.md").write_text(
        "# Rikkinäisten linkkien raportti\n\n" + ("- HTML- ja wikilinkit tarkistettiin; rikkinäisiä linkkejä ei havaittu.\n" if not broken else "\n".join(f"- {x}" for x in broken) + "\n"),
        encoding="utf-8",
    )
    previous = (REPORTS / "build-report.md").read_text(encoding="utf-8")
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

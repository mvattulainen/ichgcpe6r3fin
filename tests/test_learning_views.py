import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
sys.path.insert(0, str(ROOT / "scripts"))

from build_kb import DERIVED_NOTICE, ROLE_IDS, ROLE_WORKFLOW  # noqa: E402


class LearningViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glossary = json.loads((ROOT / "data" / "glossary.json").read_text(encoding="utf-8"))
        cls.comparisons = json.loads((ROOT / "data" / "term-comparisons.json").read_text(encoding="utf-8"))

    def test_ten_source_only_term_comparisons(self):
        self.assertEqual(len(self.comparisons), 10)
        for comparison in self.comparisons:
            page = (CONTENT / "termivertailut" / f"{comparison['slug']}.md").read_text(encoding="utf-8")
            self.assertNotIn("Johdettu näkymä", page)
            for term in comparison["terms"]:
                self.assertIn(f"## {term['term_fi']}", page)
                for source in term["sources"]:
                    self.assertIn(source["excerpt"], page)
                    self.assertIn(f"[[{source['target']}|", page)

    def test_examples_cover_every_glossary_term_with_three_scenarios(self):
        page = (CONTENT / "esimerkkeja.md").read_text(encoding="utf-8")
        self.assertIn(DERIVED_NOTICE, page)
        for entry in self.glossary:
            marker = f"## [[sanasto/{entry['slug']}|{entry['preferred_term_fi']}]]"
            self.assertEqual(page.count(marker), 1)
            block = page.split(marker, 1)[1].split("\n## [[sanasto/", 1)[0]
            self.assertEqual(len(re.findall(r"(?m)^### [123]\. ", block)), 3)
            self.assertIn("### Yleisiä sudenkuoppia", block)

    def test_principle_learning_pages_have_balanced_scenarios(self):
        pages = sorted((CONTENT / "periaatteet-oppiminen").glob("periaate-*.md"))
        self.assertEqual(len(pages), 11)
        for path in pages:
            page = path.read_text(encoding="utf-8")
            self.assertIn(DERIVED_NOTICE, page)
            self.assertEqual(len(re.findall(r"(?m)^## [1-6]\. ", page)), 6)
            self.assertEqual(page.count("Noudattaminen:"), 3)
            self.assertEqual(page.count("Noudattamatta jättäminen:"), 3)
            self.assertIn("Avaa periaatteen lähdeteksti ja selitys", page)

    def test_role_pages_follow_workflow_order(self):
        for role in ROLE_IDS:
            page = (CONTENT / "roolipohjaiset-nakymat" / f"{role}.md").read_text(encoding="utf-8")
            positions = [page.index(f"### {heading}") for heading, _ in ROLE_WORKFLOW]
            self.assertEqual(positions, sorted(positions))

    def test_source_pages_have_navigation_without_related_concepts(self):
        folders = [
            "02-gcp-periaatteet", "03-liite-1", "04-liite-a-tutkijan-tietopaketti",
            "05-liite-b-tutkimussuunnitelma", "06-liite-c-oleelliset-tallenteet",
        ]
        for folder in folders:
            for path in (CONTENT / folder).glob("*.md"):
                if path.name == "index.md":
                    continue
                page = path.read_text(encoding="utf-8")
                self.assertNotIn("## Liittyvät käsitteet", page)
        section_1_1 = (CONTENT / "03-liite-1" / "1-1-hakeminen-ja-tiedoksi-antaminen.md").read_text(encoding="utf-8")
        self.assertIn("Seuraava sivu: [[03-liite-1/1-2-vastuut|1.2 Vastuut]]", section_1_1)

    def test_teach_me_prompt_is_stateful_and_source_first(self):
        page = (CONTENT / "opeta-minua.md").read_text(encoding="utf-8")
        for token in ("Learning log.md", "lähikehityksen vyöhyke", "yksi käytännön GCP-kysymys kerrallaan", "täsmällinen lähdekohta ja linkki"):
            self.assertIn(token, page)


if __name__ == "__main__":
    unittest.main()

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_kb import PageLine, parse_toc_line, publication_text  # noqa: E402


class SectionAlignmentRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sections = {
            item["id"]: item
            for item in json.loads((ROOT / "data" / "sections.json").read_text(encoding="utf-8"))
        }
        cls.verification = json.loads(
            (ROOT / "data" / "alignment-verification.json").read_text(encoding="utf-8")
        )

    def test_spaced_finnish_toc_page_number_is_not_truncated(self):
        parsed = parse_toc_line(
            "2.1 Pätevyys ja koulutus ............................................................2 3"
        )
        self.assertEqual(parsed, ("2.1", "Pätevyys ja koulutus", 23))

    def test_wrapped_cross_reference_is_not_published_as_foreign_heading(self):
        rendered = publication_text(
            [
                PageLine(19, "1.2.5 Eettinen toimikunta voi pyytää lisätietoja kohdassa"),
                PageLine(20, "2.8.11 kuvattujen tietojen lisäksi."),
            ],
            "ich-e6-r3-a1-1.2",
            "fi",
            "1.2",
        )
        self.assertNotIn("### 2.8.11", rendered)
        self.assertIn("2.8.11 kuvattujen tietojen lisäksi", rendered)

    def test_all_sections_pass_multi_criteria_verification(self):
        self.assertEqual(self.verification["status"], "passed")
        self.assertEqual(self.verification["summary"]["errors"], 0)
        self.assertEqual(self.verification["summary"]["automatically_verified"], 146)
        self.assertEqual(self.verification["summary"]["unassigned_finnish_lines"], 0)
        self.assertEqual(self.verification["summary"]["unassigned_english_lines"], 0)

    def test_introduction_subsections_have_isolated_english_counterparts(self):
        structure = self.sections["ich-e6-r3-introduction-rakenne"]
        self.assertIn("Guideline structure", structure["exact_text_en"])
        self.assertNotIn("Guideline scope", structure["raw_text_en"])
        introduction = self.sections["ich-e6-r3-introduction-johdanto"]
        self.assertNotIn("Guideline structure", introduction["raw_text_en"])

    def test_principles_preamble_is_present_in_both_languages(self):
        preamble = self.sections["ich-e6-r3-principles-introduction"]
        self.assertIn("Kliiniset lääketutkimukset ovat olennainen osa", preamble["exact_text_fi"])
        self.assertIn("Clinical trials are a fundamental part", preamble["exact_text_en"])

    def test_principle_heading_has_exact_english_counterpart(self):
        principle = self.sections["ich-e6-r3-principle-01"]
        self.assertIn("Clinical trials should be conducted in accordance", principle["exact_text_en"])

    def test_annex_2_1_does_not_capture_principle_2_1(self):
        section = self.sections["ich-e6-r3-a1-2.1"]
        self.assertEqual(section["finnish_pages"][0], 23)
        self.assertIn("2.1.1 Tutkijalla tulee olla", section["raw_body_fi"])
        self.assertNotIn("Vapaasta tahdosta annettu", section["raw_body_fi"])

    def test_section_1_2_has_no_false_2_8_11_heading(self):
        section = self.sections["ich-e6-r3-a1-1.2"]
        self.assertNotIn("### 2.8.11", section["exact_text_fi"])


if __name__ == "__main__":
    unittest.main()

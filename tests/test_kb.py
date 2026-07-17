import json
import unicodedata
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeBaseTests(unittest.TestCase):
    def test_required_unicode_rendering_strings(self):
        samples = [
            "ä ö å Ä Ö Å",
            "tietoon perustuva suostumus",
            "tietokoneistetut järjestelmät",
            "EN–FI-termisanasto",
        ]
        encoded = "\n".join(samples).encode("utf-8")
        rendered = encoded.decode("utf-8")
        self.assertEqual(rendered, unicodedata.normalize("NFC", rendered))
        for sample in samples:
            self.assertIn(sample, rendered)

    def test_json_preserves_non_ascii(self):
        value = {"otsikko": "Tietokoneistetut järjestelmät – käyttöoikeuksien hallinta"}
        rendered = json.dumps(value, ensure_ascii=False)
        self.assertIn("ä", rendered)
        self.assertNotIn("\\u00e4", rendered)

    def test_canonical_files_exist(self):
        for name in ["documents.json", "sections.json", "alignments.json", "glossary.json", "obligations.json"]:
            self.assertTrue((ROOT / "data" / name).exists(), name)


if __name__ == "__main__":
    unittest.main()

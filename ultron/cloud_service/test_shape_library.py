import re
import unittest

import scene_design
import shape_library as lib


class ShapeLibraryTests(unittest.TestCase):
    def test_every_generator_is_valid_for_every_count(self):
        for words, gen in lib.CATALOG:
            for n in (None, 0, 1, 2, 3, 5, 8, 12, 16, 20, 99):
                parts = gen(n)
                self.assertTrue(1 <= len(parts) <= lib.MAX_PARTS, (gen.__name__, n))
                scene_design.validate({"name": gen.__name__, "parts": parts})

    def test_every_keyword_resolves_to_its_own_generator(self):
        for words, gen in lib.CATALOG:
            for w in words:
                self.assertIn(gen, lib._matches(w), (w, gen.__name__))

    def test_turkish_phrases_counts_and_combinations(self):
        self.assertEqual(len(lib.generate("8 köşeli yıldız")["parts"]), 9)
        self.assertEqual(len(lib.generate("12 basamaklı merdiven")["parts"]), 12)
        self.assertEqual(len(lib.generate("bana bir kalp göster")["parts"]), 3)
        two = lib.generate("bir ev ve ağaç")
        self.assertEqual(len(two["parts"]), 9)
        scene_design.validate(two)
        xs = [p["position"][0] for p in two["parts"]]
        self.assertLess(min(xs), -1)
        self.assertGreater(max(xs), 1)

    def test_unknown_and_lookalike_words_fall_through(self):
        for t in ("", "sihirli tilki", "evet", "okul", "toplama", "örümcek", "kupon"):
            self.assertIsNone(lib.generate(t), t)

    def test_name_is_bounded_and_data_only(self):
        d = lib.generate("kalp " + "x" * 200)
        self.assertLessEqual(len(d["name"]), 90)
        self.assertEqual(set(d), {"name", "parts"})

    def test_frontend_noun_list_covers_every_catalogue_keyword(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parents[1] / "frontend" / "src" / "spatial" / "intents.ts").read_text(encoding="utf-8")
        arrays = re.findall(r"export const SHAPE_(?:PREFIX|WORD)_NOUNS=\[(.*?)\];", src)
        nouns = set(re.findall(r"'([^']+)'", " ".join(arrays)))
        self.assertGreater(len(nouns), 80)
        for words, gen in lib.CATALOG:
            for w in words:
                # a catalogue keyword is covered by the same word, one of its words, or a noun that prefixes it
                covered = any(n == w or n in w.split() or w.startswith(n) for n in nouns)
                self.assertTrue(covered, f"{w!r} ({gen.__name__}) missing from SHAPE_*_NOUNS in intents.ts")


if __name__ == "__main__":
    unittest.main()

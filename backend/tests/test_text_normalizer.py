import unittest

from app.audio.normalizer import normalize_transcript


class TextNormalizerTests(unittest.TestCase):
    def test_luxshare_variants_seen_in_review_audio(self):
        variants = (
            "lắc se",
            "lắc xe",
            "lắc xê",
            "lắc xé",
            "lắcxé",
            "lắc xế",
            "lác xe",
            "lạc xe",
            "lát xe",
            "lúc se",
            "lux se",
        )
        for variant in variants:
            with self.subTest(variant=variant):
                text = f"nhà máy ở {variant} nghệ an"
                self.assertEqual(
                    normalize_transcript(text),
                    "nhà máy ở Luxshare nghệ an",
                )

    def test_normalizes_the_supplied_sentence_without_changing_other_words(self):
        text = "mình có đang quan tâm đến nhà máy ở lắc xê nghệ an ý"
        self.assertEqual(
            normalize_transcript(text),
            "mình có đang quan tâm đến nhà máy ở Luxshare nghệ an ý",
        )


if __name__ == "__main__":
    unittest.main()

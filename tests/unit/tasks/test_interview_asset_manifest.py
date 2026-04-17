import unittest

from depression_detection.tasks.interview.assets import load_interview_asset_manifest


class InterviewAssetManifestTests(unittest.TestCase):
    def test_manifest_loads_movie_reading_and_qa_assets_from_static_directory(self):
        manifest = load_interview_asset_manifest()
        self.assertEqual([item.key for item in manifest.movie], ["positive", "neutral", "negative"])
        self.assertEqual([item.key for item in manifest.reading], ["positive", "neutral", "negative"])
        self.assertEqual(len(manifest.qa_questions), 16)
        self.assertTrue(manifest.movie[0].url.startswith("/static/interview-assets/movie/"))
        self.assertTrue(manifest.reading[0].text)


if __name__ == "__main__":
    unittest.main()

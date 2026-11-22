import unittest
from open_ielts_strategy.composition import resolve_dependencies

class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.entries=[
            {"name":"base","dependencies":[]},
            {"name":"writing","dependencies":["base"]},
            {"name":"review","dependencies":["writing"]}
        ]
    def test_dependencies_precede_dependents(self):
        self.assertEqual(resolve_dependencies(["review"],self.entries),["base","writing","review"])
    def test_deduplicates_shared_dependency(self):
        self.assertEqual(resolve_dependencies(["writing","review"],self.entries),["base","writing","review"])
    def test_unknown_dependency(self):
        with self.assertRaisesRegex(ValueError,"unknown skill"):
            resolve_dependencies(["missing"],self.entries)
    def test_rejects_duplicate_manifest_names(self):
        entries=[{"name":"a","dependencies":[]},{"name":"a","dependencies":[]}]
        with self.assertRaisesRegex(ValueError,"duplicate skill name"):
            resolve_dependencies(["a"],entries)

    def test_rejects_non_list_dependencies(self):
        with self.assertRaisesRegex(ValueError,"dependencies must be a list"):
            resolve_dependencies(["a"],[{"name":"a","dependencies":"base"}])

    def test_rejects_duplicate_dependencies(self):
        with self.assertRaisesRegex(ValueError,"duplicate dependency"):
            resolve_dependencies(["a"],[{"name":"a","dependencies":["base","base"]},{"name":"base","dependencies":[]}])

    def test_rejects_noncanonical_selected_names(self):
        with self.assertRaisesRegex(ValueError,"canonical name"):
            resolve_dependencies([" a"],self.entries)

    def test_rejects_malformed_manifest_entries(self):
        with self.assertRaisesRegex(ValueError,"must be an object"):
            resolve_dependencies(["base"],[None])

    def test_cycle(self):
        cyclic=[{"name":"a","dependencies":["b"]},{"name":"b","dependencies":["a"]}]
        with self.assertRaisesRegex(ValueError,"cycle"):
            resolve_dependencies(["a"],cyclic)

if __name__=="__main__": unittest.main()

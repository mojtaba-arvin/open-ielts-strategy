import unittest
from open_ielts_strategy.integration_adapters import AdapterDescriptor, resolve_adapter

def descriptor(name, capability):
    return AdapterDescriptor(name, capability, "1.0", lambda: None)

class IntegrationAdapterTests(unittest.TestCase):
    def test_no_installed_adapter_is_explicit(self):
        with self.assertRaisesRegex(LookupError, "not installed"):
            resolve_adapter("audio_transcription", descriptors=())
    def test_multiple_adapters_require_selection(self):
        values = (descriptor("audio_transcription:vendor_a", "audio_transcription"),
                  descriptor("audio_transcription:vendor_b", "audio_transcription"))
        with self.assertRaisesRegex(LookupError, "select one explicitly"):
            resolve_adapter("audio_transcription", descriptors=values)
        self.assertEqual(resolve_adapter("audio_transcription",
            preferred="audio_transcription:vendor_b", descriptors=values).name,
            "audio_transcription:vendor_b")
    def test_unknown_capability_rejected(self):
        with self.assertRaises(ValueError):
            resolve_adapter("automatic_magic", descriptors=())

if __name__ == "__main__":
    unittest.main()

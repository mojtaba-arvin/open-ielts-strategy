import io
import unittest
import wave

from open_ielts_strategy.audio import inspect_audio


def wav_bytes(seconds=1, rate=16000, channels=1):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(b"\x00\x00" * int(seconds * rate * channels))
    return buffer.getvalue()


class AudioValidationTests(unittest.TestCase):
    def test_accepts_generated_wav_and_reports_metadata(self):
        result = inspect_audio(wav_bytes(2), "sample.wav")
        self.assertEqual(result["format"], "wav")
        self.assertEqual(result["sample_rate_hz"], 16000)
        self.assertEqual(result["duration_seconds"], 2.0)

    def test_rejects_empty_invalid_extension_and_corrupt_wav(self):
        for data, name in ((b"", "a.wav"), (b"not audio", "a.wav"), (b"data", "a.exe")):
            with self.subTest(name=name), self.assertRaises(ValueError):
                inspect_audio(data, name)

    def test_rejects_size_and_duration_limits(self):
        with self.assertRaisesRegex(ValueError, "max_bytes"):
            inspect_audio(wav_bytes(), "a.wav", max_bytes=10)
        with self.assertRaisesRegex(ValueError, "max_duration"):
            inspect_audio(wav_bytes(2), "a.wav", max_duration_seconds=1)

    def test_rejects_malformed_arguments(self):
        for data, name in ((bytearray(b"x"), "x.wav"), (b"x", ""), (b"x", "x.ogg")):
            with self.subTest(name=name), self.assertRaises(ValueError):
                inspect_audio(data, name)

    def test_accepts_minimal_valid_mp3_frames(self):
        frame = bytes.fromhex("ff fb 90 64") + (b"\x00" * (417 - 4))
        result = inspect_audio(frame * 3, "synthetic.mp3")
        self.assertEqual(result["format"], "mp3")
        self.assertEqual(result["frames"], 3)
        self.assertGreater(result["duration_seconds"], 0)

    def test_rejects_mp3_without_valid_frame(self):
        with self.assertRaisesRegex(ValueError, "valid MP3"):
            inspect_audio(b"ID3" + b"\x00" * 20, "bad.mp3")


if __name__ == "__main__":
    unittest.main()

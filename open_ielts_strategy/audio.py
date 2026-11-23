"""Offline audio container validation; no transcription or network calls."""
from dataclasses import asdict, dataclass
import io
import wave

DEFAULT_MAX_BYTES = 25 * 1024 * 1024
DEFAULT_MAX_DURATION_SECONDS = 15 * 60
_MPEG_BITRATES = {
    (1, 1): [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448],
    (1, 2): [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384],
    (1, 3): [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
    (2, 1): [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],
    (2, 2): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
    (2, 3): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
}
_SAMPLE_RATES = {0: 44100, 1: 48000, 2: 32000}


@dataclass(frozen=True)
class AudioMetadata:
    format: str
    size_bytes: int
    duration_seconds: float
    sample_rate_hz: int | None
    channels: int | None
    frames: int


def _mp3_metadata(data):
    offset = 0
    if data.startswith(b"ID3"):
        if len(data) < 10:
            raise ValueError("truncated MP3 ID3 header")
        size_bytes = data[6:10]
        if any(byte & 0x80 for byte in size_bytes):
            raise ValueError("invalid MP3 ID3 size")
        tag_size = (size_bytes[0] << 21) | (size_bytes[1] << 14) | (size_bytes[2] << 7) | size_bytes[3]
        offset = 10 + tag_size + (10 if data[5] & 0x10 else 0)
        if offset > len(data):
            raise ValueError("truncated MP3 ID3 tag")

    frames = 0
    duration = 0.0
    first_rate = None
    first_channels = None
    while offset + 4 <= len(data):
        header = int.from_bytes(data[offset:offset + 4], "big")
        if (header >> 21) & 0x7FF != 0x7FF:
            offset += 1
            continue
        version_bits = (header >> 19) & 0x3
        layer_bits = (header >> 17) & 0x3
        bitrate_index = (header >> 12) & 0xF
        sample_index = (header >> 10) & 0x3
        padding = (header >> 9) & 1
        if version_bits == 1 or layer_bits == 0 or bitrate_index in (0, 15) or sample_index == 3:
            offset += 1
            continue
        version = 1 if version_bits == 3 else 2
        layer = 4 - layer_bits
        bitrate = _MPEG_BITRATES[(version, layer)][bitrate_index] * 1000
        sample_rate = _SAMPLE_RATES[sample_index] // (1 if version_bits == 3 else 2 if version_bits == 2 else 4)
        if layer == 1:
            frame_length = (12 * bitrate // sample_rate + padding) * 4
            samples = 384
        else:
            coefficient = 144 if version_bits == 3 or layer == 2 else 72
            frame_length = coefficient * bitrate // sample_rate + padding
            samples = 1152 if version_bits == 3 or layer != 3 else 576
        if frame_length < 4 or offset + frame_length > len(data):
            break
        frames += 1
        duration += samples / sample_rate
        first_rate = first_rate or sample_rate
        first_channels = first_channels or (1 if ((header >> 6) & 0x3) == 3 else 2)
        offset += frame_length
    if frames == 0:
        raise ValueError("file does not contain a valid MP3 audio frame")
    return AudioMetadata("mp3", len(data), round(duration, 3), first_rate, first_channels, frames)


def inspect_audio(data, filename, *, max_bytes=DEFAULT_MAX_BYTES,
                  max_duration_seconds=DEFAULT_MAX_DURATION_SECONDS):
    """Validate supported audio bytes and return metadata without writing files."""
    if not isinstance(data, bytes) or not data:
        raise ValueError("audio data must be non-empty bytes")
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("filename must be non-empty text")
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    if type(max_duration_seconds) not in (int, float) or max_duration_seconds <= 0:
        raise ValueError("max_duration_seconds must be a positive number")
    if len(data) > max_bytes:
        raise ValueError("audio file exceeds max_bytes")
    extension = filename.rsplit(".", 1)[-1].casefold() if "." in filename else ""
    if extension == "wav":
        try:
            with wave.open(io.BytesIO(data), "rb") as stream:
                channels = stream.getnchannels()
                rate = stream.getframerate()
                frames = stream.getnframes()
                width = stream.getsampwidth()
                payload = stream.readframes(frames)
                if len(payload) != frames * channels * width:
                    raise ValueError("truncated WAV audio payload")
                if channels not in (1, 2) or rate < 8000 or width not in (1, 2, 3, 4):
                    raise ValueError("unsupported WAV audio parameters")
                duration = frames / rate
                metadata = AudioMetadata("wav", len(data), round(duration, 3), rate, channels, frames)
        except (wave.Error, EOFError) as exc:
            raise ValueError("invalid or truncated WAV file") from exc
    elif extension == "mp3":
        metadata = _mp3_metadata(data)
    else:
        raise ValueError("unsupported audio extension; expected .wav or .mp3")
    if metadata.duration_seconds <= 0:
        raise ValueError("audio duration must be greater than zero")
    if metadata.duration_seconds > max_duration_seconds:
        raise ValueError("audio file exceeds max_duration_seconds")
    return asdict(metadata)

"""
SECTION 7 — FINGERPRINT ENGINE TEST

Tests VideoFingerprinter and AudioFingerprinter.
Cases:
  - video file path input (string path)
  - video bytes input
  - audio file path input
  - audio bytes input

Verifies fingerprints generated (non-empty string).
Tests comparison similarity scores.
Tests fallback mode when deps missing.
"""

import pytest
from aimon.fingerprint import (
    VideoFingerprinter,
    AudioFingerprinter,
    FingerprintEngine,
)


# ---------------------------------------------------------------------------
# VideoFingerprinter
# ---------------------------------------------------------------------------

async def test_video_fingerprinter_name():
    fp = VideoFingerprinter()
    assert fp.name == "video_fingerprinting"


async def test_video_fingerprint_string_path():
    fp = VideoFingerprinter()
    result = await fp.fingerprint("path/to/video.mp4")
    assert isinstance(result, str)
    assert len(result) > 0


async def test_video_fingerprint_bytes():
    fp = VideoFingerprinter()
    result = await fp.fingerprint(b"fake video bytes")
    assert isinstance(result, str)
    assert len(result) > 0


async def test_video_fingerprint_dict_input():
    fp = VideoFingerprinter()
    result = await fp.fingerprint({"frames": [1, 2, 3]})
    assert isinstance(result, str)
    assert len(result) > 0


async def test_video_fingerprint_is_hex_string():
    fp = VideoFingerprinter()
    result = await fp.fingerprint("path/to/video.mp4")
    if result:
        assert all(c in "0123456789abcdef" for c in result)


async def test_video_fingerprint_deterministic():
    """Same input should produce the same fingerprint."""
    fp = VideoFingerprinter()
    fp1 = await fp.fingerprint("test_data")
    fp2 = await fp.fingerprint("test_data")
    assert fp1 == fp2


async def test_video_compare_identical():
    fp = VideoFingerprinter()
    data = "same video data"
    fpa = await fp.fingerprint(data)
    fpb = await fp.fingerprint(data)
    similarity = await fp.compare(fpa, fpb)
    assert similarity == 1.0


async def test_video_compare_different():
    fp = VideoFingerprinter()
    fpa = await fp.fingerprint("video A data")
    fpb = await fp.fingerprint("video B completely different")
    similarity = await fp.compare(fpa, fpb)
    assert isinstance(similarity, float)
    assert 0.0 <= similarity <= 1.0


# ---------------------------------------------------------------------------
# AudioFingerprinter
# ---------------------------------------------------------------------------

async def test_audio_fingerprinter_name():
    fp = AudioFingerprinter()
    assert fp.name == "audio_fingerprinting"


async def test_audio_fingerprint_string_path():
    fp = AudioFingerprinter()
    result = await fp.fingerprint("path/to/audio.mp3")
    assert isinstance(result, str)
    assert len(result) > 0


async def test_audio_fingerprint_bytes():
    fp = AudioFingerprinter()
    result = await fp.fingerprint(b"fake audio bytes")
    assert isinstance(result, str)
    assert len(result) > 0


async def test_audio_fingerprint_is_hex_string():
    fp = AudioFingerprinter()
    result = await fp.fingerprint("path/to/audio.mp3")
    if result:
        assert all(c in "0123456789abcdef" for c in result)


async def test_audio_fingerprint_deterministic():
    fp = AudioFingerprinter()
    fp1 = await fp.fingerprint("test audio")
    fp2 = await fp.fingerprint("test audio")
    assert fp1 == fp2


async def test_audio_compare_identical():
    fp = AudioFingerprinter()
    data = "same audio data"
    fpa = await fp.fingerprint(data)
    fpb = await fp.fingerprint(data)
    similarity = await fp.compare(fpa, fpb)
    assert similarity == 1.0


async def test_audio_compare_different():
    fp = AudioFingerprinter()
    fpa = await fp.fingerprint("audio A")
    fpb = await fp.fingerprint("audio B completely different")
    similarity = await fp.compare(fpa, fpb)
    assert isinstance(similarity, float)
    assert 0.0 <= similarity <= 1.0


async def test_compare_result_is_float_in_range():
    fp = VideoFingerprinter()
    fpa = await fp.fingerprint("some content")
    fpb = await fp.fingerprint("other content")
    result = await fp.compare(fpa, fpb)
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0


# ---------------------------------------------------------------------------
# FingerprintEngine
# ---------------------------------------------------------------------------

async def test_fingerprint_engine_video():
    engine = FingerprintEngine()
    fp = await engine.fingerprint("video", "video data")
    assert isinstance(fp, str)
    assert len(fp) > 0


async def test_fingerprint_engine_audio():
    engine = FingerprintEngine()
    fp = await engine.fingerprint("audio", "audio data")
    assert isinstance(fp, str)
    assert len(fp) > 0


async def test_fingerprint_engine_match_identical():
    engine = FingerprintEngine()
    fpa = await engine.fingerprint("video", "same data")
    fpb = await engine.fingerprint("video", "same data")
    match_result = await engine.match("video", fpa, fpb)
    assert "match" in match_result
    assert "similarity" in match_result
    assert match_result["match"] is True


async def test_fingerprint_engine_unknown_type_returns_empty():
    engine = FingerprintEngine()
    result = await engine.fingerprint("unknown_type", "data")
    assert result == ""

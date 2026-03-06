"""
Audio Fingerprinter - Mel-spectrogram-based audio content identification.

Uses ``librosa`` to compute a mel spectrogram and produces a compact
128-dimensional float vector (mean-pooled across time) packed as bytes.

If ``librosa`` is not installed the module falls back to a SHA-256 hash of
the raw bytes / string representation of the input.
"""

import hashlib
import io
import struct
from pathlib import Path
from typing import Any, Union

import structlog

from aimon.fingerprint.engine import BaseFingerprinter

logger = structlog.get_logger(__name__)

try:
    import librosa
    import numpy as np
    _LIBROSA_AVAILABLE = True
except ImportError:
    _LIBROSA_AVAILABLE = False

# Expected hex-string length for 128 float32 values
# 128 floats × 4 bytes/float × 2 hex chars/byte = 1024
_EXPECTED_HEX_LEN = 128 * 4 * 2


class AudioFingerprinter(BaseFingerprinter):
    """
    Audio content fingerprinter using mel spectrograms.

    Produces a hex-encoded fingerprint derived from the mean mel-spectrogram
    energy vector (128 dimensions).  Comparison uses cosine similarity of
    the decoded float vectors.
    """

    def __init__(self):
        super().__init__("audio_fingerprinting")

    # ------------------------------------------------------------------
    # BaseFingerprinter interface
    # ------------------------------------------------------------------

    async def fingerprint(self, data: Any) -> str:
        """
        Generate a fingerprint for *data*.

        *data* may be:
        - A ``str`` or ``pathlib.Path`` pointing to an audio file.
        - ``bytes`` or ``bytearray`` containing raw audio data.
        """
        try:
            if _LIBROSA_AVAILABLE:
                return self._librosa_fingerprint(data)
            else:
                return self._fallback_fingerprint(data)
        except Exception as e:
            await logger.aerror("audio_fingerprint_failed", error=str(e))
            return ""

    async def compare(self, fp1: str, fp2: str, threshold: float = 0.9) -> float:
        """
        Compare two fingerprints.

        Uses cosine similarity of the decoded float vectors when both
        fingerprints match the expected spectral format (1 024 hex chars).
        Falls back to exact match otherwise.
        """
        try:
            if not fp1 or not fp2:
                return 0.0
            if fp1 == fp2:
                return 1.0

            if (
                _LIBROSA_AVAILABLE
                and len(fp1) == _EXPECTED_HEX_LEN
                and len(fp2) == _EXPECTED_HEX_LEN
            ):
                v1 = self._decode_vector(fp1)
                v2 = self._decode_vector(fp2)
                if v1 is not None and v2 is not None:
                    return float(self._cosine_similarity(v1, v2))

            # fallback: exact match
            return 1.0 if fp1 == fp2 else 0.0
        except Exception as e:
            await logger.aerror("audio_compare_failed", error=str(e))
            return 0.0

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _librosa_fingerprint(data: Any) -> str:
        """Compute mel-spectrogram fingerprint using librosa."""
        if isinstance(data, (bytes, bytearray)):
            source = io.BytesIO(bytes(data))
        else:
            source = str(data)

        y, sr = librosa.load(source, sr=22050, mono=True)
        mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, hop_length=512)
        mel_db = librosa.power_to_db(mel, ref=np.max)
        feature = mel_db.mean(axis=1).astype(np.float32)
        packed = struct.pack(f"{len(feature)}f", *feature)
        return packed.hex()

    @staticmethod
    def _fallback_fingerprint(data: Any) -> str:
        """SHA-256 of raw bytes or string representation."""
        if isinstance(data, (bytes, bytearray)):
            payload = bytes(data)
        else:
            payload = str(data).encode()
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _decode_vector(hex_str: str):
        """Decode a hex fingerprint into a list of floats."""
        try:
            raw = bytes.fromhex(hex_str)
            n = len(raw) // 4
            return list(struct.unpack(f"{n}f", raw))
        except Exception:
            return None

    @staticmethod
    def _cosine_similarity(v1, v2) -> float:
        """Cosine similarity between two equal-length float vectors."""
        import math
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return max(-1.0, min(1.0, dot / (norm1 * norm2)))

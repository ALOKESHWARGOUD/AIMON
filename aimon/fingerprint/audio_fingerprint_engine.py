"""
Audio Fingerprint Engine - Mel spectrogram comparison for audio verification.

Uses librosa for feature extraction and scipy/numpy for cosine similarity.
All librosa calls run in a thread-pool executor since librosa is synchronous.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

_REQUIRED = (
    "librosa, scipy, and numpy must be installed. "
    "Install them with: pip install 'aimon[fingerprint]'"
)

try:
    import numpy as np
    _NP_AVAILABLE = True
except ImportError:
    _NP_AVAILABLE = False
    np = None  # type: ignore


class AudioFingerprintEngine:
    """
    Verify audio content via mel spectrogram cosine similarity.

    All librosa calls are offloaded to a ``ThreadPoolExecutor``.

    Args:
        sr: Default sample rate for audio loading.
        n_mels: Number of mel filter banks.
    """

    def __init__(self, sr: int = 22050, n_mels: int = 128) -> None:
        self.sr = sr
        self.n_mels = n_mels

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def extract_audio_fingerprint(
        self,
        audio_path: str,
        sr: Optional[int] = None,
        n_mels: Optional[int] = None,
    ) -> "np.ndarray":
        """
        Compute a mel spectrogram fingerprint for an audio file.

        Args:
            audio_path: Path to the audio file.
            sr: Sample rate override.
            n_mels: Number of mel bins override.

        Returns:
            2-D numpy array (mel spectrogram).
        """
        _sr = sr or self.sr
        _n_mels = n_mels or self.n_mels
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None, self._extract_sync, audio_path, _sr, _n_mels
            )
        except Exception as exc:
            await logger.aerror("audio_fingerprint_failed", path=audio_path, error=str(exc))
            if _NP_AVAILABLE:
                import numpy as _np
                return _np.zeros((_n_mels, 1))
            return None  # type: ignore

    async def compare_fingerprints(
        self,
        fp_a: "np.ndarray",
        fp_b: "np.ndarray",
    ) -> float:
        """
        Compute cosine similarity between two mel spectrogram fingerprints.

        Args:
            fp_a: First fingerprint (2-D numpy array).
            fp_b: Second fingerprint (2-D numpy array).

        Returns:
            Cosine similarity score in [0.0, 1.0].
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None, self._compare_sync, fp_a, fp_b
            )
        except Exception as exc:
            await logger.aerror("audio_compare_failed", error=str(exc))
            return 0.0

    async def fingerprint_from_url(
        self,
        url: str,
        temp_dir: str = "/tmp/aimon_audio",
    ) -> Optional["np.ndarray"]:
        """
        Download an audio file from *url* and return its mel spectrogram.

        Args:
            url: Remote audio URL.
            temp_dir: Directory to store temporary files.

        Returns:
            Mel spectrogram array or ``None`` on failure.
        """
        import aiohttp
        import tempfile

        os.makedirs(temp_dir, exist_ok=True)
        tmp_path: Optional[str] = None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    resp.raise_for_status()
                    suffix = os.path.splitext(url.split("?")[0])[-1] or ".mp3"
                    fd, tmp_path = tempfile.mkstemp(suffix=suffix, dir=temp_dir)
                    with os.fdopen(fd, "wb") as f:
                        async for chunk in resp.content.iter_chunked(65536):
                            f.write(chunk)

            return await self.extract_audio_fingerprint(tmp_path)
        except Exception as exc:
            await logger.aerror("audio_fingerprint_from_url_failed", url=url, error=str(exc))
            return None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    # ------------------------------------------------------------------
    # synchronous internals (run in executor)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_sync(audio_path: str, sr: int, n_mels: int) -> "np.ndarray":
        """Extract mel spectrogram synchronously."""
        try:
            import librosa  # type: ignore
            import numpy as np
        except ImportError as exc:
            raise ImportError(_REQUIRED) from exc

        y, sample_rate = librosa.load(audio_path, sr=sr)
        mel = librosa.feature.melspectrogram(y=y, sr=sample_rate, n_mels=n_mels)
        return librosa.power_to_db(mel, ref=np.max)

    @staticmethod
    def _compare_sync(fp_a: "np.ndarray", fp_b: "np.ndarray") -> float:
        """Cosine similarity between two spectrogram matrices."""
        try:
            import numpy as np
            from scipy.spatial.distance import cosine  # type: ignore
        except ImportError as exc:
            raise ImportError(_REQUIRED) from exc

        vec_a = fp_a.flatten().astype(float)
        vec_b = fp_b.flatten().astype(float)

        # Align lengths by padding the shorter vector
        max_len = max(len(vec_a), len(vec_b))
        if len(vec_a) < max_len:
            vec_a = np.pad(vec_a, (0, max_len - len(vec_a)))
        if len(vec_b) < max_len:
            vec_b = np.pad(vec_b, (0, max_len - len(vec_b)))

        # Handle zero vectors
        if np.linalg.norm(vec_a) == 0 or np.linalg.norm(vec_b) == 0:
            return 0.0

        similarity = 1.0 - cosine(vec_a, vec_b)
        return float(max(0.0, min(1.0, similarity)))

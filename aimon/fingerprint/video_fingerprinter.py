"""
Video Fingerprinter - Frame-based video content identification.

Uses OpenCV (``opencv-python-headless``) to sample frames and build a
SHA-256 fingerprint from their pixel data.  If OpenCV is not installed
the module falls back to a SHA-256 hash of the raw bytes / string
representation of the input.
"""

import hashlib
import tempfile
import os
from pathlib import Path
from typing import Any, Union

import structlog

from aimon.fingerprint.engine import BaseFingerprinter

logger = structlog.get_logger(__name__)

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False


class VideoFingerprinter(BaseFingerprinter):
    """
    Video content fingerprinter.

    Samples one frame every ``sample_interval_sec`` seconds, resizes each
    sampled frame to 32 × 32 grayscale, and feeds all pixel bytes through a
    single SHA-256 hasher.

    Args:
        sample_interval_sec: Seconds between sampled frames (default: 1.0).
    """

    def __init__(self, sample_interval_sec: float = 1.0):
        super().__init__("video_fingerprinting")
        self.sample_interval_sec = sample_interval_sec

    # ------------------------------------------------------------------
    # BaseFingerprinter interface
    # ------------------------------------------------------------------

    async def fingerprint(self, data: Any) -> str:
        """
        Generate a fingerprint for *data*.

        *data* may be:
        - A ``str`` or ``pathlib.Path`` pointing to a video file.
        - ``bytes`` or ``bytearray`` containing raw video data.
        """
        try:
            if _CV2_AVAILABLE:
                return self._cv2_fingerprint(data)
            else:
                return self._fallback_fingerprint(data)
        except Exception as e:
            await logger.aerror("video_fingerprint_failed", error=str(e))
            return ""

    async def compare(self, fp1: str, fp2: str, threshold: float = 0.9) -> float:
        """
        Compare two fingerprints using character-level Hamming similarity.

        Returns a value in [0.0, 1.0].
        """
        try:
            if not fp1 or not fp2:
                return 0.0
            if fp1 == fp2:
                return 1.0
            length = max(len(fp1), len(fp2))
            if length == 0:
                return 1.0
            # Pad shorter string
            a = fp1.ljust(length, "0")
            b = fp2.ljust(length, "0")
            different = sum(ca != cb for ca, cb in zip(a, b))
            return 1.0 - (different / length)
        except Exception as e:
            await logger.aerror("video_compare_failed", error=str(e))
            return 0.0

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    def _cv2_fingerprint(self, data: Any) -> str:
        """Produce a fingerprint using OpenCV frame sampling."""
        tmp_path: str = ""
        created_tmp = False

        try:
            if isinstance(data, (bytes, bytearray)):
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                    f.write(data)
                    tmp_path = f.name
                created_tmp = True
                path = tmp_path
            else:
                path = str(data)

            cap = cv2.VideoCapture(path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps == 0 or fps is None:
                fps = 25.0

            frame_interval = max(1, int(fps * self.sample_interval_sec))
            hasher = hashlib.sha256()
            frame_idx = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % frame_interval == 0:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    small = cv2.resize(gray, (32, 32))
                    hasher.update(small.tobytes())
                frame_idx += 1

            cap.release()
            return hasher.hexdigest()
        finally:
            if created_tmp and tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @staticmethod
    def _fallback_fingerprint(data: Any) -> str:
        """SHA-256 of raw bytes or string representation."""
        if isinstance(data, (bytes, bytearray)):
            payload = bytes(data)
        else:
            payload = str(data).encode()
        return hashlib.sha256(payload).hexdigest()

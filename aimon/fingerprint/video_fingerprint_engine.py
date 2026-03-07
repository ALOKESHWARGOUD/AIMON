"""
Video Fingerprint Engine - Perceptual hashing for video content verification.

Uses OpenCV for frame extraction and imagehash for perceptual hashing.
All blocking I/O runs in a thread-pool executor to avoid blocking the loop.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, List, Optional

import structlog

logger = structlog.get_logger(__name__)

_REQUIRED = (
    "opencv-python (cv2), imagehash, numpy, and Pillow must be installed. "
    "Install them with: pip install 'aimon[fingerprint]'"
)


class VideoFingerprintEngine:
    """
    Verify video content via perceptual frame hashing (phash).

    Frame extraction runs in a ``ThreadPoolExecutor`` because OpenCV is
    synchronous.

    Args:
        sample_rate: Extract one frame every *sample_rate* frames.
    """

    def __init__(self, sample_rate: int = 30) -> None:
        self.sample_rate = sample_rate

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def extract_frame_hashes(
        self,
        video_path: str,
        sample_rate: Optional[int] = None,
    ) -> List[str]:
        """
        Extract perceptual hashes from frames of a video file.

        Args:
            video_path: Path to the video file on disk.
            sample_rate: Sample every Nth frame (overrides instance default).

        Returns:
            List of hex hash strings (one per sampled frame).
        """
        rate = sample_rate or self.sample_rate
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None, self._extract_hashes_sync, video_path, rate
            )
        except Exception as exc:
            await logger.aerror("video_hash_extraction_failed", path=video_path, error=str(exc))
            return []

    async def compare_videos(
        self,
        hashes_a: List[str],
        hashes_b: List[str],
        threshold: float = 0.85,
    ) -> float:
        """
        Compare two sets of frame hashes and return a similarity score.

        The score is the fraction of best-matched hash pairs whose
        normalised Hamming distance is below (1 - *threshold*).

        Args:
            hashes_a: Frame hashes from video A.
            hashes_b: Frame hashes from video B.
            threshold: Minimum per-frame similarity to count as a match.

        Returns:
            Similarity score in [0.0, 1.0].
        """
        if not hashes_a or not hashes_b:
            return 0.0

        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None, self._compare_hashes_sync, hashes_a, hashes_b, threshold
            )
        except Exception as exc:
            await logger.aerror("video_compare_failed", error=str(exc))
            return 0.0

    async def fingerprint_from_url(
        self,
        url: str,
        temp_dir: str = "/tmp/aimon_video",
    ) -> Optional[List[str]]:
        """
        Download a video from *url* and return its frame hashes.

        Args:
            url: Remote video URL.
            temp_dir: Directory to store temporary downloaded file.

        Returns:
            List of hex hash strings, or ``None`` on failure.
        """
        import aiohttp
        import tempfile

        os.makedirs(temp_dir, exist_ok=True)
        tmp_path: Optional[str] = None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    resp.raise_for_status()
                    suffix = os.path.splitext(url.split("?")[0])[-1] or ".mp4"
                    fd, tmp_path = tempfile.mkstemp(suffix=suffix, dir=temp_dir)
                    with os.fdopen(fd, "wb") as f:
                        async for chunk in resp.content.iter_chunked(65536):
                            f.write(chunk)

            return await self.extract_frame_hashes(tmp_path)
        except Exception as exc:
            await logger.aerror("video_fingerprint_from_url_failed", url=url, error=str(exc))
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

    def _extract_hashes_sync(self, video_path: str, sample_rate: int) -> List[str]:
        """Extract frame hashes synchronously (must run in executor)."""
        try:
            import cv2  # type: ignore
            import imagehash  # type: ignore
            from PIL import Image  # type: ignore
        except ImportError as exc:
            raise ImportError(_REQUIRED) from exc

        cap = cv2.VideoCapture(video_path)
        hashes: List[str] = []
        frame_idx = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % sample_rate == 0:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(rgb)
                    h = imagehash.phash(img)
                    hashes.append(str(h))
                frame_idx += 1
        finally:
            cap.release()

        return hashes

    @staticmethod
    def _compare_hashes_sync(
        hashes_a: List[str],
        hashes_b: List[str],
        threshold: float,
    ) -> float:
        """Compare two hash lists synchronously."""
        try:
            import imagehash  # type: ignore
        except ImportError as exc:
            raise ImportError(_REQUIRED) from exc

        if not hashes_a or not hashes_b:
            return 0.0

        hash_size = len(hashes_a[0]) * 4  # bits per hex char = 4
        matches = 0

        for ha_str in hashes_a:
            ha = imagehash.hex_to_hash(ha_str)
            best = min(
                (imagehash.hex_to_hash(hb_str) - ha) / hash_size
                for hb_str in hashes_b
            )
            if (1.0 - best) >= threshold:
                matches += 1

        return matches / len(hashes_a)

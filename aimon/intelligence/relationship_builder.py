"""
Relationship Builder - Extracts graph node/edge pairs from leak signals.

Parses ``leak_signal_detected`` event payloads and returns the set of
(from_node_id, relationship_type, to_node_id) triples that should be
persisted to the network graph.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)

# URL pattern helpers
_DRIVE_PATTERN = re.compile(r"https?://drive\.google\.com/\S+", re.I)
_DOCS_PATTERN = re.compile(r"https?://docs\.google\.com/\S+", re.I)
_MEGA_PATTERN = re.compile(r"https?://mega\.(?:nz|co\.nz)/\S+", re.I)
_TORRENT_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:1337x\.to|thepiratebay\.org|piratebay\.org)/\S+", re.I
)
_DROPBOX_PATTERN = re.compile(r"https?://(?:www\.)?dropbox\.com/\S+", re.I)
_INVITE_PATTERN = re.compile(r"https?://t\.me/(?:\+|joinchat/)[A-Za-z0-9_-]+", re.I)
_REDDIT_PATTERN = re.compile(r"https?://(?:www\.)?reddit\.com/\S+", re.I)


class RelationshipBuilder:
    """
    Converts raw leak signal data into graph node and edge specifications.

    All methods are synchronous since they perform only in-memory
    computation (no I/O).
    """

    def __init__(self, network_mapper: Any) -> None:
        """
        Args:
            network_mapper: A :class:`LeakNetworkMapper` instance used to
                persist nodes and edges.
        """
        self._mapper = network_mapper

    async def process_signal(
        self, signal: Dict[str, Any]
    ) -> List[Tuple[str, str, str]]:
        """
        Process a ``leak_signal_detected`` payload and persist graph data.

        Args:
            signal: Full signal dict from ``LeakSignalModule``.

        Returns:
            List of (from_node_id, relationship_type, to_node_id) triples
            that were added to the graph.
        """
        relationships: List[Tuple[str, str, str]] = []
        brand = signal.get("brand", "")
        url = signal.get("url", "")
        platform = signal.get("platform", "unknown")
        raw_signals = signal.get("raw_signals", [])
        all_urls = [url] + raw_signals

        # Ensure Brand node exists
        brand_id = await self._mapper.add_node("Brand", {"name": brand})

        # -----------------------------------------------------------------
        # Platform-specific node creation
        # -----------------------------------------------------------------
        source_node_id: Optional[str] = None

        if platform == "telegram":
            source_node_id = await self._mapper.add_node(
                "TelegramChannel", {"url": url, "title": signal.get("channel_title", url)}
            )
            await self._mapper.add_relationship(source_node_id, brand_id, "TARGETS")
            relationships.append((source_node_id, "TARGETS", brand_id))

            # Invite links embedded in raw_signals
            for raw in raw_signals:
                for match in _INVITE_PATTERN.finditer(raw):
                    invite_id = await self._mapper.add_node(
                        "InviteLink", {"url": match.group(0), "platform": "telegram"}
                    )
                    await self._mapper.add_relationship(source_node_id, invite_id, "SHARED_BY")
                    relationships.append((source_node_id, "SHARED_BY", invite_id))

        elif platform == "reddit":
            source_node_id = await self._mapper.add_node(
                "RedditPost",
                {
                    "url": url,
                    "subreddit": signal.get("subreddit", ""),
                    "score": signal.get("score", 0),
                },
            )
        else:
            # Generic source — use a plain Brand-targeting edge
            source_node_id = brand_id

        # -----------------------------------------------------------------
        # Drive / cloud storage links
        # -----------------------------------------------------------------
        for raw in all_urls:
            for pattern, provider in [
                (_DRIVE_PATTERN, "google_drive"),
                (_DOCS_PATTERN, "google_drive"),
                (_MEGA_PATTERN, "mega"),
                (_DROPBOX_PATTERN, "dropbox"),
            ]:
                for match in pattern.finditer(raw):
                    drive_id = await self._mapper.add_node(
                        "DriveLink", {"url": match.group(0), "provider": provider}
                    )
                    if source_node_id and source_node_id != brand_id:
                        await self._mapper.add_relationship(
                            source_node_id, drive_id, "SHARED_BY"
                        )
                        relationships.append((source_node_id, "SHARED_BY", drive_id))
                    else:
                        await self._mapper.add_relationship(brand_id, drive_id, "TARGETS")
                        relationships.append((brand_id, "TARGETS", drive_id))

        # -----------------------------------------------------------------
        # Torrent links
        # -----------------------------------------------------------------
        for raw in all_urls:
            for match in _TORRENT_PATTERN.finditer(raw):
                torrent_id = await self._mapper.add_node(
                    "TorrentLink",
                    {"url": match.group(0), "magnet": None, "seeders": 0},
                )
                if source_node_id and source_node_id != brand_id:
                    await self._mapper.add_relationship(
                        source_node_id, torrent_id, "MIRRORED_TO"
                    )
                    relationships.append((source_node_id, "MIRRORED_TO", torrent_id))

        # -----------------------------------------------------------------
        # Reddit cross-links from non-reddit sources
        # -----------------------------------------------------------------
        if platform != "reddit":
            for raw in all_urls:
                for match in _REDDIT_PATTERN.finditer(raw):
                    reddit_id = await self._mapper.add_node(
                        "RedditPost", {"url": match.group(0), "subreddit": "", "score": 0}
                    )
                    if source_node_id and source_node_id != brand_id:
                        await self._mapper.add_relationship(
                            reddit_id, source_node_id, "LINKED_FROM"
                        )
                        relationships.append((reddit_id, "LINKED_FROM", source_node_id))

        return relationships

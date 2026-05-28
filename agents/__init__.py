"""Tunde agents package (Phase 2+).

Phase 2 introduces the first concrete agent: Listener, which demonstrates
end-to-end usage of GitHubTool + SoulOSMemory for duplicate-free monitoring.
"""

from .listener import Listener

__all__ = ["Listener"]

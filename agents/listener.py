"""
agents/listener.py — Phase 2 Listener Agent (minimal, read-only)

The Listener is the "front door" of the Tunde crew. Its sole job in V1 is:

1. Periodically poll a target GitHub repository for issues and comments.
2. Use SoulOSMemory.has_responded(gh_item_id) to filter out anything
   Tunde has already handled.
3. Surface only the genuinely new activity so that later pipeline stages
   (Researcher, Writer, Editorial, etc. — Phases 3+) can act on it.

CRITICAL Phase 2 constraints observed:
- Uses GitHubTool exclusively (all calls go through Latchkey).
- Never writes to GitHub.
- Never posts comments or updates.
- Does not yet hand off to other agents (that coordination is Phase 5).
- The mark_responded() helper exists so that a future full pipeline can
  record completion, but the Listener itself does not call it.

This file, together with tools/github.py, completes the Phase 2 deliverable.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from soul_os.memory import SoulOSMemory
from tools.github import GitHubTool


class Listener:
    """Monitors one GitHub repository for new, unhandled issues/comments.

    Example (the primary test for Phase 2):

        from agents.listener import Listener

        lis = Listener(work_dir=".", target_owner="imbue-ai", target_repo="mngr")
        fresh = lis.poll_once(max_issues=8)

        print("New issues:", len(fresh["new_issues"]))
        print("New comments:", len(fresh["new_comments"]))
    """

    def __init__(
        self,
        work_dir: str,
        target_owner: str,
        target_repo: str,
        github_tool: Optional[GitHubTool] = None,
    ) -> None:
        """Initialize Listener.

        Args:
            work_dir: Base directory where soul_os/memory/ will be created/read.
            target_owner: GitHub org or user (e.g. "imbue-ai").
            target_repo: Repository name (e.g. "mngr").
            github_tool: Optional pre-constructed GitHubTool (useful for tests
                         with a fake). If None, a real one is created.
        """
        self.memory = SoulOSMemory(work_dir)
        self.github: GitHubTool = github_tool or GitHubTool()
        self.owner = target_owner
        self.repo = target_repo

    def poll_once(self, max_issues: int = 10) -> Dict[str, Any]:
        """Execute one monitoring sweep.

        Returns a dict containing only items that have never been marked
        responded in SoulOSMemory. The shape is exactly what
        GitHubTool.fetch_unresponded_activity produces, plus a small amount
        of Listener metadata.

        In later phases this method will become the trigger for the full
        Researcher → Writer → Editorial → Publishing flow. For Phase 2 it
        simply returns the filtered activity.
        """
        activity = self.github.fetch_unresponded_activity(
            self.owner,
            self.repo,
            self.memory,
            max_issues=max_issues,
        )

        # Attach Listener identity so callers know the source
        activity["listener"] = {
            "target": f"{self.owner}/{self.repo}",
            "work_dir": str(self.memory.root.parent.parent),
        }
        return activity

    def mark_responded(self, item_id: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Record that Tunde has handled a particular GitHub item.

        This is provided for the future pipeline. The Listener does not
        call it itself during Phase 2 — marking happens after a response
        has been successfully drafted, reviewed, and (later) published.

        Args:
            item_id: Value produced by GitHubTool.make_item_id(...)
            extra: Any additional data you want persisted alongside the
                   "responded": True flag (e.g. quality score, response URL).
        """
        payload = {"responded": True, **(extra or {})}
        self.memory.save_interaction(item_id, payload)

    def get_memory_stats(self) -> Dict[str, Any]:
        """Small introspection helper useful during development."""
        mem = self.memory.load_interactions()
        return {
            "total_interactions_tracked": len(mem.get("items", {})),
            "last_updated": mem.get("last_updated"),
        }


# ---------------------------------------------------------------------------
# Direct execution convenience (matches "next command to test it" requirement)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys

    owner = sys.argv[1] if len(sys.argv) > 1 else "imbue-ai"
    repo = sys.argv[2] if len(sys.argv) > 2 else "mngr"

    print(f"[Listener] Phase 2 smoke test — polling {owner}/{repo} ...")
    listener = Listener(work_dir=".", target_owner=owner, target_repo=repo)

    try:
        result = listener.poll_once(max_issues=5)
    except Exception as exc:
        print("ERROR:", exc)
        print("\nCommon causes in Phase 2:")
        print("  1. latchkey not installed or not authed for github")
        print("      → npm install -g latchkey && latchkey auth browser github")
        print("  2. No internet or Latchkey permissions.json blocking the call")
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))
    print("\n[Listener] Done. New items above are safe to act on (no duplicates).")

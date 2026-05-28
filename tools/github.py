"""
tools/github.py — Phase 2 GitHub Tool for Tunde (Developer Relations Agent)

This module provides the single reusable GitHubTool class.

MANDATORY RULES (Phase 2 V1):
- Every single GitHub API call MUST be performed via the `latchkey` CLI.
- NO Personal Access Tokens, NO environment variables containing secrets,
  NO hardcoded Authorization headers, NO direct httpx/requests calls to api.github.com.
- Only read-only operations are implemented (GET /issues, /comments, /repos/*).
- The tool is intentionally decoupled from any specific agent but provides
  high-level helpers that integrate directly with SoulOSMemory for duplicate
  suppression via has_responded().

Intended consumers:
- Listener agent (primary focus for Phase 2)
- Researcher agent (future phases, read-only context gathering)

See: https://github.com/imbue-ai/latchkey for Latchkey installation & auth setup.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from soul_os.memory import SoulOSMemory


class GitHubTool:
    """Reusable, Latchkey-backed GitHub client for Tunde agents.

    All network access funnels through:
        latchkey curl -H 'Accept: ...' https://api.github.com/...

    This guarantees that GitHub credentials live only in the user's encrypted
    ~/.latchkey store and are never present in Tunde's source, memory files,
    or process environment.

    V1 contract: read-only. No methods exist that can create, update, or comment.
    """

    GITHUB_API_VERSION: str = "2022-11-28"

    def __init__(self, timeout_seconds: int = 30) -> None:
        """Create a GitHubTool.

        Args:
            timeout_seconds: Max wall time for any single latchkey curl invocation.
        """
        self.timeout = timeout_seconds
        self.latchkey_bin = self._resolve_latchkey_or_raise()

    def _resolve_latchkey_or_raise(self) -> str:
        """Locate the latchkey binary. Fail fast with actionable instructions."""
        path = shutil.which("latchkey")
        if not path:
            raise RuntimeError(
                "latchkey CLI not found in $PATH.\n\n"
                "Phase 2 requires Latchkey for *all* GitHub API calls.\n"
                "Install once:\n"
                "    npm install -g latchkey\n"
                "    latchkey ensure-browser\n\n"
                "Authenticate for GitHub (one-time):\n"
                "    latchkey auth browser github\n"
                "    # or: latchkey auth set github -H 'Authorization: token ghp_...'\n\n"
                "Verify:\n"
                "    latchkey services info github\n\n"
                "The GitHubTool will not function until the above succeeds."
            )
        return path

    def _request(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Internal helper: perform an authenticated GET via Latchkey.

        Returns the parsed JSON body (dict or list).
        Raises RuntimeError (with GitHub message when possible) on any failure.
        """
        url = f"https://api.github.com{path}"
        if params:
            from urllib.parse import urlencode

            query = urlencode({k: v for k, v in params.items() if v is not None})
            if query:
                url = f"{url}?{query}"

        cmd: List[str] = [
            self.latchkey_bin,
            "curl",
            "-s",
            "-f",  # curl --fail : non-2xx => non-zero exit
            "-H",
            "Accept: application/vnd.github+json",
            "-H",
            f"X-GitHub-Api-Version: {self.GITHUB_API_VERSION}",
            url,
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"GitHub request via Latchkey timed out after {self.timeout}s: {path}"
            ) from exc

        if proc.returncode != 0:
            body = (proc.stdout or proc.stderr or "").strip()
            message = body
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    message = parsed.get("message", body)
            except Exception:
                pass
            raise RuntimeError(
                f"Latchkey curl failed (exit={proc.returncode}) for {path}: {message}"
            )

        text = proc.stdout.strip()
        if not text:
            # Empty body is valid for some 204-style responses; treat as empty list for collection endpoints
            return [] if any(p in path for p in ("/issues", "/comments")) else {}

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"GitHub returned invalid JSON for {path}: {text[:400]}"
            ) from exc

    # ------------------------------------------------------------------
    # Public read-only API (V1 only — no mutations)
    # ------------------------------------------------------------------

    def list_issues(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "open",
        sort: str = "updated",
        direction: str = "desc",
        per_page: int = 10,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent issues for a repository (pull requests are filtered out).

        Corresponds to GET /repos/{owner}/{repo}/issues
        """
        path = f"/repos/{owner}/{repo}/issues"
        params = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": per_page,
            "since": since,
        }
        data = self._request(path, params)
        if not isinstance(data, list):
            return []
        # The /issues endpoint can surface PRs; keep only real issues for Listener
        return [i for i in data if "pull_request" not in i]

    def list_comments(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        *,
        per_page: int = 30,
    ) -> List[Dict[str, Any]]:
        """Return comments on a specific issue or pull request."""
        path = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
        params = {"per_page": per_page, "sort": "created", "direction": "asc"}
        data = self._request(path, params)
        return data if isinstance(data, list) else []

    def get_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        """Fetch a single issue (or PR) by its number."""
        path = f"/repos/{owner}/{repo}/issues/{issue_number}"
        return self._request(path)

    def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Return basic repository metadata (description, stars, etc.)."""
        path = f"/repos/{owner}/{repo}"
        return self._request(path)

    # ------------------------------------------------------------------
    # SoulOSMemory integration (the Phase 2 requirement)
    # ------------------------------------------------------------------

    @staticmethod
    def make_item_id(owner: str, repo: str, item_type: str, github_id: int | str) -> str:
        """Create a deterministic identifier for use with SoulOSMemory.

        These strings become the keys inside soul_os/memory/interactions.json.
        Using the numeric GitHub id (issue["id"] or comment["id"]) guarantees
        stability across renames, edits, and moves.

        Examples:
            "gh:imbue-ai/mngr:issue:123456789"
            "gh:imbue-ai/mngr:issue_comment:987654321"
        """
        return f"gh:{owner}/{repo}:{item_type}:{github_id}"

    def fetch_unresponded_activity(
        self,
        owner: str,
        repo: str,
        memory: "SoulOSMemory",
        max_issues: int = 15,
    ) -> Dict[str, Any]:
        """High-level helper intended for the Listener agent.

        Fetches the most recently updated issues and then, for each,
        its comments. Returns only the items for which
        SoulOSMemory.has_responded(item_id) returns False.

        This is the exact integration point requested for Phase 2:
            Listener can now call this, iterate the results, and know
            precisely what still needs attention without duplicates.

        The caller (Listener or tests) is responsible for eventually calling
        memory.save_interaction(item_id, {"responded": True, ...}) once the
        item has been processed by the rest of the pipeline.
        """
        # Local import avoids hard circular dependency at import time
        from soul_os.memory import SoulOSMemory as _SoulOSMemory  # noqa: F401

        # We accept duck-typed memory objects for testability; the real one is preferred
        if not hasattr(memory, "has_responded"):
            raise TypeError("memory must implement has_responded(gh_item_id)")

        new_issues: List[Dict[str, Any]] = []
        new_comments: List[Dict[str, Any]] = []

        issues = self.list_issues(owner, repo, state="all", per_page=max_issues)

        for issue in issues:
            item_id = self.make_item_id(owner, repo, "issue", issue["id"])
            if not memory.has_responded(item_id):
                new_issues.append(issue)

            # Inspect comments on this issue as well
            try:
                comments = self.list_comments(owner, repo, issue["number"])
            except Exception:
                # Non-fatal: a single issue's comments failing shouldn't kill the poll
                comments = []

            for comment in comments:
                c_id = self.make_item_id(owner, repo, "issue_comment", comment["id"])
                if not memory.has_responded(c_id):
                    # Attach lightweight context so downstream agents don't need another round-trip
                    comment["_context_issue"] = {
                        "number": issue["number"],
                        "title": issue.get("title"),
                        "html_url": issue.get("html_url"),
                    }
                    new_comments.append(comment)

        return {
            "new_issues": new_issues,
            "new_comments": new_comments,
            "scanned_issues": len(issues),
            "target": f"{owner}/{repo}",
        }


# Convenience alias for callers who prefer a shorter name
GitHub = GitHubTool

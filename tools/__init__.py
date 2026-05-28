"""Tunde tools package (Phase 2: GitHub integration).

Exposes the reusable GitHubTool that all agents (Listener first) must use
for GitHub access. Enforces Latchkey-only auth with zero hardcoded tokens.
"""

from .github import GitHubTool

__all__ = ["GitHubTool"]

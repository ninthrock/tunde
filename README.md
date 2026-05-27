# tunde

**An autonomous Developer Relations agent** — built live on Imbue’s open-source stack.

An early 2026 prototype of what AI-native dev advocacy could look like.

## Status
**In active development. Phase 1 of 6 complete.**

Everything is being built in the open, phase by phase.

| Phase | What it covers                  | Status                      |
|-------|---------------------------------|-----------------------------|
| 1     | Architecture & specification    | ✅ Complete                 |
| 2     | Tool use — GitHub integration   | In progress                 |
| 3     | Memory & state                  | **Design + stub complete**  |
| 4     | Evaluation layer                | Not started                 |
| 5     | Multi-agent coordination        | Not started                 |
| 6     | Guardrails & accountability     | Not started                 |

## Architecture

```mermaid
flowchart TD
    subgraph "Imbue Open-Source Stack"
        B[Blueprint<br>— Planning]
        M[mngr<br>— Agent Orchestration]
        L[Latchkey<br>— GitHub Auth]
        D[Detent<br>— Safety & Permissions]
    end

    subgraph "Soul OS<br>(Domain Cognition Layer)"
        S[Soul OS<br>Domain Memory + Quality Standards + Persona]
    end

    subgraph "Tunde Crew<br>(6 Specialized Agents)"
        Lis[Listener<br>→ Monitors GitHub]
        Res[Researcher<br>→ Gathers context]
        Wri[Writer<br>→ Drafts responses]
        Ed[Editorial<br>→ Quality gate]
        Pub[Publishing<br>→ Human-approved posting]
        PM[Post-Mortem<br>→ Reflection & learning]
    end

    ImbueStack["Imbue Stack"] --> SoulOS
    SoulOS --> TundeCrew["Tunde Crew"]
    TundeCrew --> GitHub[GitHub Repositories]

    style SoulOS fill:#4ade80,stroke:#166534,stroke-width:3px
    style TundeCrew fill:#64748b,stroke:#334155

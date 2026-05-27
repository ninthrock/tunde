"""
Soul OS — Memory & Domain Cognition Layer (V1)
Supplies persistent memory and quality standards that Imbue's base stack does not provide.
Persisted as simple files in each agent's work_dir for easy auditing and restartability.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

class SoulOSMemory:
    def __init__(self, work_dir: str):
        self.root = Path(work_dir) / "soul_os" / "memory"
        self.root.mkdir(parents=True, exist_ok=True)
        
    def _load_json(self, filename: str, default: Any = None) -> Dict:
        path = self.root / filename
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return default or {}
        return default or {}
    
    def _save_json(self, filename: str, data: Dict) -> None:
        path = self.root / filename
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # ==================== INTERACTIONS ====================
    def load_interactions(self) -> Dict:
        return self._load_json("interactions.json", {"last_updated": None, "items": {}})
    
    def save_interaction(self, gh_item_id: str, data: Dict) -> None:
        mem = self.load_interactions()
        mem["items"][gh_item_id] = {
            **data,
            "timestamp": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
        mem["last_updated"] = datetime.utcnow().isoformat()
        self._save_json("interactions.json", mem)
    
    def has_responded(self, gh_item_id: str) -> bool:
        mem = self.load_interactions()
        return mem["items"].get(gh_item_id, {}).get("responded", False)
    
    # ==================== LEARNINGS / POST-MORTEM ====================
    def load_learnings(self) -> Dict:
        return self._load_json("learnings.json", {"last_batch": None, "insights": [], "global_rules": []})
    
    def save_learnings(self, learnings: Dict) -> None:
        self._save_json("learnings.json", learnings)
    
    # ==================== QUALITY STANDARD ====================
    def load_quality_standard(self) -> Dict:
        default = {
            "version": "1.0",
            "criteria": {
                "technical_accuracy": 0.35,
                "genuine_usefulness": 0.30,
                "appropriate_humility": 0.15,
                "coherent_voice": 0.10,
                "restraint": 0.10
            },
            "examples": {
                "good": [],
                "bad": []
            }
        }
        return self._load_json("quality_standard.json", default)
    
    def save_quality_standard(self, standard: Dict) -> None:
        self._save_json("quality_standard.json", standard)

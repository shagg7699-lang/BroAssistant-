"""
ব্রো (Bro) — joshu প্রেডিক্টর
ব্যবহারকারীর পরবর্তী কাজ অনুমান ও সাজেশন।
joshu-assistant ইন্সপায়ার্ড।
"""

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import get_logger

log = get_logger("joshu_predictor")


class ActionRecord:
    def __init__(self, action: str, context: str = "", timestamp: float = 0.0) -> None:
        self.action = action
        self.context = context
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {"action": self.action, "context": self.context, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionRecord":
        return cls(data["action"], data.get("context", ""), data.get("timestamp", 0))


class JoshuPredictor:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.prediction_threshold = cfg.get("prediction_threshold", 0.7)
        self._history_file = Path(cfg.get("history_file", "data/action_history.json"))
        self._history: List[ActionRecord] = []
        self._patterns: Dict[str, Counter] = {}
        self._load_history()

    def _load_history(self) -> None:
        if self._history_file.exists():
            try:
                data = json.loads(self._history_file.read_text(encoding="utf-8"))
                self._history = [ActionRecord.from_dict(item) for item in data]
                self._rebuild_patterns()
            except Exception as exc:
                log.warning("অ্যাকশন হিস্ট্রি লোড ব্যর্থ: %s", exc)

    def _save_history(self) -> None:
        self._history_file.parent.mkdir(parents=True, exist_ok=True)
        data = [r.to_dict() for r in self._history[-5000:]]
        self._history_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _rebuild_patterns(self) -> None:
        self._patterns.clear()
        for i in range(len(self._history) - 1):
            current = self._history[i].action
            next_action = self._history[i + 1].action
            if current not in self._patterns:
                self._patterns[current] = Counter()
            self._patterns[current][next_action] += 1

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [{"description": "পরবর্তী কাজ অনুমান", "action": "predict", "risky": False}]

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        predictions = self.predict_next()
        return {"status": "success", "predictions": predictions}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        return await self.execute(step.get("description", ""), context)

    def record_action(self, action: str, context: str = "") -> None:
        record = ActionRecord(action, context)
        self._history.append(record)

        if len(self._history) >= 2:
            prev = self._history[-2].action
            if prev not in self._patterns:
                self._patterns[prev] = Counter()
            self._patterns[prev][action] += 1

        self._save_history()

    def predict_next(self, current_action: Optional[str] = None) -> List[Tuple[str, float]]:
        if not current_action and self._history:
            current_action = self._history[-1].action

        if not current_action or current_action not in self._patterns:
            return self._get_most_common()

        counter = self._patterns[current_action]
        total = sum(counter.values())
        predictions = [
            (action, count / total)
            for action, count in counter.most_common(5)
        ]

        return [(a, s) for a, s in predictions if s >= self.prediction_threshold * 0.5]

    def _get_most_common(self) -> List[Tuple[str, float]]:
        if not self._history:
            return []
        all_actions = Counter(r.action for r in self._history)
        total = sum(all_actions.values())
        return [(a, c / total) for a, c in all_actions.most_common(5)]

    def get_suggestions(self, current_action: Optional[str] = None) -> List[Dict[str, Any]]:
        predictions = self.predict_next(current_action)
        suggestions = []
        for action, confidence in predictions:
            suggestions.append({
                "action": action,
                "confidence": round(confidence, 3),
                "message": f"পরবর্তী কাজ হতে পারে: {action} ({confidence:.0%})",
            })
        return suggestions

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_actions": len(self._history),
            "unique_actions": len(set(r.action for r in self._history)),
            "patterns": len(self._patterns),
        }

    async def fallback(self, step: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]]) -> Any:
        return None

"""
ব্রো (Bro) — BANtz Behavior Learner
রিইনফোর্সমেন্ট লার্নিং দিয়ে ব্যবহারকারীর পছন্দ ও কৌশল শেখা।
BANtz ইন্সপায়ার্ড।
"""

import json
import random
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import get_logger

log = get_logger("bantz_behavior")


class QTable:
    def __init__(self, learning_rate: float = 0.1, discount: float = 0.95, epsilon: float = 0.1) -> None:
        self.lr = learning_rate
        self.gamma = discount
        self.epsilon = epsilon
        self._table: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    def get_action(self, state: str, available_actions: List[str]) -> str:
        if not available_actions:
            return ""

        if random.random() < self.epsilon:
            return random.choice(available_actions)

        q_values = self._table.get(state, {})
        best_action = max(available_actions, key=lambda a: q_values.get(a, 0.0))
        return best_action

    def update(self, state: str, action: str, reward: float, next_state: str, next_actions: List[str]) -> None:
        current_q = self._table[state][action]

        if next_actions:
            next_q_values = self._table.get(next_state, {})
            max_next_q = max((next_q_values.get(a, 0.0) for a in next_actions), default=0.0)
        else:
            max_next_q = 0.0

        new_q = current_q + self.lr * (reward + self.gamma * max_next_q - current_q)
        self._table[state][action] = new_q

    def to_dict(self) -> Dict[str, Dict[str, float]]:
        return {state: dict(actions) for state, actions in self._table.items()}

    def from_dict(self, data: Dict[str, Dict[str, float]]) -> None:
        self._table.clear()
        for state, actions in data.items():
            for action, value in actions.items():
                self._table[state][action] = value


class BantzBehaviorLearner:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self._model_file = Path(cfg.get("model_file", "data/bantz_model.json"))
        self._q_table = QTable(
            learning_rate=cfg.get("learning_rate", 0.1),
            discount=cfg.get("discount_factor", 0.95),
            epsilon=cfg.get("epsilon", 0.1),
        )
        self._reward_history: List[Dict[str, Any]] = []
        self._current_state: str = "idle"
        self._load_model()

    def _load_model(self) -> None:
        if self._model_file.exists():
            try:
                data = json.loads(self._model_file.read_text(encoding="utf-8"))
                self._q_table.from_dict(data.get("q_table", {}))
                self._reward_history = data.get("history", [])
                log.info("BANtz মডেল লোড: %d স্টেট", len(data.get("q_table", {})))
            except Exception as exc:
                log.warning("BANtz মডেল লোড ব্যর্থ: %s", exc)

    def _save_model(self) -> None:
        self._model_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "q_table": self._q_table.to_dict(),
            "history": self._reward_history[-1000:],
        }
        self._model_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [{"description": "আচরণ শেখা", "action": "learn", "risky": False}]

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "ready", "states": len(self._q_table.to_dict())}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        return await self.execute(step.get("description", ""), context)

    def observe(self, state: str, action: str, reward: float, next_state: str, next_actions: List[str]) -> None:
        self._q_table.update(state, action, reward, next_state, next_actions)
        self._reward_history.append({
            "state": state,
            "action": action,
            "reward": reward,
            "next_state": next_state,
            "time": time.time(),
        })
        self._current_state = next_state
        self._save_model()

    def suggest_action(self, state: Optional[str] = None, available_actions: Optional[List[str]] = None) -> str:
        state = state or self._current_state
        actions = available_actions or ["chat", "code", "video", "search", "memo"]
        return self._q_table.get_action(state, actions)

    def reward_last_action(self, reward: float) -> None:
        if self._reward_history:
            last = self._reward_history[-1]
            self.observe(
                last["state"],
                last["action"],
                reward,
                self._current_state,
                [],
            )

    def get_preferred_actions(self, state: str) -> List[Tuple[str, float]]:
        q_values = self._q_table.to_dict().get(state, {})
        sorted_actions = sorted(q_values.items(), key=lambda x: x[1], reverse=True)
        return sorted_actions[:5]

    def get_stats(self) -> Dict[str, Any]:
        q_data = self._q_table.to_dict()
        total_rewards = sum(r["reward"] for r in self._reward_history) if self._reward_history else 0
        return {
            "states": len(q_data),
            "total_observations": len(self._reward_history),
            "avg_reward": total_rewards / max(len(self._reward_history), 1),
            "current_state": self._current_state,
        }

    async def fallback(self, step: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]]) -> Any:
        return None

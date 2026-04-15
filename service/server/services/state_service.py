import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from core.logging_config import logger

class StateService:
    _instance = None
    _state: Dict[str, Any] = {}
    _file_path = "service/server/data/system_state.json"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateService, cls).__new__(cls)
            cls._instance._load_state()
        return cls._instance

    def _load_state(self):
        if os.path.exists(self._file_path):
            try:
                with open(self._file_path, 'r') as f:
                    self._state = json.load(f)
                logger.info("system_state_loaded", path=self._file_path)
            except Exception as e:
                logger.error("system_state_load_failed", error=str(e))
                self._state = {}
        else:
            self._state = {}

    def save_state(self):
        try:
            os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
            with open(self._file_path, 'w') as f:
                json.dump(self._state, f, indent=2)
            logger.info("system_state_saved", path=self._file_path)
        except Exception as e:
            logger.error("system_state_save_failed", error=str(e))

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def set(self, key: str, value: Any):
        self._state[key] = value
        # Periodic saving could be handled via a background task

    def set_cooldown(self, symbol: str, minutes: int):
        expiration = datetime.now(timezone.utc).timestamp() + (minutes * 60)
        cooldowns = self.get("cooldowns", {})
        cooldowns[symbol] = expiration
        self.set("cooldowns", cooldowns)

    def is_in_cooldown(self, symbol: str) -> bool:
        cooldowns = self.get("cooldowns", {})
        expiration = cooldowns.get(symbol, 0)
        return datetime.now(timezone.utc).timestamp() < expiration

state_service = StateService()

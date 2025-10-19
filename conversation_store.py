"""
Lightweight conversation state persistence
Stores per-phone_number conversation state in a JSON file for durability
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from config import Config

logger = logging.getLogger(__name__)


class ConversationStore:
    """Simple JSON-based conversation store"""

    def __init__(self, store_dir: Optional[Path] = None):
        self.store_dir = store_dir or (Config.PROJECT_ROOT / "data" / "conversations")
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.store_dir / f"conversations_{datetime.now().strftime('%Y%m%d')}.json"
        if not self.file_path.exists():
            self._write_all({})

    def _read_all(self) -> Dict:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_all(self, data: Dict):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to write conversation store: {e}")

    def get(self, phone_number: str) -> Optional[Dict]:
        return self._read_all().get(phone_number)

    def set(self, phone_number: str, state: Dict):
        data = self._read_all()
        data[phone_number] = state
        self._write_all(data)

    def delete(self, phone_number: str):
        data = self._read_all()
        if phone_number in data:
            del data[phone_number]
            self._write_all(data)


